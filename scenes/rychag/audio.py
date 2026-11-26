"""Рычаг. python audio.py out.wav — синтез звука рилса кодом: маримба (арпеджио), шорох петли по балке,
«ток», когда петля встала на отверстие, звонкий аккорд при равновесии, ноты подписей и финальной карточки."""
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


def whir(t0, t1, amp=0.12):
    """Шорох петли по балке: шум с растущим тоном."""
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
# петля скользит по балке: тихий шорох; приехала — «ток»; встали в равновесие — звонкий аккорд
for z, ((a, b), k0, k1) in enumerate(TL.SLIDES):
    put(whir(a, b, 0.05), a, pan=-0.35)
    put(click(0.16, 1500, seed=11 + z, dec=45), b, pan=-0.35)
    if k1 == 6:
        for j, (n, o) in enumerate([('E', 6), ('G', 6), ('C', 7)]):
            put(marimba(f(n, o), 1.4, 0.12), b + 0.35 + 0.07 * j)
# фон: спокойное арпеджио маримбы
bpm = 96; beat = 60 / bpm
prog = [['C', 'E', 'G', 'E'], ['A', 'C', 'E', 'C'], ['F', 'A', 'C', 'A'], ['G', 'B', 'D', 'B']]
t = 0.6; k = 0
while t < TL.CARD:
    ch = prog[(k // 8) % 4]; n = ch[k % 4]
    put(marimba(f(n, 4 + (1 if k % 4 else 0)), 0.8, 0.07), t, pan=0.25 if k % 2 else -0.25)
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
print('ok', N / SR)
