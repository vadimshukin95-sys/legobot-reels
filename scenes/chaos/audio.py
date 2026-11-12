"""Хаос-маятник: звук. python audio.py out.wav
Тихая подложка (пентатоника), на отпускании — щелчок; каждый раз, когда звено проходит верхнюю точку, — нота маримбы
(звено 2 — выше, звено 1 — ниже). Ноты идут в ритме самого маятника — рваном, как и его движение. В конце — аккорд к карточке."""
import os, sys, json, math, wave
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import timeline as TL

SR = 44100
N = int(SR * TL.DUR)
L = np.zeros(N); R = np.zeros(N)
PENTA = [0, 2, 4, 7, 9]


def hz(semi, octv):
    return 261.63 * 2 ** (semi / 12) * 2 ** (octv - 4)


def marimba(fr, dur=1.1, amp=0.28):
    t = np.arange(int(SR * dur)) / SR
    env = np.minimum(1, t / 0.003)
    s = np.sin(2 * np.pi * fr * t) * np.exp(-t * 3.4) + 0.33 * np.sin(2 * np.pi * fr * 3.93 * t) * np.exp(-t * 15)
    return amp * env * s


def click(amp=0.3):
    t = np.arange(int(SR * 0.07)) / SR
    noise = np.random.default_rng(3).standard_normal(len(t)) * np.exp(-t * 110)
    return amp * (0.4 * noise + np.sin(2 * np.pi * 1500 * t) * np.exp(-t * 60))


def put(sig, t0, pan=0.0):
    i = int(t0 * SR)
    if i >= N:
        return
    s = sig[:N - i]
    L[i:i + len(s)] += s * (1 - max(0, pan)); R[i:i + len(s)] += s * (1 + min(0, pan))


# подложка: медленные мягкие ноты до карточки
rng = np.random.default_rng(7)
t = 0.0
while t < TL.T_CARD:
    put(marimba(hz(PENTA[rng.integers(5)], 3), 2.0, 0.07), t, rng.uniform(-0.3, 0.3)); t += 0.9
put(click(), TL.T_REL)
# ноты на прохождение верхней точки
A = TL._load()
rate = A['rate']
for key, octv, amp, pan in (('th2', 5, 0.22, 0.25), ('th1', 4, 0.26, -0.25)):
    th = np.array(A[key])
    n = np.floor((th - math.pi) / (2 * math.pi))          # номер «оборота» относительно верхней точки
    idx = np.nonzero(np.diff(n))[0]
    last = -1.0
    for j in idx:
        tv = TL.T_REL + j / rate * TL.SLOW
        if tv >= TL.T_CARD or tv - last < 0.12:
            continue
        last = tv
        put(marimba(hz(PENTA[rng.integers(5)], octv), 1.0, amp), tv, pan)
# аккорд к карточке
for k, s in enumerate((0, 4, 7, 12)):
    put(marimba(hz(s, 4), 2.6, 0.2), TL.T_CARD + 0.05 + 0.07 * k, (k - 1.5) * 0.15)
mx = max(np.abs(L).max(), np.abs(R).max(), 1e-6)
st = (np.stack([L, R], 1) / mx * 0.85 * 32767).astype(np.int16)
fade = int(SR * 0.6); env = np.linspace(1, 0, fade)[:, None]
st[-fade:] = (st[-fade:] * env).astype(np.int16)
out = sys.argv[1] if len(sys.argv) > 1 else 'sound.wav'
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(st.tobytes())
print('звук', out, round(TL.DUR, 1), 'с')
