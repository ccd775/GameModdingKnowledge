"""Rebuild the ModelAnimDynamicsDef of shipped models with i30_dynamics.build from parameters read back out of the
section, and diff every table (floats within 2e-4, quaternion sign ignored). Expect 0 mismatches everywhere.
Integer words (u16 pairs, indices) must match exactly: before 2026-10-13 they were also accepted when both read as tiny
denormal floats, which hid a wrong T5 field (first particle) on every chain after the first."""
import argparse, struct, sys
import numpy as np
from survey_dyn2 import get
from sm2_common import load_index, load_toc
import i30_dynamics as D

MODELS = ['prop_web_dangle.model', 'npc_blackcat.model', 'npc_greathunter.model', 'boss_venom.model',
          'enm_symbiote_rusher.model', 'boss_kraven.model', 'tor_02_cultist.model', 'enm_symbiote_grabber.model',
          'enm_symbiote_heavy.model', 'enm_symbiote_melee.model', 'enm_symbiote_melee_female.model',
          'enm_symbiote_ranged.model', 'prop_backpack_brooklynvisions.model', 'prop_backpack_spidercat.model',
          'enm_kraven_falcon_rt_wing.model', 'npc_lidemon_antivenom_34x.model']


def chains_from(m):
    s = m.sec(D.T_DYN)
    cnt = struct.unpack_from('<8H', s, 0)
    off = struct.unpack_from('<8i', s, 16)
    out = []
    for c in range(cnt[5]):
        r = s[48 + off[6] + 108 * c:48 + off[6] + 108 * (c + 1)]
        w = struct.unpack_from('<14HI', r, 0)
        typ, l0, n, rootj = w[0], w[1], w[2], w[13]
        js = [rootj] + [struct.unpack_from('<H', s, 48 + off[2] + 64 * (l0 + i) + 6)[0] for i in range(n)]
        f = struct.unpack_from('<11f', s, 48 + off[2] + 64 * l0 + 12)
        fe = struct.unpack_from('<11f', s, 48 + off[2] + 64 * (l0 + n - 1) + 12)
        g = struct.unpack_from('<3f', r, 88)
        damp, name = struct.unpack_from('<fI', r, 100)
        out.append(dict(joints=js, type=typ, mass=1 / f[1], mass_end=1 / fe[1], cone=np.degrees(np.arccos(min(f[3], 1))),
                        cone_end=np.degrees(np.arccos(min(fe[3], 1))), gravity=g, damping=damp, name_off=name,
                        cone_scale=(-f[5] / f[4], f[6] / f[4], -f[7] / f[4], f[8] / f[4])))
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('models', nargs='*', help='model file names (default: MODELS, the shipped models with dynamics)')
    a = ap.parse_args()
    idx = load_index()
    toc = load_toc()
    bad_total = 0
    for name in a.models or MODELS:
        m = get(idx, toc, name)
        s = m.sec(D.T_DYN)
        try:
            b = D.build(m, chains_from(m))
        except AssertionError as e:     # chains whose joints are not a parent -> child line (not built by i30_dynamics)
            print(f'{name}: skipped, not a simple joint line {e}')
            continue
        cnt = struct.unpack_from('<8H', s, 0)
        off = struct.unpack_from('<8i', s, 16)
        line = [f'{name}: len {len(s)}/{len(b)} header {"=" if s[:48] == b[:48] else "DIFF"}']
        sizes = [12, 64, 12, 32, None, 108, 40]
        cn = [cnt[0], cnt[1], cnt[1], cnt[1], 0, cnt[5], cnt[6]]
        for k in range(7):
            if off[k + 1] < 0:
                continue
            A = s[48 + off[k + 1]:48 + off[k + 1] + sizes[k] * cn[k]]
            B = b[48 + off[k + 1]:48 + off[k + 1] + sizes[k] * cn[k]]
            fa, fb = np.frombuffer(A, np.float32), np.frombuffer(B, np.float32)
            ia, ib = np.frombuffer(A, np.uint32), np.frombuffer(B, np.uint32)
            denorm = lambda i: ((i & 0x7F800000) == 0) & ((i & 0x7FFFFF) != 0)    # packed small ints read as floats
            real = ~denorm(ia) & ~denorm(ib)
            with np.errstate(invalid='ignore'):
                ok = (ia == ib) | (real & (np.isclose(fa, fb, atol=2e-4) | np.isclose(-fa, fb, atol=2e-4)))
            nb = int((~ok).sum())
            bad_total += nb
            words = sizes[k] // 4
            where = sorted({int(i) % words for i in np.where(~ok)[0]})
            line.append(f'T{k} {nb}' + (f' (word {where})' if nb else ''))
        print('  '.join(line))
    print('total mismatching words', bad_total)


if __name__ == '__main__':
    main()
