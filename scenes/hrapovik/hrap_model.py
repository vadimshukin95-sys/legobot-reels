"""Храповик-лебёдка — модель WeDo 2.0 (45300) для рилса «Отпустил — а он не падает?».
LDraw: LDU, Y вниз; к зрителю = -Z, вправо = +X. Оси механизма вдоль Z. Модель — hrapovik.ldr (группы в комментариях).
  рама: 2 пластины 2x16 (чёрные), стенки — техно-кирпичи 1x12 (низ) и 1x8 (верх), ось 3 собачки с полувтулками;
  drive: ось 10, барабан 32012 между стенками, шестерня 24 снаружи передней стенки, втулки, колёсико-ручка сзади — вращение вокруг (40,-38);
  pawl: собачка — угловой соединитель #1 (32013), свободно качается на оси 3 вокруг (100,-38), лежит на зубьях под своим весом;
  load: 3 кирпича 1x2 на нитке, нитка сходит с барабана справа (x = 53, радиус намотки 13).
Край подставки x = 30, верх подставки y = 8, пол y = 168 (груз стоит на полу при dy = 0).
Кинематика собачки посчитана по геометрии LDraw (shapely) заранее — pawl_table.json:
  g — угол шестерни (поворот rz(g) в LDraw, подъём груза = g убывает), собачка — rel (поворот rz(rel) вокруг оси, подъём = rel растёт)."""
import os, json, numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GC = np.array([40.0, -38.0, 0.0])          # ось шестерни
PIV = np.array([100.0, -38.0, 0.0])        # ось собачки
R_ROPE = 13.0
ROPE_X = GC[0] + R_ROPE
LOAD_TOP = 92.0                            # верх шипов груза при dy = 0
PLINTH = dict(x0=-420.0, x1=30.0, y0=8.0, y1=168.0, z0=-90.0, z1=120.0)
FLOOR_Y = 168.0
TAB = json.load(open(os.path.join(HERE, 'pawl_table.json')))


def rz(deg):
    a = np.radians(deg); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1.0]])


def load_dy(g):
    """Груз: g < 0 — поднят (dy < 0 вверх)."""
    return R_ROPE * np.radians(g)


def parts0():
    out, grp = [], 'frame'
    for l in open(os.path.join(HERE, 'hrapovik.ldr'), encoding='utf-8'):
        t = l.split()
        if len(t) >= 4 and t[:3] == ['0', '//', 'группа']:
            grp = t[3]; continue
        if len(t) >= 15 and t[0] == '1':
            v = list(map(float, t[2:14]))
            out.append(dict(group=grp, color=int(t[1]), part=t[14], pos=np.array(v[:3]),
                            rot=np.array(v[3:]).reshape(3, 3), note=f'{grp} {t[14]}'))
    return out


P0 = parts0()


def build(g=0.0, pawl=0.0, dy=0.0):
    res = []
    for p in P0:
        pos, rot = p['pos'].copy(), p['rot'].copy()
        if p['group'] == 'drive':
            R = rz(g); pos = GC + R @ (pos - GC); rot = R @ rot
        elif p['group'] == 'pawl':
            R = rz(pawl); pos = PIV + R @ (pos - PIV); rot = R @ rot
        elif p['group'] == 'load':
            pos = pos + np.array([0, dy, 0])
        res.append(dict(p, pos=pos, rot=rot))
    return res


def rope(dy):
    """Нитка: от барабана (сходит справа, на высоте оси) до шипов груза."""
    return np.array([ROPE_X, GC[1], 0.0]), np.array([ROPE_X, LOAD_TOP + dy, 0.0])


def pawl_tip(rel):
    a = np.radians(TAB['base'] + rel)
    return PIV + np.array([30 * np.cos(a), 30 * np.sin(a), 0]) + np.array([0, 0, -50.0])
