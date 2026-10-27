"""Minimal LDraw loader: flattens a part into triangles with colour codes.
Coordinates returned in Blender stud space: 1 unit = 1 stud (20 LDU),
Blender (x, y, z) = (lx, lz, -ly) / 20."""
import os, re

LIB = os.environ.get('LDRAW_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'ldraw'))
_index = None

def _build_index():
    global _index
    _index = {}
    for sub in ('parts', 'p', 'parts/s', 'p/48', 'p/8', 'parts/textures', 'models'):
        d = os.path.join(LIB, sub)
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            rel = os.path.relpath(root, d)
            for f in files:
                key = (f if rel == '.' else os.path.join(rel, f)).replace('\\', '/').lower()
                _index.setdefault(key, os.path.join(root, f))
    # unofficial / local extra dir
    return _index

def find(name):
    if _index is None:
        _build_index()
    n = name.replace('\\', '/').lower()
    return _index.get(n) or _index.get('s/' + n) or _index.get(n.split('/')[-1])

def mul(a, b):  # 3x4 affine (list of 12: a,b,c,x? ) we use (M 3x3, t)
    M1, t1 = a; M2, t2 = b
    M = [[sum(M1[i][k] * M2[k][j] for k in range(3)) for j in range(3)] for i in range(3)]
    t = [sum(M1[i][k] * t2[k] for k in range(3)) + t1[i] for i in range(3)]
    return (M, t)

def app(T, p):
    M, t = T
    return [sum(M[i][k] * p[k] for k in range(3)) + t[i] for i in range(3)]

_cache = {}

_HIRES = re.compile(r'^\d+-\d+[a-z0-9]*\.dat$')

def _resolve(name):
    n = name.replace('\\', '/').lower()
    if '/' not in n and _HIRES.match(n):
        hp = find('48/' + n)
        if hp:
            return hp
    return find(n)

def _load(name):
    """BFC-aware parse. items: ('sub', c, T, name, invertnext) / ('poly', c, pts, cw)"""
    if name in _cache:
        return _cache[name]
    path = _resolve(name)
    items = []
    if path is None:
        _cache[name] = items
        return items
    cw = False
    invnext = False
    for line in open(path, encoding='utf-8', errors='ignore'):
        tok = line.split()
        if not tok:
            continue
        if tok[0] == '0':
            up = [t.upper() for t in tok[1:]]
            if up[:1] == ['BFC']:
                if 'INVERTNEXT' in up:
                    invnext = True
                if 'CW' in up:
                    cw = True
                if 'CCW' in up:
                    cw = False
            continue
        if tok[0] == '1' and len(tok) >= 15:
            c = int(tok[1]) if tok[1].lstrip('-').isdigit() else 16
            x, y, z = map(float, tok[2:5])
            a, b, cc, d, e, f, g, h, i = map(float, tok[5:14])
            items.append(('sub', c, ([[a, b, cc], [d, e, f], [g, h, i]], [x, y, z]), ' '.join(tok[14:]), invnext))
            invnext = False
        elif tok[0] in ('3', '4'):
            n = int(tok[0])
            try:
                c = int(tok[1])
            except ValueError:
                c = 16
            pts = [list(map(float, tok[2 + 3 * k: 5 + 3 * k])) for k in range(n)]
            items.append(('poly', c, pts, cw))
            invnext = False
    _cache[name] = items
    return items

def _det(M):
    return (M[0][0] * (M[1][1] * M[2][2] - M[1][2] * M[2][1])
            - M[0][1] * (M[1][0] * M[2][2] - M[1][2] * M[2][0])
            + M[0][2] * (M[1][0] * M[2][1] - M[1][1] * M[2][0]))

def flatten(name, T=None, color=16, out=None, depth=0, inv=False):
    """output polys wound CCW (as seen from outside) in LDraw space"""
    if T is None:
        T = ([[1, 0, 0], [0, 1, 0], [0, 0, 1]], [0, 0, 0])
    if out is None:
        out = []
    if depth > 40:
        return out
    for it in _load(name):
        if it[0] == 'sub':
            _, c, T2, sub, invn = it
            cc = color if c in (16, 24) else c
            sinv = inv ^ invn ^ (_det(T2[0]) < 0)
            flatten(sub, mul(T, T2), cc, out, depth + 1, sinv)
        else:
            _, c, pts, cw = it
            cc = color if c in (16, 24) else c
            P = [app(T, p) for p in pts]
            if cw ^ inv:
                P = P[::-1]
            out.append((cc, P))
    return out

def to_blender(p):
    return (p[0] / 20.0, p[2] / 20.0, -p[1] / 20.0)

def part_polys(name, color=16):
    return [(c, [to_blender(p) for p in pts]) for c, pts in flatten(name, color=color)]

def bbox(name):
    ps = [p for _, pts in part_polys(name) for p in pts]
    if not ps:
        return None
    return [min(p[i] for p in ps) for i in range(3)], [max(p[i] for p in ps) for i in range(3)]

def colours():
    """LDraw colour code -> hex, from LDConfig.ldr"""
    res = {}
    for line in open(os.path.join(LIB, 'LDConfig.ldr'), encoding='utf-8', errors='ignore'):
        m = re.search(r'!COLOUR\s+(\S+)\s+CODE\s+(\d+)\s+VALUE\s+#([0-9A-Fa-f]{6})', line)
        if m:
            res[int(m.group(2))] = (m.group(1), m.group(3))
    return res
