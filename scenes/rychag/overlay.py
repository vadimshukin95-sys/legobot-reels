"""Рычаг. Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок, линия уровня, бейджи
«1» и «3» у грузов, стрелка при перемещении петли, нумерация отверстий (плечи), подписи-стикеры, «где ещё»,
финальная карточка с логотипом. Плашка кадра i — f{SRC[i]+1:04d}.png.
python overlay.py <папка плашек> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "pila"))          # reelkit.py — общий стиль из сцены «Пила»
import timeline as TL, reelkit as K, rych_model as M

PINK, WHITE = (220, 40, 120), (255, 255, 255)
BG = K.bg_studio().convert('RGBA')
STICK, TITLE, LOGO, BADGE = {}, None, None, {}


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
            K.sticker(im, 540, 300, text, K.font(58, 'xb'), K.SUN, K.INK, tilt=-2)
        elif style == 'big':
            K.sticker(im, 540, 300, text, K.font(88, 'black'), K.LIME, K.INK, pad=(46, 26), radius=34, tilt=1)
        else:
            K.sticker(im, 540, 300, text, K.font(56, 'xb'), (255, 255, 255), K.INK)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def badge(text, r, fill, size):
    key = (text, r, fill, size)
    if key not in BADGE:
        s = 4; im = Image.new('RGBA', (2 * r * s + 8 * s, 2 * r * s + 8 * s), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        c = im.width / 2
        d.ellipse([c - r * s, c - r * s, c + r * s, c + r * s], fill=fill + (255,), outline=K.INK + (255,), width=3 * s)
        f = K.font(size * s, 'black')
        d.text((c, c + 0.04 * size * s), text, font=f, fill=K.INK, anchor='mm')
        BADGE[key] = im.resize((im.width // s, im.height // s), Image.LANCZOS)
    return BADGE[key]


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
    out = 1 - TL.smooth((t - TL.CARD) / 0.3)
    for k, im in enumerate(title_img()):
        u = (t - 0.1 - 0.15 * k) / 0.35
        paste_scaled(img, im, 540, 110 + k * 112 + im.height / 2 - 40, pop(u), out)


def arrowhead(d, tip, direction, col, size=30):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip)
    d.polygon([tuple(a), tuple(a - v * size + n * size * 0.62), tuple(a - v * size - n * size * 0.62)], fill=col)


def arrow(d, pts, col, grow):
    n = max(4, int(round(len(pts) * grow)))
    p = [tuple(q) for q in pts[:n]]
    d.line(p, fill=WHITE + (255,), width=19, joint='curve')
    arrowhead(d, pts[n - 1] + (pts[n - 1] - pts[n - 4]) / (np.linalg.norm(pts[n - 1] - pts[n - 4]) + 1e-9) * 6,
              pts[n - 1] - pts[n - 4], WHITE + (255,), 40)
    d.line(p, fill=col + (255,), width=11, joint='curve')
    arrowhead(d, pts[n - 1], pts[n - 1] - pts[n - 4], col + (255,), 32)


def fade(t, a, b, fin=0.25, fout=0.3):
    if not (a <= t <= b + fout):
        return 0.0
    return min(1, (t - a) / fin) * (1 if t <= b else max(0, 1 - (t - b) / fout))


def with_alpha(img, lay, al):
    if al <= 0:
        return
    if al < 1:
        lay.putalpha(lay.split()[-1].point(lambda v: int(v * al)))
    img.alpha_composite(lay)


def level_line(img, t):
    """Пунктир «ровно» по линии балки при нулевом наклоне."""
    al = fade(t, 0.3, TL.CARD - 0.2, 0.4, 0.3) * 0.75
    if al <= 0:
        return
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    xs = np.linspace(-175, 175, 36)
    pts = TL.project(t, np.c_[xs, np.zeros_like(xs), np.full_like(xs, -14.0)])
    for k in range(0, len(pts) - 1, 2):
        d.line([tuple(pts[k]), tuple(pts[k + 1])], fill=K.INK + (200,), width=4)
    with_alpha(img, lay, al)


def load_badges(img, t):
    al = fade(t, 0.45, TL.CARD - 0.2, 0.3, 0.3)
    if al <= 0:
        return
    th, kl = TL.state(t)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    (sl, el), (sr, er) = M.strings(th, kl)
    pl = TL.project(t, [el + np.array([36.0, 14, -20])])[0]                  # правее верха одиночного груза
    pr = TL.project(t, [er + np.array([36.0, 14, -20])])[0]                  # правее верха стопки
    s = pop((t - 0.45) / 0.35)
    paste_scaled(lay, badge('1', 34, WHITE, 44), pl[0] + 22, pl[1], s)
    paste_scaled(lay, badge('3', 34, WHITE, 44), pr[0] + 22, pr[1], s)
    with_alpha(img, lay, al)


def slide_arrows(img, t):
    for (a, b), k0, k1 in TL.SLIDES:
        al = fade(t, a - 0.1, b + 0.1, 0.15, 0.3)
        if al <= 0:
            continue
        th, _ = TL.state(t)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        R = M.rz(th)
        xs = np.linspace(-k0 * M.HOLE, -k1 * M.HOLE, 16)
        pts = np.array([M.PIV + R @ np.array([x, M.H - 34, 0.0]) + np.array([0, 0, -12.0]) for x in xs])
        arrow(d, TL.project(t, pts), PINK, TL.ease_out((t - a + 0.1) / 0.45))
        with_alpha(img, lay, al)


def hole_numbers(img, t):
    for a, b in TL.COUNT:
        al = fade(t, a, b, 0.2, 0.3)
        if al <= 0:
            continue
        th, kl = TL.state(t)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        seq = [(-k, str(k)) for k in range(1, int(round(kl)) + 1)] + [(k, str(k)) for k in range(1, M.K_R + 1)]
        for j, (k, txt) in enumerate(seq):
            u = (t - a - 0.07 * (abs(k) - 1) - (0.0 if k < 0 else 0.1)) / 0.25
            p = TL.project(t, [M.hole_pt(k, th) + M.rz(th) @ np.array([0, -30.0, 0])])[0]
            hot = abs(k) == (int(round(kl)) if k < 0 else M.K_R)
            paste_scaled(lay, badge(txt, 27 if hot else 21, K.SUN if hot else WHITE, 34 if hot else 26), p[0], p[1], pop(u))
        with_alpha(img, lay, al)


def draw_caps(img, t):
    for a, b, text, st, y in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, y, pop((t - a) / 0.3), al)
    end = TL.CAPS[-1][1]
    for k, (a, text) in enumerate(TL.WHERE):
        if a <= t < end + 0.2:
            al = 1.0 if t < end else max(0, 1 - (t - end) / 0.2)
            paste_scaled(img, sticker_img(text, 'white'), 540, 1625 + k * 84, pop((t - a) / 0.3), al)


def draw_card(img, t):
    global LOGO
    u = TL.smooth((t - TL.CARD) / 0.4)
    if u <= 0:
        return
    img.alpha_composite(Image.new('RGBA', img.size, (246, 248, 250, int(235 * u))))
    if LOGO is None:
        LOGO = K.logo_round(size=320)
    paste_scaled(img, LOGO, 540, 700, pop((t - TL.CARD - 0.15) / 0.35))
    paste_scaled(img, sticker_img('Готовые уроки\nс механизмами', 'sun'), 540, 1040, pop((t - TL.CARD - 0.4) / 0.3))
    paste_scaled(img, sticker_img('legobot.ru', 'white'), 540, 1230, pop((t - TL.CARD - 0.6) / 0.3))


def frame(i, plates):
    t = i / TL.FPS
    img = BG.copy()
    pl = Image.open(os.path.join(plates, f'f{TL.SRC[i] + 1:04d}.png')).convert('RGBA')
    if pl.size != (TL.PLATE_W, TL.PLATE_H):
        pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
    img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
    level_line(img, t)
    load_badges(img, t)
    slide_arrows(img, t)
    hole_numbers(img, t)
    draw_title(img, t)
    draw_caps(img, t)
    draw_card(img, t)
    if t < TL.CARD:
        ImageDraw.Draw(img).text((40, 1858), 'legobot.ru', font=K.font(34, 'b'), fill=K.INK)
    return img.convert('RGB')


if __name__ == '__main__':
    plates, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3:
        for i in map(int, sys.argv[3].split(',')):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
    else:
        for i in range(TL.FRAMES):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
            if i % 60 == 0:
                print('overlay', i, flush=True)
        Image.open(os.path.join(out, 'o0080.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
