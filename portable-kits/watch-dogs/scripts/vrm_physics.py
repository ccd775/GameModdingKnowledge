"""Optional physics step of build_from_vrm.py, driven by the profile's "physics" section.

  "physics": {
    "colliders": {set name: [{"from": exported object key, "mirror": [bones], "fallback": "body"|"face"}
                             | {"legs": true} | {"derived": "body"|"face"}, ...]},
    "chains": [{"start": VRM joint, "attach": char01 bone, "colliders": set name, "gravity": g, "damping": d,
                "pull": p, "radius": [root, 30 %, tip], "pool": "spare"|"collar"|"coat"|"any",
                optional "anchors": [bones], "drop_end": true, "link_kind": 1}, ...],
    "cloth": {"joints": VRM joint prefix (e.g. "Skirt_"), "skip": [joint names], "gravity": -2.0,
              "damping_scale": 0.12, "k": 8, "sigma": 0.08, "thigh_radius": 0.125, "hang_from_pelvis": true},
    "double_sided": [VRM part names, e.g. "skirt/0"]
  }

Chains: every VRM joint of the chain becomes one spare char01 physics node at the joint's fitted position (root
pinned to its animated pose, the others simulated); the vertices weighted to those joints follow the nodes 1:1.
Cloth: the template's coat cloth carries a skirt or coat.  Its particles are pushed out onto the garment, the
thigh-hung ones (and with hang_from_pelvis the spine-pinned ones) are hung from the Pelvis in the skeleton and in
the cloth's anchors, and each garment vertex's share on the chain joints below each chain root goes to its k nearest
particles by angle and height.  The objects after the coat cloth (collars, belts, zipper, pockets) are dropped, which
frees their nodes for the chains; their table entries are dropped too.
Colliders: "from" items need --colliders, a file written by `xbg_physics.py export-colliders` from a game XBG;
without it the item's fallback (capsules built from the skeleton, untested in game) is used.
"""

from __future__ import annotations

import struct
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import smu_format as S  # noqa: E402
import vrm_fit  # noqa: E402
import xbg_model  # noqa: E402
import xbg_physics as P  # noqa: E402
from xbg_skeleton import Skeleton  # noqa: E402

CHAIN_HEADER = (4, 1, 1)  # type, sub (chain), flag: as the game's ponytail chains


def chain_params(gravity: float, damping: float, pull: float) -> tuple:
    return (0.0, gravity, damping, damping, damping, 0.1, 0.1, 0.0, 0.0, pull, 0.0, 0.0)


def vrm_chain(m, start: str) -> list[int]:
    """The joint and its first-child descendants down to the leaf."""
    kids: dict[int, list[int]] = {}
    for i, p in enumerate(m.parent):
        kids.setdefault(p, []).append(i)
    i = m.node_names.index(start)
    out = [i]
    while kids.get(i):
        i = kids[i][0]
        out.append(i)
    return out


def _skeleton(data: bytes, tmp: Path):
    path = tmp / "t.xbg"
    path.write_bytes(data)
    return Skeleton(path)


