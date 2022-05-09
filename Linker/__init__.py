import bpy
import bpy_extras
import os
import mathutils
from typing import Type
from . import utils

bl_info = {
    "name" : "Linker",
    "author" : "Lukasz Hoffmann",
    "version" : (1, 1, 5),
    "blender" : (3, 1, 0),
    "location" : "View 3D > Object Mode > Tool Shelf",
    "description" :
    "Link FBX files",
    "warning" : "",
    "wiki_url" : "",
    "tracker_url" : "",
    "category" : "Object",
    }
   



class OBJImportSettings():    
    def __init__(self):
        self.imageSearch=True   
        self.smoothGroups=True
        self.lines =True
        self.clampSize=0
        self.forward='-Z'
        self.up='Y'
        self.split={"Split"}
        self.splitByObject=False
        self.splitByGroup=False
        self.polyGroups=False
        self.reimportmaterials=False
        self.reimportuvs= True
        self.reimportposition=False

class FBXImportSettings:  
     def __init__(self):
        self.customNormals=True  
        self.subdData=False
        self.customProps=True    
        self.EnumAsStrings=True  
        self.imageSearch=True  
        self.scale=1
        self.decalOffset=0
        self.applyTransform=False
        self.usePrePostRot=True
        self.forward='-Z'
        self.up='Y'
        self.useAnim=True
        self.animOffset=1        
        self.ignoreLeafBones=False
        self.forceConnected=False
        self.autoBones=False
        self.primBoneAxis='-Y'
        self.secBoneAxis='X'
        self.reimportmaterials=False
        self.reimportuvs=False
        self.reimportposition=False
                                                  
class LinkerVariables(bpy.types.PropertyGroup):
    object: bpy.props.PointerProperty(name="object", type=bpy.types.Object)    

