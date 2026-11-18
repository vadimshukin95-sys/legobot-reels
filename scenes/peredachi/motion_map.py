"""Карта движения для согласования: каждая вращающаяся группа (ось со всем, что на ней) — свой цвет, рама — серая.
python motion_map.py out.png [lon] [lat] [theta_deg]
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
import numpy as np
import peredachi_model as M

out = sys.argv[1]
lon = float(sys.argv[2]) if len(sys.argv) > 2 else -28
lat = float(sys.argv[3]) if len(sys.argv) > 3 else 14
theta = math.radians(float(sys.argv[4])) if len(sys.argv) > 4 else 0.0

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
GROUP_COL = {'frame': '#C9CDD2', 'U2': '#1E5AA8', 'U1': '#36AEBF', 'C': '#F07A12', 'D1': '#F5CD2F', 'D2': '#C8317A'}


def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


MATS = {}


def mat(g):
    if g not in MATS:
        m = bpy.data.materials.new(g); m.use_nodes = True
        b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = lin(GROUP_COL[g]); b.inputs['Roughness'].default_value = 0.45
        MATS[g] = m
    return MATS[g]


C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))


def ld2b(p):
    return C @ Vector(tuple(float(v) for v in p)) / 20.0


MESH = {}
for k, p in enumerate(M.build(theta)):
    key = (p['part'], p['group'])
    if key not in MESH:
        verts, faces, vidx = [], [], {}
        for c, pts in ldr.part_polys(p['part'], 16):
            f = []
            for q in pts:
                q = tuple(round(v, 4) for v in q)
                if q not in vidx:
                    vidx[q] = len(verts); verts.append(q)
                f.append(vidx[q])
            if len(set(f)) >= 3:
                faces.append(f)
        me = bpy.data.meshes.new(p['part']); me.from_pydata(verts, [], faces); me.materials.append(mat(p['group']))
        me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
        MESH[key] = me
    o = bpy.data.objects.new(f'p{k}', MESH[key]); scn.collection.objects.link(o)
    R = C @ Matrix([list(map(float, r)) for r in p['rot']]) @ C.transposed()
    o.matrix_world = Matrix.Translation(ld2b(p['pos'])) @ R.to_4x4()

bpy.ops.mesh.primitive_plane_add(size=200, location=ld2b((0, 150, 40)))
floor = bpy.context.active_object
fm = bpy.data.materials.new('floor'); fm.use_nodes = True
fm.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value = lin('#F3F4F6')
floor.data.materials.append(fm)

w = bpy.data.worlds.new('w'); scn.world = w; w.use_nodes = True
w.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#FFFFFF')
w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
ld = bpy.data.lights.new('sun', 'SUN'); ld.energy = 3.0
so = bpy.data.objects.new('sun', ld); scn.collection.objects.link(so); so.rotation_euler = (math.radians(50), math.radians(-20), math.radians(-30))

tg = np.array([0.0, 0.0, 10.0]); d = float(os.environ.get("DIST", 1150))
la, lo = math.radians(lat), math.radians(lon)
eye = tg + d * np.array([math.sin(lo) * math.cos(la), -math.sin(la), -math.cos(lo) * math.cos(la)])
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); scn.collection.objects.link(cam)
scn.camera = cam; cam_d.lens = 70
t = bpy.data.objects.new('t', None); scn.collection.objects.link(t); t.location = ld2b(tg)
cam.location = ld2b(eye)
cc = cam.constraints.new('TRACK_TO'); cc.target = t; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'

r = scn.render; r.engine = 'CYCLES'; scn.cycles.samples = 24; scn.cycles.use_denoising = True
r.resolution_x, r.resolution_y = 900, 1300
scn.view_settings.view_transform = 'Standard'
r.filepath = out
bpy.ops.render.render(write_still=True)
