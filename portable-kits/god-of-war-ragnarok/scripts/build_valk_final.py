"""Freya as companion (r_freyavalkyrie00 — the resource every Freya level/companion WAD depends on; r_freya00 is
referenced by nothing). Karin_Original goes into the always-visible skin groups plus the main hair group; every
other mesh (Freya's hair pieces, all outfit variants, wings, eyes) is hidden.

Groups (parent 0 = always shown, 12 = hair set, 11 = wings, 3-10 = outfit variants):
  36 head+neck skin (packed 11-bit joints, 7 weights)   14 arms skin (u16 joints, 4 weights)
  13 feet skin (u8 joints: bones < 256 only)              27 main hair cap (u8 joints)
usage: build_valk_final.py --game G --base-wad W --fit DIR --fit-lods DIR --karin-bones J --rigspec J --out DIR
"""
import json, os, sys, glob
from wad import Wad
from mesh import parse_mesh
from mg import parse_mg_groups
from geometry import build as build_geo
from charbuild import room_finder, plan_groups
from build_inplace import build
from gamedir import set_game

# Only the largest def of each LOD is used: the smaller ones cover the same volume with other materials
# (lashes, nails, overlays), so Karin stays on the skin/hair material. Part order = detail priority.
GROUP_PARTS = {
    36: [['Body', 'body_2', 'kemomimi']],
    14: [['pullover', 'underwear', 'skirt', 'tail']],
    13: [['shoes', 'knee_socks']],                        # u8 joints: legs/feet bones only
    27: [['hair']],                                       # u8 joints: rigid on the head bone (136)
}


HOST = 280      # head LOD0 def: its stream buffer is shipped (bumped hash) and has spare vertex room after Karin


def dummy_block(ms, chosen):
    """(bumped hash, offset) of a zeroed 0x100 block in the unused tail of the HOST def's vertex range.
    Pointing hidden defs into the in-WAD gpu entry instead (hash 0) drew stray triangles in game."""
    m = ms[HOST]
    off = (m.buf_offs[0] + chosen[HOST]['verts'] * m.strides[0] + 15) & ~15
    assert m.buf_count == 1 and off + 0x100 <= m.ind_off, 'no room for the hidden-mesh block'
    return m.hash + 1, off


def main(out_dir, base_wad, fit, fit_lods, kb, spec):
    w = Wad(open(base_wad, 'rb').read())
    ms = parse_mesh(w.get([e for e in w.entries if e.name == 'MESH_freyavalkyrie00_0' and e.type == 1][0]))
    gs = parse_mg_groups(w.get([e for e in w.entries if e.name == 'MG_freyavalkyrie00_0' and e.type == 153][0]))
    gpu_len = len(w.get([e for e in w.entries if e.name == 'MG_freyavalkyrie00_0_gpu'][0]))
    caps = room_finder(ms, gpu_len)
    geos = {'full': build_geo(fit, kb, spec)}
    for d in glob.glob(os.path.join(fit_lods, 'r*')):
        geos[os.path.basename(d)[1:]] = build_geo(d, kb, spec)
    plan, chosen = plan_groups(gs, GROUP_PARTS, caps, geos)
    dummy = dummy_block(ms, chosen)
    os.makedirs(out_dir, exist_ok=True)
    report = build(base_wad, geos, plan, set(), f'{out_dir}/r_freyavalkyrie00.wad', f'{out_dir}/KarinOriginalFreya.lodpack',
                   dummy=dummy, mesh_entry='MESH_freyavalkyrie00_0', gpu_entry='MG_freyavalkyrie00_0_gpu', pad_joint=None)
    json.dump(dict(dummy=dict(host_def=HOST, hash=hex(dummy[0]), offset=dummy[1]), chosen={str(k): v for k, v in chosen.items()},
                   report={str(k): v for k, v in report.items()}),
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
    a = parse_args(__doc__, 'original r_freyavalkyrie00.wad from the game (keep your own copy; LZ4 is fine)')
    for k, v in main(a.out, a.base_wad, a.fit, a.fit_lods, a.karin_bones, a.rigspec).items():
        print(k, v)