class TrackingSettings(bpy.types.PropertyGroup):
    linkid: bpy.props.IntProperty()
    linktime: bpy.props.StringProperty()
    linkpath: bpy.props.StringProperty(default="")
    tracked: bpy.props.BoolProperty(default=False)    
    OBJSettings=OBJImportSettings()
    FBXSettings=FBXImportSettings()

    OBJSettings_imageSearch: bpy.props.BoolProperty(default=True) 
    OBJSettings_smoothGroups: bpy.props.BoolProperty(default=True) 
    OBJSettings_lines: bpy.props.BoolProperty(default=True) 
    OBJSettings_reimportuvs: bpy.props.BoolProperty(default=True) 
    OBJSettings_splitByObject: bpy.props.BoolProperty(default=False) 
    OBJSettings_splitByGroup: bpy.props.BoolProperty(default=False) 
    OBJSettings_polyGroups: bpy.props.BoolProperty(default=False) 
    OBJSettings_reimportmaterials: bpy.props.BoolProperty(default=False) 
    OBJSettings_reimportposition: bpy.props.BoolProperty(default=False) 
    OBJSettings_clampSize: bpy.props.IntProperty(default=0) 
    OBJSettings_forward: bpy.props.EnumProperty(
                        name='Forward axis',
                        description='Forward axis',
                        items={
                        ('X', 'X Forward', 'X'),
                        ('Y', 'Y Forward', 'Y'),
                        ('Z', 'Z Forward', 'Z'),
                        ('-X', '-X Forward', '-X'),
                        ('-Y', '-Y Forward', '-Y'),
                        ('-Z', '-Z Forward', '-Z')
                        },
                        default='-Z')

    OBJSettings_up: bpy.props.EnumProperty(
                        name='Up axis',
                        description='Up axis',
                        items={
                        ('X', 'X Up', 'X'),
                        ('Y', 'Y Up', 'Y'),
                        ('Z', 'Z Up', 'Z'),
                        ('-X', '-X Up', '-X'),
                        ('-Y', '-Y Up', '-Y'),
                        ('-Z', '-Z Up', '-Z')
                        },
                        default='Y')

    OBJSettings_split: bpy.props.EnumProperty(
                name = "Split",
                description = "Split/Keep Vert Order",
                items = [
                    ("Split" , "Split" , "Split geometry, omits unused verts"),
                    ("Keep Vert Order", "Keep Vert Order", "Keep vertex order from file")
                ],
                default={"Split"},
                options = {"ENUM_FLAG"}
            ) 

    FBXSettings_customNormals:bpy.props.BoolProperty(default=True) 
    FBXSettings_subdData:bpy.props.BoolProperty(default=False) 
    FBXSettings_customProps:bpy.props.BoolProperty(default=True) 
    FBXSettings_EnumAsStrings:bpy.props.BoolProperty(default=True) 
    FBXSettings_imageSearch:bpy.props.BoolProperty(default=True) 
    FBXSettings_scale: bpy.props.IntProperty(default=1) 
    FBXSettings_decalOffset: bpy.props.IntProperty(default=0) 
    FBXSettings_applyTransform:bpy.props.BoolProperty(default=False) 
    FBXSettings_usePrePostRot:bpy.props.BoolProperty(default=True) 
    FBXSettings_forward:bpy.props.EnumProperty(
                    name='Forward axis',
                    description='Forward axis',
                    items={
                    ('X', 'X Forward', 'X'),
                    ('Y', 'Y Forward', 'Y'),
                    ('Z', 'Z Forward', 'Z'),
                    ('-X', '-X Forward', '-X'),
                    ('-Y', '-Y Forward', '-Y'),
                    ('-Z', '-Z Forward', '-Z')
                    },
                    default='-Z')
    FBXSettings_up:bpy.props.EnumProperty(
                    name='Up',
                    description='Up axis',
                    items={
                    ('X', 'X Up', 'X'),
                    ('Y', 'Y Up', 'Y'),
                    ('Z', 'Z Up', 'Z'),
                    ('-X', '-X Up', '-X'),
                    ('-Y', '-Y Up', '-Y'),
                    ('-Z', '-Z Up', '-Z')
                    },
                    default='Y')
    FBXSettings_useAnim:bpy.props.BoolProperty(default=True) 
    FBXSettings_animOffset:bpy.props.IntProperty(default=1)       
    FBXSettings_ignoreLeafBones:bpy.props.BoolProperty(default=False) 
    FBXSettings_forceConnected:bpy.props.BoolProperty(default=False) 
    FBXSettings_autoBones:bpy.props.BoolProperty(default=False) 
    FBXSettings_primBoneAxis:bpy.props.EnumProperty(
                    name='Primary Bone Axis',
                    description='Primary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='Y')
    FBXSettings_secBoneAxis:bpy.props.EnumProperty(
                    name='Secondary Bone Axis',
                    description='Secondary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='X')				
    FBXSettings_reimportmaterials:bpy.props.BoolProperty(default=False) 
    FBXSettings_reimportuvs:bpy.props.BoolProperty(default=False) 
    FBXSettings_reimportposition:bpy.props.BoolProperty(default=False) 

    filetype=""    
     
def registerprops():  
    bpy.utils.register_class(LinkerVariables)
    bpy.types.Scene.tracked_objects = bpy.props.CollectionProperty(type = LinkerVariables)    
    bpy.utils.register_class(TrackingSettings)    
    try:
        bpy.context.scene.tracked_objects.clear()
    except:
        pass        
    bpy.types.Object.tracking = bpy.props.PointerProperty(type=TrackingSettings)
    bpy.types.Scene.temp_date = bpy.props.StringProperty \
    (
     name = "Date",
     description = "Date",
     default = ""
    )   
    bpy.types.Scene.syncbuttonname=bpy.props.StringProperty(name="Sync button name", default="Start Sync")
    bpy.types.Scene.linkbuttonname=bpy.props.StringProperty(name="Link button name", default="Link")
    bpy.types.Scene.linkstatusname=bpy.props.StringProperty(name="Link status name", default="Linked")
    bpy.types.Scene.isinsync=bpy.props.BoolProperty(name="isinsync", description="isinsync", default=False)        
    bpy.types.Scene.savemat=bpy.props.BoolProperty(name="savemat", description="Save material", default=False)        

class LinkerDeleteOverride(bpy.types.Operator):
    """delete objects and their derivatives"""
    bl_idname = "object.delete"
    bl_label = "Delete"

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None
    
    def execute(self, context):
        for obj in context.selected_objects:
            utils.removeobject(obj)
            bpy.data.objects.remove(obj)
        return {'FINISHED'}
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

class OBJECT_OT_HeartBeat(bpy.types.Operator):
    bl_idname = "fbxlinker.heartbeat"
    bl_label = "Heartbeat modal operator"
    _timer = None
    def invoke(self, context,event):
        bpy.context.scene.isinsync=not bpy.context.scene.isinsync
        if bpy.context.scene.isinsync:bpy.context.scene.syncbuttonname="Pause Sync"
        if not bpy.context.scene.isinsync:bpy.context.scene.syncbuttonname="Start Sync"
        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}   
    def modal(self, context, event):
        if event.type in {'ESC'} or not bpy.context.scene.isinsync:
            self.cancel(context)            
            return {'CANCELLED'}
        if event.type == 'TIMER':
            if (bpy.context.object!=None and bpy.context.object.mode=='OBJECT'):
                path=""
                reimport=False
                oldselected=[]
                oldselectedindices=[]
                oldactive=[]
                oldactiveindex=[]
                object_to_merge=None
                OBJSettings=OBJImportSettings()
                FBXSettings=FBXImportSettings()
                for on in bpy.context.scene.tracked_objects: 
                    obj=None
                    try:
                        obj=on.object                        
                    except:
                        pass    
                    try:                        
                        if not utils.compareobjects(obj):
                            utils.removeobject(obj) 
                            continue                         
                    except Exception as e:
                        utils.removeobject(obj)                       
                        continue   
                    if (obj.tracking.tracked) and (not obj==None): 
                        path=obj.tracking.linkpath   

                        OBJSettings.imageSearch= obj.tracking.OBJSettings_imageSearch
                        OBJSettings.smoothGroups = obj.tracking.OBJSettings_smoothGroups
                        OBJSettings.lines = obj.tracking.OBJSettings_lines
                        OBJSettings.clampSize = obj.tracking.OBJSettings_clampSize
                        OBJSettings.splitByObject = obj.tracking.OBJSettings_splitByObject
                        OBJSettings.reimportuvs = obj.tracking.OBJSettings_reimportuvs     
                        OBJSettings.splitByGroup = obj.tracking.OBJSettings_splitByGroup
                        OBJSettings.polyGroups = obj.tracking.OBJSettings_polyGroups
                        OBJSettings.reimportmaterials = obj.tracking.OBJSettings_reimportmaterials
                        OBJSettings.reimportposition = obj.tracking.OBJSettings_reimportposition
                        OBJSettings.forward = obj.tracking.OBJSettings_forward
                        OBJSettings.up = obj.tracking.OBJSettings_up
                        OBJSettings.Split = obj.tracking.OBJSettings_split

                        FBXSettings.customNormals=obj.tracking.FBXSettings_customNormals
                        FBXSettings.subdData=obj.tracking.FBXSettings_subdData
                        FBXSettings.customProps=obj.tracking.FBXSettings_customProps
                        FBXSettings.EnumAsStrings=obj.tracking.FBXSettings_EnumAsStrings
                        FBXSettings.imageSearch=obj.tracking.FBXSettings_imageSearch
                        FBXSettings.scale=obj.tracking.FBXSettings_scale
                        FBXSettings.decalOffset=obj.tracking.FBXSettings_decalOffset
                        FBXSettings.applyTransform=obj.tracking.FBXSettings_applyTransform
                        FBXSettings.usePrePostRot=obj.tracking.FBXSettings_usePrePostRot
                        FBXSettings.forward=obj.tracking.FBXSettings_forward
                        FBXSettings.useAnim=obj.tracking.FBXSettings_useAnim
                        FBXSettings.animOffset=obj.tracking.FBXSettings_animOffset    
                        FBXSettings.ignoreLeafBones=obj.tracking.FBXSettings_ignoreLeafBones
                        FBXSettings.forceConnected=obj.tracking.FBXSettings_forceConnected
                        FBXSettings.autoBones=obj.tracking.FBXSettings_autoBones
                        FBXSettings.primBoneAxis=obj.tracking.FBXSettings_primBoneAxis
                        FBXSettings.secBoneAxis=obj.tracking.FBXSettings_secBoneAxis		
                        FBXSettings.reimportmaterials=obj.tracking.FBXSettings_reimportmaterials
                        FBXSettings.reimportuvs=obj.tracking.FBXSettings_reimportuvs
                        FBXSettings.reimportposition=obj.tracking.FBXSettings_reimportposition
	

                        if os.path.isfile(path):      
                            time=str(os.path.getmtime(path))
                            if (not time==obj.tracking.linktime):
                                reimport=True
                                oldselected=bpy.context.selected_objects
                                oldselectedindices=utils.get_indices_from_selection()
                                if (obj.tracking.linkid!=-1): oldactiveindex=bpy.context.view_layer.objects.active.tracking.linkid
                                oldactive=bpy.context.view_layer.objects.active
                                object_to_merge=obj
                                break      
                        else: 
                            utils.removeobject(obj)                    
                if reimport: 
                    #objectcontainers=[]
                    '''
                    if (bpy.context.scene.savemat):
                        objectcontainers=utils.findfacesmaterials(object_to_merge)
                        '''
                    materialcontainers=[]
                    uvcontainers=[]
                    positions=[]
                    extension=path[(len(path)-3):]
                    if (extension.lower()=="fbx"):
                        if (not FBXSettings.reimportmaterials):
                            materialcontainers=utils.materialstosave(path)
                        if (not FBXSettings.reimportuvs):    
                            uvcontainers=utils.uvtosave(path)
                        if (not FBXSettings.reimportposition):    
                            positions=utils.positionstosave(path)    
                    if (extension.lower()=="obj"): 
                        if (not OBJSettings.reimportmaterials):
                            materialcontainers=utils.materialstosave(path)      
                        if (not OBJSettings.reimportuvs):  
                            uvcontainers=utils.uvtosave(path) 
                        if (not OBJSettings.reimportposition):  
                            positions=utils.positionstosave(path)                
                    utils.deldependancies(object_to_merge)
                    utils.importModel(materialcontainers,uvcontainers,positions,path,OBJSettings,FBXSettings) 
                    '''
                    if (bpy.context.scene.savemat):
                        for i in objectcontainers:
                            print("number of faces: "+str(len(i.facemats)))
                            print("test id: "+str(i.facemats[10].face_id))
                            print("test mat: "+i.facemats[10].material.name)
                            '''
                    bpy.ops.object.select_all(action='DESELECT') 
                    activedeleted=False
                    selectiondeleted=False  
                    for o in oldselected:
                        try:
                            o.select_set(True)
                        except:
                            selectiondeleted=True
                            pass
                        try:            
                            bpy.context.view_layer.objects.active=oldactive
                        except:
                            activedeleted=True
                            pass 
                    if activedeleted:
                        for on in bpy.context.scene.tracked_objects:
                            o=on.object
                            if (o.tracking.tracked):
                                if (o.tracking.linkpath==path and o.tracking.linkid==oldactiveindex): bpy.context.view_layer.objects.active=o
                    if selectiondeleted:
                        for on in bpy.context.scene.tracked_objects:
                            o=on.object
                            if (o.tracking.tracked):
                                if (o.tracking.linkpath==path):
                                    for i in oldselectedindices:
                                        if o.tracking.linkid==i: 
                                            try:
                                                o.select_set(True)    
                                            except:
                                                utils.removeobject(o)    
                                                   
                                
        return {'PASS_THROUGH'}
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)    
    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}        
    
