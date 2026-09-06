#!/usr/bin/env python3
"""Build a validated low/high Watch Dogs XBT pair from one PNG and donor headers."""

from __future__ import annotations

import argparse
import hashlib
import json
import locale
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path, PureWindowsPath

from xbt_tool import FormatError, compatibility_errors, parse_dds, parse_xbt


DEFAULT_TEXCONV_SHA256 = "DCFDEC10244E02CF5037FBA089C55FB7E1326B1C8181742D77D15FA5CB5EEF06"
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
TEXCONV_FORMAT = {
    "FOURCC:DXT1": "BC1_UNORM",
    "FOURCC:DXT5": "BC3_UNORM",
}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def inspect_png(path: Path) -> dict[str, int]:
    header = path.read_bytes()[:29]
    if len(header) < 29 or header[:8] != PNG_SIGNATURE or header[12:16] != b"IHDR":
        raise FormatError(f"input is not a PNG with a valid IHDR header: {path}")
    width, height = struct.unpack_from(">II", header, 16)
    if width == 0 or height == 0:
        raise FormatError("PNG width and height must be non-zero")
    return {
        "width": width,
        "height": height,
        "bit_depth": header[24],
        "color_type": header[25],
    }


def expected_dds_bytes(pixel_format: str, width: int, height: int, mips: int) -> int:
    block_bytes = {"FOURCC:DXT1": 8, "FOURCC:DXT5": 16}.get(pixel_format)
    if block_bytes is None:
        raise FormatError(f"unsupported block-compressed donor format: {pixel_format}")
    payload = 0
    for level in range(mips):
        mip_width = max(1, width >> level)
        mip_height = max(1, height >> level)
        payload += max(1, (mip_width + 3) // 4) * max(1, (mip_height + 3) // 4) * block_bytes
    return 128 + payload


def validate_dds_size(data: bytes, label: str) -> None:
    info = parse_dds(data)
    expected = expected_dds_bytes(
        info.pixel_format, info.width, info.height, info.mip_count
    )
    if len(data) != expected:
        raise FormatError(
            f"{label} DDS byte length is {len(data)}, expected {expected} from its header"
        )


def validate_templates(
    low_path: Path, high_path: Path, low_data: bytes, high_data: bytes
) -> tuple[object, object]:
    low = parse_xbt(low_data)
    high = parse_xbt(high_data)
    if low.version != 123 or high.version != 123:
        raise FormatError(
            f"expected Watch Dogs XBT version 123, got low={low.version}, high={high.version}"
        )
    if not low.streamed_high_path:
        raise FormatError("low donor has no embedded high-stream path")
    embedded_name = PureWindowsPath(low.streamed_high_path).name
    if embedded_name.casefold() != high_path.name.casefold():
        raise FormatError(
            "high donor filename does not match the low donor's embedded path: "
            f"expected {embedded_name!r}, got {high_path.name!r}"
        )
    if high.streamed_high_path:
        raise FormatError("high donor unexpectedly references another high stream")
    if low.dds.pixel_format != high.dds.pixel_format:
        raise FormatError(
            f"low/high donor DDS formats differ: {low.dds.pixel_format} vs {high.dds.pixel_format}"
        )
    if high.dds.width != low.dds.width * 2 or high.dds.height != low.dds.height * 2:
        raise FormatError(
            "high donor dimensions must be exactly 2x the low donor dimensions: "
            f"low={low.dds.width}x{low.dds.height}, "
            f"high={high.dds.width}x{high.dds.height}"
        )
    if high.dds.mip_count != 1:
        raise FormatError(
            f"high donor must contain exactly one mip, got {high.dds.mip_count}"
        )
    expected_low_mips = max(low.dds.width, low.dds.height).bit_length()
    if low.dds.mip_count != expected_low_mips:
        raise FormatError(
            "low donor must contain a complete mip chain: "
            f"got {low.dds.mip_count}, expected {expected_low_mips}"
        )
    if low.dds.pixel_format not in TEXCONV_FORMAT:
        raise FormatError(f"unsupported donor DDS format: {low.dds.pixel_format}")
    if low_path.name.casefold() == high_path.name.casefold():
        raise FormatError("low and high output filenames would collide")
    validate_dds_size(low_data[low.dds_offset :], "low donor")
    validate_dds_size(high_data[high.dds_offset :], "high donor")
    return low, high


def run_texconv(
    texconv: Path,
    png: Path,
    output_dir: Path,
    pixel_format: str,
    width: int,
    height: int,
    mips: int,
    separate_alpha: bool,
    alpha_threshold: float | None,
) -> tuple[bytes, list[str], str]:
    command = [
        str(texconv),
        "-nologo",
        "-y",
        "-ft",
        "DDS",
        "-dx9",
        "-f",
        TEXCONV_FORMAT[pixel_format],
        "-w",
        str(width),
        "-h",
        str(height),
        "-m",
        str(mips),
        "-o",
        str(output_dir),
    ]
    if separate_alpha:
        command.append("-sepalpha")
    if alpha_threshold is not None:
        command.extend(["-at", str(alpha_threshold)])
    command.append(str(png))

    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        encoding=locale.getpreferredencoding(False),
        errors="replace",
    )
    if result.returncode != 0:
        raise FormatError(
            f"texconv failed with exit code {result.returncode}:\n"
            f"{result.stdout}{result.stderr}"
        )
    candidates = [path for path in output_dir.iterdir() if path.suffix.casefold() == ".dds"]
    if len(candidates) != 1:
        raise FormatError(
            f"texconv produced {len(candidates)} DDS files in {output_dir}; expected exactly one"
        )
    data = candidates[0].read_bytes()
    validate_dds_size(data, "generated")
    return data, command, (result.stdout + result.stderr).strip()


