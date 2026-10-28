"""Видео-петля для первого экрана legobot.ru: три модели WeDo 2.0 на одной подставке.
Робот-курьер шагает на месте, Ёлка-карусель вращается (червяк 1:24) и машет рукой фигурке,
Скрипач водит смычком. Петля 24 с без шва: все механизмы делают целое число оборотов.
Фон прозрачный (film_transparent + ловец теней) — цвет фона сайта подставляет compose.py.
Units: 1 Blender unit = 1 stud, Z up.
  python scene.py test 1,97,193,289 1280 800 12
  python scene.py anim 1 576 1280 800 12
"""
import bpy, bmesh, math, sys, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
import ldr, json

FPS = 24
LOOP_S = 24
FRAMES = FPS * LOOP_S                                   # 576
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 25: '#F07A12',
            10: '#4CC04A', 27: '#A5CA18', 322: '#3EB7E8', 34: '#3BAA4A', 79: '#EDEDE6', 191: '#F8B71B',
            2: '#3BAA4A', 14: '#F5CD2F', 19: '#D9BB7B', 43: '#AEE9EF', 46: '#F5CD2F', 36: '#E8432F'}
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
    if COL.get(code, ('', ''))[0].startswith('Trans') and code != 79:
        b.inputs['Transmission Weight'].default_value = 0.7
        b.inputs['Roughness'].default_value = 0.12
    MATS[code] = m
    return m

def mat(name, hexv, rough=0.5):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    return m

# Ёлка и Скрипач: файлы моделей не лежат в публичном репозитории — workflow кладёт их в models/ из секретов
ldr.find('3001.dat')                                    # строим индекс библиотеки
INLINE = os.path.join(HERE, 'inline'); os.makedirs(INLINE, exist_ok=True)
def read_model(fname):
    """главный файл модели (+ вложенные подмодели MPD записываются в inline/ и индексируются)"""
    text = open(os.path.join(HERE, fname), encoding='utf-8-sig', errors='ignore').read()
    lines = text.splitlines(True)
    files, cur, order = {}, None, []
    for line in lines:
        t = line.split()
        if len(t) >= 3 and t[0] == '0' and t[1] == 'FILE':
            cur = ' '.join(t[2:]); files[cur] = []; order.append(cur); continue
        if len(t) >= 2 and t[0] == '0' and t[1] == 'NOFILE':
            cur = None; continue
        if not order:
            cur = '__main__'; files[cur] = []; order.append(cur)
        if cur is not None:
            files[cur].append(line)
    for name in order[1:]:
        p = os.path.join(INLINE, name)
        open(p, 'w', encoding='utf-8').writelines(files[name])
        ldr._index[name.lower()] = p
    return [l for l in files[order[0]] if l.split()[:1] == ['1'] and len(l.split()) >= 15]

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

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))          # LDraw (x, y вниз, z) LDU -> Blender (x, z, -y)/20
def ld2b(p):
    return C @ Vector(p) / 20.0
def ld_matrix(R, pos):
    return Matrix.Translation(ld2b(pos)) @ (C @ Matrix(R) @ C.transposed()).to_4x4()

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None); bpy.context.collection.objects.link(o)
    o.location = loc
    if parent is not None:
        o.parent = parent
    return o

# ------------------------------------------------------------------ модели и подвижные группы (индексы строк типа 1)
MODELS = {
    'kurer': dict(file='../courier/model.mpd', at=(-340, -40), yaw=-60, groups={
        'axF': ([6, 7, 8, 9, 64, 65, 66, 77, 78, 79], (0, 0, 0)),
        'axR': ([10, 11, 67, 68, 69, 80, 81, 82], (0, 0, -80)),
        'worm': ([14, 16, 17], (0, -40, 0)),
        'legL': (list(range(70, 77)), (-70, 20, 0)),
        'legR': (list(range(83, 90)), (70, -20, 0))}),
    'elka': dict(file='models/elka.mpd', at=(10, 200), yaw=20, groups={
        'shaft': ([19, 20, 21, 22, 23, 24, 25], (-40, -62, 0)),
        'tree': (list(range(52, 84)), (0, 0, 0)),
        'rod': ([26], (-82.0431, -84.8063, -98)),
        'rocker': ([50, 27], (-160, -110, -68))}),
    'skripach': dict(file='models/skripach.ldr', at=(330, -40), yaw=25, groups={
        'crank': ([25, 26, 27, 28, 29], (100, -70, 0)),
        'pinion': ([21, 22], (100, -30, 0)),
        'bow': ([30, 31], (100, -90, -70)),
        'pivotc': ([32], (-60, -110, -70))}),
}
# расстановка, подставка и камера — в layout.json (правится без изменения кода)
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
for k, v in LAY['models'].items():
    MODELS[k]['at'], MODELS[k]['yaw'] = tuple(v['at']), v['yaw']
