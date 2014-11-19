import bpy
from mathutils import Vector
import bmesh

def unix_slashes(input):
    return input.replace('\\','/')

class CheetahAtlasLayout(bpy.types.Panel):
    """Cheetah atlas import"""
    bl_label = "Cheetah Atlas Tools"
    bl_idname = "SCENE_PT_layout"
    bl_space_type = 'PROPERTIES'
    bl_region_type = 'WINDOW'
    bl_context = "scene"
    
    

    def draw(self, context):
        layout = self.layout

        scene = context.scene
        
        row = layout.row()
        row.prop(bpy.context.scene, "cheetah_pixel_per_unit")
        
        row = layout.row()
        row.prop(bpy.context.scene, "cheetah_relpath")

        layout.label(text="Import atlas:")
        row = layout.row()
        row.operator("cheetah.atlas_import")




import os.path


# ImportHelper is a helper class, defines filename and
# invoke() function which calls the file selector.
from bpy_extras.io_utils import ImportHelper
from bpy.props import StringProperty, BoolProperty, EnumProperty
from bpy.types import Operator

class CheetahImportAtlas(Operator, ImportHelper):
    """Import an .atlas file"""
    bl_idname = "cheetah.atlas_import"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Import Cheetah Atlas"

    # ImportHelper mixin class uses this
    filename_ext = ".atlas"

    filter_glob = StringProperty(
            default="*.atlas",
            options={'HIDDEN'},
            )
    relpathProp = bpy.props.StringProperty \
      (
      name = "Root Path",
      default = "",
      description = "Define the root path of the project",
      subtype = 'DIR_PATH'
      )
    # List of operator properties, the attributes will be assigned
    # to the class instance from the operator settings before calling.
    #use_setting = BoolProperty(
    #        name="Example Boolean",
    #        description="Example Tooltip",
    #        default=True,
    #        )

    #type = EnumProperty(
    #        name="Example Enum",
    #        description="Choose between two items",
    #        items=(('OPT_A', "First Option", "Description one"),
    #               ('OPT_B', "Second Option", "Description two")),
    #        default='OPT_A',
    #        )

    def createMesh(self, name, verts, uvs, img, mat, parent):
        edges = []
        faces = [[0, 1, 2, 3]]

        mesh = bpy.data.meshes.new(name=name)
        mesh.from_pydata(verts, edges, faces)
        
        ob = bpy.data.objects.new(name, mesh)
        scn = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active = ob
        
        ob.parent = parent
        
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.layers.tex.verify()
        
        # adjust UVs
        for f in bm.faces:
            for l in f.loops:
                luv = l[uv_layer]
                luv.uv = uvs[l.vert.index]
        
        bm.to_mesh(mesh)
        bm.free()      
        
        # set uv faces image
        for uv_face in ob.data.uv_textures.active.data:
            uv_face.image = img
        
        ob.data.materials.append(mat)
        
        return ob
    
    def read_cheetah_atlas(self, context, filepath):
        atlasesHolder = None
        if "atlases" in bpy.data.objects:
            atlasesHolder = bpy.data.objects["atlases"]
        else:
            bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
            atlasesHolder = bpy.context.active_object
            atlasesHolder.location[0] = -5;
            atlasesHolder.name = "atlases"
        
        # if atlas already exists, skip it
        for atlas in atlasesHolder.children:
            if atlas["path"] == filepath: return {'FINISHED'}
        
        atlasHolder = None
        bpy.ops.object.empty_add(type='PLAIN_AXES', radius=1, view_align=False, location=(0, 0, 0), layers=(True, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False, False))
        atlasHolder = bpy.context.active_object
        atlasHolder.parent = atlasesHolder
        atlasHolder['path'] = filepath
        try: 
            atlasHolder.name = unix_slashes(os.path.relpath(filepath, bpy.context.scene.cheetah_relpath))
        except:
            atlasHolder.name = unix_slashes(os.path.basename(filepath))
        atlasHolder['name'] = atlasHolder.name
        
        f = open(filepath, 'r', encoding='utf-8')
        data = f.read()
        f.close()

        img = bpy.data.images.load(filepath=filepath.replace(".atlas",".png"));
        
        mat = bpy.data.materials.new(atlasHolder.name)
        mat.use_shadeless = True
        
        tex = bpy.data.textures.new(atlasHolder.name, type = 'IMAGE')
        tex.image = img
        
        mtex = mat.texture_slots.add()
        mtex.texture = tex
        mtex.texture_coords = 'UV'
        
        prevOb = None
        
        for line in iter(data.splitlines()):
            if line[:9] == "textures:": continue
            frameData = line.split('\t')
            print(frameData)
            fName   = frameData[0]
            xPos    = int(float(frameData[1]))
            yPos    = int(float(frameData[2]))
            width   = int(float(frameData[3]))
            height  = int(float(frameData[4]))
            xOffset = int(float(frameData[5]))
            yOffset = int(float(frameData[6]))
            origW   = int(float(frameData[7]))
            origH   = int(float(frameData[8]))
            
            unitPerPixel = 1 / bpy.context.scene.cheetah_pixel_per_unit 

            imgW = img.size[0]
            imgH = img.size[1]
            
            if len(frameData) == 9 or frameData[9] != 'r': # !rotated
                verts = [Vector((xOffset, 0, origH - yOffset)) * unitPerPixel,
                         Vector((xOffset + width, 0, origH - yOffset)) * unitPerPixel,
                         Vector((xOffset + width, 0, origH - yOffset - height)) * unitPerPixel,
                         Vector((xOffset, 0, origH - yOffset - height)) * unitPerPixel,
                         Vector((0, 0, 0)) * unitPerPixel,
                         Vector((origW, 0, origH)) * unitPerPixel]

                uvs = [ Vector((float(xPos) / float(imgW), float(imgH - yPos) / float(imgH) )),
                        Vector((float(xPos + width) / float(imgW), float(imgH - yPos) / float(imgH) )),
                        Vector((float(xPos + width) / float(imgW), float(imgH - yPos - height) / float(imgH) )),
                        Vector((float(xPos) / float(imgW), float(imgH - yPos - height) / float(imgH) ))]
            else:
                verts = [Vector((yOffset, 0, origH - xOffset)) * unitPerPixel,
                         Vector((yOffset + height, 0, origH - xOffset)) * unitPerPixel,
                         Vector((yOffset + height, 0, origH - xOffset - width)) * unitPerPixel,
                         Vector((yOffset, 0, origH - xOffset - width)) * unitPerPixel,
                         Vector((0, 0, 0)) * unitPerPixel,
                         Vector((origW, 0, origH)) * unitPerPixel]

                uvs = [ Vector((float(xPos + width) / float(imgW), float(imgH - yPos) / float(imgH) )),
                        Vector((float(xPos + width) / float(imgW), float(imgH - yPos - height) / float(imgH) )),
                        Vector((float(xPos) / float(imgW), float(imgH - yPos - height) / float(imgH) )),
                        Vector((float(xPos) / float(imgW), float(imgH - yPos) / float(imgH) ))]
                
            ob = self.createMesh(fName, verts, uvs, img, mat, atlasHolder)
            ob["name"] = fName
            if prevOb: ob.location[2] = prevOb.bound_box[6][2] + prevOb.location[2]
            prevOb = ob
        
        return {'FINISHED'}
    
        
        
    def execute(self, context):
        return self.read_cheetah_atlas(context, self.filepath)
 
