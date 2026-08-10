"""Automatic and one-shot synchronization policy."""

from __future__ import annotations

import time
from contextlib import contextmanager
from pathlib import Path

import bpy
from bpy.app.handlers import persistent
from bpy.props import PointerProperty

from . import io
from .models import all_model_owners, migrate_legacy_data, model_owner
from .paths import addon_preferences, resolved_path, validation_error
from .properties import LINKER_PG_TrackingSettings

DIRTY_MODELS: dict[str, float] = {}
IGNORE_UNTIL: dict[str, float] = {}
_SUSPEND_DEPTH = 0
_MIGRATION_PENDING = True


@contextmanager
def suspend_tracking():
    global _SUSPEND_DEPTH
    _SUSPEND_DEPTH += 1
    try:
        yield
    finally:
        _SUSPEND_DEPTH -= 1


def mark_clean(model_id: str) -> None:
    DIRTY_MODELS.pop(model_id, None)
    IGNORE_UNTIL[model_id] = time.time() + 0.75


def is_dirty(model_id: str) -> bool:
    return model_id in DIRTY_MODELS


@persistent
def depsgraph_update_handler(_scene, depsgraph):
    if _SUSPEND_DEPTH:
        return
    now = time.time()
    for update in depsgraph.updates:
        datablock = getattr(update.id, "original", update.id)
        candidates = []
        if isinstance(datablock, bpy.types.Object):
            candidates = [datablock]
        else:
            candidates = [obj for obj in bpy.data.objects if obj.data == datablock]
        for obj in candidates:
            owner = model_owner(obj)
            if not owner or IGNORE_UNTIL.get(owner.linker.model_id, 0.0) > now:
                continue
            DIRTY_MODELS[owner.linker.model_id] = now


def _external_state(owner):
    error = validation_error(owner.linker.link_path)
    if error:
        return error, 0.0, False
    path = resolved_path(owner.linker.link_path)
    stat = Path(path).stat()
    changed = str(stat.st_mtime_ns) != owner.linker.last_sync_signature
    return None, stat.st_mtime, changed


def sync_model(owner, force: bool = False) -> str:
    """Apply direction policy and return IMPORT, EXPORT, CLEAN, or an error."""
    error, file_mtime, external_changed = _external_state(owner)
    if error:
        raise ValueError(error)
    model_id = owner.linker.model_id
    local_changed = is_dirty(model_id)
    direction = owner.linker.sync_direction

    action = None
    if direction == "IMPORT":
        action = "IMPORT" if force or external_changed else None
    elif direction == "EXPORT":
        action = "EXPORT" if force or local_changed else None
    elif external_changed and local_changed:
        action = "IMPORT" if file_mtime >= DIRTY_MODELS[model_id] else "EXPORT"
    elif external_changed:
        action = "IMPORT"
    elif local_changed:
        action = "EXPORT"

    if action == "IMPORT":
        with suspend_tracking():
            io.import_model(owner)
        mark_clean(model_id)
        return action
    if action == "EXPORT":
        with suspend_tracking():
            io.export_model(owner)
        mark_clean(model_id)
        return action
    return "CLEAN"


def sync_all(scene, force: bool = False):
    results = []
    for owner in all_model_owners(scene):
        try:
            results.append((owner.linker.model_name, sync_model(owner, force=force), None))
        except Exception as exc:  # keep other independent models synchronizing
            results.append((owner.linker.model_name, "ERROR", str(exc)))
    return results


def _poll_interval() -> float:
    preferences = addon_preferences()
    return preferences.poll_interval if preferences else 1.0


def timer_callback():
    global _MIGRATION_PENDING
    try:
        if _MIGRATION_PENDING:
            migrate_legacy_data()
            _MIGRATION_PENDING = False
        scene = getattr(bpy.context, "scene", None)
        if scene and scene.linker_auto_sync:
            sync_all(scene)
    except Exception as exc:
        print(f"Linker automatic sync error: {exc}")
    return _poll_interval()


def ensure_timer():
    if not bpy.app.timers.is_registered(timer_callback):
        bpy.app.timers.register(timer_callback, first_interval=_poll_interval(), persistent=True)


@persistent
def load_post_handler(_filepath):
    global _MIGRATION_PENDING
    DIRTY_MODELS.clear()
    IGNORE_UNTIL.clear()
    migrated = migrate_legacy_data()
    _MIGRATION_PENDING = False
    if migrated:
        print(f"Linker migrated {migrated} object(s) from 1.x tracking data")
    ensure_timer()


def register():
    global _MIGRATION_PENDING
    # Remove the 1.x handler if this is a live upgrade in the same Blender session.
    for handler in list(bpy.app.handlers.load_post):
        if handler.__name__ == "load_handler" and handler.__module__.endswith(".utils"):
            bpy.app.handlers.load_post.remove(handler)
    if hasattr(bpy.types.Object, "tracking"):
        del bpy.types.Object.tracking
    bpy.types.Object.tracking = PointerProperty(type=LINKER_PG_TrackingSettings)
    if load_post_handler not in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.append(load_post_handler)
    if depsgraph_update_handler not in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.append(depsgraph_update_handler)
    _MIGRATION_PENDING = True
    ensure_timer()


def unregister():
    if bpy.app.timers.is_registered(timer_callback):
        bpy.app.timers.unregister(timer_callback)
    if load_post_handler in bpy.app.handlers.load_post:
        bpy.app.handlers.load_post.remove(load_post_handler)
    if depsgraph_update_handler in bpy.app.handlers.depsgraph_update_post:
        bpy.app.handlers.depsgraph_update_post.remove(depsgraph_update_handler)
    if hasattr(bpy.types.Object, "tracking"):
        del bpy.types.Object.tracking
    DIRTY_MODELS.clear()
    IGNORE_UNTIL.clear()
