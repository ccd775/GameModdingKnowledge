"""Rigidly rotate a whole AnvilToolkit / Blender GLB about the raw vertical axis (glTF z: the toolkit writes raw Anvil
data, Z up, without axis conversion).

  python glb_rotate.py <in.glb> <out.glb> <degrees>

Why: fit_karin.py (ACShadow) is written for Naoe's raw frame (X forward, Y left, Z up). Odyssey's raw frame is
X = character's left, -Y forward, Z up, i.e. Naoe = Rz(+90) * Odyssey. Rotate the Kassandra fit skeleton by +90 before
fitting and the exported Karin LODs by -90 before import-glb; the round trip is exact.

World W -> Q W: skinned vertex data p -> Q p (positions, normals, tangent xyz), inverse bind matrices IBM -> IBM Q^-1,
root nodes (except skinned mesh nodes, whose transform glTF ignores) L -> Q L. POSITION min/max are recomputed.
"""
import argparse
import json
import math
import struct
import sys

import numpy as np

COMP = {5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    with open(path, "rb") as f:
        data = f.read()
    magic, ver, length = struct.unpack_from("<III", data, 0)
    assert magic == 0x46546C67, "not a GLB"
    pos, doc, binbuf = 12, None, b""
    while pos < length:
        clen, ctype = struct.unpack_from("<II", data, pos)
        chunk = data[pos + 8:pos + 8 + clen]
        if ctype == 0x4E4F534A:
            doc = json.loads(chunk)
        elif ctype == 0x004E4942:
            binbuf = bytearray(chunk)
        pos += 8 + clen
    return doc, binbuf


def write_glb(path, doc, binbuf):
    js = json.dumps(doc, separators=(",", ":")).encode()
    js += b" " * (-len(js) % 4)
    binbuf = bytes(binbuf) + b"\0" * (-len(binbuf) % 4)
    total = 12 + 8 + len(js) + 8 + len(binbuf)
    with open(path, "wb") as f:
        f.write(struct.pack("<III", 0x46546C67, 2, total))
        f.write(struct.pack("<II", len(js), 0x4E4F534A) + js)
        f.write(struct.pack("<II", len(binbuf), 0x004E4942) + binbuf)


def accessor_view(doc, binbuf, ai):
    a = doc["accessors"][ai]
    assert a["componentType"] == 5126 and "sparse" not in a, a
    bv = doc["bufferViews"][a["bufferView"]]
    n = NCOMP[a["type"]]
    stride = bv.get("byteStride", 4 * n)
    base = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    return a, base, stride, n


def get(doc, binbuf, ai):
    a, base, stride, n = accessor_view(doc, binbuf, ai)
    out = np.empty((a["count"], n), dtype=np.float32)
    for i in range(a["count"]):
        out[i] = struct.unpack_from(f"<{n}f", binbuf, base + i * stride)
    return out


def put(doc, binbuf, ai, arr):
    a, base, stride, n = accessor_view(doc, binbuf, ai)
    for i in range(a["count"]):
        struct.pack_into(f"<{n}f", binbuf, base + i * stride, *[float(x) for x in arr[i]])


def quat_mul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return [aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src")
    ap.add_argument("dst")
    ap.add_argument("degrees", type=float, help="about the raw vertical axis: +90 before fitting, -90 on exported LODs")
    a = ap.parse_args()
    src, dst, deg = a.src, a.dst, a.degrees
    doc, binbuf = read_glb(src)
    t = math.radians(deg)
    Q = np.array([[math.cos(t), -math.sin(t), 0], [math.sin(t), math.cos(t), 0], [0, 0, 1]])
    q = [0.0, 0.0, math.sin(t / 2), math.cos(t / 2)]
    nodes = doc.get("nodes", [])
    skinned_meshes = {n["mesh"] for n in nodes if "mesh" in n and "skin" in n}
    skinned_nodes = {i for i, n in enumerate(nodes) if "mesh" in n and "skin" in n}
    done = set()
    for mi in skinned_meshes:
        for prim in doc["meshes"][mi]["primitives"]:
            targets = [prim["attributes"]] + prim.get("targets", [])
            for attrs in targets:
                for key in ("POSITION", "NORMAL", "TANGENT"):
                    ai = attrs.get(key)
                    if ai is None or ai in done:
                        continue
                    done.add(ai)
                    v = get(doc, binbuf, ai).astype(np.float64)
                    v[:, :3] = v[:, :3] @ Q.T
                    put(doc, binbuf, ai, v)
                    if key == "POSITION" and "min" in doc["accessors"][ai]:
                        doc["accessors"][ai]["min"] = [float(x) for x in v[:, :3].min(0)]
                        doc["accessors"][ai]["max"] = [float(x) for x in v[:, :3].max(0)]
    Qi4 = np.eye(4)
    Qi4[:3, :3] = Q.T
    for skin in doc.get("skins", []):
        ai = skin.get("inverseBindMatrices")
        if ai is None or ai in done:
            continue
        done.add(ai)
        m = get(doc, binbuf, ai).astype(np.float64)
        for i in range(len(m)):
            M = m[i].reshape(4, 4).T  # column-major
            m[i] = (M @ Qi4).T.reshape(16)
        put(doc, binbuf, ai, m)
    roots = set()
    for sc in doc.get("scenes", []):
        roots.update(sc.get("nodes", []))
    for ri in roots:
        if ri in skinned_nodes:
            continue
        n = nodes[ri]
        if "matrix" in n:
            M = np.array(n["matrix"], dtype=float).reshape(4, 4).T
            Q4 = np.eye(4)
            Q4[:3, :3] = Q
            n["matrix"] = [float(x) for x in (Q4 @ M).T.reshape(16)]
        else:
            n["translation"] = [float(x) for x in Q @ np.array(n.get("translation", [0, 0, 0]), dtype=float)]
            n["rotation"] = quat_mul(q, n.get("rotation", [0, 0, 0, 1]))
    write_glb(dst, doc, binbuf)
    print(f"rotated {src} by {deg} deg about z -> {dst} ({len(done)} accessors, {len(roots - skinned_nodes)} root nodes)")


if __name__ == "__main__":
    main()
