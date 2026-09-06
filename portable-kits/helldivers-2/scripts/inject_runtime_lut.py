#!/usr/bin/env python3
"""Inject compatible same-ID Piece.MaterialLut textures into one HD2 patch."""

from __future__ import annotations

import argparse
import json
import os
import re
import struct
import uuid
from collections import Counter
from pathlib import Path
from typing import Any

from stingray_archive import (
    ENTRY_SIZE,
    HEADER_SIZE,
    TEXTURE_ID,
    TYPE_ROW_SIZE,
    aligned,
    companion,
    entry_gpu,
    entry_key,
    entry_main,
    entry_stream,
    pack_entry,
    parse_dds_contract,
    rebuild_non_streaming_dds,
    require_valid_archive,
    sha256_bytes,
    sha256_file,
    texture_dds_header,
)


KNOWN_ARMOR_LUT = {
    "width": 23,
    "height": 8,
    "mipmaps": 5,
    "format_id": 10,
    "array_size": 1,
}
STANDARD_NON_STREAMING_PREFIX = b"\0" * 8 + b"\xff" * 4 + b"\0" * 180


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-patch", required=True, type=Path)
    parser.add_argument("--mapping", required=True, type=Path)
    parser.add_argument("--output-patch", required=True, type=Path)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--dry-run", action="store_true", help="Validate and construct in memory without writing files")
    return parser.parse_args()


def parse_u64(value: Any, field: str) -> int:
    try:
        result = int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not a valid integer: {value!r}") from exc
    if result <= 0 or result > 0xFFFFFFFFFFFFFFFF:
        raise ValueError(f"{field} must be a nonzero unsigned 64-bit value")
    return result


def parse_uint(value: Any, field: str, bits: int) -> int:
    try:
        result = int(value, 0) if isinstance(value, str) else int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field} is not a valid integer: {value!r}") from exc
    if result < 0 or result >= 1 << bits:
        raise ValueError(f"{field} must be an unsigned {bits}-bit value")
    return result


