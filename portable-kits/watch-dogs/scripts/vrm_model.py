"""Minimal glTF-binary / VRM reader: nodes, skins, skinned mesh primitives, materials and images.

VRM 1.0 (VRMC_vrm) and VRM 0.x (VRM) humanoids are both read; VRM 0.x thumb names are renamed to the
VRM 1.0 names (Proximal -> Metacarpal, Intermediate -> Proximal).  Facing is left to the caller
(VRM 0.x models face -Z, VRM 1.0 models face +Z).
"""

from __future__ import annotations

import json
import struct
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

COMPONENT = {5120: "<i1", 5121: "<u1", 5122: "<i2", 5123: "<u2", 5125: "<u4", 5126: "<f4"}
WIDTH = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}
NORM_DIV = {5120: 127.0, 5121: 255.0, 5122: 32767.0, 5123: 65535.0}


@dataclass
class Primitive:
    mesh: str
    index: int
    material: int
    positions: np.ndarray  # (n,3) mesh-node space
    normals: np.ndarray
    uv0: np.ndarray
    joints: np.ndarray  # (n,k) indices into the skin's joint list
    weights: np.ndarray  # (n,k)
    triangles: np.ndarray  # (t,3)
    color: np.ndarray | None = None


@dataclass
class Vrm:
    json: dict
    bin: bytes
    node_names: list[str]
    parent: list[int]
    local: np.ndarray  # (n,4,4)
    world: np.ndarray  # (n,4,4) rest pose
    humanoid: dict[str, int]  # VRM humanoid bone -> node index
    primitives: list[Primitive] = field(default_factory=list)
    prim_skin: list[int] = field(default_factory=list)
    prim_node: list[int] = field(default_factory=list)

    def accessor(self, i: int) -> np.ndarray:
        return read_accessor(self.json, self.bin, i)

    def image_bytes(self, i: int) -> bytes:
        bv = self.json["bufferViews"][self.json["images"][i]["bufferView"]]
        o = bv.get("byteOffset", 0)
        return self.bin[o : o + bv["byteLength"]]

    def skin_joints(self, s: int) -> list[int]:
        return self.json["skins"][s]["joints"]

    def inverse_binds(self, s: int) -> np.ndarray:
        m = self.accessor(self.json["skins"][s]["inverseBindMatrices"]).reshape(-1, 4, 4)
        return np.transpose(m, (0, 2, 1)).astype(np.float64)  # glTF is column-major


def read_accessor(j: dict, binary: bytes, i: int) -> np.ndarray:
    a = j["accessors"][i]
    width = WIDTH[a["type"]]
    dtype = np.dtype(COMPONENT[a["componentType"]])
    count = a["count"]
    if "bufferView" in a:
        bv = j["bufferViews"][a["bufferView"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        stride = bv.get("byteStride", 0) or dtype.itemsize * width
        raw = np.frombuffer(binary, np.uint8, stride * (count - 1) + dtype.itemsize * width, off)
        out = np.lib.stride_tricks.as_strided(
            raw.view(np.uint8), shape=(count, width * dtype.itemsize), strides=(stride, 1)
        ).copy().view(dtype).reshape(count, width)
    else:
        out = np.zeros((count, width), dtype)
    if "sparse" in a:
        sp = a["sparse"]
        iv = j["bufferViews"][sp["indices"]["bufferView"]]
        idx = np.frombuffer(binary, COMPONENT[sp["indices"]["componentType"]], sp["count"],
                            iv.get("byteOffset", 0) + sp["indices"].get("byteOffset", 0))
        vv = j["bufferViews"][sp["values"]["bufferView"]]
        val = np.frombuffer(binary, dtype, sp["count"] * width, vv.get("byteOffset", 0) + sp["values"].get("byteOffset", 0))
        out = out.copy()
        out[idx.astype(np.int64)] = val.reshape(-1, width)
    if a.get("normalized") and a["componentType"] in NORM_DIV:
        out = out.astype(np.float64) / NORM_DIV[a["componentType"]]
    return out


def _trs(node: dict) -> np.ndarray:
    if "matrix" in node:
        return np.array(node["matrix"], float).reshape(4, 4).T
    m = np.eye(4)
    x, y, z, w = node.get("rotation", [0, 0, 0, 1])
    r = np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])
    s = np.array(node.get("scale", [1, 1, 1]), float)
    m[:3, :3] = r * s
    m[:3, 3] = node.get("translation", [0, 0, 0])
    return m


