"""Звук для рилса «Ремень проскальзывает» (24 fps, длина из timeline.json). Пишет audio.wav.
Гул мотора не смолкает (мотор крутится всё время), под нагрузкой чуть ниже и напряжённее.
Шорох лопастей идёт за скоростью вентилятора (motion.py): стоп — тишина лопастей.
Касание карандаша — деревянный «тук»; пока ремень скользит — мягкое «шшш» с пульсом от оборотов шкива.
Маримба: фраза вверх на общем плане; на застревании — две ноты «туда-сюда»; после перезапуска — фраза вверх; финал — аккорд."""
import os, sys, wave, json, math
import numpy as np
from scipy.signal import lfilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import motion as MO
TL = MO.TL
SR, FPS = 44100, 24
FRAMES = TL['frames']
DUR = FRAMES / FPS + 0.3
N = int(SR * DUR)
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
SH = {nm: fr for fr, nm in TL['shots']}
END = TL['end']; FC = MO.FC; R0, R1 = TL['stop']['restart']

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

tt = t_(N)
fa = np.arange(1, FRAMES + 2)
def curve(vals): return np.interp(tt, (fa - 1) / FPS, vals)
drive = curve([MO.rev_s(f) for f in fa]) / MO.SP[0][1]
fan = curve([MO.SPEED.get(f, MO.SPEED[FRAMES]) for f in fa]) / MO.SP[0][1]
stuck = curve([1.0 if (FC <= f < R0) else 0.0 for f in fa])
stuck = onepole(stuck, 6)                                    # плавный вход/выход нагрузки
tail = tt > sec(END) + 1.0
drive[tail] *= np.clip(1 - (tt[tail] - sec(END) - 1.0) / 1.5, 0, 1)
fan[tail] *= np.clip(1 - (tt[tail] - sec(END) - 1.0) / 1.5, 0, 1)

# ------------------------------------------------ мотор: гул; под нагрузкой ниже и чуть громче
phm = 2 * np.pi * np.cumsum((70 + 85 * drive) * (1 - 0.10 * stuck)) / SR
hum = np.sin(phm) + 0.4 * np.sin(2 * phm) + (0.18 + 0.12 * stuck) * np.sin(3 * phm) + 0.15 * onepole(rng.standard_normal(N), 1200)
hum = onepole(hum, 1800) * drive * (1 + 0.25 * stuck)
L += hum * 0.045; R += hum * 0.045
# ------------------------------------------------ лопасти: шорох воздуха по скорости вентилятора
blade = 0.5 + 0.5 * np.sin(2 * np.pi * np.cumsum(4 * MO.SP[0][1] * fan) / SR)
air = onepole(rng.standard_normal(N), 700) - onepole(rng.standard_normal(N), 120)
air *= blade ** 2 * fan
L += air * 0.06; R += air * 0.05
# ------------------------------------------------ скольжение ремня: «шшш», пульс 6 отверстий шкива
puls = 0.65 + 0.35 * np.sin(2 * np.pi * np.cumsum(6 * MO.SP[0][1] * drive) / SR)
hiss = onepole(rng.standard_normal(N), 3200) - onepole(rng.standard_normal(N), 900)
hiss *= stuck * puls
L += hiss * 0.05; R += hiss * 0.055

# ------------------------------------------------ «тук» лопасти о карандаш, «вжух» карандаша
def knock(f0=900, d=0.18):
    n = int(d * SR); t = t_(n)
    body = np.sin(2 * np.pi * f0 * t) * np.exp(-t * 38) + 0.6 * np.sin(2 * np.pi * f0 * 1.7 * t) * np.exp(-t * 55)
    click = onepole(rng.standard_normal(n), 4000) * np.exp(-t * 120)
    return body + 0.6 * click
add(knock(), sec(FC) - 0.01, 0.30, pan=0.2)
def swish(d=0.35):
    n = int(d * SR); t = t_(n)
    return onepole(rng.standard_normal(n), 2500) * np.sin(np.pi * np.clip(t / d, 0, 1)) ** 2
pi0, pi1 = TL['pencil']['in']; po0, po1 = TL['pencil']['out']
add(swish(), sec(pi0), 0.10, pan=0.3)
add(swish(0.45), sec(po0), 0.10, pan=0.3)

# ------------------------------------------------ маримба
def marimba(f, d=0.6):
    n = int(d * SR); t = t_(n)
    w = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return w * np.minimum(1, t / 0.002) * np.exp(-t * 6.5)
PENTA = [60, 62, 64, 67, 69, 72, 74, 76]
STEP = 0.25
def phrase(notes, d_total, step=STEP):
    n = int(d_total * SR); out = np.zeros(n)
    for k, m in enumerate(notes):
        i = int(k * step * SR)
        if i >= n: break
        s = marimba(note(m))[: n - i]; out[i:i + len(s)] += s * (0.9 if k % 4 else 1.0)
    return out
up = [PENTA[i % 8] for i in (0, 1, 2, 3, 4, 3, 4, 5)]
n_before = int((sec(FC) - 0.15) / STEP)                      # фраза обрывается на касании
add(phrase(up[:n_before], n_before * STEP + 0.6), 0.15, 0.10, pan=0.15)
# застревание: две ноты «туда-сюда», тихо
seesaw = [64, 62] * 9
t0 = sec(SH['close']) + 0.1; t1 = sec(R0) - 0.3
k = int((t1 - t0) / 0.5)
add(phrase(seesaw[:k], k * 0.5 + 0.6, 0.5), t0, 0.08, pan=-0.1)
# перезапуск: фраза вверх
up2 = [PENTA[i] for i in (0, 1, 2, 3, 4, 5, 6, 7, 6, 7)]
add(phrase(up2, len(up2) * STEP + 0.6), sec(R0) + 0.1, 0.14)
# итог
add(phrase([PENTA[i] for i in (7, 5, 4, 5, 7)], 5 * STEP + 0.6), sec(SH['wide_end']) + 0.05, 0.12)

# ------------------------------------------------ подписи и карточка — блипы; финальный аккорд До мажор
def blip(a, b, d=0.07):
    n = int(d * SR); t = t_(n); fr = a + (b - a) * t / d
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.45))
for k_, (f_, _) in TL['captions'].items():
    add(blip(620, 980), sec(f_), 0.10)
for f_ in (END + 4, END + 8, END + 14, END + 22):
    add(blip(700, 1100), sec(f_), 0.10)
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
