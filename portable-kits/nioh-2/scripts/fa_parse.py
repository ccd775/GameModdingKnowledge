"""Parse a 3DMigoto frame analysis folder: per draw call -> shaders, vb/ib hashes, layouts, counts, bound ps textures.
usage: fa_parse.py <FrameAnalysis dir> [--json out.json]"""
import json
import os
import re
import sys
from collections import defaultdict

FN = re.compile(r'^(\d{6})-(vb\d|ib|vs-cb\d+|ps-cb\d+|cs-cb\d+|ps-t\d+|vs-t\d+)=([0-9a-f]+)(?:\(([0-9a-f]+)\))?-?(?:vs=([0-9a-f]+))?-?(?:ps=([0-9a-f]+))?.*\.(txt|buf|dds|jpg)$')


def read_header(path):
    hdr = {}
    elems = []
    cur = None
    with open(path, 'r', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n')
            if line.startswith('vertex-data') or (line and line[0].isdigit() and ' ' in line and ':' not in line):
                break
            if line.startswith('element['):
                cur = {}
                elems.append(cur)
                continue
            if line.startswith('  ') and cur is not None:
                k, _, v = line.strip().partition(': ')
                cur[k] = v
                continue
            if ': ' in line:
                k, _, v = line.partition(': ')
                hdr[k.strip()] = v.strip()
            if line.startswith('vb0[') or line.startswith('vb1['):
                break
    hdr['elements'] = elems
    return hdr


def parse(d):
    draws = defaultdict(lambda: {'files': {}})
    for fn in os.listdir(d):
        m = FN.match(fn)
        if not m:
            continue
        idx, slot, h, h2, vs, ps, ext = m.groups()
        dr = draws[int(idx)]
        dr['vs'] = vs or dr.get('vs')
        dr['ps'] = ps or dr.get('ps')
        dr['files'].setdefault(slot, {})['hash'] = h
        dr['files'][slot][ext] = fn
    # log: draw calls and texture binds
    log = os.path.join(d, 'log.txt')
    calls = defaultdict(list)
    if os.path.exists(log):
        with open(log, 'r', errors='replace') as f:
            for line in f:
                m = re.match(r'^(\d{6}) (Draw\w*)\((.*?)\)', line)
                if m:
                    calls[int(m.group(1))].append(m.group(2) + '(' + m.group(3) + ')')
    out = []
    for idx in sorted(draws):
        dr = draws[idx]
        rec = {'draw': idx, 'vs': dr.get('vs'), 'ps': dr.get('ps'), 'calls': calls.get(idx, [])}
        for slot, info in dr['files'].items():
            if slot.startswith('vb') or slot == 'ib':
                if 'txt' in info:
                    h = read_header(os.path.join(d, info['txt']))
                    info['hdr'] = {k: v for k, v in h.items() if k != 'elements'}
                    info['layout'] = [f"{e.get('SemanticName')}{e.get('SemanticIndex')}:{e.get('Format')}@{e.get('InputSlot')}+{e.get('AlignedByteOffset')}" for e in h['elements']]
            rec[slot] = info
        out.append(rec)
    return out


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('d', metavar='FrameAnalysis_dir'); ap.add_argument('--json', metavar='out.json')
    a = ap.parse_args()
    d = a.d
    res = parse(d)
    if a.json:
        json.dump(res, open(a.json, 'w'), indent=1)
    for r in res:
        if 'ib' not in r:
            continue
        ib = r['ib'].get('hdr', {})
        vbs = [k for k in r if k.startswith('vb')]
        desc = []
        for k in sorted(vbs):
            h = r[k].get('hdr', {})
            desc.append(f"{k}={r[k]['hash']} s{h.get('stride')} n{h.get('vertex count')}")
        lay = r.get('vb1', r.get('vb0', {})).get('layout', [])
        skinned = any('BLENDINDICES' in x for x in r.get('vb0', {}).get('layout', []))
        print(f"{r['draw']:4d} vs={r['vs']} ps={r['ps']} ib={r['ib']['hash']} first={ib.get('first index')} cnt={ib.get('index count')} {' '.join(desc)} {'SKIN' if skinned else ''} {r['calls'][:1]}")
