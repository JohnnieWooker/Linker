import bpy
import bpy_extras
import os
from bpy.app.handlers import persistent
from struct import unpack
import zlib
import array
import json
import mathutils
from mathutils import Vector
from typing import Type

_BLOCK_SIZE = 13
_BLOCK_DATA = (b'\0' * _BLOCK_SIZE)
_KAYDARA_HEADER = b'Kaydara FBX Binary\x20\x20\x00\x1a\x00'
_IS_BIG_ENDIAN = (__import__("sys").byteorder != 'little')
from collections import namedtuple
FBXElem = namedtuple("FBXElem", ("id", "props", "props_type", "elems"))
del namedtuple


bl_info = {
    "name" : "Linker",
    "author" : "Lukasz Hoffmann",
    "version" : (1, 1, 3),
    "blender" : (2, 80, 0),
    "location" : "View 3D > Object Mode > Tool Shelf",
    "description" :
    "Link FBX files",
    "warning" : "",
    "wiki_url" : "",
    "tracker_url" : "",
    "category" : "Object",
    }
   
tracked_objects=[]           
parsedobjects=[]
parsedmaterials=[]

class MaterialContainter():
    def __init__(self):
        self.object=None
        self.materials_blend=[]
        self.materials_file=[]

class ObjectContainer():
    def __init__(self):
        self.facemats=[]

class facemat:
    def __init__(self):
        self.face_id=-1
        self.material=None

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
                                                  
class FBXMaterial:
    name=""
    guid=-1

class FBXObject:
    def __init__(self):
        self.name=""
        self.materials=[]
        self.guid=-2
    def addMaterial(self, material):   
        self.materials.append(material)

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
    
    
def appendobject(obj):
    item=bpy.context.scene.tracked_objects.add()
    item.object=obj

def istracked(obj):
    for o in bpy.context.scene.tracked_objects:
        if o.object==obj:
            return True
    return False

def removeobject(obj):
    counter=0
    for o in bpy.context.scene.tracked_objects:
        if o.object==obj:
            bpy.context.scene.tracked_objects.remove(counter)    
        counter=counter+1

def cleanlist():
    counter=0
    for o in bpy.context.scene.tracked_objects:
        if o.object.name not in bpy.context.scene.objects:
            bpy.context.scene.tracked_objects.remove(counter)
        counter=counter+1    

class LinkerDeleteOverride(bpy.types.Operator):
    """delete objects and their derivatives"""
    bl_idname = "object.delete"
    bl_label = "Delete"

    @classmethod
    def poll(cls, context):
        return context.selected_objects is not None
    
    def execute(self, context):
        for obj in context.selected_objects:
            removeobject(obj)
            bpy.data.objects.remove(obj)
        return {'FINISHED'}
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)

@persistent
def load_handler(dummy):
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')

bpy.app.handlers.load_post.append(load_handler)     
    
def correctmats(materialcontainers): 
    #find bloody way to determine the original material names
    if len(bpy.context.selected_objects)>0:
        path=bpy.context.selected_objects[0].tracking.linkpath
        extension=path[(len(path)-3):]
        if (extension.lower()=="fbx"):
            print("parsing fbx") 
            parsematerials(path) 
            for obj in bpy.context.selected_objects:
                if (obj.type=='MESH'):
                    for fbxobj in parsedobjects:
                        if (fbxobj.name==obj.name):                        
                            for i in range(0,len(obj.data.materials)):                                                   
                                if (fbxobj.materials[i] in bpy.data.materials):                                
                                    mat = bpy.data.materials.get(fbxobj.materials[i])
                                    oldmat=obj.data.materials[i]
                                    if (oldmat!=None):
                                        if (mat.name!=oldmat.name):
                                            obj.data.materials[i] = mat
                                            bpy.data.materials.remove(oldmat)
                                    else:
                                        obj.data.materials[i] = mat            
                                
        if (extension.lower()=="obj"):
            print("parsing obj")
            parseobjmats(path)    
    parsedobjects.clear()
    parsedmaterials.clear()
    if (len(materialcontainers)>0):
        RestoreMaterials(materialcontainers)

def read_uint(read):
    return unpack(b'<I', read(4))[0]