def build(args: argparse.Namespace) -> dict[str, object]:
    png = args.png.resolve(strict=True)
    low_path = args.low_template.resolve(strict=True)
    high_path = args.high_template.resolve(strict=True)
    texconv = args.texconv.resolve(strict=True)
    output_dir = args.output_dir.resolve()

    if output_dir == low_path.parent or output_dir == high_path.parent:
        raise FormatError("output directory must not be either donor template directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    output_low = output_dir / low_path.name
    output_high = output_dir / high_path.name
    output_report = output_dir / f"{low_path.stem}.build.json"
    targets = (output_low, output_high, output_report)
    collisions = [str(path) for path in targets if path.exists()]
    if collisions and not args.overwrite:
        raise FormatError("refusing to overwrite existing output(s): " + ", ".join(collisions))

    texconv_hash = sha256_file(texconv)
    if texconv_hash != args.expected_texconv_sha256.upper():
        raise FormatError(
            "texconv SHA256 mismatch: "
            f"expected {args.expected_texconv_sha256.upper()}, got {texconv_hash}"
        )

    png_info = inspect_png(png)
    low_template_data = low_path.read_bytes()
    high_template_data = high_path.read_bytes()
    low, high = validate_templates(
        low_path, high_path, low_template_data, high_template_data
    )

    staging = Path(tempfile.mkdtemp(prefix=".xbt_build_", dir=output_dir))
    try:
        low_dds_dir = staging / "low"
        high_dds_dir = staging / "high"
        low_dds_dir.mkdir()
        high_dds_dir.mkdir()
        low_dds, low_command, low_log = run_texconv(
            texconv,
            png,
            low_dds_dir,
            low.dds.pixel_format,
            low.dds.width,
            low.dds.height,
            low.dds.mip_count,
            args.separate_alpha,
            args.alpha_threshold,
        )
        high_dds, high_command, high_log = run_texconv(
            texconv,
            png,
            high_dds_dir,
            high.dds.pixel_format,
            high.dds.width,
            high.dds.height,
            high.dds.mip_count,
            args.separate_alpha,
            args.alpha_threshold,
        )

        low_generated = parse_dds(low_dds)
        high_generated = parse_dds(high_dds)
        low_errors = compatibility_errors(low.dds, low_generated)
        high_errors = compatibility_errors(high.dds, high_generated)
        if low_errors or high_errors:
            raise FormatError(
                "generated DDS metadata is incompatible with donor(s): "
                + "; ".join(low_errors + high_errors)
            )

        rebuilt_low = low_template_data[: low.dds_offset] + low_dds
        rebuilt_high = high_template_data[: high.dds_offset] + high_dds
        rebuilt_low_info = parse_xbt(rebuilt_low)
        rebuilt_high_info = parse_xbt(rebuilt_high)
        if rebuilt_low[: low.dds_offset] != low_template_data[: low.dds_offset]:
            raise FormatError("low XBT header changed during rebuild")
        if rebuilt_high[: high.dds_offset] != high_template_data[: high.dds_offset]:
            raise FormatError("high XBT header changed during rebuild")
        if rebuilt_low_info.streamed_high_path != low.streamed_high_path:
            raise FormatError("low XBT embedded high-stream path changed during rebuild")

        staged_low = staging / output_low.name
        staged_high = staging / output_high.name
        staged_low.write_bytes(rebuilt_low)
        staged_high.write_bytes(rebuilt_high)
        report = {
            "schema_version": 1,
            "source_png": {
                "path": str(png),
                "sha256": sha256_file(png),
                **png_info,
            },
            "texconv": {"path": str(texconv), "sha256": texconv_hash},
            "options": {
                "separate_alpha": args.separate_alpha,
                "alpha_threshold": args.alpha_threshold,
            },
            "low": {
                "template": str(low_path),
                "template_sha256": sha256_bytes(low_template_data),
                "output": str(output_low),
                "output_sha256": sha256_bytes(rebuilt_low),
                "xbt": asdict(rebuilt_low_info),
                "dds_sha256": sha256_bytes(low_dds),
                "texconv_command": low_command,
                "texconv_log": low_log,
            },
            "high": {
                "template": str(high_path),
                "template_sha256": sha256_bytes(high_template_data),
                "output": str(output_high),
                "output_sha256": sha256_bytes(rebuilt_high),
                "xbt": asdict(rebuilt_high_info),
                "dds_sha256": sha256_bytes(high_dds),
                "texconv_command": high_command,
                "texconv_log": high_log,
            },
            "validation": {
                "xbt_headers_preserved": True,
                "embedded_high_path_preserved": True,
                "dds_metadata_matches_donors": True,
                "dds_byte_lengths_match_headers": True,
            },
        }
        staged_report = staging / output_report.name
        staged_report.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

        if not args.overwrite:
            late_collisions = [str(path) for path in targets if path.exists()]
            if late_collisions:
                raise FormatError(
                    "output(s) appeared during build; refusing to overwrite: "
                    + ", ".join(late_collisions)
                )
        os.replace(staged_low, output_low)
        os.replace(staged_high, output_high)
        os.replace(staged_report, output_report)
        return report
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def build_parser() -> argparse.ArgumentParser:
    repo_root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("png", type=Path, help="source PNG")
    parser.add_argument("low_template", type=Path, help="streaming low XBT donor")
    parser.add_argument("high_template", type=Path, help="matching _high XBT donor")
    parser.add_argument("output_dir", type=Path, help="output directory")
    parser.add_argument(
        "--texconv",
        type=Path,
        required=True,
        help="DirectXTex texconv executable",
    )
    parser.add_argument(
        "--expected-texconv-sha256",
        required=True,
        help="required SHA256 for the texconv executable",
    )
    parser.add_argument(
        "--separate-alpha",
        action="store_true",
        help="filter alpha separately while resizing and generating mips",
    )
    parser.add_argument(
        "--alpha-threshold",
        type=float,
        help="BC1 alpha threshold from 0.0 through 1.0",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="replace files already present in the output directory",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.alpha_threshold is not None and not 0.0 <= args.alpha_threshold <= 1.0:
        parser.error("--alpha-threshold must be between 0.0 and 1.0")
    try:
        report = build(args)
    except (OSError, FormatError, subprocess.SubprocessError) as error:
        parser.error(str(error))
        return 2
    print(
        json.dumps(
            {
                "low": report["low"]["output"],
                "high": report["high"]["output"],
                "validation": report["validation"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
