"""Хаос-маятник (SPIKE Prime): сцена Blender (Cycles). Студия: синяя стена, синий коврик с сеткой — кадр целиком 1080×1920.
python scene.py still 135 240 out.png 1080 1920 48   — стоп-кадр (углы звеньев в градусах); рядом out.png.json с проекциями
python scene.py map 135 240 out.png 1080 1920 16     — карта движения: детали раскрашены по группам
python scene.py test 24,180,300 1080 1920 14         — кадры ролика (30 к/с) в frames/f0024.png…
python scene.py anim 24 434 1080 1920 14             — кадры F_REL..PLATE_LAST (размытие движения по ключам на 1/4 кадра)
Движение — timeline.angles() (физика sim.py)."""
import bpy, math, sys, os, json
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'courier')); sys.path.insert(0, HERE)
import ldr
import numpy as np
import chaos_model as M
from bpy_extras.object_utils import world_to_camera_view

ldr._index = None
COL = ldr.colours()
OVR = {14: '#F7C600', 322: '#2FA6D9', 26: '#C8327D', 0: '#2E3136', 71: '#A3A8AD', 15: '#F4F4F0'}
MAP = {'stand': '#8A9096', 'arm1': '#E2453C', 'arm2': '#2F8FE0'}
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))


def lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(((x + 0.055) / 1.055) ** 2.4 if x > 0.04045 else x / 12.92 for x in c) + (1.0,)


def ld2b(p):
    return C @ Vector(tuple(float(v) for v in p)) / 20.0


def to_b(pos, rot):
    M3 = Matrix([list(map(float, r)) for r in rot])
    return Matrix.Translation(ld2b(pos)) @ (C @ M3 @ C.transposed()).to_4x4()


bpy.ops.wm.read_factory_settings(use_empty=True)
scn = bpy.context.scene
MATS = {}


def mat(key, hexv, rough=0.32, coat=0.25):
    if key in MATS:
        return MATS[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.15
    MATS[key] = m
    return m


def plastic(code):
    return mat(f'ld_{code}', OVR.get(code) or ('#' + COL.get(code, ('x', '888888'))[1]), 0.45 if code == 0 else 0.32)


MESHES = {}


def part_mesh(part, color):
    key = (part, color)
    if key in MESHES:
        return MESHES[key]
    verts, faces, mats, vidx, codes = [], [], [], {}, []
    for c, pts in ldr.part_polys(part, color):
        f = []
        for p in pts:
            q = (round(p[0], 4), round(p[1], 4), round(p[2], 4))
            if q not in vidx:
                vidx[q] = len(verts); verts.append(q)
            f.append(vidx[q])
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


P_init = M.build(0, 0)
OBJ = []
for k, p in enumerate(P_init):
    o = bpy.data.objects.new(f'p{k:02d}', part_mesh(p['part'], p['color']))
    bpy.context.collection.objects.link(o); o.rotation_mode = 'QUATERNION'
    OBJ.append(o)


def make_textures():
    """Коврик для резки (клетка 1 см) и синяя стена с мягкими пятнами света — рисуются кодом."""
    from PIL import Image, ImageDraw, ImageFilter
    D = os.path.join(HERE, 'tex'); os.makedirs(D, exist_ok=True)
    if not os.path.exists(os.path.join(D, 'mat.png')):
        N, cell = 2048, 32
        im = Image.new('RGB', (N, N), (22, 52, 92)); d = ImageDraw.Draw(im)
        for i in range(0, N + 1, cell):
            w = 3 if (i // cell) % 5 == 0 else 1
            col = (120, 160, 200) if w == 1 else (150, 190, 225)
            d.line([(i, 0), (i, N)], fill=col, width=w); d.line([(0, i), (N, i)], fill=col, width=w)
        im.filter(ImageFilter.GaussianBlur(0.6)).save(os.path.join(D, 'mat.png'))
    if not os.path.exists(os.path.join(D, 'wall.png')):
        W = H = 2048
        y = np.linspace(0, 1, H)[:, None]; x = np.linspace(0, 1, W)[None, :]
        c_top, c_bot = np.array([18, 62, 135]), np.array([30, 95, 175])
        base = c_top + (c_bot - c_top) * y[..., None] + np.zeros((H, W, 3))
        light = np.zeros((H, W))
        for x0 in (0.12, 0.30, 0.48, 0.66, 0.84):
            light += np.exp(-((x - x0) / 0.045) ** 2) * np.exp(-((y - 0.32) / 0.22) ** 2)
        img = np.clip(base + (light / light.max())[..., None] * np.array([40, 55, 70]), 0, 255).astype(np.uint8)
        Image.fromarray(img).filter(ImageFilter.GaussianBlur(6)).save(os.path.join(D, 'wall.png'))


make_textures()


def tex_mat(name, img, scale, rough):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; b = nt.nodes['Principled BSDF']
    t = nt.nodes.new('ShaderNodeTexImage'); t.image = bpy.data.images.load(os.path.join(HERE, 'tex', img))
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
    tc = nt.nodes.new('ShaderNodeTexCoord')
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], t.inputs['Vector'])
    nt.links.new(t.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = rough
    return m


# пол-коврик (клетка 1 см = 25 LDU = 1.25 ед. Blender; текстура 64 клетки -> плоскость 80 ед.)
bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 40, 0))
floor = bpy.context.active_object; floor.data.materials.append(tex_mat('mat', 'mat.png', (2.5, 2.5, 1), 0.75))
# стена позади
bpy.ops.mesh.primitive_plane_add(size=90, location=(0, -16, 30), rotation=(math.radians(90), 0, 0))
wall = bpy.context.active_object; wall.data.materials.append(tex_mat('wall', 'wall.png', (1, 1, 1), 0.9))

