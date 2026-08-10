"""Blender import/export adapters and transactional model replacement."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

import bpy

from .models import assign_model, model_members
from .paths import resolved_path, validation_error


def _operator_exists(operator):
    try:
        operator.get_rna_type()
        return True
    except KeyError:
        return False


def _supported_kwargs(operator, kwargs):
    properties = operator.get_rna_type().properties.keys()
    return {name: value for name, value in kwargs.items() if name in properties}


def _call(operator, **kwargs):
    return operator(**_supported_kwargs(operator, kwargs))


def _native_fbx_import(path: str, settings):
    return _call(
        bpy.ops.wm.fbx_import,
        filepath=path,
        global_scale=settings.global_scale,
        use_custom_normals=settings.use_custom_normals,
        import_subdivision=settings.import_subdivision,
        use_custom_props=settings.use_custom_props,
        use_custom_props_enum_as_string=settings.enums_as_strings,
        import_colors=settings.import_colors,
        use_anim=settings.use_animation,
        anim_offset=settings.animation_offset,
        ignore_leaf_bones=settings.ignore_leaf_bones,
        validate_meshes=settings.validate_meshes,
        mtl_name_collision_mode=settings.material_collision,
    )


def _legacy_fbx_import(path: str, settings):
    return _call(
        bpy.ops.import_scene.fbx,
        filepath=path,
        global_scale=settings.global_scale,
        use_custom_normals=settings.use_custom_normals,
        use_subsurf=settings.import_subdivision,
        use_custom_props=settings.use_custom_props,
        use_custom_props_enum_as_string=settings.enums_as_strings,
        use_anim=settings.use_animation,
        anim_offset=settings.animation_offset,
        ignore_leaf_bones=settings.ignore_leaf_bones,
    )


def _import_file(path: str, tracking):
    extension = Path(path).suffix.lower()
    if extension == ".fbx":
        if _operator_exists(bpy.ops.wm.fbx_import):
            return _native_fbx_import(path, tracking.fbx)
        return _legacy_fbx_import(path, tracking.fbx)
    if extension == ".obj":
        settings = tracking.obj
        if _operator_exists(bpy.ops.wm.obj_import):
            return _call(
                bpy.ops.wm.obj_import,
                filepath=path,
                global_scale=settings.global_scale,
                clamp_size=settings.clamp_size,
                forward_axis=settings.forward_axis,
                up_axis=settings.up_axis,
                use_split_objects=settings.split_objects,
                use_split_groups=settings.split_groups,
                import_vertex_groups=settings.import_vertex_groups,
                validate_meshes=settings.validate_meshes,
            )
        def legacy_axis(value):
            return value.replace("NEGATIVE_", "-")
        return _call(
            bpy.ops.import_scene.obj,
            filepath=path,
            global_clamp_size=settings.clamp_size,
            axis_forward=legacy_axis(settings.forward_axis),
            axis_up=legacy_axis(settings.up_axis),
            use_split_objects=settings.split_objects,
            use_split_groups=settings.split_groups,
            use_groups_as_vgroups=settings.import_vertex_groups,
        )
    raise ValueError(f"Unsupported model format: {extension}")


def _export_file(path: str, tracking):
    extension = Path(path).suffix.lower()
    if extension == ".fbx":
        settings = tracking.fbx
        return _call(
            bpy.ops.export_scene.fbx,
            filepath=path,
            use_selection=True,
            global_scale=settings.global_scale,
            use_custom_props=settings.use_custom_props,
            axis_forward=settings.axis_forward,
            axis_up=settings.axis_up,
            use_subsurf=settings.export_subdivision,
            apply_unit_scale=settings.apply_unit_scale,
            bake_space_transform=settings.bake_space_transform,
            use_mesh_modifiers=settings.use_mesh_modifiers,
            use_armature_deform_only=settings.only_deform_bones,
            add_leaf_bones=settings.add_leaf_bones,
            bake_anim=settings.bake_animation,
        )
    if extension == ".obj":
        settings = tracking.obj
        if _operator_exists(bpy.ops.wm.obj_export):
            return _call(
                bpy.ops.wm.obj_export,
                filepath=path,
                export_selected_objects=True,
                global_scale=settings.global_scale,
                forward_axis=settings.forward_axis,
                up_axis=settings.up_axis,
                export_materials=settings.export_materials,
                export_smooth_groups=settings.export_smooth_groups,
                apply_modifiers=settings.apply_modifiers,
            )
        def legacy_axis(value):
            return value.replace("NEGATIVE_", "-")
        return _call(
            bpy.ops.export_scene.obj,
            filepath=path,
            use_selection=True,
            axis_forward=legacy_axis(settings.forward_axis),
            axis_up=legacy_axis(settings.up_axis),
            use_materials=settings.export_materials,
            use_smooth_groups=settings.export_smooth_groups,
            use_modifiers=settings.apply_modifiers,
        )
    raise ValueError(f"Unsupported model format: {extension}")


def _walk_layer_collections(layer_collection):
    yield layer_collection
    for child in layer_collection.children:
        yield from _walk_layer_collections(child)


def _layer_collections_for_objects(root, objects):
    targets = {collection for obj in objects for collection in obj.users_collection}
    result = []

    def visit(layer_collection, path):
        path = (*path, layer_collection)
        if layer_collection.collection in targets:
            for item in path:
                if item not in result:
                    result.append(item)
        for child in layer_collection.children:
            visit(child, path)

    visit(root, ())
    return result


def _find_layer_collection(root, collection):
    for layer_collection in _walk_layer_collections(root):
        if layer_collection.collection == collection:
            return layer_collection
    return None


@contextmanager
def preserved_context(expose_objects=()):
    """Restore mode, active object, selection, and viewport visibility."""
    expose_objects = tuple(expose_objects)
    view_layer = bpy.context.view_layer
    selected_names = [obj.name for obj in view_layer.objects if obj.select_get()]
    active = view_layer.objects.active
    active_name = active.name if active else None
    old_mode = active.mode if active and active.mode != "OBJECT" else None
    visibility = {}
    layer_visibility = []
    collection_visibility = {}

    if expose_objects:
        layers = _layer_collections_for_objects(view_layer.layer_collection, expose_objects)
        for layer_collection in layers:
            collection = layer_collection.collection
            layer_visibility.append((
                collection, layer_collection.exclude, layer_collection.hide_viewport
            ))
            collection_visibility.setdefault(collection, collection.hide_viewport)

        # Snapshot every flag before assignments that can rebuild LayerCollection RNA.
        for collection in collection_visibility:
            if not collection_visibility[collection]:
                continue
            collection.hide_viewport = False
        for collection, _excluded, _hidden in layer_visibility:
            if not (_excluded or _hidden):
                continue
            layer_collection = _find_layer_collection(view_layer.layer_collection, collection)
            if not layer_collection:
                continue
            layer_collection.exclude = False
            layer_collection = _find_layer_collection(view_layer.layer_collection, collection)
            if layer_collection:
                layer_collection.hide_viewport = False

    for obj in expose_objects:
        if obj.name not in view_layer.objects:
            continue
        visibility[obj.name] = (obj.hide_viewport, obj.hide_get(view_layer=view_layer), obj.hide_select)
        obj.hide_viewport = False
        obj.hide_select = False
        obj.hide_set(False, view_layer=view_layer)

    if old_mode:
        bpy.ops.object.mode_set(mode="OBJECT")
    try:
        yield
    finally:
        if view_layer:
            # Imported replacements reuse the old names. Expose them before
            # restoring the original selection and active object.
            for name in visibility:
                obj = view_layer.objects.get(name)
                if obj:
                    obj.hide_viewport = False
                    obj.hide_select = False
                    obj.hide_set(False, view_layer=view_layer)

            bpy.ops.object.select_all(action="DESELECT")
            for name in selected_names:
                obj = view_layer.objects.get(name)
                if obj:
                    try:
                        obj.select_set(True, view_layer=view_layer)
                    except RuntimeError:
                        pass

            restored_active = view_layer.objects.get(active_name) if active_name else None
            if restored_active:
                view_layer.objects.active = restored_active
                if old_mode:
                    try:
                        bpy.ops.object.mode_set(mode=old_mode)
                    except RuntimeError:
                        pass

            for name, (hide_viewport, hidden, hide_select) in visibility.items():
                obj = view_layer.objects.get(name)
                if obj:
                    obj.hide_set(hidden, view_layer=view_layer)
                    obj.hide_viewport = hide_viewport
                    obj.hide_select = hide_select

            # Global collection flags rebuild the layer tree, so restore them
            # before applying per-view-layer flags through fresh RNA handles.
            for collection, hidden in collection_visibility.items():
                if not hidden:
                    continue
                collection.hide_viewport = hidden
            # Restore ancestors first; changing an ancestor rebuilds its child layers.
            for collection, excluded, hidden in layer_visibility:
                if not (excluded or hidden):
                    continue
                layer_collection = _find_layer_collection(view_layer.layer_collection, collection)
                if not layer_collection:
                    continue
                layer_collection.hide_viewport = hidden
                layer_collection = _find_layer_collection(view_layer.layer_collection, collection)
                if not layer_collection:
                    continue
                layer_collection.exclude = excluded


def _select_only(objects):
    bpy.ops.object.select_all(action="DESELECT")
    objects = list(objects)
    for obj in objects:
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def _file_signature(path: str) -> str:
    return str(Path(path).stat().st_mtime_ns)


def _mark_synced(objects, signature: str) -> None:
    for obj in objects:
        obj.linker.last_sync_signature = signature


def import_new_model(raw_path: str) -> list[bpy.types.Object]:
    error = validation_error(raw_path)
    if error:
        raise ValueError(error)
    path = resolved_path(raw_path)
    before = set(bpy.data.objects)
    bpy.ops.object.select_all(action="DESELECT")
    # An untracked object still provides persisted default import settings.
    settings_source = bpy.context.active_object
    if settings_source is None:
        settings_source = bpy.data.objects.new("Linker Import Settings", None)
        temporary = True
    else:
        temporary = False
    try:
        _import_file(path, settings_source.linker)
    finally:
        if temporary:
            bpy.data.objects.remove(settings_source)
    imported = [obj for obj in bpy.data.objects if obj not in before and obj != settings_source]
    if not imported:
        raise RuntimeError("The importer did not create any objects")
    assign_model(imported, raw_path)
    _mark_synced(imported, _file_signature(path))
    _select_only(imported)
    return imported


def export_new_model(objects, raw_path: str) -> list[bpy.types.Object]:
    objects = list(objects)
    if not objects:
        raise ValueError("Select at least one object to export")
    error = validation_error(raw_path, require_exists=False)
    if error:
        raise ValueError(error)
    path = resolved_path(raw_path)
    if not Path(path).parent.is_dir():
        raise ValueError("The export directory does not exist")
    with preserved_context(objects):
        _select_only(objects)
        _export_file(path, objects[0].linker)
    assign_model(objects, raw_path)
    _mark_synced(objects, _file_signature(path))
    return objects


def export_model(owner) -> list[bpy.types.Object]:
    raw_path = owner.linker.link_path
    error = validation_error(raw_path, require_exists=False)
    if error:
        raise ValueError(error)
    path = resolved_path(raw_path)
    if not Path(path).parent.is_dir():
        raise ValueError("The export directory does not exist")
    members = model_members(owner)
    with preserved_context(members):
        _select_only(members)
        _export_file(path, owner.linker)
    _mark_synced(members, _file_signature(path))
    return members


def _snapshot(obj):
    result = {
        "name": obj.name,
        "matrix": obj.matrix_world.copy(),
        "materials": list(obj.data.materials) if hasattr(obj.data, "materials") else [],
        "uvs": [],
    }
    if obj.type == "MESH":
        for layer in obj.data.uv_layers:
            result["uvs"].append((layer.name, [loop.uv.copy() for loop in layer.data]))
    return result


def _restore_snapshot(obj, snapshot, tracking):
    format_settings = tracking.fbx if Path(tracking.link_path).suffix.lower() == ".fbx" else tracking.obj
    if not format_settings.reimport_transforms:
        obj.matrix_world = snapshot["matrix"]
    if not format_settings.reimport_materials and hasattr(obj.data, "materials"):
        obj.data.materials.clear()
        for material in snapshot["materials"]:
            obj.data.materials.append(material)
    if not format_settings.reimport_uvs and obj.type == "MESH":
        for layer_name, coordinates in snapshot["uvs"]:
            if len(coordinates) != len(obj.data.loops):
                continue
            layer = obj.data.uv_layers.get(layer_name) or obj.data.uv_layers.new(name=layer_name)
            for loop, uv in zip(layer.data, coordinates):
                loop.uv = uv


def import_model(owner) -> list[bpy.types.Object]:
    error = validation_error(owner.linker.link_path)
    if error:
        raise ValueError(error)
    path = resolved_path(owner.linker.link_path)
    old_members = model_members(owner)
    snapshots = [_snapshot(obj) for obj in old_members]
    before = set(bpy.data.objects)
    with preserved_context(old_members):
        bpy.ops.object.select_all(action="DESELECT")
        _import_file(path, owner.linker)
        imported = [obj for obj in bpy.data.objects if obj not in before]
        if not imported:
            raise RuntimeError("The importer did not create any objects; the existing model was kept")
        assign_model(imported, owner.linker.link_path, source=owner, model_id=owner.linker.model_id)
        for index, obj in enumerate(imported):
            if index < len(snapshots):
                _restore_snapshot(obj, snapshots[index], owner.linker)
        for obj in old_members:
            bpy.data.objects.remove(obj, do_unlink=True)
        for obj, snapshot in zip(imported, snapshots):
            obj.name = snapshot["name"]
        _mark_synced(imported, _file_signature(path))
    return imported
