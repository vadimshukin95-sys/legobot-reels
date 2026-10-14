"""LEGObot reel style: Rubik volume titles, cartoon caption pills, pop-in placement, sensor rings."""
import os, sys, json, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, 'fonts')
LOGO_PATH = os.path.join(HERE, '..', 'assets', 'logo.png')
W, H = 1080, 1920
FPS = 24
GRAPH = (43, 45, 49)
GREEN = (52, 168, 83)
GREEN_D = (27, 110, 52)
YEL = (255, 210, 31)
WHITE = (255, 255, 255)
RED = (226, 45, 36)

_fc = {}
def font(weight, size, kind):
    k = (weight, size, kind)
    if k not in _fc:
        if kind == 'sym':
            _fc[k] = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
        else:
            _fc[k] = ImageFont.truetype(os.path.join(FD, f"rubik-{'cyrillic' if kind == 'cyr' else 'latin'}-{weight}-normal.woff"), size)
    return _fc[k]

def kind(ch):
    if 'Ѐ' <= ch <= 'ӿ':
        return 'cyr'
    if ch in '→←↑↓':
        return 'sym'
    return 'lat'

def runs(text):
    out, cur, ck = [], '', None
    for ch in text:
        k = ck if (ch == ' ' and ck) else kind(ch)
        if ck is None or k == ck:
            cur += ch; ck = k
        else:
            out.append((cur, ck)); cur, ck = ch, k
    if cur:
        out.append((cur, ck))
    return out

def line_w(text, weight, size):
    return sum(font(weight, size, c).getlength(t) for t, c in runs(text))

def draw_line(d, x, y, text, weight, size, **kw):
    for t, c in runs(text):
        f = font(weight, size, c)
        d.text((x, y), t, font=f, **kw)
        x += f.getlength(t)

def text_mask(lines, weight, size, lh):
    wmax = int(max(line_w(l, weight, size) for l in lines)) + 4
    hh = int(lh * len(lines) + size * 0.4)
    m = Image.new('L', (wmax, hh), 0)
    d = ImageDraw.Draw(m)
    for i, l in enumerate(lines):
        draw_line(d, (wmax - line_w(l, weight, size)) / 2, i * lh, l, weight, size, fill=255)
    return m

def dilate(m, r):
    return m.filter(ImageFilter.MaxFilter(r * 2 + 1)) if r > 0 else m

