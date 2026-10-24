"""Watch Dogs facial definition (.dpdx, magic "Dp", version 2), e.g. char01_facial_definition.dpdx.

It holds the rest pose of the facial bones and, per facial control, each bone's delta.  The facial runtime
rebuilds the facial bones' local transforms from it, which is why moving a facial bone only in the XBG has no
effect in game (Karin_Original 0.1.1): the rest translation here must move with it.

Layout (little-endian; char01: 19,612 bytes, 100 bones, 1,169 items, 184 controls):
  0x00  u16 version (2), "Dp", u32 0
  0x08  u64 file size, u64 bone table offset (0x30), u64 item table offset, u64 control table offset
  0x28  u16 bone count, u16 item count, u32 control count
  bone (48 bytes): f32 rest quaternion (x, y, z, w), f32 rest translation (parent space, metres),
                   u32 CRC32 of the bone name, u64 offset of its first item, u64 item count
  item (12 bytes): u32 delta rotation (smallest three: 2-bit index of the omitted largest component, then the
                   other three as 10-bit values over [-1/sqrt2, 1/sqrt2]), 3 x s16 delta translation
                   (1/8192 m), u16 control index
  control: u32 name hash (names unknown)
A control at weight 1 sets a bone's local transform to rotation R_rest @ R_delta, translation t_rest + t_delta
(inferred: the eye controls turn the eyes about their own axes, control 55 opens the jaw, and the brow-raise
translations point up only in parent space).  Bone 0 (hash 8CB05FD5) and the _Neck_* bones are not under
Facial_Hook; the Wrinkle* bones carry wrinkle-map weights (8192 = 1.0).

  python dpdx_format.py FILE.dpdx [--xbg char01.xbg]
prints the tables; with --xbg, checks every rest transform against the XBG's local transforms.
"""

from __future__ import annotations

import argparse
import math
import struct
import sys
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

HEADER = 0x30
BONE = 48
ITEM = 12
UNIT = 1.0 / 8192.0  # metres per delta-translation step
NO_ROTATION = 0xDFF7FDFF  # the code vanilla items use for "no delta rotation" (each small component 511)
_K = 1.0 / math.sqrt(2.0)


def name_hash(name: str) -> int:
    return zlib.crc32(name.encode("ascii"))


def decode_quat(u: int) -> np.ndarray:
    """Smallest-three quaternion -> (x, y, z, w)."""
    largest = u >> 30
    rest = [((u >> s) & 1023) / 1023.0 * 2.0 * _K - _K for s in (20, 10, 0)]
    big = math.sqrt(max(0.0, 1.0 - sum(v * v for v in rest)))
    return np.array(rest[:largest] + [big] + rest[largest:])


def encode_quat(q) -> int:
    """(x, y, z, w) -> smallest-three; decode_quat(encode_quat(decode_quat(u))) reproduces u."""
    q = np.asarray(q, float)
    q = q / np.linalg.norm(q)
    largest = int(np.argmax(np.abs(q)))
    if q[largest] < 0:
        q = -q
    rest = [q[k] for k in range(4) if k != largest]
    a, b, c = (int(np.clip(round((v + _K) / (2.0 * _K) * 1023.0), 0, 1023)) for v in rest)
    return (largest << 30) | (a << 20) | (b << 10) | c


@dataclass
class Item:
    raw: bytes

    @classmethod
    def translation_only(cls, control: int, translation) -> Item:
        """A pure translation delta (parent space, metres)."""
        t = np.round(np.asarray(translation, float) / UNIT)
        if np.abs(t).max() > 32767:
            raise ValueError(f"delta translation {translation} out of range")
        return cls(struct.pack("<I3hH", NO_ROTATION, *(int(v) for v in t), control))

    @property
    def control(self) -> int:
        return struct.unpack_from("<H", self.raw, 10)[0]

    @property
    def rotation(self) -> np.ndarray:
        return decode_quat(struct.unpack_from("<I", self.raw, 0)[0])

    @property
    def translation(self) -> np.ndarray:
        return np.array(struct.unpack_from("<3h", self.raw, 4), float) * UNIT

    def scale_rotation(self, k: float) -> None:
        """Same axis, k times the angle."""
        q = self.rotation
        if q[3] < 0:
            q = -q
        angle = 2.0 * math.acos(min(1.0, q[3]))
        axis = q[:3] / max(np.linalg.norm(q[:3]), 1e-12)
        h = 0.5 * k * angle
        self.raw = struct.pack("<I", encode_quat([*(axis * math.sin(h)), math.cos(h)])) + self.raw[4:]


@dataclass
class Bone:
    rest_q: tuple[float, float, float, float]
    rest_t: tuple[float, float, float]
    hash: int
    items: list[Item] = field(default_factory=list)

    def delta(self, control: int) -> Item | None:
        return next((it for it in self.items if it.control == control), None)


