"""Звук для рилса «Скрипач» (24 fps, длина из timeline.json): виолончель в такт смычку модели,
маримба на крупных планах механизма, щелчки зубьев 24z, гул мотора, финальный аккорд. Пишет audio.wav.
Громкость виолончели идёт за скоростью, с которой смычок скользит сквозь кисть (та же кинематика, что в scene.py);
на каждой смене направления смычка — новая нота (тоника/квинта текущего аккорда)."""
import os, sys, wave, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
SR, FPS = 44100, 24
FRAMES = TL['frames']
DUR = FRAMES / FPS + 0.3
N = int(SR * DUR)
rng = np.random.default_rng(11)
L = np.zeros(N); R = np.zeros(N)
SH = {nm: fr for fr, nm in TL['shots']}
G0, C0, W0, END = SH['gears'], SH['crank'], SH['wide'], TL['end']

def t_(n): return np.arange(n) / SR
def sec(f): return (f - 1) / FPS
def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))
from scipy.signal import lfilter
def onepole(x, cutoff):
    a = math.exp(-2 * math.pi * cutoff / SR)
    return lfilter([1 - a], [1, -a], np.asarray(x, float))
def note(m): return 440.0 * 2 ** ((m - 69) / 12)
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

# ------------------------------------------------ кинематика смычка (как в scene.py)
SP = TL['speed']
def rev_s(f):
    for (f0, v0), (f1, v1) in zip(SP, SP[1:]):
        if f0 <= f <= f1:
            return v0 + (v1 - v0) * ease((f - f0) / max(1, f1 - f0))
    return SP[-1][1]
TH = {1: 25.0}
for f in range(2, FRAMES + 3):
    TH[f] = TH[f - 1] + rev_s(f) * 360.0 / FPS
XK, YK, RC, HX, HY = 100.0, -70.0, 20.0, -60.0, -110.0
def dist(th):
    t = math.radians(th)
    return math.hypot(XK + RC * math.cos(t) - HX, YK - RC * math.sin(t) - HY)
# скорость скольжения смычка (LDU/кадр) с разрешением 1/8 кадра
SUB = 8
fs = np.arange(1, FRAMES + 1, 1 / SUB)
def th_at(x):
    f = int(x); w = x - f
    return TH[f] + (TH[f + 1] - TH[f]) * w
dd = np.array([dist(th_at(x)) for x in fs])
vel = np.gradient(dd) * SUB                              # LDU/кадр
ts = (fs - 1) / FPS
# смены направления — начала штрихов
rev_idx = np.nonzero(np.sign(vel[1:]) != np.sign(vel[:-1]))[0]
strokes = [0.0] + [ts[i] for i in rev_idx] + [DUR]

# ------------------------------------------------ гармония: Dm – B♭ – F – C, аккорд каждые 2 с
CHORDS = [(50, [62, 65, 69]), (46, [58, 62, 65]), (53, [60, 65, 69]), (48, [60, 64, 67])]
BAR = 2.0
def chord_at(t): return CHORDS[int(t / BAR) % 4]

# ------------------------------------------------ виолончель: аддитивная «пила» с вибрато, громкость = скорость смычка
tt = t_(N)
freq = np.zeros(N)
for k, (a, b) in enumerate(zip(strokes, strokes[1:])):
    root = chord_at(a + 0.05)[0] - 12
    m = root + (7 if k % 2 else 0)
    i0, i1 = int(a * SR), min(N, int(b * SR))
    freq[i0:i1] = note(m)
freq = onepole(freq, 18.0)                               # лёгкое портаменто между нотами
freq *= 1 + 0.006 * np.sin(2 * np.pi * 5.4 * tt) * np.clip((tt % 1.0) * 3, 0, 1)
ph = 2 * np.pi * np.cumsum(freq) / SR
cello = np.zeros(N)
for h in range(1, 13):
    cello += np.sin(h * ph) / h * (1.0 if h < 4 else 0.7)
