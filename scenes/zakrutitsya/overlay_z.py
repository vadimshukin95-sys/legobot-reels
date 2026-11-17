"""«Закрутится?» — сборка кадров рилса: кадр модели из Blender на весь экран (камера крючка), 2D-наезд и дрожь,
заголовок, стрелки вращения (по проекции камеры, proj.json), подписи-стикеры, логотип; последний кадр = первый (петля).
python overlay_z.py hook PLATE.png OUT.png             — один кадр крючка
python overlay_z.py reel STATES_DIR OUT_DIR [кадры]     — кадры ролика o0000.png…"""
import os, sys, math, json, numpy as np
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', 'pila'))
import reelkit as K
import timeline_z as TL

W, H = 1080, 1920
MY = int(os.environ.get('MY', '0'))
SUNC, GREEN, REDC, WHITE = (245, 197, 24), (52, 168, 83), (236, 72, 58), (255, 255, 255)
TITLE_IM, STICK, LOGO = None, {}, None
PJ = json.load(open(os.path.join(HERE, 'proj.json')))['uv'] if os.path.exists(os.path.join(HERE, 'proj.json')) else {}


def ease(u):
    u = min(1.0, max(0.0, u)); return u * u * (3 - 2 * u)


def pop(u):
    if u <= 0: return 0
    if u >= 1: return 1
    return 1 + 0.08 * math.sin(u * math.pi) if u > 0.55 else (1 - (1 - u / 0.55) ** 3) * 1.04