def setSpriteFrame(src, dst):
    for vert in src.data.vertices:
        dst.data.vertices[vert.index].co = vert.co
        
    sbm = bmesh.new()
    dbm = bmesh.new()
    sbm.from_mesh(src.data)
    dbm.from_mesh(dst.data)
    
    suv_layer = sbm.loops.layers.uv.verify()
    duv_layer = dbm.loops.layers.uv.verify()
    dbm.faces.layers.tex.verify()
    
    # adjust UVs
    for f in dbm.faces:
        for l in f.loops:
            luv = l[duv_layer]
            luv.uv = sbm.faces[f.index].loops[l.index][suv_layer].uv
    
    dbm.to_mesh(dst.data)
    sbm.free()      
    dbm.free()      
    
    mat = src.data.materials[0]
    tex = mat.texture_slots[0].texture
    img = tex.image
    
    if len(dst.data.materials) > 0: dst.data.materials[0] = mat
    else: dst.data.materials.append(mat)
    
    # set uv faces image
    for uv_face in dst.data.uv_textures.active.data:
        uv_face.image = img
        
    dst['sprite'] = src.parent['name']+'|'+src['name']

def getAtlasItems(self, context):
    items = []
    for atlas in bpy.data.objects['atlases'].children:
        items.append((atlas['name'],atlas['name'], ""))
    return items
