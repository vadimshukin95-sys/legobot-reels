"""«Ремень проскальзывает» — вентилятор на LEGO WeDo 2.0 (45300), продолжение «Ремня восьмёркой». Рилс LEGObot.
Механизм: мотор -> красная ось 2 -> шкив 4185 (ведущий) -> жёлтый ремень -> шкив 4185 на оси 6 -> лопасти.
В лопасти вставляют карандаш: вентилятор встаёт, мотор крутится дальше — ремень проскальзывает по ведущему шкиву
(шестерни бы заклинило). Карандаш вынули — вентилятор снова разгоняется. Кинематика — motion.py (общая со звуком).
Модель, свет и камера — как в scenes/remen (согласованный стиль серии).
1 unit = 1 stud, Z вверх, вентилятор смотрит в +Y (камера спереди).
  python scene.py test 30,48,52,150,256,300,360 540 960 10
  python scene.py anim 1 384 1080 1920 16
"""
import os, sys, math, json
HERE = os.path.dirname(os.path.abspath(__file__))
ARGS = sys.argv[1:]
sys.argv = sys.argv[:1]
exec(open(os.path.join(HERE, '_common.py')).read())
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FRAMES = TL['render_frames']
scn.frame_start, scn.frame_end = 1, FRAMES

def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------ кинематика (motion.py)
import motion as MO
ANG = MO.DRIVE

# ------------------------------------------------ модель (детали и цвета набора 45300)
TLBLUE, BGREEN = 43, 10
MZ = 6.8
OUTP = (0.0, 1.0, MZ - 1.3)          # выход мотора
FAN = (0.0, 0.0, 9.1)                # ось вентилятора в техно-кирпичах на крыше мотора
PY = 1.5                             # плоскость шкивов
for x in (-1, 1):
    put('4282.dat', BLACK, (x, 0, 0.4), rz=90)
for y in (-7.5, 7.5):
    put('3710.dat', WHITE, (0, y, 0.8))
for z, c in ((1.6, BLORANGE), (2.8, BLORANGE), (4.0, AZURE)):
    put('3001.dat', c, (0, -2, z), rz=90)
put('21980.dat', LBG, (0, 0, MZ), rz=180, name='мотор')
put('3003.dat', BLACK, (0, 0, MZ + 1.2))
for y in (-0.5, 0.5):
    put('3023.dat', WHITE, (0, y, MZ + 1.6))
for y in (-0.5, 0.5):
    put('3701.dat', LIME, (0, y, MZ + 2.8))
drive = empty('drive', (0, 0, OUTP[2]))
put('32062.dat', RED, (0, 1.0, 0), rz=90, parent=drive)
put('4185.dat', TLBLUE, (0, PY, 0), parent=drive)
fan = empty('fan', FAN)
put('3706.dat', BLACK, (0, 2.0, 0), rz=90, parent=fan)
put('4185.dat', TLBLUE, (0, PY, 0), parent=fan)
blades = empty('blades', (0, 3.4, 0), parent=fan); blades.rotation_euler = (math.radians(-90), 0, 0)
BLADES = [put('4032b.dat', BGREEN, (0, 0, 0.0), parent=blades), put('60474.dat', AZURE, (0, 0, 0.4), parent=blades)]
for i in range(4):
    a = math.radians(90 * i); px, py = 0.5, 2.0
    BLADES.append(put('42022.dat', LIME, (px * math.cos(a) - py * math.sin(a), px * math.sin(a) + py * math.cos(a), 1.6),
                      rz=180 + 90 * i, parent=blades))
