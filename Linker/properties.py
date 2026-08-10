"""Persistent RNA properties and add-on preferences."""

from __future__ import annotations

import bpy
from bpy.props import BoolProperty, CollectionProperty, EnumProperty, FloatProperty
from bpy.props import IntProperty, PointerProperty, StringProperty


AXES = tuple((axis, axis, axis) for axis in ("X", "Y", "Z", "-X", "-Y", "-Z"))
OBJ_AXES = (
    ("X", "X", "Positive X"), ("Y", "Y", "Positive Y"), ("Z", "Z", "Positive Z"),
    ("NEGATIVE_X", "-X", "Negative X"), ("NEGATIVE_Y", "-Y", "Negative Y"),
    ("NEGATIVE_Z", "-Z", "Negative Z"),
)
PATH_OPTIONS = {'PATH_SUPPORTS_BLEND_RELATIVE'} if bpy.app.version >= (4, 5, 0) else set()
_PROPAGATING = False


def _propagate_model_value(settings, attribute: str) -> None:
    global _PROPAGATING
    if _PROPAGATING or not settings.model_id:
        return
    _PROPAGATING = True
    try:
        value = getattr(settings, attribute)
        for obj in bpy.data.objects:
            peer = getattr(obj, "linker", None)
            if peer and peer.model_id == settings.model_id and peer != settings:
                setattr(peer, attribute, value)
    finally:
        _PROPAGATING = False


def _path_updated(self, _context):
    _propagate_model_value(self, "link_path")


def _direction_updated(self, _context):
    _propagate_model_value(self, "sync_direction")


class LINKER_PG_EnvironmentVariable(bpy.types.PropertyGroup):
    name: StringProperty(name="Name", description="Variable referenced as %NAME% in a link path")
    value: StringProperty(name="Value", subtype="DIR_PATH")


class LINKER_PG_FBXSettings(bpy.types.PropertyGroup):
    global_scale: FloatProperty(name="Scale", default=1.0, min=0.0001)
    use_custom_normals: BoolProperty(name="Custom Normals", default=True)
    import_subdivision: BoolProperty(name="Subdivision Data", default=False)
    use_custom_props: BoolProperty(name="Custom Properties", default=True)
    enums_as_strings: BoolProperty(name="Enums as Strings", default=True)
    import_colors: EnumProperty(
        name="Vertex Colors",
        items=(("NONE", "None", "Do not import colors"),
               ("SRGB", "sRGB", "Import colors as sRGB"),
               ("LINEAR", "Linear", "Import colors as linear")),
        default="SRGB",
    )
    use_animation: BoolProperty(name="Animation", default=True)
    animation_offset: FloatProperty(name="Animation Offset", default=1.0)
    ignore_leaf_bones: BoolProperty(name="Ignore Leaf Bones", default=False)
    validate_meshes: BoolProperty(name="Validate Meshes", default=True)
    material_collision: EnumProperty(
        name="Material Name Collision",
        items=(("MAKE_UNIQUE", "Make Unique", "Create unique materials"),
               ("REFERENCE_EXISTING", "Reference Existing", "Reuse matching materials")),
        default="MAKE_UNIQUE",
    )
    axis_forward: EnumProperty(name="Forward", items=AXES, default="-Z")
    axis_up: EnumProperty(name="Up", items=AXES, default="Y")
    export_subdivision: BoolProperty(name="Export Subdivision", default=False)
    apply_unit_scale: BoolProperty(name="Apply Unit Scale", default=True)
    bake_space_transform: BoolProperty(name="Bake Space Transform", default=False)
    use_mesh_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    only_deform_bones: BoolProperty(name="Only Deform Bones", default=False)
    add_leaf_bones: BoolProperty(name="Add Leaf Bones", default=True)
    bake_animation: BoolProperty(name="Bake Animation", default=True)
    reimport_materials: BoolProperty(name="Replace Materials", default=True)
    reimport_uvs: BoolProperty(name="Replace UVs", default=True)
    reimport_transforms: BoolProperty(name="Replace Transforms", default=True)


