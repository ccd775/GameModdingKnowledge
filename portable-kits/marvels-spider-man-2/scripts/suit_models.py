"""Enumerate every suit: reward loadout config -> item loadout -> vanity item configs -> .model paths.
Writes Work/reports/suit_models.json  {reward config: {character, models[], mask}}."""
import argparse, json, os, re
from sm2_common import load_index, load_toc, extract, REPORTS

argparse.ArgumentParser(description=__doc__).parse_args()
idx = load_index()
toc = load_toc()


def read(path):
    v = idx.get(path.replace('/', chr(92)).lower())
    if not v:
        return None
    return extract(toc, int(v['id'], 16), 0)[0]


def strings(data):
    return [s.decode() for s in re.findall(rb'[\x20-\x7e]{6,}', data)]


out = {}
for name in sorted(idx):
    p = name.replace(chr(92), '/')
    if not re.match(r'^configs/inventory/inv_reward_loadout_.*\.config$', p):
        continue
    data = read(p)
    s = strings(data)
    loadout = next((x for x in s if 'masteritemloadoutlist' in x.lower()), None)
    mask = next((x for x in s if x.lower().endswith('.model')), None)
    models, vanities = [], []
    if loadout:
        ld = read(loadout)
        if ld:
            for x in strings(ld):
                xl = x.lower().replace(chr(92), '/')
                if xl.endswith('.config') and xl not in vanities:
                    vanities.append(xl)
    for vpath in vanities:
        vd = read(vpath)
        if not vd:
            continue
        for x in strings(vd):
            xl = x.lower().replace(chr(92), '/')
            if xl.endswith('.model') and xl not in models:
                models.append(xl)
    char = 'miles' if 'miles' in p else 'peter'
    out[p] = dict(character=char, loadout=loadout, vanities=vanities, models=models, mask=mask)
json.dump(out, open(os.path.join(REPORTS, 'suit_models.json'), 'w'), indent=1)
allm = {}
for k, v in out.items():
    for m in v['models']:
        allm.setdefault(m, set()).add(v['character'])
print(len(out), 'reward loadouts;', len(allm), 'distinct models')
for m in sorted(allm):
    print(sorted(allm[m]), m)
