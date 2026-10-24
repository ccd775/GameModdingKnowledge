"""Physics for a char01.xbg written from a template (no ZModeler): chains on spare physics nodes, and the template's
own coat cloth reused for a coat or a skirt.

Library (used by vrm_physics.py) plus one command:

  python xbg_physics.py export-colliders --xbg GAME_CHARACTER.xbg --out colliders.json

which writes the collider lists of every physics object of a game XBG (keyed by the object's first node name), so a
profile can reuse e.g. a game ponytail's capsules without any game data in the profile itself.

What the game does with this data (in-game tests on two models, 2026-10-06):
  * chain objects (sub 1) only react to the rotation of their anchor bone: a chain on the head swings when the head
    turns, a chain on the pelvis hardly moves; nothing trails behind a running character, whatever the parameters;
  * the template's coat cloth (object header 2,0,1, 130 particles PL_Coat_SMUNode_*) does react to the body's motion
    and to the legs; its rest shape comes from the particles' bind positions, so the particles may be moved;
  * every node flag's high 16 bits index the object's anchor list; an index past its end leaves the node unsimulated.
The template must carry Aiden's original physics block (any char01 written by ZModeler or by this kit does).
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
import tempfile
import zlib
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smu_format as S  # noqa: E402
import xbg_model  # noqa: E402
from xbg_skeleton import Skeleton  # noqa: E402
from xbg_skeleton_patch import node_records  # noqa: E402

PINNED, FREE = 0x1, 0x10000
SKINNABLE = 382  # nodes with b >= this have no skinning matrix in char01
COAT_HEADER = (2, 0, 1)
COAT_SPAN = 0x3A00  # bytes searched for the coat's particle records after the object start
COAT_PREFIX = "PL_Coat_SMUNode_"
LEG_HELPERS = ("Rfx_LThigh_Back", "Rfx_RThigh_Back")
SPINE_BONES = ("Spine", "Spine1", "Spine2")
COAT_ANCHORS = ("L Thigh", "R Thigh", "Pelvis", "Spine", "Spine1", "Spine2")  # the coat cloth's anchor list
PELVIS_ANCHOR = COAT_ANCHORS.index("Pelvis")
LEG_CAPSULES = ("L Thigh", "R Thigh", "Pelvis", "L Calf", "R Calf")
PARTICLE_RADIUS = 0.0255  # every coat particle record
CLEAR_MARGIN = 0.005
R_ARC = 0.2  # metres per radian when mixing angle and height
POOLS = {  # spare physics nodes by name prefix
    "any": ("Ph_", "PL_"),
    "collar": ("Ph_Pl_Sweater_Colar", "Ph_Pl_Coat_Colar"),
    "coat": ("PL_Coat",),
}
POOLS["spare"] = POOLS["collar"] + ("Ph_Ch_Belt", "Ph_Jig_Zipper", "Ph_Ch_Zipper", "Ph_JiggleStiff")


# ---------------------------------------------------------------- skeleton edits

def mat_to_quat(m: np.ndarray) -> tuple:
    """xyzw quaternion for a rotation matrix (inverse of xbg_skeleton.quat_to_mat)."""
    t = np.trace(m)
    if t > 0:
        s = np.sqrt(t + 1.0) * 2
        w, x, y, z = 0.25 * s, (m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s
    elif m[0, 0] > m[1, 1] and m[0, 0] > m[2, 2]:
        s = np.sqrt(1.0 + m[0, 0] - m[1, 1] - m[2, 2]) * 2
        w, x, y, z = (m[2, 1] - m[1, 2]) / s, 0.25 * s, (m[0, 1] + m[1, 0]) / s, (m[0, 2] + m[2, 0]) / s
    elif m[1, 1] > m[2, 2]:
        s = np.sqrt(1.0 + m[1, 1] - m[0, 0] - m[2, 2]) * 2
        w, x, y, z = (m[0, 2] - m[2, 0]) / s, (m[0, 1] + m[1, 0]) / s, 0.25 * s, (m[1, 2] + m[2, 1]) / s
    else:
        s = np.sqrt(1.0 + m[2, 2] - m[0, 0] - m[1, 1]) * 2
        w, x, y, z = (m[1, 0] - m[0, 1]) / s, (m[0, 2] + m[2, 0]) / s, (m[1, 2] + m[2, 1]) / s, 0.25 * s
    q = np.array([x, y, z, w])
    return tuple(q / np.linalg.norm(q))


def chain_frames(points: np.ndarray, ref_x: np.ndarray) -> list[np.ndarray]:
    """World matrices: +Y toward the next point (last node keeps the previous direction), X from ref_x."""
    out = []
    for i, p in enumerate(points):
        d = points[i + 1] - p if i + 1 < len(points) else p - points[i - 1]
        y = d / np.linalg.norm(d)
        x = ref_x - y * (ref_x @ y)
        if np.linalg.norm(x) < 1e-6:
            x = np.cross(y, [0.0, 0.0, 1.0])
        x /= np.linalg.norm(x)
        z = np.cross(x, y)
        m = np.eye(4)
        m[:3, 0], m[:3, 1], m[:3, 2], m[:3, 3] = x, y, z, p
        out.append(m)
    return out


def _load(data: bytes):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.xbg"
        path.write_bytes(data)
        return xbg_model.load(path), Skeleton(path)


def edit(template: bytes, chains: list[dict], keep_objects: tuple[int, int] | None = None, phys_table: bytes | None = None,
         fix_anchor: bool = False) -> tuple[bytes, dict]:
    """Turn spare physics nodes into chain particles and write a new physics block.

    chains: dicts {"nodes": [node names, root first], "parent": attach bone, "points": [(x, y, z)],
                   "object": smu_format.Obj without nodes/links (params, header, colliders, anchors),
                   "radius": [per node], "link_kinds": [per link], optional "node_parents": [per node]}
    Each node is re-parented (to the attach bone, or its node_parents entry), placed at its point and oriented with
    local +Y toward the next point; inverse binds of every node whose bind changes are rewritten.  The new block is
    the template's FCB part, then (keep_objects=(count, end)) the template's first `count` objects, which end at file
    offset `end`, then the chain objects, then phys_table (raw: u32 count + entries) or an empty table.  The root is
    pinned; fix_anchor gives free nodes anchor index min(1, len(anchors) - 1) instead of the legacy 1."""
    x, sk = _load(template)
    d = bytearray(template)
    records, after = node_records(template, x.palette_offset, len(sk.names))
    count, total = struct.unpack_from("<II", template, after)
    table = (after + 8 + 15) & ~15
    block = table + 64 * total
    world = sk.bind.copy()
    parent = list(sk.parent)
    edited: set[int] = set()
    objects = []
    for ch in chains:
        idx = [sk.index[n] for n in ch["nodes"]]
        if len(set(idx)) != len(idx):
            raise ValueError("duplicate node in chain")
        pa = sk.index[ch["parent"]]
        pts = np.asarray(ch["points"], float)
        frames = chain_frames(pts, world[pa][:3, 0])
        node_parents = [sk.index[q] for q in ch.get("node_parents", [ch["parent"]] * len(idx))]
        for i, m, pn in zip(idx, frames, node_parents):
            if i <= pn:
                raise ValueError(f"{sk.names[i]} comes before its new parent {sk.names[pn]}")
            if sk.b[i] >= count:
                raise ValueError(f"{sk.names[i]} has no skinning matrix (b={sk.b[i]})")
            parent[i] = pn
            world[i] = m
            edited.add(i)
        o = ch["object"]
        n = len(idx)
        free = (min(1, len(o.anchors) - 1) << 16) if fix_anchor else FREE
        nodes = [(ch["nodes"][k], float(ch["radius"][k]), PINNED if k == 0 else free, 0.0, 0.0) for k in range(n)]
        links = [(k, k + 1, int(ch["link_kinds"][k])) for k in range(n - 1)]
        objects.append(S.Obj(offset=0, params=o.params, type=o.type, sub=o.sub, flag=o.flag, spheres=list(o.spheres),
                             capsules=list(o.capsules), nodes=nodes, anchors=list(o.anchors), links=links))
    new_world = np.zeros_like(world)
    for i in range(len(sk.names)):
        if i in edited:
            new_world[i] = world[i]
        elif parent[i] < 0:
            new_world[i] = sk.bind[i]
        else:
            new_world[i] = new_world[parent[i]] @ sk.local[i]
    changed = []
    for i in range(len(sk.names)):
        if i in edited:
            loc = np.linalg.inv(new_world[parent[i]]) @ new_world[i]
            struct.pack_into("<3f", d, records[i] + 4, *loc[:3, 3].astype(np.float32))
            struct.pack_into("<4f", d, records[i] + 16, *np.asarray(mat_to_quat(loc[:3, :3]), np.float32))
            struct.pack_into("<H", d, records[i] + 32, parent[i])
        if np.abs(new_world[i] - sk.bind[i]).max() > 1e-6 and sk.b[i] < total:
            off = table + 64 * sk.b[i]
            d[off:off + 64] = np.linalg.inv(new_world[i]).T.astype("<f4").tobytes()
            changed.append(sk.names[i])
    r = S.Reader(template, block)
    if r.u32() != 1:
        raise ValueError("template has no FCB part")
    fcb_end = r.p + 4 + struct.unpack_from("<I", template, r.p)[0]
    new_block = bytearray(template[block:fcb_end])
    kept = 0
    if keep_objects:
        kept, keep_end = keep_objects
        if struct.unpack_from("<I", template, fcb_end)[0] < kept:
            raise ValueError("template has fewer objects than asked to keep")
        new_block += struct.pack("<I", kept + len(objects)) + template[fcb_end + 4:keep_end]
    else:
        new_block += struct.pack("<I", len(objects))
    for o in objects:
        new_block += S.write_object(o, block + len(new_block))
    new_block += phys_table if phys_table is not None else struct.pack("<I", 0)
    out = bytes(d[:block]) + bytes(new_block) + bytes(template[x.lod_offset:])
    return out, {"edited_nodes": len(edited), "inverse_binds_rewritten": len(changed), "objects": kept + len(objects),
                 "block_bytes": len(new_block), "old_block_bytes": x.lod_offset - block}


def move(template: bytes, targets: dict[str, np.ndarray], parents: dict[str, str] | None = None) -> tuple[bytes, dict]:
    """Move nodes to new world positions (world rotation kept) and optionally give nodes a new parent (world bind
    kept).  Descendants keep their local transform and follow; every node whose bind changes gets its inverse bind
    rewritten.  The physics block is untouched."""
    x, sk = _load(template)
    d = bytearray(template)
    records, after = node_records(template, x.palette_offset, len(sk.names))
    _, total = struct.unpack_from("<II", template, after)
    table = (after + 8 + 15) & ~15
    parent = list(sk.parent)
    target_world = {}
    for name, p in targets.items():
        i = sk.index[name]
        m = sk.bind[i].copy()
        m[:3, 3] = p
        target_world[i] = m
    for name, pa_name in (parents or {}).items():
        i, pa = sk.index[name], sk.index[pa_name]
        if pa >= i:
            raise ValueError(f"{name} comes before its new parent {pa_name}")
        parent[i] = pa
        target_world.setdefault(i, sk.bind[i].copy())
    new_world = np.zeros_like(sk.bind)
    for i in range(len(sk.names)):
        if i in target_world:
            new_world[i] = target_world[i]
        elif parent[i] < 0:
            new_world[i] = sk.bind[i]
        else:
            new_world[i] = new_world[parent[i]] @ sk.local[i]
    changed = []
    for i in target_world:
        pa = parent[i]
        struct.pack_into("<H", d, records[i] + 32, pa if pa >= 0 else 0xFFFF)
        loc = np.linalg.inv(new_world[pa]) @ new_world[i] if pa >= 0 else new_world[i]
        struct.pack_into("<3f", d, records[i] + 4, *loc[:3, 3].astype(np.float32))
        struct.pack_into("<4f", d, records[i] + 16, *np.asarray(mat_to_quat(loc[:3, :3]), np.float32))
    for i in range(len(sk.names)):
        if np.abs(new_world[i] - sk.bind[i]).max() > 1e-6 and sk.b[i] < total:
            off = table + 64 * sk.b[i]
            d[off:off + 64] = np.linalg.inv(new_world[i]).T.astype("<f4").tobytes()
            changed.append(sk.names[i])
    return bytes(d), {"moved_nodes": len(targets), "reparented_nodes": len(parents or {}),
                      "inverse_binds_rewritten": len(changed)}


# ---------------------------------------------------------------- the template's physics block

def block_range(xb) -> tuple[int, int]:
    """File range of the physics block (after the inverse binds, up to the LOD table)."""
    p = Skeleton._after_nodes(xb)
    _, total = struct.unpack_from("<II", xb.data, p)
    return ((p + 8 + 15) & ~15) + 64 * total, xb.lod_offset


def object_starts(data: bytes, start: int, end: int) -> list[int]:
    """Start offsets of the physics objects (u32 0, 12 params with params[0] 0 and gravity <= 0, small header)."""
    out = []
    for o in range(start, end - 64, 4):
        z, f0, g = struct.unpack_from("<Iff", data, o)
        if z == 0 and f0 == 0.0 and -30 < g <= 0:
            prm = struct.unpack_from("<12f", data, o + 4)
            hdr = struct.unpack_from("<3I", data, o + 52)
            if 1 <= hdr[0] <= 16 and hdr[1] <= 16 and hdr[2] <= 1 and all(abs(v) < 100 for v in prm) and prm[2] > 0:
                out.append(o)
    return out


def coat_object_offset(data: bytes, start: int, end: int) -> int:
    """File offset of the coat cloth object (u32 0, 12 params, header 2,0,1) inside the physics block."""
    hits = [o for o in range(start, end - 64, 4) if struct.unpack_from("<I", data, o)[0] == 0
            and struct.unpack_from("<3I", data, o + 52) == COAT_HEADER and struct.unpack_from("<f", data, o + 4)[0] == 0.0
            and struct.unpack_from("<f", data, o + 8)[0] < 0.0]  # gravity: rules out a misaligned read in a jiggle
    if len(hits) != 1:
        raise ValueError(f"coat cloth object found {len(hits)} times")
    return hits[0]


def _record_key(name: str) -> bytes:
    return struct.pack("<II", zlib.crc32(name.encode()) & 0xFFFFFFFF, len(name) + 1) + name.encode() + b"\0"


def coat_particle_flags(data: bytes, coat_off: int, names: list[str]) -> dict[str, int]:
    """File offset of every coat particle's u32 flag field (record: name, f32 radius, u32 flags, f32 u, f32 v)."""
    seg = data[coat_off:coat_off + COAT_SPAN]
    out = {}
    for n in names:
        key = _record_key(n)
        i = seg.find(key)
        if i < 0 or seg.find(key, i + 1) >= 0:
            raise ValueError(f"coat particle record {n} not found exactly once")
        out[n] = coat_off + i + 8 + ((len(n) + 1 + 3) & ~3) + 4
    return out


