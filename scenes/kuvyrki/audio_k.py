"""«Кувырки». python audio_k.py out.wav — синтез звука рилса: деревянные «туки» на кувырках плашек (у каждой плашки свой тон),
«клац» крючка на переносе, мягкое арпеджио маримбы. События берутся из траектории симуляции и пересчитываются во время ролика
(в замедленных кусках звук ниже и тише)."""
import os, sys, numpy as np, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline_k as TL

SR, DUR = 44100, TL.DUR
N = int(SR * DUR)
L = np.zeros(N); Rr = np.zeros(N)
NOTE = {n: 440 * 2 ** ((i - 9) / 12) for i, n in enumerate(['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B'])}
def f(name, octv): return NOTE[name] * 2 ** (octv - 4)


def marimba(fr, dur=1.2, amp=0.3):
    t = np.arange(int(SR * dur)) / SR
    s = np.sin(2 * np.pi * fr * t) * np.exp(-t * 3.2) + 0.35 * np.sin(2 * np.pi * fr * 3.93 * t) * np.exp(-t * 14) \
        + 0.08 * np.sin(2 * np.pi * fr * 9.2 * t) * np.exp(-t * 40)
    return amp * np.minimum(1, t / 0.003) * s


def knock(fr, amp=0.3, slow=1.0):
    """деревянный стук: короткий тон + шумовой щелчок"""
    fr = fr * (0.8 if slow < 1 else 1.0)
    t = np.arange(int(SR * 0.25)) / SR
    rng = np.random.default_rng(int(fr))
    noise = rng.standard_normal(len(t)) * np.exp(-t * 160)
    tone = np.sin(2 * np.pi * fr * t) * np.exp(-t * 28) + 0.45 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 55)
    return amp * (0.3 * noise + tone)


def click(amp=0.2, fr=2400):
    t = np.arange(int(SR * 0.06)) / SR
    rng = np.random.default_rng(int(fr))
    return amp * (0.5 * rng.standard_normal(len(t)) * np.exp(-t * 200) + np.sin(2 * np.pi * fr * t) * np.exp(-t * 90))


def put(sig, t0, pan=0.0, gain=1.0):
    i = int(t0 * SR)
    if i < 0 or i >= N or t0 >= TL.T_CARD + 0.3:
        return
    s = sig[:N - i] * gain
    L[i:i + len(s)] += s * (1 - pan); Rr[i:i + len(s)] += s * (1 + pan)


REC = TL.REC; ts = REC[:, 0]
PITCH = [f('G', 4), f('D', 4), f('G', 3)]          # плашка 1 — выше, плашка 3 — ниже
PAN = [0.35, 0.0, -0.35]
EV = []
for k in range(3):
    th = REC[:, 2 + 2 * k]; v = np.gradient(th, ts)
    # «тук» — пик скорости кувырка (плашка проходит низ после падения): один удар на кувырок
    seg = None
    for i in range(1, len(th)):
        if v[i] > 25 and seg is None:
            seg = i
        if (v[i] <= 25 or i == len(th) - 1) and seg is not None:
            j = seg + int(np.argmax(v[seg:i + 1]))
            if v[j] > 250 and th[i] - th[seg] > 150:
                for tt, kk in TL.sim_to_reel(ts[j]):
                    put(knock(PITCH[k], 0.34, kk), tt, PAN[k], 1.0 if kk == 1 else 0.85)
                EV.append((k, ts[j]))
            seg = None
    # «клац» — крючок подхватил плашку (k>=1 начинает движение, пока предыдущая уже крутится)
    if k >= 1:
        moving = False
        for i in range(1, len(th)):
            if not moving and v[i] > 40 and v[i - 1] <= 40 and REC[i, 2 + 2 * (k - 1)] % 360 < 120:
                for tt, kk in TL.sim_to_reel(ts[i]):
                    put(click(0.22, 2600 - 300 * k), tt, PAN[k])
                moving = True
            if moving and abs(v[i]) < 10:
                moving = False
# заголовок
for k, (n, o) in enumerate([('C', 5), ('E', 5), ('G', 5)]):
    put(marimba(f(n, o), 1.4, 0.26), 0.1 + 0.16 * k + 0.1, pan=-0.2 + 0.2 * k)
# подписи
for a, b, text, st in TL.CAPS:
    put(marimba(f('G', 5) if st != 'big' else f('C', 6), 1.0, 0.16), a + 0.05)
    if st == 'big':
        put(marimba(f('E', 6), 1.0, 0.12), a + 0.12); put(marimba(f('G', 6), 1.2, 0.1), a + 0.19)
# фон: спокойное арпеджио (тише в замедлении)
bpm = 92; beat = 60 / bpm
prog = [['C', 'E', 'G', 'E'], ['A', 'C', 'E', 'C'], ['F', 'A', 'C', 'A'], ['G', 'B', 'D', 'B']]
t = 0.0; k = 0
while t < TL.T_CARD + 0.3:
    slow = any(a <= t < b for a, b in TL.SLOW)
    ch = prog[(k // 8) % 4]; n = ch[k % 4]
    put(marimba(f(n, 4 + (1 if k % 4 else 0)), 0.8, 0.06 if slow else 0.08), t, pan=0.25 if k % 2 else -0.25)
    t += beat / 2 * (1.6 if slow else 1.0); k += 1
# финальная карточка
for k, (n, o) in enumerate([('C', 4), ('E', 4), ('G', 4), ('C', 5), ('E', 5), ('G', 5), ('C', 6)]):
    i0 = TL.T_CARD + 0.05 + 0.06 * k
    sig = marimba(f(n, o), 2.4, 0.2); i = int(i0 * SR); s = sig[:N - i]
    L[i:i + len(s)] += s * (0.6 + 0.13 * k); Rr[i:i + len(s)] += s * (1.4 - 0.13 * k)
def reverb(x):
    y = x.copy()
    for d, g in ((0.031, 0.32), (0.047, 0.27), (0.071, 0.22), (0.113, 0.16)):
        i = int(d * SR); z = np.zeros_like(x); z[i:] = x[:-i] * g; y += z
    return y
L, Rr = reverb(L), reverb(Rr)
fade = np.ones(N); fl = int(0.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
st = np.stack([L * fade, Rr * fade], 1); st /= np.abs(st).max() / 0.85
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'sound.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((st * 32767).astype(np.int16).tobytes())
print('ok', N / SR, sorted((k + 1, round(t, 2)) for k, t in EV))