put('19071c01.dat', WHITE, (-8.0, -3.5, 3.6), name='смартхаб')
cd = bpy.data.curves.new('cable_motor', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = 0.12; cd.bevel_resolution = 4
sp = cd.splines.new('BEZIER'); pts = [(0, -5.6, 5.6), (-0.4, -7.0, 3.5), (-2.8, -7.2, 0.3), (-4.4, -6.0, 0.4), (-5.0, -4.8, 1.8)]
sp.bezier_points.add(len(pts) - 1)
for bp, p in zip(sp.bezier_points, pts):
    bp.co = p; bp.handle_left_type = bp.handle_right_type = 'AUTO'
oc = bpy.data.objects.new('cable_motor', cd); bpy.context.collection.objects.link(oc); oc.data.materials.append(plastic(BLACK))

# ------------------------------------------------ жёлтый ремень: прямой и восьмёркой
BELT_R, BELT_T = 1.45, 0.13
def belt_points(c1, c2, y, r, rad, cross):
    (x1, z1), (x2, z2) = c1, c2
    a1 = math.atan2(z2 - z1, x2 - x1); n = 48; pts = []
    if not cross:
        for i in range(n + 1):
            a = a1 + math.pi / 2 + math.pi * i / n; pts.append((x1 + r * math.cos(a), y, z1 + r * math.sin(a)))
        for i in range(n + 1):
            a = a1 - math.pi / 2 + math.pi * i / n; pts.append((x2 + r * math.cos(a), y, z2 + r * math.sin(a)))
        return pts
    d = math.hypot(x2 - x1, z2 - z1); phi = math.acos(2 * r / d); a2 = a1 + math.pi
    def line(p, q, side):
        k = 14
        for j in range(1, k):
            s = j / k
            pts.append((p[0] + (q[0] - p[0]) * s, y + side * rad * 1.05 * math.sin(math.pi * s), p[2] + (q[2] - p[2]) * s))
    for i in range(n + 1):
        a = a1 + phi + (2 * math.pi - 2 * phi) * i / n; pts.append((x1 + r * math.cos(a), y, z1 + r * math.sin(a)))
    e1 = pts[-1]; s2 = (x2 + r * math.cos(a2 - phi), y, z2 + r * math.sin(a2 - phi)); line(e1, s2, +1)
    for i in range(n + 1):
        a = a2 - phi - (2 * math.pi - 2 * phi) * i / n; pts.append((x2 + r * math.cos(a), y, z2 + r * math.sin(a)))
    e2 = pts[-1]; line(e2, pts[0], -1)
    return pts
BELT_M = bpy.data.materials.new('belt'); BELT_M.use_nodes = True
_bb = BELT_M.node_tree.nodes['Principled BSDF']
_bb.inputs['Base Color'].default_value = lin('#F4C20D'); _bb.inputs['Roughness'].default_value = 0.55
def belt(name, cross):
    pts = belt_points((OUTP[0], OUTP[2]), (FAN[0], FAN[2]), PY, BELT_R, BELT_T, cross)
    c = bpy.data.curves.new(name, 'CURVE'); c.dimensions = '3D'; c.bevel_depth = BELT_T; c.bevel_resolution = 3
    s = c.splines.new('POLY'); s.points.add(len(pts) - 1)
    for p_, q in zip(s.points, pts):
        p_.co = (q[0], q[1], q[2], 1)
    s.use_cyclic_u = True
    o = bpy.data.objects.new(name, c); bpy.context.collection.objects.link(o); o.data.materials.append(BELT_M)
    return o
B_OPEN = belt('belt_open', False)

# ------------------------------------------------ вращение: ведущий всегда, вентилятор — по motion.py (стоит, пока карандаш)
for f in range(1, FRAMES + 1):
    drive.rotation_euler = (0, math.radians(-ANG[f]), 0); drive.keyframe_insert('rotation_euler', frame=f)
    fan.rotation_euler = (0, math.radians(MO.FAN[f]), 0); fan.keyframe_insert('rotation_euler', frame=f)
for o in (drive, fan):
    for fc in o.animation_data.action.fcurves if hasattr(o.animation_data.action, 'fcurves') else []:
        for k in fc.keyframe_points:
            k.interpolation = 'LINEAR'

# ------------------------------------------------ «рентген»: лопасти полупрозрачные на крупных планах
X0, X1 = TL['xray']
for o in BLADES:
    for slot in o.material_slots:
        base = slot.material
        g = base.copy(); g.name = base.name + '_xray'
        bs = g.node_tree.nodes['Principled BSDF']
        slot.link = 'OBJECT'; slot.material = g
        for f, al in ((1, 1.0), (X0, 0.10), (X1 + 1, 1.0)):
            bs.inputs['Alpha'].default_value = al; bs.inputs['Alpha'].keyframe_insert('default_value', frame=f)
            bs.inputs['Coat Weight'].default_value = 0.3 if al == 1.0 else 0.0
            bs.inputs['Coat Weight'].keyframe_insert('default_value', frame=f)
for m in bpy.data.materials:
    ad = m.node_tree.animation_data if m.node_tree else None
    if ad and ad.action:
        try:
            fcs = ad.action.fcurves
        except AttributeError:
            fcs = [fc for layer in ad.action.layers for st in layer.strips for cb in st.channelbags for fc in cb.fcurves]
        for fc in fcs:
            for k in fc.keyframe_points:
                k.interpolation = 'CONSTANT'

# ------------------------------------------------ студия как на эскизе: ловец теней, мягкий свет
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F3F0EA')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
area('key', (-16, -24, 30), (0, 0, 3), 18, 11000, '#FFF4E6')
area('fill', (28, -16, 12), (2, 0, 3), 14, 3000, '#E8F0FF')
area('rim', (4, 26, 22), (0, 0, 4), 12, 5200)
area('front', (10, 34, 10), (0, 1.5, 7), 16, 2600, '#FFF8EE')     # подсветка шкивов спереди
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
catcher = bpy.context.object; catcher.name = 'shadow_catcher'; catcher.is_shadow_catcher = True

# ------------------------------------------------ камера: общий план и крупный план шкивов (как на эскизе)
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36
r = scn.render
def framing(lo, hi, view, lens, margin, w=1080, h=1920):
    center = (lo + hi) / 2; d = Vector(view).normalized()
    rad = (hi - lo).length / 2
    fov_w = 2 * math.atan(cam_d.sensor_width / 2 / lens)
    fov = 2 * math.atan(math.tan(fov_w / 2) * h / w) if w >= h else fov_w
    return center + d * (rad * margin / math.sin(fov / 2)), center
bpy.context.view_layer.update()
MODEL = [o for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and o.name not in ('shadow_catcher',)]
pts = [o.matrix_world @ Vector(cc) for o in MODEL for cc in o.bound_box]
LO = Vector([min(p[i] for p in pts) for i in range(3)]); HI = Vector([max(p[i] for p in pts) for i in range(3)])
print('model bbox', tuple(round(v, 2) for v in LO), tuple(round(v, 2) for v in HI))
WIDE = framing(LO, HI, (0.55, 0.80, 0.28), 50, 0.92)
CLO = framing(Vector((-2.6, PY - 0.3, OUTP[2] - 2.4)), Vector((2.6, PY + 0.3, FAN[2] + 2.4)), (0.0, 1.0, 0.10), 70, 1.22)
SHOTS = {'wide': (WIDE, 50, 1.05, 1.0), 'close': (CLO, 70, 1.0, 0.97), 'wide2': (WIDE, 50, 1.0, 0.98),
         'wide_end': (WIDE, 50, 0.98, 0.95)}
SEQ = TL['shots'] + [[FRAMES + 1, None]]
def shake(f, amp):
    t = f / 24.0
    return Vector((amp * (math.sin(t * 2.1) * 0.6 + math.sin(t * 5.3 + 1.0) * 0.25),
                   amp * (math.sin(t * 1.7 + 2.0) * 0.4 + math.sin(t * 6.1) * 0.15),
                   amp * (math.sin(t * 2.6 + 0.5) * 0.5 + math.sin(t * 7.9 + 3.0) * 0.18)))
for (fs, nm), (fe, _) in zip(SEQ, SEQ[1:]):
    (loc, ctr), lens, k0, k1 = SHOTS[nm]
    for f in range(fs, min(fe, FRAMES + 1)):
        k = k0 + (k1 - k0) * ease((f - fs) / max(1, fe - fs))       # медленный наезд
        cam.location = ctr + (loc - ctr) * k + shake(f, 0.03)
        tgt.location = ctr + shake(f + 400, 0.012)
        cam_d.lens = lens
        cam.keyframe_insert('location', frame=f); tgt.keyframe_insert('location', frame=f)
        cam_d.keyframe_insert('lens', frame=f)
for o in (cam, tgt, cam_d):
    ad = o.animation_data
    try:
        fcs = ad.action.fcurves
    except AttributeError:
        fcs = [fc for layer in ad.action.layers for st in layer.strips for cb in st.channelbags for fc in cb.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'                              # склейки — жёсткие, без пролёта камеры

# ------------------------------------------------ карандаш (не деталь набора): шестигранный, в плоскости лопастей
def frustum(name, s0, s1, r0, r1, hexv, rough, metal=0.0):
    k = 6; vs, fs = [], []
    for s, rr in ((s0, r0), (s1, r1)):
        for j in range(k):
            a_ = 2 * math.pi * j / k + math.pi / 6
            vs.append((s, rr * math.cos(a_), rr * math.sin(a_)))
    for j in range(k):
        fs.append((j, (j + 1) % k, k + (j + 1) % k, k + j))
    if r0 > 0.01:
        fs.append(tuple(range(k - 1, -1, -1)))
    fs.append(tuple(range(k, 2 * k)))
    me = bpy.data.meshes.new(name); me.from_pydata(vs, [], fs); me.update()
    m = bpy.data.materials.new(name + '_m'); m.use_nodes = True
    bs = m.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = lin(hexv); bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    if name == 'pencil_body':
        bs.inputs['Coat Weight'].default_value = 0.5; bs.inputs['Coat Roughness'].default_value = 0.15
    me.materials.append(m)
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    return o
PC = MO.PC
PHI = math.radians(PC['phi'])
DIR = Vector((math.cos(PHI), 0, math.sin(PHI)))
pencil = empty('pencil', (0, 0, 0))
pencil.rotation_euler = (0, -PHI, 0)                   # локальная +X -> вдоль DIR (наружу от оси вентилятора)
for nm, s0, s1, r0, r1, hx, rough, met in (('pencil_lead', 0.0, 0.5, 0.0, 0.12, '#2B2B2E', 0.35, 0.4),
                                          ('pencil_wood', 0.5, 2.2, 0.12, 0.45, '#E8C79C', 0.75, 0.0),
                                          ('pencil_body', 2.2, 20.0, 0.45, 0.45, '#F7C21F', 0.3, 0.0)):
    frustum(nm, s0, s1, r0, r1, hx, rough, met).parent = pencil
for f in range(1, FRAMES + 1):
    rr = MO.pencil_r(f) + MO.pencil_far(f)
    p = Vector(FAN) + DIR * rr; p.y = PC['y']
    pencil.location = p; pencil.keyframe_insert('location', frame=f)
for o in pencil.children:
    for f, h in ((1, False), (PC['out'][1] + 24, True)):
        o.hide_render = h; o.keyframe_insert('hide_render', frame=f)
for o in [pencil] + list(pencil.children):
    ad = o.animation_data
    if not ad or not ad.action:
        continue
    try:
        fcs = ad.action.fcurves
    except AttributeError:
        fcs = [fc for layer in ad.action.layers for st in layer.strips for cb in st.channelbags for fc in cb.fcurves]
    for fc in fcs:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR' if fc.data_path == 'location' else 'CONSTANT'

# ------------------------------------------------ рендер
r.engine = 'CYCLES'
cy = scn.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.04
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 48; cy.diffuse_bounces = 3; cy.glossy_bounces = 2
cy.transmission_bounces = 6; cy.transparent_max_bounces = 48
r.use_persistent_data = True
r.use_motion_blur = True; r.motion_blur_shutter = 0.3; r.motion_blur_position = 'START'   # склейки без смаза
r.film_transparent = True
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'

def write_proj(frames):
    """экранные точки для стрелок: центры шкивов и радиус шкива в пикселях 1080×1920"""
    r.resolution_x, r.resolution_y = 1080, 1920
    res = {}
    for f in frames:
        scn.frame_set(f)
        pr = lambda v: [round(x, 5) for x in list(world_to_camera_view(scn, cam, Vector(v)))[:2]]
        lo = pr((OUTP[0], PY, OUTP[2])); hi = pr((FAN[0], PY, FAN[2])); e = pr((OUTP[0] + 1.5, PY, OUTP[2]))
        res[f] = {'low': lo, 'high': hi, 'r': round(math.hypot((e[0] - lo[0]) * 1080, (e[1] - lo[1]) * 1920), 2)}
    old = {}
    pj = os.path.join(HERE, 'proj.json')
    if os.path.exists(pj):
        old = json.load(open(pj))
    old.update({str(k): v for k, v in res.items()})
    json.dump(old, open(pj, 'w'))

mode = ARGS[0] if ARGS else 'test'
os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)
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
elif mode == 'proj':
    write_proj(range(1, FRAMES + 1))
