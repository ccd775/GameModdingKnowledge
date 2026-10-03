"""Minimal binary FBX (7.x) reader: node tree, properties, objects, connections."""

from __future__ import annotations

import struct
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

MAGIC = b"Kaydara FBX Binary  \x00\x1a\x00"
ARRAY_TYPES = {"f": "<f4", "d": "<f8", "l": "<i8", "i": "<i4", "b": "u1"}


@dataclass
class Node:
    name: str
    props: list
    children: list["Node"] = field(default_factory=list)

    def find(self, name: str) -> "Node | None":
        for c in self.children:
            if c.name == name:
                return c
        return None

    def find_all(self, name: str) -> list["Node"]:
        return [c for c in self.children if c.name == name]

    def value(self, name: str):
        c = self.find(name)
        return None if c is None else c.props[0]

    def props70(self) -> dict:
        out = {}
        p = self.find("Properties70")
        if p is None:
            return out
        for c in p.children:
            out[c.props[0]] = c.props[4:]
        return out


class Reader:
    def __init__(self, data: bytes):
        if not data.startswith(MAGIC):
            raise ValueError("not a binary FBX")
        self.d = data
        self.version = struct.unpack_from("<I", data, 23)[0]
        self.wide = self.version >= 7500

    def _prop(self, p: int):
        t = chr(self.d[p])
        p += 1
        if t == "Y":
            return struct.unpack_from("<h", self.d, p)[0], p + 2
        if t == "C":
            return bool(self.d[p]), p + 1
        if t == "I":
            return struct.unpack_from("<i", self.d, p)[0], p + 4
        if t == "F":
            return struct.unpack_from("<f", self.d, p)[0], p + 4
        if t == "D":
            return struct.unpack_from("<d", self.d, p)[0], p + 8
        if t == "L":
            return struct.unpack_from("<q", self.d, p)[0], p + 8
        if t in ("S", "R"):
            n = struct.unpack_from("<I", self.d, p)[0]
            raw = self.d[p + 4 : p + 4 + n]
            return (raw.decode("utf-8", "replace") if t == "S" else raw), p + 4 + n
        if t in ARRAY_TYPES:
            count, enc, clen = struct.unpack_from("<III", self.d, p)
            raw = self.d[p + 12 : p + 12 + clen]
            if enc == 1:
                raw = zlib.decompress(raw)
            return np.frombuffer(raw, dtype=ARRAY_TYPES[t], count=count), p + 12 + clen
        raise ValueError(f"unknown property type {t!r} at {p - 1:#x}")

    def _node(self, p: int) -> tuple[Node | None, int]:
        if self.wide:
            end, nprops, _ = struct.unpack_from("<QQQ", self.d, p)
            p += 24
        else:
            end, nprops, _ = struct.unpack_from("<III", self.d, p)
            p += 12
        nlen = self.d[p]
        p += 1
        if end == 0:
            return None, p + nlen
        name = self.d[p : p + nlen].decode("ascii")
        p += nlen
        props = []
        for _ in range(nprops):
            v, p = self._prop(p)
            props.append(v)
        node = Node(name, props)
        while p < end:
            child, p = self._node(p)
            if child is None:
                break
            node.children.append(child)
        return node, end

    def root(self) -> Node:
        p = 27
        root = Node("root", [])
        while p < len(self.d):
            child, p = self._node(p)
            if child is None:
                break
            root.children.append(child)
        return root


@dataclass
class Scene:
    root: Node
    objects: dict  # id -> Node
    children: dict  # parent id -> list[(child id, prop)]
    parents: dict  # child id -> list[(parent id, prop)]

    def kids(self, oid: int, cls: str | None = None) -> list[Node]:
        out = []
        for cid, _ in self.children.get(oid, []):
            node = self.objects.get(cid)
            if node is not None and (cls is None or node.name == cls):
                out.append(node)
        return out

    def parent_ids(self, oid: int) -> list[int]:
        return [pid for pid, _ in self.parents.get(oid, [])]


def load(path: Path | str) -> Scene:
    root = Reader(Path(path).read_bytes()).root()
    objects = {}
    for obj in root.find("Objects").children:
        objects[obj.props[0]] = obj
    children: dict = {}
    parents: dict = {}
    for c in root.find("Connections").children:
        kind, child, parent = c.props[0], c.props[1], c.props[2]
        prop = c.props[3] if len(c.props) > 3 else None
        children.setdefault(parent, []).append((child, prop))
        parents.setdefault(child, []).append((parent, prop))
    return Scene(root, objects, children, parents)


def obj_name(node: Node) -> str:
    return node.props[1].split("\x00\x01")[0]
