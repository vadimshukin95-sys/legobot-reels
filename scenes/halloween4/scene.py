"""«Сладость или гадость?» — 4 конструктора, 4 хэллоуинских мастер-класса LEGObot (рилс).
Ночная улица под луной: камера едет от «крыльца» к «крыльцу», гостя изображает луч фонарика.
Модели и механика — из мастер-классов (models/*.json, LDraw LDU, подвижные детали mov=True):
  WeDo 2.0        — датчик движения -> мотор 0,6 с -> 8z/24z -> призрак встаёт, через 3 с падает
  SPIKE Prime     — датчик расстояния < 15 см -> мотор B 90° -> мышь взлетает из-за тыквы-хаба
  SPIKE Essential — датчик цвета: жёлтая «конфета» -> «Ам!», шляпа ↺60° и обратно; красная -> шляпа клацает
  EV3             — ультразвук -> смех, мотор вскидывает руки пугала -> опускает, ждёт 2 с
Units: 1 Blender unit = 1 stud, Z up, camera at -Y.
  python scene.py test 1,120,300 360 640 8     -> test/*.png
  python scene.py anim 1 756 1080 1920 12      -> frames/f0001.png ...
  python scene.py proj                          -> proj.json (экранные точки для подписей)
"""
import bpy, bmesh, math, sys, json, os, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ldr

TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FPS, FRAMES = TL['fps'], TL['frames']
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start, scn.frame_end = 1, FRAMES
COL = ldr.colours()

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

# real set colours (WeDo 45300 / SPIKE / EV3), slightly brightened for the night light
OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 25: '#F07A12',
            10: '#4CC04A', 27: '#A5CA18', 322: '#3EB7E8', 34: '#3BAA4A', 79: '#EDEDE6', 14: '#F5CD2F',
            191: '#F8BB3D', 1: '#1E5AA8', 19: '#E4CD9E', 2: '#2A8A3E', 5: '#C870A0', 26: '#C64587'}
MATS = {}
def plastic(code):
    if code in MATS:
        return MATS[code]
    hexv = OVERRIDE.get(code) or ('#' + COL.get(code, ('x', '888888'))[1])
    m = bpy.data.materials.new(f'ld_{code}')
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv)
    b.inputs['Roughness'].default_value = 0.3
    b.inputs['Coat Weight'].default_value = 0.3
    b.inputs['Coat Roughness'].default_value = 0.12
    name = COL.get(code, ('', ''))[0]
    if 'Trans' in name:
        b.inputs['Transmission Weight'].default_value = 0.9
        b.inputs['Roughness'].default_value = 0.05
    MATS[code] = m
    return m

def mat(name, hexv, rough=0.5, coat=0.0, emit=None, es=0.0, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Metallic'].default_value = metal
    if emit:
        b.inputs['Emission Color'].default_value = lin(emit); b.inputs['Emission Strength'].default_value = es
    return m

def emissive(name, hexv, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    e = nt.nodes.new('ShaderNodeEmission'); e.inputs['Color'].default_value = lin(hexv); e.inputs['Strength'].default_value = strength
    o = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(e.outputs[0], o.inputs[0])
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
    me = bpy.data.meshes.new(part.replace('.dat', '') + f'_{color}')
    me.from_pydata(verts, [], faces)
    for c in codes:
        me.materials.append(plastic(c))
    me.polygons.foreach_set('material_index', mats)
    me.update()
    me.shade_smooth()
    me.set_sharp_from_angle(angle=math.radians(38))
    MESHES[key] = me
    return me

C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))     # LDraw (x, y down, z) -> Blender (x, z, -y)
def ld2b(p):
    return C @ Vector(p) / 20.0
def ld_matrix(R, pos):
    return Matrix.Translation(ld2b(pos)) @ (C @ Matrix(R) @ C.transposed()).to_4x4()

def empty(name, loc=(0, 0, 0), parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o); o.location = loc
    if parent:
        o.parent = parent
    return o

def link(o):
    bpy.context.collection.objects.link(o); return o

# ------------------------------------------------------------------ models on the street
STOPS = TL['stops']                      # wedo, prime, essential, ev3 (in street order)
XS = {s['id']: s['x'] for s in STOPS}
ROOT, PIV, OBJ, MOV = {}, {}, {}, {}

def load_model(mid, pivot_ld=None, axis='X', is_mov=None, extra_pivot=None):
    P = json.load(open(os.path.join(HERE, 'models', mid + '.json')))
    root = empty(mid + '_root')
    ROOT[mid] = root
    pv = None
    if pivot_ld is not None:
        pv = empty(mid + '_pivot', ld2b(pivot_ld), root)
        PIV[mid] = pv
    objs = {}
    for i, p in enumerate(P):
        pid = p['pid'] if p['pid'].endswith('.dat') else p['pid'] + '.dat'
        o = link(bpy.data.objects.new(f"{mid}_{p['name']}_{i}", part_mesh(pid, p['color'])))
        Mw = ld_matrix(p['R'], p['pos'])
        mv = is_mov(p) if is_mov else p.get('mov', False)
        if mv and pv is not None:
            o.parent = pv
            o.matrix_basis = Matrix.Translation(-pv.location) @ Mw
        elif extra_pivot and extra_pivot[1](p):
            ep = extra_pivot[0]
            o.parent = ep
            o.matrix_basis = Matrix.Translation(-ep.location) @ Mw
        else:
            o.parent = root
            o.matrix_basis = Mw
        objs.setdefault(p['name'], []).append(o)
    OBJ[mid] = objs
    return root

def wedo_arm(p):
    n = p['name']
    return n in ('spine', 'armhub', 'g24', 'axle4') or (n.startswith(('row', 'br', 'eye')) and n not in ('eyeL', 'eyeR'))

