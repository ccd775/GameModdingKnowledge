"""Facial expressions (vrm_face.py) for an existing char01.xbg whose face is a VRM's face mesh.

  python xbg_face.py --xbg char01.xbg --vrm model.vrm --profile face.json \
      --facial-definition char01_facial_definition.dpdx --out-dir DIR

For replacers not built by build_from_vrm.py (Karin 1.6.0: an FBX handoff from a blend of karin_picodra.vrm, with
the face weighted to Head only).  The XBG's face submesh (profile "xbg_face_material") is matched to the VRM's face
primitives (profile "vrm_face_materials") by a similarity transform: ICP over the XBG vertices, nearest VRM vertex,
Umeyama fit.  A shape key then moves each XBG vertex by its matched VRM vertex's delta through that transform.  The
eye pivots are the skin joints that carry the look keys' vertices besides the head (a VRM's humanoid eye bones may
be wrong: karin_picodra.vrm maps them to Hair_tail_L and Ahoge), or profile "eye_nodes" {"L": name, "R": name}.

Writes DIR/char01.xbg (eyes and jaw moved in the skeleton, face submesh re-weighted in every LOD that has the same
vertices in the same order; everything else as decoded, encoded with "nearest" rounding, which reproduces the mesh data exactly),
DIR/char01_facial_definition.dpdx and DIR/build_report.json (its "face" section as build_from_vrm writes it).

  {"schema": "watchdogs.xbg_face_profile.v1", "xbg_face_material": 0, "vrm_face_materials": ["Karin_Face"],
   "face": {... as in a build_from_vrm profile ...}}
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import dpdx_format  # noqa: E402
import fbx_to_xbg  # noqa: E402
import vrm_face  # noqa: E402
import vrm_fit  # noqa: E402
import vrm_model  # noqa: E402
import xbg_codec  # noqa: E402
import xbg_model  # noqa: E402
import xbg_skeleton_patch  # noqa: E402
from xbg_skeleton import Skeleton  # noqa: E402

MATCH_M = 0.001  # an XBG vertex farther than this from every aligned VRM vertex gets no shape-key motion
ICP_ROUNDS = 40


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def nearest(points: np.ndarray, queries: np.ndarray, chunk: int = 2048) -> tuple[np.ndarray, np.ndarray]:
    """Distance to and index of the nearest of `points` for every query (exact, numpy only)."""
    pp = (points ** 2).sum(1)
    dist = np.empty(len(queries))
    idx = np.empty(len(queries), np.int64)
    for a in range(0, len(queries), chunk):
        q = queries[a:a + chunk]
        d2 = (q ** 2).sum(1)[:, None] - 2.0 * q @ points.T + pp[None, :]
        k = np.argmin(d2, axis=1)
        idx[a:a + chunk] = k
        dist[a:a + chunk] = np.linalg.norm(q - points[k], axis=1)
    return dist, idx


def _neighbours(tri: np.ndarray, n: int) -> list[list[int]]:
    nb: list[set] = [set() for _ in range(n)]
    for a, b, c in tri.tolist():
        nb[a] |= {b, c}
        nb[b] |= {a, c}
        nb[c] |= {a, b}
    return [sorted(x) for x in nb]


def match_rows(face: VrmFace, xbg_pos: np.ndarray, xbg_tri: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Nearest aligned VRM row per XBG vertex.  A VRM seam keeps several rows at one position, and a shape key can
    move them apart (Karin's lid edge, up to 7 mm under blink_L): among such rows take the one whose mesh neighbours
    lie where the XBG vertex's neighbours are, so the pick never depends on how ties fall."""
    dist, near = nearest(face.aligned, xbg_pos)
    _, group = np.unique(np.round(face.aligned / 1e-7).astype(np.int64), axis=0, return_inverse=True)
    group = group.reshape(-1)
    members: dict[int, list[int]] = {}
    for row, g in enumerate(group.tolist()):
        members.setdefault(g, []).append(row)
    nb_v = _neighbours(face.triangles, len(face.aligned))
    nb_x = _neighbours(xbg_tri, len(xbg_pos))
    for v in range(len(xbg_pos)):
        cand = members[int(group[near[v]])]
        if len(cand) < 2 or not nb_x[v]:
            continue
        xs = xbg_pos[nb_x[v]]

        def score(j: int) -> float:
            if not nb_v[j]:
                return np.inf
            ys = face.aligned[nb_v[j]]
            return float(np.sqrt(((xs[:, None] - ys[None]) ** 2).sum(-1)).min(1).sum())

        near[v] = min(cand, key=lambda j: (score(j), j))
    return dist, near


