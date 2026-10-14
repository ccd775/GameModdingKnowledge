"""Decode + re-encode shipped .actor assets with i30_actor and require byte equality.

  python -B test_actor_roundtrip.py            # the hero / suit-addition actors (fast)
  python -B test_actor_roundtrip.py --all      # every .actor in the index (11,477; several minutes)
"""
import argparse, sys
import i30_actor as A
from sm2_common import load_index, load_toc, extract

HERO = [p.replace('/', chr(92)) for p in (
    'actors/hrm_bdy_firsthero/hero_spiderman.actor', 'actors/hrm_bdy_firsthero/hero_milesmorales.actor',
    'characters/prop/prop_backpack_cat/prop_backpack_spidercat.actor',
    'characters/hero/hero_milesmorales/head/hero_milesmorales_head.actor',
    'characters/hero/hero_peterparker/head/hero_peterparker_head.actor')]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--all', action='store_true', help='every .actor in the index')
    a = ap.parse_args()
    idx = load_index()
    toc = load_toc()
    names = sorted(k for k in idx if k.endswith('.actor')) if a.all else HERO
    bad = 0
    for n in names:
        b = extract(toc, n, 0)[0]
        try:
            ok = A.Actor(b).save(reencode=True) == b
        except Exception as e:          # noqa: BLE001
            ok = False
            print('ERR ', n, e)
        bad += not ok
        if not ok or len(names) <= 20:
            print('ok  ' if ok else 'DIFF', n)
    print('actors', len(names), 'bad', bad)
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
