"""Подложка для HyperFrames: фон «Студия» + модель из Blender + красные стрелки из overlay.py — без заголовка, подписей,
подписи legobot.ru и финальной карточки (их рисует композиция scenes/pila/hf).
python hf_base.py <папка плашек f0001.png…> <папка вывода o0000.png…>"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from PIL import Image, ImageDraw as _ID
import overlay as O

O.draw_title = lambda img, t: None
O.draw_caps = lambda img, t: None
_EMPTY = Image.new('RGBA', (1080, 1920), (0, 0, 0, 0))
O.card = lambda: _EMPTY


class _NoText:
    """ImageDraw без text(): стрелки рисуются как раньше, надпись legobot.ru внизу — нет."""
    def __init__(self, d):
        self._d = d

    def text(self, *a, **k):
        pass

    def __getattr__(self, n):
        return getattr(self._d, n)


class _IDProxy:
    def __getattr__(self, n):
        return getattr(_ID, n)

    @staticmethod
    def Draw(im, *a, **k):
        return _NoText(_ID.Draw(im, *a, **k))


O.ImageDraw = _IDProxy()

if __name__ == '__main__':
    plates, out = sys.argv[1], sys.argv[2]
    os.makedirs(out, exist_ok=True)
    for i in range(O.TL.FRAMES):
        O.frame(i, plates).save(os.path.join(out, f'o{i:04d}.png'))
        if i % 60 == 0:
            print('base', i, flush=True)
