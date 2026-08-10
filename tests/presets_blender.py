"""Batch format settings and project-preset persistence regression test."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import bpy

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

import Linker  # noqa: E402
from Linker import io  # noqa: E402
from Linker.format_settings import common_field_value, common_preset_id, mixed_fields  # noqa: E402


def new_linked_cube(name, path):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = name
    io.export_new_model([obj], str(path))
    return obj


def select_only(objects, active):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


OUTPUT = Path(tempfile.mkdtemp(prefix="linker-presets-"))
try:
    Linker.register()
    model_a = new_linked_cube("PresetModelA", OUTPUT / "preset_a.fbx")
    model_b = new_linked_cube("PresetModelB", OUTPUT / "preset_b.fbx")
    select_only([model_a, model_b], model_a)
    owners = [model_a, model_b]

    # A direct UI-style edit on the active owner propagates across the selection.
    model_a.linker.fbx.global_scale = 2.5
    assert common_field_value(owners, "fbx", "global_scale") == (True, 2.5)

    # A mixed field disables preset saving until the values are resolved.
    select_only([model_b], model_b)
    model_b.linker.fbx.use_animation = False
    select_only([model_a, model_b], model_a)
    assert "use_animation" in mixed_fields(owners, "fbx", "IMPORT")
    assert bpy.ops.linker.save_format_preset(side="IMPORT", name="Mixed") == {"CANCELLED"}
    select_only([model_b], model_b)
    model_b.linker.fbx.use_animation = True
    select_only([model_a, model_b], model_a)

    assert bpy.ops.linker.save_format_preset(side="IMPORT", name="Studio Import") == {"FINISHED"}
    import_preset = next(item for item in bpy.context.scene.linker_format_presets if item.side == "IMPORT")
    assert common_preset_id(owners, "IMPORT") == (True, import_preset.preset_id)

    model_a.linker.fbx.axis_forward = "-X"
    assert model_b.linker.fbx.axis_forward == "-X"
    assert bpy.ops.linker.save_format_preset(side="EXPORT", name="Studio Export") == {"FINISHED"}
    export_preset = next(item for item in bpy.context.scene.linker_format_presets if item.side == "EXPORT")
    assert common_preset_id(owners, "EXPORT") == (True, export_preset.preset_id)

    # Manual changes mark affected selections Custom; compatible import/export
    # presets can then be loaded and remain selected independently.
    model_a.linker.fbx.global_scale = 4.0
    assert common_preset_id(owners, "IMPORT") == (True, "")
    assert common_preset_id(owners, "EXPORT") == (True, "")
    assert bpy.ops.linker.load_format_preset(
        preset_id=import_preset.preset_id, side="IMPORT"
    ) == {"FINISHED"}
    assert bpy.ops.linker.load_format_preset(
        preset_id=export_preset.preset_id, side="EXPORT"
    ) == {"FINISHED"}
    assert common_preset_id(owners, "IMPORT") == (True, import_preset.preset_id)
    assert common_preset_id(owners, "EXPORT") == (True, export_preset.preset_id)

    # Mixed dropdown selections guard against an accidental batch overwrite.
    model_b.linker.import_preset_id = ""
    assert common_preset_id(owners, "IMPORT") == (False, None)
    assert bpy.ops.linker.load_format_preset(
        preset_id=import_preset.preset_id, side="IMPORT"
    ) == {"CANCELLED"}
    model_b.linker.import_preset_id = import_preset.preset_id

    blend_path = OUTPUT / "preset_persistence.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    bpy.ops.wm.open_mainfile(filepath=str(blend_path))
    restored_a = bpy.data.objects["PresetModelA"]
    restored_b = bpy.data.objects["PresetModelB"]
    assert len(bpy.context.scene.linker_format_presets) == 2
    assert restored_a.linker.import_preset_id == restored_b.linker.import_preset_id
    assert restored_a.linker.export_preset_id == restored_b.linker.export_preset_id
    assert restored_a.linker.fbx.global_scale == 2.5
    assert restored_b.linker.fbx.axis_forward == "-X"

    Linker.unregister()
    print("LINKER_PRESET_TEST_OK")
finally:
    shutil.rmtree(OUTPUT, ignore_errors=True)
