"""Двери от одной шестерни. Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок,
подписи-стикеры, стрелки поверх механизма (по камере timeline.VP_at). Финальной карточки нет — ролик зациклен,
legobot.ru стоит в углу всё время.
python overlay.py <папка плашек f0001.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "pila"))          # reelkit.py — общий стиль из сцены «Пила»
import timeline as TL, reelkit as K

ORANGE, PURPLE, GREEN, WHITE = (242, 140, 40), (123, 79, 216), (46, 158, 91), (255, 255, 255)
BG = K.bg_studio().convert('RGBA')
STICK, TITLE = {}, None


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
            K.sticker(im, 540, 300, text, K.font(56, 'xb'), (255, 255, 255), K.INK)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in TL.TITLE:
            im = Image.new('RGBA', (1300, 200), (0, 0, 0, 0))
            K.tracked(im, (650, 30), line, K.font(96), (255, 255, 255), K.INK, 6, track=4, shadow=((35, 41, 44), (0, 12)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def draw_title(img, t):
    for k, im in enumerate(title_img()):
        u = (t - 0.1 - 0.15 * k) / 0.35
        paste_scaled(img, im, 540, 190 + k * 116 + im.height / 2 - 40, pop(u))


def arrowhead(d, tip, direction, col, size=30):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip)
    d.polygon([tuple(a), tuple(a - v * size + n * size * 0.62), tuple(a - v * size - n * size * 0.62)], fill=col)


def arrow(d, pts, col, grow):
    """Стрелка по ломаной pts (пиксели) с белой подложкой; grow 0..1 — доля длины."""
    n = max(2, int(round(len(pts) * grow)))
    p = [tuple(q) for q in pts[:n]]
    d.line(p, fill=WHITE + (255,), width=19, joint='curve')
    arrowhead(d, pts[n - 1] + (pts[n - 1] - pts[n - 4]) / (np.linalg.norm(pts[n - 1] - pts[n - 4]) + 1e-9) * 6,
              pts[n - 1] - pts[n - 4], WHITE + (255,), 40)
    d.line(p, fill=col + (255,), width=11, joint='curve')
    arrowhead(d, pts[n - 1], pts[n - 1] - pts[n - 4], col + (255,), 32)


def overlays(img, t):
    a0, a1 = TL.ARROWS
    if not (a0 <= t <= a1 + 0.3):
        return
    alpha = min(1, (t - a0) / 0.25) * (1 if t <= a1 else max(0, 1 - (t - a1) / 0.3))
    grow = TL.ease_out(min(1, (t - a0) / 0.5))
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    xs = np.linspace(-75, 75, 24)
    top = TL.project(t, np.c_[xs, np.full(24, -80.0), np.full(24, 30.0)])            # над верхней направляющей → вправо
    bot = TL.project(t, np.c_[xs[::-1], np.full(24, 80.0), np.full(24, 30.0)])       # под нижней направляющей ← влево
    arrow(d, top, ORANGE, grow)
    arrow(d, bot, PURPLE, grow)
    aa = np.radians(np.linspace(58, 122, 24))                                          # дуга справа от шестерни: по часовой
    r = 52.0
    gear = TL.project(t, np.c_[r * np.sin(aa), -r * np.cos(aa), np.full(24, 28.0)])
    arrow(d, gear, GREEN, grow)
    if alpha < 1:
        lay.putalpha(lay.split()[-1].point(lambda v: int(v * alpha)))
    img.alpha_composite(lay)


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, 1530, pop((t - a) / 0.3), al)


def frame(i, plates):
    t = i / TL.FPS
    img = BG.copy()
    pl = Image.open(os.path.join(plates, f'f{i + 1:04d}.png')).convert('RGBA')
    if pl.size != (TL.PLATE_W, TL.PLATE_H):
        pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
    img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
    overlays(img, t)
    draw_title(img, t)
    draw_caps(img, t)
    ImageDraw.Draw(img).text((40, 1858), 'legobot.ru', font=K.font(34, 'b'), fill=K.INK)
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
        # обложка рилса — кадр со стрелками на крупном плане
        Image.open(os.path.join(out, 'o0120.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
