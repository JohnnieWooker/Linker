# Linker User Guide

Linker keeps groups of Blender objects synchronized with external FBX or OBJ files.
Use it to pull changes from another DCC, publish Blender changes to disk, or maintain
a two-way link while you work.

This guide covers Blender 4.2 and later. Blender 5.1 is the primary supported version
and uses Blender's native FBX importer.

## Install Linker

1. Create a ZIP whose root contains the contents of the `Linker` directory,
   including `__init__.py` and `blender_manifest.toml`.
2. In Blender, open **Edit > Preferences > Extensions**.
3. Open the extension menu and choose **Install from Disk**.
4. Select the ZIP and enable Linker if Blender does not enable it automatically.
5. In a 3D Viewport, press `N` and select the **Linker** tab.

> **Screenshot placeholder — Installing Linker**
>
> Capture Blender's **Preferences > Extensions** page after Linker is installed.
> Show the enabled Linker entry, its version, and the route to **Install from Disk**.
> Crop out unrelated extensions and personal paths.

## Interface overview

The main panel shows synchronization controls for the active linked model. The
**Import / Export Settings** subpanel contains format-specific settings and presets.
The **Linked Models** subpanel summarizes every linked model in the current scene.
When no linked model is active, the panel offers **Sync All**, **Link Existing**, and
**Export Selection**.

> **Screenshot placeholder — Linker sidebar overview**
>
> Capture the full Linker tab with one FBX model active. Expand **Import / Export
> Settings** and **Linked Models**. Annotate the direction controls, batch actions,
> linked path, validation status, import/export presets, and model summary.

## Core concepts

### Linked model

A linked model is one or more Blender objects that share a stable model ID and one
FBX or OBJ path. Selecting any member makes the model available in the Linker panel.
Linker persists its ID, raw path, direction, timestamps, format settings, and preset
selections in the `.blend` file.

### Active model and selected models

The active linked object supplies the path preview and model-specific context. Batch
actions derive a separate, deduplicated list of linked models from the entire Blender
selection. Selecting several members of the same model still processes it only once.

### Explicit actions and automatic synchronization

**Save** and **Reload** are deliberate overrides. Save always exports and Reload
always imports, regardless of the automatic direction. **Sync**, **Sync All**, and
**Auto Sync** follow the configured direction policy.

## Create a link

### Link an existing file

1. Click **Link Existing**.
2. Choose an `.fbx` or `.obj` file.
3. Linker imports every object created by that operation as one linked model.
4. Select any imported member to review its path, direction, and format settings.

> **GIF placeholder — Linking an existing FBX**
>
> Record a 10–15 second loop. Start with no linked model active and the Linker tab
> visible. Click **Link Existing**, choose a small FBX, wait for import, then select
> two different imported members to show that both expose the same model settings.
> Do not record personal folder names.

### Export and link a Blender selection

1. Select every object that should belong to the model.
2. Keep the intended primary object active.
3. Click **Export Selection** and choose an FBX or OBJ destination.
4. Linker exports the selection and assigns one model ID to all exported objects.

> **GIF placeholder — Exporting and linking a selection**
>
> Record selecting three related objects, clicking **Export Selection**, choosing
> `Models/example.fbx`, and returning to the viewport. Finish by selecting each
> object once so the shared model name and path are visible.

## Choose a synchronization direction

| Direction | Automatic and one-shot Sync behavior |
| --- | --- |
| **Two-way** | Imports disk changes and exports Blender changes. If both sides changed, the newer timestamp wins. |
| **Import only** | Updates Blender from disk and never exports automatically. |
| **Export only** | Updates the external file from Blender and never imports automatically. |

When selected linked models share a direction, choosing another direction applies it
to all of them. With mixed directions, the buttons are disabled and the panel shows
**Multiple values**. Select one policy group at a time to resolve the difference.

> **Screenshot placeholder — Direction batch guard**
>
> Show two selected linked models with different directions. Frame the disabled
> **Two-way**, **Import only**, and **Export only** buttons with the **Multiple
> values** note. The Outliner should make both selected model groups obvious.

## Synchronize models

- **Sync (N)** applies each selected model's configured direction once.
- **Save (N)** immediately exports every selected linked model, including Import-only
  models.
- **Reload (N)** immediately imports every selected linked file, including Export-only
  models, and replaces its current model members.
- **Sync All** processes every valid linked model in the current scene and respects
  each model's direction. A failure in one model does not stop the rest.
- **Auto Sync** periodically applies the direction policy. Configure its interval in
  Linker's add-on preferences.

