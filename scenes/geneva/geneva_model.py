"""Мальтийский механизм — модель SPIKE Prime (45678) для рилса «Мотор крутится ровно, а крест — рывками».
LDraw: LDU, Y вниз; вперёд (к зрителю) = -Z, вправо = +X. Механизм лежит горизонтально, оси вертикальные.
Все детали — из набора 45678:
  средний мотор 54696 лежит выходом вверх (ротор u9363 крутится, корпус стоит);
  кривошип — балка 1x7 (32524) на роторе, 2 штифта 2780 в отверстия ротора (R = 1), палец — штифт 3L 6558 (R = 5);
  крест — «решётка» из 4 балок 1x11 (32525) в два слоя: слой B — пазы вдоль лок. Z, слой A — пазы вдоль лок. X,
  слои сшиты 4 штифтами 2780; сверху ступица 60483 (отверстие под ось) на штифте; ось 9 (60485);
  основание — 2 балки 1x15 (32278), мотор приколот снизу штифтами 2780; втулка 3713 держит ось.
Межосевое C = 7 шипов, радиус пальца r = 5 (r/C = 0,714 ≈ sin 45°): 4 паза, за оборот мотора крест — на 90°.
Слои по Y: основание [30, 50], мотор [-50, 30], кривошип [-70, -50], крест B [-90, -70], A [-110, -90], ступица [-130, -110].
"""
import numpy as np

LIME, GREEN, BLACK, WHITE, AZURE, BLUE, MAGENTA, LTGREY, YELLOW = 27, 2, 0, 15, 322, 1, 26, 71, 14

XC = 140.0           # центр креста (x), центр ротора — (0, 0)
R_PIN = 100.0        # радиус пальца
PHI_IN = np.degrees(np.arcsin(0.6))          # 36.87: палец входит/выходит при |phi| = 36.87 (точка (4,3) шипа)
S0, S1 = 90 - PHI_IN, 90 + PHI_IN             # окно зацепления по углу мотора: 53.13 … 126.87


def rot_y_math(a):
    """Поворот вокруг вертикали на угол a (град) в смысле atan2(z, x): (1,0,0) -> (cos a, 0, sin a)."""
    a = np.radians(a); c, s = np.cos(a), np.sin(a)
    return np.array([[c, 0, -s], [0, 1, 0], [s, 0, c]])


I = np.eye(3)
BEAM_X = rot_y_math(0) @ np.array([[0, 0, 1], [0, 1, 0], [-1, 0, 0]])   # балка: лок. Z -> мир X
PIN_V = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1]])                     # штифт: лок. X -> мир Y (вертикально)
AXLE_V = PIN_V
BUSH_V = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0]])                    # втулка: лок. Z -> мир Y


def pin_pos(theta):
    """Палец в плоскости XZ. theta — угол мотора (град, растёт); phi = 90 - theta."""
    phi = np.radians(90 - theta)
    return np.array([R_PIN * np.cos(phi), R_PIN * np.sin(phi)])


def cross_angle(theta):
    """Поворот креста psi (град): стоит, пока палец вне паза; в окне зацепления следует за пальцем."""
    k = np.floor(theta / 360.0); s = theta - 360 * k
    if s < S0:
        return 90 * k
    if s > S1:
        return 90 * (k + 1)
    P = pin_pos(s)
    b = np.degrees(np.arctan2(P[1], P[0] - XC)) % 360
    return 90 * k + float(np.clip(b, 135, 225) - 135)


def engaged(theta):
    s = theta % 360
    return S0 <= s <= S1