def coat_capsules(data: bytes, coat_off: int) -> dict[str, int]:
    """File offset of the 7 floats (r0, 0, 0, r1, 0, 0, length) of each capsule collider of the coat cloth object."""
    r = S.Reader(data, coat_off)
    r.u32()
    r.f(12)
    r.f(3)  # type, sub, flag
    out = {}
    for nf in (1, 7, 7, 6):  # lists A (spheres), B, C (capsules), D
        for _ in range(r.u32()):
            bone = r.name()
            r.align16()
            r.f(16)
            if nf == 7:
                out.setdefault(bone, r.p)
            r.f(nf)
    return out


def coat_layout(data: bytes, start: int, end: int, names: list[str]) -> dict:
    """Where the coat cloth sits in the template's object list, and the table without entries that reference the
    objects after it.  The table holds entries of kind 2 (12 bytes: u16 particle, u16 2, u16 target, u16 0, f32
    weight) and kind 6 (24 bytes); particles are numbered globally in object order."""
    starts = object_starts(data, start, end)
    coat = coat_object_offset(data, start, end)
    if coat not in starts or starts.index(coat) == len(starts) - 1:
        raise ValueError("unexpected physics object layout (no coat cloth followed by other objects)")
    keep = starts.index(coat) + 1
    cut = 0
    for o in starts[:keep - 1]:
        cut += len(S.parse_object(S.Reader(data, o)).nodes)
    seg = data[coat:starts[keep]]
    cut += sum(1 for n in names if n.startswith(COAT_PREFIX) and _record_key(n) in seg)
    r = S.Reader(data, starts[-1])
    S.parse_object(r)
    n = r.u32()
    p = r.p
    kept, dropped = [], 0
    for _ in range(n):
        a, kind = struct.unpack_from("<HH", data, p)
        size = {2: 12, 6: 24}.get(kind)
        if size is None:
            raise ValueError(f"unknown table entry kind {kind}")
        refs = [a] + ([struct.unpack_from("<H", data, p + 4)[0]] if kind == 2 else [])
        if max(refs) >= cut:
            dropped += 1
        else:
            kept.append(data[p:p + size])
        p += size
    if p != end:
        raise ValueError("the table does not end at the block end")
    return {"objects": len(starts), "coat": coat, "keep": keep, "keep_end": starts[keep], "global_cut": cut,
            "table": struct.pack("<I", len(kept)) + b"".join(kept), "table_entries": n, "table_dropped": dropped}