def paste_scaled(img, src, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01: return
    w, h = max(1, int(src.width * s)), max(1, int(src.height * s))
    im = src.resize((w, h), Image.LANCZOS)
    if alpha < 1: im.putalpha(im.split()[-1].point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def title_lines():
    global TITLE_IM
    if TITLE_IM is None:
        TITLE_IM = []
        for text, size in TL.TITLE:
            im = Image.new('RGBA', (1500, 260), (0, 0, 0, 0))
            K.tracked(im, (750, 40), text, K.font(size), WHITE, K.INK, 7 if size > 100 else 6, track=3,
                      shadow=((35, 41, 44), (0, 12 if size > 100 else 10)))
            TITLE_IM.append(im.crop(im.getbbox()))
    return TITLE_IM


def draw_title(img, alpha=1.0, scale=1.0):
    y = 190
    for im in title_lines():
        paste_scaled(img, im, 540, y + im.height / 2, scale, alpha); y += im.height + 26


def sticker_img(text, style):
    key = (text, style)
    if key not in STICK:
        im = Image.new('RGBA', (1080, 600), (0, 0, 0, 0))
        if style == 'sun':
            K.sticker(im, 540, 300, text, K.font(60, 'xb'), K.SUN, K.INK, tilt=-2)
        else:
            K.sticker(im, 540, 300, text, K.font(76, 'black'), K.LIME, K.INK, pad=(44, 24), radius=34, tilt=1)
        STICK[key] = im.crop(im.getbbox())
    return STICK[key]


def draw_caps(img, t):
    for a, b, text, st in TL.CAPS:
        if a <= t < b + 0.2:
            al = 1.0 if t < b else max(0, 1 - (t - b) / 0.2)
            paste_scaled(img, sticker_img(text, st), 540, 1660, pop((t - a) / 0.3), al)


def logo():
    global LOGO
    if LOGO is None: LOGO = K.logo_round(size=170)
    return LOGO


# ------------------------------------------------------------------ 2D-камера: наезд и дрожь
def cam2d(t):
    """(масштаб, сдвиг x, сдвиг y) кадра модели; центр масштаба — угол O"""
    if t < TL.T_PUSH[1]:
        s = 1.0 + 0.07 * ease(t / TL.T_PUSH[1])
    elif t < TL.T_END[0]:
        s = 1.07
    else:
        s = 1.07 - 0.07 * ease((t - TL.T_END[0]) / (TL.T_END[1] - TL.T_END[0] - 1 / TL.FPS))
    dx = dy = 0.0
    if TL.T_JAM[0] <= t < TL.T_JAM[1] and (t - TL.T_JAM[0]) % 1.0 < 0.62:
        f = int(t * TL.FPS); rng = np.random.default_rng(f)
        dx, dy = rng.uniform(-7, 7), rng.uniform(-5, 5)
    return s, dx, dy


def xf(p, cam):
    s, dx, dy = cam; o = PJ['O'][0]
    return (o[0] + (p[0] - o[0]) * s + dx, o[1] + (p[1] - o[1]) * s + dy + MY)


def model_layer(states, name, cam):
    im = Image.open(os.path.join(states, f'{name}.png')).convert('RGBA')
    if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
    s, dx, dy = cam; o = PJ['O'][0]
    w, h = int(W * s), int(H * s)
    big = im.resize((w, h), Image.LANCZOS) if s != 1 else im
    x0 = int(round(o[0] - o[0] * s + dx)); y0 = int(round(o[1] - o[1] * s + dy))
    return big, (x0, y0)


# ------------------------------------------------------------------ стрелки
def arrowhead(d, tip, direction, col, size=34):
    v = np.array(direction, float); v /= (np.linalg.norm(v) + 1e-9); n = np.array([-v[1], v[0]])
    a = np.array(tip)
    d.polygon([tuple(a + v * 6), tuple(a - v * size + n * size * 0.62), tuple(a - v * size - n * size * 0.62)], fill=col)


def arc_pts(key, a0, span, sign, u):
    """дуга по точкам proj.json (шаг 6°): от a0 на span градусов, sign — направление обхода; u — доля прорисовки"""
    P = PJ[key]; n = len(P) - 1
    idx = [int(round(((a0 + sign * k) % 360) / 6)) % n for k in np.linspace(0, span * u, max(2, int(span * u / 6) + 1))]
    return [P[i] for i in idx]


def draw_arrow_path(lay, pts, col, cam, w=12):
    if len(pts) < 2: return
    d = ImageDraw.Draw(lay)
    q = [xf(p, cam) for p in pts]
    d.line(q, fill=WHITE + (255,), width=w + 10, joint='curve')
    tip, back = np.array(q[-1]), np.array(q[-3] if len(q) > 2 else q[0])
    arrowhead(d, tip + (tip - back) / (np.linalg.norm(tip - back) + 1e-9) * 3, tip - back, WHITE + (255,), 44)
    d.line(q, fill=col + (255,), width=w, joint='curve')
    arrowhead(d, tip, tip - back, col + (255,), 34)


# Правило правой руки (proj.json: u × v = ось). Мотор крутит C в «+» (жёлтая дуга); C поворачивает A и B навстречу себе,
# и в точке касания A–B зуб A тянет вниз, зуб B — вверх (красные стрелки): спор.
def draw_expl(img, t, cam):
    if not (TL.T_EXPL[0] <= t < TL.T_EXPL[1] + 0.25): return
    fade = 1.0 if t < TL.T_EXPL[1] else max(0, 1 - (t - TL.T_EXPL[1]) / 0.25)
    lay = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw_arrow_path(lay, arc_pts('arcC', 130, 190, +1, ease((t - 6.0) / 0.7)), SUNC, cam, w=12)
    if t >= 8.6:
        u = ease((t - 8.6) / 0.35); blink = int((t - 8.6) * 4) % 2 == 0 or t > 9.8
        for key in ('confA', 'confB'):
            p0, p1 = np.array(PJ[key][0]), np.array(PJ[key][1]); m = (p0 + p1) / 2; p0, p1 = m + (p0 - m) * 0.7, m + (p1 - m) * 0.7
            draw_arrow_path(lay, [list(p0), list(p0 + (p1 - p0) * max(0.08, u))], REDC if blink else (255, 150, 140), cam, w=14)
    if fade < 1: lay.putalpha(lay.split()[-1].point(lambda v: int(v * fade)))
    img.alpha_composite(lay)


# ------------------------------------------------------------------ кадр
def frame(i, states):
    t = i / TL.FPS
    cam = cam2d(t)
    img = K.bg_studio().convert('RGBA')
    big, xy = model_layer(states, TL.state_at(t), cam)
    img.paste(big, xy, big)
    # заголовок: 0–6 с, потом гаснет; к концу — снова (петля)
    if t < 6.0:
        draw_title(img, 1.0 if t < 5.7 else (6.0 - t) / 0.3)
    elif t >= TL.T_END[0]:
        draw_title(img, ease((t - TL.T_END[0]) / 0.4))
    draw_expl(img, t, cam)
    draw_caps(img, t)
    if 13.6 <= t < 14.7:            # логотип — коротко, до возврата заголовка
        al = min(1, (t - 13.6) / 0.25, (14.7 - t) / 0.25)
        paste_scaled(img, logo(), 540, 1700, pop((t - 13.6) / 0.3), al)
    return img.convert('RGB')


def hook(plate, out):
    img = K.bg_studio().convert('RGBA')
    pl = Image.open(plate).convert('RGBA')
    img.alpha_composite(pl if pl.height + MY >= 1920 else K.soften_plate(pl), (0, MY))
    draw_title(img)
    img.convert('RGB').save(out)


if __name__ == '__main__':
    if sys.argv[1] == 'hook':
        hook(sys.argv[2], sys.argv[3])
    elif sys.argv[1] == 'reel':
        states, out = sys.argv[2], sys.argv[3]
        os.makedirs(out, exist_ok=True)
        fr = list(map(int, sys.argv[4].split(','))) if len(sys.argv) > 4 else range(TL.FRAMES)
        for i in fr:
            frame(i, states).save(os.path.join(out, f'o{i:04d}.png'))
