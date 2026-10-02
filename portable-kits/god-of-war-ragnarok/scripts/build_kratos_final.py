"""Kratos (r_heroa00) build: Karin_Original in group 230 (head/torso/arms, all LODs); everything else hidden.

Base WAD: the user's reference Karin mod's r_heroa00.wad (shipped data + bumped LOD0/trouser hashes); all its
replaced stream data is rebuilt here from root.lodpack, so the reference mod's own geometry is not reused.
usage: build_kratos_final.py --game G --base-wad W --fit DIR --fit-lods DIR --karin-bones J --rigspec J --out DIR
"""
import json, os, sys, glob
from wad import Wad
from mesh import parse_mesh
from mg import parse_mg_groups
from geometry import build as build_geo
from charbuild import room_finder, plan_groups
from build_inplace import build
from gamedir import set_game

GROUP_PARTS = {230: [['Body', 'body_2', 'pullover', 'shoes', 'underwear'],     # head mesh (skin material)
                     ['hair', 'kemomimi', 'tail', 'skirt', 'knee_socks']]}     # arms mesh (same material)
LOD0_HASH = 0x167745b9b547165b                                   # root ...5a bumped by one
PASSTHROUGH = {0x2a5ef0f242a705b6: 0x2a5ef0f242a705b5}           # trouser buffer, listed bumped in the base WAD


def main(out_dir, base_wad, fit, fit_lods, kb, spec):
    w = Wad(open(base_wad, 'rb').read())
    ms = parse_mesh(w.get([e for e in w.entries if e.name == 'MESH_heroa00_0' and e.type == 1][0]))
    gs = parse_mg_groups(w.get([e for e in w.entries if e.name == 'MG_heroa00_0' and e.type == 153][0]))
    caps = room_finder(ms, len(w.get([e for e in w.entries if e.name == 'MG_heroa00_0_gpu'][0])))
    geos = {'full': build_geo(fit, kb, spec)}
    for d in glob.glob(os.path.join(fit_lods, 'r*')):
        geos[os.path.basename(d)[1:]] = build_geo(d, kb, spec)
    plan, chosen = plan_groups(gs, GROUP_PARTS, caps, geos)
    os.makedirs(out_dir, exist_ok=True)
    report = build(base_wad, geos, plan, set(), f'{out_dir}/r_heroa00.wad', f'{out_dir}/KarinOriginal.lodpack',
                   passthrough=PASSTHROUGH, dummy=(LOD0_HASH, 0x0))
    json.dump(dict(chosen={str(k): v for k, v in chosen.items()}, report={str(k): v for k, v in report.items()}),
              open(f'{out_dir}/mesh_report.json', 'w'), indent=1, default=str)
    return chosen


def parse_args(description, base_help):
    import argparse
    ap = argparse.ArgumentParser(description=description, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--game', help='game folder with exec/ (root.lodpack is read from it; default: GOWR_GAME)')
    ap.add_argument('--base-wad', required=True, help=base_help)
    ap.add_argument('--fit', required=True, help='fit_karin.py output (npz + summary.json)')
    ap.add_argument('--fit-lods', required=True, help='decimate_levels.py output (r<ratio> folders)')
    ap.add_argument('--karin-bones', required=True, help='dump_bones.py output for the source model')
    ap.add_argument('--rigspec', required=True, help='rigspec.py output for this character')
    ap.add_argument('--out', required=True, help='output folder (wad, lodpack, lodpack.toc, mesh_report.json)')
    args = ap.parse_args()
    set_game(args.game)
    return args


if __name__ == '__main__':
    a = parse_args(__doc__, "base r_heroa00.wad (this case: the reference mod's wad, see the docstring)")
    for k, v in main(a.out, a.base_wad, a.fit, a.fit_lods, a.karin_bones, a.rigspec).items():
        print(k, v)
