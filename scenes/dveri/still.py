"""«Двери супермаркета» (WeDo 2.0, реечная передача) — стоп-кадр для поста.
Вечерний вход в магазин: мокрый асфальт перед дверью, тёплый свет магазина льётся через открытый проём,
внутри — светлый пол и размытые огни полок, сверху — сумеречное небо.
Модель берётся из конвейера инструкций (legobot-wedo-pipeline/models/dveri) — model_tNNN.json.
Хаб и пластины под ним в кадр не берём (как на посте с катапультой): за проёмом виден «магазин».

  python3 still.py W H SAMPLES [out.png] [t]      t = 0 | 70 | 100 (положение двери, %)
1 unit = 1 stud. Z вверх. Фасад смотрит в -Y.
"""
import os, sys, math, json, random
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, SAMPLES = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
OUTP = sys.argv[4] if len(sys.argv) > 4 else os.path.join(HERE, 'out', 'dveri_post.png')
T = int(sys.argv[5]) if len(sys.argv) > 5 else 70
sys.argv = sys.argv[:1]
exec(open(os.path.join(HERE, '_common.py')).read())
from mathutils import Matrix, Vector

HIDE_GROUPS = {'hub'}
HIDE_NOTES = ('под хаб',)

# ------------------------------------------------ модель
C = Matrix(((1, 0, 0), (0, 0, 1), (0, -1, 0)))
parts = json.load(open(os.path.join(HERE, f'model_t{T:03d}.json'), encoding='utf-8'))
MODEL = []
for p in parts:
    if p['group'] in HIDE_GROUPS or any(s in p['note'] for s in HIDE_NOTES):
        continue
    o = bpy.data.objects.new(p['note'], part_mesh(p['part'], p['color']))
    bpy.context.collection.objects.link(o)
    R = C @ Matrix(p['rot']) @ C.transposed()
    t = C @ (Vector(p['pos']) / 20.0)
    o.matrix_world = Matrix.Translation(t) @ R.to_4x4()
    MODEL.append(o)
    if p['group'] == 'door' and p['part'] == '3702.dat':
        DOOR = o
