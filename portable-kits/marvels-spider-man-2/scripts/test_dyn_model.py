"""Consistency checks for models built with --dyn (reads .model assets out of a .stage).

  python test_dyn_model.py ../builds/t6_dyn_test.stage

- bind pose: world matrices composed from ModelBindPose (scale, quat, pos) along the parents == inverse(InvBindPose)
- ModelJointLookup sorted, complete, hashes = crc32(name), sentinel last; Hierarchy joint / leaf counts; leaves childless
- ModelBuilt 0x20000000 set; ModelAnimDynamicsDef parses back (test_dyn_roundtrip.chains_from) and rebuilds identically
- every simulated joint carries skin weights somewhere in the Karin mesh (except chain tips)
- ModelMirrorIds: count = hierarchy mirror count, sorted, and every u2 & 0x01 joint is listed (T9 broke this in game)
- models built with --dyn-ab joints / plain have no ModelAnimDynamicsDef: those checks are skipped
"""
import argparse, json, os, struct, sys
import numpy as np

import i30_model as M
import i30_joints as IJ
import i30_dynamics as ID
import sm2_stage
import sm2_build_model as SB
from sm2_common import REPORTS
from test_dyn_roundtrip import chains_from


def bind_worlds(m):
    W = []
    for i, j in enumerate(m.joints):
        b = m.bind_local[i]
        L = np.eye(4)
        L[:3, :3] = ID.q2m(b['rot']).T * np.array(b['scale'])[:, None]
        L[3, :3] = b['pos']
        W.append(L if j['parent'] < 0 else L @ W[j['parent']])
    return np.array(W)