# WeDo 2.0: arm pivot on axle 4 (24z), motor 8z on axle 2
load_model('wedo', (0, -70, 10), is_mov=wedo_arm)
g8p = empty('wedo_g8', ld2b((0, -30, 10)), ROOT['wedo'])
for nm in ('axle2', 'g8'):
    for o in OBJ['wedo'][nm]:
        Mw = o.matrix_basis.copy()
        o.parent = g8p; o.matrix_basis = Matrix.Rotation(math.radians(22.5), 4, 'X') @ Matrix.Translation(-g8p.location) @ Mw
load_model('prime', (0, -170, 60))          # bat on the motor disc, rotation about X (0 = up, -90 = rest)
load_model('essential', (-110, -118, 0))    # lid on the motor disc, rotation about Blender Y (-ANG)
load_model('ev3', (0, -250, 0))             # arms on the 12L shaft, rotation about X (-ANG)

def world_bbox(objs):
    lo, hi = Vector((1e9,) * 3), Vector((-1e9,) * 3)
    bpy.context.view_layer.update()
    for o in objs:
        for v in o.bound_box:
            w = o.matrix_world @ Vector(v)
            lo = Vector(map(min, lo, w)); hi = Vector(map(max, hi, w))
    return lo, hi

def model_objs(mid):
    return [o for l in OBJ[mid].values() for o in l]

BB = {}
for s in STOPS:
    mid = s['id']
    lo, hi = world_bbox(model_objs(mid))
    ROOT[mid].location = (s['x'] - (lo.x + hi.x) / 2, -(lo.y + hi.y) / 2, -lo.z)
    ROOT[mid].rotation_euler.z = math.radians(s.get('yaw', 0))
bpy.context.view_layer.update()
for s in STOPS:
    BB[s['id']] = world_bbox(model_objs(s['id']))

def wpos(mid, name, off=(0, 0, 0)):
    o = OBJ[mid][name][0]
    return o.matrix_world.translation + Vector(off)

# ------------------------------------------------------------------ hub / brick lights
def led_material_slot(objs, code_names):
    pass

# WeDo hub LED (light pipe colour 79): blue idle, red on trigger
wedo_led = plastic(79).node_tree.nodes['Principled BSDF']

def face_grid(name, centre, size, n, pattern, parent, col_off='#3A2C1C'):
    """n x n square 'pixels' on a vertical plane facing -Y (hub light matrix / EV3 screen pixels)"""
    root = empty(name, centre, parent)
    cells = []
    pitch = size / n
    for r in range(n):
        for c in range(n):
            me = bpy.data.meshes.new(f'{name}_{r}_{c}'); bm = bmesh.new()
            bmesh.ops.create_cube(bm, size=1)
            bmesh.ops.scale(bm, vec=(pitch * 0.72, 0.04, pitch * 0.72), verts=bm.verts)
            bm.to_mesh(me); bm.free()
            o = link(bpy.data.objects.new(f'{name}_{r}_{c}', me)); o.parent = root
            o.location = ((c - (n - 1) / 2) * pitch, 0, ((n - 1) / 2 - r) * pitch)
            cells.append((r, c, o))
    return root, cells

# ------------------------------------------------------------------ props
def lathe(name, prof, N=64, ridges=0, ridge_amp=0.0):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); rings = []
    for i in range(N):
        a = 2 * math.pi * i / N
        k = 1 + (ridge_amp * abs(math.cos(ridges * a / 2)) if ridges else 0)
        rings.append([bm.verts.new((r * k * math.cos(a), r * k * math.sin(a), z)) for r, z in prof])
    for i in range(N):
        A, B = rings[i], rings[(i + 1) % N]
        for j in range(len(prof) - 1):
            bm.faces.new((A[j], B[j], B[j + 1], A[j + 1]))
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-4)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    return link(bpy.data.objects.new(name, me))

CANDY_COLS = ['#F07A12', '#7B3FB8', '#4CC04A', '#F5CD2F', '#E8E8E8', '#C91A09']
def candy(name, loc, rz, ry, col):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.42)
    for v in bm.verts:
        v.co.x *= 1.35
    for sgn in (-1, 1):
        r = bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.05, radius2=0.38, depth=0.45)
        M = Matrix.Translation((sgn * 0.78, 0, 0)) @ Matrix.Rotation(math.radians(90 * sgn), 4, 'Y')
        bmesh.ops.transform(bm, matrix=M, verts=r['verts'])
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = link(bpy.data.objects.new(name, me))
    o.location = loc; o.rotation_euler = (0, math.radians(ry), math.radians(rz))
    o.data.materials.append(mat(name, col, 0.18, coat=1.0))
    return o

def pail(name, centre, rnd):
    """orange jack-o'-lantern trick-or-treat pail full of candies"""
    prof = [(0.0, 0.0), (2.0, 0.0), (2.6, 0.3), (3.1, 1.2), (3.2, 2.2), (3.0, 3.1), (2.75, 3.4),
            (2.6, 3.4), (2.82, 3.05), (3.0, 2.2), (2.9, 1.25), (2.45, 0.42), (0.0, 0.36)]
    o = lathe(name, prof, 72, ridges=8, ridge_amp=0.05)
    o.location = centre; o.scale = (0.8, 0.8, 0.8)
    o.data.materials.append(mat(name, '#F07A12', 0.35, coat=0.5))
    # handle
    cd = bpy.data.curves.new(name + '_h', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = 0.09
    sp = cd.splines.new('BEZIER'); sp.bezier_points.add(2)
    for bp, q in zip(sp.bezier_points, [(-2.75, 0, 3.2), (0, 0, 6.0), (2.75, 0, 3.2)]):
        bp.co = q; bp.handle_left_type = bp.handle_right_type = 'AUTO'
    h = link(bpy.data.objects.new(name + '_h', cd)); h.parent = o; h.rotation_euler.z = 0.5
    cd.materials.append(mat(name + '_hm', '#232529', 0.4))
    k = 0
    for ring_r, n, z in ((0.0, 1, 3.0), (1.2, 5, 3.0), (2.0, 7, 3.2), (1.0, 4, 3.6)):
        for j in range(n):
            a = 2 * math.pi * j / max(n, 1) + rnd.uniform(-0.3, 0.3)
            loc = Vector((ring_r * math.cos(a), ring_r * math.sin(a), z + rnd.uniform(-0.1, 0.15)))
            candy(f'{name}_c{k}', loc, rnd.uniform(0, 180), rnd.uniform(-25, 25), CANDY_COLS[k % 6]).parent = o; k += 1

rnd = random.Random(7)
for s in STOPS:
    if s.get('pail'):
        pail(s['id'] + '_pail', Vector((s['x'], 0, 0)) + Vector(s['pail']), rnd)

# Essential: «конфеты» = кирпичики 1x2 из набора, подъезжают к датчику цвета
CANDY_BRICKS = {}
for code, nm in ((14, 'yellow'), (4, 'red')):
    o = link(bpy.data.objects.new('candy_' + nm, part_mesh('3004.dat', code)))
    o.rotation_euler.z = math.radians(90)
    CANDY_BRICKS[nm] = o

# ------------------------------------------------------------------ street: baseplates, houses, fence, sky
def box(name, x0, x1, y0, y1, z0, z1, material):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((x0 + (v.co.x + .5) * (x1 - x0), y0 + (v.co.y + .5) * (y1 - y0), z0 + (v.co.z + .5) * (z1 - z0)))
    bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); me.materials.append(material)
    return o

