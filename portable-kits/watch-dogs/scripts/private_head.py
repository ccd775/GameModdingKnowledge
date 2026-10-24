"""Give a char01 replacer pack its own head material and head textures.

The Fall of Windy City II (1.1.x) overrides Aiden's head material (mkamelaquino-m-20130115113413): it reads
char01_head_v2_d.xbt and char01_head_v2_s_lowend.xbt instead of the _d2/_s2 textures a replacer overrides, so the
replacer's face samples Aiden's own face texture and turns dark.  This rewrites a built pack so that

  - char01.xbg's head slot names a private copy of the vanilla head material (same path length, new FNV);
  - that material reads private copies of the head diffuse/normal/specular (same path lengths);
  - each private texture is one file holding the whole mip chain (the high stream's level 0 followed by the low
    stream's levels, lossless), with the high stream's XBT prefix and the mip count byte (0x19) set to the chain
    length.  Windy City II ships its own textures in this layout;
  - Aiden's char01_head_v2_d2/_n/_s2 entries (low and high) leave the pack, so other outfits that use Aiden's head
    show his own face again.

No other mod overrides the private paths, so the face no longer depends on the load order.

  python private_head.py SRC.fat OUT_DIR --vanilla-material mkamelaquino-m-20130115113413.material.bin
         [--filelists DIR] [--force]
writes OUT_DIR/<pack>.fat/.dat (+ private_head.json).  build scripts call privatize() on the entry dict instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xbt_tool  # noqa: E402
from extract_fat8 import read_entries  # noqa: E402
from repack_fat8 import path_hash, write  # noqa: E402

BS = "\\"
MATERIALS = BS.join(["graphics", "_materials", ""])
CHAR01 = BS.join(["graphics", "characters", "char", "char01", ""])
XBG = CHAR01 + "char01.xbg"
HEAD_MATERIAL = MATERIALS + "mkamelaquino-m-20130115113413.material.bin"
PRIVATE_MATERIAL = MATERIALS + "droylouo-m-20261010120000-h1a.material.bin"
VANILLA_MATERIAL_SHA256 = "6178B386C47D437383229C95442BE7F22BF0C10FFD8A36FDDF21BE11D7B18DD4"  # unmodified game file
# Aiden's head textures (as the material names them) -> private copies of the same length
TEXTURES = {
    CHAR01 + "char01_head_v2_d2.xbt": CHAR01 + "karin_face_drl_d2.xbt",
    CHAR01 + "char01_head_v2_n.xbt": CHAR01 + "karin_face_drl_n.xbt",
    CHAR01 + "char01_head_v2_s2.xbt": CHAR01 + "karin_face_drl_s2.xbt",
}
MIPS_BYTE = 0x19


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def high_path(path: str) -> str:
    return path[: -len(".xbt")] + "_high.xbt"


def replace_same_length(data: bytes, old: str, new: str, what: str) -> bytes:
    a, b = old.encode("ascii"), new.encode("ascii")
    if len(a) != len(b):
        raise ValueError(f"{what}: {new} is not the length of {old}")
    if data.count(a) != 1:
        raise ValueError(f"{what}: {old} occurs {data.count(a)} times")
    return data.replace(a, b)


def retarget_xbg(xbg: bytes) -> bytes:
    """Swap the head slot's material path (and its FNV) in the XBG material table at 0x8C."""
    d = bytearray(xbg)
    p = 0x8C
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    hits = 0
    for _ in range(n):
        fnv, ln = struct.unpack_from("<II", d, p)
        path = bytes(d[p + 8 : p + 8 + ln]).rstrip(b"\0").decode("ascii")
        if path.lower() == HEAD_MATERIAL.lower():
            if fnv != path_hash(path) or len(PRIVATE_MATERIAL) != len(path):
                raise ValueError("unexpected head material record")
            struct.pack_into("<I", d, p, path_hash(PRIVATE_MATERIAL))
            d[p + 8 : p + 8 + len(path)] = PRIVATE_MATERIAL.encode("ascii")
            hits += 1
        p += 8 + ((ln + 3) & ~3)
    if hits != 1:
        raise ValueError(f"head material found {hits} times in the XBG material table")
    return bytes(d)


def private_material(vanilla: bytes) -> bytes:
    if sha(vanilla) != VANILLA_MATERIAL_SHA256:
        raise ValueError("not the vanilla head material (a Windy City II copy reads other textures)")
    out = vanilla
    for old, new in TEXTURES.items():
        out = replace_same_length(out, old, new, "material")
    return out


