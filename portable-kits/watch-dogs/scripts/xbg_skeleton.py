"""char01 skeleton from a ZModeler-style XBG: bind pose, inverse binds, posing, skinning.

  python xbg_skeleton.py char01.xbg [--joint NAME ...]
prints the worst bind @ inverse-bind residuals and the bind head of the named joints.
"""

from __future__ import annotations

import argparse
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xbg_model  # noqa: E402


def quat_to_mat(q) -> np.ndarray:
    x, y, z, w = q
    n = x * x + y * y + z * z + w * w
    s = 2.0 / n if n else 0.0
    return np.array(
        [
            [1 - s * (y * y + z * z), s * (x * y - z * w), s * (x * z + y * w)],
            [s * (x * y + z * w), 1 - s * (x * x + z * z), s * (y * z - x * w)],
            [s * (x * z - y * w), s * (y * z + x * w), 1 - s * (x * x + y * y)],
        ]
    )


def axis_angle(axis, deg) -> np.ndarray:
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    t = np.radians(deg)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * k + (1 - np.cos(t)) * (k @ k)


class Skeleton:
    def __init__(self, xbg_path: Path | str):
        x = xbg_model.load(xbg_path)
        self.nodes = x.nodes
        self.names = [n["name"] for n in x.nodes]
        self.index = {n: i for i, n in enumerate(self.names)}
        self.parent = [n["parent"] if n["parent"] != 0xFFFF else -1 for n in x.nodes]
        self.b = [n["b"] for n in x.nodes]
        n = len(self.nodes)
        self.local = np.zeros((n, 4, 4))
        for i, node in enumerate(x.nodes):
            m = np.eye(4)
            m[:3, :3] = quat_to_mat(node["xf"][3:7])
            m[:3, 3] = node["xf"][0:3]
            self.local[i] = m
        self.bind = self.globals(self.local)
        # inverse bind table: after nodes, u32 count, u32 nodes, pad16, count * 4x4 (row-vector layout)
        d = x.data
        p = self._after_nodes(x)
        count, total = struct.unpack_from("<II", d, p)
        p = (p + 8 + 15) & ~15
        raw = np.frombuffer(d, "<f4", count * 16, p).reshape(count, 4, 4).astype(np.float64)
        self.inv_bind = np.transpose(raw, (0, 2, 1))  # to column-vector convention
        self.node_of_b = {b: i for i, b in enumerate(self.b) if b < count}

    @staticmethod
    def _after_nodes(x) -> int:
        d = x.data
        p = x.palette_offset
        (n,) = struct.unpack_from("<I", d, p)
        p += 4 + ((2 * n + 3) & ~3) + 8
        for _ in range(len(x.nodes)):
            p += 36
            _, ln = struct.unpack_from("<II", d, p)
            p += 8 + ((ln + 3) & ~3)
        return p

    def globals(self, local: np.ndarray) -> np.ndarray:
        out = np.zeros_like(local)
        for i in range(len(local)):
            p = self.parent[i]
            out[i] = local[i] if p < 0 else out[p] @ local[i]
        return out

    def head(self, name: str, posed: np.ndarray | None = None) -> np.ndarray:
        g = self.bind if posed is None else posed
        return g[self.index[name], :3, 3]

    def pose(self, rotations: dict[str, np.ndarray]) -> np.ndarray:
        """rotations: node name -> 3x3 rotation applied in the node's local frame."""
        local = self.local.copy()
        for name, r in rotations.items():
            i = self.index[name]
            local[i, :3, :3] = local[i, :3, :3] @ r
        return self.globals(local)

    def skin(self, positions: np.ndarray, bones_b: np.ndarray, weights: np.ndarray, posed: np.ndarray) -> np.ndarray:
        """Linear blend skinning. bones_b: (n,k) node b indices (-1 unused), weights (n,k) floats."""
        n = len(positions)
        hom = np.c_[positions, np.ones(n)]
        out = np.zeros((n, 3))
        for k in range(bones_b.shape[1]):
            bk = bones_b[:, k]
            wk = weights[:, k]
            live = wk > 0
            for b in np.unique(bk[live]):
                sel = live & (bk == b)
                node = self.node_of_b[int(b)]
                m = posed[node] @ self.inv_bind[int(b)]
                out[sel] += wk[sel, None] * (hom[sel] @ m.T)[:, :3]
        return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Check a char01 XBG skeleton: bind @ inverse-bind residuals and joint heads.")
    ap.add_argument("xbg", type=Path)
    ap.add_argument("--joint", action="append", default=[], help="print this joint's bind head (repeatable)")
    args = ap.parse_args()
    sk = Skeleton(args.xbg)
    err = []
    for b, node in sk.node_of_b.items():
        e = np.abs(sk.bind[node] @ sk.inv_bind[b] - np.eye(4)).max()
        err.append((float(e), sk.names[node]))
    err.sort(reverse=True)
    print(f"nodes {len(sk.names)}  inverse binds {len(sk.inv_bind)}")
    print("bind @ inv_bind - I : worst", [(round(e, 6), n) for e, n in err[:5]], "median", float(np.median([e for e, _ in err])))
    for nm in args.joint:
        if nm not in sk.index:
            raise SystemExit(f"no joint named {nm!r}")
        print(nm, sk.head(nm).round(4))


if __name__ == "__main__":
    main()
