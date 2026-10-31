"""Resources of a type read in phase A but not in phase B, by size (min bytes). usage: phase_only.py <json> <type> <A> <B> [min]"""
import argparse, json
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('reads', help='etw_reads.py JSON'); ap.add_argument('type', help='type name, e.g. g1t')
ap.add_argument('a', metavar='A'); ap.add_argument('b', metavar='B')
ap.add_argument('min', nargs='?', type=int, default=0, help='minimum size in bytes')
args = ap.parse_args()
d = json.load(open(args.reads)); t, a, b = args.type, args.a, args.b; mn = args.min
ph = {p['name']: p['resources'] for p in d['phases']}
only = [(h, v) for h, v in ph[a].items() if v['type'] == t and h not in ph[b] and v['size'] >= mn]
for h, v in sorted(only, key=lambda x: -x[1]['size']):
    print(h, v['size'], v['container'])
print(len(only), 'only in', a)
