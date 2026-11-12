"""Хаос-маятник: сборка кадров рилса. Плашки — полные кадры 1080×1920 из Blender (студия уже в кадре);
сверху заголовок «Два звена — полный хаос», внизу «замедлено в 2 раза» и legobot.ru, в конце карточка с логотипом.
python overlay.py <папка f0024.png…> <папка вывода o0000.png…> [номера кадров через запятую]"""
import os, sys, math
from PIL import Image, ImageDraw, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
sys.path.append(os.path.join(HERE, '..', 'pila'))
import timeline as TL, reelkit as K

TITLE, CHIP, CARD = None, None, None


def pop(u):
    if u <= 0:
        return 0
    if u >= 1:
        return 1
    return 1 + 0.08 * math.sin(u * math.pi) if u > 0.55 else (1 - (1 - u / 0.55) ** 3) * 1.04


def paste_scaled(img, src, cx, cy, s, alpha=1.0):
    if s <= 0.01 or alpha <= 0.01:
        return
    w, h = max(1, int(src.width * s)), max(1, int(src.height * s))
    im = src.resize((w, h), Image.LANCZOS)
    if alpha < 1:
        im.putalpha(im.split()[-1].point(lambda v: int(v * alpha)))
    img.alpha_composite(im, (int(cx - w / 2), int(cy - h / 2)))


def title_img():
    global TITLE
    if TITLE is None:
        TITLE = []
        for line in TL.TITLE:
            im = Image.new('RGBA', (1300, 220), (0, 0, 0, 0))
            K.tracked(im, (650, 30), line, K.font(96), (255, 255, 255), K.INK, 7, track=4, shadow=((12, 30, 60), (0, 12)))
            TITLE.append(im.crop(im.getbbox()))
    return TITLE


def chip_img():
    global CHIP
    if CHIP is None:
        im = Image.new('RGBA', (700, 200), (0, 0, 0, 0))
        K.sticker(im, 350, 100, 'замедлено в 2 раза', K.font(34, 'xb'), (255, 255, 255), K.INK, pad=(22, 10), radius=20)
        CHIP = im.crop(im.getbbox())
    return CHIP


def card(last_plate):
    global CARD
    if CARD is None:
        im = last_plate.convert('RGB').filter(ImageFilter.GaussianBlur(22)).convert('RGBA')
        im = Image.alpha_composite(im, Image.new('RGBA', im.size, (14, 38, 80, 150)))
        lg = K.logo_round(size=360)
        sh = Image.new('RGBA', (440, 440), (0, 0, 0, 0)); ImageDraw.Draw(sh).ellipse((40, 52, 400, 412), fill=(0, 10, 30, 110))
        sh = sh.filter(ImageFilter.GaussianBlur(14))
        im.alpha_composite(sh, (540 - 220, 640 - 190)); im.alpha_composite(lg, (540 - 180, 640 - 180))
        K.tracked(im, (540, 900), 'ХАОС-МАЯТНИК', K.font(104), (255, 255, 255), K.INK, 7, track=4, shadow=((10, 25, 50), (0, 12)))
        K.outlined(im, (540, 1060), 'собран из LEGO® Education\nSPIKE™ Prime', K.font(54, 'xb'), (255, 255, 255), K.INK, 0, spacing=12)
        K.outlined(im, (540, 1640), 'legobot.ru', K.font(64, 'black'), (255, 255, 255), K.INK, 0)
        CARD = im
    return CARD


def frame(i, plates):
    t = i / TL.FPS
    k = TL.plate_index(i)
    pl = Image.open(os.path.join(plates, f'f{k:04d}.png')).convert('RGBA')
    img = pl.copy()
    if t < TL.T_CARD + TL.CARD_FADE:
        for n, im in enumerate(title_img()):
            u = (t - 0.15 - 0.16 * n) / 0.35
            paste_scaled(img, im, 540, 150 + n * 118 + im.height / 2 - 40, pop(u))
        if t >= TL.T_REL:
            a = min(1, (t - TL.T_REL) / 0.4)
            c = chip_img(); paste_scaled(img, c, 40 + c.width / 2, 1780, 1.0, a)
        ImageDraw.Draw(img).text((1040, 1780), 'legobot.ru', font=K.font(36, 'b'), fill=(255, 255, 255), anchor='rm')
    if t >= TL.T_CARD:
        c = card(Image.open(os.path.join(plates, f'f{TL.PLATE_LAST:04d}.png')))
        u = min(1, (t - TL.T_CARD) / TL.CARD_FADE)
        if u < 1:
            c = c.copy(); c.putalpha(c.split()[-1].point(lambda v: int(v * u)))
        img.alpha_composite(c)
    return img.convert('RGB')


if __name__ == '__main__':
    plates, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    if len(sys.argv) > 3:
        for i in map(int, sys.argv[3].split(',')):
            frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
    else:
        last = None
        for i in range(TL.FRAMES):
            if i / TL.FPS >= TL.T_CARD + TL.CARD_FADE:
                last = last or frame(i, plates)
                last.save(os.path.join(out, f'o{i:04d}.png'))
            else:
                frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
            if i % 60 == 0:
                print('overlay', i, flush=True)
        # обложка рилса: кадр с заголовком в разгар движения
        Image.open(os.path.join(out, 'o0180.png')).convert('RGB').save(os.path.join(out, '..', 'cover.jpg'), quality=93)
