import bpy
import os
from bpy.app.handlers import persistent

bl_info = {
    "name" : "Linker",
    "author" : "Lukasz Hoffmann",
    "version" : (1, 0, 2),
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
supported_types=['MESH']         

class LinkerVariables(bpy.types.PropertyGroup):
    object = bpy.props.PointerProperty(name="object", type=bpy.types.Object)    

class TrackingSettings(bpy.types.PropertyGroup):
    linkid = bpy.props.IntProperty()
    linktime = bpy.props.StringProperty()
    linkpath = bpy.props.StringProperty()
    tracked=bpy.props.BoolProperty(default=False)
     
def registerprops():  
    bpy.utils.register_class(LinkerVariables)
    bpy.types.Scene.tracked_objects = bpy.props.CollectionProperty(type = LinkerVariables)    
    bpy.utils.register_class(TrackingSettings)
    #bpy.context.scene.tracked_objects.clear()
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

@persistent
def load_handler(dummy):
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')
    bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT')

bpy.app.handlers.load_post.append(load_handler)     
    
def importfbx(filepath):
    bpy.ops.import_scene.fbx( filepath = filepath)
    time=os.path.getmtime(filepath)
    index=0
    for obj in bpy.context.selected_objects:
        obj.tracking.linkpath=str(filepath)
        obj.tracking.linktime=str(time)
        obj.tracking.linkid=index
        obj.tracking.tracked=True
        index=index+1
        appendobject(obj)     
    
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
    bpy.ops.object.delete(use_global=False)
    bpy.ops.object.select_all(action='DESELECT')
    
def get_indices_from_selection():
    indices=[]
    for s in bpy.context.selected_objects:
        if (s.tracking.tracked):
            indices.append(s.tracking.linkid)    
    return(indices)
    
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
                for on in bpy.context.scene.tracked_objects: 
                    obj=on.object
                    try:
                        o=obj.name
                    except:
                        removeobject(obj) 
                        continue   
                    if (obj.tracking.tracked) and (not obj==None): 
                        path=obj.tracking.linkpath      
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
                    deldependancies(object_to_merge)
                    importfbx(path) 
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
    
def togglelink(self):   
    obj=bpy.context.view_layer.objects.active
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
            self.report({'ERROR'}, 'File doesn\'t exists')    
    
class Open_OT_OpenBrowser(bpy.types.Operator):
        bl_idname = "open.browser"
        bl_label = "Choose FBX to link"
        filepath: bpy.props.StringProperty(subtype="DIR_PATH") 
        #somewhere to remember the address of the file

        def execute(self, context):
            importfbx(self.filepath)  
            return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
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
        return bpy.ops.fbxlinker.heartbeat('INVOKE_DEFAULT') 
        return {'FINISHED'}
    
class OBJECT_OT_SingleLinkButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.singlelinkbutton"   
    bl_label = "Link"
    def execute(self, context):        
        togglelink(self)
        return {'FINISHED'} 
       
class OBJECT_OT_DebugButton(bpy.types.Operator):    
    bl_idname = "fbxlinker.debugbutton"   
    bl_label = "Debug"
    def execute(self, context):     
        #appendobject(bpy.context.view_layer.objects.active)
        print(len(bpy.context.scene.tracked_objects))     
        for o in bpy.context.scene.tracked_objects:
            print(o)      
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
            return bpy.context.view_layer.objects.active.tracking.tracked
        else: return False
    
    def draw(self, context):  
        row=self.layout.row()
        box = self.layout.box() 
        box.row()
        if istracked(bpy.context.view_layer.objects.active):
            box.label(text=bpy.context.scene.linkstatusname)  
            box.operator("fbxlinker.singlelinkbutton", text="Unlink") 
        else:
            box.operator("fbxlinker.singlelinkbutton", text="Link")         
        box.label(text="path: "+bpy.context.view_layer.objects.active.tracking.linkpath)
        
    
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
        boxLink.operator("fbxlinker.debugbutton")  
        
classes =(
PANEL_PT_FBXLinkerMenu,
Open_OT_OpenBrowser,
OBJECT_OT_HeartBeat,
OBJECT_OT_LinkButton,
OBJECT_OT_DebugButton,
OBJECT_OT_SingleLinkButton,
PANEL_PT_FBXLinkerSubPanelDynamic,
)            

register, unregister = bpy.utils.register_classes_factory(classes) 

registerprops()

if __name__ == "__main__":
    register()