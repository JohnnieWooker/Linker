"""Batch-aware format setting metadata and propagation."""

from __future__ import annotations

import json
from contextlib import contextmanager
from pathlib import Path

from .models import active_model_owner, model_members, model_owner, selected_model_owners
from .paths import resolved_path


FORMAT_FIELDS = {
    ("fbx", "IMPORT"): (
        "global_scale",
        "use_custom_normals",
        "import_subdivision",
        "use_custom_props",
        "enums_as_strings",
        "import_colors",
        "validate_meshes",
        "material_collision",
        "use_animation",
        "animation_offset",
        "ignore_leaf_bones",
        "reimport_materials",
        "reimport_uvs",
        "reimport_transforms",
    ),
    ("fbx", "EXPORT"): (
        "global_scale",
        "use_custom_props",
        "axis_forward",
        "axis_up",
        "export_subdivision",
        "apply_unit_scale",
        "bake_space_transform",
        "use_mesh_modifiers",
        "only_deform_bones",
        "add_leaf_bones",
        "bake_animation",
    ),
    ("obj", "IMPORT"): (
        "global_scale",
        "clamp_size",
        "forward_axis",
        "up_axis",
        "split_objects",
        "split_groups",
        "import_vertex_groups",
        "validate_meshes",
        "reimport_materials",
        "reimport_uvs",
        "reimport_transforms",
    ),
    ("obj", "EXPORT"): (
        "global_scale",
        "forward_axis",
        "up_axis",
        "export_materials",
        "export_smooth_groups",
        "apply_modifiers",
    ),
}

_UPDATE_DEPTH = 0


def owner_format(owner) -> str:
    extension = Path(resolved_path(owner.linker.link_path)).suffix.lower()
    return extension.removeprefix(".") if extension in {".fbx", ".obj"} else ""


def common_format(owners) -> str | None:
    formats = {owner_format(owner) for owner in owners}
    return formats.pop() if len(formats) == 1 and "" not in formats else None


def settings_group(owner, file_format: str):
    return getattr(owner.linker, file_format)


def common_field_value(owners, file_format: str, field: str):
    values = [getattr(settings_group(owner, file_format), field) for owner in owners]
    return (True, values[0]) if values and all(value == values[0] for value in values[1:]) else (False, None)


def mixed_fields(owners, file_format: str, side: str) -> list[str]:
    return [
        field
        for field in FORMAT_FIELDS[(file_format, side)]
        if not common_field_value(owners, file_format, field)[0]
    ]


def preset_attribute(side: str) -> str:
    return "import_preset_id" if side == "IMPORT" else "export_preset_id"


def common_preset_id(owners, side: str):
    attribute = preset_attribute(side)
    values = [getattr(owner.linker, attribute) for owner in owners]
    return (True, values[0]) if values and all(value == values[0] for value in values[1:]) else (False, None)


def field_sides(file_format: str, field: str) -> tuple[str, ...]:
    return tuple(side for side in ("IMPORT", "EXPORT") if field in FORMAT_FIELDS[(file_format, side)])


@contextmanager
def suspend_batch_updates():
    global _UPDATE_DEPTH
    _UPDATE_DEPTH += 1
    try:
        yield
    finally:
        _UPDATE_DEPTH -= 1


def _set_for_model(owner, file_format: str, field: str, value) -> None:
    for member in model_members(owner):
        setattr(settings_group(member, file_format), field, value)
        for side in field_sides(file_format, field):
            setattr(member.linker, preset_attribute(side), "")


def propagate_batch_field(source_settings, context, file_format: str, field: str) -> None:
    """Propagate a UI property edit across its model and compatible selection."""
    if _UPDATE_DEPTH:
        return
    source_owner = model_owner(getattr(source_settings, "id_data", None))
    if not source_owner:
        return
    owners = [source_owner]
    active_owner = active_model_owner(context)
    selected = selected_model_owners(context)
    if (
        active_owner
        and active_owner.linker.model_id == source_owner.linker.model_id
        and common_format(selected) == file_format
    ):
        owners = selected
    value = getattr(source_settings, field)
    with suspend_batch_updates():
        for owner in owners:
            _set_for_model(owner, file_format, field, value)


def batch_update(file_format: str, field: str):
    def updated(self, context):
        propagate_batch_field(self, context, file_format, field)

    return updated


def _matches_preset(scene, member, file_format: str, side: str, preset_id: str) -> bool:
    preset = next((item for item in scene.linker_format_presets if item.preset_id == preset_id), None)
    if not preset or preset.file_format.lower() != file_format or preset.side != side:
        return False
    try:
        values = json.loads(preset.data)
    except (TypeError, json.JSONDecodeError):
        return False
    group = settings_group(member, file_format)
    return all(getattr(group, field) == value for field, value in values.items())


def apply_values(scene, owners, file_format: str, side: str, values: dict, preset_id: str) -> None:
    fields = FORMAT_FIELDS[(file_format, side)]
    opposite = "EXPORT" if side == "IMPORT" else "IMPORT"
    opposite_attribute = preset_attribute(opposite)
    with suspend_batch_updates():
        for owner in owners:
            for member in model_members(owner):
                group = settings_group(member, file_format)
                for field in fields:
                    if field in values:
                        setattr(group, field, values[field])
                setattr(member.linker, preset_attribute(side), preset_id)
                opposite_id = getattr(member.linker, opposite_attribute)
                if opposite_id and not _matches_preset(
                    scene, member, file_format, opposite, opposite_id
                ):
                    setattr(member.linker, opposite_attribute, "")


def set_preset_id(owners, side: str, preset_id: str) -> None:
    with suspend_batch_updates():
        for owner in owners:
            for member in model_members(owner):
                setattr(member.linker, preset_attribute(side), preset_id)
