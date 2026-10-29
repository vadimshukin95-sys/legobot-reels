"""Сценарий «Мотоцикла» без Blender: сдвиг вдоль хода и углы осей.
Координаты LDraw (y вниз), мотоцикл смотрит в −z. pos — сдвиг по z (плюс — назад), в начале петли pos = +stroke/2.
Колёса катятся без проскальзывания; передачи по резинкам: заднее колесо ← полувтулка (r 9.5) ← шкив средней оси (r 22);
средняя ось ← ось мотора (полувтулки r 9 на обеих)."""
import math


class Motion:
    def __init__(self, lay):
        self.L = lay
        self.S = lay['stroke']; self.ramp = lay['ramp']
        self.drives = lay['drives']
        self.R = lay['level']['tyre_r']
        P = lay['pulleys']
        self.k_mid = P['rear_small_r'] / P['mid_big_r']           # средняя ось медленнее заднего колеса
        self.k_motor = self.k_mid * P['mid_small_r'] / P['motor_r']

    def prof(self, u, f):
        """Трапеция скорости: разгон f, ход, торможение f; u, результат — 0..1."""
        u = max(0.0, min(1.0, u)); v = 1.0 / (1.0 - f)
        if u < f: return 0.5 * v * u * u / f
        if u > 1 - f: return 1.0 - 0.5 * v * (1 - u) ** 2 / f
        return v * (f / 2 + (u - f))

    def pos(self, t):
        p = self.S / 2
        for t0, t1, sgn in self.drives:
            if t <= t0: break
            u = (t - t0) / (t1 - t0); f = self.ramp / (t1 - t0)
            p -= sgn * self.S * self.prof(u, f)
        return p

    def level(self):
        """Наклон модели вокруг x (рад) и подъём, чтобы оба колеса стояли на полу y = 0."""
        (yf, zf), (yr, zr) = self.L['level']['front'], self.L['level']['rear']
        a = math.atan2(yr - yf, zr - zf)
        y = yf * math.cos(a) - zf * math.sin(a)
        return a, y + self.R

    def belts(self):
        """Две резинки (в координатах модели): 1 — с перекрутом на четверть оборота, 2 — плоская."""
        P = self.L['pulleys']; ax = self.L['axes']
        out = []
        # 1: ось мотора (наклонная) -> ролик из полувтулок на средней оси
        c1 = P['motor_c']; r1 = P['motor_r']; d = ax['motor']['d']
        u = (1.0, 0.0, 0.0); w = (0.0, d[2], -d[1])                 # w = d x u (в плоскости yz, к низу)
        c2 = ax['mid']['c']; r2 = P['mid_small_r']; xa, xb = P['belt1_x'][1], P['belt1_x'][0]
        dy, dz = c1[1] - c2[1], c1[2] - c2[2]; n = math.hypot(dy, dz); dy, dz = dy / n, dz / n
        front = (c2[1] + r2 * dz, c2[2] - r2 * dy); back = (c2[1] - r2 * dz, c2[2] + r2 * dy)
        pts = []
        for k in range(13):                                          # верх: вокруг оси мотора, от x=69 к x=51
            th = math.pi * k / 12
            pts.append((c1[0] + r1 * math.cos(th), c1[1] - r1 * math.sin(th) * w[1], c1[2] - r1 * math.sin(th) * w[2]))
        a0 = math.atan2(back[0] - c2[1], back[1] - c2[2]); a1 = math.atan2(front[0] - c2[1], front[1] - c2[2])
        if a1 < a0: a1 += 2 * math.pi
        if math.sin((a0 + a1) / 2) < 0: a1 -= 2 * math.pi              # дуга должна идти под роликом (y больше)
        for k in range(13):                                          # низ: под роликом, от задней точки к передней
            a = a0 + (a1 - a0) * k / 12; x = xb + (xa - xb) * k / 12
            pts.append((x, c2[1] + r2 * math.sin(a), c2[2] + r2 * math.cos(a)))
        out.append(pts)
        # 2: шкив средней оси -> полувтулка заднего колеса, в плоскости x = belt2_x
        x = P['belt2_x']; A = (ax['mid']['c'][1], ax['mid']['c'][2], P['mid_big_r']); B = (ax['rear']['c'][1], ax['rear']['c'][2], P['rear_small_r'])
        dz_, dy_ = B[1] - A[1], B[0] - A[0]; L = math.hypot(dz_, dy_); phi = math.atan2(dy_, dz_)
        beta = math.acos((A[2] - B[2]) / L)
        pts = []
        for (cy, cz, r), a_from, a_to in ((A, phi + beta, phi + 2 * math.pi - beta), (B, phi - beta, phi + beta)):
            for k in range(25):
                a = a_from + (a_to - a_from) * k / 24
                pts.append((x, cy + r * math.sin(a), cz + r * math.cos(a)))
        out.append(pts)
        return out

    def state(self, t):
        z = self.pos(t)
        travel = self.S / 2 - z                                     # пройдено вперёд (−z), со знаком
        wheel = travel / self.R                                     # угол колёс вокруг x (плюс — качение вперёд)
        return dict(z=z, wheel=wheel, mid=wheel * self.k_mid, motor=wheel * self.k_motor)