bow = onepole(rng.standard_normal(N), 2500) * 0.35      # шорох смычка
cello = onepole(cello + bow * 0.2, 2600)
env = np.interp(tt, ts, np.clip(np.abs(vel) / 6.0, 0, 1))
env = onepole(env, 12.0)
# где звучит виолончель: общий план и вопрос, снова на общем плане, затихает под финал
def lvl(t):
    f = t * FPS + 1
    if f < G0: return 1.0 if f < G0 - 20 else 1.0 - 0.75 * ease((f - (G0 - 20)) / 20)
    if f < W0 - 10: return 0.25
    if f < W0 + 10: return 0.25 + 0.75 * ease((f - (W0 - 10)) / 20)
    if f < END: return 1.0
    return max(0.0, 1.0 - (f - END) / 40)
cl = np.array([lvl(x) for x in np.arange(0, DUR, 0.01)])
cello *= env * np.interp(tt, np.arange(0, DUR, 0.01), cl)
L += cello * 0.30; R += cello * 0.24

# ------------------------------------------------ маримба: арпеджио по аккордам, громче на механизме
def marimba(f, d=0.5):
    n = int(d * SR); t = t_(n)
    w = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return w * np.minimum(1, t / 0.002) * np.exp(-t * 7)
S8 = BAR / 8
t = 0.0; step = 0
while t < sec(END) + 0.2:
    root, ch = chord_at(t)
    f = t * FPS + 1
    g = 0.05 if f < G0 - 10 else (0.13 if f < W0 else 0.07)
    add(marimba(note(ch[step % 3] + (12 if step % 4 == 3 else 0))), t, g, pan=-0.25 if step % 2 else 0.25)
    t += S8; step += 1

# ------------------------------------------------ мотор: тихий гул, щелчки зубьев 24z на крупных планах
mot = 0.5 + 0.5 * np.interp(tt, ts, np.clip(np.abs(np.gradient([th_at(x) for x in fs]) * SUB) / 10, 0, 1))
phm = 2 * np.pi * np.cumsum(140 + 30 * mot) / SR
hum = (np.sin(phm) + 0.35 * np.sin(2 * phm) + 0.2 * onepole(rng.standard_normal(N), 1500))
hum *= np.interp(tt, [0, sec(G0) - 0.3, sec(G0) + 0.3, sec(W0), sec(W0) + 0.5, DUR], [0.25, 0.25, 1.0, 1.0, 0.25, 0.1])
L += hum * 0.035; R += hum * 0.035
def tick():
    n = int(0.025 * SR); t = t_(n)
    return (np.sin(2 * np.pi * 2900 * t) * 0.5 + rng.standard_normal(n) * 0.3) * np.exp(-t * 170)
acc = 0.0
for f in range(G0, W0):
    acc += (TH[f + 1] - TH[f]) / 15.0                    # зуб 24z = 15°
    while acc >= 1.0:
        add(tick(), sec(f), 0.07, pan=0.2); acc -= 1.0

# ------------------------------------------------ подписи (короткие «блипы») и финальный аккорд
def blip(f0, f1, d=0.08):
    n = int(d * SR); t = t_(n); fr = f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.45))
for f_ in (3, 16, 72, G0 + 12, G0 + 64, C0 + 16, C0 + 60, W0 + 6, W0 + 16, END + 6, END + 10, END + 18):
    add(blip(620, 980, 0.07), sec(f_), 0.12)
for i, m in enumerate((62, 65, 69, 74)):                 # Dm
    n = int(2.4 * SR); t = t_(n); fr = note(m)
    add((np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 1.6),
        sec(END + 10) + i * 0.09, 0.09)
n = int(3.0 * SR); t = t_(n)                             # последняя длинная нота виолончели
lowd = sum(np.sin(h * 2 * np.pi * note(38) * t) / h for h in range(1, 10))
add(onepole(lowd, 2000) * np.minimum(1, t / 0.25) * np.exp(-t * 0.8), sec(END + 8), 0.13)

mix = np.stack([L, R], 1)
mix *= np.clip(tt / 0.05, 0, 1)[:, None] * np.clip((DUR - tt) / 0.5, 0, 1)[:, None]
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 0.89 / np.max(np.abs(mix))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'audio.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out, round(DUR, 2), 's', 'strokes', len(strokes) - 1)