def resolve_mapping_path(mapping_path: Path, value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (mapping_path.parent / path).resolve()


def looks_like_game_destination(path: Path) -> bool:
    normalized = str(path.resolve()).replace("/", "\\").lower()
    return "\\steamapps\\common\\helldivers 2\\" in normalized or normalized.endswith(
        "\\steamapps\\common\\helldivers 2"
    )


def atomic_write_new(path: Path, data: bytes) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    try:
        with temporary.open("xb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def choose_texture_template(
    source_data: bytes,
    source_entries: list[dict[str, int]],
    source_dds: bytes,
) -> tuple[dict[str, int], list[bytes]]:
    textures = [row for row in source_entries if row["type_id"] == TEXTURE_ID]
    if not textures:
        raise ValueError("source patch has no Texture type group")
    matching = []
    for row in textures:
        main = entry_main(source_data, row)
        if row["stream_size"] != 0 or row["gpu_size"] != len(source_dds) - 148 or len(main) < 340:
            continue
        try:
            if texture_dds_header(main) == source_dds[:148]:
                matching.append(row)
        except ValueError:
            continue
    return (matching[0] if matching else textures[0]), [entry_main(source_data, row)[:192] for row in matching]


def select_prefix(target: dict[str, Any], inferred_prefixes: list[bytes]) -> bytes:
    if "texture_info_prefix_hex" in target:
        prefix = bytes.fromhex(str(target["texture_info_prefix_hex"]))
        if len(prefix) != 192:
            raise ValueError("texture_info_prefix_hex must decode to exactly 192 bytes")
        return prefix
    unique = {prefix for prefix in inferred_prefixes}
    if len(unique) == 1:
        return next(iter(unique))
    if target.get("allow_standard_non_streaming_prefix") is True:
        return STANDARD_NON_STREAMING_PREFIX
    raise ValueError(
        "could not infer one TextureInfo prefix; provide texture_info_prefix_hex or explicitly allow the standard non-streaming prefix"
    )


def metadata_value(target: dict[str, Any], name: str, fallback: int) -> int:
    metadata = target.get("entry_metadata", {})
    if name not in metadata:
        return fallback
    bits = 64 if name in {"unknown_1", "unknown_2"} else 32
    return parse_uint(metadata[name], f"entry_metadata.{name}", bits)


def validate_source_hashes(mapping: dict[str, Any], source: Path) -> dict[str, str]:
    hashes = {
        "patch": sha256_file(source),
        "gpu_resources": sha256_file(companion(source, ".gpu_resources")),
        "stream": sha256_file(companion(source, ".stream")),
    }
    expected = mapping.get("expected_source_hashes")
    if expected:
        normalized = {name: str(expected[name]).lower() for name in hashes}
        if hashes != normalized:
            raise ValueError(f"source triplet hashes differ from mapping: got {hashes}, expected {normalized}")
    return hashes


def validate_mapping_identity(mapping: dict[str, Any]) -> tuple[str, str]:
    if mapping.get("schema") != "hd2-runtime-material-lut-map-v1":
        raise ValueError("mapping schema must be hd2-runtime-material-lut-map-v1")
    armor_kit = mapping.get("armor_kit")
    if not isinstance(armor_kit, str) or not armor_kit.strip():
        raise ValueError("mapping must identify armor_kit")
    snapshot_hash = mapping.get("armor_set_snapshot_sha256")
    if not isinstance(snapshot_hash, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", snapshot_hash):
        raise ValueError("mapping must contain the current armor_set_snapshot_sha256")
    return armor_kit.strip(), snapshot_hash.lower()


def main() -> None:
    args = parse_args()
    source = args.source_patch.resolve()
    mapping_path = args.mapping.resolve()
    output = args.output_patch.resolve()
    report_path = (args.report or Path(f"{output}.runtime_lut_report.json")).resolve()
    source_gpu_path = companion(source, ".gpu_resources")
    source_stream_path = companion(source, ".stream")
    output_gpu_path = companion(output, ".gpu_resources")
    output_stream_path = companion(output, ".stream")

    for required in (source, source_gpu_path, source_stream_path, mapping_path):
        if not required.is_file():
            raise FileNotFoundError(required)
    if source == output:
        raise ValueError("refusing to overwrite the source patch")
    if source.parent == output.parent:
        raise ValueError("refusing to write a candidate into the immutable source triplet directory")
    if any(looks_like_game_destination(path) for path in (output, output_gpu_path, output_stream_path, report_path)):
        raise ValueError("refusing to write directly into a Helldivers 2 Steam game directory")
    if not args.dry_run:
        existing = [path for path in (output, output_gpu_path, output_stream_path, report_path) if path.exists()]
        if existing:
            raise FileExistsError("refusing to overwrite outputs: " + ", ".join(str(path) for path in existing))

    mapping = json.loads(mapping_path.read_text(encoding="utf-8"))
    armor_kit, armor_set_snapshot_sha256 = validate_mapping_identity(mapping)
    raw_targets = mapping.get("targets")
    if not isinstance(raw_targets, list) or not raw_targets:
        raise ValueError("mapping must contain a non-empty targets array")

    source_hashes = validate_source_hashes(mapping, source)
    source_data = source.read_bytes()
    source_gpu = source_gpu_path.read_bytes()
    source_stream = source_stream_path.read_bytes()
    source_entries, source_header, source_validation = require_valid_archive(
        source_data, source_gpu, source_stream, "source patch"
    )
    source_map = {entry_key(row): row for row in source_entries}

    targets: list[dict[str, Any]] = []
    target_ids: set[int] = set()
    for index, raw in enumerate(raw_targets):
        if not isinstance(raw, dict):
            raise ValueError(f"target {index} must be an object")
        target_id = parse_u64(raw.get("target_id"), f"targets[{index}].target_id")
        if target_id in target_ids:
            raise ValueError(f"duplicate target ID 0x{target_id:016x}")
        target_ids.add(target_id)
        if (TEXTURE_ID, target_id) in source_map:
            raise ValueError(f"source already contains target texture 0x{target_id:016x}; rebuild from an earlier baseline")

        if "target_dds" not in raw or "source_dds" not in raw:
            raise ValueError(f"target 0x{target_id:016x} needs target_dds and source_dds")
        scope = raw.get("scope")
        if not isinstance(scope, str) or not scope.strip():
            raise ValueError(f"target 0x{target_id:016x} needs an exact Piece scope")
        reference_count = raw.get("reference_count")
        if not isinstance(reference_count, int) or reference_count <= 0:
            raise ValueError(f"target 0x{target_id:016x} needs a positive reference_count")
        ownership_value = raw.get("ownership_evidence")
        if not isinstance(ownership_value, str) or not ownership_value.strip():
            raise ValueError(f"target 0x{target_id:016x} needs ownership_evidence")
        ownership_path = resolve_mapping_path(mapping_path, ownership_value)
        if not ownership_path.is_file():
            raise FileNotFoundError(ownership_path)
        target_dds_path = resolve_mapping_path(mapping_path, str(raw["target_dds"]))
        source_dds_path = resolve_mapping_path(mapping_path, str(raw["source_dds"]))
        for required in (target_dds_path, source_dds_path):
            if not required.is_file():
                raise FileNotFoundError(required)

        native_dds = target_dds_path.read_bytes()
        content_dds = source_dds_path.read_bytes()
        native_contract = parse_dds_contract(native_dds)
        content_contract = parse_dds_contract(content_dds)
        if native_contract != content_contract or native_dds[:148] != content_dds[:148]:
            raise ValueError(
                f"DDS ABI mismatch for 0x{target_id:016x}: target={native_contract}, source={content_contract}"
            )
        known_fields = {key: content_contract[key] for key in KNOWN_ARMOR_LUT}
        if not mapping.get("allow_nonstandard_lut_contract") and known_fields != KNOWN_ARMOR_LUT:
            raise ValueError(
                f"0x{target_id:016x} is not the audited Armor LUT contract: {known_fields}; re-audit or set allow_nonstandard_lut_contract explicitly"
            )

        template, inferred_prefixes = choose_texture_template(source_data, source_entries, content_dds)
        prefix = select_prefix(raw, inferred_prefixes)
        new_main = prefix + content_dds[:148]
        if len(new_main) != 340:
            raise AssertionError("runtime LUT main payload is not 340 bytes")

        row = template.copy()
        row.update(
            {
                "file_id": target_id,
                "stream_offset": 0,
                "stream_size": 0,
                "toc_size": len(new_main),
                "gpu_size": len(content_dds) - 148,
                "unknown_1": metadata_value(raw, "unknown_1", template["unknown_1"]),
                "unknown_2": metadata_value(raw, "unknown_2", template["unknown_2"]),
                "unknown_3": metadata_value(raw, "unknown_3", template["unknown_3"]),
                "unknown_4": metadata_value(raw, "unknown_4", template["unknown_4"]),
                "index": 0,
            }
        )
        targets.append(
            {
                "id": target_id,
                "raw": raw,
                "native_path": target_dds_path,
                "source_path": source_dds_path,
                "native_dds": native_dds,
                "content_dds": content_dds,
                "contract": content_contract,
                "main": new_main,
                "row": row,
                "template_file_id": template["file_id"],
                "scope": scope.strip(),
                "reference_count": reference_count,
                "ownership_path": ownership_path,
            }
        )

    header_delta = ENTRY_SIZE * len(targets)
    main_cursor = len(source_data) + header_delta
    output_gpu = bytearray(source_gpu)
    for target in targets:
        row = target["row"]
        row["toc_offset"] = main_cursor
        main_cursor += len(target["main"])
        row["gpu_offset"] = aligned(len(output_gpu))
        output_gpu.extend(b"\0" * (row["gpu_offset"] - len(output_gpu)))
        output_gpu.extend(target["content_dds"][148:])

    texture_positions = [index for index, row in enumerate(source_entries) if row["type_id"] == TEXTURE_ID]
    if not texture_positions:
        raise ValueError("source patch has no texture group")
    last_texture = texture_positions[-1]
    rows: list[dict[str, int]] = []
    for position, source_row in enumerate(source_entries):
        copied = source_row.copy()
        copied["toc_offset"] += header_delta
        rows.append(copied)
        if position == last_texture:
            rows.extend(target["row"].copy() for target in targets)
    for index, row in enumerate(rows, 1):
        row["index"] = index

    fixed_header = bytearray(source_data[:HEADER_SIZE])
    struct.pack_into("<I", fixed_header, 8, len(rows))
    type_table_size = int(source_header["num_types"]) * TYPE_ROW_SIZE
    type_table = bytearray(source_data[HEADER_SIZE : HEADER_SIZE + type_table_size])
    texture_type_rows = []
    for index in range(int(source_header["num_types"])):
        offset = index * TYPE_ROW_SIZE
        type_id = struct.unpack_from("<Q", type_table, offset + 8)[0]
        if type_id == TEXTURE_ID:
            old_count = struct.unpack_from("<Q", type_table, offset + 16)[0]
            struct.pack_into("<Q", type_table, offset + 16, old_count + len(targets))
            texture_type_rows.append(index)
    if len(texture_type_rows) != 1:
        raise ValueError(f"expected exactly one Texture type row, found {texture_type_rows}")

    header = bytearray(fixed_header)
    header.extend(type_table)
    for row in rows:
        header.extend(pack_entry(row))
    expected_header_end = int(source_header["header_end"]) + header_delta
    if len(header) != expected_header_end:
        raise AssertionError("candidate header length mismatch")

    output_data = bytearray(header)
    output_data.extend(source_data[int(source_header["header_end"]) :])
    for target in targets:
        output_data.extend(target["main"])
    output_stream = source_stream

    candidate_entries, candidate_header, candidate_validation = require_valid_archive(
        bytes(output_data), bytes(output_gpu), output_stream, "candidate patch"
    )
    candidate_map = {entry_key(row): row for row in candidate_entries}
    expected_keys = set(source_map) | {(TEXTURE_ID, target["id"]) for target in targets}
    if set(candidate_map) != expected_keys:
        raise AssertionError("candidate resource-key set differs from baseline plus targets")

    unchanged_rows = []
    unchanged_passed = True
    for key, before_row in source_map.items():
        after_row = candidate_map[key]
        main_equal = entry_main(source_data, before_row) == entry_main(bytes(output_data), after_row)
        gpu_equal = entry_gpu(source_gpu, before_row) == entry_gpu(bytes(output_gpu), after_row)
        stream_equal = entry_stream(source_stream, before_row) == entry_stream(output_stream, after_row)
        passed = main_equal and gpu_equal and stream_equal
        unchanged_passed &= passed
        unchanged_rows.append(
            {
                "type_id": f"0x{key[0]:016x}",
                "file_id": f"0x{key[1]:016x}",
                "passed": passed,
            }
        )
    if not unchanged_passed:
        raise AssertionError("one or more baseline resource payloads changed")

    target_reports = []
    for target in targets:
        row = candidate_map[(TEXTURE_ID, target["id"])]
        main = entry_main(bytes(output_data), row)
        gpu_payload = entry_gpu(bytes(output_gpu), row)
        stream_payload = entry_stream(output_stream, row)
        rebuilt = rebuild_non_streaming_dds(main, gpu_payload, stream_payload)
        passed = rebuilt == target["content_dds"]
        if not passed:
            raise AssertionError(f"target 0x{target['id']:016x} did not reconstruct to its source DDS")
        target_reports.append(
            {
                "target_id": f"0x{target['id']:016x}",
                "scope": target["scope"],
                "reference_count": target["reference_count"],
                "ownership_evidence": str(target["ownership_path"]),
                "target_dds": str(target["native_path"]),
                "source_dds": str(target["source_path"]),
                "contract": target["contract"],
                "native_dds_sha256": sha256_bytes(target["native_dds"]),
                "source_dds_sha256": sha256_bytes(target["content_dds"]),
                "candidate_dds_sha256": sha256_bytes(rebuilt),
                "main_sha256": sha256_bytes(main),
                "gpu_sha256": sha256_bytes(gpu_payload),
                "toc_index": row["index"],
                "gpu_offset": row["gpu_offset"],
                "entry_metadata": {
                    "template_file_id": f"0x{target['template_file_id']:016x}",
                    "unknown_1": row["unknown_1"],
                    "unknown_2": row["unknown_2"],
                    "unknown_3": row["unknown_3"],
                    "unknown_4": row["unknown_4"],
                },
                "passed": passed,
            }
        )

    source_counts = Counter(row["type_id"] for row in source_entries)
    candidate_counts = Counter(row["type_id"] for row in candidate_entries)
    if candidate_counts[TEXTURE_ID] != source_counts[TEXTURE_ID] + len(targets):
        raise AssertionError("candidate Texture count mismatch")

    output_hashes = {
        "patch": sha256_bytes(output_data),
        "gpu_resources": sha256_bytes(output_gpu),
        "stream": sha256_bytes(output_stream),
    }
    report = {
        "schema": "hd2-runtime-material-lut-injection-v1",
        "status": "ok",
        "dry_run": bool(args.dry_run),
        "source_patch": str(source),
        "mapping": str(mapping_path),
        "armor_kit": armor_kit,
        "armor_set_snapshot_sha256": armor_set_snapshot_sha256,
        "output_patch": str(output),
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
        "source_validation": source_validation,
        "candidate_validation": candidate_validation,
        "unchanged_baseline_payloads": {"passed": unchanged_passed, "rows": unchanged_rows},
        "targets": target_reports,
        "safety": {
            "target_count": len(targets),
            "source_and_output_directories_distinct": source.parent != output.parent,
            "output_outside_game_directory": not looks_like_game_destination(output),
            "stream_byte_identical": output_stream == source_stream,
        },
    }
    report_bytes = (json.dumps(report, indent=2) + "\n").encode("utf-8")

    if not args.dry_run:
        atomic_write_new(output, bytes(output_data))
        atomic_write_new(output_gpu_path, bytes(output_gpu))
        atomic_write_new(output_stream_path, output_stream)
        atomic_write_new(report_path, report_bytes)

    print(json.dumps({"passed": True, "dry_run": args.dry_run, "output_hashes": output_hashes, "report": str(report_path)}, indent=2))


if __name__ == "__main__":
    main()
