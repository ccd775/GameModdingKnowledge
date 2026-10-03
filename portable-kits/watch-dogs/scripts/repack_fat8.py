"""Rebuild an uncompressed FAT v8 / DAT pair, optionally replacing entries.

Usage:
  repack_fat8.py SRC.fat OUT.fat [HASH=file | game/path=file ...] [--force]

Entries keep the source order (ascending name hash); each file starts on a
16-byte boundary with zero padding and no padding after the last file, which
reproduces Gibbed Pack output for this project's packages byte for byte.
A replacement key is either the 8-digit hex name hash or the game path; the hash of a path is the
low 32 bits of FNV-1 64 over the lower-case backslash path (char01.xbg -> E886A8DB).
An existing OUT.fat / OUT.dat is refused unless --force is given.
"""

import argparse
import string
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from extract_fat8 import read_entries  # noqa: E402


def path_hash(path: str) -> int:
    value = 0xCBF29CE484222325
    for ch in path.replace("/", "\\").lower():
        value = (value * 0x100000001B3) & 0xFFFFFFFFFFFFFFFF
        value ^= ord(ch)
    return value & 0xFFFFFFFF


def entry_hash(key: str) -> int:
    if len(key) == 8 and all(c in string.hexdigits for c in key):
        return int(key, 16)
    return path_hash(key)


def main() -> None:
    ap = argparse.ArgumentParser(description="Rebuild an uncompressed Watch Dogs FAT v8 / DAT pair, replacing entries.")
    ap.add_argument("src_fat", type=Path, help="source FAT; the DAT next to it is read")
    ap.add_argument("out_fat", type=Path, help="output FAT; the DAT is written next to it")
    ap.add_argument("replacements", nargs="*", metavar="KEY=file",
                    help="8-digit hex name hash or game path (graphics/.../char01.xbg), and the replacement file")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output pair")
    args = ap.parse_args()
    src_fat, out_fat = args.src_fat, args.out_fat
    if out_fat.resolve() == src_fat.resolve():
        raise SystemExit("refusing to overwrite the source pack")
    for target in (out_fat, out_fat.with_suffix(".dat")):
        if target.exists() and not args.force:
            raise SystemExit(f"refusing to overwrite existing {target} (use --force)")
    replacements = {}
    for arg in args.replacements:
        key, path = arg.split("=", 1)
        replacements[entry_hash(key)] = Path(path).read_bytes()
    fat = src_fat.read_bytes()
    dat = src_fat.with_suffix(".dat").read_bytes()
    entries = read_entries(fat)
    if sorted(e[0] for e in entries) != [e[0] for e in entries]:
        raise SystemExit("source FAT is not hash-ordered")
    unknown = set(replacements) - {e[0] for e in entries}
    if unknown:
        raise SystemExit(f"replacement hashes not in source: {[hex(h) for h in unknown]}")
    out_dat = bytearray()
    out_entries = bytearray()
    for name_hash, offset, size in entries:
        blob = replacements.get(name_hash, dat[offset : offset + size])
        out_dat += b"\0" * ((-len(out_dat)) % 16)
        new_offset = len(out_dat)
        if new_offset % 8 or len(blob) >= 1 << 29 or new_offset >= 1 << 35:
            raise SystemExit("entry does not fit FAT v8 packing")
        out_dat += blob
        packed_size = len(blob) | ((new_offset & 7) << 29)
        out_entries += struct.pack("<4I", name_hash, 0, packed_size, new_offset >> 3)
    out_fat.parent.mkdir(parents=True, exist_ok=True)
    out_fat.write_bytes(fat[:16] + bytes(out_entries) + fat[16 + len(entries) * 16 :])
    out_fat.with_suffix(".dat").write_bytes(bytes(out_dat))
    print(f"wrote {out_fat} ({len(entries)} entries, dat {len(out_dat)} bytes)")


if __name__ == "__main__":
    main()
