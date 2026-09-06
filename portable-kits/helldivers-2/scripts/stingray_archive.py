#!/usr/bin/env python3
"""Minimal HD2 Stingray patch parser and structural validator."""

from __future__ import annotations

import hashlib
import struct
from collections import Counter
from pathlib import Path
from typing import Any


MAGIC = 0xF0000011
HEADER_SIZE = 72
TYPE_ROW_SIZE = 32
ENTRY_SIZE = 80

MATERIAL_ID = 0xEAC0B497876ADEDF
TEXTURE_ID = 0xCD4238C6A0C69E32
UNIT_ID = 0xE0A48D0BE9A7453F


def sha256_bytes(data: bytes | bytearray) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def companion(path: Path, suffix: str) -> Path:
    return Path(f"{path}{suffix}")


def aligned(value: int, alignment: int = 64) -> int:
    return (value + alignment - 1) // alignment * alignment


def parse_archive_bytes(data: bytes, label: str = "archive") -> tuple[list[dict[str, int]], dict[str, Any]]:
    if len(data) < HEADER_SIZE:
        raise ValueError(f"{label} is shorter than the fixed header")

    magic, num_types, num_files, unknown = struct.unpack_from("<IIII", data, 0)
    if magic != MAGIC:
        raise ValueError(f"{label} has unexpected magic 0x{magic:08x}")

    table_end = HEADER_SIZE + num_types * TYPE_ROW_SIZE + num_files * ENTRY_SIZE
    if table_end > len(data):
        raise ValueError(f"{label} tables exceed the file size")

    offset = HEADER_SIZE
    types: list[dict[str, int]] = []
    for _ in range(num_types):
        unknown_1, type_id, count, unknown_2, unknown_3 = struct.unpack_from("<QQQII", data, offset)
        offset += TYPE_ROW_SIZE
        types.append(
            {
                "unknown_1": unknown_1,
                "type_id": type_id,
                "count": count,
                "unknown_2": unknown_2,
                "unknown_3": unknown_3,
            }
        )

    entries: list[dict[str, int]] = []
    for _ in range(num_files):
        values = struct.unpack_from("<QQQQQQQIIIIII", data, offset)
        offset += ENTRY_SIZE
        entries.append(
            dict(
                zip(
                    (
                        "file_id",
                        "type_id",
                        "toc_offset",
                        "stream_offset",
                        "gpu_offset",
                        "unknown_1",
                        "unknown_2",
                        "toc_size",
                        "stream_size",
                        "gpu_size",
                        "unknown_3",
                        "unknown_4",
                        "index",
                    ),
                    values,
                )
            )
        )

    return entries, {
        "magic": magic,
        "num_types": num_types,
        "num_files": num_files,
        "unknown": unknown,
        "types": types,
        "header_end": table_end,
    }


def parse_archive(path: Path) -> tuple[bytes, list[dict[str, int]], dict[str, Any]]:
    data = path.read_bytes()
    entries, header = parse_archive_bytes(data, str(path))
    return data, entries, header


def pack_entry(row: dict[str, int]) -> bytes:
    return struct.pack(
        "<QQQQQQQIIIIII",
        row["file_id"],
        row["type_id"],
        row["toc_offset"],
        row["stream_offset"],
        row["gpu_offset"],
        row["unknown_1"],
        row["unknown_2"],
        row["toc_size"],
        row["stream_size"],
        row["gpu_size"],
        row["unknown_3"],
        row["unknown_4"],
        row["index"],
    )


def type_groups_match(entries: list[dict[str, int]], header: dict[str, Any]) -> bool:
    cursor = 0
    for type_row in header["types"]:
        count = int(type_row["count"])
        group = entries[cursor : cursor + count]
        if len(group) != count or any(row["type_id"] != int(type_row["type_id"]) for row in group):
            return False
        cursor += count
    return cursor == len(entries)


def entry_key(row: dict[str, int]) -> tuple[int, int]:
    return row["type_id"], row["file_id"]


def entry_main(data: bytes, row: dict[str, int]) -> bytes:
    start = row["toc_offset"]
    return data[start : start + row["toc_size"]]


