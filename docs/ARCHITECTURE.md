# Architecture

The add-on is split by responsibility:

- `properties.py` — persisted RNA data and machine-local add-on preferences.
- `paths.py` — `%VARIABLE%`, environment, and Blender `//` path resolution.
- `models.py` — model grouping, settings copying, and 1.x migration.
- `format_settings.py` — format metadata, mixed-value checks, and batch propagation.
- `presets.py` — project-preset serialization, menus, and operators.
- `io.py` — Blender-version-sensitive FBX/OBJ calls and transactional reloads.
- `sync.py` — dependency-graph dirty tracking, direction policy, and timer.
- `operators.py` — undoable user commands and reports.
- `ui.py` — sidebar panels only.
- `__init__.py` — deterministic registration order.

## Persistence

Each linked object owns a `LinkerTrackingSettings` property group. Objects in the
same logical model share a UUID. The member with the lowest stored object index is
the model owner presented by the UI. Link discovery derives from persisted object
data; there is no runtime-only scene list to rebuild or clear.

Machine-local path variables use `AddonPreferences`, so local roots do not pollute
the `.blend`. Paths themselves remain on objects and therefore travel with the
document.

Import and export preset definitions are separate scene-level RNA collections and
therefore persist in the `.blend`. Model objects store their import and export preset
IDs independently. Preset payloads are JSON inside RNA string properties, restricted
to the declared field list for their file format and side.

## I/O compatibility boundary

`io.py` feature-detects operators and filters keyword arguments through operator
RNA. Blender 5.1 takes the native FBX import path (`wm.fbx_import`). Older supported
versions can fall back to `import_scene.fbx` if the native operator is unavailable.
FBX export remains `export_scene.fbx`. Modern OBJ uses `wm.obj_import` and
`wm.obj_export` with a legacy fallback.

## Viewport context and batch operations

UI configuration resolves from the active model owner. Action operators instead derive
a deduplicated model-owner list from selected objects. The I/O context manager temporarily
clears object-, collection-, and view-layer-level viewport hiding plus selection
locks for exported members, then restores hide flags, selection, active object, and
mode. Reload restoration is name-based because successful imports replace the original
Blender object instances.

Sync-direction editing uses a batch operator rather than binding the UI directly to the
active object's property. The operator is available only when selected model owners have
one common direction, preventing an accidental overwrite of deliberately mixed policies.

Format property update callbacks propagate an enabled field from the active model to
all selected owners of the same format. The UI compares every field before enabling
its control. Preset load/save operators repeat the compatibility checks so mixed-value
or mixed-selection safeguards cannot be bypassed through direct operator invocation.

## Synchronization policy

The dependency graph marks models dirty. A persistent Blender timer compares that
state with the linked file's modification time. Operations are serialized on the
main thread. Import is transactional in the practical Blender sense: new objects
must import successfully before old objects are removed.

The automatic timer returns `DEFERRED` for a linked model while any member is outside
Object Mode. Its dirty state is retained and processed after the model returns to
Object Mode. Explicit operators do not use this guard because Save and Reload are
intentional overrides. This prevents automatic I/O context changes from fighting an
active Edit Mode session or generating self-induced dirty-state oscillation.

There is no semantic model merge. When both sides changed, the later timestamp is
authoritative. A future file-watcher service and explicit conflict UI are tracked
in the development plan.