class Open_OT_Export(bpy.types.Operator ,bpy_extras.io_utils.ImportHelper):
        bl_idname = "fbxlinker.export"
        bl_label = "Save as"
        bl_options={'PRESET'}
        filter_glob: bpy.props.StringProperty(
        default="*.obj;*.fbx",
        options={'HIDDEN'}
        )
        filepath: bpy.props.StringProperty(subtype="FILE_PATH") 
        #somewhere to remember the address of the file
        imageSearch: bpy.props.BoolProperty( name='Image Search', description='Search subdirs for any associated images (Warning, may be slow).', default=True )
        smoothGroups: bpy.props.BoolProperty( name='Smooth Groups', description='Surround smooth groups by sharp edges.', default=True )
        lines: bpy.props.BoolProperty( name='Lines', description='Import lines and faces with 2 verts as edge.', default=True )
        clampSize: bpy.props.IntProperty( name='Clamp Size', description='Clamp bounds under this value (zero to disable).', default=0 )
        forward: bpy.props.EnumProperty(
                    name='Forward axis',
                    description='Forward axis',
                    items={
                    ('X', 'X Forward', 'X'),
                    ('Y', 'Y Forward', 'Y'),
                    ('Z', 'Z Forward', 'Z'),
                    ('-X', '-X Forward', '-X'),
                    ('-Y', '-Y Forward', '-Y'),
                    ('-Z', '-Z Forward', '-Z')
                    },
                    default='-Z')
        up: bpy.props.EnumProperty(
                    name='Up',
                    description='Up axis',
                    items={
                    ('X', 'X Up', 'X'),
                    ('Y', 'Y Up', 'Y'),
                    ('Z', 'Z Up', 'Z'),
                    ('-X', '-X Up', '-X'),
                    ('-Y', '-Y Up', '-Y'),
                    ('-Z', '-Z Up', '-Z')
                    },
                    default='Y') 
        split: bpy.props.EnumProperty(
            name = "Split",
            description = "Split/Keep Vert Order",
            items = [
                ("Split" , "Split" , "Split geometry, omits unused verts"),
                ("Keep Vert Order", "Keep Vert Order", "Keep vertex order from file")
            ],
            default={"Split"},
            options = {"ENUM_FLAG"}
        )            
        splitByObject: bpy.props.BoolProperty( name='Split by Object', description='Import OBJ Objects into Blender Objects.', default=True )
        splitByGroup: bpy.props.BoolProperty( name='Split by Group', description='Import OBJ Groups into Blender Objects.', default=False )
        polyGroups: bpy.props.BoolProperty( name='Poly Groups', description='Import OBJ groups as vertex groups.', default=False )
        reimportmaterials: bpy.props.BoolProperty( name='Reimport materials', description='If unchecked it will prevent materials from reimporting.', default=True )
        reimportuvs: bpy.props.BoolProperty( name='Reimport UVs', description='If unchecked it will prevent UVs from reimporting, trying to match UVs from object on scene onto modeified models from file', default=True )
        reimportposition: bpy.props.BoolProperty( name='Reimport position', description='If unchecked it will prevent position from reimporting', default=True )

        fbxCustomNormals: bpy.props.BoolProperty( name='Custom Normals', description='Import custom normas, if available (otherwise Blender will recompute them).', default=True )
        fbxSubdData: bpy.props.BoolProperty( name='Subdivision Data', description='Import FBX subdivision information as subdivision surface modifiers.', default=False )
        fbxCustomProps: bpy.props.BoolProperty( name='Custom Properties', description='Import user properties as custom properties.', default=True )
        fbxEnumAsStrings: bpy.props.BoolProperty( name='Import Enums As Strings', description='Stores enumeration values as strings.', default=True )
        fbxImageSearch: bpy.props.BoolProperty( name='Image Search', description='Search subdirs for any associated images (WARNING: may be slow).', default=True )
        fbxScale: bpy.props.IntProperty( name='Scale', description='Scale.', default=1 )
        fbxDecalOffset: bpy.props.IntProperty( name='Decal Offset', description='Displace geometry of alpha meshes.', default=0 )
        fbxApplyTransform: bpy.props.BoolProperty( name='Apply Transformz', description='Bake space transform into object, avoids getting unwanted rotations to objects when target space is not aligned with Blender\'s space (WARNING! experimental option, use at own risks, known broken with armatures/animations).', default=False )
        fbxPrePostRot: bpy.props.BoolProperty( name='Use Pre/Post Rotation', description='Use pre/post rotation from FBX transform (you may have to disable that in some cases).', default=True )
        fbxManualORient: bpy.props.BoolProperty( name='Manual Orientation', description='Specify orientation and scale, instead of using embedded data in FBX file.', default=False )
        fbxforward: bpy.props.EnumProperty(
                    name='Forward axis',
                    description='Forward axis',
                    items={
                    ('X', 'X Forward', 'X'),
                    ('Y', 'Y Forward', 'Y'),
                    ('Z', 'Z Forward', 'Z'),
                    ('-X', '-X Forward', '-X'),
                    ('-Y', '-Y Forward', '-Y'),
                    ('-Z', '-Z Forward', '-Z')
                    },
                    default='-Z')
        fbxup:bpy.props.EnumProperty(
                    name='Up',
                    description='Up axis',
                    items={
                    ('X', 'X Up', 'X'),
                    ('Y', 'Y Up', 'Y'),
                    ('Z', 'Z Up', 'Z'),
                    ('-X', '-X Up', '-X'),
                    ('-Y', '-Y Up', '-Y'),
                    ('-Z', '-Z Up', '-Z')
                    },
                    default='Y')
        fbxAnimation: bpy.props.BoolProperty( name='Animation', description='Import FBX animation.', default=True )
        fbxAnimationOffset: bpy.props.IntProperty( name='Animation Offset', description='Offset to apply to animation during import, in frames.', default=1 )
        fbxIgnoreLeafBones: bpy.props.BoolProperty( name='Ignore Leaf Bones', description='Ignore the las bone at the end of each chain (used to mark the length of the previous bone).', default=False )
        fbxForceConnected: bpy.props.BoolProperty( name='Force Connect Children', description='Force connection of children bones to their parent, even if their computed head/tail position do not match (can be useful with pure-joints-type armatures).', default=False )
        fbxAutoBones: bpy.props.BoolProperty( name='Automatic Bone Orientation', description='Try to align major bone axis with the bone children.', default=False )
        fbxreimportmaterials: bpy.props.BoolProperty( name='Reimport materials', description='If unchecked it will prevent materials from reimporting.', default=True )
        fbxreimportuvs: bpy.props.BoolProperty( name='Reimport UVs', description='If unchecked it will prevent UVs from reimporting, trying to match UVs from object on scene onto modeified models from file.', default=True )
        fbxreimportposition: bpy.props.BoolProperty( name='Reimport position', description='If unchecked it will prevent position from reimporting', default=True )
        fbxPrimBoneAxis: bpy.props.EnumProperty(
                    name='Primary Bone Axis',
                    description='Primary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='Y')
        fbxSecBoneAxis: bpy.props.EnumProperty(
                    name='Secondary Bone Axis',
                    description='Secondary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='X')

        def draw(self, context):  
            extension=""
            try:
                extension=self.filepath[-3:]
            except:
                pass    
            if extension.lower()=="obj": 
                layout = self.layout
                includeBox=layout.box()
                includeBox.label(text="Include")
                includeBox.prop(self, 'imageSearch')
                includeBox.prop(self, 'smoothGroups')
                includeBox.prop(self, 'lines')
                includeBox.prop(self, 'reimportmaterials')
                includeBox.prop(self, 'reimportuvs')
                transformBox = layout.box()
                transformBox.label(text="Transform")
                transformBox.prop(self, 'clampSize')
                transformBox.prop(self, 'forward')
                transformBox.prop(self, 'up')
                transformBox.prop(self, 'reimportposition')
                geometryBox = layout.box()
                geometryBox.prop(self, 'split', expand=True)
                if self.split=={'Split'}:
                    geometryBox.prop(self, 'splitByObject')
                    geometryBox.prop(self, 'splitByGroup')
                if self.split=={'Keep Vert Order'}:    
                    geometryBox.prop(self, 'polyGroups')
            if extension.lower()=="fbx": 
                layout = self.layout
                includeBox=layout.box()
                includeBox.label(text="Include") 
                includeBox.prop(self, 'fbxCustomNormals')
                includeBox.prop(self, 'fbxSubdData')
                includeBox.prop(self, 'fbxCustomProps')
                includeBox.prop(self, 'fbxEnumAsStrings')
                includeBox.prop(self, 'fbxImageSearch')
                includeBox.prop(self, 'fbxreimportmaterials')
                includeBox.prop(self, 'fbxreimportuvs')
                transformBox=layout.box()       
                transformBox.label(text="Transform")  
                transformBox.prop(self, 'fbxScale')   
                transformBox.prop(self, 'fbxDecalOffset') 
                transformBox.prop(self, 'fbxApplyTransform') 
                transformBox.prop(self, 'fbxPrePostRot') 
                transformBox.prop(self, 'fbxManualORient')
                transformBox.prop(self, 'fbxreimportposition')
                transformBoxRow=transformBox.row()
                transformBoxRow.prop(self, 'fbxforward')
                transformBoxRow.enabled=self.fbxManualORient
                transformBoxRow=transformBox.row()
                transformBoxRow.prop(self, 'fbxup')
                transformBoxRow.enabled=self.fbxManualORient
                AnimationBox=layout.box() 
                AnimationBox.label(text="Animation") 
                AnimationBox.prop(self, 'fbxAnimation') 
                AnimationBoxRow = AnimationBox.row()
                AnimationBoxRow.prop(self, 'fbxAnimationOffset')
                AnimationBoxRow.enabled=self.fbxAnimation
                ArmatureBox=layout.box()             
                ArmatureBox.label(text="Armature")
                ArmatureBox.prop(self, 'fbxIgnoreLeafBones') 
                ArmatureBox.prop(self, 'fbxForceConnected') 
                ArmatureBox.prop(self, 'fbxAutoBones') 
                ArmatureBoxRow=ArmatureBox.row()
                ArmatureBoxRow.prop(self, 'fbxPrimBoneAxis')
                ArmatureBoxRow.enabled=not self.fbxAutoBones 
                ArmatureBoxRow=ArmatureBox.row()                
                ArmatureBoxRow.prop(self, 'fbxSecBoneAxis') 
                ArmatureBoxRow.enabled=not self.fbxAutoBones

        def execute(self, context):
            utils.cleanlist()  
            OBJSettings=OBJImportSettings()
            OBJSettings.imageSearch=self.imageSearch
            OBJSettings.smoothGroups=self.smoothGroups
            OBJSettings.lines=self.lines
            OBJSettings.clampSize=self.clampSize
            OBJSettings.forward=self.forward
            OBJSettings.up=self.up
            OBJSettings.split=self.split
            OBJSettings.splitByObject=self.splitByObject
            OBJSettings.splitByGroup=self.splitByGroup
            OBJSettings.polyGroups=self.polyGroups
            OBJSettings.reimportmaterials=self.reimportmaterials
            OBJSettings.reimportuvs=self.reimportuvs
            OBJSettings.reimportposition=self.reimportposition
            FBXSettings=FBXImportSettings()
            FBXSettings.customNormals=self.fbxCustomNormals
            FBXSettings.subdData=self.fbxSubdData
            FBXSettings.customProps=self.fbxCustomProps
            FBXSettings.EnumAsStrings=self.fbxEnumAsStrings
            FBXSettings.imageSearch=self.fbxImageSearch
            FBXSettings.scale=self.fbxScale
            FBXSettings.decalOffset=self.fbxDecalOffset
            FBXSettings.applyTransform=self.fbxApplyTransform
            FBXSettings.usePrePostRot=self.fbxPrePostRot
            FBXSettings.forward=self.fbxforward
            FBXSettings.up=self.fbxup
            FBXSettings.useAnim=self.fbxAnimation
            FBXSettings.animOffset=self.fbxAnimationOffset
            FBXSettings.ignoreLeafBones=self.fbxIgnoreLeafBones
            FBXSettings.forceConnected=self.fbxForceConnected
            FBXSettings.autoBones=self.fbxAutoBones
            FBXSettings.primBoneAxis=self.fbxPrimBoneAxis
            FBXSettings.secBoneAxis=self.fbxSecBoneAxis
            FBXSettings.reimportmaterials=self.fbxreimportmaterials
            FBXSettings.reimportuvs=self.reimportuvs
            FBXSettings.reimportposition=self.fbxreimportposition
            utils.exportfbx(self.filepath,OBJSettings,FBXSettings)  
            #return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
            return {'FINISHED'}

        def invoke(self, context, event): # See comments at end  [1]
            context.window_manager.fileselect_add(self) 
            #Open browser, take reference to 'self' 
            #read the path to selected file, 
            #put path in declared string type data structure self.filepath

            return {'RUNNING_MODAL'}    
    
class Open_OT_OpenBrowser(bpy.types.Operator ,bpy_extras.io_utils.ImportHelper):
        bl_idname = "open.browser"
        bl_label = "Choose FBX to link"
        bl_options={'PRESET'}
        filter_glob: bpy.props.StringProperty(
        default="*.obj;*.fbx",
        options={'HIDDEN'}
    )
        filepath: bpy.props.StringProperty(subtype="FILE_PATH") 
        #somewhere to remember the address of the file
        imageSearch: bpy.props.BoolProperty( name='Image Search', description='Search subdirs for any associated images (Warning, may be slow).', default=True )
        smoothGroups: bpy.props.BoolProperty( name='Smooth Groups', description='Surround smooth groups by sharp edges.', default=True )
        lines: bpy.props.BoolProperty( name='Lines', description='Import lines and faces with 2 verts as edge.', default=True )
        clampSize: bpy.props.IntProperty( name='Clamp Size', description='Clamp bounds under this value (zero to disable).', default=0 )
        forward: bpy.props.EnumProperty(
                    name='Forward axis',
                    description='Forward axis',
                    items={
                    ('X', 'X Forward', 'X'),
                    ('Y', 'Y Forward', 'Y'),
                    ('Z', 'Z Forward', 'Z'),
                    ('-X', '-X Forward', '-X'),
                    ('-Y', '-Y Forward', '-Y'),
                    ('-Z', '-Z Forward', '-Z')
                    },
                    default='-Z')
        up: bpy.props.EnumProperty(
                    name='Up',
                    description='Up axis',
                    items={
                    ('X', 'X Up', 'X'),
                    ('Y', 'Y Up', 'Y'),
                    ('Z', 'Z Up', 'Z'),
                    ('-X', '-X Up', '-X'),
                    ('-Y', '-Y Up', '-Y'),
                    ('-Z', '-Z Up', '-Z')
                    },
                    default='Y') 
        split: bpy.props.EnumProperty(
            name = "Split",
            description = "Split/Keep Vert Order",
            items = [
                ("Split" , "Split" , "Split geometry, omits unused verts"),
                ("Keep Vert Order", "Keep Vert Order", "Keep vertex order from file")
            ],
            default={"Split"},
            options = {"ENUM_FLAG"}
        )            
        splitByObject: bpy.props.BoolProperty( name='Split by Object', description='Import OBJ Objects into Blender Objects.', default=True )
        splitByGroup: bpy.props.BoolProperty( name='Split by Group', description='Import OBJ Groups into Blender Objects.', default=False )
        polyGroups: bpy.props.BoolProperty( name='Poly Groups', description='Import OBJ groups as vertex groups.', default=False )
        reimportmaterials: bpy.props.BoolProperty( name='Reimport materials', description='If unchecked it will prevent materials from reimporting.', default=True )
        reimportuvs: bpy.props.BoolProperty( name='Reimport UVs', description='If unchecked it will prevent UVs from reimporting, trying to match UVs from object on scene onto modeified models from file', default=True )
        reimportposition: bpy.props.BoolProperty( name='Reimport position', description='If unchecked it will prevent position from reimporting', default=True )

        fbxCustomNormals: bpy.props.BoolProperty( name='Custom Normals', description='Import custom normas, if available (otherwise Blender will recompute them).', default=True )
        fbxSubdData: bpy.props.BoolProperty( name='Subdivision Data', description='Import FBX subdivision information as subdivision surface modifiers.', default=False )
        fbxCustomProps: bpy.props.BoolProperty( name='Custom Properties', description='Import user properties as custom properties.', default=True )
        fbxEnumAsStrings: bpy.props.BoolProperty( name='Import Enums As Strings', description='Stores enumeration values as strings.', default=True )
        fbxImageSearch: bpy.props.BoolProperty( name='Image Search', description='Search subdirs for any associated images (WARNING: may be slow).', default=True )
        fbxScale: bpy.props.IntProperty( name='Scale', description='Scale.', default=1 )
        fbxDecalOffset: bpy.props.IntProperty( name='Decal Offset', description='Displace geometry of alpha meshes.', default=0 )
        fbxApplyTransform: bpy.props.BoolProperty( name='Apply Transformz', description='Bake space transform into object, avoids getting unwanted rotations to objects when target space is not aligned with Blender\'s space (WARNING! experimental option, use at own risks, known broken with armatures/animations).', default=False )
        fbxPrePostRot: bpy.props.BoolProperty( name='Use Pre/Post Rotation', description='Use pre/post rotation from FBX transform (you may have to disable that in some cases).', default=True )
        fbxManualORient: bpy.props.BoolProperty( name='Manual Orientation', description='Specify orientation and scale, instead of using embedded data in FBX file.', default=False )
        fbxforward: bpy.props.EnumProperty(
                    name='Forward axis',
                    description='Forward axis',
                    items={
                    ('X', 'X Forward', 'X'),
                    ('Y', 'Y Forward', 'Y'),
                    ('Z', 'Z Forward', 'Z'),
                    ('-X', '-X Forward', '-X'),
                    ('-Y', '-Y Forward', '-Y'),
                    ('-Z', '-Z Forward', '-Z')
                    },
                    default='-Z')
        fbxup:bpy.props.EnumProperty(
                    name='Up',
                    description='Up axis',
                    items={
                    ('X', 'X Up', 'X'),
                    ('Y', 'Y Up', 'Y'),
                    ('Z', 'Z Up', 'Z'),
                    ('-X', '-X Up', '-X'),
                    ('-Y', '-Y Up', '-Y'),
                    ('-Z', '-Z Up', '-Z')
                    },
                    default='Y')
        fbxAnimation: bpy.props.BoolProperty( name='Animation', description='Import FBX animation.', default=True )
        fbxAnimationOffset: bpy.props.IntProperty( name='Animation Offset', description='Offset to apply to animation during import, in frames.', default=1 )
        fbxIgnoreLeafBones: bpy.props.BoolProperty( name='Ignore Leaf Bones', description='Ignore the las bone at the end of each chain (used to mark the length of the previous bone).', default=False )
        fbxForceConnected: bpy.props.BoolProperty( name='Force Connect Children', description='Force connection of children bones to their parent, even if their computed head/tail position do not match (can be useful with pure-joints-type armatures).', default=False )
        fbxAutoBones: bpy.props.BoolProperty( name='Automatic Bone Orientation', description='Try to align major bone axis with the bone children.', default=False )
        fbxreimportmaterials: bpy.props.BoolProperty( name='Reimport materials', description='If unchecked it will prevent materials from reimporting.', default=True )
        fbxreimportuvs: bpy.props.BoolProperty( name='Reimport UVs', description='If unchecked it will prevent UVs from reimporting, trying to match UVs from object on scene onto modeified models from file.', default=True )
        fbxreimportposition: bpy.props.BoolProperty( name='Reimport position', description='If unchecked it will prevent position from reimporting', default=True )
        fbxPrimBoneAxis: bpy.props.EnumProperty(
                    name='Primary Bone Axis',
                    description='Primary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='Y')
        fbxSecBoneAxis: bpy.props.EnumProperty(
                    name='Secondary Bone Axis',
                    description='Secondary Bone Axis',
                    items={
                    ('X', 'X Axis', 'X'),
                    ('Y', 'Y Axis', 'Y'),
                    ('Z', 'Z Axis', 'Z'),
                    ('-X', '-X Axis', '-X'),
                    ('-Y', '-Y Axis', '-Y'),
                    ('-Z', '-Z Axis', '-Z')
                    },
                    default='X')
       
        def draw(self, context):  
            extension=""
            try:
                extension=self.filepath[-3:]
            except:
                pass    
            if extension.lower()=="obj": 
                layout = self.layout
                includeBox=layout.box()
                includeBox.label(text="Include")
                includeBox.prop(self, 'imageSearch')
                includeBox.prop(self, 'smoothGroups')
                includeBox.prop(self, 'lines')
                includeBox.prop(self, 'reimportmaterials')
                includeBox.prop(self, 'reimportuvs')
                transformBox = layout.box()
                transformBox.label(text="Transform")
                transformBox.prop(self, 'clampSize')
                transformBox.prop(self, 'forward')
                transformBox.prop(self, 'up')
                transformBox.prop(self, 'reimportposition')
                geometryBox = layout.box()
                geometryBox.prop(self, 'split', expand=True)
                if self.split=={'Split'}:
                    geometryBox.prop(self, 'splitByObject')
                    geometryBox.prop(self, 'splitByGroup')
                if self.split=={'Keep Vert Order'}:    
                    geometryBox.prop(self, 'polyGroups')
            if extension.lower()=="fbx": 
                layout = self.layout
                includeBox=layout.box()
                includeBox.label(text="Include") 
                includeBox.prop(self, 'fbxCustomNormals')
                includeBox.prop(self, 'fbxSubdData')
                includeBox.prop(self, 'fbxCustomProps')
                includeBox.prop(self, 'fbxEnumAsStrings')
                includeBox.prop(self, 'fbxImageSearch')
                includeBox.prop(self, 'fbxreimportmaterials')
                includeBox.prop(self, 'fbxreimportuvs')
                transformBox=layout.box()       
                transformBox.label(text="Transform")  
                transformBox.prop(self, 'fbxScale')   
                transformBox.prop(self, 'fbxDecalOffset') 
                transformBox.prop(self, 'fbxApplyTransform') 
                transformBox.prop(self, 'fbxPrePostRot') 
                transformBox.prop(self, 'fbxManualORient')
                transformBox.prop(self, 'fbxreimportposition')
                transformBoxRow=transformBox.row()
                transformBoxRow.prop(self, 'fbxforward')
                transformBoxRow.enabled=self.fbxManualORient
                transformBoxRow=transformBox.row()
                transformBoxRow.prop(self, 'fbxup')
                transformBoxRow.enabled=self.fbxManualORient
                AnimationBox=layout.box() 
                AnimationBox.label(text="Animation") 
                AnimationBox.prop(self, 'fbxAnimation') 
                AnimationBoxRow = AnimationBox.row()
                AnimationBoxRow.prop(self, 'fbxAnimationOffset')
                AnimationBoxRow.enabled=self.fbxAnimation
                ArmatureBox=layout.box()             
                ArmatureBox.label(text="Armature")
                ArmatureBox.prop(self, 'fbxIgnoreLeafBones') 
                ArmatureBox.prop(self, 'fbxForceConnected') 
                ArmatureBox.prop(self, 'fbxAutoBones') 
                ArmatureBoxRow=ArmatureBox.row()
                ArmatureBoxRow.prop(self, 'fbxPrimBoneAxis')
                ArmatureBoxRow.enabled=not self.fbxAutoBones 
                ArmatureBoxRow=ArmatureBox.row()                
                ArmatureBoxRow.prop(self, 'fbxSecBoneAxis') 
                ArmatureBoxRow.enabled=not self.fbxAutoBones
            
        def execute(self, context):
            utils.cleanlist()              
            OBJSettings=OBJImportSettings()
            OBJSettings.imageSearch=self.imageSearch
            OBJSettings.smoothGroups=self.smoothGroups
            OBJSettings.lines=self.lines
            OBJSettings.clampSize=self.clampSize
            OBJSettings.forward=self.forward
            OBJSettings.up=self.up
            OBJSettings.split=self.split
            OBJSettings.splitByObject=self.splitByObject
            OBJSettings.splitByGroup=self.splitByGroup
            OBJSettings.polyGroups=self.polyGroups
            OBJSettings.reimportmaterials=self.reimportmaterials
            OBJSettings.reimportuvs=self.reimportuvs
            OBJSettings.reimportposition=self.reimportposition
            FBXSettings=FBXImportSettings()
            FBXSettings.customNormals=self.fbxCustomNormals
            FBXSettings.subdData=self.fbxSubdData
            FBXSettings.customProps=self.fbxCustomProps
            FBXSettings.EnumAsStrings=self.fbxEnumAsStrings
            FBXSettings.imageSearch=self.fbxImageSearch
            FBXSettings.scale=self.fbxScale
            FBXSettings.decalOffset=self.fbxDecalOffset
            FBXSettings.applyTransform=self.fbxApplyTransform
            FBXSettings.usePrePostRot=self.fbxPrePostRot
            FBXSettings.forward=self.fbxforward
            FBXSettings.up=self.fbxup
            FBXSettings.useAnim=self.fbxAnimation
            FBXSettings.animOffset=self.fbxAnimationOffset
            FBXSettings.ignoreLeafBones=self.fbxIgnoreLeafBones
            FBXSettings.forceConnected=self.fbxForceConnected
            FBXSettings.autoBones=self.fbxAutoBones
            FBXSettings.primBoneAxis=self.fbxPrimBoneAxis
            FBXSettings.secBoneAxis=self.fbxSecBoneAxis
            FBXSettings.reimportmaterials=self.fbxreimportmaterials
            FBXSettings.reimportuvs=self.reimportuvs
            FBXSettings.reimportposition=self.fbxreimportposition
            
            utils.importModel([],[],[],self.filepath, OBJSettings, FBXSettings)  
            #return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
            return {'FINISHED'}

        def invoke(self, context, event): # See comments at end  [1]

            context.window_manager.fileselect_add(self) 
            #Open browser, take reference to 'self' 
            #read the path to selected file, 
            #put path in declared string type data structure self.filepath

            return {'RUNNING_MODAL'}
    
class OBJECT_OT_LinkButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.linkbutton"   
    bl_label = "Start Sync"
    def execute(self, context): 
        utils.cleanlist()
        return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
        return {'FINISHED'}
    
class OBJECT_OT_SingleLinkButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.singlelinkbutton"   
    bl_label = "Link"
    def execute(self, context):   
        utils.cleanlist()     
        utils.togglelink(self)
        return {'FINISHED'} 
    
class OBJECT_OT_SaveButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.savebutton"   
    bl_label = "Save"
    def execute(self, context):        
        utils.cleanlist()  
        utils.save()
        return {'FINISHED'}     
       
class OBJECT_OT_DebugButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.debugbutton"   
    bl_label = "Debug"
    def execute(self, context):
        print("test")
        return {'FINISHED'}        
    
class PANEL_PT_FBXLinkerSubPanelDynamic(bpy.types.Panel):     
    bl_label = "Link status"
    bl_idname = "PANEL_PT_FBXLinkerSubPanelDynamic"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = "Linker"   
    @classmethod
    def poll(cls, context):
        if (context.active_object != None):
            return bpy.context.view_layer.objects.active!=None
        else: return False
    
    def draw(self, context):  
        row=self.layout.row()
        box = self.layout.box() 
        box.row() 
        obj=bpy.context.view_layer.objects.active       
        if utils.istracked(obj):  
            box.label(text="Linked")            
            box.operator("fbxlinker.singlelinkbutton", text="Unlink") 
            box.operator("fbxlinker.savebutton", text="Save")
            box.label(text="path: "+bpy.context.view_layer.objects.active.tracking.linkpath)
        else:
            box.label(text="Unlinked")  
            path=""
            try:
                path=obj.tracking.linkpath
            except:
                pass    
            if (os.path.isfile(path)):
                box.operator("fbxlinker.singlelinkbutton", text="Link")
                box.label(text="path: "+bpy.context.view_layer.objects.active.tracking.linkpath)
            else:
                box.operator("fbxlinker.export", text="Save as")  
         
class PANEL_PT_FBXLinkerMenu(bpy.types.Panel):
    bl_label = "Linker"
    bl_idname = "OBJECT_PT_FBXLinkerMenu"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Linker"
    
    def draw(self, context):        
        layout = self.layout        
        row = layout.row()
        boxLink = self.layout.box() 
        boxLink.label(text="Link files")  
        boxLink.operator("open.browser", icon="FILE_FOLDER", text="")
        boxLink.operator("fbxlinker.linkbutton", text=bpy.context.scene.syncbuttonname)   
        #boxLink.operator("fbxlinker.debugbutton")  
        
classes =(
PANEL_PT_FBXLinkerMenu,
Open_OT_OpenBrowser,
Open_OT_Export,
OBJECT_OT_HeartBeat,
OBJECT_OT_LinkButton,
OBJECT_OT_DebugButton,
OBJECT_OT_SaveButton,
OBJECT_OT_SingleLinkButton,
LinkerDeleteOverride,
PANEL_PT_FBXLinkerSubPanelDynamic,
)            

register, unregister = bpy.utils.register_classes_factory(classes) 

registerprops()

if __name__ == "__main__":    
    register()