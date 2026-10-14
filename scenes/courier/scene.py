"""«Робот-курьер» — шагающий робот WeDo 2.0 (модель из инструкции, kurer_final.mpd), рилс LEGObot.
Механизм: мотор -> червяк -> 24z на оси G -> ремень -> ось F; на концах осей шкивы с пальцами
(сдвиг 180° между сторонами) водят бёдра 1x8 по кругу; датчик расстояния останавливает робота.
Units: 1 Blender unit = 1 stud, Z up, robot walks toward -Y (LDraw front -Z), camera in front.
  python scene.py test 1,90,200 360 640 8
  python scene.py anim 1 492 1080 1920 12
  python scene.py proj
"""
import bpy, math, sys, json, os
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ldr

FPS = 24
bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
scn.render.fps = FPS
scn.frame_start = 1
COL = ldr.colours()

# ------------------------------------------------------------------ timeline (shared with overlay.py / audio.py)
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FRAMES = TL.get('frames', 444)
scn.frame_end = FRAMES
F_HAND0, F_HAND1, F_STOP, F_GO, F_HANDOUT = TL['hand0'], TL['hand1'], TL['stop'], TL['go'], TL['handout']
OMEGA = TL['rev_per_s'] * 2 * math.pi / FPS          # crank rad per frame at full speed

