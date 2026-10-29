"""Рилс «Как колесо превращается в пилу?» (WeDo 2.0, своя модель LEGObot — 39 деталей, кривошипно-ползунный механизм).
Blender рендерит только модель — прозрачная плашка 1080×700 с тенью (ловец теней); фон, заголовок, подписи,
стрелки и финальную карточку дорисовывает overlay.py. Сценарий — timeline.py, модель — pila_model.py.
python scene.py test 150,280,330 1080 700 12      # номера кадров ролика (с 0, 30 к/с)
python scene.py still 50 585 1080 700 24          # стоп-кадр: угол кривошипа, дистанция камеры (картинка для ВК)
python scene.py anim 1 375 1080 700 12            # кадры плашки 1..N (кадр ролика = PLATE_FIRST + f - 1)
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
import numpy as np
import pila_model as PM
import timeline as TL

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = TL.FPS
NPL = TL.PLATE_LAST - TL.PLATE_FIRST + 1
scn.frame_start, scn.frame_end = 1, NPL
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 25: '#F07A12', 322: '#36AEBF', 27: '#A5CA18', 191: '#F2A93B', 10: '#4B9F4A'}
MATS = {}


def plastic(code):
    if code in MATS:
        return MATS[code]
    hexv = OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'ld_{code}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv)
    b.inputs['Roughness'].default_value = 0.3
    b.inputs['Coat Weight'].default_value = 0.3
    b.inputs['Coat Roughness'].default_value = 0.12
    name = COL.get(code, ('', ''))[0]
    if name.startswith('Trans'):
        b.inputs['Transmission Weight'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.12
    if code == 0:
        b.inputs['Roughness'].default_value = 0.5
    MATS[code] = m
    return m


C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))     # LDraw (x, y, z) -> Blender (x, z, -y)


def ld2b(p):
    return C @ Vector(tuple(float(v) for v in p)) / 20.0


def to_b(pos, rot):
    M3 = Matrix([list(map(float, r)) for r in rot])
    R = C @ M3 @ C.transposed()
    return Matrix.Translation(ld2b(pos)) @ R.to_4x4()


def resolve(part):
    if ldr.find(part):
        return part
    alt = {'3665a.dat': '3665.dat', '4185.dat': '4185a.dat'}.get(part)
    return alt if alt and ldr.find(alt) else part


MESHES = {}


def part_mesh(part, color):
    key = (part, color)
    if key in MESHES:
        return MESHES[key]
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(resolve(part), color):
        f = []
        for p in pts:
            q = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if q not in vidx:
                vidx[q] = len(verts); verts.append(q)
            f.append(vidx[q])
        if len(set(f)) < 3:
            continue
        if c not in codes:
            codes.append(c)
        faces.append(f); mats.append(codes.index(c))
    if not faces:
        print('MISSING or empty part:', part)
    me = bpy.data.meshes.new(part.replace('.dat', '') + f'_{color}')
    me.from_pydata(verts, [], faces)
    for c in codes:
        me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats)
    me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me
    return me


P0 = PM.build(0)
OBJ = []
for k, p in enumerate(P0):
    o = bpy.data.objects.new(f'p{k:02d}_{p["note"]}', part_mesh(p['part'], p['color']))
    bpy.context.collection.objects.link(o); o.rotation_mode = 'QUATERNION'
    OBJ.append(o)
print('parts', len(OBJ))


def pose(parts):
    for o, p in zip(OBJ, parts):
        M4 = to_b(p['pos'], p['rot'])
        loc, q, _ = M4.decompose()
        o.location = loc; o.rotation_quaternion = q
        o.hide_render = not p.get('visible', True)


# ------------------------------------------------------------------ ловец теней под основанием
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, -16 / 20.0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ свет, мир
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#EEF2F6')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
AZ0 = math.radians(TL.CAM['lon'])


def rot_az(v):
    c, s = math.cos(AZ0), math.sin(AZ0)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])


def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False


S = float(os.environ.get('LIGHT_SCALE', '1.0'))
area('key', rot_az((-40, -48, 70)), (0, 0, 3), 34, 70000 * S, '#FFE9CC')
area('fill', rot_az((54, -40, 30)), (0, 0, 3), 30, 19000 * S, '#DDE8FF')
area('rim', rot_az((10, 54, 54)), (0, 0, 4), 26, 24000 * S, '#FFF4E0')

# ------------------------------------------------------------------ камера: та же, что у overlay.py (timeline.VP_at)
eye0, tg0 = TL.eye_target(TL.T_RUN)
tgt = bpy.data.objects.new('cam_target', None); bpy.context.collection.objects.link(tgt)
tgt.location = ld2b(tg0)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24.0
cam_d.lens = 12.0 / math.tan(math.radians(TL.CAM['fov']) / 2)
cam_d.clip_start = 0.5; cam_d.clip_end = 2000


def cam_at(t, dist=None):
    if dist is None:
        eye, tg = TL.eye_target(t)
    else:
        la, lo = np.radians(TL.CAM['lat']), np.radians(TL.CAM['lon'])
        tg = np.array(TL.CAM['target'], float)
        eye = tg + dist * np.array([np.sin(lo) * np.cos(la), -np.sin(la), -np.cos(lo) * np.cos(la)])
    cam.location = ld2b(eye)


# ------------------------------------------------------------------ рендер
r = scn.render; r.engine = 'CYCLES'; r.film_transparent = True
cy_ = scn.cycles; cy_.device = 'CPU'
cy_.use_adaptive_sampling = True; cy_.adaptive_threshold = 0.06
cy_.use_denoising = True; cy_.denoiser = 'OPENIMAGEDENOISE'
cy_.max_bounces = 4; cy_.diffuse_bounces = 2; cy_.glossy_bounces = 1; cy_.transmission_bounces = 3; cy_.transparent_max_bounces = 6
r.use_persistent_data = True
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'
os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4]); cy_.samples = int(sys.argv[5])
    for i in map(int, sys.argv[2].split(',')):
        t = i / TL.FPS
        pose(TL.parts_at(t)[0]); cam_at(t)
        r.filepath = os.path.join(HERE, 'frames', f'f{i - TL.PLATE_FIRST + 1:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'still':
    th, dist = float(sys.argv[2]), float(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    pose(PM.build(th)); cam_at(0, dist)
    r.filepath = os.path.join(HERE, 'frames', 'still.png')
    bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    for f in range(s, e + 1):
        t = (TL.PLATE_FIRST + f - 1) / TL.FPS
        pose(TL.parts_at(t)[0]); cam_at(t)
        for o in OBJ:
            o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_quaternion', frame=f)
            o.keyframe_insert('hide_render', frame=f)
        cam.keyframe_insert('location', frame=f)
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
