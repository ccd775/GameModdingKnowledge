#!/usr/bin/env python3
"""Inspect and structurally validate an HD2 Stingray patch triplet."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from stingray_archive import (
    TEXTURE_ID,
    companion,
    entry_gpu,
    entry_main,
    entry_stream,
    parse_dds_contract,
    parse_archive,
    rebuild_non_streaming_dds,
    sha256_bytes,
    sha256_file,
    validate_archive,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("patch", type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--extract-non-streaming-textures", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    patch = args.patch.resolve()
    gpu_path = companion(patch, ".gpu_resources")
    stream_path = companion(patch, ".stream")
    for required in (patch, gpu_path, stream_path):
        if not required.is_file():
            raise FileNotFoundError(required)

    data, entries, header = parse_archive(patch)
    gpu = gpu_path.read_bytes()
    stream = stream_path.read_bytes()
    validation = validate_archive(data, gpu, stream, entries, header)
    inventory = []
    extraction = args.extract_non_streaming_textures.resolve() if args.extract_non_streaming_textures else None
    if extraction:
        extraction.mkdir(parents=True, exist_ok=True)

    for row in entries:
        item = {
            "index": row["index"],
            "type_id": f"0x{row['type_id']:016x}",
            "file_id": f"0x{row['file_id']:016x}",
            "toc_size": row["toc_size"],
            "gpu_size": row["gpu_size"],
            "stream_size": row["stream_size"],
            "main_sha256": sha256_bytes(entry_main(data, row)),
            "gpu_sha256": sha256_bytes(entry_gpu(gpu, row)),
            "stream_sha256": sha256_bytes(entry_stream(stream, row)),
        }
        if row["type_id"] == TEXTURE_ID and row["stream_size"] == 0:
            try:
                dds = rebuild_non_streaming_dds(entry_main(data, row), entry_gpu(gpu, row))
                item["texture"] = {
                    "contract": parse_dds_contract(dds),
                    "dds_sha256": sha256_bytes(dds),
                }
                if extraction:
                    (extraction / f"0x{row['file_id']:016x}.dds").write_bytes(dds)
            except ValueError as exc:
                item["texture_error"] = str(exc)
        inventory.append(item)

    report = {
        "schema": "hd2-stingray-patch-inventory-v1",
        "patch": str(patch),
        "hashes": {
            "patch": sha256_file(patch),
            "gpu_resources": sha256_file(gpu_path),
            "stream": sha256_file(stream_path),
        },
        "header": header,
        "validation": validation,
        "entries": inventory,
    }
    output = json.dumps(report, indent=2) + "\n"
    if args.report:
        report_path = args.report.resolve()
        if report_path.exists():
            raise FileExistsError(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(output, encoding="utf-8")
    print(output, end="")
    if not validation["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

