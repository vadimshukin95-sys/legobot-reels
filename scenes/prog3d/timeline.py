"""Сценарий петли /prog (15 с): общий для экранов (screens.py) и 3D-сцены (scene.py).
0–3 с   Scratch: блоки защёлкиваются, скрипт подсвечивается.
3–6 с   Python: код печатается, внизу строка вывода.
6–9 с   браузер: собирается страница, курсор жмёт «Играть».
8.7 с   робот выпрыгивает из экрана браузера, идёт по подставке, перепрыгивает красный кирпич,
        приседает и ныряет в экран Scratch (14.3 с) — там снова начинается сборка программы."""
import math, json, os
LOOP, FPS = 15.0, 24
HERE = os.path.dirname(os.path.abspath(__file__))
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))

def clamp(x): return max(0.0, min(1.0, x))
def ease(x): x = clamp(x); return x * x * (3 - 2 * x)
def seg(t, a, b): return ease((t - a) / (b - a))

# ------------------------------------------------------------------ экраны
SCR_BLOCK0, SCR_STEP = 0.35, 0.4              # блоки Scratch: i-й прилетает в 0.35 + 0.4·i
SCR_GLOW = 2.8                                # скрипт «запущен» — жёлтая обводка
SCR_FADE = (11.8, 12.3)                       # блоки убираются к новому кругу
SCR_ENTER = 14.15                             # робот входит в экран Scratch — круги по экрану
PY_TYPE = (3.3, 6.0); PY_OUT = 6.1; PY_CLEAR = (13.0, 13.4)
WEB_HEAD = (6.4, 6.8); WEB_CARD0 = 6.9; WEB_BTN = (7.7, 8.0)
WEB_CURSOR = (7.75, 8.3); WEB_CLICK = 8.35; WEB_EXIT = 8.7; WEB_WIPE = (14.3, 14.7)

# ------------------------------------------------------------------ геометрия (как в scene.py)
PLH = LAY['plinth']['h']
SCREEN_Z = 9.8                                # середина экрана над подставкой (LDraw y = -196)
SCREEN_W, SCREEN_H = 14.0, 10.8               # экран 280 × 216 LDU
RC = 5.0                                      # середина робота над подошвами
def screen(name):
    m = LAY['monitors'][name]; a = math.radians(m['rot'])
    n = (math.sin(a), -math.cos(a))           # нормаль экрана (куда он смотрит)
    c = (m['at'][0] + 0.03 * n[0], m['at'][1] + 0.03 * n[1], PLH + SCREEN_Z)
    return c, n

# ------------------------------------------------------------------ робот
T_EXIT, T_WALK1, T_JUMP, T_WALK2, T_CROUCH, T_DIVE, T_GONE = 8.7, 9.4, 10.9, 11.5, 13.1, 13.4, 14.3
STEP = 1.4                                    # длина шага (по пути), в шипах
LEG, ARM = math.radians(28), math.radians(32)

def _lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def _dist(a, b): return math.hypot(b[0] - a[0], b[1] - a[1])
def _yaw(d): return math.atan2(d[0], -d[1])   # rotation_z, при котором перед робота (-y) смотрит вдоль d
def _ang(a, b, u):                             # поворот по кратчайшему пути
    d = (b - a + math.pi) % (2 * math.pi) - math.pi
    return a + d * u

R = LAY['robot']
LAND, PRE, POST, TAKE = R['land'], R['pre_jump'], R['post_jump'], R['takeoff']
CW, NW = screen('web'); CS, NS = screen('scratch')
S0 = (CW[0] - 2.0 * NW[0], CW[1] - 2.0 * NW[1])          # старт — за плоскостью экрана браузера
E1 = (CS[0] - 2.0 * NS[0], CS[1] - 2.0 * NS[1])          # финиш — за плоскостью экрана Scratch
def face(d): return _yaw(d) * 0.72             # на ходу робот немного развёрнут к камере
Y_W1, Y_W2 = face((PRE[0] - LAND[0], PRE[1] - LAND[1])), face((TAKE[0] - POST[0], TAKE[1] - POST[1]))
Y_DIVE = _yaw((E1[0] - TAKE[0], E1[1] - TAKE[1]))
D1, D2 = _dist(LAND, PRE), _dist(POST, TAKE)

