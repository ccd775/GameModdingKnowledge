"""Which DSPlayerBodyVariant root groups reach a group through subgroup links: python sharing.py <gid> [...]"""
import argparse
import sys

from graph import Graph, game_root

VARIANTS = {5494: 'DeadbodyBag', 34852: 'Naked', 43771: 'Naked2', 39983: 'Suit', 58940: 'Suit2', 40436: 'PrivateRoom',
            50107: 'Porter', 65631: 'SkeletonOnly', 67631: 'Jacket'}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gids', nargs='+')
    gids = ap.parse_args().gids
    g = Graph(game_root())
    parents = {}
    for gi in range(len(g.groups)):
        for s in g.subgroups(gi):
            parents.setdefault(s, set()).add(gi)
    for a in gids:
        start = g.group_by_id[int(a)]
        seen, stack = {start}, [start]
        while stack:
            for p in parents.get(stack.pop(), ()):
                if p not in seen:
                    seen.add(p)
                    stack.append(p)
        roots = sorted(VARIANTS[g.groups[x]['GroupID']] for x in seen if g.groups[x]['GroupID'] in VARIANTS)
        print('%s: %d ancestor groups, variants %s' % (a, len(seen) - 1, roots))


if __name__ == '__main__':
    main()
