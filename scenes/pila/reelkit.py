"""Стиль рилса LEGObot: фоны, заголовки с обводкой, стикеры, логотип, проекция 3D-точек."""
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageChops

W, H = 1080, 1920
LIME, LEAF, SUN, INK = (140, 198, 63), (59, 138, 46), (245, 197, 24), (35, 41, 44)


FONT_DIRS = ['/usr/share/fonts/opentype/inter/', '/usr/share/fonts/truetype/inter/', '/usr/share/fonts/opentype/inter-ui/']
FONT_FILES = {'black': ['InterDisplay-Black.otf', 'Inter-Black.otf', 'Inter-Black.ttf'],
              'xb': ['InterDisplay-ExtraBold.otf', 'Inter-ExtraBold.otf', 'Inter-ExtraBold.ttf'],
              'b': ['Inter-Bold.otf', 'Inter-Bold.ttf'], 'sb': ['Inter-SemiBold.otf', 'Inter-SemiBold.ttf'],
              'r': ['Inter-Regular.otf', 'Inter-Regular.ttf']}
_FC = {}


def font(size, w='black'):
    import os
    if w not in _FC:
        for f in FONT_FILES[w]:
            for d in FONT_DIRS:
                if os.path.exists(d + f):
                    _FC[w] = d + f; break
            if w in _FC:
                break
        else:
            raise SystemExit('нет шрифта Inter: ' + w)
    return ImageFont.truetype(_FC[w], size)


def vgrad(c1, c2, w=W, h=H):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(c1, float)[None, None] * (1 - t) + np.array(c2, float)[None, None] * t
    return Image.fromarray(np.repeat(a, w, axis=1).astype(np.uint8), 'RGB')


def radial_glow(img, center, radius, color, strength=0.6):
    w, h = img.size
    y, x = np.mgrid[0:h, 0:w]
    d = np.sqrt((x - center[0]) ** 2 + ((y - center[1]) * 1.6) ** 2) / radius
    a = np.clip(1 - d, 0, 1) ** 2 * strength
    base = np.asarray(img, float)
    out = base * (1 - a[..., None]) + np.array(color, float) * a[..., None]
    return Image.fromarray(out.astype(np.uint8))


def bg_studio():
    im = vgrad((226, 232, 238), (196, 205, 214))
    im = radial_glow(im, (W / 2, 980), 760, (246, 248, 250), 0.85)
    return im


def bg_night():
    im = vgrad((22, 28, 58), (60, 30, 92))
    im = radial_glow(im, (W / 2, 1060), 640, (90, 160, 210), 0.55)
    # точки-звёзды
    rng = np.random.default_rng(3); d = ImageDraw.Draw(im)
    for _ in range(90):
        x, y = rng.integers(0, W), rng.integers(0, 700)
        r = rng.choice([1, 1, 2]); d.ellipse((x - r, y - r, x + r, y + r), fill=(200, 210, 255))
    return im


def bg_table(top=1180):
    wall = vgrad((250, 243, 228), (236, 222, 196), h=top)
    wall = radial_glow(wall, (W / 2, top - 200), 700, (255, 251, 240), 0.7)
    # дерево: волокна из шума
    rng = np.random.default_rng(7)
    h = H - top
    y = np.arange(h)[:, None]; x = np.arange(W)[None, :]
    n = np.zeros((h, W))
    for k in range(6):
        f = 2 ** k; ph = rng.uniform(0, 6.28, 3)
        n += np.sin(x / (180 / f) * 0.15 + ph[0] + np.sin(y / (40 / f) + ph[1]) * 1.5) / f
    grain = np.sin(y * 0.22 + n * 3.0) * 0.5 + 0.5
    base = np.array([186, 132, 84], float); dark = np.array([140, 92, 54], float)
    wood = base * (1 - grain[..., None] * 0.45) + dark * grain[..., None] * 0.45
    persp = np.linspace(0.82, 1.08, h)[:, None, None]
    wood = np.clip(wood * persp, 0, 255).astype(np.uint8)
    im = Image.new('RGB', (W, H)); im.paste(wall, (0, 0)); im.paste(Image.fromarray(wood), (0, top))
    d = ImageDraw.Draw(im); d.rectangle((0, top - 3, W, top + 2), fill=(120, 80, 48))
    return im


def shadow_from(model_rgba, opacity=0.38, blur=18, dy=14, squash=0.35):
    """Мягкая тень под моделью: силуэт альфы, сплющенный и размытый."""
    a = model_rgba.split()[-1]
    bb = a.getbbox()
    if not bb:
        return Image.new('RGBA', model_rgba.size, (0, 0, 0, 0))
    w, h = model_rgba.size
    sil = a.crop((bb[0], bb[1], bb[2], bb[3]))
    sh_h = max(4, int((bb[3] - bb[1]) * squash))
    sil = sil.resize((bb[2] - bb[0], sh_h))
    S = Image.new('L', (w, h), 0); S.paste(sil, (bb[0], bb[3] - sh_h + dy))
    S = S.filter(ImageFilter.GaussianBlur(blur)).point(lambda v: int(v * opacity))
    out = Image.new('RGBA', (w, h), (20, 25, 35, 0)); out.putalpha(S)
    return out


