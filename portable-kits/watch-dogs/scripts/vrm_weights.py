"""Map a fitted VRM's skin weights onto char01 bones.

  * Humanoid bones map one to one (vrm_fit.HUMAN_TO_AIDEN).  `spine` is split by height between Spine and
    Spine1 (Spine/Spine1/Spine2 when the model has no chest); `upperChest` goes to Spine2.
  * Eyes and jaw go to Head: the game's facial animation resets facial bone translations, so anything
    skinned to them is dragged to Aiden's face layout (Karin_Original 0.1.1 in-game finding).
  * Upper arm and forearm weight is spread over the twist bones with a measured profile (TWIST_PROFILE,
    from the in-game-proven Karin 1.3 weights); hand weight fades into the palm meta bones toward the knuckles.
  * Non-humanoid bones go to their nearest humanoid ancestor, unless a profile chain rule matches:
      {"match": regex on the node name, "under": humanoid ancestor, "shares": [per chain level],
       "to": char01 bone | "to_side": [character-left bone, right bone], "side_width": metres}
    A rule moves `share` of the weight from the ancestor's bone to the target (split left/right by the
    vertex's X for `to_side`).  The chain level counts the steps up to a branching node or humanoid bone;
    levels past the list reuse its last value.
  * Humanoid bones whose char01 bone is missing from the template fall back to the nearest mapped ancestor.
"""

from __future__ import annotations

import re

import numpy as np

import vrm_fit

FACE_TO_HEAD = {"leftEye", "rightEye", "jaw"}
EXTRA = {"upperChest": "Spine2"}
# Karin 1.3 measurement: per fraction t along the segment, the share carried by each bone
TWIST_PROFILE = {
    "upperarm": {"bones": ["UpperArm", "U UpperArm Twist", "D UpperArm Twist"], "profile": [
        [-0.049999999999999996, [0.0, 0.9629, 0.0371]],
        [0.050000000000000024, [0.0, 0.9027, 0.0973]],
        [0.15000000000000002, [0.0034, 0.8198, 0.1767]],
        [0.25000000000000006, [0.0228, 0.7214, 0.2558]],
        [0.3500000000000001, [0.0549, 0.6199, 0.3252]],
        [0.4500000000000001, [0.0952, 0.4993, 0.4055]],
        [0.5500000000000002, [0.1356, 0.3658, 0.4986]],
        [0.6500000000000001, [0.2159, 0.1752, 0.6089]],
        [0.7500000000000002, [0.315, 0.0595, 0.6255]],
        [0.8500000000000002, [0.4358, 0.0068, 0.5574]],
        [0.9500000000000002, [0.5494, 0.0, 0.4506]],
        [1.0500000000000003, [0.6386, 0.0, 0.3614]],
    ]},
    "forearm": {"bones": ["Forearm", "U Forearm Twist", "M Forearm Twist", "D Forearm Twist"], "profile": [
        [-0.049999999999999996, [0.0021, 0.9979, 0.0, 0.0]],
        [0.050000000000000024, [0.1229, 0.8771, 0.0, 0.0]],
        [0.15000000000000002, [0.2696, 0.7304, 0.0, 0.0]],
        [0.25000000000000006, [0.1218, 0.8782, 0.0, 0.0]],
        [0.3500000000000001, [0.1059, 0.8941, 0.0, 0.0]],
        [0.4500000000000001, [0.1496, 0.8504, 0.0, 0.0]],
        [0.5500000000000002, [0.2271, 0.7718, 0.0, 0.0011]],
        [0.6500000000000001, [0.4927, 0.4883, 0.0009, 0.0181]],
        [0.7500000000000002, [0.7647, 0.1523, 0.0121, 0.0709]],
        [0.8500000000000002, [0.5886, 0.0049, 0.0874, 0.3191]],
        [0.9500000000000002, [0.2734, 0.0, 0.0643, 0.6622]],
        [1.0500000000000003, [0.4895, 0.0, 0.0167, 0.4938]],
    ]},
}


def _interp_profile(prof: list, t: np.ndarray) -> np.ndarray:
    xs = np.array([p[0] for p in prof])
    ys = np.array([p[1] for p in prof])
    out = np.column_stack([np.interp(t, xs, ys[:, k]) for k in range(ys.shape[1])])
    return out / out.sum(1, keepdims=True)


def chain_levels(parent: list[int], humanoid_nodes: set[int]) -> list[int]:
    """Steps from each node up to the first node whose parent is humanoid, a root, or branching."""
    children: dict[int, int] = {}
    for p in parent:
        children[p] = children.get(p, 0) + 1
    out = []
    for i in range(len(parent)):
        level, n = 0, i
        while True:
            p = parent[n]
            if p < 0 or p in humanoid_nodes or children.get(p, 0) > 1:
                break
            level += 1
            n = p
        out.append(level)
    return out


def compile_rules(rules: list[dict]) -> list[dict]:
    out = []
    for r in rules or []:
        if ("to" in r) == ("to_side" in r):
            raise ValueError(f"chain rule needs exactly one of to / to_side: {r}")
        out.append({**r, "re": re.compile(r["match"]), "side_width": float(r.get("side_width", 0.02))})
    return out