def umeyama(src: np.ndarray, dst: np.ndarray) -> tuple[float, np.ndarray, np.ndarray]:
    """s, R, t with dst ~ s R src + t (least squares)."""
    ms, md = src.mean(0), dst.mean(0)
    a, b = src - ms, dst - md
    u, d, vt = np.linalg.svd(b.T @ a / len(src))
    e = np.eye(3)
    e[2, 2] = np.sign(np.linalg.det(u @ vt))
    r = u @ e @ vt
    s = float(np.trace(np.diag(d) @ e) / (a ** 2).sum(1).mean())
    return s, r, md - s * r @ ms


class VrmFace:
    """The VRM's face primitives in world rest space and their shape keys."""

    def __init__(self, m: vrm_model.Vrm, materials: list[str]):
        names = [mt.get("name") for mt in m.json["materials"]]
        self.m = m
        self.prims = [i for i, p in enumerate(m.primitives) if names[p.material] in materials]
        if not self.prims:
            raise SystemExit(f"the VRM has no primitive with material {materials}")
        pos, src, tri = [], [], []
        for i in self.prims:
            p = m.primitives[i]
            used = np.unique(p.triangles)
            w = m.world[m.prim_node[i]]
            pos.append(p.positions[used] @ w[:3, :3].T + w[:3, 3])
            tri.append(np.searchsorted(used, p.triangles) + len(src))
            src += [(i, int(v)) for v in used]
        self.positions = np.vstack(pos)
        self.source = src  # (primitive, vertex) per row
        self.triangles = np.vstack(tri)  # in rows
        self.aligned = self.positions  # on the XBG face once align() has run

    def delta(self, key: str) -> np.ndarray | None:
        """World-space displacement per row under `key`, or None if no face primitive has it."""
        out = np.zeros_like(self.positions)
        found = False
        cache = {}
        for row, (i, v) in enumerate(self.source):
            if i not in cache:
                d = self.m.morph(i, key)
                cache[i] = None if d is None else d @ self.m.world[self.m.prim_node[i]][:3, :3].T
            if cache[i] is not None:
                out[row] = cache[i][v]
                found = True
        return out if found else None

    def joint_weights(self, rows: np.ndarray) -> dict[int, float]:
        """Summed skin weight per node over the given rows."""
        acc: dict[int, float] = {}
        for row in rows:
            i, v = self.source[row]
            p = self.m.primitives[i]
            joints = self.m.skin_joints(self.m.prim_skin[i])
            for j, w in zip(p.joints[v], p.weights[v]):
                if w > 0:
                    acc[joints[int(j)]] = acc.get(joints[int(j)], 0.0) + float(w)
        return acc


def align(face: VrmFace, axes: np.ndarray, target: np.ndarray) -> tuple[float, np.ndarray, np.ndarray, dict]:
    """Similarity (s, R, t) taking VRM world positions onto the XBG face vertices."""
    src = face.positions @ axes.T
    s0 = np.sqrt(((target - target.mean(0)) ** 2).sum(1).mean() / ((src - src.mean(0)) ** 2).sum(1).mean())
    s, r, t = s0, np.eye(3), target.mean(0) - s0 * src.mean(0)
    for _ in range(ICP_ROUNDS):
        back = ((target - t) @ r) / s  # XBG vertices in (axis-turned) VRM space
        d, idx = nearest(src, back)
        keep = d <= max(3.0 * np.median(d), 1e-6)
        s, r, t = umeyama(src[idx[keep]], target[keep])
    d, idx = nearest(src, ((target - t) @ r) / s)
    stats = {"scale": s, "rotation_deg": float(np.degrees(np.arccos(np.clip((np.trace(r) - 1) / 2, -1, 1)))),
             "match_median_mm": 1000 * s * float(np.median(d)), "match_max_mm": 1000 * s * float(d.max()),
             "unmatched_vertices": int(np.count_nonzero(s * d > MATCH_M))}
    return s, r @ axes, t, stats


