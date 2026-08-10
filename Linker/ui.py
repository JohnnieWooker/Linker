"""3D Viewport sidebar UI."""

from __future__ import annotations

from pathlib import Path

import bpy

from .models import (
    active_model_owner,
    all_model_owners,
    common_sync_direction,
    model_members,
    selected_model_owners,
)
from .format_settings import (
    common_field_value,
    common_format,
    common_preset_id,
    mixed_fields,
)
from .paths import resolved_path, validation_error
from .presets import preset_label
from .sync import is_dirty


class LINKER_PT_Main(bpy.types.Panel):
    bl_label = "Linker"
    bl_idname = "LINKER_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Linker"

    def draw(self, context):
        layout = self.layout
        top = layout.row(align=True)
        auto = context.scene.linker_auto_sync
        top.operator(
            "linker.toggle_auto_sync",
            text="Auto Sync On" if auto else "Auto Sync Off",
            icon="PAUSE" if auto else "PLAY",
            depress=auto,
        )
        top.operator("linker.sync_all", text="", icon="FILE_REFRESH")

        owner = active_model_owner(context)
        if not owner:
            empty = layout.box()
            empty.label(text="No linked model selected", icon="INFO")
            empty.operator("linker.sync_all", text="Sync All", icon="FILE_REFRESH")
            row = empty.row(align=True)
            row.operator("linker.link_existing", text="Link Existing", icon="IMPORT")
            export_row = row.row(align=True)
            export_row.enabled = bool(context.selected_objects)
            export_row.operator("linker.export_selection", text="Export Selection", icon="EXPORT")
            return

        settings = owner.linker
        batch_count = len(selected_model_owners(context))
        box = layout.box()
        header = box.row()
        header.label(text=settings.model_name, icon="LINKED")
        header.label(text=f"{len(model_members(owner))} object(s)")
        shared_direction = common_sync_direction(context)
        direction = box.column(align=True)
        direction.enabled = shared_direction is not None
        for value, label, icon in (
            ("BOTH", "Two-way", "ARROW_LEFTRIGHT"),
            ("IMPORT", "Import only", "IMPORT"),
            ("EXPORT", "Export only", "EXPORT"),
        ):
            operator = direction.operator(
                "linker.set_sync_direction",
                text=label,
                icon=icon,
                depress=shared_direction == value,
            )
            operator.direction = value
        if shared_direction is None:
            box.label(text="Multiple values", icon="INFO")

        actions = box.row(align=True)
        actions.operator("linker.sync_model", text=f"Sync ({batch_count})", icon="FILE_REFRESH")
        actions.operator("linker.save_model", text=f"Save ({batch_count})", icon="EXPORT")
        actions.operator("linker.reload_model", text=f"Reload ({batch_count})", icon="IMPORT")

        path_box = layout.box()
        path_box.label(text="Linked File")
        path_box.prop(settings, "link_path", text="")
        error = validation_error(settings.link_path, require_exists=settings.sync_direction != "EXPORT")
        status = path_box.row()
        status.alert = bool(error)
        status.label(
            text=error or resolved_path(settings.link_path),
            icon="ERROR" if error else "CHECKMARK",
        )
        if error:
            path_box.operator("linker.sync_all", text="Sync All Valid Models", icon="FILE_REFRESH")
        path_actions = path_box.row(align=True)
        path_actions.operator("linker.make_relative", text=f"Relative ({batch_count})", icon="FILE_PARENT")
        path_actions.operator("linker.open_location", icon="FILE_FOLDER")
        path_actions.operator("linker.unlink_model", text=f"Unlink ({batch_count})", icon="UNLINKED")

        if is_dirty(settings.model_id):
            layout.label(text="Blender model has unsaved changes", icon="DOT")


def _batch_property(layout, settings, owners, file_format, field, batch_enabled=True, **kwargs):
    common, _value = common_field_value(owners, file_format, field)
    row = layout.row()
    row.enabled = batch_enabled and common and kwargs.pop("enabled", True)
    row.prop(settings, field, **kwargs)


def _preset_controls(layout, context, owners, file_format, side, batch_enabled):
    fields_mixed = bool(mixed_fields(owners, file_format, side)) if batch_enabled else True
    common_selection, preset_id = common_preset_id(owners, side)
    if fields_mixed or not common_selection:
        layout.label(text="Multiple values", icon="INFO")

    row = layout.row(align=True)
    row.enabled = batch_enabled and common_selection
    menu_id = "LINKER_MT_import_presets" if side == "IMPORT" else "LINKER_MT_export_presets"
    row.menu(menu_id, text=preset_label(context.scene, preset_id or ""), icon="PRESET")

    save = row.row(align=True)
    save.enabled = not fields_mixed
    operator = save.operator("linker.save_format_preset", text="", icon="ADD")
    operator.side = side

    remove = row.row(align=True)
    remove.enabled = bool(preset_id and preset_label(context.scene, preset_id) != "Missing Preset")
    operator = remove.operator("linker.remove_format_preset", text="", icon="REMOVE")
    operator.side = side


