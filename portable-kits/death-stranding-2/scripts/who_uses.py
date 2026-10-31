"""Find ModelPartResources (in the given groups) whose mesh chain reaches meshes of a target group.

python who_uses.py <target gid> <gid> [<gid> ...]
"""
import argparse
import sys

from graph import Graph, game_root
from group import read_group

CACHE = {}


def obj(g, ref):
    if ref[1] not in CACHE:
        CACHE[ref[1]] = read_group(g, ref[1])
    return CACHE[ref[1]][ref[2]]


def leaves(g, ref):
    m = obj(g, ref)
    t = m['__type__']
    if t == 'RegularSkinnedMeshResource':
        yield tuple(ref[1:])
    elif t == 'LodMeshResource':
        for part in m['RuntimeMeshes']:
            yield from leaves(g, part['Mesh'])
    elif t == 'MultiMeshResource':
        for r in m['Meshes']:
            yield from leaves(g, r)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('target', type=int); ap.add_argument('gids', nargs='+', type=int)
    a = ap.parse_args()
    target = a.target
    g = Graph(game_root())
    for gid in a.gids:
        for i, o in enumerate(read_group(g, gid)):
            if o['__type__'] != 'ModelPartResource' or not o['MeshResource']:
                continue
            ls = [l for l in leaves(g, o['MeshResource']) if l[0] == target]
            if ls:
                print('%d:%d hidden=%d -> %s' % (gid, i, o['IsHideAndDisableDefault'], ls))


if __name__ == '__main__':
    main()
