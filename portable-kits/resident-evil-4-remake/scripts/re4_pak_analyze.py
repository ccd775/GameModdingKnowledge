#!/usr/bin/env python3
"""Inspect RE Engine KPKA v4 archives and recover paths from candidates.

This intentionally implements only the small, well-understood subset needed for
mod archives: the v4 header/table and raw DEFLATE entries. It never modifies the
input PAK.
"""

from __future__ import annotations

import argparse
import csv
import struct
import sys
import zlib
from dataclasses import dataclass
from pathlib import Path


SEED = 0xFFFFFFFF


def murmur3_32(data: bytes, seed: int = SEED) -> int:
    c1 = 0xCC9E2D51
    c2 = 0x1B873593
    value = seed
    rounded = len(data) & ~3

    for offset in range(0, rounded, 4):
        block = int.from_bytes(data[offset : offset + 4], "little")
        block = (block * c1) & 0xFFFFFFFF
        block = ((block << 15) | (block >> 17)) & 0xFFFFFFFF
        block = (block * c2) & 0xFFFFFFFF
        value ^= block
        value = ((value << 13) | (value >> 19)) & 0xFFFFFFFF
        value = (value * 5 + 0xE6546B64) & 0xFFFFFFFF

    tail = data[rounded:]
    block = 0
    if len(tail) >= 3:
        block ^= tail[2] << 16
    if len(tail) >= 2:
        block ^= tail[1] << 8
    if tail:
        block ^= tail[0]
        block = (block * c1) & 0xFFFFFFFF
        block = ((block << 15) | (block >> 17)) & 0xFFFFFFFF
        block = (block * c2) & 0xFFFFFFFF
        value ^= block

    value ^= len(data)
    value ^= value >> 16
    value = (value * 0x85EBCA6B) & 0xFFFFFFFF
    value ^= value >> 13
    value = (value * 0xC2B2AE35) & 0xFFFFFFFF
    value ^= value >> 16
    return value


def path_hash(path: str) -> tuple[int, int]:
    normalized = path.replace("\\", "/")
    lower = murmur3_32(normalized.lower().encode("utf-16le"))
    upper = murmur3_32(normalized.upper().encode("utf-16le"))
    return lower, upper


@dataclass(frozen=True)
class Entry:
    index: int
    lower_hash: int
    upper_hash: int
    offset: int
    compressed_size: int
    size: int
    attributes: int
    checksum: int

    @property
    def hash_pair(self) -> tuple[int, int]:
        return self.lower_hash, self.upper_hash


def read_entries(pak: Path) -> list[Entry]:
    with pak.open("rb") as stream:
        header = stream.read(16)
        if len(header) != 16 or header[:4] != b"KPKA":
            raise ValueError(f"not a KPKA archive: {pak}")
        version, count = struct.unpack_from("<II", header, 4)
        if version != 4:
            raise ValueError(f"unsupported KPKA version {version}; expected 4")
        file_size = pak.stat().st_size
        table_end = 16 + 48 * count
        if table_end > file_size:
            raise ValueError("entry table exceeds archive size")

        entries = []
        for index in range(count):
            raw = stream.read(48)
            if len(raw) != 48:
                raise ValueError(f"truncated entry table at index {index}")
            filename_hash, offset, compressed, size, attributes, checksum = struct.unpack(
                "<QQQQQQ", raw
            )
            if offset < table_end or offset + compressed > file_size:
                raise ValueError(f"payload outside archive at entry {index}")
            entries.append(
                Entry(
                    index=index,
                    lower_hash=filename_hash & 0xFFFFFFFF,
                    upper_hash=filename_hash >> 32,
                    offset=offset,
                    compressed_size=compressed,
                    size=size,
                    attributes=attributes,
                    checksum=checksum,
                )
            )
        return entries


def read_entry_data(pak: Path, entry: Entry) -> bytes:
    with pak.open("rb") as stream:
        stream.seek(entry.offset)
        data = stream.read(entry.compressed_size)
    if len(data) != entry.compressed_size:
        raise ValueError(f"truncated data for entry {entry.index}")
    if entry.compressed_size == entry.size:
        return data
    for window_bits in (-15, zlib.MAX_WBITS):
        try:
            unpacked = zlib.decompress(data, window_bits)
        except zlib.error:
            continue
        if len(unpacked) == entry.size:
            return unpacked
    raise ValueError(f"unsupported compression for entry {entry.index}")


def guess_magic(data: bytes) -> str:
    signatures = {
        b"MESH": "mesh",
        b"MDF\x00": "mdf2",
        b"USR\x00": "rsz",
        b"TEX\x00": "tex",
        b"MOT\x00": "mot",
        b"CHN\x00": "chain",
        b"JCNS": "jcns",
        b"JMAP": "jmap",
    }
    for magic, name in signatures.items():
        if data.startswith(magic):
            return name
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data.startswith(b"\x89PNG"):
        return "png"
    text = data[:256].decode("utf-8", "ignore")
    if "name=" in text or "category" in text:
        return "modinfo"
    return data[:4].hex()


def load_candidates(path: Path) -> dict[tuple[int, int], list[str]]:
    result: dict[tuple[int, int], list[str]] = {}
    for raw in path.read_text(encoding="utf-8-sig").splitlines():
        candidate = raw.strip()
        if not candidate or candidate.startswith("#"):
            continue
        result.setdefault(path_hash(candidate), []).append(candidate)
    return result


def command_list(args: argparse.Namespace) -> None:
    candidates = load_candidates(args.candidates) if args.candidates else {}
    rows = []
    for entry in read_entries(args.pak):
        data = read_entry_data(args.pak, entry) if args.magic else b""
        matches = candidates.get(entry.hash_pair, [])
        rows.append(
            {
                "index": entry.index,
                "lower_hash": entry.lower_hash,
                "upper_hash": entry.upper_hash,
                "offset": entry.offset,
                "compressed_size": entry.compressed_size,
                "size": entry.size,
                "attributes": f"0x{entry.attributes:016x}",
                "magic": guess_magic(data) if args.magic else "",
                "path": " | ".join(matches),
            }
        )

    fields = list(rows[0]) if rows else ['index','lower_hash','upper_hash','offset','compressed_size','size','attributes','magic','path']
    writer = csv.DictWriter(sys.stdout, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)


def command_extract_index(args: argparse.Namespace) -> None:
    entries = read_entries(args.pak)
    if args.index < 0 or args.output.exists():
        raise ValueError("Require a nonnegative index and a new output path")
    try:
        entry = entries[args.index]
    except IndexError as error:
        raise ValueError(f"entry index out of range: {args.index}") from error
    data = read_entry_data(args.pak, entry)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(data)


def command_hash(args: argparse.Namespace) -> None:
    lower, upper = path_hash(args.path)
    print(f"{lower}-{upper}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)

    hash_parser = subparsers.add_parser("hash")
    hash_parser.add_argument("path")
    hash_parser.set_defaults(func=command_hash)

    list_parser = subparsers.add_parser("list")
    list_parser.add_argument("pak", type=Path)
    list_parser.add_argument("--candidates", type=Path)
    list_parser.add_argument("--magic", action="store_true")
    list_parser.set_defaults(func=command_list)

    extract_parser = subparsers.add_parser("extract-index")
    extract_parser.add_argument("pak", type=Path)
    extract_parser.add_argument("index", type=int)
    extract_parser.add_argument("output", type=Path)
    extract_parser.set_defaults(func=command_extract_index)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        args.func(args)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