# ---------------------------------------------------------------- coat particles and the mesh

def particles(sk) -> tuple[list[str], np.ndarray]:
    names = [n for i, n in enumerate(sk.names) if n.startswith(COAT_PREFIX) and sk.b[i] < SKINNABLE]
    return names, np.array([sk.bind[sk.index[n]][:3, 3] for n in names])


def around(p: np.ndarray, centre: np.ndarray) -> np.ndarray:
    """Angle around the body measured from the back (-Y), so the front opening (+Y) is the cut at +-pi."""
    return np.arctan2(-(p[:, 0] - centre[0]), -(p[:, 1] - centre[1]))


def particle_weights(pts: np.ndarray, part_pos: np.ndarray, centre: np.ndarray, k: int,
                     sigma: float | None) -> tuple[np.ndarray, np.ndarray]:
    """The k nearest particles by angle and height: inverse-square weights, or Gaussian ones when sigma is set."""
    a_v, a_p = around(pts, centre), around(part_pos, centre)
    d = np.hypot(R_ARC * (a_v[:, None] - a_p[None, :]), pts[:, 2][:, None] - part_pos[:, 2][None, :])
    idx = np.argsort(d, axis=1)[:, :k]
    dd = np.take_along_axis(d, idx, 1)
    w = np.exp(-0.5 * (dd / sigma) ** 2) if sigma else 1.0 / np.maximum(dd, 1e-3) ** 2
    return idx, w / w.sum(1, keepdims=True)