def eye_nodes(face: VrmFace, look: np.ndarray, side_of, node_pos, names: dict | None) -> dict[str, int]:
    """Per side, the joint on that side of the head that carries most of the look keys' weight there (the head
    joint itself sits on the middle; the face may be skinned to a copy of the humanoid head, e.g. Head_3)."""
    m = face.m
    if names:
        return {s: m.node_names.index(n) for s, n in names.items()}
    out = {}
    for s in ("L", "R"):
        acc = {n: w for n, w in face.joint_weights(np.flatnonzero(look & side_of[s](face.aligned))).items()
               if side_of[s](node_pos(n)[None])[0]}
        if not acc:
            raise SystemExit(f"no joint on the {s} side carries the look keys' vertices: set profile eye_nodes")
        out[s] = max(acc, key=lambda n: acc[n])
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="Add facial expressions to an existing char01.xbg (see vrm_face.py).")
    ap.add_argument("--xbg", required=True, type=Path)
    ap.add_argument("--vrm", required=True, type=Path)
    ap.add_argument("--profile", required=True, type=Path)
    ap.add_argument("--facial-definition", required=True, type=Path)
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--force", action="store_true")
    args = ap.parse_args()
    out = args.out_dir
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit(f"refusing to write into non-empty {out} (use --force)")
    out.mkdir(parents=True, exist_ok=True)
    profile = json.loads(args.profile.read_text(encoding="utf-8"))
    cfg = profile["face"]

    x = xbg_model.load(args.xbg)
    sk = Skeleton(args.xbg)
    scale, lods = xbg_codec.decode(x)
    mat = profile.get("xbg_face_material", 0)
    subs = [next((k for k, sm in enumerate(subs) if sm.material == mat), None) for subs in lods]
    if subs[0] is None:
        raise SystemExit(f"LOD0 has no submesh with material {mat}")
    face_sm = lods[0][subs[0]]

    # ---- the VRM's face on the XBG face
    m = vrm_model.load(args.vrm)
    vf = VrmFace(m, profile.get("vrm_face_materials", ["Karin_Face"]))
    s, lin, t, match = align(vf, vrm_fit.model_axes(m), face_sm.positions)
    vf.aligned = vf.positions @ lin.T * s + t
    dist, near = match_rows(vf, face_sm.positions, face_sm.triangles)
    matched = dist <= MATCH_M
    deltas: dict[str, np.ndarray | None] = {}

    def motion(prim: int, key: str):
        if prim != 0:
            return None
        if key not in deltas:
            d = vf.delta(key)
            deltas[key] = None if d is None else np.where(matched[:, None], (d @ lin.T * s)[near], 0.0)
        return deltas[key]

    look_keys = cfg.get("gaze", {}).get("keys", [])
    look = np.zeros(len(vf.positions), bool)
    for key in look_keys:
        d = vf.delta(key)
        if d is not None:
            look |= np.linalg.norm(d, axis=1) * s > vrm_face.GAZE_ACTIVE_M
    mid_x = sk.head("Head")[0]
    left_x = np.sign(sk.head("L_Eye")[0] - sk.head("R_Eye")[0])
    side_of = {"L": lambda p: (p[:, 0] - mid_x) * left_x > 0.01, "R": lambda p: (p[:, 0] - mid_x) * left_x < -0.01}

    def node_pos(n: int) -> np.ndarray:
        return m.world[n][:3, 3] @ lin.T * s + t

    eyes = eye_nodes(vf, look, side_of, node_pos, profile.get("eye_nodes")) if look_keys else {}
    eye_world = {k: node_pos(n) for k, n in eyes.items()}

    fit = SimpleNamespace(
        aiden_world={n: sk.head(n) for n in sk.names},
        parts=[SimpleNamespace(name=f"lod0/submesh{subs[0]}", positions=face_sm.positions, triangles=face_sm.triangles)],
        human_node={"leftEye": 0, "rightEye": 1},
        posed_joint=np.array([eye_world.get("L", sk.head("L_Eye")), eye_world.get("R", sk.head("R_Eye"))]),
        key_motion=motion,
    )
    dp =dpdx_format.load(args.facial_definition.read_bytes())
    face = vrm_face.build(fit, sk, dp, cfg)

    # ---- skeleton: moved facial bones (and their children), inverse binds follow
    world = {**fit.aiden_world, **face.world}
    patched, skel_report = xbg_skeleton_patch.patch_positions(x.data, x, sk, world)
    template_path = out / "template_face.xbg"
    template_path.write_bytes(patched)
    template = xbg_model.load(template_path)
    sk2 = Skeleton(template_path)
    for name, p in face.world.items():
        if np.abs(sk2.head(name) - p).max() > 1e-5:
            raise SystemExit(f"patched skeleton misplaces {name}")
    dpdx_bytes, dp_report = vrm_face.facial_definition(dp, sk2, face)

    # ---- weights of the face submesh, in every LOD with the same vertices
    node_b = {n: sk.b[i] for i, n in enumerate(sk.names)}
    name_of_b = {b: sk.names[sk.node_of_b[b]] for b in np.unique(face_sm.bones[face_sm.weights > 0])}
    old = [{name_of_b[int(b)]: w / 255.0 for b, w in zip(row_b, row_w) if w > 0}
           for row_b, row_w in zip(face_sm.bones, face_sm.weights)]
    new = face.apply(0, old)
    bones = np.full((len(new), 4), -1, np.int64)
    weights = np.zeros((len(new), 4), np.uint8)
    for v, d in enumerate(new):
        names, ws = fbx_to_xbg.quantize_weights(list(d.items()), 4)
        for k, (n, w) in enumerate(zip(names, ws)):
            bones[v, k] = node_b[n]
            weights[v, k] = w
    lod_report = []
    for li, k in enumerate(subs):
        if k is None:
            continue
        sm = lods[li][k]
        if not np.array_equal(sm.positions, face_sm.positions):
            lod_report.append({"lod": li, "reweighted": False, "reason": "different vertices"})
            continue
        sm.bones, sm.weights = bones.copy(), weights.copy()
        lod_report.append({"lod": li, "reweighted": True})
    palette = list(x.palette) + sorted({int(b) for b in bones[weights > 0]} - set(x.palette))
    data = xbg_codec.encode(template, lods, palette=palette, scale=scale, rounding="nearest")
    (out / "char01.xbg").write_bytes(data)
    _, back = xbg_codec.decode(xbg_model.load(out / "char01.xbg"))
    for li, (want, got) in enumerate(zip(lods, back)):
        for a, b in zip(want, got):
            same = (np.array_equal(a.positions, b.positions) and np.array_equal(a.uv0, b.uv0) and np.array_equal(a.uv1, b.uv1)
                    and np.array_equal(a.normals, b.normals) and np.array_equal(a.color, b.color)
                    and np.array_equal(a.triangles, b.triangles) and np.array_equal(a.weights, b.weights)
                    and np.array_equal(np.where(a.weights > 0, a.bones, -1), np.where(b.weights > 0, b.bones, -1)))
            if not same:
                raise SystemExit(f"readback differs: LOD{li} material {a.material}")
    (out / "char01_facial_definition.dpdx").write_bytes(dpdx_bytes)
    report = {
        "schema": "watchdogs.xbg_face.v1",
        "xbg": str(args.xbg), "xbg_sha256": sha(args.xbg.read_bytes()), "vrm": args.vrm.name,
        "vrm_sha256": sha(args.vrm.read_bytes()), "profile": str(args.profile),
        "match": {**match, "matched_vertices": int(matched.sum()), "face_vertices": len(matched)},
        "eye_nodes": {k: m.node_names[n] for k, n in eyes.items()},
        "skeleton": skel_report, "lods": lod_report, "palette": {"before": len(x.palette), "after": len(palette)},
        "out_xbg_sha256": sha(data), "readback": "PASS",
        "face": {**face.report, **dp_report, "dpdx_sha256": sha(dpdx_bytes)},
    }
    (out / "build_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("match", "eye_nodes", "lods", "palette", "out_xbg_sha256")}, indent=1))


if __name__ == "__main__":
    main()
