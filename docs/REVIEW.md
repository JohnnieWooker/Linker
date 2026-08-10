# Technical Review

## High-impact findings in Linker 1.1.7

1. **Registration mutated document data.** `registerprops()` ran at import time and
   cleared `scene.tracked_objects`. Settings were duplicated between that collection,
   object properties, and ordinary Python settings classes. The new model derives
   membership from persistent object RNA data and never clears document state.
2. **The add-on replaced `object.delete`.** This affected deletion throughout Blender
   and bypassed normal operator behavior. Linker 2.0 uses no built-in operator
   overrides; unlinking is explicit and model replacement owns its cleanup.
3. **The heartbeat was fragile.** A modal operator was started twice by a load handler,
   mixed UI context with file polling, and processed one changed model per tick. A
   persistent application timer and dependency-graph handler now separate change
   detection from user operators.
4. **Reload was destructive before import success.** The old objects were deleted
   before the importer ran. Linker 2.0 imports first and removes the old group only
   after Blender created replacement objects.
5. **Settings were not reliably persistent.** Plain `OBJImportSettings` and
   `FBXImportSettings` instances were class attributes, while dozens of fields were
   manually copied to RNA properties. Settings are now nested persistent property
   groups. A save/reopen background test verifies identity, path, direction, and
   settings ownership.
6. **Timestamps were unsuitable for robust comparison.** Text/float conversions and
   Blender float precision could miss changes. The persisted value is now the file's
   integer nanosecond timestamp stored as a string.
7. **Errors were broadly swallowed.** Large `try/except: pass` regions could silently
   unlink or delete data. User operations now report failures; Sync All isolates an
   error to one model and continues with the rest.
8. **The code contained two monoliths and an embedded FBX parser.** The active package
   is now split by responsibility, and material/UV preservation uses Blender data
   rather than parsing FBX binary internals.

## Blender 5.1 API compatibility

Runtime introspection against Blender 5.1.1 showed:

- FBX import is `bpy.ops.wm.fbx_import`. Legacy options such as `axis_forward`,
  `axis_up`, image search, decal offset, pre/post rotation, force-connected children,
  and automatic bone orientation are not parameters of the native importer.
- FBX export remains `bpy.ops.export_scene.fbx`; import and export settings therefore
  cannot be represented as one shared option set.
- OBJ import/export are `bpy.ops.wm.obj_import` and `bpy.ops.wm.obj_export`, with
  renamed selection and axis parameters.

`io.py` feature-detects operators through RNA (dynamic `hasattr(bpy.ops, ...)` is not
reliable) and filters optional keyword arguments against the installed operator.
Blender 4.2 uses the legacy FBX fallback; Blender 5.1 uses the native importer.

## Remaining limitations

- Two-way synchronization is timestamp-based; it does not merge concurrent model
  edits. The newer side wins when both changed.
- UV preservation requires equal mesh loop counts. Model members are paired by
  stable import order, so major hierarchy/topology changes should use replacement.
- External constraints or drivers pointing at objects replaced by reload may need
  repair. A future version should preserve identities through a more sophisticated
  object-matching layer.
- Automatic dirty tracking depends on dependency-graph notifications. Manual Save
  and Reload are the deterministic overrides.
- Blender's operators run on the main thread. Sync All is sequential by design to
  keep selection, undo, and scene mutation safe.
