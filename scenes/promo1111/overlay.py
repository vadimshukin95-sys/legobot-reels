"""Рилс «Чёрная пятница 11.11 · 1+1=3»: графитовый фон с шипами + 3D + подписи, вспышка подарка, финальная карточка.
  python overlay.py <папка с f*.png и proj.json> <папка вывода>"""
import sys, os, glob, json, math
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('reel_style', os.path.join(HERE, '..', '..', 'common', 'reel_style.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
TL = LAY['timeline']
FPS = 24
def F(sec): return int(round(sec * FPS)) + 1
W, Hh = 1080, 1920
GRAPH, WHITE = H.GRAPH, H.WHITE
ORANGE = (245, 159, 0)
PROJ = json.load(open(os.path.join(SRC, 'proj.json')))

# объёмные заголовки — в оранжевом цвете акции (общий стиль рилсов: белое лицо, объём, графитовый контур)
H.GREEN, H.GREEN_D = (255, 178, 40), (196, 112, 0)
T_TOP = H.volume_title(['ЧЁРНАЯ ПЯТНИЦА', '11.11'], 104)
T_EQ = H.volume_title(['1+1=3'], 210)
N1 = H.pill(['1 · WeDo 2.0'], WHITE, GRAPH, 54)
N2 = H.pill(['+1 · SPIKE Prime'], WHITE, GRAPH, 54)
N3 = H.pill(['=3 · в подарок!'], ORANGE, WHITE, 58)
C1 = H.pill(['Два материала в корзину —', 'третий выбираете сами'], WHITE, GRAPH, 50)
C2 = H.pill(['Подарок — на любую платформу'], WHITE, GRAPH, 50)
K1 = H.pill(['ЧЁРНАЯ ПЯТНИЦА 11.11'], WHITE, GRAPH, 56)
K2 = H.pill(['до 12 ноября · legobot.ru'], ORANGE, WHITE, 60)
lg = Image.open(H.LOGO_PATH).convert('RGBA')
lg = lg.resize((330, int(lg.height * 330 / lg.width)), Image.LANCZOS)
LOGO = Image.new('RGBA', (lg.width + 60, lg.height + 50), (0, 0, 0, 0))
_d = ImageDraw.Draw(LOGO)
_d.rounded_rectangle([8, 12, LOGO.width - 2, LOGO.height - 2], 40, fill=(0, 0, 0, 90))
_d.rounded_rectangle([0, 0, LOGO.width - 10, LOGO.height - 14], 40, fill=(255, 255, 255, 248))
LOGO.alpha_composite(lg, (25, 18))

def background():
    """графит с мягким светлым центром и еле заметными шипами LEGO"""
    g = Image.radial_gradient('L').resize((W, Hh), Image.BICUBIC)
    bg = Image.composite(Image.new('RGB', (W, Hh), (34, 36, 41)), Image.new('RGB', (W, Hh), (72, 76, 86)), g)
    st = Image.new('RGBA', (W, Hh), (0, 0, 0, 0)); d = ImageDraw.Draw(st)
    for y in range(24, Hh, 54):
        for x in range(24, W, 54):
            d.ellipse([x - 13, y - 13, x + 13, y + 13], fill=(255, 255, 255, 9))
            d.arc([x - 13, y - 13, x + 13, y + 13], 200, 340, fill=(255, 255, 255, 14), width=2)
    out = bg.convert('RGBA'); out.alpha_composite(st)
    return out
BG = background()

def clampx(sp, x, pad=26):
    return max(sp.width / 2 + pad, min(W - sp.width / 2 - pad, x))

def proj(f, key):
    k = str(f if f % 2 else f - 1)
    rec = PROJ.get(k) or PROJ[min(PROJ, key=lambda s: abs(int(s) - f))]
    x, y = rec[key]; return x * W, y * Hh

def burst(cv, cx, cy, f, f0, dur=16):
    """вспышка подарка: оранжевые лучи и искры"""
    t = (f - f0) / dur
    if not 0 <= t <= 1:
        return
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a = int(255 * (1 - t))
    for i in range(14):
        ang = 2 * math.pi * i / 14 + 0.2
        r0, r1 = 60 + 260 * t, 120 + 380 * t
        d.line([(cx + r0 * math.cos(ang), cy + r0 * math.sin(ang)), (cx + r1 * math.cos(ang), cy + r1 * math.sin(ang))],
               fill=ORANGE + (a,), width=12)
    for i in range(22):
        ang = 2 * math.pi * i / 22; r = 90 + 330 * t + 30 * math.sin(i * 1.7)
        x, y = cx + r * math.cos(ang), cy + r * math.sin(ang); s = 9 * (1 - t) + 3
        d.ellipse([x - s, y - s, x + s, y + s], fill=(255, 230, 150, a))
    cv.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1)))

def dim(cv, f, f0, dur=12, amax=0.84):
    t = min(1.0, max(0.0, (f - f0) / dur))
    if t <= 0:
        return
    cv.alpha_composite(Image.new('RGBA', cv.size, (30, 32, 37, int(255 * amax * t))))

f_sk, f_pr, f_box = F(TL['skripach_drop']), F(TL['printer_drop']), F(TL['box_drop'])
f_pop, f_card = F(TL['lid_pop']), F(TL['card'])
f_drv, f_turn = F(TL['drive'][0]), F(TL['turn'][0])
files = sorted(glob.glob(os.path.join(SRC, 'f*.png')))
for p in files:
    n = int(os.path.basename(p)[1:5])
    im = Image.open(p).convert('RGBA')
    if im.size != (W, Hh):
        im = im.resize((W, Hh), Image.LANCZOS)
    cv = BG.copy(); cv.alpha_composite(im)
    H.place(cv, T_TOP, W / 2, 250, n, 3, f_card - 2, rot=-2, wobble=0.5, intro=8)
    x, y = proj(n, 'sk'); H.place(cv, N1, clampx(N1, x), max(y - 40, 470), n, f_sk + 16, f_card - 2, rot=-3, wobble=0.6)
    x, y = proj(n, 'pr'); H.place(cv, N2, clampx(N2, x), max(y - 40, 470), n, f_pr + 16, f_card - 2, rot=3, wobble=0.6)
    bx, by = proj(n, 'box')
    if f_pop - 2 <= n <= f_pop + 18:
        burst(cv, bx, by + 120, n, f_pop - 2)
    x, y = proj(n, 'go'); H.place(cv, N3, clampx(N3, x), max(min(y - 30, Hh - 520), 560), n, f_pop + 6, f_card - 2, rot=-2, wobble=0.9)
    H.place(cv, C1, W / 2, 1690, n, f_drv, f_turn + 10, rot=1.2, wobble=0.5)
    H.place(cv, C2, W / 2, 1690, n, f_turn + 12, f_card - 2, rot=-1.2, wobble=0.5)
    # финальная карточка
    dim(cv, n, f_card)
    H.place(cv, LOGO, W / 2, 470, n, f_card + 4, 9999, rot=-3, wobble=0.8, intro=9)
    H.place(cv, T_EQ, W / 2, 860, n, f_card + 8, 9999, rot=-2, wobble=0.6, intro=9)
    H.place(cv, K1, W / 2, 1150, n, f_card + 12, 9999, rot=1.5, wobble=0.5)
    H.place(cv, K2, W / 2, 1320, n, f_card + 16, 9999, rot=-1.5, wobble=0.5)
    cv.convert('RGB').save(os.path.join(DST, 'o' + os.path.basename(p)[1:]), compress_level=1)
print(len(files), 'frames composed')
