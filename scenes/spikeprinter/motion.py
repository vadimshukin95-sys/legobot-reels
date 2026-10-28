"""Сценарий «3D-принтера» без Blender: положение стола, головки, каретки, рычага кнопки и длина напечатанной нити.
Координаты LDraw (y вниз). Стол едет по X, головка по Z, каретка с ручкой по Y.
bx — сдвиг стола, hz — сдвиг головки, cy — сдвиг каретки (минус — вверх), lever — угол рычага (рад), s — длина нити, alpha — видимость отпечатка."""
import math


class Motion:
    def __init__(self, lay):
        self.L = lay
        pen, pr = lay['pen'], lay['print']
        self.px, self.pz = pen['axis']                      # ось ручки в мире при нулевых сдвигах
        self.y0 = pen['tip_y']                              # высота кончика (= центр первого слоя) при cy = 0
        self.size, self.n, self.h = pr['size'], pr['layers'], pr['layer_h']
        self.cx, self.cz = pr['center']                     # центр квадрата в координатах стола
        self.per = 4 * self.size
        self.S = self.per * self.n
        self.raise_ = lay['raise']
        self.lever = math.radians(lay['lever_deg'])
        self.T = lay['times']
        h = self.size / 2
        self.corners = [(self.cx - h, self.cz - h), (self.cx + h, self.cz - h), (self.cx + h, self.cz + h), (self.cx - h, self.cz + h)]

    def point(self, s):
        """Точка нити (координаты стола) на длине s: квадрат по спирали, каждый круг выше на layer_h."""
        s = max(0.0, min(self.S, s))
        u = s % self.per if s < self.S else self.per
        k = min(3, int(u // self.size)); f = (u - k * self.size) / self.size
        (x0, z0), (x1, z1) = self.corners[k], self.corners[(k + 1) % 4]
        y = self.y0 - self.h * s / self.per
        return (x0 + (x1 - x0) * f, y, z0 + (z1 - z0) * f)

    def path(self, step=4.0):
        pts, s = [], 0.0
        while s < self.S:
            pts.append(self.point(s)); s += step
        pts.append(self.point(self.S))
        return pts

    def axes_for(self, p):
        """Сдвиги стола/головки/каретки, при которых кончик ручки в точке p (координаты стола)."""
        return self.px - p[0], p[2] - self.pz, p[1] - self.y0

    @staticmethod
    def ease(x):
        x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)

    def k(self, name, t):
        a, b = self.T[name]; return self.ease((t - a) / (b - a))

    def state(self, t):
        T = self.T
        start = self.axes_for(self.point(0)); end = self.axes_for(self.point(self.S))
        top = end[2] - self.raise_                          # над готовой рамкой
        rest = -self.raise_                                 # «дом»: ручка поднята
        if t < T['print'][0]:
            m, d = self.k('move_in', t), self.k('down', t)
            bx, hz = start[0] * m, start[1] * m
            cy = rest + (start[2] - rest) * d
            s = 0.0
        elif t < T['print'][1]:
            a, b = T['print']
            s = self.S * (t - a) / (b - a)
            bx, hz, cy = self.axes_for(self.point(s))
        else:
            s = self.S
            u, hm, st = self.k('up', t), self.k('home', t), self.k('settle', t)
            bx, hz = end[0] * (1 - hm), end[1] * (1 - hm)
            cy = end[2] + (top - end[2]) * u
            cy = cy + (rest - top) * st
        lever = self.lever * (self.k('press', t) - self.k('release', t))
        alpha = 1.0 - self.k('fade', t)
        return dict(bx=bx, hz=hz, cy=cy, lever=lever, s=s, alpha=alpha)
