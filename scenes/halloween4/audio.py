"""Музыка и звуки для «Сладость или гадость?» (4 конструктора): жутковатый вальс, дверной звонок у каждого крыльца,
звуки механизмов из уроков. Всё синтезировано кодом. -> audio.wav"""
import os, json, wave
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
SR, FPS, FRAMES = 44100, TL['fps'], TL['frames']
DUR = FRAMES / FPS + 0.3
N = int(SR * DUR)
rng = np.random.default_rng(31)
L = np.zeros(N); R = np.zeros(N)
ST = {s['id']: s for s in TL['stops']}

def t_(n):
    return np.arange(n) / SR
def sec(f):
    return (f - 1) / FPS
def add(sig, at, gain=1.0, pan=0.0):
    i = int(at * SR)
    if i >= N or i < 0:
        return
    sig = sig[: N - i]
    L[i:i + len(sig)] += sig * gain * (1 - max(0, pan))
    R[i:i + len(sig)] += sig * gain * (1 + min(0, pan))
def lp(x, cutoff):
    # one-pole low-pass, vectorised via lfilter-like recursion in chunks
    a = np.exp(-2 * np.pi * cutoff / SR)
    y = np.empty_like(x); acc = 0.0
    for i in range(len(x)):
        acc = (1 - a) * x[i] + a * acc; y[i] = acc
    return y
def note(m):
    return 440.0 * 2 ** ((m - 69) / 12)
def env(n, a=0.003, d=0.3):
    t = t_(n); return np.minimum(1, t / a) * np.exp(-t / d)

# ------------------------------------------------------------- music: creepy waltz, E minor, 3/4, 112 BPM
BPM = 112; BEAT = 60 / BPM
def harpsi(f, d=0.6):
    n = int(d * SR); t = t_(n)
    ph = 2 * np.pi * f * t
    w = sum((1 / k) * np.sin(k * ph) * np.exp(-t * (3 + k * 1.6)) for k in range(1, 9))
    return w * np.minimum(1, t / 0.0015)
def organ(fs, d):
    n = int(d * SR); t = t_(n)
    w = sum(np.sin(2 * np.pi * f * t) + 0.5 * np.sin(4 * np.pi * f * t) + 0.25 * np.sin(6 * np.pi * f * t) for f in fs)
    return w * np.minimum(1, t / 0.02) * np.minimum(1, (d - t) / 0.05) * (1 + 0.08 * np.sin(2 * np.pi * 5.5 * t))
def bassn(f, d=0.5):
    n = int(d * SR); t = t_(n)
    return (np.sin(2 * np.pi * f * t) + 0.4 * np.sin(4 * np.pi * f * t)) * env(n, 0.005, 0.22)
# progression (per bar): Em, Em, C, B7 | Em, Am, B7, Em
PROG = [(40, (64, 67, 71)), (40, (64, 67, 71)), (36, (64, 67, 72)), (35, (63, 66, 69)),
        (40, (64, 67, 71)), (45, (64, 69, 72)), (35, (63, 66, 69)), (40, (64, 67, 71))]
MEL = [[76, None, 79], [78, 76, 75], [76, None, 72], [71, None, None],
       [76, 79, 83], [81, 79, 76], [75, 76, 78], [76, None, None]]

def music(t0, t1, gain=1.0, oct_=0):
    t = t0; bar = 0
    while t < t1 - 0.05:
        b, ch = PROG[bar % 8]
        add(bassn(note(b)), t, 0.42 * gain)
        for k in (1, 2):
            if t + k * BEAT < t1:
                add(organ([note(m) for m in ch], BEAT * 0.55), t + k * BEAT, 0.035 * gain, pan=0.25 if k == 1 else -0.25)
        for k, m in enumerate(MEL[bar % 8]):
            if m and t + k * BEAT < t1:
                add(harpsi(note(m + oct_), 0.7), t + k * BEAT, 0.13 * gain, pan=-0.2)
        t += 3 * BEAT; bar += 1

# music runs under the whole reel but stops dead for each scare and comes back a moment later
cuts = [(ST['wedo']['f0'] + ST['wedo']['ev']['trig'], 22), (ST['prime']['f0'] + ST['prime']['ev']['trig'], 20),
        (ST['essential']['f0'] + ST['essential']['ev']['red'], 26), (ST['ev3']['f0'] + ST['ev3']['ev']['trig'], 22)]
segs = []; t0 = 0.0
for f, hold in cuts:
    segs.append((t0, sec(f) - 0.03)); t0 = sec(f + hold)
segs.append((t0, sec(TL['overlay']['final_f']) - 0.05))
for a, b in segs:
    music(a, b, 1.0)
music(sec(TL['overlay']['final_f']), DUR - 0.25, 1.05, oct_=12)

