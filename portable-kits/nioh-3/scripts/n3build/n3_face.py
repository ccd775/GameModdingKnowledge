"""Karin's facial rig for Nioh 3: skin her face (Body mesh) to the player face bones so the game's facial poses
move it like her own shape keys.

The game drives faces with ~340 bones (ids 400-737) that every player model carries (base body, head, both chest
pieces). A facial pose library (g1fpose 0xc76b3a43, female, 389 poses, tools/fpose.py) gives each pose's bone
deltas, and weight animations (g1frani) mix poses: the gameplay idle face 0x5ca044ef blinks with poses 41/42
(left/right) at weight 1. Karin's face is ~1.7x the vanilla one (eyes at x=+-6.3 vs +-3.8, a full blink moves her
upper lid ~3 cm vs 1.2 cm), so every driven vertex is fitted to reproduce, for each mapped pose, the shape key mix it
stands for: non-negative ridge least squares over a few driver bones per pose, weights may exceed 1 and the vertex's
own (head) bones take the negative rest so the weights still sum to 1 exactly (quantised to a common f16 grid).
Drivers are limited to bones whose bind pose is identical in the base body, the female head and both chests, so the
result does not depend on which model's rest pose the game evaluates face bones from.

POSES: game pose -> {Karin shape key: amount}; DRIVERS bones per pose (largest translation, no control bones 718+).
Output: BUILD/face.json {weights: {Body vertex: [[bone, w], ...]}, report}
usage: n3_face.py [--extended]
"""
import argparse
import json
import sys

import numpy as np
from scipy.optimize import nnls

from n3_common import BODY, BUILD, CHEST, HERE, gt, load_model

sys.path.insert(0, str(HERE.parent))
import fpose  # noqa: E402  # pyright: ignore[reportMissingImports]

POSE_LIB = BUILD / 'face' / '0xc76b3a43.g1fpose'     # female player face library (ids 401-737, 389 poses)
SAME_BIND = ('0xb24cac84', BODY, CHEST, '0xed9b4309')  # female head, base body, ninja / samurai chest
POSES = {
    41: {'blink_L': 1.0}, 42: {'blink_R': 1.0},       # the idle face's blinks
    1: {'mayu_up_L': 1.0}, 2: {'mayu_up_R': 1.0},     # brow raise (vanilla +0.5 cm)
    3: {'mayu_down_L': 0.4}, 4: {'mayu_down_R': 0.4},  # brow lower (vanilla -0.2 cm)
    187: {'kuchi_A': 1.0},                            # jaw open
}
EXTRA = {     # --extended: channels the static expression presets (g1frani) use, fitted at EXTRA_PRIORITY
    27: {'blink_L': 1.0}, 28: {'blink_R': 1.0}, 39: {'blink_L': 1.0}, 40: {'blink_R': 1.0},  # other lid closures
    59: {'kuchi_smile_1_L': 1.0}, 60: {'kuchi_smile_1_R': 1.0},  # mouth corner up (vanilla +0.3 cm)
    160: {'kuchi_A': 0.4},                                      # lower lip down (vanilla -0.8 cm)
}
EXTRA_PRIORITY = 0.3          # least-squares weight of EXTRA poses against the POSES ones (1)
# not mapped: 5/6 brow knit (its drivers move sideways, Karin's angry brows turn down: residual ~60%),
# 147/148 mouth corner down (the largest movers differ between the sides)
DRIVERS = 6
MAX_ROT = 0.25                # rad: drivers that mostly rotate move far-away Karin vertices on long arcs
RIDGE = 0.02
MIN_TARGET = 0.02             # cm: vertices whose targets all stay below this keep their weights
MAX_BONES = 7                 # face bones per vertex (the 8th slot is the head bone)


def qmat(q):
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - w * z), 2 * (x * z + w * y)],
                     [2 * (x * y + w * z), 1 - 2 * (x * x + z * z), 2 * (y * z - w * x)],
                     [2 * (x * z - w * y), 2 * (y * z + w * x), 1 - 2 * (x * x + y * y)]])


