#!/usr/bin/env python3
"""Rebuild the observed Black Flag Resynced v50 reference patch.

The tool preserves the supplied Forge's object IDs, entry order, untyped
metadata entries, and opaque bundle-index suffixes.  Only explicitly selected
decoded resources are replaced.  Affected typed entries are rebuilt with the
measured field-4 LZ4 BMS layouts and then decoded again before the output is
committed.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import struct
import sys
import tempfile
import zlib
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "work" / "reference_extraction" / "input" / "DataPC_boot_patch_02.forge"
DEFAULT_OUTPUT = ROOT / "work" / "package" / "DataPC_boot_patch_02.forge"
DEFAULT_REPORT = ROOT / "work" / "reports" / "forge_v50_patch_rebuild.json"

FORGE_HEADER = struct.Struct("<8sBIQQQ")
FAT_HEADER = struct.Struct("<IQQ")
FAT_ROW = struct.Struct("<QQII")
BMS_HEADER = struct.Struct("<QHBI")
BMS_MAGIC = 0x1004FA9957FBAA33
BUNDLE_RECORD = struct.Struct("<QI6s")
FORGE_MAGIC = b"scimitar"
FORGE_VERSION = 50
LZ4_FIELD = 4
DEFAULT_ALIGNMENT = 32768


class RebuildError(RuntimeError):
    pass


@dataclass(frozen=True)
class TocRow:
    offset: int
    object_id: int
    stored_size: int
    resource_type: int


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "path": str(path.resolve()),
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256_file(path),
    }


def hex64(value: int) -> str:
    return f"0x{value:016X}"


def hex32(value: int) -> str:
    return f"0x{value:08X}"


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return str(path.resolve())


def load_lz4() -> Any:
    local = ROOT / "tools" / "python-packages"
    if local.is_dir():
        sys.path.insert(0, str(local))
    try:
        import lz4.block  # type: ignore[import-not-found]
    except ImportError as error:
        raise RebuildError("lz4.block is unavailable; expected tools/python-packages") from error
    return lz4.block


def parse_outer_forge(data: bytes) -> tuple[dict[str, Any], list[TocRow], list[bytes]]:
    if len(data) < FORGE_HEADER.size:
        raise RebuildError("Forge header is truncated")
    magic, separator, version, fat_offset, global_id, flags = FORGE_HEADER.unpack_from(data, 0)
    if magic != FORGE_MAGIC or separator != 0 or version != FORGE_VERSION:
        raise RebuildError(f"unexpected Forge header: {magic!r}, separator={separator}, version={version}")
    if fat_offset + FAT_HEADER.size > len(data):
        raise RebuildError("FAT header is out of bounds")
    entry_count, toc_offset, sentinel = FAT_HEADER.unpack_from(data, fat_offset)
    data_start = fat_offset + FAT_HEADER.size
    toc_end = toc_offset + entry_count * FAT_ROW.size
    if not (data_start <= toc_offset <= toc_end <= len(data)):
        raise RebuildError("Forge TOC is out of bounds")

    rows: list[TocRow] = []
    entries: list[bytes] = []
    previous_end = data_start
    for index in range(entry_count):
        row = TocRow(*FAT_ROW.unpack_from(data, toc_offset + index * FAT_ROW.size))
        end = row.offset + row.stored_size
        if row.offset != previous_end or end > toc_offset:
            raise RebuildError(f"entry {index} is not in the measured contiguous data layout")
        rows.append(row)
        entries.append(data[row.offset:end])
        previous_end = end
    if previous_end != toc_offset:
        raise RebuildError("entry data does not end at the TOC")
    if any(data[toc_end:]):
        raise RebuildError("reference Forge has non-zero trailing bytes")
    header = {
        "fat_offset": fat_offset,
        "data_start": data_start,
        "toc_offset": toc_offset,
        "toc_end": toc_end,
        "entry_count": entry_count,
        "global_id": hex64(global_id),
        "flags": hex64(flags),
        "sentinel": hex64(sentinel),
        "prefix": data[:data_start],
    }
    return header, rows, entries


def decode_lz4_chunk(lz4_block: Any, stored: bytes, decoded_size: int) -> bytes:
    if len(stored) == decoded_size:
        return stored
    try:
        decoded = lz4_block.decompress(stored, uncompressed_size=decoded_size)
    except Exception as error:
        raise RebuildError(f"LZ4 block failed to decode to {decoded_size} bytes") from error
    if len(decoded) != decoded_size:
        raise RebuildError(f"LZ4 decoded {len(decoded)} bytes, expected {decoded_size}")
    return decoded


def decode_bms(
    data: bytes,
    start: int,
    expected_size: int | None,
    lz4_block: Any,
) -> tuple[dict[str, Any], bytes, int]:
    if start + BMS_HEADER.size > len(data):
        raise RebuildError("BMS header is out of bounds")
    magic, version, field, block_size_raw = BMS_HEADER.unpack_from(data, start)
    if magic != BMS_MAGIC or field != LZ4_FIELD:
        raise RebuildError(f"unsupported BMS magic/field: {hex64(magic)}/{field}")
    toc_mode = bool(block_size_raw & 0x80000000)
    block_size = block_size_raw & 0x7FFFFFFF
    if block_size <= 0:
        raise RebuildError("BMS block size is zero")
    cursor = start + BMS_HEADER.size
    records: list[tuple[bool, int, int, int | None, int]] = []
    if toc_mode:
        if cursor + 4 > len(data):
            raise RebuildError("BMS TOC count is truncated")
        count = struct.unpack_from("<i", data, cursor)[0]
        cursor += 4
        if not (0 < count <= 1_000_000) or cursor + count * 8 > len(data):
            raise RebuildError(f"invalid BMS TOC chunk count {count}")
        sizes = [struct.unpack_from("<ii", data, cursor + i * 8) for i in range(count)]
        cursor += count * 8
        for decoded_size, stored_size in sizes:
            if decoded_size <= 0 or stored_size <= 0 or cursor + 4 + stored_size > len(data):
                raise RebuildError("invalid BMS TOC chunk bounds")
            checksum = struct.unpack_from("<I", data, cursor)[0]
            cursor += 4
            records.append((stored_size != decoded_size, stored_size, decoded_size, checksum, cursor))
            cursor += stored_size
    else:
        decoded_total = 0
        while expected_size is None or decoded_total < expected_size:
            if cursor >= len(data):
                raise RebuildError("default-mode BMS ended before its decoded payload")
            compressed = data[cursor]
            cursor += 1
            if compressed not in (0, 1):
                raise RebuildError(f"invalid default-mode BMS flag {compressed}")
            if compressed:
                if cursor + 12 > len(data):
                    raise RebuildError("compressed default-mode header is truncated")
                stored_size, decoded_size, checksum = struct.unpack_from("<iiI", data, cursor)
                cursor += 12
            else:
                if cursor + 4 > len(data):
                    raise RebuildError("raw default-mode header is truncated")
                stored_size = struct.unpack_from("<i", data, cursor)[0]
                decoded_size = stored_size
                checksum = None
                cursor += 4
            if stored_size <= 0 or decoded_size <= 0 or cursor + stored_size > len(data):
                raise RebuildError("invalid default-mode BMS chunk bounds")
            records.append((bool(compressed), stored_size, decoded_size, checksum, cursor))
            cursor += stored_size
            decoded_total += decoded_size
            if expected_size is not None and decoded_total > expected_size:
                raise RebuildError("default-mode BMS exceeds its expected decoded size")
            if expected_size is None and cursor == len(data):
                break

    decoded_parts: list[bytes] = []
    chunk_report: list[dict[str, Any]] = []
    for index, (compressed, stored_size, decoded_size, checksum, payload_offset) in enumerate(records):
        stored = data[payload_offset : payload_offset + stored_size]
        if checksum is not None:
            actual = zlib.adler32(stored, 0) & 0xFFFFFFFF
            if actual != checksum:
                raise RebuildError(f"BMS chunk {index} Adler32 mismatch")
        decoded = decode_lz4_chunk(lz4_block, stored, decoded_size)
        decoded_parts.append(decoded)
        chunk_report.append(
            {
                "index": index,
                "compressed": compressed,
                "stored_size": stored_size,
                "decoded_size": decoded_size,
                "stored_sha256": sha256_bytes(stored),
                "decoded_sha256": sha256_bytes(decoded),
            }
        )
    decoded = b"".join(decoded_parts)
    if expected_size is not None and len(decoded) != expected_size:
        raise RebuildError(f"BMS decoded {len(decoded)} bytes, expected {expected_size}")
    return (
        {
            "format_version": version,
            "field": field,
            "toc_mode": toc_mode,
            "block_size": block_size,
            "chunk_count": len(records),
            "chunks": chunk_report,
            "decoded_size": len(decoded),
            "decoded_sha256": sha256_bytes(decoded),
        },
        decoded,
        cursor,
    )


def parse_bundle_index(data: bytes) -> tuple[list[dict[str, Any]], bytes]:
    if len(data) < 2:
        raise RebuildError("bundle index is truncated")
    count = struct.unpack_from("<H", data, 0)[0]
    records_end = 2 + count * BUNDLE_RECORD.size
    if records_end > len(data):
        raise RebuildError("bundle index records are out of bounds")
    records: list[dict[str, Any]] = []
    for index in range(count):
        offset = 2 + index * BUNDLE_RECORD.size
        object_id, decoded_size, reserved = BUNDLE_RECORD.unpack_from(data, offset)
        records.append(
            {
                "index": index,
                "object_id": object_id,
                "decoded_size": decoded_size,
                "reserved": reserved,
            }
        )
    return records, data[records_end:]


def build_bundle_index(records: list[dict[str, Any]], suffix: bytes) -> bytes:
    output = bytearray(struct.pack("<H", len(records)))
    for record in records:
        output += BUNDLE_RECORD.pack(record["object_id"], record["decoded_size"], record["reserved"])
    output += suffix
    return bytes(output)


def encode_lz4_chunk(lz4_block: Any, decoded: bytes) -> tuple[bool, bytes]:
    if not decoded:
        raise RebuildError("zero-length BMS chunks are not supported")
    compressed = lz4_block.compress(decoded, mode="high_compression", compression=12, store_size=False)
    if len(compressed) < len(decoded):
        return True, compressed
    return False, decoded


def encode_bms(
    decoded: bytes,
    version: int,
    block_size: int,
    toc_mode: bool,
    lz4_block: Any,
) -> tuple[bytes, dict[str, Any]]:
    if not decoded:
        raise RebuildError("cannot encode an empty BMS payload")
    chunks = [decoded[offset : offset + block_size] for offset in range(0, len(decoded), block_size)]
    encoded_chunks = [encode_lz4_chunk(lz4_block, chunk) for chunk in chunks]
    raw_block_size = block_size | (0x80000000 if toc_mode else 0)
    output = bytearray(BMS_HEADER.pack(BMS_MAGIC, version, LZ4_FIELD, raw_block_size))
    if toc_mode:
        output += struct.pack("<i", len(chunks))
        for chunk, (_, stored) in zip(chunks, encoded_chunks):
            output += struct.pack("<ii", len(chunk), len(stored))
        for _, stored in encoded_chunks:
            output += struct.pack("<I", zlib.adler32(stored, 0) & 0xFFFFFFFF)
            output += stored
    else:
        for chunk, (compressed, stored) in zip(chunks, encoded_chunks):
            if compressed:
                output += struct.pack(
                    "<BiiI",
                    1,
                    len(stored),
                    len(chunk),
                    zlib.adler32(stored, 0) & 0xFFFFFFFF,
                )
            else:
                output += struct.pack("<Bi", 0, len(stored))
            output += stored
    report = {
        "toc_mode": toc_mode,
        "block_size": block_size,
        "chunk_count": len(chunks),
        "decoded_size": len(decoded),
        "decoded_sha256": sha256_bytes(decoded),
        "stored_size": len(output),
        "stored_sha256": sha256_bytes(output),
        "compressed_chunks": sum(1 for compressed, _ in encoded_chunks if compressed),
        "raw_chunks": sum(1 for compressed, _ in encoded_chunks if not compressed),
    }
    return bytes(output), report


def validate_resource(resource: bytes, expected_id: int, expected_type: int) -> dict[str, Any]:
    if len(resource) < 25:
        raise RebuildError(f"resource {hex64(expected_id)} is too short")
    wrapper_type = struct.unpack_from("<I", resource, 0)[0]
    body_size = struct.unpack_from("<Q", resource, 4)[0]
    zero_flag = resource[12]
    object_id = struct.unpack_from("<Q", resource, 13)[0]
    embedded_type = struct.unpack_from("<I", resource, 21)[0]
    if wrapper_type != expected_type or embedded_type != expected_type:
        raise RebuildError(
            f"resource {hex64(expected_id)} type mismatch: wrapper={hex32(wrapper_type)}, "
            f"embedded={hex32(embedded_type)}, expected={hex32(expected_type)}"
        )
    if object_id != expected_id or body_size != len(resource) - 13 or zero_flag != 0:
        raise RebuildError(f"resource {hex64(expected_id)} envelope mismatch")
    return {
        "object_id": hex64(object_id),
        "type": hex32(wrapper_type),
        "size": len(resource),
        "sha256": sha256_bytes(resource),
    }


def parse_typed_entry(entry: bytes, expected_type: int, lz4_block: Any) -> dict[str, Any]:
    bms0, bundle_data, cursor = decode_bms(entry, 0, None, lz4_block)
    records, suffix = parse_bundle_index(bundle_data)
    expected_payload = sum(record["decoded_size"] for record in records)
    bms1, payload, end = decode_bms(entry, cursor, expected_payload, lz4_block)
    if end != len(entry):
        raise RebuildError(f"typed entry has {len(entry) - end} unparsed trailing bytes")
    assets: list[bytes] = []
    asset_reports: list[dict[str, Any]] = []
    payload_cursor = 0
    for record in records:
        asset = payload[payload_cursor : payload_cursor + record["decoded_size"]]
        payload_cursor += record["decoded_size"]
        asset_reports.append(validate_resource(asset, record["object_id"], expected_type if len(records) == 1 else struct.unpack_from("<I", asset, 0)[0]))
        assets.append(asset)
    if payload_cursor != len(payload):
        raise RebuildError("asset records do not consume the typed-entry payload")
    return {
        "bms0": bms0,
        "bms1": bms1,
        "records": records,
        "bundle_suffix": suffix,
        "assets": assets,
        "asset_reports": asset_reports,
    }


def rebuild_typed_entry(
    entry: bytes,
    resource_type: int,
    replacements: dict[int, bytes],
    reencode_all: bool,
    lz4_block: Any,
) -> tuple[bytes, dict[str, Any], set[int]]:
    parsed = parse_typed_entry(entry, resource_type, lz4_block)
    replaced: set[int] = set()
    rebuilt_assets: list[bytes] = []
    updated_records: list[dict[str, Any]] = []
    for record, original in zip(parsed["records"], parsed["assets"]):
        object_id = record["object_id"]
        asset = replacements.get(object_id, original)
        if object_id in replacements:
            expected_type = struct.unpack_from("<I", original, 0)[0]
            validate_resource(asset, object_id, expected_type)
            replaced.add(object_id)
        rebuilt_assets.append(asset)
        updated_records.append({**record, "decoded_size": len(asset)})
    if not replaced and not reencode_all:
        return entry, {"copied_exactly": True, "replaced_ids": []}, replaced

    bundle = build_bundle_index(updated_records, parsed["bundle_suffix"])
    payload = b"".join(rebuilt_assets)
    encoded0, encoded0_report = encode_bms(
        bundle,
        parsed["bms0"]["format_version"],
        parsed["bms0"]["block_size"],
        True,
        lz4_block,
    )
    encoded1, encoded1_report = encode_bms(
        payload,
        parsed["bms1"]["format_version"],
        parsed["bms1"]["block_size"],
        False,
        lz4_block,
    )
    rebuilt = encoded0 + encoded1

    verified = parse_typed_entry(rebuilt, resource_type, lz4_block)
    if [item["object_id"] for item in verified["records"]] != [item["object_id"] for item in updated_records]:
        raise RebuildError("rebuilt typed-entry object order changed")
    for expected, actual in zip(rebuilt_assets, verified["assets"]):
        if actual != expected:
            raise RebuildError("rebuilt typed-entry asset bytes changed after decode")
    report = {
        "copied_exactly": False,
        "source_size": len(entry),
        "rebuilt_size": len(rebuilt),
        "source_sha256": sha256_bytes(entry),
        "rebuilt_sha256": sha256_bytes(rebuilt),
        "replaced_ids": [hex64(value) for value in sorted(replaced)],
        "asset_count": len(rebuilt_assets),
        "bms0": encoded0_report,
        "bms1": encoded1_report,
        "verified_asset_sha256": [sha256_bytes(asset) for asset in verified["assets"]],
    }
    return rebuilt, report, replaced


def build_outer_forge(
    source: bytes,
    header: dict[str, Any],
    rows: list[TocRow],
    entries: list[bytes],
    alignment: int,
) -> tuple[bytes, list[TocRow]]:
    if alignment <= 0 or alignment & (alignment - 1):
        raise RebuildError("output alignment must be a positive power of two")
    prefix = bytearray(header["prefix"])
    cursor = header["data_start"]
    new_rows: list[TocRow] = []
    data_region = bytearray()
    for row, entry in zip(rows, entries):
        new_rows.append(TocRow(cursor, row.object_id, len(entry), row.resource_type))
        data_region += entry
        cursor += len(entry)
    toc_offset = cursor
    struct.pack_into("<Q", prefix, header["fat_offset"] + 4, toc_offset)
    toc = b"".join(FAT_ROW.pack(row.offset, row.object_id, row.stored_size, row.resource_type) for row in new_rows)
    output = bytes(prefix) + bytes(data_region) + toc
    padding = (-len(output)) % alignment
    output += bytes(padding)
    return output, new_rows


def parse_replacements(values: list[str]) -> tuple[dict[int, bytes], dict[int, str]]:
    replacements: dict[int, bytes] = {}
    paths: dict[int, str] = {}
    for value in values:
        if "=" not in value:
            raise RebuildError(f"replacement must be OBJECT_ID=PATH: {value}")
        object_text, path_text = value.split("=", 1)
        object_id = int(object_text, 0)
        path = Path(path_text).expanduser().resolve()
        if object_id in replacements:
            raise RebuildError(f"duplicate replacement ID {hex64(object_id)}")
        if not path.is_file():
            raise RebuildError(f"replacement file does not exist: {path}")
        replacements[object_id] = path.read_bytes()
        paths[object_id] = relative(path)
    return replacements, paths


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_name, path)
    except Exception:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise


def run(args: argparse.Namespace) -> dict[str, Any]:
    input_path = args.input.resolve()
    output_path = args.output.resolve()
    if input_path == output_path:
        raise RebuildError("input and output paths must differ")
    if output_path.exists() or args.report.exists() or args.report.resolve() == output_path:
        raise RebuildError("Use distinct, new output and report paths")
    if args.alignment < 1 or args.alignment & (args.alignment - 1):
        raise RebuildError("alignment must be a positive power of two")
    before = snapshot(input_path)
    source = input_path.read_bytes()
    replacements, replacement_paths = parse_replacements(args.replace)
    lz4_block = load_lz4()
    header, rows, source_entries = parse_outer_forge(source)

    rebuilt_entries: list[bytes] = []
    entry_reports: list[dict[str, Any]] = []
    found: set[int] = set()
    for index, (row, entry) in enumerate(zip(rows, source_entries)):
        if row.resource_type:
            rebuilt, details, replaced = rebuild_typed_entry(
                entry,
                row.resource_type,
                replacements,
                args.reencode_all,
                lz4_block,
            )
            found.update(replaced)
        else:
            rebuilt = entry
            details = {"copied_exactly": True, "replaced_ids": []}
        rebuilt_entries.append(rebuilt)
        entry_reports.append(
            {
                "index": index,
                "object_id": hex64(row.object_id),
                "resource_type": hex32(row.resource_type),
                **details,
            }
        )
    missing = set(replacements) - found
    if missing:
        raise RebuildError("replacement IDs not found in reference patch: " + ", ".join(hex64(v) for v in sorted(missing)))

    output, new_rows = build_outer_forge(source, header, rows, rebuilt_entries, args.alignment)
    parsed_header, parsed_rows, parsed_entries = parse_outer_forge(output)
    if len(parsed_rows) != len(rows) or parsed_header["entry_count"] != header["entry_count"]:
        raise RebuildError("rebuilt Forge entry count changed")
    for index, (row, new_row, expected_entry, actual_entry) in enumerate(zip(rows, parsed_rows, rebuilt_entries, parsed_entries)):
        if (row.object_id, row.resource_type) != (new_row.object_id, new_row.resource_type):
            raise RebuildError(f"rebuilt Forge TOC identity changed at row {index}")
        if actual_entry != expected_entry:
            raise RebuildError(f"rebuilt Forge entry {index} differs after outer parse")
        if new_row != new_rows[index]:
            raise RebuildError(f"rebuilt Forge row {index} differs after outer parse")
        if row.resource_type:
            parse_typed_entry(actual_entry, row.resource_type, lz4_block)

    atomic_write(output_path, output)
    written = snapshot(output_path)
    if written["sha256"] != sha256_bytes(output):
        raise RebuildError("committed output hash differs from in-memory output")
    after = snapshot(input_path)
    if before != after:
        raise RebuildError("input changed during rebuild")

    report = {
        "schema": "bfr-forge-v50-patch-rebuild/v1",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "PASS",
        "input": before,
        "input_unchanged": True,
        "output": {**written, "path": relative(output_path)},
        "settings": {
            "reencode_all_typed_entries": args.reencode_all,
            "alignment": args.alignment,
            "compression_field": LZ4_FIELD,
            "layout": "BMS0 TOC-mode; BMS1 default-mode",
        },
        "replacements": [
            {
                "object_id": hex64(object_id),
                "path": replacement_paths[object_id],
                "size": len(replacements[object_id]),
                "sha256": sha256_bytes(replacements[object_id]),
            }
            for object_id in sorted(replacements)
        ],
        "outer_verification": {
            "entry_count": len(parsed_rows),
            "object_ids_preserved": True,
            "resource_types_preserved": True,
            "entry_payloads_reopened": True,
            "typed_assets_redecoded": True,
            "replacement_bytes_exact_after_redecode": True,
            "untyped_entries_copied_exactly": True,
        },
        "entries": entry_reports,
    }
    report_path = args.report.resolve()
    atomic_write(report_path, json.dumps(report, indent=2, ensure_ascii=True).encode("utf-8") + b"\n")
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument(
        "--replace",
        action="append",
        default=[],
        metavar="OBJECT_ID=PATH",
        help="replace one decoded resource; may be repeated",
    )
    parser.add_argument(
        "--reencode-all",
        action="store_true",
        help="re-encode typed entries even when they contain no replacement",
    )
    parser.add_argument("--alignment", type=int, default=DEFAULT_ALIGNMENT)
    return parser.parse_args()


def main() -> int:
    try:
        report = run(parse_args())
    except (OSError, ValueError, struct.error, RebuildError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"PASS: wrote {report['output']['path']} ({report['output']['size']} bytes, "
        f"SHA-256 {report['output']['sha256']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
