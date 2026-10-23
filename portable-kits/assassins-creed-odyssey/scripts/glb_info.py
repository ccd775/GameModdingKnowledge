"""Print a GLB's meshes, primitives, materials and skin joints (with world positions from the node tree).

  python glb_info.py <file.glb> [--joints]
"""
import argparse
import json
import struct
import sys

import numpy as np


def load(path):
    with open(path, "rb") as f:
        magic, ver, length = struct.unpack("<III", f.read(12))
        clen, ctype = struct.unpack("<II", f.read(8))
        doc = json.loads(f.read(clen))
    return doc


def node_matrix(n):
    if "matrix" in n:
        return np.array(n["matrix"], dtype=float).reshape(4, 4).T
    t = np.array(n.get("translation", [0, 0, 0]), dtype=float)
    x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    s = np.array(n.get("scale", [1, 1, 1]), dtype=float)
    r = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                  [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                  [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
    m = np.eye(4)
    m[:3, :3] = r * s
    m[:3, 3] = t
    return m


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("glb")
    ap.add_argument("--joints", action="store_true", help="list every skin joint with its parent and world position")
    a = ap.parse_args()
    doc = load(a.glb)
    nodes = doc.get("nodes", [])
    parent = {}
    for i, n in enumerate(nodes):
        for c in n.get("children", []):
            parent[c] = i
    world = {}

    def w(i):
        if i not in world:
            m = node_matrix(nodes[i])
            world[i] = (w(parent[i]) @ m) if i in parent else m
        return world[i]

    for m in doc.get("meshes", []):
        print("mesh", m.get("name"), "prims", len(m["primitives"]),
              "materials", [p.get("material") for p in m["primitives"]])
    for mat in doc.get("materials", []):
        print("material", mat.get("name"))
    for s in doc.get("skins", []):
        print("skin joints", len(s["joints"]))
        if a.joints:
            for j in s["joints"]:
                p = w(j)[:3, 3]
                par = nodes[parent[j]].get("name") if j in parent else "-"
                print(f"  {nodes[j].get('name'):<40} parent={par:<30} pos=({p[0]:.4f}, {p[1]:.4f}, {p[2]:.4f})")


if __name__ == "__main__":
    main()
