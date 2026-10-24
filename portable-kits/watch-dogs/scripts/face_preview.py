"""Offline preview of facial controls on a built char01.xbg + char01_facial_definition.dpdx.

  python face_preview.py OUT_DIR [--controls 32 36 55 42 50] [--obj DIR]

OUT_DIR holds the build's char01.xbg and char01_facial_definition.dpdx.  Each control is applied at weight 1 the
way the game is assumed to (dpdx_format.py): facial bones get local (R_rest R_delta, t_rest + t_delta), every
other bone keeps the XBG bind, and vertices are skinned with the XBG's inverse binds.  Prints, per control, how
far the skinned vertices move and through which bones, plus the rest-pose error (dpdx rest vs XBG bind) of every
weighted facial bone.  --obj writes the submeshes that carry facial weights, at rest and per control.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dpdx_format  # noqa: E402
import xbg_codec  # noqa: E402
import xbg_model  # noqa: E402
from xbg_skeleton import Skeleton, quat_to_mat  # noqa: E402


def pose(sk: Skeleton, dp: dpdx_format.Dpdx, control: int | None) -> np.ndarray:
    """World matrices of every node with the dpdx rest pose and `control` at weight 1."""
    by_hash = {b.hash: b for b in dp.bones}
    world = np.zeros((len(sk.names), 4, 4))
    for i, name in enumerate(sk.names):
        local = sk.local[i].copy()
        b = by_hash.get(dpdx_format.name_hash(name))
        if b is not None:
            r = quat_to_mat(b.rest_q)
            t = np.array(b.rest_t, float)
            it = b.delta(control) if control is not None else None
            if it is not None:
                r = r @ quat_to_mat(it.rotation)
                t = t + it.translation
            local[:3, :3], local[:3, 3] = r, t
        par = sk.parent[i]
        world[i] = local if par < 0 else world[par] @ local
    return world


def skin(sub, sk: Skeleton, world: np.ndarray) -> np.ndarray:
    mats = {b: world[sk.node_of_b[b]] @ sk.inv_bind[b] for b in np.unique(sub.bones[sub.bones >= 0])}
    out = np.zeros_like(sub.positions)
    h = np.c_[sub.positions, np.ones(len(sub.positions))]
    for k in range(4):
        for b in np.unique(sub.bones[:, k][sub.bones[:, k] >= 0]):
            sel = sub.bones[:, k] == b
            out[sel] += (sub.weights[sel, k, None] / 255.0) * (h[sel] @ mats[b].T)[:, :3]
    return out


def write_obj(path: Path, pos: np.ndarray, tri: np.ndarray) -> None:
    lines = [f"v {x:.6f} {y:.6f} {z:.6f}" for x, y, z in pos]
    lines += [f"f {a + 1} {b + 1} {c + 1}" for a, b, c in tri]
    path.write_text("\n".join(lines) + "\n", encoding="ascii")


def main() -> None:
    ap = argparse.ArgumentParser(description="Preview facial controls on a built char01.xbg (offline).")
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--controls", type=int, nargs="*", default=[32, 36, 55, 42, 50])
    ap.add_argument("--obj", type=Path, default=None)
    args = ap.parse_args()
    xbg = args.out_dir / "char01.xbg"
    sk = Skeleton(xbg)
    dp = dpdx_format.load((args.out_dir / "char01_facial_definition.dpdx").read_bytes())
    _, lods = xbg_codec.decode(xbg_model.load(xbg))
    facial = {dpdx_format.name_hash(n) for n in sk.names} & {b.hash for b in dp.bones}
    facial_b = {sk.b[i] for i, n in enumerate(sk.names) if dpdx_format.name_hash(n) in facial and sk.b[i] < len(sk.inv_bind)}
    subs = [(k, s) for k, s in enumerate(lods[0]) if np.isin(s.bones, list(facial_b)).any()]
    rest_world = pose(sk, dp, None)
    for k, s in subs:
        used = sorted({sk.names[sk.node_of_b[b]] for b in np.unique(s.bones[np.isin(s.bones, list(facial_b))])})
        err = {n: float(np.abs(rest_world[sk.index[n]] @ sk.inv_bind[sk.b[sk.index[n]]] - np.eye(4))[:3].max()) for n in used}
        moved_rest = np.linalg.norm(skin(s, sk, rest_world) - s.positions, axis=1)
        print(f"submesh {k} (material {s.material}, {len(s.positions)} vertices): facial bones {used}")
        print(f"  rest pose: largest bind error {max(err.values()):.4f} ({max(err, key=err.get)}), "
              f"largest vertex shift {1000 * moved_rest.max():.2f} mm")
        if args.obj:
            args.obj.mkdir(parents=True, exist_ok=True)
            write_obj(args.obj / f"sub{k}_rest.obj", s.positions, s.triangles)
        for c in args.controls:
            p = skin(s, sk, pose(sk, dp, c))
            d = np.linalg.norm(p - skin(s, sk, rest_world), axis=1)
            mv = d > 0.0005
            print(f"  control {c:3d}: {int(mv.sum()):5d} vertices move > 0.5 mm, max {1000 * d.max():6.2f} mm, "
                  f"median of those {1000 * np.median(d[mv]) if mv.any() else 0:5.2f} mm")
            if args.obj:
                write_obj(args.obj / f"sub{k}_control{c}.obj", p, s.triangles)


if __name__ == "__main__":
    main()
