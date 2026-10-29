"""Картинки трёх экранов (Scratch, Python, браузер) для 3D-петли /prog. 440×340 — пропорции экрана монитора 280×216 LDU.
В 3D экраны — «дырки» (holdout); overlay.py подкладывает эти картинки под рендер по углам экранов из screens.json.
  python screens.py <t>  -> пробная картинка всех трёх экранов в момент t"""
import math, os, sys
from PIL import Image, ImageDraw, ImageFilter, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from timeline import *
ACC, ORANGE = (58, 158, 194), (245, 159, 0)
FB, FR = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FM = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
_f = {}
def F(path, s):
    if (path, s) not in _f: _f[(path, s)] = ImageFont.truetype(path, s)
    return _f[(path, s)]
WW, WH = 440, 340

def frame(title, bar, dark=False):
    im = Image.new('RGBA', (WW, WH), (30, 32, 44, 255) if dark else (255, 255, 255, 255)); d = ImageDraw.Draw(im)
    d.rectangle([0, 0, WW, 34], fill=bar)
    for k, c in enumerate([(255, 95, 87), (255, 189, 46), (40, 200, 64)]): d.ellipse([12 + k * 20, 11, 24 + k * 20, 23], fill=c)
    d.text((80, 8), title, font=F(FB, 15), fill='white')
    return im, d

def rings(im, cx, cy, t0, t, col=(255, 255, 255), dur=0.6, n=3):     # расходящиеся круги (клик, вход/выход робота)
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for i in range(n):
        u = (t - t0 - i * 0.12) / dur
        if 0 < u < 1:
            r = 12 + 190 * u; a = int(190 * (1 - u))
            d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=col + (a,), width=5)
    im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.2)))

BLOCKS = [('hat', 'когда щёлкнут по ⚑', (255, 191, 0), 0), ('c', 'повторять всегда', (255, 171, 25), 0),
          ('cmd', 'идти 10 шагов', (76, 151, 255), 1), ('cmd', 'изменить y на 40', (76, 151, 255), 1),
          ('cmd', 'если касается края, оттолкнуться', (76, 151, 255), 1), ('cmd', 'включить звук «бип»', (207, 99, 207), 1)]
def scratch(t):
    im, d = frame('Scratch — игра', (76, 151, 255))
    d.rectangle([0, 34, WW, WH], fill=(249, 249, 252))
    for gx in range(12, WW, 22):
        for gy in range(46, WH, 22): d.point((gx, gy), fill=(222, 226, 236))
    fade = 1 - seg(t, *SCR_FADE)
    y = 66
    for i, (kind, txt, col, ind) in enumerate(BLOCKS):
        a = SCR_BLOCK0 + i * SCR_STEP                                   # блок прилетает сверху и защёлкивается
        k = seg(t, a, a + 0.35) * fade
        if k <= 0: y += 34 + (6 if kind == 'hat' else 0); continue
        dy = (1 - k) * -60
        x = 22 + ind * 16; w = 330 - ind * 16; h = 30; yy = y + dy + (6 if kind == 'hat' else 0)
        dk = tuple(int(v * .8) for v in col); al = int(255 * k)
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
        if kind == 'hat': ld.ellipse([x, yy - 12, x + 80, yy + 14], fill=col + (al,), outline=dk + (al,))
        ld.rounded_rectangle([x, yy, x + w, yy + h], 6, fill=col + (al,), outline=dk + (al,), width=2)
        ld.text((x + 12, yy + 6), txt, font=F(FB, 14), fill=(255, 255, 255, al))
        im.alpha_composite(lay); y += 34 + (6 if kind == 'hat' else 0)
    if fade > 0 and t >= SCR_GLOW:                                     # скрипт запущен — пульсирующая жёлтая обводка
        g = 0.55 + 0.45 * math.sin((t - SCR_GLOW) * 7); a = int(200 * seg(t, SCR_GLOW, SCR_GLOW + 0.2) * fade * g)
        lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(lay).rounded_rectangle([16, 46, 358, 276], 10, outline=(255, 214, 0, a), width=4)
        im.alpha_composite(lay.filter(ImageFilter.GaussianBlur(1.5)))
    if t >= SCR_ENTER - 0.05: rings(im, WW / 2, WH / 2 + 10, SCR_ENTER, t, (76, 151, 255), 0.7)
    return im

PY = [[('def ', (198, 120, 221)), ('jump', (97, 175, 239)), ('(hero):', (220, 223, 228))],
      [('    hero.y ', (220, 223, 228)), ('-= ', (86, 182, 194)), ('40', (209, 154, 102))],
      [('    print', (97, 175, 239)), ('(', (220, 223, 228)), ('"Прыжок!"', (152, 195, 121)), (')', (220, 223, 228))],
      [],
      [('for ', (198, 120, 221)), ('step ', (220, 223, 228)), ('in ', (198, 120, 221)), ('range', (97, 175, 239)), ('(10):', (220, 223, 228))],
      [('    hero.x ', (220, 223, 228)), ('+= ', (86, 182, 194)), ('10', (209, 154, 102))],
      [('    jump', (97, 175, 239)), ('(hero)', (220, 223, 228))]]