`N` is the number of distinct linked models represented by the selection.

> **GIF placeholder — Sync All without disrupting viewport context**
>
> Record three linked models with mixed Import-only and Export-only directions.
> Establish a recognizable selection and active object, invoke **Sync All**, and
> finish by showing that the original selection and active object were restored.

Automatic synchronization is timestamp- and dependency-graph-based; it is not a
semantic merge. Use explicit Save or Reload when the desired authority must be clear.
## Batch behavior and viewport state

These operations act once on every distinct linked model represented by the selection:

- Sync, Save, Reload, Make Relative, and Unlink
- direction changes, when current directions match
- format-setting changes, when current values and formats match
- preset loading, when current preset selections match

Linker restores the original selection, active object, and mode after I/O. Export
temporarily exposes linked members hidden at the object, collection, or view-layer
level and clears selection locks. It restores those states afterward, so hidden
members remain part of the external model without interrupting the viewport workflow.

> **GIF placeholder — Exporting hidden model members**
>
> Record a linked model with one visible member, one hidden with the viewport eye,
> and one inside an excluded collection. Click **Save**, then verify in a temporary
> scene that all three were exported. Return to the original scene and show that its
> hide, exclusion, selection, and active-object states did not change.

## Configure import and export settings

Expand **Import / Export Settings**. Linker shows separate Import and Export sections
for the active model's format.

A setting is editable across multiple selected models only when:

1. every selected linked model uses the same file format; and
2. every selected linked model has the same current value for that setting.

A mixed setting is disabled and its section shows **Multiple values**. Matching
settings remain available for batch editing. If the selection mixes FBX and OBJ, the
whole format editor is disabled until the selection contains one format.

> **Screenshot placeholder — Mixed format-setting values**
>
> Capture two selected FBX models whose Scale values differ while other import values
> match. Show the disabled Scale field, one still-enabled matching field, and the
> **Multiple values** note in the FBX Import section.

### FBX settings

FBX Import includes scale, normals, subdivision data, custom properties, vertex
colors, animation, validation, and material-collision settings supported by the
detected importer. FBX Export includes scale, axes, subdivision, unit scaling, space
transform, modifiers, armature/bone options, custom properties, and animation baking.

Blender 5.1 uses `wm.fbx_import`. Blender 4.2 uses the legacy compatible importer
when the native operator is unavailable. Linker forwards only parameters supported
by the installed Blender operator.

### OBJ settings

OBJ Import includes scale, clamp size, axes, object/group splitting, vertex groups,
and mesh validation. OBJ Export includes scale, axes, materials, smooth groups, and
modifier application.

## Save and load presets

Import and Export have independent named preset selectors. Presets are format-specific
and belong to the current Blender scene. Preset definitions and each model's selected
preset IDs are stored in the `.blend` file.

### Save a preset

1. Select linked models with one format and matching values in the relevant section.
2. Click **+** beside the Import or Export preset selector.
3. Enter a descriptive name and confirm.
4. Linker creates the preset and selects it for every selected linked model.

Saving is disabled while the section contains mixed values. Saving with an existing
name replaces that preset. Models outside the selection that referenced the previous
payload are marked **Custom**, preventing a stale preset label.

### Load a preset

1. Select linked models with the same current preset selection.
2. Open the Import or Export preset selector.
3. Choose a compatible preset.
4. Linker applies it to every distinct selected linked model.

When current preset selections differ, the selector is disabled and shows **Multiple
values**. Narrow the selection until it is unambiguous, then load the preset.

### Custom settings and shared values

Changing a parameter manually marks affected preset selections as **Custom**. Import
and Export presets remain independently selected when shared parameters—such as scale
or OBJ axes—still match both preset payloads. Loading an incompatible shared value
marks only the affected opposite selection as Custom.

The **On Reload** material, UV, and transform options belong to Import presets. Use
**-** to remove the selected preset. Removing one marks all referencing models Custom
without changing their current parameter values.

> **GIF placeholder — Saving and applying separate presets**
>
> Record two selected FBX models with matching settings. Save an Import preset named
> `Studio Import`, change a setting so it becomes **Custom**, and reload the preset.
> Then save and select a separate `Game Export` preset. Finish with both names visible.

> **Screenshot placeholder — Mixed preset selections**
>
> Show two selected FBX models where one uses `Studio Import` and the other is
> **Custom**. Capture the disabled Import selector and **Multiple values** note while
> leaving the independent Export selector visible.
## Use portable paths

