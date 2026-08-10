"""3D Viewport sidebar UI."""

from __future__ import annotations

from pathlib import Path

import bpy

from .models import active_model_owner, all_model_owners, model_members
from .paths import resolved_path, validation_error
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
        box = layout.box()
        header = box.row()
        header.label(text=settings.model_name, icon="LINKED")
        header.label(text=f"{len(model_members(owner))} object(s)")
        box.prop(settings, "sync_direction", expand=True)

        actions = box.row(align=True)
        actions.operator("linker.sync_model", text="Sync", icon="FILE_REFRESH")
        actions.operator("linker.save_model", text="Save", icon="EXPORT")
        actions.operator("linker.reload_model", text="Reload", icon="IMPORT")

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
        path_actions.operator("linker.make_relative", icon="FILE_PARENT")
        path_actions.operator("linker.open_location", icon="FILE_FOLDER")
        path_actions.operator("linker.unlink_model", icon="UNLINKED")

        if is_dirty(settings.model_id):
            layout.label(text="Blender model has unsaved changes", icon="DOT")


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
        extension = Path(resolved_path(owner.linker.link_path)).suffix.lower()
        if extension == ".fbx":
            settings = owner.linker.fbx
            imported = layout.box()
            imported.label(text="FBX Import (Blender 5.1 Native)")
            imported.prop(settings, "global_scale")
            imported.prop(settings, "use_custom_normals")
            imported.prop(settings, "import_subdivision")
            imported.prop(settings, "use_custom_props")
            imported.prop(settings, "enums_as_strings")
            imported.prop(settings, "import_colors")
            imported.prop(settings, "validate_meshes")
            imported.prop(settings, "material_collision")
            imported.prop(settings, "use_animation")
            anim = imported.row()
            anim.enabled = settings.use_animation
            anim.prop(settings, "animation_offset")
            imported.prop(settings, "ignore_leaf_bones")

            exported = layout.box()
            exported.label(text="FBX Export")
            axes = exported.row(align=True)
            axes.prop(settings, "axis_forward")
            axes.prop(settings, "axis_up")
            exported.prop(settings, "export_subdivision")
            exported.prop(settings, "apply_unit_scale")
            exported.prop(settings, "bake_space_transform")
            exported.prop(settings, "use_mesh_modifiers")
            exported.prop(settings, "only_deform_bones")
            exported.prop(settings, "add_leaf_bones")
            exported.prop(settings, "bake_animation")
        elif extension == ".obj":
            settings = owner.linker.obj
            layout.prop(settings, "global_scale")
            layout.prop(settings, "clamp_size")
            axes = layout.row(align=True)
            axes.prop(settings, "forward_axis")
            axes.prop(settings, "up_axis")
            layout.prop(settings, "split_objects")
            layout.prop(settings, "split_groups")
            layout.prop(settings, "import_vertex_groups")
            layout.prop(settings, "validate_meshes")
            layout.separator()
            layout.prop(settings, "export_materials")
            layout.prop(settings, "export_smooth_groups")
            layout.prop(settings, "apply_modifiers")
        else:
            layout.label(text="Set a valid .fbx or .obj path", icon="INFO")

        if extension in {".fbx", ".obj"}:
            preserve = layout.box()
            preserve.label(text="On Reload")
            preserve.prop(settings, "reimport_materials")
            preserve.prop(settings, "reimport_uvs")
            preserve.prop(settings, "reimport_transforms")


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