def build(theta=0.0):
    P = []

    def add(group, color, part, pos, rot=I, note=''):
        P.append(dict(group=group, color=color, part=part, pos=np.array(pos, float), rot=np.array(rot, float), note=note))

    # ---------- 1. Основание: две балки 1x15 лёжа, вдоль X ----------
    for z, nm in ((0, 'основание перед'), (140, 'основание зад')):
        add('base', BLACK, '32278.dat', (80, 40, z), BEAM_X, nm)
    for x, z in ((-20, 0), (20, 0), (0, 140)):
        add('base_pin', BLACK, '2780.dat', (x, 30, z), PIN_V, 'штифт мотор-основание')
    # ---------- 2. Мотор: корпус неподвижен, ротор крутится ----------
    add('motor', WHITE, 'u9364c01.dat', (0, 0, 0), I, 'мотор: корпус')
    Rm = rot_y_math(-theta)
    add('rotor', AZURE, 'u9363.dat', (0, -50, 0), Rm, 'мотор: ротор')
    # ---------- 3. Кривошип ----------
    phi = 90 - theta
    Rc = rot_y_math(phi)                     # лок. X кривошипа -> направление на палец
    d = Rc @ np.array([1.0, 0, 0])
    add('crank', AZURE, '32524.dat', (40 * d[0], -60, 40 * d[2]), Rc @ BEAM_X, 'кривошип 1x7')
    for r in (-20, 20):
        add('crank', BLACK, '2780.dat', (r * d[0], -50, r * d[2]), PIN_V, 'штифт кривошип-ротор')
    pp = pin_pos(theta)
    add('drivepin', BLUE, '6558.dat', (pp[0], -80, pp[1]), PIN_V, 'палец 3L')
    # ---------- 4. Ось креста и втулка ----------
    psi = cross_angle(theta)
    g = 135 + psi
    Rx = rot_y_math(g)
    add('axle', LTGREY, '60485.dat', (XC, -40, 0), Rx @ AXLE_V, 'ось 9')
    add('axle', LTGREY, '3713.dat', (XC, 20, 0), Rx @ BUSH_V, 'втулка')
    # ---------- 5. Крест ----------
    def W(lx, lz):
        v = Rx @ np.array([lx, 0, lz]); return XC + v[0], v[2]
    for lx in (-20, 20):                      # слой B: балки вдоль лок. Z
        x, z = W(lx, 0); add('cross', MAGENTA, '32525.dat', (x, -80, z), Rx, 'крест B 1x11')
    for lz in (-20, 20):                      # слой A: балки вдоль лок. X
        x, z = W(0, lz); add('cross', MAGENTA, '32525.dat', (x, -100, z), Rx @ BEAM_X, 'крест A 1x11')
    for lx in (-20, 20):
        for lz in (-20, 20):
            x, z = W(lx, lz); add('cross', BLACK, '2780.dat', (x, -90, z), PIN_V, 'штифт A-B')
    x, z = W(0, 0); add('hub', AZURE, '60483.dat', (x, -120, z), Rx, 'ступица 1x2')
    x, z = W(0, 20); add('hub', BLACK, '2780.dat', (x, -110, z), PIN_V, 'штифт ступицы')
    return P


def write_ldr(parts, path, title='Мальтийский механизм'):
    def fmt(c, part, pos, R):
        v = list(pos) + list(np.asarray(R).reshape(-1))
        return f'1 {c} ' + ' '.join(f'{x:.4f}'.rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0' for x in v) + f' {part}'
    lines = [f'0 {title}', '0 Name: ' + path.split('/')[-1], '0 Author: LEGObot', '']
    lines += [fmt(p['color'], p['part'], p['pos'], p['rot']) for p in parts]
    open(path, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    for th in (0, 53.13, 70, 90, 110, 126.87, 200, 360 + 90):
        print(th, round(cross_angle(th), 2), engaged(th))
    # проверка зазоров: палец — балки креста слоя, где паза нет; палец — центр
    worst = 1e9
    for th in np.arange(0, 360, 0.25):
        pp = pin_pos(th); psi = cross_angle(th); Rx = rot_y_math(135 + psi)
        loc = Rx.T @ np.array([pp[0] - XC, 0, pp[1]])      # палец в координатах креста
        lx, lz = loc[0], loc[2]
        # балки B: |lx| = 20, |lz| <= 109 ; балки A: |lz| = 20, |lx| <= 109; полуширина балки 9, радиус пальца 6
        for (a, b) in ((lx, lz), (lz, lx)):
            for w in (-20, 20):
                if abs(b) <= 109 + 6:
                    gap = abs(a - w) - 9 - 6
                    if gap < worst and abs(a) < 100:
                        worst = gap; wth = (th, round(lx, 1), round(lz, 1))
    print('мин. зазор палец-балка (LDU):', round(worst, 2), wth)
    print(len(build()), 'деталей')
