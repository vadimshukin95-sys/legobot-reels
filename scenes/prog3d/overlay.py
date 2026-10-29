"""Сборка кадров /prog: фон первого экрана + картинки экранов (screens.py) по углам из screens.json + 3D-рендер сверху.
Экраны в рендере прозрачные (holdout), поэтому картинка видна только там, где её не закрывает рамка или робот.
  python overlay.py <папка с f*.png и screens.json> <папка вывода>"""
import sys, os, glob, json
import numpy as np
from PIL import Image, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import screens as SC
SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
EDGE = tuple(int(v) for v in os.environ.get('BG_EDGE', '232,244,249').split(','))
CENTRE = tuple(int(v) for v in os.environ.get('BG_CENTRE', '246,251,253').split(','))
GAIN = float(os.environ.get('BG_GAIN', '2.0'))
FPS = SC.FPS
QUADS = json.load(open(os.path.join(SRC, 'screens.json')))

_bg = {}
def background(w, h):
    if (w, h) not in _bg:
        g = Image.radial_gradient('L').resize((w, h), Image.BICUBIC).point(lambda v: min(255, int(v * GAIN)))
        _bg[(w, h)] = Image.composite(Image.new('RGB', (w, h), EDGE), Image.new('RGB', (w, h), CENTRE), g).filter(ImageFilter.GaussianBlur(2))
    return _bg[(w, h)]

def coeffs(dst, src):
    A = []
    for (x, y), (u, v) in zip(dst, src):
        A += [[x, y, 1, 0, 0, 0, -u * x, -u * y], [0, 0, 0, x, y, 1, -v * x, -v * y]]
    return np.linalg.solve(np.array(A, float), np.array(src, float).reshape(8))

def put(out, img, quad, grow=1.5):
    """Картинка экрана в четырёхугольник quad (пиксели, TL TR BR BL), чуть шире — под край holdout."""
    q = np.array(quad, float); c = q.mean(0)
    q = c + (q - c) * (1 + grow / max(1.0, np.linalg.norm(q[1] - q[0]) / 2))
    wq = max(np.linalg.norm(q[1] - q[0]), np.linalg.norm(q[2] - q[3]))
    sc = min(1.0, wq * 1.15 / img.width)                                    # сначала уменьшаем до размера на экране
    if sc < 1.0: img = img.resize((max(8, int(img.width * sc)), max(8, int(img.height * sc))), Image.LANCZOS)
    w, h = img.size
    x0, y0 = np.floor(q.min(0)).astype(int) - 2; x1, y1 = np.ceil(q.max(0)).astype(int) + 2
    W, H = x1 - x0, y1 - y0
    loc = [(x - x0, y - y0) for x, y in q]
    tile = img.convert('RGBA').transform((W, H), Image.PERSPECTIVE, tuple(coeffs(loc, [(0, 0), (w, 0), (w, h), (0, h)])), Image.BICUBIC)
    out.alpha_composite(tile, (int(x0), int(y0)))

files = sorted(glob.glob(os.path.join(SRC, 'f*.png')))
for p in files:
    n = int(os.path.basename(p)[1:5]); t = (n - 1) / FPS
    im = Image.open(p).convert('RGBA'); W, H = im.size
    out = background(W, H).convert('RGBA')
    for name, fn in SC.SCREENS.items():
        quad = [(x * W, y * H) for x, y in QUADS[str(n)][name]]
        put(out, fn(t), quad)
    out.alpha_composite(im)
    out.convert('RGB').save(os.path.join(DST, 'o' + os.path.basename(p)[1:]))
print(len(files), 'frames composed')