def read_ubyte(read):
    return unpack(b'B', read(1))[0]

read_data_dict = {
    b'Y'[0]: lambda read: unpack(b'<h', read(2))[0],  # 16 bit int
    b'C'[0]: lambda read: unpack(b'?', read(1))[0],   # 1 bit bool (yes/no)
    b'I'[0]: lambda read: unpack(b'<i', read(4))[0],  # 32 bit int
    b'F'[0]: lambda read: unpack(b'<f', read(4))[0],  # 32 bit float
    b'D'[0]: lambda read: unpack(b'<d', read(8))[0],  # 64 bit float
    b'L'[0]: lambda read: unpack(b'<q', read(8))[0],  # 64 bit int
    b'R'[0]: lambda read: read(read_uint(read)),      # binary data
    b'S'[0]: lambda read: read(read_uint(read)),      # string data
    b'f'[0]: lambda read: unpack_array(read, 'f', 4, False),  # array (float)
    b'i'[0]: lambda read: unpack_array(read, 'i', 4, True),   # array (int)
    b'd'[0]: lambda read: unpack_array(read, 'd', 8, False),  # array (double)
    b'l'[0]: lambda read: unpack_array(read, 'q', 8, True),   # array (long)
    b'b'[0]: lambda read: unpack_array(read, 'b', 1, False),  # array (bool)
    b'c'[0]: lambda read: unpack_array(read, 'B', 1, False),  # array (ubyte)
}

def unpack_array(read, array_type, array_stride, array_byteswap):
    length = read_uint(read)
    encoding = read_uint(read)
    comp_len = read_uint(read)

    data = read(comp_len)

    if encoding == 0:
        pass
    elif encoding == 1:
        data = zlib.decompress(data)

    assert(length * array_stride == len(data))

    data_array = array.array(array_type, data)
    if array_byteswap and _IS_BIG_ENDIAN:
        data_array.byteswap()
    return data_array

def read_string_ubyte(read):
    size = read_ubyte(read)
    data = read(size)
    return data

def read_elem(read, tell, use_namedtuple):
    # [0] the offset at which this block ends
    # [1] the number of properties in the scope
    # [2] the length of the property list
    end_offset = read_uint(read)
    if end_offset == 0:
        return None

    prop_count = read_uint(read)
    prop_length = read_uint(read)

    elem_id = read_string_ubyte(read)
    elem_props_type = bytearray(prop_count) 
    elem_props_data = [None] * prop_count    
    elem_subtree = []                        

    for i in range(prop_count):
        data_type = read(1)[0]
        elem_props_data[i] = read_data_dict[data_type](read)
        elem_props_type[i] = data_type

    if tell() < end_offset:
        while tell() < (end_offset - _BLOCK_SIZE):
            elem_subtree.append(read_elem(read, tell, use_namedtuple))

        if read(_BLOCK_SIZE) != _BLOCK_DATA:
            raise IOError("failed to read nested block sentinel, "
                          "expected all bytes to be 0")

    if tell() != end_offset:
        raise IOError("scope length not reached, "
                      "something is wrong (%d)" % (end_offset - tell()))

    args = (elem_id, elem_props_data, elem_props_type, elem_subtree)
    return FBXElem(*args) if use_namedtuple else args

def parse(fn, use_namedtuple=True):
    root_elems = []
    with open(fn, 'rb') as f:
        read = f.read
        tell = f.tell
        if read(len(_KAYDARA_HEADER)) != _KAYDARA_HEADER:
            raise IOError("Invalid header")
        fbx_version = read_uint(read)
        while True:
            elem = read_elem(read, tell, use_namedtuple)
            if elem is None:
                break
            root_elems.append(elem)
    args = (b'', [], bytearray(0), root_elems)
    return FBXElem(*args) if use_namedtuple else args, fbx_version

data_types = type(array)("data_types")
data_types.__dict__.update(
    dict(
        INT16=b'Y'[0],
        BOOL=b'C'[0],
        INT32=b'I'[0],
        FLOAT32=b'F'[0],
        FLOAT64=b'D'[0],
        INT64=b'L'[0],
        BYTES=b'R'[0],
        STRING=b'S'[0],
        FLOAT32_ARRAY=b'f'[0],
        INT32_ARRAY=b'i'[0],
        FLOAT64_ARRAY=b'd'[0],
        INT64_ARRAY=b'l'[0],
        BOOL_ARRAY=b'b'[0],
        BYTE_ARRAY=b'c'[0],
    ))

