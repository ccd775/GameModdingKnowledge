"""Scan a PE file's raw bytes for IDA-style patterns ('E8 ? ? ? ? 85 C0'); print match file offsets + byte entropy of .text."""
import argparse, re, math, collections
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('file', help='PE file'); ap.add_argument('patterns', nargs='*', metavar='pattern', help="e.g. 'E8 ? ? ? ? 85 C0'")
args = ap.parse_args()
d = open(args.file, 'rb').read()
for pat in args.patterns:
    rx = b''.join(b'.' if t == '?' else re.escape(bytes([int(t, 16)])) for t in pat.split())
    m = [x.start() for x in re.finditer(rx, d, re.S)]
    print(len(m), [hex(x) for x in m[:5]], pat)
chunk = d[0x400:0x400 + 4_000_000]
c = collections.Counter(chunk)
H = -sum(v / len(chunk) * math.log2(v / len(chunk)) for v in c.values())
print('text entropy', round(H, 3), 'top', [(hex(k), v) for k, v in c.most_common(5)])