def particle_targets(sk, cloth_pts: np.ndarray, centre: np.ndarray) -> dict[str, np.ndarray]:
    """Push every coat particle radially out to the garment's surface (median radius of its vertices around the same
    angle and height; wider windows past its edge).  Particles never move inwards."""
    names = [n for n in sk.names if n.startswith(COAT_PREFIX)]
    pos = np.array([sk.bind[sk.index[n]][:3, 3] for n in names])
    a_p, a_c = around(pos, centre), around(cloth_pts, centre)
    r_p = np.hypot(pos[:, 0] - centre[0], pos[:, 1] - centre[1])
    r_c = np.hypot(cloth_pts[:, 0] - centre[0], cloth_pts[:, 1] - centre[1])
    out = {}
    for n, p, a, r in zip(names, pos, a_p, r_p):
        da = np.abs((a_c - a + np.pi) % (2 * np.pi) - np.pi)
        for win_a, win_z in ((np.radians(12), 0.05), (np.radians(20), 0.1), (np.radians(30), 0.3)):
            sel = (da < win_a) & (np.abs(cloth_pts[:, 2] - p[2]) < win_z)
            if sel.sum() >= 10:
                rk = float(np.median(r_c[sel]))
                if rk > r:
                    q = p.copy()
                    q[:2] = centre[:2] + (p[:2] - centre[:2]) * rk / r
                    out[n] = q
                break
    return out


