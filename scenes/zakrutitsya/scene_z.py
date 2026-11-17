"""«Закрутится?» — плашка модели (прозрачный фон) из Blender.
python scene_z.py hook OUT.png W H SAMPLES [dist] [lat] [lon]   — макро-кадр угла из трёх шестерён"""
import bpy, math, sys, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier')); sys.path.insert(0, HERE)
import ldr
import numpy as np
import zak_model as ZM

argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
ldr._index = None; ldr.find('3001.dat'); COL = ldr.colours()


def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 19: '#D9BB7B', 14: '#F5CD2F', 322: '#36AEBF', 26: '#C8317A'}
MATS = {}


def plastic(code):
    if code in MATS: return MATS[code]
    hexv = MAPCOL.get(code) or OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'ld_{code}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = 0.32
    b.inputs['Coat Weight'].default_value = 0.3; b.inputs['Coat Roughness'].default_value = 0.12
    MATS[code] = m; return m


C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p): return C @ Vector(tuple(float(v) for v in p)) / 20.0
def to_b(pos, rot):
    R = C @ Matrix([list(map(float, r)) for r in rot]) @ C.transposed()
    return Matrix.Translation(ld2b(pos)) @ R.to_4x4()


MESHES = {}
def part_mesh(part, color):
    key = (part, color)
    if key in MESHES: return MESHES[key]
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(part, color):
        if color in MAPCOL: c = color
        f = []
        for p in pts:
            q = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if q not in vidx: vidx[q] = len(verts); verts.append(q)
            f.append(vidx[q])
        if len(set(f)) < 3: continue
        if c not in codes: codes.append(c)
        faces.append(f); mats.append(codes.index(c))
    if not faces: print('MISSING or empty part:', part)
    me = bpy.data.meshes.new(part.replace('.dat', '') + f'_{color}')
    me.from_pydata(verts, [], faces)
    for c in codes: me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats)
    me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me; return me


MAPCOL = {900: '#F28C28', 901: '#7B4FD8', 902: '#22A699', 903: '#C9CED3'}
MAPG = {'gearC': 900, 'gearA': 901, 'gearB': 902, 'frame': 903}
MAPMODE = argv[0] == 'map'
OBJ = []
for k, p in enumerate(ZM.build()):
    col = MAPG[p['group']] if MAPMODE else p['color']
    o = bpy.data.objects.new(f'p{k:02d}_{p["note"]}', part_mesh(p['part'], col))
    bpy.context.collection.objects.link(o); o.matrix_world = to_b(p['pos'], p['rot']); OBJ.append(o)


def pose(**kw):
    for o, p in zip(OBJ, ZM.build(**kw)):
        o.matrix_world = to_b(p['pos'], p['rot'])

world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#EEF2F6')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6


def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); o.visible_camera = False


T0 = Vector((0.4, 0.4, float(os.environ.get('T0Z', '6.8'))))                     # центр узла шестерён (Blender, шипы)
TF = Vector((2.6, 0.6, 3.0))                     # центр всей модели
area('key', (-34, -30, 44), TF, 26, 14000, '#FFE9CC')
area('fill', (32, -34, 14), TF, 24, 4200, '#DDE8FF')
area('rim', (8, 36, 34), TF, 22, 6500, '#FFF4E0')

cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = bpy.data.objects.new('t', None); bpy.context.collection.objects.link(tgt); tgt.location = T0
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.lens = 85; cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = 5.6

r = scn.render; r.engine = 'CYCLES'; r.film_transparent = True
cy = scn.cycles; cy.device = 'CPU'; cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.05
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 1
scn.view_settings.view_transform = 'AgX'
try: scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'

mode = argv[0]
if mode in ('map', 'full'):
    out, W, H, S = argv[1], int(argv[2]), int(argv[3]), int(argv[4])
    dist, lat, lon = float(argv[5]), float(argv[6]), float(argv[7])
    tgt.location = TF if len(argv) < 9 else T0
    cam_d.lens = 50; cam_d.dof.use_dof = False
    la, lo = math.radians(lat), math.radians(lon)
    cam.location = tgt.location + dist * Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
    r.resolution_x, r.resolution_y = W, H; cy.samples = S
    r.filepath = out; bpy.ops.render.render(write_still=True)
if mode in ('states', 'proj'):
    # камера крючка: python scene_z.py states OUTDIR W H SAMPLES [имена через запятую]
    import timeline_z as TZ
    dist, lat, lon = 26.0, 24.0, -122.0
    la, lo = math.radians(lat), math.radians(lon)
    cam.location = T0 + dist * Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
    W, H = int(argv[2]), int(argv[3]); r.resolution_x, r.resolution_y = W, H
    if mode == 'proj':
        # проекция 3D-точек (LDraw, LDU) из JSON-файла argv[1] -> argv[1] с полем uv (пиксели 1080x1920)
        import json
        from bpy_extras.object_utils import world_to_camera_view
        bpy.context.view_layer.update()
        J = json.load(open(argv[1]))
        for key, pts in J['pts'].items():
            uv = []
            for q in pts:
                c = world_to_camera_view(scn, cam, ld2b(q))
                uv.append([c.x * 1080, (1 - c.y) * 1920])
            J.setdefault('uv', {})[key] = uv
        json.dump(J, open(argv[1], 'w'))
    else:
        cy.samples = int(argv[4]); S = TZ.states()
        names = argv[5].split(',') if len(argv) > 5 else sorted(S)
        os.makedirs(argv[1], exist_ok=True)
        for n in names:
            fp = os.path.join(argv[1], f'{n}.png')
            if os.path.exists(fp): continue
            pose(**S[n]); bpy.context.view_layer.update()
            r.filepath = fp; bpy.ops.render.render(write_still=True)
if mode == 'hook':
    out, W, H, S = argv[1], int(argv[2]), int(argv[3]), int(argv[4])
    dist = float(argv[5]) if len(argv) > 5 else 30
    lat, lon = (float(argv[6]) if len(argv) > 6 else 32), (float(argv[7]) if len(argv) > 7 else -135)
    la, lo = math.radians(lat), math.radians(lon)
    cam.location = T0 + dist * Vector((math.cos(la) * math.cos(lo), math.cos(la) * math.sin(lo), math.sin(la)))
    r.resolution_x, r.resolution_y = W, H; cy.samples = S
    r.filepath = out; bpy.ops.render.render(write_still=True)