# ------------------------------------------------------------- SFX
def blip(f0, f1, d=0.09, sq=False):
    n = int(d * SR); t = t_(n)
    f = f0 + (f1 - f0) * t / d
    ph = 2 * np.pi * np.cumsum(f) / SR
    w = np.sign(np.sin(ph)) * 0.55 if sq else np.sin(ph)
    return w * np.minimum(1, t / 0.003) * np.exp(-t / (d * 0.45))
def bell(m, d=1.2):
    n = int(d * SR); t = t_(n); fr = note(m)
    return (np.sin(2 * np.pi * fr * t) + 0.5 * np.sin(2 * np.pi * fr * 2.76 * t) * np.exp(-t * 5)
            + 0.25 * np.sin(2 * np.pi * fr * 5.4 * t) * np.exp(-t * 9)) * np.exp(-t * 2.4) * np.minimum(1, t / 0.002)
def doorbell(at):
    add(bell(79), at, 0.22, 0.1); add(bell(75), at + 0.42, 0.22, -0.1)
def whoosh(d, lo=1400):
    n = int(d * SR); t = t_(n)
    return lp(rng.standard_normal(n) * np.sin(np.pi * t / d) ** 2, lo) * 1.6
def motor(d, f0=260, f1=430):
    n = int(d * SR); tt = t_(n)
    ramp = np.clip(tt / 0.04, 0, 1) * np.clip((d - tt) / 0.04, 0, 1)
    fm = f0 + (f1 - f0) * np.clip(tt / 0.15, 0, 1)
    ph = 2 * np.pi * np.cumsum(fm) / SR
    return (np.sin(ph) + 0.4 * np.sin(2 * ph) + 0.25 * lp(rng.standard_normal(n), 2200)) * ramp
def clack(f=420):
    n = int(0.12 * SR); t = t_(n)
    return (np.sin(2 * np.pi * f * t) + 0.6 * np.sin(2 * np.pi * f * 2.3 * t)) * np.exp(-t * 50)
def hit(at, g=0.8):
    n = int(1.2 * SR); t = t_(n)
    add(np.sin(2 * np.pi * (46 + 52 * np.exp(-t * 12)) * t) * np.exp(-t * 3.5), at, g)
def step_sound():
    n = int(0.09 * SR); t = t_(n)
    return lp(rng.standard_normal(n), 900) * np.exp(-t * 45) * 2.2
def ha(f0, d=0.17, bright=1.0):
    """one 'ha' of a laugh: breathy onset + vowel /a/ by formant-weighted harmonics"""
    n = int(d * SR); t = t_(n)
    f = f0 * (1 + 0.04 * np.sin(np.pi * t / d))
    ph = 2 * np.pi * np.cumsum(f) / SR
    v = np.zeros(n)
    for k in range(1, 30):
        fk = k * f0
        a = np.exp(-((fk - 780) / 160) ** 2) + 0.7 * np.exp(-((fk - 1180) / 220) ** 2) + 0.35 * bright * np.exp(-((fk - 2600) / 320) ** 2)
        v += a * np.sin(k * ph)
    e = np.minimum(1, t / 0.025) * np.clip((d - t) / 0.06, 0, 1)
    h = lp(rng.standard_normal(n), 3000) * np.exp(-t * 40) * 0.6
    return v * e * 0.5 + h
def laugh(at, f0=170, n=5, gap=0.21, g=0.5, pan=0.0):
    for i in range(n):
        add(ha(f0 * (1 - 0.05 * i)), at + i * gap, g * (1 - 0.08 * i), pan)

# footsteps while the camera walks to the next porch, doorbell on arrival
for s in TL['stops']:
    f0 = s['f0']
    for k in range(5):
        add(step_sound(), sec(f0 - 16) + k * 0.16, 0.5, pan=(-0.3 if k % 2 else 0.3))
    doorbell(sec(f0 + 2))

# --- WeDo 2.0: motion sensor -> hub red -> motor 0,6 s -> ghost up (BOO) -> after 3 s falls
w = ST['wedo']; f0 = w['f0']; e = w['ev']
add(blip(880, 880, 0.07, True), sec(f0 + e['trig']), 0.22); add(blip(660, 660, 0.09, True), sec(f0 + e['trig']) + 0.08, 0.22)
add(motor(0.6), sec(f0 + e['trig']), 0.26)
hit(sec(f0 + e['trig'] + 13))
n = int(1.7 * SR); t = t_(n)
fq = 300 + 230 * np.sin(np.pi * t / 1.7) + 9 * np.sin(2 * np.pi * 6 * t)
gv = (np.sin(2 * np.pi * np.cumsum(fq) / SR) + 0.25 * np.sin(4 * np.pi * np.cumsum(fq) / SR)) * np.sin(np.pi * t / 1.7) ** 1.2
add(gv, sec(f0 + e['trig'] + 14), 0.17, -0.15)
add(clack(), sec(f0 + e['trig'] + 14), 0.4)
add(whoosh(0.3, 1600), sec(f0 + e['down']), 0.3); add(clack(300), sec(f0 + e['down'] + 7), 0.45)

