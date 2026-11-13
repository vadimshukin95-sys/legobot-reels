"""«Кувырки» — механический двоичный счётчик из LEGO Education SPIKE Prime (45678), своя модель LEGObot.
Три плашки (балки 1x15) кувыркаются на неподвижной оси; мотор крутит кривошип, он перекидывает плашку 0.
Память — мальтийский крестик на плашке: неподвижный зуб на оси поворачивает его на 1/4 за кувырок,
крючок крестика через раз оказывается напротив зацепа соседней плашки и тащит её через верх.
LDraw: LDU, Y вниз, к зрителю = -Z, вправо = +X. Главная ось — вдоль X на y=0, z=0.
Слои плашки k (x в шипах от x_k=-9k): s1 0 | s0 -1 | замок L -2 | зуб T -3 | крестик A -4, B -5 | ступица H -6 | зазор -7, -8.
Геометрия крестика: центр S в 7 шипах под осью, зуб на радиусе 5 (окно зацепления около 295 град кувырка),
крючки в отверстиях (1,3) и (-1,-3) крестика, зацеп следующей плашки — (u,v)=(-6,-1) на Т-балке.
Проверено физической симуляцией (phys/counter.py): счёт 0..16 без ошибок."""
import numpy as np

BLACK, AZURE, MAGENTA, YELLOW, LBG, WHITE, TAN, BLUE, RED = 0, 322, 26, 14, 71, 15, 19, 1, 4
I = np.eye(3)
PITCH = 9
C_STAR, R_TOOTH, WIN = 7, 5, 295.0
D_T = np.array([0.0, np.cos(np.radians(-115)) * -1, np.sin(np.radians(-115)) * -1])   # (x,y,z): u,v -> y=-u, z=-v
STAR_PART = ['32525.dat', '40490.dat']      # 1x11 пурпурная, 1x9 чёрная
STAR_COL = [MAGENTA, BLACK]


def Rx(a):
    c, s = np.cos(a), np.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])


def M_in_plane(d):
    """ориентация балки/детали с отверстиями вдоль X и длиной вдоль d=(0,dy,dz)"""
    d = np.asarray(d, float); d = d / np.linalg.norm(d)
    cy = np.array([1.0, 0, 0]); cz = d; cx = np.cross(cy, cz)
    return np.column_stack([cx, cy, cz])


M_U = M_in_plane((0, 1, 0))          # балка вдоль Y
M_V = M_in_plane((0, 0, 1))          # балка вдоль Z
M_AX = I                              # оси и штифты — вдоль X
M_AXZ = np.column_stack([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])   # детали с осью вдоль лок. Z (втулка, соединитель) -> X


