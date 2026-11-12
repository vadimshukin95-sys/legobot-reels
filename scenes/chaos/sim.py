"""Физика двойного (физического) маятника: два твёрдых тела, шарниры P0 и P1, лёгкое трение в осях.
Массы — оценка по деталям SPIKE Prime (г), длины — из chaos_model (LDU -> м).
python sim.py -> печатает сводку; simulate() -> массив углов th1, th2 по кадрам."""
import numpy as np
import chaos_model as M

LDU = 0.0004            # м
G = 9.81
# --- тело 1: балка 11 (центр на 80 от P0), колесо W1 + ось 5 на P1
m_b1, Lb1 = 2.6e-3, 220 * LDU
m_w, r_w = 11.0e-3, 70 * LDU
m_ax = 0.6e-3
L1 = M.L1 * LDU
m1 = m_b1 + m_w + m_ax
a1 = (m_b1 * 80 * LDU + (m_w + m_ax) * L1) / m1
I1 = m_b1 * (Lb1 ** 2 / 12 + (80 * LDU) ** 2) + 0.6 * m_w * r_w ** 2 + (m_w + m_ax) * L1 ** 2   # вокруг P0
# --- тело 2: балка 13 (центр +20), W2 + штифт на -100, W3 (диск+шина) + штифт на +140, плитка и втулка на P1
parts2 = [(3.0e-3, 20, 260), (m_w, -100, None), (0.5e-3, -100, 0), (2.7e-3, 140, None), (0.5e-3, 140, 0), (0.85e-3, 0, 0)]
m2 = sum(p[0] for p in parts2)
a2 = sum(p[0] * p[1] for p in parts2) / m2 * LDU          # центр масс вдоль звена 2 от P1 (знак: + к длинному концу)
I2c = 0.0
for m, d, ln in parts2:
    d = d * LDU - a2
    own = m * (ln * LDU) ** 2 / 12 if ln else 0.0
    I2c += own + m * d * d
I2c += 0.6 * m_w * r_w ** 2 + 0.6 * 2.2e-3 * (28 * LDU) ** 2     # собственная инерция колёс (крутятся вместе с балкой)
C_FR = 2.0e-6           # вязкое трение в осях, Н·м·с


def deriv(s):
    t1, t2, w1, w2 = s
    d = t1 - t2
    Mm = np.array([[I1 + m2 * L1 ** 2, m2 * L1 * a2 * np.cos(d)],
                   [m2 * L1 * a2 * np.cos(d), I2c + m2 * a2 ** 2]])
    f1 = -m2 * L1 * a2 * np.sin(d) * w2 ** 2 - G * (m1 * a1 + m2 * L1) * np.sin(t1) - C_FR * w1 + C_FR * (w2 - w1)
    f2 = m2 * L1 * a2 * np.sin(d) * w1 ** 2 - G * m2 * a2 * np.sin(t2) - C_FR * (w2 - w1)
    acc = np.linalg.solve(Mm, [f1, f2])
    return np.array([w1, w2, acc[0], acc[1]])


def simulate(t1, t2, dur, fps=30, sub=80, w1=0.0, w2=0.0):
    s = np.array([t1, t2, w1, w2], float)
    dt = 1.0 / (fps * sub)
    out = [s.copy()]
    for k in range(int(dur * fps)):
        for _ in range(sub):
            k1 = deriv(s); k2 = deriv(s + dt / 2 * k1); k3 = deriv(s + dt / 2 * k2); k4 = deriv(s + dt * k3)
            s = s + dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        out.append(s.copy())
    return np.array(out)


def energy(s):
    t1, t2, w1, w2 = s
    T = 0.5 * (I1 + m2 * L1 ** 2) * w1 ** 2 + 0.5 * (I2c + m2 * a2 ** 2) * w2 ** 2 + m2 * L1 * a2 * np.cos(t1 - t2) * w1 * w2
    V = -G * ((m1 * a1 + m2 * L1) * np.cos(t1) + m2 * a2 * np.cos(t2))
    return T + V


if __name__ == '__main__':
    print(f'm1={m1*1e3:.1f} г a1={a1/LDU:.0f} LDU I1={I1:.2e}; m2={m2*1e3:.1f} г a2={a2/LDU:.0f} LDU I2c={I2c:.2e}')
    import sys
    t1 = np.radians(float(sys.argv[1])) if len(sys.argv) > 1 else np.radians(165)
    t2 = np.radians(float(sys.argv[2])) if len(sys.argv) > 2 else np.radians(150)
    S = simulate(t1, t2, 14)
    E = [energy(s) for s in S]
    print('макс |w1|, |w2| рад/с:', np.abs(S[:, 2]).max().round(1), np.abs(S[:, 3]).max().round(1))
    print('энергия: начало', round(E[0] * 1e3, 3), 'мДж, конец', round(E[-1] * 1e3, 3))
    turns1 = np.abs(np.diff(S[:, 0])).sum() / (2 * np.pi); turns2 = np.abs(np.diff(S[:, 1])).sum() / (2 * np.pi)
    print('обороты (путь угла): звено1', round(turns1, 1), 'звено2', round(turns2, 1))
    for sec in range(0, 15, 2):
        s = S[sec * 30]; print(f'  t={sec:2d}s th1={np.degrees(s[0]):8.0f} th2={np.degrees(s[1]):8.0f}')
