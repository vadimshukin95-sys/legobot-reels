"""3D-петля 15 с для первого экрана /prog на legobot.ru: «Три экрана из кирпичиков».
Три монитора, собранные из деталей LEGO (models3d.py, свои модели LEGObot), стоят полукругом на подставке.
Экраны в рендере — holdout (прозрачные «окна»): overlay.py подкладывает под них картинки Scratch / Python / браузера
по углам из frames/screens.json, поэтому робот, проходящий сквозь экран, честно исчезает в нём.
Робот из кирпичиков выпрыгивает из экрана браузера, перепрыгивает красный кирпич и ныряет в экран Scratch (timeline.py).
  python scene.py test 1,150,212,240,262,300,330 1280 800 12
  python scene.py anim 1 360 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
import timeline as TL
import models3d as MD
from bpy_extras.object_utils import world_to_camera_view

FPS = TL.FPS
FRAMES = int(FPS * TL.LOOP)                              # 360
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
LAY = TL.LAY
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 25: '#F07A12', 322: '#36AEBF', 27: '#A5CA18', 191: '#F59A1B', 10: '#4B9F4A'}
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
    if code == 0:
        b.inputs['Roughness'].default_value = 0.45
    MATS[code] = m
    return m

def mat(name, hexv, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    return m

def lmat(v):
    return Matrix(((v[3], v[4], v[5], v[0]), (v[6], v[7], v[8], v[1]), (v[9], v[10], v[11], v[2]), (0, 0, 0, 1)))
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def to_b(M):
    R = C @ M.to_3x3() @ C.transposed()
    return Matrix.Translation(ld2b(M.translation)) @ R.to_4x4()

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
    if parent is not None:
        o.parent = parent
    o.location = loc
    return o

def build(lines, root, groups=None, pivots=None):
    """Детали модели в объекты; строки «0 GROUP имя» раскладывают их по узлам (узел стоит в своей оси вращения)."""
    grp, n = None, 0
    for l in lines:
        t = l.split()
        if t[:2] == ['0', 'GROUP']:
            grp = t[2]; continue
        if len(t) < 15 or t[0] != '1':
            continue
        name, c, M = ' '.join(t[14:]), int(t[1]), lmat(list(map(float, t[2:14])))
        o = bpy.data.objects.new(f'{root.name}_{n:02d}_{name}', part_mesh(name, c)); n += 1
        bpy.context.collection.objects.link(o)
        if groups and grp in groups:
            o.parent = groups[grp]; o.matrix_basis = Matrix.Translation(-pivots[grp]) @ to_b(M)
        else:
            o.parent = root; o.matrix_basis = to_b(M)
    return n

PLH = LAY['plinth']['h']
# ------------------------------------------------------------------ мониторы, экраны-holdout, подсветка от экранов
HOLD = bpy.data.materials.new('screen_holdout'); HOLD.use_nodes = True
nt = HOLD.node_tree; nt.nodes.clear()
nt.links.new(nt.nodes.new('ShaderNodeHoldout').outputs[0], nt.nodes.new('ShaderNodeOutputMaterial').inputs['Surface'])
SCREENS = {}
for name, m in LAY['monitors'].items():
    root = empty(f'mon_{name}', (m['at'][0], m['at'][1], PLH))
    root.rotation_euler = (0, 0, math.radians(m['rot']))
    print('parts', name, build(MD.monitor(m['bezel']), root))
    me = bpy.data.meshes.new(f'screen_{name}')
    me.from_pydata([(-0.5, 0, -0.5), (0.5, 0, -0.5), (0.5, 0, 0.5), (-0.5, 0, 0.5)], [], [(0, 1, 2, 3)])
    me.materials.append(HOLD)
    sc = bpy.data.objects.new(f'screen_{name}', me); bpy.context.collection.objects.link(sc)
    sc.parent = root; sc.location = (0, -0.03, TL.SCREEN_Z); sc.scale = (TL.SCREEN_W, 1, TL.SCREEN_H)
    sc.visible_shadow = False
    SCREENS[name] = sc
    ld = bpy.data.lights.new(f'glow_{name}', 'AREA'); ld.shape = 'RECTANGLE'
    ld.size, ld.size_y = TL.SCREEN_W * 0.9, TL.SCREEN_H * 0.9
    ld.energy = LAY['screen_light']; ld.color = lin(m['light'])[:3]
    lo = bpy.data.objects.new(f'glow_{name}', ld); bpy.context.collection.objects.link(lo)
    lo.parent = root; lo.location = (0, -0.4, TL.SCREEN_Z)
    lo.rotation_euler = (math.radians(-90), 0, 0)                 # свет смотрит вдоль -y монитора (на зрителя)
    lo.visible_camera = False

# ------------------------------------------------------------------ кирпич-препятствие
OB = LAY['obstacle']
ob = empty('obstacle', (OB['at'][0], OB['at'][1], PLH)); ob.rotation_euler = (0, 0, math.radians(OB['rot']))
build(['1 4 0 -24 0 1 0 0 0 1 0 0 0 1 3003.dat', '1 4 0 -48 0 1 0 0 0 1 0 0 0 1 3003.dat'], ob)

# ------------------------------------------------------------------ робот
PIV_LD = {'legL': (-30, -56, 0), 'legR': (30, -56, 0), 'armL': (-50, -108, 0), 'armR': (50, -108, 0), 'head': (0, -120, 0)}
ROB = empty('robot', (0, 0, -50))
PIV = {k: ld2b(v) for k, v in PIV_LD.items()}
GR = {k: empty(f'rb_{k}', PIV[k], ROB) for k in PIV}
print('parts robot', build(MD.robot(), ROB, GR, PIV))

# ------------------------------------------------------------------ подставка, ловец теней
bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=1, depth=PLH, location=(0, 0, PLH / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth'].get('color', '#FCFDFF'), 0.55))
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ анимация робота
for f in range(1, FRAMES + 1):
    s = TL.robot((f - 1) / FPS)
    ROB.location = s['pos']; ROB.rotation_euler = (0, 0, s['yaw']); ROB.scale = (s['scale'],) * 3
    for k in ('location', 'rotation_euler', 'scale'):                # спрятан: крошечный и под полом
        ROB.keyframe_insert(k, frame=f)
    for k in GR:
        GR[k].rotation_euler = (s[k], 0, 0); GR[k].keyframe_insert('rotation_euler', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#E8F4F9'))
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
CAM = LAY['camera']
AZ0 = math.radians(CAM.get('azimuth', 0))
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
k = LAY.get('light_scale', 1.0)
area('key', (-48, -56, 80), (0, 0, 8), 44, 95000 * k, '#FFE9CC')
area('fill', (64, -48, 34), (0, 0, 8), 38, 26000 * k, '#DDE8FF')
area('rim', (10, 64, 62), (0, 0, 12), 34, 32000 * k, '#FFF4E0')

tgt = empty('cam_target', tuple(CAM['target']))
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    az = AZ0 + SWING * math.sin(2 * math.pi * (f - 1) / FRAMES)
    T = Vector(CAM['target'])
    cam.location = T + Vector((DIST * math.cos(ELEV) * math.sin(az), -DIST * math.cos(ELEV) * math.cos(az), DIST * math.sin(ELEV)))
    cam.keyframe_insert('location', frame=f)

from bpy_extras import anim_utils
for idb in list(bpy.data.objects):
    ad = idb.animation_data
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
cy_.max_bounces = 4; cy_.diffuse_bounces = 2; cy_.glossy_bounces = 1; cy_.transmission_bounces = 2; cy_.transparent_max_bounces = 4
r.use_persistent_data = True
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'

def screens_json(path):
    """Углы трёх экранов в долях кадра (x слева, y сверху) на каждый кадр — для overlay.py."""
    out = {}
    corners = [Vector((-0.5, 0, 0.5)), Vector((0.5, 0, 0.5)), Vector((0.5, 0, -0.5)), Vector((-0.5, 0, -0.5))]   # TL TR BR BL
    for f in range(1, FRAMES + 1):
        scn.frame_set(f)
        fr = {}
        for name, sc in SCREENS.items():
            q = []
            for c in corners:
                v = world_to_camera_view(scn, cam, sc.matrix_world @ c)
                q.append([round(v.x, 6), round(1 - v.y, 6)])
            fr[name] = q
        out[f] = fr
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, 'w'))

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4]); cy_.samples = int(sys.argv[5])
    screens_json(os.path.join(HERE, 'frames', 'screens.json'))
    for f in map(int, sys.argv[2].split(',')):
        scn.frame_set(f)
        r.filepath = os.path.join(HERE, 'frames', f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    screens_json(os.path.join(HERE, 'frames', 'screens.json'))
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
