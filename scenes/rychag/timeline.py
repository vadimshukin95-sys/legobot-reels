"""Сценарий рилса «1 груз сильнее трёх?» (рычаг) — общий для scene.py, overlay.py и audio.py.
18,5 с, 30 к/с, 1080×1920. Blender рендерит плашку модели 1080×1500 (верх плашки в кадре — MY).
Камера неподвижна; уникальные кадры — только пока петля скользит и балка качается: UNIQUE, SRC[i] — откуда брать плашку.
Справа всё время 3 груза на 2-м отверстии; слева 1 груз, его петля скользит: 5 -> 7 -> 6 -> 5 -> 6.
Балка следует за углом равновесия (rych_model.theta_eq) как маятник с затуханием — честная статика + лёгкое покачивание."""
import numpy as np
import rych_model as M

FPS, DUR = 30, 18.5
FRAMES = int(round(FPS * DUR))                  # 555
PLATE_W, PLATE_H, MY = 1080, 1500, 420

SLIDES = [((0.35, 1.75), 5, 7),                 # крючок: один груз перевешивает три
          ((3.70, 4.90), 7, 6),                 # равновесие
          ((8.95, 10.15), 6, 5),                # перевесили три
          ((11.45, 12.45), 5, 6)]               # снова равновесие
CARD = 16.3

TITLE = ['1 ГРУЗ', 'СИЛЬНЕЕ', 'ТРЁХ?']
CAPS = [  # (начало, конец, текст, стиль, y центра)
    (1.95, 3.5, 'Перевесил!', 'sun', 1700),
    (3.65, 5.0, 'Сдвинем петлю\nна одно отверстие', 'sun', 1700),
    (5.15, 8.7, 'Равновесие', 'big', 1600),
    (5.6, 8.7, '1 груз × 6 = 3 груза × 2', 'sun', 1745),
    (8.9, 11.0, 'Ещё на одно —\nи перевесили три', 'sun', 1700),
    (12.3, 14.0, 'Правило рычага', 'big', 1590),
    (12.7, 14.0, 'груз × плечо слева =\nгруз × плечо справа', 'sun', 1755),
    (14.2, 16.1, 'Где ещё рычаг?', 'big', 1520),
]
WHERE = [(14.6, 'Качели'), (14.95, 'Ножницы'), (15.3, 'Гаечный ключ')]
COUNT = [(5.4, 8.7), (12.5, 14.0)]              # окна, когда на балке нумеруем отверстия (плечи)

CAM = dict(lat=9, lon=12, fov=30)
VIEW = dict(dist=890.0, target=(-10.0, 100.0, 10.0))


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_out(u):
    u = float(np.clip(u, 0, 1)); return 1 - (1 - u) ** 3


def kl_at(t):
    """Отверстие левого груза (дробное — петля в пути)."""
    k = SLIDES[0][1]
    for (a, b), k0, k1 in SLIDES:
        if t < a:
            return k
        if t < b:
            return k0 + (k1 - k0) * smooth((t - a) / (b - a))
        k = k1
    return k


# угол балки: маятник с затуханием, тянется к углу равновесия (интегрируем заранее, шаг 1/1200 с)
_DT = 1 / 1200
_W, _Z = 2 * np.pi * 1.25, 0.42
_T = np.arange(0, DUR + 0.5, _DT)
_TH = np.zeros_like(_T)
_th, _v = M.theta_eq(kl_at(0)), 0.0
for _j, _t in enumerate(_T):
    _TH[_j] = _th
    _acc = _W * _W * (M.theta_eq(kl_at(_t)) - _th) - 2 * _Z * _W * _v
    _v += _acc * _DT; _th += _v * _DT


def state(t):
    """(theta, kl) в момент t."""
    th = float(np.interp(t, _T, _TH))
    eq = M.theta_eq(kl_at(t))
    if abs(th - eq) < 0.03:
        th = eq
    return round(th, 2), round(kl_at(t), 3)


def eye_target(t=0.0):
    tg = np.array(VIEW['target'])
    la, lo = np.radians(CAM['lat']), np.radians(CAM['lon'])
    eye = tg + VIEW['dist'] * np.array([np.sin(lo) * np.cos(la), -np.sin(la), -np.cos(lo) * np.cos(la)])
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


def VP_at(t=0.0):
    eye, tg = eye_target(t)
    return perspective(CAM['fov'], PLATE_W / PLATE_H) @ look_at(eye, tg)


def project(t, pts):
    """LDraw-точки -> пиксели кадра 1080×1920 (с учётом места плашки)."""
    pts = np.atleast_2d(np.asarray(pts, float))
    hp = np.c_[pts, np.ones(len(pts))] @ VP_at(t).T
    ndc = hp[:, :3] / hp[:, 3:4]
    return np.c_[(ndc[:, 0] + 1) / 2 * PLATE_W, (1 - ndc[:, 1]) / 2 * PLATE_H + MY]


def key(i):
    return state(i / FPS)


SRC, UNIQUE = [], []
_seen = {}
for _i in range(FRAMES):
    _k = key(_i)
    if _k not in _seen:
        _seen[_k] = _i; UNIQUE.append(_i)
    SRC.append(_seen[_k])

if __name__ == '__main__':
    print('кадров', FRAMES, 'уникальных', len(UNIQUE))
    for t in np.arange(0, DUR + 0.01, 0.25):
        th, kl = state(t)
        print(f'{t:5.2f}  theta={th:6.2f}  kl={kl:5.2f}  eq={M.theta_eq(kl):6.2f}')
