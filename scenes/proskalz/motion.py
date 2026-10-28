"""Кинематика рилса «Ремень проскальзывает» (без bpy — общая для scene.py и audio.py).
Мотор и нижний шкив крутятся всё время. Вентилятор крутится вместе с ними, пока лопасть не упрётся в карандаш
(угол касания посчитан заранее по геометрии лопастей 42022 и карандаша, зазор ~0.03 стада), затем стоит:
ремень держит верхний шкив, нижний шкив проскальзывает в ремне. Карандаш вынули — вентилятор разгоняется."""
import json, math, os
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
FPS = 24
N = TL['frames'] + 2

def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

SP = TL['speed']
def rev_s(f):
    for (f0, v0), (f1, v1) in zip(SP, SP[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * ease((f - f0) / max(1, f1 - f0))
    return SP[-1][1]

DRIVE = {1: 0.0}                                    # угол ведущего шкива, градусы (растёт)
for f in range(2, N + 1):
    DRIVE[f] = DRIVE[f - 1] + rev_s(f) * 360.0 / FPS

ST = TL['stop']; TC = ST['theta']; RC = ST['recoil']; R0, R1 = ST['restart']
FAN = {}; SPEED = {}                                # угол вентилятора (rotation Y, градусы; вперёд — убывает), об/с
FC = None
for f in range(1, N + 1):
    if f < R0:
        t = 12.0 - DRIVE[f]
        if FC is None and t <= TC:
            FC = f
        if FC is not None:
            k = (f - FC) / RC
            t = TC + (4.0 * math.sin(math.pi * k) if k < 1 else 0.0)      # лёгкий отскок от карандаша
    else:
        step = (DRIVE[f] - DRIVE[f - 1]) * ease((f - R0) / (R1 - R0))
        t = FAN[f - 1] - step
    FAN[f] = t
for f in range(1, N + 1):
    SPEED[f] = abs(FAN[f] - FAN.get(f - 1, FAN[f])) * FPS / 360.0

PC = TL['pencil']
def pencil_r(f):
    (i0, i1), (o0, o1) = PC['in'], PC['out']
    if f <= i1:
        return PC['r_out'] + (PC['r_in'] - PC['r_out']) * ease((f - i0) / (i1 - i0))
    return PC['r_in'] + (PC['r_out'] - PC['r_in']) * ease((f - o0) / (o1 - o0))
def pencil_vis(f):
    return f < PC['out'][1] + 30                     # после выхода уезжает за кадр
def pencil_far(f):
    """после выхода из лопастей карандаш уезжает дальше и пропадает из кадра"""
    o1 = PC['out'][1]
    return 0.0 if f <= o1 else 26.0 * ease((f - o1) / 22)

if __name__ == '__main__':
    print('contact frame', FC, 'restart', R0, R1)
    for f in (30, 44, 48, FC, FC + 3, 150, 250, 262, 270, 290, 330):
        print(f, round(FAN[f], 1), round(SPEED[f], 2), round(pencil_r(f) + pencil_far(f), 2))
