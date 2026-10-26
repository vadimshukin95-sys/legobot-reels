"""«Скрипач» — виолончелист на LEGO WeDo 2.0 (45300). Рилс LEGObot, прогрев перед курсом по WeDo 2.0.
Механизм: мотор -> шестерня 8z -> 24z на оси кривошипа (i = 3) -> шкив-кривошип с пальцем ->
смычок (ось 10) висит на пальце и скользит сквозь «кисть» — соединитель, качающийся на запястье.
Модель — из конвейера инструкций (legobot-wedo-pipeline/models/skripach), model.json при theta = 0;
подвижные детали считаются здесь же по тем же формулам (kin).
Фон: стол педагога (дуб), стена, школьная доска с нотами (tex/board.png, make_tex.py), окно слева.
1 unit = 1 stud, Z вверх, музыкант смотрит в -Y.
  python scene.py test 30,150,300,400,480 540 960 10
  python scene.py anim 1 528 1080 1920 16
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
sys.argv = sys.argv[:1]
exec(open(os.path.join(HERE, '_common.py')).read())
from mathutils import Matrix, Vector, Quaternion
from bpy_extras.object_utils import world_to_camera_view

TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FRAMES = TL['frames']
scn.frame_start, scn.frame_end = 1, FRAMES

def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------ скорость кривошипа (об/с) и угол по кадрам
SP = TL['speed']
def rev_s(f):
    for (f0, v0), (f1, v1) in zip(SP, SP[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * ease((f - f0) / max(1, f1 - f0))
    return SP[-1][1]
THETA = {1: 25.0}
for f in range(2, FRAMES + 2):
    THETA[f] = THETA[f - 1] + rev_s(f) * 360.0 / FPS

# ------------------------------------------------ кинематика (LDraw: LDU, Y вниз, вперёд = -Z) — как в model.py
XK, YK, ZM, R_CRANK, ZB = 100.0, -70.0, 0.0, 20.0, -70.0
HX, HY = -60.0, -110.0
def rx(d):
    r = math.radians(d); c, s = math.cos(r), math.sin(r); return Matrix(((1, 0, 0), (0, c, -s), (0, s, c)))
def ry(d):
    r = math.radians(d); c, s = math.cos(r), math.sin(r); return Matrix(((c, 0, s), (0, 1, 0), (-s, 0, c)))
def rz(d):
    r = math.radians(d); c, s = math.cos(r), math.sin(r); return Matrix(((c, -s, 0), (s, c, 0), (0, 0, 1)))
AXZ = ry(-90)
CONN = Matrix(((0, 0, 1), (0, -1, 0), (1, 0, 0)))       # np.column_stack([[0,0,1],[0,-1,0],[1,0,0]]) — симметрична
def kin(th):
    t = math.radians(th)
    P = (XK + R_CRANK * math.cos(t), YK - R_CRANK * math.sin(t))
    dx, dy = P[0] - HX, P[1] - HY
    return P, math.atan2(dy, dx)
def moving(th):
    """note -> (pos, rot) LDraw для подвижных деталей"""
    P, al = kin(th)
    u = (math.cos(al), math.sin(al))
    Rz = rz(math.degrees(al))
    return {
        'ось 2': ((XK, -30, ZM - 20), rz(3 * th) @ AXZ),
        'шестерня 8z': ((XK, -30, ZM - 30), rz(22.5 + 3 * th)),
        'ось 6 (кривошип)': ((XK, YK, ZM), rz(-th) @ AXZ),
        'втулка': ((XK, YK, ZM + 30), rz(-th)),
        'шестерня 24z': ((XK, YK, ZM - 30), rz(-th)),
        'шкив-кривошип': ((XK, YK, ZB + 15), rz(90 - th)),
        'палец кривошипа': ((P[0], P[1], ZB + 10), AXZ),
        'соединитель на кривошипе': ((P[0], P[1], ZB), Rz @ CONN),
        'смычок (ось 10)': ((P[0] - 110 * u[0], P[1] - 110 * u[1], ZB), Rz),
        'кисть (соединитель №1)': ((HX, HY, ZB), Rz @ rx(180)),
    }

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld_mat(rot, pos):
    R = C @ Matrix(rot) @ C.transposed()
    return Matrix.Translation(C @ (Vector(pos) / 20.0)) @ R.to_4x4()
def b(pos):
    return C @ (Vector(pos) / 20.0)

parts = json.load(open(os.path.join(HERE, 'model.json'), encoding='utf-8'))
MODEL, MOV = [], {}
DYN = set(moving(0).keys())
for p in parts:
    o = bpy.data.objects.new(p['note'], part_mesh(p['part'], p['color']))
    bpy.context.collection.objects.link(o)
    o.matrix_world = ld_mat(p['rot'], p['pos'])
    MODEL.append(o)
    if p['note'] in DYN:
        o.rotation_mode = 'QUATERNION'
        MOV[p['note']] = o
    if p['group'] == 'hub':
        HUB = p
assert len(MOV) == len(DYN), (len(MOV), DYN - set(MOV))
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in MODEL for c in o.bound_box]
LO = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
HI = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
Z0 = LO.z
print('model bbox', tuple(round(v, 2) for v in LO), tuple(round(v, 2) for v in HI))

# анимация подвижных деталей: позиция + кватернион с непрерывным знаком
prevq = {}
for f in range(1, FRAMES + 1):
    for note, (pos, rot) in moving(THETA[f]).items():
        o = MOV[note]
        M = ld_mat(rot, pos)
        loc, q, _ = M.decompose()
        if note in prevq and prevq[note].dot(q) < 0:
            q = -q
        prevq[note] = q
        o.location = loc; o.rotation_quaternion = q
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_quaternion', frame=f)

# ------------------------------------------------ провод мотора к хабу (на столе, за моделью)
CABLE_M = bpy.data.materials.new('cable'); CABLE_M.use_nodes = True
_cb = CABLE_M.node_tree.nodes['Principled BSDF']
_cb.inputs['Base Color'].default_value = lin('#1E1F22'); _cb.inputs['Roughness'].default_value = 0.45
def cable(name, pts, r=0.13):
    cd = bpy.data.curves.new(name, 'CURVE'); cd.dimensions = '3D'
    cd.bevel_depth = r; cd.bevel_resolution = 4
    spl = cd.splines.new('BEZIER'); spl.bezier_points.add(len(pts) - 1)
    for bp, q in zip(spl.bezier_points, pts):
        bp.co = q; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cd); bpy.context.collection.objects.link(o)
    o.data.materials.append(CABLE_M)
    return o
def obox(o):
    ps = [o.matrix_world @ Vector(c) for c in o.bound_box]
    return Vector([min(p[i] for p in ps) for i in range(3)]), Vector([max(p[i] for p in ps) for i in range(3)])
_ml, _mh = obox(next(o for o in MODEL if o.name.startswith('мотор')))
_hl, _hh = obox(next(o for o in MODEL if o.name.startswith('смартхаб')))
MOT = Vector(((_ml.x + _mh.x) / 2, _mh.y, (_ml.z + _mh.z) / 2))        # задний торец мотора
HUBB = Vector(((_hl.x + _hh.x) / 2 + 1.0, _hh.y, _hh.z - 1.2))        # задний торец хаба (порты)
print('motor back', tuple(round(v, 2) for v in MOT), 'hub back', tuple(round(v, 2) for v in HUBB))
TZ = Z0 + 0.13
cable('cable_motor', [MOT, MOT + Vector((0, 1.6, -0.8)), Vector((MOT.x, MOT.y + 4.0, TZ)),
                      Vector((HUBB.x + 2.5, HUBB.y + 3.0, TZ)), Vector((HUBB.x + 1.0, HUBB.y + 1.2, HUBB.z - 0.6)), HUBB])

# ------------------------------------------------ живой пластик (как в «Дверях»)
for m in list(bpy.data.materials):
    if not m.name.startswith('ld_'):
        continue
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = N['Principled BSDF']
    base = bs.inputs['Roughness'].default_value
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 8
    L.new(tc.outputs['Object'], nz.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = base * 0.7; mr.inputs['To Max'].default_value = base * 1.5
    L.new(nz.outputs['Fac'], mr.inputs['Value']); L.new(mr.outputs['Result'], bs.inputs['Roughness'])

def mat(name, hexv, rough=0.5, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = lin(hexv); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Coat Weight'].default_value = coat
    return m

# ------------------------------------------------ кабинет: дубовый стол, стена, доска, окно слева, полка
def box(name, x0, x1, y0, y1, z0, z1, m, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name; o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(m)
    if bevel:
        bm_ = o.modifiers.new('bev', 'BEVEL'); bm_.width = bevel; bm_.segments = 3
    return o
def mat_wood():
    m = bpy.data.materials.new('oak'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = N['Principled BSDF']; bs.inputs['Roughness'].default_value = 0.42; bs.inputs['Coat Weight'].default_value = 0.15
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    tex = os.path.join(HERE, 'tex', 'oak_veneer_01_diff_2k.jpg')
    if os.path.exists(tex):
        mp.inputs['Scale'].default_value = (0.045, 0.045, 1.0)
        mp.inputs['Rotation'].default_value = (0, 0, math.radians(90))
        im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(tex)
        L.new(mp.outputs['Vector'], im.inputs['Vector'])
        hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Value'].default_value = 1.2
        L.new(im.outputs['Color'], hsv.inputs['Color']); L.new(hsv.outputs['Color'], bs.inputs['Base Color'])
    else:
        mp.inputs['Scale'].default_value = (0.08, 1.2, 1.0)
        wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.5; wv.inputs['Distortion'].default_value = 6
        L.new(mp.outputs['Vector'], wv.inputs['Vector'])
        cr = N.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = lin('#B88A5A'); cr.color_ramp.elements[1].color = lin('#D9B48A')
        L.new(wv.outputs['Fac'], cr.inputs['Fac']); L.new(cr.outputs['Color'], bs.inputs['Base Color'])
    return m
def mat_image(name, path, rough=0.85, value=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    bs = N['Principled BSDF']; bs.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord')
    im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(path); im.extension = 'CLIP'
    L.new(tc.outputs['UV'], im.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Value'].default_value = value
    L.new(im.outputs['Color'], hsv.inputs['Color']); L.new(hsv.outputs['Color'], bs.inputs['Base Color'])
    return m
def plane(name, x0, x1, y, z0, z1, m):
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x0, y, z0), (x1, y, z0), (x1, y, z1), (x0, y, z1)], [], [(0, 1, 2, 3)])
    uv = me.uv_layers.new()
    for li, (u_, v_) in zip(range(4), ((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[li].uv = (u_, v_)
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m)
    return o

YW = 44.0                                                # стена
box('table', -60, 60, -70, 30, Z0 - 1.2, Z0, mat_wood(), bevel=0.15)
box('floor_far', -300, 300, -300, 300, Z0 - 30, Z0 - 29, mat('floor', '#8D857A', 0.8))
box('wall', -300, 300, YW, YW + 1, Z0 - 30, Z0 + 120, mat('wall', '#E8E3DA', 0.9))
BW, BH = 64.0, 34.7                                      # доска 2400x1300 px
plane('board', -BW / 2 + 4, BW / 2 + 4, YW - 0.3, Z0 + 10, Z0 + 10 + BH, mat_image('board', os.path.join(HERE, 'tex', 'board.png'), 0.9, 1.15))
box('board_ledge', -BW / 2 + 4, BW / 2 + 4, YW - 2.0, YW - 0.2, Z0 + 9.2, Z0 + 10.0, mat('ledge', '#A0764A', 0.6))
# окно слева (в расфокусе)
WIN = bpy.data.materials.new('window'); WIN.use_nodes = True
_wn = WIN.node_tree.nodes; _wl = WIN.node_tree.links
_em = _wn.new('ShaderNodeEmission'); _em.inputs['Color'].default_value = lin('#EAF3FF'); _em.inputs['Strength'].default_value = 4.0
_wl.new(_em.outputs['Emission'], _wn['Material Output'].inputs['Surface'])
box('window', -78, -40, YW - 0.2, YW + 0.2, Z0 + 6, Z0 + 46, WIN)
FRAME = mat('frame', '#F4F4F2', 0.5)
for x in (-78, -59, -40):
    box('wframe', x - 0.7, x + 0.7, YW - 0.5, YW - 0.1, Z0 + 6, Z0 + 46, FRAME)
for z in (6, 26, 46):
    box('wframe', -78.7, -39.3, YW - 0.5, YW - 0.1, Z0 + z - 0.7, Z0 + z + 0.7, FRAME)
# полка справа с коробками наборов
SH = mat('shelf', '#C9B79C', 0.6)
import random
random.seed(3)
for z in (12, 26):
    box('shelf', 40, 72, YW - 7, YW - 0.4, Z0 + z - 0.5, Z0 + z, SH)
    x = 41.0
    while x < 70:
        w = random.uniform(3.0, 5.5); h = random.uniform(5.0, 8.5)
        col = random.choice(['#F2B33D', '#4CB2E6', '#E85A4F', '#8CC63F', '#F4F1EA'])
        box('kit', x, x + w, YW - 6, YW - 1, Z0 + z, Z0 + z + h, mat('k' + col, col, 0.45))
        x += w + random.uniform(0.3, 0.9)

# ------------------------------------------------ свет
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F2EEE6')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(4); sun.color = lin('#FFF0DC')[:3]
so = bpy.data.objects.new('sun', sun); bpy.context.collection.objects.link(so)
so.rotation_euler = (Vector((0, 0, 0)) - Vector((-30, 40, 38))).to_track_quat('-Z', 'Y').to_euler()
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power
    ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.visible_camera = False
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
MC = (LO + HI) / 2
area('window_soft', (-32, 26, Z0 + 22), (MC.x, MC.y, Z0 + 4), 26, 9000, '#EEF4FF')
area('fill', (16, -34, Z0 + 18), (MC.x, MC.y, Z0 + 4), 20, 4200, '#FFF2E2')
area('rim', (10, 30, Z0 + 26), (MC.x, MC.y, Z0 + 6), 14, 3000, '#FFF4E0')

# ------------------------------------------------ камера: планы заданы как в эскизах (цель LDraw, дистанция LDU, широта, долгота)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.sensor_fit = 'AUTO'
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6
LENS = 18 / math.tan(math.radians(15))                   # вертикальный угол 30°, как в эскизах
SHOT = {   # цель (LDraw), дистанция LDU, широта, долгота, фокус (LDraw)
    'hero':  ((15, -150, 40), 1080, 12, -28, (20, -110, -40)),
    'orbit': ((30, -140, 20), 1000, 12, 22, (60, -90, -40)),
    'gears': ((100, -48, -40), 330, 3, 28, (100, -50, -30)),
    'crank': ((30, -95, -60), 650, 4, -5, (40, -90, -70)),
    'wide':  ((15, -150, 40), 1080, 12, -15, (20, -110, -40)),
    'end':   ((15, -150, 40), 1250, 14, -20, (20, -110, -40)),
}
SEQ = TL['shots']; BLEND = TL['blend']
def shot_at(f):
    cur = SEQ[0][1]; w = 1.0; prev = cur
    for i, (fs, nm) in enumerate(SEQ):
        if f >= fs:
            prev = SEQ[i - 1][1] if i else nm; cur = nm
            w = ease((f - fs) / BLEND) if i else 1.0
    a, bb = SHOT[prev], SHOT[cur]
    lerp = lambda x, y: x + (y - x) * w
    tg = Vector(a[0]).lerp(Vector(bb[0]), w); dist = lerp(a[1], bb[1]); lat = lerp(a[2], bb[2]); lon = lerp(a[3], bb[3])
    fo = Vector(a[4]).lerp(Vector(bb[4]), w)
    la, lo = math.radians(lat), math.radians(lon)
    d = Vector((math.sin(lo) * math.cos(la), -math.sin(la), -math.cos(lo) * math.cos(la)))
    return b(tg + d * dist), b(tg), b(fo)
def shake(f, amp):
    t = f / 24.0
    return Vector((amp * (math.sin(t * 2.1) * 0.6 + math.sin(t * 5.3 + 1.0) * 0.25),
                   amp * (math.sin(t * 1.7 + 2.0) * 0.4 + math.sin(t * 6.1) * 0.15),
                   amp * (math.sin(t * 2.6 + 0.5) * 0.5 + math.sin(t * 7.9 + 3.0) * 0.18)))
cam_d.lens = LENS
for f in range(1, FRAMES + 1):
    co, to, fp = shot_at(f)
    cam.location = co + shake(f, 0.06); cam.keyframe_insert('location', frame=f)
    tgt.location = to + shake(f + 400, 0.025); tgt.keyframe_insert('location', frame=f)
    cam_d.dof.focus_distance = (co - fp).length; cam_d.dof.keyframe_insert('focus_distance', frame=f)

# ------------------------------------------------ рендер
r = scn.render
r.engine = 'CYCLES'
cy = scn.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.04
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 2
cy.transmission_bounces = 4; cy.transparent_max_bounces = 16
r.use_persistent_data = True
r.use_motion_blur = True; r.motion_blur_shutter = 0.25
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'

def write_proj(frames):
    """экранные точки для подписей: путь пальца кривошипа, дуги-стрелки шестерён, кисть"""
    r.resolution_x, r.resolution_y = 1080, 1920
    res = {}
    for f in frames:
        scn.frame_set(f)
        pr = lambda v: [round(x, 4) for x in list(world_to_camera_view(scn, cam, v))[:2]]
        th = THETA[f]
        P, al = kin(th)
        d = {'pin': pr(b((P[0], P[1], ZB - 12))),
             'circle': [pr(b((XK + R_CRANK * math.cos(a), YK - R_CRANK * math.sin(a), ZB - 12)))
                        for a in [2 * math.pi * k / 40 for k in range(41)]],
             'hand': pr(b((HX, HY, ZB - 12)))}
        c24 = Vector((XK, YK, -30.0)); c8 = Vector((XK, -30.0, -30.0))
        d['arc24'] = [pr(b(c24 + rz(-t) @ Vector((40.0, 0, 0)))) for t in range(40, 141, 5)]      # над 24z, по ходу вращения
        d['arc8'] = [pr(b(c8 + rz(t) @ Vector((17.0, 0, 0)))) for t in range(20, 161, 8)]          # под 8z, навстречу
        res[f] = d
    old = {}
    pj = os.path.join(HERE, 'proj.json')
    if os.path.exists(pj):
        old = json.load(open(pj))
    old.update({str(k): v for k, v in res.items()})
    json.dump(old, open(pj, 'w'))

mode = ARGS[0] if ARGS else 'test'
if mode == 'test':
    frames = list(map(int, ARGS[1].split(',')))
    write_proj(frames)
    r.resolution_x, r.resolution_y = int(ARGS[2]), int(ARGS[3])
    cy.samples = int(ARGS[4])
    for f in frames:
        scn.frame_set(f)
        r.filepath = os.path.join(HERE, 'frames', f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(ARGS[1]), int(ARGS[2])
    write_proj(range(s, e + 1))
    r.resolution_x, r.resolution_y = int(ARGS[3]), int(ARGS[4])
    cy.samples = int(ARGS[5])
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
elif mode == 'save':
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'skripach.blend'))
