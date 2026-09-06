#!/usr/bin/env python3
"""Extract selected VPK entries using Valve vpk.exe metadata."""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import subprocess
import tempfile
import zlib
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath


ENTRY_RE = re.compile(
    r"^(?P<path>.+) crc=0x(?P<crc>[0-9a-fA-F]+) "
    r"metadatasz=(?P<metadata>\d+) fnumber=(?P<archive>\d+) "
    r"ofs=0x(?P<offset>[0-9a-fA-F]+) sz=(?P<size>\d+)$"
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vpk-exe", required=True, type=Path)
    parser.add_argument("--dir-vpk", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--entry", action="append", required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--replace", action="store_true")
    return parser.parse_args()


def load_index(vpk_exe: Path, dir_vpk: Path) -> dict[str, dict[str, int]]:
    result = subprocess.run(
        [str(vpk_exe), "L", str(dir_vpk)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    index: dict[str, dict[str, int]] = {}
    for raw_line in result.stdout.splitlines():
        match = ENTRY_RE.match(raw_line.strip())
        if not match:
            continue
        path = match.group("path").replace("\\", "/")
        index[path.casefold()] = {
            "path": path,
            "crc32": int(match.group("crc"), 16),
            "metadata_size": int(match.group("metadata")),
            "archive_index": int(match.group("archive")),
            "offset": int(match.group("offset"), 16),
            "size": int(match.group("size")),
        }
    return index


def archive_path(dir_vpk: Path, archive_index: int) -> Path:
    suffix = "_dir.vpk"
    if not dir_vpk.name.casefold().endswith(suffix):
        raise ValueError(f"Expected a *_dir.vpk path: {dir_vpk}")
    prefix = dir_vpk.name[: -len(suffix)]
    return dir_vpk.with_name(f"{prefix}_{archive_index:03d}.vpk")


def embedded_data_offset(vpk_path: Path) -> int:
    with vpk_path.open("rb") as stream:
        header = stream.read(28)
    if len(header) < 12:
        raise ValueError(f"VPK header is truncated: {vpk_path}")
    signature, version, tree_size = struct.unpack_from("<III", header)
    if signature != 0x55AA1234:
        raise ValueError(f"Unexpected VPK signature: 0x{signature:08X}")
    if version == 1:
        header_size = 12
    elif version == 2:
        if len(header) < 28:
            raise ValueError(f"VPK v2 header is truncated: {vpk_path}")
        header_size = 28
    else:
        raise ValueError(f"Unsupported VPK version: {version}")
    return header_size + tree_size


def archive_location(vpk_path: Path, archive_index: int) -> tuple[Path, int]:
    if archive_index == 0x7FFF:
        return vpk_path, embedded_data_offset(vpk_path)
    return archive_path(vpk_path, archive_index), 0


def safe_destination(root: Path, entry: str) -> Path:
    posix = PurePosixPath(entry)
    if posix.is_absolute() or ".." in posix.parts:
        raise ValueError(f"Unsafe VPK entry path: {entry}")
    destination = root.joinpath(*posix.parts).resolve()
    root_resolved = root.resolve()
    if root_resolved != destination and root_resolved not in destination.parents:
        raise ValueError(f"Entry escapes output root: {entry}")
    return destination


def extract_one(
    dir_vpk: Path,
    output: Path,
    metadata: dict[str, int],
    replace: bool,
) -> dict[str, object]:
    if metadata["metadata_size"] != 0:
        raise ValueError(
            f"Preload metadata is not supported for {metadata['path']}: "
            f"{metadata['metadata_size']} bytes"
        )

    source, base_offset = archive_location(dir_vpk, metadata["archive_index"])
    destination = safe_destination(output, str(metadata["path"]))
    if destination.exists() and not replace:
        raise FileExistsError(destination)

    with source.open("rb") as stream:
        stream.seek(base_offset + metadata["offset"])
        payload = stream.read(metadata["size"])
    if len(payload) != metadata["size"]:
        raise IOError(
            f"Short read for {metadata['path']}: {len(payload)} != {metadata['size']}"
        )

    actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
    if actual_crc != metadata["crc32"]:
        raise IOError(
            f"CRC32 mismatch for {metadata['path']}: "
            f"{actual_crc:08X} != {metadata['crc32']:08X}"
        )

    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=destination.parent, prefix=f".{destination.name}.", suffix=".part", delete=False
    ) as temp:
        temp.write(payload)
        temp_path = Path(temp.name)
    try:
        if destination.exists() and not replace:
            raise FileExistsError(destination)
        os.replace(temp_path, destination)
    finally:
        temp_path.unlink(missing_ok=True)

    return {
        "entry": metadata["path"],
        "archive": str(source),
        "archive_index": metadata["archive_index"],
        "offset": metadata["offset"],
        "absolute_offset": base_offset + metadata["offset"],
        "bytes": len(payload),
        "crc32": f"{actual_crc:08X}",
        "output": str(destination),
    }


def main() -> int:
    args = parse_args()
    index = load_index(args.vpk_exe.resolve(), args.dir_vpk.resolve())
    extracted = []
    for requested in args.entry:
        key = requested.replace("\\", "/").casefold()
        if key not in index:
            raise KeyError(f"VPK entry not found: {requested}")
        extracted.append(
            extract_one(
                args.dir_vpk.resolve(), args.output.resolve(), index[key], args.replace
            )
        )

    report = {
        "schema": "karin-l4d2-vpk-extract/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "dir_vpk": str(args.dir_vpk.resolve()),
        "vpk_exe": str(args.vpk_exe.resolve()),
        "accepted": True,
        "entries": extracted,
    }
    encoded = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(encoded, encoding="utf-8")
    print(encoded, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
