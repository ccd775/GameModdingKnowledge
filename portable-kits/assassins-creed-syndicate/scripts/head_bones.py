"""List the bones a GLB mesh is skinned to, with their weighted vertex centroids (to identify unnamed facial bones).

  python head_bones.py <file.glb> <mesh name> [--min 0.3]

Prints, per joint with weight >= --min on some vertex: name, parent, vertex count, joint world position and the
centroid / extent of its vertices (GLB frame), sorted by height.
"""
import argparse
import json
import struct

import numpy as np

from glb_info import node_matrix

CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def load(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 12)[0]
    doc = json.loads(d[20:20 + n])
    bin_ = d[20 + n + 8:]
    return doc, bin_


def acc(doc, bin_, i):
    a = doc["accessors"][i]
    v = doc["bufferViews"][a["bufferView"]]
    dt = np.dtype(CT[a["componentType"]])
    k = NC[a["type"]]
    off = v.get("byteOffset", 0) + a.get("byteOffset", 0)
    stride = v.get("byteStride", dt.itemsize * k)
    raw = np.frombuffer(bin_, np.uint8, count=stride * (a["count"] - 1) + dt.itemsize * k, offset=off)
    out = np.lib.stride_tricks.as_strided(raw, (a["count"], dt.itemsize * k), (stride, 1)).copy().view(dt).reshape(a["count"], k)
    if a.get("normalized") and dt != np.float32:
        out = out.astype(float) / np.iinfo(dt).max
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("glb")
    ap.add_argument("mesh_name")
    ap.add_argument("--min", type=float, default=0.3, help="lowest vertex weight that counts")
    a = ap.parse_args()
    path, mesh_name, wmin = a.glb, a.mesh_name, a.min
    doc, bin_ = load(path)
    nodes = doc["nodes"]
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    W = {}

    def world(i):
        if i not in W:
            W[i] = (world(parent[i]) @ node_matrix(nodes[i])) if i in parent else node_matrix(nodes[i])
        return W[i]
    mi = next(i for i, m in enumerate(doc["meshes"]) if m.get("name") == mesh_name)
    ni = next(i for i, n in enumerate(nodes) if n.get("mesh") == mi)
    joints = doc["skins"][nodes[ni]["skin"]]["joints"]
    P, J, Wt = [], [], []
    for pr in doc["meshes"][mi]["primitives"]:
        at = pr["attributes"]
        P.append(acc(doc, bin_, at["POSITION"]))
        J.append(acc(doc, bin_, at["JOINTS_0"]))
        Wt.append(acc(doc, bin_, at["WEIGHTS_0"]))
    P, J, Wt = np.concatenate(P), np.concatenate(J), np.concatenate(Wt).astype(float)
    P = (world(ni) @ np.c_[P, np.ones(len(P))].T).T[:, :3]
    rows = []
    for j in np.unique(J[Wt >= wmin]):
        sel = ((J == j) & (Wt >= wmin)).any(1)
        pts = P[sel]
        n = nodes[joints[j]]
        pn = nodes[parent[joints[j]]].get("name", "?") if joints[j] in parent else "-"
        rows.append((pts[:, 2].mean(), n.get("name"), pn, sel.sum(), world(joints[j])[:3, 3], pts.mean(0), np.ptp(pts, 0)))
    for z, name, pn, cnt, jp, c, e in sorted(rows, key=lambda r: -r[0]):
        f = lambda v: "(" + ", ".join(f"{x:+.3f}" for x in v) + ")"
        print(f"{name:24s} <- {pn:22s} n={cnt:5d} joint {f(jp)} verts {f(c)} ext {f(e)}")


if __name__ == "__main__":
    main()