def load(path: Path | str) -> Vrm:
    d = Path(path).read_bytes()
    magic, _ver, _len = struct.unpack_from("<4sII", d, 0)
    if magic != b"glTF":
        raise ValueError("not a glTF binary")
    clen, _ = struct.unpack_from("<I4s", d, 12)
    j = json.loads(d[20 : 20 + clen])
    p = 20 + clen
    blen, btype = struct.unpack_from("<I4s", d, p)
    binary = d[p + 8 : p + 8 + blen]
    nodes = j["nodes"]
    n = len(nodes)
    parent = [-1] * n
    for i, nd in enumerate(nodes):
        for c in nd.get("children", []):
            parent[c] = i
    local = np.array([_trs(nd) for nd in nodes])
    world = np.zeros_like(local)
    done = [False] * n

    def solve(i):
        if done[i]:
            return world[i]
        world[i] = local[i] if parent[i] < 0 else solve(parent[i]) @ local[i]
        done[i] = True
        return world[i]

    for i in range(n):
        solve(i)
    ext = j.get("extensions", {})
    vrm = ext.get("VRMC_vrm") or ext.get("VRM") or {}
    hb = vrm.get("humanoid", {}).get("humanBones", {})
    if isinstance(hb, dict):
        humanoid = {k: v["node"] for k, v in hb.items() if v.get("node", -1) >= 0}
    else:
        humanoid = {b["bone"]: b["node"] for b in hb if b.get("node", -1) >= 0}
    if "VRMC_vrm" not in ext and "VRM" in ext:  # VRM 0.x thumb names -> VRM 1.0
        for side in ("left", "right"):
            ren = {f"{side}ThumbProximal": f"{side}ThumbMetacarpal", f"{side}ThumbIntermediate": f"{side}ThumbProximal"}
            old = {key: humanoid.pop(key) for key in list(ren) if key in humanoid}
            humanoid.update({ren[key]: node for key, node in old.items()})
    model = Vrm(j, binary, [nd.get("name", f"node{i}") for i, nd in enumerate(nodes)], parent, local, world, humanoid)
    for ni, nd in enumerate(nodes):
        if "mesh" not in nd:
            continue
        mesh = j["meshes"][nd["mesh"]]
        for pi, prim in enumerate(mesh["primitives"]):
            at = prim["attributes"]
            pos = read_accessor(j, binary, at["POSITION"]).astype(np.float64)
            nrm = read_accessor(j, binary, at["NORMAL"]).astype(np.float64) if "NORMAL" in at else np.zeros_like(pos)
            uv = read_accessor(j, binary, at["TEXCOORD_0"]).astype(np.float64) if "TEXCOORD_0" in at else np.zeros((len(pos), 2))
            joints, weights = [], []
            for k in range(4):
                if f"JOINTS_{k}" in at:
                    joints.append(read_accessor(j, binary, at[f"JOINTS_{k}"]).astype(np.int64))
                    weights.append(read_accessor(j, binary, at[f"WEIGHTS_{k}"]).astype(np.float64))
            jt = np.hstack(joints) if joints else np.zeros((len(pos), 0), np.int64)
            wt = np.hstack(weights) if weights else np.zeros((len(pos), 0))
            tri = read_accessor(j, binary, prim["indices"]).reshape(-1, 3).astype(np.int64)
            col = read_accessor(j, binary, at["COLOR_0"]).astype(np.float64) if "COLOR_0" in at else None
            model.primitives.append(Primitive(mesh.get("name", f"mesh{nd['mesh']}"), pi, prim.get("material", -1),
                                              pos, nrm, uv, jt, wt, tri, col))
            model.prim_skin.append(nd.get("skin", -1))
            model.prim_node.append(ni)
    return model
