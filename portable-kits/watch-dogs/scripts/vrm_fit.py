"""Fit a humanoid VRM onto the Watch Dogs char01 skeleton without stretching the mesh.

Strategy (proven in game by Karin 1.5 and Karin_Original 0.1.2: the game honours body-bone bind
translations; facial bones are reset by animation):
  1. Uniform scale so the hip-to-ankle length equals the template's; glTF axes -> XBG axes.  VRM 0.x
     models face -Z and are turned 180 degrees first (detected from the left/right upper legs).
  2. Repose the T-pose mesh into the template's bind pose (limb directions, palm roll) with
     dual-quaternion skinning on the model's own skeleton and weights.
  3. Move char01 joints to the model's posed joints (bone rotations stay the template's), keeping the
     template's Pelvis/Spine/Spine1/Spine2; twist and meta bones are interpolated, every other node
     follows its parent rigidly.
Optional humanoid bones (chest, shoulders, toes, fingers, eyes) and template bones (twist, meta,
fingers) may be missing; the matching steps are skipped.  Weights are mapped by vrm_weights.py.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

import vrm_model

G2X = np.array([[-1.0, 0, 0], [0, 0, 1], [0, 1, 0]])  # glTF (left=+X, up=+Y, fwd=+Z) -> XBG (left=-X, fwd=+Y, up=+Z)
TURN = np.diag([-1.0, 1.0, -1.0])  # 180 degrees about glTF up, for models that face -Z

SIDES = {"L": "left", "R": "right"}
FINGERS = {"Index": "Index", "Middle": "Middle", "Ring": "Ring", "Little": "Pinky"}

# humanoid bone -> char01 node
HUMAN_TO_AIDEN = {"hips": "Pelvis", "chest": "Spine2", "neck": "Neck", "head": "Head",
                  "leftEye": "L_Eye", "rightEye": "R_Eye"}
for s, side in SIDES.items():
    HUMAN_TO_AIDEN.update({
        f"{side}Shoulder": f"{s} Clavicle", f"{side}UpperArm": f"{s} UpperArm", f"{side}LowerArm": f"{s} Forearm",
        f"{side}Hand": f"{s} Hand", f"{side}UpperLeg": f"{s} Thigh", f"{side}LowerLeg": f"{s} Calf",
        f"{side}Foot": f"{s} Foot", f"{side}Toes": f"{s} Toe",
        f"{side}ThumbMetacarpal": f"{s} Thumb01", f"{side}ThumbProximal": f"{s} Thumb02", f"{side}ThumbDistal": f"{s} Thumb03",
    })
    for v, a in FINGERS.items():
        for seg, k in (("Proximal", "01"), ("Intermediate", "02"), ("Distal", "03")):
            HUMAN_TO_AIDEN[f"{side}{v}{seg}"] = f"{s} {a}{k}"
# joints whose position stays the template's (root/torso pivots; pelvis height may come from animation)
KEEP_AIDEN = {"Pelvis", "Spine", "Spine1", "Spine2"}
# direction targets for the repose: humanoid bone -> (humanoid child, template head, template child)
CHAIN = {}
for s, side in SIDES.items():
    CHAIN[f"{side}Shoulder"] = (f"{side}UpperArm", f"{s} Clavicle", f"{s} UpperArm")
    CHAIN[f"{side}UpperArm"] = (f"{side}LowerArm", f"{s} UpperArm", f"{s} Forearm")
    CHAIN[f"{side}LowerArm"] = (f"{side}Hand", f"{s} Forearm", f"{s} Hand")
    CHAIN[f"{side}UpperLeg"] = (f"{side}LowerLeg", f"{s} Thigh", f"{s} Calf")
    CHAIN[f"{side}LowerLeg"] = (f"{side}Foot", f"{s} Calf", f"{s} Foot")
    CHAIN[f"{side}Foot"] = (f"{side}Toes", f"{s} Foot", f"{s} Toe")
    CHAIN[f"{side}ThumbMetacarpal"] = (f"{side}ThumbProximal", f"{s} Thumb01", f"{s} Thumb02")
    CHAIN[f"{side}ThumbProximal"] = (f"{side}ThumbDistal", f"{s} Thumb02", f"{s} Thumb03")
    for v, a in FINGERS.items():
        CHAIN[f"{side}{v}Proximal"] = (f"{side}{v}Intermediate", f"{s} {a}01", f"{s} {a}02")
        CHAIN[f"{side}{v}Intermediate"] = (f"{side}{v}Distal", f"{s} {a}02", f"{s} {a}03")
# bones placed by the template's fractional position between two joints: (bone, from, to)
INTERPOLATED = []
for s in SIDES:
    INTERPOLATED += [(f"{s} U UpperArm Twist", f"{s} UpperArm", f"{s} Forearm"),
                     (f"{s} D UpperArm Twist", f"{s} UpperArm", f"{s} Forearm"),
                     (f"{s} U Forearm Twist", f"{s} Forearm", f"{s} Hand"),
                     (f"{s} M Forearm Twist", f"{s} Forearm", f"{s} Hand"),
                     (f"{s} D Forearm Twist", f"{s} Forearm", f"{s} Hand"),
                     (f"{s} Middle_Meta", f"{s} Hand", f"{s} Middle01"),
                     (f"{s} Ring_Meta", f"{s} Hand", f"{s} Ring01"),
                     (f"{s} Hand_Meta", f"{s} Hand", f"{s} Pinky01")]
REQUIRED = ("hips", "head", "leftUpperLeg", "rightUpperLeg", "leftFoot")


def rot_between(a: np.ndarray, b: np.ndarray) -> np.ndarray:
    a = a / np.linalg.norm(a)
    b = b / np.linalg.norm(b)
    v = np.cross(a, b)
    c = float(a @ b)
    if c < -0.999999:
        raise ValueError("opposite directions")
    k = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + k + k @ k / (1 + c)


def rot_about(axis: np.ndarray, src: np.ndarray, dst: np.ndarray) -> np.ndarray:
    """Rotation about `axis` taking the projection of src onto the projection of dst."""
    a = axis / np.linalg.norm(axis)
    s = src - a * (src @ a)
    d = dst - a * (dst @ a)
    s /= np.linalg.norm(s)
    d /= np.linalg.norm(d)
    ang = np.arctan2(a @ np.cross(s, d), s @ d)
    k = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(ang) * k + (1 - np.cos(ang)) * (k @ k)


@dataclass
class Part:
    name: str  # mesh/primitive
    material: int  # VRM material index
    positions: np.ndarray  # XBG space, posed (after fit)
    normals: np.ndarray
    uv: np.ndarray  # glTF convention (v down)
    triangles: np.ndarray
    joints: np.ndarray  # VRM node indices
    weights: np.ndarray
    rest_positions: np.ndarray  # XBG space, scaled T-pose


@dataclass
class Fit:
    scale: float
    parts: list[Part]
    vrm: vrm_model.Vrm
    rest_joint: np.ndarray  # (nodes,3) XBG scaled T-pose
    posed_joint: np.ndarray  # (nodes,3) after repose
    node_rot: np.ndarray  # (nodes,3,3) repose rotation per VRM node
    aiden_world: dict[str, np.ndarray]  # char01 node name -> new bind head
    human_node: dict[str, int]
    axes: np.ndarray  # glTF -> XBG, including the 180-degree turn for -Z facing models


def model_axes(m: vrm_model.Vrm) -> np.ndarray:
    """glTF -> XBG axes.  A model facing +Z has its left upper leg at +X (VRM 1.0); otherwise turn it."""
    left = m.world[m.humanoid["leftUpperLeg"]][0, 3]
    right = m.world[m.humanoid["rightUpperLeg"]][0, 3]
    return G2X if left > right else G2X @ TURN


def scale_for(m: vrm_model.Vrm, sk, axes: np.ndarray = G2X) -> float:
    h = {k: axes @ m.world[v][:3, 3] for k, v in m.humanoid.items()}
    model = h["leftUpperLeg"][2] - h["leftFoot"][2]
    template = sk.head("L Thigh")[2] - sk.head("L Foot")[2]
    return float(template / model)


def palm_normal(wrist, index, middle, pinky):
    n = np.cross(index - pinky, middle - wrist)
    return n / np.linalg.norm(n)


def build_fit(vrm_path: Path, sk) -> Fit:
    m = vrm_model.load(vrm_path)
    missing = [b for b in REQUIRED if b not in m.humanoid]
    if missing:
        raise ValueError(f"VRM humanoid lacks required bones {missing}")
    axes = model_axes(m)
    s = scale_for(m, sk, axes)
    nn = len(m.node_names)
    rest = np.array([s * (axes @ m.world[i][:3, 3]) for i in range(nn)])
    hn = m.humanoid
    by_node = {v: k for k, v in hn.items()}
    A = {n: sk.head(n) for n in sk.names}

    # ---- repose rotations, parents first
    R = np.zeros((nn, 3, 3))
    P = np.zeros((nn, 3))
    order = []
    seen = set()

    def visit(i):
        if i in seen:
            return
        if m.parent[i] >= 0:
            visit(m.parent[i])
        seen.add(i)
        order.append(i)

    for i in range(nn):
        visit(i)
    for i in order:
        par = m.parent[i]
        rp = R[par] if par >= 0 else np.eye(3)
        P[i] = rest[i] if par < 0 else P[par] + R[par] @ (rest[i] - rest[par])
        h = by_node.get(i)
        Ri = rp
        if h in CHAIN:
            child, a0, a1 = CHAIN[h]
            if child in hn and a0 in A and a1 in A:
                d = rp @ (rest[hn[child]] - rest[i])
                Ri = rot_between(d, A[a1] - A[a0]) @ rp
        if h in ("leftHand", "rightHand"):
            side = h[:-4]
            s_ = "L" if side == "left" else "R"
            fingers = [f"{side}IndexProximal", f"{side}MiddleProximal", f"{side}LittleProximal"]
            bones = [f"{s_} Hand", f"{s_} Index01", f"{s_} Middle01", f"{s_} Pinky01"]
            if f"{side}MiddleProximal" in hn and f"{s_} Hand" in A and f"{s_} Middle01" in A:
                mid = hn[f"{side}MiddleProximal"]
                d = rp @ (rest[mid] - rest[i])
                q = rot_between(d, A[f"{s_} Middle01"] - A[f"{s_} Hand"])
                Ri = q @ rp
                if all(f in hn for f in fingers) and all(b in A for b in bones):
                    her_n = Ri @ palm_normal(rest[i], rest[hn[fingers[0]]], rest[mid], rest[hn[fingers[2]]])
                    aid_n = palm_normal(A[f"{s_} Hand"], A[f"{s_} Index01"], A[f"{s_} Middle01"], A[f"{s_} Pinky01"])
                    Ri = rot_about(A[f"{s_} Middle01"] - A[f"{s_} Hand"], her_n, aid_n) @ Ri
        R[i] = Ri

    # ---- skin parts with DQS on the VRM skeleton
    parts = []
    for prim, skin, node in zip(m.primitives, m.prim_skin, m.prim_node):
        if skin < 0 or prim.joints.shape[1] == 0:
            raise ValueError(f"primitive {prim.mesh}/{prim.index} is not skinned")
        js = np.array(m.skin_joints(skin))
        mw = m.world[node]
        pos = s * ((mw[:3, :3] @ prim.positions.T).T + mw[:3, 3]) @ axes.T
        nrm = (mw[:3, :3] @ prim.normals.T).T @ axes.T
        nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
        jn = js[prim.joints]
        posed, pn = dqs(pos, nrm, jn, prim.weights, R, P, rest)
        parts.append(Part(f"{prim.mesh}/{prim.index}", prim.material, posed, pn, prim.uv0.copy(),
                          prim.triangles, jn, prim.weights, pos))

    # ---- char01 joint positions
    world = {}
    target = {aid: P[hn[h]] for h, aid in HUMAN_TO_AIDEN.items() if h in hn and aid in A}
    for i, name in enumerate(sk.names):
        par = sk.parent[i]
        if name in target and name not in KEEP_AIDEN:
            world[name] = target[name]
        elif par < 0 or name in KEEP_AIDEN:
            world[name] = A[name].copy()
        else:
            pname = sk.names[par]
            world[name] = world[pname] + sk.bind[par][:3, :3] @ sk.local[i][:3, 3]
    # twist and meta bones by the template's fractional placement along the new links
    interpolated = set()
    for bone, a, b in INTERPOLATED:
        if bone in A and a in A and b in A:
            f = (A[bone] - A[a]) @ (A[b] - A[a]) / np.linalg.norm(A[b] - A[a]) ** 2
            world[bone] = world[a] + f * (world[b] - world[a])
            interpolated.add(bone)
    # nodes below a moved node that are not themselves targets follow their parent rigidly
    for i, name in enumerate(sk.names):
        par = sk.parent[i]
        if par < 0 or name in target or name in KEEP_AIDEN or name in interpolated:
            continue
        world[name] = world[sk.names[par]] + sk.bind[par][:3, :3] @ sk.local[i][:3, 3]
    return Fit(s, parts, m, rest, P, R, world, hn, axes)


def _quat(r: np.ndarray) -> np.ndarray:
    """Rotation matrix -> quaternion (w, x, y, z)."""
    t = np.trace(r)
    if t > 0:
        q = np.array([t + 1, r[2, 1] - r[1, 2], r[0, 2] - r[2, 0], r[1, 0] - r[0, 1]])
    else:
        i = int(np.argmax(np.diag(r)))
        j, k = (i + 1) % 3, (i + 2) % 3
        q = np.zeros(4)
        q[i + 1] = 1 + r[i, i] - r[j, j] - r[k, k]
        q[j + 1] = r[j, i] + r[i, j]
        q[k + 1] = r[k, i] + r[i, k]
        q[0] = r[k, j] - r[j, k]
    return q / np.linalg.norm(q)


def _qmul(a, b):
    w1, x1, y1, z1 = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    w2, x2, y2, z2 = b[..., 0], b[..., 1], b[..., 2], b[..., 3]
    return np.stack([w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2, w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                     w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2, w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2], -1)


def _qrot(q, v):
    u = q[..., 1:]
    w = q[..., :1]
    return v + 2 * np.cross(u, np.cross(u, v) + w * v)


def dqs(pos, nrm, jn, wt, R, P, rest):
    """Dual-quaternion skinning of rest-pose points with per-node transform x' = P + R (x - rest)."""
    nodes = np.unique(jn[wt > 0])
    q0 = {n: _quat(R[n]) for n in nodes}
    t = {n: P[n] - R[n] @ rest[n] for n in nodes}
    real = np.zeros((len(pos), 4))
    dual = np.zeros((len(pos), 4))
    ref = np.array([q0[n] for n in jn[np.arange(len(pos)), np.argmax(wt, 1)]])
    for k in range(jn.shape[1]):
        w = wt[:, k]
        live = w > 0
        if not live.any():
            continue
        qr = np.array([q0[n] if l else [1, 0, 0, 0] for n, l in zip(jn[:, k], live)])
        tq = np.array([np.r_[0.0, t[n]] if l else np.zeros(4) for n, l in zip(jn[:, k], live)])
        qd = 0.5 * _qmul(tq, qr)
        sign = np.sign(np.einsum("ij,ij->i", qr, ref))
        sign[sign == 0] = 1
        real += (w * sign)[:, None] * qr
        dual += (w * sign)[:, None] * qd
    norm = np.linalg.norm(real, axis=1, keepdims=True)
    real /= norm
    dual /= norm
    conj = real * np.array([1, -1, -1, -1])
    trans = 2 * _qmul(dual, conj)[:, 1:]
    out = _qrot(real, pos) + trans
    on = _qrot(real, nrm)
    return out, on / np.maximum(np.linalg.norm(on, axis=1, keepdims=True), 1e-12)
