"""Nioh 3 G1M ONUN (NUNO, version 0036) reader, focused on type 0x00030004 bone-chain physics entries.
usage: nuno4.py <file.g1m> [...] [--dump]

Type-4 entry layout (reverse engineered on v2.0.0.2 hair / ornament / armour samples; offsets in bytes):
  +0   u32 parent bone id +4 u32 nPoints     +8 u32 nChains     +12 u32 A (1 or 2)
  +16  u32 nPoints       +20 u32 nChains    +24 u32 id         +28.. fixed parameter block up to +196
  +196 nChains  x u32    first point of each chain
       nChains  x 9 f32  root frame of each chain (row 0 = chain direction)
       nPoints  x (4 f32 position (model space, w=1), u32 chain index | 0x80000000 on a chain root,
                   f32 normalised position along the chain, f32 distance to the previous point)
       A        x u32
       nPoints  x (u32 point index, u32 skeleton storage index)
       nChains  x (u32 first point, u32 flags, u32 k, u32 n, n x (u32 bone id, f32 weight))  anchor binding
"""
import argparse
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool as gt  # noqa: E402

FIXED = 196


def parse_entry(b, o):
    u = lambda k: struct.unpack_from('<I', b, o + k)[0]  # noqa: E731
    e = {'offset': o, 'parent': u(0), 'n_points': u(4), 'n_chains': u(8), 'A': u(12), 'id': u(24),
         'fixed': b[o + 28:o + FIXED]}
    assert u(16) == e['n_points'] and u(20) == e['n_chains'], 'entry header'
    p = o + FIXED
    nc, npnt = e['n_chains'], e['n_points']
    e['chain_starts'] = list(struct.unpack_from(f'<{nc}I', b, p)); p += 4 * nc
    e['frames'] = [struct.unpack_from('<9f', b, p + 36 * i) for i in range(nc)]; p += 36 * nc
    e['points'] = []
    for i in range(npnt):
        x, y, z, w, ch, t, ln = struct.unpack_from('<4fIff', b, p); p += 28
        e['points'].append({'pos': (x, y, z), 'w': w, 'chain': ch & 0x7FFFFFFF, 'root': bool(ch & 0x80000000),
                            't': t, 'len': ln})
    e['a_list'] = list(struct.unpack_from(f"<{e['A']}I", b, p)); p += 4 * e['A']
    e['joints'] = [struct.unpack_from('<2I', b, p + 8 * i) for i in range(npnt)]; p += 8 * npnt
    e['anchors'] = []
    for i in range(nc):
        start, flags, k, n = struct.unpack_from('<4I', b, p); p += 16
        bones = [struct.unpack_from('<If', b, p + 8 * j) for j in range(n)]; p += 8 * n
        e['anchors'].append({'start': start, 'flags': flags, 'k': k, 'bones': bones})
    e['size'] = p - o
    return e


def parse_onun(d, m):
    c = m.chunks['ONUN']
    magic, ver, size, n = struct.unpack_from('<4s4s2I', d, c.offset)
    p, subs = c.offset + 16, []
    for _ in range(n):
        t, sz, cnt = struct.unpack_from('<3I', d, p)
        s = {'type': t, 'offset': p, 'size': sz, 'count': cnt, 'entries': []}
        if t == 0x30004:
            q = p + 12
            for _ in range(cnt):
                e = parse_entry(d, q); s['entries'].append(e); q += e['size']
            s['parsed_end'] = q
        subs.append(s); p += sz
    return {'version': ver, 'subs': subs, 'end': p, 'chunk_end': c.end}


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('files', nargs='+', metavar='file.g1m')
    ap.add_argument('--dump', action='store_true', help='also print every chain point')
    args = ap.parse_intermixed_args(argv)
    dump = args.dump
    for f in args.files:
        d = Path(f).read_bytes(); m = gt.embedded_models(d)[-1]
        if 'ONUN' not in m.chunks:
            print(Path(f).name, 'no ONUN'); continue
        joints, by_id = gt.skeleton(m); st2id = {s: b for b, s in by_id.items()}
        on = parse_onun(d, m)
        print(Path(f).name, 'ONUN', on['version'], 'subs', [(hex(s['type']), s['count']) for s in on['subs']],
              'end ok' if on['end'] == on['chunk_end'] else 'END MISMATCH')
        for s in on['subs']:
            if s['type'] != 0x30004:
                continue
            ok = s['parsed_end'] == s['offset'] + s['size']
            print(f"  type4 x{s['count']} parse {'exact' if ok else 'MISMATCH'} ({s['parsed_end'] - s['offset']} of {s['size']})")
            for e in s['entries']:
                sts = [j for _, j in e['joints']]
                print(f"   id {e['id']} A={e['A']} {e['a_list']} chains {e['n_chains']} points {e['n_points']} starts {e['chain_starts']}"
                      f" joints {sts[0]}..{sts[-1]} (ids {st2id.get(sts[0])}..{st2id.get(sts[-1])})"
                      f" anchors {[(hex(a['flags']), a['k'], [(b, round(w, 3)) for b, w in a['bones']]) for a in e['anchors']][:2]}")
                if dump:
                    for i, pt in enumerate(e['points']):
                        j = joints[e['joints'][i][1]]
                        print(f"     p{i} chain {pt['chain']}{'*' if pt['root'] else ' '} t {pt['t']:.3f} len {pt['len']:.3f}"
                              f" pos {[round(v, 2) for v in pt['pos']]} joint {e['joints'][i]} jw {[round(v, 2) for v in j['world_p']]}"
                              f" parent id {st2id.get(j['parent'])}")


if __name__ == '__main__':
    main(sys.argv[1:])