ground_m = mat('ground', '#1C2746', 0.75)
box('ground', -200, 380, -160, 400, -0.6, -0.4, ground_m)
# a dark-blue 32x32 LEGO baseplate under every porch (real part 3811)
bp_me = part_mesh('3811.dat', 272)
for s in STOPS:
    o = link(bpy.data.objects.new(s['id'] + '_plate', bp_me))
    o.location = (s['x'], 4, -0.4)
# path stones between porches
stone_m = mat('stone', '#2B3A63', 0.6, coat=0.2)
for i in range(-6, 52):
    x = -40 + i * 4.2 + rnd.uniform(-0.6, 0.6)
    box(f'stone{i}', x, x + 3.2, -24 - rnd.uniform(0, 1), -20.5, -0.4, -0.1, stone_m)

house_m = mat('house', '#0E1630', 0.9)
roof_m = mat('roof', '#0A1026', 0.9)
win_m = emissive('win', '#FFB84A', 6.0)
win2_m = emissive('win2', '#FF8A3A', 4.0)
def house(x, y, w, h, d=18):
    box(f'house{x}', x - w / 2, x + w / 2, y, y + d, -0.5, h, house_m)
    me = bpy.data.meshes.new(f'roof{x}'); bm = bmesh.new()
    v = [bm.verts.new(q) for q in ((x - w / 2 - 2, y - 1, h), (x + w / 2 + 2, y - 1, h), (x, y - 1, h + w * 0.45),
                                   (x - w / 2 - 2, y + d + 1, h), (x + w / 2 + 2, y + d + 1, h), (x, y + d + 1, h + w * 0.45))]
    for f in ((0, 1, 2), (3, 5, 4), (0, 3, 4, 1), (1, 4, 5, 2), (2, 5, 3, 0)):
        bm.faces.new([v[i] for i in f])
    bm.to_mesh(me); bm.free()
    link(bpy.data.objects.new(f'roof{x}', me)).data.materials.append(roof_m)
    for i in range(int(w // 9)):
        for j in range(int(h // 11)):
            if rnd.random() < 0.55:
                wx = x - w / 2 + 4 + i * 9; wz = 5 + j * 11
                box(f'w{x}_{i}_{j}', wx, wx + 4, y - 0.3, y, wz, wz + 5.5, win_m if rnd.random() < 0.7 else win2_m)
for x, w, h in ((-60, 34, 30), (-14, 30, 40), (30, 38, 28), (76, 30, 44), (118, 36, 32), (164, 32, 38), (208, 40, 30), (252, 30, 42)):
    house(x, 70 + rnd.uniform(-6, 10), w, h)

# picket fence behind the porches
fence_m = mat('fence', '#141C38', 0.8)
for i in range(0, 120):
    x = -70 + i * 2.6
    box(f'pk{i}', x, x + 1.4, 26, 26.6, -0.4, 7 + (0.8 if i % 2 else 0), fence_m)
box('rail1', -70, 245, 26.6, 27.1, 2.2, 2.9, fence_m); box('rail2', -70, 245, 26.6, 27.1, 5.0, 5.7, fence_m)

# bare tree silhouettes
tree_m = mat('tree', '#0A0F22', 0.9)
def tree(x, y, h, seed):
    r = random.Random(seed)
    def branch(p, d, l, rad, depth):
        q = p + d * l
        cd = bpy.data.curves.new(f'tr{seed}', 'CURVE'); cd.dimensions = '3D'; cd.bevel_depth = rad
        sp = cd.splines.new('POLY'); sp.points.add(1)
        sp.points[0].co = (*p, 1); sp.points[1].co = (*q, 1)
        link(bpy.data.objects.new(f'tr{seed}', cd)).data.materials.append(tree_m)
        if depth < 4:
            for _ in range(2):
                nd = (d + Vector((r.uniform(-0.8, 0.8), r.uniform(-0.3, 0.3), r.uniform(0.0, 0.6)))).normalized()
                branch(q, nd, l * 0.68, rad * 0.62, depth + 1)
    branch(Vector((x, y, -0.5)), Vector((0, 0, 1)), h, 1.1, 0)
tree(-40, 46, 26, 1); tree(98, 50, 30, 2); tree(236, 44, 24, 3)

# moon
MOON = Vector(TL['moon']['pos'])
moon_me = bpy.data.meshes.new('moon'); bm = bmesh.new()
bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=TL['moon']['r'])
bm.to_mesh(moon_me); bm.free()
moon = link(bpy.data.objects.new('moon', moon_me)); moon.location = MOON
mm = bpy.data.materials.new('moon'); mm.use_nodes = True; nt = mm.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 3.5
nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = lin('#D9D2B0'); ramp.color_ramp.elements[1].color = lin('#FFF8DC')
ramp.color_ramp.elements[0].position = 0.42; ramp.color_ramp.elements[1].position = 0.6
nt.links.new(ns.outputs['Fac'], ramp.inputs['Fac'])
em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 3.2
nt.links.new(ramp.outputs['Color'], em.inputs['Color'])
out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(em.outputs[0], out.inputs[0])
moon_me.materials.append(mm)
moon.visible_shadow = False
# soft halo behind the moon
halo_me = bpy.data.meshes.new('halo'); bm = bmesh.new()
bmesh.ops.create_circle(bm, cap_ends=True, segments=64, radius=TL['moon']['r'] * 2.6)
bm.to_mesh(halo_me); bm.free()
halo = link(bpy.data.objects.new('halo', halo_me)); halo.location = MOON + Vector((0, 8, 0)); halo.rotation_euler.x = math.radians(90)
hm = bpy.data.materials.new('halo'); hm.use_nodes = True; nt = hm.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'
mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1 / (TL['moon']['r'] * 2.6),) * 3
nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs[0], gr.inputs['Vector'])
pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 2.2
nt.links.new(gr.outputs['Fac'], pw.inputs[0])
em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = lin('#9DB8FF'); em.inputs['Strength'].default_value = 1.4
tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
nt.links.new(pw.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(mx.outputs[0], out.inputs[0])
halo_me.materials.append(hm); halo.visible_shadow = False
hm.blend_method = 'BLEND' if hasattr(hm, 'blend_method') else None

# bats flying across the moon (flat silhouettes)
bat_m = emissive('batsil', '#05070F', 0.0)
BATS = []
def bat_sil(i):
    me = bpy.data.meshes.new(f'bat{i}'); bm = bmesh.new()
    pts = [(-3, 0), (-1.8, 0.9), (-1.0, 0.3), (-0.5, 0.8), (0, 0.2), (0.5, 0.8), (1.0, 0.3), (1.8, 0.9), (3, 0), (1.2, -0.3), (0, -0.8), (-1.2, -0.3)]
    v = [bm.verts.new((x, 0, z)) for x, z in pts]
    bm.faces.new(v); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(f'bat{i}', me)); me.materials.append(bat_m); o.visible_shadow = False
    BATS.append(o); return o
for i, b in enumerate(TL['bats']):
    o = bat_sil(i); o.scale = (b['s'],) * 3
    for f, p in b['keys']:
        o.location = MOON + Vector(p); o.keyframe_insert('location', frame=f)
    for k in range(0, FRAMES, 5):     # wing flap: scale z
        o.scale.z = b['s'] * (1.0 if (k // 5) % 2 else 0.35); o.keyframe_insert('scale', index=2, frame=k + 1)

# low fog cards
fog_m = bpy.data.materials.new('fog'); fog_m.use_nodes = True; nt = fog_m.node_tree; nt.nodes.clear()
tc = nt.nodes.new('ShaderNodeTexCoord'); ns = nt.nodes.new('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 0.05; ns.inputs['Detail'].default_value = 3
nt.links.new(tc.outputs['Object'], ns.inputs['Vector'])
gz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], gz.inputs[0])
inv = nt.nodes.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0
nt.links.new(gz.outputs['Z'], inv.inputs[1])
m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; nt.links.new(inv.outputs[0], m1.inputs[0]); nt.links.new(ns.outputs['Fac'], m1.inputs[1])
m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; m2.inputs[1].default_value = 0.55; nt.links.new(m1.outputs[0], m2.inputs[0])
em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = lin('#8FA6D8'); em.inputs['Strength'].default_value = 0.35
tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
nt.links.new(m2.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(mx.outputs[0], out.inputs[0])
for i, (y, h) in enumerate(((18, 6), (34, 9), (55, 12))):
    me = bpy.data.meshes.new(f'fog{i}'); bm = bmesh.new()
    v = [bm.verts.new(q) for q in ((-220, y, -0.3), (420, y, -0.3), (420, y, h), (-220, y, h))]
    bm.faces.new(v); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(f'fog{i}', me)); me.materials.append(fog_m); o.visible_shadow = False

# sky: vertical gradient + stars (world shader)
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True; nt = world.node_tree
bg = nt.nodes['Background']
tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sep.inputs[0])
ramp = nt.nodes.new('ShaderNodeValToRGB')
ramp.color_ramp.elements[0].position = 0.0; ramp.color_ramp.elements[0].color = lin('#3D5A9E')
ramp.color_ramp.elements[1].position = 0.45; ramp.color_ramp.elements[1].color = lin('#0B1838')
nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
vor = nt.nodes.new('ShaderNodeTexVoronoi'); vor.inputs['Scale'].default_value = 420; vor.feature = 'DISTANCE_TO_EDGE' if False else 'F1'
nt.links.new(tc.outputs['Generated'], vor.inputs['Vector'])
lt = nt.nodes.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; lt.inputs[1].default_value = 0.035
nt.links.new(vor.outputs['Distance'], lt.inputs[0])
hz = nt.nodes.new('ShaderNodeMath'); hz.operation = 'GREATER_THAN'; hz.inputs[1].default_value = 0.53
nt.links.new(sep.outputs['Z'], hz.inputs[0])
st = nt.nodes.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; nt.links.new(lt.outputs[0], st.inputs[0]); nt.links.new(hz.outputs[0], st.inputs[1])
st2 = nt.nodes.new('ShaderNodeMath'); st2.operation = 'MULTIPLY'; st2.inputs[1].default_value = 3.0; nt.links.new(st.outputs[0], st2.inputs[0])
add = nt.nodes.new('ShaderNodeMix'); add.data_type = 'RGBA'; add.blend_type = 'ADD'
nt.links.new(st2.outputs[0], add.inputs['Factor']); nt.links.new(ramp.outputs['Color'], add.inputs['A'])
add.inputs['B'].default_value = (1, 1, 0.92, 1)
nt.links.new(add.outputs['Result'], bg.inputs['Color'])
bg.inputs['Strength'].default_value = 1.0
# the world lights the scene too strongly in blue -> separate the camera-visible sky from lighting
lp = nt.nodes.new('ShaderNodeLightPath'); bg2 = nt.nodes.new('ShaderNodeBackground'); bg2.inputs['Color'].default_value = lin('#2A3C70'); bg2.inputs['Strength'].default_value = 0.35
mx = nt.nodes.new('ShaderNodeMixShader'); nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0])
nt.links.new(bg2.outputs[0], mx.inputs[1]); nt.links.new(bg.outputs[0], mx.inputs[2])
nt.links.new(mx.outputs[0], nt.nodes['World Output'].inputs[0])

