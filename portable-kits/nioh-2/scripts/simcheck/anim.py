"""Skirt and chain physics on a synthetic run: the Python port of sim_a.hlsl (simpy.py) driven by an eased start, a
symmetric 45 deg gait, an eased stop and a 120 deg turn. Prints the max swing per chain group (skirt, side hair,
twin tails, ears) per phase and the frames where skin pokes out of the skirt.
usage: anim.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
import sys
from simpy import *     # noqa: F401,F403


def smooth(x):
    x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)


def frame_T(t):
    """token -> 4x4 at time t (s): eased start, run 0.3-1.7 s, eased stop, idle, 120 deg turn at 2.6 s, idle."""
    run = smooth(t / 0.3) * (1 - smooth((t - 1.7) / 0.3))
    ph = 2 * np.pi * 1.4 * t
    legs = dict(flexL=45 * run * np.sin(ph), flexR=-45 * run * np.sin(ph), twist=10 * run * np.sin(ph), bend=8 * run)
    T = pose2(**legs)
    # forward distance: integral of 450 * run
    ts = np.arange(0, t, 1 / 240.0)
    z = np.sum(450 * smooth(ts / 0.3) * (1 - smooth((ts - 1.7) / 0.3))) / 240.0
    yaw = np.radians(120) * smooth((t - 2.6) / 0.25)
    G = np.eye(4)
    c, s = np.cos(yaw), np.sin(yaw)
    G[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
    piv = np.array([0, 110, 1.85])
    G[:3, 3] = np.array([0, 2 * run * np.sin(2 * ph), z]) + piv - G[:3, :3] @ piv
    out = {f'g{i}': G for i in range(130)}
    out.update({k: G @ v for k, v in T.items()})
    out['__root__'] = G
    return out, G


def run_anim(over=None, T_end=3.6, check_every=3, verbose=False):
    sim = Sim(over)
    g0 = outer_grid(SP, Stris)
    Tp, _ = frame_T(0)
    dev = {k: [] for k in ('skirt', 'side', 'twin', 'ear')}
    poke_frames = []
    keys = {'skirt': [c for c in CH if c['key'].startswith('K')], 'side': [c for c in CH if c['key'] in ('HL', 'HR')],
            'twin': [c for c in CH if c['key'] in ('TL', 'TR')], 'ear': [c for c in CH if c['key'] in ('EL', 'ER')]}
    for f in range(int(T_end * 60)):
        t = f / 60.0
        T, G = frame_T(t)
        bones = sim.step(T, Tp)
        Tp = T
        for grp, cs in keys.items():
            m = 0
            for c in cs:
                n, j0, p0 = c['n'], c['j0'], c['p0']
                rT = xf(jframe(T, j0 + n), JOINTS[j0 + n]); r0 = xf(jframe(T, j0), JOINTS[j0])
                pT = sim.cur[p0 + n - 1]
                L = np.linalg.norm(rT - r0)
                m = max(m, np.degrees(2 * np.arcsin(min(1, np.linalg.norm(pT - rT) / (2 * L)))))
            dev[grp].append(m)
        if f % check_every == 0:
            Gi = np.linalg.inv(G)
            Sp = skin_all(SP, SKIRT_GW, T, bones)
            Sp = (Gi[:3, :3] @ Sp.T).T + Gi[:3, 3]
            g = outer_grid(Sp, Stris); n_ = 0; w_ = 0
            for bn, (P, tris, bgw, m) in BODY.items():
                r0s, r0 = lookup(g0, P)
                cov = np.isfinite(r0s) & (r0 < r0s - 0.2) & (P[:, 1] > 78) & (P[:, 1] < 121)
                Pp = skin(P[cov], [bgw[j] for j in np.nonzero(cov)[0]], T)
                Pp = (Gi[:3, :3] @ Pp.T).T + Gi[:3, 3]
                rs, r = lookup(g, Pp); o = np.isfinite(rs) & (r > rs)
                n_ += o.sum(); w_ = max(w_, np.where(o, r - rs, 0).max(initial=0))
            if n_:
                poke_frames.append((round(t, 2), int(n_), round(float(w_), 1)))
    d = {k: np.array(v) for k, v in dev.items()}
    seg = lambda a, b: slice(int(a * 60), int(b * 60))  # noqa: E731
    summary = {k: 'run %.1f stop %.1f turn %.1f end %.2f' % (v[seg(0.4, 1.7)].max(), v[seg(1.7, 2.6)].max(),
                                                           v[seg(2.6, 3.4)].max(), v[-1]) for k, v in d.items()}
    return summary, poke_frames, d


if __name__ == '__main__':
    s, pk, d = run_anim()
    for k, v in s.items():
        print(f'{k:6s} {v}')
    print('poke frames', len(pk), pk[:12])
