"""Сценарий рилса «Две двери, одна шестерёнка» — общий для scene.py (Blender), overlay.py и audio.py.
12 с, 30 к/с, 1080×1920, ролик зациклен: последний кадр = первому (двери закрыты, общий план).
Модель рендерится плашкой 1080×860 на всю длину ролика (кадр плашки f0001 = кадр ролика 0)."""
import numpy as np
import dveri_model as M

FPS, DUR = 30, 12.0
FRAMES = int(FPS * DUR)                       # 360
PLATE_W, PLATE_H, MY = 1080, 860, 520         # плашка модели и её верх в кадре
PLATE_FIRST, PLATE_LAST = 0, FRAMES - 1

T_OPEN0, T_OPEN1 = 0.7, 5.2                   # открываются медленно, камера в это время наезжает на шестерню
T_CLOSE0, T_CLOSE1 = 7.2, 10.7                # закрываются на общем плане
ZOOM_IN = (0.9, 3.2)                          # наезд
ZOOM_OUT = (5.6, 7.0)                         # отъезд
XRAY_IN = (2.0, 2.8)                          # мосты и двери становятся полупрозрачными
XRAY_OUT = (5.4, 6.2)
XRAY_ALPHA = 0.22
ARROWS = (2.4, 5.2)                           # стрелки движения поверх механизма

CAPS = [  # (начало, конец, текст, стиль)
    (0.7, 2.1, 'Мотор крутит\nодну шестерню', 'sun'),
    (2.35, 5.2, 'Сверху рейка — вправо,\nснизу — влево', 'sun'),
    (5.45, 6.95, 'Это реечная\nпередача', 'big'),
    (7.2, 10.9, 'Мотор назад —\nдвери закрылись', 'white'),
]
TITLE = ['ДВЕ ДВЕРИ —', 'ОДНА', 'ШЕСТЕРЁНКА']

CAM = dict(lat=10, lon=-14, fov=25)
WIDE = dict(dist=960.0, target=(0.0, 20.0, 40.0))
CLOSE = dict(dist=680.0, target=(0.0, 0.0, 30.0))


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_out(u):
    return 1 - (1 - u) ** 3


def travel(t):
    """Ход дверей s (LDU) в момент t."""
    if t < T_CLOSE0:
        return M.S_OPEN * smooth((t - T_OPEN0) / (T_OPEN1 - T_OPEN0))
    return M.S_OPEN * (1 - smooth((t - T_CLOSE0) / (T_CLOSE1 - T_CLOSE0)))


def zoom(t):
    a = smooth((t - ZOOM_IN[0]) / (ZOOM_IN[1] - ZOOM_IN[0]))
    b = smooth((t - ZOOM_OUT[0]) / (ZOOM_OUT[1] - ZOOM_OUT[0]))
    return a * (1 - b)


def xray(t):
    """Непрозрачность мостов и дверей: 1 — обычные, XRAY_ALPHA — «рентген»."""
    a = smooth((t - XRAY_IN[0]) / (XRAY_IN[1] - XRAY_IN[0]))
    b = smooth((t - XRAY_OUT[0]) / (XRAY_OUT[1] - XRAY_OUT[0]))
    k = a * (1 - b)
    return 1 - (1 - XRAY_ALPHA) * k


def parts_at(t):
    return M.build(travel(t)), travel(t)


def eye_target(t):
    z = zoom(t)
    d = WIDE['dist'] + (CLOSE['dist'] - WIDE['dist']) * z
    tg = np.array(WIDE['target']) + (np.array(CLOSE['target']) - np.array(WIDE['target'])) * z
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


if __name__ == '__main__':
    for t in np.arange(0, DUR + 0.01, 0.5):
        print(f'{t:5.1f}  s={travel(t):6.1f}  zoom={zoom(t):.2f}  xray={xray(t):.2f}')
