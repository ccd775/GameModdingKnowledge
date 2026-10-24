"""Facial expressions for char01 from a VRM's shape keys (profile section "face").

The game drives Aiden's facial bones through char01_facial_definition.dpdx (dpdx_format.py): each facial control
is a delta on the bones' rest transforms.  A facial bone moved only in the XBG is put back by that file
(Karin_Original 0.1.1), so a moved bone needs the same rest translation in both.  This module
  1. puts L_Eye / R_Eye on the model's eye joints and the jaw pivot where the jaw-open control best reproduces her
     jaw-open key (grid search in the head's up/forward plane, then a finer grid); each vertex the key moves gets
     a share (0..1) of _Jaw, solved per vertex so that the control at weight 1 moves it like key x gain, smoothed
     over the mesh;
  2. makes the blink a translation, like the shape key itself.  A lid turned about a pivot (Aiden's rig) does not
     close an anime eye: the shares that fit the lid's edge leave it short and sink the lid behind the iris layer
     (Karin_Original 1.1.0-test, in game: the eye did not close).  So two upper-lid bones (_ELid_U, _EPuf_U) get
     translations spanning the directions her upper lid moves in, the lower lid (_ELid_D) one translation for
     the vertices the key moves the other way, and every vertex non-negative shares solved per vertex;
  3. gives the eye layers one constant share of the eye bone per eye from her look keys (per-vertex shares would
     tear the iris), fitted on the front layer of the eye (the visible one), times gaze "gain": an anime iris is
     several times wider than Aiden's, so moving it as far as he moves his barely shows (1.1.0-test);
  4. rewrites the dpdx: moved bones' rest translations from the patched XBG (checked against every named rest
     translation), and the lid bones' items.  The blink control gets the translations above.  The upper lid
     follows the other controls that close Aiden's upper lid (looking down), by the fraction of a blink they turn
     it, times blink "follow_scale" (default 0.5); controls that open his lid wider are left out, since an anime
     lid has nothing to show above its rest.  The lid bones' other items are dropped.
Children of the moved bones (pupils, everything under _Jaw) keep their local offsets.  Weights go only to the lid
bones above, _Jaw and the eye bones; the other facial bones move with the head as before.

Controls (indices into the dpdx control table, identified from the bones they move): 32 / 36 close the
left / right upper lid (_ELid_U 39 degrees), 55 opens the jaw (20 degrees), 42 / 45 and 46 / 49 turn one eye
sideways, 50 / 51 turn both eyes down / up.  Each look key is paired with the gaze control that moves its
vertices most alike.

  "face": {"blink": {"L": "blink_L", "R": "blink_R", "gain": 1.0, "follow_scale": 0.5}
                     (or {"key": "blink"} split by side),
           "jaw": {"key": "kuchi_A", "gain": 1.0},
           "gaze": {"keys": ["LookLeft", "LookRight", "LookUp", "LookDown"], "gain": 1.0}}
Any of the three may be left out.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations

import numpy as np

import dpdx_format
import vrm_fit
import xbg_skeleton

BLINK = {"L": 32, "R": 36}
JAW = 55
GAZE = {"L": (42, 45, 50, 51), "R": (46, 49, 50, 51)}
UPPER_LID = {"L": ("_ELid_U_L", "_EPuf_U_L"), "R": ("_ELid_U_R", "_EPuf_U_R")}  # [0]: Aiden's upper lid
LOWER_LID = {"L": "_ELid_D_L", "R": "_ELid_D_R"}
EYE = {"L": "L_Eye", "R": "R_Eye"}
HUMAN_EYE = {"L": "leftEye", "R": "rightEye"}
ACTIVE_M = 0.0005  # a key moves a vertex by more than this: the vertex takes part in the fit
GAZE_ACTIVE_M = 0.0003
SMOOTH_PASSES = 2
MIN_FOLLOW = 0.01  # smaller fractions of a blink are left out


@dataclass
class LidMove:
    bone: str
    side: str
    move: np.ndarray  # world translation at blink weight 1
    follow: bool  # also follows the controls that close Aiden's upper lid


@dataclass
class FaceRig:
    world: dict[str, np.ndarray]  # new bind heads of the moved bones and their descendants
    moved: list[str]  # bones whose rest translation changes in the dpdx
    shares: dict[int, dict[str, np.ndarray]] = field(default_factory=dict)  # part -> bone -> per-vertex share
    report: dict = field(default_factory=dict)
    lids: list[LidMove] = field(default_factory=list)
    follow_scale: float = 0.5

    def apply(self, part_index: int, weights: list[dict[str, float]]) -> list[dict[str, float]]:
        """Per-vertex {bone: weight} with the facial shares taken out of the vertex's other weights."""
        shares = self.shares.get(part_index)
        if not shares:
            return weights
        total = np.sum(list(shares.values()), axis=0)
        scale = np.where(total > 1.0, 1.0 / np.maximum(total, 1e-12), 1.0)
        out = []
        for v, d in enumerate(weights):
            s = float(min(total[v], 1.0))
            if s <= 0.0:
                out.append(d)
                continue
            nd = {k: w * (1.0 - s) for k, w in d.items()}
            for bone, arr in shares.items():
                w = float(arr[v] * scale[v])
                if w > 0.0:
                    nd[bone] = nd.get(bone, 0.0) + w
            out.append(nd)
        return out


