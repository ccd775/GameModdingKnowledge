"""Move char01 joints (translations only) inside an XBG: node table local positions + every inverse bind.

  python xbg_skeleton_patch.py IN.xbg TARGETS.json OUT.xbg [--force]
TARGETS.json maps joint names to new bind heads in XBG model space (metres), e.g. {"L Clavicle": [x, y, z]}.
Joints that are not listed keep their local offset, so they follow their parent rigidly.

Bone rotations stay as they are.  For each node i with new bind head p_i:
  local translation  t_i = R_parent^T (p_i - p_parent)
  inverse bind       inv_i' = inv_i @ T(-(p_i - p_i_old))     (the bind moves by a pure translation)
The inverse binds sit 16-byte aligned after the node table, indexed by the node's `b` field; the u32 before the
table gives their count (382 for char01), and nodes with a larger `b` have none.
Only body joints follow their bind position in game; facial joints (under Facial_Hook) are reset by animation.
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import xbg_model  # noqa: E402
from xbg_skeleton import Skeleton  # noqa: E402


def node_records(data: bytes, palette_offset: int, node_count: int) -> tuple[list[int], int]:
    (n,) = struct.unpack_from("<I", data, palette_offset)
    p = palette_offset + 4 + ((2 * n + 3) & ~3) + 4
    (count,) = struct.unpack_from("<I", data, p)
    if count != node_count:
        raise ValueError("node count mismatch")
    p += 4
    out = []
    for _ in range(count):
        out.append(p)
        _, ln = struct.unpack_from("<II", data, p + 36)
        p += 36 + 8 + ((ln + 3) & ~3)
    return out, p


def patch_positions(data: bytes, x, sk, world: dict[str, np.ndarray]) -> tuple[bytes, dict]:
    buf = bytearray(data)
    records, after = node_records(data, x.palette_offset, len(sk.names))
    count, total = struct.unpack_from("<II", data, after)
    table = (after + 8 + 15) & ~15
    if total != len(sk.names):
        raise ValueError("inverse-bind table does not cover every node")
    for i in range(len(sk.names)):
        if sk.parent[i] > i:
            raise ValueError("node table is not parent-first")
    moved = {}
    for i, name in enumerate(sk.names):
        new = np.asarray(world[name], float)
        old = sk.bind[i][:3, 3]
        par = sk.parent[i]
        if par < 0:
            local_t = new
        else:
            local_t = sk.bind[par][:3, :3].T @ (new - np.asarray(world[sk.names[par]], float))
        struct.pack_into("<3f", buf, records[i] + 4, *local_t.astype(np.float32))
        delta = new - old
        if np.abs(delta).max() < 1e-7:
            continue
        moved[name] = float(np.linalg.norm(delta))
        b = sk.b[i]
        if b >= total:
            continue
        off = table + 64 * b
        inv = np.frombuffer(data, "<f4", 16, off).reshape(4, 4).T.astype(np.float64)
        shift = np.eye(4)
        shift[:3, 3] = -delta
        buf[off : off + 64] = (inv @ shift).T.astype("<f4").tobytes()
    return bytes(buf), {"moved_nodes": len(moved), "max_move_m": max(moved.values()) if moved else 0.0}


def rigid_world(sk, targets: dict[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Bind heads after moving `targets`; every other joint keeps its local offset from its parent."""
    unknown = set(targets) - set(sk.names)
    if unknown:
        raise KeyError(f"unknown joints {sorted(unknown)}")
    world: dict[str, np.ndarray] = {}
    for i, name in enumerate(sk.names):
        par = sk.parent[i]
        if name in targets:
            world[name] = np.asarray(targets[name], float)
        elif par < 0:
            world[name] = sk.bind[i][:3, 3].copy()
        else:
            world[name] = world[sk.names[par]] + sk.bind[par][:3, :3] @ sk.local[i][:3, 3]
    return world


def residuals(sk) -> dict[str, float]:
    return {sk.names[n]: float(np.abs(sk.bind[n] @ sk.inv_bind[b] - np.eye(4)).max()) for b, n in sk.node_of_b.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description="Move char01 joints inside an XBG and update the inverse binds.")
    ap.add_argument("xbg", type=Path)
    ap.add_argument("targets", type=Path, help='JSON {"joint": [x, y, z]} in XBG model space')
    ap.add_argument("output", type=Path)
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    args = ap.parse_args()
    if args.output.resolve() == args.xbg.resolve():
        raise SystemExit("refusing to overwrite the input")
    if args.output.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite existing {args.output} (use --force)")
    targets = {k: np.asarray(v, float) for k, v in json.loads(args.targets.read_text(encoding="utf-8")).items()}
    x = xbg_model.load(args.xbg)
    sk = Skeleton(args.xbg)
    out, report = patch_positions(x.data, x, sk, rigid_world(sk, targets))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(out)
    after = Skeleton(args.output)
    before_res, after_res = residuals(sk), residuals(after)
    worse = {n: after_res[n] for n in after_res if after_res[n] > before_res[n] + 1e-4}
    missed = {n: float(np.linalg.norm(after.head(n) - p)) for n, p in targets.items() if np.linalg.norm(after.head(n) - p) > 1e-4}
    report.update({"targets": len(targets), "residual_regressions": worse, "missed_targets": missed})
    print(json.dumps(report, indent=1))
    if worse or missed:
        args.output.unlink()
        raise SystemExit("verification failed; output removed")


if __name__ == "__main__":
    main()
