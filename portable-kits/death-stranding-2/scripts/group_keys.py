"""Tool keys (group index, hex) of streaming groups: python group_keys.py <gid> [...] -> lines "gid KEY"."""
import argparse
import sys

from graph import Graph, game_root


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gids', nargs='+', type=int)
    gids = ap.parse_args().gids
    g = Graph(game_root())
    for gid in gids:
        print(gid, '%X' % g.group_by_id[gid])


if __name__ == '__main__':
    main()
