"""Звук для рилса «Ремень восьмёркой» (24 fps, длина из timeline.json). Пишет audio.wav.
Гул мотора идёт за скоростью мотора (та же кривая speed, что в scene.py): затихает и снова набирает обороты на переходе.
Маримба: на прямом ремне фраза идёт вверх; на восьмёрке та же фраза звучит задом наперёд (развёрнутая запись);
на итоговом общем плане — вниз. На переходе — «дзынь» резинки. Финал — мажорный аккорд."""
import os, sys, wave, json, math
import numpy as np
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
SR, FPS = 44100, 24
FRAMES = TL['frames']
DUR = FRAMES / FPS + 0.3
N = int(SR * DUR)
rng = np.random.default_rng(7)
L = np.zeros(N); R = np.zeros(N)
SH = {nm: fr for fr, nm in TL['shots']}
SW, END = TL['belt_switch'], TL['end']
X0, X1 = TL['captions']['cross'][0], SH['wide_end']

def t_(n): return np.arange(n) / SR
def sec(f): return (f - 1) / FPS
def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))
def onepole(x, cutoff):
    a = math.exp(-2 * math.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], np.asarray(x, float))
def note(m): return 440.0 * 2 ** ((m - 69) / 12)
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------ скорость мотора по кадрам (как в scene.py)
SP = TL['speed']
def rev_s(f):
    for (f0, v0), (f1, v1) in zip(SP, SP[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * ease((f - f0) / max(1, f1 - f0))
    return SP[-1][1]
tt = t_(N)
fr_axis = np.arange(1, FRAMES + 2)
speed = np.interp(tt, (fr_axis - 1) / FPS, [rev_s(f) for f in fr_axis]) / SP[0][1]
speed[tt > sec(END) + 1.0] *= np.clip(1 - (tt[tt > sec(END) + 1.0] - sec(END) - 1.0) / 1.5, 0, 1)

# ------------------------------------------------ мотор: гул с высотой по оборотам + шорох лопастей
phm = 2 * np.pi * np.cumsum(70 + 85 * speed) / SR
hum = np.sin(phm) + 0.4 * np.sin(2 * phm) + 0.18 * np.sin(3 * phm) + 0.15 * onepole(rng.standard_normal(N), 1200)
hum = onepole(hum, 1800) * speed
L += hum * 0.045; R += hum * 0.045
blade = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(4 * SP[0][1] * speed) / SR)   # 4 лопасти
air = onepole(rng.standard_normal(N), 700) - onepole(rng.standard_normal(N), 120)
air *= blade ** 2 * speed
L += air * 0.06; R += air * 0.05

# ------------------------------------------------ маримба: фраза вверх -> та же задом наперёд -> вниз
def marimba(f, d=0.6):
    n = int(d * SR); t = t_(n)
    w = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return w * np.minimum(1, t / 0.002) * np.exp(-t * 6.5)
PENTA = [60, 62, 64, 67, 69, 72, 74, 76]                      # до-мажорная пентатоника
STEP = 0.25
def phrase(notes, d_total):
    n = int(d_total * SR); out = np.zeros(n)
    for k, m in enumerate(notes):
        i = int(k * STEP * SR)
        if i >= n: break
        s = marimba(note(m))[: n - i]; out[i:i + len(s)] += s * (0.9 if k % 4 else 1.0)
    return out
up = [PENTA[i % 8] for i in (0, 1, 2, 3, 4, 3, 4, 5, 4, 5, 6, 5, 6, 7, 6, 7)]
UPLEN = len(up) * STEP + 0.6
p_up = phrase(up, UPLEN)
add(phrase(up[:11], 11 * STEP + 0.6), 0.15, 0.10, pan=0.15)   # общий план: тихо
add(p_up, sec(SH['close']) + 0.05, 0.14, pan=-0.1)           # прямой ремень
rev = p_up[::-1]                                             # восьмёрка: та же фраза задом наперёд
add(rev, sec(X0) - 0.3, 0.16, pan=0.1)
down = [PENTA[i] for i in (7, 6, 5, 4, 3, 2)]
add(phrase(down, len(down) * STEP + 0.6), sec(X1) + 0.05, 0.13)

# ------------------------------------------------ переход: «дзынь» резинки на смене ремня
n = int(0.9 * SR); t = t_(n)
f0 = 210 * (1 + 0.35 * np.exp(-t * 18))                      # резинка: короткий подтяг высоты
ph = 2 * np.pi * np.cumsum(f0) / SR
twang = (np.sin(ph) + 0.5 * np.sin(2 * ph) + 0.25 * np.sin(3 * ph)) * np.exp(-t * 5.5) * np.minimum(1, t / 0.004)
add(onepole(twang, 3000), sec(SW) - 0.05, 0.22)
n = int(0.5 * SR); t = t_(n)
swish = onepole(rng.standard_normal(n), 2500) * np.sin(np.pi * np.clip(t / 0.5, 0, 1)) ** 2
add(swish, sec(SW) - 0.4, 0.10)

# ------------------------------------------------ подписи: короткие «блипы»
def blip(a, b, d=0.07):
    n = int(d * SR); t = t_(n); fr = a + (b - a) * t / d
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.45))
for k, (f_, _) in TL['captions'].items():
    add(blip(620, 980), sec(f_), 0.10)
for f_ in (END + 4, END + 8, END + 14, END + 22):
    add(blip(700, 1100), sec(f_), 0.10)

# ------------------------------------------------ финальный аккорд До мажор
for i, m in enumerate((60, 64, 67, 72)):
    n = int(2.6 * SR); t = t_(n); fr = note(m)
    add((np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 1.4),
        sec(END + 8) + i * 0.09, 0.10)
n = int(2.8 * SR); t = t_(n)
bass = sum(np.sin(h * 2 * np.pi * note(36) * t) / h for h in range(1, 7))
add(onepole(bass, 1500) * np.minimum(1, t / 0.2) * np.exp(-t * 0.9), sec(END + 8), 0.10)

mix = np.stack([L, R], 1)
mix *= np.clip(tt / 0.05, 0, 1)[:, None] * np.clip((DUR - tt) / 0.5, 0, 1)[:, None]
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 0.89 / np.max(np.abs(mix))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'audio.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out, round(DUR, 2), 's')