def entry_gpu(gpu: bytes, row: dict[str, int]) -> bytes:
    start = row["gpu_offset"]
    return gpu[start : start + row["gpu_size"]]


def entry_stream(stream: bytes, row: dict[str, int]) -> bytes:
    start = row["stream_offset"]
    return stream[start : start + row["stream_size"]]


def parse_dds_contract(dds: bytes) -> dict[str, int]:
    if len(dds) < 148 or dds[:4] != b"DDS " or dds[84:88] != b"DX10":
        raise ValueError("expected a complete DX10 DDS")
    return {
        "width": struct.unpack_from("<I", dds, 16)[0],
        "height": struct.unpack_from("<I", dds, 12)[0],
        "mipmaps": struct.unpack_from("<I", dds, 28)[0],
        "format_id": struct.unpack_from("<I", dds, 128)[0],
        "resource_dimension": struct.unpack_from("<I", dds, 132)[0],
        "misc_flag": struct.unpack_from("<I", dds, 136)[0],
        "array_size": struct.unpack_from("<I", dds, 140)[0],
        "misc_flags_2": struct.unpack_from("<I", dds, 144)[0],
        "dds_size": len(dds),
        "gpu_payload_size": len(dds) - 148,
    }


def texture_dds_header(main: bytes) -> bytes:
    if len(main) < 340:
        raise ValueError("texture main payload is shorter than TextureInfo + DDS header")
    header = main[192:340]
    parse_dds_contract(header)
    return header


def rebuild_non_streaming_dds(main: bytes, gpu_payload: bytes, stream_payload: bytes = b"") -> bytes:
    if stream_payload:
        raise ValueError("runtime LUT helper only rebuilds non-streaming textures")
    return texture_dds_header(main) + gpu_payload


def validate_archive(
    data: bytes,
    gpu: bytes,
    stream: bytes,
    entries: list[dict[str, int]],
    header: dict[str, Any],
) -> dict[str, Any]:
    checks: dict[str, bool] = {}
    checks["file_count"] = int(header["num_files"]) == len(entries)
    checks["type_count_sum"] = sum(int(row["count"]) for row in header["types"]) == len(entries)
    checks["type_segments_contiguous"] = type_groups_match(entries, header)
    keys = [entry_key(row) for row in entries]
    checks["unique_resource_keys"] = len(keys) == len(set(keys))
    checks["sequential_indices"] = [row["index"] for row in entries] == list(range(1, len(entries) + 1))

    main_bounds = all(
        row["toc_offset"] >= int(header["header_end"])
        and row["toc_offset"] + row["toc_size"] <= len(data)
        for row in entries
    )
    gpu_bounds = all(row["gpu_size"] == 0 or row["gpu_offset"] + row["gpu_size"] <= len(gpu) for row in entries)
    stream_bounds = all(
        row["stream_size"] == 0 or row["stream_offset"] + row["stream_size"] <= len(stream) for row in entries
    )
    checks["main_bounds"] = main_bounds
    checks["gpu_bounds"] = gpu_bounds
    checks["stream_bounds"] = stream_bounds

    cursor = int(header["header_end"])
    contiguous_main = True
    for row in sorted(entries, key=lambda item: item["toc_offset"]):
        if row["toc_offset"] != cursor:
            contiguous_main = False
            break
        cursor += row["toc_size"]
    checks["main_payloads_contiguous"] = contiguous_main and cursor == len(data)

    counts = Counter(row["type_id"] for row in entries)
    return {
        "passed": all(checks.values()),
        "checks": checks,
        "entry_count": len(entries),
        "type_counts": {f"0x{key:016x}": value for key, value in counts.items()},
        "sizes": {"patch": len(data), "gpu_resources": len(gpu), "stream": len(stream)},
    }


def require_valid_archive(data: bytes, gpu: bytes, stream: bytes, label: str) -> tuple[list[dict[str, int]], dict[str, Any], dict[str, Any]]:
    entries, header = parse_archive_bytes(data, label)
    report = validate_archive(data, gpu, stream, entries, header)
    if not report["passed"]:
        failed = [name for name, passed in report["checks"].items() if not passed]
        raise ValueError(f"{label} failed archive validation: {', '.join(failed)}")
    return entries, header, report

