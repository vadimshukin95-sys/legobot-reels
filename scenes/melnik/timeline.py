"""Сценарий рилса «Кто кого крутит?» (WeDo 2.0, «Мельник» из курса «Инженерная мастерская») — общий для scene.py и overlay.py.
19,5 с, 30 к/с, 1080×1920. Модель рендерится плашкой PLATE_W×PLATE_H (кадры PLATE_FIRST..PLATE_LAST)."""
import numpy as np
import melnik_model as M

FPS, DUR = 30, 19.5
FRAMES = int(FPS * DUR)                     # 585
T_RUN = 2.6                                 # мельница заработала
T_TOP0, T_TOP = 6.2, 7.2                    # переезд камеры сверху
T_X0, T_X1 = 11.0, 14.4                     # «рентген»: палуба и жернов скрыты, всё замедлено
T_BACK = 15.2                               # камера вернулась в общий план
T_CARD = 16.4
CARD_FADE = 0.45
PLATE_W, PLATE_H, MY = 1080, 1080, 470      # плашка модели и её верх в кадре
PLATE_FIRST = 0
PLATE_LAST = int((T_CARD + CARD_FADE) * FPS) + 1
SENSOR = (0.9, 2.6)                         # «ладонь у датчика»: волны от головы

CAPS = [  # (начало, конец, текст, стиль)
    (0.9, 2.6, 'Подносим ладонь к датчику', 'white'),
    (2.8, 6.2, 'Мельник крутит жернов?', 'sun'),
    (6.4, 8.4, 'Нет! Это жернов\nкрутит мельника', 'big'),
    (8.4, 9.7, 'Палец на жернове\nходит по кругу', 'sun'),
    (9.7, 11.0, 'Балка тянет плечо —\nмельник поворачивается', 'sun'),
    (11.1, 12.8, 'Внутри: червяк\nи шестерня на 24 зуба', 'white'),
    (12.8, 14.4, 'Жернов крутится\nв 24 раза медленнее мотора', 'sun'),
    (14.6, 16.4, '1 мотор → 2 движения', 'big'),
]

# скрыто на «рентгене» (палуба, жернов, мешки, замок мотора, палец и рука, мельник)
XRAY_HIDE = ('deck', 'mill', 'sacks', 'pin', 'arm', 'robot', 'shpin', 'hub')
XRAY_KEEP_NOTES = ('ось 6 вертикальная',)
XRAY_HIDE_NOTES = ('замок мотора 2x4', 'проставка на мотор')

# ---------- скорость жернова (град/с) ----------
W_RUN = 360 / 5.0                           # оборот жернова за 5 с
SEGS = [(T_RUN, T_X0, W_RUN), (T_X0, T_X1, W_RUN * 0.25), (T_X1, T_CARD + CARD_FADE + 0.1, W_RUN)]
TH_START = M.TH0                            # мельник смотрит прямо на жернов


def theta_at(t):
    th = TH_START
    for a, b, om in SEGS:
        if t > a:
            th += (min(t, b) - a) * om
    return th


def xray(t):
    return T_X0 <= t < T_X1


def parts_at(t):
    th = theta_at(t)
    out = []
    hide = xray(t)
    for p in M.build(th):
        q = dict(p)
        v = True
        if hide and (p['group'] in XRAY_HIDE or p['note'] in XRAY_HIDE_NOTES) and p['note'] not in XRAY_KEEP_NOTES:
            v = False
        q['visible'] = v
        out.append(q)
    return out, th


# ---------- камера (LDraw: Y вниз, вперёд = -Z) ----------
#            t      lat  lon   dist  target(x, y, z)                fov
KEYS = [(0.0, 18, -32, 840, (95, -100, 40), 24),
        (T_TOP0, 20, -28, 820, (95, -105, 35), 24),
        (T_TOP, 72, -6, 690, (112, -165, -30), 24),
        (T_X0 - 0.01, 72, -2, 680, (112, -165, -30), 24),
        (T_X0, 38, -38, 520, (30, -30, 15), 24),
        (T_X1, 34, -46, 500, (30, -30, 15), 24),
        (T_BACK, 18, -32, 840, (95, -100, 40), 24),
        (DUR, 16, -26, 820, (95, -100, 40), 24)]


def smooth(u):
    u = min(1, max(0, u))
    return u * u * (3 - 2 * u)


def cam_params(t):
    for (t0, *a), (t1, *b) in zip(KEYS, KEYS[1:]):
        if t0 <= t <= t1:
            if t0 == T_X0 - 0.01 or t1 - t0 < 0.02:
                u = 1.0 if t >= t1 else 0.0
            elif t0 == T_X0:                   # на «рентгене» — медленный наезд по прямой
                u = (t - t0) / (t1 - t0)
            else:
                u = smooth((t - t0) / (t1 - t0))
            lat, lon, d = (a[k] + (b[k] - a[k]) * u for k in range(3))
            tg = np.array(a[3], float) + (np.array(b[3], float) - np.array(a[3], float)) * u
            fov = a[4] + (b[4] - a[4]) * u
            return lat, lon, d, tg, fov
    lat, lon, d, tg, fov = KEYS[-1][1:]
    return lat, lon, d, np.array(tg, float), fov


def eye_target(t):
    lat, lon, d, tg, fov = cam_params(t)
    la, lo = np.radians(lat), np.radians(lon)
    eye = tg + d * np.array([np.sin(lo) * np.cos(la), -np.sin(la), -np.cos(lo) * np.cos(la)])
    return eye, tg, fov


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
    eye, tg, fov = eye_target(t)
    return perspective(fov, PLATE_W / PLATE_H) @ look_at(eye, tg)


def project(t, pts):
    """LDraw-точки -> пиксели кадра 1080×1920 (с учётом места плашки)."""
    pts = np.atleast_2d(np.asarray(pts, float))
    hp = np.c_[pts, np.ones(len(pts))] @ VP_at(t).T
    ndc = hp[:, :3] / hp[:, 3:4]
    return np.c_[(ndc[:, 0] + 1) / 2 * PLATE_W, (1 - ndc[:, 1]) / 2 * PLATE_H + MY]
