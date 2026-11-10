"""Offline test of fox-ear tunings (two-segment chain Ear_L on Karin's conformed joints, N2_BUILD/build1/conform.json)
on an eased run and stop with bob and head pitch, a 120 deg standing turn and a 30 cm lunge: max swing per phase,
rebounds above 1.5 deg and the swing left after 3 s.
usage: eartest.py"""
import argparse
import os
argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
if not os.environ.get('N2_BUILD'):
    raise SystemExit('N2_BUILD is not set: point it at the build directory (build1/conform.json)')
import json, numpy as np
J = {k: np.array(v) for k, v in json.load(open(os.path.join(os.environ['N2_BUILD'], 'build1', 'conform.json')))['karin_joints_game'].items()}
def smooth(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def anchor_at(t, mode):
    piv = J['Head']
    if mode == 'runstop':   # accelerate 0.3 s, run with bob (4 cm, 2.6 Hz) and head pitch, decelerate over 0.3 s at 1.5 s
        v = 450 * smooth(t / 0.3) * (1 - smooth((t - 1.5) / 0.3))
        z = np.sum([450 * smooth(tt / 0.3) * (1 - smooth((tt - 1.5) / 0.3)) / 120 for tt in np.arange(0, t, 1 / 120)])
        run = v / 450
        pos = np.array([0, 2 * run * np.sin(2 * np.pi * 2.6 * t), z]); ang = 0; pitch = np.radians(4) * run * np.sin(2 * np.pi * 2.6 * t + 1)
    elif mode == 'turn':    # character turns 120 deg in 0.25 s (standing)
        pos = np.zeros(3); ang = np.radians(120) * smooth(t / 0.25); pitch = 0
    else:                   # attack-like jolt: 30 cm lunge in 0.15 s then back over 0.4 s
        d = 30 * smooth(t / 0.15) * (1 - smooth((t - 0.3) / 0.4)); pos = np.array([0, 0, d]); ang = 0; pitch = np.radians(10) * smooth(t / 0.15) * (1 - smooth((t - 0.3) / 0.4))
    c, s = np.cos(ang), np.sin(ang); Ry = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
    cp, sp = np.cos(pitch), np.sin(pitch); Rx = np.array([[1, 0, 0], [0, cp, -sp], [0, sp, cp]])
    R = Ry @ Rx
    A = np.eye(4); A[:3, :3] = R; A[:3, 3] = pos + piv - R @ piv; return A
def run(names, k0, k1, damp, inertia, mode, T=3.0):
    pts = np.array([J[n] for n in names]); n = len(pts) - 1
    xf = lambda A, p: (A @ np.r_[p, 1])[:3]
    cur = old = rprev = None; dev = []
    for f in range(int(T * 60)):
        A = anchor_at(f / 60, mode); r = np.array([xf(A, p) for p in pts])
        if cur is None: cur = r.copy(); old = r.copy(); rprev = r.copy()
        carry = (r - rprev) * (1 - inertia); cur = cur + carry; old = old + carry
        p = r.copy()
        for k in range(1, n + 1):
            stiff = k0 + (k1 - k0) * ((k - 1) / max(n - 1, 1))
            q = cur[k] + (cur[k] - old[k]) * damp
            p[k] = q + (r[k] - q) * stiff
        for it in range(3):
            for k in range(1, n + 1):
                rd = r[k] - r[k - 1]; d = p[k] - p[k - 1]
                p[k] = p[k - 1] + d / np.linalg.norm(d) * np.linalg.norm(rd)
        old, cur, rprev = cur, p, r
        L = np.linalg.norm(pts[-1] - pts[0])
        dev.append(np.degrees(2 * np.arcsin(min(1, np.linalg.norm(p[-1] - r[-1]) / (2 * L)))))
    return np.array(dev)
def bounces(d, start):
    st = d[start:]
    return sum(1 for i in range(1, len(st) - 1) if st[i] > st[i - 1] and st[i] >= st[i + 1] and st[i] > 1.5)
E2 = ['Ear_L', 'Ear_L_001', 'Ear_L_001_end']
for lab, a in [('b3 cur', (.22, .15, .92, .35)), ('P', (.14, .09, .94, .55)), ('Q', (.12, .07, .95, .6)),
               ('R', (.10, .06, .95, .65)), ('S', (.16, .08, .95, .6)), ('T', (.12, .06, .96, .6)), ('U', (.09, .05, .94, .7))]:
    rs = run(E2, *a, 'runstop'); tu = run(E2, *a, 'turn'); jo = run(E2, *a, 'jolt')
    print(f'{lab:7s} run {rs[30:90].max():4.1f}  stop {rs[90:150].max():4.1f} (bounces {bounces(rs, 100)})  turn {tu.max():4.1f} (b {bounces(tu, 10)})  jolt {jo.max():4.1f} (b {bounces(jo, 15)})  settle@3s {rs[-1]:.2f}')
