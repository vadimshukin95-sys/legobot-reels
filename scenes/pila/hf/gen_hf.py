"""Собирает scenes/pila/hf/index.html — композицию HyperFrames для рилса «Пила», вариант C «Кинетический текст».
Подложка base.mp4 (hf_base.py: фон + модель + красные стрелки из overlay.py), поверх — заголовок, подписи и финальная карточка.
python gen_hf.py <out.html> [preview_state]   preview_state: title|c0..c4|card — статичный кадр без GSAP (для проверки вёрстки)"""
import sys, html

LIME, LEAF, SUN, INK = '#8CC63F', '#3B8A2E', '#F5C518', '#23292C'
DUR = 17.0
T_RUN, T_CARD = 5.0, 14.0

# (начало, конец, слова, стиль). Слово с * — выделение (плашка), с ^ — зелёный цвет, _ — неразрывный пробел
CAPS = [
    (5.0, 6.7, 'Мотор крутит *колесо', 'n'),
    (6.7, 8.4, 'Палец на колесе ходит *по_кругу', 'n'),
    (8.4, 10.2, 'Шатун толкает пилу *туда-сюда', 'n'),
    (10.2, 12.0, 'Это ^кривошип', 'big'),
    (12.0, 14.0, 'Кривошип есть в ^велосипеде, ^швейной_машинке и ^лобзике', 'small'),
]
TITLE = 'Как колесо ^превращается в пилу?'
CARD = 'Больше ^механизмов для уроков'


def words(text, cls):
    out = []
    for w in text.split():
        c = 'w'
        if w.startswith('*'):
            w, c = w[1:], 'w hl'
        elif w.startswith('^'):
            w, c = w[1:], 'w g'
        w = html.escape(w.replace('_', ' '))
        out.append(f'<span class="{c}">{w}</span>')
    return f'<div class="{cls}">' + ' '.join(out) + '</div>'


CSS = f'''
* {{ margin:0; padding:0; box-sizing:border-box; }}
html, body {{ width:1080px; height:1920px; background:#000; }}
#root {{ position:relative; width:1080px; height:1920px; overflow:hidden; font-family:"Inter Display","Inter",sans-serif; }}
#base {{ position:absolute; left:0; top:0; width:1080px; height:1920px; object-fit:cover; z-index:0; }}
.w {{ display:inline-block; }}
.title {{ position:absolute; left:70px; right:70px; top:170px; z-index:5; font-weight:900; font-size:132px; line-height:128px;
  letter-spacing:-3px; color:{INK}; }}
.g {{ color:{LEAF}; }}
.bar {{ position:absolute; left:70px; top:1360px; width:120px; height:14px; border-radius:7px; background:{SUN}; z-index:5;
  transform-origin:left center; }}
.cap {{ position:absolute; left:70px; right:60px; top:1400px; z-index:5; font-weight:900; font-size:96px; line-height:104px;
  letter-spacing:-2px; color:{INK}; }}
.cap.big {{ font-size:150px; line-height:150px; letter-spacing:-4px; top:1395px; }}
.cap.small {{ font-size:74px; line-height:84px; letter-spacing:-1.5px; }}
.hl {{ color:#fff; background:{INK}; padding:0 14px; border-radius:14px; margin:0 -4px; }}
.foot {{ position:absolute; left:40px; bottom:28px; z-index:5; font:700 34px "Inter",sans-serif; color:{INK}; }}
#card {{ position:absolute; inset:0; z-index:10; background:{INK}; }}
.logo {{ position:absolute; left:70px; top:300px; width:260px; height:260px; border-radius:50%; background:#fff; z-index:11;
  display:flex; align-items:center; justify-content:center; box-shadow:0 18px 40px rgba(0,0,0,.35); }}
.logo img {{ width:72%; height:auto; }}
.ctext {{ position:absolute; left:70px; right:70px; top:700px; z-index:11; font-weight:900; font-size:120px; line-height:124px;
  letter-spacing:-3px; color:#fff; }}
.ctext .g {{ color:{LIME}; }}
.url {{ position:absolute; left:70px; top:1260px; z-index:11; font-weight:800; font-size:76px; color:{SUN}; }}
.url .arr {{ display:inline-block; }}
'''

# Начальные состояния для рендера (GSAP «оживляет» их по времени)
CSS_ANIM = '''
.title .w, .cap .w, .ctext .w { opacity:0; }
.bar { transform:scaleX(0); }
.foot { opacity:0; }
#card { clip-path: inset(100% 0 0 0); }
.logo { transform:scale(0); }
.url { opacity:0; }
'''

