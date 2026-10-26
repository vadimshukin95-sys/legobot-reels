"""Школьная доска для фона «Скрипача»: нотный стан, ноты, «8 → 24», эскиз кривошипа — мелом. -> tex/board.png"""
import os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
FD = os.path.join(HERE, '..', '..', 'common', 'fonts')
W, H = 2400, 1300
random.seed(7)
img = Image.new('RGB', (W, H), (46, 84, 66))
# неровный тон доски и следы стёртого мела
px = img.load()
noise = Image.effect_noise((W // 8, H // 8), 22).resize((W, H), Image.BICUBIC)
img = Image.composite(Image.new('RGB', (W, H), (58, 98, 78)), img, noise.point(lambda v: int(max(0, v - 110) * 0.9)))
d = ImageDraw.Draw(img)
for _ in range(40):
    x, y = random.randint(0, W), random.randint(0, H)
    d.ellipse([x - 160, y - 40, x + 160, y + 40], fill=(66, 104, 86))
img = img.filter(ImageFilter.GaussianBlur(18))

chalk = Image.new('L', (W, H), 0)
cd = ImageDraw.Draw(chalk)
def wobble_line(p0, p1, w=7, n=40):
    pts = []
    for k in range(n + 1):
        t = k / n
        pts.append((p0[0] + (p1[0] - p0[0]) * t + random.uniform(-1.5, 1.5), p0[1] + (p1[1] - p0[1]) * t + random.uniform(-1.5, 1.5)))
    cd.line(pts, fill=230, width=w)
# нотный стан
for k in range(5):
    wobble_line((140, 260 + k * 46), (2260, 250 + k * 46), 6, 80)
sym = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 230)
clef = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 300)
for x, s, dy in ((380, '♩', 40), (620, '♪', -20), (860, '♫', 20), (1180, '♩', -40), (1420, '♪', 10), (1680, '♫', -30), (1980, '♩', 30)):
    cd.text((x, 150 + dy), s, font=sym, fill=235)
# «8 → 24» и подпись
big = ImageFont.truetype(os.path.join(FD, 'Nunito-Variable.ttf'), 210); big.set_variation_by_name('ExtraBold')
cd.text((180, 640), '8', font=big, fill=235)
cd.text((470, 640), '24', font=big, fill=235)
wobble_line((320, 760), (440, 760), 12); cd.polygon([(440, 735), (480, 760), (440, 785)], fill=235)
mid = ImageFont.truetype(os.path.join(FD, 'Nunito-Variable.ttf'), 90); mid.set_variation_by_name('Bold')
cd.text((190, 920), 'i = 24 : 8 = 3', font=mid, fill=220)
# эскиз кривошипа: окружность, палец, шатун-смычок, кисть
cx, cy, r = 1900, 840, 150
cd.ellipse([cx - r, cy - r, cx + r, cy + r], outline=230, width=9)
cd.ellipse([cx - 22, cy - 22, cx + 22, cy + 22], outline=230, width=8)
px_, py_ = cx + r * math.cos(math.radians(40)), cy - r * math.sin(math.radians(40))
cd.ellipse([px_ - 20, py_ - 20, px_ + 20, py_ + 20], fill=230)
hx, hy = 1250, 760
wobble_line((px_, py_), (hx - 120, hy - 20), 10)
cd.ellipse([hx - 30, hy - 30, hx + 30, hy + 30], outline=230, width=8)
for a in range(150, 215, 6):                                   # дуга-стрелка вращения
    a0, a1 = math.radians(a), math.radians(a + 4)
    cd.line([(cx + (r + 50) * math.cos(a0), cy - (r + 50) * math.sin(a0)), (cx + (r + 50) * math.cos(a1), cy - (r + 50) * math.sin(a1))], fill=220, width=8)
# меловая фактура: крошка
grain = Image.effect_noise((W, H), 90).point(lambda v: 255 if v > 120 else int(v * 1.6))
chalk = Image.composite(chalk, Image.new('L', (W, H), 0), grain).filter(ImageFilter.GaussianBlur(1.2))
img.paste((236, 240, 232), (0, 0), chalk)
# деревянная рама
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W - 1, H - 1], outline=(150, 108, 66), width=34)
d.rectangle([0, H - 60, W, H], fill=(140, 100, 60))
os.makedirs(os.path.join(HERE, 'tex'), exist_ok=True)
img.save(os.path.join(HERE, 'tex', 'board.png'), optimize=True)
print('ok', img.size)
