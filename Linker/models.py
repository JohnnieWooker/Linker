"""Model grouping, persistent metadata, and 1.x migration."""

from __future__ import annotations

import os
import uuid

import bpy


def model_members(owner_or_id, scene=None) -> list[bpy.types.Object]:
    model_id = owner_or_id if isinstance(owner_or_id, str) else owner_or_id.linker.model_id
    objects = scene.objects if scene else bpy.data.objects
    return sorted(
        (obj for obj in objects if obj.linker.tracked and obj.linker.model_id == model_id),
        key=lambda obj: (obj.linker.object_index, obj.name),
    )


def model_owner(obj):
    if not obj or not hasattr(obj, "linker") or not obj.linker.tracked:
        return None
    members = model_members(obj)
    return members[0] if members else None


def active_model_owner(context):
    return model_owner(getattr(context, "active_object", None))


def selected_model_owners(context) -> list[bpy.types.Object]:
    """Return each linked model represented by the selection exactly once."""
    owners = {}
    for obj in getattr(context, "selected_objects", ()):
        owner = model_owner(obj)
        if owner:
            owners.setdefault(owner.linker.model_id, owner)
    if not owners:
        owner = active_model_owner(context)
        if owner:
            owners[owner.linker.model_id] = owner
    return list(owners.values())


def common_sync_direction(context) -> str | None:
    """Return the selected models' shared direction, or None for mixed values."""
    directions = {owner.linker.sync_direction for owner in selected_model_owners(context)}
    return directions.pop() if len(directions) == 1 else None


def all_model_owners(scene=None) -> list[bpy.types.Object]:
    objects = scene.objects if scene else bpy.data.objects
    owners = {}
    for obj in objects:
        if obj.linker.tracked and obj.linker.model_id:
            current = owners.get(obj.linker.model_id)
            if current is None or (obj.linker.object_index, obj.name) < (
                current.linker.object_index, current.name
            ):
                owners[obj.linker.model_id] = obj
    return sorted(owners.values(), key=lambda obj: (obj.linker.model_name.casefold(), obj.name))


def copy_property_group(source, target) -> None:
    for prop in source.bl_rna.properties:
        if prop.identifier == "rna_type" or prop.is_readonly or prop.type == "POINTER":
            continue
        try:
            setattr(target, prop.identifier, getattr(source, prop.identifier))
        except (AttributeError, TypeError, ValueError):
            pass


def copy_settings(source, target) -> None:
    from .format_settings import suspend_batch_updates

    with suspend_batch_updates():
        copy_property_group(source.linker.fbx, target.linker.fbx)
        copy_property_group(source.linker.obj, target.linker.obj)
        target.linker.import_preset_id = source.linker.import_preset_id
        target.linker.export_preset_id = source.linker.export_preset_id
        target.linker.sync_direction = source.linker.sync_direction


def assign_model(objects, raw_path: str, source=None, model_id: str | None = None) -> str:
    objects = list(objects)
    if not objects:
        raise ValueError("A linked model must contain at least one object")
    model_id = model_id or str(uuid.uuid4())
    model_name = source.linker.model_name if source else os.path.splitext(os.path.basename(raw_path))[0]
    signature = source.linker.last_sync_signature if source else ""
    direction = source.linker.sync_direction if source else "BOTH"
    for index, obj in enumerate(objects):
        settings = obj.linker
        settings.tracked = True
        settings.model_id = model_id
        settings.model_name = model_name or "Linked Model"
        settings.link_path = raw_path
        settings.last_sync_signature = signature
        settings.object_index = index
        settings.sync_direction = direction
        if source:
            copy_settings(source, obj)
    return model_id


def unlink_model(owner) -> None:
    for obj in model_members(owner):
        obj.linker.tracked = False
        obj.linker.model_id = ""


LEGACY_FBX_MAP = {
    "FBXSettings_customNormals": "use_custom_normals",
    "FBXSettings_subdData": "import_subdivision",
    "FBXSettings_customProps": "use_custom_props",
    "FBXSettings_EnumAsStrings": "enums_as_strings",
    "FBXSettings_scale": "global_scale",
    "FBXSettings_useAnim": "use_animation",
    "FBXSettings_animOffset": "animation_offset",
    "FBXSettings_ignoreLeafBones": "ignore_leaf_bones",
    "FBXSettings_forward": "axis_forward",
    "FBXSettings_up": "axis_up",
    "FBXSettings_reimportmaterials": "reimport_materials",
    "FBXSettings_reimportuvs": "reimport_uvs",
    "FBXSettings_reimportposition": "reimport_transforms",
}
LEGACY_OBJ_MAP = {
    "OBJSettings_clampSize": "clamp_size",
    "OBJSettings_splitByObject": "split_objects",
    "OBJSettings_splitByGroup": "split_groups",
    "OBJSettings_polyGroups": "import_vertex_groups",
    "OBJSettings_reimportmaterials": "reimport_materials",
    "OBJSettings_reimportuvs": "reimport_uvs",
    "OBJSettings_reimportposition": "reimport_transforms",
}


def _legacy_value(settings, name):
    try:
        return settings[name] if name in settings else getattr(settings, name)
    except (KeyError, AttributeError, TypeError):
        return None


def migrate_legacy_data() -> int:
    migrated = 0
    ids_by_path = {}
    for obj in bpy.data.objects:
        if obj.linker.tracked and obj.linker.model_id:
            continue
        old = getattr(obj, "tracking", None)
        if not old or not old.tracked or not old.linkpath:
            continue
        raw_path = old.linkpath
        model_id = ids_by_path.setdefault(raw_path.casefold(), str(uuid.uuid4()))
        new = obj.linker
        new.tracked = True
        new.model_id = model_id
        new.model_name = os.path.splitext(os.path.basename(raw_path))[0] or obj.name
        new.link_path = raw_path
        new.object_index = max(0, old.linkid)
        try:
            new.last_sync_signature = old.linktime
        except (TypeError, ValueError):
            new.last_sync_signature = ""
        for legacy_name, new_name in LEGACY_FBX_MAP.items():
            value = _legacy_value(old, legacy_name)
            if value is not None:
                try:
                    setattr(new.fbx, new_name, value)
                except (TypeError, ValueError):
                    pass
        for legacy_name, new_name in LEGACY_OBJ_MAP.items():
            value = _legacy_value(old, legacy_name)
            if value is not None:
                try:
                    setattr(new.obj, new_name, value)
                except (TypeError, ValueError):
                    pass
        migrated += 1
    return migrated
