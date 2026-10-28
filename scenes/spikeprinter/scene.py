"""Видео-петля для страницы SPIKE Prime на legobot.ru: «3D-принтер» с 3D-ручкой печатает квадратную рамку слоями.
Механика (по модели): большой мотор сзади -> вал с 12z -> рейка под столом: стол едет по X;
средний мотор сверху -> 28z -> рейка головки: головка едет по Z; большой мотор в головке -> 12z -> рейка 1x7: каретка с ручкой вверх-вниз;
средний мотор на каретке поворачивает рычаг, который нажимает кнопку ручки. Сценарий и размеры — в layout.json, движение — motion.py.
Модель — секрет MODEL_PRINTER (xz + base64): структура из Studio, все детали — из официальной библиотеки LDraw
(хаб Studio 53444c01 = LDraw 45601c01 вместе с батареей). Если в MPD есть разделы деталей — они кладутся в библиотеку.
  python scene.py test 1,60,150,330 1280 800 12
  python scene.py anim 1 432 1280 800 12
"""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier'))
sys.path.insert(0, HERE)
import ldr
from motion import Motion

FPS, LOOP_S = 24, 18
FRAMES = FPS * LOOP_S                                   # 432
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
MO = Motion(LAY)

# ------------------------------------------------------------------ модель: разделы MPD; детали не из библиотеки — в папку LDraw
text = open(os.path.join(HERE, 'models', 'printer.mpd'), encoding='utf-8-sig', errors='ignore').read().replace('\r', '')
files, cur, order = {}, None, []
for line in text.splitlines():
    if line.startswith('0 FILE '):
        cur = line[7:].strip().lower(); files[cur] = []; order.append(cur); continue
    if line.startswith('0 NOFILE'):
        cur = None; continue
    if cur is not None:
        files[cur].append(line)
MAIN = order[0]
for k in order[1:]:
    if k.startswith('submodel'):
        continue
    p = os.path.join(ldr.LIB, 'parts', k)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    open(p, 'w', encoding='utf-8').write('\n'.join(files[k]) + '\n')
ldr._index = None
ldr.find('3001.dat')
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 1: '#1E5AA8',
            14: '#F5CD2F', 19: '#D9BB7B', 25: '#F07A12', 322: '#36AEBF', 26: '#C0397E'}
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
    if 'Chrome' in name or 'Metal' in name:
        b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.25
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
        if name.lower().startswith('submodel') and name.lower() in files:
            walk(files[name.lower()], W, f'{path}/{k}', c)
        else:
            PARTS.append((f'{path}/{k}', name, c, W))
walk(files[MAIN], Matrix.Identity(4), '', 16)
print('parts', len(PARTS))

# ------------------------------------------------------------------ подвижные узлы
LEVER = {'/73/1/29', '/73/1/30', '/73/1/31', '/73/1/32', '/73/1/33', '/73/1/34'}   # ось мотора на каретке + рычаг кнопки
def group_of(p):
    if p in ('/64', '/65'): return 'hgear'                # 28z и ось на моторе сверху
    if p in ('/73/0/19', '/73/0/20'): return 'cgear'      # 12z подъёма каретки
    if p in LEVER: return 'lever'
    if p.startswith('/73/1/'): return 'carr'
    if p.startswith('/73/'): return 'head'
    if p.startswith('/26/'): return 'bed'
    if p.startswith('/13/0/'): return 'shaft'             # вал стола с двумя 12z и роликом
    return 'body'
PIV = {'body': (0, 0, 0), 'bed': (0, 0, 0), 'shaft': (440, -70, 0), 'hgear': (0, -390, -110), 'head': (0, 0, 0),
       'cgear': (0, -390, 70), 'carr': (0, 0, 0), 'lever': (0, -370, -30)}
PARENT = {'bed': 'body', 'shaft': 'body', 'hgear': 'body', 'head': 'body', 'cgear': 'head', 'carr': 'head', 'lever': 'carr'}

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
            k = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if k not in vidx:
                vidx[k] = len(verts); verts.append(k)
            f.append(vidx[k])
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

PL_H = LAY['plinth']['h']
CEN = tuple(LAY['model_center'])                          # середина габарита (LDraw), низ колёс — на подставке
ROOT = empty('printer', (0, 0, PL_H))
BODY = empty('body', -ld2b(CEN), ROOT)
G = {'body': BODY}
for g in ('bed', 'shaft', 'hgear', 'head', 'cgear', 'carr', 'lever'):
    G[g] = empty('grp_' + g, ld2b(PIV[g]) - ld2b(PIV[PARENT[g]]), G[PARENT[g]])
