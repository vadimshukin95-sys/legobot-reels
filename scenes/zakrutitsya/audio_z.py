"""«Закрутится?» — звук, синтезирован кодом (без чужой музыки), синхронно с timeline_z.py.
Тихий фон одинаковой громкости от начала до конца (петля без шва); тиканье на наезде; мотор рвётся рывками и «скрипит»
зубьями; маримба на стрелках, диссонанс на «споре»; щелчок и вжух при снятии шестерни, ровный мотор и радостное арпеджио
при вращении, щелчок при возврате.  python audio_z.py OUT.wav"""
import sys, wave, numpy as np
import timeline_z as TL

SR = 48000
N = int(SR * TL.DUR)
T = np.arange(N) / SR
out = np.zeros(N)
rng = np.random.default_rng(7)


def at(t0, sig, gain=1.0):
    i0 = int(t0 * SR)
    n = min(len(sig), N - i0)
    if n > 0: out[i0:i0 + n] += gain * sig[:n]


def env(n, a=0.005, r=0.2):
    t = np.arange(n) / SR
    return np.minimum(1, t / a) * np.exp(-t / r)


def marimba(f, dur=0.9, gain=0.5):
    n = int(dur * SR); t = np.arange(n) / SR
    s = np.sin(2 * np.pi * f * t) * np.exp(-t / 0.35) + 0.35 * np.sin(2 * np.pi * 4 * f * t) * np.exp(-t / 0.06)
    return gain * s * np.minimum(1, t / 0.003)


def click(gain=0.6, f=1800):
    n = int(0.05 * SR); t = np.arange(n) / SR
    return gain * (np.sin(2 * np.pi * f * t) * 0.6 + rng.normal(0, 0.5, n)) * np.exp(-t / 0.008)


def thud(gain=0.6):
    n = int(0.25 * SR); t = np.arange(n) / SR
    f = 90 * np.exp(-t / 0.08) + 45
    return gain * np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t / 0.09)


def whoosh(dur, f0, f1, gain=0.25):
    n = int(dur * SR); t = np.arange(n) / SR
    noise = rng.normal(0, 1, n)
    # простой резонансный фильтр с плавающей частотой
    y = np.zeros(n); y1 = y2 = 0.0
    for i in range(n):
        f = f0 + (f1 - f0) * (i / n); w = 2 * np.pi * f / SR; rr = 0.985
        y0 = noise[i] * (1 - rr) + 2 * rr * np.cos(w) * y1 - rr * rr * y2
        y[i] = y0; y2, y1 = y1, y0
    y /= (np.abs(y).max() + 1e-9)
    return gain * y * np.sin(np.pi * t / dur) ** 2


def motor(dur, f_of_t, gain=0.12):
    n = int(dur * SR); t = np.arange(n) / SR
    f = f_of_t(t); ph = 2 * np.pi * np.cumsum(f) / SR
    s = sum(np.sin(k * ph) / k for k in range(1, 7))
    return gain * s


# 1. фон: тихий аккорд, одинаковый на всём ролике (петля)
pad = sum(np.sin(2 * np.pi * f * T + p) for f, p in ((110, 0), (164.8, 1.1), (220, 2.0), (261.6, 0.4)))
out += 0.018 * pad * (1 + 0.15 * np.sin(2 * np.pi * 0.25 * T))

# 2. наезд: тиканье, ускоряется
tk = 0.0
while tk < TL.T_PUSH[1] - 0.05:
    at(tk, click(0.18, 2600)); tk += 0.5 - 0.12 * tk / TL.T_PUSH[1]

# 3. рывки мотора
for k in range(3):
    t0 = TL.T_JAM[0] + k
    at(t0, thud(0.55))
    whine = motor(0.62, lambda t: 210 + 25 * np.sin(2 * np.pi * 9 * t) + 40 * (1 - np.exp(-t / 0.05)), 0.10)
    at(t0, whine * np.minimum(1, np.arange(len(whine)) / (0.02 * SR)) * np.minimum(1, (len(whine) - np.arange(len(whine))) / (0.05 * SR)))
    for c in np.arange(0, 0.6, 1 / 15):             # «скрип» зубьев
        at(t0 + c, click(0.22 * (1 - c), 1200 + 300 * rng.random()))

# 4. объяснение: маримба и диссонанс
at(6.0, marimba(523.3)); at(6.4, marimba(659.3, gain=0.4)); at(7.2, marimba(784.0, gain=0.4))
for k in range(5):                                   # «спор»: полутон, 4 раза в секунду
    n = int(0.18 * SR); t = np.arange(n) / SR
    at(8.6 + k * 0.25, 0.10 * (np.sin(2 * np.pi * 330 * t) + np.sin(2 * np.pi * 349.2 * t)) * np.exp(-t / 0.08))

# 5. снятие шестерни: щелчок оси, вжух вверх
at(TL.T_OUT[0] + 0.05, click(0.5, 1500)); at(TL.T_OUT[0] + 0.4, whoosh(0.6, 300, 1800))

# 6. вращение: ровный мотор по скорости + арпеджио
a, b = TL.T_SPIN
dur = b - a
spin = motor(dur, lambda t: 170 + 120 * np.sin(np.pi * t / dur) ** 2, 0.09)
at(a, spin * np.sin(np.pi * np.arange(len(spin)) / len(spin)) ** 0.5)
for k, f in enumerate((523.3, 659.3, 784.0, 1046.5, 784.0, 1046.5)):
    at(a + 0.1 + k * 0.24, marimba(f, gain=0.38))

# 7. возврат: вжух вниз и щелчок посадки
at(TL.T_BACK[0], whoosh(0.5, 1600, 300, 0.2)); at(TL.T_BACK[1] - 0.12, click(0.45, 1500))

out /= max(1e-9, np.abs(out).max()) / 0.85
pcm = (out * 32767).astype(np.int16)
with wave.open(sys.argv[1] if len(sys.argv) > 1 else 'audio.wav', 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print('ok', len(pcm) / SR, 'с')
