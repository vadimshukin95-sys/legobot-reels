"""Пила на кривошипе — модель WeDo 2.0 (45300) для рилса «Как колесо превращается в пилу?».
LDraw: LDU, Y вниз. Вперёд (к зрителю) = -Z, вправо = +X. Основание: верх y = 0.
Привод — как у «Снеговика-дворника»: мотор → 8z → 24z → шкив 4185 с пальцем 3749 (R = 20).
Кривошипно-ползунный механизм: шатун 7M (отв. 0 и 6, L = 120) толкает каретку,
каретка (2 столбика из Technic 1x4, по 2 кирпича) скользит по двум неподвижным осям 7,
оси зажаты в рамках из кирпичей 32064a (крестовое отверстие). Сверху поперёк столбиков —
кирпич с пальцем 2458 и три кирпича 1x2, на них полотно пилы (пластина 2x8) с зубьями из скосов 3665.
Ряды по Z: R0 [-60,-40] — плоскость шатуна; R1 [-40,-20] — палец и зубья; R3–R4 [0,40] — направляющие.
"""
import numpy as np


def rot_y(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])


def rot_z(a):
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def fmt_line(color, part, pos, R):
    v = list(pos) + list(np.asarray(R).reshape(-1))
    return f'1 {color} ' + ' '.join(f'{x:.4f}'.rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0' for x in v) + f' {part}'

I = np.eye(3)
RY90 = rot_y(90)           # лок. X -> -Z, лок. Z -> +X
AXZ = rot_y(-90)           # лок. X -> +Z (ось вдоль Z)

LIME, GREEN, BLACK, WHITE, AZURE, ORANGE = 27, 2, 0, 15, 322, 191
DKGREY, LTGREY, TRBLUE, TAN, RED = 72, 71, 43, 19, 4
GREEN = 10                 # Bright Green (как балки 32524 в наборе)

XK, YK = 120, -70          # ось кривошипа
R_CRANK = 20
L_ROD = 120                # шатун 7M: отверстия 0 и 6
YJ = -78                   # высота пальца каретки (2458 на y=-88, палец на +10)
Z_ROD = -50
YA1, YA2, ZA = -30, -54, 20   # неподвижные оси-направляющие
XF = 60                    # рамки направляющих на x = ±60


def kin(theta):
    """theta (град): 0 = палец справа, против часовой при взгляде спереди. -> (палец P, шарнир каретки J)."""
    t = np.radians(theta)
    P = np.array([XK + R_CRANK * np.cos(t), YK - R_CRANK * np.sin(t)])
    dy = P[1] - YJ
    J = np.array([P[0] - np.sqrt(L_ROD ** 2 - dy ** 2), YJ])
    return P, J


def _beam(a, b, z):
    """Балка 32524 от отверстия 0 в точке a до отверстия 6 в точке b (длина 120)."""
    u = np.array([b[0] - a[0], b[1] - a[1], 0.0]); u /= np.linalg.norm(u)
    Rb = np.column_stack([np.cross([0, 0, 1.0], u), [0, 0, 1.0], u])
    c = (np.array(a) + np.array(b)) / 2
    return (c[0], c[1], z), Rb


def build(theta=90.0, teeth=True):
    P = []

    def add(group, color, part, pos, rot=I, note=''):
        P.append(dict(group=group, color=color, part=part,
                      pos=np.array(pos, float), rot=np.array(rot, float), note=note))

    pin, J = kin(theta)
    xs = J[0]
    # ---------- 1. Основание ----------
    for x, z in ((-100, 20), (0, 20), (120, 40)):
        add('base', ORANGE, '32001.dat', (x, 8, z), RY90, 'стяжка 2x6')
    for z in (-20, 20):
        add('base', BLACK, '4282.dat', (0, 0, z), I, 'пластина 2x16')
    for x in (100, 140):
        add('base', ORANGE, '3709b.dat', (x, 0, 80), RY90, 'пластина 2x4 под мотор')
    # ---------- 2. Мотор и редуктор 8:24 (узел «Снеговика-дворника») ----------
    add('motor', WHITE, '21980.dat', (XK, -56, 20), I, 'мотор')
    add('drive', RED, '32062.dat', (XK, -30, 0), AXZ, 'ось 2')
    add('drive', DKGREY, '10928.dat', (XK, -30, -10), rot_z(22.5 + 3 * theta), 'шестерня 8z')
    for z in (10, 30):
        add('bear', LIME, '3700.dat', (XK, -80, z), I, 'подшипник 1x2')
    add('crank', DKGREY, '87083.dat', (XK, YK, 0), AXZ, 'ось 4 с упором')
    add('crank', DKGREY, '3648b.dat', (XK, YK, -10), rot_z(-theta), 'шестерня 24z')
    add('crank', TRBLUE, '4185.dat', (XK, YK, -35), rot_z(90 - theta), 'шкив-кривошип')
    add('crank', TAN, '3749.dat', (pin[0], pin[1], -40), AXZ, 'палец кривошипа')
    # ---------- 3. Направляющие: рамки 32064a на пластинах, две оси 7 ----------
    for x in (-XF, XF):
        for k, y in enumerate((-8, -16)):
            add('frame', WHITE, '3023.dat', (x, y, ZA), RY90, 'подкладка 1x2')
        for y, nm in ((-40, 'рамка нижняя'), (-64, 'рамка верхняя')):
            add('frame', DKGREY, '32064a.dat', (x, y, ZA), RY90, nm)
    for y in (YA1, YA2):
        add('rail', LTGREY, '44294.dat', (0, y, ZA), I, 'ось 7 — направляющая')
    # ---------- 4. Каретка (ползун) ----------
    for dx in (-10, 10):
        for y in (-40, -64):
            add('slider', LIME, '3701.dat', (xs + dx, y, 0), RY90, 'каретка 1x4')
    # 2458 и три кирпича 1x2 лежат поперёк обоих столбиков — связывают каретку
    add('slider', LTGREY, '2458.dat', (xs, -88, -30), I, 'палец каретки 2458')
    for z in (-10, 10, 30):
        add('slider', AZURE, '3004.dat', (xs, -88, z), I, 'связь каретки 1x2')
    add('slider', GREEN, '3738.dat', (xs - 60, -96, -20), I, 'полотно пилы 2x8')
    if teeth:
        for k in range(3):
            add('slider', ORANGE, '3665a.dat', (xs - 140 + 40 * k + 30, -88, -30), RY90, f'зуб {k + 1}')
    # ---------- 5. Шатун ----------
    pos, R = _beam(pin, J, Z_ROD)
    add('rod', GREEN, '32524.dat', pos, R, 'шатун 7M')
    return P


def write_ldr(parts, path, title='Пила на кривошипе'):
    lines = [f'0 {title}', '0 Name: ' + path.split('/')[-1], '0 Author: LEGObot', '']
    for p in parts:
        lines.append(fmt_line(p['color'], p['part'], p['pos'], p['rot']))
    open(path, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    xs = []
    for th in range(0, 360, 15):
        p, j = kin(th); xs.append(j[0])
    print('ход каретки', round(min(xs), 1), '…', round(max(xs), 1), 'ход', round(max(xs) - min(xs), 1))
    Pp = build()
    print(len(Pp), 'деталей')