# pyfbx.parse_bin
parse_bin = type(array)("parse_bin")
parse_bin.__dict__.update(
    dict(
        parse=parse
    ))

def fbx2json_property_as_string(prop, prop_type):
    if prop_type == data_types.STRING:
        prop_str = prop.decode('utf-8')
        prop_str = prop_str.replace('\x00\x01', '::')
        return json.dumps(prop_str)
    else:
        prop_py_type = type(prop)
        if prop_py_type == bytes:
            return json.dumps(repr(prop)[2:-1])
        elif prop_py_type == bool:
            return json.dumps(prop)
        elif prop_py_type == array.array:
            return repr(list(prop))

    return repr(prop)

def fbx2json_properties_as_string(fbx_elem):        
    return ",".join(fbx2json_property_as_string(*prop_item) for prop_item in zip(fbx_elem.props,fbx_elem.props_type))

def fbx2json_recurse(fbx_elem, is_last):
    fbx_elem_id = fbx_elem.id.decode('utf-8')
    if (fbx_elem_id=="Model"):
        model=FBXObject()
        line=fbx2json_properties_as_string(fbx_elem)
        model.guid=line[:line.index(",")]
        model.name=line[line.index(",\"")+2:line.index("::Model")]
        parsedobjects.append(model)
    if (fbx_elem_id=="Material"):
        material=FBXMaterial()
        line=line=fbx2json_properties_as_string(fbx_elem)
        material.guid=line[:line.index(",")]
        material.name=line[line.index(",\"")+2:line.index("::Material")]
        parsedmaterials.append(material)
    if (fbx_elem_id=="C"):     
        line=line=fbx2json_properties_as_string(fbx_elem)
        leftline=line[(line.index("\",")+2):]
        mguid=leftline[:leftline.index(",")]
        oguid=leftline[(leftline.index(",")+1):]
        for o in parsedobjects:
            if o.guid==oguid: 
                for m in parsedmaterials:
                    if m.guid==mguid:
                        o.addMaterial(m.name)                                           
        
    if fbx_elem.elems:
        for fbx_elem_sub in fbx_elem.elems:
            fbx2json_recurse(fbx_elem_sub,fbx_elem_sub is fbx_elem.elems[-1])

def parsematerials(fn):
    fn_json = "%s.json" % os.path.splitext(fn)[0]
    fbx_root_elem, fbx_version = parse(fn, use_namedtuple=True)    
    for fbx_elem_sub in fbx_root_elem.elems:
        fbx2json_recurse(fbx_elem_sub,fbx_elem_sub is fbx_root_elem.elems[-1]) 
        
def parseobjmats(path):
    correctmatnames=[]
    correctmats=[]
    objfile = open(path, 'r') 
    lines = objfile.readlines()
    for line in lines: 
        if (line[:6]=="usemtl"):
            correctmatnames.append(line[7:].strip())
    for m in bpy.data.materials:  
        for mn in correctmatnames:      
            if m.name==mn:
                correctmats.append(m)
    for obj in bpy.context.selected_objects:
        for i in range(0,len(obj.data.materials)):
            if (obj.data.materials[i] in correctmats):  
                continue
            else:
                oldmat=obj.data.materials[i]
                trimmedname=""
                if (not obj.data.materials[i]==None):
                    trimmedname=obj.data.materials[i].name
                    trimmedname=trimmedname[:len(trimmedname)-4]
                    for cm in correctmats:
                        if trimmedname==cm.name:
                            obj.data.materials[i] = cm
                            try:
                                bpy.data.materials.remove(oldmat)
                            except:
                                pass    
                
    
    
