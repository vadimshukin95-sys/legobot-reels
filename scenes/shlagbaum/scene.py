"""Видео-петля 12 с для страницы /wedo-scratch на legobot.ru: «Шлагбаум с датчиком» (WeDo 2.0, своя модель LEGObot).
Механика (по инструкции): мотор крутит червяк, червяк — шестерню 24z на оси 10, на той же оси стрела.
Лампа на смартхабе красная, пока проезд закрыт, и зелёная, когда машину пропускают; жёлтые огни на стойке мигают,
пока стрела движется. Сценарий — timeline.py (тот же, что у окна программы в overlay.py), кадр — layout.json.
Модель — секрет MODEL_SHLAG (xz + base64), в публичный репозиторий не попадает.
  python scene.py test 1,60,96,150,230 1280 800 12
  python scene.py anim 1 288 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
import timeline as TL

FPS = 24
FRAMES = int(FPS * TL.LOOP)                              # 288
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))

text = open(os.path.join(HERE, 'models', 'shlagbaum.ldr'), encoding='utf-8-sig', errors='ignore').read().replace('\r', '')
files = {'main': text.splitlines()}
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
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

def mat(name, hexv, rough=0.5, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    return m

def lamp_mat(name, base, glow):                          # прозрачный круглый кирпич, который светится
    m = mat(name, base, 0.12)
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Transmission Weight'].default_value = 0.55
    b.inputs['Emission Color'].default_value = lin(glow)
    b.inputs['Emission Strength'].default_value = 0.0
    return m, b.inputs['Emission Strength']

def lmat(v):
    return Matrix(((v[3], v[4], v[5], v[0]), (v[6], v[7], v[8], v[1]), (v[9], v[10], v[11], v[2]), (0, 0, 0, 1)))
PARTS = []                                               # (путь, деталь, цвет, матрица LDraw)
k = -1
for l in files['main']:
    t = l.split()
    if len(t) < 15 or t[0] != '1':
        continue
    k += 1
    PARTS.append((k, ' '.join(t[14:]), int(t[1]), lmat(list(map(float, t[2:14])))))
print('parts', len(PARTS))

# ------------------------------------------------------------------ подвижные узлы и огни (номера — порядок строк «1 …» в модели)
BOOM = set(LAY['groups']['boom']); WORM = set(LAY['groups']['worm'])
LAMPS = {int(k): v for k, v in LAY['lamps'].items()}      # номер детали -> 'red' / 'green' / 'yellow'
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

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o

GLOW = {'red': lamp_mat('lamp_red', '#C91A09', '#FF2A14'), 'green': lamp_mat('lamp_green', '#237841', '#2BFF62'),
        'yellow': lamp_mat('lamp_yellow', '#F5CD2F', '#FFC21A')}
PL_H = LAY['plinth']['h']
CEN = tuple(LAY['model_center'])                          # середина модели (LDraw), низ модели — на подставке
ROOT = empty('shlagbaum', (0, 0, PL_H))
BODY = empty('body', -ld2b(CEN), ROOT)
G = {'body': BODY, 'boom': empty('grp_boom', (0, 0, 0), BODY), 'worm': empty('grp_worm', (0, 0, 0), BODY)}
for k, name, c, M in PARTS:
    g = 'boom' if k in BOOM else 'worm' if k in WORM else 'body'
    o = bpy.data.objects.new(f'p{k:02d}_{name}', part_mesh(name, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    o.matrix_basis = to_b(M)
    if k in LAMPS:
        for s in o.material_slots:
            s.link = 'OBJECT'; s.material = GLOW[LAMPS[k]][0]

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
B, Wm = LAY['boom'], LAY['worm']
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    c = Vector(B['c']); d = Vector(B['d']).normalized()
    G['boom'].matrix_basis = to_b(Tl(c) @ Matrix.Rotation(math.radians(TL.boom(t)) * B['sign'], 4, d) @ Tl(-c))
    c = Vector(Wm['c']); d = Vector(Wm['d']).normalized()
    G['worm'].matrix_basis = to_b(Tl(c) @ Matrix.Rotation(TL.worm(t) * Wm['sign'], 4, d) @ Tl(-c))
    for g in ('boom', 'worm'):
        G[g].keyframe_insert('location', frame=f); G[g].keyframe_insert('rotation_euler', frame=f)
    on = {'red': TL.lamp(t) == 'red', 'green': TL.lamp(t) == 'green', 'yellow': TL.blink(t)}
    for key, (m, sock) in GLOW.items():
        sock.default_value = LAY['glow'][key] if on[key] else 0.0
        sock.keyframe_insert('default_value', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#FFF7ED'))
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
S = LAY.get('light_scale', 1.0)
area('key', rot_az((-40, -48, 70)), (0, 0, 6), 34, 70000 * S, '#FFE9CC')
area('fill', rot_az((54, -40, 30)), (0, 0, 6), 30, 19000 * S, '#DDE8FF')
area('rim', rot_az((10, 54, 54)), (0, 0, 8), 26, 24000 * S, '#FFF4E0')

tgt = empty('cam_target', tuple(CAM['target']))
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
cam_d.shift_x = CAM.get('shift_x', 0.0); cam_d.shift_y = -CAM.get('shift_y', 0.0)   # в layout: + сдвигает модель вниз
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
                kp.interpolation = 'CONSTANT' if idb.__class__.__name__ == 'Material' else 'LINEAR'

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
