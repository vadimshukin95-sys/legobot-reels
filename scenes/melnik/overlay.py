"""Сборка кадров рилса «Кто кого крутит?»: фон «Студия», плашка модели из Blender (с тенью), заголовок, подписи-стикеры,
волны датчика, путь пальца и дуга поворота мельника (по камере timeline.VP_at) и финальная карточка курса.
python overlay.py <папка плашек f0001.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE); sys.path.insert(1, os.path.join(HERE, '..', 'pila'))
import timeline as TL, melnik_model as M, reelkit as K

RED = (236, 72, 58)
BLUE = (40, 150, 225)
BG = K.bg_studio().convert('RGBA')
STICK, TITLE, CARD = {}, None, None
CAP_Y = 1690
Y_PIN = -172            # высота пальца/руки для стрелок (верх стойки пальца)


def pop(u):
    if u <= 0:
        return 0
    if u >= 1:
        return 1
    return 1 + 0.08 * math.sin(u * math.pi) if u > 0.55 else (1 - (1 - u / 0.55) ** 3) * 1.04


def paste_scaled(img, src, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01:
        return
    w, h = max(1, int(src.width * s)), max(1, int(src.height * s))
    im = src.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.split()[-1].point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def sticker_img(text, style):
    key = (text, style)
    if key not in STICK:
        im = Image.new('RGBA', (1080, 600), (0, 0, 0, 0))
        if style == 'sun':
            K.sticker(im, 540, 300, text, K.font(58, 'xb'), K.SUN, K.INK, tilt=-2)
        elif style == 'big':
            K.sticker(im, 540, 300, text, K.font(80, 'black'), K.LIME, K.INK, pad=(44, 24), radius=34, tilt=1)
        else:
            K.sticker(im, 540, 300, text, K.font(52, 'xb'), (255, 255, 255), K.INK)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in ['КТО КОГО', 'КРУТИТ?']:
            im = Image.new('RGBA', (1080, 200), (0, 0, 0, 0))
            K.tracked(im, (540, 30), line, K.font(118), (255, 255, 255), K.INK, 6, track=5, shadow=((35, 41, 44), (0, 12)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def draw_title(img, t):
    for k, im in enumerate(title_img()):
        u = (t - 0.15 - 0.18 * k) / 0.35
        paste_scaled(img, im, 540, 170 + k * 138 + im.height / 2 - 40, pop(u))


def dashed(d, pts, col, w=7, on=2):
    for k in range(0, len(pts) - 1):
        if (k // on) % 2 == 0:
            d.line([tuple(pts[k]), tuple(pts[k + 1])], fill=col, width=w)


def arrowhead(d, tip, direction, col, size=30):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip); d.polygon([tuple(a), tuple(a - v * size + n * size * 0.6), tuple(a - v * size - n * size * 0.6)], fill=col)


def sensor_waves(d, t, th):
    a, b = TL.SENSOR
    if not (a <= t < b + 0.3):
        return
    phi = M.kin(th)[0]
    R = M.rot_y(phi)
    face = np.array([M.TX, 0, M.TZ]) + R @ np.array([-14, -200, 0])     # перед «глазами» датчика
    ahead = np.array([M.TX, 0, M.TZ]) + R @ np.array([-60, -200, 0])
    c, f = TL.project(t, [face, ahead])
    v = f - c; v /= np.linalg.norm(v); base = math.degrees(math.atan2(v[1], v[0]))
    fade = 1.0 if t < b else max(0, 1 - (t - b) / 0.3)
    for k in range(3):
        ph = ((t - a) * 1.4 + k / 3) % 1.0
        r = 34 + ph * 150
        al = int(255 * fade * (1 - ph) ** 1.2)
        d.arc((c[0] - r, c[1] - r, c[0] + r, c[1] + r), base - 38, base + 38, fill=BLUE + (al,), width=11)


def mech_overlays(img, t, th):
    if not (TL.T_TOP0 + 0.6 <= t < TL.T_X0):
        return
    fade = min(1, (t - TL.T_TOP0 - 0.6) / 0.4) * (1 if t < TL.T_X0 - 0.25 else max(0, (TL.T_X0 - t) / 0.25))
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if t >= 8.3:                                               # путь пальца + точка
        ang = np.radians(np.arange(0, 361, 3))
        pts = TL.project(t, np.c_[M.MX + M.R_CRANK * np.cos(ang), np.full(len(ang), Y_PIN), M.MZ - M.R_CRANK * np.sin(ang)])
        n = max(2, int(len(pts) * min(1, (t - 8.3) / 1.0)))
        dashed(d, pts[:n], RED + (255,), 9, 2)
        P = M.crank(th)
        c = TL.project(t, [[P[0], Y_PIN, P[1]]])[0]
        d.ellipse((c[0] - 17, c[1] - 17, c[0] + 17, c[1] + 17), fill=RED + (255,), outline=(255, 255, 255, 255), width=4)
    if t >= 9.6:                                               # дуга поворота мельника ±30°
        R0 = 72
        ang = np.radians(np.linspace(-30, 30, 40))
        # мельник поворачивается на ±30°: дуга перед ним (сторона -Z, к зрителю) на высоте плеч
        pts = TL.project(t, np.c_[M.TX + R0 * np.sin(ang), np.full(len(ang), -165), M.TZ - R0 * np.cos(ang)])
        u = min(1, (t - 9.6) / 0.5)
        k = max(2, int(len(pts) * u))
        mid = len(pts) // 2
        seg = pts[max(0, mid - k // 2): mid + k // 2 + 1]
        d.line([tuple(p) for p in seg], fill=RED + (255,), width=12, joint='curve')
        if u >= 1:
            arrowhead(d, pts[0], pts[0] - pts[3], RED + (255,), 38)
            arrowhead(d, pts[-1], pts[-1] - pts[-4], RED + (255,), 38)
    if fade < 1:
        lay.putalpha(lay.split()[-1].point(lambda v: int(v * fade)))
    img.alpha_composite(lay)


def xray_tag(img, t):
    if TL.T_X0 + 0.2 <= t < TL.T_X1:
        d = ImageDraw.Draw(img)
        txt = 'замедлено ×4'
        f = K.font(34, 'b')
        w = d.textlength(txt, font=f)
        d.rounded_rectangle((1040 - w - 32, 486, 1040, 540), 18, fill=(35, 41, 44, 200))
        d.text((1040 - w - 16, 494), txt, font=f, fill=(255, 255, 255))


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, CAP_Y, pop((t - a) / 0.3), al)


def card():
    global CARD
    if CARD is None:
        im = K.bg_studio().convert('RGBA')
        im = Image.alpha_composite(im, Image.new('RGBA', im.size, (255, 255, 255, 90)))
        lg = K.logo_round(size=380)
        sh = Image.new('RGBA', (470, 470), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((45, 60, 425, 440), fill=(30, 40, 60, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        cy = 560
        im.alpha_composite(sh, (540 - 235, cy - 200)); im.alpha_composite(lg, (540 - 190, cy - 190))
        K.outlined(im, (540, 830), 'Курс', K.font(56, 'xb'), K.INK, K.INK, 0)
        K.outlined(im, (540, 905), 'Инженерная мастерская\nWeDo 2.0', K.font(84, 'black'), K.INK, K.INK, 0, spacing=10)
        K.outlined(im, (540, 1125), '36 занятий · 12 моделей · 2–4 класс', K.font(48, 'sb'), (70, 78, 84), (70, 78, 84), 0)
        K.sticker(im, 540, 1300, 'Занятие 1 — бесплатно', K.font(70, 'black'), K.LIME, K.INK, pad=(44, 24), radius=34, tilt=-1)
        K.tracked(im, (540, 1450), 'legobot.ru', K.font(124), (255, 255, 255), K.LEAF, 7, track=4, shadow=((40, 90, 30), (0, 10)))
        CARD = im
    return CARD


def frame(i, plates):
    t = i / TL.FPS
    img = BG.copy()
    if t < TL.T_CARD + TL.CARD_FADE:
        th = TL.theta_at(t)
        if TL.PLATE_FIRST <= i <= TL.PLATE_LAST:
            pl = Image.open(os.path.join(plates, f'f{i - TL.PLATE_FIRST + 1:04d}.png')).convert('RGBA')
            if pl.size != (TL.PLATE_W, TL.PLATE_H):
                pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
            img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        sensor_waves(ImageDraw.Draw(lay), t, th)
        img.alpha_composite(lay)
        mech_overlays(img, t, th)
        xray_tag(img, t)
        draw_title(img, t)
        draw_caps(img, t)
        ImageDraw.Draw(img).text((40, 1858), 'legobot.ru', font=K.font(34, 'b'), fill=K.INK)
    if t >= TL.T_CARD:
        c = card()
        u = min(1, (t - TL.T_CARD) / TL.CARD_FADE)
        if u < 1:
            c = c.copy(); c.putalpha(c.split()[-1].point(lambda v: int(v * u)))
        img.alpha_composite(c)
    return img.convert('RGB')


if __name__ == '__main__':
    plates, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3:                       # только отдельные кадры (тест)
        for i in map(int, sys.argv[3].split(',')):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
    else:
        last = None
        for i in range(TL.FRAMES):
            if i / TL.FPS >= TL.T_CARD + TL.CARD_FADE:
                last = last or frame(i, plates)
                last.save(os.path.join(out, f'o{i:04d}.png'))
            else:
                frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
            if i % 60 == 0:
                print('overlay', i, flush=True)
        # обложка рилса — кадр «Нет! Это жернов крутит мельника» (переезд камеры сверху)
        Image.open(os.path.join(out, 'o0240.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
