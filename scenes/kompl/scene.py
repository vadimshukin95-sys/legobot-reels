"""Видео-петля 18 с для страницы «Комплекты и акции» (/kompl) на legobot.ru: витрина из трёх моделей разных наборов.
Слева Скрипач (WeDo 2.0) водит смычком, в центре 3D-принтер (SPIKE Prime) печатает рамку, справа Робостроитель (EV3)
на месте поднимает и ставит кубик. Модели и их механика берутся из готовых сцен:
  принтер — scenes/spikeprinter/scene.py, Робостроитель — scenes/ev3robo/scene.py (выполняются здесь без своих подставок,
  света и камеры, а потом ставятся на общую подставку), Скрипач — как в scenes/hero3/scene.py.
Расстановка, подставка и камера — layout.json. Модели — секреты MODEL_SKRIPACH, MODEL_PRINTER, MODEL_ROBO.
  python scene.py test 1,100,220,330 1280 800 12
  python scene.py anim 1 432 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(SC, 'courier'))
import ldr

FPS, LOOP_S = 24, 18
FRAMES = FPS * LOOP_S                                   # 432
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
PL_H = LAY['plinth']['h']

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

def mat(name, hexv, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    return m

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o

def placement(key):
    p = LAY['models'][key]
    o = empty('place_' + key, (p['at'][0], p['at'][1], 0))
    o.rotation_euler = (0, 0, -math.radians(p['yaw']))
    return o

# ------------------------------------------------------------------ сцена из готового файла: без сброса, подставки, света и камеры
def run_scene(path, cut_plinth, override=None):
    src = open(path, encoding='utf-8').read()
    src = src.replace('bpy.ops.wm.read_factory_settings(use_empty=True)', 'pass')
    a = src.index(cut_plinth[0]); b = src.index(cut_plinth[1], a) + len(cut_plinth[1])
    src = src[:a] + src[b:]                                                  # без своей подставки и ловца теней
    src = src[:src.index('# ------------------------------------------------------------------ свет, мир, камера')]
    if override:
        line = "LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))"
        src = src.replace(line, line + '\nLAY.update(OVERRIDE)', 1)
    before = set(bpy.data.objects)
    ns = {'__file__': path, '__name__': '__kompl_part__', 'OVERRIDE': override or {}}
    exec(compile(src, path, 'exec'), ns)
    return [o for o in bpy.data.objects if o not in before and o.parent is None]

PLINTH = ('bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))',
          'bpy.context.active_object.is_shadow_catcher = True')

# 3D-принтер (SPIKE Prime) — как на странице SPIKE Prime
P = placement('printer')
for o in run_scene(os.path.join(SC, 'spikeprinter', 'scene.py'), PLINTH):
    o.parent = P

# Робостроитель (EV3) — на месте: без езды, два раза берёт кубик, поднимает, держит и ставит обратно
R = placement('robo')
for o in run_scene(os.path.join(SC, 'ev3robo', 'scene.py'), PLINTH, LAY['robo_override']):
    o.parent = R

# ------------------------------------------------------------------ Скрипач (WeDo 2.0) — как в hero3
ldr.find('3001.dat')
COL = ldr.colours()
OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 25: '#F07A12',
            10: '#4CC04A', 27: '#A5CA18', 322: '#3EB7E8', 34: '#3BAA4A', 79: '#EDEDE6', 191: '#F8B71B',
            2: '#3BAA4A', 14: '#F5CD2F', 19: '#D9BB7B', 43: '#AEE9EF', 46: '#F5CD2F', 36: '#E8432F'}
MATS = {}
def plastic(code):
    if code in MATS:
        return MATS[code]
    hexv = OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'sk_{code}'); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv)
    b.inputs['Roughness'].default_value = 0.3
    b.inputs['Coat Weight'].default_value = 0.3
    b.inputs['Coat Roughness'].default_value = 0.12
    if COL.get(code, ('', ''))[0].startswith('Trans') and code != 79:
        b.inputs['Transmission Weight'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.12
    MATS[code] = m
    return m

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
    me = bpy.data.meshes.new('sk_' + part.replace('.dat', '') + f'_{color}')
    me.from_pydata(verts, [], faces)
    for c in codes:
        me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats)
    me.update(); me.shade_smooth(); me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me
    return me

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def ld_matrix(Rm, pos):
    return Matrix.Translation(ld2b(pos)) @ (C @ Matrix(Rm) @ C.transposed()).to_4x4()

lines = [l for l in open(os.path.join(HERE, 'models', 'skripach.ldr'), encoding='utf-8-sig', errors='ignore')
         if l.split()[:1] == ['1'] and len(l.split()) >= 15]
GROUPS = {'crank': ([25, 26, 27, 28, 29], (100, -70, 0)), 'pinion': ([21, 22], (100, -30, 0)),
          'bow': ([30, 31], (100, -90, -70)), 'pivotc': ([32], (-60, -110, -70))}
owner = {i: g for g, (idx, _) in GROUPS.items() for i in idx}
lo = [1e9] * 3; hi = [-1e9] * 3
for l in lines:
    t = l.split(); v = list(map(float, t[2:14])); bb = ldr.bbox(' '.join(t[14:]))
    if not bb:
        continue
    for cx in (0, 1):
        for cy in (0, 1):
            for cz in (0, 1):
                w = ld_matrix([v[3:6], v[6:9], v[9:12]], v[0:3]) @ Vector((bb[cx][0], bb[cy][1], bb[cz][2]))
                for i in range(3):
                    lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
S = placement('skripach')
body = empty('sk_body', Vector((0, 0, PL_H)) - centre, S)
G = {'static': body}
for g, (_, piv) in GROUPS.items():
    G[g] = empty('sk_' + g, ld2b(piv), body)
for k, l in enumerate(lines):
    t = l.split(); c = int(t[1]); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
    g = owner.get(k, 'static')
    o = bpy.data.objects.new(f'sk_{k:03d}_{pid}', part_mesh(pid, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    piv = ld2b(GROUPS[g][1]) if g != 'static' else Vector((0, 0, 0))
    o.matrix_basis = Matrix.Translation(-piv) @ ld_matrix([v[3:6], v[6:9], v[9:12]], v[0:3])
ang = lambda p, q: math.atan2(q[1] - p[1], q[0] - p[0])
for f in range(1, FRAMES + 1):
    a = 2 * math.pi * 0.5 * (f - 1) / FPS                                   # кривошип 0,5 об/с: 9 оборотов за петлю
    G['crank'].rotation_euler = (0, a, 0)
    G['pinion'].rotation_euler = (0, -3 * a, 0)
    A = (100 + 20 * math.sin(a), -70 - 20 * math.cos(a))
    da = ang(A, (-60, -110)) - math.atan2(-20, -160)
    G['bow'].location = ld2b((A[0], A[1], -70)); G['bow'].rotation_euler = (0, da, 0)
    G['pivotc'].rotation_euler = (0, da, 0)
    for g in ('crank', 'pinion', 'bow', 'pivotc'):
        G[g].keyframe_insert('rotation_euler', frame=f); G[g].keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ общая подставка, ловец теней, мир
bpy.ops.mesh.primitive_cylinder_add(vertices=160, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth']['color'], 0.55))
bpy.ops.mesh.primitive_plane_add(size=600, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY['world'])
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6

# ------------------------------------------------------------------ свет и камера
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
k = LAY.get('light_scale', 1.0)
area('key', (-48, -56, 80), (0, 0, 8), 44, 95000 * k, '#FFE9CC')
area('fill', (64, -48, 34), (0, 0, 8), 38, 26000 * k, '#DDE8FF')
area('rim', (10, 64, 62), (0, 0, 12), 34, 32000 * k, '#FFF4E0')
CAM = LAY['camera']
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', tuple(CAM['target']))
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    az = math.radians(CAM.get('azimuth', 0)) + SWING * math.sin(2 * math.pi * (f - 1) / FRAMES)
    T = Vector(CAM['target'])
    cam.location = T + Vector((DIST * math.cos(ELEV) * math.sin(az), -DIST * math.cos(ELEV) * math.cos(az), DIST * math.sin(ELEV)))
    cam.keyframe_insert('location', frame=f)

from bpy_extras import anim_utils                        # все кривые линейные: петля без замедлений на стыке
for idb in list(bpy.data.objects) + list(bpy.data.curves) + list(bpy.data.materials):
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
print('objects', len(bpy.data.objects))

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
