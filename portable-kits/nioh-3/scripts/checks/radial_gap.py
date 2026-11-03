"""Radial rest gap of coat vertices behind her (|az| >= 100, y < 108): vertex radius minus the largest skirt / ribbon
radius within 3 deg and 1 cm. usage: radial_gap.py conformed.npz [..]"""
import argparse
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('files', nargs='+', metavar='conformed.npz')
args = ap.parse_args()
import numpy as np  # noqa: E402
for f in args.files:
    c = np.load(f); zc = float(c['skirt__pos'][:, 2].mean())
    S = np.concatenate([c['skirt__pos'], c['ribbon__pos']]).astype(float)
    Pc = c['coat__pos'].astype(float)
    az = np.degrees(np.arctan2(Pc[:, 0], Pc[:, 2] - zc))
    sel = np.nonzero((np.abs(az) >= 100) & (Pc[:, 1] < 108) & (np.abs(Pc[:, 0]) < 30))[0]
    rs = np.hypot(S[:, 0], S[:, 2] - zc); azs = np.degrees(np.arctan2(S[:, 0], S[:, 2] - zc))
    g = []
    for v in sel:
        m = (np.abs(((azs - az[v] + 180) % 360) - 180) < 3) & (np.abs(S[:, 1] - Pc[v, 1]) < 1.0)
        if m.any():
            g.append(np.hypot(Pc[v, 0], Pc[v, 2] - zc) - rs[m].max())
    g = np.array(g)
    print(f, len(g), 'radial gap min %.2f p5 %.2f p50 %.2f p95 %.2f max %.2f' % tuple(np.percentile(g, [0, 5, 50, 95, 100])),
          'below 1 cm', int((g < 1).sum()), 'below 1.5 cm', int((g < 1.5).sum()))
