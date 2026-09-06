#!/usr/bin/env python3
"""Build a header-preserving Armor LUT whose rows all use one audited source row."""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
from pathlib import Path


DDS_HEADER_SIZE = 148
BYTES_PER_PIXEL = 8
EXPECTED = {
    "width": 23,
    "height": 8,
    "mipmaps": 5,
    "format_id": 10,
    "resource_dimension": 3,
    "misc_flag": 0,
    "array_size": 1,
    "misc_flags_2": 0,
    "dds_size": 2076,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dds", required=True, type=Path)
    parser.add_argument("--source-row", required=True, type=int, choices=range(8))
    parser.add_argument("--output-dds", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument(
        "--selection-reason",
        default="",
        help="Evidence-backed reason for choosing this source LUT and row",
    )
    return parser.parse_args()


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def parse_contract(data: bytes) -> dict[str, int]:
    if len(data) < DDS_HEADER_SIZE or data[:4] != b"DDS " or data[84:88] != b"DX10":
        raise RuntimeError("Input is not a DX10 DDS")
    if struct.unpack_from("<I", data, 4)[0] != 124:
        raise RuntimeError("Unexpected DDS header")
    return {
        "width": struct.unpack_from("<I", data, 16)[0],
        "height": struct.unpack_from("<I", data, 12)[0],
        "mipmaps": struct.unpack_from("<I", data, 28)[0],
        "format_id": struct.unpack_from("<I", data, 128)[0],
        "resource_dimension": struct.unpack_from("<I", data, 132)[0],
        "misc_flag": struct.unpack_from("<I", data, 136)[0],
        "array_size": struct.unpack_from("<I", data, 140)[0],
        "misc_flags_2": struct.unpack_from("<I", data, 144)[0],
        "dds_size": len(data),
    }


def decode_half_float_row(row: bytes) -> list[dict[str, object]]:
    return [
        {
            "column": column,
            "rgba": [float(value) for value in struct.unpack_from("<4e", row, column * 8)],
        }
        for column in range(len(row) // 8)
    ]


def main() -> None:
    args = parse_args()
    source_path = args.source_dds.resolve()
    output_path = args.output_dds.resolve()
    report_path = args.report.resolve()
    if output_path == source_path:
        raise RuntimeError("output DDS must not be the source DDS")
    for path in (output_path, report_path):
        if path.exists():
            raise FileExistsError(path)

    source = source_path.read_bytes()
    source_contract = parse_contract(source)
    if source_contract != EXPECTED:
        raise RuntimeError(
            "Unexpected Armor LUT contract: "
            f"expected {EXPECTED}, found {source_contract}. Re-audit the game build first."
        )

    output = bytearray(source[:DDS_HEADER_SIZE])
    offset = DDS_HEADER_SIZE
    width = EXPECTED["width"]
    height = EXPECTED["height"]
    mip_reports = []
    selected_base_row: bytes | None = None
    for mip in range(EXPECTED["mipmaps"]):
        row_size = width * BYTES_PER_PIXEL
        mip_size = row_size * height
        source_mip = source[offset : offset + mip_size]
        if len(source_mip) != mip_size:
            raise RuntimeError(f"Mip {mip} is truncated")
        source_row = min(height - 1, args.source_row >> mip)
        row = source_mip[source_row * row_size : (source_row + 1) * row_size]
        if mip == 0:
            selected_base_row = row
        source_row_hashes = [
            sha256(source_mip[index * row_size : (index + 1) * row_size])
            for index in range(height)
        ]
        collapsed = row * height
        output.extend(collapsed)
        output_row_hashes = [
            sha256(collapsed[index * row_size : (index + 1) * row_size])
            for index in range(height)
        ]
        mip_reports.append(
            {
                "mip": mip,
                "width": width,
                "height": height,
                "source_row": source_row,
                "source_unique_rows": len(set(source_row_hashes)),
                "source_row_sha256": sha256(row),
                "all_output_rows_identical": len(set(output_row_hashes)) == 1,
                "output_mip_sha256": sha256(collapsed),
            }
        )
        offset += mip_size
        width = max(1, width // 2)
        height = max(1, height // 2)

    if offset != len(source) or len(output) != len(source):
        raise RuntimeError("Mip traversal did not preserve the DDS size")
    result = bytes(output)
    if result[:DDS_HEADER_SIZE] != source[:DDS_HEADER_SIZE]:
        raise RuntimeError("Output DDS header differs from the source")
    if parse_contract(result) != EXPECTED:
        raise RuntimeError("Output DDS ABI differs from the source")
    if not all(item["all_output_rows_identical"] for item in mip_reports):
        raise RuntimeError("At least one output mip still has different rows")
    if selected_base_row is None:
        raise RuntimeError("No base mip row was selected")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(result)
    report = {
        "schema": "hd2-armor-lut-row-collapse-v1",
        "passed": True,
        "source": {
            "path": str(source_path),
            "sha256": sha256(source),
        },
        "source_row": args.source_row,
        "selection_reason": args.selection_reason,
        "selected_base_row_values": decode_half_float_row(selected_base_row),
        "output": {
            "path": str(output_path),
            "sha256": sha256(result),
        },
        "contract": EXPECTED,
        "header_byte_identical": result[:DDS_HEADER_SIZE] == source[:DDS_HEADER_SIZE],
        "all_mips_collapsed": all(item["all_output_rows_identical"] for item in mip_reports),
        "source_base_mip_unique_rows": mip_reports[0]["source_unique_rows"],
        "mips": mip_reports,
        "interpretation": (
            "The output removes LUT-row variation while preserving the exact DDS header and ABI. "
            "It is causally useful only after the active ID mask and runtime Piece lookup are proven."
        ),
    }
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "HD2_ARMOR_LUT_ROW_COLLAPSE",
        json.dumps(
            {
                "passed": True,
                "source_row": args.source_row,
                "sha256": report["output"]["sha256"],
                "mips": len(mip_reports),
                "source_base_mip_unique_rows": report["source_base_mip_unique_rows"],
            }
        ),
    )


if __name__ == "__main__":
    main()
