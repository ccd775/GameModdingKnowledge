"""anim.py at 45 / 65 deg gaits, with a sideways dodge (and a crouch) in place of the turn, and with softer skirt
chains: skirt and side-hair swing per phase, frames with skin outside the skirt.
usage: anim2.py   (build dir: N2_BUILD)"""
import argparse
if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
import anim
from anim import *
AMP = {'legs': 45, 'dodge': False}
def frame_T2(t):
    run = smooth(t / 0.3) * (1 - smooth((t - 1.7) / 0.3))
    ph = 2 * np.pi * 1.4 * t
    T = pose2(flexL=AMP['legs'] * run * np.sin(ph), flexR=-AMP['legs'] * run * np.sin(ph), twist=10 * run * np.sin(ph), bend=8 * run)
    ts = np.arange(0, t, 1 / 240.0)
    z = np.sum(450 * smooth(ts / 0.3) * (1 - smooth((ts - 1.7) / 0.3))) / 240.0
    G = np.eye(4)
    if AMP['dodge']:   # sideways dodge 250 cm in 0.25 s at 2.6 s with a crouch
        x = 250 * smooth((t - 2.6) / 0.25); dk = np.sin(np.pi * np.clip((t - 2.6) / 0.35, 0, 1))
        T = pose2(flexL=AMP['legs'] * run * np.sin(ph) + 50 * dk, flexR=-AMP['legs'] * run * np.sin(ph) + 50 * dk, bend=8 * run + 20 * dk)
        G[:3, 3] = [x, 2 * run * np.sin(2 * ph) - 12 * dk, z]
    else:
        yaw = np.radians(120) * smooth((t - 2.6) / 0.25); c, s = np.cos(yaw), np.sin(yaw)
        G[:3, :3] = [[c, 0, s], [0, 1, 0], [-s, 0, c]]
        piv = np.array([0, 110, 1.85]); G[:3, 3] = np.array([0, 2 * run * np.sin(2 * ph), z]) + piv - G[:3, :3] @ piv
    out = {f'g{i}': G for i in range(130)}
    out.update({k: G @ v for k, v in T.items()}); out['__root__'] = G
    return out, G
anim.frame_T = frame_T2
if __name__ == '__main__':
    soft = {f'K{n[6:]}': dict(k0=0.18, k1=0.10, damp=0.9, inertia=0.6) for n in nb.SKIRT_CHAINS}
    for lab, legs, dodge, over in [('legs65 turn', 65, False, None), ('legs45 dodge', 45, True, None), ('legs65 dodge', 65, True, None),
                                    ('soft legs45 turn', 45, False, soft), ('soft legs65 dodge', 65, True, soft)]:
        AMP.update(legs=legs, dodge=dodge)
        s, pk, d = anim.run_anim(over)
        print(f'{lab:18s} skirt {s["skirt"]} | side {s["side"]} | pokes {len(pk)} {pk[:6]}', flush=True)
