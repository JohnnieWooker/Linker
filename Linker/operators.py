"""User-invoked operations. Business logic lives in io.py and sync.py."""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.props import IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import io, sync
from .models import active_model_owner, unlink_model
from .paths import addon_preferences, relative_path, resolved_path


class LINKER_OT_LinkExisting(bpy.types.Operator, ImportHelper):
    bl_idname = "linker.link_existing"
    bl_label = "Link Existing Model"
    bl_description = "Import an FBX or OBJ and link the imported objects to it"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx;*.obj", options={"HIDDEN"})

    def execute(self, _context):
        try:
            with sync.suspend_tracking():
                imported = io.import_new_model(self.filepath)
            sync.mark_clean(imported[0].linker.model_id)
            self.report({"INFO"}, f"Linked {len(imported)} object(s)")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_ExportSelection(bpy.types.Operator, ExportHelper):
    bl_idname = "linker.export_selection"
    bl_label = "Export and Link Selection"
    bl_description = "Export selected objects and treat them as one linked model"
    bl_options = {"REGISTER", "UNDO"}
    filename_ext = ".fbx"
    filter_glob: StringProperty(default="*.fbx;*.obj", options={"HIDDEN"})

    @classmethod
    def poll(cls, context):
        return bool(context.selected_objects)

    def execute(self, context):
        try:
            objects = list(context.selected_objects)
            with sync.suspend_tracking():
                io.export_new_model(objects, self.filepath)
            sync.mark_clean(objects[0].linker.model_id)
            self.report({"INFO"}, f"Exported and linked {len(objects)} object(s)")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_SaveModel(bpy.types.Operator):
    bl_idname = "linker.save_model"
    bl_label = "Save Model"
    bl_description = "Export this linked model now, regardless of automatic sync direction"

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        owner = active_model_owner(context)
        try:
            with sync.suspend_tracking():
                io.export_model(owner)
            sync.mark_clean(owner.linker.model_id)
            self.report({"INFO"}, f"Saved {owner.linker.model_name}")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_ReloadModel(bpy.types.Operator):
    bl_idname = "linker.reload_model"
    bl_label = "Reload Model"
    bl_description = "Import the linked file now, replacing this model"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        owner = active_model_owner(context)
        model_id = owner.linker.model_id
        try:
            with sync.suspend_tracking():
                imported = io.import_model(owner)
            sync.mark_clean(model_id)
            self.report({"INFO"}, f"Reloaded {len(imported)} object(s)")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_SyncModel(bpy.types.Operator):
    bl_idname = "linker.sync_model"
    bl_label = "Sync Model"
    bl_description = "Run one synchronization pass for the selected linked model"

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        owner = active_model_owner(context)
        try:
            action = sync.sync_model(owner, force=True)
            self.report({"INFO"}, "Model is up to date" if action == "CLEAN" else f"{action.title()} completed")
            return {"FINISHED"}
        except Exception as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_SyncAll(bpy.types.Operator):
    bl_idname = "linker.sync_all"
    bl_label = "Sync All"
    bl_description = "Run one synchronization pass for every valid linked model"

    def execute(self, context):
        results = sync.sync_all(context.scene, force=True)
        errors = [f"{name}: {error}" for name, action, error in results if action == "ERROR"]
        changed = sum(action in {"IMPORT", "EXPORT"} for _, action, _ in results)
        if errors:
            self.report({"WARNING"}, f"Synced {changed}; {len(errors)} failed. See console.")
            for error in errors:
                print(f"Linker: {error}")
        else:
            self.report({"INFO"}, f"Processed {len(results)} model(s); synchronized {changed}")
        return {"FINISHED"}


class LINKER_OT_ToggleAutoSync(bpy.types.Operator):
    bl_idname = "linker.toggle_auto_sync"
    bl_label = "Toggle Automatic Sync"

    def execute(self, context):
        context.scene.linker_auto_sync = not context.scene.linker_auto_sync
        sync.ensure_timer()
        state = "enabled" if context.scene.linker_auto_sync else "disabled"
        self.report({"INFO"}, f"Automatic sync {state}")
        return {"FINISHED"}


class LINKER_OT_UnlinkModel(bpy.types.Operator):
    bl_idname = "linker.unlink_model"
    bl_label = "Unlink Model"
    bl_description = "Stop tracking this model without deleting its objects or file"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        owner = active_model_owner(context)
        model_id = owner.linker.model_id
        unlink_model(owner)
        sync.mark_clean(model_id)
        return {"FINISHED"}


class LINKER_OT_MakeRelative(bpy.types.Operator):
    bl_idname = "linker.make_relative"
    bl_label = "Make Relative"
    bl_description = "Store the link relative to the saved .blend file"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        owner = active_model_owner(context)
        try:
            owner.linker.link_path = relative_path(owner.linker.link_path)
            return {"FINISHED"}
        except ValueError as exc:
            self.report({"ERROR"}, str(exc))
            return {"CANCELLED"}


class LINKER_OT_OpenLocation(bpy.types.Operator):
    bl_idname = "linker.open_location"
    bl_label = "Open File Location"

    @classmethod
    def poll(cls, context):
        return active_model_owner(context) is not None

    def execute(self, context):
        path = Path(resolved_path(active_model_owner(context).linker.link_path))
        bpy.ops.wm.path_open(filepath=str(path.parent))
        return {"FINISHED"}


class LINKER_OT_VariableAdd(bpy.types.Operator):
    bl_idname = "linker.variable_add"
    bl_label = "Add Variable"

    def execute(self, _context):
        preferences = addon_preferences()
        item = preferences.variables.add()
        item.name = "PROJECT_ROOT"
        return {"FINISHED"}


class LINKER_OT_VariableRemove(bpy.types.Operator):
    bl_idname = "linker.variable_remove"
    bl_label = "Remove Variable"
    index: IntProperty(default=-1)

    def execute(self, _context):
        preferences = addon_preferences()
        if 0 <= self.index < len(preferences.variables):
            preferences.variables.remove(self.index)
        return {"FINISHED"}


CLASSES = (
    LINKER_OT_LinkExisting, LINKER_OT_ExportSelection, LINKER_OT_SaveModel,
    LINKER_OT_ReloadModel, LINKER_OT_SyncModel, LINKER_OT_SyncAll,
    LINKER_OT_ToggleAutoSync, LINKER_OT_UnlinkModel, LINKER_OT_MakeRelative,
    LINKER_OT_OpenLocation, LINKER_OT_VariableAdd, LINKER_OT_VariableRemove,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
