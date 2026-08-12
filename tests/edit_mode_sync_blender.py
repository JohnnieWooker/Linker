"""Automatic synchronization must not disturb an active Edit Mode session."""

from __future__ import annotations

import shutil
import sys
import tempfile
from pathlib import Path

import bmesh
import bpy

REPOSITORY = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPOSITORY))

import Linker  # noqa: E402
from Linker import io, sync  # noqa: E402


OUTPUT = Path(tempfile.mkdtemp(prefix="linker-edit-sync-"))
try:
    Linker.register()

    bpy.ops.mesh.primitive_cube_add()
    edited = bpy.context.active_object
    edited.name = "EditedMember"
    bpy.ops.mesh.primitive_cube_add(location=(3.0, 0.0, 0.0))
    hidden = bpy.context.active_object
    hidden.name = "HiddenMember"

    linked_path = OUTPUT / "edit_mode.fbx"
    io.export_new_model([edited, hidden], str(linked_path))
    edited.linker.sync_direction = "EXPORT"

    bpy.ops.object.select_all(action="DESELECT")
    edited.select_set(True)
    bpy.context.view_layer.objects.active = edited
    hidden.hide_select = True
    hidden.hide_viewport = True
    hidden.hide_set(True, view_layer=bpy.context.view_layer)

    bpy.ops.object.mode_set(mode="EDIT")
    mesh = bmesh.from_edit_mesh(edited.data)
    mesh.verts.ensure_lookup_table()
    mesh.verts[0].co.x += 0.25
    bmesh.update_edit_mesh(edited.data)
    bpy.context.view_layer.update()

    model_id = edited.linker.model_id
    sync.DIRTY_MODELS[model_id] = 1.0
    signature_before = edited.linker.last_sync_signature
    bpy.context.scene.linker_auto_sync = True

    # Repeated timer passes keep one stable dirty state and never leave Edit Mode.
    for _index in range(3):
        sync.timer_callback()
        assert sync.is_dirty(model_id)
        assert edited.linker.last_sync_signature == signature_before
        assert edited.mode == "EDIT"
        assert hidden.hide_select and hidden.hide_viewport
        assert hidden.hide_get(view_layer=bpy.context.view_layer)

    bpy.ops.object.mode_set(mode="OBJECT")
    sync.timer_callback()
    assert not sync.is_dirty(model_id)
    assert edited.linker.last_sync_signature != signature_before
    assert hidden.hide_select and hidden.hide_viewport
    assert hidden.hide_get(view_layer=bpy.context.view_layer)

    Linker.unregister()
    print("LINKER_EDIT_MODE_SYNC_TEST_OK")
finally:
    shutil.rmtree(OUTPUT, ignore_errors=True)