def importfbx(materialcontainers,uvcontainers,positions,filepath, OBJSettings, FBXSettings):                  
    extension=filepath[(len(filepath)-3):]
    if (extension.lower()=="fbx"):
        bpy.ops.import_scene.fbx(filepath = filepath,
        use_custom_normals = FBXSettings.customNormals,
        use_subsurf = FBXSettings.subdData,
        use_custom_props  = FBXSettings.customProps,
        use_custom_props_enum_as_string = FBXSettings.EnumAsStrings,
        use_image_search = FBXSettings.imageSearch,
        global_scale = FBXSettings.scale,
        decal_offset = FBXSettings.decalOffset,
        bake_space_transform =  FBXSettings.applyTransform,
        use_prepost_rot = FBXSettings.usePrePostRot,
        axis_forward = FBXSettings.forward,
        axis_up = FBXSettings.up,
        use_anim = FBXSettings.useAnim,
        anim_offset = FBXSettings.animOffset,
        ignore_leaf_bones = FBXSettings.ignoreLeafBones,
        force_connect_children = FBXSettings.forceConnected,
        automatic_bone_orientation = FBXSettings.autoBones,
        primary_bone_axis = FBXSettings.primBoneAxis,
        secondary_bone_axis = FBXSettings.secBoneAxis
        )
    if (extension.lower()=="obj"):     
        bpy.ops.import_scene.obj(
        filepath = filepath,
        use_image_search=OBJSettings.imageSearch,
        use_smooth_groups=OBJSettings.smoothGroups,
        use_edges=OBJSettings.lines, 
        global_clamp_size=OBJSettings.clampSize, 
        use_split_objects=OBJSettings.splitByObject, 
        use_split_groups=OBJSettings.splitByGroup,
        use_groups_as_vgroups=OBJSettings.polyGroups, 
        axis_forward =OBJSettings.forward,
        axis_up =OBJSettings.up)   
    time=os.path.getmtime(filepath)
    index=0
    
    for obj in bpy.context.selected_objects:        
        obj.tracking.linkpath=str(filepath)
        obj.tracking.linktime=str(time)
        obj.tracking.linkid=index
        obj.tracking.tracked=True

        obj.tracking.OBJSettings_imageSearch= OBJSettings.imageSearch
        obj.tracking.OBJSettings_smoothGroups= OBJSettings.smoothGroups
        obj.tracking.OBJSettings_lines= OBJSettings.lines
        obj.tracking.OBJSettings_clampSize=OBJSettings.clampSize
        obj.tracking.OBJSettings_splitByObject=OBJSettings.splitByObject
        obj.tracking.OBJSettings_reimportuvs= OBJSettings.reimportuvs        
        obj.tracking.OBJSettings_splitByGroup= OBJSettings.splitByGroup
        obj.tracking.OBJSettings_polyGroups= OBJSettings.polyGroups
        obj.tracking.OBJSettings_reimportmaterials= OBJSettings.reimportmaterials
        obj.tracking.OBJSettings_reimportposition= OBJSettings.reimportposition
        obj.tracking.OBJSettings_forward= OBJSettings.forward
        obj.tracking.OBJSettings_up=OBJSettings.up
        obj.tracking.OBJSettings_split= OBJSettings.split

        obj.tracking.FBXSettings_customNormals=FBXSettings.customNormals
        obj.tracking.FBXSettings_subdData=FBXSettings.subdData
        obj.tracking.FBXSettings_customProps=FBXSettings.customProps
        obj.tracking.FBXSettings_EnumAsStrings=FBXSettings.EnumAsStrings
        obj.tracking.FBXSettings_imageSearch=FBXSettings.imageSearch
        obj.tracking.FBXSettings_scale=FBXSettings.scale        
        obj.tracking.FBXSettings_decalOffset=FBXSettings.decalOffset        
        obj.tracking.FBXSettings_applyTransform=FBXSettings.applyTransform
        obj.tracking.FBXSettings_usePrePostRot=FBXSettings.usePrePostRot
        obj.tracking.FBXSettings_forward=FBXSettings.forward
        obj.tracking.FBXSettings_up=FBXSettings.up
        obj.tracking.FBXSettings_useAnim=FBXSettings.useAnim
        obj.tracking.FBXSettings_animOffset=FBXSettings.animOffset        
        obj.tracking.FBXSettings_ignoreLeafBones=FBXSettings.ignoreLeafBones
        obj.tracking.FBXSettings_forceConnected=FBXSettings.forceConnected
        obj.tracking.FBXSettings_autoBones=FBXSettings.autoBones
        obj.tracking.FBXSettings_primBoneAxis=FBXSettings.primBoneAxis
        obj.tracking.FBXSettings_secBoneAxis=FBXSettings.secBoneAxis
        obj.tracking.FBXSettings_reimportmaterials=FBXSettings.reimportmaterials
        obj.tracking.FBXSettings_reimportuvs=FBXSettings.reimportuvs
        obj.tracking.FBXSettings_reimportposition=FBXSettings.reimportposition
        #print(obj.tracking.OBJSettings.lines)
        index=index+1
        appendobject(obj) 
    correctmats(materialcontainers)       
    if (len(uvcontainers)>0):
        RestoreUVs(uvcontainers) 
    if (len(positions)>0):
        RestorePositions(positions)    
    