def single_file(low: bytes, high: bytes, low_path: str) -> bytes:
    """One XBT with the whole mip chain: high prefix (mip byte = chain length), low DDS header at top size."""
    li, hi = xbt_tool.parse_xbt(low), xbt_tool.parse_xbt(high)
    embedded = low[: li.dds_offset]
    if high_path(low_path).encode("ascii").lower() not in embedded.lower():
        raise ValueError(f"{low_path}: low stream does not name its high stream")
    ld, hd = li.dds, hi.dds
    if hd.mip_count != 1 or ld.pixel_format != hd.pixel_format or (ld.width * 2, ld.height * 2) != (hd.width, hd.height):
        raise ValueError(f"{low_path}: streams do not pair up")
    mips = ld.mip_count + 1
    prefix = bytearray(high[: hi.dds_offset])
    prefix[MIPS_BYTE] = mips
    header = bytearray(low[li.dds_offset : li.dds_offset + 128])
    hh = high[hi.dds_offset : hi.dds_offset + 128]
    header[12:24] = hh[12:24]  # height, width, linear size of the top level
    struct.pack_into("<I", header, 28, mips)
    out = bytes(prefix) + bytes(header) + high[hi.dds_offset + 128 :] + low[li.dds_offset + 128 :]
    check = xbt_tool.parse_xbt(out)
    if (check.dds.width, check.dds.height, check.dds.mip_count) != (hd.width, hd.height, mips):
        raise ValueError(f"{low_path}: single-file XBT does not parse back")
    return out


def privatize(entries: dict[int, bytes], vanilla_material: bytes) -> tuple[dict[int, bytes], dict]:
    """New entry dict and a report.  entries: FAT name hash -> payload of a char01 replacer pack."""
    out = dict(entries)
    xbg_hash = path_hash(XBG)
    out[xbg_hash] = retarget_xbg(entries[xbg_hash])
    added, removed = {PRIVATE_MATERIAL: private_material(vanilla_material)}, []
    for old, new in TEXTURES.items():
        lo, hi = path_hash(old), path_hash(high_path(old))
        if lo not in entries or hi not in entries:
            raise ValueError(f"pack has no {old} low/high pair")
        added[new] = single_file(entries[lo], entries[hi], old)
        removed += [old, high_path(old)]
        del out[lo], out[hi]
    for path, blob in added.items():
        h = path_hash(path)
        if h in out:
            raise ValueError(f"{path} hash {h:08X} already in the pack")
        out[h] = blob
    report = {
        "xbg_material": {"from": HEAD_MATERIAL, "to": PRIVATE_MATERIAL},
        "added": {p: {"hash": f"{path_hash(p):08X}", "bytes": len(b), "sha256": sha(b)} for p, b in added.items()},
        "removed": {p: f"{path_hash(p):08X}" for p in removed},
    }
    return out, report


def check_filelists(paths: list[str], folder: Path) -> list[str]:
    """Private paths whose FAT hash matches any known game path."""
    want = {path_hash(p): p for p in paths}
    clashes = []
    for fl in folder.rglob("*.filelist"):
        for line in fl.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if line and path_hash(line) in want and line.lower() != want[path_hash(line)].lower():
                clashes.append(f"{want[path_hash(line)]} vs {line} ({fl.name})")
    return clashes


def main() -> None:
    ap = argparse.ArgumentParser(description="Give a char01 replacer pack its own head material and textures.")
    ap.add_argument("fat", type=Path, help="pack FAT (the DAT next to it is read)")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--vanilla-material", required=True, type=Path, help="Aiden's mkamelaquino-m-20130115113413.material.bin")
    ap.add_argument("--filelists", type=Path, default=None, help="folder of game .filelist files for a hash clash check")
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    fat = args.fat.read_bytes()
    dat = args.fat.with_suffix(".dat").read_bytes()
    entries = {h: dat[o : o + s] for h, o, s in read_entries(fat)}
    new, report = privatize(entries, args.vanilla_material.read_bytes())
    if args.filelists:
        report["filelist_clashes"] = check_filelists([PRIVATE_MATERIAL, *TEXTURES.values()], args.filelists)
        if report["filelist_clashes"]:
            raise SystemExit(f"hash clashes: {report['filelist_clashes']}")
    out_fat, out_dat = write(fat, new)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    targets = [args.out_dir / args.fat.name, args.out_dir / args.fat.with_suffix(".dat").name]
    if any(t.exists() for t in targets) and not args.force:
        raise SystemExit("output exists (use --force)")
    targets[0].write_bytes(out_fat)
    targets[1].write_bytes(out_dat)
    report["fat_sha256"], report["dat_sha256"] = sha(out_fat), sha(out_dat)
    (args.out_dir / "private_head.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=1))


if __name__ == "__main__":
    main()
