"""Dump a DD2 collision shape preset (.clsp.3): shape, joint(s), flags and geometry per preset.

Layout (REE-Lib ClspFile): "CLSP", count, data offset; per preset 112 bytes: shape type u32, joint hash u32, pair joint
hash u32, 4 pad, flags1 i32, flags2 i32, 8 pad, then 80 bytes of shape (Sphere pos+r / Capsule p0,p1,r (16-aligned) /
TaperedCapsule p0,r0,p1,r1 / Box). Joint hashes are MurMur3 (seed 0xffffffff) of the UTF-16LE name; names come from a
meshinfo json (DD2Tool meshinfo).

usage: python clsp_dump.py <file.clsp.3> <meshinfo.json> [--json out.json]
"""
import argparse
import json
import struct


def murmur3(data, seed=0xFFFFFFFF):
    c1, c2 = 0xCC9E2D51, 0x1B873593
    h = seed
    n = len(data) // 4
    for i in range(n):
        k = struct.unpack_from("<I", data, i * 4)[0]
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
        h = ((h << 13) | (h >> 19)) & 0xFFFFFFFF
        h = (h * 5 + 0xE6546B64) & 0xFFFFFFFF
    tail = data[n * 4:]
    k = 0
    for i, b in enumerate(tail):
        k |= b << (8 * i)
    if tail:
        k = (k * c1) & 0xFFFFFFFF
        k = ((k << 15) | (k >> 17)) & 0xFFFFFFFF
        k = (k * c2) & 0xFFFFFFFF
        h ^= k
    h ^= len(data)
    h ^= h >> 16
    h = (h * 0x85EBCA6B) & 0xFFFFFFFF
    h ^= h >> 13
    h = (h * 0xC2B2AE35) & 0xFFFFFFFF
    h ^= h >> 16
    return h


def name_hash(s):
    return murmur3(s.encode("utf-16-le"))


SHAPES = {0: "Sphere", 1: "Capsule", 2: "Box", 3: "TaperedCapsule", 4: "Plane"}


def parse(path, names):
    b = open(path, "rb").read()
    magic, count, off = struct.unpack_from("<IiQ", b, 0)
    assert magic == 0x50534C43, hex(magic)
    out = []
    for i in range(count):
        o = off + i * 112
        st, h1, h2, _, f1, f2 = struct.unpack_from("<IIIIii", b, o)
        s = o + 32
        if st == 0:
            geo = {"pos": struct.unpack_from("<3f", b, s), "r": struct.unpack_from("<f", b, s + 12)[0]}
        elif st == 1:
            geo = {"p0": struct.unpack_from("<3f", b, s), "p1": struct.unpack_from("<3f", b, s + 16),
                   "r": struct.unpack_from("<f", b, s + 32)[0]}
        elif st == 3:
            geo = {"p0": struct.unpack_from("<3f", b, s), "r0": struct.unpack_from("<f", b, s + 12)[0],
                   "p1": struct.unpack_from("<3f", b, s + 16), "r1": struct.unpack_from("<f", b, s + 28)[0]}
        else:
            geo = {"raw": struct.unpack_from("<20f", b, s)}
        out.append({"i": i, "shape": SHAPES.get(st, st), "joint": names.get(h1, hex(h1)), "pair": names.get(h2, hex(h2)),
                    "flags1": f1, "flags2": f2, **{k: [round(x, 4) for x in v] if isinstance(v, tuple) else round(v, 4)
                                                   for k, v in geo.items()}})
    return out


def main():
    ap = argparse.ArgumentParser(description="Dump a DD2 collision shape preset (.clsp.3).")
    ap.add_argument("clsp", help=".clsp.3 file")
    ap.add_argument("meshinfo", help="DD2Tool meshinfo json of the mesh whose joints the presets use")
    ap.add_argument("--json", dest="out_json", help="also write the rows to this json file")
    a = ap.parse_args()
    mi = json.load(open(a.meshinfo, encoding="utf-8"))
    names = {name_hash(bn["name"]): bn["name"] for bn in mi["bones"]}
    names[name_hash("")] = "<none>"
    rows = parse(a.clsp, names)
    for r in rows:
        print(r)
    if a.out_json:
        json.dump(rows, open(a.out_json, "w"), indent=1)


if __name__ == "__main__":
    main()
