"""Generate the DD2Tool chainbuild spec for Karin's secondary bones (K_* joints of karin_body.mesh).

Base = DD2 body_chain.chain.55 (breast jiggle, belt hooks, back props keep working); Karin groups are appended.
Nested chains (a chain whose parent joint is itself simulated) are left rigid on purpose.

usage: python make_chain_spec.py <build_report.json> <out_spec.json> <out_chain> [variant] [child] [--profile=original]
           --native-dir <dir> --inventory <inventory.json>
  --native-dir (or DD2_NATIVE_DIR): the folder DD2Tool extract wrote, holding natives/stm/character/... (the native
  chains below are read by DD2Tool chainbuild; the spec stores their absolute paths).
  --inventory: the source model's bone hierarchy ({"armatures": [{"bones": [{"name", "parent"}, ...]}]}); for the
  original profile it is <out_dir>/inventory.json of scripts/blender/prepare_karin_original.py.
"""
import argparse
import json
import os
import sys
from pathlib import Path

# native chain templates, relative to <native-dir>/natives/stm/character
BODY = "_kit/body/_common/secondary/body_chain.chain.55"
HAIR011 = "_kit/hair/hair_011/hair_011.chain.55"
HAIR001 = "_kit/hair/hair_001/hair_001.chain.55"
MANTLE = "_kit/_equipment/mantle/523/mantle_523_f.chain.55"

SETTINGS = {
    # long, heavy twin tails
    "hair_long": {"file": HAIR011, "index": 0, "set": {"damping": 0.15, "minDamping": 0.15, "springForce": 0.35}},
    "hair": {"file": HAIR011, "index": 0},
    "hair_stiff": {"file": HAIR011, "index": 1, "set": {"springForce": 0.45}},
    "ear": {"file": HAIR011, "index": 1, "set": {"springForce": 0.8, "damping": 0.4, "minDamping": 0.4}},
    "ribbon": {"file": HAIR001, "index": 0, "set": {"damping": 0.05, "minDamping": 0.05, "springForce": 0.02}},
    "cord": {"file": HAIR001, "index": 0, "set": {"damping": 0.15, "minDamping": 0.15, "springForce": 0.05}},
    "tail": {"file": HAIR011, "index": 0, "set": {"springForce": 0.35, "damping": 0.15, "minDamping": 0.15}},
    "coat": {"file": MANTLE, "index": 0, "set": {"springForce": 0.08, "damping": 0.08}},
    "skirt": {"file": MANTLE, "index": 0, "set": {"springForce": 0.25, "damping": 0.2}},
}
HAIR_T = {"file": HAIR011, "group": 1}
COAT_T = {"file": MANTLE, "group": 0}

