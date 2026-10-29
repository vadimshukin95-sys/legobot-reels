"""Кадры витрины /kompl: фон первого экрана страницы + 3D + лента «Комплектом выгоднее» сверху.
  python overlay.py <папка с f*.png> <папка вывода>      (фон — BG_CENTRE / BG_EDGE / BG_GAIN, как у других роликов)"""
import sys, os, glob, json, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
RIB = LAY['ribbon']
EDGE = tuple(int(v) for v in os.environ.get('BG_EDGE', '253,242,248').split(','))
CENTRE = tuple(int(v) for v in os.environ.get('BG_CENTRE', '255,255,255').split(','))
GAIN = float(os.environ.get('BG_GAIN', '2.0'))
FPS, LOOP = 24, 18.0

def font(size):
    try:
        f = ImageFont.truetype(os.path.join(HERE, '..', '..', 'common', 'fonts', 'Nunito-Variable.ttf'), size)
        f.set_variation_by_name('ExtraBold'); return f
    except Exception:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size - 4)
FONT = font(RIB['size'])
def hexrgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
COLR = hexrgb(RIB['color']); DARK = tuple(int(v * 0.68) for v in COLR)

def ribbon(W, H):
    """Лента с хвостами в 2× разрешении, затем уменьшается — края гладкие."""
    k = 2; im = Image.new('RGBA', (W * k, H * k), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    f = font(RIB['size'] * k); text = RIB['text']
    tw = d.textlength(text, font=f); cx, cy = W * k / 2, RIB['y'] * k
    w2, h2 = tw / 2 + 34 * k, 34 * k
    for s in (-1, 1):                                                     # хвосты: ниже основной ленты, с вырезом
        x0 = cx + s * w2
        d.polygon([(x0 - s * 14 * k, cy - h2 + 16 * k), (x0 + s * 58 * k, cy - h2 + 16 * k), (x0 + s * 38 * k, cy + 16 * k),
                   (x0 + s * 58 * k, cy + h2 + 16 * k), (x0 - s * 14 * k, cy + h2 + 16 * k)], fill=DARK + (255,))
        d.polygon([(x0 - s * 1 * k, cy + h2), (x0 - s * 14 * k, cy + h2 + 16 * k), (x0 - s * 14 * k, cy + h2)], fill=tuple(int(v * 0.5) for v in COLR) + (255,))
    d.rounded_rectangle([cx - w2, cy - h2, cx + w2, cy + h2], 10 * k, fill=COLR + (255,))
    d.rounded_rectangle([cx - w2 + 6 * k, cy - h2 + 6 * k, cx + w2 - 6 * k, cy - h2 + 9 * k], 2 * k, fill=(255, 255, 255, 50))
    bb = d.textbbox((0, 0), text, font=f)
    d.text((cx - tw / 2, cy - (bb[1] + bb[3]) / 2), text, font=f, fill=(255, 255, 255, 255))
    im = im.resize((W, H), Image.LANCZOS)
    sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); a = im.getchannel('A').point(lambda v: v * 40 // 255)
    sh.putalpha(a); sh = sh.filter(ImageFilter.GaussianBlur(10))
    out = Image.new('RGBA', (W, H), (0, 0, 0, 0)); out.alpha_composite(sh, (0, 8)); out.alpha_composite(im)
    return out

_bg = {}
def background(w, h):
    if (w, h) not in _bg:
        g = Image.radial_gradient('L').resize((w, h), Image.BICUBIC).point(lambda v: min(255, int(v * GAIN)))
        _bg[(w, h)] = Image.composite(Image.new('RGB', (w, h), EDGE), Image.new('RGB', (w, h), CENTRE), g).filter(ImageFilter.GaussianBlur(2))
    return _bg[(w, h)]

files = sorted(glob.glob(os.path.join(SRC, 'f*.png'))); RB = None
for p in files:
    n = int(os.path.basename(p)[1:5]); t = (n - 1) / FPS
    im = Image.open(p).convert('RGBA')
    if RB is None: RB = ribbon(*im.size)
    out = background(*im.size).convert('RGBA'); out.alpha_composite(im)
    bob = round(3 * math.sin(2 * math.pi * t / (LOOP / 3)))                 # лента чуть покачивается, 3 раза за петлю
    out.alpha_composite(RB, (0, bob))
    out.convert('RGB').save(os.path.join(DST, 'o' + os.path.basename(p)[1:]))
print(len(files), 'frames with ribbon')
