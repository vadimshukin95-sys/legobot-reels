"""Сценарий рилса «Мотор крутится ровно, а крест — рывками» — общий для scene.py (Blender), overlay.py и audio.py.
17 с, 30 к/с, 1080×1920. Модель рендерится плашкой 1080×860 (кадры PLATE_FIRST..PLATE_LAST)."""
import numpy as np
import geneva_model as M

FPS, DUR = 30, 17.0
FRAMES = int(FPS * DUR)                    # 510
T_ASM0, T_RUN, T_FAST, T_CARD = 2.0, 5.0, 12.4, 14.4
CARD_FADE = 0.45
PLATE_W, PLATE_H, MY = 1080, 860, 520      # плашка модели и её верх в кадре
PLATE_FIRST = int(T_ASM0 * FPS)            # 60
PLATE_LAST = int((T_CARD + CARD_FADE) * FPS) + 1
OMEGA = 90.0                               # град/с: оборот мотора за 4 с
OMEGA_FAST = 300.0                         # оборот за 1,2 с
T_ENG1 = 6.8                               # начало первого зацепления
THETA0 = M.S0 - OMEGA * (T_ENG1 - T_RUN)   # угол мотора в T_RUN
CAPS = [  # (начало, конец, текст, стиль)
    (5.0, 6.8, 'Мотор крутится ровно', 'sun'),
    (6.8, 8.8, 'Палец зашёл в паз —\nкрест повернулся на ¼', 'sun'),
    (8.8, 10.8, 'Палец вышел —\nкрест стоит и ждёт', 'sun'),
    (10.8, 12.4, 'Это мальтийский\nмеханизм', 'big'),
    (12.4, 14.4, 'Так плёнка шла в кинопроекторе:\nкадр — стоп — кадр', 'white'),
]
TITLE = ['МОТОР — РОВНО,', 'А КРЕСТ —', 'РЫВКАМИ. КАК?']
CAM = dict(lat=50, lon=-10, fov=25, target=(94, -60, 30))

ORDER = [
    lambda p: p['group'] == 'base',
    lambda p: p['group'] == 'base_pin',
    lambda p: p['group'] in ('motor', 'rotor'),
    lambda p: p['group'] == 'crank',
    lambda p: p['group'] == 'drivepin',
    lambda p: p['group'] == 'axle',
    lambda p: p['group'] == 'cross' and p['note'].startswith('крест B'),
    lambda p: p['group'] == 'cross',
    lambda p: p['group'] == 'hub',
]
STAG, DROP = 0.3, 0.36
LAND = [T_ASM0 + k * STAG + DROP for k in range(len(ORDER))]


def group_of(p):
    for k, f in enumerate(ORDER):
        if f(p):
            return k
    return 0


def theta_at(t):
    if t <= T_RUN:
        return THETA0
    if t <= T_FAST:
        return THETA0 + (t - T_RUN) * OMEGA
    # плавный разгон за 0,4 с
    th = THETA0 + (T_FAST - T_RUN) * OMEGA
    a = min(t - T_FAST, 0.4)
    th += OMEGA * a + (OMEGA_FAST - OMEGA) * a * a / 0.8
    if t > T_FAST + 0.4:
        th += (t - T_FAST - 0.4) * OMEGA_FAST
    return th


def dist_at(t):
    u = np.clip((t - T_RUN) / (T_FAST - T_RUN), 0, 1)
    u = u * u * (3 - 2 * u)
    return 920 - 60 * u


def ease_out(u):
    return 1 - (1 - u) ** 3


def parts_at(t):
    """Все детали с положением на момент t; у ещё не появившихся visible=False."""
    th = theta_at(t)
    out = []
    for p in M.build(th):
        g = group_of(p)
        s = T_ASM0 + g * STAG
        q = dict(p); q['pos'] = p['pos'].copy(); q['visible'] = t >= s
        u = min(1, max(0, (t - s) / DROP))
        if u < 1:
            q['pos'][1] -= 420 * (1 - ease_out(u))
        out.append(q)
    return out, th


def eye_target(t):
    la, lo = np.radians(CAM['lat']), np.radians(CAM['lon'])
    tg = np.array(CAM['target'], float); d = dist_at(t)
    eye = tg + d * np.array([np.sin(lo) * np.cos(la), -np.sin(la), -np.cos(lo) * np.cos(la)])
    return eye, tg


def look_at(eye, target, up=(0, -1, 0)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    s = np.cross(f, up); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    V = np.eye(4)
    V[0, :3], V[1, :3], V[2, :3] = s, u, -f
    V[:3, 3] = -V[:3, :3] @ eye
    return V


def perspective(fovy, aspect, near=50, far=5000):
    f = 1 / np.tan(np.radians(fovy) / 2)
    P = np.zeros((4, 4))
    P[0, 0] = f / aspect; P[1, 1] = f
    P[2, 2] = (far + near) / (near - far); P[2, 3] = 2 * far * near / (near - far); P[3, 2] = -1
    return P


def VP_at(t):
    eye, tg = eye_target(t)
    return perspective(CAM['fov'], PLATE_W / PLATE_H) @ look_at(eye, tg)


def project(t, pts):
    """LDraw-точки -> пиксели кадра 1080×1920 (с учётом места плашки)."""
    pts = np.atleast_2d(np.asarray(pts, float))
    hp = np.c_[pts, np.ones(len(pts))] @ VP_at(t).T
    ndc = hp[:, :3] / hp[:, 3:4]
    return np.c_[(ndc[:, 0] + 1) / 2 * PLATE_W, (1 - ndc[:, 1]) / 2 * PLATE_H + MY]


if __name__ == '__main__':
    for t in np.arange(5, 15, 0.2):
        th = theta_at(t)
        print(round(t, 1), round(th % 360, 1), round(M.cross_angle(th), 1), 'ЗАЦЕП' if M.engaged(th) else '')