def outlined(draw_img, xy, text, f, fill, stroke, sw, shadow=None, anchor='ma', spacing=6):
    d = ImageDraw.Draw(draw_img)
    if shadow:
        sc, off = shadow
        d.multiline_text((xy[0] + off[0], xy[1] + off[1]), text, font=f, fill=sc, anchor=anchor, align='center',
                         stroke_width=sw, stroke_fill=sc, spacing=spacing)
    d.multiline_text(xy, text, font=f, fill=fill, anchor=anchor, align='center', stroke_width=sw, stroke_fill=stroke, spacing=spacing)


def sticker(img, cx, cy, text, f, bg, fg, pad=(34, 20), radius=26, tilt=0, shadow=True):
    tmp = ImageDraw.Draw(img)
    bb = tmp.multiline_textbbox((0, 0), text, font=f, align='center', spacing=8)
    tw, th = int(bb[2] - bb[0]), int(bb[3] - bb[1])
    w, h = tw + 2 * pad[0], th + 2 * pad[1]
    S = Image.new('RGBA', (w + 40, h + 40), (0, 0, 0, 0))
    d = ImageDraw.Draw(S)
    if shadow:
        d.rounded_rectangle((20 + 4, 20 + 8, 20 + w + 4, 20 + h + 8), radius, fill=(0, 0, 0, 60))
        S = S.filter(ImageFilter.GaussianBlur(5)); d = ImageDraw.Draw(S)
    d.rounded_rectangle((20, 20, 20 + w, 20 + h), radius, fill=bg)
    d.multiline_text((20 + w / 2, 20 + pad[1] - bb[1]), text, font=f, fill=fg, anchor='ma', align='center', spacing=8)
    if tilt:
        S = S.rotate(tilt, resample=Image.BICUBIC, expand=True)
    img.alpha_composite(S, (int(cx - S.width / 2), int(cy - S.height / 2)))
    return (int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))


def logo_round(path=None, size=200):
    """Логотип в белом круге. По умолчанию — assets/logo.png репозитория (прямоугольный, на белом)."""
    import os
    path = path or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'logo.png')
    im = Image.open(path).convert('RGBA')
    S4 = size * 4
    disk = Image.new('RGBA', (S4, S4), (0, 0, 0, 0))
    m = Image.new('L', (S4, S4), 0); ImageDraw.Draw(m).ellipse((6, 6, S4 - 6, S4 - 6), fill=255)
    disk.paste((255, 255, 255, 255), (0, 0), m)
    k = 0.72 * S4 / max(im.size)
    lg = im.resize((int(im.width * k), int(im.height * k)), Image.LANCZOS)
    disk.alpha_composite(lg, ((S4 - lg.width) // 2, (S4 - lg.height) // 2))
    disk.putalpha(Image.fromarray(np.minimum(np.asarray(disk.split()[-1]), np.asarray(m))))
    return disk.resize((size, size), Image.LANCZOS)


def soften_plate(pl, feather=110, solid=0.97):
    """Тень с ловца теней плавно гаснет к краям плашки; сама модель (почти непрозрачная) не трогается."""
    a = np.asarray(pl.split()[-1], float) / 255
    h, w = a.shape
    y = np.arange(h)[:, None]; x = np.arange(w)[None, :]
    d = np.minimum(np.minimum(y, h - 1 - y), np.minimum(x, w - 1 - x)).astype(float)
    m = np.clip(d / feather, 0, 1); m = m * m * (3 - 2 * m)
    a2 = np.where(a >= solid, a, a * m)
    out = pl.copy(); out.putalpha(Image.fromarray((a2 * 255).astype(np.uint8)))
    return out


def project(VP, pts, w, h):
    pts = np.atleast_2d(np.asarray(pts, float))
    hp = np.c_[pts, np.ones(len(pts))] @ np.asarray(VP).T
    ndc = hp[:, :3] / hp[:, 3:4]
    return np.c_[(ndc[:, 0] + 1) / 2 * w, (1 - ndc[:, 1]) / 2 * h]


def tracked(img, xy, text, f, fill, stroke, sw, track=4, shadow=None):
    """Одна строка с разрядкой: буквы по одной, центр по xy[0], верх по xy[1]."""
    d = ImageDraw.Draw(img)
    widths = [d.textlength(ch, font=f) for ch in text]
    total = sum(widths) + track * (len(text) - 1)
    x = xy[0] - total / 2
    for layer in (('s',) if shadow else ()) + ('t',):
        xx = x
        for ch, w in zip(text, widths):
            if layer == 's':
                sc, off = shadow
                d.text((xx + off[0], xy[1] + off[1]), ch, font=f, fill=sc, stroke_width=sw, stroke_fill=sc)
            else:
                d.text((xx, xy[1]), ch, font=f, fill=fill, stroke_width=sw, stroke_fill=stroke)
            xx += w + track
