"""Read and write the SMU physics objects inside a Watch Dogs char01.xbg (reverse engineered without ZModeler).

Physics block (after the inverse-bind table, up to the LOD table):
  u32 has_fcb [u32 size, FCB "nbCF" = RFX_Legs leg colliders] | u32 n_objects | objects | u32 n_table | table
Every 4x4 matrix in the block is 16-byte aligned to the FILE offset (zero padding).

Object (chains, jiggles; the cloth objects share the head and collider lists, the rest of a cloth is not decoded):
  u32 0, f32 params[12], u32 type, u32 sub (1 chain, 2 jiggle, 0 cloth), u32 flag
  u32 nA, A: name, align16 mat4, f32 radius                          sphere colliders
  u32 nB, B: name, align16 mat4, f32 x7
  u32 nC, C: name, align16 mat4, f32 x7 (r0, 0, 0, r1, 0, 0, length)  capsule colliders, axis = the matrix's local +Z
  u32 nD, D: name, align16 mat4, f32 x6
  u32 nE, E: i32 -1, u32 1, u16 node, u16 0, f32 x4                  point records
  u32 0 (list F)
  u32 nG, G: i32 -1, u32 1, u16 node, u16 0, f32 x8                  oriented records
  u32 nN, N: name, f32 radius, u32 flags, f32, f32                    simulated nodes
  u32 nK, K: name                                                     anchor bones
  u32 0, u32 0, u32 nL, L: u16 a, u16 b, u16 kind (padded to 4)       links
  u32 tail                                                            0, 1 or 4 in the game's files
Names are (u32 CRC-32 of the case-sensitive name, u32 length incl. NUL, bytes, padding to 4).
Node flags: bit 0 = pinned to its animated pose; bits 16-31 = index into the object's anchor list (the bone the
node is referenced to).  An index past the end of the anchor list leaves the node unsimulated.
params[1] is gravity; for chains params[2:5] act like damping and params[9] like the pull back to the animated pose.
"""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field


class Reader:
    def __init__(self, d: bytes, p: int):
        self.d, self.p = d, p

    def u32(self) -> int:
        v = struct.unpack_from("<I", self.d, self.p)[0]
        self.p += 4
        return v

    def i32(self) -> int:
        v = struct.unpack_from("<i", self.d, self.p)[0]
        self.p += 4
        return v

    def f(self, n: int) -> tuple:
        v = struct.unpack_from(f"<{n}f", self.d, self.p)
        self.p += 4 * n
        return v

    def name(self) -> str:
        h, n = struct.unpack_from("<II", self.d, self.p)
        if not 1 <= n <= 128:
            raise ValueError(f"bad name length {n} at {self.p:#x}")
        raw = self.d[self.p + 8:self.p + 8 + n]
        if raw[-1:] != b"\0":
            raise ValueError(f"name not NUL-terminated at {self.p:#x}")
        s = raw[:-1].decode("ascii")
        if name_hash(s) != h:
            raise ValueError(f"name hash mismatch for {s!r} at {self.p:#x}: {h:08x} vs {name_hash(s):08x}")
        self.p += 8 + ((n + 3) & ~3)
        return s

    def align16(self) -> None:
        pad = (-self.p) % 16
        if any(self.d[self.p:self.p + pad]):
            raise ValueError(f"nonzero alignment padding at {self.p:#x}")
        self.p += pad


def name_hash(s: str) -> int:
    """CRC-32 of the case-sensitive ASCII name."""
    return zlib.crc32(s.encode("ascii")) & 0xFFFFFFFF


@dataclass
class Obj:
    offset: int
    params: tuple
    type: int
    sub: int
    flag: int = 0
    spheres: list = field(default_factory=list)   # (bone, mat16, radius)
    capsules: list = field(default_factory=list)  # (bone, mat16, f7)
    blist: list = field(default_factory=list)     # list B: (bone, mat16, f7), meaning unknown
    dlist: list = field(default_factory=list)     # list D: (bone, mat16, f6), plane-like
    tail: int = 0
    points: list = field(default_factory=list)    # (index, vec4)
    oriented: list = field(default_factory=list)  # (index, quat4, f2)
    nodes: list = field(default_factory=list)     # (name, f, u, f, f)
    anchors: list = field(default_factory=list)
    links: list = field(default_factory=list)     # (a, b, kind)
    end: int = 0


