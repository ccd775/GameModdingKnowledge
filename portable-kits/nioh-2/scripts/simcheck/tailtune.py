"""Fox tail (chain TA) tuning: tip swing during eased run / stop / 120 deg turn, and how deep tail particles get into
the thigh capsules (the tail only collides with the pelvis sphere in build 4)."""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
import sys
from anim import *      # noqa: F401,F403  (frame_T, Sim, CH, COL, JOINTS, jframe, xf, np)

TA = next(c for c in CH if c['key'] == 'TA')


def seg_dist(p, a, b):
    ab = b - a
    t = np.clip(np.dot(p - a, ab) / max(np.dot(ab, ab), 1e-6), 0, 1)
    return np.linalg.norm(p - (a + t * ab))


def run(over, cols=None, T_end=3.6):
    if cols is not None:
        TA['cols'] = cols
    sim = Sim({'TA': over})
    Tp, _ = frame_T(0)
    dev, pen = [], []
    n, j0, p0 = TA['n'], TA['j0'], TA['p0']
    for f in range(int(T_end * 60)):
        t = f / 60.0
        T, G = frame_T(t)
        sim.step(T, Tp)
        Tp = T
        r0 = xf(jframe(T, j0), JOINTS[j0]); rT = xf(jframe(T, j0 + n), JOINTS[j0 + n])
        pT = sim.cur[p0 + n - 1]
        L = np.linalg.norm(rT - r0)
        dev.append(np.degrees(2 * np.arcsin(min(1, np.linalg.norm(pT - rT) / (2 * L)))))
        worst = 0
        for cc in COL:
            if cc['name'] not in ('thighL', 'thighR'):
                continue
            m = tokmat(T, USED_B[cc['tok']])
            a, b = xf(m, cc['a']), xf(m, cc['b'])
            for k in range(1, n + 1):
                worst = max(worst, cc['r'] - seg_dist(sim.cur[p0 + k - 1], a, b))
        pen.append(worst)
    d = np.array(dev); pe = np.array(pen)
    s = lambda a, b: slice(int(a * 60), int(b * 60))  # noqa: E731
    return ('run %5.1f  stop %5.1f  turn %5.1f  end %4.1f | thigh pen %4.1f cm'
            % (d[s(0.4, 1.7)].max(), d[s(1.7, 2.6)].max(), d[s(2.6, 3.4)].max(), d[-1], pe.max()))


_plain_T = frame_T


def rotm(axis, deg):
    a = np.radians(deg); axis = np.array(axis, float); axis /= np.linalg.norm(axis)
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def sway_T(t):
    """anim.frame_T plus the whole body swaying with the stride (8 deg yaw, 4 deg roll about the pelvis): the plain
    harness keeps the pelvis (the tail's anchor) rigid, which a real run does not."""
    out, G = _plain_T(t)
    run_ = smooth(t / 0.3) * (1 - smooth((t - 1.7) / 0.3))
    ph = 2 * np.pi * 1.4 * t
    R = rotm([0, 1, 0], 8 * run_ * np.sin(ph)) @ rotm([0, 0, 1], 4 * run_ * np.sin(ph))
    piv = np.array([0, 105, 0.0]); M = np.eye(4); M[:3, :3] = R; M[:3, 3] = piv - R @ piv
    return {k: (v @ M if k != '__root__' else v) for k, v in out.items()}, G


def droop(over):
    """tip drop after 4 s standing still."""
    n, j0, p0 = TA['n'], TA['j0'], TA['p0']
    sim = Sim({'TA': over}); T, _ = _plain_T(0.0)
    for f in range(240):
        sim.step(T, T)
    rT = xf(jframe(T, j0 + n), JOINTS[j0 + n])
    return 'idle tip drop %.1f cm' % (rT[1] - sim.cur[p0 + n - 1][1])


if __name__ == '__main__':
    print('TA joints', [tuple(np.round(JOINTS[TA['j0'] + k], 1)) for k in range(TA['n'] + 1)], 'cols', TA['cols'])
    base = {k: TA[k] for k in ('k0', 'k1', 'damp', 'inertia', 'lag', 'cosmax', 'grav')}
    print('built tuning', base)
    frame_T = sway_T
    b4 = dict(k0=0.15, k1=0.08, damp=0.85, inertia=0.5, lag=5.0, grav=300 / 3600)
    for name, o in [('build 4', b4), ('built', {}),
                    ('softer', dict(k0=0.06, k1=0.03, damp=0.94, inertia=0.7, lag=5.0, grav=300 / 3600))]:
        print(f'{name:8s}', run(o), '|', droop(o))
        sys.stdout.flush()
