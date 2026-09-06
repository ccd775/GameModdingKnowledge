#!/usr/bin/env python3
"""Rebuild configured Karin atlas TGAs into Glacier TEXT/TEXD resources."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import subprocess
from pathlib import Path


TEXT_HEADER = struct.Struct("<HHIIHHHBBBBH")
HASH_META_VIDEO_MEMORY_OFFSET = 40
HASH_META_MIN_SIZE = HASH_META_VIDEO_MEMORY_OFFSET + 4
STREAMING_MIP_CUTOFF = 256


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--atlas-dir", required=True)
    parser.add_argument("--carrier-text-dir", required=True)
    parser.add_argument("--build-dir", required=True)
    parser.add_argument("--rpkg-cli", required=True)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(4 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def tga_dimensions(path: Path) -> tuple[int, int]:
    data = path.read_bytes()[:18]
    if len(data) != 18:
        raise ValueError(f"TGA header is truncated: {path}")
    width, height = struct.unpack_from("<HH", data, 12)
    if width == 0 or height == 0:
        raise ValueError(f"TGA has invalid dimensions: {path}")
    return width, height


def streamed_pixel_count(dimension: int, cutoff: int = STREAMING_MIP_CUTOFF) -> int:
    if dimension < cutoff or dimension & (dimension - 1):
        raise ValueError(f"Texture dimension must be a power of two >= {cutoff}: {dimension}")
    total = 0
    mip = dimension
    while mip >= cutoff:
        total += mip * mip
        mip //= 2
    return total


def rescale_video_memory_size(
    carrier_size: int, carrier_dimension: int, target_dimension: int
) -> int:
    if carrier_size in (0, 0xFFFFFFFF):
        raise ValueError(f"Carrier video-memory size is not usable: {carrier_size}")
    numerator = carrier_size * streamed_pixel_count(target_dimension)
    denominator = streamed_pixel_count(carrier_dimension)
    target_size, remainder = divmod(numerator, denominator)
    if remainder:
        raise ValueError(
            "Carrier video-memory size does not scale exactly with its streamed mip chain: "
            f"size={carrier_size}, carrier={carrier_dimension}, target={target_dimension}"
        )
    if target_size > 0xFFFFFFFF:
        raise ValueError(f"Target video-memory size overflows uint32: {target_size}")
    return target_size


def hash_meta_video_memory_size(path: Path) -> int:
    data = path.read_bytes()
    if len(data) < HASH_META_MIN_SIZE:
        raise ValueError(f"Hash meta is too short: {path}")
    return struct.unpack_from("<I", data, HASH_META_VIDEO_MEMORY_OFFSET)[0]


def patch_hash_meta_video_memory_size(path: Path, target_size: int) -> None:
    data = bytearray(path.read_bytes())
    if len(data) < HASH_META_MIN_SIZE:
        raise ValueError(f"Hash meta is too short: {path}")
    struct.pack_into("<I", data, HASH_META_VIDEO_MEMORY_OFFSET, target_size)
    path.write_bytes(data)


def texd_hash_from_tga_meta(path: Path) -> str:
    data = path.read_bytes()
    if len(data) < 12:
        raise ValueError(f"TGA meta is too short: {path}")
    rpkg_name_length = struct.unpack_from("<I", data, 0)[0]
    texd_offset = 4 + rpkg_name_length
    if texd_offset + 8 > len(data):
        raise ValueError(f"TGA meta has an invalid RPKG name length: {path}")
    texd_hash = struct.unpack_from("<Q", data, texd_offset)[0]
    if texd_hash == 0:
        raise ValueError(f"Configured carrier TEXT has no TEXD dependency: {path}")
    return f"{texd_hash:016X}"


def parse_text_header(path: Path) -> dict:
    data = path.read_bytes()[: TEXT_HEADER.size]
    if len(data) != TEXT_HEADER.size:
        raise ValueError(f"Rebuilt TEXT header is truncated: {path}")
    (
        magic,
        texture_type,
        file_size,
        flags,
        width,
        height,
        directx_format,
        mip_count,
        mip_default,
        mip_unknown_1,
        mip_unknown_2,
        mip_mode,
    ) = TEXT_HEADER.unpack(data)
    return {
        "magic": magic,
        "texture_type": texture_type,
        "file_size": file_size,
        "flags": flags,
        "width": width,
        "height": height,
        "directx_format": directx_format,
        "mip_count": mip_count,
        "mip_default": mip_default,
        "mip_unknown_1": mip_unknown_1,
        "mip_unknown_2": mip_unknown_2,
        "mip_mode": mip_mode,
    }


def configured_text_hashes(config: dict) -> list[str]:
    hashes = []
    for slot in config["slots"]:
        for semantic in ("normal", "specular", "diffuse"):
            value = str(slot["texture_hashes"][semantic]).upper()
            if len(value) != 16 or any(char not in "0123456789ABCDEF" for char in value):
                raise ValueError(f"Invalid {semantic} TEXT hash in slot {slot['slot']}: {value}")
            hashes.append(value)
    if len(set(hashes)) != len(hashes):
        raise ValueError("Configured TEXT hashes are not unique")
    return hashes


def validate_carrier_slot_contract(config: dict) -> None:
    slots = sorted(config["slots"], key=lambda item: int(item["slot"]))
    if [int(slot["slot"]) for slot in slots] != list(range(6)):
        raise ValueError("Carrier texture config must define slots 0 through 5 exactly once")
    base = str(slots[0]["carrier_mati_hash"]).upper()[:-3]
    semantic_tail = {"normal": "1A", "specular": "2A", "diffuse": "3A"}
    for slot in slots:
        index = int(slot["slot"])
        expected_dependency = index + 1
        if int(slot["carrier_material_id"]) != expected_dependency:
            raise ValueError(f"Slot {index} has the wrong raw PRIM material ID")
        if int(slot["carrier_dependency_index"]) != expected_dependency:
            raise ValueError(f"Slot {index} has the wrong PRIM dependency index")
        expected_mati = f"{base}{index:X}00"
        if str(slot["carrier_mati_hash"]).upper() != expected_mati:
            raise ValueError(f"Slot {index} must use MATI {expected_mati}")
        for semantic, tail in semantic_tail.items():
            expected_text = f"{base}{index:X}{tail}"
            actual_text = str(slot["texture_hashes"][semantic]).upper()
            if actual_text != expected_text:
                raise ValueError(
                    f"Slot {index} {semantic} must use TEXT {expected_text}, got {actual_text}"
                )


def copy_input_set(
    text_hash: str, atlas_dir: Path, carrier_text_dir: Path, build_dir: Path
) -> dict:
    carrier_metas = carrier_text_dir / "metas"
    tga_source = atlas_dir / f"{text_hash}.TEXT.tga"
    carrier_tga_source = carrier_text_dir / f"{text_hash}.TEXT.tga"
    tga_meta_source = carrier_metas / f"{text_hash}.TEXT.tga.meta"
    text_meta_source = carrier_metas / f"{text_hash}.TEXT.meta"
    for path in (tga_source, carrier_tga_source, tga_meta_source, text_meta_source):
        if not path.is_file():
            raise FileNotFoundError(path)

    texd_hash = texd_hash_from_tga_meta(tga_meta_source)
    texd_meta_source = carrier_metas / f"{texd_hash}.TEXD.meta"
    if not texd_meta_source.is_file():
        raise FileNotFoundError(texd_meta_source)

    meta_dir = build_dir / "metas"
    meta_dir.mkdir(parents=True, exist_ok=True)
    destinations = {
        "tga": build_dir / tga_source.name,
        "tga_meta": meta_dir / tga_meta_source.name,
        "text_meta": meta_dir / text_meta_source.name,
        "texd_meta": meta_dir / texd_meta_source.name,
    }
    for source, destination in (
        (tga_source, destinations["tga"]),
        (tga_meta_source, destinations["tga_meta"]),
        (text_meta_source, destinations["text_meta"]),
        (texd_meta_source, destinations["texd_meta"]),
    ):
        shutil.copy2(source, destination)

    atlas_dimensions = tga_dimensions(tga_source)
    carrier_dimensions = tga_dimensions(carrier_tga_source)
    if atlas_dimensions[0] != atlas_dimensions[1]:
        raise ValueError(f"Atlas must be square: {tga_source}")
    if carrier_dimensions[0] != carrier_dimensions[1]:
        raise ValueError(f"Carrier texture must be square: {carrier_tga_source}")
    carrier_text_video_size = hash_meta_video_memory_size(text_meta_source)
    carrier_texd_video_size = hash_meta_video_memory_size(texd_meta_source)
    if carrier_text_video_size != carrier_texd_video_size:
        raise ValueError(
            f"Carrier TEXT/TEXD video-memory sizes differ for {text_hash}: "
            f"{carrier_text_video_size} != {carrier_texd_video_size}"
        )
    target_video_size = rescale_video_memory_size(
        carrier_text_video_size, carrier_dimensions[0], atlas_dimensions[0]
    )
    patch_hash_meta_video_memory_size(destinations["text_meta"], target_video_size)
    patch_hash_meta_video_memory_size(destinations["texd_meta"], target_video_size)

    return {
        "text_hash": text_hash,
        "texd_hash": texd_hash,
        "tga": str(destinations["tga"]),
        "tga_sha256": sha256_file(destinations["tga"]),
        "carrier_dimensions": list(carrier_dimensions),
        "atlas_dimensions": list(atlas_dimensions),
        "carrier_video_memory_size": carrier_text_video_size,
        "target_video_memory_size": target_video_size,
    }


def validate_no_unexpected_tgas(build_dir: Path, expected_hashes: set[str]) -> None:
    actual = {path.name[:16].upper() for path in build_dir.glob("*.TEXT.tga")}
    unexpected = sorted(actual - expected_hashes)
    if unexpected:
        raise RuntimeError(
            "Build directory contains unexpected root TGAs: " + ", ".join(unexpected)
        )


def main() -> None:
    args = parse_args()
    config_path = Path(args.config).resolve()
    atlas_dir = Path(args.atlas_dir).resolve()
    carrier_text_dir = Path(args.carrier_text_dir).resolve()
    carrier_metas = carrier_text_dir / "metas"
    build_dir = Path(args.build_dir).resolve()
    rpkg_cli = Path(args.rpkg_cli).resolve()
    if build_dir.exists():
        raise FileExistsError("Choose a fresh build directory")

    if not rpkg_cli.is_file():
        raise FileNotFoundError(rpkg_cli)
    if not carrier_metas.is_dir():
        raise FileNotFoundError(carrier_metas)
    build_dir.mkdir(parents=True, exist_ok=True)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    validate_carrier_slot_contract(config)
    text_hashes = configured_text_hashes(config)
    expected_hashes = set(text_hashes)
    validate_no_unexpected_tgas(build_dir, expected_hashes)

    resources = [
        copy_input_set(text_hash, atlas_dir, carrier_text_dir, build_dir)
        for text_hash in text_hashes
    ]
    texd_hashes = [entry["texd_hash"] for entry in resources]
    if len(set(texd_hashes)) != len(texd_hashes):
        raise RuntimeError("Carrier TEXT resources do not have unique TEXD dependencies")

    log_path = build_dir / "rpkg-rebuild-text.log"
    with log_path.open("w", encoding="utf-8", newline="\n") as log:
        result = subprocess.run(
            [str(rpkg_cli), "-rebuild_text_in", str(build_dir)],
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
        )
    if result.returncode != 0:
        raise RuntimeError(f"RPKG TEXT rebuild failed; see {log_path}")

    rebuilt_dir = build_dir / "REBUILT"
    package_path = build_dir / "RPKGS" / "chunk0.rpkg"
    if not package_path.is_file() or package_path.stat().st_size == 0:
        raise RuntimeError(f"RPKG output is missing or empty: {package_path}")

    expected_rebuilt_names: set[str] = {"rpkgfilename.txt"}
    for entry in resources:
        expected_rebuilt_names.update(
            {
                f"{entry['text_hash']}.TEXT",
                f"{entry['text_hash']}.TEXT.meta",
                f"{entry['texd_hash']}.TEXD",
                f"{entry['texd_hash']}.TEXD.meta",
            }
        )
    actual_rebuilt_names = {path.name for path in rebuilt_dir.iterdir() if path.is_file()}
    missing = sorted(expected_rebuilt_names - actual_rebuilt_names)
    unexpected = sorted(actual_rebuilt_names - expected_rebuilt_names)
    if missing or unexpected:
        raise RuntimeError(
            f"Rebuilt resource set mismatch; missing={missing}, unexpected={unexpected}"
        )

    atlas_size = int(config["atlas_size"])
    expected_mips = atlas_size.bit_length()
    for entry in resources:
        text_path = rebuilt_dir / f"{entry['text_hash']}.TEXT"
        texd_path = rebuilt_dir / f"{entry['texd_hash']}.TEXD"
        header = parse_text_header(text_path)
        if header["magic"] != 1:
            raise RuntimeError(f"Unexpected TEXT magic for {entry['text_hash']}: {header['magic']}")
        if (header["width"], header["height"]) != (atlas_size, atlas_size):
            raise RuntimeError(
                f"Unexpected TEXT size for {entry['text_hash']}: "
                f"{header['width']}x{header['height']}"
            )
        if header["mip_count"] != expected_mips:
            raise RuntimeError(
                f"Unexpected mip count for {entry['text_hash']}: {header['mip_count']}"
            )
        rebuilt_text_meta = rebuilt_dir / f"{entry['text_hash']}.TEXT.meta"
        rebuilt_texd_meta = rebuilt_dir / f"{entry['texd_hash']}.TEXD.meta"
        rebuilt_video_sizes = {
            "TEXT": hash_meta_video_memory_size(rebuilt_text_meta),
            "TEXD": hash_meta_video_memory_size(rebuilt_texd_meta),
        }
        if set(rebuilt_video_sizes.values()) != {entry["target_video_memory_size"]}:
            raise RuntimeError(
                f"Rebuilt video-memory metadata mismatch for {entry['text_hash']}: "
                f"{rebuilt_video_sizes}, expected {entry['target_video_memory_size']}"
            )
        entry.update(
            {
                "text_header": header,
                "text_bytes": text_path.stat().st_size,
                "text_sha256": sha256_file(text_path),
                "texd_bytes": texd_path.stat().st_size,
                "texd_sha256": sha256_file(texd_path),
                "rebuilt_video_memory_sizes": rebuilt_video_sizes,
            }
        )

    manifest = {
        "schema_version": 1,
        "config": str(config_path),
        "atlas_dir": str(atlas_dir),
        "carrier_text_dir": str(carrier_text_dir),
        "rpkg_cli": str(rpkg_cli),
        "atlas_size": atlas_size,
        "expected_mips": expected_mips,
        "resource_count": len(resources) * 2,
        "resources": resources,
        "package": {
            "path": str(package_path),
            "bytes": package_path.stat().st_size,
            "sha256": sha256_file(package_path),
        },
        "log": str(log_path),
        "status": "pass",
    }
    manifest_path = build_dir / "build-manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"REBUILT_TEXT={len(resources)}")
    print(f"REBUILT_TEXD={len(resources)}")
    print(f"PACKAGE={package_path}")
    print(f"MANIFEST={manifest_path}")


if __name__ == "__main__":
    main()
