"""Видео-петля для страницы 9686 на legobot.ru: «Мотоцикл» едет вперёд, останавливается и задним ходом возвращается (дважды за петлю).
Механика (по модели): мотор M сзади сверху крутит свою ось; резинка 1 (с перекрутом) — с оси мотора на среднюю ось,
резинка 2 — со шкива средней оси на полувтулку заднего колеса. Резинок в файле нет — они дорисованы.
В Studio модель стоит с наклоном 3,2° — здесь она выровнена, оба колеса на полу. Сценарий — layout.json, движение — motion.py.
Модель — секрет MODEL_MOTO (xz + base64): структура из Studio, все детали — из официальной библиотеки LDraw.
  python scene.py test 1,54,92,145 1280 800 12
  python scene.py anim 1 432 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix, Quaternion
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
from motion import Motion

FPS, LOOP_S = 24, 18
FRAMES = FPS * LOOP_S                                   # 432
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
MO = Motion(LAY)

# ------------------------------------------------------------------ модель: разделы MPD; разделы .dat (если есть) — в папку LDraw
text = open(os.path.join(HERE, 'models', 'moto.mpd'), encoding='utf-8-sig', errors='ignore').read().replace('\r', '')
files, cur, order = {'main': []}, 'main', ['main']
for line in text.splitlines():
    if line.startswith('0 FILE '):
        cur = line[7:].strip().lower(); files[cur] = []; order.append(cur); continue
    if line.startswith('0 NOFILE'):
        cur = None; continue
    if cur is not None:
        files[cur].append(line)
MAIN = order[0] if files['main'] else order[1]
for k in order[1:]:
    if not k.endswith('.dat'):
        continue
    p = os.path.join(ldr.LIB, 'parts', k)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write('\n'.join(files[k]) + '\n')
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 25: '#F07A12', 322: '#36AEBF', 26: '#C0397E'}
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
    if 'Chrome' in name or 'Metal' in name:
        b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.25
    if code == 0:
        b.inputs['Roughness'].default_value = 0.5
    MATS[code] = m
    return m

def mat(name, hexv, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

def lmat(v):
    return Matrix(((v[3], v[4], v[5], v[0]), (v[6], v[7], v[8], v[1]), (v[9], v[10], v[11], v[2]), (0, 0, 0, 1)))
ALIAS = {}
PARTS = []                                               # (путь, деталь, цвет, матрица LDraw)
def walk(lines, M, path, colour):
    k = -1
    for l in lines:
        t = l.split()
        if len(t) < 15 or t[0] != '1':
            continue
        k += 1
        c = int(t[1]); c = colour if c == 16 else c
        name = ' '.join(t[14:]); W = M @ lmat(list(map(float, t[2:14])))
        name = ALIAS.get(name.lower(), name)
        if name.lower() in files and not name.lower().endswith('.dat'):
            walk(files[name.lower()], W, f'{path}/{k}', c)
        else:
            PARTS.append((f'{path}/{k}', name, c, W))
walk(files[MAIN], Matrix.Identity(4), '', 16)
print('parts', len(PARTS))

# ------------------------------------------------------------------ подвижные узлы
GROUPS = {'front': {'/30', '/31', '/32', '/33', '/34', '/35'},                         # переднее колесо с осью
          'rear': {'/66', '/73', '/75', '/76', '/77', '/78', '/79', '/80', '/81'},      # заднее колесо, ось, полувтулка-шкив
          'mid': {'/65', '/67', '/68', '/69', '/70', '/71', '/72', '/74', '/82'},       # средняя ось: ролик из полувтулок и шкив 4185
          'motor': {'/54', '/55', '/56', '/57'}}                                        # ось мотора с втулкой и полувтулками
def group_of(p):
    for g, s in GROUPS.items():
        if p in s: return g
    return 'body'

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def to_b(M):
    R = C @ M.to_3x3() @ C.transposed()
    return Matrix.Translation(ld2b(M.translation)) @ R.to_4x4()
def Tl(v):
    return Matrix.Translation(Vector(v))

MESHES = {}
def part_mesh(part, color):
    key = (part, color)
    if key in MESHES:
        return MESHES[key]
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(part, color):
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

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o

PL_H = LAY['plinth']['h']
CEN = tuple(LAY['model_center'])                          # середина мотоцикла (LDraw), пол — на подставке
ROOT = empty('moto', (0, 0, PL_H))
BODY = empty('body', -ld2b(CEN), ROOT)
BIKE = empty('bike', (0, 0, 0), BODY)                     # выравнивание и ход вдоль z
G = {'body': BIKE}
AX = LAY['axes']
for g in GROUPS:
    G[g] = empty('grp_' + g, (0, 0, 0), BIKE)
for p, name, c, M in PARTS:
    g = group_of(p)
    o = bpy.data.objects.new(f'p{p.replace("/", "_")}_{name}', part_mesh(name, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    o.matrix_basis = to_b(M)

# ------------------------------------------------------------------ резинки (в файле их нет)
m_belt = mat('belt', LAY['belt']['color'], 0.55)
for i, pts_ld in enumerate(MO.belts()):
    cu = bpy.data.curves.new(f'belt{i + 1}', 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = LAY['belt']['radius'] / 20.0; cu.bevel_resolution = 3
    sp = cu.splines.new('POLY'); sp.points.add(len(pts_ld) - 1)
    for k, p in enumerate(pts_ld):
        v = ld2b(p); sp.points[k].co = (v.x, v.y, v.z, 1.0)
    sp.use_cyclic_u = True
    o = bpy.data.objects.new(f'belt{i + 1}', cu); bpy.context.collection.objects.link(o); o.parent = BIKE
    cu.materials.append(m_belt)

# ------------------------------------------------------------------ подставка, ловец теней
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth'].get('color', '#FCFDFF'), 0.55))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ анимация
LA, LY = MO.level()
LEVEL = Tl((0, -LY, 0)) @ Matrix.Rotation(LA, 4, 'X')
CAM = LAY['camera']
tgt = empty('cam_target', tuple(CAM['target']))
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    S = MO.state(t)
    BIKE.matrix_basis = to_b(Tl((0, 0, S['z'])) @ LEVEL)
    BIKE.keyframe_insert('location', frame=f); BIKE.keyframe_insert('rotation_euler', frame=f)
    for g, a in (('front', S['wheel']), ('rear', S['wheel']), ('mid', S['mid']), ('motor', S['motor'])):
        c = Vector(AX[g]['c']); d = Vector(AX[g]['d']).normalized()
        G[g].matrix_basis = to_b(Tl(c) @ Matrix.Rotation(a, 4, d) @ Tl(-c))
        G[g].keyframe_insert('location', frame=f); G[g].keyframe_insert('rotation_euler', frame=f)
    tgt.location = Vector(CAM['target']) + Vector((0, CAM.get('follow', 0) * S['z'] / 20.0, 0))
    tgt.keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#F1F6FF'))
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
AZ0 = math.radians(CAM.get('azimuth', 0))
def rot_az(v):
    c, s = math.cos(AZ0), math.sin(AZ0)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
area('key', rot_az((-34, -40, 60)), (0, 0, 6), 30, 52000, '#FFE9CC')
area('fill', rot_az((46, -34, 26)), (0, 0, 6), 26, 14000, '#DDE8FF')
area('rim', rot_az((8, 46, 46)), (0, 0, 8), 22, 18000, '#FFF4E0')

cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    az = AZ0 + SWING * math.sin(2 * math.pi * (f - 1) / FRAMES)
    T = Vector(CAM['target']) + Vector((0, CAM.get('follow', 0) * MO.state(t)['z'] / 20.0, 0))
    cam.location = T + Vector((DIST * math.cos(ELEV) * math.sin(az), -DIST * math.cos(ELEV) * math.cos(az), DIST * math.sin(ELEV)))
    cam.keyframe_insert('location', frame=f)

from bpy_extras import anim_utils
for idb in list(bpy.data.objects) + list(bpy.data.materials):
    ad = getattr(idb, 'animation_data', None)
    if idb.__class__.__name__ == 'Material' and idb.node_tree is not None:
        ad = idb.node_tree.animation_data
    if ad and ad.action:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        for fc in (cb.fcurves if cb else []):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

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

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4]); cy_.samples = int(sys.argv[5])
    for f in map(int, sys.argv[2].split(',')):
        scn.frame_set(f)
        r.filepath = os.path.join(HERE, 'frames', f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
