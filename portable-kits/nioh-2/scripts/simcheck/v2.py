"""Skirt weight experiment: kernel transfer from the body with a constant, gap-scaled or height-blended sigma;
prints penetration and stretch per variant.
usage: v2.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from adapt import *
POSES.clear()
POSES.update({'run': dict(flexL=50, flexR=-30, twist=15, bend=10), 'sprint': dict(flexL=75, flexR=-35, twist=12, bend=15),
              'kneeup': dict(flexL=95, flexR=-10, bend=10), 'sprintR': dict(flexR=75, flexL=-35, twist=-12, bend=15),
              'crouch': dict(flexL=70, flexR=70, bend=25), 'side': dict(abdL=30), 'stance': dict(abdL=12, abdR=12, flexL=10, flexR=10)})

def src_arrays():
    pts, ws = [], []
    for n in ('body_2', 'underwear'):
        P, tris, gw, m = BODY[n] if n in BODY else mesh(n)
        for i in range(len(P)):
            if 60 < P[i, 1] < 130 and set(gw[i]) <= OK_TOK:
                pts.append(P[i]); ws.append(gw[i])
    toks = sorted({t for d in ws for t in d}, key=lambda t: int(t[1:]))
    ti = {t: j for j, t in enumerate(toks)}
    Wsrc = np.zeros((len(ws), len(toks)))
    for i, d in enumerate(ws):
        s = sum(d.values())
        for t, w in d.items(): Wsrc[i, ti[t]] = w / s
    return np.array(pts), Wsrc, toks
PTS, WSRC, TOKS = src_arrays()
TREE = cKDTree(PTS)
NB = mesh_nb(len(SP), Stris)

def kern(sig, k=128):
    d, idx = TREE.query(SP, k)
    a = np.exp(-((d - d[:, :1]) / sig[:, None]) ** 2)
    return np.einsum('vk,vkt->vt', a, WSRC[idx]) / a.sum(1, keepdims=True), d[:, 0]

def finish(W, iters):
    for _ in range(iters):
        W = 0.5 * W + 0.5 * np.array([W[s].mean(0) if len(s) else W[v] for v, s in enumerate(NB)])
    out = []
    for v in range(len(SP)):
        order = np.argsort(-W[v])[:4]
        out.append({TOKS[j]: float(W[v, j]) for j in order if W[v, j] > 1e-3})
    return out

_, GAP = TREE.query(SP, 1)
def variant(kind, a=1.0, c=0.8, g0=4.0, y0=92.0, y1=80.0, it=8):
    if kind == 'A':
        W, _ = kern(a + c * GAP)
    elif kind == 'B':
        W, _ = kern(a + c * np.maximum(GAP - g0, 0))
    elif kind == 'D':
        Wn, _ = kern(np.full(len(SP), a)); Ww, _ = kern(a + c * GAP)
        t = np.clip((y0 - SP[:, 1]) / (y0 - y1), 0, 1); t = t * t * (3 - 2 * t)
        W = (1 - t[:, None]) * Wn + t[:, None] * Ww
    return finish(W, it)

if __name__ == '__main__':
    for lab, kw in [('A 1/.8', dict(kind='A')), ('B g4', dict(kind='B')), ('B g6', dict(kind='B', g0=6)),
                    ('D 92-80', dict(kind='D')), ('D 88-78', dict(kind='D', y0=88, y1=78)), ('D 92-80 it3', dict(kind='D', it=3))]:
        gw = variant(**kw)
        abs_stretch_poses = None
        evaluate(gw, lab)
