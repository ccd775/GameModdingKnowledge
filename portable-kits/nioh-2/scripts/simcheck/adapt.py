"""Skirt weight experiment: adaptive Gaussian transfer from the body under the skirt (sigma grows with the distance
to the nearest body point) plus mesh smoothing; prints stretch and penetration on the test2 poses per setting.
usage: adapt.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from harm import *

def adaptive_xfer(SP, Stris, s0=1.5, c=0.6, k=96, iters=3, srcs=('body_2', 'underwear')):
    pts, ws = [], []
    for n in srcs:
        P, tris, gw, m = BODY[n] if n in BODY else mesh(n)
        for i in range(len(P)):
            if 60 < P[i, 1] < 130 and set(gw[i]) <= OK_TOK:
                pts.append(P[i]); ws.append(gw[i])
    pts = np.array(pts)
    toks = sorted({t for d in ws for t in d}, key=lambda t: int(t[1:]))
    ti = {t: j for j, t in enumerate(toks)}
    Wsrc = np.zeros((len(ws), len(toks)))
    for i, d in enumerate(ws):
        s = sum(d.values())
        for t, w in d.items(): Wsrc[i, ti[t]] = w / s
    tree = cKDTree(pts)
    d, idx = tree.query(SP, k)
    sig = s0 + c * d[:, :1]
    a = np.exp(-((d - d[:, :1]) / sig) ** 2)
    W = np.einsum('vk,vkt->vt', a, Wsrc[idx]) / a.sum(1, keepdims=True)
    nb_ = mesh_nb(len(SP), Stris)
    for _ in range(iters):
        W = 0.5 * W + 0.5 * np.array([W[s].mean(0) if len(s) else W[v] for v, s in enumerate(nb_)])
    out = []
    for v in range(len(SP)):
        order = np.argsort(-W[v])[:4]
        out.append({toks[j]: float(W[v, j]) for j in order if W[v, j] > 1e-3})
    return out

if __name__ == '__main__':
    for s0, c, k, it in ((1.5, 0.6, 96, 3), (1.5, 1.0, 160, 3), (2.0, 0.4, 96, 5), (1.0, 0.8, 128, 8)):
        gw = adaptive_xfer(SP, Stris, s0, c, k, it)
        lab = f'a{s0}/{c}/{k}/{it}'
        abs_stretch(gw, lab)
        evaluate(gw, lab)
