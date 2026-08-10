"""Persistence and Linker 1.x migration smoke test for Blender background mode."""

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
from Linker.models import migrate_legacy_data  # noqa: E402


OUTPUT = Path(tempfile.mkdtemp(prefix="linker-persistence-"))
try:
    Linker.register()
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = "PersistentModel"
    linked_file = OUTPUT / "persistent.fbx"
    blend_file = OUTPUT / "persistence.blend"
    io.export_new_model([cube], str(linked_file))

    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
    model_id = cube.linker.model_id
    cube.linker.link_path = "//persistent.fbx"
    cube.linker.sync_direction = "IMPORT"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_file))
    bpy.ops.wm.open_mainfile(filepath=str(blend_file))

    restored = bpy.data.objects["PersistentModel"]
    assert restored.linker.tracked
    assert restored.linker.model_id == model_id
    assert restored.linker.link_path == "//persistent.fbx"
    assert restored.linker.sync_direction == "IMPORT"

    bpy.ops.mesh.primitive_cube_add()
    legacy = bpy.context.active_object
    legacy.tracking.tracked = True
    legacy.tracking.linkpath = str(linked_file)
    legacy.tracking.linktime = str(linked_file.stat().st_mtime)
    legacy.tracking.linkid = 0
    assert migrate_legacy_data() == 1
    assert legacy.linker.tracked and legacy.linker.model_id
    assert legacy.linker.link_path == str(linked_file)

    Linker.unregister()
    print("LINKER_PERSISTENCE_TEST_OK")
finally:
    shutil.rmtree(OUTPUT, ignore_errors=True)