def _bone_motion(dp: dpdx_format.Dpdx, sk, name: str, control: int):
    """(rotation, translation) a control applies to a bone, in world axes, about the bone's own head.

    The local transform becomes (R_rest R_delta, t_rest + t_delta); for a bone whose parent the control leaves
    alone this moves world points by x' = Q (x - head) + head + d with Q = F R_rest R_delta R_rest^T F^T and
    d = F t_delta, F being the parent's world rotation."""
    b = dp.bone(name)
    i = sk.index[name]
    par = sk.parent[i]
    pb = dp.bone(sk.names[par])
    if pb is not None and pb.delta(control) is not None:
        raise ValueError(f"control {control} also moves {sk.names[par]}, the parent of {name}")
    it = b.delta(control) if b is not None else None
    if it is None:
        return np.eye(3), np.zeros(3)
    frame = sk.bind[par][:3, :3]
    rl = xbg_skeleton.quat_to_mat(b.rest_q)
    q = frame @ rl @ xbg_skeleton.quat_to_mat(it.rotation) @ rl.T @ frame.T
    return q, frame @ it.translation


def _shares(q, d, pivot, pos, target):
    """Closed-form share in [0, 1] per vertex and the summed squared residual."""
    disp = (pos - pivot) @ (q - np.eye(3)).T + d
    dd = np.einsum("ij,ij->i", disp, disp)
    w = np.clip(np.einsum("ij,ij->i", disp, target) / np.maximum(dd, 1e-18), 0.0, 1.0)
    res = target - w[:, None] * disp
    return w, float(np.einsum("ij,ij->", res, res))


def _search(q, d, pos, target, centre, up, fwd, coarse, fine):
    """Pivot in centre + a*up + b*fwd minimizing the residual: coarse grid, then a fine grid around the best."""
    def scan(c0, ra, rb, step):
        best = None
        for a in np.arange(ra[0], ra[1] + 1e-9, step):
            for b in np.arange(rb[0], rb[1] + 1e-9, step):
                p = c0 + a * up + b * fwd
                _, r = _shares(q, d, p, pos, target)
                if best is None or r < best[0]:
                    best = (r, p)
        return best

    _, p = scan(centre, coarse[0], coarse[1], coarse[2])
    r, p = scan(p, (-fine[0], fine[0]), (-fine[0], fine[0]), fine[1])
    return p, r


def _nnls(basis: np.ndarray, x: np.ndarray, cap: bool = True) -> np.ndarray:
    """Non-negative shares of a few basis vectors (rows) closest to x, scaled down to sum to at most 1 (cap)."""
    best_r, best = float(x @ x), np.zeros(len(basis))
    for k in range(1, len(basis) + 1):
        for sub in combinations(range(len(basis)), k):
            a = basis[list(sub)].T
            c = np.linalg.lstsq(a, x, rcond=None)[0]
            if (c < 0).any():
                continue
            if cap:
                c = c / max(1.0, c.sum())
            r = x - a @ c
            if r @ r < best_r:
                best_r, best = float(r @ r), np.zeros(len(basis))
                best[list(sub)] = c
    return best


