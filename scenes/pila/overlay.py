"""Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок, подписи-стикеры,
стрелки поверх механизма (по камере timeline.VP_at) и финальная карточка с логотипом.
python overlay.py <папка плашек f0001.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import timeline as TL, pila_model as M, reelkit as K

RED = (236, 72, 58)
BG = K.bg_studio().convert('RGBA')
STICK, TITLE, CARD = {}, None, None


def pop(u):
    if u <= 0:
        return 0
    if u >= 1:
        return 1
    return 1 + 0.08 * math.sin(u * math.pi) if u > 0.55 else TL.ease_out(u / 0.55) * 1.04


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
            K.sticker(im, 540, 300, text, K.font(60, 'xb'), K.SUN, K.INK, tilt=-2)
        elif style == 'big':
            K.sticker(im, 540, 300, text, K.font(88, 'black'), K.LIME, K.INK, pad=(46, 26), radius=34, tilt=1)
        else:
            K.sticker(im, 540, 300, text, K.font(52, 'xb'), (255, 255, 255), K.INK)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in ['КАК КОЛЕСО', 'ПРЕВРАЩАЕТСЯ', 'В ПИЛУ?']:
            im = Image.new('RGBA', (1080, 200), (0, 0, 0, 0))
            K.tracked(im, (540, 30), line, K.font(104), (255, 255, 255), K.INK, 6, track=5, shadow=((35, 41, 44), (0, 12)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def draw_title(img, t):
    for k, im in enumerate(title_img()):
        u = (t - 0.15 - 0.18 * k) / 0.35
        paste_scaled(img, im, 540, 205 + k * 122 + im.height / 2 - 40, pop(u))


def dashed(d, pts, col, w=7, on=2):
    for k in range(0, len(pts) - 1):
        if (k // on) % 2 == 0:
            d.line([tuple(pts[k]), tuple(pts[k + 1])], fill=col, width=w)


def arrowhead(d, tip, direction, col, size=30):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip); d.polygon([tuple(a), tuple(a - v * size + n * size * 0.6), tuple(a - v * size - n * size * 0.6)], fill=col)


def overlays(img, t, th):
    if t < TL.T_RUN:
        return
    fade = 1.0 if t <= TL.T_FAST else max(0, 1 - (t - TL.T_FAST) / 0.5)
    if fade <= 0:
        return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    if TL.T_RUN <= t < 6.9:                                    # стрелка вращения вокруг колеса
        ang = np.radians(th) + np.radians(np.linspace(20, 290, 40)); r = 36
        pts = TL.project(t, np.c_[M.XK + r * np.cos(ang), M.YK - r * np.sin(ang), np.full(len(ang), -62)])
        d.line([tuple(p) for p in pts], fill=RED + (255,), width=9, joint='curve')
        arrowhead(d, pts[-1], pts[-1] - pts[-4], RED + (255,), 30)
    if t >= 6.7:                                               # путь пальца + точка
        ang = np.radians(np.arange(0, 361, 3))
        pts = TL.project(t, np.c_[M.XK + M.R_CRANK * np.cos(ang), M.YK - M.R_CRANK * np.sin(ang), np.full(len(ang), -61)])
        n = max(2, int(len(pts) * min(1, (t - 6.7) / 1.2)))
        dashed(d, pts[:n], RED + (255,), 7, 2)
        P, _ = M.kin(th)
        c = TL.project(t, [[P[0], P[1], -61]])[0]
        d.ellipse((c[0] - 13, c[1] - 13, c[0] + 13, c[1] + 13), fill=RED + (255,), outline=(255, 255, 255, 255), width=4)
    if t >= 8.4:                                               # двойная стрелка хода пилы
        xs = M.kin(th)[1][0]
        (x1, y1), (x2, y2) = TL.project(t, [[xs - 112, -116, -40], [xs + 4, -116, -40]])
        d.line([(x1 + 20, y1), (x2 - 20, y2)], fill=RED + (255,), width=11)
        arrowhead(d, (x1, y1), (x1 - x2, y1 - y2), RED + (255,), 36)
        arrowhead(d, (x2, y2), (x2 - x1, y2 - y1), RED + (255,), 36)
    if fade < 1:
        lay.putalpha(lay.split()[-1].point(lambda v: int(v * fade)))
    img.alpha_composite(lay)


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, 1540, pop((t - a) / 0.3), al)


def card():
    global CARD
    if CARD is None:
        im = K.bg_studio().convert('RGBA')
        im = Image.alpha_composite(im, Image.new('RGBA', im.size, (255, 255, 255, 90)))
        lg = K.logo_round(size=470)
        sh = Image.new('RGBA', (560, 560), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((45, 60, 515, 530), fill=(30, 40, 60, 70))
        sh = sh.filter(ImageFilter.GaussianBlur(16))
        im.alpha_composite(sh, (540 - 280, 760 - 245)); im.alpha_composite(lg, (540 - 235, 760 - 235))
        K.outlined(im, (540, 1100), 'Больше механизмов —', K.font(70, 'xb'), K.INK, K.INK, 0)
        K.tracked(im, (540, 1200), 'legobot.ru', K.font(124), (255, 255, 255), K.LEAF, 7, track=4, shadow=((40, 90, 30), (0, 10)))
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
            img.alpha_composite(pl, (0, TL.MY))
        overlays(img, t, th)
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
        # обложка рилса — кадр «Это кривошип»
        Image.open(os.path.join(out, 'o0315.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
