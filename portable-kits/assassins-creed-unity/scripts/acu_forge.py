"""AC Unity (AnvilNext 2.0, forge v27) helpers, forked from ACOd/scripts/aco_forge.py. Pure Python.

  python acu_forge.py index <forge> [<forge> ...] > out.tsv     forge, index, id, offset, size, name
  python acu_forge.py extract <forge> <out_dir> <id_hex> [...]    raw .data containers (<index>_-_<name>.data)

Forge v27 layout (measured 2026-10-24 on DataPC / DataPC_patch_01, Steam build 21970519) = Odyssey's v28 layout:
  header: "scimitar\\0", u32 version (27), u64 offset of the forge header (1050)
  forge header: u32 count, u32, i64, i64, i32, u32 max, u32 table count, i64 first table
  table: u32 count, u32, i64 index offset, i64 next table (-1), u32 first, u32 last, i64 name table, i64
  index entry (20 B): i64 offset, u64 id, i32 size
  name entry (0xC0 B): u32 size, ..., u32 timestamp at +40, name (char[128]) at +44
"""
import os
import struct
import sys

VERSIONS = (27, 28)


def read_index(path):
    out = []
    with open(path, "rb") as f:
        if f.read(9) != b"scimitar\0":
            raise ValueError(f"{path}: not a forge")
        version, hdr = struct.unpack("<IQ", f.read(12))
        if version not in VERSIONS:
            raise ValueError(f"{path}: forge version {version} not in {VERSIONS}")
        f.seek(hdr)
        count, _, _, _, _, _, ntables, pos = struct.unpack("<IIqqiIIq", f.read(44))
        while pos != -1 and len(out) < count:
            f.seek(pos)
            n, _, idx_off, nxt, first, last, name_off, _ = struct.unpack("<IIqqIIqq", f.read(48))
            f.seek(idx_off)
            raw = f.read(20 * n)
            f.seek(name_off)
            names = f.read(0xC0 * n)
            for i in range(n):
                off, oid, size = struct.unpack_from("<qQi", raw, 20 * i)
                nm = names[0xC0 * i + 44:0xC0 * i + 172].split(b"\0", 1)[0].decode("utf-8", "replace")
                out.append((len(out), oid, off, size, nm))
            pos = nxt
    return out


def extract(forge, out_dir, ids):
    os.makedirs(out_dir, exist_ok=True)
    want = set(ids)
    written = []
    with open(forge, "rb") as f:
        for i, oid, off, size, nm in read_index(forge):
            if oid not in want:
                continue
            f.seek(off)
            safe = "".join(c if c not in '<>:"/\\|?*' else "_" for c in nm) or f"{oid:016X}"
            p = os.path.join(out_dir, f"{i}_-_{safe}.data")
            with open(p, "wb") as o:
                o.write(f.read(size))
            written.append(p)
    return written


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("index", help="TSV of every index row on stdout: forge, index, id, offset, size, name")
    p.add_argument("forges", nargs="*")
    p = sub.add_parser("extract", help="write the raw .data containers of the given IDs")
    p.add_argument("forge")
    p.add_argument("out_dir")
    p.add_argument("ids", nargs="*", help="data file IDs (hex)")
    a = ap.parse_args()
    if a.cmd == "index":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        w = sys.stdout
        for fg in a.forges:
            name = os.path.relpath(fg, os.path.dirname(os.path.dirname(os.path.abspath(fg)))) if os.sep + "dlc_" in os.path.abspath(fg) else os.path.basename(fg)
            for i, oid, off, size, nm in read_index(fg):
                w.write(f"{name}\t{i}\t{oid:016X}\t{off}\t{size}\t{nm}\n")
    else:
        for p in extract(a.forge, a.out_dir, [int(x, 16) for x in a.ids]):
            print(p)
