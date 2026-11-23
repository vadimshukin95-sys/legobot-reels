"""Храповик. Сборка кадров рилса: фон «Студия», плашка модели из Blender (с тенью), заголовок, подписи-стикеры,
стрелки поверх механизма (по камере timeline.VP_at), «где ещё», финальная карточка с логотипом.
Плашки рендерятся только для уникальных кадров: плашка кадра i — f{SRC[i]+1:04d}.png.
python overlay.py <папка плашек> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math, numpy as np
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, "..", "pila"))          # reelkit.py — общий стиль из сцены «Пила»
import timeline as TL, reelkit as K, hrap_model as M

GREEN, BLUE, PINK, WHITE = (46, 158, 91), (40, 110, 230), (220, 40, 120), (255, 255, 255)
BG = K.bg_studio().convert('RGBA')
STICK, TITLE, LOGO = {}, None, None


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
    out = 1 - TL.smooth((t - TL.CARD) / 0.3)
    for k, im in enumerate(title_img()):
        u = (t - 0.1 - 0.15 * k) / 0.35
        paste_scaled(img, im, 540, 110 + k * 112 + im.height / 2 - 40, pop(u), out)


def arrowhead(d, tip, direction, col, size=30):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip)
    d.polygon([tuple(a), tuple(a - v * size + n * size * 0.62), tuple(a - v * size - n * size * 0.62)], fill=col)


def arrow(d, pts, col, grow):
    """Стрелка по ломаной pts (пиксели) с белой подложкой; grow 0..1 — доля длины."""
    n = max(4, int(round(len(pts) * grow)))
    p = [tuple(q) for q in pts[:n]]
    d.line(p, fill=WHITE + (255,), width=19, joint='curve')
    arrowhead(d, pts[n - 1] + (pts[n - 1] - pts[n - 4]) / (np.linalg.norm(pts[n - 1] - pts[n - 4]) + 1e-9) * 6,
              pts[n - 1] - pts[n - 4], WHITE + (255,), 40)
    d.line(p, fill=col + (255,), width=11, joint='curve')
    arrowhead(d, pts[n - 1], pts[n - 1] - pts[n - 4], col + (255,), 32)


def window(t, a, b, fin=0.25, fout=0.3):
    if not (a <= t <= b + fout):
        return 0.0, 0.0
    al = min(1, (t - a) / fin) * (1 if t <= b else max(0, 1 - (t - b) / fout))
    return al, TL.ease_out(min(1, (t - a) / 0.5))


def layer_alpha(lay, al):
    if al < 1:
        lay.putalpha(lay.split()[-1].point(lambda v: int(v * al)))
    return lay


def overlays(img, t):
    g, pw, dy = TL.state(t)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    used = False
    # 1) крутим: дуга вокруг шестерни (по ходу подъёма) + груз вверх
    al, gr = window(t, 3.2, 7.8)
    if al > 0:
        aa = np.radians(np.linspace(262, 196, 24)); r = 46.0
        arc = TL.project(t, np.c_[M.GC[0] + r * np.cos(aa), M.GC[1] + r * np.sin(aa), np.full(24, -62.0)])
        arrow(d, arc, GREEN, gr)
        ys = np.linspace(M.LOAD_TOP + dy + 60, M.LOAD_TOP + dy - 10, 20)
        up = TL.project(t, np.c_[np.full(20, 92.0), ys, np.zeros(20)])
        arrow(d, up, BLUE, gr); used = True
        lay = layer_alpha(lay, al); img.alpha_composite(lay)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # 2) крупный план: кольцо вокруг места, где зуб упёрся в собачку
    al, gr = window(t, 10.8, 12.9)
    if al > 0:
        c = TL.project(t, [M.pawl_tip(TL.PAWL_LOCK)])[0]
        rr = 46 + 6 * math.sin((t - 10.8) * 7)
        for w, col in ((16, WHITE), (9, PINK)):
            d.ellipse([c[0] - rr, c[1] - rr, c[0] + rr, c[1] + rr], outline=col + (255,), width=w)
        lay = layer_alpha(lay, al); img.alpha_composite(lay)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # 3) поднимаем собачку
    al, gr = window(t, 12.95, 13.6, 0.15, 0.25)
    if al > 0:
        a = np.radians(M.TAB['base'] + TL.PAWL_LOCK)
        mid = M.PIV + np.array([16 * np.cos(a), 16 * np.sin(a), -64.0])           # середина собачки, перед ней
        pts = TL.project(t, np.c_[np.full(16, mid[0]), np.linspace(mid[1] - 4, mid[1] - 58, 16), np.full(16, mid[2])])
        arrow(d, pts, PINK, gr)
        lay = layer_alpha(lay, al); img.alpha_composite(lay)
        lay = Image.new('RGBA', img.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    # 4) падает
    al, gr = window(t, 13.5, 14.25, 0.1, 0.3)
    if al > 0:
        y0 = M.LOAD_TOP + TL.state(13.5)[2]
        pts = TL.project(t, np.c_[np.full(20, 92.0), np.linspace(y0, y0 + 80, 20), np.zeros(20)])
        arrow(d, pts, BLUE, gr)
        lay = layer_alpha(lay, al); img.alpha_composite(lay)


def draw_caps(img, t):
    for a, b, text, st, y in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, y, pop((t - a) / 0.3), al)
    for k, (a, text) in enumerate(TL.WHERE):
        if a <= t < 17.9 + 0.2:
            al = 1.0 if t < 17.9 else max(0, 1 - (t - 17.9) / 0.2)
            paste_scaled(img, sticker_img(text, 'white'), 540, 1665 + k * 86, pop((t - a) / 0.3), al)


def draw_card(img, t):
    global LOGO
    u = TL.smooth((t - TL.CARD) / 0.4)
    if u <= 0:
        return
    veil = Image.new('RGBA', img.size, (246, 248, 250, int(235 * u)))
    img.alpha_composite(veil)
    if LOGO is None:
        LOGO = K.logo_round(size=320)
    paste_scaled(img, LOGO, 540, 700, pop((t - TL.CARD - 0.15) / 0.35))
    paste_scaled(img, sticker_img('Готовые уроки\nс механизмами', 'sun'), 540, 1040, pop((t - TL.CARD - 0.4) / 0.3))
    paste_scaled(img, sticker_img('Ссылка в шапке профиля', 'white'), 540, 1230, pop((t - TL.CARD - 0.6) / 0.3))


def frame(i, plates):
    t = i / TL.FPS
    img = BG.copy()
    pl = Image.open(os.path.join(plates, f'f{TL.SRC[i] + 1:04d}.png')).convert('RGBA')
    if pl.size != (TL.PLATE_W, TL.PLATE_H):
        pl = pl.resize((TL.PLATE_W, TL.PLATE_H), Image.LANCZOS)
    img.alpha_composite(K.soften_plate(pl), (0, TL.MY))
    overlays(img, t)
    draw_title(img, t)
    draw_caps(img, t)
    draw_card(img, t)
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
        Image.open(os.path.join(out, 'o0045.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
