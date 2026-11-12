"""Сценарий рилса «Два звена — полный хаос» (30 к/с, 17 с).
0–0.8 с маятник поднят и замер, на 0.8 с отпускаем; движение показано замедленным в 2 раза;
с 14 с — финальная карточка. Углы звеньев — из физики (sim.py), сохранены в angles.json (шаг — четверть кадра)."""
import os, json, math

HERE = os.path.dirname(os.path.abspath(__file__))
FPS = 30
DUR = 17.0
FRAMES = int(FPS * DUR)                     # 510
SLOW = 2.0                                  # замедление
T_REL = 0.8
F_REL = int(T_REL * FPS)                    # 24 — первый кадр движения
T_CARD = 14.0
CARD_FADE = 0.45
PLATE_LAST = int((T_CARD + CARD_FADE) * FPS) + 1   # 434 — последний кадр, который рендерит Blender
TH0 = (math.radians(165), math.radians(150))
TITLE = ['ДВА ЗВЕНА —', 'ПОЛНЫЙ ХАОС']
SUB = 4                                      # ключей на кадр (для размытия движения)

_A = None


def _load():
    global _A
    if _A is None:
        f = os.path.join(HERE, 'angles.json')
        if os.path.exists(f):
            _A = json.load(open(f))
        else:
            import make_angles
            _A = make_angles.compute()[0]
    return _A


def real_time(fv):
    """Секунды реального движения маятника для кадра ролика fv (может быть дробным)."""
    return max(0.0, (fv - F_REL) / FPS / SLOW)


def angles(fv):
    """th1, th2 (рад) для кадра ролика fv; до F_REL маятник неподвижен в TH0."""
    if fv <= F_REL:
        return TH0
    A = _load()
    k = (fv - F_REL) * SUB
    i = int(math.floor(k)); a = k - i
    n = len(A['th1']) - 1
    i = min(i, n - 1)
    return (A['th1'][i] * (1 - a) + A['th1'][i + 1] * a, A['th2'][i] * (1 - a) + A['th2'][i + 1] * a)


def plate_index(f):
    """Какой отрендеренный кадр взять для кадра ролика f."""
    return min(max(f, F_REL), PLATE_LAST)
