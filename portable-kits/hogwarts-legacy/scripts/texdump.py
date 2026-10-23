# texdump.py <uasset> : names + hex dump of the uexp after the tagged properties (UE4.27 legacy cooked package)
import argparse, struct, sys
ap = argparse.ArgumentParser(description='names, PF_ name refs and a hex dump of the .uexp of a legacy cooked package')
ap.add_argument('uasset'); ap.add_argument('start', type=int, nargs='?', default=0); ap.add_argument('end', type=int, nargs='?')
args = ap.parse_args()
ua = open(args.uasset, 'rb').read()
ue = open(args.uasset[:-7] + '.uexp', 'rb').read()
p = 0
def i32():
    global p; v = struct.unpack_from('<i', ua, p)[0]; p += 4; return v
def fstr():
    global p; n = i32()
    if n == 0: return ''
    if n < 0: s = ua[p:p - n * 2].decode('utf-16le'); p += -n * 2; return s[:-1]
    s = ua[p:p + n].decode('latin1'); p += n; return s[:-1]
tag = i32(); lfv = i32(); lue3 = i32(); fue4 = i32(); fue4l = i32()
ncv = i32(); p += 20 * ncv  # custom versions
total = i32(); folder = fstr(); flags = i32()
ncount = i32(); noff = i32()
p = noff
names = []
for _ in range(ncount):
    names.append(fstr()); p += 4
print('names:', names)
hdr = total
print('uexp len', len(ue), 'header', hdr)
def nm(off):
    i, n = struct.unpack_from('<ii', ue, off); return (names[i] if 0 <= i < len(names) else '?%d' % i) + ('_%d' % (n - 1) if n else '')
# find PF_ name refs
for i in range(0, len(ue) - 8, 1):
    a, b = struct.unpack_from('<ii', ue, i)
    if 0 <= a < len(names) and b == 0 and names[a].startswith('PF_'):
        print('PF name at uexp+%d (%s)' % (i, names[a]))
start = args.start
end = args.end if args.end is not None else min(len(ue), start + 256)
for o in range(start, end, 16):
    chunk = ue[o:o + 16]
    print('%5d  %s' % (o, ' '.join('%02x' % c for c in chunk)))
