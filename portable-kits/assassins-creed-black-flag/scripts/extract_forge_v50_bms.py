#!/usr/bin/env python3
"""Read-only Forge v50 BMS extractor for the pinned reference patch.

The extractor understands both BMS layouts observed in Anvil containers:

* TOC mode: a chunk count and a decoded/stored-size table.
* Default mode: a sequence of raw or compressed chunk records.

Compression field 4 is decoded as raw LZ4. Field 8 is decoded with the
AnvilToolkit-bundled oo2core v9 DLL and independently checked with its bundled
v7 DLL. The unrelated ``tools/codec`` directory is never searched or loaded.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import os
import struct
import sys
import zlib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


WORKSPACE = Path(__file__).resolve().parent.parent
OODLE_LIBS: Path | None = None
DEFAULT_INPUT = (
    WORKSPACE
    / "work"
    / "reference_extraction"
    / "input"
    / "DataPC_boot_patch_02.forge"
)
DEFAULT_OUTPUT = WORKSPACE / "work" / "reference_extraction" / "decoded_bms"
DEFAULT_JSON = WORKSPACE / "work" / "reports" / "reference_forge_v50_bms_extraction.json"
DEFAULT_MARKDOWN = WORKSPACE / "work" / "reports" / "reference_forge_v50_bms_extraction.md"

FORGE_HEADER = struct.Struct("<8sBIQQQ")
FAT_HEADER = struct.Struct("<IQ8s")
FAT_ROW = struct.Struct("<QQII")
BMS_HEADER = struct.Struct("<QHBI")
BMS_MAGIC = 0x1004FA9957FBAA33
BUNDLE_RECORD = struct.Struct("<QI6s")
BUNDLE_RECORD_HEADER = struct.Struct("<QIIH")

RESOURCE_TYPES = {
    0x22ECBE63: "BuildTable",
    0x85C817C3: "Material",
    0xD70E6670: "TextureSet",
    0xA2B7E917: "TextureMap",
    0x415D9568: "Mesh",
    0x24AECB7C: "Skeleton",
    0xBCFB3C7A: "MaterialTemplate",
    0x51DC6B80: "LODSelector",
}

PINNED_OODLE = {
    9: {
        "relative_path": "tools/AnvilToolkit-1.3.6/Libs/oo2core_9_win64.dll",
        "sha256": "D484C81158B4E6EDB593DE75B1573992E304B008C133C62E7D383EACFD3DA995",
    },
    7: {
        "relative_path": "tools/AnvilToolkit-1.3.6/Libs/oo2core_7_win64.dll",
        "sha256": "02FBF4C1E39DC3CCAA616226F0B6237AD7BCE9FDD8FE29D77BC7ECD9C37C738E",
    },
}


class ExtractError(RuntimeError):
    pass


class Validation:
    def __init__(self) -> None:
        self.checks: list[dict[str, Any]] = []

    def require(self, name: str, condition: bool, detail: str) -> None:
        self.checks.append({"name": name, "ok": bool(condition), "detail": detail})
        if not condition:
            raise ExtractError(f"{name}: {detail}")

    def result(self) -> dict[str, Any]:
        passed = sum(1 for check in self.checks if check["ok"])
        return {
            "all_passed": passed == len(self.checks),
            "passed": passed,
            "total": len(self.checks),
            "checks": self.checks,
        }


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def file_snapshot(path: Path) -> dict[str, Any]:
    stat = path.stat()
    return {
        "size": stat.st_size,
        "mtime_ns": stat.st_mtime_ns,
        "sha256": sha256(path.read_bytes()),
    }


def hex64(value: int) -> str:
    return f"0x{value:016X}"


def hex32(value: int) -> str:
    return f"0x{value:08X}"


def relative(path: Path) -> str:
    try:
        return path.resolve().relative_to(WORKSPACE).as_posix()
    except ValueError:
        return str(path.resolve())


def atomic_write_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    os.replace(temporary, path)


def load_lz4() -> tuple[Any, str]:
    try:
        import lz4.block  # type: ignore[import-not-found]
    except ImportError as error:
        raise ExtractError("Install lz4 with the selected Python interpreter") from error
    return lz4.block, str(Path(lz4.block.__file__).resolve())


class OodleRuntime:
    """Pinned two-version Oodle decoder with deterministic cross-checking."""

    def __init__(self, validation: Validation) -> None:
        if os.name != "nt":
            raise ExtractError("Oodle runtime requires 64-bit Windows")
        self.validation = validation
        self.libraries: dict[int, Any] = {}
        self.metadata: dict[str, Any] = {}
        for version in (9, 7):
            pin = PINNED_OODLE[version]
            if OODLE_LIBS is None:
                raise ExtractError("Field 8 requires --oodle-libs with the pinned v7/v9 DLLs")
            path = (OODLE_LIBS / Path(pin["relative_path"]).name).resolve()
            validation.require(
                f"oodle.v{version}.inside_trusted_libs",
                path.parent == OODLE_LIBS.resolve(),
                str(path),
            )
            validation.require(f"oodle.v{version}.exists", path.is_file(), str(path))
            actual_hash = sha256(path.read_bytes())
            validation.require(
                f"oodle.v{version}.pinned_sha256",
                actual_hash == pin["sha256"],
                actual_hash,
            )
            library = ctypes.WinDLL(str(path))  # type: ignore[attr-defined]
            self._configure(library)
            self.libraries[version] = library
            self.metadata[str(version)] = {
                "path": relative(path),
                "size": path.stat().st_size,
                "sha256": actual_hash,
            }

    @staticmethod
    def _configure(library: Any) -> None:
        decompress = library.OodleLZ_Decompress
        decompress.argtypes = [
            ctypes.c_void_p,
            ctypes.c_longlong,
            ctypes.c_void_p,
            ctypes.c_longlong,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_ulonglong,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
            ctypes.c_uint,
        ]
        decompress.restype = ctypes.c_longlong
        compress = library.OodleLZ_Compress
        compress.argtypes = [
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
            ctypes.c_void_p,
        ]
        compress.restype = ctypes.c_longlong

    def _decode(self, version: int, encoded: bytes, decoded_size: int) -> bytes:
        source = ctypes.create_string_buffer(encoded)
        destination = ctypes.create_string_buffer(decoded_size)
        result = self.libraries[version].OodleLZ_Decompress(
            source,
            len(encoded),
            destination,
            decoded_size,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            0,
            3,
        )
        if result != decoded_size:
            raise ExtractError(
                f"oo2core v{version} returned {result}, expected {decoded_size}"
            )
        return destination.raw[:decoded_size]

    def decode_cross_checked(self, encoded: bytes, decoded_size: int) -> bytes:
        primary = self._decode(9, encoded, decoded_size)
        secondary = self._decode(7, encoded, decoded_size)
        if primary != secondary:
            raise ExtractError("oo2core v9 and v7 decoded different bytes")
        return primary

    def _compress(self, version: int, source_data: bytes) -> bytes:
        source = ctypes.create_string_buffer(source_data)
        capacity = len(source_data) + 274 * ((len(source_data) + 262143) // 262144)
        destination = ctypes.create_string_buffer(capacity)
        # Oodle compressor 8 is Kraken; level 4 is Normal.
        result = self.libraries[version].OodleLZ_Compress(
            8, source, len(source_data), destination, 4, None, None, None, None, None
        )
        if result <= 0 or result > capacity:
            raise ExtractError(f"oo2core v{version} self-test compression returned {result}")
        return destination.raw[:result]

    def self_test(self) -> dict[str, Any]:
        source = (b"ForgeV50 Oodle cross version self test\x00" * 4096) + (
            bytes(range(256)) * 128
        )
        rows: list[dict[str, Any]] = []
        encoded_by_version: dict[int, bytes] = {}
        for encoder in (9, 7):
            encoded = self._compress(encoder, source)
            encoded_by_version[encoder] = encoded
            decodes: list[dict[str, Any]] = []
            for decoder in (9, 7):
                decoded = self._decode(decoder, encoded, len(source))
                exact = decoded == source
                self.validation.require(
                    f"oodle.self_test.encode_v{encoder}.decode_v{decoder}",
                    exact,
                    f"decoded_sha256={sha256(decoded)}",
                )
                decodes.append(
                    {
                        "decoder_version": decoder,
                        "decoded_size": len(decoded),
                        "decoded_sha256": sha256(decoded),
                        "exact": exact,
                    }
                )
            rows.append(
                {
                    "encoder_version": encoder,
                    "encoded_size": len(encoded),
                    "encoded_sha256": sha256(encoded),
                    "decodes": decodes,
                }
            )
        self.validation.require(
            "oodle.self_test.encoders_match",
            encoded_by_version[9] == encoded_by_version[7],
            "v9 and v7 produced identical deterministic Kraken output",
        )
        return {
            "source_size": len(source),
            "source_sha256": sha256(source),
            "format": "Kraken",
            "compression_level": "Normal",
            "runs": rows,
        }


def decode_chunk(
    codec: int,
    encoded: bytes,
    decoded_size: int,
    lz4_block: Any,
    oodle: OodleRuntime,
) -> tuple[bytes, str, list[int]]:
    if len(encoded) == decoded_size:
        return encoded, "raw", []
    if codec == 4:
        try:
            decoded = lz4_block.decompress(encoded, uncompressed_size=decoded_size)
        except Exception as error:
            raise ExtractError(f"LZ4 decode failed: {error}") from error
        return decoded, "lz4", []
    if codec == 8:
        return oodle.decode_cross_checked(encoded, decoded_size), "oodle-v9-v7", [9, 7]
    raise ExtractError(f"unsupported compressed BMS field {codec}")


def parse_bms(
    entry: bytes,
    start: int,
    expected_decoded_size: int | None,
    lz4_block: Any,
    oodle: OodleRuntime,
    validation: Validation,
    label: str,
) -> tuple[dict[str, Any], bytes, int]:
    validation.require(f"{label}.header_bounds", start + BMS_HEADER.size <= len(entry), str(start))
    magic, version, codec, block_size_raw = BMS_HEADER.unpack_from(entry, start)
    validation.require(f"{label}.magic", magic == BMS_MAGIC, hex64(magic))
    toc_mode = bool(block_size_raw & 0x80000000)
    nominal_block_size = block_size_raw & 0x7FFFFFFF
    validation.require(
        f"{label}.nominal_block_size",
        nominal_block_size > 0,
        str(nominal_block_size),
    )
    cursor = start + BMS_HEADER.size
    descriptors: list[tuple[bool, int, int, int | None, int]] = []
    if toc_mode:
        validation.require(f"{label}.count_bounds", cursor + 4 <= len(entry), str(cursor))
        count = struct.unpack_from("<i", entry, cursor)[0]
        cursor += 4
        validation.require(f"{label}.chunk_count", 0 < count <= 1_000_000, str(count))
        table_end = cursor + count * 8
        validation.require(f"{label}.table_bounds", table_end <= len(entry), str(table_end))
        sizes = [struct.unpack_from("<ii", entry, cursor + index * 8) for index in range(count)]
        cursor = table_end
        for index, (decoded_size, stored_size) in enumerate(sizes):
            validation.require(
                f"{label}.chunk_{index}.positive_sizes",
                decoded_size > 0 and stored_size > 0,
                f"decoded={decoded_size}, stored={stored_size}",
            )
            validation.require(f"{label}.chunk_{index}.checksum_bounds", cursor + 4 <= len(entry), str(cursor))
            checksum = struct.unpack_from("<I", entry, cursor)[0]
            cursor += 4
            descriptors.append((stored_size != decoded_size, stored_size, decoded_size, checksum, cursor))
            cursor += stored_size
            validation.require(f"{label}.chunk_{index}.stored_bounds", cursor <= len(entry), str(cursor))
    else:
        decoded_total = 0
        index = 0
        while cursor < len(entry):
            if expected_decoded_size is not None and decoded_total == expected_decoded_size:
                break
            flag = entry[cursor]
            cursor += 1
            validation.require(f"{label}.chunk_{index}.flag", flag in (0, 1), str(flag))
            if flag:
                validation.require(f"{label}.chunk_{index}.header_bounds", cursor + 12 <= len(entry), str(cursor))
                stored_size, decoded_size, checksum = struct.unpack_from("<iiI", entry, cursor)
                cursor += 12
            else:
                validation.require(f"{label}.chunk_{index}.header_bounds", cursor + 4 <= len(entry), str(cursor))
                stored_size = struct.unpack_from("<i", entry, cursor)[0]
                cursor += 4
                decoded_size = stored_size
                checksum = None
            validation.require(
                f"{label}.chunk_{index}.positive_sizes",
                stored_size > 0 and decoded_size > 0,
                f"decoded={decoded_size}, stored={stored_size}",
            )
            payload_offset = cursor
            cursor += stored_size
            validation.require(f"{label}.chunk_{index}.stored_bounds", cursor <= len(entry), str(cursor))
            descriptors.append((bool(flag), stored_size, decoded_size, checksum, payload_offset))
            decoded_total += decoded_size
            validation.require(
                f"{label}.chunk_{index}.decoded_not_over_expected",
                expected_decoded_size is None or decoded_total <= expected_decoded_size,
                f"decoded_total={decoded_total}, expected={expected_decoded_size}",
            )
            index += 1

    decoded_parts: list[bytes] = []
    chunks: list[dict[str, Any]] = []
    for index, (compressed, stored_size, decoded_size, checksum, payload_offset) in enumerate(descriptors):
        stored = entry[payload_offset : payload_offset + stored_size]
        actual_checksum = zlib.adler32(stored, 0) & 0xFFFFFFFF
        if checksum is not None:
            validation.require(
                f"{label}.chunk_{index}.stored_adler32",
                actual_checksum == checksum,
                f"stored={hex32(checksum)}, computed={hex32(actual_checksum)}",
            )
        decoded, storage, decoder_versions = decode_chunk(codec, stored, decoded_size, lz4_block, oodle)
        validation.require(
            f"{label}.chunk_{index}.decoded_size",
            len(decoded) == decoded_size,
            f"decoded={len(decoded)}, expected={decoded_size}",
        )
        decoded_parts.append(decoded)
        chunks.append(
            {
                "index": index,
                "compressed_flag": compressed,
                "stored_offset_in_entry": payload_offset,
                "stored_size": stored_size,
                "decoded_size": decoded_size,
                "storage": storage,
                "decoder_versions": decoder_versions,
                "stored_adler32": hex32(actual_checksum),
                "stored_checksum_present": checksum is not None,
                "stored_sha256": sha256(stored),
                "decoded_sha256": sha256(decoded),
            }
        )
    decoded_data = b"".join(decoded_parts)
    if expected_decoded_size is not None:
        validation.require(
            f"{label}.expected_decoded_size",
            len(decoded_data) == expected_decoded_size,
            f"decoded={len(decoded_data)}, expected={expected_decoded_size}",
        )
    return (
        {
            "offset_in_entry": start,
            "format_version": version,
            "compression_field": codec,
            "toc_mode": toc_mode,
            "block_size_raw": hex32(block_size_raw),
            "nominal_block_size": nominal_block_size,
            "chunk_count": len(chunks),
            "chunks": chunks,
            "stored_size_consumed": cursor - start,
            "decoded_size": len(decoded_data),
            "decoded_sha256": sha256(decoded_data),
        },
        decoded_data,
        cursor,
    )


def parse_bundle_index(data: bytes, validation: Validation, label: str) -> dict[str, Any]:
    validation.require(f"{label}.count_bounds", len(data) >= 2, str(len(data)))
    count = struct.unpack_from("<H", data, 0)[0]
    assets = []
    cursor = 2
    for index in range(count):
        validation.require(
            f"{label}.asset_{index}.record_bounds",
            cursor + BUNDLE_RECORD_HEADER.size <= len(data),
            f"cursor={cursor}, total={len(data)}",
        )
        object_id, decoded_size, auxiliary_size, reserved = BUNDLE_RECORD_HEADER.unpack_from(
            data, cursor
        )
        cursor += BUNDLE_RECORD_HEADER.size
        validation.require(
            f"{label}.asset_{index}.decoded_size", decoded_size > 0, str(decoded_size)
        )
        validation.require(
            f"{label}.asset_{index}.auxiliary_bounds",
            cursor + auxiliary_size <= len(data),
            f"cursor={cursor}, auxiliary={auxiliary_size}, total={len(data)}",
        )
        auxiliary = data[cursor : cursor + auxiliary_size]
        cursor += auxiliary_size
        assets.append(
            {
                "index": index,
                "object_id": hex64(object_id),
                "decoded_size": decoded_size,
                "reserved_hex": struct.pack("<IH", auxiliary_size, reserved).hex().upper(),
                "auxiliary_size": auxiliary_size,
                "auxiliary_reserved": reserved,
                "auxiliary_sha256": sha256(auxiliary),
                "auxiliary_hex": auxiliary.hex().upper(),
                "auxiliary_u64": [
                    hex64(struct.unpack_from("<Q", auxiliary, offset)[0])
                    for offset in range(0, len(auxiliary), 8)
                ]
                if len(auxiliary) % 8 == 0
                else [],
            }
        )
    suffix = data[cursor:]
    return {
        "asset_count": count,
        "assets": assets,
        "asset_decoded_size_total": sum(asset["decoded_size"] for asset in assets),
        "records_size": cursor - 2,
        "opaque_suffix_size": len(suffix),
        "opaque_suffix_sha256": sha256(suffix),
    }


def write_output(path: Path, data: bytes, validation: Validation, label: str) -> dict[str, Any]:
    atomic_write_bytes(path, data)
    readback = path.read_bytes()
    validation.require(f"{label}.readback", readback == data, relative(path))
    return {"path": relative(path), "size": len(data), "sha256": sha256(data)}


def parse_resource_header(
    data: bytes,
    expected_object_id: int,
    validation: Validation,
    label: str,
) -> dict[str, Any]:
    validation.require(f"{label}.header_bounds", len(data) >= 25, str(len(data)))
    wrapper_type = struct.unpack_from("<I", data, 0)[0]
    declared_body_size = struct.unpack_from("<Q", data, 4)[0]
    wrapper_flag = data[12]
    class_id = struct.unpack_from("<Q", data, 13)[0]
    embedded_type = struct.unpack_from("<I", data, 21)[0]
    validation.require(
        f"{label}.declared_body_size",
        declared_body_size == len(data) - 13,
        f"declared={declared_body_size}, actual={len(data) - 13}",
    )
    validation.require(
        f"{label}.wrapper_flag", wrapper_flag == 0, f"value={wrapper_flag}"
    )
    validation.require(
        f"{label}.class_id",
        class_id == expected_object_id,
        f"embedded={hex64(class_id)}, expected={hex64(expected_object_id)}",
    )
    validation.require(
        f"{label}.type_hash_match",
        wrapper_type == embedded_type,
        f"wrapper={hex32(wrapper_type)}, embedded={hex32(embedded_type)}",
    )
    type_name = RESOURCE_TYPES.get(wrapper_type, "Unknown")
    validation.require(
        f"{label}.known_type",
        type_name != "Unknown",
        f"type={hex32(wrapper_type)}",
    )
    return {
        "wrapper_type_hash": hex32(wrapper_type),
        "type_name": type_name,
        "declared_body_size": declared_body_size,
        "wrapper_flag": wrapper_flag,
        "class_id": hex64(class_id),
        "embedded_type_hash": hex32(embedded_type),
        "class_payload_offset": 25,
    }


def add_known_asset_references(entries: list[dict[str, Any]]) -> dict[str, int]:
    assets = [asset for entry in entries for asset in entry["assets"]]
    known_ids = {int(asset["object_id"], 16): asset for asset in assets}
    type_counts: dict[str, int] = {}
    for asset in assets:
        type_name = asset["resource_header"]["type_name"]
        type_counts[type_name] = type_counts.get(type_name, 0) + 1
        path = WORKSPACE / asset["output"]["path"]
        data = path.read_bytes()
        source_id = int(asset["object_id"], 16)
        references: list[dict[str, Any]] = []
        self_offsets: list[int] = []
        for target_id, target_asset in known_ids.items():
            needle = struct.pack("<Q", target_id)
            offsets: list[int] = []
            cursor = 0
            while True:
                cursor = data.find(needle, cursor)
                if cursor < 0:
                    break
                offsets.append(cursor)
                cursor += 1
            if target_id == source_id:
                self_offsets = [offset for offset in offsets if offset != 13]
            elif offsets:
                references.append(
                    {
                        "object_id": hex64(target_id),
                        "type_name": target_asset["resource_header"]["type_name"],
                        "offsets": offsets,
                        "occurrences": len(offsets),
                    }
                )
        asset["known_asset_references"] = references
        asset["self_reference_offsets_excluding_header"] = self_offsets
    return type_counts


def extract_forge(
    input_path: Path,
    output_root: Path,
    lz4_block: Any,
    oodle: OodleRuntime,
    validation: Validation,
) -> dict[str, Any]:
    data = input_path.read_bytes()
    validation.require("forge.header_bounds", len(data) >= FORGE_HEADER.size, str(len(data)))
    magic, separator, version, fat_offset, global_id, flags = FORGE_HEADER.unpack_from(data, 0)
    validation.require("forge.magic", magic == b"scimitar", repr(magic))
    validation.require("forge.separator", separator == 0, str(separator))
    validation.require("forge.version", version == 50, str(version))
    validation.require("forge.fat_bounds", fat_offset + FAT_HEADER.size <= len(data), str(fat_offset))
    entry_count, toc_offset, sentinel = FAT_HEADER.unpack_from(data, fat_offset)
    validation.require("forge.sentinel", sentinel == b"\xFF" * 8, sentinel.hex())
    validation.require("forge.toc_bounds", toc_offset + entry_count * FAT_ROW.size <= len(data), str(toc_offset))

    entries: list[dict[str, Any]] = []
    asset_count = 0
    bms_count = 0
    codec_usage: dict[str, dict[str, int]] = {}
    for index in range(entry_count):
        row = toc_offset + index * FAT_ROW.size
        offset, object_id, stored_size, resource_type = FAT_ROW.unpack_from(data, row)
        end = offset + stored_size
        validation.require(f"entry_{index}.bounds", fat_offset + FAT_HEADER.size <= offset <= end <= toc_offset, f"{offset}:{end}")
        stored_entry = data[offset:end]
        record: dict[str, Any] = {
            "index": index,
            "object_id": hex64(object_id),
            "resource_type": hex32(resource_type),
            "offset": offset,
            "stored_size": stored_size,
            "stored_sha256": sha256(stored_entry),
            "typed": resource_type != 0,
            "bms_blocks": [],
            "assets": [],
        }
        if resource_type == 0 or len(stored_entry) < BMS_HEADER.size or struct.unpack_from("<Q", stored_entry, 0)[0] != BMS_MAGIC:
            record["status"] = "no_reachable_bms"
            entries.append(record)
            continue

        entry_dir = output_root / f"entry_{index:03d}_{object_id:016X}"
        first, first_decoded, cursor = parse_bms(
            stored_entry, 0, None, lz4_block, oodle, validation, f"entry_{index}.bms_0"
        )
        first["output"] = write_output(
            entry_dir / "bms_0_bundle_index.bin",
            first_decoded,
            validation,
            f"entry_{index}.bms_0.output",
        )
        bundle = parse_bundle_index(first_decoded, validation, f"entry_{index}.bundle_index")
        first["bundle_index"] = bundle
        record["bms_blocks"].append(first)
        bms_count += 1

        validation.require(
            f"entry_{index}.second_bms_present",
            cursor + 8 <= len(stored_entry) and struct.unpack_from("<Q", stored_entry, cursor)[0] == BMS_MAGIC,
            f"cursor={cursor}, entry_size={len(stored_entry)}",
        )
        second, payload, cursor = parse_bms(
            stored_entry,
            cursor,
            bundle["asset_decoded_size_total"],
            lz4_block,
            oodle,
            validation,
            f"entry_{index}.bms_1",
        )
        second["output"] = write_output(
            entry_dir / "bms_1_resource_payload.bin",
            payload,
            validation,
            f"entry_{index}.bms_1.output",
        )
        record["bms_blocks"].append(second)
        bms_count += 1
        validation.require(
            f"entry_{index}.bms_consumes_entry",
            cursor == len(stored_entry),
            f"consumed={cursor}, entry_size={len(stored_entry)}",
        )

        payload_cursor = 0
        for asset in bundle["assets"]:
            asset_end = payload_cursor + asset["decoded_size"]
            validation.require(
                f"entry_{index}.asset_{asset['index']}.bounds",
                asset_end <= len(payload),
                f"{payload_cursor}:{asset_end}",
            )
            asset_data = payload[payload_cursor:asset_end]
            asset_id = int(asset["object_id"], 16)
            resource_header = parse_resource_header(
                asset_data,
                asset_id,
                validation,
                f"entry_{index}.asset_{asset['index']}.resource_header",
            )
            output = write_output(
                entry_dir / f"asset_{asset['index']:03d}_{asset_id:016X}.bin",
                asset_data,
                validation,
                f"entry_{index}.asset_{asset['index']}.output",
            )
            record["assets"].append(
                {
                    **asset,
                    "payload_offset": payload_cursor,
                    "sha256": sha256(asset_data),
                    "prefix_32_hex": asset_data[:32].hex().upper(),
                    "resource_header": resource_header,
                    "output": output,
                }
            )
            payload_cursor = asset_end
            asset_count += 1
        validation.require(
            f"entry_{index}.assets_consume_payload",
            payload_cursor == len(payload),
            f"assets={payload_cursor}, payload={len(payload)}",
        )
        record["status"] = "decoded"

        for bms in record["bms_blocks"]:
            key = str(bms["compression_field"])
            usage = codec_usage.setdefault(key, {"bms_blocks": 0, "raw_chunks": 0, "compressed_chunks": 0})
            usage["bms_blocks"] += 1
            for chunk in bms["chunks"]:
                if chunk["storage"] == "raw":
                    usage["raw_chunks"] += 1
                else:
                    usage["compressed_chunks"] += 1
        entries.append(record)

    type_counts = add_known_asset_references(entries)

    return {
        "header": {
            "magic": magic.decode("ascii"),
            "version": version,
            "fat_offset": fat_offset,
            "global_id": hex64(global_id),
            "flags": hex64(flags),
            "toc_offset": toc_offset,
            "entry_count": entry_count,
        },
        "entries": entries,
        "summary": {
            "typed_entries_decoded": sum(1 for entry in entries if entry["status"] == "decoded"),
            "entries_without_bms": sum(1 for entry in entries if entry["status"] == "no_reachable_bms"),
            "reachable_bms_blocks": bms_count,
            "reachable_assets": asset_count,
            "resource_type_counts": type_counts,
            "codec_usage": codec_usage,
        },
    }


def make_markdown(report: dict[str, Any]) -> str:
    summary = report["forge"]["summary"]
    validation = report["validation"]
    lines = [
        "# Forge v50 BMS Extraction",
        "",
        f"Generated (UTC): `{report['generated_at_utc']}`",
        "",
        "## Result",
        "",
        f"- Validation: `{'PASS' if validation['all_passed'] else 'FAIL'}` ({validation['passed']}/{validation['total']})",
        f"- Typed entries decoded: `{summary['typed_entries_decoded']}`",
        f"- Reachable BMS blocks: `{summary['reachable_bms_blocks']}`",
        f"- Reachable assets written: `{summary['reachable_assets']}`",
        f"- Input unchanged: `{'PASS' if report['input']['unchanged']['all'] else 'FAIL'}`",
        "",
        "Codec usage below is measured from this input. Field 4 uses raw LZ4; field 8 requires explicitly supplied pinned Oodle DLLs.",
        "",
        "TOC mode and default mode are parsed separately. This report makes no GUI or game-runtime claim.",
        "",
        "## Codec Usage",
        "",
        "| Field | BMS blocks | Raw chunks | Compressed chunks | Decoder |",
        "|---:|---:|---:|---:|---|",
    ]
    for field, usage in sorted(summary["codec_usage"].items(), key=lambda item: int(item[0])):
        decoder = "LZ4 raw block" if field == "4" else "oo2core v9 + v7"
        lines.append(
            f"| {field} | {usage['bms_blocks']} | {usage['raw_chunks']} | {usage['compressed_chunks']} | {decoder} |"
        )
    lines.extend(
        [
            "",
            "## Decoded Assets",
            "",
            "| Entry | Asset | Object ID | Type | Bytes | Known in-patch references | SHA-256 |",
            "|---:|---:|---:|---|---:|---|---|",
        ]
    )
    for entry in report["forge"]["entries"]:
        for asset in entry["assets"]:
            references = ", ".join(
                reference["object_id"] for reference in asset["known_asset_references"]
            ) or "-"
            lines.append(
                f"| {entry['index']} | {asset['index']} | `{asset['object_id']}` | {asset['resource_header']['type_name']} | {asset['decoded_size']} | `{references}` | `{asset['sha256']}` |"
            )
    lines.extend(
        [
            "",
            "Each asset has a verified 13-byte resource envelope: a wrapper type hash, UInt64 body size, zero flag, then an embedded class ID and matching class hash. Known in-patch references are exact little-endian occurrences of another extracted 64-bit object ID. They provide a reproducible dependency candidate graph, but are not claimed as a complete semantic class parse.",
            "",
            "## Oodle Trust Boundary",
            "",
            f"- Loaded DLLs: `{json.dumps(report['oodle']['libraries'], sort_keys=True)}`",
            "- `tools/codec` was not searched or loaded.",
            f"- Codec self-test: `{json.dumps(report['oodle']['self_test'], sort_keys=True)}`",
            "",
            "## Input Integrity",
            "",
            f"- Input: `{report['input']['path']}`",
            f"- Size: `{report['input']['before']['size']}` bytes",
            f"- SHA-256: `{report['input']['before']['sha256']}`",
            f"- Output root: `{report['output_root']}`",
            "",
        ]
    )
    return "\n".join(lines)


def run(input_path: Path, output_root: Path) -> dict[str, Any]:
    input_path = input_path.resolve()
    output_root = output_root.resolve()
    validation = Validation()
    validation.require("input.exists", input_path.is_file(), str(input_path))
    validation.require("output.new_directory", not output_root.exists(), str(output_root))
    before = file_snapshot(input_path)
    lz4_block, lz4_source = load_lz4()
    class LazyOodle:
        metadata: dict[str, Any] = {}
        tests: dict[str, Any] = {"status": "not_needed"}
        runtime: OodleRuntime | None = None

        def decode_cross_checked(self, encoded: bytes, size: int) -> bytes:
            if self.runtime is None:
                self.runtime = OodleRuntime(validation)
                self.tests = self.runtime.self_test()
                self.metadata = self.runtime.metadata
            return self.runtime.decode_cross_checked(encoded, size)

    oodle = LazyOodle()
    forge = extract_forge(input_path, output_root, lz4_block, oodle, validation)
    after = file_snapshot(input_path)
    unchanged = {
        "size": before["size"] == after["size"],
        "mtime_ns": before["mtime_ns"] == after["mtime_ns"],
        "sha256": before["sha256"] == after["sha256"],
    }
    unchanged["all"] = all(unchanged.values())
    validation.require("input.unchanged", unchanged["all"], json.dumps(unchanged, sort_keys=True))
    return {
        "schema": "forge-v50-bms-extraction/v2",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "script": {"path": relative(Path(__file__)), "sha256": sha256(Path(__file__).read_bytes())},
        "input": {"path": relative(input_path), "before": before, "after": after, "unchanged": unchanged},
        "output_root": relative(output_root),
        "dependencies": {"lz4_import_source": lz4_source},
        "oodle": {
            "primary_version": 9,
            "cross_check_version": 7,
            "libraries": oodle.metadata,
            "self_test": oodle.tests,
            "source_field_8_chunks_decoded": sum(
                usage["compressed_chunks"]
                for field, usage in forge["summary"]["codec_usage"].items()
                if field == "8"
            ),
            "standalone_tools_codec_used": False,
        },
        "interpretation": {"scope": "Decoded this input only; no runtime acceptance implied"},
        "forge": forge,
        "validation": validation.result(),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--json-output", type=Path, required=True)
    parser.add_argument("--markdown-output", type=Path, required=True)
    parser.add_argument("--oodle-libs", type=Path, help="Optional pinned v7/v9 DLL directory for field 8")
    return parser.parse_args()


def main() -> int:
    global OODLE_LIBS
    args = parse_args()
    OODLE_LIBS = args.oodle_libs
    try:
        reports = [args.json_output.resolve(), args.markdown_output.resolve()]
        if len(set(reports)) != 2 or any(p.exists() for p in reports):
            raise ExtractError("Reports must have distinct new paths")
        report = run(args.input, args.output_root)
        atomic_write_text(args.json_output.resolve(), json.dumps(report, indent=2, ensure_ascii=True) + "\n")
        atomic_write_text(args.markdown_output.resolve(), make_markdown(report))
        readback = json.loads(args.json_output.resolve().read_text(encoding="utf-8"))
        if readback["input"]["before"]["sha256"] != report["input"]["before"]["sha256"]:
            raise ExtractError("JSON report readback failed")
    except (OSError, ExtractError, ValueError, struct.error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 2
    validation = report["validation"]
    summary = report["forge"]["summary"]
    print(
        f"PASS: {validation['passed']}/{validation['total']} checks; "
        f"{summary['reachable_bms_blocks']} BMS blocks; "
        f"{summary['reachable_assets']} assets; input unchanged"
    )
    print(f"JSON: {args.json_output.resolve()}")
    print(f"Markdown: {args.markdown_output.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
