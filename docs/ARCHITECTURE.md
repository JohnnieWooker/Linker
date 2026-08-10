# Architecture

The add-on is split by responsibility:

- `properties.py` — persisted RNA data and machine-local add-on preferences.
- `paths.py` — `%VARIABLE%`, environment, and Blender `//` path resolution.
- `models.py` — model grouping, settings copying, and 1.x migration.
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

## I/O compatibility boundary

`io.py` feature-detects operators and filters keyword arguments through operator
RNA. Blender 5.1 takes the native FBX import path (`wm.fbx_import`). Older supported
versions can fall back to `import_scene.fbx` if the native operator is unavailable.
FBX export remains `export_scene.fbx`. Modern OBJ uses `wm.obj_import` and
`wm.obj_export` with a legacy fallback.

## Synchronization policy

The dependency graph marks models dirty. A persistent Blender timer compares that
state with the linked file's modification time. Operations are serialized on the
main thread. Import is transactional in the practical Blender sense: new objects
must import successfully before old objects are removed.

There is no semantic model merge. When both sides changed, the later timestamp is
authoritative. A future file-watcher service and explicit conflict UI are tracked
in the development plan.
