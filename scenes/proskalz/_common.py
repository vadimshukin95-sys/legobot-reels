"""(shared helpers) Simple catapult built ONLY from LEGO Education WeDo 2.0 Core Set 45300 parts (real LDraw geometry,
set colours). Mechanism: WeDo motor -> 24t gear -> 8t gear on the arm axle (x3 speed-up) -> arm flips
up and hits a stop bar -> paper ball flies.
1 Blender unit = 1 stud. Z up. Arm points to -X at rest; it swings up and throws toward +X.

  python3 scene.py still rest,launch,side,mech,back W H SAMPLES    -> test/*.png
  python3 scene.py parts                                           -> bill of materials
"""
import bpy, bmesh, math, sys, json, os
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ldr

FPS = 24
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# LDraw colour codes used by set 45300
BLACK, WHITE, LBG, DBG, LIME, AZURE, BLORANGE, RED = 0, 15, 71, 72, 27, 322, 191, 4
OVERRIDE = {15: '#F2F2EE', 71: '#A0A5A9', 72: '#5B5F63', 0: '#2A2C30', 27: '#A5CA18',
            322: '#3EB7E8', 191: '#F8B436', 79: '#EDEDE6', 4: '#C91A09'}
MATS = {}
def plastic(code):
    if code in MATS:
        return MATS[code]
    hexv = OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'ld_{code}')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv)
    b.inputs['Roughness'].default_value = 0.3
    b.inputs['Coat Weight'].default_value = 0.3
    b.inputs['Coat Roughness'].default_value = 0.12
    name = COL.get(code, ('', ''))[0]
    if name.startswith('Trans') and code != 79:
        b.inputs['Transmission Weight'].default_value = 0.6
        b.inputs['Roughness'].default_value = 0.15
    if code == 79:
        b.inputs['Emission Color'].default_value = lin('#3BFF6E')
        b.inputs['Emission Strength'].default_value = 0.0
    MATS[code] = m
    return m

MESHES = {}
def part_mesh(part, color):
    key = (part, color)
    if key in MESHES:
        return MESHES[key]
    polys = ldr.part_polys(part, color)
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in polys:
        f = []
        for p in pts:
            k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if k not in vidx:
                vidx[k] = len(verts); verts.append(k)
            f.append(vidx[k])
        if len(set(f)) < 3:
            continue
        if c not in codes:
            codes.append(c)
        faces.append(f); mats.append(codes.index(c))
    me = bpy.data.meshes.new(part.replace('.dat', '') + f'_{color}')
    me.from_pydata(verts, [], faces)
    for c in codes:
        me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats)
    me.update()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me
    return me

BOM = []
OBJS = []
def put(part, color, loc, rz=0.0, rx=0.0, ry=0.0, parent=None, name=None, label=None):
    o = bpy.data.objects.new(name or part, part_mesh(part, color))
    bpy.context.collection.objects.link(o)
    o.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    o.location = loc
    if parent:
        o.parent = parent
    BOM.append((part, color, label))
    OBJS.append((o, part, color, label))
    return o

def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o); o.location = loc
    if parent:
        o.parent = parent
    return o

