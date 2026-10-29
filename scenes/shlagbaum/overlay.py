"""Окно программы поверх 3D-кадров «Шлагбаума»: блоки в стиле Scratch 3.0 (расширение WeDo 2.0), сцена с машинкой.
Подсвечивается блок, который сейчас выполняется; стрела на сцене и лампа повторяют 3D (сценарий — timeline.py).
  python overlay.py <папка с f*.png> <папка вывода>      (фон — BG_CENTRE / BG_EDGE / BG_GAIN, как у других роликов)"""
import sys, os, glob, json, math
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import timeline as TL

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
LAY = json.load(open(os.path.join(HERE, 'layout.json'), encoding='utf-8'))
WIN = LAY['window']
CW = WIN.get('code_w', 300)                                                     # ширина области блоков
EDGE = tuple(int(v) for v in os.environ.get('BG_EDGE', '255,247,237').split(','))
CENTRE = tuple(int(v) for v in os.environ.get('BG_CENTRE', '255,255,255').split(','))
GAIN = float(os.environ.get('BG_GAIN', '2.0'))
FPS = 24

def font(size, weight='Bold'):
    p = os.path.join(HERE, '..', '..', 'common', 'fonts', 'Nunito-Variable.ttf')
    try:
        f = ImageFont.truetype(p, size); f.set_variation_by_name(weight); return f
    except Exception:
        return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', size - 1)
F13, F12, F14 = font(13), font(12), font(14)
try:
    FARROW = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 13)
except Exception:
    FARROW = F13

EVENT, CONTROL, WEDO, OPER = (255, 191, 0), (255, 171, 25), (15, 189, 140), (89, 192, 89)
def dark(c, k=0.8): return tuple(int(v * k) for v in c)
# (вид, текст, цвет, отступ): программа «КПП работает весь день» из инструкции, блоками Scratch с расширением WeDo 2.0
BLOCKS = [('hat', 'когда щёлкнут по', EVENT, 0), ('c', 'повторять всегда', CONTROL, 0),
          ('lamp', 'цвет лампы:', WEDO, 1, (230, 40, 30), 'красный'),
          ('until', 'ждать до', CONTROL, 1),
          ('lamp', 'цвет лампы:', WEDO, 1, (40, 190, 80), 'зелёный'),
          ('cmd', 'направление мотора: туда', WEDO, 1), ('cmd', 'включить мотор на 2 с', WEDO, 1),
          ('cmd', 'ждать 3 с', CONTROL, 1),
          ('cmd', 'направление мотора: обратно', WEDO, 1), ('cmd', 'включить мотор на 2 с', WEDO, 1)]
BH, GAP, ARM = 24, 2, 14

def stack_block(d, x, y, w, col, h=BH):
    d.rounded_rectangle([x, y, x + w, y + h], 5, fill=col, outline=dark(col), width=1)
    d.rectangle([x + 12, y - 1, x + 28, y + 2], fill=col)                        # «зубчик» сверху, как в Scratch

def flag(d, x, y):
    d.line([x, y, x, y + 14], fill=(40, 110, 40), width=2)
    d.polygon([(x + 1, y), (x + 12, y + 2), (x + 9, y + 5), (x + 12, y + 8), (x + 1, y + 7)], fill=(76, 191, 86))

