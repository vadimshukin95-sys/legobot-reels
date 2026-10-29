"""Картинка для ВК 1080×1350 (два варианта макета) из стоп-кадра Blender: python vk.py still.png out_dir"""
import os, sys, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import pila_model as M, timeline as TL, reelkit as K

W, H = 1080, 1350
TH, DIST = 50, 585
RED = (236, 72, 58)
la, lo = np.radians(TL.CAM['lat']), np.radians(TL.CAM['lon'])
_tg = np.array(TL.CAM['target'], float)
_eye = _tg + DIST * np.array([np.sin(lo) * np.cos(la), -np.sin(la), -np.cos(lo) * np.cos(la)])
VP = TL.perspective(TL.CAM['fov'], TL.PLATE_W / TL.PLATE_H) @ TL.look_at(_eye, _tg)
mod = Image.open(sys.argv[1]).convert('RGBA').resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
mod = K.soften_plate(mod.crop((0, 60, 1080, 640)), feather=90)   # поля сверху/снизу убраны, тень гаснет к краям
OFF = (0, -60)
LOGO = K.logo_round(size=104)


def P(pts, my):
    return K.project(VP, pts, TL.PLATE_W, TL.PLATE_H) + [OFF[0], OFF[1] + my]


def fit(d, text, wmax, size, w='black'):
    while size > 30 and d.textlength(text, font=K.font(size, w)) > wmax:
        size -= 2
    return K.font(size, w)


def spaced(d, xy, text, f, fill, track=6):
    x, y = xy
    for ch in text:
        d.text((x, y), ch, font=f, fill=fill); x += d.textlength(ch, font=f) + track


def dashed_circle(d, my):
    ang = np.radians(np.arange(0, 361, 3))
    pts = P(np.c_[M.XK + M.R_CRANK * np.cos(ang), M.YK - M.R_CRANK * np.sin(ang), np.full(len(ang), -61)], my)
    for k in range(0, len(pts) - 1):
        if (k // 2) % 2 == 0:
            d.line([tuple(pts[k]), tuple(pts[k + 1])], fill=RED, width=6)
    pin, J = M.kin(TH)
    c = P([[pin[0], pin[1], -61]], my)[0]
    d.ellipse((c[0] - 11, c[1] - 11, c[0] + 11, c[1] + 11), fill=RED, outline=(255, 255, 255), width=3)
    return c


def saw_arrow(d, my, y=-116):
    xs = M.kin(TH)[1][0]
    (x1, y1), (x2, y2) = P([[xs - 112, y, -40], [xs + 4, y, -40]], my)
    d.line([(x1 + 18, y1), (x2 - 18, y2)], fill=RED, width=9)
    for (xa, ya), s in (((x1, y1), 1), ((x2, y2), -1)):
        d.polygon([(xa, ya), (xa + s * 30, ya - 17), (xa + s * 30, ya + 17)], fill=RED)


def base(bg=(248, 248, 245)):
    im = Image.new('RGBA', (W, H), bg + (255,))
    return im


def header(im, over='МЕХАНИЗМЫ · КРИВОШИП'):
    d = ImageDraw.Draw(im)
    im.alpha_composite(LOGO, (W - 104 - 48, 44))
    spaced(d, (60, 70), over, K.font(26, 'b'), (120, 124, 128), track=5)
    f1 = fit(d, 'Как колесо', 900, 96)
    d.text((58, 112), 'Как колесо', font=f1, fill=K.INK)
    f2 = fit(d, 'превращается в пилу', 960, 96)
    d.text((58, 112 + f1.size + 6), 'превращается в пилу', font=f2, fill=K.LIME)
    return 112 + f1.size + 6 + f2.size


def put_model(im, my):
    im.alpha_composite(mod, (0, my))


def num_badge(d, cx, cy, n, r=30, col=K.LIME):
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=col)
    d.text((cx, cy + 1), str(n), font=K.font(36, 'black'), fill=K.INK, anchor='mm')


# ---------- Вариант 1: «Памятка» — три плашки-шага внизу ----------
def v1():
    im = base(); d = ImageDraw.Draw(im)
    y = header(im)
    my = y + 40
    put_model(im, my)
    dashed_circle(d, my); saw_arrow(d, my)
    steps = [('Мотор крутит\nколесо', 1), ('Палец ходит\nпо кругу', 2), ('Шатун толкает\nпилу туда-сюда', 3)]
    top = 1010; cw = 312; gap = 22; x0 = (W - 3 * cw - 2 * gap) // 2
    for k, (t, n) in enumerate(steps):
        x = x0 + k * (cw + gap)
        d.rounded_rectangle((x, top, x + cw, top + 190), 24, fill=(255, 255, 255), outline=(228, 230, 226), width=2)
        num_badge(d, x + 50, top + 52, n)
        d.multiline_text((x + 28, top + 96), t, font=K.font(31, 'xb'), fill=K.INK, spacing=6)
    d.rounded_rectangle((60, 1236, 60 + 520, 1236 + 64), 20, fill=K.SUN)
    d.text((60 + 260, 1236 + 33), 'Круг → туда-сюда', font=K.font(34, 'black'), fill=K.INK, anchor='mm')
    d.text((W - 60, 1268), 'legobot.ru', font=K.font(34, 'xb'), fill=K.LEAF, anchor='rm')
    return im


# ---------- Вариант 2: «Схема с выносками» ----------
def v2():
    im = base((244, 246, 248)); d = ImageDraw.Draw(im)
    y = header(im)
    my = y + 70
    put_model(im, my)
    c = dashed_circle(d, my); saw_arrow(d, my)
    pin, J = M.kin(TH)
    motor = P([[M.XK, -20, -10]], my)[0]
    rod = P([[(pin[0] + J[0]) / 2, (pin[1] + J[1]) / 2, -50]], my)[0]
    saw = P([[J[0] - 80, -100, -40]], my)[0]
    pts = [(motor, (95, 120)), (c, (70, -95)), (rod, (-40, -120)), (saw, (-30, 150))]
    for k, (pt, (dx, dy)) in enumerate(pts):
        bx, by = pt[0] + dx, pt[1] + dy
        bx = min(max(bx, 50), W - 50)
        d.line([tuple(pt), (bx, by)], fill=K.INK, width=3)
        d.ellipse((pt[0] - 7, pt[1] - 7, pt[0] + 7, pt[1] + 7), fill=K.INK)
        num_badge(d, bx, by, k + 1, r=30)
    leg = ['Мотор крутит колесо', 'Палец ходит по кругу', 'Шатун толкает пилу', 'Пила ходит туда-сюда']
    for k, t in enumerate(leg):
        x = 70 + (k % 2) * 480; yy = 1010 + (k // 2) * 78
        num_badge(d, x + 28, yy + 26, k + 1, r=26)
        d.text((x + 70, yy + 26), t, font=K.font(32, 'xb'), fill=K.INK, anchor='lm')
    d.rounded_rectangle((60, 1210, W - 60, 1300), 26, fill=K.INK)
    d.text((W / 2, 1255), 'Это кривошип: круг превращается в «туда-сюда»', font=fit(d, 'Это кривошип: круг превращается в «туда-сюда»', W - 180, 36, 'xb'), fill=(255, 255, 255), anchor='mm')
    return im


A, B = v1(), v2()
out = sys.argv[2] if len(sys.argv) > 2 else '.'
os.makedirs(out, exist_ok=True)
A.convert('RGB').save(os.path.join(out, 'vk_1_pamyatka.jpg'), quality=94)
B.convert('RGB').save(os.path.join(out, 'vk_2_shema.jpg'), quality=94)
print('vk ok')