_tcache = {}
def volume_title(lines, size=108):
    """white face, green extruded depth, graphite outline — the agreed reel style"""
    key = (tuple(lines), size)
    if key in _tcache:
        return _tcache[key]
    lh = int(size * 1.08)
    face = text_mask(lines, 900, size, lh)
    depth = int(size * 0.14)
    pad = depth + 24
    w, h = face.width + pad * 2, face.height + pad * 2
    ext = Image.new('L', (w, h), 0)
    for i in range(depth + 1):
        ext.paste(face, (pad + i // 3, pad + i), face)
    outline = dilate(ext, 7)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    # soft drop shadow
    sh = outline.filter(ImageFilter.GaussianBlur(10)).point(lambda v: int(v * 0.35))
    img.paste((0, 0, 0, 255), (6, 10), sh)
    img.paste(GRAPH + (255,), (0, 0), outline)
    # extrusion with darkening toward the back
    for i in range(depth, 0, -1):
        t = i / depth
        col = tuple(int(GREEN[j] * (1 - t) + GREEN_D[j] * t) for j in range(3))
        img.paste(col + (255,), (pad + i // 3, pad + i), face)
    # face + thin graphite contour on face
    fo = dilate(face, 2)
    img.paste(GRAPH + (255,), (pad, pad), fo)
    img.paste(WHITE + (255,), (pad, pad), face)
    # glossy top highlight on face
    hl = Image.new('L', face.size, 0)
    hd = ImageDraw.Draw(hl)
    for i in range(len(lines)):
        hd.rectangle([0, i * lh, face.width, i * lh + int(size * 0.42)], fill=60)
    hl = Image.composite(hl, Image.new('L', face.size, 0), face)
    img.paste((235, 255, 240, 255), (pad, pad), hl)
    if img.width > 1010:
        sc = 1010 / img.width
        img = img.resize((1010, int(img.height * sc)), Image.LANCZOS)
    _tcache[key] = img
    return img

_pcache = {}
def pill(lines, bg, fg, size=58, border=GRAPH):
    key = (tuple(lines), bg, fg, size)
    if key in _pcache:
        return _pcache[key]
    lh = int(size * 1.22)
    tw = int(max(line_w(l, 800, size) for l in lines))
    px, py = 48, 26
    w, h = tw + px * 2, lh * len(lines) + py * 2 - int(size * 0.18)
    img = Image.new('RGBA', (w + 30, h + 34), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r = min(46, h // 2)
    d.rounded_rectangle([10, 16, w + 10, h + 16], r, fill=(0, 0, 0, 70))     # offset shadow
    d.rounded_rectangle([4, 4, w + 4, h + 4], r, fill=border)
    d.rounded_rectangle([10, 10, w - 2, h - 2], r - 6, fill=bg)
    # shine strip
    d.rounded_rectangle([26, 18, w - 20, 18 + (h - 30) // 3], 20, fill=tuple(min(255, c + 28) for c in bg))
    for i, l in enumerate(lines):
        draw_line(d, 4 + px + (tw - line_w(l, 800, size)) / 2, 4 + py - int(size * 0.12) + i * lh, l, 800, size, fill=fg)
    _pcache[key] = img
    return img

def ease_back(t):
    t = max(0.0, min(1.0, t))
    c1 = 1.9; c3 = c1 + 1
    return 1 + c3 * (t - 1) ** 3 + c1 * (t - 1) ** 2

def place(canvas, sprite, cx, cy, f, f0, f1, rot=0.0, wobble=0.0, intro=7, outro=5):
    if f < f0 or f > f1:
        return
    t_in = (f - f0) / intro
    t_out = (f1 - f) / outro
    s = ease_back(t_in) if t_in < 1 else 1.0
    a = min(1.0, t_in * 1.6, max(0.0, t_out))
    if t_out < 1:
        s *= 0.85 + 0.15 * t_out
    if s <= 0.02 or a <= 0:
        return
    ang = rot + wobble * math.sin((f - f0) * 0.35)
    sp = sprite.resize((max(1, int(sprite.width * s)), max(1, int(sprite.height * s))), Image.LANCZOS)
    if ang:
        sp = sp.rotate(ang, resample=Image.BICUBIC, expand=True)
    if a < 1:
        al = sp.getchannel('A').point(lambda v: int(v * a)); sp.putalpha(al)
    canvas.alpha_composite(sp, (int(cx - sp.width / 2), int(cy - sp.height / 2)))

ORANGE = (240, 122, 18)
PURPLE = (116, 66, 176)

def rings(canvas, cx, cy, f, f0, n=3, period=10, rmax=170, col=YEL):
    """expanding 'radar' rings — the motion sensor sees the hand"""
    d = ImageDraw.Draw(canvas)
    for i in range(n):
        t = (f - f0 - i * period / n) / period
        if t < 0 or t > 1.6:
            continue
        t = t % 1.0
        r = 30 + rmax * t
        a = int(255 * (1 - t))
        lay = Image.new('RGBA', canvas.size, (0, 0, 0, 0))
        ld = ImageDraw.Draw(lay)
        ld.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], outline=GRAPH + (a,), width=14)
        ld.ellipse([cx - r, cy - r * 0.6, cx + r, cy + r * 0.6], outline=col + (a,), width=8)
        canvas.alpha_composite(lay)

def main(s, e):
    proj = json.load(open(os.path.join(HERE, 'proj.json')))
    os.makedirs(os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out')), exist_ok=True)
    T1 = volume_title(['СЛАДОСТЬ', 'ИЛИ ГАДОСТЬ?'], 112)
    T2 = volume_title(['БУ!'], 230)
    T4 = volume_title(['СОБЕРИ САМ!'], 122)
    C1 = pill(['Тянешься за конфетой…'], YEL, GRAPH, 58)
    C2 = pill(['Датчик движения', 'видит руку!'], WHITE, GRAPH, 56)
    C3 = pill(['мотор → шестерни → призрак'], ORANGE, WHITE, 52)
    C3b = pill(['Через 3 секунды', 'призрак прячется'], WHITE, GRAPH, 52)
    C4 = pill(['Скоро на legobot.ru'], GREEN, WHITE, 64)
    lg = Image.open(LOGO_PATH).convert('RGBA')
    lg = lg.resize((300, int(lg.height * 300 / lg.width)), Image.LANCZOS)
    LOGO = Image.new('RGBA', (lg.width + 60, lg.height + 50), (0, 0, 0, 0))
    ld_ = ImageDraw.Draw(LOGO)
    ld_.rounded_rectangle([8, 12, LOGO.width - 2, LOGO.height - 2], 40, fill=(0, 0, 0, 80))
    ld_.rounded_rectangle([0, 0, LOGO.width - 10, LOGO.height - 14], 40, fill=(255, 255, 255, 245))
    LOGO.alpha_composite(lg, (25, 18))
    for f in range(s, e + 1):
        src = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'), f'f{f:04d}.png')
        cv = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS).convert('RGBA')
        p = proj[str(f)]
        if 80 <= f <= 100:
            sx, sy = p['sensor']
            rings(cv, sx * W, (1 - sy) * H, f, 80)
        place(cv, T1, W / 2, 300, f, 3, 76, rot=-2, wobble=0.6)
        place(cv, C1, W / 2, 1640, f, 32, 84, rot=1.5, wobble=0.8)
        place(cv, C2, W / 2, 1640, f, 86, 124, rot=-1.5, wobble=0.8, intro=5)
        if 98 <= f <= 150:
            jit = 6 * math.sin(f * 2.1) if f < 112 else 0
            place(cv, T2, W * 0.70 + jit, 300, f, 98, 150, rot=8, wobble=2.5, intro=5)
        place(cv, C3, W / 2, 1660, f, 126, 168, rot=1.2, wobble=0.6)
        place(cv, C3b, W / 2, 1640, f, 170, 200, rot=-1.2, wobble=0.6)
        place(cv, LOGO, 250, 300, f, 204, 999, rot=-4, wobble=1.0, intro=9)
        place(cv, T4, W / 2, 1370, f, 206, 999, rot=-3, wobble=0.6)
        place(cv, C4, W / 2, 1640, f, 212, 999, rot=1.5, wobble=0.5)
        cv.convert('RGB').save(os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out'), f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
