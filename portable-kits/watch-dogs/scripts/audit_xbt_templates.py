#!/usr/bin/env python3
"""Audit Watch Dogs XBT files and emit a compact donor-template matrix."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from collections import defaultdict
from dataclasses import asdict
from pathlib import Path, PureWindowsPath

from xbt_tool import FormatError, inspect_xbt


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def full_mip_count(width: int, height: int) -> int:
    return int(math.floor(math.log2(max(width, height)))) + 1


def metadata(path: Path, root: Path) -> dict[str, object]:
    info = inspect_xbt(path)
    return {
        "file": path.relative_to(root).as_posix(),
        "sha256": sha256(path),
        "version": info.version,
        "xbt_bytes": info.total_bytes,
        "dds_offset": info.dds_offset,
        "streamed_high_path": info.streamed_high_path,
        "dds": asdict(info.dds),
    }


def signature(record: dict[str, object], high: dict[str, object] | None) -> tuple:
    low_dds = record["dds"]
    assert isinstance(low_dds, dict)
    if high is None:
        return (
            "standalone",
            low_dds["pixel_format"],
            low_dds["width"],
            low_dds["height"],
            low_dds["mip_count"],
            "",
            "",
            "",
        )
    high_dds = high["dds"]
    assert isinstance(high_dds, dict)
    return (
        "stream_pair",
        low_dds["pixel_format"],
        low_dds["width"],
        low_dds["height"],
        low_dds["mip_count"],
        high_dds["width"],
        high_dds["height"],
        high_dds["mip_count"],
    )


def audit(root: Path) -> dict[str, object]:
    paths = sorted(root.glob("*.xbt"), key=lambda path: path.name.casefold())
    if not paths:
        raise FormatError(f"no .xbt files found in {root}")

    records = [metadata(path, root) for path in paths]
    by_name = {str(record["file"]).casefold(): record for record in records}
    referenced_highs: set[str] = set()
    pairs: list[dict[str, object]] = []
    issues: list[str] = []
    matrix_groups: dict[tuple, list[tuple[str, str | None]]] = defaultdict(list)

    for low in records:
        high_path = low["streamed_high_path"]
        if not high_path:
            continue
        high_name = PureWindowsPath(str(high_path)).name
        referenced_highs.add(high_name.casefold())
        high = by_name.get(high_name.casefold())
        pair_issues: list[str] = []
        if high is None:
            pair_issues.append(f"referenced high stream is missing: {high_name}")
        else:
            low_dds = low["dds"]
            high_dds = high["dds"]
            assert isinstance(low_dds, dict) and isinstance(high_dds, dict)
            if low["version"] != high["version"]:
                pair_issues.append("XBT versions differ")
            if low_dds["pixel_format"] != high_dds["pixel_format"]:
                pair_issues.append("DDS formats differ")
            if high_dds["width"] != int(low_dds["width"]) * 2:
                pair_issues.append("high width is not 2x low width")
            if high_dds["height"] != int(low_dds["height"]) * 2:
                pair_issues.append("high height is not 2x low height")
            if high_dds["mip_count"] != 1:
                pair_issues.append("high stream does not contain exactly one mip")
            expected_low_mips = full_mip_count(
                int(low_dds["width"]), int(low_dds["height"])
            )
            if low_dds["mip_count"] != expected_low_mips:
                pair_issues.append(
                    f"low stream has {low_dds['mip_count']} mips; expected {expected_low_mips}"
                )
            if high["streamed_high_path"]:
                pair_issues.append("high stream unexpectedly references another high stream")

        pair = {
            "low": low["file"],
            "high": high["file"] if high else None,
            "embedded_high_path": high_path,
            "issues": pair_issues,
        }
        pairs.append(pair)
        matrix_groups[signature(low, high)].append((str(low["file"]), high_name if high else None))
        issues.extend(f"{low['file']}: {issue}" for issue in pair_issues)

    standalone: list[str] = []
    orphan_highs: list[str] = []
    for record in records:
        name = str(record["file"])
        if record["streamed_high_path"]:
            continue
        if name.casefold().endswith("_high.xbt"):
            if name.casefold() not in referenced_highs:
                orphan_highs.append(name)
                issues.append(f"{name}: unreferenced _high stream")
            continue
        standalone.append(name)
        matrix_groups[signature(record, None)].append((name, None))

    matrix: list[dict[str, object]] = []
    for index, (key, members) in enumerate(sorted(matrix_groups.items()), start=1):
        (
            kind,
            pixel_format,
            low_width,
            low_height,
            low_mips,
            high_width,
            high_height,
            high_mips,
        ) = key
        matrix.append(
            {
                "template_id": f"T{index:02d}",
                "kind": kind,
                "pixel_format": pixel_format,
                "low_width": low_width,
                "low_height": low_height,
                "low_mips": low_mips,
                "high_width": high_width,
                "high_height": high_height,
                "high_mips": high_mips,
                "member_count": len(members),
                "example_low": members[0][0],
                "example_high": members[0][1] or "",
            }
        )

    return {
        "schema_version": 1,
        "source_root": str(root.resolve()),
        "summary": {
            "xbt_files": len(records),
            "stream_pairs": len(pairs),
            "standalone_files": len(standalone),
            "orphan_high_files": len(orphan_highs),
            "unique_template_signatures": len(matrix),
            "issues": len(issues),
        },
        "template_matrix": matrix,
        "pairs": pairs,
        "standalone": standalone,
        "orphan_highs": orphan_highs,
        "issues": issues,
        "files": records,
    }


def write_outputs(report: dict[str, object], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "template_matrix.json"
    csv_path = output_dir / "template_matrix.csv"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )

    fieldnames = [
        "template_id",
        "kind",
        "pixel_format",
        "low_width",
        "low_height",
        "low_mips",
        "high_width",
        "high_height",
        "high_mips",
        "member_count",
        "example_low",
        "example_high",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(report["template_matrix"])


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("xbt_dir", type=Path, help="directory containing donor XBT files")
    parser.add_argument("output_dir", type=Path, help="directory for CSV/JSON audit output")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        root = args.xbt_dir.resolve(strict=True)
        report = audit(root)
        write_outputs(report, args.output_dir.resolve())
    except (OSError, FormatError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2

    print(json.dumps(report["summary"], sort_keys=True))
    return 1 if report["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
