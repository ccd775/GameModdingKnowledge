"""Offline test of spring-chain tunings for the twin tails, the fox tail and an ear on Karin's conformed joints
(N2_BUILD/build1/conform.json): the chain is carried by a run with a 180 deg turn and by a 300 cm sidestep, stepped
like sim_a.hlsl (Verlet, stiffness ramp, inertia, fixed segment lengths). Prints the tip swing in degrees.
usage: simtest.py"""
import argparse
import os
argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
if not os.environ.get('N2_BUILD'):
    raise SystemExit('N2_BUILD is not set: point it at the build directory (build1/conform.json)')
import json, numpy as np, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
J = {k: np.array(v) for k, v in json.load(open(os.path.join(os.environ['N2_BUILD'], 'build1', 'conform.json')))['karin_joints_game'].items()}
def anchor_at(t, mode):
    if mode == 'run':
        pos = np.array([0, 0, min(t, 1.0) * 500.0]) + [0, 3 * np.sin(2 * np.pi * 2.5 * t) * (t < 1), 0]
        ang = np.pi * np.clip((t - 1.0) / 0.4, 0, 1)
    else:   # dodge roll-ish sidestep: 300 cm in 0.3 s
        pos = np.array([300 * np.clip(t / 0.3, 0, 1), 0, 0]); ang = 0
    c, s = np.cos(ang), np.sin(ang); R = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    A = np.eye(4); A[:3, :3] = R; A[:3, 3] = pos; return A
def run(names, k0, k1, damp, inertia, grav=300, mode='run', col=None):
    pts = np.array([J[n] for n in names]); n = len(pts) - 1; g = grav / 3600
    xf = lambda A, p: (A @ np.r_[p, 1])[:3]
    cur = old = None; dev = []; rprev = None
    for f in range(180):
        A = anchor_at(f / 60, mode); r = np.array([xf(A, p) for p in pts])
        if cur is None: cur = r.copy(); old = r.copy(); rprev = r.copy()
        carry = (r - rprev) * (1 - inertia); cur = cur + carry; old = old + carry
        p = r.copy()
        for k in range(1, n + 1):
            stiff = k0 + (k1 - k0) * ((k - 1) / max(n - 1, 1))
            q = cur[k] + (cur[k] - old[k]) * damp - [0, g, 0]
            p[k] = q + (r[k] - q) * stiff
        for it in range(3):
            for k in range(1, n + 1):
                rd = r[k] - r[k - 1]; d = p[k] - p[k - 1]
                p[k] = p[k - 1] + d / np.linalg.norm(d) * np.linalg.norm(rd)
        old, cur, rprev = cur, p, r
        L = np.linalg.norm(pts[-1] - pts[0])
        dev.append(np.degrees(np.arcsin(min(1, np.linalg.norm(p[-1] - r[-1]) / (2 * L))) * 2))
    d = np.array(dev)
    return 'run %4.1f deg  turn %4.1f deg  settle(1.5s) %4.2f deg' % (d[10:60].max(), d[60:90].max(), d[-1])
TL = ['Hair_tail_L_001', 'Hair_tail_L_002', 'Hair_tail_L_003', 'Hair_tail_L_004', 'Hair_tail_L_005', 'Hair_tail_L_005_end']
TA = ['Tail', 'Tail_001', 'Tail_002', 'Tail_003', 'Tail_004', 'Tail_005', 'Tail_005_end']
EL = ['Ear_L', 'Ear_L_001_end']
for lab, args in [('twin  cur', (TL, .12, .05, .88, 1.0)), ('twin  A', (TL, .12, .06, .88, .5)), ('twin  B', (TL, .15, .08, .85, .4)),
                  ('tail  A', (TA, .15, .08, .85, .5)), ('tail  B', (TA, .2, .1, .85, .4)),
                  ('ear   A', (EL, .3, .3, .7, .15)), ('ear   B', (EL, .25, .25, .75, .2))]:
    print(lab, run(*args), '| dodge', run(*args, mode='dodge').split('  turn')[0])
