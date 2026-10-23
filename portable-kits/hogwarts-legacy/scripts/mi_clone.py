# mi_clone.py <in MI.uasset> <out MI.uasset> <old>=<new> ...
# Clones a cooked game material instance (legacy extract) to a new package path. HL material instances end with a
# game-specific 20-byte hash, so new MIs are cloned from the game's own instead of cooked in stock UE. Every <old>
# string in the package (name map, asset registry strings, shader map names) becomes <new>. Replacements must keep
# the length, so no offset changes. Used to give the female pieces their own copies of the male outfit MIs, whose
# texture paths are then pointed at the Karin textures.
import argparse, sys, struct
ap = argparse.ArgumentParser(description='clone a cooked material instance with same-length string replacements')
ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('pair', nargs='*', help='<old>=<new>, same length')
args = ap.parse_args()
src, dst = args.src, args.dst
pairs = [a.split('=', 1) for a in args.pair]
for old, new in pairs: assert len(old) == len(new) and old != new, (old, new)
for ext in ('.uasset', '.uexp'):
    b = open(src[:-7] + ext, 'rb').read()
    counts = []
    for old, new in pairs:
        counts.append(b.count(old.encode()))
        b = b.replace(old.encode(), new.encode())
    open(dst[:-7] + ext, 'wb').write(b)
    print(ext, ' '.join('%s x%d' % (old, n) for (old, _), n in zip(pairs, counts)))
assert struct.unpack_from('<I', open(dst, 'rb').read(), 0)[0] == 0x9E2A83C1