bpy.context.view_layer.update()
pts = [o.matrix_world @ Vector(c) for o in MODEL for c in o.bound_box]
lo = Vector((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts)))
hi = Vector((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
print('model bbox', tuple(round(v, 2) for v in lo), tuple(round(v, 2) for v in hi))
Z0 = lo.z                       # низ основания

# ------------------------------------------------ материалы окружения
def mat(name, hexv, rough=0.5, emit=None, strength=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = lin(hexv); b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = lin(emit); b.inputs['Emission Strength'].default_value = strength
    return m

def asphalt():
    """мокрый асфальт: тёмный, лужи (низкая шероховатость) по шуму, мелкая зернистость"""
    m = bpy.data.materials.new('asphalt'); m.use_nodes = True
    nt = m.node_tree; N = nt.nodes; L = nt.links
    b = N['Principled BSDF']
    tc = N.new('ShaderNodeTexCoord')
    big = N.new('ShaderNodeTexNoise'); big.inputs['Scale'].default_value = 0.09; big.inputs['Detail'].default_value = 4
    L.new(tc.outputs['Object'], big.inputs['Vector'])
    ramp = N.new('ShaderNodeValToRGB')
    ramp.color_ramp.elements[0].position = 0.46; ramp.color_ramp.elements[0].color = (0.03, 0.03, 0.03, 1)   # лужа
    ramp.color_ramp.elements[1].position = 0.56; ramp.color_ramp.elements[1].color = (0.55, 0.55, 0.55, 1)   # сухо
    L.new(big.outputs['Fac'], ramp.inputs['Fac']); L.new(ramp.outputs['Color'], b.inputs['Roughness'])
    grain = N.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 9.0; grain.inputs['Detail'].default_value = 6
    L.new(tc.outputs['Object'], grain.inputs['Vector'])
    col = N.new('ShaderNodeValToRGB')
    col.color_ramp.elements[0].color = lin('#17181B'); col.color_ramp.elements[1].color = lin('#3A3C41')
    L.new(grain.outputs['Fac'], col.inputs['Fac']); L.new(col.outputs['Color'], b.inputs['Base Color'])
    bump = N.new('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.12
    L.new(grain.outputs['Fac'], bump.inputs['Height']); L.new(bump.outputs['Normal'], b.inputs['Normal'])
    return m

def box(name, x0, x1, y0, y1, z0, z1, m):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
    o = bpy.context.object; o.name = name; o.scale = (x1 - x0, y1 - y0, z1 - z0)
    o.data.materials.append(m); return o

# улица перед фасадом и пол магазина за ним (линия фасада — задний край основания перед дверью)
FAC_Y = 2.0
box('street', -200, 200, -200, FAC_Y, Z0 - 0.3, Z0, asphalt())
box('store_floor', -200, 200, FAC_Y, 120, Z0 - 0.3, Z0 - 0.02, mat('store_floor', '#E9E1D2', 0.18))
# «бордюр» под основанием модели — чтобы модель стояла на чём-то, а не парила
# стена магазина вдали — тёплая, размытая расфокусом
box('store_back', -200, 200, 60, 61, Z0, 60, mat('store_back', '#F3E3C4', 0.9, '#FFD9A0', 1.6))
# полки с «товарами»: ряды цветных светящихся кубиков — в расфокусе дадут разноцветное боке
random.seed(7)
GOODS = ['#E8475F', '#F5A623', '#4CAF2E', '#2A9FD6', '#FFD23A', '#F28C28', '#E86AA6', '#FFFFFF']
for row, (y, x0, x1) in enumerate(((22, -40, 40), (34, -50, 50), (46, -60, 60))):
    shelf = mat(f'shelf{row}', '#D8D2C6', 0.6)
    for zz in (2.5, 6.0, 9.5, 13.0):
        box(f'shelf_{row}_{zz}', x0, x1, y, y + 3, Z0 + zz - 0.2, Z0 + zz, shelf)
        x = x0 + random.uniform(0, 2)
        while x < x1 - 1.5:
            w = random.uniform(0.8, 2.0); h = random.uniform(1.0, 2.6)
            c = random.choice(GOODS)
            box('good', x, x + w, y + 0.4, y + 2.4, Z0 + zz, Z0 + zz + h, mat('g' + c, c, 0.5, c, 0.6))
            x += w + random.uniform(0.15, 0.6)
# потолочные светильники магазина (линии)
for y in (12, 26, 40, 54):
    box(f'lamp_{y}', -60, 60, y, y + 0.8, Z0 + 26, Z0 + 26.3, mat('lamp', '#FFFFFF', 0.5, '#FFF1D6', 12))

# небо: сумерки (градиент тёмно-синего), подсвечивает модель холодным
world = bpy.data.worlds.new('w'); scn.world = world; world.use_nodes = True
wn = world.node_tree.nodes; wl = world.node_tree.links
bg = wn['Background']; bg.inputs['Strength'].default_value = 0.6
grad_tc = wn.new('ShaderNodeTexCoord'); sep = wn.new('ShaderNodeSeparateXYZ')
wl.new(grad_tc.outputs['Generated'], sep.inputs['Vector'])
sky = wn.new('ShaderNodeValToRGB')
sky.color_ramp.elements[0].position = 0.48; sky.color_ramp.elements[0].color = lin('#3A4E7A')
sky.color_ramp.elements[1].position = 0.75; sky.color_ramp.elements[1].color = lin('#0E1630')
wl.new(sep.outputs['Z'], sky.inputs['Fac']); wl.new(sky.outputs['Color'], bg.inputs['Color'])

def area(name, loc, look, size, power, hexv='#FFFFFF', cam_vis=False):
    ld = bpy.data.lights.new(name, 'AREA'); ld.size = size; ld.energy = power
    ld.color = lin(hexv)[:3]
    o = bpy.data.objects.new(name, ld); bpy.context.collection.objects.link(o)
    o.location = loc; o.visible_camera = cam_vis
    o.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler()
    return o

cx = (lo.x + hi.x) / 2
door_gap_x = (-6.0 + DOOR.matrix_world.translation.x - 4.0) / 2      # середина проёма между стойкой и створкой
# свет магазина: изнутри, из-за проёма — тёплое пятно на асфальте перед дверью
area('store_light', (door_gap_x, 9, Z0 + 9), (door_gap_x, -4, Z0), 10, 9000, '#FFC27A')
area('store_fill', (cx, 30, Z0 + 18), (cx, 0, Z0 + 2), 30, 14000, '#FFD8A8')
# фонарь над входом (тёплый) и холодный «уличный» свет слева-спереди
area('door_lamp', (door_gap_x, -4, Z0 + 12), (door_gap_x, -1, Z0 + 4), 3, 1400, '#FFE2B0')
area('street_key', (-26, -22, Z0 + 22), (cx, 0, Z0 + 3), 16, 9500, '#BFD3FF')
area('warm_key', (24, -26, Z0 + 14), (cx, 0, Z0 + 3), 12, 4200, '#FFE9CF')

# ------------------------------------------------ камера: спереди-слева, чуть сверху, глубина резкости
cam_d = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', cam_d)
bpy.context.collection.objects.link(cam); scn.camera = cam
tgt = empty('cam_target', (0, 0, 0))
c = cam.constraints.new('TRACK_TO'); c.target = tgt; c.track_axis = 'TRACK_NEGATIVE_Z'; c.up_axis = 'UP_Y'
cam_d.sensor_width = 36; cam_d.lens = 55
VIEW = Vector((-0.34, -0.90, 0.27)).normalized()
ctr = Vector(((lo.x + hi.x) / 2 - 0.6, (lo.y + 2.0) / 2, (lo.z + hi.z) / 2))
fov = 2 * math.atan(cam_d.sensor_width / 2 / cam_d.lens)
rad = max(hi.x - lo.x, hi.z - lo.z) * 0.62
dist = rad / math.tan(fov / 2) * (1.0 if W >= H else W / H)
tgt.location = ctr + Vector((0, 0, 0.3))
cam.location = ctr + VIEW * dist
cam_d.dof.use_dof = True; cam_d.dof.focus_object = DOOR; cam_d.dof.aperture_fstop = 2.2

r = scn.render
r.engine = 'CYCLES'; r.resolution_x, r.resolution_y = W, H
cy = scn.cycles; cy.device = 'CPU'; cy.samples = SAMPLES
cy.use_adaptive_sampling = True; cy.adaptive_threshold = 0.03
cy.use_denoising = True; cy.denoiser = 'OPENIMAGEDENOISE'
cy.max_bounces = 6; cy.diffuse_bounces = 3; cy.glossy_bounces = 3
cy.transmission_bounces = 3; cy.transparent_max_bounces = 4
scn.view_settings.view_transform = 'AgX'
try:
    scn.view_settings.look = 'AgX - Medium High Contrast'
except Exception:
    pass
scn.view_settings.exposure = 0.0
r.image_settings.file_format = 'PNG'
os.makedirs(os.path.dirname(OUTP), exist_ok=True)
r.filepath = OUTP
bpy.ops.render.render(write_still=True)
print('still', OUTP)