class Rig:
    """Physics of one build: rig() edits the fitted template, override() maps the weights, mesh_parts() adds the
    back faces."""

    def __init__(self, cfg: dict, fit, sk, exported: dict | None = None):
        self.cfg, self.fit, self.sk, self.exported = cfg, fit, sk, exported
        self.report: dict = {}

    def rig(self, patched: bytes) -> bytes:
        cfg, fit, m = self.cfg, self.fit, self.fit.vrm
        base = _xbg(patched)
        blk0, blk1 = P.block_range(base)
        with tempfile.TemporaryDirectory() as tmp:
            sk0 = _skeleton(patched, Path(tmp))
            layout = P.coat_layout(patched, blk0, blk1, sk0.names)
            coat_off = layout["coat"]
            legs = P.leg_capsules(patched, coat_off)  # chain colliders use the template's capsules as they are
            cloth = cfg.get("cloth")
            data = bytearray(patched)
            capsules_changed = {}
            if cloth:
                before = struct.unpack_from("<12f", data, coat_off + 4)
                struct.pack_into("<f", data, coat_off + 8, cloth.get("gravity", before[1]))
                scale = cloth.get("damping_scale", 1.0)
                struct.pack_into("<3f", data, coat_off + 12, *(v * scale for v in before[2:5]))
                if cloth.get("thigh_radius"):
                    caps_at = P.coat_capsules(bytes(data), coat_off)
                    for bone in ("L Thigh", "R Thigh"):
                        f7 = list(struct.unpack_from("<7f", data, caps_at[bone]))
                        f7[0] = f7[3] = cloth["thigh_radius"]
                        struct.pack_into("<7f", data, caps_at[bone], *f7)
                        capsules_changed[bone] = f7
            data = bytes(data)
            skf = _skeleton(data, Path(tmp))
            self.centre = skf.bind[skf.index["Pelvis"]][:3, 3]
            names = m.node_names
            self.cloth_swing, self.cloth_all, move_report, switched = set(), set(), None, 0
            if cloth:
                prefix, skip = cloth["joints"], set(cloth.get("skip", []))
                chains = [vrm_chain(m, n) for n in names if n.startswith(prefix) and "." not in n and n not in skip]
                self.cloth_swing = {j for js in chains for j in js[1:]}
                self.cloth_all = {j for js in chains for j in js}
                pts = np.concatenate([part.positions[(np.isin(part.joints, list(self.cloth_all)) & (part.weights > 0)).any(1)]
                                      for part in fit.parts])
                targets = P.particle_targets(skf, pts, self.centre)
                if cloth.get("thigh_radius"):
                    targets = P.clear_of_capsules(data, coat_off, skf, targets)
                leg_hung = [n for i, n in enumerate(skf.names)
                            if n.startswith(P.COAT_PREFIX) and skf.names[skf.parent[i]] in P.LEG_HELPERS]
                spine_hung = [n for i, n in enumerate(skf.names) if n.startswith(P.COAT_PREFIX)
                              and skf.names[skf.parent[i]] in P.SPINE_BONES] if cloth.get("hang_from_pelvis") else []
                data, move_report = P.move(data, targets, {n: "Pelvis" for n in leg_hung + spine_hung})
                data = bytearray(data)
                groups = (0, 1, 3, 4, 5) if cloth.get("hang_from_pelvis") else (0, 1)
                flags = P.coat_particle_flags(data, coat_off, [n for n in skf.names if n.startswith(P.COAT_PREFIX)])
                for n, off in flags.items():
                    f = struct.unpack_from("<I", data, off)[0]
                    if f >> 16 in groups:
                        struct.pack_into("<I", data, off, (P.PELVIS_ANCHOR << 16) | (f & 0xFFFF))
                        switched += 1
                if switched != len(leg_hung) + len(spine_hung):
                    raise SystemExit("coat anchor switch count mismatch")
                data = bytes(data)
            sk_c = _skeleton(data, Path(tmp))
            used: set[int] = set()

            def take(n: int, after: int, pool: str) -> list[str]:
                free = [i for i, nm in enumerate(sk_c.names) if nm.startswith(P.POOLS[pool]) and sk_c.b[i] < P.SKINNABLE]
                got = [i for i in free if i > after and i not in used][:n]
                if len(got) < n:
                    raise SystemExit(f"not enough spare physics nodes in pool {pool!r}")
                used.update(got)
                return [sk_c.names[i] for i in sorted(got)]

            sets = {name: P.collider_set(spec, sk_c, legs, self.exported) for name, spec in cfg.get("colliders", {}).items()}
            sets.setdefault("none", ([], []))
            sets.setdefault("legs", ([], legs))
            self.joint_to_node, rig_chains, chains_report = {}, [], []
            for ch in cfg.get("chains", []):
                js = vrm_chain(m, ch["start"])
                if ch.get("drop_end"):
                    js = js[:-1]
                pts = fit.posed_joint[js]
                n = len(js)
                attach = ch["attach"]
                spheres, caps = sets[ch.get("colliders", "none")]
                anchors = ch.get("anchors") or (["Facial_Hook", "Head"] if attach == "Head" else [attach])
                nodes = take(n, sk_c.index[attach], ch.get("pool", "spare"))
                for j, nd in zip(js, nodes):
                    self.joint_to_node[j] = nd
                o = S.Obj(offset=0, params=chain_params(ch["gravity"], ch["damping"], ch["pull"]), type=CHAIN_HEADER[0],
                          sub=CHAIN_HEADER[1], flag=CHAIN_HEADER[2], spheres=spheres, capsules=caps, anchors=anchors)
                rig_chains.append({"nodes": nodes, "parent": attach, "points": pts, "object": o,
                                   "radius": np.interp(np.linspace(0, 1, n), [0, 0.3, 1], ch["radius"]),
                                   "link_kinds": [ch.get("link_kind", 1)] * (n - 1)})
                chains_report.append({"start": ch["start"], "joints": [names[j] for j in js], "nodes": nodes,
                                      "anchors": anchors,
                                      "clearance_cm": [round(P.clearance(sk_c, caps, p)[0] * 100, 1) for p in pts] if caps else []})
            rigged, rig_report = P.edit(data, rig_chains, keep_objects=(layout["keep"], layout["keep_end"]),
                                        phys_table=layout["table"], fix_anchor=True)
            skp = _skeleton(rigged, Path(tmp))
            for ch in rig_chains:
                for nd, p in zip(ch["nodes"], ch["points"]):
                    i = skp.index[nd]
                    if np.abs(skp.head(nd) - p).max() > 1e-4 or np.abs(skp.bind[i] @ skp.inv_bind[skp.b[i]] - np.eye(4)).max() > 1e-4:
                        raise SystemExit(f"{nd} misplaced or inverse bind mismatch")
            self.p_names, self.p_pos = P.particles(skp)
        self._check_block(rigged, data, layout, len(rig_chains))
        self.report = {"objects_kept": layout["keep"], "objects_dropped": layout["objects"] - layout["keep"],
                       "table_entries": layout["table_entries"], "table_dropped": layout["table_dropped"],
                       "global_cut": layout["global_cut"], "coat_capsules_changed": capsules_changed,
                       "particles_moved": move_report, "anchors_switched": switched, "rig": rig_report,
                       "chains": chains_report}
        return rigged

    @staticmethod
    def _check_block(rigged: bytes, before: bytes, layout: dict, n_chains: int) -> None:
        x = _xbg(rigged)
        b0, b1 = P.block_range(x)
        a0 = P.block_range(_xbg(before))[0]
        fcb = struct.unpack_from("<I", x.data, b0 + 4)[0]
        if struct.unpack_from("<I", x.data, b0 + 8 + fcb)[0] != layout["keep"] + n_chains:
            raise SystemExit("physics object count wrong")
        kept = layout["keep_end"] - (a0 + 12 + fcb)
        if x.data[b0 + 12 + fcb:b0 + 12 + fcb + kept] != before[a0 + 12 + fcb:layout["keep_end"]]:
            raise SystemExit("kept physics objects changed")
        r = S.Reader(x.data, b0 + 12 + fcb + kept)
        for _ in range(n_chains):
            S.parse_object(r)
        if x.data[r.p:b1] != layout["table"]:
            raise SystemExit("physics table mismatch")

    def human_bone(self, j: int) -> str:
        fit, m = self.fit, self.fit.vrm
        by_node = {v: k for k, v in fit.human_node.items()}
        while j >= 0 and j not in by_node:
            j = m.parent[j]
        h = by_node.get(j)
        if h == "spine":
            return "Spine"
        if h in ("upperChest", "chest"):
            return "Spine2"
        return vrm_fit.HUMAN_TO_AIDEN.get(h, "Pelvis")

    def override(self, part, w: list) -> list:
        """Chain joints 1:1 to their nodes; the cloth share onto the coat particles; other joints of the touched
        vertices to their humanoid bone."""
        cloth = self.cfg.get("cloth") or {}
        special = set(self.joint_to_node) | self.cloth_all
        hit = np.isin(part.joints, list(special)) & (part.weights > 0)
        for i in np.flatnonzero(hit.any(1)):
            acc: dict[str, float] = {}
            share = 0.0
            for j, wk in zip(part.joints[i], part.weights[i]):
                if wk <= 0:
                    continue
                j = int(j)
                if j in self.joint_to_node:
                    acc[self.joint_to_node[j]] = acc.get(self.joint_to_node[j], 0.0) + float(wk)
                elif j in self.cloth_swing:
                    share += float(wk)
                else:
                    acc[self.human_bone(j)] = acc.get(self.human_bone(j), 0.0) + float(wk)
            if share > 0:
                ii, ww = P.particle_weights(part.positions[i][None, :], self.p_pos, self.centre, cloth.get("k", 8),
                                            cloth.get("sigma", 0.08))
                for k, a in zip(ii[0], ww[0]):
                    acc[self.p_names[k]] = acc.get(self.p_names[k], 0.0) + share * float(a)
            tot = sum(acc.values())
            w[i] = {k: v / tot for k, v in acc.items()}
        return w

    def mesh_parts(self, parts: list, weights: list) -> tuple[list, list]:
        """Append a back-face copy of every double-sided part: same vertices, weights and UVs, reversed triangles,
        negated normals, so the part is visible from inside and both sides deform together."""
        names = set(self.cfg.get("double_sided", []))
        out_p, out_w, added = list(parts), list(weights), []
        for part, w in zip(parts, weights):
            if part.name in names:
                out_p.append(replace(part, name=part.name + "/back", normals=-part.normals,
                                     triangles=part.triangles[:, ::-1].copy()))
                out_w.append([dict(d) for d in w])
                added.append(part.name)
        if set(added) != names:
            raise SystemExit(f"double-sided parts not found: {sorted(names - set(added))}")
        self.report["double_sided"] = added
        return out_p, out_w


def _xbg(data: bytes):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "t.xbg"
        path.write_bytes(data)
        return xbg_model.load(path)