def deldependancies(obj):
    linkpath=obj.tracking.linkpath
    bpy.ops.object.select_all(action='DESELECT')
    for onb in bpy.context.scene.tracked_objects:    
        o=onb.object          
        try:
            on=o.name
        except:            
            continue      
        if (str(o.tracking.linkpath)==str(linkpath)): 
            try:
                o.select_set(True)
            except:
                removeobject(o)    
    for o in bpy.context.selected_objects:
        o.tracking.tracked=False
        removeobject(o)         
    bpy.ops.object.delete()
    bpy.ops.object.select_all(action='DESELECT')
    
def get_indices_from_selection():
    indices=[]
    for s in bpy.context.selected_objects:
        if (s.tracking.tracked):
            indices.append(s.tracking.linkid)    
    return(indices)
    
def compareobjects(obj):
    for o in bpy.data.objects:
        if o==obj: return True
    return False  
    
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
                        if not compareobjects(obj):
                            removeobject(obj) 
                            continue                         
                    except Exception as e:
                        removeobject(obj)                       
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
                                oldselectedindices=get_indices_from_selection()
                                if (obj.tracking.linkid!=-1): oldactiveindex=bpy.context.view_layer.objects.active.tracking.linkid
                                oldactive=bpy.context.view_layer.objects.active
                                object_to_merge=obj
                                break      
                        else: 
                            removeobject(obj)                    
                if reimport: 
                    #objectcontainers=[]
                    '''
                    if (bpy.context.scene.savemat):
                        objectcontainers=findfacesmaterials(object_to_merge)
                        '''
                    materialcontainers=[]
                    uvcontainers=[]
                    positions=[]
                    extension=path[(len(path)-3):]
                    if (extension.lower()=="fbx"):
                        if (not FBXSettings.reimportmaterials):
                            materialcontainers=materialstosave(path)
                        if (not FBXSettings.reimportuvs):    
                            uvcontainers=uvtosave(path)
                        if (not FBXSettings.reimportposition):    
                            positions=positionstosave(path)    
                    if (extension.lower()=="obj"): 
                        if (not OBJSettings.reimportmaterials):
                            materialcontainers=materialstosave(path)      
                        if (not OBJSettings.reimportuvs):  
                            uvcontainers=uvtosave(path) 
                        if (not OBJSettings.reimportposition):  
                            positions=positionstosave(path)                
                    deldependancies(object_to_merge)
                    importfbx(materialcontainers,uvcontainers,positions,path,OBJSettings,FBXSettings) 
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
                                                removeobject(o)    
                                                   
                                
        return {'PASS_THROUGH'}
    def cancel(self, context):
        wm = context.window_manager
        wm.event_timer_remove(self._timer)    
    def execute(self, context):
        wm = context.window_manager
        self._timer = wm.event_timer_add(1, window=context.window)
        wm.modal_handler_add(self)
        return {'RUNNING_MODAL'}        
    
