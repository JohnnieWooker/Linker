# Linker User Guide

## Link a model

- **Link Existing** imports an FBX or OBJ file and groups every object created by
  that import as one linked model.
- **Export Selection** exports the selected objects and links them as one model.

Select any object in the group to manage the model. Linker stores the model ID,
path, direction, timestamps, and import/export settings in the `.blend` file.

## Synchronization direction

- **Two-way** imports when the disk file changed and exports when Blender data
  changed. If both changed between checks, the newer timestamp wins.
- **Import only** never writes during automatic or one-shot synchronization.
- **Export only** never imports during automatic or one-shot synchronization.

**Sync** applies this policy to the selected model. If no linked model is active,
the panel presents **Sync All**, which applies it once to every valid linked model
in the current scene. **Auto Sync** checks continuously at the interval configured
in the add-on preferences.

**Save** is an explicit override: it exports the selected model immediately even
when its direction is Import only. **Reload** likewise explicitly imports now.

## Portable paths

Paths may be:

- absolute: `D:\Project\Models\chair.fbx`
- relative to the saved `.blend`: `//Models/chair.fbx`
- based on a local variable: `%PROJECT_ROOT%/Models/chair.fbx`

Use **Make Relative** after saving the `.blend` file. Raw and resolved paths are
visible in the sidebar. All links in the current scene are summarized under
**Linked Models**.

Define `%NAME%` values in **Preferences > Add-ons/Extensions > Linker > Local Path
Variables**. Values live in each user's Blender preferences, while `%NAME%` remains
in the source-controlled `.blend`. Operating-system environment variables are
also accepted; a Linker preference with the same name takes precedence.

## Reload preservation

The format settings can preserve materials, UVs, or transforms during reload.
Objects are paired by stable import order. UVs can only be restored when the old
and new mesh loop counts match. Keep replacement enabled for topology-changing
files unless you control that mapping.

## Migration from Linker 1.x

On load, Linker 2.0 reads the old `Object.tracking` values and creates stable model
IDs grouped by the old link path. It does not clear the old scene tracking data.
Save a backup copy before first migration, then save the `.blend` after confirming
the groups and paths.

## Troubleshooting

- **Undefined `%VARIABLE%`**: define it in Linker preferences or in the OS.
- **Relative path cannot be created**: save the `.blend` first.
- **Two-way model is not exported**: use **Save** immediately; automatic dirty
  tracking depends on Blender dependency-graph notifications.
- **Unexpected conflict result**: use explicit **Save** or **Reload**. Linker uses
  timestamps, not a merge of two model files.
