"""anim.py with an asymmetric run (70 deg forward / 30 deg back strides, or 55 / 25) and a sideways dodge: rigid
chains vs the built tuning, thigh capsule radius 9 vs 11 cm.
usage: anim5.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
import anim, anim2
from anim2 import *
def gait(x, af, ae):
    return af * max(x, 0) - ae * max(-x, 0)
AMP2 = {'af': 70, 'ae': 30, 'dodge': False}
def frame_T5(t):
    run = smooth(t / 0.3) * (1 - smooth((t - 1.7) / 0.3))
    ph = 2 * np.pi * 1.4 * t; sn = np.sin(ph)
    fl, fr = gait(sn, AMP2['af'], AMP2['ae']) * run, gait(-sn, AMP2['af'], AMP2['ae']) * run
    T = pose2(flexL=fl, flexR=fr, twist=10 * run * sn, bend=8 * run)
    ts = np.arange(0, t, 1 / 240.0)
    z = np.sum(450 * smooth(ts / 0.3) * (1 - smooth((ts - 1.7) / 0.3))) / 240.0
    G = np.eye(4)
    if AMP2['dodge']:
        x = 250 * smooth((t - 2.6) / 0.25); dk = np.sin(np.pi * np.clip((t - 2.6) / 0.35, 0, 1))
        T = pose2(flexL=fl + 50 * dk, flexR=fr + 50 * dk, bend=8 * run + 20 * dk)
        G[:3, 3] = [x, 2 * run * np.sin(2 * ph) - 12 * dk, z]
    else:
        yaw = np.radians(120) * smooth((t - 2.6) / 0.25); c, s = np.cos(yaw), np.sin(yaw)
        G[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
        piv = np.array([0, 110, 1.85]); G[:3, 3] = np.array([0, 2 * run * np.sin(2 * ph), z]) + piv - G[:3, :3] @ piv
    out = {f'g{i}': G for i in range(130)}
    out.update({k: G @ v for k, v in T.items()}); out['__root__'] = G
    return out, G
anim.frame_T = frame_T5
ks = [f'K{n[6:]}' for n in nb.SKIRT_CHAINS]
def trial(lab, over=None, thighR=None, **amp):
    AMP2.update(amp)
    for c in COL:
        if c['name'].startswith('thigh'): c['r'] = thighR or 9.0
    s, pk, d = anim.run_anim(over)
    print(f'{lab:30s} skirt {s["skirt"]} | side {s["side"]} | pokes {len(pk)} worst {max([x[2] for x in pk], default=0)} {pk[:6]}', flush=True)
if __name__ == '__main__':
    trial('rigid 70/30', {k: dict(k0=1.0, k1=1.0, inertia=0.0) for k in ks}, af=70, ae=30)
    trial('default 70/30', af=70, ae=30)
    trial('default 70/30 thigh 11', thighR=11, af=70, ae=30)
    trial('default 70/30 dodge', af=70, ae=30, dodge=True)
    trial('default 55/25 dodge', af=55, ae=25, dodge=True)