class LINKER_PT_FormatSettings(bpy.types.Panel):
    bl_label = "Import / Export Settings"
    bl_idname = "LINKER_PT_format_settings"
    bl_parent_id = "LINKER_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Linker"
    bl_options = {"DEFAULT_CLOSED"}

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def draw(self, context):
        layout = self.layout
        owner = active_model_owner(context)
        owners = selected_model_owners(context)
        extension = Path(resolved_path(owner.linker.link_path)).suffix.lower()
        file_format = extension.removeprefix(".")
        batch_enabled = common_format(owners) == file_format
        if not batch_enabled:
            layout.label(text="Multiple values (file formats)", icon="INFO")

        if extension == ".fbx":
            self._draw_fbx(layout, context, owner.linker.fbx, owners, batch_enabled)
        elif extension == ".obj":
            self._draw_obj(layout, context, owner.linker.obj, owners, batch_enabled)
        else:
            layout.label(text="Set a valid .fbx or .obj path", icon="INFO")

    @staticmethod
    def _draw_fbx(layout, context, settings, owners, batch_enabled):
        imported = layout.box()
        imported.label(text="FBX Import")
        _preset_controls(imported, context, owners, "fbx", "IMPORT", batch_enabled)
        for field in (
            "global_scale",
            "use_custom_normals",
            "import_subdivision",
            "use_custom_props",
            "enums_as_strings",
            "import_colors",
            "validate_meshes",
            "material_collision",
            "use_animation",
        ):
            _batch_property(imported, settings, owners, "fbx", field, batch_enabled)
        animation_common, animation_enabled = common_field_value(owners, "fbx", "use_animation")
        _batch_property(
            imported,
            settings,
            owners,
            "fbx",
            "animation_offset",
            batch_enabled,
            enabled=animation_common and animation_enabled,
        )
        _batch_property(imported, settings, owners, "fbx", "ignore_leaf_bones", batch_enabled)
        imported.separator()
        imported.label(text="On Reload")
        for field in ("reimport_materials", "reimport_uvs", "reimport_transforms"):
            _batch_property(imported, settings, owners, "fbx", field, batch_enabled)

        exported = layout.box()
        exported.label(text="FBX Export")
        _preset_controls(exported, context, owners, "fbx", "EXPORT", batch_enabled)
        for field in (
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
        ):
            _batch_property(exported, settings, owners, "fbx", field, batch_enabled)

    @staticmethod
    def _draw_obj(layout, context, settings, owners, batch_enabled):
        imported = layout.box()
        imported.label(text="OBJ Import")
        _preset_controls(imported, context, owners, "obj", "IMPORT", batch_enabled)
        for field in (
            "global_scale",
            "clamp_size",
            "forward_axis",
            "up_axis",
            "split_objects",
            "split_groups",
            "import_vertex_groups",
            "validate_meshes",
        ):
            _batch_property(imported, settings, owners, "obj", field, batch_enabled)
        imported.separator()
        imported.label(text="On Reload")
        for field in ("reimport_materials", "reimport_uvs", "reimport_transforms"):
            _batch_property(imported, settings, owners, "obj", field, batch_enabled)

        exported = layout.box()
        exported.label(text="OBJ Export")
        _preset_controls(exported, context, owners, "obj", "EXPORT", batch_enabled)
        for field in (
            "global_scale",
            "forward_axis",
            "up_axis",
            "export_materials",
            "export_smooth_groups",
            "apply_modifiers",
        ):
            _batch_property(exported, settings, owners, "obj", field, batch_enabled)

class LINKER_PT_Models(bpy.types.Panel):
    bl_label = "Linked Models"
    bl_idname = "LINKER_PT_models"
    bl_parent_id = "LINKER_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Linker"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        owners = all_model_owners(context.scene)
        if not owners:
            layout.label(text="No linked models in this scene")
            return
        for owner in owners:
            box = layout.box()
            row = box.row()
            row.label(text=owner.linker.model_name, icon="OBJECT_DATA")
            row.label(text=owner.linker.sync_direction.title())
            box.label(text=owner.linker.link_path, icon="FILE")


CLASSES = (LINKER_PT_Main, LINKER_PT_FormatSettings, LINKER_PT_Models)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
