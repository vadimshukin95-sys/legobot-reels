"""Сценарий рилса «Одна ручка — две скорости» — общий для scene.py (Blender), overlay.py и audio.py.
14,5 с, 30 к/с, 1080×1920. Камера неподвижна (как в рилсе «625 раз»), модель — плашка 1080×1080.
Только объяснение, без вопросов к зрителю. В конце — карточка «Больше механизмов — legobot.ru» (2,5 с)."""
import numpy as np
import peredachi_model as M

FPS, DUR = 30, 14.5
FRAMES = int(round(FPS * DUR))                # 435
PLATE_W, PLATE_H, MY = 1080, 1080, 455        # плашка модели и её верх в кадре
PLATE_FIRST, PLATE_LAST = 0, FRAMES - 1

OMEGA = np.radians(100.0)                     # ручка: 100°/с → синяя 900°/с (30°/кадр), малиновая ≈11°/с
T_SPIN0, T_RAMP = 1.0, 0.7                    # разгон ручки
T_STOP0, T_STOP1 = 11.6, 12.3                 # плавная остановка
T_CARD, CARD_FADE = 12.0, 0.45                # финальная карточка: наплыв 0,45 с, держится до конца (2,5 с)

TITLE = ['ОДНА РУЧКА —', 'ДВЕ СКОРОСТИ']
BADGES = [  # (ось, текст, время появления)
    ('C', 'ручка', 0.9),
    ('U1', '×3', 1.6), ('U2', '×9', 2.2),
    ('D1', '÷3', 4.4), ('D2', '÷9', 5.0),
]
CAPS = [  # (начало, конец, текст, стиль)
    (1.4, 4.0, 'Большая крутит маленькую —\nбыстрее. Это повышающая', 'sun'),
    (4.2, 6.8, 'Маленькая крутит большую —\nмедленнее. Это понижающая', 'white'),
    (7.0, 8.7, '24 зуба → 8 зубьев = ×3\nдве пары: 3 × 3 = 9', 'big'),
    (8.9, 10.3, 'Синяя быстрее\nмалиновой в 81 раз', 'sun'),
    (10.5, 11.9, 'Быстрая ось — слабая,\nмедленная — сильная', 'white'),
]
CAM = dict(lat=8, lon=-12, fov=24)
VIEW = dict(dist=800.0, target=(0.0, 10.0, 0.0))


def smooth(u):
    u = float(np.clip(u, 0, 1))
    return u * u * (3 - 2 * u)


def ease_out(u):
    return 1 - (1 - u) ** 3


def crank(t):
    """Угол ручки theta(t), рад: разгон, постоянная скорость, остановка (интеграл скорости)."""
    def speed_int(x):                         # ∫ скорости от 0 до x в долях OMEGA (сек)
        a0, a1 = T_SPIN0, T_SPIN0 + T_RAMP
        if x <= a0:
            return 0.0
        if x <= a1:                           # линейный разгон
            return 0.5 * (x - a0) ** 2 / T_RAMP
        base = 0.5 * T_RAMP
        if x <= T_STOP0:
            return base + (x - a1)
        base += T_STOP0 - a1
        d = T_STOP1 - T_STOP0
        if x <= T_STOP1:
            u = x - T_STOP0
            return base + u - 0.5 * u * u / d
        return base + 0.5 * d
    return OMEGA * speed_int(t)


def parts_at(t):
    th = crank(t)
    return M.build(th), th


def eye_target(t):
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
        th = crank(t)
        print(f'{t:5.1f}  ручка {np.degrees(th):7.1f}°  синяя {np.degrees(th) * 9:8.1f}°  малиновая {np.degrees(th) / 9:6.1f}°')
