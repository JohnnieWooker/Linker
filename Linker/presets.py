"""Project-persistent import and export preset operators and menus."""

from __future__ import annotations

import json
import uuid

import bpy
from bpy.props import EnumProperty, StringProperty

from .format_settings import (
    FORMAT_FIELDS,
    apply_values,
    common_field_value,
    common_format,
    common_preset_id,
    mixed_fields,
    preset_attribute,
    set_preset_id,
)
from .models import selected_model_owners


SIDE_ITEMS = (
    ("IMPORT", "Import", "Import and reload settings"),
    ("EXPORT", "Export", "Export settings"),
)


def find_preset(scene, preset_id: str):
    return next((preset for preset in scene.linker_format_presets if preset.preset_id == preset_id), None)


def preset_label(scene, preset_id: str) -> str:
    preset = find_preset(scene, preset_id)
    return preset.name if preset else ("Missing Preset" if preset_id else "Custom")


def _preset_context(context, side: str):
    owners = selected_model_owners(context)
    file_format = common_format(owners)
    common_selection, selected_id = common_preset_id(owners, side)
    return owners, file_format, common_selection, selected_id


class LINKER_OT_SaveFormatPreset(bpy.types.Operator):
    bl_idname = "linker.save_format_preset"
    bl_label = "Save Format Preset"
    bl_description = "Save the selected models' common settings as a project preset"
    bl_options = {"REGISTER", "UNDO"}

    side: EnumProperty(name="Settings", items=SIDE_ITEMS)
    name: StringProperty(name="Name", default="Preset")

    @classmethod
    def poll(cls, context):
        return common_format(selected_model_owners(context)) is not None

    def invoke(self, context, _event):
        self.name = f"{self.side.title()} Preset"
        return context.window_manager.invoke_props_dialog(self)

    def execute(self, context):
        owners = selected_model_owners(context)
        file_format = common_format(owners)
        name = self.name.strip()
        if not file_format or not name:
            self.report({"ERROR"}, "A common file format and preset name are required")
            return {"CANCELLED"}
        if mixed_fields(owners, file_format, self.side):
            self.report({"WARNING"}, "Selected models have multiple values")
            return {"CANCELLED"}
        values = {
            field: common_field_value(owners, file_format, field)[1]
            for field in FORMAT_FIELDS[(file_format, self.side)]
        }
        preset = next(
            (
                item
                for item in context.scene.linker_format_presets
                if item.file_format == file_format.upper()
                and item.side == self.side
                and item.name.casefold() == name.casefold()
            ),
            None,
        )
        if preset is None:
            preset = context.scene.linker_format_presets.add()
            preset.preset_id = str(uuid.uuid4())
        else:
            # Other models may still reference the old payload under this ID.
            # Mark them Custom before replacing it, then reselect it on targets.
            attribute = preset_attribute(self.side)
            for obj in bpy.data.objects:
                if getattr(obj, "linker", None) and getattr(obj.linker, attribute) == preset.preset_id:
                    setattr(obj.linker, attribute, "")
        preset.name = name
        preset.file_format = file_format.upper()
        preset.side = self.side
        preset.data = json.dumps(values, sort_keys=True)
        set_preset_id(owners, self.side, preset.preset_id)
        self.report({"INFO"}, f"Saved {self.side.lower()} preset '{name}'")
        return {"FINISHED"}


class LINKER_OT_LoadFormatPreset(bpy.types.Operator):
    bl_idname = "linker.load_format_preset"
    bl_label = "Load Format Preset"
    bl_description = "Load this preset into every selected linked model"
    bl_options = {"REGISTER", "UNDO"}

    preset_id: StringProperty(options={"HIDDEN"})
    side: EnumProperty(name="Settings", items=SIDE_ITEMS)

    @classmethod
    def poll(cls, context):
        return common_format(selected_model_owners(context)) is not None

    def execute(self, context):
        owners, file_format, common_selection, _selected_id = _preset_context(context, self.side)
        preset = find_preset(context.scene, self.preset_id)
        if not common_selection:
            self.report({"WARNING"}, "Selected models have multiple preset values")
            return {"CANCELLED"}
        if not preset or preset.file_format.lower() != file_format or preset.side != self.side:
            self.report({"ERROR"}, "The preset is missing or incompatible")
            return {"CANCELLED"}
        try:
            values = json.loads(preset.data)
        except (TypeError, json.JSONDecodeError):
            self.report({"ERROR"}, "The preset data is invalid")
            return {"CANCELLED"}
        apply_values(context.scene, owners, file_format, self.side, values, preset.preset_id)
        self.report({"INFO"}, f"Loaded preset '{preset.name}' into {len(owners)} model(s)")
        return {"FINISHED"}


class LINKER_OT_RemoveFormatPreset(bpy.types.Operator):
    bl_idname = "linker.remove_format_preset"
    bl_label = "Remove Format Preset"
    bl_description = "Remove the selected project preset"
    bl_options = {"REGISTER", "UNDO"}

    side: EnumProperty(name="Settings", items=SIDE_ITEMS)

    def execute(self, context):
        owners, _file_format, common_selection, preset_id = _preset_context(context, self.side)
        if not common_selection or not preset_id:
            self.report({"WARNING"}, "Selected models do not share a preset")
            return {"CANCELLED"}
        index = next(
            (index for index, item in enumerate(context.scene.linker_format_presets) if item.preset_id == preset_id),
            -1,
        )
        if index < 0:
            self.report({"ERROR"}, "The selected preset no longer exists")
            return {"CANCELLED"}
        context.scene.linker_format_presets.remove(index)
        for obj in bpy.data.objects:
            if getattr(obj, "linker", None) and getattr(obj.linker, preset_attribute(self.side)) == preset_id:
                setattr(obj.linker, preset_attribute(self.side), "")
        self.report({"INFO"}, f"Removed preset from {len(owners)} selected model(s)")
        return {"FINISHED"}


def _draw_presets(menu, context, side: str):
    owners = selected_model_owners(context)
    file_format = common_format(owners)
    presets = [
        preset
        for preset in context.scene.linker_format_presets
        if file_format and preset.file_format.lower() == file_format and preset.side == side
    ]
    if not presets:
        menu.layout.label(text="No saved presets", icon="INFO")
        return
    for preset in sorted(presets, key=lambda item: item.name.casefold()):
        operator = menu.layout.operator("linker.load_format_preset", text=preset.name)
        operator.preset_id = preset.preset_id
        operator.side = side


class LINKER_MT_ImportPresets(bpy.types.Menu):
    bl_idname = "LINKER_MT_import_presets"
    bl_label = "Import Presets"

    def draw(self, context):
        _draw_presets(self, context, "IMPORT")


class LINKER_MT_ExportPresets(bpy.types.Menu):
    bl_idname = "LINKER_MT_export_presets"
    bl_label = "Export Presets"

    def draw(self, context):
        _draw_presets(self, context, "EXPORT")


CLASSES = (
    LINKER_OT_SaveFormatPreset,
    LINKER_OT_LoadFormatPreset,
    LINKER_OT_RemoveFormatPreset,
    LINKER_MT_ImportPresets,
    LINKER_MT_ExportPresets,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)


def unregister():
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)
