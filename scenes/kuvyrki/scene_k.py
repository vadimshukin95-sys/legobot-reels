"""Рилс «Кувырки» (SPIKE Prime) — Blender-сцена: модель kuvyrki_model.py, поза из траектории физической симуляции (timeline_k).
python scene_k.py still '<json state>' W H SAMPLES out.png [map]   # стоп-кадр / карта движения
python scene_k.py test 60,240,450 W H SAMPLES                     # кадры ролика (с 0, 30 к/с) -> frames/fNNNN.png
python scene_k.py anim S E W H SAMPLES                            # плашки S..E (номер = кадр ролика + 1)"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier')); sys.path.insert(0, HERE)
import ldr, numpy as np
import kuvyrki_model as KM
import timeline_k as TL
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
ldr._index = None; ldr.find('3001.dat'); COL = ldr.colours()
def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)
OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#26282C', 4: '#C91A09', 1: '#1E5AA8', 14: '#F5CD2F',
            322: '#36AEBF', 26: '#C8317A', 19: '#D8BE8C'}
MAPCOL = {'frame': '#C9CED3', 'axle': '#C9CED3', 'fixed': '#8E959C', 'motor': '#F28C28', 'crank': '#F28C28', 'hub': '#C9CED3',
          'plate0': '#1F77D4', 'plate1': '#2CA02C', 'plate2': '#C2185B', 'star0': '#7FC4FF', 'star1': '#8FE08F', 'hook': '#E53935', 'catch': '#111111'}
MAPMODE = len(argv) > 5 and argv[5] == 'map'
MATS = {}
def plastic(key):
    if key in MATS: return MATS[key]
    hexv = MAPCOL[key] if isinstance(key, str) else (OVERRIDE.get(key) or '#' + COL.get(key, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'm_{key}'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = 0.32
    b.inputs['Coat Weight'].default_value = 0.3; b.inputs['Coat Roughness'].default_value = 0.12
    if key == 0: b.inputs['Roughness'].default_value = 0.45
    MATS[key] = m; return m
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p): return C @ Vector(tuple(float(v) for v in p)) / 20.0
def to_b(pos, rot):
    M3 = Matrix([list(map(float, r)) for r in rot]); R = C @ M3 @ C.transposed()
    return Matrix.Translation(ld2b(pos)) @ R.to_4x4()
MESHES = {}
def part_mesh(part, color, mapkey=None):
    key = (part, color, mapkey)
    if key in MESHES: return MESHES[key]
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(part, color):
        if mapkey: c = mapkey
        f = []
        for p in pts:
            q = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if q not in vidx: vidx[q] = len(verts); verts.append(q)
            f.append(vidx[q])
        if len(set(f)) < 3: continue
        if c not in codes: codes.append(c)
        faces.append(f); mats.append(codes.index(c))
    if not faces: print('MISSING or empty part:', part)
    me = bpy.data.meshes.new(part); me.from_pydata(verts, [], faces)
    for c in codes: me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats); me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me; return me
MODE = argv[0] if argv[0] in ('test', 'anim') else 'still'
if MODE == 'still':
    state = json.loads(argv[0])
else:
    state = TL.state_at(0); state['cam'] = dict(TL.CAM)
P = KM.build(state)
OBJ = []
for k, p in enumerate(P):
    o = bpy.data.objects.new(f'p{k:03d}', part_mesh(p['part'], p['color'], p['group'] if MAPMODE else None))
    bpy.context.collection.objects.link(o); o.rotation_mode = 'QUATERNION'
    OBJ.append(o)
def pose(parts):
    for o, p in zip(OBJ, parts):
        loc, q, _ = to_b(p['pos'], p['rot']).decompose(); o.location = loc; o.rotation_quaternion = q
pose(P)
print('parts', len(P))
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, -310 / 20.0)); bpy.context.active_object.is_shadow_catcher = True
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#EEF2F6'); world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); o.visible_camera = False
cam_cfg = state.get('cam', dict(target=[-60, 40, 0], dist=1150, az=32, el=20, fov=30))
tg = np.array(cam_cfg['target'], float); az, el = np.radians(cam_cfg['az']), np.radians(cam_cfg['el'])
eye = tg + cam_cfg['dist'] * np.array([np.sin(az) * np.cos(el), -np.sin(el), -np.cos(az) * np.cos(el)])
E, T = ld2b(eye), ld2b(tg)
area('key', tuple(T + (E - T).normalized() * 40 + Vector((-30, 0, 45))), tuple(T), 40, 90000, '#FFE9CC')
area('fill', tuple(T + Vector((45, -30, 20))), tuple(T), 34, 26000, '#DDE8FF')
area('rim', tuple(T + Vector((-20, 55, 40))), tuple(T), 30, 30000, '#FFF4E0')
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d); bpy.context.collection.objects.link(cam); scn.camera = cam
cam.location = E; cam.rotation_euler = (T - E).to_track_quat('-Z', 'Y').to_euler()
cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24.0; cam_d.lens = 12.0 / math.tan(math.radians(cam_cfg['fov']) / 2)
r = scn.render; r.engine = 'CYCLES'; r.film_transparent = True
cy_ = scn.cycles; cy_.device = 'CPU'; cy_.use_adaptive_sampling = True; cy_.adaptive_threshold = 0.05
cy_.use_denoising = True; cy_.denoiser = 'OPENIMAGEDENOISE'; cy_.max_bounces = 4; cy_.diffuse_bounces = 2; cy_.glossy_bounces = 1
scn.view_settings.view_transform = 'AgX'
try: scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception: pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'
os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)
if MODE == 'still':
    r.resolution_x, r.resolution_y = int(argv[1]), int(argv[2]); cy_.samples = int(argv[3]); r.filepath = argv[4]
    bpy.ops.render.render(write_still=True)
elif MODE == 'test':
    r.resolution_x, r.resolution_y = int(argv[2]), int(argv[3]); cy_.samples = int(argv[4])
    for i in map(int, argv[1].split(',')):
        pose(KM.build(TL.state_at(i / TL.FPS)))
        r.filepath = os.path.join(HERE, 'frames', f'f{i + 1:04d}.png'); bpy.ops.render.render(write_still=True)
else:
    s0, e0 = int(argv[1]), int(argv[2])
    r.resolution_x, r.resolution_y = int(argv[3]), int(argv[4]); cy_.samples = int(argv[5])
    for f in range(s0, e0 + 1):
        pose(KM.build(TL.state_at((f - 1) / TL.FPS)))
        for o in OBJ:
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_quaternion', frame=f)
    scn.frame_start, scn.frame_end = s0, e0
    r.use_persistent_data = True
    r.filepath = os.path.join(HERE, 'frames', 'f'); r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