def rvec(r):
    a = np.linalg.norm(r)
    if a < 1e-12:
        return np.eye(3)
    k = r / a
    K = np.array([[0, -k[2], k[1]], [k[2], 0, -k[0]], [-k[1], k[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K


def world(joints, by_id, pose):
    """World matrices of every joint with a pose's deltas (local rotation vector, parent-space translation, scale)."""
    out = []
    for j in joints:
        M = np.eye(4)
        M[:3, :3] = qmat(j['local_q']); M[:3, 3] = j['local_p']
        out.append(M)
    for b, r in pose.items():
        if b in by_id:
            M = out[by_id[b]]
            M[:3, :3] = M[:3, :3] @ rvec(r['rot']) @ np.diag(r['scale'])
            M[:3, 3] += r['loc']
    for i, j in enumerate(joints):
        if j['parent'] >= 0:
            out[i] = out[j['parent']] @ out[i]
    return out


def same_bind_bones():
    skels = [gt.skeleton(load_model(h)[1]) for h in SAME_BIND]
    ok = set()
    for b in range(400, 718):
        if all(b in ids for _, ids in skels):
            p = [np.array(J[ids[b]]['world_p']) for J, ids in skels]
            q = [np.array(J[ids[b]]['world_q']) for J, ids in skels]
            if max(np.linalg.norm(x - p[0]) for x in p) < 5e-3 and min(abs(x @ q[0]) for x in q) > 1 - 1e-6:
                ok.add(b)
    return ok


def shape_keys(head_scale):
    names = {r['name']: r['index'] for r in
             json.loads((BUILD / 'source' / 'shapekeys.json').read_text(encoding='utf-8'))['Body']}
    z = np.load(BUILD / 'source' / 'shapekeys.npz')
    def key(name):
        d = z[f'Body__{names[name]}'].astype(float)
        return head_scale * np.stack([d[:, 0], d[:, 2], -d[:, 1]], -1)      # Blender -> game axes, cm
    return key


def f16_grid(ws):
    """Quantise to one grid that f16 represents exactly at every |w| present; the last entry absorbs the rounding
    (it can cross a power of two, hence the coarser retry)."""
    e = int(np.floor(np.log2(max(abs(w) for w in ws))))
    for step in (e - 10, e - 9):
        q = 2.0 ** step
        out = [round(w / q) * q for w in ws[:-1]]
        out.append(1.0 - sum(out))
        if all(float(np.float16(w)) == w for w in out) and sum(out) == 1.0:
            return out
    raise AssertionError(ws)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--extended', action='store_true', help='also fit the EXTRA poses at EXTRA_PRIORITY')
    args = ap.parse_args()
    prio = {p: 1.0 for p in POSES}
    if args.extended:
        POSES.update(EXTRA)
        prio.update({p: EXTRA_PRIORITY for p in EXTRA})
    conf = np.load(BUILD / 'conformed.npz')
    head_scale = json.loads((BUILD / 'conform.json').read_text(encoding='utf-8'))['head_scale']
    P = conf['Body__pos'].astype(float)
    gws = [{int(b): w for b, w in json.loads(x).items()} for x in conf['Body__gw']]
    key = shape_keys(head_scale)
    _, chest = load_model(CHEST)
    joints, by_id = gt.skeleton(chest)
    lib = fpose.parse_pose(POSE_LIB.read_bytes())
    robust = same_bind_bones()
    rest = world(joints, by_id, {})
    inv = {b: np.linalg.inv(rest[by_id[b]]) for b in robust}
    H = np.c_[P, np.ones(len(P))]

    targets, drivers, disp = {}, {}, {}
    for p, mix in POSES.items():
        targets[p] = sum(a * key(n) for n, a in mix.items())
        pose = lib['poses'][p]
        cand = [b for b in pose if b in robust and np.linalg.norm(pose[b]['rot']) <= MAX_ROT]
        drivers[p] = sorted(cand, key=lambda b: -np.linalg.norm(pose[b]['loc']))[:DRIVERS]
        wm = world(joints, by_id, pose)
        for b in drivers[p]:
            S = wm[by_id[b]] @ inv[b]
            disp[p, b] = (H @ S.T)[:, :3] - P                                # unit-weight displacement per vertex
        side = np.sign(P[np.linalg.norm(targets[p], axis=1) > MIN_TARGET, 0].mean())
        print(p, mix, 'drivers', drivers[p], 'target side', '+x' if side > 0 else '-x')
    all_b = sorted({b for v in drivers.values() for b in v})
    # every driver's displacement in every mapped pose (0 when the pose does not move it)
    for p in POSES:
        wm = None
        for b in all_b:
            if (p, b) not in disp:
                if wm is None:
                    wm = world(joints, by_id, lib['poses'][p])
                disp[p, b] = (H @ (wm[by_id[b]] @ inv[b]).T)[:, :3] - P

    out = {}
    report: dict = {'poses': {str(p): {'mix': m, 'drivers': drivers[p]} for p, m in POSES.items()}}
    err = {p: [] for p in POSES}
    used = set()
    for v in range(len(P)):
        active = [p for p in POSES if np.linalg.norm(targets[p][v]) > MIN_TARGET]
        if not active:
            continue
        cand = sorted({b for p in active for b in drivers[p]})
        A = np.concatenate([np.sqrt(prio[p]) * np.stack([disp[p, b][v] for b in cand], 1) for p in POSES])
        t = np.concatenate([np.sqrt(prio[p]) * targets[p][v] for p in POSES])
        Ar = np.concatenate([A, np.sqrt(RIDGE) * np.eye(len(cand))]); tr = np.concatenate([t, np.zeros(len(cand))])
        w, _ = nnls(Ar, tr)
        keep = [i for i in np.argsort(-w)[:MAX_BONES] if w[i] > 1e-3]
        if not keep:
            continue
        w2, _ = nnls(np.concatenate([A[:, keep], np.sqrt(RIDGE) * np.eye(len(keep))]), np.concatenate([t, np.zeros(len(keep))]))
        face = [(cand[i], float(x)) for i, x in zip(keep, w2) if x > 1e-3]
        if not face:
            continue
        rest_share = 1.0 - sum(x for _, x in face)
        base = sorted(gws[v].items(), key=lambda kv: kv[1])                  # absorber (largest) last
        items = face + [(b, rest_share * x) for b, x in base]
        items = [it for it in items if abs(it[1]) > 1e-6 or it is items[-1]]
        ws = f16_grid([x for _, x in items])
        pairs = sorted(zip([b for b, _ in items], ws), key=lambda bw: -abs(bw[1]))
        assert len(pairs) <= 8, pairs
        out[str(v)] = [[int(b), w] for b, w in pairs]
        used |= {b for b, _ in face}
        fw = dict(face)
        for p in POSES:
            got = sum(fw.get(b, 0) * disp[p, b][v] for b in all_b)
            if np.linalg.norm(targets[p][v]) > MIN_TARGET:
                err[p].append((np.linalg.norm(got - targets[p][v]), np.linalg.norm(targets[p][v])))
    for p in POSES:
        e = np.array(err[p])
        report['poses'][str(p)].update({'vertices': len(e), 'target_max': round(float(e[:, 1].max()), 3),
                                        'residual_rms': round(float(np.sqrt((e[:, 0] ** 2).mean())), 3),
                                        'residual_max': round(float(e[:, 0].max()), 3)})
        print(p, report['poses'][str(p)])
    allw = [w for v in out.values() for _, w in v]
    report.update({'vertices': len(out), 'face_bones': sorted(used), 'max_weight': max(allw), 'min_weight': min(allw)})
    print('face vertices', len(out), 'bones', len(used), 'weight range', round(min(allw), 3), round(max(allw), 3))
    (BUILD / 'face.json').write_text(json.dumps({'weights': out, 'report': report}), encoding='utf-8')


if __name__ == '__main__':
    main()