def clear_of_capsules(data: bytes, coat_off: int, sk, targets: dict, bones=("L Thigh", "R Thigh")) -> dict:
    """Push coat particles (at their target or bind position) radially out of the given capsule colliders so that none
    starts inside one (radius + particle radius + margin).  Returns the updated targets."""
    caps_at = coat_capsules(data, coat_off)
    segs = []
    for bone in bones:
        m = np.array(struct.unpack_from("<16f", data, caps_at[bone] - 64)).reshape(4, 4).T
        f7 = struct.unpack_from("<7f", data, caps_at[bone])
        w = sk.bind[sk.index[bone]] @ m
        segs.append((w[:3, 3], w[:3, 3] + w[:3, 2] * f7[6], f7[0], f7[3]))
    out = dict(targets)
    for n in [nm for nm in sk.names if nm.startswith(COAT_PREFIX)]:
        p = np.array(out.get(n, sk.bind[sk.index[n]][:3, 3]), float)
        for _ in range(3):
            for a, b, r0, r1 in segs:
                ab = b - a
                t = float(np.clip((p - a) @ ab / (ab @ ab), 0, 1))
                c = a + t * ab
                need = r0 + (r1 - r0) * t + PARTICLE_RADIUS + CLEAR_MARGIN
                dist = np.linalg.norm(p - c)
                if dist < need:
                    p = c + (p - c) / max(dist, 1e-6) * need
        if np.abs(p - sk.bind[sk.index[n]][:3, 3]).max() > 1e-6:
            out[n] = p
    return out