for p, name, c, M in PARTS:
    g = group_of(p)
    o = bpy.data.objects.new(f'p{p.replace("/", "_")}_{name}', part_mesh(name, c))
    bpy.context.collection.objects.link(o); o.parent = G[g]
    o.matrix_basis = Matrix.Translation(-ld2b(PIV[g])) @ to_b(M)

# ------------------------------------------------------------------ 3D-ручка (на каретке), резинка, бумага и отпечаток (на столе)
def lathe(name, profile, axis_xz, material, parent, seg=48):
    """Тело вращения вокруг вертикали LDraw: profile — [(y, r)], координаты LDraw при нулевых сдвигах."""
    ax, az = axis_xz
    verts, faces = [], []
    for y, r in profile:
        for i in range(seg):
            a = 2 * math.pi * i / seg
            verts.append(tuple(ld2b((ax + r * math.cos(a), y, az + r * math.sin(a)))))
    n = len(profile)
    for j in range(n - 1):
        for i in range(seg):
            a, b = j * seg + i, j * seg + (i + 1) % seg
            faces.append((a, b, b + seg, a + seg))
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update(); me.shade_smooth()
    me.materials.append(material)
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o); o.parent = parent
    return o

PEN = LAY['pen']; tip = PEN['tip_y']; R = PEN['radius']; top = tip - PEN['length']
m_cyan, m_white = mat('pen_cyan', PEN['color'], 0.35), mat('pen_white', PEN['white'], 0.4)
m_metal = mat('pen_nozzle', '#C9CED3', 0.25, 1.0)
lathe('pen_nozzle', [(tip, 0.1), (tip, 2.2), (tip - 22, 6.0)], PEN['axis'], m_metal, G['carr'])
lathe('pen_tipcone', [(tip - 22, 6.0), (tip - 60, 14.0), (tip - 105, R - 3)], PEN['axis'], m_white, G['carr'])
lathe('pen_body', [(tip - 105, R - 3), (tip - 135, R), (top + 40, R)], PEN['axis'], m_cyan, G['carr'])
lathe('pen_cap', [(top + 40, R), (top + 18, R - 2), (top + 6, R - 9), (top, 0.1)], PEN['axis'], m_white, G['carr'])
# кнопка подачи — со стороны рычага (−Z)
bpy.ops.mesh.primitive_cube_add(size=1)
btn = bpy.context.active_object; btn.name = 'pen_button'
btn.scale = (12 / 20, 9 / 20, 24 / 20)
btn.location = ld2b((PEN['axis'][0], -318, PEN['axis'][1] - R - 3))
btn.data.materials.append(m_white); btn.parent = G['carr']
bv = btn.modifiers.new('bev', 'BEVEL'); bv.width = 0.08; bv.segments = 3

def curve_obj(name, pts_ld, radius_ld, material, parent, closed=False):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'
    cu.bevel_depth = radius_ld / 20.0; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts_ld) - 1)
    for i, p in enumerate(pts_ld):
        v = ld2b(p); sp.points[i].co = (v.x, v.y, v.z, 1.0)
    sp.use_cyclic_u = closed
    o = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(o); o.parent = parent
    cu.materials.append(material)
    return o, cu

# резинка: от крючка, вокруг ручки со стороны −X, к другому крючку (крючки 49283 у каретки)
ax, az = PEN['axis']
band = [(380, -550, 0)] + [(ax + (R + 1.5) * math.cos(a), -550, az + (R + 1.5) * math.sin(a))
                           for a in [math.radians(d) for d in range(-60, -301, -15)]] + [(380, -550, 140)]
curve_obj('band', band, 1.6, mat('band', '#F2C21B', 0.5), G['carr'])
# кабель ручки: из колпачка вверх и назад
curve_obj('cable', [(ax, top + 2, az), (ax, top - 30, az), (ax + 10, top - 70, az + 30), (ax + 40, top - 95, az + 90), (ax + 90, top - 105, az + 160)],
          3.5, mat('cable', '#1E1F22', 0.6), G['carr'])

PAP = LAY['paper']
bpy.ops.mesh.primitive_cube_add(size=1)
paper = bpy.context.active_object; paper.name = 'paper'
lo, hi = Vector((PAP['x'][0], -123.4, PAP['z'][0])), Vector((PAP['x'][1], -122.6, PAP['z'][1]))   # лист лежит на шипах стола
paper.location = ld2b((lo + hi) / 2); d = ld2b(hi) - ld2b(lo)
paper.scale = (abs(d.x), abs(d.y), abs(d.z))
paper.data.materials.append(mat('paper', '#FFFFFF', 0.8)); paper.parent = G['bed']

