"""Считает движение маятника (sim.py) и пишет angles.json: углы на каждую четверть кадра ролика от F_REL.
python make_angles.py   (timeline.py вызывает compute() сам, если angles.json нет)"""
import os, json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))


def compute(write=True):
    import sim
    import timeline as TL
    rate = TL.FPS * TL.SLOW * TL.SUB                    # 240 точек в секунду реального движения
    n = (TL.PLATE_LAST + 2 - TL.F_REL) * TL.SUB + 1
    S = sim.simulate(TL.TH0[0], TL.TH0[1], n / rate, fps=int(rate), sub=10)[:n]
    A = {'rate': rate, 'th1': [round(float(v), 6) for v in S[:, 0]], 'th2': [round(float(v), 6) for v in S[:, 1]]}
    if write:
        json.dump(A, open(os.path.join(HERE, 'angles.json'), 'w'))
    return A, S


if __name__ == '__main__':
    A, S = compute()
    print('точек', len(S), 'макс |w| рад/с', np.abs(S[:, 2:]).max(0).round(1))
