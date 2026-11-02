"""Музыка и звуки рилса «Чёрная пятница 11.11 · 1+1=3» (синтез кодом, 21 с). Пишет audio.wav.
Маримба на пентатонике + мягкий бас; удары приземления моделей, «дзынь» подарка, свист крышки, гул моторов Горыныча."""
import os, sys, wave, json, math
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))['timeline']
SR, DUR = 44100, 21.3
N = int(SR * DUR); L = np.zeros(N); R = np.zeros(N); rng = np.random.default_rng(11)
def t_(n): return np.arange(n) / SR
def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i < 0 or i >= N: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan)); R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))
def note(m): return 440.0 * 2 ** ((m - 69) / 12)
def marimba(f, d=0.5):
    t = t_(int(SR * d)); e = np.exp(-t * 9)
    return (np.sin(2 * np.pi * f * t) + 0.35 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)) * e
def bass(f, d=0.4):
    t = t_(int(SR * d)); return np.sin(2 * np.pi * f * t) * np.exp(-t * 6) * np.minimum(1, t * 80)
def thump(d=0.35):
    t = t_(int(SR * d)); return np.sin(2 * np.pi * (90 - 50 * t) * t) * np.exp(-t * 14)
def bell(f=1568, d=1.6):
    t = t_(int(SR * d)); e = np.exp(-t * 3.2)
    return (np.sin(2 * np.pi * f * t) + 0.5 * np.sin(2 * np.pi * f * 2.76 * t) * np.exp(-t * 6) + 0.25 * np.sin(2 * np.pi * f * 5.4 * t) * np.exp(-t * 9)) * e
def whoosh(d=0.6, f0=600, f1=2600):
    n = int(SR * d); x = rng.standard_normal(n); t = t_(n)
    fc = f0 + (f1 - f0) * t / d; y = np.zeros(n); acc = 0.0
    for i in range(n):
        a = math.exp(-2 * math.pi * fc[i] / SR); acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y * np.sin(np.pi * t / d) * 2.5
def hum(d, f=110):
    t = t_(int(SR * d)); env = np.minimum(1, t * 6) * np.minimum(1, (d - t) * 6)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(2 * np.pi * 2 * f * t) + 0.15 * np.sign(np.sin(2 * np.pi * f * t))) * env

# музыка: 104 уд/мин, пентатоника до мажор, 4 такта по кругу; к финалу — аккорд
BPM = 104; beat = 60 / BPM
MEL = [72, 76, 79, 76, 81, 79, 76, 74, 72, 74, 76, 79, 76, 74, 72, 67]
BAS = [48, 48, 45, 45, 43, 43, 48, 48]
end_music = TL['card'] - 0.1
k = 0; t = 0.45
while t < end_music:
    add(marimba(note(MEL[k % len(MEL)])), t, 0.16, pan=0.25 * math.sin(k))
    if k % 2 == 0:
        add(bass(note(BAS[(k // 2) % len(BAS)] - 12)), t, 0.22)
    k += 1; t += beat / 2
for m in (60, 64, 67, 72, 76):                              # финальный аккорд под карточку
    add(marimba(note(m), 2.6), TL['card'] + 0.15, 0.13)
add(bell(2093, 2.2), TL['card'] + 0.5, 0.10)

# звуки событий
for key in ('skripach_drop', 'printer_drop', 'box_drop'):
    add(thump(), TL[key] + 14 / 24, 0.55)                   # приземление (падение длится 14 кадров)
add(whoosh(0.55, 500, 2400), TL['lid_pop'] - 0.05, 0.25)    # крышка взлетает
add(bell(1568), TL['lid_pop'] + 0.05, 0.22); add(bell(2349, 1.2), TL['lid_pop'] + 0.18, 0.12)
add(whoosh(0.7, 400, 1800), TL['shell_up'], 0.18)           # коробка улетает
d0, d1 = TL['drive']; t0, t1 = TL['turn']
add(hum(d1 - d0, 104), d0, 0.05); add(hum(t1 - t0, 98), t0, 0.05)   # моторы Горыныча

mx = max(np.abs(L).max(), np.abs(R).max(), 1e-9)
L *= 0.89 / mx; R *= 0.89 / mx
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'audio.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((np.stack([L, R], 1) * 32767).astype('<i2').tobytes())
print('audio', out, round(DUR, 2), 's')
