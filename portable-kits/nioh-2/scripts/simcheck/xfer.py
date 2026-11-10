"""Skirt weight experiment: nearest-body weight transfer (k neighbours, Gaussian falloff) with Laplacian smoothing;
prints the skirt-to-body distance and penetration on the test2 poses per setting.
usage: xfer.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
from test2 import *
from scipy.spatial import cKDTree

OK_TOK = {'g0', 'g1', 'g2'} | LEGTOK

def body_xfer(SP, Stris, k=12, sigma=2.0, iters=5, srcs=('body_2', 'underwear')):
    pts, ws = [], []
    for n in srcs:
        P, tris, gw, m = BODY[n] if n in BODY else mesh(n)
        for i in range(len(P)):
            if 70 < P[i, 1] < 130 and set(gw[i]) <= OK_TOK:
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
    a = np.exp(-((d - d[:, :1]) / sigma) ** 2)
    W = np.einsum('vk,vkt->vt', a, Wsrc[idx]) / a.sum(1, keepdims=True)
    # Laplacian smoothing over the skirt mesh
    nv = len(SP)
    nb_ = [set() for _ in range(nv)]
    for t in Stris:
        for i in range(3):
            nb_[t[i]].update((t[(i + 1) % 3], t[(i + 2) % 3]))
    for _ in range(iters):
        W = 0.5 * W + 0.5 * np.array([W[list(s)].mean(0) if s else W[v] for v, s in enumerate(nb_)])
    out = []
    for v in range(nv):
        order = np.argsort(-W[v])[:4]
        dct = {toks[j]: float(W[v, j]) for j in order if W[v, j] > 1e-3}
        out.append(dct)
    return out, d[:, 0]

if __name__ == '__main__':
    for kk, sg, it in ((12, 2.0, 5), (16, 3.0, 10), (8, 1.5, 0)):
        gw, dmin = body_xfer(SP, Stris, kk, sg, it)
        print('nearest body dist: med %.1f p95 %.1f max %.1f' % (np.median(dmin), np.percentile(dmin, 95), dmin.max()))
        evaluate(gw, f'x{kk}/{sg}/{it}')
