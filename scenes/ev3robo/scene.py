"""Видео-петля для страницы EV3 на legobot.ru: «Робостроитель» (EV3) переносит кубик.
Робот подъезжает с поднятым захватом, опускает его на кубик, сжимает лапы (мотор -> 12z/20z -> ось -> 8z/8z -> ряд 16z),
второй мотор поднимает захват, робот везёт кубик, ставит, разжимает. Вторая половина петли — кубик обратно на место.
Сценарий (события, расстояния, углы) — в layout.json.
Петля 18 с без шва. Фон прозрачный: цвет фона сайта подставляет compose.py (как в hero3).
Модель — секрет MODEL_ROBO (workflow кладёт её в models/robostroitel.ldr). Units: 1 Blender unit = 1 stud, Z up.
  python scene.py test 1,80,140,185 1280 800 12
  python scene.py anim 1 432 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
import ldr

FPS, LOOP_S = 24, 18
FRAMES = FPS * LOOP_S                                   # 432
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
COL = ldr.colours()
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 19: '#D9BB7B', 25: '#F07A12'}
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
    if COL.get(code, ('', ''))[0].startswith('Trans'):
        b.inputs['Transmission Weight'].default_value = 0.7; b.inputs['Roughness'].default_value = 0.12
    if code == 0:
        b.inputs['Roughness'].default_value = 0.55          # шины и чёрные штифты — матовые
    MATS[code] = m
    return m

def mat(name, hexv, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    return m

# ------------------------------------------------------------------ модель: MPD с подмоделями -> список деталей с мировыми матрицами
ldr.find('3001.dat')
text = open(os.path.join(HERE, 'models', 'robostroitel.ldr'), encoding='utf-8-sig', errors='ignore').read().replace('\r', '')
files, cur, order = {}, None, []
for line in text.splitlines(True):
    t = line.split()
    if len(t) >= 3 and t[0] == '0' and t[1] == 'FILE':
        cur = ' '.join(t[2:]).lower(); files[cur] = []; order.append(cur); continue
    if len(t) >= 2 and t[0] == '0' and t[1] == 'NOFILE':
        cur = None; continue
    if cur is not None:
        files[cur].append(line)

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
        if name.lower() in files:
            walk(files[name.lower()], W, f'{path}/{k}', c)
        else:
            PARTS.append((f'{path}/{k}', name, c, W))
walk(files[order[0]], Matrix.Identity(4), '', 16)

# ------------------------------------------------------------------ подвижные группы (пути из карты движения)
WHEELS = {'/110', '/111', '/112', '/113', '/114', '/115', '/116', '/117'}
# лапа = подмодель лапы + шестерня 16z, её ось, крестовой блок 63869, штифты и Т-балка, которыми лапа висит на оси
CLAW_L = {'/102/0/46', '/102/0/35', '/102/0/37', '/102/0/57', '/102/0/58', '/102/0/62', '/102/0/65', '/102/0/66'}
CLAW_R = {'/102/0/45', '/102/0/34', '/102/0/36', '/102/0/59', '/102/0/60', '/102/0/61', '/102/0/63', '/102/0/64'}
def group_of(p):
    if p in WHEELS: return 'wheels'
    if p.startswith('/102/0/67/') or p in CLAW_L: return 'clawL'
    if p.startswith('/102/0/68/') or p in CLAW_R: return 'clawR'
    if p in ('/102/0/43', '/102/0/30'): return 'g2'                      # промежуточные 16z со своими осями
    if p in ('/102/0/44', '/102/0/31', '/102/0/33'): return 'g3'         # 16z + 8z ведомой оси
    if p.startswith('/102/0/'): return 'lift'                            # рама захвата качается на оси мотора подъёма
    return 'body'
PIV = {'wheels': (634, -73, 486), 'lift': (434, -213, 286), 'clawL': (374, -213, 47), 'clawR': (494, -213, 47),
       'g2': (414, -213, 47), 'g3': (454, -213, 47), 'body': (0, 0, 0)}
PARENT = {'wheels': 'body', 'lift': 'body', 'clawL': 'lift', 'clawR': 'lift', 'g2': 'lift', 'g3': 'lift'}

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def to_b(M):                                             # матрица LDraw (LDU) -> Blender (studs)
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
            k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if k not in vidx:
                vidx[k] = len(verts); verts.append(k)
            f.append(vidx[k])
        if len(set(f)) < 3:
            continue
        if c not in codes:
            codes.append(c)
        faces.append(f); mats.append(codes.index(c))
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

GROUND_Y = -2.0                                          # низ шин в LDraw (шар опоры на 12 LDU ниже — уходит в подставку, не видно)
PL_H = LAY['plinth']['h']
CEN = tuple(LAY['robot_center'])                          # середина габарита робота (LDraw) — над точкой (0,0)
ROBOT = empty('robot', (0, 0, PL_H))                     # едет вдоль X
BODY = empty('robot_body', -ld2b(CEN), ROBOT)
G = {'body': BODY}
for g in ('wheels', 'lift', 'clawL', 'clawR', 'g2', 'g3'):
    par = G[PARENT[g]]
    G[g] = empty('grp_' + g, ld2b(PIV[g]) - ld2b(PIV[PARENT[g]]), par)
for p, name, c, M in PARTS:
    g = group_of(p)
    o = bpy.data.objects.new(f'p{p.replace("/", "_")}_{name}', part_mesh(name, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    o.matrix_basis = Matrix.Translation(-ld2b(PIV[g])) @ to_b(M)

# ------------------------------------------------------------------ кубик (реквизит), подставка, ловец теней
CUBE_LDU = LAY['cube']['size']
bpy.ops.mesh.primitive_cube_add(size=CUBE_LDU / 20.0)
CUBE = bpy.context.active_object; CUBE.name = 'cube'
bv = CUBE.modifiers.new('bev', 'BEVEL'); bv.width = 0.12; bv.segments = 4
for pg in CUBE.data.polygons:
    pg.use_smooth = True
CUBE.data.materials.append(mat('cube', LAY['cube']['color'], 0.45))

bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth'].get('color', '#F7FBF3'), 0.55))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ сценарий: путь робота, лапы, подъём
def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
D1, D2 = LAY['travel']['approach'], LAY['travel']['carry']          # LDU
S0 = -(D1 + D2) / 2                                                  # робот: от S0 до B и обратно
A, B = S0 + D1, S0 + D1 + D2                                         # где стоит робот, когда кубик точно между лапами
OPEN, CLOSED, LIFT = math.radians(LAY['claw']['open']), math.radians(LAY['claw']['closed']), math.radians(LAY['lift_deg'])
SYM = {'S0': S0, 'A': A, 'B': B, 'OPEN': OPEN, 'CLOSED': CLOSED}
EVENTS = [(e[0], e[1], e[2], SYM.get(e[3], e[3]), SYM.get(e[4], e[4])) for e in LAY['events']]
def inside(t, spans):
    return any(a <= t < b for a, b in spans)
def state(t):
    s, claw, lift = S0, OPEN, 1.0                        # начало петли: на старте, захват поднят и раскрыт
    for a, b, kind, v0, v1 in EVENTS:                    # события по порядку: последнее начавшееся задаёт значение
        if t < a:
            break
        v = v0 + (v1 - v0) * ease((t - a) / (b - a))
        if kind == 'drive': s = v
        elif kind == 'claw': claw = v
        else: lift = v
    return s, claw, lift, inside(t, LAY['held'])

R_WHEEL = 70.0
def cube_world(lift_frac, s_now):
    # кубик между лапами: x=434, z=107 (LDraw), низ на полу; в захвате поворачивается вместе с рамой вокруг оси подъёма
    c = Vector((434, GROUND_Y - CUBE_LDU / 2, 107))
    piv = Vector(PIV['lift'])
    c = piv + Matrix.Rotation(-LIFT * lift_frac, 3, 'X') @ (c - piv)
    b = ld2b(c) - ld2b(CEN)
    return Vector((b.x + s_now / 20.0, b.y, b.z + PL_H))

last_cube = None
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    s, claw, lift, held = state(t)
    ROBOT.location = (s / 20.0, 0, PL_H)
    G['wheels'].rotation_euler = (0, s / R_WHEEL, 0)                  # ось колёс — LDraw Z = Blender Y
    G['lift'].rotation_euler = (-LIFT * lift, 0, 0)                   # подъём захвата вокруг оси X (минус — нос вверх)
    G['clawL'].rotation_euler = (0, claw, 0)                          # ряд 16z: соседние шестерни крутятся в разные стороны,
    G['g2'].rotation_euler = (0, -claw, 0)                            # поэтому лапы расходятся зеркально (+ = шире)
    G['g3'].rotation_euler = (0, claw, 0)
    G['clawR'].rotation_euler = (0, -claw, 0)
    if held:
        pos = cube_world(lift, s); CUBE.rotation_euler = (-LIFT * lift, 0, 0)
    else:
        pos = cube_world(0.0, B if inside(t, LAY['home_b']) else A); CUBE.rotation_euler = (0, 0, 0)
    CUBE.location = pos
    for o in [ROBOT, CUBE] + [G[g] for g in ('wheels', 'lift', 'clawL', 'clawR', 'g2', 'g3')]:
        o.keyframe_insert('location', frame=f); o.keyframe_insert('rotation_euler', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#F2FAEC'))
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
area('key', (-34, -40, 52), (0, 0, 5), 30, 45000, '#FFE9CC')
area('fill', (46, -34, 22), (0, 0, 5), 26, 12000, '#DDE8FF')
area('rim', (8, 46, 38), (0, 0, 7), 22, 16000, '#FFF4E0')

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

from bpy_extras import anim_utils
for o in bpy.data.objects:
    ad = o.animation_data
    if ad and ad.action:
        cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
        for fc in (cb.fcurves if cb else []):
            for kp in fc.keyframe_points:
                kp.interpolation = 'LINEAR'

# ------------------------------------------------------------------ рендер
r = scn.render; r.engine = 'CYCLES'; r.film_transparent = True
cy = scn.cycles; cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.06
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 1; cy.transmission_bounces = 3; cy.transparent_max_bounces = 3
r.use_persistent_data = True
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGBA'

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4]); cy.samples = int(sys.argv[5])
    for f in map(int, sys.argv[2].split(',')):
        scn.frame_set(f)
        r.filepath = os.path.join(HERE, 'frames', f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5]); cy.samples = int(sys.argv[6])
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
