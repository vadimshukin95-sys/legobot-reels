"""«Кувырки». Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок, подписи-стикеры,
номера плашек, значок «замедленно» и финальная карточка с логотипом.
python overlay_k.py <папка плашек f0001.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "pila"))
import timeline_k as TL, kuvyrki_model as KM, reelkit as K

BG = K.bg_studio().convert('RGBA')
STICK, TITLE, CARD, BADGE = {}, None, None, {}


def pop(u):
    if u <= 0: return 0
    if u >= 1: return 1
    return 1 + 0.08 * math.sin(u * math.pi) if u > 0.55 else TL.ease_out(u / 0.55) * 1.04


def paste_scaled(img, src, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01: return
    w, h = max(1, int(src.width * s)), max(1, int(src.height * s))
    im = src.resize((w, h), Image.LANCZOS)
    if alpha < 1: im.putalpha(im.split()[-1].point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def sticker_img(text, style):
    key = (text, style)
    if key not in STICK:
        im = Image.new('RGBA', (1080, 600), (0, 0, 0, 0))
        if style == 'sun':
            K.sticker(im, 540, 300, text, K.font(58, 'xb'), K.SUN, K.INK, tilt=-2)
        elif style == 'big':
            K.sticker(im, 540, 300, text, K.font(70, 'black'), K.LIME, K.INK, pad=(44, 24), radius=34, tilt=1)
        else:
            K.sticker(im, 540, 300, text, K.font(46, 'xb'), (255, 255, 255), K.INK, pad=(26, 14), radius=22)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in TL.TITLE:
            im = Image.new('RGBA', (1400, 200), (0, 0, 0, 0))
            K.tracked(im, (700, 30), line, K.font(78), (255, 255, 255), K.INK, 6, track=3, shadow=((35, 41, 44), (0, 10)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def draw_title(img, t):
    for k, im in enumerate(title_img()):
        u = (t - 0.1 - 0.16 * k) / 0.35
        paste_scaled(img, im, 540, 140 + k * 94 + im.height / 2 - 30, pop(u))


def badge(n):
    if n not in BADGE:
        im = Image.new('RGBA', (120, 120), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.ellipse((6, 10, 114, 118), fill=(30, 36, 40, 90))
        d.ellipse((4, 4, 112, 112), fill=K.INK + (255,), outline=(255, 255, 255, 255), width=6)
        f = K.font(64, 'black'); w = d.textlength(str(n), font=f)
        d.text((58 - w / 2, 18), str(n), font=f, fill=(255, 255, 255))
        BADGE[n] = im
    return BADGE[n]


def draw_badges(img, t):
    a, b = TL.BADGES
    if not (a <= t < b + 0.3): return
    al = 1.0 if t < b else max(0, 1 - (t - b) / 0.3)
    for k in range(3):
        x0 = -KM.PITCH * k * 20 - 10
        p = TL.project([[x0, 300, -125]])[0]
        paste_scaled(img, badge(k + 1), p[0], p[1], 0.62 * pop((t - a - 0.12 * k) / 0.3), al)


def draw_slow(img, t):
    for a, b in TL.SLOW:
        if a <= t < b:
            al = min(1, (t - a) / 0.2, (b - t) / 0.2)
            paste_scaled(img, sticker_img('замедленно', 'white'), 870, 500, 1.0, al)


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, 1690, pop((t - a) / 0.3), al)


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
        if TL.PLATE_FIRST <= i <= TL.PLATE_LAST:
            pl = Image.open(os.path.join(plates, f'f{i - TL.PLATE_FIRST + 1:04d}.png')).convert('RGBA')
            if pl.size != (TL.PLATE_W, TL.PLATE_H): pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
            img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
        draw_badges(img, t); draw_slow(img, t); draw_title(img, t); draw_caps(img, t)
        ImageDraw.Draw(img).text((40, 1858), 'legobot.ru', font=K.font(34, 'b'), fill=K.INK)
    if t >= TL.T_CARD:
        c = card(); u = min(1, (t - TL.T_CARD) / TL.CARD_FADE)
        if u < 1: c = c.copy(); c.putalpha(c.split()[-1].point(lambda v: int(v * u)))
        img.alpha_composite(c)
    return img.convert('RGB')


if __name__ == '__main__':
    plates, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3:
        for i in map(int, sys.argv[3].split(',')):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
    else:
        last = None
        for i in range(TL.FRAMES):
            if i / TL.FPS >= TL.T_CARD + TL.CARD_FADE:
                last = last or frame(i, plates); last.save(os.path.join(out, f'o{i:04d}.png'))
            else:
                frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
            if i % 60 == 0: print('overlay', i, flush=True)
        Image.open(os.path.join(out, 'o0462.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