def getFrameItems(self, context):
    items = []
    atlas = None
    for atlas in bpy.data.objects['atlases'].children:
        if atlas['name'] == self.atlasName: break
    for frame in atlas.children:
        items.append((frame['name'],frame['name'], ""))
    return items

    
class CheetahSetSpriteFrame(Operator):
    """Set Frame To Sprite"""
    bl_idname = "cheetah.set_sprite_frame"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Set Frame To Sprite"
    bl_options = {'REGISTER', 'UNDO'}


    atlasName = bpy.props.EnumProperty(
          items=getAtlasItems, 
          name="Atlas Name", description="One of the imported atlases")


    frameName = bpy.props.EnumProperty(
          items=getFrameItems, 
          name="Frame Name", description="One of the selected atlas frame")

            
    def execute(self, context):
        dst = context.active_object
        src = None
        for atlas in bpy.data.objects['atlases'].children:
            if atlas['name'] == self.atlasName: break
        for src in atlas.children:
            if src['name'] == self.frameName: break
        setSpriteFrame(src, dst)
        return {'FINISHED'}

    def invoke(self, context, event):
        return self.execute(context)
    
class CheetahAddSpriteOperator(Operator):
    """Add a new cheetah sprite object"""
    bl_idname = "cheetah.add_sprite_frame"  # important since its how bpy.ops.import_test.some_data is constructed
    bl_label = "Add Cheetah Sprite"
    bl_options = {'REGISTER', 'UNDO'}

    atlasName = bpy.props.EnumProperty(
          items=getAtlasItems, 
          name="Atlas Name", description="One of the imported atlases")

    frameName = bpy.props.EnumProperty(
          items=getFrameItems, 
          name="Frame Name", description="One of the selected atlas frame")

    
    def execute(self, context):
        edges = []
        faces = [[0, 1, 2, 3]]
        name = "sprite"
        verts = []
        parent = context.active_object
        for i in range(0,6): verts.append(Vector((0,0,0)))
        
        mesh = bpy.data.meshes.new(name=name)
        mesh.from_pydata(verts, edges, faces)
        
        ob = bpy.data.objects.new(name, mesh)
        scn = bpy.context.scene
        scn.objects.link(ob)
        scn.objects.active = ob
        
        ob.parent = parent #todo: add is mesh assert for parent
        
        mesh.update()
        bm = bmesh.new()
        bm.from_mesh(mesh)
        
        uv_layer = bm.loops.layers.uv.verify()
        bm.faces.layers.tex.verify()
        
        # adjust UVs
        for f in bm.faces:
            for l in f.loops:
                luv = l[uv_layer]
                luv.uv = Vector((0,0))
        
        bm.to_mesh(mesh)
        bm.free()      
        
        # copypaste from setframe operator
        dst = ob
        src = None
        for atlas in bpy.data.objects['atlases'].children:
            if atlas['name'] == self.atlasName: break
        for src in atlas.children:
            if src['name'] == self.frameName: break
        setSpriteFrame(src, dst)
        return {'FINISHED'}
        
    
    
def register():
    bpy.types.Scene.cheetah_relpath = bpy.props.StringProperty \
      (
      name = "Root Path",
      default = os.curdir,
      description = "Tries to use this for atlas naming",
      subtype = 'DIR_PATH'
      )
    bpy.types.Scene.cheetah_pixel_per_unit = bpy.props.FloatProperty \
      (
      name = "Pixel Per Unit",
      default = 100.0,
      description = "Default pixel/unit value for the scene",
      )
    bpy.utils.register_class(CheetahImportAtlas)
    bpy.utils.register_class(CheetahAtlasLayout)
    bpy.utils.register_class(CheetahSetSpriteFrame)
    bpy.utils.register_class(CheetahAddSpriteOperator)


def unregister():
    del bpy.types.Scene.cheetah_relpath
    del bpy.types.Scene.cheetah_pixel_per_unit
    bpy.utils.unregister_class(CheetahImportAtlas)
    bpy.utils.unregister_class(CheetahAtlasLayout)
    bpy.utils.unregister_class(CheetahSetSpriteFrame)
    bpy.utils.unregister_class(CheetahAddSpriteOperator)



if __name__ == "__main__":
    register()