# --- SPIKE Prime: distance < 15 cm -> beep (сигнал 72) -> motor B 90° -> bat flies up, flutters
p = ST['prime']; f0 = p['f0']; e = p['ev']
add(blip(note(72), note(72), 0.25, True), sec(f0 + e['trig']), 0.2)
add(motor(0.45, 320, 520), sec(f0 + e['trig']), 0.24)
hit(sec(f0 + e['trig'] + 11), 0.6)
for k in range(10):                                   # wing flutter
    add(whoosh(0.07, 2500), sec(f0 + e['trig'] + 10) + k * 0.075, 0.35, pan=0.3 * np.sin(k))
for k in range(4):                                    # squeaks
    add(blip(3200, 4200, 0.05), sec(f0 + e['trig'] + 12) + k * 0.13, 0.12, pan=0.2)
add(motor(0.45, 320, 520), sec(f0 + e['down']), 0.2)

# --- SPIKE Essential: yellow -> "Ам!" + lid up/down; red -> angry clacks + evil laugh
s3 = ST['essential']; f0 = s3['f0']; e = s3['ev']
add(whoosh(0.5, 900), sec(f0 + e['y_in0']), 0.25)
add(blip(1200, 1600, 0.06), sec(f0 + e['yellow']), 0.18)
n = int(0.22 * SR); t = t_(n)
chomp = lp(rng.standard_normal(n), 1800) * np.exp(-t * 18) * 1.4 + np.sin(2 * np.pi * (180 - 80 * t / 0.22) * t) * np.exp(-t * 14)
add(chomp, sec(f0 + e['yellow'] + 1), 0.55)
add(ha(240, 0.22, 1.3), sec(f0 + e['yellow'] + 2), 0.35)          # "Ам!"
add(motor(0.4, 300, 420), sec(f0 + e['yellow']), 0.18); add(motor(0.4, 300, 420), sec(f0 + e['ydown']), 0.16)
add(clack(), sec(f0 + e['ydown'] + 9), 0.35)
add(whoosh(0.5, 900), sec(f0 + e['r_in0']), 0.25)
add(blip(500, 300, 0.12, True), sec(f0 + e['red']), 0.2)
for k in range(5):
    add(clack(520 + 30 * k), sec(f0 + e['red'] + 4 + k * 6), 0.5)
laugh(sec(f0 + e['red'] + 24), f0=230, n=5, gap=0.19, g=0.45)

# --- EV3: ultrasonic ping -> laugh, arms up (motor 0,3 s) -> arms down
v = ST['ev3']; f0 = v['f0']; e = v['ev']
for k in range(3):
    add(blip(2400, 2400, 0.04), sec(f0 + e['trig'] - 14) + k * 0.18, 0.1)
add(motor(0.3, 200, 330), sec(f0 + e['trig']), 0.3)
hit(sec(f0 + e['trig'] + 8), 0.7)
laugh(sec(f0 + e['trig'] + 4), f0=120, n=6, gap=0.22, g=0.6)
add(whoosh(0.3, 1400), sec(f0 + e['down']), 0.3); add(clack(260), sec(f0 + e['down'] + 8), 0.45)

# bursts pop
for s in TL['stops']:
    for b in s['ov']['bursts']:
        add(blip(700, 1100, 0.06), sec(s['f0'] + b['t0']), 0.1)

# intro: wind + owl-ish distant hoot; finale chime
add(whoosh(2.4, 500), 0.0, 0.5)
add(blip(note(64), note(62), 0.5) * 0.6, 0.6, 0.12); add(blip(note(64), note(60), 0.7) * 0.6, 1.2, 0.12)
ff = sec(TL['overlay']['final_f'])
for i, m in enumerate((64, 67, 71, 76)):
    add(bell(m + 12, 1.5), ff + i * 0.12, 0.13, pan=-0.3 + 0.2 * i)
for k in range(4):
    add(blip(620, 980, 0.07), sec(TL['overlay']['final_f'] + 5 + 4 * k), 0.12)

# master: gentle limiter, fades
mx = np.stack([L, R], 1)
fade = np.ones(N); fi = int(0.25 * SR); fo = int(0.6 * SR)
fade[:fi] = np.linspace(0, 1, fi); fade[-fo:] = np.linspace(1, 0, fo)
mx *= fade[:, None]
peak = np.max(np.abs(mx)); mx = np.tanh(mx / peak * 1.25) * 0.9
with wave.open(os.path.join(HERE, 'audio.wav'), 'wb') as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR)
    wf.writeframes((mx * 32767).astype(np.int16).tobytes())
print('audio ok', round(DUR, 2), 's')