def check(m):
    out = []
    nj = len(m.joints)
    Wb = bind_worlds(m)
    Wi = m.joint_world()
    err = np.abs(Wb - Wi).max(axis=(1, 2))
    new = [i for i, j in enumerate(m.joints) if j['name'].startswith('karin_')]
    if not new:                          # static build (sm2_prop_test suit body): nothing to check here
        return True, ['no karin_ joints (static)']
    out.append(f'joints {nj} (+{len(new)} karin_), bind/invbind max err old {err[:new[0]].max():.2e} new {err[new].max():.2e}')
    L = m.sec(IJ.T_LOOKUP)
    pairs = [struct.unpack_from('<II', L, 8 * i) for i in range(len(L) // 8)]
    ok_lookup = (pairs[-1] == (0xFFFFFFFF, 0xFFFFFFFF) and [p[0] for p in pairs[:-1]] == sorted(p[0] for p in pairs[:-1])
                 and sorted(p[1] for p in pairs[:-1]) == list(range(nj))
                 and all(IJ.joint_hash(m.joints[i]['name']) == h and m.joints[i]['hash'] == h for h, i in pairs[:-1]))
    hier = struct.unpack_from('<4H', m.sec(IJ.T_HIER), 0)
    leaf = struct.unpack_from(f'<{len(m.sec(IJ.T_LEAF)) // 2}H', m.sec(IJ.T_LEAF), 0)
    parents = {j['parent'] for j in m.joints}
    ok_leaf = hier[1] == nj and hier[3] == len(leaf) and not (set(leaf) & parents)
    mir = m.sec(IJ.T_MIRROR)
    mp = [struct.unpack_from('<2H', mir, 4 * i) for i in range(len(mir) // 4)]
    listed = {a & 0xFFF for a, _ in mp} | {b for _, b in mp}
    ok_mirror = (len(mp) == hier[2] and [a & 0xFFF for a, _ in mp] == sorted(a & 0xFFF for a, _ in mp)
                 and all(i in listed for i, j in enumerate(m.joints) if j['u2'] & 1))
    built = struct.unpack_from('<I', m.sec(0x283D0383), 0)[0]
    s = m.sec(ID.T_DYN)
    if s is None:       # --dyn-ab joints / plain
        ch, same = [], not built & ID.BUILT_HAS_DYNAMICS
        tips = {j for j in new if not any(x['parent'] == j for x in m.joints)}
        chain_joints = new
    else:
        ch = chains_from(m)
        a_, b_ = np.frombuffer(s, np.uint32), np.frombuffer(ID.build(m, ch), np.uint32)
        fa, fb = a_.view(np.float32), b_.view(np.float32)
        with np.errstate(invalid='ignore'):
            same = len(a_) == len(b_) and bool(((a_ == b_) | np.isclose(fa, fb, atol=2e-4) | np.isclose(-fa, fb, atol=2e-4)).all())
        tips = {c['joints'][-1] for c in ch}
        chain_joints = [j for c in ch for j in c['joints']]
        # T5 integer fields checked against the shipped layout, independently of the builder (2026-10-13 bug):
        # word 3 = (links, first particle), word 4 = (particles, 0), u16 12 = first particle
        cnt = struct.unpack_from('<8H', s, 0)
        off = struct.unpack_from('<8i', s, 16)
        p0 = 0
        for c in range(cnt[5]):
            w = struct.unpack_from('<14H', s, 48 + off[6] + 108 * c)
            same = same and w[6] == w[2] and w[7] == p0 and w[8] == w[2] + 1 and w[9] == 0 and w[12] == p0
            p0 += w[8]
        same = same and p0 == cnt[0]
    names = [m.cstr(c['name_off']) for c in ch]
    out.append(f'lookup {"ok" if ok_lookup else "BAD"}  hierarchy/leaf {"ok" if ok_leaf else "BAD"} {hier}  '
               f'mirror {"ok" if ok_mirror else "BAD"}  '
               + (f'built dyn bit {"ok" if built & ID.BUILT_HAS_DYNAMICS else "MISSING"}  dyn chains {len(ch)} '
                  f'rebuild {"=" if same else "DIFF"}' if s is not None else f'no dynamics (A/B variant) {"ok" if same else "BUILT BIT SET"}'))
    out.append('chain names ' + ', '.join(names))
    lk = SB.looks(m)
    main = lk.get('body') or lk.get('Default')
    me = max((m.meshes[i] for i in main[0]), key=lambda x: x.vertex_count)
    d = m.decode(me)
    used = set(np.unique(d['joints'][d['weights'] > 0]).tolist())
    unweighted = [m.joints[j]['name'] for j in chain_joints if j not in used and j not in tips]
    flags = {hex(m.joints[j]['u2']) for j in new}
    out.append(f'unweighted simulated joints {unweighted[:6]}{"..." if len(unweighted) > 6 else ""} ({len(unweighted)}); new joint u2 {sorted(flags)}')
    ok = bool(err.max() < 1e-3 and ok_lookup and ok_leaf and ok_mirror and same
              and (s is None or built & ID.BUILT_HAS_DYNAMICS))
    return ok, out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('stage')
    a = ap.parse_args()
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    names = {sm2_stage.crc64_path(p): p for p in targets}
    from sm2_batch import BASES          # --dyn-base: the player base models carry the simulation
    names.update({sm2_stage.crc64_path(p): p for p in BASES.values()})
    from sm2_prop_test import PROP       # attached prop actor carrying the chains (T15+)
    names[sm2_stage.crc64_path(PROP)] = PROP
    from sm2_head_carrier import HEAD_MODEL   # head-actor carrier (T19+)
    names[sm2_stage.crc64_path(HEAD_MODEL)] = HEAD_MODEL
    _, entries = sm2_stage.read_stage(a.stage)
    bad = 0
    for span, aid, h, _, data in entries:
        p = names.get(aid)
        if span or p is None:
            continue
        ok, lines = check(M.Model(h + data))
        bad += not ok
        print(('ok  ' if ok else 'BAD ') + p.split('/')[-1])
        for x in lines:
            print('    ' + x)
    print(bad, 'bad')


if __name__ == '__main__':
    main()