| Path type | Example | Use case |
| --- | --- | --- |
| Absolute | `D:\Project\Models\chair.fbx` | Local experiments or fixed machine paths |
| Blend-relative | `//Models/chair.fbx` | Files stored beside a source-controlled `.blend` |
| Variable-based | `%PROJECT_ROOT%/Models/chair.fbx` | Different local roots for different users |

The panel displays the raw stored path and resolved disk location. Path editing and
**Open File Location** use the active linked model as context. **Make Relative (N)**
converts paths for all selected linked models and requires the `.blend` to be saved.

> **Screenshot placeholder — Raw and resolved linked paths**
>
> Capture `%PROJECT_ROOT%/Models/character.fbx` as the raw path together with its
> resolved absolute path and green validation status. Include the **Relative (N)**
> and folder buttons.

### Define local path variables

1. Open **Edit > Preferences > Extensions > Linker**.
2. Under **Local Path Variables**, click **Add**.
3. Enter a name without percent signs, such as `PROJECT_ROOT`.
4. Enter the machine-specific directory.
5. Reference it as `%PROJECT_ROOT%` inside linked paths.

Values live in each user's Blender preferences and do not pollute the source-controlled
`.blend`. Operating-system environment variables also work. A Linker preference with
the same name takes precedence over the operating-system value.

> **Screenshot placeholder — Local path variables**
>
> Capture Linker's preferences with two examples, such as `PROJECT_ROOT` and
> `SHARED_ASSETS`. Use generic paths. Show the `%NAME%` hint and sync interval without
> exposing personal directories.

## Preserve data during Reload

The Import section's **On Reload** settings control whether Linker replaces or
preserves materials, UVs, and transforms when it reloads an external file.

Objects are paired by stable import order. UV data can only be restored when old and
new mesh loop counts match. For topology-changing files, keep replacement enabled
unless the pipeline guarantees a compatible mapping.

Reload imports replacement objects before deleting the existing model. If the import
creates no objects or reports an error, Linker keeps the existing model. Constraints,
drivers, or other relationships targeting replaced object instances may still need
repair after a major hierarchy change.

> **GIF placeholder — Reload preservation options**
>
> Record a linked object with an obvious Blender-side material and transform. Disable
> **Replace Materials** and **Replace Transforms**, modify the external file, then
> click **Reload**. Show new geometry arriving while the material and transform remain.

## Review linked models

Expand **Linked Models** to see the name, direction, and raw path of every linked
model in the current scene. Use it to audit links; editing remains driven by the
active linked object in the main panel.

> **Screenshot placeholder — Linked Models summary**
>
> Capture at least one FBX and one OBJ model using different directions and path
> styles. Keep the list short enough that every entry is legible.

## Unlink models

Select one or more linked models and click **Unlink (N)**. This removes Linker
tracking metadata without deleting Blender objects or external files.

## Migrate from Linker 1.x

When a legacy file loads, Linker 2.x reads old `Object.tracking` data, creates stable
model IDs, and groups objects by their old link path. It leaves old scene tracking
data intact.

Before migration:

1. Save a backup of the `.blend`.
2. Open it with the current Linker version.
3. Confirm model membership, paths, directions, and format settings.
4. Save the migrated file only after validation.

## Troubleshooting

### A path contains an undefined variable

Define the variable in Linker's preferences or operating system. Names are
case-insensitive in Linker's local preference list.

### Make Relative is unavailable or fails

Save the `.blend` first. Blender-relative `//` paths require a document location.

### A model did not export automatically

Click **Save** for a deterministic export. Automatic dirty tracking depends on Blender
dependency-graph notifications and may not observe every third-party add-on change.

### Sync chose the unexpected side

Two-way synchronization compares timestamps; it does not merge model data. Use
explicit **Save** when Blender is authoritative or **Reload** when disk is authoritative.

### Settings or presets are disabled

Look for **Multiple values**. Reduce the selection to models with one format and a
common value or preset selection. Resolve each policy group separately, then select
them together again for later batch operations.

### A hidden object is missing after export

Confirm it belongs to the linked model and shares its model ID. Linker includes
viewport-hidden members, hidden collection members, and members in excluded view-layer
collections, but it does not export unrelated objects.

### Reload changed external relationships

Reload replaces imported object instances. Constraints, drivers, or other data that
referenced them may require repair after significant hierarchy changes.

## Related technical documentation

- [Architecture](ARCHITECTURE.md)
- [Blender API compatibility and technical review](REVIEW.md)