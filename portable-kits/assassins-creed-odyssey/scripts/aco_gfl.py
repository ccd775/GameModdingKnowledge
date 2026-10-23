"""Dump AnvilToolkit's Odyssey file list (Lists/Odyssey.gfl) to TSV: id, class hash, forge, data file, name.

  python aco_gfl.py <out.tsv> [--gfl <Odyssey.gfl>] [--acsh-scripts <folder with acsh_forge.py>]

Same GFL container as Shadows (ACShadow/scripts/acsh_forge.read_gfl, Oodle v7 from the AnvilToolkit Libs).
Class hash = CRC32 of the class name (MaterialTemplate 0xBCFB3C7A, Material 0x85C817C3, TextureMap 0xA2B7E917, ...).
Portable kit: the GFL comes from --gfl / ACO_GFL; acsh_forge.py (AC Shadows project, NOT part of this kit) is imported
from --acsh-scripts / ACO_ACSH_SCRIPTS.
"""
import argparse
import os
import sys

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_tsv")
    ap.add_argument("--gfl", default=os.environ.get("ACO_GFL"), help="Odyssey.gfl (default: ACO_GFL)")
    ap.add_argument("--acsh-scripts", default=os.environ.get("ACO_ACSH_SCRIPTS"),
                    help="folder holding acsh_forge.py (default: ACO_ACSH_SCRIPTS)")
    a = ap.parse_args()
    if not a.gfl:
        raise SystemExit("set ACO_GFL (AnvilToolkit Lists/Odyssey.gfl) or pass --gfl")
    if not a.acsh_scripts:
        raise SystemExit("set ACO_ACSH_SCRIPTS (folder with acsh_forge.py) or pass --acsh-scripts")
    sys.path.insert(0, a.acsh_scripts)
    import acsh_forge as af  # noqa: E402
    forges, datas, entries = af.read_gfl(a.gfl)
    with open(a.out_tsv, "w", encoding="utf-8") as o:
        for oid, (nm, t, fi, di) in entries.items():
            o.write(f"{oid:016X}\t{t:08X}\t{forges[fi] if fi >= 0 else ''}\t{datas[di] if di >= 0 else ''}\t{nm}\n")
    print(len(forges), "forges", len(datas), "datafiles", len(entries), "entries")