def _translations(tgt: np.ndarray, n: int) -> tuple[np.ndarray, np.ndarray]:
    """n bone translations (rows) and per-vertex shares (m, n) reproducing the target motions: the main direction
    of the motions, or for n = 2 the two directions bounding them in their main plane, long enough that no
    vertex needs shares summing to more than 1."""
    _, vecs = np.linalg.eigh(tgt.T @ tgt)
    e1 = vecs[:, -1] if (tgt @ vecs[:, -1]).sum() >= 0 else -vecs[:, -1]
    if n == 1:
        dirs = e1[None]
    else:
        e2 = vecs[:, -2]
        mag = np.linalg.norm(tgt, axis=1)
        big = mag > 0.25 * mag.max()
        ang = np.arctan2(tgt[big] @ e2, tgt[big] @ e1)
        dirs = np.array([np.cos(a) * e1 + np.sin(a) * e2 for a in np.percentile(ang, [1, 99])])
    length = max(max(float(_nnls(dirs, x, cap=False).sum()) for x in tgt), 1e-6)
    basis = dirs * length
    return basis, np.array([_nnls(basis, x) for x in tgt])


def _key_motion(fit, prim: int, name: str):
    """Fitted-space displacement of every vertex of part `prim` under shape key `name` at weight 1, or None."""
    own = getattr(fit, "key_motion", None)
    if own is not None:  # not a vrm_fit.Fit: the caller matched the shape keys itself (xbg_face.py)
        return own(prim, name)
    m = fit.vrm
    delta = m.morph(prim, name)
    if delta is None:
        return None
    part = fit.parts[prim]
    out = np.zeros_like(part.positions)
    moved = np.flatnonzero(np.abs(delta).max(1) > 0)
    if len(moved) == 0:
        return out
    mw = m.world[m.prim_node[prim]][:3, :3]
    rest = part.rest_positions[moved] + fit.scale * (delta[moved] @ mw.T) @ fit.axes.T
    posed, _ = vrm_fit.dqs(rest, np.tile([0.0, 0.0, 1.0], (len(moved), 1)), part.joints[moved], part.weights[moved],
                           fit.node_rot, fit.posed_joint, fit.rest_joint)
    out[moved] = posed - part.positions[moved]
    return out


def _gather(fit, key: str, gain: float, keep=None):
    """[(part, vertex indices, positions, targets)] for the vertices `key` moves by more than ACTIVE_M."""
    out = []
    for i in range(len(fit.parts)):
        t = _key_motion(fit, i, key)
        if t is None:
            continue
        t = t * gain
        sel = np.flatnonzero(np.linalg.norm(t, axis=1) > ACTIVE_M)
        if keep is not None:
            sel = sel[keep(fit.parts[i].positions[sel])]
        if len(sel):
            out.append((i, sel, fit.parts[i].positions[sel], t[sel]))
    if not out:
        raise ValueError(f"face: shape key {key!r} moves no vertex")
    return out


def _smooth(part, field: np.ndarray, passes: int = SMOOTH_PASSES) -> np.ndarray:
    """Average with the edge neighbours (vertices at one position share a value first)."""
    pos = np.round(part.positions / 1e-5).astype(np.int64)
    _, group = np.unique(pos, axis=0, return_inverse=True)
    group = group.reshape(-1)
    tri = part.triangles
    a = np.concatenate([tri[:, 0], tri[:, 1], tri[:, 2], tri[:, 1], tri[:, 2], tri[:, 0]])
    b = np.concatenate([tri[:, 1], tri[:, 2], tri[:, 0], tri[:, 0], tri[:, 1], tri[:, 2]])
    a, b = group[a], group[b]
    ng = group.max() + 1
    f = np.zeros(ng)
    cnt = np.zeros(ng)
    np.add.at(f, group, field)
    np.add.at(cnt, group, 1)
    f /= np.maximum(cnt, 1)
    deg = np.zeros(ng)
    np.add.at(deg, a, 1)
    for _ in range(passes):
        acc = np.zeros(ng)
        np.add.at(acc, a, f[b])
        f = np.where(deg > 0, 0.5 * f + 0.5 * acc / np.maximum(deg, 1), f)
    return np.clip(f[group], 0.0, 1.0)


