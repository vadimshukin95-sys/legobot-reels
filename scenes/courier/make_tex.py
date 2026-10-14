"""Procedural set textures for the courier reel: tex/road.png (toy street) and tex/map.png (delivery map).
1 texture = 60 x 60 studs (Blender mapping in scene.py). Robot walks along -Y = image 'up'."""
import os, random, math
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
S = 2048
PX = S / 60.0                       # pixels per stud
rnd = random.Random(7)

def road():
    im = Image.new('RGB', (S, S), (92, 96, 102))
    d = ImageDraw.Draw(im)
    # asphalt grain
    px = im.load()
    for _ in range(260000):
        x, y = rnd.randrange(S), rnd.randrange(S); v = rnd.randint(-18, 18)
        r, g, b = px[x, y]; px[x, y] = (r + v, g + v, b + v)
    im = im.filter(ImageFilter.GaussianBlur(0.8)); d = ImageDraw.Draw(im)
    cx = S / 2
    half = 13 * PX                  # road half width
    # sidewalks with tiles
    for side in (-1, 1):
        x0 = cx + side * half
        x1 = 0 if side < 0 else S
        d.rectangle([min(x0, x1), 0, max(x0, x1), S], fill=(206, 203, 196))
        for y in range(0, S, int(4 * PX)):
            d.line([(min(x0, x1), y), (max(x0, x1), y)], fill=(178, 175, 168), width=4)
        for x in range(int(min(x0, x1)), int(max(x0, x1)), int(4 * PX)):
            d.line([(x, 0), (x, S)], fill=(178, 175, 168), width=4)
        d.rectangle([x0 - 10 if side > 0 else x0 - 30, 0, x0 + 30 if side > 0 else x0 + 10, S], fill=(236, 234, 228))
    # lane lines: dashed white centre, solid edges
    for y in range(0, S, int(6 * PX)):
        d.rectangle([cx - 0.35 * PX + 6 * PX, y, cx + 0.35 * PX + 6 * PX, y + 3 * PX], fill=(246, 246, 240))
        d.rectangle([cx - 0.35 * PX - 6 * PX, y, cx + 0.35 * PX - 6 * PX, y + 3 * PX], fill=(246, 246, 240))
    # zebra crossing near the top (delivery spot)
    zy = int(S * 0.18)
    for k in range(-6, 7):
        x = cx + k * 2 * PX
        d.rectangle([x - 0.7 * PX, zy, x + 0.7 * PX, zy + 7 * PX], fill=(250, 250, 244))
    im.save(os.path.join(HERE, 'tex', 'road.png'))

def city_map():
    im = Image.new('RGB', (S, S), (238, 234, 222))
    d = ImageDraw.Draw(im)
    blocks = [(250, 214, 165), (205, 228, 245), (246, 205, 211), (214, 236, 200), (240, 228, 180)]
    step = int(10 * PX); street = int(2.6 * PX)
    for i in range(-1, S // step + 2):
        for j in range(-1, S // step + 2):
            x, y = i * step + (j % 2) * step // 3, j * step
            c = rnd.choice(blocks)
            d.rounded_rectangle([x + street, y + street, x + step, y + step], 18, fill=c)
            for _ in range(3):                             # little houses
                hx, hy = x + street + rnd.randint(20, step - 120), y + street + rnd.randint(20, step - 120)
                d.rounded_rectangle([hx, hy, hx + 70, hy + 60], 8, fill=tuple(max(0, v - 28) for v in c))
    # park + river
    d.rounded_rectangle([int(S * 0.62), int(S * 0.45), int(S * 0.95), int(S * 0.72)], 60, fill=(150, 205, 120))
    for _ in range(40):
        tx, ty = rnd.randint(int(S * 0.64), int(S * 0.93)), rnd.randint(int(S * 0.47), int(S * 0.70))
        d.ellipse([tx - 22, ty - 22, tx + 22, ty + 22], fill=(98, 170, 82))
    pts = [(0, int(S * 0.86))]
    for k in range(1, 12):
        pts.append((k * S / 11, S * 0.86 + 70 * math.sin(k * 0.9)))
    d.line(pts, fill=(120, 190, 235), width=int(4.5 * PX), joint='curve')
    # main street along the robot path (centre, vertical)
    cx = S / 2
    d.rectangle([cx - 9 * PX, 0, cx + 9 * PX, S], fill=(250, 248, 242))
    # dashed delivery route: from the bottom up the street to the pin
    yy = S
    while yy > S * 0.16:
        d.rounded_rectangle([cx - 0.5 * PX, yy - 2.2 * PX, cx + 0.5 * PX, yy], 10, fill=(226, 45, 36))
        yy -= 3.6 * PX
    # destination pin
    px_, py_ = cx, S * 0.12
    d.ellipse([px_ - 2.4 * PX, py_ - 2.4 * PX, px_ + 2.4 * PX, py_ + 2.4 * PX], fill=(226, 45, 36))
    d.polygon([(px_ - 1.9 * PX, py_ + 1.2 * PX), (px_ + 1.9 * PX, py_ + 1.2 * PX), (px_, py_ + 5 * PX)], fill=(226, 45, 36))
    d.ellipse([px_ - 1 * PX, py_ - 1 * PX, px_ + 1 * PX, py_ + 1 * PX], fill=(255, 255, 255))
    im = im.filter(ImageFilter.GaussianBlur(0.6))
    im.save(os.path.join(HERE, 'tex', 'map.png'))

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'tex'), exist_ok=True)
    city_map()
