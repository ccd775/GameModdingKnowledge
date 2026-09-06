#!/usr/bin/env python3
"""Verify every VPK payload byte-for-byte against a loose addon tree."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
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
    parser.add_argument("--vpk", required=True, type=Path)
    parser.add_argument("--loose", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    return parser.parse_args()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def embedded_data_offset(vpk: Path) -> int:
    header = vpk.read_bytes()[:28]
    if len(header) < 12:
        raise ValueError("Truncated VPK header")
    signature, version, tree_size = struct.unpack_from("<III", header)
    if signature != 0x55AA1234:
        raise ValueError(f"Unexpected VPK signature: 0x{signature:08X}")
    if version == 1:
        return 12 + tree_size
    if version == 2 and len(header) >= 28:
        return 28 + tree_size
    raise ValueError(f"Unsupported VPK version: {version}")


def safe_loose_path(root: Path, entry: str) -> Path:
    relative = PurePosixPath(entry)
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe VPK path: {entry}")
    path = root.joinpath(*relative.parts).resolve()
    if root != path and root not in path.parents:
        raise ValueError(f"VPK path escapes loose root: {entry}")
    return path


def main() -> None:
    args = parse_args()
    vpk_exe = args.vpk_exe.resolve()
    vpk = args.vpk.resolve()
    loose = args.loose.resolve()
    result = subprocess.run(
        [str(vpk_exe), "L", str(vpk)],
        check=True,
        capture_output=True,
        text=True,
        errors="replace",
    )
    entries = []
    for raw_line in result.stdout.splitlines():
        match = ENTRY_RE.match(raw_line.strip())
        if not match:
            continue
        entry = {
            "path": match.group("path").replace("\\", "/"),
            "crc32": int(match.group("crc"), 16),
            "metadata_size": int(match.group("metadata")),
            "archive_index": int(match.group("archive")),
            "offset": int(match.group("offset"), 16),
            "size": int(match.group("size")),
        }
        entries.append(entry)
    if not entries:
        raise ValueError("vpk.exe returned no detailed entries")

    loose_files = sorted(path for path in loose.rglob("*") if path.is_file())
    loose_by_key = {
        path.relative_to(loose).as_posix().casefold(): path for path in loose_files
    }
    entry_by_key = {str(entry["path"]).casefold(): entry for entry in entries}
    if len(entry_by_key) != len(entries):
        raise ValueError("VPK contains case-insensitive duplicate paths")
    if set(entry_by_key) != set(loose_by_key):
        raise ValueError(
            "VPK/loose path mismatch: "
            f"missing={sorted(set(loose_by_key) - set(entry_by_key))}, "
            f"extra={sorted(set(entry_by_key) - set(loose_by_key))}"
        )

    embedded_base = embedded_data_offset(vpk)
    verified = []
    with vpk.open("rb") as stream:
        for key in sorted(entry_by_key):
            entry = entry_by_key[key]
            if entry["metadata_size"] != 0:
                raise ValueError(f"Unexpected preload metadata for {entry['path']}")
            if entry["archive_index"] != 0x7FFF:
                raise ValueError(
                    f"Expected a monolithic embedded VPK, but {entry['path']} uses archive "
                    f"{entry['archive_index']}"
                )
            stream.seek(embedded_base + int(entry["offset"]))
            payload = stream.read(int(entry["size"]))
            if len(payload) != entry["size"]:
                raise IOError(f"Short VPK read for {entry['path']}")
            actual_crc = zlib.crc32(payload) & 0xFFFFFFFF
            if actual_crc != entry["crc32"]:
                raise ValueError(f"VPK CRC mismatch for {entry['path']}")
            loose_path = safe_loose_path(loose, str(entry["path"]))
            loose_payload = loose_path.read_bytes()
            if payload != loose_payload:
                raise ValueError(f"VPK payload differs from loose file: {entry['path']}")
            verified.append(
                {
                    "path": entry["path"],
                    "bytes": len(payload),
                    "crc32": f"{actual_crc:08X}",
                    "sha256": sha256_bytes(payload),
                }
            )

    report = {
        "schema": "karin-l4d2-vpk-validation/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "accepted": True,
        "vpk": {"path": str(vpk), "bytes": vpk.stat().st_size, "sha256": sha256_file(vpk)},
        "loose": str(loose),
        "counts": {"files": len(verified), "payload_bytes": sum(row["bytes"] for row in verified)},
        "files": verified,
    }
    report_path = args.report.resolve()
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"VPK={vpk}")
    print(f"FILES={len(verified)}")
    print(f"SHA256={report['vpk']['sha256']}")
    print(f"REPORT={report_path}")


if __name__ == "__main__":
    main()