# ------------------------------------------------------------------ lights
def light(name, kind, loc, energy, col, size=1.0, rot=None, spot=None):
    ld = bpy.data.lights.new(name, kind); ld.energy = energy; ld.color = lin(col)[:3]
    if kind == 'AREA':
        ld.size = size
    elif kind in ('POINT', 'SPOT'):
        ld.shadow_soft_size = size
    if kind == 'SUN':
        ld.angle = math.radians(size)
    if spot:
        ld.spot_size = math.radians(spot[0]); ld.spot_blend = spot[1]
    o = link(bpy.data.objects.new(name, ld)); o.location = loc
    if rot:
        o.rotation_euler = [math.radians(a) for a in rot]
    return o
# moonlight: cool key from behind-left-above (rim), neutral soft fill from the front so set colours read true
light('moon_key', 'SUN', (0, 0, 100), 2.4, '#B9CCFF', 2.0, rot=(-52, 0, 200))
light('front_fill', 'SUN', (0, 0, 100), 1.6, '#FFF2E2', 8.0, rot=(62, 0, -18))
# warm porch glow for every stop (pumpkin-lantern light)
for s in STOPS:
    light(s['id'] + '_porch', 'POINT', (s['x'] + s.get('porch', 9), -4, 3.0), 900, '#FF8A2A', 1.5)
    light(s['id'] + '_top', 'AREA', (s['x'], -26, 40), 2600, '#FFF4E6', 26, rot=(35, 0, 0))

