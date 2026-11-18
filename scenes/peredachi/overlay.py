"""Одна ручка — две скорости. Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок,
цветные числа у осей (по камере timeline.VP_at), подписи-стикеры. В конце — полноэкранная карточка
«Больше механизмов — legobot.ru» с круглым логотипом, как в опубликованных рилсах. Адреса в углу нет.
Только объяснение — без вопросов к зрителю.
python overlay.py <папка плашек f0001.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "pila"))          # reelkit.py — общий стиль из сцены «Пила»
import timeline as TL, reelkit as K, peredachi_model as M

BADGE_COL = {'U2': (30, 90, 168), 'U1': (36, 150, 168), 'C': (240, 122, 18), 'D1': (232, 178, 20), 'D2': (200, 49, 122)}
BADGE_X = -100.0                                 # LDU: слева от шестерён
BG = K.bg_studio().convert('RGBA')
STICK, BADGE, CARD, TITLE = {}, {}, None, None


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
            K.sticker(im, 540, 300, text, K.font(54, 'xb'), K.SUN, K.INK, tilt=-1.5)
        elif style == 'big':
            K.sticker(im, 540, 300, text, K.font(62, 'black'), K.LIME, K.INK, pad=(42, 24), radius=32, tilt=1)
        else:
            K.sticker(im, 540, 300, text, K.font(54, 'xb'), (255, 255, 255), K.INK, tilt=1.5)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def badge_img(name, text):
    key = (name, text)
    if key not in BADGE:
        im = Image.new('RGBA', (500, 260), (0, 0, 0, 0))
        f = K.font(60 if len(text) > 2 else 76, 'black')
        K.sticker(im, 250, 130, text, f, BADGE_COL[name], (255, 255, 255), pad=(26, 12), radius=28)
        BADGE[key] = im.crop(im.getbbox())
    return BADGE[key]


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in TL.TITLE:
            im = Image.new('RGBA', (1300, 200), (0, 0, 0, 0))
            K.tracked(im, (650, 30), line, K.font(92), (255, 255, 255), K.INK, 6, track=3, shadow=((35, 41, 44), (0, 12)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def draw_title(img, t):
    for k, im in enumerate(title_img()):
        u = 1.0                                   # заголовок с первого кадра: он же обложка и стык петли
        paste_scaled(img, im, 540, 200 + k * 118 + im.height / 2 - 40, pop(u))


def draw_badges(img, t):
    al = 1.0
    for name, text, t0 in TL.BADGES:
        y = M.AXLES[name]['y']
        x, yy = TL.project(t, [(BADGE_X, y, -30.0)])[0]
        paste_scaled(img, badge_img(name, text), x, yy, pop((t - t0) / 0.3), al)


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, 1630, pop((t - a) / 0.3), al)


def card_img():
    """Финальная карточка — как в «Закрутится?», «Пиле», «Мальтийском кресте»."""
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
        pl = Image.open(os.path.join(plates, f'f{i + 1:04d}.png')).convert('RGBA')
        if pl.size != (TL.PLATE_W, TL.PLATE_H):
            pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
        img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
        draw_badges(img, t)
        draw_title(img, t)
        draw_caps(img, t)
    if t >= TL.T_CARD:
        c = card_img()
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
        for i in range(TL.FRAMES):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
            if i % 60 == 0:
                print('overlay', i, flush=True)
        # обложка: все числа на месте, крупная подпись про 81 раз
        Image.open(os.path.join(out, 'o0290.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