# отпечаток: трубка по всему пути, видимая часть растёт (bevel_factor_end), в конце петли — плавно исчезает
pm = bpy.data.materials.new('print'); pm.use_nodes = True
nt = pm.node_tree; bsdf = nt.nodes['Principled BSDF']; out = nt.nodes['Material Output']
bsdf.inputs['Base Color'].default_value = lin(LAY['print']['color']); bsdf.inputs['Roughness'].default_value = 0.35
tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mix = nt.nodes.new('ShaderNodeMixShader')
nt.links.new(tr.outputs[0], mix.inputs[1]); nt.links.new(bsdf.outputs[0], mix.inputs[2]); nt.links.new(mix.outputs[0], out.inputs['Surface'])
PRINT, PCU = curve_obj('print', MO.path(3.0), LAY['print']['radius'], pm, G['bed'])
PCU.bevel_factor_mapping_end = 'SPLINE'; PCU.bevel_factor_start = 0.0

# ------------------------------------------------------------------ подставка, ловец теней
bpy.ops.mesh.primitive_cylinder_add(vertices=128, radius=1, depth=PL_H, location=(0, 0, PL_H / 2))
PL = bpy.context.active_object; PL.name = 'plinth'; PL.scale = (LAY['plinth']['rx'], LAY['plinth']['ry'], 1)
bpy.ops.object.transform_apply(scale=True)
md = PL.modifiers.new('bev', 'BEVEL'); md.width = 0.3; md.segments = 6; md.limit_method = 'ANGLE'
for pg in PL.data.polygons:
    pg.use_smooth = True
PL.data.materials.append(mat('plinth', LAY['plinth'].get('color', '#F7FBF3'), 0.55))
bpy.ops.mesh.primitive_plane_add(size=400, location=(0, 0, 0))
bpy.context.active_object.is_shadow_catcher = True

# ------------------------------------------------------------------ анимация
for f in range(1, FRAMES + 1):
    t = (f - 1) / FPS
    S = MO.state(t)
    bx, hz, cy = S['bx'], S['hz'], S['cy']
    G['bed'].location = ld2b((bx, 0, 0))
    G['head'].location = ld2b((0, 0, hz))
    G['carr'].location = ld2b((0, cy, 0))
    G['shaft'].rotation_euler = (0, bx / 15.0, 0)          # 12z под рейкой стола: ось LDraw Z = Blender Y
    G['hgear'].rotation_euler = (hz / 35.0, 0, 0)          # 28z над рейкой головки
    G['cgear'].rotation_euler = (-cy / 15.0, 0, 0)         # 12z рядом с рейкой каретки
    G['lever'].rotation_euler = (S['lever'], 0, 0)
    for g in ('bed', 'head', 'carr'):
        G[g].keyframe_insert('location', frame=f)
    for g in ('shaft', 'hgear', 'cgear', 'lever'):
        G[g].keyframe_insert('rotation_euler', frame=f)
    PCU.bevel_factor_end = S['s'] / MO.S; PCU.keyframe_insert('bevel_factor_end', frame=f)
    mix.inputs[0].default_value = S['alpha']; mix.inputs[0].keyframe_insert('default_value', frame=f)

# ------------------------------------------------------------------ свет, мир, камера
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin(LAY.get('world', '#F2FAEC'))
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
area('key', rot_az((-34, -40, 60)), (0, 0, 12), 30, 52000, '#FFE9CC')
area('fill', rot_az((46, -34, 26)), (0, 0, 12), 26, 14000, '#DDE8FF')
area('rim', rot_az((8, 46, 46)), (0, 0, 14), 22, 18000, '#FFF4E0')

cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', tuple(CAM['target']))
cc = cam.constraints.new('TRACK_TO'); cc.target = tgt; cc.track_axis = 'TRACK_NEGATIVE_Z'; cc.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = CAM['lens']
DIST, ELEV, SWING = CAM['dist'], math.radians(CAM['elev']), math.radians(CAM['swing'])
for f in range(1, FRAMES + 1):
    az = AZ0 + SWING * math.sin(2 * math.pi * (f - 1) / FRAMES)
    T = Vector(CAM['target'])
    cam.location = T + Vector((DIST * math.cos(ELEV) * math.sin(az), -DIST * math.cos(ELEV) * math.cos(az), DIST * math.sin(ELEV)))
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