def build(state):
    """state: theta=[3] прогресс кувырка, град; psi=[2] угол крестиков, град; crank — угол кривошипа, град"""
    P = []

    def add(group, color, part, pos, rot=I, note=''):
        P.append(dict(group=group, color=color, part=part, pos=np.array(pos, float), rot=np.array(rot, float), note=note))

    th = [np.radians(t) for t in state['theta']]
    ps = [np.radians(t) for t in state['psi']]
    # ---------------- рама: 2 жёлтые базовые пластины 19x11, две рамы 11x15 (левая — опора оси, правая — мотор)
    M_base = np.column_stack([[0, 0, -1.0], [0, 1.0, 0], [1.0, 0, 0]])     # лок. Z -> X, отверстия вертикально
    for cx in (-12, 7):
        add('frame', YELLOW, '39369.dat', (cx * 20, 300, 0), M_base, 'основание 19x11')
    M_frame = np.column_stack([[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]])     # отверстия вдоль X, длинная сторона вниз
    M_cb = np.column_stack([[1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])       # крест-блок: оси вдоль X, штифт вниз
    M_pinV = np.column_stack([[0, 1.0, 0], [1.0, 0, 0], [0, 0, -1.0]])     # штифт вертикально
    for fx, bx, nm in ((-20, -21, 'левая стойка'), (6, 7, 'стойка мотора')):
        add('frame', AZURE, '39790.dat', (fx * 20, 140, 0), M_frame, nm + ' 11x15')
        for z0 in (0,):          # ножка: крест-блок на штифте в основании + ось 2 в нижний ряд рамы
            add('frame', WHITE, '32184.dat', (bx * 20, 280, z0), M_cb, nm + ': крест-блок')
            add('frame', BLACK, '2780.dat', (bx * 20, 290, z0), M_pinV, nm + ': штифт в основание')
            for dz in (-20, 20):
                add('frame', RED, '32062.dat', ((fx + bx) * 10, 280, z0 + dz), M_AX, nm + ': ось 2')
    add('frame', WHITE, '32184.dat', (-21 * 20, 0, 20), M_cb, 'замок главной оси')
    add('frame', RED, '32062.dat', (-20.5 * 20, 0, 40), M_AX, 'ось-фиксатор 2')
    for dz in (-20, 20):
        add('frame', BLACK, '2780.dat', (5.5 * 20, 0, dz), M_AX, 'штифт мотор-рама')
    # ---------------- главная неподвижная ось: 9 + соединитель + 9 + соединитель + 5
    add('axle', LBG, '60485.dat', (-3.0 * 20, 0, 0), M_AX, 'ось 9 (правая)')
    add('axle', WHITE, '6538a.dat', (-7.5 * 20, 0, 0), M_AXZ, 'соединитель осей')
    add('axle', LBG, '60485.dat', (-12.0 * 20, 0, 0), M_AX, 'ось 9 (средняя)')
    add('axle', WHITE, '6538a.dat', (-16.5 * 20, 0, 0), M_AXZ, 'соединитель осей')
    add('axle', LBG, '32073.dat', (-19.0 * 20, 0, 0), M_AX, 'ось 5 (левая)')
    # ---------------- мотор (выход к плашкам, корпус вниз), ротор, кривошип
    M_mot = np.column_stack([[0, 0, 1.0], [1.0, 0, 0], [0, 1.0, 0]])
    add('motor', WHITE, 'u9364c01.dat', (80, 0, 0), M_mot, 'мотор: корпус')
    ac = np.radians(state['crank'])
    add('crank', AZURE, 'u9363p01.dat', (30, 0, 0), M_mot @ np.array([[np.cos(-ac), 0, np.sin(-ac)], [0, 1, 0], [-np.sin(-ac), 0, np.cos(-ac)]]), 'мотор: ротор')
    d = np.array([0, np.cos(ac), -np.sin(ac)])
    add('crank', AZURE, '32524.dat', (20, 40 * d[1], 40 * d[2]), M_in_plane(d), 'кривошип 1x7')
    for r in (-1, 1):
        add('crank', BLACK, '2780.dat', (30, 20 * r * d[1], 20 * r * d[2]), M_AX, 'штифт кривошип-ротор')
    add('crank', BLUE, '6558.dat', (0, 100 * d[1], 100 * d[2]), M_AX, 'палец кривошипа 3L')
    add('hub', YELLOW, '45601.dat', (12 * 20, 290, 0), I, 'хаб SPIKE Prime')
    # ---------------- плашки
    for k in range(3):
        x0 = -PITCH * k * 20
        R = Rx(-th[k]); g = f'plate{k}'

        def addp(group, color, part, pl, rot=I, note=''):
            add(group, color, part, np.array([x0, 0, 0]) + R @ (np.array(pl, float) - np.array([x0, 0, 0])), R @ rot, note)
        for dx, nm in ((0, 's1'), (-20, 's0')):
            addp(g, BLACK, '32278.dat', (x0 + dx, 100, 0), M_U, f'плашка {k}: балка 1x15 {nm}')
        if k > 0:   # Т-балка с зацепом в зазоре справа
            addp(g, BLACK, '60484.dat', (x0 + 20, 120, 0), M_in_plane((0, -1, 0)), f'плашка {k}: Т-балка')
            for y in (80, 100):
                addp(g, BLACK, '2780.dat', (x0 + 10, y, 0), M_AX, 'штифт Т-балка')
            addp('catch', TAN, '3749.dat', (x0 + 30, 120, 20), M_AX, f'плашка {k}: зацеп')
        if k < 2:   # крестик
            Rs = Rx(ps[k]); ys = 20 * C_STAR

            def adds(group, color, part, sl, rot=I, note=''):
                q = np.array([0, ys, 0]) + Rs @ np.array(sl, float)
                addp(group, color, part, (x0 + q[0], q[1], q[2]), Rs @ rot, note)
            sp, sc = STAR_PART[k], STAR_COL[k]
            for b in (-1, 1):     # слой A: балки вдоль a (лок. Y звезды), b=+-1 -> z=-20b
                adds(f'star{k}', sc, sp, (-80, 0, -20 * b), M_U, 'крестик A')
            for a in (-1, 1):     # слой B: балки вдоль b, a=+-1 -> y=-20a
                adds(f'star{k}', sc, sp, (-100, -20 * a, 0), M_V, 'крестик B')
            for a in (-1, 1):
                for b in (-1, 1):
                    adds(f'star{k}', BLACK, '2780.dat', (-90, -20 * a, -20 * b), M_AX, 'штифт A-B')
            adds(f'star{k}', AZURE, '60483.dat', (-120, 0, 0), M_in_plane((0, -1, 0)), 'ступица крестика')
            adds(f'star{k}', BLACK, '2780.dat', (-110, -20, 0), M_AX, 'штифт ступицы')
            adds(f'star{k}', YELLOW, '44294.dat', (-60, 0, 0), M_AX, 'ось крестика 7')
            for (a, b) in ((1, 3), (-1, -3)):
                adds('hook', BLUE, '6558.dat', (-120, -20 * a, -20 * b), M_AX, 'крючок 3L')
            # неподвижные замок и зуб (в мире, не вращаются)
            add('fixed', AZURE, '60483.dat', (x0 - 40, 0, 0), M_in_plane(D_T), 'замок зуба')
            add('fixed', AZURE, '32524.dat', (x0 - 60, 40 * D_T[1], 40 * D_T[2]), M_in_plane(D_T), 'балка зуба 1x7')
            add('fixed', BLACK, '2780.dat', (x0 - 50, 20 * D_T[1], 20 * D_T[2]), M_AX, 'штифт замок-балка')
            add('fixed', BLUE, '6558.dat', (x0 - 80, 100 * D_T[1], 100 * D_T[2]), M_AX, 'зуб 3L')
    return P


def write_ldr(parts, path, title='Кувырки — двоичный счётчик'):
    def fmt(c, part, pos, R):
        v = list(pos) + list(np.asarray(R).reshape(-1))
        return f'1 {c} ' + ' '.join(f'{x:.4f}'.rstrip('0').rstrip('.') if abs(x) > 1e-9 else '0' for x in v) + f' {part}'
    lines = [f'0 {title}', '0 Name: ' + path.split('/')[-1], '0 Author: LEGObot', '']
    lines += [fmt(p['color'], p['part'], p['pos'], p['rot']) for p in parts]
    open(path, 'w').write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    st = dict(theta=[0, 0, 0], psi=[-45.21, -45.38], crank=-40)
    P = build(st); print(len(P), 'деталей')
    from collections import Counter
    for (part, col), n in sorted(Counter((p['part'], p['color']) for p in P).items()): print(n, part, col)
    write_ldr(P, 'kuvyrki_rest.ldr')