JS = f'''
window.__timelines = window.__timelines || {{}};
const tl = gsap.timeline({{ paused: true }});
// заголовок: слова выпрыгивают по одному, потом улетают вверх перед подписями
tl.fromTo(".title .w", {{ opacity:0, y:70 }}, {{ opacity:1, y:0, duration:0.5, ease:"back.out(1.7)", stagger:0.13 }}, 0.2);
tl.fromTo(".title .g", {{ color:"{INK}" }}, {{ color:"{LEAF}", duration:0.35 }}, 0.75);
tl.to(".title .w", {{ opacity:0, y:-50, duration:0.3, ease:"power2.in", stagger:0.04 }}, {T_RUN - 0.45});
tl.fromTo(".foot", {{ opacity:0 }}, {{ opacity:1, duration:0.4 }}, 0.5);
tl.to(".foot", {{ opacity:0, duration:0.2 }}, {T_CARD - 0.05});
// жёлтая черта над подписями
tl.fromTo(".bar", {{ scaleX:0 }}, {{ scaleX:1, duration:0.35, ease:"power3.out" }}, {T_RUN - 0.1});
tl.to(".bar", {{ scaleX:0, duration:0.25, ease:"power2.in" }}, {T_CARD - 0.3});
'''
for k, (a, b, text, st) in enumerate(CAPS):
    sel = f'#c{k}'
    JS += f'''tl.fromTo("{sel} .w", {{ opacity:0, y:60 }}, {{ opacity:1, y:0, duration:0.32, ease:"power3.out", stagger:0.07 }}, {a + 0.02});
'''
    if '*' in text:
        JS += f'''tl.fromTo("{sel} .hl", {{ backgroundColor:"rgba(35,41,44,0)", color:"{INK}" }}, {{ backgroundColor:"{INK}", color:"#ffffff", duration:0.2 }}, {a + 0.35});
'''
    if st == 'big':
        JS += f'''tl.fromTo("{sel} .g", {{ scale:0.85 }}, {{ scale:1, duration:0.4, ease:"back.out(2.2)" }}, {a + 0.12});
'''
    out_t = b - 0.22 if k < len(CAPS) - 1 else T_CARD - 0.25
    JS += f'''tl.to("{sel} .w", {{ opacity:0, y:-36, duration:0.18, ease:"power2.in", stagger:0.015 }}, {out_t});
'''
JS += f'''
// финальная карточка: тёмная шторка снизу, логотип, текст по словам, адрес
tl.fromTo("#card", {{ clipPath:"inset(100% 0 0 0)" }}, {{ clipPath:"inset(0% 0 0 0)", duration:0.45, ease:"power2.inOut" }}, {T_CARD});
tl.fromTo(".logo", {{ scale:0 }}, {{ scale:1, duration:0.5, ease:"back.out(1.8)" }}, {T_CARD + 0.35});
tl.fromTo(".ctext .w", {{ opacity:0, y:70 }}, {{ opacity:1, y:0, duration:0.45, ease:"back.out(1.6)", stagger:0.12 }}, {T_CARD + 0.55});
tl.fromTo(".url", {{ opacity:0, y:30 }}, {{ opacity:1, y:0, duration:0.4, ease:"power3.out" }}, {T_CARD + 1.25});
tl.to(".url .arr", {{ x:14, duration:0.3, ease:"sine.inOut", yoyo:true, repeat:3 }}, {T_CARD + 1.7});
tl.to({{}}, {{ duration:0.01 }}, {DUR - 0.01});
window.__timelines.pila = tl;
'''


def build(preview=None):
    caps = '\n'.join(
        f'<div id="c{k}" class="cap {"big" if st == "big" else ("small" if st == "small" else "")}">'
        + words(text, 'inner')[len('<div class="inner">'):-len('</div>')] + '</div>'
        for k, (a, b, text, st) in enumerate(CAPS))
    body = f'''
<div id="root" data-composition-id="pila" data-start="0" data-duration="{DUR:g}" data-width="1080" data-height="1920" data-fps="30">
  <video id="base" src="base.mp4" muted playsinline data-start="0" data-duration="{DUR:g}" data-track-index="0"></video>
  {words(TITLE, 'title')}
  <div class="bar"></div>
  {caps}
  <div class="foot">legobot.ru</div>
  <div id="card"></div>
  <div class="logo"><img src="logo.png" alt=""></div>
  {words(CARD, 'ctext')}
  <div class="url">legobot.ru <span class="arr">→</span></div>
</div>'''
    if preview is None:
        head_extra = f'<style>{CSS}{CSS_ANIM}</style>\n<script src="https://cdn.jsdelivr.net/npm/gsap@3.12.5/dist/gsap.min.js"></script>'
        tail = f'<script>{JS}</script>'
    else:
        # статичный кадр: показываем только нужное состояние
        show = {'title': '.title,.foot', 'card': '#card,.logo,.ctext,.url'}.get(preview, f'#{preview},.bar,.foot')
        hide = '.title,.bar,.cap,.foot,#card,.logo,.ctext,.url'
        logo_off = '.logo{display:none}' if preview != 'card' else ''
        head_extra = (f'<style>{CSS} {hide}{{display:none}} {show}{{display:block}} .logo{{display:flex}}'
                      f'{logo_off} #base{{background:#cfd7de}}</style>')
        tail = ''
    return f'''<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=1080, height=1920">
{head_extra}
</head>
<body>{body}
{tail}
</body>
</html>
'''


if __name__ == '__main__':
    out = sys.argv[1]
    pv = sys.argv[2] if len(sys.argv) > 2 else None
    open(out, 'w', encoding='utf-8').write(build(pv))
