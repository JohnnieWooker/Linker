"""Run with: blender --background --factory-startup --python tests/smoke_blender.py"""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import bpy

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

import Linker  # noqa: E402
from Linker import io, sync  # noqa: E402
from Linker.models import model_members  # noqa: E402


def new_cube(name):
    bpy.ops.mesh.primitive_cube_add()
    cube = bpy.context.active_object
    cube.name = name
    return cube


def round_trip(extension):
    cube = new_cube(f"Source_{extension[1:]}")
    path = OUTPUT / f"round_trip{extension}"
    io.export_new_model([cube], str(path))
    assert path.is_file(), path
    assert cube.linker.tracked and len(model_members(cube)) == 1

    model_id = cube.linker.model_id
    imported = io.import_model(cube)
    assert imported and imported[0].linker.model_id == model_id
    assert imported[0].linker.last_sync_signature == str(path.stat().st_mtime_ns)
    for obj in imported:
        bpy.data.objects.remove(obj, do_unlink=True)


OUTPUT = Path(tempfile.mkdtemp(prefix="linker-smoke-"))
try:
    Linker.register()
    round_trip(".fbx")
    round_trip(".obj")
    assert bpy.app.timers.is_registered(sync.timer_callback)
    Linker.unregister()
    print("LINKER_SMOKE_TEST_OK")
finally:
    shutil.rmtree(OUTPUT, ignore_errors=True)