def uvtosave(linkpath):
    uvcontainers=[]
    oldselected=bpy.context.selected_objects
    oldactive=bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT')    
    for onb in bpy.context.scene.tracked_objects:   
        o=onb.object          
        try:
            on=o.name
        except:            
            continue      
        if (str(o.tracking.linkpath)==str(linkpath)): 
            try:                
                o.select_set(True)
                bpy.context.view_layer.objects.active=o
                bpy.ops.object.duplicate_move(OBJECT_OT_duplicate={"linked":False, "mode":'TRANSLATION'}, TRANSFORM_OT_translate={"value":(0, 0, 0), "orient_type":'GLOBAL', "orient_matrix":((0, 0, 0), (0, 0, 0), (0, 0, 0)), "orient_matrix_type":'GLOBAL', "constraint_axis":(False, False, False), "mirror":False, "use_proportional_edit":False, "proportional_edit_falloff":'SMOOTH', "proportional_size":1, "use_proportional_connected":False, "use_proportional_projected":False, "snap":False, "snap_target":'CLOSEST', "snap_point":(0, 0, 0), "snap_align":False, "snap_normal":(0, 0, 0), "gpencil_strokes":False, "cursor_transform":False, "texture_space":False, "remove_on_cancel":False, "release_confirm":False, "use_accurate":False, "use_automerge_and_split":False})
                uvcontainers.append(bpy.context.selected_objects[0])
                bpy.ops.object.select_all(action='DESELECT')
            except Exception as e:
                print(e)
                pass     
    for o in oldselected: o.select_set(True)
    bpy.context.view_layer.objects.active=oldactive     
    return uvcontainers

def RestorePositions(positions):
    counter=0
    for o in positions:    
        if (counter+1<=len(bpy.context.selected_objects)):  
            print("old position: ")
            print(o)
            bpy.context.selected_objects[counter].location=o
        counter=counter+1    
    
def RestoreUVs(uvcontainers):
    counter=0
    selected=bpy.context.selected_objects
    oldactive=bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT')  
    for container in uvcontainers:
        bpy.context.view_layer.objects.active=container
        if (len(selected)>counter):
            selected[counter].select_set(True)
            bpy.ops.object.join_uvs()
        bpy.ops.object.select_all(action='DESELECT')  
        counter=counter+1
    bpy.ops.object.select_all(action='DESELECT') 
    for o in uvcontainers: o.select_set(True)    
    bpy.ops.object.delete()    
    bpy.context.view_layer.objects.active=oldactive
    for o in selected: o.select_set(True)
    
def RestoreMaterials(materialcontainers):
    #a tutaj powinno przywaracac material ale klasa moze wymagac przeprojektowania
    counter=0
    for o in materialcontainers:    
        if (counter+1<=len(bpy.context.selected_objects)):  
            if (bpy.context.selected_objects[counter].type=='MESH'):
                for i in range (0,len(bpy.context.selected_objects[counter].data.materials)):
                    if (len(o.materials_blend)>i and len(bpy.context.selected_objects[counter].data.materials)>i):
                        bpy.context.selected_objects[counter].data.materials[i]=o.materials_blend[i]
        counter=counter+1    
    
def positionstosave(linkpath):
    positionstosave=[]
    for onb in bpy.context.scene.tracked_objects:   
        o=onb.object          
        try:
            on=o.name
        except:            
            continue      
        if (str(o.tracking.linkpath)==str(linkpath)): 
            try:                
                print(o.location)
                x=0
                y=0
                z=0
                x=x+o.location.x
                y=y+o.location.y
                z=z+o.location.z
                positionstosave.append(Vector((x,y,z)))
            except Exception as e:
                print(e)
                pass       
    #tutaj naprawic cos bo zwraca zerowa liste
    return positionstosave       
    
def materialstosave(linkpath):
    materialcontainers=[]
    for onb in bpy.context.scene.tracked_objects:   
        o=onb.object          
        try:
            on=o.name
        except:            
            continue      
        if (str(o.tracking.linkpath)==str(linkpath)): 
            try:                
                materialcontainer=MaterialContainter()
                materialcontainer.object=o
                materialcontainer.materials_blend=o.data.materials
                materialcontainers.append(materialcontainer)
            except Exception as e:
                print(e)
                pass       
    #tutaj naprawic cos bo zwraca zerowa liste
    return materialcontainers   
    
def findfacesmaterials(objecttomerge):
    linkpath=objecttomerge.tracking.linkpath
    objectcontainers=[]
    for onb in bpy.context.scene.tracked_objects:    
        o=onb.object          
        try:
            on=o.name
        except:            
            continue      
        if (str(o.tracking.linkpath)==str(linkpath)): 
            try:
                objectcontainer=ObjectContainer()
                materialfaces=[]
                for p in objecttomerge.data.polygons:
                    facemat_instance=facemat()    
                    facemat_instance.face_id=p.index
                    facemat_instance.material=o.material_slots[p.material_index].material
                    materialfaces.append(facemat_instance)
                objectcontainer.facemats=materialfaces   
                objectcontainers.append(objectcontainer) 
            except:
                pass  
    
    return objectcontainers    
    
