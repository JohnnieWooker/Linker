# Development Plan

## Current release: 2.0

- Blender 5.1 native FBX importer integration.
- Persisted model UUID, direction, path, timestamps, and format settings.
- Manual Save/Reload, one-shot Sync/Sync All, and automatic timer sync.
- Blender-relative paths and machine-local `%VARIABLE%` expansion.
- Non-destructive 1.x migration and Blender extension manifest.

## Next milestones

### 2.0 stabilization

- Test migration on representative production `.blend` files from every 1.x
  release.
- Add armature, animation, multi-material, hierarchy, and topology-change fixtures.
- Verify Blender 4.2 LTS behavior and document the exact supported patch versions.
- Add UI tests for extension and legacy add-on installation modes.

### 2.1 reliability

- Add an explicit conflict state instead of resolving simultaneous edits only by
  timestamp.
- Store a lightweight content fingerprint to avoid timestamp edge cases.
- Improve old/new object pairing using hierarchy and source names rather than only
  import order.
- Add per-model sync history and actionable error details.

### 2.2 pipeline integration

- Variable presets that teams can distribute without storing local values.
- Optional collection-based model ownership and relink/move-file tooling.
- Pluggable formats and import/export profiles.
- Automated release packaging and Blender background test matrix.

## Suggested commit boundaries

1. Persistence model and legacy migration.
2. Blender 5.1 I/O compatibility adapter.
3. Direction policy and automatic synchronization.
4. Operators, path variables, and UI.
5. Manifest, tests, and documentation.

Keep functional changes and generated release archives in separate commits. Never
commit user preference values, local absolute paths, `.blend1` backups, or smoke
test output.
