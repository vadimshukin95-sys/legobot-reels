"""Башня передач «Одна ручка — две скорости»: повышающая вверх, понижающая вниз (набор 9686).
LDraw: LDU, Y вниз; вперёд (к зрителю) = -Z, вправо = +X. Оси шестерён — вдоль Z, все на одной вертикали x = 0.

Оси (y): U2 -80, U1 -40, C 0 (ручка), D1 40, D2 80 — межосевое 40 LDU = пара 24 + 8 зубьев.
  вверх (повышающая):  C 24z -> U1 8z (×3), U1 24z -> U2 8z (×9)
  вниз  (понижающая):  C 8z -> D1 24z (÷3), D1 8z -> D2 24z (÷9)
Только пары 24/8: 40-зубой шестерне рядом не хватает места (соседняя ось на 40 LDU проходит сквозь неё).
Детали 9686: 24z (3648) ×4, 8z (3647) ×4 из 6, ручка 33299, балки 1x15 (32278) и 1x7 (32524), оси, втулки, штифты.

Слои по Z (центры): ручка -60 | указатели U2/D2 -40 и U1/D1 -20 | передняя балка 0 |
шестерни A 20, B 40, C 60 | задняя балка 80 | втулки 100.
  A: C 24z + U1 8z        B: C 8z + D1 24z        C: U1 24z + U2 8z, D1 8z + D2 24z
Указатели соседних осей в разных слоях (рычаг 30 LDU > половины межосевого), ручка — в самом переднем.
Стол: y = 150 (низ ножек и балок).
Указатели — балка 2L с крестовым отверстием (60483), рычаг 29 LDU.
"""
import numpy as np

BLACK, LTGREY, DKGREY, WHITE = 0, 71, 72, 15
BLUE, AZURE, ORANGE, YELLOW, MAGENTA, GREEN = 1, 322, 25, 14, 26, 10
I = np.eye(3)
# Локальные оси деталей LDraw: шестерни/втулки — ось Z; оси/штифты — вдоль X; балки — длина Z, отверстия Y;
# 60483 и ручка 33299 — отверстие по Y, рычаг вдоль +Z (у ручки шип торчит по +Y).
R_G = I                                                       # шестерня, втулка: ось уже вдоль Z
R_PZ = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)   # ось, штифт: лок. X -> Z
R_B = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0]], float)    # балка стоя: длина -> Y, отверстия -> Z
R_F = np.array([[0, 0, 1], [1, 0, 0], [0, 1, 0]], float)     # балка лёжа вдоль X, отверстия -> Z
R_P = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)    # указатель 60483: рычаг вверх (-Y)
R_K = np.array([[-1, 0, 0], [0, 0, -1], [0, -1, 0]], float)  # ручка: рычаг вверх, шип к зрителю (-Z)
TEETH = {'3647.dat': 8, '3648.dat': 24}

# ось: (имя, y, цвет указателя, z указателя, передаточное к ручке со знаком)
AXLES = {
    'U2': dict(y=-80, col=BLUE, pz=-40, ratio=+9.0),
    'U1': dict(y=-40, col=AZURE, pz=-20, ratio=-3.0),
    'C':  dict(y=0, col=ORANGE, pz=None, ratio=+1.0),
    'D1': dict(y=40, col=YELLOW, pz=-20, ratio=-1 / 3),
    'D2': dict(y=80, col=MAGENTA, pz=-40, ratio=+1 / 9),
}
GEARS = {  # ось -> [(деталь, z)]
    'C': [('3648.dat', 20), ('3647.dat', 40)],
    'U1': [('3647.dat', 20), ('3648.dat', 60)],
    'U2': [('3647.dat', 60)],
    'D1': [('3648.dat', 40), ('3647.dat', 60)],
    'D2': [('3648.dat', 60)],
}
MESH = [('C', '3648.dat', 'U1', '3647.dat'), ('U1', '3648.dat', 'U2', '3647.dat'),
        ('C', '3647.dat', 'D1', '3648.dat'), ('D1', '3647.dat', 'D2', '3648.dat')]


def rz(phi):
    c, s = np.cos(phi), np.sin(phi)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def _offsets():
    """Начальные углы осей, чтобы зубья входили во впадины. Угол на экране (матем.) = -phi + угол зуба."""
    off = {'C': 0.0}
    for a, ga, b, gb in MESH:
        na, nb = TEETH[ga], TEETH[gb]
        pa, pb = 2 * np.pi / na, 2 * np.pi / nb
        ya, yb = AXLES[a]['y'], AXLES[b]['y']
        alpha = np.arctan2(-(yb - ya), 0.0)          # направление от a к b (матем., Y вверх)
        delta = (-off[a] - alpha) % pa               # зуб a смещён от линии центров на delta
        off[b] = -(alpha + np.pi - delta * na / nb + pb / 2)
    return off


OFF = _offsets()


