"""User-invoked operations. Business logic lives in io.py and sync.py."""

from __future__ import annotations

from pathlib import Path

import bpy
from bpy.props import EnumProperty, IntProperty, StringProperty
from bpy_extras.io_utils import ExportHelper, ImportHelper

from . import io, sync
from .models import active_model_owner, common_sync_direction, selected_model_owners, unlink_model
from .paths import addon_preferences, relative_path, resolved_path


def _batch_result(operator, action: str, completed: int, errors: list[str]):
    if errors:
        level = {"WARNING"} if completed else {"ERROR"}
        operator.report(level, f"{action} {completed} model(s); {len(errors)} failed. See console.")
        for error in errors:
            print(f"Linker: {error}")
    else:
        operator.report({"INFO"}, f"{action} {completed} model(s)")
    return {"FINISHED"} if completed else {"CANCELLED"}


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
    bl_label = "Save Selected Models"
    bl_description = "Export every linked model represented by the selection"

    @classmethod
    def poll(cls, context):
        return bool(selected_model_owners(context))

    def execute(self, context):
        owners = selected_model_owners(context)
        completed = 0
        errors = []
        with sync.suspend_tracking():
            for owner in owners:
                name = owner.linker.model_name
                model_id = owner.linker.model_id
                try:
                    io.export_model(owner)
                    sync.mark_clean(model_id)
                    completed += 1
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
        return _batch_result(self, "Saved", completed, errors)

class LINKER_OT_ReloadModel(bpy.types.Operator):
    bl_idname = "linker.reload_model"
    bl_label = "Reload Selected Models"
    bl_description = "Reload every linked model represented by the selection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(selected_model_owners(context))

    def execute(self, context):
        owners = selected_model_owners(context)
        completed = 0
        errors = []
        with sync.suspend_tracking():
            for owner in owners:
                name = owner.linker.model_name
                model_id = owner.linker.model_id
                try:
                    io.import_model(owner)
                    sync.mark_clean(model_id)
                    completed += 1
                except Exception as exc:
                    errors.append(f"{name}: {exc}")
        return _batch_result(self, "Reloaded", completed, errors)

class LINKER_OT_SyncModel(bpy.types.Operator):
    bl_idname = "linker.sync_model"
    bl_label = "Sync Selected Models"
    bl_description = "Synchronize every linked model represented by the selection"

    @classmethod
    def poll(cls, context):
        return bool(selected_model_owners(context))

    def execute(self, context):
        completed = 0
        errors = []
        for owner in selected_model_owners(context):
            name = owner.linker.model_name
            try:
                sync.sync_model(owner, force=True)
                completed += 1
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return _batch_result(self, "Synchronized", completed, errors)

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


class LINKER_OT_SetSyncDirection(bpy.types.Operator):
    bl_idname = "linker.set_sync_direction"
    bl_label = "Set Sync Direction"
    bl_description = "Set the sync direction for every linked model represented by the selection"
    bl_options = {"REGISTER", "UNDO"}

    direction: EnumProperty(
        name="Direction",
        items=(
            ("BOTH", "Two-way", "Import file changes and export Blender changes"),
            ("IMPORT", "Import only", "Only update Blender from disk"),
            ("EXPORT", "Export only", "Only update the file from Blender"),
        ),
    )

    @classmethod
    def poll(cls, context):
        owners = selected_model_owners(context)
        return bool(owners) and common_sync_direction(context) is not None

    def execute(self, context):
        owners = selected_model_owners(context)
        if not owners or common_sync_direction(context) is None:
            self.report({"WARNING"}, "Selected models have multiple sync direction values")
            return {"CANCELLED"}
        for owner in owners:
            owner.linker.sync_direction = self.direction
        self.report({"INFO"}, f"Updated {len(owners)} model(s)")
        return {"FINISHED"}


class LINKER_OT_UnlinkModel(bpy.types.Operator):
    bl_idname = "linker.unlink_model"
    bl_label = "Unlink Selected Models"
    bl_description = "Stop tracking every linked model represented by the selection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(selected_model_owners(context))

    def execute(self, context):
        owners = selected_model_owners(context)
        for owner in owners:
            model_id = owner.linker.model_id
            unlink_model(owner)
            sync.mark_clean(model_id)
        self.report({"INFO"}, f"Unlinked {len(owners)} model(s)")
        return {"FINISHED"}

class LINKER_OT_MakeRelative(bpy.types.Operator):
    bl_idname = "linker.make_relative"
    bl_label = "Make Selected Paths Relative"
    bl_description = "Make paths relative for every linked model represented by the selection"
    bl_options = {"REGISTER", "UNDO"}

    @classmethod
    def poll(cls, context):
        return bool(selected_model_owners(context))

    def execute(self, context):
        completed = 0
        errors = []
        for owner in selected_model_owners(context):
            name = owner.linker.model_name
            try:
                owner.linker.link_path = relative_path(owner.linker.link_path)
                completed += 1
            except ValueError as exc:
                errors.append(f"{name}: {exc}")
        return _batch_result(self, "Updated", completed, errors)

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
    LINKER_OT_ToggleAutoSync, LINKER_OT_SetSyncDirection,
    LINKER_OT_UnlinkModel, LINKER_OT_MakeRelative,
    LINKER_OT_OpenLocation, LINKER_OT_VariableAdd, LINKER_OT_VariableRemove,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
