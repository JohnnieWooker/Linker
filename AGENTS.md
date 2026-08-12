# AGENTS.md

## Scope

These instructions apply to the entire repository. Linker is a Blender Python
extension. Runtime code lives in `Linker/`; documentation and headless tests live
at repository root.

## Design rules

- Keep `Linker/__init__.py` registration-only.
- Put all Blender import/export API compatibility in `Linker/io.py`.
- Persist document data with RNA properties; do not use module globals as the
  source of truth. Runtime dirty/cooldown state is the exception.
- Treat every model operation as a group operation using `model_id`.
- Deduplicate selected-object batch actions by `model_id`; keep active-object context for UI settings.
- Batch-edit sync direction only when selected models share one current direction.
- Disable batch format fields and preset selectors when their selected model values differ.
- Defer automatic synchronization while any model member is outside Object Mode;
  retain its dirty state until editing finishes. Explicit actions remain overrides.
- Export must include members hidden at object, collection, or view-layer level and restore selection, active object, mode, and hide flags.
- Preserve raw paths. Resolve `%VARIABLE%` and `//` only at the I/O boundary.
- Do not override built-in Blender operators.
- Never delete the existing model until a replacement import succeeds.
- New direction-aware automation must respect Import only and Export only. Explicit
  Save and Reload are deliberate user overrides.

## Compatibility

The minimum supported version is Blender 4.2; Blender 5.1 is the primary target.
Feature-detect operators and filter optional arguments using RNA. Do not assume the
legacy `import_scene.fbx`, `import_scene.obj`, or `export_scene.obj` operators exist.

When changing I/O, inspect the target Blender runtime with `get_rna_type()` and add
or update a background smoke test. Preserve the 1.x fields registered in
`LINKER_PG_TrackingSettings` until a separately planned migration removal.

## Verification

From the repository root on Windows:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python tests/smoke_blender.py
```

Also run `python -m compileall Linker tests` with a Python version matching Blender.
Tests must create output under a temporary directory and clean it up.

## Documentation

Update `docs/USER_GUIDE.md` for visible behavior, `docs/ARCHITECTURE.md` for design
or persistence changes, and `DEVELOPMENT.md` for deferred work. Keep Blender API
claims version-specific.
