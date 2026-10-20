"""Двери супермаркета: объёмные заголовки, подписи-пилюли, круги датчика, логотип -> out/ PNG."""
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

def main(s, e):
    proj = json.load(open(os.path.join(HERE, 'proj.json')))
    out_dir = os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out'))
    os.makedirs(out_dir, exist_ok=True)
    det, o0, o1, ho, c0, c1, end = (TL[k] for k in ('detect', 'open0', 'open1', 'handout', 'close0', 'close1', 'end'))
    T1 = volume_title(['КАК ДВЕРЬ', 'ВИДИТ ТЕБЯ?'], 112)
    T2 = volume_title(['ОТКРЫТО!'], 132)
    T4 = volume_title(['СОБЕРИ САМ!'], 122)
    P = PALETTES[os.environ.get('CAP_PALETTE', TL.get('cap_palette', 'pastel'))]
    def c(lines, role, size):
        bg = P[role]; fg = GRAPH if (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) > 140 else WHITE
        return cap(lines, bg, fg, size)
    C0 = c(['Двери супермаркета', 'из LEGO WeDo 2.0'], 'hook', 60)
    C1 = c(['Датчик заметил', 'ладонь!'], 'a', 62)
    C2 = c(['Мотор крутит шестерню,', 'она толкает рейку'], 'b', 58)
    C3 = c(['Рейка едет —', 'дверь открывается!'], 'c', 60)
    C4 = c(['Ладонь ушла.', 'Ждём 3 секунды'], 'a', 60)
    C5 = c(['Мотор назад —', 'дверь закрылась'], 'b', 60)
    C8 = c(['Схемы и уроки WeDo 2.0:', 'legobot.ru'], 'cta', 58)
    LOGO = logo_tile()
    ARR_R = pill(['рейка  →'], YEL, GRAPH, 50)
    ARR_L = pill(['←  рейка'], YEL, GRAPH, 50)
    for f in range(s, e + 1):
        src = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'), f'f{f:04d}.png')
        cv = Image.open(src).convert('RGB').resize((W, Hh), Image.LANCZOS).convert('RGBA')
        p = proj.get(str(f))
        if p and det - 8 <= f <= det + 14:
            sx, sy = p['sensor']
            rings(cv, sx * W, (1 - sy) * Hh, f, det - 8, rmax=160, col=(51, 224, 90))
        place(cv, ARR_R, W / 2, 1460, f, o0 + 4, o1 + 8, rot=0, wobble=0.3, intro=5)
        place(cv, ARR_L, W / 2, 1460, f, c0, c1 + 8, rot=0, wobble=0.3, intro=5)
        place(cv, T1, W / 2, 330, f, 3, 76, rot=-2, wobble=0.6)
        place(cv, C0, W / 2, 1640, f, 12, 74, rot=1.5, wobble=0.8)
        place(cv, C1, W / 2, 1640, f, det - 4, o0 + 2, rot=-1.4, wobble=0.8, intro=5)
        place(cv, C2, W / 2, 1640, f, o0 + 4, o0 + 40, rot=1.2, wobble=0.6)
        place(cv, C3, W / 2, 1640, f, o0 + 42, ho, rot=-1.2, wobble=0.6)
        if o1 - 2 <= f <= o1 + 56:
            jit = 5 * math.sin(f * 2.1) if f < o1 + 10 else 0
            place(cv, T2, W / 2 + jit, 330, f, o1 - 2, o1 + 56, rot=-3, wobble=1.2, intro=5)
        place(cv, C4, W / 2, 1640, f, ho + 2, c0 - 2, rot=1.2, wobble=0.6)
        place(cv, C5, W / 2, 1640, f, c0 + 2, c1 + 6, rot=-1.4, wobble=0.6)
        place(cv, LOGO, 250, 330, f, end, 999, rot=-4, wobble=1.0, intro=9)
        place(cv, T4, W / 2, 1380, f, end + 4, 999, rot=-3, wobble=0.6)
        place(cv, C8, W / 2, 1650, f, end + 10, 999, rot=1.5, wobble=0.5)
        cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
