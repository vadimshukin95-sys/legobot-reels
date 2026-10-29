"""LDraw-модели для 3D-ролика /prog: монитор из кирпичиков и робот LEGObot.
  python3 prog/models3d.py  -> prog/models/monitor_<имя>.ldr, prog/models/robot.ldr
Монитор: низ подставки в y=0, экран смотрит в -Z. Внутренний прямоугольник экрана: x -140..140, y -304..-88, z=0 (перед ним — плоскость с картинкой в Blender).
Робот: подошвы в y=0, лицом в -Z. Группы для анимации — в комментариях «0 GROUP <имя>» перед деталями."""
import os
HERE = os.path.dirname(os.path.abspath(__file__))
I = '1 0 0 0 1 0 0 0 1'                      # без поворота
RY = '0 0 1 0 1 0 -1 0 0'                    # поворот 90° вокруг Y: длинная сторона вдоль Z
FRONT = '1 0 0 0 0 -1 0 1 0'                 # плитка лицом в -Z (верх плитки смотрит на зрителя)

def L(c, x, y, z, part, m=I): return f'1 {c} {x:g} {y:g} {z:g} {m} {part}.dat'

SCREEN = dict(x0=-140, x1=140, y0=-304, y1=-88, z=0)

def monitor(bezel, stand=72, inner=0):
    out = ['0 Монитор LEGObot из кирпичиков', '0 Name: monitor.ldr']
    out.append(L(stand, 0, -8, 0, '3032'))                                  # подошва 4×6
    out += [L(stand, 0, -32, 0, '3003'), L(stand, 0, -56, 0, '3003')]       # ножка 2×2 ×2
    out.append(L(stand, 0, -64, 0, '4282'))                                 # полка 2×16
    z = 10                                                                   # стенка на заднем ряду полки
    for r in range(11):
        top = -64 - 24 * (r + 1)
        if r in (0, 10): out.append(L(bezel, 0, top, z, '2465')); continue  # нижняя и верхняя рамка 1×16
        out += [L(bezel, -150, top, z, '3005'), L(bezel, 150, top, z, '3005')]
        if r % 2: out += [L(inner, -60, top, z, '3008'), L(inner, 80, top, z, '3009')]
        else:     out += [L(inner, -80, top, z, '3009'), L(inner, 60, top, z, '3008')]
    out.append(L(10, 118, -76, -8, '98138', FRONT))                         # зелёный «светодиод» на рамке
    return out

def robot():
    o = ['0 Робот LEGObot из кирпичиков', '0 Name: robot.ldr']
    for nm, x in (('legL', -30), ('legR', 30)):                              # ноги: пластина-ботинок + 2 кирпича 1×2 вдоль Z
        o += [f'0 GROUP {nm}', L(72, x, -8, 0, '3023', RY), L(71, x, -32, 0, '3004', RY), L(71, x, -56, 0, '3004', RY)]
    o += ['0 GROUP body', L(72, 0, -64, 0, '3020'), L(25, 0, -88, 0, '3001'), L(25, 0, -112, 0, '3001'),
          L(322, 0, -100, -28, '3069b', FRONT),                               # панель на груди 1×2
          L(14, -10, -78, -28, '98138', FRONT), L(4, 10, -78, -28, '98138', FRONT),   # две «кнопки»
          L(72, 0, -120, 0, '3022')]                                          # шея
    for nm, x in (('armL', -50), ('armR', 50)):                              # руки 1×1×2 + круглая «кисть»
        o += [f'0 GROUP {nm}', L(322, x, -88, 0, '3005'), L(322, x, -112, 0, '3005'), L(72, x, -64, 0, '6141')]
    o += ['0 GROUP head', L(15, 0, -128, 0, '3020'), L(15, 0, -152, 0, '3001'),
          L(0, -20, -140, -28, '98138', FRONT), L(0, 20, -140, -28, '98138', FRONT),   # глаза
          L(72, 0, -160, 10, '3794b'), L(72, 0, -184, 10, '4589'), L(25, 0, -208, 10, '3062b')]  # антенна с оранжевым огоньком
    return o

if __name__ == '__main__':
    os.makedirs(os.path.join(HERE, 'models'), exist_ok=True)
    for name, col in (('scratch', 191), ('python', 1), ('web', 10)):
        open(os.path.join(HERE, 'models', f'monitor_{name}.ldr'), 'w').write('\n'.join(monitor(col)) + '\n')
    open(os.path.join(HERE, 'models', 'robot.ldr'), 'w').write('\n'.join(robot()) + '\n')
    print('ok')