# ---------------------------------------------------------------- colliders

def leg_capsules(data: bytes, coat_off: int) -> list:
    """The coat cloth's thigh, pelvis and calf capsules (bone, matrix, f7) in their bones' frames."""
    caps_at = coat_capsules(data, coat_off)
    out = []
    for bone, off in caps_at.items():
        if bone in LEG_CAPSULES:
            out.append((bone, struct.unpack_from("<16f", data, off - 64), struct.unpack_from("<7f", data, off)))
    return out


def mirror_capsule(cap):
    """Mirror a capsule across the bone's local XY plane (Spine2's local Z is the body's left-right axis)."""
    bone, m, f7 = cap
    mat = np.array(m).reshape(4, 4).T
    sz = np.diag([1.0, 1.0, -1.0, 1.0])
    return bone, tuple((sz @ mat @ sz).T.reshape(-1)), f7


def capsule_between(sk, bone: str, a: np.ndarray, b: np.ndarray, radius: float):
    """A capsule from world point a to b (radius) stored in bone's frame (axis = local +Z, length in f7[6])."""
    z = (b - a) / np.linalg.norm(b - a)
    x = np.cross([0.0, 1.0, 0.0], z)
    if np.linalg.norm(x) < 1e-6:
        x = np.cross([1.0, 0.0, 0.0], z)
    x /= np.linalg.norm(x)
    w = np.eye(4)
    w[:3, 0], w[:3, 1], w[:3, 2], w[:3, 3] = x, np.cross(z, x), z, a
    local = np.linalg.inv(sk.bind[sk.index[bone]]) @ w
    return bone, tuple(local.T.reshape(-1)), (radius, 0.0, 0.0, radius, 0.0, 0.0, float(np.linalg.norm(b - a)))


def derived_colliders(sk, kind: str) -> tuple[list, list]:
    """Capsules built from the skeleton alone (untested in game; export a game object's colliders for tested ones).
    body: chest, neck and head; face: the head."""
    h = sk.head
    up = np.array([0.0, 0.0, 1.0])
    head = [capsule_between(sk, "Head", h("Head"), h("Head") + 0.15 * up, 0.085)] if "Head" in sk.index else []
    if kind == "face":
        return [], head
    caps = []
    if "Spine2" in sk.index and "Neck" in sk.index:
        caps.append(capsule_between(sk, "Spine2", h("Spine2") - 0.1 * up, h("Neck"), 0.12))
    if "Neck" in sk.index and "Head" in sk.index:
        caps.append(capsule_between(sk, "Neck", h("Neck"), h("Head"), 0.05))
    return [], caps + head


