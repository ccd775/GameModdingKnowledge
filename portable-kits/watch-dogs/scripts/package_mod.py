"""Package a Watch Dogs character mod for ModManager: base pack with replaced entries + modconfig.json -> ZIP.

  python package_mod.py --base-fat OLD.fat --out-dir OUT --pack NAME --friendly-id ID --name TEXT --version X
         [--replace game/path=file | HASH=file ...] [--modconfig FILE] [--description TEXT] [--author NAME]
         [--zip-date YYYY-MM-DD] [--force]

Start from an existing char01 replacer pack: it carries what the template XBG references (private
materials) and any model database entries; replacing only XBG/XBT keeps those.  FAT/DAT are rebuilt with
repack_fat8.rebuild and every entry is re-read and compared.  modconfig.json starts from --modconfig, else
the modconfig.json next to the base FAT, else a minimal config, with friendlyId, name, packs, version and
the given description/author overridden.  A new friendlyId and pack let the mod sit next to the old one in
ModManager; enable only one of them.  The ZIP holds <pack>.dat, <pack>.fat and modconfig.json with a fixed
timestamp, so it is reproducible.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_fat8 import read_entries  # noqa: E402
from repack_fat8 import entry_hash, rebuild  # noqa: E402

MINIMAL_CONFIG = {"friendlyId": "", "name": "", "author": "", "description": "", "packs": [], "version": "",
                  "configVersion": 1, "luaAutoStart": [], "dominoAutoStart": [], "donationUrl": "",
                  "minTntVersion": "1.1.1", "authorProfileUrl": "", "modsRecommendedBelowPriority": ["living_city"]}


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def entries_of(fat: bytes, dat: bytes) -> dict[int, bytes]:
    return {h: dat[o : o + s] for h, o, s in read_entries(fat)}


def package(base_fat: Path, replacements: dict[int, bytes], out_dir: Path, config: dict, pack: str,
            zip_date=(1980, 1, 1, 0, 0, 0)) -> dict:
    fat, dat = base_fat.read_bytes(), base_fat.with_suffix(".dat").read_bytes()
    new_fat, new_dat = rebuild(fat, dat, replacements)
    src, dst = entries_of(fat, dat), entries_of(new_fat, new_dat)
    if src.keys() != dst.keys():
        raise SystemExit("entry set changed")
    for h in src:
        if dst[h] != replacements.get(h, src[h]):
            raise SystemExit(f"entry {h:08X} mismatch after repack")
    folder = out_dir / "package"
    folder.mkdir(parents=True, exist_ok=True)
    files = {f"{pack}.dat": new_dat, f"{pack}.fat": new_fat,
             # CRLF, like the ModManager-accepted packages
             "modconfig.json": (json.dumps(config, indent=2, ensure_ascii=True) + "\n").replace("\n", "\r\n").encode("ascii")}
    for name, data in files.items():
        (folder / name).write_bytes(data)
    version = str(config.get("version", "")).replace(".", "_").replace("-", "_")
    zip_path = out_dir / f"{config['friendlyId']}_v{version}.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for name, data in files.items():
            info = zipfile.ZipInfo(name, date_time=zip_date)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            z.writestr(info, data, compresslevel=9)
    return {"zip": str(zip_path), "zip_sha256": sha(zip_path.read_bytes()),
            "files": {n: sha(d) for n, d in files.items()},
            "replaced_entries": sorted(f"{h:08X}" for h in replacements), "unchanged_entries": len(src) - len(replacements)}


def make_config(base_fat: Path, modconfig: Path | None, pack: str, friendly_id: str, name: str, version: str,
                description: str | None = None, author: str | None = None) -> dict:
    source = modconfig or base_fat.with_name("modconfig.json")
    cfg = json.loads(source.read_text(encoding="utf-8-sig")) if source.is_file() else dict(MINIMAL_CONFIG)
    cfg.update({"friendlyId": friendly_id, "name": name, "packs": [pack], "version": version})
    if description is not None:
        cfg["description"] = description
    if author is not None:
        cfg["author"] = author
    return cfg


def main() -> None:
    ap = argparse.ArgumentParser(description="Package a Watch Dogs character mod: base pack + replaced entries + modconfig -> ZIP.")
    ap.add_argument("--base-fat", required=True, type=Path, help="existing char01 replacer FAT; its DAT is read")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--pack", required=True, help="FAT/DAT base name, also listed in modconfig packs")
    ap.add_argument("--friendly-id", required=True)
    ap.add_argument("--name", required=True)
    ap.add_argument("--version", required=True)
    ap.add_argument("--replace", action="append", default=[], metavar="KEY=file", help="game path or 8-digit hash, repeatable")
    ap.add_argument("--modconfig", type=Path, default=None)
    ap.add_argument("--description", default=None)
    ap.add_argument("--author", default=None)
    ap.add_argument("--zip-date", default="1980-01-01", help="timestamp stored in the ZIP (reproducible output)")
    ap.add_argument("--force", action="store_true", help="write into an existing package folder / ZIP")
    args = ap.parse_args()
    if (args.out_dir / "package").exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.out_dir / 'package'} (use --force)")
    replacements = {}
    for item in args.replace:
        key, path = item.split("=", 1)
        replacements[entry_hash(key)] = Path(path).read_bytes()
    cfg = make_config(args.base_fat, args.modconfig, args.pack, args.friendly_id, args.name, args.version,
                      args.description, args.author)
    y, mo, d = (int(x) for x in args.zip_date.split("-"))
    print(json.dumps(package(args.base_fat, replacements, args.out_dir, cfg, args.pack, (y, mo, d, 0, 0, 0)), indent=1))


if __name__ == "__main__":
    main()
