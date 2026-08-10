"""Linker add-on entry point."""

bl_info = {
    "name": "Linker",
    "author": "Lukasz Hoffmann and contributors",
    "version": (2, 0, 0),
    "blender": (4, 2, 0),
    "location": "3D Viewport > Sidebar > Linker",
    "description": "Synchronize Blender model groups with FBX and OBJ files",
    "doc_url": "https://github.com/JohnnieWooker/Linker",
    "category": "Import-Export",
}

from . import operators, properties, sync, ui  # noqa: E402


def register():
    properties.register()
    operators.register()
    ui.register()
    sync.register()


def unregister():
    sync.unregister()
    ui.unregister()
    operators.unregister()
    properties.unregister()


if __name__ == "__main__":
    register()
