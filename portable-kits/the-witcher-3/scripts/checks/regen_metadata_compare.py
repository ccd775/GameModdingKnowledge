"""Regenerate the vanilla content/metadata.store from the vanilla bundles with w3metadata_write.build_store and
compare it table by table with the game's own file (the check that validated the v7 writer).

Usage: python regen_metadata_compare.py [<game dir>] [--out <regenerated.store>]
Default game dir: W3_GAME_DIR. The vanilla store leaves out the '_censored' files, so they are excluded here too.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # kit scripts/
from w3metadata import R  # noqa: E402
import w3metadata_write as W  # noqa: E402
import w3paths  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('game', nargs='?')
ap.add_argument('--out')
args = ap.parse_args()
root = os.path.join(args.game or w3paths.game(), 'content')
bdir = os.path.join(root, 'content0', 'bundles')
bundles = [('content0\\bundles\\' + fn, os.path.join(bdir, fn)) for fn in sorted(os.listdir(bdir)) if fn.endswith('.bundle')]
gen = W.build_store(bundles, exclude=lambda n: '_censored' in n)
if args.out:
    open(args.out, 'wb').write(gen)
van = open(os.path.join(root, 'metadata.store'), 'rb').read()
print('sizes gen', len(gen), 'van', len(van), 'identical', gen == van)


def parse(d):
    r = R(d)
    r.raw(4)
    hdr = (r.i32(), r.i32(), r.i32())
    sts = r.vlq(); st = r.raw(sts)
    out = {'hdr': hdr, 'strtab': st}
    for name, size in (('fi', 32), ('fe', 24), ('bi', 24)):
        n = r.vlq(); out[name] = [d[r.p + i * size:r.p + (i + 1) * size] for i in range(n)]; r.p += n * size
    n = r.vlq(); out['buf'] = list(struct.unpack_from('<%dI' % n, d, r.p)); r.p += 4 * n
    for name, size in (('dir', 8), ('finit', 12), ('hash', 16)):
        n = r.vlq(); out[name] = [d[r.p + i * size:r.p + (i + 1) * size] for i in range(n)]; r.p += n * size
    out['end'] = (r.p, len(d))
    return out


G, V = parse(gen), parse(van)
print('hdr', G['hdr'], V['hdr'])
print('strtab', len(G['strtab']), len(V['strtab']), G['strtab'] == V['strtab'])
for k in ('fi', 'fe', 'bi', 'buf', 'dir', 'finit', 'hash'):
    g, v = G[k], V[k]
    same = sum(1 for a, b in zip(g, v) if a == b)
    print(k, len(g), len(v), 'equal prefix count', same)
    for i, (a, b) in enumerate(zip(g, v)):
        if a != b:
            fmt = {'fi': '<8I', 'fe': '<QIIII', 'bi': '<QIIII', 'dir': '<iI', 'finit': '<iii', 'hash': '<QQ'}.get(k)
            if fmt:
                print('  first diff at', i, struct.unpack(fmt, a), struct.unpack(fmt, b))
            else:
                print('  first diff at', i, a, b)
            break
print('end', G['end'], V['end'])
