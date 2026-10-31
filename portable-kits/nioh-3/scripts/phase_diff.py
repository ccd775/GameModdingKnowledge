"""Resources of a given type read in every listed phase of an etw_reads.py JSON (intersection), with sizes.
usage: phase_diff.py <reads.json> <type> <phase> [<phase> ...]"""
import argparse, json
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('reads', help='etw_reads.py JSON'); ap.add_argument('type', help='type name, e.g. g1m')
ap.add_argument('phases', nargs='+', metavar='phase')
args = ap.parse_args()
d = json.load(open(args.reads))
t, names = args.type, args.phases
ph = {p['name']: p['resources'] for p in d['phases']}
sets = [{h for h, v in ph[n].items() if v['type'] == t} for n in names]
common = set.intersection(*sets)
print(t, [len(s) for s in sets], 'common', len(common))
for h in sorted(common, key=lambda h: -ph[names[0]][h]['size']):
    v = ph[names[0]][h]
    print(h, v['size'], v['container'], v['first_t'])