def togglelink(self):   
    for obj in bpy.context.selected_objects:
        if (istracked(obj)):
            removeobject(obj)
            bpy.context.scene.linkbuttonname="Link"
            bpy.context.scene.linkstatusname="Unlinked"
        else: 
            path=obj.tracking.linkpath
            if (os.path.isfile(path)):
                appendobject(obj)
                bpy.context.scene.linkbuttonname="Unlink"
                bpy.context.scene.linkstatusname="Linked" 
            else:
                bpy.ops.fbxlinker.export('INVOKE_DEFAULT')    
            
def save():
    oldselected=bpy.context.selected_objects
    oldactive=bpy.context.view_layer.objects.active
    filepath=bpy.context.view_layer.objects.active.tracking.linkpath    
    bpy.ops.object.select_all(action='DESELECT')
    for on in bpy.context.scene.tracked_objects:        
        obj=on.object
        if obj.tracking.linkpath==filepath:
            obj.select_set(True)

    extension=filepath[(len(filepath)-3):]       
    if (extension.lower()=="fbx"):
        bpy.ops.export_scene.fbx(filepath = filepath,use_selection=True)
    if (extension.lower()=="obj"):     
        bpy.ops.export_scene.obj(filepath = filepath,use_selection=True)    
    time=os.path.getmtime(filepath)
    for obj in bpy.context.selected_objects:
        obj.tracking.linktime=str(time)                   
    bpy.ops.object.select_all(action='DESELECT')   
    bpy.context.view_layer.objects.active=oldactive
    for obj in oldselected:
        obj.select_set(True)
        
    
