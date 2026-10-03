"""Extract entries from an uncompressed Watch Dogs FAT v8 / DAT pair.

Only handles the uncompressed packs produced by Gibbed Pack for this project.
Files are written as <hash>.<ext>, where ext is guessed from the magic.
Existing files in the output directory are refused unless --force is given.
"""

import argparse
import struct
from pathlib import Path

MAGICS = {b"MOEG": "xbg", b"TBX\x00": "xbt", b"TXB\x00": "xbt"}


def read_entries(fat: bytes) -> list[tuple[int, int, int]]:
    magic, version = struct.unpack_from("<4sI", fat, 0)
    if magic != b"3TAF" or version != 8:
        raise SystemExit(f"unsupported FAT header {magic!r} v{version}")
    count = struct.unpack_from("<I", fat, 12)[0]
    entries = []
    for index in range(count):
        name_hash, flags, packed_size, packed_offset = struct.unpack_from(
            "<4I", fat, 16 + index * 16
        )
        if flags:
            raise SystemExit(f"entry {index} has unexpected flags {flags:#x}")
        size = packed_size & 0x1FFFFFFF
        offset = (packed_offset << 3) | (packed_size >> 29)
        entries.append((name_hash, offset, size))
    return entries


def main() -> None:
    ap = argparse.ArgumentParser(description="Extract entries from an uncompressed Watch Dogs FAT v8 / DAT pair.")
    ap.add_argument("fat", type=Path, help="FAT file; the DAT next to it is read")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite existing extracted files")
    args = ap.parse_args()
    fat = args.fat.read_bytes()
    dat = args.fat.with_suffix(".dat").read_bytes()
    jobs = []
    for name_hash, offset, size in read_entries(fat):
        blob = dat[offset : offset + size]
        if len(blob) != size:
            raise SystemExit(f"{name_hash:08X} runs past the DAT")
        ext = MAGICS.get(blob[:4], "bin")
        jobs.append((name_hash, offset, size, ext, blob, args.out_dir / f"{name_hash:08X}.{ext}"))
    existing = [str(j[5]) for j in jobs if j[5].exists()]
    if existing and not args.force:
        raise SystemExit(f"refusing to overwrite {len(existing)} existing file(s), e.g. {existing[0]} (use --force)")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name_hash, offset, size, ext, blob, target in jobs:
        target.write_bytes(blob)
        print(f"{name_hash:08X} off={offset:#010x} size={size:>9} {ext} {blob[:8].hex(' ')}")


if __name__ == "__main__":
    main()
