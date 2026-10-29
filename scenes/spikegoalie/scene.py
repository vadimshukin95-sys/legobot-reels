"""Видео-петля для страницы SPIKE Essential на legobot.ru: «Вратарь» отбивает три удара.
Механика (по модели): малый мотор справа качает фиолетовую балку 11; её низ на штифте тянет зелёную балку 1x16;
второй конец балки на штифте у вратаря. Вратарь стоит на полу (круглые пластины под ногами) и скользит вдоль ворот,
балка при этом наклоняется. Мяч — добавленный реквизит. Сценарий и размеры — layout.json, движение — motion.py.
Модель — секрет MODEL_ARQUERO (xz + base64): структура из Studio, все детали — из официальной библиотеки LDraw.
  python scene.py test 1,46,157,277 1280 800 12
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
text = open(os.path.join(HERE, 'models', 'arquero.mpd'), encoding='utf-8-sig', errors='ignore').read().replace('\r', '')
files, cur, order = {}, None, []
for line in text.splitlines():
    if line.startswith('0 FILE '):
        cur = line[7:].strip().lower(); files[cur] = []; order.append(cur); continue
    if line.startswith('0 NOFILE'):
        cur = None; continue
    if cur is not None:
        files[cur].append(line)
MAIN = order[0]
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
        if name.lower() in files and not name.lower().endswith('.dat'):
            walk(files[name.lower()], W, f'{path}/{k}', c)
        else:
            PARTS.append((f'{path}/{k}', name, c, W))
walk(files[MAIN], Matrix.Identity(4), '', 16)
print('parts', len(PARTS))

# ------------------------------------------------------------------ подвижные узлы
LEVER = {'/42', '/43', '/44', '/45', '/46'}              # 2 штифта на валу мотора, балка 11, ось-штифт с втулкой внизу
def group_of(p):
    if p in LEVER: return 'lever'
    if p == '/47': return 'beam'                         # зелёная 1x16
    if p == '/48' or p.startswith('/49/'): return 'keeper'
    return 'body'

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def to_b(M):
    R = C @ M.to_3x3() @ C.transposed()
    return Matrix.Translation(ld2b(M.translation)) @ R.to_4x4()
def Tl(x, y, z=0.0):
    return Matrix.Translation(Vector((x, y, z)))
def Rz(a):
    return Matrix.Rotation(a, 4, 'Z')                    # поворот вокруг оси z LDraw

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
CEN = tuple(LAY['model_center'])                          # середина габарита (LDraw), пол — на подставке
ROOT = empty('goalie', (0, 0, PL_H))
BODY = empty('body', -ld2b(CEN), ROOT)
G = {'body': BODY}
for g in ('lever', 'beam', 'keeper'):
    G[g] = empty('grp_' + g, (0, 0, 0), BODY)
for p, name, c, M in PARTS:
    g = group_of(p)
    o = bpy.data.objects.new(f'p{p.replace("/", "_")}_{name}', part_mesh(name, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    o.matrix_basis = to_b(M)

# ------------------------------------------------------------------ мяч (реквизит): белый с тёмными пятиугольниками, плавно появляется и исчезает
BL = LAY['ball']; BR = BL['r']
def fade_mat(name, hexv, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = 0.2
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(b.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return m, mx
m_white, mix_w = fade_mat('ball_white', BL['white'], 0.38)
m_patch, mix_p = fade_mat('ball_patch', BL['patch'], 0.45)
bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=5, radius=BR / 20.0, location=(0, 0, 0))
BALL = bpy.context.active_object; BALL.name = 'ball'
BALL.data.materials.append(m_white); BALL.data.materials.append(m_patch)
ph = (1 + 5 ** 0.5) / 2
ICO = [Vector(v).normalized() for v in [(0, 1, ph), (0, 1, -ph), (0, -1, ph), (0, -1, -ph), (1, ph, 0), (1, -ph, 0),
                                         (-1, ph, 0), (-1, -ph, 0), (ph, 0, 1), (ph, 0, -1), (-ph, 0, 1), (-ph, 0, -1)]]
cosr = math.cos(math.radians(19.5))
for pg in BALL.data.polygons:
    n = pg.center.normalized()
    pg.material_index = 1 if max(n.dot(v) for v in ICO) > cosr else 0
    pg.use_smooth = True
BALL.parent = BODY
BALL.rotation_mode = 'QUATERNION'

# ------------------------------------------------------------------ подставка, ловец теней
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth'].get('color', '#FCFFFE'), 0.55))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ анимация
P = Vector((MO.PX, MO.PY, 0)); L0 = Vector((MO.L0[0], MO.L0[1], 0))
q = Quaternion((1, 0, 0, 0)); last = None
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    K = MO.kin(MO.theta(t))
    G['lever'].matrix_basis = to_b(Tl(*P[:2]) @ Rz(K['lever']) @ Tl(-P.x, -P.y))
    G['beam'].matrix_basis = to_b(Tl(*K['L']) @ Rz(K['phi']) @ Tl(-L0.x, -L0.y))
    G['keeper'].matrix_basis = to_b(Tl(*K['shift']))
    for g in ('lever', 'beam', 'keeper'):
        G[g].keyframe_insert('location', frame=f); G[g].keyframe_insert('rotation_euler', frame=f)
    bx, bz, a, i = MO.ball(t)
    if bx is not None:
        pos = ld2b((bx, -BR, bz))
        if last is not None and last[1] == i:
            d = pos - last[0]; dist = d.length
            if dist > 1e-6:
                axis = Vector((0, 0, 1)).cross(d).normalized()
                q = Quaternion(axis, dist / (BR / 20.0)) @ q
        last = (pos, i)
        BALL.location = pos
    BALL.rotation_quaternion = q
    BALL.keyframe_insert('location', frame=f); BALL.keyframe_insert('rotation_quaternion', frame=f)
    for mx in (mix_w, mix_p):
        mx.inputs[0].default_value = a; mx.inputs[0].keyframe_insert('default_value', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#F2FBF8'))
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
CAM = LAY['camera']
AZ0 = math.radians(CAM.get('azimuth', 0))
def rot_az(v):
    c, s = math.cos(AZ0), math.sin(AZ0)
    return (v[0] * c - v[1] * s, v[0] * s + v[1] * c, v[2])
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
area('key', rot_az((-34, -40, 60)), (0, 0, 8), 30, 52000, '#FFE9CC')
area('fill', rot_az((46, -34, 26)), (0, 0, 8), 26, 14000, '#DDE8FF')
area('rim', rot_az((8, 46, 46)), (0, 0, 10), 22, 18000, '#FFF4E0')

cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', tuple(CAM['target']))
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    az = AZ0 + SWING * math.sin(2 * math.pi * (f - 1) / FRAMES)
    T = Vector(CAM['target'])
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
