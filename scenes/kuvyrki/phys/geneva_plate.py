import numpy as np
class Star:
    """Мальтийский крестик на плашке. theta — прогресс кувырка (град, растёт вперёд).
    Зуб неподвижен на оси, радиус RT; центр крестика S=(-C,0) в (u,v) плашки.
    Кувырок вперёд = полярный угол в (u,v) убывает, поэтому зуб в системе плашки на угле alpha+theta."""
    def __init__(s,win_center=295.0,C=4.0,RT=3.0,slot=3.5,turns=14,step=0.05,psi0=None):
        s.C,s.RT=C,RT; s.alpha=180.0-win_center
        th=np.arange(0,360*turns+step,step); psi=np.empty_like(th)
        cur=psi0 if psi0 is not None else 0.0
        S=np.array([-C,0.0]); first=True
        for i,t in enumerate(th):
            a=np.radians(s.alpha+t); P=np.array([RT*np.cos(a),RT*np.sin(a)]); rel=P-S
            if np.linalg.norm(rel)<=slot:
                b=np.degrees(np.arctan2(rel[1],rel[0]))
                if first and psi0 is None: cur=b; first=False
                n=np.round((cur-b)/90.0); cand=b+90*n
                if abs(cand-cur)<25: cur=cand
            psi[i]=cur
        s.th,s.psi=th,psi
    def __call__(s,theta): return float(np.interp(theta,s.th,s.psi))