def robot(t):
    """dict: pos (x, y, z подошв), yaw, scale, legL, legR, armL, armR, head (радианы), visible."""
    st = dict(pos=(0, 0, -50), yaw=0.0, scale=0.001, legL=0.0, legR=0.0, armL=0.0, armR=0.0, head=0.0, visible=False)
    if t < T_EXIT or t >= T_GONE: return st
    st['visible'] = True
    def walk(ph, k=1.0):
        s = math.sin(ph)
        st.update(legL=LEG * s * k, legR=-LEG * s * k, armL=-ARM * s * k, armR=ARM * s * k, head=0.05 * math.sin(2 * ph) * k)
        return 0.12 * abs(s) * k
    def leap(u, up=-2.4):                       # прыжок: ноги поджаты, руки вперёд-вверх
        k = math.sin(math.pi * clamp(u))
        st.update(legL=-0.35 * k, legR=-0.35 * k, armL=up * k, armR=up * k, head=-0.12 * k)
    if t < T_WALK1:                             # из экрана браузера на подставку
        u = (t - T_EXIT) / (T_WALK1 - T_EXIT); e = ease(u)
        z0 = CW[2] - RC * 0.75
        xy = _lerp(S0, LAND, u); z = z0 + (PLH - z0) * u + 4 * 3.0 * u * (1 - u)
        st.update(pos=(xy[0], xy[1], z), yaw=_ang(_yaw(NW), Y_W1, e), scale=0.75 + 0.25 * e); leap(u, -1.8)
    elif t < T_JUMP:                            # идёт к кирпичу
        u = (t - T_WALK1) / (T_JUMP - T_WALK1); xy = _lerp(LAND, PRE, u)
        bob = walk(D1 * u / STEP * math.pi, min(1, u * 6))
        st.update(pos=(xy[0], xy[1], PLH + bob), yaw=Y_W1, scale=1.0)
    elif t < T_WALK2:                           # прыжок через кирпич
        u = (t - T_JUMP) / (T_WALK2 - T_JUMP); xy = _lerp(PRE, POST, u)
        st.update(pos=(xy[0], xy[1], PLH + 4 * 3.6 * u * (1 - u)), yaw=_ang(Y_W1, Y_W2, ease(u)), scale=1.0); leap(u)
    elif t < T_CROUCH:                          # идёт к экрану Scratch
        u = (t - T_WALK2) / (T_CROUCH - T_WALK2); xy = _lerp(POST, TAKE, u)
        bob = walk(D2 * u / STEP * math.pi, min(1, u * 6, (1 - u) * 6))
        st.update(pos=(xy[0], xy[1], PLH + bob), yaw=Y_W2, scale=1.0)
    elif t < T_DIVE:                            # поворачивается к экрану и приседает перед прыжком
        u = (t - T_CROUCH) / (T_DIVE - T_CROUCH); k = math.sin(math.pi * u)
        st.update(pos=(TAKE[0], TAKE[1], PLH - 0.0), yaw=_ang(Y_W2, Y_DIVE, ease(u * 1.4)), scale=1.0,
                  armL=0.7 * k, armR=0.7 * k, head=0.15 * k)
    else:                                       # ныряет в экран Scratch
        u = (t - T_DIVE) / (T_GONE - T_DIVE); e = ease(u)
        z1 = CS[2] - RC * 0.75
        xy = _lerp(TAKE, E1, u); z = PLH + (z1 - PLH) * u + 4 * 4.5 * u * (1 - u)
        st.update(pos=(xy[0], xy[1], z), yaw=Y_DIVE, scale=1.0 - 0.25 * e); leap(min(1, u * 1.6) * 0.5 + 0.0, -2.6)
        st.update(armL=-2.6 * ease(u * 2), armR=-2.6 * ease(u * 2))
    return st

if __name__ == '__main__':
    for t in (8.7, 9.0, 9.4, 10.0, 10.9, 11.2, 11.5, 12.5, 13.2, 13.4, 13.9, 14.2, 14.29):
        s = robot(t); print(t, [round(v, 2) for v in s['pos']], round(math.degrees(s['yaw'])), round(s['scale'], 2))
