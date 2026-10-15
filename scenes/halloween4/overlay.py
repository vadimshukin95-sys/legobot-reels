"""«Сладость или гадость?» 4 конструктора: заголовок, таблички-«номера домов», комикс-облачка, финальная карточка.
frames/fXXXX.png -> out/oXXXX.png (1080x1920)."""
import os, sys, json, math, random
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('reel_style', os.path.join(HERE, '..', '..', 'common', 'reel_style.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)
volume_title, place, ease_back = H.volume_title, H.place, H.ease_back
GRAPH, YEL, WHITE, ORANGE, RED, GREEN = H.GRAPH, H.YEL, H.WHITE, H.ORANGE, H.RED, H.GREEN
W, HH = 1080, 1920
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
OV = TL['overlay']
NAVY = (22, 40, 92)
LOGO_PATH = os.path.join(HERE, '..', '..', 'assets', 'logo.png')

def text_w(t, size, weight=800):
    return H.line_w(t, weight, size)

def plate(num, name, sub):
    """enamel house-number plate: navy, white double border, orange number disc, screws"""
    s1, s2 = 64, 38
    tw = max(text_w(name, s1, 900), text_w(sub, s2, 800))
    disc = 150
    w = int(disc + tw + 120); h = 190
    img = Image.new('RGBA', (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([12, 16, w + 12, h + 16], 36, fill=(0, 0, 0, 90))
    d.rounded_rectangle([0, 0, w, h], 36, fill=GRAPH)
    d.rounded_rectangle([6, 6, w - 6, h - 6], 31, fill=NAVY)
    d.rounded_rectangle([18, 18, w - 18, h - 18], 22, outline=WHITE, width=5)
    d.rounded_rectangle([30, 26, w - 30, 26 + 40], 18, fill=(38, 62, 128))           # enamel shine
    cx, cy = 40 + disc // 2, h // 2
    d.ellipse([cx - 62, cy - 62, cx + 62, cy + 62], fill=GRAPH)
    d.ellipse([cx - 56, cy - 56, cx + 56, cy + 56], fill=ORANGE)
    d.ellipse([cx - 40, cy - 48, cx + 8, cy - 22], fill=(255, 170, 90))
    nw = text_w(num, 92, 900)
    H.draw_line(d, cx - nw / 2, cy - 60, num, 900, 92, fill=WHITE)
    x0 = 40 + disc + 20
    H.draw_line(d, x0, 34, name, 900, s1, fill=WHITE)
    H.draw_line(d, x0, 112, sub, 800, s2, fill=(255, 214, 140))
    for sx, sy in ((30, h // 2), (w - 30, h // 2)):
        d.ellipse([sx - 7, sy - 7, sx + 7, sy + 7], fill=(150, 160, 185)); d.line([sx - 4, sy, sx + 4, sy], fill=GRAPH, width=2)
    return img

def mech_tag(text):
    """chalk-on-slate tag with the sensor -> motor chain"""
    size = 44
    tw = text_w(text, size, 800)
    w, h = int(tw + 70), 96
    img = Image.new('RGBA', (w + 20, h + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([8, 12, w + 8, h + 12], 22, fill=(0, 0, 0, 80))
    d.rounded_rectangle([0, 0, w, h], 22, fill=WHITE)
    d.rounded_rectangle([5, 5, w - 5, h - 5], 18, fill=(255, 248, 232))
    H.draw_line(d, 35, 18, text, 800, size, fill=GRAPH)
    return img

def burst(text, fill, fg, size=120, spikes=14, seed=1, round_=False):
    """comic speech burst: spiky (scare) or round (friendly) with a tail"""
    r = random.Random(seed)
    tw = text_w(text, size, 900)
    rx, ry = tw / 2 + 80, size * 0.95
    w, h = int(rx * 2 + 120), int(ry * 2 + 170)
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    cx, cy = w / 2, ry + 40
    if round_:
        pts = [(cx + rx * math.cos(a), cy + ry * math.sin(a)) for a in [i * 2 * math.pi / 60 for i in range(60)]]
    else:
        pts = []
        n = spikes * 2
        for i in range(n):
            a = i * 2 * math.pi / n
            k = 1.18 + r.uniform(0, 0.12) if i % 2 == 0 else 0.86
            pts.append((cx + rx * k * math.cos(a), cy + ry * k * math.sin(a)))
    tail = [(cx - rx * 0.35, cy + ry * 0.6), (cx - rx * 0.62, cy + ry + 110), (cx - rx * 0.05, cy + ry * 0.75)]
    sh = [(x + 10, y + 14) for x, y in pts]
    d.polygon(sh, fill=(0, 0, 0, 90)); d.polygon([(x + 10, y + 14) for x, y in tail], fill=(0, 0, 0, 90))
    for poly in (pts, tail):
        d.polygon(poly, fill=GRAPH)
    lay = Image.new('L', (w, h), 0); ld = ImageDraw.Draw(lay); ld.polygon(pts, fill=255); ld.polygon(tail, fill=255)
    inner = lay.filter(ImageFilter.MinFilter(17))
    img.paste(fill + (255,), (0, 0), inner)
    # outline of text in graphite, face in fg
    tx, ty = cx - tw / 2, cy - size * 0.62
    tm = Image.new('L', (w, h), 0); H.draw_line(ImageDraw.Draw(tm), tx, ty, text, 900, size, fill=255)
    img.paste(GRAPH + (255,), (0, 0), tm.filter(ImageFilter.MaxFilter(11)))
    img.paste(fg + (255,), (0, 0), tm)
    return img

def card(path, label, accent):
    """finale tile: model cut-out on a porch-light disc + kit label"""
    S = 470
    img = Image.new('RGBA', (S, S + 70), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 14, S - 2, S + 2], 46, fill=(0, 0, 0, 90))
    d.rounded_rectangle([0, 0, S - 12, S - 12], 46, fill=GRAPH)
    d.rounded_rectangle([7, 7, S - 19, S - 19], 40, fill=(24, 38, 82))
    glow = Image.new('L', (S, S), 0); ImageDraw.Draw(glow).ellipse([60, 80, S - 70, S - 60], fill=150)
    img.paste((255, 170, 70, 255), (0, 0), glow.filter(ImageFilter.GaussianBlur(50)).point(lambda v: v // 2))
    m = Image.open(path).convert('RGBA'); m = m.crop(m.getbbox())
    sc = min((S - 90) / m.width, (S - 110) / m.height)
    m = m.resize((int(m.width * sc), int(m.height * sc)), Image.LANCZOS)
    img.alpha_composite(m, ((S - 12 - m.width) // 2, 30 + (S - 130 - m.height) // 2))
    lw = text_w(label, 46, 900) + 56
    lx = (S - 12 - lw) / 2; ly = S - 100
    d = ImageDraw.Draw(img)
    d.rounded_rectangle([lx, ly, lx + lw, ly + 74], 30, fill=GRAPH)
    d.rounded_rectangle([lx + 5, ly + 5, lx + lw - 5, ly + 69], 26, fill=accent)
    H.draw_line(d, lx + 28, ly + 9, label, 900, 46, fill=WHITE)
    return img

def url_plate(text):
    size = 78
    tw = text_w(text, size, 900)
    w, h = int(tw + 110), 140
    img = Image.new('RGBA', (w + 24, h + 28), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([10, 16, w + 10, h + 16], 50, fill=(0, 0, 0, 90))
    d.rounded_rectangle([0, 0, w, h], 50, fill=GRAPH)
    d.rounded_rectangle([7, 7, w - 7, h - 7], 44, fill=ORANGE)
    d.rounded_rectangle([24, 16, w - 24, 50], 18, fill=(255, 158, 70))
    H.draw_line(d, 55, 14, text, 900, size, fill=WHITE)
    return img

def logo_badge():
    lg = Image.open(LOGO_PATH).convert('RGBA')
    lg = lg.resize((240, int(lg.height * 240 / lg.width)), Image.LANCZOS)
    b = Image.new('RGBA', (lg.width + 56, lg.height + 46), (0, 0, 0, 0)); d = ImageDraw.Draw(b)
    d.rounded_rectangle([8, 12, b.width - 2, b.height - 2], 36, fill=(0, 0, 0, 80))
    d.rounded_rectangle([0, 0, b.width - 10, b.height - 14], 36, fill=(255, 255, 255, 245))
    b.alpha_composite(lg, (23, 16))
    return b

def main(s, e):
    proj = json.load(open(os.path.join(HERE, 'proj.json')))
    out_dir = os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out')); os.makedirs(out_dir, exist_ok=True)
    fr_dir = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'))
    T1 = volume_title(OV['title'], 112)
    SUB = mech_tag(OV['subtitle'])
    stops = {st['id']: st for st in TL['stops']}
    PL, MT, BU = {}, {}, []
    for st in TL['stops']:
        o = st['ov']
        PL[st['id']] = plate(o['num'], o['name'], o['model'])
        MT[st['id']] = mech_tag(o['mech'])
        for i, b in enumerate(o['bursts']):
            BU.append((st['id'], st['f0'] + b['t0'], st['f0'] + b['t1'],
                       burst(b['text'], tuple(b['fill']), tuple(b['fg']), b.get('size', 120), seed=len(BU) + 3, round_=b.get('round', False)),
                       b.get('dx', 0.18), b.get('dy', -0.06), b.get('rot', 6)))
    FT = volume_title(OV['final_title'], 92)
    CARDS = [card(os.path.join(HERE, 'assets', f"cut_{c['id']}.png"), c['label'], tuple(c['accent'])) for c in OV['cards']]
    URL = url_plate('legobot.ru')
    FSUB = mech_tag(OV['final_sub'])
    LOGO = logo_badge()
    F_FIN = OV['final_f']
    for f in range(s, e + 1):
        cv = Image.open(os.path.join(fr_dir, f'f{f:04d}.png')).convert('RGB').resize((W, HH), Image.LANCZOS).convert('RGBA')
        p = proj[str(f)]
        place(cv, T1, W / 2, 470, f, 4, 62, rot=-2, wobble=0.6)
        place(cv, SUB, W / 2, 1560, f, 16, 62, rot=1.2, wobble=0.5)
        for mid, f0, f1, spr, dx, dy, rot in BU:
            if f0 <= f <= f1:
                ax, ay = p[mid]
                jit = 7 * math.sin(f * 2.3) if f - f0 < 12 else 0
                cx = min(max((ax + dx) * W, spr.width / 2 + 10), W - spr.width / 2 - 10)
                cy = min(max((ay + dy) * HH, 120 + spr.height / 2), 1380)
                place(cv, spr, cx + jit, cy, f, f0, f1, rot=rot, wobble=2.0, intro=5, outro=4)
        if f >= F_FIN:
            place(cv, FT, W / 2, 300, f, F_FIN, 9999, rot=-2, wobble=0.5)
            for i, c in enumerate(CARDS):
                cx = W / 2 + (-1 if i % 2 == 0 else 1) * 245
                cy = 760 + (i // 2) * 520
                place(cv, c, cx, cy, f, F_FIN + 5 + i * 4, 9999, rot=(-3, 2.5, 2, -2.5)[i], wobble=0.4, intro=9)
            place(cv, URL, W / 2 + 120, 1740, f, F_FIN + 24, 9999, rot=-2, wobble=0.4)
            place(cv, LOGO, 210, 1730, f, F_FIN + 28, 9999, rot=-4, wobble=0.6)
            place(cv, FSUB, W / 2, 1585, f, F_FIN + 20, 9999, rot=1, wobble=0.3)
        cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