# (chain root karin bone, setting, template, radius root->tip, node overrides)
ROOTS = [
    ("Hair_Tail.L", "hair_long", HAIR_T, [0.03, 0.02], {"angleLimitRadius": 0.7}),
    ("Hair_Tail.R", "hair_long", HAIR_T, [0.03, 0.02], {"angleLimitRadius": 0.7}),
    ("Hair_Side_1.L", "hair", HAIR_T, [0.012, 0.012], {"angleLimitRadius": 0.6}),
    ("Hair_Side_1.R", "hair", HAIR_T, [0.012, 0.012], {"angleLimitRadius": 0.6}),
    ("Hair_Front", "hair_stiff", HAIR_T, [0.01, 0.01], None),
    ("Ahoge", "hair_stiff", HAIR_T, [0.005, 0.005], None),
    ("Ear_1.L", "ear", HAIR_T, [0.02, 0.015], {"angleLimitRadius": 0.35}),
    ("Ear_1.R", "ear", HAIR_T, [0.02, 0.015], {"angleLimitRadius": 0.35}),
    ("Ribbon_1.L", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Ribbon_1.R", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Code.L", "cord", HAIR_T, [0.008, 0.008], None),
    ("Code.R", "cord", HAIR_T, [0.008, 0.008], None),
    ("Tail_1", "tail", HAIR_T, [0.06, 0.04], {"angleLimitRadius": 1.0}),
    ("Belt_Ribbon", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Belt_Ribbon_3", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Belt_Ribbon_5", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Belt_Ribbon_8", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Belt_String_1.L", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Belt_String_1.R", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Right_Belt_1", "ribbon", HAIR_T, [0.01, 0.01], None),
    ("Leg_Ring_Ribbon", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Leg_Ring_Ribbon_3", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Leg_Ribbon", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Leg_Ribbon_3", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Leg_Ribbon_5", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Leg_Ribbon_9", "ribbon", HAIR_T, [0.008, 0.008], None),
]
for side in ("L", "R"):
    for c in "ABCD":
        ROOTS.append((f"Outer{c}.{side}", "coat", COAT_T, [0.03, 0.045], None))
ROOTS.append(("OuterB", "coat", COAT_T, [0.03, 0.045], None))

# Karin_Original (VRM spring roots; every chain ends in the model's unweighted "*_end" tip bone). The Cheek_* bones
# stay rigid: they weight face skin (her VRM "cheek" jiggle, 166 face vertices), not hair; the locks along her cheeks
# are Hair_side_*.
ROOTS_ORIGINAL = []
for side in ("L", "R"):
    ROOTS_ORIGINAL += [
        (f"Hair_tail_{side}", "hair_long", HAIR_T, [0.03, 0.02], {"angleLimitRadius": 0.7}),
        (f"Hair_side_{side}", "hair", HAIR_T, [0.012, 0.012], {"angleLimitRadius": 0.6}),
        (f"Hair_front_{side}", "hair_stiff", HAIR_T, [0.01, 0.01], None),
        (f"Ear_{side}", "ear", HAIR_T, [0.02, 0.015], {"angleLimitRadius": 0.35}),
        (f"Ribbon_{side}", "ribbon", HAIR_T, [0.01, 0.01], None),
        (f"Ribbon_tops_{side}", "ribbon", HAIR_T, [0.01, 0.01], None),
        (f"Ribbon_hand_{side}_1", "ribbon", HAIR_T, [0.008, 0.008], None),
        (f"Ribbon_hand_{side}_2", "ribbon", HAIR_T, [0.008, 0.008], None),
        (f"Shoes_tag_{side}", "cord", HAIR_T, [0.008, 0.008], None),
    ]
ROOTS_ORIGINAL += [
    ("Hair_front", "hair_stiff", HAIR_T, [0.01, 0.01], None),
    ("Ribbon_camisole", "ribbon", HAIR_T, [0.008, 0.008], None),
    ("Tail", "tail", HAIR_T, [0.06, 0.04], {"angleLimitRadius": 1.5}),
]
# Skirt swing limit: a cone per node, tilted outward (see "tilt" below) so a piece may swing in ~11 deg but out ~40 deg.
# The mantle template's 75 deg oval let walking fold the front pieces up to 18 cm into her belly and crotch, where no
# collider is; a tight symmetric cone kept them out but left a forward-swinging thigh no room to push the hem forward,
# so the thigh split the skirt between two pieces and showed through (all measured live).
ROOTS_ORIGINAL += [(f"Skirt_{p}", "skirt", COAT_T, [0.008, 0.012], {"angleMode": "LimitCone", "angleLimitRadius": 0.45})
                   for p in ["0", "8"] + [f"{i}_{side}" for i in range(1, 8) for side in ("L", "R")]]
PROFILES = {
    "picodra": {"roots": ROOTS},
    # group field overrides per setting. The skirt hits only the thighs (V15/V16 of body_female.clsp): the native hip
    # and spine capsules are sized for the native body and sit around Karin's skirt roots, which blew the skirt out.
    # tilt: per setting, the angle limit cone's axis is the rest direction turned this far (rad) away from the hip axis.
    "original": {"roots": ROOTS_ORIGINAL,
                 "group": {"skirt": {"clspFlags1": "V15, V16", "clspFlags2": "0"}}, "tilt": {"skirt": 0.25}},
}

# chain end overrides where a bone has several children (follow the named tip)
TIPS = {"OuterB.L": "OuterB_4.L", "OuterB.R": "OuterB_4.R", "OuterB": "OuterB_4", "Back_Ribbon_4": "Back_Ribbon_12"}


# VRM secondaryAnimation reference (karin_picodra.vrm): stiffness / gravityPower / dragForce per group
VRM = {
    "hair_long": (0.447, 0.447, 0.424), "hair": (0.316, 0.224, 0.283), "hair_stiff": (0.316, 0.0, 0.283),
    "ear": (0.31, 0.0, 0.26), "ribbon": (0.316, 0.1, 0.245), "cord": (0.0, 0.548, 0.283),
    "tail": (0.316, 0.0, 0.224), "coat": (0.167, 0.151, 0.283), "skirt": (0.2, 0.0, 0.49),
}


def apply_variant(spec, variant):
    """A: first in-game version; B: VRM-derived; C: B with softer twin tails; D: no spring (gravity only);
    E: strong spring, no gravity (shows the pose the engine springs back to)."""
    if variant in ("F", "O"):
        # (spring, gravity m/s^2, damping). F: final PicodraTech, VRM-shaped. O: Karin_Original, tuned live with the user
        # (her joints held to the rest pose every frame, CHAIN_REST_POSE): twin tails and tail weightless like in her VRM,
        # light spring and damping for a wide swing; side hair a little gravity; skirt near its rest shape
        table = {
            "F": {"hair_long": (0.3, 5.0, 0.2), "hair": (0.25, 3.0, 0.15), "hair_stiff": (0.3, 0.0, 0.2), "ear": (0.5, 0.0, 0.3),
                  "ribbon": (0.25, 1.0, 0.12), "cord": (0.02, 6.0, 0.15), "tail": (0.3, 0.0, 0.12), "coat": (0.12, 2.0, 0.14)},
            "O": {"hair_long": (0.03, 0.0, 0.015), "hair": (0.08, 1.8, 0.05), "hair_stiff": (0.3, 2.0, 0.2), "ear": (0.5, 0.0, 0.3),
                  "ribbon": (0.06, 6.0, 0.1), "cord": (0.02, 6.0, 0.15), "tail": (0.05, 0.0, 0.015), "skirt": (0.08, 2.0, 0.2)},
        }[variant]
        for key, st in spec["settings"].items():
            sp, gr, dm = table[key]
            st.setdefault("set", {}).update({"springForce": sp, "damping": dm, "minDamping": dm, "gravity": [0.0, -gr, 0.0]})
        for g in spec["groups"]:
            g.setdefault("node", {})["gravityCoef"] = 1.0
            if g["setting"] in ("hair_long", "hair"):
                g["node"].pop("angleLimitRadius", None)
        return
    if variant == "A":
        spec["settings"]["hair_long"]["set"] = {"damping": 0.12, "minDamping": 0.12, "springForce": 0.12}
        for g in spec["groups"]:
            if g["setting"] in ("hair_long", "hair") and "node" in g:
                g["node"].pop("angleLimitRadius", None)
        return
    for key, st in spec["settings"].items():
        stiff, grav, drag = VRM[key]
        st.setdefault("set", {})
        if variant in ("B", "C"):
            st["set"].update({"springForce": round(stiff * 0.6, 3), "damping": round(drag * 0.5, 3), "minDamping": round(drag * 0.5, 3)})
            if variant == "C" and key == "hair_long":
                st["set"]["springForce"] = 0.12
        elif variant == "D":
            st["set"].update({"springForce": 0.0})
        elif variant == "E":
            st["set"].update({"springForce": 0.6, "damping": 0.3, "minDamping": 0.3})
    for g in spec["groups"]:
        stiff, grav, drag = VRM[g["setting"]]
        g.setdefault("node", {})
        g["node"].pop("angleLimitRadius", None) if g["setting"] in ("hair_long", "hair") else None
        if variant in ("B", "C"):
            g["node"]["gravityCoef"] = round(min(1.0, grav * 1.5), 3)
        elif variant == "E":
            g["node"]["gravityCoef"] = 0.0


def swing_from_x(d):
    """Quaternion (x, y, z, w) rotating +X onto direction d (no twist about X) - DD2 chain angleLimitDirection."""
    import math
    n = math.sqrt(sum(c * c for c in d))
    d = [c / n for c in d]
    ax = [0.0, -d[2], d[1]]  # X cross d
    s = math.sqrt(ax[1] ** 2 + ax[2] ** 2)
    if s < 1e-9:
        return [0.0, 0.0, 0.0, 1.0] if d[0] > 0 else [0.0, 0.0, 1.0, 0.0]
    ang = math.atan2(s, d[0])
    k = math.sin(ang / 2) / s
    return [0.0, ax[1] * k, ax[2] * k, math.cos(ang / 2)]


def rest_dirs(meshinfo):
    """Node rest direction in the parent frame = local rotation * X (RE row-major local matrix: row 0 = X axis)."""
    out = {}
    for b in meshinfo["bones"]:
        l = b["local"]
        out[b["name"]] = [l[0], l[1], l[2]]
    return out


def tilt_outward(meshinfo, groups, setting, angle):
    """Turn the angle limit direction of every node of the setting's groups by `angle` (rad) away from the vertical axis
    through the centre of their chain roots (rest pose): an asymmetric limit, less room inward than outward."""
    import math
    bones = {b["name"]: b for b in meshinfo["bones"]}
    gs = [g for g in groups if g["setting"] == setting]
    roots = [bones[g["joints"][0]]["global"][12:15] for g in gs]
    cx, cz = sum(r[0] for r in roots) / len(roots), sum(r[2] for r in roots) / len(roots)
    for g in gs:
        r = bones[g["joints"][0]]["global"]
        u = [r[12] - cx, 0.0, r[14] - cz]
        aldir = []
        for j in g["joints"]:
            pm = bones[bones[j]["parent"]]["global"]  # rows 0..2 = parent axes in model space
            up = [sum(pm[4 * i + k] * u[k] for k in range(3)) for i in range(3)]
            d = bones[j]["local"][0:3]
            w = [up[i] - sum(up[k] * d[k] for k in range(3)) * d[i] for i in range(3)]
            n = math.sqrt(sum(c * c for c in w))
            aldir.append(swing_from_x([d[i] * math.cos(angle) + w[i] / n * math.sin(angle) for i in range(3)]))
        g["aldir"] = aldir


def parse_args():
    ap = argparse.ArgumentParser(description="Generate the DD2Tool chainbuild spec for the K_* joints of a built body.")
    ap.add_argument("build_report", help="build_report.json of build_karin_body.py (its <name>.meshinfo.json beside it)")
    ap.add_argument("out_spec", help="chainbuild spec to write")
    ap.add_argument("out_chain", help="chain file the spec tells chainbuild to write (.chain.55)")
    ap.add_argument("variant", nargs="?", help="parameter set: A..F (PicodraTech experiments, F = final) or O (Original)")
    ap.add_argument("child", nargs="?", help='"child": Karin groups only, on a cleared hair chain')
    ap.add_argument("--profile", default="picodra", choices=sorted(PROFILES))
    ap.add_argument("--native-dir", default=os.environ.get("DD2_NATIVE_DIR"),
                    help="DD2Tool extract output folder with natives/stm/character (default: DD2_NATIVE_DIR)")
    ap.add_argument("--inventory", required=True, help="source model bone hierarchy (inventory.json)")
    a = ap.parse_args()
    if not a.native_dir:
        ap.error("set --native-dir or DD2_NATIVE_DIR to the folder DD2Tool extract wrote (it holds natives/stm)")
    a.native = Path(a.native_dir).resolve() / "natives/stm/character"
    if not (a.native / BODY).is_file():
        ap.error(f"native chain not found: {a.native / BODY}")
    return a


def main():
    args = parse_args()
    profile = args.profile
    prof = PROFILES[profile]

    def native(rel):
        return str(args.native / rel)

    report = json.loads(Path(args.build_report).read_text(encoding="utf-8"))
    name = report["args"].get("name") or "karin_body"
    meshinfo = json.loads((Path(args.build_report).parent / f"{name}.meshinfo.json").read_text(encoding="utf-8"))
    dirs = rest_dirs(meshinfo)
    extra = report["extra_bones"]
    inv = json.loads(Path(args.inventory).read_text(encoding="utf-8"))
    bones = {b["name"]: b for b in inv["armatures"][0]["bones"]}
    children = {}
    for n, b in bones.items():
        children.setdefault(b["parent"], []).append(n)
    groups = []
    for root, setting, tmpl, radius, node in prof["roots"]:
        assert root in extra, ("chain root is not a bone of the mesh", root)
        path = [root]
        cur = root
        while True:
            kids = [k for k in children.get(cur, []) if k in extra]
            if not kids:
                break
            if len(kids) > 1:
                tip = TIPS.get(root)
                nxt = next((k for k in kids if tip and (k == tip or tip.startswith(k.split(".")[0]))), None)
                if nxt is None:
                    nxt = sorted(kids, key=lambda k: (k.startswith("Pocket") or k.startswith("Back_Ribbon_Root"), k))[0]
                cur = nxt
            else:
                cur = kids[0]
            path.append(cur)
        if len(path) < 2:
            assert profile == "picodra", ("chain without a child joint", root)
            continue
        joints = [extra[p] for p in path]
        g = {"joints": joints, "setting": setting, "template": dict(tmpl, file=native(tmpl["file"])), "radius": radius,
             "aldir": [swing_from_x(dirs[j]) for j in joints]}
        if node:
            g["node"] = node
        if setting in prof.get("group", {}):
            g["group"] = prof["group"][setting]
        groups.append(g)
    for setting, angle in prof.get("tilt", {}).items():
        tilt_outward(meshinfo, groups, setting, angle)
    import copy
    variant = args.variant
    child_only = args.child == "child"
    used = {g["setting"] for g in groups}
    settings = {k: v for k, v in copy.deepcopy(SETTINGS).items() if k in used}
    for st in settings.values():
        st["file"] = native(st["file"])
    spec = {"base": native(BODY), "output": args.out_chain, "settings": settings, "groups": groups}
    if variant:
        apply_variant(spec, variant)
    if child_only:  # chain for the Karin child object: Karin groups only (the body's own chain stays on the player)
        spec["base"] = native(HAIR011)
        spec["clearBase"] = True
    Path(args.out_spec).write_text(json.dumps(spec, indent=1), encoding="utf-8")
    for g in groups:
        print(f"{g['setting']:10s} {len(g['joints']):2d}  {g['joints'][0]} .. {g['joints'][-1]}")
    print("groups:", len(groups))


if __name__ == "__main__":
    main()
