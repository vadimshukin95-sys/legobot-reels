"""Одна ручка — две скорости. python audio.py out.wav — синтез звука рилса: маримба + щелчки зубьев синхронно с осями:
ручка — средний щелчок на каждый зуб 24z, синяя (×9) — частый тихий тик, малиновая (÷9) — редкий низкий «тук».
Звук сам показывает разницу скоростей. В конце — аккорд под карточку с логотипом, затем тихое затухание."""
import os, sys, numpy as np, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as RL

SR, DUR = 44100, RL.DUR
N = int(SR * DUR)
L = np.zeros(N); Rr = np.zeros(N)
NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}


def f(name, octv):
    return NOTE[name] * 2 ** (octv - 4)


def marimba(fr, dur=1.2, amp=0.3):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 0.003)
    s = np.sin(2 * np.pi * fr * t) * np.exp(-t * 3.2) + 0.35 * np.sin(2 * np.pi * fr * 3.93 * t) * np.exp(-t * 14) \
        + 0.08 * np.sin(2 * np.pi * fr * 9.2 * t) * np.exp(-t * 40)
    return amp * env * s


def click(amp=0.25, fr=1700, seed=1):
    t = np.arange(int(SR * 0.08)) / SR
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(t)) * np.exp(-t * 120)
    tone = np.sin(2 * np.pi * fr * t) * np.exp(-t * 60) + 0.5 * np.sin(2 * np.pi * fr * 0.47 * t) * np.exp(-t * 45)
    return amp * (0.35 * noise + tone)


def hum(t0, t1, amp=0.035):
    """Тихий гул мотора, пока двери едут."""
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    env = np.minimum(1, np.minimum(t / 0.25, (t[-1] - t + 1e-9) / 0.25))
    s = np.sin(2 * np.pi * 110 * t) + 0.5 * np.sin(2 * np.pi * 220 * t) + 0.25 * np.sin(2 * np.pi * 330 * t)
    return amp * env * s


def put(sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    s = sig[:N - i]
    L[i:i + len(s)] += s * (1 - pan); Rr[i:i + len(s)] += s * (1 + pan)


# заголовок
for k, (n, o) in enumerate([('C', 5), ('E', 5), ('G', 5)]):
    put(marimba(f(n, o), 1.4, 0.3), 0.1 + 0.15 * k, pan=-0.2 + 0.2 * k)
# зубья: ручка (24z), синяя ось (8z, ×9), малиновая (24z, ÷9)
def teeth(angle_per_rad, n_teeth, amp, fr, pan, seed0, step=1 / 2000):
    prev = 0
    for t in np.arange(0, DUR, step):
        z = int(np.floor(abs(RL.crank(t) * angle_per_rad) / (2 * np.pi / n_teeth) + 1e-9))
        if z != prev:
            put(click(amp, fr, seed=seed0 + z), t, pan=pan)
            prev = z


teeth(1.0, 24, 0.06, 1800, 0.0, 0)
teeth(9.0, 8, 0.018, 3200, -0.35, 1000)
teeth(1 / 9, 24, 0.30, 420, 0.35, 5000)
# карточка с логотипом
for k, n in enumerate(['C', 'E', 'G', 'C']):
    put(marimba(f(n, 5 if k < 3 else 6), 1.6, 0.2), RL.T_CARD + 0.08 * k)
# фон: спокойное арпеджио маримбы
bpm = 96; beat = 60 / bpm
prog = [['C', 'E', 'G', 'E'], ['A', 'C', 'E', 'C'], ['F', 'A', 'C', 'A'], ['G', 'B', 'D', 'B']]
t = 0.6; k = 0
while t < DUR - 0.8:
    ch = prog[(k // 8) % 4]; n = ch[k % 4]
    put(marimba(f(n, 4 + (1 if k % 4 else 0)), 0.8, 0.08), t, pan=0.25 if k % 2 else -0.25)
    t += beat / 2; k += 1
# подписи
for a, b, text, st in RL.CAPS:
    put(marimba(f('G', 5) if st != 'big' else f('C', 6), 1.0, 0.18), a + 0.05)
    if st == 'big':
        put(marimba(f('E', 6), 1.0, 0.14), a + 0.12); put(marimba(f('G', 6), 1.2, 0.11), a + 0.19)


def reverb(x):
    y = x.copy()
    for d, g in ((0.031, 0.32), (0.047, 0.27), (0.071, 0.22), (0.113, 0.16)):
        i = int(d * SR); z = np.zeros_like(x); z[i:] = x[:-i] * g; y += z
    return y


L, Rr = reverb(L), reverb(Rr)
fade = np.ones(N); fl = int(0.5 * SR); fade[-fl:] = np.linspace(1, 0, fl)
st = np.stack([L * fade, Rr * fade], 1)
st /= np.abs(st).max() / 0.85
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'sound.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', N / SR)