def axle_angle(name, theta):
    return OFF[name] + AXLES[name]['ratio'] * theta


def build(theta=0.0):
    """theta — угол ручки, рад (положительный — по часовой на экране)."""
    P = []

    def add(group, color, part, pos, rot=I, note=''):
        P.append(dict(group=group, color=color, part=part, pos=np.array(pos, float),
                      rot=np.array(rot, float), note=note))

    # ---------- рама ----------
    for z, nm in ((0, 'передняя'), (80, 'задняя')):
        add('frame', WHITE, '32278.dat', (0, 0, z), R_B, f'{nm} балка 1x15')
    for y in (-140, 140):
        add('frame', BLACK, '3705.dat', (0, y, 40), R_PZ, 'распорка: ось 4')
        add('frame', LTGREY, '3713.dat', (0, y, 40), R_G, 'распорка: втулка')
    for z in (-20, 100):
        add('frame', WHITE, '32524.dat', (0, 140, z), R_F, 'ножка: балка 1x7')
        add('frame', BLACK, '2780.dat', (0, 140, z + (10 if z < 0 else -10)), R_PZ, 'штифт ножка-балка')
    # ---------- оси: ось 8, шестерни, втулка сзади, указатель или ручка спереди ----------
    AXLE_Z = {'C': 20, 'U2': 30, 'D2': 30, 'U1': 40, 'D1': 40}
    for name, ax in AXLES.items():
        R = rz(axle_angle(name, theta))
        y = ax['y']
        add(name, BLACK, '3707.dat', (0, y, AXLE_Z[name]), R @ R_PZ, f'{name}: ось 8')
        add(name, LTGREY, '3713.dat', (0, y, 100), R @ R_G, f'{name}: втулка сзади')
        for part, z in GEARS[name]:
            add(name, DKGREY if part == '3647.dat' else LTGREY, part, (0, y, z), R @ R_G,
                f'{name}: шестерня {TEETH[part]}z')
        if name == 'C':
            add(name, ORANGE, '33299b.dat', (0, y, -60), R @ R_K, 'C: ручка')
        else:
            add(name, ax['col'], '60483.dat', (0, y, ax['pz']), R @ R_P, f'{name}: указатель')
    return P


def check():
    """Зацепления и зазоры: межосевое = r1 + r2; ни одна чужая ось не проходит через шестерню."""
    pitch_r = {'3647.dat': 10.0, '3648.dat': 30.0}
    tip_r = {'3647.dat': 12.4, '3648.dat': 32.4}
    ok = True
    for a, ga, b, gb in MESH:
        d = abs(AXLES[a]['y'] - AXLES[b]['y'])
        za = dict((p, z) for p, z in GEARS[a])[ga]; zb = dict((p, z) for p, z in GEARS[b])[gb]
        good = abs(d - pitch_r[ga] - pitch_r[gb]) < 1e-6 and za == zb
        ok &= good
        print(f'{a}{TEETH[ga]}z -> {b}{TEETH[gb]}z  межосевое {d} слой {za}/{zb}', 'OK' if good else 'ОШИБКА')
    partners = {(a, b) for a, _, b, _ in MESH} | {(b, a) for a, _, b, _ in MESH}
    for g, gl in GEARS.items():
        for part, z in gl:
            for o in AXLES:
                if o == g:
                    continue
                d = abs(AXLES[o]['y'] - AXLES[g]['y'])
                if tip_r[part] + 6 >= d:
                    print('  КОЛЛИЗИЯ: ось', o, 'проходит через', g, part, 'z', z); ok = False
            for g2, gl2 in GEARS.items():          # шестерни в одном слое, не пара
                if g2 <= g:
                    continue
                for part2, z2 in gl2:
                    if z2 != z:
                        continue
                    d = abs(AXLES[g2]['y'] - AXLES[g]['y'])
                    pair = (g, g2) in partners and abs(d - pitch_r[part] - pitch_r[part2]) < 1e-6
                    if not pair and tip_r[part] + tip_r[part2] >= d:
                        print('  КОЛЛИЗИЯ шестерён', g, part, g2, part2, 'слой', z); ok = False
    # указатели: соседние оси — в разных слоях; рычаг 30 + ось 6 < межосевого
    for n1, a1 in AXLES.items():
        for n2, a2 in AXLES.items():
            if n1 < n2 and a1['pz'] is not None and a1['pz'] == a2['pz']:
                d = abs(a1['y'] - a2['y'])
                if 30 + 30 >= d:
                    print('  КОЛЛИЗИЯ указателей', n1, n2); ok = False
    print('итог:', 'всё сходится' if ok else 'ЕСТЬ ОШИБКИ')
    return ok


if __name__ == '__main__':
    from collections import Counter
    check()
    cnt = Counter(p['part'] for p in build(0))
    print(dict(cnt))
    for n in AXLES:
        print(n, 'передаточное', AXLES[n]['ratio'], 'смещение', round(np.degrees(OFF[n]), 2))
