"""Физическая симуляция «Кувырков» -> scenes/kuvyrki/traj.b64 (60 к/с) + проверка счёта.
Параметры ролика: 0,6 об/с, трение подвеса 20 % от момента веса + вязкое 8000, крестики держатся трением.
python make_traj.py ../traj.b64"""
import os, sys, zlib, base64, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import counter as C
P = dict(n_rev=8.7, fric=0.2, visc=8000, rps=0.6, fps=60)
rec, PP = C.run(P)
bad = []
for n, th, st in C.report(rec, PP):
    exp = [n, n // 2, n // 4]; got = [round(x) for x in th]
    print(n, got, 'ok' if got == exp else 'ОШИБКА')
    if got != exp: bad.append(n)
T = np.arange(0, rec[-1, 0], 1 / 60)
cols = [np.interp(T, rec[:, 0], rec[:, j]) for j in range(1, 7)]
A = np.round(np.array(cols).T * 100).astype(np.int32)
D = np.diff(A, axis=0, prepend=np.zeros((1, 6), np.int32)).astype(np.int32)
b = base64.b64encode(zlib.compress(D.tobytes(), 9)).decode()
out = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'traj.b64')
with open(out, 'w', encoding='utf-8') as f:
    f.write('# траектория симуляции: 60 к/с, столбцы crank,p0,s0,p1,s1,p2 (град*100), разности int32, zlib, base64\n')
    f.write('\n'.join(b[i:i + 100] for i in range(0, len(b), 100)) + '\n')
print('traj', len(T), 'кадров ->', out)
if bad:
    raise SystemExit('счёт сбился на шагах ' + str(bad))