# flashlight = the trick-or-treater: a spot + visible soft beam, per stop
beam_m = bpy.data.materials.new('beam'); beam_m.use_nodes = True; nt = beam_m.node_tree; nt.nodes.clear()
lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.6
iv = nt.nodes.new('ShaderNodeMath'); iv.operation = 'SUBTRACT'; iv.inputs[0].default_value = 1.0; nt.links.new(lw.outputs['Facing'], iv.inputs[1])
tc = nt.nodes.new('ShaderNodeTexCoord'); sz = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Generated'], sz.inputs[0])
fall = nt.nodes.new('ShaderNodeMath'); fall.operation = 'SUBTRACT'; fall.inputs[0].default_value = 1.0; nt.links.new(sz.outputs['Z'], fall.inputs[1])
mm1 = nt.nodes.new('ShaderNodeMath'); mm1.operation = 'MULTIPLY'; nt.links.new(iv.outputs[0], mm1.inputs[0]); nt.links.new(fall.outputs[0], mm1.inputs[1])
BEAM_K = nt.nodes.new('ShaderNodeMath'); BEAM_K.operation = 'MULTIPLY'; BEAM_K.inputs[1].default_value = 0.0
nt.links.new(mm1.outputs[0], BEAM_K.inputs[0])
em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = lin('#FFE7A8'); em.inputs['Strength'].default_value = 1.6
tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
nt.links.new(BEAM_K.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2])
out = nt.nodes.new('ShaderNodeOutputMaterial'); nt.links.new(mx.outputs[0], out.inputs[0])

beam_me = bpy.data.meshes.new('beam'); bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=40, radius1=0.6, radius2=7.0, depth=1.0)
bmesh.ops.translate(bm, vec=(0, 0, 0.5), verts=bm.verts)     # apex at 0, opens along +Z, length 1
bm.to_mesh(beam_me); bm.free()
for p in beam_me.polygons:
    p.use_smooth = True
beam_me.materials.append(beam_m)
torch = empty('torch')
beam = link(bpy.data.objects.new('beam', beam_me)); beam.parent = torch; beam.visible_shadow = False
beam.visible_diffuse = beam.visible_glossy = False
spot = light('torch_spot', 'SPOT', (0, 0, 0), 0, '#FFE2A0', 0.4, spot=(26, 0.35)); spot.parent = torch
spot.rotation_euler = (math.radians(180), 0, 0)   # spot shines along -Z; torch looks along +Z -> flip
torch_tgt = empty('torch_tgt')
tt = torch.constraints.new('TRACK_TO'); tt.target = torch_tgt; tt.track_axis = 'TRACK_Z'; tt.up_axis = 'UP_Y'

def key_torch(f, pos, tgt, on, length):
    torch.location = pos; torch.keyframe_insert('location', frame=f)
    torch_tgt.location = tgt; torch_tgt.keyframe_insert('location', frame=f)
    spot.data.energy = 30000 * on; spot.data.keyframe_insert('energy', frame=f)
    BEAM_K.inputs[1].default_value = 0.55 * on; BEAM_K.inputs[1].keyframe_insert('default_value', frame=f)
    beam.scale = (1, 1, length); beam.keyframe_insert('scale', frame=f)

# ------------------------------------------------------------------ animation helpers
def fcurves(idb):
    from bpy_extras import anim_utils
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return list(cb.fcurves) if cb else []

def kr(o, f, idx, deg, interp=None):
    o.rotation_euler[idx] = math.radians(deg)
    o.keyframe_insert('rotation_euler', index=idx, frame=f)
    if interp:
        for fc in fcurves(o):
            for kp in fc.keyframe_points:
                if int(round(kp.co.x)) == f:
                    kp.interpolation = interp[0]
                    if len(interp) > 1:
                        kp.easing = interp[1]

def emit_key(node, f, col, strength):
    node.inputs['Emission Color'].default_value = lin(col); node.inputs['Emission Color'].keyframe_insert('default_value', frame=f)
    node.inputs['Emission Strength'].default_value = strength; node.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)

