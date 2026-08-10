"""Batch operations, hidden export, and viewport-context regression test."""

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
from Linker.operators import LINKER_OT_SetSyncDirection  # noqa: E402
from Linker.models import model_members, selected_model_owners  # noqa: E402


def new_cube(name):
    bpy.ops.mesh.primitive_cube_add()
    obj = bpy.context.active_object
    obj.name = name
    return obj


def select_only(objects, active):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = active


def selected_names():
    return {obj.name for obj in bpy.context.view_layer.objects if obj.select_get()}


OUTPUT = Path(tempfile.mkdtemp(prefix="linker-batch-"))
try:
    Linker.register()

    model_a = new_cube("ModelA")
    model_a_hidden = new_cube("ModelA_Hidden")
    model_a_local_hidden = new_cube("ModelA_LocalHidden")
    path_a = OUTPUT / "model_a.fbx"
    io.export_new_model([model_a, model_a_hidden, model_a_local_hidden], str(path_a))

    model_b = new_cube("ModelB")
    path_b = OUTPUT / "model_b.obj"
    io.export_new_model([model_b], str(path_b))

    sentinel = new_cube("SelectionSentinel")
    select_only([model_a, model_b, sentinel], model_a)
    expected_selection = selected_names()
    expected_active = model_a.name

    model_a_local_hidden.hide_select = True
    model_a_local_hidden.hide_set(True, view_layer=bpy.context.view_layer)
    hidden_collection = bpy.data.collections.new("HiddenModelCollection")
    bpy.context.scene.collection.children.link(hidden_collection)
    for collection in list(model_a_hidden.users_collection):
        collection.objects.unlink(model_a_hidden)
    hidden_collection.objects.link(model_a_hidden)
    hidden_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]

    model_a_hidden.hide_select = True
    model_a_hidden.hide_set(True, view_layer=bpy.context.view_layer)
    model_a_hidden.hide_viewport = True
    hidden_collection.hide_viewport = True
    hidden_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]
    hidden_layer.exclude = True
    hidden_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]
    assert hidden_layer.exclude, "Fixture failed to exclude hidden collection"

    io.export_model(model_a)
    direct_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]
    assert hidden_collection.hide_viewport and direct_layer.exclude, "Direct export changed collection visibility"
    assert len(selected_model_owners(bpy.context)) == 2

    # Sync direction changes all selected models, but mixed values disable it.
    assert bpy.ops.linker.set_sync_direction(direction="EXPORT") == {"FINISHED"}
    assert all(member.linker.sync_direction == "EXPORT" for member in model_members(model_a))
    assert model_b.linker.sync_direction == "EXPORT"
    model_b.linker.sync_direction = "IMPORT"
    assert not LINKER_OT_SetSyncDirection.poll(bpy.context)
    model_b.linker.sync_direction = "EXPORT"
    assert LINKER_OT_SetSyncDirection.poll(bpy.context)

    assert bpy.ops.linker.save_model() == {"FINISHED"}
    assert selected_names() == expected_selection
    assert bpy.context.active_object.name == expected_active
    assert model_a_hidden.hide_select and model_a_hidden.hide_viewport
    assert model_a_local_hidden.hide_select
    assert model_a_local_hidden.hide_get(view_layer=bpy.context.view_layer)
    restored_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]
    assert hidden_collection.hide_viewport and restored_layer.exclude

    # A reload proves that the hidden member was present in the exported FBX.
    io.import_model(model_a)
    model_a = bpy.data.objects["ModelA"]
    model_a_hidden = bpy.data.objects["ModelA_Hidden"]
    model_a_local_hidden = bpy.data.objects["ModelA_LocalHidden"]
    assert len(model_members(model_a)) == 3
    assert model_a_hidden.hide_select and model_a_hidden.hide_viewport
    assert model_a_local_hidden.hide_select
    assert model_a_local_hidden.hide_get(view_layer=bpy.context.view_layer)
    restored_layer = bpy.context.view_layer.layer_collection.children[hidden_collection.name]
    assert hidden_collection.hide_viewport and restored_layer.exclude
    assert selected_names() == expected_selection
    assert bpy.context.active_object.name == expected_active

    # Reload every distinct linked model represented by the selection.
    model_b = bpy.data.objects["ModelB"]
    sentinel = bpy.data.objects["SelectionSentinel"]
    select_only([model_a, model_b, sentinel], model_a)
    expected_selection = selected_names()
    assert bpy.ops.linker.reload_model() == {"FINISHED"}
    assert selected_names() == expected_selection
    assert bpy.context.active_object.name == expected_active

    # Make Relative is also a selected-model batch action.
    blend_path = OUTPUT / "batch.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    model_a = bpy.data.objects["ModelA"]
    model_b = bpy.data.objects["ModelB"]
    sentinel = bpy.data.objects["SelectionSentinel"]
    select_only([model_a, model_b, sentinel], model_a)
    assert bpy.ops.linker.make_relative() == {"FINISHED"}
    assert model_a.linker.link_path.startswith("//")
    assert model_b.linker.link_path.startswith("//")

    # Sync All may export both models but must not alter viewport context.
    model_a.linker.sync_direction = "EXPORT"
    model_b.linker.sync_direction = "EXPORT"
    expected_selection = selected_names()
    expected_active = bpy.context.active_object.name
    assert bpy.ops.linker.sync_all() == {"FINISHED"}
    assert selected_names() == expected_selection
    assert bpy.context.active_object.name == expected_active

    Linker.unregister()
    print("LINKER_BATCH_TEST_OK")
finally:
    shutil.rmtree(OUTPUT, ignore_errors=True)