def parse_object(r: Reader) -> Obj:
    start = r.p
    if r.u32() != 0:
        raise ValueError(f"object at {start:#x} does not start with 0")
    params = r.f(12)
    typ, sub, z = r.u32(), r.u32(), r.u32()
    if not (1 <= typ <= 16 and sub <= 16 and z <= 1):
        raise ValueError(f"unknown object header {typ},{sub},{z} at {start:#x}")
    o = Obj(start, params, typ, sub, z)
    for _ in range(r.u32()):
        bone = r.name()
        r.align16()
        m = r.f(16)
        o.spheres.append((bone, m, r.f(1)[0]))
    for _ in range(r.u32()):
        bone = r.name()
        r.align16()
        m = r.f(16)
        o.blist.append((bone, m, r.f(7)))
    for _ in range(r.u32()):
        bone = r.name()
        r.align16()
        m = r.f(16)
        o.capsules.append((bone, m, r.f(7)))
    for _ in range(r.u32()):
        bone = r.name()
        r.align16()
        m = r.f(16)
        o.dlist.append((bone, m, r.f(6)))
    for _ in range(r.u32()):
        if (r.i32(), r.u32()) != (-1, 1):
            raise ValueError(f"point record header at {r.p - 8:#x}")
        idx = r.u32()
        o.points.append((idx >> 16, idx & 0xFFFF, r.f(4)))
    if r.u32() != 0:
        raise ValueError(f"list F not empty at {r.p - 4:#x}")
    for _ in range(r.u32()):
        if (r.i32(), r.u32()) != (-1, 1):
            raise ValueError(f"oriented record header at {r.p - 8:#x}")
        idx = r.u32()
        o.oriented.append((idx >> 16, idx & 0xFFFF, r.f(3), r.f(3), r.f(2)))
    for _ in range(r.u32()):
        nm = r.name()
        a = r.f(1)[0]
        u = r.u32()
        b, c = r.f(2)
        o.nodes.append((nm, a, u, b, c))
    for _ in range(r.u32()):
        o.anchors.append(r.name())
    if (r.u32(), r.u32()) != (0, 0):
        raise ValueError(f"link header at {r.p - 8:#x}")
    n = r.u32()
    raw = struct.unpack_from(f"<{3 * n}H", r.d, r.p)
    r.p += (6 * n + 3) & ~3
    o.links = [tuple(raw[3 * i:3 * i + 3]) for i in range(n)]
    o.tail = r.u32()  # 0 or 1 in most objects, 4 in Aiden's belt chains
    if o.tail > 16:
        raise ValueError(f"object tail {o.tail} at {r.p - 4:#x}")
    o.end = r.p
    return o


def _name_bytes(s: str) -> bytes:
    raw = s.encode("ascii") + b"\0"
    return struct.pack("<II", name_hash(s), len(raw)) + raw + b"\0" * ((-len(raw)) % 4)


def write_object(o: Obj, pos: int) -> bytes:
    """Serialize an object that will start at absolute file offset `pos` (matrices are file-aligned to 16)."""
    out = bytearray()

    def align16() -> None:
        out.extend(b"\0" * ((-(pos + len(out))) % 16))

    out += struct.pack("<I", 0) + struct.pack("<12f", *o.params) + struct.pack("<3I", o.type, o.sub, o.flag)
    out += struct.pack("<I", len(o.spheres))
    for bone, m, rad in o.spheres:
        out += _name_bytes(bone)
        align16()
        out += struct.pack("<16f", *m) + struct.pack("<f", rad)
    out += struct.pack("<I", len(o.blist))
    for bone, m, f7 in o.blist:
        out += _name_bytes(bone)
        align16()
        out += struct.pack("<16f", *m) + struct.pack("<7f", *f7)
    out += struct.pack("<I", len(o.capsules))
    for bone, m, f7 in o.capsules:
        out += _name_bytes(bone)
        align16()
        out += struct.pack("<16f", *m) + struct.pack("<7f", *f7)
    out += struct.pack("<I", len(o.dlist))
    for bone, m, f6 in o.dlist:
        out += _name_bytes(bone)
        align16()
        out += struct.pack("<16f", *m) + struct.pack("<6f", *f6)
    out += struct.pack("<I", len(o.points))
    for hi, lo, v in o.points:
        out += struct.pack("<iII4f", -1, 1, (hi << 16) | lo, *v)
    out += struct.pack("<2I", 0, len(o.oriented))
    for hi, lo, off, dr, f2 in o.oriented:
        out += struct.pack("<iII8f", -1, 1, (hi << 16) | lo, *off, *dr, *f2)
    out += struct.pack("<I", len(o.nodes))
    for nm, a, u, b, c in o.nodes:
        out += _name_bytes(nm) + struct.pack("<fIff", a, u, b, c)
    out += struct.pack("<I", len(o.anchors))
    for a in o.anchors:
        out += _name_bytes(a)
    raw = b"".join(struct.pack("<3H", *link) for link in o.links)
    out += struct.pack("<3I", 0, 0, len(o.links)) + raw + b"\0" * ((-len(raw)) % 4)
    out += struct.pack("<I", o.tail)
    return bytes(out)