def constant(idb):
    for fc in fcurves(idb):
        for kp in fc.keyframe_points:
            kp.interpolation = 'CONSTANT'

S = {s['id']: s for s in STOPS}
def T(mid, t):
    return S[mid]['f0'] + t

def sensor_point(mid):
    return Vector(S[mid]['sensor_pt']) + Vector((S[mid]['x'], 0, 0))

# torch: off everywhere, swings in for each stop
key_torch(1, (0, -60, 10), (0, 0, 0), 0, 1)
for s in STOPS:
    mid = s['id']; sp = sensor_point(mid)
    side = s.get('torch_side', 1)
    o0 = sp + Vector((side * 34, -36, 9)); o1 = sp + Vector((side * 15, -24, 7))
    tg0 = sp + Vector((side * 10, -6, 0)); tg1 = sp
    a, b, c, d = s['torch']                      # frames: on, arrive, leave, off (local)
    key_torch(T(mid, a) - 1, o0, tg0, 0, (tg0 - o0).length)
    key_torch(T(mid, a) + 2, o0, tg0, 1, (tg0 - o0).length)
    key_torch(T(mid, b), o1, tg1, 1, (tg1 - o1).length)
    key_torch(T(mid, c), o1 + Vector((side * 2, -3, 1)), tg1, 1, (tg1 - o1).length + 2)
    key_torch(T(mid, d), o0, tg0, 0, (tg0 - o0).length)

# ---- WeDo: motor 0,6 s -> ghost up 100° (24z/8z = x3 on the motor), 3 s, back, ghost falls
wedo_arm_p = PIV['wedo']
ev = S['wedo']['ev']; tr0 = ev['trig']
def wedo_key(f, deg, interp=None):
    kr(wedo_arm_p, f, 0, deg, interp); kr(g8p, f, 0, 22.5 - 3 * deg, interp)
wedo_key(1, 0)
wedo_key(T('wedo', tr0 + 1), 0, ('LINEAR',))
wedo_key(T('wedo', tr0 + 14), 100)
wedo_key(T('wedo', tr0 + 16), 103); wedo_key(T('wedo', tr0 + 18), 100)
wedo_key(T('wedo', ev['down']), 100, ('QUAD', 'EASE_IN'))
wedo_key(T('wedo', ev['down'] + 7), 0)
wedo_key(T('wedo', ev['down'] + 9), 4); wedo_key(T('wedo', ev['down'] + 11), 0)
emit_key(wedo_led, 1, '#2F7BFF', 8); emit_key(wedo_led, T('wedo', tr0) - 1, '#2F7BFF', 8)
emit_key(wedo_led, T('wedo', tr0), '#FF2416', 22); emit_key(wedo_led, T('wedo', ev['down'] + 9), '#FF2416', 22)
emit_key(wedo_led, T('wedo', ev['down'] + 10), '#2F7BFF', 8)
constant(plastic(79).node_tree)

# ---- SPIKE Prime: rest -90° (bat lying behind the hub), motor B 90° at 50 % -> 0°, 3 s, back
pp = PIV['prime']; ev = S['prime']['ev']; tr0 = ev['trig']
kr(pp, 1, 0, -90)
kr(pp, T('prime', tr0 + 1), 0, -90, ('SINE', 'EASE_IN'))
kr(pp, T('prime', tr0 + 12), 0, 0)
kr(pp, T('prime', tr0 + 14), 0, 4); kr(pp, T('prime', tr0 + 17), 0, 0)
kr(pp, T('prime', ev['down']), 0, 0, ('SINE', 'EASE_IN_OUT'))
kr(pp, T('prime', ev['down'] + 13), 0, -90)
# hub light matrix: idle dim, trigger = pumpkin face (lesson task 3)
PRIME_HUB = OBJ['prime']['hub'][0]
FACE = ['.....', '#.#.#', '.....', '#...#', '.###.']
pix_on = emissive('pix_on', '#FFFFFF', 0.0)
pix_off = mat('pix_off', '#E9E9E4', 0.4)
grid_pos = Vector(S['prime']['matrix_pos']) + Vector((S['prime']['x'], 0, 0))
groot, cells = face_grid('prime_matrix', grid_pos, S['prime']['matrix_size'], 5, FACE, None)
pnode = pix_on.node_tree.nodes['Emission']
for r, c, o in cells:
    o.data.materials.append(pix_on if FACE[r][c] == '#' else pix_off)
for f, v in ((1, 0.0), (T('prime', tr0) - 1, 0.0), (T('prime', tr0), 14.0), (T('prime', ev['down'] + 13), 14.0), (T('prime', ev['down'] + 14), 0.0)):
    pnode.inputs['Strength'].default_value = v; pnode.inputs['Strength'].keyframe_insert('default_value', frame=f)
pnode.inputs['Color'].default_value = lin('#FFFFFF')
constant(pix_on.node_tree)

# ---- SPIKE Essential: yellow -> "Ам!", lid ↺60°, wait 2 s, ↻60°; red -> lid clacks angrily
ep = PIV['essential']; ev = S['essential']['ev']
def lid(f, deg, interp=None):
    kr(ep, f, 1, -deg, interp)
lid(1, 0)
y0 = ev['yellow']
lid(T('essential', y0 + 1), 0, ('SINE', 'EASE_OUT'))
lid(T('essential', y0 + 11), 60); lid(T('essential', y0 + 13), 63); lid(T('essential', y0 + 15), 60)
lid(T('essential', ev['ydown']), 60, ('SINE', 'EASE_IN'))
lid(T('essential', ev['ydown'] + 9), 0); lid(T('essential', ev['ydown'] + 11), 3); lid(T('essential', ev['ydown'] + 13), 0)
r0 = ev['red']
for k in range(5):       # angry clacks
    lid(T('essential', r0 + 1 + k * 6), 0, ('LINEAR',))
    lid(T('essential', r0 + 4 + k * 6), 24)
