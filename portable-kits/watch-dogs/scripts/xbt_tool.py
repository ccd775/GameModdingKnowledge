#!/usr/bin/env python3
"""Inspect, extract, and safely inject DDS payloads in Watch Dogs XBT files."""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


XBT_MAGIC = b"TBX\x00"
DDS_MAGIC = b"DDS "


class FormatError(ValueError):
    pass


@dataclass(frozen=True)
class DdsInfo:
    width: int
    height: int
    mip_count: int
    pixel_format: str
    payload_bytes: int


@dataclass(frozen=True)
class XbtInfo:
    version: int
    dds_offset: int
    total_bytes: int
    dds: DdsInfo
    streamed_high_path: str | None


def _u32(data: bytes, offset: int) -> int:
    if offset < 0 or offset + 4 > len(data):
        raise FormatError(f"u32 at offset {offset} is outside the file")
    return struct.unpack_from("<I", data, offset)[0]


def parse_dds(data: bytes) -> DdsInfo:
    if len(data) < 128 or data[:4] != DDS_MAGIC:
        raise FormatError("DDS magic or 124-byte header is missing")
    if _u32(data, 4) != 124:
        raise FormatError(f"unsupported DDS header size: {_u32(data, 4)}")
    if _u32(data, 76) != 32:
        raise FormatError(f"unsupported DDS pixel-format size: {_u32(data, 76)}")

    height = _u32(data, 12)
    width = _u32(data, 16)
    mip_count = max(1, _u32(data, 28))
    fourcc = data[84:88]
    if fourcc == b"DX10":
        if len(data) < 148:
            raise FormatError("DDS declares DX10 format but has no DX10 header")
        pixel_format = f"DXGI:{_u32(data, 128)}"
    elif fourcc.strip(b"\x00 "):
        pixel_format = "FOURCC:" + fourcc.decode("ascii", errors="replace")
    else:
        pixel_format = "RGBA:" + ":".join(
            f"{_u32(data, offset):08X}" for offset in (88, 92, 96, 100, 104)
        )

    return DdsInfo(
        width=width,
        height=height,
        mip_count=mip_count,
        pixel_format=pixel_format,
        payload_bytes=len(data),
    )


def parse_xbt(data: bytes) -> XbtInfo:
    if len(data) < 48 or data[:4] != XBT_MAGIC:
        raise FormatError("Watch Dogs XBT magic TBX\\0 is missing")
    version = _u32(data, 4)
    dds_offset = _u32(data, 8)
    if dds_offset < 12 or dds_offset + 4 > len(data):
        raise FormatError(f"invalid DDS offset in XBT header: {dds_offset}")
    if data[dds_offset : dds_offset + 4] != DDS_MAGIC:
        raise FormatError(f"XBT offset {dds_offset} does not point to DDS magic")

    streamed_high_path = None
    header = data[:dds_offset]
    marker = header.find(b"graphics\\")
    if marker >= 0:
        end = header.find(b"\x00", marker)
        if end > marker:
            streamed_high_path = header[marker:end].decode("ascii", errors="strict")

    return XbtInfo(
        version=version,
        dds_offset=dds_offset,
        total_bytes=len(data),
        dds=parse_dds(data[dds_offset:]),
        streamed_high_path=streamed_high_path,
    )


def compatibility_errors(template: DdsInfo, replacement: DdsInfo) -> list[str]:
    errors = []
    for field in ("width", "height", "mip_count", "pixel_format"):
        expected = getattr(template, field)
        actual = getattr(replacement, field)
        if expected != actual:
            errors.append(f"{field}: template={expected!r}, replacement={actual!r}")
    return errors


def inspect_xbt(path: Path) -> XbtInfo:
    return parse_xbt(path.read_bytes())


def command_inspect(args: argparse.Namespace) -> int:
    for raw_path in args.xbt:
        path = Path(raw_path)
        record = {"path": str(path), **asdict(inspect_xbt(path))}
        print(json.dumps(record, ensure_ascii=False, sort_keys=True))
    return 0


def command_extract(args: argparse.Namespace) -> int:
    source = Path(args.xbt)
    for path in (args.dds, args.header):
        if path and Path(path).exists():
            raise FileExistsError(path)
    data = source.read_bytes()
    info = parse_xbt(data)
    Path(args.dds).write_bytes(data[info.dds_offset :])
    if args.header:
        Path(args.header).write_bytes(data[: info.dds_offset])
    print(json.dumps(asdict(info), ensure_ascii=False, sort_keys=True))
    return 0


def command_inject(args: argparse.Namespace) -> int:
    if Path(args.output_xbt).exists():
        raise FileExistsError(args.output_xbt)
    template_path = Path(args.template_xbt)
    template_data = template_path.read_bytes()
    template_info = parse_xbt(template_data)
    replacement_data = Path(args.dds).read_bytes()
    replacement_info = parse_dds(replacement_data)
    errors = compatibility_errors(template_info.dds, replacement_info)
    if errors and not args.force:
        detail = "\n  - ".join(errors)
        raise FormatError(
            "replacement DDS is incompatible with the donor XBT header:\n"
            f"  - {detail}\n"
            "Use a matching texture conversion target. --force is for diagnostics only."
        )

    output = template_data[: template_info.dds_offset] + replacement_data
    output_path = Path(args.output_xbt)
    output_path.write_bytes(output)
    result = {
        "output": str(output_path),
        "bytes": len(output),
        "forced": bool(errors),
        "compatibility_errors": errors,
        "xbt": asdict(parse_xbt(output)),
    }
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    inspect_parser = subparsers.add_parser("inspect", help="print XBT/DDS metadata as JSON")
    inspect_parser.add_argument("xbt", nargs="+", help="XBT file(s) to inspect")
    inspect_parser.set_defaults(func=command_inspect)

    extract_parser = subparsers.add_parser("extract", help="extract the embedded DDS payload")
    extract_parser.add_argument("xbt", help="source XBT")
    extract_parser.add_argument("dds", help="output DDS")
    extract_parser.add_argument("--header", help="optional output file for the XBT header")
    extract_parser.set_defaults(func=command_extract)

    inject_parser = subparsers.add_parser(
        "inject", help="replace the DDS payload while preserving the donor XBT header"
    )
    inject_parser.add_argument("template_xbt", help="donor XBT whose header is preserved")
    inject_parser.add_argument("dds", help="replacement DDS")
    inject_parser.add_argument("output_xbt", help="output XBT")
    inject_parser.add_argument(
        "--force",
        action="store_true",
        help="allow incompatible DDS metadata; intended only for format diagnostics",
    )
    inject_parser.set_defaults(func=command_inject)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    try:
        return args.func(args)
    except (OSError, FormatError) as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    sys.exit(main())