PLINTH_H = LAY['plinth']['h']                           # высота подставки, studs
G = {}                                                  # (модель, группа) -> empty
LIFT = {}
for key, cfg in MODELS.items():
    lines = read_model(cfg['file'])
    owner = {i: g for g, (idx, _) in cfg['groups'].items() for i in idx}
    # центр модели по габаритам деталей (как в черновой компоновке): x/z — середина, низ — по самой нижней точке
    lo = [1e9] * 3; hi = [-1e9] * 3
    for l in lines:
        t = l.split(); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
        bb = ldr.bbox(pid)
        if not bb:
            continue
        for cx in (0, 1):
            for cy in (0, 1):
                for cz in (0, 1):
                    p = Vector((bb[cx][0], bb[cy][1], bb[cz][2]))
                    w = ld_matrix([v[3:6], v[6:9], v[9:12]], v[0:3]) @ p
                    for i in range(3):
                        lo[i] = min(lo[i], w[i]); hi[i] = max(hi[i], w[i])
    centre = Vector(((lo[0] + hi[0]) / 2, (lo[1] + hi[1]) / 2, lo[2]))
    root = empty(key, (cfg['at'][0] / 20, cfg['at'][1] / 20, PLINTH_H))
    root.rotation_euler = (0, 0, -math.radians(cfg['yaw']))
    lift = empty(key + '_lift', (0, 0, 0), root); LIFT[key] = lift
    body = empty(key + '_body', -centre, lift)
    grp = {'static': body}
    for g, (_, piv) in cfg['groups'].items():
        grp[g] = empty(f'{key}_{g}', ld2b(piv), body); G[(key, g)] = grp[g]
    for k, l in enumerate(lines):
        t = l.split(); c = int(t[1]); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
        g = owner.get(k, 'static')
        o = bpy.data.objects.new(f'{key}_{k:03d}_{pid}', part_mesh(pid, c))
        bpy.context.collection.objects.link(o); o.parent = grp[g]
        piv = ld2b(cfg['groups'][g][1]) if g != 'static' else Vector((0, 0, 0))
        o.matrix_basis = Matrix.Translation(-piv) @ ld_matrix([v[3:6], v[6:9], v[9:12]], v[0:3])

# ------------------------------------------------------------------ кинематика (в координатах LDraw)
def th(f, rev_per_s):
    return 2 * math.pi * rev_per_s * (f - 1) / FPS

def circ(A, R, P, r, prev):
    """точка на окружности (P, r) на расстоянии R от A, ближайшая к prev"""
    dx, dy = A[0] - P[0], A[1] - P[1]; d = math.hypot(dx, dy)
    a = (r * r - R * R + d * d) / (2 * d); h = math.sqrt(max(0.0, r * r - a * a))
    bx, by = P[0] + a * dx / d, P[1] + a * dy / d
    c1 = (bx - h * dy / d, by + h * dx / d); c2 = (bx + h * dy / d, by - h * dx / d)
    return c1 if math.dist(c1, prev) < math.dist(c2, prev) else c2
ang = lambda p, q: math.atan2(q[1] - p[1], q[0] - p[0])