lid(T('essential', r0 + 31), 0)
# candy bricks slide to the sensor along -Y on the baseplate
spe = sensor_point('essential')
def brick_key(o, f, dy, dz=0.0):
    o.location = spe + Vector((0, -dy, -spe.z + S['essential']['candy_z'] + dz)); o.keyframe_insert('location', frame=f)
for nm, a, b, c, d in (('yellow', ev['y_in0'], ev['y_in1'], ev['y_out0'], ev['y_out1']),
                       ('red', ev['r_in0'], ev['r_in1'], ev['r_out0'], ev['r_out1'])):
    o = CANDY_BRICKS[nm]
    brick_key(o, 1, 30); brick_key(o, T('essential', a), 30); brick_key(o, T('essential', b), S['essential']['candy_gap'])
    brick_key(o, T('essential', c), S['essential']['candy_gap']); brick_key(o, T('essential', d), 30)
# Essential hub light (sensor colour feedback): emissive dot on top of the hub
ess_light = emissive('ess_light', '#FFFFFF', 0.0)
en = ess_light.node_tree.nodes['Emission']
for f, col, v in ((1, '#FFFFFF', 0.0), (T('essential', y0) - 1, '#FFD21F', 0.0), (T('essential', y0), '#FFD21F', 7.0),
                  (T('essential', ev['ydown'] + 13), '#FFD21F', 7.0), (T('essential', ev['ydown'] + 14), '#FFD21F', 0.0),
                  (T('essential', r0) - 1, '#FF2416', 0.0), (T('essential', r0), '#FF2416', 8.0),
                  (T('essential', r0 + 34), '#FF2416', 8.0), (T('essential', r0 + 35), '#FF2416', 0.0)):
    en.inputs['Color'].default_value = lin(col); en.inputs['Color'].keyframe_insert('default_value', frame=f)
    en.inputs['Strength'].default_value = v; en.inputs['Strength'].keyframe_insert('default_value', frame=f)
constant(ess_light.node_tree)
me = bpy.data.meshes.new('ess_dot'); bm = bmesh.new(); bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=S['essential']['light_r']); bm.to_mesh(me); bm.free()
dot = link(bpy.data.objects.new('ess_dot', me)); me.materials.append(ess_light)
dot.location = Vector(S['essential']['light_pos']) + Vector((S['essential']['x'], 0, 0))
dot.rotation_euler = [math.radians(a) for a in S['essential'].get('light_rot', (0, 0, 0))]

# ---- EV3: laugh, arms up (motor 0,3 s), arms down, wait 2 s
xp = PIV['ev3']; ev = S['ev3']['ev']; tr0 = ev['trig']
def arms(f, deg, interp=None):
    kr(xp, f, 0, -deg, interp)
arms(1, 0)
arms(T('ev3', tr0 + 1), 0, ('LINEAR',))
arms(T('ev3', tr0 + 8), 125); arms(T('ev3', tr0 + 10), 132); arms(T('ev3', tr0 + 13), 125)
arms(T('ev3', ev['down']), 125, ('QUAD', 'EASE_IN'))
arms(T('ev3', ev['down'] + 8), 0); arms(T('ev3', ev['down'] + 10), -6); arms(T('ev3', ev['down'] + 13), 0)
# EV3 screen: calm eyes -> angry eyes
SC = S['ev3']
scr_bg = emissive('scr_bg', '#C9E8C0', 0.6)
me = bpy.data.meshes.new('scr'); bm = bmesh.new(); bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=0.5); bm.to_mesh(me); bm.free()
scr = link(bpy.data.objects.new('ev3_screen', me)); me.materials.append(scr_bg)
scr.location = Vector(SC['screen_pos']) + Vector((SC['x'], 0, 0)); scr.rotation_euler.x = math.radians(90)
scr.scale = (SC['screen_size'][0], SC['screen_size'][1], 1)
eye_m = mat('eye_px', '#1B2A1A', 0.6)
EYES = {}
for mood, shape in (('calm', [(-1, 0, 0.9, 0.9), (1, 0, 0.9, 0.9)]),
                    ('angry', [(-1, 0, 1.1, 0.55), (1, 0, 1.1, 0.55)])):
    grp = empty('eyes_' + mood, scr.location + Vector((0, -0.02, 0)))
    for i, (ex, ez, w, h) in enumerate(shape):
        me = bpy.data.meshes.new(f'{mood}{i}'); bm = bmesh.new()
        bmesh.ops.create_circle(bm, cap_ends=True, segments=24, radius=0.5); bm.to_mesh(me); bm.free()
        o = link(bpy.data.objects.new(f'{mood}{i}', me)); o.parent = grp; me.materials.append(eye_m)
        sw = SC['screen_size'][0] * 0.18
        o.location = (ex * SC['screen_size'][0] * 0.22, -0.01, ez); o.rotation_euler.x = math.radians(90)
        o.scale = (w * sw, h * sw, 1)
        if mood == 'angry':
            o.rotation_euler.y = math.radians(-18 * ex)
    EYES[mood] = grp
def vis(o, f, show):
    for ch in [o] + list(o.children):
        ch.hide_render = not show; ch.keyframe_insert('hide_render', frame=f)
vis(EYES['calm'], 1, True); vis(EYES['angry'], 1, False)
vis(EYES['calm'], T('ev3', tr0), False); vis(EYES['angry'], T('ev3', tr0), True)
vis(EYES['calm'], T('ev3', ev['down'] + 14), True); vis(EYES['angry'], T('ev3', ev['down'] + 14), False)

# ------------------------------------------------------------------ camera
cam_d = bpy.data.cameras.new('cam'); cam = link(bpy.data.objects.new('cam', cam_d)); scn.camera = cam
tgt = empty('cam_target')
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.clip_end = 3000
cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = TL['fstop']
for f, cl, tl, lens in TL['camera']:
    cam.location = cl; cam.keyframe_insert('location', frame=f)
    tgt.location = tl; tgt.keyframe_insert('location', frame=f)
    cam_d.lens = lens; cam_d.keyframe_insert('lens', frame=f)
