# Linker

Linker keeps a group of Blender objects connected to an FBX or OBJ file. It can
pull changes made by another DCC, push Blender changes to disk, or synchronize in
both directions.

This repository contains Linker 2.0, refactored for Blender 4.2+ and tested with
Blender 5.1. The add-on uses Blender 5.1's native `wm.fbx_import` operator and the
currently supported Python FBX exporter, `export_scene.fbx`.

## Install

1. Zip the contents of the `Linker` directory so `__init__.py` and
   `blender_manifest.toml` are at the archive root.
2. In Blender, open **Edit > Preferences > Extensions**.
3. Use the menu's **Install from Disk** action and select the zip.
4. Open the 3D Viewport sidebar (`N`) and select the **Linker** tab.

For development, add this repository to Blender's script search path or install
the `Linker` directory as a legacy add-on.

See [User Guide](docs/USER_GUIDE.md), [Architecture](docs/ARCHITECTURE.md), and
[Development Plan](DEVELOPMENT.md).