class LINKER_PG_OBJSettings(bpy.types.PropertyGroup):
    global_scale: FloatProperty(name="Scale", default=1.0, min=0.0001)
    clamp_size: FloatProperty(name="Clamp Size", default=0.0, min=0.0)
    forward_axis: EnumProperty(name="Forward", items=OBJ_AXES, default="NEGATIVE_Z")
    up_axis: EnumProperty(name="Up", items=OBJ_AXES, default="Y")
    split_objects: BoolProperty(name="Split by Object", default=True)
    split_groups: BoolProperty(name="Split by Group", default=False)
    import_vertex_groups: BoolProperty(name="Vertex Groups", default=False)
    validate_meshes: BoolProperty(name="Validate Meshes", default=True)
    export_materials: BoolProperty(name="Export Materials", default=True)
    export_smooth_groups: BoolProperty(name="Smooth Groups", default=True)
    apply_modifiers: BoolProperty(name="Apply Modifiers", default=True)
    reimport_materials: BoolProperty(name="Replace Materials", default=True)
    reimport_uvs: BoolProperty(name="Replace UVs", default=True)
    reimport_transforms: BoolProperty(name="Replace Transforms", default=True)


class LINKER_PG_TrackingSettings(bpy.types.PropertyGroup):
    tracked: BoolProperty(name="Linked", default=False)
    model_id: StringProperty(name="Model ID", default="")
    model_name: StringProperty(name="Model Name", default="Linked Model")
    link_path: StringProperty(
        name="File", description="Absolute, // relative, or %VARIABLE%-based FBX/OBJ path",
        subtype="FILE_PATH", options=PATH_OPTIONS, update=_path_updated,
    )
    last_sync_signature: StringProperty(name="Last File Signature", default="", options={"HIDDEN"})
    object_index: IntProperty(name="Object Index", default=0, min=0)
    sync_direction: EnumProperty(
        name="Direction",
        items=(("BOTH", "Two-way", "Import file changes and export Blender changes", "ARROW_LEFTRIGHT", 0),
               ("IMPORT", "Import only", "Only update Blender from disk", "IMPORT", 1),
               ("EXPORT", "Export only", "Only update the file from Blender", "EXPORT", 2)),
        default="BOTH", update=_direction_updated,
    )
    fbx: PointerProperty(type=LINKER_PG_FBXSettings)
    obj: PointerProperty(type=LINKER_PG_OBJSettings)

    # Registered legacy names allow 1.x data to load before migration.
    linkid: IntProperty(default=-1, options={"HIDDEN"})
    linktime: StringProperty(default="", options={"HIDDEN"})
    linkpath: StringProperty(default="", options={"HIDDEN"})


class LINKER_AddonPreferences(bpy.types.AddonPreferences):
    bl_idname = __package__
    variables: CollectionProperty(type=LINKER_PG_EnvironmentVariable)
    variable_index: IntProperty(default=0)
    poll_interval: FloatProperty(
        name="Sync Interval", description="Seconds between automatic sync checks",
        default=1.0, min=0.25, max=60.0,
    )
    show_advanced: BoolProperty(name="Show Advanced Settings", default=False)

    def draw(self, context):
        from .models import active_model_owner
        from .paths import resolved_path

        layout = self.layout
        layout.prop(self, "poll_interval")
        variables = layout.box()
        variables.label(text="Local Path Variables")
        variables.label(text="Use as %NAME% inside a linked path.", icon="INFO")
        for index, item in enumerate(self.variables):
            row = variables.row(align=True)
            row.prop(item, "name", text="")
            row.prop(item, "value", text="")
            remove = row.operator("linker.variable_remove", text="", icon="X")
            remove.index = index
        variables.operator("linker.variable_add", icon="ADD")
        owner = active_model_owner(context)
        if owner:
            box = layout.box()
            box.label(text="Active Model Link")
            box.prop(owner.linker, "link_path")
            box.label(text=resolved_path(owner.linker.link_path), icon="FILE_FOLDER")


CLASSES = (
    LINKER_PG_EnvironmentVariable, LINKER_PG_FBXSettings, LINKER_PG_OBJSettings,
    LINKER_PG_TrackingSettings, LINKER_AddonPreferences,
)


def register():
    for cls in CLASSES:
        bpy.utils.register_class(cls)
    bpy.types.Object.linker = PointerProperty(type=LINKER_PG_TrackingSettings)
    bpy.types.Scene.linker_auto_sync = BoolProperty(
        name="Automatic Sync", description="Continuously synchronize linked models", default=False,
    )
    bpy.types.WindowManager.linker_status = StringProperty(options={"SKIP_SAVE"})


def unregister():
    del bpy.types.WindowManager.linker_status
    del bpy.types.Scene.linker_auto_sync
    del bpy.types.Object.linker
    for cls in reversed(CLASSES):
        bpy.utils.unregister_class(cls)

