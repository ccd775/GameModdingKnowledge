"""Collapse every mesh of whole groups (all exported LODs) and write import jobs in build_ds2.py's format.

python gen_collapse.py <out dir> <skeletons dir> <export dir>:<group hex>:<gid> [...] [--skel=<KEY>:<skeleton ascii>]
    [--only=<gid>:<mesh>,<mesh>,...]   (collapse only these meshes of that group; repeatable)
    [--stream-only]   (mark the jobs stream-only: collapse keeps the counts, so make_mod_ds2 packs only the streams)
"""
import argparse
import json
import os
import re
import sys

from collapse_mesh import collapse
from ds2ascii import read_meshes, read_skeleton, write

SKEL_FILES = {'47CC': '47CC_skel_0.ascii', '47CD': '47CD_skel_26.ascii', '19FF': '19FF_skel_0.ascii'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('out'); ap.add_argument('skeletons')
    ap.add_argument('specs', nargs='+', metavar='<export dir>:<group hex>:<gid>')
    ap.add_argument('--skel', action='append', default=[], metavar='<KEY>:<skeleton ascii>')
    ap.add_argument('--only', action='append', default=[], metavar='<gid>:<mesh>,<mesh>,...')
    ap.add_argument('--stream-only', action='store_true')
    a = ap.parse_intermixed_args()
    out, skdir = a.out, a.skeletons
    os.makedirs(out, exist_ok=True)
    specs = a.specs
    only = {}
    stream_only = a.stream_only
    for x in a.only:
        k, v = x.split(':', 1)
        only[int(k)] = {int(y) for y in v.split(',') if y}
    for x in a.skel:
        k, v = x.split(':', 1)
        SKEL_FILES[k] = v
    def skel_key(k, i):
        # groups holding several skeletons (cutscene bundles) need KEY_IDX; older single-skeleton keys stay KEY
        if f'{k}_{i}' in SKEL_FILES or k not in SKEL_FILES:
            SKEL_FILES.setdefault(f'{k}_{i}', f'{k}_skel_{i}.ascii')
            return f'{k}_{i}'
        return k

    skels = {}

    def skel(k):
        if k not in skels:
            skels[k] = read_skeleton(os.path.join(skdir, SKEL_FILES[k]))
        return skels[k]
    jobs = []
    for spec in specs:
        exp, group, gid = spec.split(':') if spec.count(':') == 2 else spec.rsplit(':', 2)
        done = set()
        for lod in sorted(d for d in os.listdir(exp) if d.startswith('lod')):
            d = os.path.join(exp, lod)
            log = open(os.path.join(d, 'export.log'), encoding='utf-8-sig', errors='replace').read()
            mesh_skel = {int(m): skel_key(k, i) for m, k, i in re.findall(r'Mesh (\d+) with skeleton (\w+) (\w+)', log)}
            for f in sorted(os.listdir(d)):
                if not f.endswith('.ascii') or '_skel_' in f:
                    continue
                by_mesh = {}   # one export file can hold several meshes (MultiMeshResource members)
                for s in read_meshes(os.path.join(d, f))[1]:
                    mm = re.match(r'mesh_(\d+)_sm_(\d+)_', s['name'])
                    by_mesh.setdefault(int(mm.group(1)), []).append((int(mm.group(2)), s))
                for mid, items in by_mesh.items():
                    if mid in done or (int(gid) in only and mid not in only[int(gid)]):
                        continue
                    done.add(mid)
                    items.sort(key=lambda t: t[0])
                    path = os.path.join(out, f'{group}_{lod}_{mid}.ascii')
                    write(path, [collapse(s)[0] for _, s in items], skel(mesh_skel[mid]))
                    jobs.append(dict(group=group, gid=int(gid), lod=int(lod[3:]), mesh=mid, skel=SKEL_FILES[mesh_skel[mid]],
                                     ascii=path, prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                                     verts=[len(s['pos']) for _, s in items], **({'stream_only': True} if stream_only else {})))
    json.dump(jobs, open(os.path.join(out, 'jobs.json'), 'w'), indent=1)
    print(len(jobs), 'collapse jobs:', ' '.join(f"{j['group']}/{j['lod']}/{j['mesh']}" for j in jobs))


if __name__ == '__main__':
    main()
