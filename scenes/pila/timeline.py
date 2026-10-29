"""Сценарий рилса «Как колесо превращается в пилу?» — общий для scene.py (Blender) и overlay.py (подписи).
17 с, 30 к/с, 1080×1920. Модель рендерится плашкой 1080×700 (кадры PLATE_FIRST..PLATE_LAST)."""
import math, numpy as np
import pila_model as M

FPS, DUR = 30, 17.0
FRAMES = int(FPS * DUR)                    # 510
T_ASM0, T_RUN, T_FAST, T_CARD = 2.0, 5.0, 12.0, 14.0
CARD_FADE = 0.45
PLATE_W, PLATE_H, MY = 1080, 700, 640      # плашка модели и её верх в кадре
PLATE_FIRST = int(T_ASM0 * FPS)            # индекс кадра (с 0): 60
PLATE_LAST = int((T_CARD + CARD_FADE) * FPS) + 1   # 434
CAPS = [  # (начало, конец, текст, стиль)
    (5.0, 6.7, 'Мотор крутит колесо', 'sun'),
    (6.7, 8.4, 'Палец на колесе\nходит по кругу', 'sun'),
    (8.4, 10.2, 'Шатун толкает пилу\nтуда-сюда', 'sun'),
    (10.2, 12.0, 'Это кривошип', 'big'),
    (12.0, 14.0, 'Кривошип есть в велосипеде,\nшвейной машинке и лобзике', 'white'),
]
CAM = dict(lat=14, lon=-18, fov=25, target=(8, -58, 0))

# ---------- сборка: группы деталей по порядку ----------
ORDER = [
    lambda p: p['group'] == 'base',
    lambda p: p['group'] == 'motor',
    lambda p: p['group'] in ('drive', 'bear'),
    lambda p: p['group'] == 'crank',
    lambda p: p['group'] == 'frame',
    lambda p: p['group'] == 'slider' and p['part'] == '3701.dat',
    lambda p: p['group'] == 'rail',
    lambda p: p['group'] == 'slider' and p['part'] in ('2458.dat', '3004.dat'),
    lambda p: p['group'] == 'slider' and p['part'] in ('3738.dat', '3665a.dat'),
    lambda p: p['group'] == 'rod',
]
STAG, DROP = 0.29, 0.36
LAND = [T_ASM0 + k * STAG + DROP for k in range(len(ORDER))]


def group_of(p):
    for k, f in enumerate(ORDER):
        if f(p):
            return k
    return 0


def theta_at(t):
    w = 360 / 3.5
    th = 0.0
    for a, b, om in [(T_RUN, 8.4, w), (8.4, 10.2, w * 0.6), (10.2, T_FAST, w), (T_FAST, DUR, 360 / 1.4)]:
        if t > a:
            th += (min(t, b) - a) * om
    return th


def dist_at(t):
    u = np.clip((t - T_RUN) / (T_FAST - T_RUN), 0, 1)
    u = u * u * (3 - 2 * u)
    return 600 - 45 * u


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
            if p['group'] == 'rail':
                q['pos'][0] += 340 * (1 - ease_out(u))      # ось вдвигается сквозь рамки справа
            else:
                q['pos'][1] -= 420 * (1 - ease_out(u))
        out.append(q)
    return out, th


# ---------- камера (LDraw: Y вниз, вперёд = -Z) ----------
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
