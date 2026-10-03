"""Decode/encode the mesh part of ZModeler-style Watch Dogs char01 XBG files.

The encoder rebuilds a complete XBG from:
  * a template XBG (header constants, material tables, skeleton and the
    constant skeleton/physics block are copied verbatim), and
  * a neutral mesh description (per LOD, per material submesh arrays).

Vertex layouts (vertex type -> byte offsets), all little endian:
  0x179A stride 40: pos i16x3, w i16=1, uv0 i16x2, uv1 i16x2, weights u8x4,
                    palette u8x4, normal u8x4 (B=z,G=y,R=x,A=0x40), color u8x4,
                    tangent u8x4 (80 80 80 00), binormal u8x4 (80 80 80 00)
  0x17BA stride 44: as 0x179A plus 4 zero bytes after palette
  0x11BA stride 36: as 0x17BA without tangent/binormal
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np

import xbg_model

UV_SCALE = 2.0 ** -15  # what the file header declares (game-side decode)
UV_ONE = 32766.0  # ZModeler encodes uv 1.0 as 32766: q = (int)(uv * 32766 + 0.5)
QMAX = 32766.0


def c_round(x: np.ndarray, mode: str = "zmodeler") -> np.ndarray:
    """Quantize like ZModeler, (int)(x + 0.5) in float32, or to nearest.

    "nearest" is the exact inverse of decode() and is used to re-encode data
    that was decoded from an existing XBG; "zmodeler" reproduces ZModeler's
    output when encoding fresh float data (e.g. from an FBX).
    """
    if mode == "nearest":
        return np.round(np.asarray(x, dtype=np.float64)).astype(np.int64)
    return np.trunc(np.asarray(x, dtype=np.float32) + np.float32(0.5)).astype(np.int64)

LAYOUTS = {
    # vertex type: (stride, extra_after_palette, has_tangent_frame)
    0x179A: (40, False, True),
    0x17BA: (44, True, True),
    0x11BA: (36, True, False),
}


@dataclass
class Submesh:
    material: int
    vertex_type: int
    positions: np.ndarray  # (n,3) float64, XBG model space metres
    normals: np.ndarray  # (n,3) float64 unit
    uv0: np.ndarray  # (n,2) float64, stored convention (already flipped), 1.0 == 32766
    uv1: np.ndarray  # (n,2)
    color: np.ndarray  # (n,4) uint8 as stored (B,G,R,A)
    weights: np.ndarray  # (n,4) uint8, sum 255
    bones: np.ndarray  # (n,4) int, skeleton node "b" index (-1 unused)
    triangles: np.ndarray  # (m,3) int, local indices, stored winding


def _normal_bytes(n: np.ndarray) -> np.ndarray:
    out = np.empty((len(n), 4), dtype=np.uint8)
    q = np.clip(c_round(np.asarray(n, np.float32) * np.float32(127.0) + np.float32(127.0)), 0, 255).astype(np.uint8)
    out[:, 0] = q[:, 2]
    out[:, 1] = q[:, 1]
    out[:, 2] = q[:, 0]
    out[:, 3] = 0x40
    return out


def _normal_floats(b: np.ndarray) -> np.ndarray:
    return (b[:, [2, 1, 0]].astype(np.float64) - 127.0) / 127.0


def decode(x: xbg_model.Xbg) -> tuple[float, list[list[Submesh]]]:
    scale = struct.unpack_from("<f", x.data, 0x28)[0]
    palette = np.array(x.palette + [0], dtype=np.int64)
    lods = []
    for lod, descs in enumerate(x.lods):
        subs = []
        for desc in descs:
            stride, extra, tframe = LAYOUTS[desc.vertex_type]
            assert stride == desc.stride
            v = x.vertices(lod, desc)
            tri = x.indices(lod, desc).astype(np.int64)
            used = np.unique(tri)
            remap = np.full(desc.vertex_count, -1, dtype=np.int64)
            remap[used] = np.arange(len(used))
            v = v[used]
            tri = remap[tri]
            q = v[:, 0:8].copy().view("<i2").reshape(-1, 4)
            assert np.all(q[:, 3] == 1)
            noff = 28 if extra else 24
            w = v[:, 16:20].copy()
            pal = v[:, 20:24].astype(np.int64)
            bones = np.where(w > 0, palette[pal], -1)
            subs.append(
                Submesh(
                    material=desc.material,
                    vertex_type=desc.vertex_type,
                    positions=q[:, :3].astype(np.float64) * scale,
                    normals=_normal_floats(v[:, noff : noff + 3]),
                    uv0=v[:, 8:12].copy().view("<i2").reshape(-1, 2) / UV_ONE,
                    uv1=v[:, 12:16].copy().view("<i2").reshape(-1, 2) / UV_ONE,
                    color=v[:, noff + 4 : noff + 8].copy(),
                    weights=w,
                    bones=bones,
                    triangles=tri,
                )
            )
        lods.append(subs)
    return scale, lods


def _name_bytes(h: int, s: str) -> bytes:
    raw = s.encode("ascii") + b"\0"
    pad = (-len(raw)) % 4
    return struct.pack("<II", h, len(raw)) + raw + b"\0" * pad


def _bounds(p: np.ndarray) -> tuple:
    lo = p.min(0)
    hi = p.max(0)
    c = (lo + hi) / 2
    r = float(np.linalg.norm(hi - lo) / 2)
    return (*c, r, *lo, *hi)


def build_palette(lods: list[list[Submesh]]) -> list[int]:
    seen: dict[int, None] = {}
    for subs in lods:
        for sm in subs:
            for row_b, row_w in zip(sm.bones, sm.weights):
                for b, w in zip(row_b, row_w):
                    if w > 0 and b not in seen:
                        seen[int(b)] = None
    return list(seen)


def encode(
    template: xbg_model.Xbg,
    lods: list[list[Submesh]],
    palette: list[int] | None = None,
    scale: float | None = None,
    rounding: str = "zmodeler",
) -> bytes:
    t = template.data
    all_pos = np.concatenate([sm.positions for subs in lods for sm in subs])
    if scale is None:
        scale = float(np.float32(np.abs(all_pos).max() / QMAX))
    if palette is None:
        palette = build_palette(lods)
    pal_index = {b: i for i, b in enumerate(palette)}
    if len(palette) > 255:
        raise ValueError("palette exceeds 255 bones")

    # ---- header
    head = bytearray(t[:0x8C])
    lo = all_pos.min(0)
    hi = all_pos.max(0)
    c = (lo + hi) / 2
    radius = float(np.linalg.norm(hi - lo) / 2)
    height = hi[2] - lo[2]
    struct.pack_into("<ff", head, 0x28, scale, hi[2] - c[2])
    struct.pack_into("<4f", head, 0x38, *c, radius)
    struct.pack_into("<6f", head, 0x48, *lo, *hi)
    maxabs = np.maximum(np.abs(lo), np.abs(hi))
    struct.pack_into("<4f", head, 0x60, maxabs[0], maxabs[1], 0.4 * height, 0.16 * height)

    # ---- material tables + skeleton name: copy up to the palette
    out = bytearray(head)
    out += t[0x8C : template.palette_offset]
    out += struct.pack("<I", len(palette))
    out += struct.pack(f"<{len(palette)}H", *palette)
    if len(palette) % 2:
        out += b"\0\0"
    old_pal_end = template.palette_offset + 4 + ((2 * len(template.palette) + 3) & ~3)
    # The matrix table after the node list starts on an absolute 16-byte boundary (the game
    # aligns before reading it), so a palette of a different length needs new zero padding.
    words_end = template.nodes_end + 8
    table = (words_end + 15) & ~15
    if any(t[words_end:table]):
        raise ValueError("template padding before the matrix table is not zero")
    out += t[old_pal_end:words_end]
    out += b"\0" * ((-len(out)) % 16)
    out += t[table : template.lod_offset]

    # ---- GPU buffers and descriptors
    lod_tables = bytearray()
    gpu = bytearray(struct.pack("<I", len(lods)))
    for subs in lods:
        vdata = bytearray()
        idata = bytearray()
        lod_tables += struct.pack("<I", len(subs))
        first_index = 0
        for sm in subs:
            stride, extra, tframe = LAYOUTS[sm.vertex_type]
            n = len(sm.positions)
            if n > 0xFFFF:
                raise ValueError("submesh exceeds 65535 vertices")
            v = np.zeros((n, stride), dtype=np.uint8)
            q = np.empty((n, 4), dtype="<i2")
            inv = np.float32(1.0) / np.float32(scale)
            if rounding == "nearest":
                q[:, :3] = np.clip(c_round(sm.positions / scale, rounding), -32767, 32767)
            else:
                q[:, :3] = np.clip(c_round(sm.positions.astype(np.float32) * inv), -32767, 32767)
            q[:, 3] = 1
            v[:, 0:8] = q.view(np.uint8).reshape(n, 8)
            uv = np.empty((n, 4), dtype="<i2")
            uv[:, 0:2] = np.clip(c_round(sm.uv0 * UV_ONE, rounding), -32767, 32767)
            uv[:, 2:4] = np.clip(c_round(sm.uv1 * UV_ONE, rounding), -32767, 32767)
            v[:, 8:16] = uv.view(np.uint8).reshape(n, 8)
            v[:, 16:20] = sm.weights
            pal = np.zeros((n, 4), dtype=np.uint8)
            for k in range(4):
                bk = sm.bones[:, k]
                live = sm.weights[:, k] > 0
                pal[live, k] = [pal_index[int(b)] for b in bk[live]]
            v[:, 20:24] = pal
            noff = 28 if extra else 24
            v[:, noff : noff + 4] = _normal_bytes(sm.normals)
            v[:, noff + 4 : noff + 8] = sm.color
            if tframe:
                v[:, noff + 8 : noff + 16] = np.array([128, 128, 128, 0] * 2, dtype=np.uint8)
            tri = sm.triangles.astype("<u2")
            voff = len(vdata)
            vdata += v.tobytes()
            idata += tri.tobytes()
            # ZModeler derives bounds from the unquantized source positions.
            bounds = struct.pack("<10f", *_bounds(sm.positions))
            fields = struct.pack(
                "<9I",
                (sm.vertex_type << 16) | sm.material,
                stride,
                0,
                voff,
                len(tri),
                len(tri) * 3,
                first_index,
                n,
                n - 1,
            )
            sub = struct.pack("<II", 0, 0) + fields[12:]
            lod_tables += bounds + struct.pack("<I", 0) + fields + struct.pack("<I", 1)
            lod_tables += sub + bounds + _name_bytes(0xCC97FA4A, "char01") + struct.pack("<HH", 0, 0xFFFF)
            first_index += len(tri) * 3
        gpu += struct.pack("<I", len(vdata)) + vdata + struct.pack("<I", len(idata)) + idata
        gpu += b"\0" * ((-len(gpu)) % 4)
    out += lod_tables + struct.pack("<I", 0) + gpu
    out += struct.pack("<II", 0, 0)
    return bytes(out)


def load_and_decode(path: Path | str):
    x = xbg_model.load(path)
    return x, *decode(x)
