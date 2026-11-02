"""Рилс 1080×1920 к акции legobot.ru «Чёрная пятница 11.11 · 1+1=3», 21 с, 24 fps.
Скрипач (WeDo 2.0) и 3D-принтер (SPIKE Prime) опускаются на подставку («1», «+1»), падает коробка-подарок,
крышка подпрыгивает, коробка улетает вверх — из неё выезжает Змей Горыныч (SPIKE Essential, «=3») и
разворачивается на месте. Механика: Скрипач — как в hero3/kompl, принтер — scenes/spikeprinter,
Горыныч — два мотора крутят по колесу (дифференциальный привод), остальное едет вместе с корпусом.
Модели: MODEL_SKRIPACH, MODEL_PRINTER (секреты), gorynych.ldr — из legobot-stills/lesson_gorynych.
Тайминги и расстановка — layout.json. Экранные точки для подписей пишутся в frames/proj.json.
  python scene.py test 100,230,250,300,380 1080 1920 12
  python scene.py anim 1 504 1080 1920 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
HERE = os.path.dirname(os.path.abspath(__file__))
SC = os.path.join(HERE, '..')
sys.path.insert(0, os.path.join(SC, 'courier'))
import ldr

FPS, LOOP_S = 24, 21
FRAMES = FPS * LOOP_S                                   # 504
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
TL = LAY['timeline']
PL_H = LAY['plinth']['h']
def F(sec): return int(round(sec * FPS)) + 1

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

def mat(name, hexv, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    if coat:
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.12
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

def smooth(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def drop(obj, f0, h=48.0, dur=14, bounce=1.4):
    """объект висит за кадром, падает с ускорением и чуть подпрыгивает"""
    base = obj.location.copy()
    for f in range(1, FRAMES + 1):
        if f < f0:
            z = 400.0
        elif f < f0 + dur:
            t = (f - f0) / dur; z = h * (1 - t * t)
        else:
            u = (f - f0 - dur) / 9.0
            z = bounce * math.sin(math.pi * u) if u < 1 else 0.0
        obj.location = base + Vector((0, 0, z)); obj.keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ сцена из готового файла: без сброса, подставки, света и камеры
def run_scene(path, cut_plinth, override=None):
    src = open(path, encoding='utf-8').read()
    src = src.replace('bpy.ops.wm.read_factory_settings(use_empty=True)', 'pass')
    a = src.index(cut_plinth[0]); b = src.index(cut_plinth[1], a) + len(cut_plinth[1])
    src = src[:a] + src[b:]
    src = src[:src.index('# ------------------------------------------------------------------ свет, мир, камера')]
    if override:
        line = "LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))"
        src = src.replace(line, line + '\nLAY.update(OVERRIDE)', 1)
    before = set(bpy.data.objects)
    ns = {'__file__': path, '__name__': '__promo_part__', 'OVERRIDE': override or {}}
    exec(compile(src, path, 'exec'), ns)
    return [o for o in bpy.data.objects if o not in before and o.parent is None]

PLINTH = ('bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))',
          'bpy.context.active_object.is_shadow_catcher = True')

# ------------------------------------------------------------------ 3D-принтер (SPIKE Prime)
P = placement('printer')
for o in run_scene(os.path.join(SC, 'spikeprinter', 'scene.py'), PLINTH):
    o.parent = P
scn.render.fps = FPS; scn.frame_start, scn.frame_end = 1, FRAMES        # принтер ставит свою длину — вернуть 21 с

# ------------------------------------------------------------------ LDraw-помощники (как в kompl)
ldr.find('3001.dat')
COL = ldr.colours()
OVR = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 25: '#F07A12',
       10: '#4CC04A', 27: '#A5CA18', 322: '#3EB7E8', 34: '#3BAA4A', 79: '#EDEDE6', 191: '#F8B71B',
       2: '#3BAA4A', 14: '#F5CD2F', 19: '#D9BB7B', 43: '#AEE9EF', 46: '#F5CD2F', 36: '#E8432F'}
MATS = {}
def plastic(code):
    if code in MATS:
        return MATS[code]
    hexv = OVR.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = mat(f'pl_{code}', hexv, 0.3, coat=0.3)
    if COL.get(code, ('', ''))[0].startswith('Trans') and code != 79:
        b = m.node_tree.nodes['Principled BSDF']
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
    me = bpy.data.meshes.new('m_' + part.replace('.dat', '') + f'_{color}')
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

def read_lines(path):
    return [l for l in open(path, encoding='utf-8-sig', errors='ignore') if l.split()[:1] == ['1'] and len(l.split()) >= 15]

def bounds(lines):
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
    return Vector(lo), Vector(hi)

def add_part(k, line, parent, pivot, prefix):
    t = line.split(); c = int(t[1]); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
    o = bpy.data.objects.new(f'{prefix}_{k:03d}_{pid}', part_mesh(pid, c))
    bpy.context.collection.objects.link(o); o.parent = parent
    o.matrix_basis = Matrix.Translation(-pivot) @ ld_matrix([v[3:6], v[6:9], v[9:12]], v[0:3])
    return o

# ------------------------------------------------------------------ Скрипач (WeDo 2.0) — как в hero3/kompl
sk_lines = read_lines(os.path.join(HERE, 'models', 'skripach.ldr'))
GROUPS = {'crank': ([25, 26, 27, 28, 29], (100, -70, 0)), 'pinion': ([21, 22], (100, -30, 0)),
          'bow': ([30, 31], (100, -90, -70)), 'pivotc': ([32], (-60, -110, -70))}
owner = {i: g for g, (idx, _) in GROUPS.items() for i in idx}
lo, hi = bounds(sk_lines)
S = placement('skripach')
sk_body = empty('sk_body', Vector((0, 0, PL_H)) - Vector(((lo.x + hi.x) / 2, (lo.y + hi.y) / 2, lo.z)), S)
SK_TOP = hi.z - lo.z + PL_H
G = {'static': sk_body}
for g, (_, piv) in GROUPS.items():
    G[g] = empty('sk_' + g, ld2b(piv), sk_body)
for k, l in enumerate(sk_lines):
    g = owner.get(k, 'static')
    add_part(k, l, G[g], ld2b(GROUPS[g][1]) if g != 'static' else Vector((0, 0, 0)), 'sk')
ang = lambda p, q: math.atan2(q[1] - p[1], q[0] - p[0])
for f in range(1, FRAMES + 1):
    a = 2 * math.pi * 0.5 * (f - 1) / FPS                                   # кривошип 0,5 об/с
    G['crank'].rotation_euler = (0, a, 0)
    G['pinion'].rotation_euler = (0, -3 * a, 0)
    A = (100 + 20 * math.sin(a), -70 - 20 * math.cos(a))
    da = ang(A, (-60, -110)) - math.atan2(-20, -160)
    G['bow'].location = ld2b((A[0], A[1], -70)); G['bow'].rotation_euler = (0, da, 0)
    G['pivotc'].rotation_euler = (0, da, 0)
    for g in ('crank', 'pinion', 'bow', 'pivotc'):
        G[g].keyframe_insert('rotation_euler', frame=f); G[g].keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ коробка-подарок + Змей Горыныч (SPIKE Essential)
BOX = placement('box')                                   # здесь коробка падает; Горыныч — внутри неё
go_lines = read_lines(os.path.join(HERE, 'gorynych.ldr'))
WHEEL_PARTS = ('4185.dat', '2815.dat', '3705.dat')
def wheel_side(pid, v):
    if pid in WHEEL_PARTS or (pid == '3713.dat' and abs(v[1] - 30) < 1 and abs(v[2] - 20) < 1):
        return 1 if v[0] > 0 else -1
    return 0
R_WHEEL, HALF_TRACK = 38.0 / 20, 115.0 / 20              # шипы
AXLE = ld2b((0, 30, 20))                                 # середина оси колёс
GROUND = ld2b((0, 30 + 38, 20)).z                        # низ колёс
glo, ghi = bounds(go_lines)
GO = empty('go_root', (0, 0, 0), BOX)                    # точка разворота — середина оси, на подставке
go_body = empty('go_body', Vector((-AXLE.x, -AXLE.y, PL_H - GROUND)), GO)
WE = {s: empty(f'go_wheel{s}', Vector((s * HALF_TRACK, AXLE.y, AXLE.z)), go_body) for s in (1, -1)}
for k, l in enumerate(go_lines):
    t = l.split(); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
    s = wheel_side(pid, v)
    add_part(k, l, WE[s] if s else go_body, WE[s].location if s else Vector((0, 0, 0)), 'go')
# габарит Горыныча в системе go_root
gx0, gx1 = glo.x - AXLE.x, ghi.x - AXLE.x
gy0, gy1 = glo.y - AXLE.y, ghi.y - AXLE.y
GH = ghi.z - GROUND
GO_TOP = PL_H + GH

BX = LAY['box']; M = BX['margin']; T = BX['wall']
bw, bd, bh = (gx1 - gx0) + 2 * M, (gy1 - gy0) + 2 * M, GH + M
bcx, bcy = (gx0 + gx1) / 2, (gy0 + gy1) / 2
M_BOX = mat('box', BX['color'], 0.28, coat=0.5)
M_RIB = mat('ribbon', BX['ribbon'], 0.35, coat=0.4)
def cube(name, cx, cy, cz, sx, sy, sz, m, parent, bevel=0.12):
    bpy.ops.mesh.primitive_cube_add(size=1, location=(cx, cy, cz))
    o = bpy.context.active_object; o.name = name; o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    if bevel:
        md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = 3
    o.data.materials.append(m)
    for pg in o.data.polygons:
        pg.use_smooth = True
    o.parent = parent
    return o
SHELL = empty('box_shell', (bcx, bcy, 0), BOX)
z0 = PL_H; zc = z0 + bh / 2
cube('wall_f', 0, -bd / 2 + T / 2, zc, bw, T, bh, M_BOX, SHELL)
cube('wall_b', 0, bd / 2 - T / 2, zc, bw, T, bh, M_BOX, SHELL)
cube('wall_l', -bw / 2 + T / 2, 0, zc, T, bd - 2 * T, bh, M_BOX, SHELL)
cube('wall_r', bw / 2 - T / 2, 0, zc, T, bd - 2 * T, bh, M_BOX, SHELL)
RW = BX['ribbon_w']
cube('rib_f', 0, -bd / 2 - 0.05, zc, RW, 0.2, bh, M_RIB, SHELL, 0.04)
cube('rib_b', 0, bd / 2 + 0.05, zc, RW, 0.2, bh, M_RIB, SHELL, 0.04)
cube('rib_l', -bw / 2 - 0.05, 0, zc, 0.2, RW, bh, M_RIB, SHELL, 0.04)
cube('rib_r', bw / 2 + 0.05, 0, zc, 0.2, RW, bh, M_RIB, SHELL, 0.04)
LID = empty('box_lid', (bcx, bcy, z0 + bh), BOX)
LH = BX['lid_h']; lw, ld_ = bw + 0.6, bd + 0.6
cube('lid', 0, 0, LH / 2, lw, ld_, LH, M_BOX, LID)
cube('lid_rx', 0, 0, LH / 2, RW, ld_ + 0.1, LH + 0.12, M_RIB, LID, 0.04)
cube('lid_ry', 0, 0, LH / 2, lw + 0.1, RW, LH + 0.12, M_RIB, LID, 0.04)
# шипы на крышке — как у детали LEGO
nx, ny = int(lw), int(ld_)
for i in range(nx):
    for j in range(ny):
        x = (i - (nx - 1) / 2); y = (j - (ny - 1) / 2)
        if abs(x) < RW / 2 + 0.3 or abs(y) < RW / 2 + 0.3:
            continue
        bpy.ops.mesh.primitive_cylinder_add(vertices=16, radius=0.3, depth=0.2, location=(x, y, LH + 0.1))
        st = bpy.context.active_object; st.data.materials.append(M_BOX); st.parent = LID
# бант: две петли и узел
for s in (-1, 1):
    bpy.ops.mesh.primitive_torus_add(major_radius=1.25, minor_radius=0.32, location=(s * 1.15, 0, LH + 1.0),
                                     rotation=(math.radians(90), 0, math.radians(s * 18)))
    bw_ = bpy.context.active_object; bw_.data.materials.append(M_RIB); bw_.parent = LID
bpy.ops.mesh.primitive_uv_sphere_add(radius=0.55, location=(0, 0, LH + 0.75))
kn = bpy.context.active_object; kn.data.materials.append(M_RIB); kn.parent = LID

# ------------------------------------------------------------------ анимация: падения, подарок, Горыныч
drop(S, F(TL['skripach_drop']))
drop(P, F(TL['printer_drop']))
drop(BOX, F(TL['box_drop']), h=52.0, bounce=1.8)
f_pop, f_up = F(TL['lid_pop']), F(TL['shell_up'])
lid0, sh0 = LID.location.copy(), SHELL.location.copy()
for f in range(1, FRAMES + 1):
    # крышка: подпрыгивает, на миг зависает и улетает вверх, вращаясь
    u = (f - f_pop) / 24.0
    if u <= 0:
        dz, rx, rz = 0.0, 0.0, 0.0
    else:
        dz = 7.0 * math.sin(math.pi * min(u, 0.5)) + max(0.0, u - 0.35) ** 2 * 160
        rx = math.radians(-14) * min(1.0, u * 2); rz = math.radians(150) * max(0.0, u - 0.3)
    LID.location = lid0 + Vector((0, 0, dz)); LID.rotation_euler = (rx, 0, rz)
    LID.keyframe_insert('location', frame=f); LID.keyframe_insert('rotation_euler', frame=f)
    # стенки: уезжают вверх и уменьшаются
    w = (f - f_up) / 18.0
    if w <= 0:
        SHELL.location = sh0; SHELL.scale = (1, 1, 1)
    else:
        e = smooth(w)
        SHELL.location = sh0 + Vector((0, 0, 70 * e * e)); k = 1 - 0.45 * e; SHELL.scale = (k, k, k)
    SHELL.keyframe_insert('location', frame=f); SHELL.keyframe_insert('scale', frame=f)

def trap(t, T_, L):
    """путь при разгоне–движении–торможении: 0..L за время T_ (с), разгон/торможение по 0,3 с"""
    r = 0.3; v = L / (T_ - r)
    t = max(0.0, min(T_, t))
    if t < r: return 0.5 * v * t * t / r
    if t < T_ - r: return 0.5 * v * r + v * (t - r)
    tt = T_ - t; return L - 0.5 * v * tt * tt / r
d0, d1 = TL['drive']; t0, t1 = TL['turn']; DIST = TL['drive_dist']
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    s = trap(t - d0, d1 - d0, DIST)                       # путь вперёд (к камере, −Y)
    ph = trap(t - t0, t1 - t0, 2 * math.pi)                # разворот на месте на 360°
    GO.location = (0, -s, 0); GO.rotation_euler = (0, 0, ph)
    sP = s - ph * HALF_TRACK; sM = s + ph * HALF_TRACK     # путь правого и левого колеса
    WE[1].rotation_euler = (sP / R_WHEEL, 0, 0); WE[-1].rotation_euler = (sM / R_WHEEL, 0, 0)
    GO.keyframe_insert('location', frame=f); GO.keyframe_insert('rotation_euler', frame=f)
    WE[1].keyframe_insert('rotation_euler', frame=f); WE[-1].keyframe_insert('rotation_euler', frame=f)

# ------------------------------------------------------------------ подставка, ловец теней, мир
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
cam_d.sensor_fit = 'HORIZONTAL'; cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
ELEV, AZ = math.radians(CAM['elev']), math.radians(CAM.get('azimuth', 0))
for f in range(1, FRAMES + 1):
    D = CAM['dist0'] + (CAM['dist1'] - CAM['dist0']) * smooth((f - 1) / (FRAMES - 1))   # медленный наезд
    Tg = Vector(CAM['target'])
    cam.location = Tg + Vector((D * math.cos(ELEV) * math.sin(AZ), -D * math.cos(ELEV) * math.cos(AZ), D * math.sin(ELEV)))
    cam.keyframe_insert('location', frame=f)

from bpy_extras import anim_utils
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
print('objects', len(bpy.data.objects), '| gorynych parts', len(go_lines), '| box', round(bw, 1), round(bd, 1), round(bh, 1))

def write_proj(path, w, h):
    """экранные точки (0..1, y сверху) над моделями — для подписей overlay.py"""
    r.resolution_x, r.resolution_y = w, h
    anchors = {'sk': (S, SK_TOP + 3.0), 'pr': (P, 30.0), 'box': (BOX, None), 'go': (GO, GO_TOP + 2.0)}
    out = {}
    for f in range(1, FRAMES + 1, 2):
        scn.frame_set(f); rec = {}
        for key, (ob, top) in anchors.items():
            if key == 'box':
                p = LID.matrix_world.translation + Vector((0, 0, 3.0))
            else:
                p = ob.matrix_world.translation.copy(); p.z = top
            v = world_to_camera_view(scn, cam, p)
            rec[key] = [round(v.x, 4), round(1 - v.y, 4)]
        out[str(f)] = rec
    os.makedirs(os.path.dirname(path), exist_ok=True)
    json.dump(out, open(path, 'w'))

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
OUT = os.path.join(HERE, 'frames')
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4]); cy_.samples = int(sys.argv[5])
    write_proj(os.path.join(OUT, 'proj.json'), r.resolution_x, r.resolution_y)
    for f in map(int, sys.argv[2].split(',')):
        scn.frame_set(f)
        r.filepath = os.path.join(OUT, f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy_.samples = int(sys.argv[6])
    write_proj(os.path.join(OUT, 'proj.json'), r.resolution_x, r.resolution_y)
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(OUT, 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
