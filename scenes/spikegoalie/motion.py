"""Сценарий «Вратаря» без Blender: угол мотора, положение тяги и вратаря, путь мяча.
Координаты LDraw (y вниз). Мотор качает рычаг вокруг своей оси (ось вдоль z), низ рычага тянет зелёную балку,
второй конец балки на штифте у вратаря; вратарь стоит на полу и скользит по x, балка при этом наклоняется.
theta — угол рычага (плюс — низ рычага уходит в +x), градусы."""
import math


def ease(x):
    x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)


class Motion:
    def __init__(self, lay):
        m = lay['mech']
        self.PX, self.PY = m['pivot']
        self.LEV, self.BEAM = m['lever'], m['beam']
        self.L0 = tuple(m['beam_end0'])
        self.K0 = tuple(m['keeper_pin0'])
        self.lift = m['keeper_lift']
        self.KY = self.K0[1] - self.lift                    # высота штифта вратаря, когда он стоит на полу
        self.legx = m['leg']
        self.keys = lay['keeper_deg']
        self.B = lay['ball']; self.shots = lay['shots']

    def theta(self, t):
        k = self.keys
        if t <= k[0][0]: return k[0][1]
        for (t0, a0), (t1, a1) in zip(k[:-1], k[1:]):
            if t0 <= t <= t1:
                return a0 + (a1 - a0) * ease((t - t0) / (t1 - t0)) if t1 > t0 else a1
        return k[-1][1]

    def kin(self, deg):
        """Низ рычага L, штифт вратаря K, угол балки phi (рад, поворот вокруг z LDraw), сдвиг вратаря."""
        th = math.radians(deg)
        lx, ly = self.PX + self.LEV * math.sin(th), self.PY + self.LEV * math.cos(th)
        dy = ly - self.KY
        kx = lx - math.sqrt(self.BEAM ** 2 - dy ** 2)
        phi = math.atan2(self.KY - ly, kx - lx) - math.atan2(self.K0[1] - self.L0[1], self.K0[0] - self.L0[0])
        phi = (phi + math.pi) % (2 * math.pi) - math.pi
        return dict(L=(lx, ly), K=(kx, self.KY), phi=phi, shift=(kx - self.K0[0], self.KY - self.K0[1]), lever=-th)

    def ball(self, t):
        """Положение центра мяча (x, z), видимость 0..1 и номер удара (или None)."""
        B = self.B; sx, sz = B['spot']
        for i, s in enumerate(self.shots):
            if not (s['appear'] <= t <= s['end']):
                continue
            kc = self.kin(self.theta(s['contact']))['K'][0]
            cx, cz = kc + s['leg'] * self.legx, B['contact_z']
            dx, dz = cx - sx, cz - sz; d = math.hypot(dx, dz); ux, uz = dx / d, dz / d
            rx, rz = ux * 0.5, -uz; rn = math.hypot(rx, rz); rx, rz = rx / rn, rz / rn   # отскок: назад и чуть в сторону
            if t < s['kick']:
                x, z = sx, sz
            elif t < s['contact']:
                p = (t - s['kick']) / (s['contact'] - s['kick']); u = p * (1.3 - 0.3 * p)
                x, z = sx + dx * u, sz + dz * u
            else:
                q = (t - s['contact']) / (s['end'] - s['contact']); u = 1 - (1 - q) ** 2
                x, z = cx + rx * B['rebound'] * u, cz + rz * B['rebound'] * u
            a = min(1.0, (t - s['appear']) / B['fade'], (s['end'] - t) / (B['fade'] * 1.25))
            return x, z, max(0.0, a), i
        return None, None, 0.0, None
