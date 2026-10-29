"""python audio.py out.wav — синтез звука рилса: маримба (пентатоника) + деревянные щелчки, синхронно с событиями ролика."""
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


def click(amp=0.25, fr=1700):
    t = np.arange(int(SR * 0.08)) / SR
    rng = np.random.default_rng(int(fr))
    noise = rng.standard_normal(len(t)) * np.exp(-t * 120)
    tone = np.sin(2 * np.pi * fr * t) * np.exp(-t * 60) + 0.5 * np.sin(2 * np.pi * fr * 0.47 * t) * np.exp(-t * 45)
    return amp * (0.35 * noise + tone)


def whoosh(dur=0.35, amp=0.12):
    t = np.arange(int(SR * dur)) / SR
    rng = np.random.default_rng(5)
    n = rng.standard_normal(len(t))
    k = np.ones(40) / 40; n = np.convolve(n, k, 'same')
    env = np.sin(np.pi * t / dur) ** 2
    return amp * 6 * n * env


def put(sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    s = sig[:N - i]
    L[i:i + len(s)] += s * (1 - pan) ; Rr[i:i + len(s)] += s * (1 + pan)


PENTA = [('C', 5), ('D', 5), ('E', 5), ('G', 5), ('A', 5), ('C', 6), ('D', 6), ('E', 6), ('G', 6), ('A', 6)]
# заголовок
for k, (n, o) in enumerate([('C', 5), ('E', 5), ('G', 5)]):
    put(marimba(f(n, o), 1.4, 0.32), 0.15 + 0.18 * k + 0.12, pan=-0.2 + 0.2 * k)
# сборка: щелчок + нота при посадке каждой группы
for k, tl in enumerate(RL.LAND):
    if RL.ORDER[k](dict(group='rail', part='44294.dat')):
        put(whoosh(), tl - 0.33)
    put(click(0.22, 1500 + 90 * k), tl)
    n, o = PENTA[k % len(PENTA)]
    put(marimba(f(n, o), 0.9, 0.18), tl, pan=0.3 * np.sin(k))
# механизм: тихий щелчок в каждой крайней точке пилы
th_prev = RL.theta_at(RL.T_RUN)
tt = np.arange(RL.T_RUN, RL.T_CARD, 1 / 600)
last = 0
for t in tt:
    th = RL.theta_at(t)
    if int(th // 180) != int(th_prev // 180):
        put(click(0.13, 1200 if int(th // 180) % 2 else 950), t, pan=-0.3 if int(th // 180) % 2 else 0.3)
    th_prev = th
# фон: спокойное арпеджио маримбы
bpm = 96; beat = 60 / bpm
prog = [['C', 'E', 'G', 'E'], ['A', 'C', 'E', 'C'], ['F', 'A', 'C', 'A'], ['G', 'B', 'D', 'B']]
t = RL.T_RUN - 0.1; k = 0
while t < RL.T_CARD + 0.4:
    ch = prog[(k // 8) % 4]; n = ch[k % 4]
    o = 4 if n in ('C', 'D', 'E') and k % 4 == 0 else 4
    put(marimba(f(n, o + (1 if k % 4 else 0)), 0.8, 0.09), t, pan=0.25 if k % 2 else -0.25)
    t += beat / 2; k += 1
# подписи
for a, b, text, st in RL.CAPS:
    put(marimba(f('G', 5) if st != 'big' else f('C', 6), 1.0, 0.2), a + 0.05)
    if st == 'big':
        put(marimba(f('E', 6), 1.0, 0.15), a + 0.12); put(marimba(f('G', 6), 1.2, 0.12), a + 0.19)
# финальная карточка
for k, (n, o) in enumerate([('C', 4), ('E', 4), ('G', 4), ('C', 5), ('E', 5), ('G', 5), ('C', 6)]):
    put(marimba(f(n, o), 2.4, 0.2), RL.T_CARD + 0.05 + 0.06 * k, pan=-0.4 + 0.13 * k)
# лёгкая реверберация
def reverb(x):
    y = x.copy()
    for d, g in ((0.031, 0.32), (0.047, 0.27), (0.071, 0.22), (0.113, 0.16)):
        i = int(d * SR); z = np.zeros_like(x); z[i:] = x[:-i] * g; y += z
    return y
L, Rr = reverb(L), reverb(Rr)
fade = np.ones(N); fl = int(0.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
st = np.stack([L * fade, Rr * fade], 1)
st /= np.abs(st).max() / 0.85
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'sound.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', N / SR)