def map_part(fit: vrm_fit.Fit, part: vrm_fit.Part, sk, profile: dict | None = None, rules: list[dict] | None = None,
             levels: list[int] | None = None) -> list[dict[str, float]]:
    """Per-vertex {char01 bone: weight} (normalized).  `rules` come from compile_rules()."""
    m = fit.vrm
    by_node = {v: k for k, v in fit.human_node.items()}
    W = fit.aiden_world
    names = m.node_names
    profile = profile or TWIST_PROFILE
    rules = rules or []
    if levels is None:
        levels = chain_levels(m.parent, set(fit.human_node.values()))

    def human_anc(n):
        while n >= 0 and n not in by_node:
            n = m.parent[n]
        return by_node.get(n)

    def bone_for(h):
        """char01 bone for a humanoid bone, falling back to the nearest mapped humanoid ancestor."""
        start = h
        while h is not None:
            aid = "Head" if h in FACE_TO_HEAD else vrm_fit.HUMAN_TO_AIDEN.get(h) or EXTRA.get(h)
            if aid in W:
                return aid
            h = human_anc(m.parent[fit.human_node[h]])
        raise KeyError(f"no char01 bone for humanoid {start}")

    pos = part.positions
    out = [dict() for _ in range(len(pos))]

    def add(idx, bone, w):
        for i, ww in zip(idx, w):
            if ww > 0:
                out[i][bone] = out[i].get(bone, 0.0) + float(ww)

    for k in range(part.joints.shape[1]):
        wk = part.weights[:, k]
        for node in np.unique(part.joints[wk > 0, k]):
            sel = np.flatnonzero((part.joints[:, k] == node) & (wk > 0))
            w = wk[sel]
            nm = names[node]
            h = by_node.get(node)
            if h is None:
                anc = human_anc(node)
                if anc is None:
                    raise KeyError(f"node {nm} has no humanoid ancestor")
                rule = next((r for r in rules if r["re"].match(nm) and r["under"] == anc), None)
                if rule is not None:
                    shares = rule["shares"]
                    c = shares[levels[node]] if levels[node] < len(shares) else shares[-1]
                    add(sel, bone_for(anc), w * (1 - c))
                    if "to" in rule:
                        add(sel, rule["to"], w * c)
                    else:
                        left = 1.0 / (1.0 + np.exp(pos[sel, 0] / rule["side_width"]))  # character left is -X
                        add(sel, rule["to_side"][0], w * c * left)
                        add(sel, rule["to_side"][1], w * c * (1 - left))
                    continue
                h = anc
            if h in FACE_TO_HEAD:
                add(sel, bone_for(h), w)
                continue
            if h == "spine":
                z = pos[sel, 2]
                if "chest" in fit.human_node or "Spine2" not in W:
                    t = np.clip((z - W["Spine"][2]) / (W["Spine1"][2] - W["Spine"][2]), 0, 1)
                    add(sel, "Spine", w * (1 - t))
                    add(sel, "Spine1", w * t)
                else:  # no chest bone: the spine covers the whole torso
                    zs = np.array([W["Spine"][2], W["Spine1"][2], W["Spine2"][2]])
                    for j, bone in enumerate(("Spine", "Spine1", "Spine2")):
                        y = np.zeros(3)
                        y[j] = 1
                        add(sel, bone, w * np.interp(z, zs, y))
                continue
            aid = bone_for(h)
            s = aid[0]
            if aid.endswith("UpperArm") or aid.endswith("Forearm"):
                seg = "upperarm" if aid.endswith("UpperArm") else "forearm"
                a, b = (f"{s} UpperArm", f"{s} Forearm") if seg == "upperarm" else (f"{s} Forearm", f"{s} Hand")
                bones = [f"{s} {bone}" for bone in profile[seg]["bones"]]
                if a in W and b in W and all(bone in W for bone in bones):
                    A, B = W[a], W[b]
                    t = (pos[sel] - A) @ (B - A) / np.linalg.norm(B - A) ** 2
                    share = _interp_profile(profile[seg]["profile"], t)
                    for j, bone in enumerate(bones):
                        add(sel, bone, w * share[:, j])
                    continue
            if aid.endswith(" Hand") and all(f"{s} {b}" in W for b in
                                             ("Index01", "Middle01", "Ring01", "Pinky01", "Middle_Meta", "Ring_Meta", "Hand_Meta")):
                add_palm(sel, w, pos, s, W, add)
                continue
            add(sel, aid, w)
    for d in out:
        tot = sum(d.values())
        for key in d:
            d[key] /= tot
    return out


def add_palm(sel, w, pos, s, W, add):
    """Hand weight -> Hand plus meta bones (Middle_Meta, Ring_Meta, Hand_Meta) toward the knuckles."""
    hand = W[f"{s} Hand"]
    cols = {"Hand": W[f"{s} Index01"], f"{s} Middle_Meta": W[f"{s} Middle01"],
            f"{s} Ring_Meta": W[f"{s} Ring01"], f"{s} Hand_Meta": W[f"{s} Pinky01"]}
    axis = W[f"{s} Middle01"] - hand
    length = np.linalg.norm(axis)
    axis /= length
    lateral = W[f"{s} Index01"] - W[f"{s} Pinky01"]
    lateral -= axis * (lateral @ axis)
    lateral /= np.linalg.norm(lateral)
    rel = pos[sel] - hand
    along = np.clip(rel @ axis / length, 0, 1)
    ramp = along * along * (3 - 2 * along)  # 0 at wrist, 1 at knuckles
    lat = rel @ lateral
    keys = list(cols)
    lat_c = np.array([(cols[k] - hand) @ lateral for k in keys])  # index, middle, ring, pinky
    order = np.argsort(lat_c)
    xs = lat_c[order]
    share = np.zeros((len(sel), len(keys)))
    for j, k in enumerate(order):
        y = np.zeros(len(keys))
        y[j] = 1
        share[:, k] = np.interp(lat, xs, y)
    share /= np.maximum(share.sum(1, keepdims=True), 1e-12)
    meta = share * ramp[:, None]
    hand_w = 1 - meta[:, 1:].sum(1)  # index column stays on the Hand bone
    add(sel, f"{s} Hand", w * hand_w)
    for j, k in enumerate(keys[1:], start=1):
        add(sel, k, w * meta[:, j])