def read_objects(path) -> tuple[list[str], list]:
    """Node names and physics objects of a game character XBG (non-ZModeler layout; the node table is found by
    its pattern: u32 1, u32 n, then n records of u32 0x64, 7 f32, u16 parent, u16 b, name)."""
    d = Path(path).read_bytes()
    p = 0
    while True:
        p = d.find(struct.pack("<I", 1), p)
        if p < 0:
            raise ValueError("node table not found")
        n = struct.unpack_from("<I", d, p + 4)[0]
        if 2 <= n <= 2000 and struct.unpack_from("<I", d, p + 8)[0] == 0x64:
            names, q = [], p + 8
            for _ in range(n):
                if q + 44 > len(d) or struct.unpack_from("<I", d, q)[0] != 0x64:
                    break
                ln = struct.unpack_from("<I", d, q + 40)[0]
                if not 1 <= ln <= 128:
                    break
                try:
                    names.append(d[q + 44:q + 44 + ln].rstrip(b"\0").decode("ascii"))
                except UnicodeDecodeError:
                    break
                q += 44 + ((ln + 3) & ~3)
            if len(names) == n:
                break
        p += 4
    _, total = struct.unpack_from("<II", d, q)
    r = S.Reader(d, ((q + 8 + 15) & ~15) + total * 64)
    if r.u32():
        r.p += 4 + struct.unpack_from("<I", d, r.p)[0]
    return names, [S.parse_object(r) for _ in range(r.u32())]


def export_colliders(xbg: Path) -> dict:
    _, objects = read_objects(xbg)
    out = {}
    for o in objects:
        if o.nodes:
            out[o.nodes[0][0]] = {"spheres": [[b, list(m), r] for b, m, r in o.spheres],
                                  "capsules": [[b, list(m), list(f7)] for b, m, f7 in o.capsules]}
    return {"schema": "watchdogs.physics_colliders.v1", "source": xbg.name, "objects": out}


def collider_set(spec: list, sk, legs: list, exported: dict | None) -> tuple[list, list]:
    """Build one collider set from its profile spec: items {"from": object key[, "mirror": [bones]],
    "fallback": "body"|"face"} | {"legs": true} | {"derived": "body"|"face"} | {"arm": "L"|"R", "radius": r}
    (upper arm and forearm capsules from joint to joint)."""
    spheres, caps = [], []
    for item in spec:
        if item.get("legs"):
            caps += legs
        elif item.get("arm"):
            s_, r = item["arm"], float(item.get("radius", 0.05))
            caps.append(capsule_between(sk, f"{s_} UpperArm", sk.head(f"{s_} UpperArm"), sk.head(f"{s_} Forearm"), r))
            caps.append(capsule_between(sk, f"{s_} Forearm", sk.head(f"{s_} Forearm"), sk.head(f"{s_} Hand"), r))
        elif "from" in item and exported and item["from"] in exported["objects"]:
            src = exported["objects"][item["from"]]
            mirror = set(item.get("mirror", []))
            spheres += [(b, tuple(m), r) for b, m, r in src["spheres"]]
            for b, m, f7 in src["capsules"]:
                cap = (b, tuple(m), tuple(f7))
                caps.append(mirror_capsule(cap) if b in mirror else cap)
        else:
            s, c = derived_colliders(sk, item.get("derived") or item.get("fallback", "body"))
            spheres += s
            caps += c
    return spheres, caps


def clearance(sk, caps, p: np.ndarray) -> tuple[float, str]:
    """Distance (m) from point p to the surface of the nearest capsule, and that capsule's bone."""
    best = (9.0, "")
    for bone, m, f7 in caps:
        w = sk.bind[sk.index[bone]] @ np.array(m).reshape(4, 4).T
        a = w[:3, 3]
        b = a + w[:3, 2] * f7[6]
        ab = b - a
        t = np.clip((p - a) @ ab / (ab @ ab), 0, 1)
        dd = np.linalg.norm(p - (a + t * ab)) - (f7[0] + (f7[3] - f7[0]) * t)
        best = min(best, (float(dd), bone))
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description="Watch Dogs char01 physics helpers.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    ex = sub.add_parser("export-colliders", help="write the collider lists of a game character XBG as JSON")
    ex.add_argument("--xbg", required=True, type=Path)
    ex.add_argument("--out", required=True, type=Path)
    ex.add_argument("--force", action="store_true")
    args = ap.parse_args()
    if args.out.exists() and not args.force:
        raise SystemExit(f"refusing to overwrite {args.out} (use --force)")
    data = export_colliders(args.xbg)
    args.out.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    print(f"{len(data['objects'])} objects -> {args.out}")


if __name__ == "__main__":
    main()
