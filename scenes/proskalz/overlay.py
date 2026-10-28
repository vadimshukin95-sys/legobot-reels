"""«Ремень проскальзывает»: студийный фон, подписи-пилюли, стрелка ведущего шкива, знак «стоп» на ведомом,
штрихи скольжения ремня, финальная карточка -> out/oNNNN.png. Кадры сцены — frames/fNNNN.png (RGBA, прозрачный фон).
  python overlay.py S E          (кадры после последнего отрендеренного берут его как фон финальной карточки)"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
import importlib.util
_spec = importlib.util.spec_from_file_location('reel_style', os.path.join(HERE, '..', '..', 'common', 'reel_style.py'))
H = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(H)
GRAPH, WHITE = H.GRAPH, H.WHITE

W, Hh = 1080, 1920
TL = json.load(open(os.path.join(HERE, 'timeline.json')))
LAST = TL['render_frames']; END = TL['end']; CAP = TL['captions']
LOGO_PATH = os.path.join(HERE, '..', '..', 'assets', 'logo.png')

# заголовки Nunito Black, как в «Скрипаче»
_FD = os.path.join(HERE, '..', '..', 'common', 'fonts')
H.GREEN, H.GREEN_D = (240, 150, 110), (190, 92, 66)
_cache = {}
def _font(weight, size, kind):
    if kind == 'sym':
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size)
    k = (weight, size)
    if k not in _cache:
        f = ImageFont.truetype(os.path.join(_FD, 'Nunito-Variable.ttf'), size)
        f.set_variation_by_name('Black' if weight >= 900 else 'ExtraBold')
        _cache[k] = f
    return _cache[k]
H.font = _font

PASTEL = {'hook': (250, 214, 165), 'white': (255, 252, 246), 'blue': (205, 228, 245), 'green': (214, 236, 200),
          'pink': (246, 205, 211)}
LIME, ORANGE = (110, 176, 20), (240, 122, 18)
BG_TOP, BG_BOT = (244, 239, 230), (226, 214, 196)

def gradient():
    a = np.linspace(0, 1, Hh)[:, None, None]
    top, bot = np.array(BG_TOP, float), np.array(BG_BOT, float)
    img = (top + (bot - top) * a) * np.ones((1, W, 1))
    return Image.fromarray(img.astype(np.uint8), 'RGB')
BG = gradient()

def arrow_arc(cv, c, rad, a0, a1, cw, col, alpha=1.0):
    """дуга-стрелка вокруг центра c (пиксели) от a0 до a1 (градусы PIL: 0 вправо, 90 вниз); остриё по ходу вращения"""
    if alpha <= 0:
        return
    angs = np.linspace(a0, a1, 32) if cw else np.linspace(a1, a0, 32)
    pts = [(c[0] + rad * math.cos(math.radians(t)), c[1] + rad * math.sin(math.radians(t))) for t in angs]
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    a, b = np.array(pts[-2]), np.array(pts[-1]); v = b - a; v /= (np.linalg.norm(v) or 1); n = np.array([-v[1], v[0]])
    for w, cc in ((24, GRAPH), (13, col)):
        d.line(pts, fill=cc + (255,), width=w, joint='curve')
    tip = b + v * 38
    d.polygon([tuple(tip), tuple(b + n * 29), tuple(b - n * 29)], fill=GRAPH + (255,))
    d.polygon([tuple(b + v * 22), tuple(b + n * 17 - v * 4), tuple(b - n * 17 - v * 4)], fill=col + (255,))
    if alpha < 1:
        lay.putalpha(lay.getchannel('A').point(lambda x: int(x * alpha)))
    cv.alpha_composite(lay)

def fade(f, f0, f1, k=6):
    return max(0.0, min(1.0, (f - f0) / k, (f1 - f) / k))

RED = (226, 64, 52)
def stop_badge(cv, c, rad, alpha):
    """красный кружок с белой полосой — «стоит»"""
    if alpha <= 0:
        return
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    x, y = c
    d.ellipse([x - rad - 6, y - rad - 6, x + rad + 6, y + rad + 6], fill=GRAPH + (255,))
    d.ellipse([x - rad, y - rad, x + rad, y + rad], fill=RED + (255,))
    w, h = rad * 0.62, rad * 0.20
    d.rounded_rectangle([x - w, y - h, x + w, y + h], radius=int(h), fill=(255, 255, 255, 255))
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v * alpha)))
    cv.alpha_composite(lay)

def slip_marks(cv, c, rad, f, alpha):
    """короткие штрихи по низу ведущего шкива, бегут по ходу вращения — шкив скользит внутри ремня"""
    if alpha <= 0:
        return
    lay = Image.new('RGBA', cv.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    ph = (f * 9) % 40
    for base in (20, 60, 100, 140):
        a0 = base + ph
        if not 15 <= a0 <= 165:
            continue
        angs = np.linspace(a0, a0 + 16, 8)
        pts = [(c[0] + rad * math.cos(math.radians(t)), c[1] + rad * math.sin(math.radians(t))) for t in angs]
        d.line(pts, fill=GRAPH + (255,), width=12, joint='curve')
        d.line(pts, fill=(255, 255, 255, 255), width=6, joint='curve')
    lay.putalpha(lay.getchannel('A').point(lambda v: int(v * alpha)))
    cv.alpha_composite(lay)

def logo_tile():
    lg = Image.open(LOGO_PATH).convert('RGBA')
    lg = lg.resize((300, int(lg.height * 300 / lg.width)), Image.LANCZOS)
    T = Image.new('RGBA', (lg.width + 60, lg.height + 50), (0, 0, 0, 0))
    d = ImageDraw.Draw(T)
    d.rounded_rectangle([8, 12, T.width - 2, T.height - 2], 40, fill=(0, 0, 0, 80))
    d.rounded_rectangle([0, 0, T.width - 10, T.height - 14], 40, fill=(255, 255, 255, 245))
    T.alpha_composite(lg, (25, 18))
    return T

def pill(lines, role, size):
    return H.pill(lines, PASTEL[role], GRAPH, size)

def main(s, e):
    proj = json.load(open(os.path.join(HERE, 'proj.json'))) if os.path.exists(os.path.join(HERE, 'proj.json')) else {}
    fdir = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'))
    out_dir = os.path.join(HERE, os.environ.get('OVL_OUT_DIR', 'out'))
    os.makedirs(out_dir, exist_ok=True)
    C_HOOK = pill(['Вентилятор застрял…'], 'hook', 60)
    C_SLIP = pill(['Мотор крутится,', 'ремень проскальзывает'], 'green', 54)
    C_SUM = pill(['Это не поломка.', 'Ремень бережёт мотор'], 'blue', 58)
    T_END = H.volume_title(['МЕХАНИЗМЫ', 'WEDO 2.0'], 120)
    C_END = pill(['простыми словами'], 'green', 60)
    C_CTA = pill(['legobot.ru'], 'pink', 66)
    LOGO = logo_tile()
    clean = bool(os.environ.get('CLEAN'))                     # чистая версия: без подписей и стрелок
    s0, s1 = CAP['slip']
    for f in range(s, e + 1):
        src = os.path.join(fdir, f'f{min(f, LAST):04d}.png')
        fr = Image.open(src).convert('RGBA')
        if fr.size != (W, Hh):
            fr = fr.resize((W, Hh), Image.LANCZOS)
        cv = BG.convert('RGBA'); cv.alpha_composite(fr)
        if f >= END:                                           # финальная карточка: модель уходит в мягкое размытие
            k = min(1.0, (f - END + 1) / 14)
            base = cv.convert('RGB')
            base = Image.blend(base, base.filter(ImageFilter.GaussianBlur(16)), k)
            base = Image.blend(base, Image.new('RGB', base.size, (248, 244, 236)), 0.5 * k)
            cv = base.convert('RGBA')
        p = proj.get(str(min(f, LAST)))
        if p and f < END and not clean:
            lo = (p['low'][0] * W, (1 - p['low'][1]) * Hh); hi = (p['high'][0] * W, (1 - p['high'][1]) * Hh)
            rr = p['r'] * 1.28
            if s0 + 4 <= f <= s1:
                al = fade(f, s0 + 4, s1)
                arrow_arc(cv, lo, rr, 25, 150, True, LIME, al)              # ведущий крутится (по часовой)
                slip_marks(cv, lo, p['r'] * 0.93, f, al * 0.9)
                stop_badge(cv, (hi[0] + rr * 0.80, hi[1] - rr * 0.80), rr * 0.30, al)
        if clean:
            cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)
            continue
        H.place(cv, C_HOOK, W / 2, 300, f, *CAP['hook'], rot=-1.5, wobble=0.6)
        H.place(cv, C_SLIP, W / 2, 210, f, *CAP['slip'], rot=1.2, wobble=0.5)
        H.place(cv, C_SUM, W / 2, 300, f, *CAP['sum'], rot=1.5, wobble=0.6)
        H.place(cv, LOGO, W / 2, 470, f, END + 4, 999, rot=-3, wobble=1.0, intro=9)
        H.place(cv, T_END, W / 2, 900, f, END + 8, 999, rot=-2, wobble=0.6)
        H.place(cv, C_END, W / 2, 1120, f, END + 14, 999, rot=1.5, wobble=0.5)
        H.place(cv, C_CTA, W / 2, 1560, f, END + 22, 999, rot=-1.5, wobble=0.5)
        cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