for idb in (cam, tgt, cam_d):
    for fc in fcurves(idb):
        for kp in fc.keyframe_points:
            kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'
# a small scare-shake on every trigger
SHAKE = TL['shake']
cam.rotation_mode = 'XYZ'
shk = empty('shake'); cam.parent = None

# ------------------------------------------------------------------ render settings
scn.render.engine = 'CYCLES'
scn.cycles.device = 'CPU'
scn.cycles.use_denoising = True
scn.cycles.max_bounces = 6; scn.cycles.transparent_max_bounces = 16
scn.view_settings.view_transform = 'AgX'
scn.view_settings.look = 'AgX - Punchy'
scn.view_settings.exposure = 0.5
scn.render.film_transparent = False
scn.render.use_motion_blur = True; scn.render.motion_blur_shutter = 0.45
scn.render.image_settings.file_format = 'PNG'

def setup(w, h, samples):
    scn.render.resolution_x, scn.render.resolution_y = w, h
    scn.render.resolution_percentage = 100
    scn.cycles.samples = samples
    scn.cycles.use_adaptive_sampling = True

def apply_shake(f):
    cam.matrix_world  # noqa
    for f0 in SHAKE:
        d = f - f0
        if 0 <= d < 10:
            a = 0.35 * (1 - d / 10) * math.sin(d * 2.4)
            return a
    return 0.0

def render_frame(f, path):
    scn.frame_set(f)
    a = apply_shake(f)
    if a:
        cam.delta_location = (a * 0.6, 0, a * 0.4)
    else:
        cam.delta_location = (0, 0, 0)
    scn.render.filepath = path
    bpy.ops.render.render(write_still=True)

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    frames = [int(x) for x in sys.argv[2].split(',')]
    w, h, smp = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    setup(w, h, smp)
    os.makedirs(os.path.join(HERE, 'test'), exist_ok=True)
    for f in frames:
        render_frame(f, os.path.join(HERE, 'test', f't{f:04d}.png'))
elif mode == 'anim':
    s, e, w, h, smp = (int(x) for x in sys.argv[2:7])
    setup(w, h, smp)
    os.makedirs(os.path.join(HERE, 'frames'), exist_ok=True)
    for f in range(s, e + 1):
        render_frame(f, os.path.join(HERE, 'frames', f'f{f:04d}.png'))
elif mode == 'proj':
    setup(1080, 1920, 1)
    res = {}
    for f in range(1, FRAMES + 1):
        scn.frame_set(f)
        a = apply_shake(f); cam.delta_location = (a * 0.6, 0, a * 0.4) if a else (0, 0, 0)
        bpy.context.view_layer.update()
        def pr(v):
            q = world_to_camera_view(scn, cam, v)
            return [round(q[0], 4), round(1 - q[1], 4)]
        res[f] = {s['id']: pr(Vector(s['anchor']) + Vector((s['x'], 0, 0))) for s in STOPS}
    json.dump(res, open(os.path.join(HERE, 'proj.json'), 'w'))
    print('proj ok')
elif mode == 'cutout':
    # each model alone, triggered pose, transparent film -> assets/cut_<id>.png (finale card)
    setup(int(sys.argv[2]), int(sys.argv[2]), int(sys.argv[3]))
    scn.render.film_transparent = True
    scn.render.use_motion_blur = False
    cam_d.dof.use_dof = False
    keep = set()
    for mid in ROOT:
        for o in model_objs(mid):
            keep.add(o.name)
    keep |= {'prime_matrix'} | {o.name for o in bpy.data.objects if o.name.startswith(('prime_matrix', 'ev3_screen', 'eyes_', 'calm', 'angry', 'ess_dot'))}
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name not in keep:
            o.hide_render = True
    for o in bpy.data.objects:
        if o.type in ('CURVE', 'META'):
            o.hide_render = True
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    os.makedirs(os.path.join(HERE, 'assets'), exist_ok=True)
    for s_ in STOPS:
        mid = s_['id']
        scn.frame_set(T(mid, s_['cut_t']))
        for o in model_objs(mid):
            pass
        lo, hi = BB[mid]
        c0 = (lo + hi) / 2
        if mid == 'prime':
            c0.z = 9.0
        ext = max(hi.x - lo.x, hi.z - lo.z, 14)
        cam.parent = None
        cam.animation_data_clear(); tgt.animation_data_clear(); cam_d.animation_data_clear()
        cam_d.lens = 50
        d = ext * 0.62 / math.tan(math.atan(18 / 50))
        side = (0.95, -0.75) if mid == 'ev3' else (0.42, -1.0)
        cam.location = c0 + Vector((d * side[0], d * side[1], d * 0.28)); tgt.location = c0
        # hide the other models
        for m2 in ROOT:
            for o in model_objs(m2):
                o.hide_render = (m2 != mid)
        for o in bpy.data.objects:
            if o.name.startswith(('prime_matrix', 'ev3_screen', 'eyes_', 'calm', 'angry', 'ess_dot')) and o.type == 'MESH':
                o.hide_render = not ((mid == 'prime' and o.name.startswith('prime_matrix')) or
                                     (mid == 'ev3' and o.name.startswith(('ev3_screen', 'angry'))) or
                                     (mid == 'essential' and o.name.startswith('ess_dot')))
        scn.render.filepath = os.path.join(HERE, 'assets', f'cut_{mid}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'bbox':
    for s in STOPS:
        lo, hi = BB[s['id']]
        print(s['id'], [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    def ob(name, mid, key):
        lo, hi = world_bbox(OBJ[mid][key])
        print(' ', mid, key, [round(v, 2) for v in lo], [round(v, 2) for v in hi])
    ob('', 'prime', 'hub'); ob('', 'prime', 'sensor'); ob('', 'essential', 'sensor'); ob('', 'essential', 'hub')
    ob('', 'ev3', 'brick'); ob('', 'wedo', 'sensor'); ob('', 'ev3', 'sonar'); ob('', 'essential', 'lid')
    print(sorted(OBJ['ev3'].keys()))
