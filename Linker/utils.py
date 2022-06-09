import bpy
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

tracked_objects=[]           
parsedobjects=[]
parsedmaterials=[]

class FBXMaterial:
    name=""
    guid=-1

class facemat:
    def __init__(self):
        self.face_id=-1
        self.material=None

class ObjectContainer():
    def __init__(self):
        self.facemats=[]

class MaterialContainter():
    def __init__(self):
        self.object=None
        self.materials_blend=[]
        self.materials_file=[]

class FBXObject:
    def __init__(self):
        self.name=""
        self.materials=[]
        self.guid=-2
    def addMaterial(self, material):   
        self.materials.append(material)

def appendobject(obj):
    item=bpy.context.scene.tracked_objects.add()
    item.object=obj

def istracked(obj):
    for o in bpy.context.scene.tracked_objects:
        if o.object==obj:
            return True
    return False

def cleanlist():
    counter=0
    for o in bpy.context.scene.tracked_objects:
        if o.object.name not in bpy.context.scene.objects:
            bpy.context.scene.tracked_objects.remove(counter)
        counter=counter+1 

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

def removeobject(obj):
    counter=0
    for o in bpy.context.scene.tracked_objects:
        if o.object==obj:
            bpy.context.scene.tracked_objects.remove(counter)    
        counter=counter+1
      
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
                    
def importModel(materialcontainers,uvcontainers,positions,filepath, OBJSettings, FBXSettings):                  
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
            
def getContext(context):
    if context=="EDIT_MESH": return "EDIT"
    return context 

def save():
    oldselected=bpy.context.selected_objects
    oldactive=bpy.context.view_layer.objects.active
    filepath=bpy.context.view_layer.objects.active.tracking.linkpath
    oldmode=getContext(bpy.context.mode)
    if (bpy.context.mode!='OBJECT'):    
        bpy.ops.object.mode_set(mode='OBJECT')
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
    bpy.ops.object.mode_set(mode=oldmode)    
        
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

@persistent
def load_handler(dummy):
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')

bpy.app.handlers.load_post.append(load_handler)             