"""«Двери супермаркета» — WeDo 2.0 (45300), реечная передача. Рилс LEGObot, реалистичная версия.
Модель целиком, как на занятии: хаб, провода, светодиод хаба (синий -> зелёный, пока дверь работает).
Стол из дуба в кабинете: окно слева, полка с наборами, мягкий дневной свет, камера «с рук», перевод фокуса.
Сюжет: ладонь у датчика → мотор крутит шестерню 8z → рейки на балке двери едут → дверь открывается,
ладонь ушла → 3 с → дверь закрывается.
Модель — из конвейера инструкций (legobot-wedo-pipeline/models/dveri), model_t000.json (дверь закрыта).
1 unit = 1 stud, Z вверх, фасад смотрит в -Y.
  python scene.py test 1,90,140,300 540 960 8
  python scene.py anim 1 420 1080 1920 16      (+ пишет proj.json для кадров s..e)
Текстура дуба: tex/oak_veneer_01_diff_2k.jpg (Poly Haven, CC0; качается в workflow), без неё — процедурное дерево.
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
sys.argv = sys.argv[:1]
exec(open(os.path.join(HERE, '_common.py')).read())
import bmesh
from mathutils import Matrix, Vector
from bpy_extras.object_utils import world_to_camera_view

TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FRAMES = TL['frames']
scn.frame_start, scn.frame_end = 1, FRAMES
TRAVEL = TL['travel']
R_GEAR = 0.5                                           # шестерня 8z: делительный радиус 10 LDU = 0.5 шипа

def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

def disp(f):
    if f < TL['open0']: return 0.0
    if f < TL['open1']: return TRAVEL * ease((f - TL['open0']) / (TL['open1'] - TL['open0']))
    if f < TL['close0']: return TRAVEL
    if f < TL['close1']: return TRAVEL * (1 - ease((f - TL['close0']) / (TL['close1'] - TL['close0'])))
    return 0.0

# ------------------------------------------------ модель (целиком)
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld_mat(rot, pos):
    R = C @ Matrix(rot) @ C.transposed()
    return Matrix.Translation(C @ (Vector(pos) / 20.0)) @ R.to_4x4()
def b(pos):
    return C @ (Vector(pos) / 20.0)

parts = json.load(open(os.path.join(HERE, 'model_t000.json'), encoding='utf-8'))
DOOR_ROOT = empty('door_root', (0, 0, 0))
gp = next(p for p in parts if p['note'] == 'шестерня 8z')
GEAR_C = b(gp['pos']); GEAR_C.y = 0.0
GEAR_ROOT = empty('gear_root', tuple(GEAR_C))
bpy.context.view_layer.update()
MODEL = []
def add_part(part, color, M, parent=None, name='part'):
    o = bpy.data.objects.new(name, part_mesh(part, color))
    bpy.context.collection.objects.link(o)
    if parent:
        o.parent = parent
    o.matrix_world = M
    if parent:
        bpy.context.view_layer.update()
    MODEL.append(o)
    return o
for p in parts:
    par = DOOR_ROOT if p['group'] == 'door' else GEAR_ROOT if p['group'] == 'drive' else None
    o = add_part(p['part'], p['color'], ld_mat(p['rot'], p['pos']), par, p['note'])
    if p['note'] == 'шестерня 8z':
        GEAR = o
    if p['group'] == 'hub':
        HUB_POS = Vector(p['pos'])
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in MODEL for c in o.bound_box]
LO = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
HI = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
Z0 = LO.z
print('model bbox', tuple(round(v, 2) for v in LO), tuple(round(v, 2) for v in HI), 'gear', tuple(GEAR_C))

sp = next(p for p in parts if p['group'] == 'sensor')
SENSOR_FRONT = b(sp['pos']) + Vector((0, -2.0, -0.6))
LED = b(HUB_POS + Vector((0, 3, -38)))                  # светодиод хаба (деталь 22994, цвет 79)

# ------------------------------------------------ штекеры и провода (порты хаба — на заднем торце)
PORTS = [HUB_POS + Vector((x, 11, 80)) for x in (-20, 20)]
PLUG_R = ((-1, 0, 0), (0, 1, 0), (0, 0, -1))
for pt in PORTS:
    add_part('23816a.dat', 0, ld_mat(PLUG_R, pt), None, 'штекер')
CABLE_M = bpy.data.materials.new('cable'); CABLE_M.use_nodes = True
_cb = CABLE_M.node_tree.nodes['Principled BSDF']
_cb.inputs['Base Color'].default_value = lin('#1E1F22'); _cb.inputs['Roughness'].default_value = 0.45
_cb.inputs['Coat Weight'].default_value = 0.2
def cable(name, pts, r=0.13):
    cd = bpy.data.curves.new(name, 'CURVE'); cd.dimensions = '3D'
    cd.bevel_depth = r; cd.bevel_resolution = 4
    spl = cd.splines.new('BEZIER'); spl.bezier_points.add(len(pts) - 1)
    for bp, q in zip(spl.bezier_points, pts):
        bp.co = q; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cd); bpy.context.collection.objects.link(o)
    o.data.materials.append(CABLE_M)
    return o
pA, pB = b(PORTS[0]) + Vector((0, 0.9, 0)), b(PORTS[1]) + Vector((0, 0.9, 0))
TZ = Z0 + 0.13                                           # провод лежит на столе
cable('cable_sensor', [SENSOR_FRONT + Vector((0.2, 4.0, 0.2)), SENSOR_FRONT + Vector((0.0, 5.6, -0.4)),
                       Vector((-4.6, 5.0, 4.4)), Vector((-6.6, 7.6, 3.6)), Vector((-7.6, 10.4, 2.0)),
                       Vector((-7.0, 12.0, TZ)), Vector((-6.0, 11.0, TZ + 0.4)), pA + Vector((0, 0.9, 0.2)), pA])
cable('cable_motor', [Vector((GEAR_C.x + 0.6, 6.1, 3.9)), Vector((GEAR_C.x + 0.6, 7.6, 2.2)), Vector((GEAR_C.x, 9.8, TZ)),
                      Vector((-1.6, 11.6, TZ)), Vector((-3.6, 10.6, TZ + 0.5)), pB + Vector((0, 0.9, 0.2)), pB])

# ------------------------------------------------ живой пластик: лёгкая неравномерность блеска и микрорельеф
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
    sc = N.new('ShaderNodeTexNoise'); sc.inputs['Scale'].default_value = 60.0; sc.inputs['Detail'].default_value = 2
    L.new(tc.outputs['Object'], sc.inputs['Vector'])
    bu = N.new('ShaderNodeBump'); bu.inputs['Strength'].default_value = 0.025
    L.new(sc.outputs['Fac'], bu.inputs['Height']); L.new(bu.outputs['Normal'], bs.inputs['Normal'])

# светодиод хаба: синий — на связи, зелёный — пока дверь работает
led_m = MATS.get(79)
led = led_m.node_tree.nodes['Principled BSDF'] if led_m else None
BLUE, GREENL = lin('#2F7BFF'), lin('#33E05A')
def kled(f, col, strength):
    if not led: return
    led.inputs['Emission Color'].default_value = col; led.inputs['Emission Color'].keyframe_insert('default_value', frame=f)
    led.inputs['Emission Strength'].default_value = strength; led.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
F_ON, F_OFF = TL['detect'], TL['close1']
kled(1, BLUE, 6); kled(F_ON - 1, BLUE, 6); kled(F_ON, GREENL, 7); kled(F_OFF, GREENL, 7); kled(F_OFF + 1, BLUE, 6)
gl = bpy.data.lights.new('ledglow', 'POINT'); gl.shadow_soft_size = 0.3
glo = bpy.data.objects.new('ledglow', gl); bpy.context.collection.objects.link(glo); glo.location = LED + Vector((0, 0, 0.6))
glo.visible_glossy = False
for f, colr, e in ((1, '#2F7BFF', 15), (F_ON - 1, '#2F7BFF', 15), (F_ON, '#33E05A', 40), (F_OFF, '#33E05A', 40), (F_OFF + 1, '#2F7BFF', 15)):
    gl.color = lin(colr)[:3]; gl.keyframe_insert('color', frame=f)
    gl.energy = e; gl.keyframe_insert('energy', frame=f)
def fcurves(idb):
    out = []
    ad = getattr(idb, 'animation_data', None)
    if ad and ad.action:
        try:
            out += list(ad.action.fcurves)
        except Exception:
            for lay in ad.action.layers:
                for st in lay.strips:
                    for cb in st.channelbags:
                        out += list(cb.fcurves)
    return out
for idb in (gl, led_m.node_tree if led_m else None):
    if idb is None: continue
    for fc in fcurves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'

# анимация двери и шестерни
for f in range(1, FRAMES + 1):
    d = disp(f)
    DOOR_ROOT.location = (d, 0, 0); DOOR_ROOT.keyframe_insert('location', frame=f)
    GEAR_ROOT.rotation_euler = (0, -d / R_GEAR, 0); GEAR_ROOT.keyframe_insert('rotation_euler', frame=f)

# ------------------------------------------------ реалистичная ладонь (кожа с подповерхностным рассеиванием, без рукава)
def mat(name, hexv, rough=0.5, coat=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = lin(hexv); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Coat Weight'].default_value = coat
    if sss:
        bs.inputs['Subsurface Weight'].default_value = sss
        bs.inputs['Subsurface Radius'].default_value = (1.0, 0.45, 0.25)
        bs.inputs['Subsurface Scale'].default_value = 0.35
    return m

def hand():
    root = empty('hand', (0, 0, 0))
    mb = bpy.data.metaballs.new('hand_mb'); mb.resolution = 0.12; mb.render_resolution = 0.05; mb.threshold = 0.6
    def cap(p0, p1, r):
        p0, p1 = Vector(p0), Vector(p1)
        el = mb.elements.new(); el.type = 'CAPSULE'; el.co = (p0 + p1) / 2; el.radius = r
        el.size_x = (p1 - p0).length / 2
        el.rotation = Vector((1, 0, 0)).rotation_difference((p1 - p0).normalized())
    el = mb.elements.new(); el.type = 'ELLIPSOID'; el.co = (0, 0, -2.6); el.radius = 2.2
    el.size_x, el.size_y, el.size_z = 1.15, 0.45, 1.2
    cap((0, 0, 0.6), (0, 0, -1.4), 1.75)
    cap((0, 0, 0.6), (0, 0.1, 11.0), 1.95)               # предплечье
    for x, ln in ((-1.15, 0.82), (-0.38, 1.0), (0.4, 0.94), (1.12, 0.74)):
        b0 = (x * 1.0, 0.0, -3.7); b1 = (x * 1.1, 0.12, -3.7 - 1.6 * ln); b2 = (x * 1.16, 0.18, -3.7 - 2.75 * ln)
        cap(b0, b1, 0.78); cap(b1, b2, 0.7)
    cap((-1.35, -0.3, -1.9), (-2.55, -0.85, -3.1), 0.85)
    h = bpy.data.objects.new('hand_mesh', mb); bpy.context.collection.objects.link(h); h.parent = root
    mb.materials.append(mat('skin', '#F2C9A8', 0.45, coat=0.05, sss=0.25))
    return root
HAND = hand()
for _o in [HAND] + list(HAND.children):          # метаболы + размытие движения дают «волоски» — выключаем
    try:
        _o.cycles.use_motion_blur = False
    except Exception:
        pass
HSC = 0.6
PALM_LOCAL = Vector((0, 0, -3.4)) * HSC
def hand_rot(sleeve_dir):
    z = sleeve_dir.normalized()
    y = Vector((0, -1, 0)); y = (y - z * y.dot(z)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()
SLEEVE = Vector((-0.95, -0.55, -0.42))
PALM_AT = SENSOR_FRONT + Vector((-1.0, -4.2, -0.8))
OUT = Vector((-16, -6, -2))
def kh(f, palm, sleeve=SLEEVE):
    Rm = hand_rot(sleeve)
    HAND.matrix_world = Matrix.Translation(palm - Rm @ PALM_LOCAL) @ Rm.to_4x4() @ Matrix.Scale(HSC, 4)
    HAND.keyframe_insert('location', frame=f); HAND.keyframe_insert('rotation_euler', frame=f); HAND.keyframe_insert('scale', frame=f)
for ob in [HAND] + list(HAND.children):
    for f_, hid in ((1, True), (TL['hand0'] - 1, True), (TL['hand0'], False), (TL['handout'] + 30, False), (TL['handout'] + 31, True)):
        ob.hide_render = hid; ob.keyframe_insert('hide_render', frame=f_)
kh(1, PALM_AT + OUT)
kh(TL['hand0'], PALM_AT + OUT)
kh(TL['hand1'] - 8, PALM_AT + Vector((-0.8, -0.6, 0.4)))
kh(TL['hand1'], PALM_AT)
kh(TL['handout'] - 4, PALM_AT + Vector((-0.2, 0.1, 0.1)))
kh(TL['handout'] + 26, PALM_AT + OUT * 1.1)

# ------------------------------------------------ кабинет: дубовый стол, стена, окно слева, полка с наборами
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
    else:                                              # процедурное дерево
        mp.inputs['Scale'].default_value = (0.08, 1.2, 1.0)
        wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.5; wv.inputs['Distortion'].default_value = 6
        wv.inputs['Detail'].default_value = 4
        L.new(mp.outputs['Vector'], wv.inputs['Vector'])
        cr = N.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].color = lin('#B88A5A'); cr.color_ramp.elements[1].color = lin('#D9B48A')
        L.new(wv.outputs['Fac'], cr.inputs['Fac']); L.new(cr.outputs['Color'], bs.inputs['Base Color'])
    return m
box('table', -60, 60, -60, 26, Z0 - 1.2, Z0, mat_wood(), bevel=0.15)
WALL = mat('wall', '#E8E3DA', 0.9)
box('floor_far', -300, 300, -300, 300, Z0 - 30, Z0 - 29, mat('floor', '#8D857A', 0.8))
box('wall', -300, 300, 40, 41, Z0 - 30, Z0 + 90, WALL)
# окно слева на стене: светлый проём с рамой (в расфокусе)
WIN = bpy.data.materials.new('window'); WIN.use_nodes = True
_wn = WIN.node_tree.nodes; _wl = WIN.node_tree.links
_em = _wn.new('ShaderNodeEmission'); _em.inputs['Color'].default_value = lin('#EAF3FF'); _em.inputs['Strength'].default_value = 4.0
_wl.new(_em.outputs['Emission'], _wn['Material Output'].inputs['Surface'])
box('window', -44, -14, 39.8, 40.2, Z0 + 4, Z0 + 34, WIN)
FRAME = mat('frame', '#F4F4F2', 0.5)
for x in (-44, -29.5, -14):
    box('wframe', x - 0.6, x + 0.6, 39.5, 39.9, Z0 + 4, Z0 + 34, FRAME)
for z in (4, 19, 34):
    box('wframe', -44.6, -13.4, 39.5, 39.9, Z0 + z - 0.6, Z0 + z + 0.6, FRAME)
# полка справа с коробками наборов (цветные, в расфокусе)
SH = mat('shelf', '#C9B79C', 0.6)
for z in (8, 20):
    box('shelf', 14, 46, 33, 39.6, Z0 + z - 0.5, Z0 + z, SH)
import random
random.seed(3)
for z in (8, 20):
    x = 15.0
    while x < 44:
        w = random.uniform(3.0, 5.5); h = random.uniform(5.0, 8.5)
        col = random.choice(['#F2B33D', '#4CB2E6', '#E85A4F', '#8CC63F', '#F4F1EA'])
        box('kit', x, x + w, 34, 39, Z0 + z, Z0 + z + h, mat('k' + col, col, 0.45))
        x += w + random.uniform(0.3, 0.9)

# свет: солнце из окна слева-сзади, мягкий заполняющий спереди, небо
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F2EEE6')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35
sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.2; sun.angle = math.radians(4); sun.color = lin('#FFF0DC')[:3]
so = bpy.data.objects.new('sun', sun); bpy.context.collection.objects.link(so)
so.rotation_euler = (Vector((0, 0, 0)) - Vector((-30, 40, 38))).to_track_quat('-Z', 'Y').to_euler()
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power
    ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.visible_camera = False
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
area('window_soft', (-30, 30, Z0 + 20), (0, 0, Z0 + 3), 26, 9000, '#EEF4FF')
area('fill', (14, -30, Z0 + 16), (0, 0, Z0 + 3), 20, 3800, '#FFF2E2')

# ------------------------------------------------ камера «с рук», перевод фокуса
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = 5.6
SHOT = {   # камера, цель, объектив, точка фокуса
    'hero':   ((-6.0, -29.0, 11.5), (-0.5, 1.0, 3.6), 45, 'door'),
    'sensor': ((6.0, -21.0, 10.0), (-3.4, -3.4, 5.0), 48, 'sensor'),
    'mech':   ((15.5, -8.0, 7.8), (7.5, -0.5, 4.3), 55, 'rack'),
    'open':   ((-3.0, -26.0, 7.5), (0.0, 0.0, 3.0), 45, 'door'),
    'mech2':  ((16.5, -4.5, 6.8), (8.0, -0.5, 4.2), 60, 'rack'),
    'end':    ((6.0, -31.0, 13.0), (-0.5, 1.0, 3.8), 45, 'door'),
}
FOCUS = {'door': Vector((-3.0, -1.0, 2.5)), 'sensor': (SENSOR_FRONT + PALM_AT) / 2, 'gear': GEAR_C + Vector((0, -0.5, 0)),
         'rack': Vector((9.0, -0.5, 4.5))}
SEQ = TL['shots']; BLEND = TL['blend']
def shot_at(f):
    cur = SEQ[0][1]; w = 1.0; prev = cur
    for i, (fs, nm) in enumerate(SEQ):
        if f >= fs:
            prev = SEQ[i - 1][1] if i else nm; cur = nm
            w = ease((f - fs) / BLEND) if i else 1.0
    a, bb = SHOT[prev], SHOT[cur]
    mix = lambda p, q: Vector(p).lerp(Vector(q), w)
    return mix(a[0], bb[0]), mix(a[1], bb[1]), a[2] + (bb[2] - a[2]) * w, FOCUS[a[3]].lerp(FOCUS[bb[3]], w)
def shake(f, amp):
    t = f / 24.0
    return Vector((amp * (math.sin(t * 2.1) * 0.6 + math.sin(t * 5.3 + 1.0) * 0.25 + math.sin(t * 11.7) * 0.08),
                  amp * (math.sin(t * 1.7 + 2.0) * 0.4 + math.sin(t * 6.1) * 0.15),
                  amp * (math.sin(t * 2.6 + 0.5) * 0.5 + math.sin(t * 7.9 + 3.0) * 0.18)))
for f in range(1, FRAMES + 1):
    co, to, lens, fp = shot_at(f)
    cam.location = co + shake(f, 0.12); cam.keyframe_insert('location', frame=f)
    tgt.location = to + shake(f + 400, 0.05); tgt.keyframe_insert('location', frame=f)
    cam_d.lens = lens; cam_d.keyframe_insert('lens', frame=f)
    cam_d.dof.focus_distance = (co - fp).length; cam_d.dof.keyframe_insert('focus_distance', frame=f)

# ------------------------------------------------ рендер
r = scn.render
r.engine = 'CYCLES'
cy = scn.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.04
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 2
cy.transmission_bounces = 4; cy.transparent_max_bounces = 4
r.use_persistent_data = True
r.use_motion_blur = True; r.motion_blur_shutter = 0.2
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'

def write_proj(frames):
    r.resolution_x, r.resolution_y = 1080, 1920
    res = {}
    for f in frames:
        scn.frame_set(f)
        pr = lambda v: [round(x, 4) for x in list(world_to_camera_view(scn, cam, v))[:2]]
        g = GEAR.matrix_world.translation
        res[f] = {'sensor': pr(SENSOR_FRONT), 'gear': pr(g), 'gear_e': pr(g + Vector((0, 0, 0.62))), 'led': pr(LED)}
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
