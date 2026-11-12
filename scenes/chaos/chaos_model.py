"""Хаос-маятник (двойной маятник) из LEGO Education SPIKE Prime (45678).
LDraw: LDU, Y вниз, пол y=0. Маятник качается в плоскости XY, оси шарниров — вдоль Z (к зрителю +Z).

Стойка: жёлтая рама 11x19 (39369) стоит вертикально на голубой раме 11x15 (39790), лежащей на столе;
их скрепляют два угловых соединителя 55615 (по 2 штифта в каждую раму).
Звено 1: пурпурная балка 11 (32525), шарнир P0 — центральное отверстие верхнего ряда стойки, на конце P1 — большое колесо W1.
Звено 2: голубая балка 13 (41239) висит на P1 (6-е отверстие); на коротком конце (5 шипов) большое колесо W2,
на длинном (7 шипов) — маленькое колесо W3.
th1 — угол звена 1 от вертикали вниз (P0->P1), th2 — угол звена 2 (P1 -> длинный конец), рад.
"""
import numpy as np

YELLOW, AZURE, MAGENTA, BLACK, LBG, WHITE = 14, 322, 26, 0, 71, 15
I3 = np.eye(3)

YC = -210.0                     # центр вертикальной рамы (19 шипов = 380, стоит на раме-основании, верх основания y=-20)
P0 = np.array([0.0, YC - 160.0, 0.0])   # верхнее отверстие центрального ряда: y = -370
L1 = 160.0                      # P0 -> P1 (отверстия 2 и 10 балки 11)
A2S, A2L = 100.0, 140.0         # P1 -> короткий / длинный конец звена 2 (отверстия 6 -> 1 и 6 -> 13 балки 13)

R_UP = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]], float)   # плита: лок. Y (отверстия) -> мир Z, лок. Z -> мир -Y
R_AXZ = np.array([[0, 0, -1], [0, 1, 0], [1, 0, 0]], float)  # ось/штифт: лок. X -> мир Z
R_TILE = R_UP                                                 # плитка 15535: лок. Y -> мир Z


def u(th):
    """Направление звена (y вниз): th=0 — вниз."""
    return np.array([np.sin(th), np.cos(th), 0.0])


def R_beam(th):
    """Балка: лок. Z (длина) -> направление звена, лок. Y (оси отверстий) -> мир Z."""
    ez = u(th); ey = np.array([0, 0, 1.0]); ex = np.cross(ey, ez)
    return np.column_stack([ex, ey, ez])


def Rz(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])


def points(th1, th2):
    p1 = P0 + L1 * u(th1)
    return dict(P0=P0, P1=p1, S=p1 - A2S * u(th2), Lg=p1 + A2L * u(th2))


def build(th1=0.0, th2=0.0):
    P = []

    def add(group, color, part, pos, rot=I3, note=''):
        P.append(dict(group=group, color=color, part=part, pos=np.array(pos, float), rot=np.array(rot, float), note=note))

    q = points(th1, th2)
    # ---------- стойка (неподвижна)
    add('stand', AZURE, '39790.dat', (0, -10, 0), I3, 'основание: рама 11x15')
    add('stand', YELLOW, '39369.dat', (0, YC, 0), R_UP, 'стойка: рама 11x19')
    for x in (-100, 100):
        add('stand', LBG, '55615.dat', (x, -30, 20), I3, 'уголок 55615')
    # ось шарнира P0 (ось 5) и втулки
    add('stand', LBG, '32073.dat', (0, P0[1], 20), R_AXZ, 'ось P0: ось 5')
    for z, nm in ((-20, 'втулка P0 сзади'), (20, 'втулка P0 1'), (40, 'втулка P0 2')):
        add('stand', LBG, '3713.dat', (0, P0[1], z), I3, nm)
    # ---------- звено 1
    R1 = R_beam(th1)
    add('arm1', MAGENTA, '32525.dat', P0 + 80 * u(th1) + [0, 0, 60], R1, 'звено 1: балка 11')
    add('arm1', BLACK, '39367p01.dat', q['P1'] + [0, 0, 32.5], Rz(th1), 'колесо W1')
    add('arm1', LBG, '32073.dat', q['P1'] + [0, 0, 68], R_AXZ @ np.array([[1, 0, 0], [0, np.cos(th1), -np.sin(th1)], [0, np.sin(th1), np.cos(th1)]]), 'ось P1: ось 5')
    # ---------- звено 2
    R2 = R_beam(th2)
    add('arm2', BLACK, '15535.dat', q['P1'] + [0, 0, 70], R_TILE, 'плитка-проставка P1')
    add('arm2', AZURE, '41239.dat', q['P1'] + 20 * u(th2) + [0, 0, 88], R2, 'звено 2: балка 13')
    add('arm2', LBG, '3713.dat', q['P1'] + [0, 0, 108], I3, 'втулка P1')
    add('arm2', BLACK, '18651.dat', q['S'] + [0, 0, 108], R_AXZ, 'штифт-ось W2')
    add('arm2', BLACK, '39367p01.dat', q['S'] + [0, 0, 115.5], Rz(th2), 'колесо W2')
    add('arm2', BLACK, '18651.dat', q['Lg'] + [0, 0, 108], R_AXZ, 'штифт-ось W3')
    add('arm2', WHITE, '56903.dat', q['Lg'] + [0, 0, 108], Rz(th2), 'диск W3')
    add('arm2', BLACK, '61254.dat', q['Lg'] + [0, 0, 108], Rz(th2), 'шина W3')
    return P


def write_ldr(parts, path, title='Хаос-маятник SPIKE Prime'):
    def fmt(c, part, pos, R):
        v = list(pos) + list(np.asarray(R).reshape(-1))
        return f'1 {c} ' + ' '.join(f'{x:.4f}'.rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0' for x in v) + f' {part}'
    lines = [f'0 {title}', '0 Name: ' + path.split('/')[-1], '0 Author: LEGObot', '']
    lines += [fmt(p['color'], p['part'], p['pos'], p['rot']) for p in parts]
    open(path, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    from collections import Counter
    P = build()
    print(len(P), 'деталей')
    for (part, col), n in sorted(Counter((p['part'], p['color']) for p in P).items()):
        print(f'  {part:14s} цвет {col:3d}  x{n}')
