"""Сценарий рилса «Закрутится?» — общий для scene_z.py (Blender), overlay_z.py и audio_z.py.
15 с, 30 к/с, 1080×1920. Камера одна (макро, как у крючка); движение кадра — 2D (наезд, дрожь) в overlay.
Состояния модели: rest — собрано; j+ / j- — мотор дёргает C в пределах люфта (±1°);
  out_k — снятие B (ось назад на 30 LDU, потом шестерня вверх); spin_k — без B мотор крутит C, A крутится навстречу
  (пара A–C: A + C = const), ровно 180° — чтобы B встала на место в той же фазе; возврат — снятие в обратном порядке."""
import numpy as np

FPS, DUR = 30, 15.0
FRAMES = int(FPS * DUR)
T_PUSH = (0.0, 3.0)          # тишина и медленный наезд
T_JAM = (3.0, 6.0)           # мотор дёргается, модель дрожит
T_EXPL = (6.0, 11.0)         # стрелки: каждая крутит соседку наоборот
T_OUT = (11.0, 12.0)         # ось B назад (0,4 с), шестерня B вверх (0,6 с)
T_SPIN = (12.0, 13.6)        # A и C крутятся: 360°
T_BACK = (13.6, 14.4)        # B на место (обратный порядок)
T_END = (14.4, 15.0)         # снова крючок — петля
AXLE_OUT, LIFT = 30.0, 320.0
SPIN_DEG = 180.0             # кратно шагу зуба z12 (30°): B встаёт обратно в той же фазе
N_OUT, N_SPIN = 24, 48

TITLE = [('МОТОР ВКЛЮЧЁН.', 78), ('ЗАКРУТИТСЯ?', 118)]
CAPS = [(6.2, 8.6, 'Каждая крутит соседку\nнаоборот', 'sun'),
        (8.6, 10.9, 'По кругу — спор', 'big'),
        (11.2, 13.5, 'Убери одну —\nи всё поехало', 'big')]


def smooth(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def out_state(k):
    """k = 0..N_OUT: первая половина — ось назад, вторая — шестерня вверх"""
    u = k / N_OUT
    return dict(b_axle=AXLE_OUT * smooth(u / 0.4), b_lift=LIFT * smooth((u - 0.4) / 0.6))


def states():
    S = {'rest': dict(), 'jp': dict(dC=1.0, dA=-0.5, dB=0.5), 'jm': dict(dC=-1.0, dA=0.5, dB=-0.5)}
    for k in range(1, N_OUT + 1):
        S[f'out{k:02d}'] = out_state(k)
    full = out_state(N_OUT)
    for k in range(1, N_SPIN):
        th = SPIN_DEG * k / N_SPIN
        S[f'spin{k:02d}'] = dict(full, dC=th, dA=-th)
    return S


def state_at(t):
    """имя состояния для момента ролика t"""
    if t < T_JAM[0] or t >= T_END[0] or (T_EXPL[0] <= t < T_OUT[0]):
        return 'rest'
    if t < T_JAM[1]:
        f = int(t * FPS)
        burst = (t - T_JAM[0]) % 1.0 < 0.62               # рывки: 0,6 с дёргает, 0,4 с пауза
        if not burst: return 'rest'
        return ('jp', 'rest', 'jm', 'rest')[f % 4]
    if t < T_OUT[1]:
        k = int(round((t - T_OUT[0]) / (T_OUT[1] - T_OUT[0]) * N_OUT))
        return 'rest' if k == 0 else f'out{min(k, N_OUT):02d}'
    if t < T_SPIN[1]:
        u = (t - T_SPIN[0]) / (T_SPIN[1] - T_SPIN[0])
        # разгон и торможение: угол по сглаженной кривой, ровно 360° к концу
        th = SPIN_DEG * (u - np.sin(2 * np.pi * u) / (2 * np.pi))
        k = int(round(th / SPIN_DEG * N_SPIN)) % N_SPIN
        return f'out{N_OUT:02d}' if k == 0 else f'spin{k:02d}'
    k = N_OUT - int(round((t - T_BACK[0]) / (T_BACK[1] - T_BACK[0]) * N_OUT))
    return 'rest' if k <= 0 else f'out{min(k, N_OUT):02d}'


if __name__ == '__main__':
    used = sorted({state_at(i / FPS) for i in range(FRAMES)})
    print(len(states()), 'состояний,', len(used), 'используется')
    print([state_at(t) for t in np.arange(11, 15, 0.1)])
