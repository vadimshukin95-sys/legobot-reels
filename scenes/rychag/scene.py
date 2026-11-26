"""Рилс «1 груз сильнее трёх?» (рычаг-весы LEGObot, детали SPIKE Prime / 9686).
Blender рендерит модель на пластине и грузы — прозрачная плашка 1080×1500 с тенью на полу (ловец теней); фон, заголовок,
подписи, стрелки дорисовывает overlay.py. Сценарий — timeline.py, модель — rych_model.py.
python scene.py test 10,120,250 1080 1500 16     # номера кадров ролика (с 0, 30 к/с)
python scene.py anim <chunk> <chunks> 1080 1500 14   # рендер уникальных кадров (timeline.UNIQUE) порциями
"""
import bpy, math, sys, os
from mathutils import Vector, Matrix, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
import numpy as np
import rych_model as PM
import timeline as TL

bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = TL.FPS
scn.frame_start, scn.frame_end = 1, TL.FRAMES
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()


def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 25: '#F07A12', 322: '#36AEBF', 27: '#A5CA18', 191: '#F2A93B', 10: '#4B9F4A',
            26: '#C8317A', 9999: '#9A4612'}
MAPCOL = {}
XR_MATS = []                       # материалы мостов и дверей: прозрачность по timeline.xray
MATS = {}


def plastic(code, xr=False):
    if (code, xr) in MATS:
        return MATS[(code, xr)]
    hexv = MAPCOL.get(code) or OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
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
    if xr:
        XR_MATS.append(b)
    MATS[(code, xr)] = m
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


def part_mesh(part, color, xr=False):
    key = (part, color, xr)
    if key in MESHES:
        return MESHES[key]
    if part == 'SEAM':                          # шов стопки: полоска 40.4 x 0.7 x 40.4 LDU
        bpy.ops.mesh.primitive_cube_add(size=1.0)
        tmp = bpy.context.active_object; me = tmp.data
        me.transform(Matrix.Diagonal((40.4 / 20, 40.4 / 20, 0.7 / 20, 1.0)))
        me.materials.append(plastic(color)); bpy.data.objects.remove(tmp)
        MESHES[key] = me
        return me
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(resolve(part), color):
        if color in MAPCOL:
            c = color
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
        me.materials.append(plastic(c, xr))
    me.polygons.foreach_set('material_index', mats)
    me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me
    return me


P0 = PM.build(*TL.state(0))
OBJ = []
for k, (part, color, pos, rot, grp) in enumerate(P0):
    o = bpy.data.objects.new(f'p{k:02d}_{grp}_{part}', part_mesh(part, color))
    bpy.context.collection.objects.link(o); o.rotation_mode = 'QUATERNION'
    OBJ.append(o)
print('parts', len(OBJ))


def mat(name, hexv, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    return m


ROPE_M = mat('rope', '#2B2B2E', 0.8)
ROPES = []
for _ in range(2):  # нитки: цилиндр длины 1 вдоль Blender Z, тянем масштабом
    bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=1.2 / 20, depth=1.0, location=(0, 0, 0))
    o = bpy.context.active_object; o.data.materials.append(ROPE_M)
    for pg in o.data.polygons:
        pg.use_smooth = True
    ROPES.append(o)


def loop_mesh(ry=9.6, rz=11.6, r=1.2, n=40, m=10):
    """Петля вокруг балки: эллипс в плоскости YZ (LDraw), трубка радиуса r; вершины в локальных координатах Blender."""
    verts, faces = [], []
    for i in range(n):
        a = 2 * math.pi * i / n
        c = np.array([0, ry * math.cos(a), rz * math.sin(a)])
        tng = np.array([0, -ry * math.sin(a), rz * math.cos(a)]); tng /= np.linalg.norm(tng)
        nrm = np.cross(tng, [1.0, 0, 0]); nrm /= np.linalg.norm(nrm)
        for j in range(m):
            b = 2 * math.pi * j / m
            p = c + r * (math.cos(b) * nrm + math.sin(b) * np.array([1.0, 0, 0]))
            verts.append(tuple(C @ Vector(tuple(p)) / 20.0))
    for i in range(n):
        for j in range(m):
            a0, a1 = i * m + j, i * m + (j + 1) % m
            b0, b1 = ((i + 1) % n) * m + j, ((i + 1) % n) * m + (j + 1) % m
            faces.append((a0, a1, b1, b0))
    me = bpy.data.meshes.new('loop'); me.from_pydata(verts, [], faces); me.update()
    for pg in me.polygons:
        pg.use_smooth = True
    me.materials.append(ROPE_M)
    return me


LOOP_ME = loop_mesh()
LOOPS = []
for k in range(2):
    o = bpy.data.objects.new(f'loop{k}', LOOP_ME); bpy.context.collection.objects.link(o)
    o.rotation_mode = 'QUATERNION'; LOOPS.append(o)

# пол — ловец теней
bpy.ops.mesh.primitive_plane_add(size=600, location=ld2b((0, PM.FLOOR_Y, 0)))
bpy.context.active_object.is_shadow_catcher = True


def pose(t):
    th, kl = TL.state(t)
    for o, (part, color, pos, rot, grp) in zip(OBJ, PM.build(th, kl)):
        loc, q, _ = to_b(pos, rot).decompose()
        o.location = loc; o.rotation_quaternion = q
    for o, (top, bot) in zip(ROPES, PM.strings(th, kl)):
        A, B = ld2b(top), ld2b(bot)
        o.location = (A + B) / 2; o.scale = (1, 1, (A - B).length)
    for o, (c, R) in zip(LOOPS, PM.loops(th, kl)):
        loc, q, _ = to_b(c, R).decompose()
        o.location = loc; o.rotation_quaternion = q
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
area('key', rot_az((-40, -48, 70)), (0, 0, 0), 34, 70000 * S, '#FFE9CC')
area('fill', rot_az((54, -40, 30)), (0, 0, 0), 30, 19000 * S, '#DDE8FF')
area('rim', rot_az((10, 54, 54)), (0, 0, 2), 26, 24000 * S, '#FFF4E0')

# ------------------------------------------------------------------ камера: та же, что у overlay.py (timeline.VP_at)
eye0, tg0 = TL.eye_target(0)
tgt = bpy.data.objects.new('cam_target', None); bpy.context.collection.objects.link(tgt)
tgt.location = ld2b(tg0)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24.0
cam_d.lens = 12.0 / math.tan(math.radians(TL.CAM['fov']) / 2)
cam_d.clip_start = 0.5; cam_d.clip_end = 2000


def cam_at(t):
    eye, tg = TL.eye_target(t)
    cam.location = ld2b(eye); tgt.location = ld2b(tg)


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
    todo = sorted(set(TL.SRC[i] for i in map(int, sys.argv[2].split(','))))
else:
    ch, nch = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    per = (len(TL.UNIQUE) + nch - 1) // nch
    todo = TL.UNIQUE[ch * per:(ch + 1) * per]
    print('chunk', ch, 'frames', len(todo))
for i in todo:
    t = i / TL.FPS
    pose(t); cam_at(t)
    r.filepath = os.path.join(HERE, 'frames', f'f{i + 1:04d}.png')
    bpy.ops.render.render(write_still=True)
