"""Encode a PNG into a donor XBT (header kept byte for byte) with Pillow's DXT1/DXT5 encoder.

The donor's embedded DDS header fixes size, format and mip count; every mip level is resampled
from the full-resolution source (Lanczos), padded to whole 4x4 blocks and compressed separately.
No texconv is needed.  The output has exactly the donor's size, format and mip count.

  python xbt_encode.py SOURCE.png DONOR.xbt OUT.xbt [--force]
"""

from __future__ import annotations

import argparse
import io
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xbt_tool  # noqa: E402

BLOCK = {"FOURCC:DXT1": 8, "FOURCC:DXT5": 16}
PILLOW_FMT = {"FOURCC:DXT1": "DXT1", "FOURCC:DXT5": "DXT5"}


def _encode_level(img: Image.Image, fmt: str) -> bytes:
    w, h = img.size
    bw, bh = max(4, (w + 3) // 4 * 4), max(4, (h + 3) // 4 * 4)
    if (bw, bh) != (w, h):
        a = np.asarray(img)
        a = np.pad(a, ((0, bh - h), (0, bw - w), (0, 0)), mode="edge")
        img = Image.fromarray(a, img.mode)
    buf = io.BytesIO()
    img.save(buf, format="DDS", pixel_format=PILLOW_FMT[fmt])
    data = buf.getvalue()
    if data[84:88] != PILLOW_FMT[fmt].encode():
        raise ValueError("unexpected DDS header from Pillow")
    payload = data[128:]
    want = (bw // 4) * (bh // 4) * BLOCK[fmt]
    if len(payload) != want:
        raise ValueError(f"level payload {len(payload)} != {want}")
    return payload


def encode(png: Path | Image.Image, donor_xbt: Path, out_xbt: Path) -> dict:
    donor = donor_xbt.read_bytes()
    info = xbt_tool.parse_xbt(donor)
    dds = info.dds
    fmt = dds.pixel_format
    if fmt not in BLOCK:
        raise ValueError(f"unsupported donor format {fmt}")
    src = png if isinstance(png, Image.Image) else Image.open(png)
    mode = "RGBA" if fmt == "FOURCC:DXT5" else "RGB"
    src = src.convert(mode)
    payload = b""
    for level in range(dds.mip_count):
        lw, lh = max(1, dds.width >> level), max(1, dds.height >> level)
        payload += _encode_level(src.resize((lw, lh), Image.LANCZOS), fmt)
    off = info.dds_offset
    header = donor[off : off + 128]
    new = donor[:off] + header + payload
    if len(new) != len(donor):
        raise ValueError(f"size mismatch {len(new)} vs donor {len(donor)}")
    check = xbt_tool.parse_xbt(new)
    if (check.dds.width, check.dds.height, check.dds.mip_count, check.dds.pixel_format) != (dds.width, dds.height, dds.mip_count, fmt):
        raise ValueError("re-parsed XBT metadata differs from donor")
    out_xbt.parent.mkdir(parents=True, exist_ok=True)
    out_xbt.write_bytes(new)
    # fidelity check on the top level
    top = Image.open(io.BytesIO(header + payload))
    top.load()
    ref = np.asarray(src.resize((dds.width, dds.height), Image.LANCZOS)).astype(float)
    got = np.asarray(top.convert(mode)).astype(float)
    mse = float(((ref - got) ** 2).mean())
    psnr = 99.0 if mse == 0 else 10 * np.log10(255**2 / mse)
    return {"xbt": str(out_xbt), "size": [dds.width, dds.height], "mips": dds.mip_count, "format": fmt, "psnr_top": round(float(psnr), 2)}


def main() -> None:
    ap = argparse.ArgumentParser(description="Encode a PNG into a donor Watch Dogs XBT (DXT1/DXT5) without texconv.")
    ap.add_argument("png", type=Path)
    ap.add_argument("donor_xbt", type=Path)
    ap.add_argument("out_xbt", type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    args = ap.parse_args()
    if args.out_xbt.resolve() == args.donor_xbt.resolve():
        raise SystemExit("refusing to overwrite the donor")
    if args.out_xbt.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing {args.out_xbt} (use --force)")
    print(encode(args.png, args.donor_xbt, args.out_xbt))


if __name__ == "__main__":
    main()