def code_panel(t):
    w, h = CW, WIN['h'] - 34
    im = Image.new('RGBA', (w, h), (249, 249, 252, 255)); d = ImageDraw.Draw(im)
    for gx in range(10, w, 22):                                                    # точки сетки области скриптов
        for gy in range(10, h, 22): d.point((gx, gy), fill=(225, 228, 238))
    active = TL.block(t); x0, y = 12, 16; boxes = {}
    bw = w - 2 * x0
    for i, b in enumerate(BLOCKS):
        kind, txt, col, ind = b[:4]; x = x0 + ind * ARM; ww = bw - ind * ARM
        if kind == 'hat':
            d.ellipse([x, y - 6, x + 70, y + 16], fill=col, outline=dark(col)); stack_block(d, x, y, ww, col, 28)
            d.text((x + 10, y + 7), txt, font=F13, fill='white'); flag(d, x + 12 + d.textlength(txt, font=F13), y + 7)
            boxes[i] = (x, y - 6, x + ww, y + 28); y += 28 + GAP
        elif kind == 'c':
            top = y; stack_block(d, x, y, ww, col, 22); d.text((x + 10, y + 4), txt, font=F13, fill='white')
            boxes[i] = (x, y, x + ww, y + 22); y += 22; c_top = top; c_col = col
        else:
            stack_block(d, x, y, ww, col)
            d.text((x + 10, y + 5), txt, font=F13, fill='white')
            if kind == 'lamp':
                tx = x + 14 + d.textlength(txt, font=F13)
                d.rounded_rectangle([tx, y + 4, tx + 82, y + BH - 4], 8, fill=dark(col, 0.85))
                d.ellipse([tx + 5, y + 7, tx + 15, y + 17], fill=b[4]); d.text((tx + 20, y + 5), b[5], font=F12, fill='white')
            if kind == 'until':
                tx = x + 14 + d.textlength(txt, font=F13)
                d.polygon([(tx, y + 12), (tx + 8, y + 3), (tx + 148, y + 3), (tx + 156, y + 12), (tx + 148, y + BH - 3), (tx + 8, y + BH - 3)], fill=OPER, outline=dark(OPER))
                d.rounded_rectangle([tx + 12, y + 5, tx + 92, y + BH - 5], 7, fill=WEDO, outline=dark(WEDO))
                d.text((tx + 18, y + 5), 'расстояние', font=F12, fill='white'); d.text((tx + 98, y + 5), '<', font=F13, fill='white')
                d.ellipse([tx + 112, y + 5, tx + 142, y + BH - 5], fill='white'); d.text((tx + 119, y + 5), '10', font=F12, fill=(90, 90, 90))
            boxes[i] = (x, y, x + ww, y + BH); y += BH + GAP
    d.rectangle([x0, c_top + 20, x0 + ARM, y + 2], fill=c_col)                    # «скобка» цикла
    d.rounded_rectangle([x0, y, x0 + bw * 0.55, y + 16], 5, fill=c_col, outline=dark(c_col), width=1)
    d.text((x0 + bw * 0.55 - 18, y - 1), '↻', font=FARROW, fill='white')
    gl = Image.new('RGBA', im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(gl)          # жёлтое свечение у работающего блока
    bx = boxes[active]; gd.rounded_rectangle([bx[0] - 2, bx[1] - 2, bx[2] + 2, bx[3] + 2], 7, outline=(255, 214, 0, 255), width=4)
    glow = gl.filter(ImageFilter.GaussianBlur(3)); im.alpha_composite(glow); im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(0.6)))
    return im

def stage_panel(t):
    w, h = WIN['w'] - CW - 12, 112
    im = Image.new('RGBA', (w, h), (214, 236, 255, 255)); d = ImageDraw.Draw(im)
    gy = int(h * 0.62)
    d.rectangle([0, gy, w, h], fill=(150, 205, 110)); d.rectangle([0, gy + 10, w, gy + 34], fill=(112, 114, 124))
    for i in range(0, w, 26): d.rectangle([i + 4, gy + 21, i + 16, gy + 23], fill='white')
    px, py = int(w * 0.70), gy + 10                                                  # стойка шлагбаума и стрела
    a = math.radians(TL.boom(t)); L = w * 0.40
    tip = (px - L * math.cos(a), py - 30 - L * math.sin(a))
    d.line([px, py - 30, tip[0], tip[1]], fill=(255, 255, 255), width=7)
    for k in range(4):                                                               # красно-белые полоски
        u0, u1 = (k * 2 + 1) / 8, (k * 2 + 2) / 8
        d.line([px - L * u0 * math.cos(a), py - 30 - L * u0 * math.sin(a), px - L * u1 * math.cos(a), py - 30 - L * u1 * math.sin(a)], fill=(225, 50, 40), width=7)
    d.rectangle([px - 4, py - 34, px + 4, py + 6], fill=(70, 72, 80))
    lc = (40, 200, 80) if TL.lamp(t) == 'green' else (235, 45, 35)
    d.ellipse([px - 6, py - 48, px + 6, py - 36], fill=lc)
    v = TL.car(t)
    if v is not None:                                                                # машинка-спрайт
        cx = (0.20 + (v - 0.55) * 1.2) * w; cy = gy + 18
        d.rounded_rectangle([cx - 24, cy - 12, cx + 24, cy + 4], 6, fill=(255, 122, 60), outline=(200, 80, 30))
        d.rounded_rectangle([cx - 13, cy - 24, cx + 13, cy - 9], 6, fill=(255, 150, 95), outline=(200, 80, 30))
        d.rectangle([cx - 8, cy - 21, cx + 8, cy - 13], fill=(200, 232, 255))
        for k in (-14, 14): d.ellipse([cx + k - 7, cy - 1, cx + k + 7, cy + 13], fill=(40, 40, 46)); d.ellipse([cx + k - 3, cy + 3, cx + k + 3, cy + 9], fill=(170, 170, 178))
    m = Image.new('L', im.size, 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, w - 1, h - 1], 8, fill=255); im.putalpha(m)
    return im