@dataclass
class Dpdx:
    version: int
    bones: list[Bone]
    controls: list[int]

    def bone(self, name: str) -> Bone | None:
        h = name_hash(name)
        return next((b for b in self.bones if b.hash == h), None)


def load(data: bytes) -> Dpdx:
    version, magic, zero = struct.unpack_from("<H2sI", data, 0)
    size, off_b, off_i, off_c = struct.unpack_from("<4Q", data, 8)
    nb, ni, nc = struct.unpack_from("<HHI", data, 0x28)
    if magic != b"Dp" or version != 2 or zero or size != len(data) or off_b != HEADER:
        raise ValueError("not a version 2 facial definition")
    if off_i != off_b + nb * BONE or off_c != off_i + ni * ITEM or size != off_c + 4 * nc:
        raise ValueError("unexpected table layout")
    bones = []
    for k in range(nb):
        p = off_b + k * BONE
        q = struct.unpack_from("<4f", data, p)
        t = struct.unpack_from("<3f", data, p + 16)
        (h,) = struct.unpack_from("<I", data, p + 28)
        io, ic = struct.unpack_from("<2Q", data, p + 32)
        items = [Item(data[io + ITEM * j : io + ITEM * (j + 1)]) for j in range(ic)]
        bones.append(Bone(q, t, h, items))
    controls = list(struct.unpack_from(f"<{nc}I", data, off_c))
    return Dpdx(version, bones, controls)


def dump(d: Dpdx) -> bytes:
    """Bytes in the vanilla layout: bones, then their items in bone order, then the control hashes."""
    nb = len(d.bones)
    ni = sum(len(b.items) for b in d.bones)
    off_i = HEADER + nb * BONE
    off_c = off_i + ni * ITEM
    size = off_c + 4 * len(d.controls)
    out = bytearray(size)
    struct.pack_into("<H2sI4Q", out, 0, d.version, b"Dp", 0, size, HEADER, off_i, off_c)
    struct.pack_into("<HHI", out, 0x28, nb, ni, len(d.controls))
    p = off_i
    for k, b in enumerate(d.bones):
        r = HEADER + k * BONE
        struct.pack_into("<4f3fI2Q", out, r, *b.rest_q, *b.rest_t, b.hash, p, len(b.items))
        for it in b.items:
            out[p : p + ITEM] = it.raw
            p += ITEM
    struct.pack_into(f"<{len(d.controls)}I", out, off_c, *d.controls)
    return bytes(out)


def check_against(d: Dpdx, sk) -> dict:
    """Largest difference between each named rest transform and the skeleton's local transform."""
    import xbg_skeleton

    by_hash = {name_hash(n): i for i, n in enumerate(sk.names)}
    worst_t, worst_r, missing = 0.0, 0.0, []
    per_bone = {}
    for b in d.bones:
        i = by_hash.get(b.hash)
        if i is None:
            missing.append(f"{b.hash:08X}")
            continue
        dt = float(np.abs(np.array(b.rest_t) - sk.local[i][:3, 3]).max())
        dr = float(np.abs(xbg_skeleton.quat_to_mat(b.rest_q) - sk.local[i][:3, :3]).max())
        per_bone[sk.names[i]] = dt
        worst_t, worst_r = max(worst_t, dt), max(worst_r, dr)
    return {"bones": len(d.bones), "unnamed": missing, "max_translation_diff_m": worst_t,
            "max_rotation_diff": worst_r, "per_bone_translation_diff_m": per_bone}


def main() -> None:
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    ap = argparse.ArgumentParser(description="Print a Watch Dogs facial definition (.dpdx).")
    ap.add_argument("dpdx", type=Path)
    ap.add_argument("--xbg", type=Path, default=None, help="compare the rest pose with this char01.xbg (ZModeler layout)")
    args = ap.parse_args()
    data = args.dpdx.read_bytes()
    d = load(data)
    print(f"version {d.version}, {len(d.bones)} bones, {sum(len(b.items) for b in d.bones)} items, "
          f"{len(d.controls)} controls, round trip {'exact' if dump(d) == data else 'DIFFERS'}")
    names = {}
    if args.xbg:
        from xbg_skeleton import Skeleton

        sk = Skeleton(args.xbg)
        names = {name_hash(n): n for n in sk.names}
        rep = check_against(d, sk)
        print({k: v for k, v in rep.items() if k != "per_bone_translation_diff_m"})
    for b in d.bones:
        ctrls = " ".join(str(it.control) for it in b.items)
        print(f"{names.get(b.hash, f'{b.hash:08X}'):24s} t_cm {np.round(np.array(b.rest_t) * 100, 2)} controls {ctrls}")


if __name__ == "__main__":
    main()
