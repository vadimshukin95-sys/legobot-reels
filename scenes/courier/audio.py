"""Cheerful music + SFX for the robot-courier reel (@ 24 fps, length from timeline.json). Writes audio.wav.
Steps tick exactly when the supporting foot changes (same gait maths as scene.py)."""
import os, sys, wave, json, math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
SR, FPS = 44100, 24
FRAMES = TL.get('frames', 444)
DUR = FRAMES / FPS + 0.25
N = int(SR * DUR)
rng = np.random.default_rng(5)
L = np.zeros(N); R = np.zeros(N)
STOP, GO = TL['stop'], TL['go']

def t_(n): return np.arange(n) / SR
def sec(f): return (f - 1) / FPS
def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0: return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))
def lp(x, cutoff):
    a = np.exp(-2 * np.pi * cutoff / SR); y = np.empty_like(x); acc = 0.0
    for i, v in enumerate(x):
        acc = (1 - a) * v + a * acc; y[i] = acc
    return y
def note(m): return 440.0 * 2 ** ((m - 69) / 12)

# ------------------------------------------------------------- music: bouncy C major, 112 BPM
BPM = 112; BEAT = 60 / BPM; S8 = BEAT / 2
def marimba(f, d=0.45):
    n = int(d * SR); t = t_(n)
    w = np.sin(2 * np.pi * f * t) + 0.25 * np.sin(2 * np.pi * f * 4 * t) * np.exp(-t * 30)
    return w * np.minimum(1, t / 0.002) * np.exp(-t * 7)
def bass(f, d=0.35):
    n = int(d * SR); t = t_(n)
    w = np.sin(2 * np.pi * f * t) + 0.3 * np.sin(4 * np.pi * f * t)
    return w * np.minimum(1, t / 0.005) * np.exp(-t * 6)
def kick():
    n = int(0.3 * SR); t = t_(n)
    return np.sin(2 * np.pi * np.cumsum(55 + 90 * np.exp(-t * 30)) / SR) * np.exp(-t * 10)
def clap():
    n = int(0.15 * SR); x = rng.standard_normal(n)
    return (x - lp(x, 1200)) * np.exp(-t_(n) * 28) * 0.6
def shaker():
    n = int(0.05 * SR); x = rng.standard_normal(n)
    return (x - lp(x, 5000)) * np.exp(-t_(n) * 70)

prog = [(48, [60, 64, 67, 72]), (53, [65, 69, 72, 77]), (55, [67, 71, 74, 79]), (48, [64, 67, 72, 76])]
melody = [76, 79, 81, 79, 76, 74, 72, 74]
def music(t0, t1, gain=1.0, drums=True):
    t = t0; step = 0
    while t < t1:
        bar = int((t - t0) / (4 * BEAT)) % 4
        root, chord = prog[bar]
        if step % 2 == 0:
            add(bass(note(root - 12 + (7 if step % 4 == 2 else 0))), t, 0.32 * gain)
        if drums:
            if step % 4 == 0: add(kick(), t, 0.42 * gain)
            if step % 8 == 4: add(clap(), t, 0.22 * gain)
            add(shaker(), t, 0.06 * gain, pan=0.3)
        add(marimba(note(chord[step % 4])), t, 0.11 * gain, pan=-0.25 if step % 2 else 0.25)
        if step % 2 == 0:
            add(marimba(note(melody[(step // 2) % 8]), 0.6), t, 0.14 * gain)
        t += S8; step += 1

music(0.0, sec(STOP), 1.0)
music(sec(STOP) + 0.05, sec(GO), 0.45, drums=False)          # soft while the courier waits
music(sec(GO), DUR - 0.2, 1.0)

# ------------------------------------------------------------- gait-synced SFX
OMEGA = TL['rev_per_s'] * 2 * math.pi / FPS
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def speed(f):
    if f < STOP - 4: return 1.0
    if f < STOP + 2: return 1.0 - ease((f - (STOP - 4)) / 6)
    if f < GO: return 0.0
    return ease((f - GO) / 8)
def tok(pitch=1.0):
    n = int(0.09 * SR); t = t_(n)
    return (np.sin(2 * np.pi * 900 * pitch * t) * 0.6 + np.sin(2 * np.pi * 1700 * pitch * t) * 0.3) * np.exp(-t * 60)
th = TL.get('th0', 0.6); prev = math.cos(th) >= 0; k = 0
mot = np.zeros(N)
for f in range(2, FRAMES + 1):
    sp = speed(f); th += OMEGA * sp
    cur = math.cos(th) >= 0
    if cur != prev:                                  # supporting foot changes -> plastic «tok»
        add(tok(1.0 if k % 2 else 0.84), sec(f), 0.32, pan=-0.2 if k % 2 else 0.2); k += 1
    prev = cur
    if sp > 0.01:                                    # motor + worm whine envelope
        i0, i1 = int(sec(f) * SR), int(sec(f + 1) * SR)
        mot[i0:i1] = sp
tt = t_(N)
ph = 2 * np.pi * np.cumsum(190 + 6 * np.sin(2 * np.pi * 0.7 * tt)) / SR
motor = (np.sin(ph) + 0.35 * np.sin(2 * ph) + 0.25 * lp(rng.standard_normal(N), 1800)) * lp(mot, 30)
L += motor * 0.07; R += motor * 0.07

def blip(f0, f1, d=0.09):
    n = int(d * SR); t = t_(n); fr = f0 + (f1 - f0) * t / d
    return np.sin(2 * np.pi * np.cumsum(fr) / SR) * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.45))
def whoosh(d, lo=1400):
    n = int(d * SR); t = t_(n)
    return lp(rng.standard_normal(n) * np.sin(np.pi * t / d) ** 2, lo) * 1.6
add(whoosh(0.9, 900), sec(TL['hand0'] + 4), 0.3, pan=0.4)                 # hand comes in
for i in range(3):                                                           # sensor pings
    add(blip(1250, 1250, 0.06), sec(STOP - 10) + i * 0.11, 0.2)
for i, m in enumerate((72, 76, 79, 84)):                                    # «доставлено!» ding
    n = int(1.1 * SR); t = t_(n); fr = note(m + 12)
    bell = (np.sin(2 * np.pi * fr * t) + 0.4 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 3.2)
    add(bell, sec(STOP + 1) + i * 0.07, 0.2)
add(whoosh(0.5, 2000), sec(TL['handout'] + 2), 0.3, pan=0.5)               # hand leaves
for f_ in (3, 14, 92, 126, 172, 208, 252, STOP - 6, STOP, STOP + 36, GO + 6, GO + 8, GO + 14):
    add(blip(620, 980, 0.07), sec(f_), 0.15)                                 # caption pops
for i, m in enumerate((67, 72, 76, 79)):                                    # end chime
    n = int(1.3 * SR); t = t_(n); fr = note(m + 12)
    add((np.sin(2 * np.pi * fr * t) + 0.3 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 6)) * np.exp(-t * 3.0),
        sec(GO + 8) + i * 0.09, 0.16)

mix = np.stack([L, R], 1)
mix *= np.clip((DUR - t_(N)) / 0.4, 0, 1)[:, None]
mix = np.tanh(mix * 1.2) / np.tanh(1.2)
mix *= 0.89 / np.max(np.abs(mix))
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'audio.wav')
with wave.open(out, 'wb') as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR)
    w.writeframes((mix * 32767).astype('<i2').tobytes())
print('wrote', out, round(DUR, 2), 's')
