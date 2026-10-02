"""Target-skeleton descriptions: which game bone plays each humanoid role, plus bind joints in Blender space.
usage: rigspec.py --character kratos|valk --wad W --out J"""
import json
import numpy as np
from rig import parse_rig

def world(rig_bytes):
    n, par, mats, ibm, mo = parse_rig(rig_bytes)
    W = [None] * n
    for i in range(n):
        W[i] = mats[i] if par[i] < 0 else mats[i] @ W[par[i]]
    return n, par, np.array([w[3, :3] for w in W])

def mirror(P, i, par):
    """Bone at the X-mirrored position; ties (helpers stacked on one joint) go to the one whose parent mirrors i's parent."""
    q = P[i] * np.array([-1, 1, 1])
    d = np.linalg.norm(P - q, axis=1); d[i] = 9
    cands = [int(j) for j in np.nonzero(d < 2e-3)[0]]
    assert cands, (i, float(d.min()))
    if len(cands) > 1 and par[i] >= 0:
        pp = P[par[i]] * np.array([-1, 1, 1])
        cands.sort(key=lambda j: np.linalg.norm(P[par[j]] - pp) if par[j] >= 0 else 9)
    return cands[0]

def make_spec(rig_bytes, core, right, pad_joint=None, left_override=None):
    """core: Hips/Spine/Chest/Neck/Head bone ids; right: right-side role -> bone id (fingers as lists).
    Left side is found by mirroring X (left_override wins where several bones mirror equally well).
    GoW: -Z forward, +X = character's right. Use bones that actually carry skin weights: rigs such as
    freyavalkyrie00 stack non-deforming FK controls on the same joints, and skin bound to those stays put."""
    n, par, P = world(rig_bytes)
    left = {}
    for k, v in right.items():
        left[k] = [mirror(P, b, par) for b in v] if isinstance(v, list) else mirror(P, v, par)
    left.update(left_override or {})
    joints = {int(i): [-float(P[i, 0]), float(P[i, 2]), float(P[i, 1])] for i in range(n)}   # -> Blender (-x, z, y)
    return dict(core=core, Left=left, Right=right, joints=joints, pad_joint=pad_joint)

# Per-character bone roles for game build 18979360 (bone ids are build-sensitive). `proto` names the WAD entry that
# holds the skeleton. kratos was read from the reference mod's r_heroa00.wad; valk from the original
# r_freyavalkyrie00.wad and uses the deforming bones, not the FK controls stacked on the same joints.
SPECS = {
    'kratos': dict(proto='goProtoheroa00',
        core=dict(Hips=163, Spine=175, Chest=193, Neck=219, Head=318),
        right=dict(clav=221, sh=329, el=955, wr=1103, hip=167, kn=181, an=208, toe=315, toe_tip=452,
                   Index=[1326, 1388, 1432, 1453], Middle=[1327, 1389, 1433, 1454], Ring=[1328, 1390, 1434, 1455],
                   Little=[1329, 1391, 1435, 1456], Thumb=[1207, 1330, 1392, 1436]),
        pad_joint=1447),
    'valk': dict(proto='goProtofreyaValkyrie00',
        core=dict(Hips=14, Spine=69, Chest=94, Neck=111, Head=136),
        right=dict(clav=113, sh=842, el=838, wr=972, hip=59, kn=82, an=76, toe=105, toe_tip=134,
                   Index=[1282, 1386, 1434, 1434], Middle=[1283, 1387, 1435, 1435], Ring=[1280, 1384, 1433, 1433],
                   Little=[1284, 1388, 1436, 1436], Thumb=[1158, 1281, 1385, 1385]),
        pad_joint=None, left_override=dict(kn=91)),
}

if __name__ == '__main__':
    import argparse
    from wad import Wad
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--character', required=True, choices=sorted(SPECS))
    ap.add_argument('--wad', required=True, help='WAD holding the skeleton: r_heroa00.wad (kratos) or r_freyavalkyrie00.wad (valk)')
    ap.add_argument('--out', required=True, help='output rigspec .json')
    args = ap.parse_args()
    cfg = dict(SPECS[args.character])
    proto = cfg.pop('proto')
    w = Wad(open(args.wad, 'rb').read())
    spec = make_spec(w.get([e for e in w.entries if e.name == proto][0]), **cfg)
    json.dump(spec, open(args.out, 'w'))
    print('left', args.character, spec['Left'])