def exportfbx(filepath, OBJSettings,FBXSettings):
    extension=filepath[(len(filepath)-3):]
    if (extension.lower()=="fbx"):
        bpy.ops.export_scene.fbx(filepath = filepath,
        use_subsurf = FBXSettings.subdData,
        use_custom_props  = FBXSettings.customProps,
        global_scale = FBXSettings.scale,
        bake_space_transform =  FBXSettings.applyTransform,
        axis_forward = FBXSettings.forward,
        axis_up = FBXSettings.up,
        primary_bone_axis = FBXSettings.primBoneAxis,
        secondary_bone_axis = FBXSettings.secBoneAxis
        )
    if (extension.lower()=="obj"):     
        bpy.ops.export_scene.obj(
        filepath = filepath,
        use_smooth_groups=OBJSettings.smoothGroups,
        use_edges=OBJSettings.lines, 
        axis_forward =OBJSettings.forward,
        axis_up =OBJSettings.up)   
    oldselection=bpy.context.selected_objects
    oldactive=bpy.context.view_layer.objects.active
    bpy.ops.object.select_all(action='DESELECT')   
    for obj in bpy.context.scene.tracked_objects:
        if obj.object.tracking.linkpath==filepath and not obj.object in oldselection:
            obj.object.select_set(True) 
            bpy.context.view_layer.objects.active=obj.object
            removeobject(obj.object)
    bpy.ops.object.delete()        
    time=os.path.getmtime(filepath)
    index=0    
    bpy.context.view_layer.objects.active=oldactive
    for obj in oldselection: 
        obj.select_set(True)        
        obj.tracking.linkpath=str(filepath)
        obj.tracking.linktime=str(time)
        obj.tracking.linkid=index
        obj.tracking.tracked=True
        obj.tracking.OBJSettings.imageSearch=OBJSettings.imageSearch
        obj.tracking.OBJSettings.smoothGroups=OBJSettings.smoothGroups
        obj.tracking.OBJSettings.lines=OBJSettings.lines
        obj.tracking.OBJSettings.clampSize=OBJSettings.clampSize
        obj.tracking.OBJSettings.forward=OBJSettings.forward
        obj.tracking.OBJSettings.up=OBJSettings.up
        obj.tracking.OBJSettings.split=OBJSettings.split
        obj.tracking.OBJSettings.splitByObject=OBJSettings.splitByObject
        obj.tracking.OBJSettings.splitByGroup=OBJSettings.splitByGroup
        obj.tracking.OBJSettings.polyGroups=OBJSettings.polyGroups      
        obj.tracking.OBJSettings.reimportmaterials=OBJSettings.reimportmaterials  
        obj.tracking.OBJSettings.reimportuvs=OBJSettings.reimportuvs 
        obj.tracking.OBJSettings.reimportposition=OBJSettings.reimportposition 
        obj.tracking.FBXSettings.customNormals=FBXSettings.customNormals
        obj.tracking.FBXSettings.subdData=FBXSettings.subdData
        obj.tracking.FBXSettings.customProps=FBXSettings.customProps
        obj.tracking.FBXSettings.EnumAsStrings=FBXSettings.EnumAsStrings
        obj.tracking.FBXSettings.imageSearch=FBXSettings.imageSearch
        obj.tracking.FBXSettings.scale=FBXSettings.scale        
        obj.tracking.FBXSettings.decalOffset=FBXSettings.decalOffset        
        obj.tracking.FBXSettings.applyTransform=FBXSettings.applyTransform
        obj.tracking.FBXSettings.usePrePostRot=FBXSettings.usePrePostRot
        obj.tracking.FBXSettings.forward=FBXSettings.forward
        obj.tracking.FBXSettings.up=FBXSettings.up
        obj.tracking.FBXSettings.useAnim=FBXSettings.useAnim
        obj.tracking.FBXSettings.animOffset=FBXSettings.animOffset        
        obj.tracking.FBXSettings.ignoreLeafBones=FBXSettings.ignoreLeafBones
        obj.tracking.FBXSettings.forceConnected=FBXSettings.forceConnected
        obj.tracking.FBXSettings.autoBones=FBXSettings.autoBones
        obj.tracking.FBXSettings.primBoneAxis=FBXSettings.primBoneAxis
        obj.tracking.FBXSettings.secBoneAxis=FBXSettings.secBoneAxis
        obj.tracking.FBXSettings.reimportmaterials=FBXSettings.reimportmaterials
        obj.tracking.FBXSettings.reimportuvs=FBXSettings.reimportuvs
        obj.tracking.FBXSettings.reimportposition=FBXSettings.reimportposition
        index=index+1
        appendobject(obj)         
    
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
        clampSize: bpy.props.FloatProperty( name='Clamp Size', description='Clamp bounds under this value (zero to disable).', default=0 )
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
        fbxScale: bpy.props.FloatProperty( name='Scale', description='Scale.', default=1 )
        fbxDecalOffset: bpy.props.FloatProperty( name='Decal Offset', description='Displace geometry of alpha meshes.', default=0 )
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
        fbxAnimationOffset: bpy.props.FloatProperty( name='Animation Offset', description='Offset to apply to animation during import, in frames.', default=1 )
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
            cleanlist()  
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
            exportfbx(self.filepath,OBJSettings,FBXSettings)  
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
        clampSize: bpy.props.FloatProperty( name='Clamp Size', description='Clamp bounds under this value (zero to disable).', default=0 )
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
        fbxScale: bpy.props.FloatProperty( name='Scale', description='Scale.', default=1 )
        fbxDecalOffset: bpy.props.FloatProperty( name='Decal Offset', description='Displace geometry of alpha meshes.', default=0 )
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
        fbxAnimationOffset: bpy.props.FloatProperty( name='Animation Offset', description='Offset to apply to animation during import, in frames.', default=1 )
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
            cleanlist()              
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
            
            importfbx([],[],[],self.filepath, OBJSettings, FBXSettings)  
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
        cleanlist()
        return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
        return {'FINISHED'}
    
class OBJECT_OT_SingleLinkButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.singlelinkbutton"   
    bl_label = "Link"
    def execute(self, context):   
        cleanlist()     
        togglelink(self)
        return {'FINISHED'} 
    
class OBJECT_OT_SaveButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.savebutton"   
    bl_label = "Save"
    def execute(self, context):        
        cleanlist()  
        save()
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
        if istracked(obj):  
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