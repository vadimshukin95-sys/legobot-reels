"""Храповик. python audio.py out.wav — синтез звука рилса кодом: маримба (пентатоника), щелчок собачки на каждый зуб
(момент, когда собачка падает с вершины зуба — из timeline.state), «клац» при упоре, свист барабана и «бум» груза об пол."""
import os, sys, numpy as np, wave
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL

SR, DUR = 44100, TL.DUR
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


def click(amp=0.25, fr=1700, seed=1, dec=60):
    t = np.arange(int(SR * 0.08)) / SR
    rng = np.random.default_rng(seed)
    noise = rng.standard_normal(len(t)) * np.exp(-t * 120)
    tone = np.sin(2 * np.pi * fr * t) * np.exp(-t * dec) + 0.5 * np.sin(2 * np.pi * fr * 0.47 * t) * np.exp(-t * dec * 0.75)
    return amp * (0.35 * noise + tone)


def thud(amp=0.6):
    t = np.arange(int(SR * 0.5)) / SR
    rng = np.random.default_rng(5)
    body = np.sin(2 * np.pi * (62 + 40 * np.exp(-t * 30)) * t) * np.exp(-t * 9)
    knock = rng.standard_normal(len(t)) * np.exp(-t * 60) * 0.5
    return amp * (body + knock)


def whir(t0, t1, amp=0.12):
    """Барабан раскручивается: шум с растущим тоном."""
    n = int((t1 - t0) * SR); t = np.arange(n) / SR; u = t / t[-1]
    rng = np.random.default_rng(9)
    tone = np.sin(2 * np.pi * np.cumsum(180 + 900 * u ** 2) / SR)
    s = (0.6 * tone + 0.4 * rng.standard_normal(n)) * (u ** 1.5)
    return amp * s


def put(sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= N or i < 0:
        return
    s = sig[:N - i]
    L[i:i + len(s)] += s * (1 - pan); Rr[i:i + len(s)] += s * (1 + pan)


# заголовок
for k, (n, o) in enumerate([('C', 5), ('E', 5), ('G', 5)]):
    put(marimba(f(n, o), 1.4, 0.3), 0.1 + 0.15 * k, pan=-0.2 + 0.2 * k)
put(click(0.18, 900, seed=3, dec=40), TL.T_CUT)                      # склейка: груз стоит на полу
# щелчки собачки: собачка падает с вершины зуба (резкое уменьшение угла) — при подъёме и при «проседании»
armed, z = False, 0
for t in np.arange(TL.LIFT[0], TL.RELEASE[0], 1 / 600):
    p = TL.state(t)[1]
    if p > -1.0:
        armed = True
    elif armed and p < -5.0:                                   # упала с вершины зуба во впадину
        put(click(0.16, 2300, seed=z), t, pan=0.3); put(click(0.06, 1500, seed=z + 50), t + 0.006, pan=0.3)
        armed = False; z += 1
put(click(0.32, 1300, seed=77, dec=35), TL.RELEASE[1])               # клац — упёрлась
put(marimba(f('A', 5), 1.0, 0.14), TL.RELEASE[1] + 0.05)
put(click(0.12, 1900, seed=21), TL.PAWL_LIFT[0] + 0.05, pan=0.3)     # подняли собачку
put(whir(TL.FALL[0], TL.FALL[1]), TL.FALL[0])
put(thud(0.7), TL.FALL[1])                                          # бум
put(click(0.16, 2100, seed=31), TL.PAWL_DOWN[1], pan=0.3)            # собачка легла на зубья
# фон: спокойное арпеджио маримбы (затихает на крупном плане и при падении)
bpm = 96; beat = 60 / bpm
prog = [['C', 'E', 'G', 'E'], ['A', 'C', 'E', 'C'], ['F', 'A', 'C', 'A'], ['G', 'B', 'D', 'B']]
t = 0.6; k = 0
while t < TL.CARD:
    quiet = 0.4 if (10.6 < t < 12.9 or 13.4 < t < 14.6) else 1.0
    ch = prog[(k // 8) % 4]; n = ch[k % 4]
    put(marimba(f(n, 4 + (1 if k % 4 else 0)), 0.8, 0.07 * quiet), t, pan=0.25 if k % 2 else -0.25)
    t += beat / 2; k += 1
# подписи
for a, b, text, st, y in TL.CAPS:
    put(marimba(f('G', 5) if st != 'big' else f('C', 6), 1.0, 0.16), a + 0.05)
    if st == 'big':
        put(marimba(f('E', 6), 1.0, 0.12), a + 0.12); put(marimba(f('G', 6), 1.2, 0.1), a + 0.19)
for k, (a, text) in enumerate(TL.WHERE):
    put(marimba(f(['D', 'E', 'G'][k], 5), 0.9, 0.13), a + 0.05)
# финальная карточка
for k, (n, o) in enumerate([('C', 5), ('E', 5), ('G', 5), ('C', 6)]):
    put(marimba(f(n, o), 1.8, 0.22), TL.CARD + 0.15 + 0.12 * k, pan=-0.3 + 0.2 * k)


def reverb(x):
    y = x.copy()
    for d, g in ((0.031, 0.32), (0.047, 0.27), (0.071, 0.22), (0.113, 0.16)):
        i = int(d * SR); zz = np.zeros_like(x); zz[i:] = x[:-i] * g; y += zz
    return y


L, Rr = reverb(L), reverb(Rr)
fade = np.ones(N); fl = int(0.6 * SR); fade[-fl:] = np.linspace(1, 0, fl)
st = np.stack([L * fade, Rr * fade], 1)
st /= np.abs(st).max() / 0.85
pcm = (st * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'sound.wav', 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', N / SR, 'щелчков', z)
