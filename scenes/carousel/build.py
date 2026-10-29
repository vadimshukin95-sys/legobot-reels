"""Карусель для первого экрана главной legobot.ru: четыре модели подряд, по 6 с, с мягким переходом.
Берёт прозрачные кадры уже отрендеренных петель (папки frames/<имя>/f0001.png…), кладёт на фон главной
и склеивает: WeDo → SPIKE Prime → SPIKE Essential → EV3 → снова WeDo (петля без шва).
  python build.py <папка с подпапками кадров> <папка вывода>"""
import sys, os
from PIL import Image, ImageFilter

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
# (папка, первый кадр куска в своей петле): WeDo — начало петли; принтер — ручка опускается и печатает;
# вратарь — сейв слева и справа; Робостроитель — берёт кубик, везёт и ставит
SEGMENTS = [('wedo', 1), ('prime', 25), ('essential', 15), ('ev3', 44)]
N, X = 144, 12                      # видимая часть куска (6 с) и переход (0,5 с) при 24 кадрах в секунду
EDGE, CENTRE, GAIN = (236, 248, 227), (250, 253, 246), 1.55        # фон первого экрана главной (как у прежнего ролика)

_bg = {}
def background(w, h):
    if (w, h) not in _bg:
        g = Image.radial_gradient('L').resize((w, h), Image.BICUBIC)
        g = g.point(lambda v: min(255, int(v * GAIN)))
        a, b = Image.new('RGB', (w, h), CENTRE), Image.new('RGB', (w, h), EDGE)
        _bg[(w, h)] = Image.composite(b, a, g).filter(ImageFilter.GaussianBlur(2))
    return _bg[(w, h)]

def frame(k, i):
    name, start = SEGMENTS[k]
    im = Image.open(os.path.join(SRC, name, f'f{start + i:04d}.png')).convert('RGBA')
    out = background(*im.size).copy(); out.paste(im, (0, 0), im)
    return out

total = N * len(SEGMENTS)
for t in range(total):
    k, j = divmod(t, N)
    loc = X + j                                     # первые X кадров куска уходят в переход с предыдущим
    img = frame(k, loc)
    if loc >= N:                                    # хвост куска растворяется в начало следующего
        a = (loc - N + 0.5) / X
        img = Image.blend(img, frame((k + 1) % len(SEGMENTS), loc - N), a)
    img.save(os.path.join(DST, f'o{t + 1:04d}.png'))
print(total, 'frames built')
