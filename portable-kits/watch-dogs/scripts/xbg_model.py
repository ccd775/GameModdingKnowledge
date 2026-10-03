"""Structured reader for ZModeler-produced Watch Dogs char01 XBG files.

Layout (as reverse engineered from ZModeler 3.3.1.1244 output, 2026-10-03):

  0x00   header (magic MOEG, version, global bounds, ...), 0x8C bytes
  0x8C   material path table   u32 n, n * (u32 fnv, u32 len, str+NUL padded to 4)
         material name table   u32 n, n * (name, u32 slot)
         skeleton marker u32 1, skeleton name, u32 1
         palette               u32 n, n * u16 node-b index, pad to 4
         u32 1, u32 node count, nodes (u32 0x64, 7 f32, u16 parent, u16 b, name)
  ...    opaque skeleton/physics block (constant for char01)
  lods   per LOD: u32 descriptor count, descriptors (176 bytes each)
         u32 0
  gpu    u32 buffer count, per buffer: u32 vbytes, vdata, u32 ibytes, u16 idx, pad4
  tail   u32 0, u32 0, u32 jpeg bytes, jpeg thumbnail, ...
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np


@dataclass
class Descriptor:
    offset: int
    bounds: tuple
    material: int
    vertex_type: int
    stride: int
    flags: int
    vertex_offset: int
    face_count: int
    index_count: int
    first_index: int
    vertex_count: int
    first_vertex: int
    last_vertex: int
    sub: tuple
    sub_bounds: tuple
    node_name: str
    tail: tuple


@dataclass
class Buffer:
    vertex_start: int
    vertex_bytes: int
    index_start: int
    index_bytes: int
    end: int


@dataclass
class Xbg:
    data: bytes
    palette: list[int]
    palette_offset: int
    nodes: list[dict]
    lod_offset: int
    lods: list[list[Descriptor]] = field(default_factory=list)
    nodes_end: int = 0  # offset of the u32 382, u32 424 pair; the matrix table follows 16-byte aligned
    gpu_offset: int = 0
    buffers: list[Buffer] = field(default_factory=list)

    def vertices(self, lod: int, desc: Descriptor) -> np.ndarray:
        buf = self.buffers[lod]
        start = buf.vertex_start + desc.vertex_offset
        raw = np.frombuffer(
            self.data, dtype=np.uint8, count=desc.vertex_count * desc.stride, offset=start
        )
        return raw.reshape(desc.vertex_count, desc.stride)

    def indices(self, lod: int, desc: Descriptor) -> np.ndarray:
        buf = self.buffers[lod]
        return np.frombuffer(
            self.data,
            dtype="<u2",
            count=desc.index_count,
            offset=buf.index_start + desc.first_index * 2,
        ).reshape(-1, 3)


def _name(d: bytes, p: int) -> tuple[str, int]:
    h, n = struct.unpack_from("<II", d, p)
    s = d[p + 8 : p + 8 + n].rstrip(b"\0").decode("ascii")
    return s, p + 8 + ((n + 3) & ~3)


def load(path: Path | str) -> Xbg:
    d = Path(path).read_bytes()
    p = 0x8C
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    for _ in range(n):
        _, p = _name(d, p)
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    for _ in range(n):
        _, p = _name(d, p)
        p += 4
    p += 4  # skeleton marker
    _, p = _name(d, p)
    p += 4
    palette_offset = p
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    palette = list(struct.unpack_from(f"<{n}H", d, p))
    p += (2 * n + 3) & ~3
    p += 4
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    nodes = []
    for _ in range(n):
        flags = struct.unpack_from("<I", d, p)[0]
        xf = struct.unpack_from("<7f", d, p + 4)
        parent, b = struct.unpack_from("<HH", d, p + 32)
        name, p = _name(d, p + 36)
        nodes.append({"name": name, "parent": parent, "b": b, "xf": xf, "flags": flags})

    # The LOD table follows an opaque constant block; find it from the GPU header.
    gpu = _find_gpu_header(d)
    xbg = Xbg(d, palette, palette_offset, nodes, 0)
    xbg.nodes_end = p
    xbg.gpu_offset = gpu
    xbg.buffers = _read_buffers(d, gpu)
    xbg.lod_offset, xbg.lods = _read_lods_backwards(d, gpu, len(xbg.buffers))
    return xbg


def _read_buffers(d: bytes, p: int) -> list[Buffer]:
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    out = []
    for _ in range(n):
        (vb,) = struct.unpack_from("<I", d, p)
        vs = p + 4
        (ib,) = struct.unpack_from("<I", d, vs + vb)
        is_ = vs + vb + 4
        end = is_ + ib
        out.append(Buffer(vs, vb, is_, ib, end))
        p = (end + 3) & ~3
    return out


def _find_gpu_header(d: bytes) -> int:
    # descriptor records end with "char01" node ref + u16 0 + u16 0xFFFF, then u32 0, then u32 nbuf
    marker = b"\x4a\xfa\x97\xcc\x07\x00\x00\x00char01\x00\x00\x00\x00\xff\xff\x00\x00\x00\x00"
    pos = d.rfind(marker, 0, 0x40000)
    if pos < 0:
        raise RuntimeError("descriptor table end not found")
    return pos + len(marker)


DESC_SIZE = 176


def _parse_desc(d: bytes, p: int) -> Descriptor:
    bounds = struct.unpack_from("<10f", d, p)
    vals = struct.unpack_from("<10I", d, p + 40)
    zero, tag, stride, flags, voff, faces, nidx, first, packed, last = vals
    (nsub,) = struct.unpack_from("<I", d, p + 80)
    if nsub != 1 or zero != 0:
        raise RuntimeError(f"unexpected descriptor at {p:#x}: nsub={nsub} zero={zero}")
    sub = struct.unpack_from("<8I", d, p + 84)
    sub_bounds = struct.unpack_from("<10f", d, p + 116)
    node, q = _name(d, p + 156)
    tail = struct.unpack_from("<HH", d, q)
    if q + 4 - p != DESC_SIZE:
        raise RuntimeError(f"descriptor size mismatch at {p:#x}")
    return Descriptor(
        p, bounds, tag & 0xFFFF, tag >> 16, stride, flags, voff, faces, nidx, first,
        packed & 0xFFFF, packed >> 16, last, sub, sub_bounds, node, tail,
    )


def _read_lods_backwards(d: bytes, gpu: int, nlod: int) -> tuple[int, list[list[Descriptor]]]:
    # Walk backwards: [u32 count][count * 176] per LOD, then u32 0 before gpu header.
    end = gpu - 4
    lods: list[list[Descriptor]] = []
    for _ in range(nlod):
        for count in range(1, 64):
            start = end - count * DESC_SIZE - 4
            if struct.unpack_from("<I", d, start)[0] == count:
                try:
                    descs = [_parse_desc(d, start + 4 + i * DESC_SIZE) for i in range(count)]
                except (RuntimeError, struct.error, UnicodeDecodeError):
                    continue
                lods.insert(0, descs)
                end = start
                break
        else:
            raise RuntimeError("LOD table not found")
    return end, lods