def build(fit, sk, dp: dpdx_format.Dpdx, cfg: dict) -> FaceRig:
    world = {k: np.asarray(v, float).copy() for k, v in fit.aiden_world.items()}
    rot = {n: sk.bind[i][:3, :3] for i, n in enumerate(sk.names)}
    hook = rot["Facial_Hook"]
    up, fwd = hook @ np.array([1.0, 0.0, 0.0]), hook @ np.array([0.0, 1.0, 0.0])
    if up[2] < 0.9 or fwd[1] < 0.9:
        raise ValueError(f"unexpected facial frame: up {up}, forward {fwd}")
    left_x = np.sign(world["L_Eye"][0] - world["R_Eye"][0])  # the character's left in XBG x
    mid_x = world["Head"][0]
    side_of = {"L": lambda p: (p[:, 0] - mid_x) * left_x > 0, "R": lambda p: (p[:, 0] - mid_x) * left_x < 0}
    shares: dict[int, dict[str, np.ndarray]] = {}
    report: dict = {}
    lids: list[LidMove] = []

    def add_share(part_i, sel, bone, w):
        arr = shares.setdefault(part_i, {}).setdefault(bone, np.zeros(len(fit.parts[part_i].positions)))
        arr[sel] = np.maximum(arr[sel], w)

    def quality(tgt, got):
        res = tgt - got
        tm = np.linalg.norm(tgt, axis=1)
        edge = np.argsort(-tm)[: max(1, len(tm) // 20)]  # the 5 % that move most: a lid's edge
        sink = (got - tgt) @ fwd
        return {"vertices": len(tgt), "target_rms_mm": 1000 * float(np.sqrt((tgt ** 2).sum(1).mean())),
                "residual_rms_mm": 1000 * float(np.sqrt((res ** 2).sum(1).mean())),
                "relative_residual": float(np.sqrt((res ** 2).sum() / (tgt ** 2).sum())),
                "edge_reach": float(np.mean(np.einsum("ij,ij->i", got[edge], tgt[edge]) / tm[edge] ** 2)),
                "deepest_behind_target_mm": round(-1000 * float(min(0.0, sink.min())), 2)}

    # ---- eyes: on the model's eye joints
    eye_pos = {}
    for s in ("L", "R"):
        h = HUMAN_EYE[s]
        if h not in fit.human_node:
            raise ValueError(f"face needs the humanoid {h} bone")
        eye_pos[s] = fit.posed_joint[fit.human_node[h]].copy()
        if (eye_pos[s][0] - mid_x) * left_x * (1 if s == "L" else -1) <= 0:
            raise ValueError(f"the model's {h} is not on the character's {s} side")
        world[EYE[s]] = eye_pos[s]

    # ---- lids: translations and per-vertex shares from the blink keys
    bc = cfg.get("blink")
    if bc:
        report["blink"] = {}
        for s in ("L", "R"):
            key = bc.get(s, bc.get("key"))
            groups = _gather(fit, key, bc.get("gain", 1.0), side_of[s])
            tgt = np.vstack([g[3] for g in groups])
            _, vecs = np.linalg.eigh(tgt.T @ tgt)
            main = vecs[:, -1] if (tgt @ vecs[:, -1]).sum() >= 0 else -vecs[:, -1]
            upper = tgt @ main >= 0  # the rest (the lower lid) moves the other way, to meet it
            got = np.zeros_like(tgt)
            rep = {"key": key, "control": BLINK[s]}
            for bones, mask, follows in ((UPPER_LID[s], upper, True), ((LOWER_LID[s],), ~upper, False)):
                if mask.sum() < 3:
                    continue
                basis, w = _translations(tgt[mask], len(bones))
                got[mask] = w @ basis
                full = np.zeros((len(tgt), len(bones)))
                full[mask] = w
                start = 0
                for part_i, sel, _, _ in groups:
                    for k, bone in enumerate(bones):
                        add_share(part_i, sel, bone, full[start:start + len(sel), k])
                    start += len(sel)
                for bone, v in zip(bones, basis):
                    lids.append(LidMove(bone, s, v, follows))
                    rep[bone] = {"vertices": int(np.count_nonzero(full[:, bones.index(bone)] > 0)),
                                 "move_mm": {"up": round(1000 * float(v @ up), 2), "forward": round(1000 * float(v @ fwd), 2),
                                             "left": round(1000 * float(v[0] * left_x), 2)}}
            report["blink"][s] = {**rep, **quality(tgt, got)}

    # ---- jaw: pivot and shares from the jaw-open key
    jc = cfg.get("jaw")
    if jc:
        groups = _gather(fit, jc["key"], jc.get("gain", 1.0))
        pos = np.vstack([g[2] for g in groups])
        tgt = np.vstack([g[3] for g in groups])
        q, d = _bone_motion(dp, sk, "_Jaw", JAW)
        start = world["_Jaw"].copy()
        start[0] = mid_x
        p, _ = _search(q, d, pos, tgt, start, up, fwd, ((-0.06, 0.06), (-0.06, 0.06), 0.01), (0.01, 0.002))
        world["_Jaw"] = p
        for part_i, sel, ppos, t in groups:
            w, _ = _shares(q, d, p, ppos, t)
            add_share(part_i, sel, "_Jaw", w)
        for part_i in {g[0] for g in groups}:
            shares[part_i]["_Jaw"] = _smooth(fit.parts[part_i], shares[part_i]["_Jaw"])
        rel = p - fit.aiden_world["_Jaw"]
        _, r = _shares(q, d, p, pos, tgt)
        report["jaw"] = {"key": jc["key"], "control": JAW,
                         "pivot_from_template_cm": {"up": round(100 * rel @ up, 2), "forward": round(100 * rel @ fwd, 2)},
                         "vertices": len(tgt), "target_rms_mm": 1000 * float(np.sqrt((tgt ** 2).sum(1).mean())),
                         "residual_rms_mm": 1000 * float(np.sqrt(r / len(tgt))),
                         "relative_residual": float(np.sqrt(r / (tgt ** 2).sum()))}

    # ---- gaze: one share of the eye bone per eye, from the look keys
    gc = cfg.get("gaze")
    if gc:
        report["gaze"] = {}
        for s in ("L", "R"):
            num = den = 0.0
            pairs = {}
            sets: dict[int, set] = {}
            for key in gc["keys"]:
                found = []
                for i in range(len(fit.parts)):
                    t = _key_motion(fit, i, key)
                    if t is None:
                        continue
                    sel = np.flatnonzero(np.linalg.norm(t, axis=1) > GAZE_ACTIVE_M)
                    sel = sel[side_of[s](fit.parts[i].positions[sel])]
                    if len(sel):
                        found.append((i, sel, fit.parts[i].positions[sel], t[sel]))
                if not found:
                    raise ValueError(f"face: look key {key!r} moves nothing on the {s} side")
                pos = np.vstack([f[2] for f in found])
                tgt = np.vstack([f[3] for f in found])
                # anime eyes are stacks of layers; the visible one is the front of the stack (the others, e.g.
                # alternative eyes hidden inside the head, sit near the eye joint and barely move)
                depth = (pos - eye_pos[s]) @ fwd
                front = depth >= 0.5 * depth.max()
                pos, tgt = pos[front], tgt[front]
                best = None
                for c in GAZE[s]:
                    q, d = _bone_motion(dp, sk, EYE[s], c)
                    disp = (pos - eye_pos[s]) @ (q - np.eye(3)).T + d
                    dot = float(np.einsum("ij,ij->", disp, tgt))
                    corr = dot / np.sqrt(float(np.einsum("ij,ij->", disp, disp)) * float(np.einsum("ij,ij->", tgt, tgt)))
                    if best is None or corr > best[0]:
                        best = (corr, c, dot, float(np.einsum("ij,ij->", disp, disp)))
                if best[0] < 0.5:
                    raise ValueError(f"face: no gaze control moves like {key!r} (best correlation {best[0]:.2f})")
                pairs[key] = {"control": best[1], "correlation": round(best[0], 3)}
                num += best[2]
                den += best[3]
                for i, sel, _, _ in found:
                    sets.setdefault(i, set()).update(sel.tolist())
            fitted = num / den
            w_eye = float(np.clip(gc.get("gain", 1.0) * fitted, 0.0, 1.0))
            for i, sel in sets.items():
                add_share(i, np.array(sorted(sel)), EYE[s], np.full(len(sel), w_eye))
            report["gaze"][s] = {"fitted_share": round(fitted, 4), "share": round(w_eye, 4),
                                 "vertices": sum(len(v) for v in sets.values()), "pairs": pairs}

    # ---- descendants of the moved bones follow rigidly
    moved = [n for n in (*EYE.values(), "_Jaw") if np.abs(world[n] - fit.aiden_world[n]).max() > 1e-7 or n in EYE.values()]
    for i, n in enumerate(sk.names):
        par = sk.parent[i]
        if par >= 0 and n not in moved and _under(sk, i, moved):
            world[n] = world[sk.names[par]] + rot[sk.names[par]] @ sk.local[i][:3, 3]
    report["moved"] = {n: [round(float(x), 5) for x in world[n]] for n in moved}
    report["weighted_vertices"] = {fit.parts[i].name: int(np.count_nonzero(np.sum(list(b.values()), axis=0)))
                                   for i, b in shares.items()}
    return FaceRig(world, moved, shares, report, lids, float(bc.get("follow_scale", 0.5)) if bc else 0.5)


def _under(sk, i: int, names: list[str]) -> bool:
    p = sk.parent[i]
    while p >= 0:
        if sk.names[p] in names:
            return True
        p = sk.parent[p]
    return False


def _closing_fractions(dp: dpdx_format.Dpdx, side: str) -> dict[int, float]:
    """Control -> fraction of a blink by which it closes Aiden's upper lid (its turn about the blink axis)."""
    b = dp.bone(UPPER_LID[side][0])
    qb = b.delta(BLINK[side]).rotation
    axis = qb[:3] / np.linalg.norm(qb[:3])
    angle = 2.0 * np.arctan2(np.linalg.norm(qb[:3]), qb[3])
    out = {}
    for it in b.items:
        q = it.rotation
        k = 2.0 * np.arctan2(q[:3] @ axis, q[3]) / angle
        if it.control != BLINK[side] and k >= MIN_FOLLOW:
            out[it.control] = float(k)
    return out


def facial_definition(dp: dpdx_format.Dpdx, sk_patched, face: FaceRig) -> tuple[bytes, dict]:
    """The dpdx with the moved bones' rest translations taken from the patched skeleton and the lid bones' items
    replaced; fails unless every named rest translation then equals the XBG's local translation (otherwise the
    game would drag those vertices)."""
    follow = {s: _closing_fractions(dp, s) for s in {lm.side for lm in face.lids}}
    lid_items = {}
    for lm in face.lids:
        i = sk_patched.index[lm.bone]
        t = sk_patched.bind[sk_patched.parent[i]][:3, :3].T @ lm.move  # parent space
        items = {BLINK[lm.side]: t}
        if lm.follow:
            items.update({c: face.follow_scale * k * t for c, k in follow[lm.side].items()})
        dp.bone(lm.bone).items = [dpdx_format.Item.translation_only(c, v) for c, v in sorted(items.items())]
        lid_items[lm.bone] = {str(c): [round(1000 * float(x), 2) for x in v] for c, v in sorted(items.items())}
    changed = {}
    for name in face.moved:
        b = dp.bone(name)
        if b is None:
            raise ValueError(f"{name} is not in the facial definition")
        t = sk_patched.local[sk_patched.index[name]][:3, 3].astype(np.float32)
        changed[name] = float(np.linalg.norm(t - np.array(b.rest_t)))
        b.rest_t = tuple(float(x) for x in t)
    check = dpdx_format.check_against(dp, sk_patched)
    bad = {n: d for n, d in check["per_bone_translation_diff_m"].items() if d > 1e-5}
    if bad:
        raise ValueError(f"facial rest translations disagree with the XBG: {bad}")
    return dpdx_format.dump(dp), {"rest_moved_m": changed, "max_rest_diff_m": check["max_translation_diff_m"],
                                  "lid_follow": {s: {str(c): round(k, 3) for c, k in f.items()} for s, f in follow.items()},
                                  "follow_scale": face.follow_scale, "lid_items_mm": lid_items}