world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = lin('#1E4F8F')
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.35


def sun(name, rot, power, hexv='#FFFFFF', ang=10):
    ld = bpy.data.lights.new(name, 'SUN'); ld.energy = power; ld.color = lin(hexv)[:3]; ld.angle = math.radians(ang)
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.rotation_euler = [math.radians(a) for a in rot]
    return o


# rot X — наклон от вертикали, rot Z — поворот вокруг вертикали (0 — свет светит в сторону -Y, к стене)
sun('key', (50, 0, -30), 4.4, '#FFF1E2', 8)
sun('fill', (65, 0, 40), 1.1, '#DCE8FF', 20)
sun('rim', (-55, 0, 15), 1.6, '#FFFFFF', 6)

cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
cam_d.lens = 50; cam_d.sensor_fit = 'VERTICAL'; cam_d.sensor_height = 24
# камера чуть справа и выше центра маятника
target = ld2b((0, -385, 60))
cam.location = ld2b((420, -520, 2650))
cam.rotation_mode = 'QUATERNION'; cam.rotation_quaternion = (target - cam.location).to_track_quat('-Z', 'Y')
cam_d.dof.use_dof = False

r = scn.render
r.image_settings.file_format = 'PNG'; r.image_settings.color_mode = 'RGB'
scn.view_settings.view_transform = 'AgX'; scn.view_settings.look = 'AgX - Medium High Contrast'
cy = scn.cycles; cy.device = 'CPU'; cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.04
cy.max_bounces = 4; cy.diffuse_bounces = 2; cy.glossy_bounces = 2


def pose(th1, th2):
    for o, p in zip(OBJ, M.build(th1, th2)):
        loc, q, _ = to_b(p['pos'], p['rot']).decompose()
        o.location = loc; o.rotation_quaternion = q


def proj(th1, th2):
    q = M.points(th1, th2)
    out = {}
    for k in ('P0', 'P1', 'S', 'Lg'):
        v = world_to_camera_view(scn, cam, ld2b(q[k] + np.array([0, 0, 90 if k != 'P0' else 70])))
        out[k] = [v.x * r.resolution_x, (1 - v.y) * r.resolution_y]
    return out


import timeline as TL
FR = os.path.join(HERE, 'frames')


def setup(w, h, smp):
    r.resolution_x, r.resolution_y = w, h; r.engine = 'CYCLES'; cy.samples = smp


def key_range(f0, f1):
    """Ключи поз на каждую четверть кадра f0-1..f1+1 (для размытия движения); знак кватерниона без скачков."""
    r.use_motion_blur = True; r.motion_blur_shutter = 0.5; r.motion_blur_position = 'CENTER'
    bpy.context.preferences.edit.keyframe_new_interpolation_type = 'LINEAR'
    prev = [None] * len(OBJ)
    k = (f0 - 1) * TL.SUB
    while k <= (f1 + 1) * TL.SUB:
        fv = k / TL.SUB
        for j, (o, p) in enumerate(zip(OBJ, M.build(*TL.angles(fv)))):
            loc, q, _ = to_b(p['pos'], p['rot']).decompose()
            if prev[j] is not None and q.dot(prev[j]) < 0:
                q = -q
            prev[j] = q.copy()
            o.location = loc; o.rotation_quaternion = q
            o.keyframe_insert('location', frame=fv); o.keyframe_insert('rotation_quaternion', frame=fv)
        k += 1
    for o in OBJ:
        if o.animation_data and o.animation_data.action:
            for fc in getattr(o.animation_data.action, 'fcurves', []):
                for kp in fc.keyframe_points:
                    kp.interpolation = 'LINEAR'


def render_frames(frames):
    os.makedirs(FR, exist_ok=True)
    key_range(min(frames), max(frames))
    for f in frames:
        scn.frame_set(f)
        r.filepath = os.path.join(FR, f'f{f:04d}.png'); bpy.ops.render.render(write_still=True)
        print('Saved frame', f, flush=True)


mode = sys.argv[sys.argv.index('--') + 1] if '--' in sys.argv else sys.argv[1]
args = sys.argv[sys.argv.index(mode) + 1:]
if mode in ('still', 'map'):          # still|map th1 th2 out [w h samples]
    th1, th2 = math.radians(float(args[0])), math.radians(float(args[1])); out = args[2]
    setup(*((int(args[3]), int(args[4]), int(args[5])) if len(args) > 5 else (1080, 1920, 48)))
    if mode == 'map':
        for o, p in zip(OBJ, M.build(0, 0)):
            mm = mat('map_' + p['group'], MAP[p['group']], 0.5, 0.0)
            o.data = o.data.copy(); o.data.materials.clear(); o.data.materials.append(mm)
    pose(th1, th2)
    r.filepath = out; bpy.ops.render.render(write_still=True)
    json.dump(proj(th1, th2), open(out + '.json', 'w'))
    print('Saved', out)
elif mode == 'test':                  # test f1,f2,... w h samples
    setup(int(args[1]), int(args[2]), int(args[3]))
    render_frames(sorted(set(TL.plate_index(int(v)) for v in args[0].split(','))))
elif mode == 'anim':                  # anim S E w h samples  (кадры ролика, Blender рендерит F_REL..PLATE_LAST)
    S, E = max(int(args[0]), TL.F_REL), min(int(args[1]), TL.PLATE_LAST)
    setup(int(args[2]), int(args[3]), int(args[4]))
    render_frames(list(range(S, E + 1)))
