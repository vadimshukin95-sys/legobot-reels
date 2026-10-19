"""«Двери супермаркета» — WeDo 2.0 (45300), реечная передача. Рилс LEGObot.
Сюжет: ладонь подходит к датчику → мотор крутит шестерню 8z → рейки на балке двери едут → дверь открывается,
ладонь ушла → 3 с → дверь закрывается. Дверь, неподвижная панель и перемычка — стекло (стилизация),
чтобы мотор, шестерня и рейки были на виду. Хаб и пластины под ним в кадр не берём.
Модель — из конвейера инструкций (legobot-wedo-pipeline/models/dveri), model_t000.json (дверь закрыта).
1 unit = 1 stud, Z вверх, фасад смотрит в -Y.
  python scene.py test 1,90,140,300 540 960 8
  python scene.py anim 1 420 1080 1920 16      (+ пишет proj.json для кадров s..e)
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
    """ход двери (шипы) в кадре f"""
    if f < TL['open0']: return 0.0
    if f < TL['open1']: return TRAVEL * ease((f - TL['open0']) / (TL['open1'] - TL['open0']))
    if f < TL['close0']: return TRAVEL
    if f < TL['close1']: return TRAVEL * (1 - ease((f - TL['close0']) / (TL['close1'] - TL['close0'])))
    return 0.0

# ------------------------------------------------ стекло
GLASS = bpy.data.materials.new('ghost'); GLASS.use_nodes = True     # «рентген»: почти прозрачный белёсый пластик
_nt = GLASS.node_tree; _n = _nt.nodes; _l = _nt.links
_b = _n['Principled BSDF']
_b.inputs['Base Color'].default_value = lin('#DCEFFA'); _b.inputs['Roughness'].default_value = 0.25
_b.inputs['Coat Weight'].default_value = 0.3
_tr = _n.new('ShaderNodeBsdfTransparent'); _mx = _n.new('ShaderNodeMixShader')
_fr = _n.new('ShaderNodeLayerWeight'); _fr.inputs['Blend'].default_value = 0.35
_mp = _n.new('ShaderNodeMapRange'); _mp.inputs['To Min'].default_value = 0.04; _mp.inputs['To Max'].default_value = 0.32
_l.new(_fr.outputs['Facing'], _mp.inputs['Value'])
_l.new(_mp.outputs['Result'], _mx.inputs['Fac'])
_l.new(_tr.outputs['BSDF'], _mx.inputs[1]); _l.new(_b.outputs['BSDF'], _mx.inputs[2])
_l.new(_mx.outputs['Shader'], _n['Material Output'].inputs['Surface'])
try:
    GLASS.blend_method = 'BLEND'
except Exception:
    pass
GLASS_GROUPS = {'panel', 'lintel', 'clamp'}            # дверь — в настоящих цветах, «рентген» только у того, что её закрывает
KEEP = {'3743.dat'}                                     # рейки — белые

# ------------------------------------------------ модель
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld_mat(p):
    R = C @ Matrix(p['rot']) @ C.transposed()
    return Matrix.Translation(C @ (Vector(p['pos']) / 20.0)) @ R.to_4x4()

parts = json.load(open(os.path.join(HERE, 'model_t000.json'), encoding='utf-8'))
DOOR_ROOT = empty('door_root', (0, 0, 0))
gp = next(p for p in parts if p['note'] == 'шестерня 8z')
GEAR_C = C @ (Vector(gp['pos']) / 20.0)
GEAR_C.y = 0.0
GEAR_ROOT = empty('gear_root', tuple(GEAR_C))
bpy.context.view_layer.update()
MODEL = []
for p in parts:
    if p['group'] == 'hub' or 'под хаб' in p['note']:
        continue
    o = bpy.data.objects.new(p['note'], part_mesh(p['part'], p['color']))
    bpy.context.collection.objects.link(o)
    if p['group'] in GLASS_GROUPS and p['part'] not in KEEP:
        o.data = o.data.copy()
        for i in range(len(o.data.materials)):
            o.data.materials[i] = GLASS
    M = ld_mat(p)
    if p['group'] == 'door':
        o.parent = DOOR_ROOT
    elif p['group'] == 'drive':
        o.parent = GEAR_ROOT
    if o.parent:
        o.matrix_world = M
        bpy.context.view_layer.update()
    else:
        o.matrix_world = M
    MODEL.append(o)
    if p['note'] == 'шестерня 8z':
        GEAR = o
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in MODEL for c in o.bound_box]
LO = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
HI = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
Z0 = LO.z
print('model bbox', tuple(round(v, 2) for v in LO), tuple(round(v, 2) for v in HI), 'gear', tuple(GEAR_C))

# датчик: глаз на переднем торце
sp = next(p for p in parts if p['group'] == 'sensor')
SENSOR_FRONT = C @ (Vector(sp['pos']) / 20.0) + Vector((0, -2.0, -0.6))

# анимация двери и шестерни (рейка едет в +X — шестерня над ней крутится вокруг Y)
for f in range(1, FRAMES + 1):
    d = disp(f)
    DOOR_ROOT.location = (d, 0, 0); DOOR_ROOT.keyframe_insert('location', frame=f)
    GEAR_ROOT.rotation_euler = (0, -d / R_GEAR, 0); GEAR_ROOT.keyframe_insert('rotation_euler', frame=f)

# ------------------------------------------------ ладонь «покупателя» (не LEGO, реквизит — как в рилсе курьера)
def mat(name, hexv, rough=0.5, coat=0.0, sss=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    return m

def hand():
    root = empty('hand', (0, 0, 0))
    mb = bpy.data.metaballs.new('hand_mb'); mb.resolution = 0.12; mb.render_resolution = 0.06; mb.threshold = 0.6
    def cap(p0, p1, r):
        p0, p1 = Vector(p0), Vector(p1)
        el = mb.elements.new(); el.type = 'CAPSULE'; el.co = (p0 + p1) / 2; el.radius = r
        el.size_x = (p1 - p0).length / 2
        el.rotation = Vector((1, 0, 0)).rotation_difference((p1 - p0).normalized())
    el = mb.elements.new(); el.type = 'ELLIPSOID'; el.co = (0, 0, -2.6); el.radius = 2.3
    el.size_x, el.size_y, el.size_z = 1.2, 0.5, 1.2
    cap((0, 0, 0.6), (0, 0, -1.4), 1.9)
    for x, ln in ((-1.2, 0.85), (-0.4, 1.0), (0.4, 0.95), (1.18, 0.75)):
        b0 = (x * 1.0, 0.0, -3.7); b1 = (x * 1.12, 0.1, -3.7 - 1.7 * ln); b2 = (x * 1.2, 0.15, -3.7 - 2.9 * ln)
        cap(b0, b1, 0.9); cap(b1, b2, 0.85)
    cap((-1.4, -0.3, -1.9), (-2.7, -0.9, -3.2), 0.95)
    h = bpy.data.objects.new('hand_mesh', mb); bpy.context.collection.objects.link(h); h.parent = root
    mb.materials.append(mat('skin', '#F1C29A', 0.55, coat=0.1, sss=0.15))
    me = bpy.data.meshes.new('sleeve'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=1.6, radius2=1.95, depth=16)
    bmesh.ops.translate(bm, vec=(0, 0, 8.7), verts=bm.verts)
    bm.to_mesh(me); bm.free()
    for q in me.polygons:
        q.use_smooth = True
    sl = bpy.data.objects.new('sleeve', me); bpy.context.collection.objects.link(sl); sl.parent = root
    me.materials.append(mat('sleeve', '#E8746A', 0.7))
    me = bpy.data.meshes.new('cuff'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=1.8, radius2=1.8, depth=0.8)
    bmesh.ops.translate(bm, vec=(0, 0, 0.8), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.12, segments=3, affect='EDGES')
    bm.to_mesh(me); bm.free()
    for q in me.polygons:
        q.use_smooth = True
    cf = bpy.data.objects.new('cuff', me); bpy.context.collection.objects.link(cf); cf.parent = root
    me.materials.append(mat('cuff', '#F4F4F0', 0.45, coat=0.3))
    return root
HAND = hand()
HSC = 0.6
PALM_LOCAL = Vector((0, 0, -3.4)) * HSC
def hand_rot(sleeve_dir):
    z = sleeve_dir.normalized()
    y = Vector((0, -1, 0)); y = (y - z * y.dot(z)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()
SLEEVE = Vector((-0.95, -0.55, -0.42))
PALM_AT = SENSOR_FRONT + Vector((-0.6, -5.0, -0.4))
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

# ------------------------------------------------ студия: пастельная бесшовная циклорама
def cyclorama(name, m, y_wall=34.0, rad=22.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    prof = [(-200.0, 0.0), (y_wall - rad, 0.0)]
    for k in range(1, 17):
        a = math.pi / 2 * k / 16
        prof.append((y_wall - rad + rad * math.sin(a), rad - rad * math.cos(a)))
    prof.append((y_wall, 160.0))
    rows = [[bm.verts.new((x, y, z + Z0)) for (y, z) in prof] for x in (-220.0, 220.0)]
    for j in range(len(prof) - 1):
        bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
    bm.to_mesh(me); bm.free()
    for q in me.polygons:
        q.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m)
    return o
cyclorama('sweep', mat('sweep', '#D3E7F0', 0.8))
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F3F1EC')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5

def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power
    ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.visible_camera = False
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o
area('key', (-22, -26, Z0 + 32), (1, 0, Z0 + 3), 22, 15000, '#FFE9CC')
area('fill', (28, -22, Z0 + 14), (1, 0, Z0 + 3), 18, 5000, '#DDE8FF')
area('rim', (4, 26, Z0 + 24), (1, 0, Z0 + 4), 14, 6500, '#FFF4E0')
area('mech', (GEAR_C.x - 5, -9, GEAR_C.z + 9), tuple(GEAR_C), 4, 900, '#FFF1DA')

# ------------------------------------------------ камера
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = 4.0
SHOT = {   # камера, цель, объектив (абсолютные координаты: модель неподвижна)
    'hero':   ((-5.0, -27.0, 11.0), (0.0, 0.0, 3.4), 50),
    'sensor': ((7.0, -19.0, 10.0), (-2.6, -2.0, 5.0), 50),
    'mech':   ((5.0, -11.5, 6.8), (2.0, -0.5, 4.7), 70),
    'open':   ((-3.0, -26.0, 7.5), (0.0, 0.0, 3.0), 50),
    'mech2':  ((-1.5, -11.5, 6.8), (2.0, -0.5, 4.7), 70),
    'end':    ((5.0, -30.0, 13.0), (0.5, 0.0, 3.6), 50),
}
SEQ = TL['shots']; BLEND = TL['blend']
def shot_at(f):
    cur = SEQ[0][1]; w = 1.0; prev = cur
    for i, (fs, nm) in enumerate(SEQ):
        if f >= fs:
            prev = SEQ[i - 1][1] if i else nm; cur = nm
            w = ease((f - fs) / BLEND) if i else 1.0
    a, b = SHOT[prev], SHOT[cur]
    mix = lambda p, q: Vector(p).lerp(Vector(q), w)
    return mix(a[0], b[0]), mix(a[1], b[1]), a[2] + (b[2] - a[2]) * w
def push(f):                                            # лёгкий наезд на первом плане
    if f <= 36: return 5.0 * ease(f / 36)
    return 5.0 * (1 - ease((f - 36) / BLEND))
for f in range(1, FRAMES + 1):
    co, to, lens = shot_at(f)
    cam.location = co; cam.keyframe_insert('location', frame=f)
    tgt.location = to; tgt.keyframe_insert('location', frame=f)
    cam_d.lens = lens + push(f); cam_d.keyframe_insert('lens', frame=f)

# ------------------------------------------------ рендер
r = scn.render
r.engine = 'CYCLES'
cy = scn.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.05
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 8; cy.diffuse_bounces = 2; cy.glossy_bounces = 2
cy.transmission_bounces = 8; cy.transparent_max_bounces = 8
r.use_persistent_data = True
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
        res[f] = {'sensor': pr(SENSOR_FRONT), 'gear': pr(GEAR.matrix_world.translation), 'door': pr(DOOR_ROOT.matrix_world @ Vector((-4.0, -1.0, 2.0)))}
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