def lin(h):
    h = h.lstrip('#')
    c = [int(h[i:i+2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)

OVERRIDE = {15: '#F4F4F0', 71: '#A0A5A9', 72: '#5B5F63', 0: '#232529', 4: '#C91A09', 25: '#F07A12',
            10: '#4CC04A', 27: '#A5CA18', 322: '#3EB7E8', 34: '#3BAA4A', 79: '#EDEDE6', 191: '#F8B71B',
            2: '#3BAA4A', 14: '#F5CD2F', 19: '#D9BB7B', 43: '#AEE9EF', 46: '#F5CD2F'}
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
    if name.startswith('Trans') and code != 79:
        b.inputs['Transmission Weight'].default_value = 0.7
        b.inputs['Roughness'].default_value = 0.12
    if code == 79:   # hub LED diffuser -> animated emission
        b.inputs['Emission Strength'].default_value = 0.0
    MATS[code] = m
    return m

# ------------------------------------------------------------------ model file: main + inline submodels (belt, cables)
INLINE = os.path.join(HERE, 'inline')
os.makedirs(INLINE, exist_ok=True)
main_lines, cur, files = [], None, {}
for line in open(os.path.join(HERE, 'model.mpd'), encoding='utf-8'):
    t = line.split()
    if len(t) >= 3 and t[0] == '0' and t[1] == 'FILE':
        cur = ' '.join(t[2:]); files[cur] = []; continue
    if len(t) >= 2 and t[0] == '0' and t[1] == 'NOFILE':
        cur = None; continue
    if cur is not None:
        files[cur].append(line)
ldr.find('3001.dat')                                   # build the library index
for name, lines in files.items():
    if name == 'main.ldr':
        main_lines = lines; continue
    p = os.path.join(INLINE, name)
    open(p, 'w', encoding='utf-8').writelines(lines)
    ldr._index[name.lower()] = p

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

# LDraw (x, y down, z) LDU -> Blender stud space (x, z, -y)/20
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
def ld2b(p):
    return C @ Vector(p) / 20.0
def ld_matrix(R, pos):
    Rb = C @ Matrix(R) @ C.transposed()
    return Matrix.Translation(ld2b(pos)) @ Rb.to_4x4()

def empty(name, loc, parent=None):
    o = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(o); o.location = loc
    if parent is not None:
        o.parent = parent
    return o

Z_G, Z_F = 0.0, -80.0
def classify(part, x, y, z):
    p = part.lower()
    if p in ('3706.dat', '32905.dat') and abs(y + 40) < 1: return 'worm'
    if p == '32123a.dat' and abs(y + 40) < 1: return 'worm'
    on_axle = p in ('44294.dat', '3648b.dat', '32123a.dat', '4185a.dat', '3713.dat', '6562.dat')
    if on_axle and abs(z - Z_G) < 1 and abs(y) <= 21: return 'G'
    if on_axle and abs(z - Z_F) < 1 and abs(y) <= 21: return 'F'
    if p in ('3702.dat', '3001.dat', '32059.dat', '85984.dat') and abs(x) >= 40:
        return 'legL' if x < 0 else 'legR'
    return 'body'

ROOT = empty('robot', (0, 0, 0))
PIV = {'G': ld2b((0, 0, Z_G)), 'F': ld2b((0, 0, Z_F)), 'worm': ld2b((0, -40, 0)),
       'legL': Vector((0, 0, 0)), 'legR': Vector((0, 0, 0)), 'body': Vector((0, 0, 0))}
GRP = {g: (ROOT if g == 'body' else empty('grp_' + g, PIV[g], ROOT)) for g in PIV}
OBJ = {}
for k, line in enumerate(main_lines):
    t = line.split()
    if len(t) < 15 or t[0] != '1':
        continue
    c = int(t[1]); v = list(map(float, t[2:14])); pid = ' '.join(t[14:])
    R = [v[3:6], v[6:9], v[9:12]]; pos = v[0:3]
    g = classify(pid, *pos)
    o = bpy.data.objects.new(f'{g}_{k:03d}_{pid}', part_mesh(pid, c))
    bpy.context.collection.objects.link(o)
    o.parent = GRP[g]
    o.matrix_basis = Matrix.Translation(-PIV[g]) @ ld_matrix(R, pos)
    OBJ[(g, pid.lower(), k)] = o
SENSOR = [o for (g, p, k), o in OBJ.items() if p == '20844.dat'][0]
# LDraw points of interest (body frame)
SENSOR_FRONT = ld2b((0, -160, -26))                    # in front of the sensor «eyes»
LEDPOS = ld2b((0, -146, -40))                          # hub LED (light diffuser, code 79)
FOOT_L = Vector((-3.5, 0.0, -5.7))                      # left sole centre at th=0 (studs, body frame, before lift)

# ------------------------------------------------------------------ gait: crank angle, body lift and travel per frame
def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def speed(f):
    if f < F_STOP - 4:
        return 1.0
    if f < F_STOP + 2:
        return 1.0 - ease((f - (F_STOP - 4)) / 6)
    if f < F_GO:
        return 0.0
    return ease((f - F_GO) / 8)

def lowest(th):
    yl = 114 + 20 * math.cos(th) - 20               # LDraw y of sole bottoms (down +)
    yr = 74 - 20 * math.cos(th) + 20
    return max(yl, yr), ('L' if yl >= yr else 'R')
def foot_dy(th, side):                              # Blender Y offset of a sole (studs)
    return math.sin(th) if side == 'L' else -math.sin(th)

GAIT = {}
th, ypos = TL.get('th0', 0.6), 0.0
for f in range(1, FRAMES + 1):
    if f > 1:
        th1 = th + OMEGA * speed(f)
        _, sup = lowest(th)
        ypos -= foot_dy(th1, sup) - foot_dy(th, sup)
        th = th1
    lo, sup = lowest(th)
    GAIT[f] = (th, ypos, lo / 20.0)
Y_STOP = GAIT[F_STOP][1]

def pose(f):
    th, y, z = GAIT[f]
    ROOT.location = (0, y, z)
    GRP['G'].rotation_euler = (th, 0, 0)
    GRP['F'].rotation_euler = (th, 0, 0)
    GRP['worm'].rotation_euler = (0, -24 * th, 0)
    GRP['legL'].location = (0, math.sin(th), 1 - math.cos(th))
    GRP['legR'].location = (0, -math.sin(th), math.cos(th) - 1)

for f in range(1, FRAMES + 1):
    pose(f)
    ROOT.keyframe_insert('location', frame=f)
    for g in ('G', 'F', 'worm'):
        GRP[g].keyframe_insert('rotation_euler', frame=f)
    for g in ('legL', 'legR'):
        GRP[g].keyframe_insert('location', frame=f)

def fcurves(idb):
    from bpy_extras import anim_utils
    ad = idb.animation_data
    if not ad or not ad.action:
        return []
    cb = anim_utils.action_get_channelbag_for_slot(ad.action, ad.action_slot)
    return list(cb.fcurves) if cb else []
for o in [ROOT] + list(GRP.values()):
    for fc in fcurves(o):
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

# ------------------------------------------------------------------ props: the client's hand (not LEGO, scene dressing)
import bmesh
def mat(name, hexv, rough=0.5, coat=0.0, sss=0.0, metal=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Metallic'].default_value = metal
    if sss:
        b.inputs['Subsurface Weight'].default_value = sss
    return m

def hand():
    """cartoon open hand: metaball palm + fingers, sleeve with a white cuff.
    Origin at the wrist, fingers along local -Z, palm faces local -Y."""
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
    for p in me.polygons:
        p.use_smooth = True
    sl = bpy.data.objects.new('sleeve', me); bpy.context.collection.objects.link(sl); sl.parent = root
    me.materials.append(mat('sleeve', '#2F6FDE', 0.7))
    me = bpy.data.meshes.new('cuff'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=1.8, radius2=1.8, depth=0.8)
    bmesh.ops.translate(bm, vec=(0, 0, 0.8), verts=bm.verts)
    bmesh.ops.bevel(bm, geom=bm.edges[:], offset=0.12, segments=3, affect='EDGES')
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    cf = bpy.data.objects.new('cuff', me); bpy.context.collection.objects.link(cf); cf.parent = root
    me.materials.append(mat('cuff', '#F4F4F0', 0.45, coat=0.3))
    return root
HAND = hand()
HSC = 0.62
HAND.scale = (HSC, HSC, HSC)
PALM_LOCAL = Vector((0, 0, -3.4)) * HSC

def hand_rot(sleeve_dir):
    """local +Z -> sleeve direction, palm (local -Y) faces +Y (toward the robot)"""
    z = sleeve_dir.normalized()
    y = Vector((0, -1, 0)); y = (y - z * y.dot(z)).normalized()
    x = y.cross(z)
    return Matrix((x, y, z)).transposed()

# stop spot: palm stands in front of the sensor at the moment the robot stops
SF_STOP = Vector((0, Y_STOP, GAIT[F_STOP][2])) + SENSOR_FRONT
PALM_AT = SF_STOP + Vector((0.4, -TL['hand_gap'], 0.6))
SLEEVE = Vector((1.0, 0.15, -0.38))                     # forearm runs down to the right
def kh(f, palm, sleeve=SLEEVE):
    Rm = hand_rot(sleeve)
    HAND.matrix_world = Matrix.Translation(palm - Rm @ PALM_LOCAL) @ Rm.to_4x4() @ Matrix.Scale(HSC, 4)
    HAND.keyframe_insert('location', frame=f); HAND.keyframe_insert('rotation_euler', frame=f)
OUT = Vector((18, 2, 3))
kh(1, PALM_AT + OUT)
for ob in [HAND] + list(HAND.children):
    for f_, hid in ((1, True), (F_HAND0 - 1, True), (F_HAND0, False)):
        ob.hide_render = hid; ob.keyframe_insert('hide_render', frame=f_)
kh(F_HAND0, PALM_AT + OUT)
kh(F_HAND1 - 8, PALM_AT + Vector((1.0, -0.3, 0.6)))
kh(F_HAND1, PALM_AT)
kh(F_HANDOUT, PALM_AT + Vector((0.2, 0, 0.1)))
kh(F_HANDOUT + 18, PALM_AT + OUT * 1.1 + Vector((0, 0, 4)), SLEEVE + Vector((0.2, 0, 0.3)))
kh(FRAMES, PALM_AT + OUT * 1.1 + Vector((0, 0, 4)), SLEEVE + Vector((0.2, 0, 0.3)))

# ------------------------------------------------------------------ set: oak table + light grey wall
def mat_wood():
    m = bpy.data.materials.new('oak'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = 0.42
    b.inputs['Coat Weight'].default_value = 0.15
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (0.045, 0.045, 1.0)     # 2k texture ≈ 22 studs
    mp.inputs['Rotation'].default_value = (0, 0, math.radians(90))
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    im = N.new('ShaderNodeTexImage')
    im.image = bpy.data.images.load(os.path.join(HERE, 'tex', 'oak_veneer_01_diff_2k.jpg'))
    L.new(mp.outputs['Vector'], im.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Value'].default_value = 1.25; hsv.inputs['Saturation'].default_value = 0.95
    L.new(im.outputs['Color'], hsv.inputs['Color']); L.new(hsv.outputs['Color'], b.inputs['Base Color'])
    return m

def slab(name, x0, x1, y0, y1, z0, z1, m):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1)
    for v in bm.verts:
        v.co = Vector((x0 + (v.co.x + .5) * (x1 - x0), y0 + (v.co.y + .5) * (y1 - y0), z0 + (v.co.z + .5) * (z1 - z0)))
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m)
    return o
def mat_tex(name, fname, v0, rough=0.55, value=1.0):
    """image laid on the table: 1 texture = 60 studs, robot path along the image's vertical centre line"""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']; b.inputs['Roughness'].default_value = rough
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / 60, -1 / 60, 1.0)
    mp.inputs['Location'].default_value = (0.5, v0, 0.0)
    L.new(tc.outputs['Object'], mp.inputs['Vector'])
    im = N.new('ShaderNodeTexImage'); im.image = bpy.data.images.load(os.path.join(HERE, 'tex', fname))
    L.new(mp.outputs['Vector'], im.inputs['Vector'])
    hsv = N.new('ShaderNodeHueSaturation'); hsv.inputs['Value'].default_value = value
    L.new(im.outputs['Color'], hsv.inputs['Color']); L.new(hsv.outputs['Color'], b.inputs['Base Color'])
    return m

def cyclorama(name, m, y_wall=40.0, rad=26.0):
    """seamless studio sweep: floor -> quarter cove -> wall"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    prof = [(-200.0, 0.0), (y_wall - rad, 0.0)]
    for k in range(1, 17):
        a = math.pi / 2 * k / 16
        prof.append((y_wall - rad + rad * math.sin(a), rad - rad * math.cos(a)))
    prof.append((y_wall, 160.0))
    rows = [[bm.verts.new((x, y, z)) for (y, z) in prof] for x in (-220.0, 220.0)]
    for j in range(len(prof) - 1):
        bm.faces.new((rows[0][j], rows[1][j], rows[1][j + 1], rows[0][j + 1]))
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = True
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    me.materials.append(m)
    return o

BG = os.environ.get('BG', TL.get('bg', 'city'))
V0 = 0.31
if BG == 'oak':
    slab('table', -120, 120, -160, 70, -1.0, 0.0, mat_wood())
    slab('wall', -200, 200, 70, 71, -40, 160, mat('wall', '#D9D8D5', 0.9))
elif BG == 'city':
    slab('table', -120, 120, -160, 70, -1.0, 0.0, mat_tex('road', 'road.png', V0, 0.75, 1.05))
    slab('wall', -200, 200, 70, 71, -40, 160, mat('wall', '#BFE0F2', 0.9))
elif BG == 'map':
    slab('table', -120, 120, -160, 70, -1.0, 0.0, mat_tex('map', 'map.png', V0 - 0.06, 0.6, 1.0))
    slab('wall', -200, 200, 70, 71, -40, 160, mat('wall', '#F2E6D3', 0.9))
else:   # 'studio' — pastel seamless sweep
    cyclorama('sweep', mat('sweep', '#BDE3F4', 0.75))
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#F3EFE8')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.5

# hub LED: blue while walking, green while the courier «delivers», blue again
led = plastic(79).node_tree.nodes['Principled BSDF']
BLUE, GREENL = lin('#2F7BFF'), lin('#33E05A')
def kled(f, col, strength):
    led.inputs['Emission Color'].default_value = col; led.inputs['Emission Color'].keyframe_insert('default_value', frame=f)
    led.inputs['Emission Strength'].default_value = strength; led.inputs['Emission Strength'].keyframe_insert('default_value', frame=f)
kled(1, BLUE, 8); kled(F_STOP - 1, BLUE, 8); kled(F_STOP, GREENL, 20); kled(F_GO - 1, GREENL, 20); kled(F_GO, BLUE, 8)
gl = bpy.data.lights.new('ledglow', 'POINT'); gl.shadow_soft_size = 0.4
glo = bpy.data.objects.new('ledglow', gl); bpy.context.collection.objects.link(glo)
glo.parent = ROOT; glo.location = LEDPOS + Vector((0, 0, 0.8))
for f, colr, e in ((1, '#2F7BFF', 30), (F_STOP - 1, '#2F7BFF', 30), (F_STOP, '#33E05A', 220), (F_GO - 1, '#33E05A', 220), (F_GO, '#2F7BFF', 30)):
    gl.color = lin(colr)[:3]; gl.keyframe_insert('color', frame=f)
    gl.energy = e; gl.keyframe_insert('energy', frame=f)
for fc in fcurves(gl) + fcurves(plastic(79).node_tree):
    for kp in fc.keyframe_points:
        kp.interpolation = 'CONSTANT'

# ------------------------------------------------------------------ camera: shots relative to the (smoothed) robot position
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt
c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36
cam_d.dof.use_dof = True; cam_d.dof.focus_object = tgt; cam_d.dof.aperture_fstop = 3.2
SHOT = {   # camera offset, target offset (from robot root on the table), lens
    'hero':   ((12.0, -34.0, 12.5), (0.0, -1.5, 9.0), 50),
    'worm':   ((-24.0, -7.0, 9.5), (0.0, 0.0, 7.4), 92),
    'crank':  ((-42.0, -2.0, 8.0), (0.0, -0.8, 6.4), 42),
    'front':  ((4.0, -38.0, 5.0), (0.0, 0.0, 6.5), 48),
    'sensor': ((-34.0, -24.0, 13.0), (0.5, -2.0, 9.5), 44),
    'end':    ((11.0, -40.0, 15.0), (0.0, -1.0, 8.0), 46),
}
SEQ = TL['shots']          # [[frame, shot], ...] — hold until the next entry, blend over 'blend' frames
BLEND = TL['blend']
def shot_at(f):
    cur = SEQ[0][1]; w = 1.0; prev = cur
    for i, (fs, nm) in enumerate(SEQ):
        if f >= fs:
            prev = SEQ[i - 1][1] if i else nm; cur = nm
            w = ease((f - fs) / BLEND) if i else 1.0
    a, b = SHOT[prev], SHOT[cur]
    mix = lambda p, q: Vector(p).lerp(Vector(q), w)
    return mix(a[0], b[0]), mix(a[1], b[1]), a[2] + (b[2] - a[2]) * w

def follow_y(f, k=10):
    ys = [GAIT[min(FRAMES, max(1, f + d))][1] for d in range(-k, k + 1)]
    return sum(ys) / len(ys)
for f in range(1, FRAMES + 1):
    co, to, lens = shot_at(f)
    base = Vector((0, follow_y(f), 0))
    cam.location = base + co; cam.keyframe_insert('location', frame=f)
    tgt.location = base + to; tgt.keyframe_insert('location', frame=f)
    cam_d.lens = lens; cam_d.keyframe_insert('lens', frame=f)

# ------------------------------------------------------------------ lights: soft daylight, warm key, cool fill
def area(name, loc, look, size, power, hexv='#FFFFFF'):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power
    ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    o.parent = None
    o.visible_camera = False
    return o
YM = (GAIT[1][1] + GAIT[FRAMES][1]) / 2
area('key', (-22, YM - 26, 34), (0, YM, 6), 22, 16000, '#FFE7C7')
area('fill', (30, YM - 22, 14), (0, YM - 2, 6), 18, 4800, '#DCE6FF')
area('rim', (6, YM + 30, 26), (0, YM, 9), 14, 7000, '#FFF4E0')

# ------------------------------------------------------------------ render
r = scn.render
r.engine = 'CYCLES'
cy = scn.cycles
cy.device = 'CPU'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.06
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 1
cy.transmission_bounces = 3; cy.transparent_max_bounces = 3
r.use_persistent_data = True
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
r.image_settings.file_format = 'PNG'

mode = sys.argv[1] if len(sys.argv) > 1 else 'test'
if mode == 'test':
    r.resolution_x, r.resolution_y = int(sys.argv[3]), int(sys.argv[4])
    cy.samples = int(sys.argv[5])
    for f in map(int, sys.argv[2].split(',')):
        scn.frame_set(f)
        r.filepath = os.path.join(HERE, 'test', f'f{f:04d}.png')
        bpy.ops.render.render(write_still=True)
elif mode == 'anim':
    s, e = int(sys.argv[2]), int(sys.argv[3])
    r.resolution_x, r.resolution_y = int(sys.argv[4]), int(sys.argv[5])
    cy.samples = int(sys.argv[6])
    scn.frame_start, scn.frame_end = s, e
    r.filepath = os.path.join(HERE, 'frames', 'f')
    r.use_overwrite = False; r.use_placeholder = True
    bpy.ops.render.render(animation=True)
elif mode == 'proj':
    r.resolution_x, r.resolution_y = 1080, 1920
    res = {}
    for f in range(1, FRAMES + 1):
        scn.frame_set(f)
        def pr(v):
            return [round(x, 4) for x in list(world_to_camera_view(scn, cam, v))[:2]]
        Mr = ROOT.matrix_world
        d = {'sensor': pr(Mr @ SENSOR_FRONT), 'led': pr(Mr @ LEDPOS)}
        th = GAIT[f][0]
        if TL['trace'][0] <= f <= TL['trace'][1]:
            pts = []
            for k in range(33):
                a = 2 * math.pi * k / 32
                pts.append(pr(Mr @ (FOOT_L + Vector((0, math.sin(a), 1 - math.cos(a))))))
            d['trace'] = pts
            d['foot'] = pr(Mr @ (FOOT_L + Vector((0, math.sin(th), 1 - math.cos(th)))))
        res[f] = d
    json.dump(res, open(os.path.join(HERE, 'proj.json'), 'w'))
elif mode == 'gait':
    for f in (1, F_STOP, F_GO, FRAMES):
        print(f, [round(x, 3) for x in GAIT[f]])
    print('palm', PALM_AT, 'sensor at stop', SF_STOP)
elif mode == 'save':
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(HERE, 'legobot_courier_wedo2.blend'))
