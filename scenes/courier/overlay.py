"""Robot-courier reel: volume titles, cartoon caption stickers, foot-path trace, sensor rings, logo -> out/ PNGs."""
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
    stop, go = TL['stop'], TL['go']
    T1 = volume_title(['РОБОТ-КУРЬЕР'], 118)
    T2 = volume_title(['ДОСТАВЛЕНО!'], 128)
    T4 = volume_title(['СОБЕРИ САМ!'], 122)
    C0 = pill(['Как он шагает?'], YEL, GRAPH, 64)
    C1 = pill(['Мотор крутит червяк'], WHITE, GRAPH, 58)
    C2 = pill(['24 оборота мотора =', '1 оборот шестерни'], ORANGE, WHITE, 54)
    C3 = pill(['Шкив с пальцем', 'водит ногу по кругу'], WHITE, GRAPH, 56)
    C4 = pill(['Ремень крутит', 'обе оси вместе'], YEL, GRAPH, 56)
    C5 = pill(['Ноги шагают', 'по очереди'], GREEN, WHITE, 60)
    C6 = pill(['Датчик видит ладонь —', 'стоп!'], WHITE, GRAPH, 56)
    C7 = pill(['Ждёт 3 секунды', 'и идёт дальше'], YEL, GRAPH, 56)
    C8 = pill(['Инструкция доступна', 'в разделе legobot.ru/free'], GREEN, WHITE, 54)
    LOGO = logo_tile()
    t0, t1 = TL['trace']
    for f in range(s, e + 1):
        src = os.path.join(HERE, os.environ.get('OVL_FRAMES_DIR', 'frames'), f'f{f:04d}.png')
        cv = Image.open(src).convert('RGB').resize((W, Hh), Image.LANCZOS).convert('RGBA')
        p = proj[str(f)]
        # foot path: the sole runs a circle and stays level
        if t0 + 6 <= f <= t1 - 2 and 'trace' in p:
            pts = [(x * W, (1 - y) * Hh) for x, y in p['trace']]
            dashed(cv, pts, f)
            fx, fy = p['foot']; dot(cv, fx * W, (1 - fy) * Hh)
        if stop - 12 <= f <= stop + 6:
            sx, sy = p['sensor']
            rings(cv, sx * W, (1 - sy) * Hh, f, stop - 12, rmax=150, col=(51, 224, 90))
        place(cv, T1, W / 2, 300, f, 3, 80, rot=-2, wobble=0.6)
        place(cv, C0, W / 2, 1640, f, 14, 80, rot=1.5, wobble=0.8)
        place(cv, C1, W / 2, 1640, f, 92, 124, rot=-1.5, wobble=0.8)
        place(cv, C2, W / 2, 1640, f, 126, 162, rot=1.2, wobble=0.6)
        place(cv, C3, W / 2, 1640, f, 172, 206, rot=-1.2, wobble=0.6)
        place(cv, C4, W / 2, 1640, f, 208, 242, rot=1.4, wobble=0.6)
        place(cv, C5, W / 2, 1640, f, 252, 296, rot=-1.5, wobble=0.8)
        place(cv, C6, W / 2, 1640, f, stop - 6, stop + 34, rot=1.2, wobble=0.6, intro=5)
        if stop <= f <= stop + 64:
            jit = 5 * math.sin(f * 2.1) if f < stop + 12 else 0
            place(cv, T2, W / 2 + jit, 300, f, stop, stop + 64, rot=-3, wobble=1.2, intro=5)
        place(cv, C7, W / 2, 1640, f, stop + 36, go, rot=-1.2, wobble=0.6)
        place(cv, LOGO, 250, 300, f, go + 6, 999, rot=-4, wobble=1.0, intro=9)
        place(cv, T4, W / 2, 1380, f, go + 8, 999, rot=-3, wobble=0.6)
        place(cv, C8, W / 2, 1650, f, go + 14, 999, rot=1.5, wobble=0.5)
        cv.convert('RGB').save(os.path.join(out_dir, f'o{f:04d}.png'), compress_level=1)

if __name__ == '__main__':
    main(int(sys.argv[1]), int(sys.argv[2]))