PY_N = sum(len(''.join(s for s, _ in ln)) + 1 for ln in PY)
def python(t):
    im, d = frame('main.py — Python', (55, 118, 171), dark=True)
    n = int(PY_N * seg(t, *PY_TYPE) * (1 - seg(t, *PY_CLEAR)) + 0.5) if t >= PY_TYPE[0] else 0
    if t >= PY_CLEAR[1]: n = 0
    f = F(FM, 16); y = 54; left = n; cx, cy = 50, 54; x = 50
    for i, ln in enumerate(PY):
        d.text((14, y), f'{i + 1:2d}', font=F(FM, 14), fill=(92, 99, 112)); x = 50
        for s, c in ln:
            if left <= 0: break
            part = s[:left]; d.text((x, y), part, font=f, fill=c); x += d.textlength(part, font=f); left -= len(part)
        if left > 0: left -= 1; cx, cy = 50, y + 32
        else: cx, cy = x, y
        if left <= 0 and i < len(PY) - 1 and n < PY_N:
            break
        y += 32
    if n == PY_N: cx, cy = x, y
    if (t * 2.2) % 1 < 0.6: d.rectangle([cx + 2, cy + 1, cx + 11, cy + 21], fill=(220, 223, 228))
    if t >= PY_OUT and t < PY_CLEAR[0]:                                # «запуск»: строка вывода
        d.rectangle([0, WH - 52, WW, WH], fill=(22, 24, 33)); d.text((14, WH - 40), '>>> Прыжок! Прыжок! Прыжок!', font=F(FM, 15), fill=(152, 195, 121))
    return im

def web(t):
    im, d = frame('index.html — браузер', (40, 167, 120))
    d.rounded_rectangle([12, 44, WW - 12, 72], 12, fill=(241, 243, 246)); d.text((28, 49), 'мой-сайт.html', font=F(FR, 14), fill=(110, 115, 125))
    wipe = 1 - seg(t, *WEB_WIPE)
    k1 = seg(t, *WEB_HEAD) * wipe; k3 = seg(t, *WEB_BTN) * wipe
    k2 = [seg(t, WEB_CARD0 + i * 0.25, WEB_CARD0 + 0.3 + i * 0.25) * wipe for i in range(3)]
    lay = Image.new('RGBA', im.size, (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    if k1 > 0:
        ld.rectangle([12, 84, 12 + (WW - 24) * k1, 136], fill=ACC + (255,)); ld.text((28, 98), 'Моя первая страница'[:int(19 * k1)], font=F(FB, 19), fill='white')
    for i, k in enumerate(k2):
        if k <= 0: continue
        x = 12 + i * 141; yy = 150 + (1 - k) * 20; a = int(255 * k)
        ld.rounded_rectangle([x, yy, x + 129, yy + 112], 10, fill=(236, 246, 250, a), outline=(205, 228, 238, a))
        ld.rectangle([x + 12, yy + 12, x + 117, yy + 62], fill=[(200, 228, 240), (255, 226, 170), (205, 236, 210)][i] + (a,))
        ld.rectangle([x + 12, yy + 72, x + 96, yy + 82], fill=(170, 190, 200, a)); ld.rectangle([x + 12, yy + 90, x + 70, yy + 98], fill=(200, 212, 220, a))
    if k3 > 0:
        p = 1 + 0.06 * math.sin(max(0, t - WEB_BTN[1]) * 8) * (1 if t < WEB_CLICK else 0)
        bw, bh = 170 * p * k3, 38 * p * k3; cx, cy = WW / 2, 300
        ld.rounded_rectangle([cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2], int(19 * p), fill=ORANGE + (255,))
        if k3 > 0.8: ld.text((cx - 32, cy - 11), 'Играть', font=F(FB, 17), fill='white')
    im.alpha_composite(lay)
    if WEB_BTN[0] < t < WEB_EXIT + 0.4 and wipe > 0:                   # курсор едет к кнопке и нажимает
        u = seg(t, *WEB_CURSOR); x = 360 + (WW / 2 + 10 - 360) * u; y = 120 + (306 - 120) * u
        dd = ImageDraw.Draw(im); pts = [(x, y), (x, y + 24), (x + 6, y + 18), (x + 11, y + 28), (x + 15, y + 26), (x + 10, y + 16), (x + 18, y + 16)]
        dd.polygon(pts, fill=(25, 25, 30), outline='white')
    if t >= WEB_CLICK - 0.05: rings(im, WW / 2, 300, WEB_CLICK, t, (255, 255, 255), 0.45)
    if t >= WEB_EXIT - 0.05: rings(im, WW / 2, WH / 2 + 10, WEB_EXIT, t, (245, 159, 0), 0.7)
    return im

SCREENS = {'scratch': scratch, 'python': python, 'web': web}
if __name__ == '__main__':
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 9.0
    out = Image.new('RGB', (WW * 3 + 20, WH), 'white')
    for i, fn in enumerate(SCREENS.values()): out.paste(fn(t).convert('RGB'), (i * (WW + 10), 0))
    out.save(os.path.join(HERE, f'screens_{t:.2f}.png')); print('ok')