B_prev = (-124.086, -127.612)
for f in range(1, FRAMES + 1):
    # Робот-курьер: 0,5 об/с, кривошипы со сдвигом 180°, ноги идут по кругу r=20 LDU, корпус на опорной ноге
    a = th(f, 0.5)
    for g in ('axF', 'axR'):
        G[('kurer', g)].rotation_euler = (a, 0, 0)
    G[('kurer', 'worm')].rotation_euler = (0, -24 * a, 0)
    G[('kurer', 'legL')].location = ld2b((-70, 20 * math.cos(a), 20 * math.sin(a)))
    G[('kurer', 'legR')].location = ld2b((70, -20 * math.cos(a), -20 * math.sin(a)))
    LIFT['kurer'].location = (0, 0, -(20 - 20 * abs(math.cos(a))) / 20)
    # Ёлка-карусель: вал 1 об/с, ёлка 1/24 (ровно один оборот за петлю), кривошип -> тяга -> рука
    a = th(f, 1.0)
    G[('elka', 'shaft')].rotation_euler = (0, a, 0)
    G[('elka', 'tree')].rotation_euler = (0, 0, a / 24)
    A = (-40 - 20 * math.sin(a), -62 + 20 * math.cos(a))
    B = circ(A, 120, (-160, -110), 40, B_prev); B_prev = B
    G[('elka', 'rocker')].rotation_euler = (0, ang((-160, -110), B) - ang((-160, -110), (-124.086, -127.612)), 0)
    G[('elka', 'rod')].location = ld2b(((A[0] + B[0]) / 2, (A[1] + B[1]) / 2, -98))
    G[('elka', 'rod')].rotation_euler = (0, ang(A, B) - ang((-40, -42), (-124.086, -127.612)), 0)
    # Скрипач: кривошип 0,5 об/с, шестерня 8z на моторе втрое быстрее, смычок скользит через шарнир
    a = th(f, 0.5)
    G[('skripach', 'crank')].rotation_euler = (0, a, 0)
    G[('skripach', 'pinion')].rotation_euler = (0, -3 * a, 0)
    A = (100 + 20 * math.sin(a), -70 - 20 * math.cos(a))
    da = ang(A, (-60, -110)) - math.atan2(-20, -160)
    G[('skripach', 'bow')].location = ld2b((A[0], A[1], -70))
    G[('skripach', 'bow')].rotation_euler = (0, da, 0)
    G[('skripach', 'pivotc')].rotation_euler = (0, da, 0)
    for o in list(G.values()) + list(LIFT.values()):
        o.keyframe_insert('rotation_euler', frame=f); o.keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ подставка + ловец теней
def plinth(rx, ry, h, bevel):
    bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=h, location=(0, 0, h / 2))
    o = bpy.context.active_object; o.name = 'plinth'; o.scale = (rx, ry, 1)
    bpy.ops.object.transform_apply(scale=True)
    md = o.modifiers.new('bev', 'BEVEL'); md.width = bevel; md.segments = 6; md.limit_method = 'ANGLE'
    for p in o.data.polygons:
        p.use_smooth = True
    o.data.materials.append(mat('plinth', '#F7FBF3', 0.55))
    return o
PL = plinth(LAY['plinth']['rx'], LAY['plinth']['ry'], PLINTH_H, 0.3)
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
floor = bpy.context.active_object; floor.name = 'shadow_catcher'; floor.is_shadow_catcher = True

world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F2FAEC')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.6

# ------------------------------------------------------------------ камера: медленный проезд по дуге, петля без шва
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
CAM = LAY['camera']
tgt = empty('cam_target', tuple(CAM['target']))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = 5.6
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    u = math.sin(2 * math.pi * (f - 1) / FRAMES)
    az = SWING * u
    T = Vector(CAM['target'])
    cam.location = T + Vector((DIST * math.cos(ELEV) * math.sin(az), -DIST * math.cos(ELEV) * math.cos(az), DIST * math.sin(ELEV)))
    cam.keyframe_insert('location', frame=f)

# ------------------------------------------------------------------ свет: мягкий дневной, тёплый ключ, холодная заливка
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power; ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.visible_camera = False
    return o
area('key', (-34, -40, 52), (0, 0, 5), 30, 45000, '#FFE9CC')
area('fill', (46, -34, 22), (0, 0, 5), 26, 12000, '#DDE8FF')
area('rim', (8, 46, 38), (0, 0, 7), 22, 16000, '#FFF4E0')

# все анимационные кривые — линейные (иначе на стыке петли будет замедление)
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
elif mode == 'save':
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'legobot_hero3.blend'))
