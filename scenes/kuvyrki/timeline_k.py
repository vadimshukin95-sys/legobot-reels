"""Сценарий рилса «Кувырки» — общий для scene_k.py (Blender), overlay_k.py и audio_k.py.
20 с, 30 к/с, 1080×1920. Модель рендерится плашкой 1080×1080 (кадры 0..PLATE_LAST).
Движение — траектория физической симуляции (phys/counter.py: вес, трение, удары; трение 0,2 + вязкое, 0,6 об/с),
сохранена в traj.b64 (60 к/с, сжата; считается в задаче sim workflow через phys/make_traj.py):
t, кривошип, угол плашки 0, крестика 0, плашки 1, крестика 1, плашки 2 (град)."""
import os, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
def _load():
    import zlib, base64
    txt = ''.join(l.strip() for l in open(os.path.join(HERE, 'traj.b64'), encoding='utf-8') if not l.startswith('#'))
    D = np.frombuffer(zlib.decompress(base64.b64decode(txt)), np.int32).reshape(-1, 6)
    A = np.cumsum(D, axis=0) / 100.0
    T = np.arange(len(A)) / 60.0
    return np.c_[T, A, np.zeros(len(A))]      # t, crank, p0, s0, p1, s1, p2, s2


REC = _load()
FPS, DUR = 30, 20.0
FRAMES = int(FPS * DUR)                 # 600
T_CARD, CARD_FADE = 17.0, 0.45
PLATE_W, PLATE_H, MY = 1080, 1080, 470
PLATE_FIRST, PLATE_LAST = 0, int((T_CARD + CARD_FADE) * FPS) + 1     # 0..524
# время ролика -> время симуляции: крючок (замедленный перенос 7->0), счёт 0..7, перенос 7->0 замедленно, досчёт
SEG = [(0.0, 2.0, 11.9, 0.8), (2.0, 13.9, 0.0, 1.0), (13.9, 16.5, 11.9, 0.6), (16.5, 99, 13.46, 1.0)]
SLOW = [(0.0, 2.0), (13.9, 16.5)]


def tau(t):
    for a, b, s0, k in SEG:
        if a <= t < b:
            return min(s0 + k * (t - a), REC[-1, 0])
    return REC[-1, 0]


def sim_to_reel(ts):
    """все моменты ролика, в которые показывается момент симуляции ts"""
    out = []
    for a, b, s0, k in SEG:
        b = min(b, T_CARD + 0.3)
        tt = a + (ts - s0) / k
        if a <= tt < b:
            out.append((tt, k))
    return out


def state_at(t):
    s = tau(t)
    row = [np.interp(s, REC[:, 0], REC[:, j]) for j in range(REC.shape[1])]
    return dict(theta=[row[2], row[4], row[6]], psi=[row[3], row[5]], crank=row[1])


TITLE = ['МОТОР ПРОСТО', 'КРУТИТСЯ,', 'А ПЛАШКИ СЧИТАЮТ']
CAPS = [  # (начало, конец, текст, стиль)
    (2.3, 5.2, 'Мотор крутится —\nплашка 1 кувыркается', 'sun'),
    (5.2, 8.6, 'Плашка 2 — через раз', 'sun'),
    (8.6, 12.4, 'Плашка 3 — раз в 4 оборота', 'sun'),
    (13.9, 16.8, 'Удар за ударом —\nперенос по цепочке', 'big'),
]
BADGES = (2.3, 16.8)
CAM = dict(target=(-92, 30, 0), dist=1560, az=-28, el=16, fov=30)


def eye_target(t=0):
    tg = np.array(CAM['target'], float); az, el = np.radians(CAM['az']), np.radians(CAM['el'])
    eye = tg + CAM['dist'] * np.array([np.sin(az) * np.cos(el), -np.sin(el), -np.cos(az) * np.cos(el)])
    return eye, tg


def look_at(eye, target, up=(0, -1, 0)):
    eye, target, up = map(lambda v: np.array(v, float), (eye, target, up))
    f = target - eye; f /= np.linalg.norm(f)
    s = np.cross(f, up); s /= np.linalg.norm(s)
    u = np.cross(s, f)
    V = np.eye(4); V[0, :3], V[1, :3], V[2, :3] = s, u, -f; V[:3, 3] = -V[:3, :3] @ eye
    return V


def perspective(fovy, aspect, near=50, far=8000):
    f = 1 / np.tan(np.radians(fovy) / 2); P = np.zeros((4, 4))
    P[0, 0] = f / aspect; P[1, 1] = f; P[2, 2] = (far + near) / (near - far); P[2, 3] = 2 * far * near / (near - far); P[3, 2] = -1
    return P


def project(pts, t=0):
    eye, tg = eye_target(t)
    VP = perspective(CAM['fov'], PLATE_W / PLATE_H) @ look_at(eye, tg)
    pts = np.atleast_2d(np.asarray(pts, float)); hp = np.c_[pts, np.ones(len(pts))] @ VP.T; ndc = hp[:, :3] / hp[:, 3:4]
    return np.c_[(ndc[:, 0] + 1) / 2 * PLATE_W, (1 - ndc[:, 1]) / 2 * PLATE_H + MY]


def ease_out(u):
    return 1 - (1 - u) ** 3


if __name__ == '__main__':
    for t in np.arange(0, 17.5, 0.5):
        st = state_at(t); print(round(t, 1), round(tau(t), 2), [round(x) for x in st['theta']])
