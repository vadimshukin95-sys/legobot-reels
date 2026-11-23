"""Сценарий рилса «Отпустил — а он не падает?» (храповик) — общий для scene.py, overlay.py и audio.py.
20 с, 30 к/с, 1080×1920. Blender рендерит плашку модели 1080×1500 (до низа кадра — крупный план не обрезается краем плашки) (верх плашки в кадре — MY).
Кадры с одинаковым состоянием (модель + камера) рендерятся один раз: UNIQUE — список кадров для рендера, SRC[i] — откуда брать плашку."""
import numpy as np
import hrap_model as M

FPS, DUR = 30, 20.0
FRAMES = int(FPS * DUR)                         # 600
PLATE_W, PLATE_H, MY = 1080, 1500, 420

G_LIFT = -345.0                                 # 23 зуба
G_LOCK, PAWL_LOCK = M.TAB['g_lock'], M.TAB['pawl_lock']
PAWL_UP = 28.0
LIFT_PER = np.array(M.TAB['lift_period'])                      # собачка за один зуб (g = 0…-15°), дальше период
G_END, PAWL_END = 0.0, float(LIFT_PER[0])          # груз лёг на пол — барабан встал там же, где начинал
REL_T = np.array([x[0] for x in M.TAB['release']]); REL_P = np.array([x[1] for x in M.TAB['release']])

T_CUT = 2.2                                     # крючок (груз висит) -> начало (груз на полу)
LIFT = (3.0, 8.0)
RELEASE = (8.0, 8.25)
PAWL_LIFT = (13.0, 13.4)
FALL = (13.55, 14.1)
PAWL_DOWN = (15.6, 16.0)
ZOOM_IN = (9.9, 10.8)
ZOOM_OUT = (12.3, 12.95)
CARD = 18.0                                     # финальная карточка

TITLE = ['ОТПУСТИЛ —', 'А ОН', 'НЕ ПАДАЕТ?']
CAPS = [  # (начало, конец, текст, стиль, y центра)
    (3.2, 7.8, 'Крутим ручку —\nщёлк-щёлк-щёлк', 'sun', 1700),
    (8.3, 9.9, 'Отпустили…\nа груз висит!', 'white', 1700),
    (10.7, 12.7, 'Это храповик', 'big', 1640),
    (11.2, 12.7, 'Зуб упёрся в собачку', 'sun', 1780),
    (13.0, 15.3, 'Подняли собачку —\nбум!', 'sun', 1700),
    (15.6, 17.9, 'Где ещё храповик?', 'big', 1560),
]
WHERE = [(16.0, 'Ключ-трещотка'), (16.35, 'Втулка велосипеда'), (16.7, 'Лебёдка, рулетка')]

CAM = dict(lat=14, lon=30, fov=36)
WIDE = dict(dist=640.0, target=(28.0, 92.0, -10.0))
CLOSE = dict(dist=330.0, target=(64.0, -19.0, -50.0))


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = float(np.clip(u, 0, 1)); return 1 - (1 - u) ** 3


def seg(t, a):
    return (t - a[0]) / (a[1] - a[0])


def state(t):
    """(g, pawl, dy) в момент t."""
    if t < T_CUT:                                           # крючок: груз висит
        g, p = G_LOCK, PAWL_LOCK
    elif t < LIFT[0]:
        g, p = 0.0, float(LIFT_PER[0])
    elif t < LIFT[1]:                                       # крутим ручку
        g = G_LIFT * smooth(seg(t, LIFT))
        p = float(np.interp((-g) % M.TAB['tooth'], np.arange(len(LIFT_PER)), LIFT_PER))
    elif t < RELEASE[1]:                                    # отпустили: проседает до упора
        u = float(np.clip(seg(t, RELEASE), 0, 1)) ** 2
        g = G_LIFT + (G_LOCK - G_LIFT) * u
        p = float(np.interp(g, REL_T, REL_P))
    elif t < PAWL_LIFT[0]:
        g, p = G_LOCK, PAWL_LOCK
    elif t < FALL[0]:                                       # поднимаем собачку
        g = G_LOCK; p = PAWL_LOCK + (PAWL_UP - PAWL_LOCK) * smooth(seg(t, PAWL_LIFT))
    elif t < FALL[1]:                                       # падает (ускоряясь)
        u = float(np.clip(seg(t, FALL), 0, 1)) ** 2
        g = G_LOCK + (G_END - G_LOCK) * u; p = PAWL_UP
    elif t < PAWL_DOWN[0]:
        g, p = G_END, PAWL_UP
    else:                                                   # собачку отпустили — легла на зубья
        g = G_END; p = PAWL_UP + (PAWL_END - PAWL_UP) * smooth(seg(t, PAWL_DOWN))
    dy = min(0.0, float(M.load_dy(g)))
    return g, p, dy


def zoom(t):
    return smooth(seg(t, ZOOM_IN)) * (1 - smooth(seg(t, ZOOM_OUT)))


def shake(t):
    """Лёгкая встряска камеры при ударе груза об пол."""
    u = t - FALL[1]
    return 0.0 if u < 0 or u > 0.25 else 6.0 * np.exp(-u * 14) * np.sin(u * 60)


def eye_target(t):
    z = zoom(t)
    d = WIDE['dist'] + (CLOSE['dist'] - WIDE['dist']) * z
    tg = np.array(WIDE['target']) + (np.array(CLOSE['target']) - np.array(WIDE['target'])) * z
    tg = tg + np.array([0, shake(t), 0])
    la, lo = np.radians(CAM['lat']), np.radians(CAM['lon'])
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


def key(i):
    t = i / FPS
    g, p, dy = state(t); eye, tg = eye_target(t)
    return tuple(np.round([g, p, dy, *eye, *tg], 3))


SRC, UNIQUE = [], []
_seen = {}
for _i in range(FRAMES):
    _k = key(_i)
    if _k not in _seen:
        _seen[_k] = _i; UNIQUE.append(_i)
    SRC.append(_seen[_k])

if __name__ == '__main__':
    print('кадров', FRAMES, 'уникальных', len(UNIQUE))
    for t in np.arange(0, DUR + 0.01, 0.5):
        g, p, dy = state(t)
        print(f'{t:5.1f}  g={g:8.1f}  собачка={p:6.1f}  груз dy={dy:6.1f}  zoom={zoom(t):.2f}')
