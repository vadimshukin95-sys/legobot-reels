"""«Скрипач»: заголовки, подписи-пилюли, стрелки шестерён, путь пальца кривошипа, финальная карточка -> out/ PNG."""
import os, sys, json, math
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('reel_style', os.path.join(HERE, '..', '..', 'common', 'reel_style.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)   # shared reel style (Rubik, volume titles, pills)
volume_title, pill, place, rings = H.volume_title, H.pill, H.place, H.rings
GRAPH, GREEN, YEL, WHITE, ORANGE = H.GRAPH, H.GREEN, H.YEL, H.WHITE, H.ORANGE

W, Hh = 1080, 1920
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
LOGO_PATH = os.path.join(HERE, '..', '..', 'assets', 'logo.png')
BLUE = (47, 111, 222)

def dashed(cv, pts, f, col=YEL, width=9):
    """dashed closed path with graphite outline; dashes crawl along the path"""
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    n = len(pts)
    for k in range(n - 1):
        if (k + f // 3) % 3 == 0:
            continue
        a, b = pts[k], pts[k + 1]
        d.line([a, b], fill=GRAPH + (230,), width=width + 8)
    for k in range(n - 1):
        if (k + f // 3) % 3 == 0:
            continue
        a, b = pts[k], pts[k + 1]
        d.line([a, b], fill=col + (255,), width=width)
    cv.alpha_composite(lay)

def dot(cv, x, y, r=17, col=YEL):
    d = ImageDraw.Draw(cv)
    d.ellipse([x - r - 5, y - r - 5, x + r + 5, y + r + 5], fill=GRAPH + (255,))
    d.ellipse([x - r, y - r, x + r, y + r], fill=col + (255,))
    d.ellipse([x - r * 0.45, y - r * 0.55, x - r * 0.05, y - r * 0.15], fill=(255, 255, 255, 200))

KRAFT = (236, 206, 160)
RED_S = (226, 45, 36)

def label(lines, accent, size=56):
    """parcel label: off-white tag, graphite border, dashed inner frame, barcode strip in the accent colour, tape on top"""
    lh = int(size * 1.2)
    tw = int(max(H.line_w(l, 800, size) for l in lines))
    bar = 70; px, py = 40, 30
    w = bar + tw + px * 2; h = lh * len(lines) + py * 2 - int(size * 0.15)
    img = Image.new('RGBA', (w + 40, h + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    ox, oy = 14, 34
    d.rounded_rectangle([ox + 8, oy + 12, ox + w + 8, oy + h + 12], 18, fill=(0, 0, 0, 70))
    d.rounded_rectangle([ox, oy, ox + w, oy + h], 18, fill=GRAPH)
    d.rounded_rectangle([ox + 6, oy + 6, ox + w - 6, oy + h - 6], 13, fill=(255, 252, 244))
    for x in range(ox + 18, ox + w - 18, 22):                         # dashed inner frame
        d.line([(x, oy + 16), (x + 11, oy + 16)], fill=(190, 184, 172), width=3)
        d.line([(x, oy + h - 16), (x + 11, oy + h - 16)], fill=(190, 184, 172), width=3)
    d.rectangle([ox + 6, oy + 6, ox + bar, oy + h - 6], fill=accent)   # barcode strip
    rr = __import__('random').Random(len(lines[0]))
    yb = oy + 26
    while yb < oy + h - 26:
        t = rr.choice((3, 5, 8)); d.rectangle([ox + 18, yb, ox + bar - 12, yb + t], fill=GRAPH); yb += t + rr.choice((4, 6))
    for i, l in enumerate(lines):
        H.draw_line(d, ox + bar + px + (tw - H.line_w(l, 800, size)) / 2, oy + py - int(size * 0.1) + i * lh, l, 800, size, fill=GRAPH)
    tape = Image.new('RGBA', (150, 46), (250, 240, 200, 190))                 # sticky tape
    tape = tape.rotate(-6, expand=True, resample=Image.BICUBIC)
    img.alpha_composite(tape, (ox + w // 2 - 75, 4))
    return img

def bubble(lines, accent, size=58):
    """comic speech bubble with a tail pointing up toward the robot; graphite outline + accent rim"""
    lh = int(size * 1.2)
    tw = int(max(H.line_w(l, 800, size) for l in lines))
    px, py = 54, 30
    w = tw + px * 2; h = lh * len(lines) + py * 2 - int(size * 0.15)
    pad = 30; top = 90
    W_, H_ = w + pad * 2, h + top + pad
    m = Image.new('L', (W_, H_), 0); md = ImageDraw.Draw(m)
    bx, by = pad, top
    md.rounded_rectangle([bx, by, bx + w, by + h], min(64, h // 2), fill=255)
    tx = bx + w * 0.34
    md.polygon([(tx - 46, by + 30), (tx + 40, by + 30), (tx - 52, by - 70)], fill=255)
    img = Image.new('RGBA', (W_ + 12, H_ + 14), (0, 0, 0, 0))
    out = H.dilate(m, 10); rim = H.dilate(m, 5)
    sh = out.filter(__import__('PIL.ImageFilter', fromlist=['x']).GaussianBlur(6)).point(lambda v: int(v * 0.35))
    img.paste((0, 0, 0, 255), (8, 12), sh)
    img.paste(GRAPH + (255,), (0, 0), out)
    img.paste(accent + (255,), (0, 0), rim)
    img.paste(WHITE + (255,), (0, 0), m.filter(__import__('PIL.ImageFilter', fromlist=['x']).MinFilter(5)))
    d = ImageDraw.Draw(img)
    for k, l in enumerate(lines):
        H.draw_line(d, bx + px + (tw - H.line_w(l, 800, size)) / 2, by + py - int(size * 0.1) + k * lh, l, 800, size, fill=GRAPH)
    return img

# ---- title / caption font sets (all OFL, Cyrillic) ----
from PIL import ImageFont
_FD = os.path.join(HERE, '..', '..', 'common', 'fonts')
FONTSETS = {   # file, variation for titles (900), variation for captions (800), extrusion light, extrusion dark
    'rubik':      (None, None, None, (52, 168, 83), (27, 110, 52)),
    'nunito':     ('Nunito-Variable.ttf', 'Black', 'ExtraBold', (240, 150, 110), (190, 92, 66)),
    'unbounded':  ('Unbounded-Variable.ttf', 'Black', 'Bold', (110, 175, 225), (52, 110, 170)),
    'montserrat': (('MontserratAlternates-Black.ttf', 'MontserratAlternates-ExtraBold.ttf'), None, None, (165, 202, 24), (100, 135, 12)),
}
FONTSET = os.environ.get('TITLE_FONT', TL.get('title_font', 'rubik'))
_fs = FONTSETS[FONTSET]
H.GREEN, H.GREEN_D = _fs[3], _fs[4]
if _fs[0]:
    _cache = {}
    def _font(weight, size, kind):
        if kind == 'sym':
            return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        k = (weight, size)
        if k not in _cache:
            if isinstance(_fs[0], tuple):
                f = ImageFont.truetype(os.path.join(_FD, _fs[0][0] if weight >= 900 else _fs[0][1]), size)
            else:
                f = ImageFont.truetype(os.path.join(_FD, _fs[0]), size)
                f.set_variation_by_name(_fs[1] if weight >= 900 else _fs[2])
            _cache[k] = f
        return _cache[k]
    H.font = _font

PALETTES = {   # caption colours by role
    'brand':  {'hook': YEL, 'a': WHITE, 'b': ORANGE, 'c': YEL, 'cta': GREEN},
    'map':    {'hook': (226, 45, 36), 'a': (255, 248, 236), 'b': (226, 45, 36), 'c': (255, 248, 236), 'cta': (226, 45, 36)},
    'robot':  {'hook': (165, 202, 24), 'a': (255, 255, 255), 'b': (248, 183, 27), 'c': (62, 183, 232), 'cta': (165, 202, 24)},
    'pastel': {'hook': (250, 214, 165), 'a': (255, 252, 246), 'b': (205, 228, 245), 'c': (214, 236, 200), 'cta': (246, 205, 211)},
}

STYLE = os.environ.get('CAP_STYLE', TL.get('cap_style', 'pill'))
def cap(lines, bg, fg, size=56):
    if STYLE == 'label':
        return label(lines, bg if bg != WHITE else (47, 111, 222), size - 2)
    if STYLE == 'bubble':
        return bubble(lines, bg if bg != WHITE else (47, 111, 222), size)
    return pill(lines, bg, fg, size)

def logo_tile():
    lg = Image.open(LOGO_PATH).convert('RGBA')
    lg = lg.resize((300, int(lg.height * 300 / lg.width)), Image.LANCZOS)
    T = Image.new('RGBA', (lg.width + 60, lg.height + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(T)
    d.rounded_rectangle([8, 12, T.width - 2, T.height - 2], 40, fill=(0, 0, 0, 80))
    d.rounded_rectangle([0, 0, T.width - 10, T.height - 14], 40, fill=(255, 255, 255, 245))
    T.alpha_composite(lg, (25, 18))
    return T

from PIL import ImageFilter
import numpy as np

def scr(p):
    return (p[0] * W, (1 - p[1]) * Hh)

def arrow_arc(cv, pts, col, alpha=1.0):
    """дуга-стрелка по экранным точкам, остриё в конце"""
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a, b = np.array(pts[-2]), np.array(pts[-1]); v = b - a; v /= (np.linalg.norm(v) or 1); n = np.array([-v[1], v[0]])
    for w, c in ((22, GRAPH), (12, col)):
        d.line(pts, fill=c + (255,), width=w, joint='curve')
    tip = b + v * 34
    d.polygon([tuple(tip), tuple(b + n * 26), tuple(b - n * 26)], fill=GRAPH + (255,))
    d.polygon([tuple(b + v * 20), tuple(b + n * 15 - v * 4), tuple(b - n * 15 - v * 4)], fill=col + (255,))
    if alpha < 1:
        lay.putalpha(lay.getchannel('A').point(lambda x: int(x * alpha)))
    cv.alpha_composite(lay)

def fade(f, f0, f1, k=6):
    return max(0.0, min(1.0, (f - f0) / k, (f1 - f) / k))

def main(s, e):
    proj = json.load(open(os.path.join(HERE, 'proj.json')))
    out_dir = os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out'))
    os.makedirs(out_dir, exist_ok=True)
    sh = {nm: fr for fr, nm in TL['shots']}
    g0, c0, w0, end = sh['gears'], sh['crank'], sh['wide'], TL['end']
    P = PALETTES[os.environ.get('CAP_PALETTE', TL.get('cap_palette', 'pastel'))]
    def c(lines, role, size):
        bg = P[role]; fg = GRAPH if (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) > 140 else WHITE
        return cap(lines, bg, fg, size)
    T1 = volume_title(['МОТОР УМЕЕТ', 'ТОЛЬКО КРУТИТЬСЯ'], 104)
    T2 = volume_title(['КАК ОН ВОДИТ', 'СМЫЧКОМ?'], 112)
    T3 = volume_title(['ВРАЩЕНИЕ →', 'ТУДА-СЮДА'], 112)
    T4 = volume_title(['НОВЫЙ КУРС', 'ПО WEDO 2.0'], 120)
    C0 = c(['…а музыкант играет'], 'hook', 58)
    C1 = c(['Мотор крутит', 'шестерню на 8 зубьев'], 'a', 58)
    C2 = c(['24 зуба: кривошип крутится', 'в 3 раза медленнее'], 'b', 54)
    C3 = c(['Палец кривошипа', 'ходит по кругу'], 'hook', 56)
    C4 = c(['Смычок скользит', 'сквозь кисть'], 'c', 56)
    C5 = c(['кривошип + кулиса'], 'a', 58)
    C8 = c(['Скоро на legobot.ru'], 'cta', 64)
    LOGO = logo_tile()
    ORANGE_ = (240, 122, 18)
    for f in range(s, e + 1):
        src = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'), f'f{f:04d}.png')
        cv = Image.open(src).convert('RGB').resize((W, Hh), Image.LANCZOS)
        if f >= end:                                          # финальная карточка: модель уходит в мягкое размытие
            k = min(1.0, (f - end) / 14)
            cv = Image.blend(cv, cv.filter(ImageFilter.GaussianBlur(16)), k)
            cv = Image.blend(cv, Image.new('RGB', cv.size, (248, 244, 236)), 0.42 * k)
        cv = cv.convert('RGBA')
        p = proj.get(str(f))
        if p and g0 + 10 <= f <= c0 - 4:                      # стрелки вращения шестерён
            al = fade(f, g0 + 10, c0 - 4)
            arrow_arc(cv, [scr(q) for q in p['arc24']], ORANGE_, al)
            arrow_arc(cv, [scr(q) for q in p['arc8']], YEL, al)
        if p and c0 + 14 <= f <= w0 - 2:                      # путь пальца кривошипа
            dashed(cv, [scr(q) for q in p['circle']], f)
            x, y = scr(p['pin']); dot(cv, x, y, 15)
        place(cv, T1, W / 2, 330, f, 3, 66, rot=-2, wobble=0.6)
        place(cv, C0, W / 2, 1640, f, 16, 66, rot=1.5, wobble=0.8)
        place(cv, T2, W / 2, 330, f, 72, g0 + 4, rot=2, wobble=0.6)
        place(cv, C1, W / 2, 1640, f, g0 + 12, g0 + 62, rot=-1.4, wobble=0.6)
        place(cv, C2, W / 2, 1640, f, g0 + 64, c0 - 4, rot=1.2, wobble=0.6)
        place(cv, C3, W / 2, 330, f, c0 + 16, w0 - 4, rot=-1.5, wobble=0.6)
        place(cv, C4, W / 2, 1640, f, c0 + 60, w0 - 4, rot=1.5, wobble=0.6)
        place(cv, T3, W / 2, 330, f, w0 + 6, end - 2, rot=-2, wobble=0.6)
        place(cv, C5, W / 2, 1640, f, w0 + 16, end - 2, rot=1.2, wobble=0.6)
        place(cv, LOGO, W / 2, 430, f, end + 6, 999, rot=-3, wobble=1.0, intro=9)
        place(cv, T4, W / 2, 900, f, end + 10, 999, rot=-2, wobble=0.6)
        place(cv, C8, W / 2, 1600, f, end + 18, 999, rot=1.5, wobble=0.5)
        cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