def sensor_panel(t, w):
    im = Image.new('RGBA', (w, 70), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    v = TL.car(t)
    dist = 99 if v is None or v > 0.56 else max(6, min(99, int(round((0.55 - v) * 120 + 6))))
    d.rounded_rectangle([0, 0, w - 1, 30], 8, fill=(255, 255, 255), outline=(220, 224, 235))
    d.text((10, 6), 'расстояние', font=F12, fill=(90, 96, 110))
    d.rounded_rectangle([w - 50, 5, w - 8, 25], 10, fill=WEDO); d.text((w - 29 - d.textlength(str(dist), font=F12) / 2, 6), str(dist), font=F12, fill='white')
    d.rounded_rectangle([0, 38, w - 1, 68], 8, fill=(255, 255, 255), outline=(220, 224, 235))
    d.text((10, 44), 'лампа хаба', font=F12, fill=(90, 96, 110))
    lc = (40, 200, 80) if TL.lamp(t) == 'green' else (235, 45, 35)
    d.ellipse([w - 34, 44, w - 16, 62], fill=lc)
    return im

def window(t):
    W, H = WIN['w'], WIN['h']
    im = Image.new('RGBA', (W, H), (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, W, 30], fill=(76, 151, 255))
    d.text((12, 6), 'Шлагбаум с датчиком', font=F14, fill='white')
    for k, c in enumerate([(255, 255, 255, 120)] * 3): d.ellipse([W - 18 - k * 16, 11, W - 10 - k * 16, 19], fill=c)
    im.alpha_composite(code_panel(t), (0, 34))
    st = stage_panel(t); im.alpha_composite(st, (CW + 6, 40))
    im.alpha_composite(sensor_panel(t, st.width), (CW + 6, 40 + st.height + 10))
    d.line([CW, 30, CW, H], fill=(225, 228, 238), width=2)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).rounded_rectangle([0, 0, W - 1, H - 1], 14, fill=255); im.putalpha(m)
    return im

_bg = {}
def background(w, h):
    if (w, h) not in _bg:
        g = Image.radial_gradient('L').resize((w, h), Image.BICUBIC).point(lambda v: min(255, int(v * GAIN)))
        _bg[(w, h)] = Image.composite(Image.new('RGB', (w, h), EDGE), Image.new('RGB', (w, h), CENTRE), g).filter(ImageFilter.GaussianBlur(2))
    return _bg[(w, h)]

def shadow(size, box, r=16, a=60, blur=22, dy=18):
    sh = Image.new('RGBA', size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rounded_rectangle([box[0], box[1] + dy, box[2], box[3] + dy], r, fill=(110, 70, 30, a))
    return sh.filter(ImageFilter.GaussianBlur(blur))

files = sorted(glob.glob(os.path.join(SRC, 'f*.png')))
for p in files:
    n = int(os.path.basename(p)[1:5]); t = (n - 1) / FPS
    im = Image.open(p).convert('RGBA'); out = background(*im.size).convert('RGBA'); out.alpha_composite(im)
    bob = round(3 * math.sin(2 * math.pi * t / 6))
    x, y = WIN['x'], WIN['y'] + bob
    out.alpha_composite(shadow(out.size, (x, y, x + WIN['w'], y + WIN['h'])))
    out.alpha_composite(window(t), (x, y))
    out.convert('RGB').save(os.path.join(DST, 'o' + os.path.basename(p)[1:]))
print(len(files), 'frames with program window')
