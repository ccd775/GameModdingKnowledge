"""Structured dump of ModelAnimDynamicsDef (ADD1CBD3), the compiled form of ModelDef.AnimDynamics chains.

  python survey_dyn2.py npc_blackcat.model [boss_venom.model ...]

Layout so far (48 B header: u16 counts[8], i32 offsets[8], offsets relative to the end of the header):
  counts = (particles, links, ?, links, 0, chains, links, 0); table k uses offsets[k + 1], -1 = empty
  T0 particles 12 B, T1 links 64 B, T2 links 12 B, T3 links 32 B, T4 (empty), T5 chains 108 B, T6 links 40 B
"""
import argparse, struct, sys
import numpy as np
from sm2_common import load_index, load_toc, extract
import i30_model as M

SIZES = [12, 64, 12, 32, None, 108, 40]


def get(idx, toc, name):
    k = [n for n in idx if n.replace(chr(92), '/').endswith('/' + name)][0]
    return M.Model(extract(toc, int(idx[k]['id'], 16), 0)[0])


def words(b):
    out = []
    for o in range(0, len(b), 4):
        i, = struct.unpack_from('<i', b, o)
        f, = struct.unpack_from('<f', b, o)
        lo, hi = struct.unpack_from('<HH', b, o)
        if i == -1:
            out.append('-1')
        elif 0 < abs(f) < 1e5 and abs(f) > 1e-4:
            out.append(f'{f:.4f}')
        elif f == 0:
            out.append('0')
        else:
            out.append(f'{lo}|{hi}')
    return ' '.join(out)


def dump(m):
    s = m.sec(0xADD1CBD3)
    cnt = struct.unpack_from('<8H', s, 0)
    off = struct.unpack_from('<8i', s, 16)
    jn = [j['name'] for j in m.joints]
    W = m.joint_world()
    print('counts', cnt, 'offsets', off, 'len', len(s))
    base = 48
    ends = sorted([o for o in off[1:] if o >= 0] + [len(s) - base])
    for k in range(7):
        o = off[k + 1]
        if o < 0:
            continue
        e = min(x for x in ends if x > o) if any(x > o for x in ends) else len(s) - base
        n = (e - o) // SIZES[k] if SIZES[k] else 0
        print(f' T{k} @{o} bytes {e - o} (~{n} x {SIZES[k]})')
        for r in range(min(n, 30)):
            rec = s[base + o + r * SIZES[k]: base + o + (r + 1) * SIZES[k]]
            extra = ''
            if k in (1, 6):
                a, b, j, c = struct.unpack_from('<4H', rec, 0)
                p, = struct.unpack_from('<I', rec, 8)
                extra = f'  [{jn[j] if j < len(jn) else j} -> {jn[c] if c < len(jn) else c} | parent {jn[p] if p < len(jn) else p}]'
            if k == 3:
                p, a, b, c = struct.unpack_from('<4H', rec, 0)
                extra = f'  [{jn[p] if p < len(jn) else p}]'
            print(f'   {r:3d} {words(rec)}{extra}')
    return s, cnt, off


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('models', nargs='*')
    a = ap.parse_args()
    idx = load_index()
    toc = load_toc()
    for name in a.models:
        print('=' * 20, name)
        m = get(idx, toc, name)
        dump(m)
