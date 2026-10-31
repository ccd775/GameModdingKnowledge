"""Build Karin's physics add-on skeleton for AC Syndicate (stage 2; fork of the AC Unity generator).

python acs_phys_skel.py <template.Skeleton.xml> <karin_lod0_acs.glb> <out.Skeleton.xml> --id <object id>
                        [--ptr-base <id>]   (inlined bone / modifier IDs; default --id + 0x100)
                        [--report <json>]
                        [--no-collide]   (no skirt CommonData / LiteRagdoll: the skeleton is the only object)
                        [--capsule-scale <f>]   (thigh capsule radii x f; diagnostic builds)

- Syndicate: template = Jacob's hair add-on `ACVI_CHR_P_JacobFrye_Hair` (head table column 14; build_mod --phys points
  that cell at Karin_Phys_<twin> because the hair meshes are dropped). SkeletonType (CUSTOM) and the non-bone fields are
  kept, the bone list is rebuilt; --id = build_mod CHARS[twin]["base"] + PHYS. Syndicate bones carry two fields Unity's
  do not: MirroringTag (empty) and EnablePoseDrivenWrinkles (False), as in every vanilla Syndicate bone.
Unity notes (the rules below are kept; Syndicate vanilla skeletons follow them too):
- SkeletonKey / SkeletonHierarchyKey identify the bone hierarchy (vanilla skeletons share a key only when their bone
  IDs + parents are identical, e.g. the two 30-bone belts or the five head rigs; the formula is unknown): a key of its
  own (CRC32 of the bone ID / father index list), never the hair's - the hair skeleton object is still loaded.
- ChildBoneCount = number of DESCENDANTS (subtree size - 1, bones in depth-first order), as in every vanilla skeleton.
  v3 (2026-10-24) wrote the direct-child count and ACU.exe crashed at the logo in the add-on merge (ACU+0x95240: the
  ancestor stack underflows while the target subtree is skipped by these counts).
- Bones: `Reference` (root, identity) + every ancestor of a KP bone's parent (base-skeleton bones, transforms taken from
  the GLB) + the KP_* bones of fit_karin.py --phys. Unity add-on bones store GlobalPosition/Rotation relative to the
  add-on root and LocalPosition/Rotation relative to the father (checked 2026-10-24: Spine2^-1 * Head from the toolkit's
  GLB export equals the vanilla hair add-on's Head GlobalPosition/Rotation). Rooting at Reference makes Global =
  Reference^-1 * W, and the base skeleton has Reference = identity, so the skeleton frame is the base one.
- Bone ID = CRC32(name) (as the toolkit writes mesh bones).
- Simulated bones get a BallJointBoneModifier (vanilla hair / belt fields: cone ConstraintAngle in degrees, mass,
  mechanical / air friction, global gravity, rest yaw/pitch offsets = rest_offsets; or LocalOwnGravity along the
  link without offsets, see DEFAULT_PARAMS "local"). The BallJoint's own LiteRagdoll
  and OrientationBone stay Null like all 158 BallJoints of the vanilla CN_P_Arno skeletons (v3 pointed LiteRagdoll at
  LiteRagdoll_Player, an object embedded in CN_P_Arno only); the skirt collides through CommonData like the one vanilla
  joint that collides (ACU_Belt_A_Arnaud): <out>.BallJointCommonData.xml + <out>.LiteRagdoll.xml are written next to
  the skeleton (references compile to object IDs only - the Path text is not in the binary). Chains run along local +X.
"""
import json
import math
import re
import struct
import sys
import zlib

import numpy as np

PTR_OFFSET = 0x100  # inlined bone / modifier object IDs start at --id + PTR_OFFSET (Karin range, see build_mod CHARS)

# Per-chain BallJoint parameters, regex on the KP name (first match wins). angle = cone half-angle (deg),
# coll = CollisionRadius (m), mech / air = frictions, step = simulate every step-th link (others ride rigidly),
# collide = BallJointCommonData with the thigh capsules (below).
# The cone has no spring: gravity pulls a link to the cone edge. v4 (cones on the rest pose, 20-25 deg tails, 12 deg
# skirt) hung the tails / twin tails straight down and laid the skirt into the thighs; v5 (3-4 deg) kept the shapes but
# moved too little (user, 2026-10-24). v6: every cone centre is shifted by its own angle against the sag (rest_offsets),
# so gravity holds the rest pose (= source shape) on the cone edge and the link swings up / outward by up to 2 x angle.
# Syndicate v2 (2026-10-27): the v6 ears and twin tails felt stiff and hit the cone limit at the slightest move (user):
# their rest pose sits on the cone edge, and the frictions are 5-10x the vanilla hair's (ACVI_CHR_P_EvieFrye_Hair: 30 deg,
# 0.2 / 0.3). local = g: GravityMode LocalOwnGravity with OwnGravity = g along the rest link (bone frame), no rest
# offsets - a pull back toward the rest shape, so the cone is centred on the rest pose and the link sways around it.
# Vanilla Syndicate does this for pieces that stick out (EvieFrye_Outfit11 ornaments: LocalOwnGravity (15, 0, 0) /
# (20, 0, 0), 20 deg, frictions 0.5-0.7 / 0.7-1; the hood controls: LocalGravity + CommonData gravity (50, 0, 0)); the
# ornaments' X is far from their father's X (they point along Spine2 Z), so "local" is the bone's own frame.
# Syndicate v3 (2026-10-30): that frame guess was wrong in game - with v2 both ears rested tilted toward the head's right
# (a pull along one direction for both, not along each ear) and the twin tails jittered fast all the time (user). Back to
# the v1 model (GlobalGravity, rest pose held on the cone edge, stable), softer than v1: twin tails 18 deg (v1 12) with
# vanilla-hair-like frictions 0.8 / 0.6 (v1 1.5 / 1); the ears get the rest-edge offset too (upright: the cone centre
# leans toward vertical, so gravity tipping the ear outward holds it at its source tilt of ~14 deg; v1 centred the cone
# on the rest pose, so the ears sank 5 deg outward and could only swing back to it). "local" is unused since v3.
# v4 (2026-10-30): v3's twin tails (18 deg on links 0 / 2 / 4) flew up as one piece after a few steps, no chain feel
# (user): the root link swung as far as the tip. A list value is per link along the chain (chain index 0 = root, the
# last value repeats): small stiff root cone, looser toward the tip. With every link simulated (5 / 7 / 9 / 12 / 14 deg)
# the twin tails jittered fast again, as in v2 (user), so consecutive simulated links are what jitters: v5 keeps the
# grading on links 0 / 2 / 4 only (v1 and v3 simulated those and never jittered).
DEFAULT_PARAMS = [
    (r"KP_Hair_tail", {"angle": [6, 6, 10, 10, 14], "coll": 0.04, "mech": [1.3, 1.3, 1.0, 1.0, 0.8],
                       "air": [1.1, 1.1, 0.9, 0.9, 0.7], "step": 2}),
    (r"KP_Hair_side", {"angle": 5, "coll": 0.03, "mech": 2, "air": 1.5}),              # 2; hangs inward: swings toward the face
    (r"KP_Hair_front", {"angle": 5, "coll": 0.02, "mech": 3, "air": 2}),
    (r"KP_Cheek", {"angle": 6, "coll": 0.02, "mech": 2, "air": 1.5}),
    (r"KP_Ribbon", {"angle": 15, "coll": 0.02, "mech": 1.5, "air": 1}),
    (r"KP_Shoes_tag", {"angle": 12, "coll": 0.01, "mech": 2, "air": 1}),
    (r"KP_Skirt", {"angle": 14, "coll": 0.02, "mech": 2, "air": 1, "collide": True}),  # 2; v6 10: too little to clear a raised thigh
    # v5: softer, wider (user on 6 deg, 1.0 / 0.8): swings up to 18 deg; the cone now reaches 4 deg past vertical, but the
    # rest pose is still the only stable point of its edge (the farthest from vertical)
    (r"KP_Ear", {"angle": 9, "coll": 0.02, "mech": 0.6, "air": 0.5, "upright": True}),
    (r"KP_Tail", {"angle": 12, "coll": 0.05, "mech": 1.5, "air": 1, "step": 2}),       # 3
    (r".*", {"angle": 6, "coll": 0.02, "mech": 2, "air": 1.5}),
]
# Skirt collision, as the vanilla ACU_Belt_A_Arnaud flap: BallJoint CommonData -> BallJointCommonData -> LiteRagdoll
# with capsules on the thighs (written next to the skeleton XML, object IDs = skeleton ID + 1 / + 2; build_mod embeds
# them with the skeleton). Capsule frame = thigh bone (X to the knee, as the vanilla player / belt capsules). Karin's
# thighs (karin_lod0_acu.glb, UpLeg frame, length 0.437): skin radius ~0.10 m at x 0.05-0.25, 0.08 at 0.25-0.35, 0.066
# near the knee, axis offset ~-0.008 Y; the skirt hem points sit at hip-joint height (x ~0.02) 0.157-0.20 m from the
# thigh axis, the mid points at x -0.1. v6 (one capsule, centre 0.22, Height 0.2, radius 0.10 = bare skin) still let the
# thighs through the skirt when running: v7 = two capsules per thigh (x, Height, radius) with ~3 cm for the cloth between
# the bone points, covering 0.02-0.45 whether Height is the full or the half cylinder length, the rest pose still clear
# (0.13 + CollisionRadius 0.02 < 0.157). --capsule-scale <f> scales the radii (diagnostic: f 2 balloons the skirt at
# rest if the collision works at all). Vanilla player thigh: centre 0.25, Height 0.165, radius 0.085.
THIGH_CAPSULES = {"bones": ("LeftUpLeg", "RightUpLeg"), "y": -0.008, "shapes": [(0.12, 0.1, 0.13), (0.32, 0.1, 0.11)]}


def params(name):
    for rx, p in DEFAULT_PARAMS:
        if re.match(rx, name):
            d = dict({"step": 1, "mass": 1.0}, **p)
            if "--no-collide" in sys.argv:
                d["collide"] = False
            return d


def load_glb(path):
    d = open(path, "rb").read()
    n = struct.unpack_from("<I", d, 12)[0]
    return json.loads(d[20:20 + n])


def node_m(n):
    if "matrix" in n:
        return np.array(n["matrix"], float).reshape(4, 4).T
    x, y, z, w = n.get("rotation", [0, 0, 0, 1])
    m = np.eye(4)
    m[:3, :3] = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                          [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                          [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]]) * np.array(n.get("scale", [1, 1, 1]))
    m[:3, 3] = n.get("translation", [0, 0, 0])
    return m


def m_to_quat(m):
    t = m[0, 0] + m[1, 1] + m[2, 2]
    if t > 0:
        s = math.sqrt(t + 1.0) * 2
        q = [(m[2, 1] - m[1, 2]) / s, (m[0, 2] - m[2, 0]) / s, (m[1, 0] - m[0, 1]) / s, 0.25 * s]
    else:
        i = int(np.argmax([m[0, 0], m[1, 1], m[2, 2]]))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = math.sqrt(1.0 + m[i, i] - m[j, j] - m[k, k]) * 2
        q = [0.0] * 4
        q[i] = 0.25 * s
        q[j] = (m[j, i] + m[i, j]) / s
        q[k] = (m[k, i] + m[i, k]) / s
        q[3] = (m[k, j] - m[j, k]) / s
    q = np.array(q)
    return q / np.linalg.norm(q) * (1 if q[3] >= 0 else -1)


def ortho(m):
    """rotation part re-orthonormalized (the GLB carries float noise)"""
    u, _, vt = np.linalg.svd(m[:3, :3])
    r = u @ vt
    out = np.eye(4)
    out[:3, :3] = r
    out[:3, 3] = m[:3, 3]
    return out


def fmt(v):
    return ", ".join(repr(float(x)) for x in v)


def rest_offsets(Gb, tip, attach, angle, upright=False):
    """(LocalYawOft, LocalPitchOft) in degrees that move the cone centre by `angle` against the sag, so gravity holds
    the rest pose on the cone edge. Convention from the vanilla CN_P_Arno BallJoints (93 of 116 offset joints then
    swing away from the body, every other axis / sign / father-frame variant is at chance level): bone frame, pitch
    turns about local Z (+ moves X toward +Y), yaw about local Y (+ moves X toward -Z). Links hanging within ~17 deg of
    vertical get the vanilla flap offset (outward from the body bone they hang from); links pointing up none, unless
    upright: the centre then moves toward vertical (gravity tips an upright link away from vertical, onto the rest pose;
    with angle > half the link's tilt vertical lies inside the cone: the rest pose stays the only stable point of the
    edge, but the link returns slowly when it passes near vertical)."""
    up = np.array([0.0, 0.0, 1.0])
    t = tip - Gb[:3, 3]
    t /= np.linalg.norm(t)
    if t @ up > 0.7 and not upright:
        return 0.0, 0.0
    m = up - (up @ t) * t
    if np.linalg.norm(m) < 0.3 and not upright:
        o = tip - attach
        o[2] = 0
        m = o - (o @ t) * t
    if np.linalg.norm(m) < 1e-6:
        return 0.0, 0.0
    R = Gb[:3, :3]
    tl, ml = R.T @ t, R.T @ (m / np.linalg.norm(m))
    if tl[0] < 0.7:  # branch roots whose children do not lie along local X (hand ribbons): yaw / pitch would not
        return 0.0, 0.0  # move the tip predictably
    A = np.c_[np.cross([0.0, 0.0, 1.0], tl), np.cross([0.0, 1.0, 0.0], tl)]  # d tip / d pitch, d tip / d yaw
    th = np.linalg.lstsq(A, ml, rcond=None)[0]
    th *= angle / np.linalg.norm(A @ th)
    return round(float(th[1]), 3), round(float(th[0]), 3)


def capsule_block(cid, bone, cx, h, r):
    c = (cx, THIGH_CAPSULES["y"], 0)
    flags = "".join(f'                <Bool Name="Group{i}">False</Bool>\n' for i in range(1, 17))
    return (f'        <BaseObject ID="{cid}" Type="LiteRagdollShape">\n'
            f'            <Enum Name="ShapeType" Type="LiteRagdollShape::ShapeType" Value="Capsule">0</Enum>\n'
            f'            <Unsigned32 Name="BoneID">{zlib.crc32(bone.encode())}</Unsigned32>\n'
            f'            <Vector4 Name="HalfExtent">( 0.5, 0.5, 0.5, 0 )</Vector4>\n'
            f'            <Float Name="Height">{h}</Float>\n'
            f'            <Float Name="Radius">{r}</Float>\n'
            f'            <Matrix44 Name="LocalMatrix">(1, 0, 0, 0) (0, 1, 0, 0) (0, 0, 1, 0) ({c[0]}, {c[1]}, {c[2]}, 1)</Matrix44>\n'
            f'            <BaseObject ID="0" Name="GroupFlags" Type="LiteRagdollCapsuleGroupFlags">\n' + flags +
            f'            </BaseObject>\n'
            f'        </BaseObject>\n')


def collision_xml(obj_id, last_len, scale=1.0):
    """(BallJointCommonData XML, LiteRagdoll XML) for the skirt: IDs obj_id + 1 / + 2, capsules obj_id + 0x10.."""
    head = '<?xml version="1.0" encoding="utf-8"?>\n<?info tool="AnvilToolkit" toolVersion="" type="1"?>\n'
    cd = (head + f'<Object ID="{obj_id + 1}" Type="BallJointCommonData" IsManaged="true">\n'
          f'    <Reference Name="LiteRagDoll" Type="LiteRagdoll" PointerType="External" ReferenceType="0" '
          f'Path="Karin\\Karin_Phys.LiteRagdoll">{obj_id + 2}</Reference>\n'
          f'    <Vector4 Name="Gravity">( 0, 0, -9.8100004196167, 0 )</Vector4>\n'
          f'    <Float Name="LastBoneLength">{round(last_len, 4)}</Float>\n'
          f'</Object>')
    lr = (head + f'<Object ID="{obj_id + 2}" Type="LiteRagdoll" IsManaged="true">\n'
          f'    <DynamicSmallArray Name="Capsules" Type="BaseObject">\n'
          + "".join(capsule_block(obj_id + 0x10 + i, b, cx, h, round(r * scale, 4)) for i, (b, (cx, h, r)) in enumerate(
              (b, s) for b in THIGH_CAPSULES["bones"] for s in THIGH_CAPSULES["shapes"])) +
          f'    </DynamicSmallArray>\n'
          f'    <DynamicSmallArray Name="ExternalCapsules" Type="BaseObject" />\n'
          f'</Object>')
    return cd, lr


def bone_block(ptr, name, father_ptr, G, L, index, ndesc, prio, bj):
    gq, lq = m_to_quat(G[:3, :3]), m_to_quat(L[:3, :3])
    father = (f'            <ObjectPtr Name="FatherBone" PointerType="Link">\n'
              f'                <Link Name="FatherBone" Path="{father_ptr}">{father_ptr}</Link>\n'
              f'            </ObjectPtr>\n') if father_ptr else '            <ObjectPtr Name="FatherBone" PointerType="Null" />\n'
    mods = '            <DynamicSmallArray Name="Modifiers" Type="ObjectPtr" />\n'
    if bj:
        # collide: CommonData with the LiteRagdoll (the path is not compiled). Unity's one colliding joint used
        # GlobalOwnGravity; no Syndicate BallJoint does (241 vanilla joints: CommonData goes with GlobalGravity 39x,
        # LocalOwnGravity 50x, LocalGravity 13x), so Syndicate keeps GlobalGravity
        gm = '"LocalOwnGravity">3' if bj.get("own") else '"GlobalGravity">0'
        own = fmt(bj["own"]) if bj.get("own") else "0, 0, -9.8100004196167"
        cd = (f'<Reference Name="CommonData" Type="BallJointCommonData" PointerType="External" ReferenceType="0" '
              f'Path="Karin\\Karin_Phys.BallJointCommonData">{bj["cd"]}</Reference>' if bj.get("cd") else
              '<Reference Name="CommonData" Type="BallJointCommonData" PointerType="Null" />')
        mods = (f'            <DynamicSmallArray Name="Modifiers" Type="ObjectPtr">\n'
                f'                <ObjectPtr ID="{bj["ptr"]}" Type="BallJointBoneModifier" PointerType="Inlined">\n'
                f'                    <ObjectPtr Name="Owner" PointerType="Link">\n'
                f'                        <Link Name="Owner" Path="{ptr}">{ptr}</Link>\n'
                f'                    </ObjectPtr>\n'
                f'                    <Float Name="BlendWeight">1</Float>\n'
                f'                    <Bool Name="UseModifiedBoneMatrix">False</Bool>\n'
                f'                    <Enum Name="ConstraintAngleType" Type="BallJointBoneModifier::ConstraintAngleType" Value="Cone">0</Enum>\n'
                f'                    <Float Name="Mass">{bj["mass"]}</Float>\n'
                f'                    <Float Name="CollisionRadius">{bj["coll"]}</Float>\n'
                f'                    <Float Name="ConstraintAngle">{bj["angle"]}</Float>\n'
                f'                    <Float Name="ConstraintAngleZ">0</Float>\n'
                f'                    <Float Name="ConstraintScaleY">1</Float>\n'
                f'                    <Float Name="ConstraintScaleZ">1</Float>\n'
                f'                    <Float Name="MechanicalFriction">{bj["mech"]}</Float>\n'
                f'                    <Float Name="AirFriction">{bj["air"]}</Float>\n'
                f'                    <Float Name="WindScale">0</Float>\n'
                f'                    <Float Name="WindRandomFactor">0.3</Float>\n'
                f'                    <Enum Name="GravityMode" Type="BallJointBoneModifier::GravityMode" Value={gm}</Enum>\n'
                f'                    <Vector4 Name="OwnGravity">( {own}, 0 )</Vector4>\n'
                f'                    <Float Name="LocalYawOft">{bj["yaw"]}</Float>\n'
                f'                    <Float Name="LocalPitchOft">{bj["pitch"]}</Float>\n'
                f'                    <Float Name="LocalRollOft">0</Float>\n'
                f'                    {cd}\n'
                f'                    <ObjectPtr Name="OrientationBone" PointerType="Null" />\n'
                f'                    <Reference Name="LiteRagdoll" Type="LiteRagdoll" PointerType="Null" />\n'
                f'                </ObjectPtr>\n'
                f'            </DynamicSmallArray>\n')
    return (f'        <ObjectPtr ID="{ptr}" Type="Bone" PointerType="Inlined">\n'
            f'            <Hash32 Name="BoneID" HashValue="{name}">{zlib.crc32(name.encode())}</Hash32>\n'
            + father +
            f'            <ObjectPtr Name="MirrorBone" PointerType="Link">\n'
            f'                <Link Name="MirrorBone" Path="{ptr}">{ptr}</Link>\n'
            f'            </ObjectPtr>\n'
            f'            <Vector4 Name="GlobalPosition">( {fmt(G[:3, 3])}, 0 )</Vector4>\n'
            f'            <Quaternion Name="GlobalRotation">( {fmt(gq)} )</Quaternion>\n'
            f'            <Vector4 Name="LocalPosition">( {fmt(L[:3, 3])}, 0 )</Vector4>\n'
            f'            <Quaternion Name="LocalRotation">( {fmt(lq)} )</Quaternion>\n'
            f'            <Unsigned8 Name="SolvingPriority">{prio}</Unsigned8>\n'
            f'            <Enum Name="MirroringType" Type="BoneMirroringType" Value="BONEMIRRORING_BIPED_TO_BIPED">5</Enum>\n'
            f'            <String Name="MirroringTag"></String>\n'
            + mods +
            f'            <Bool Name="EnablePoseDrivenWrinkles">False</Bool>\n'
            f'            <DynamicSmallArray Name="DependenciesBoneIDs" Type="Unsigned32" />\n'
            f'            <Enum Name="WrinkleCategory" Type="Bone::WrinkleCategory" Value="None">7</Enum>\n'
            f'            <Float Name="WrinkleFactor">1</Float>\n'
            f'            <Unsigned16 Name="Index">{index}</Unsigned16>\n'
            f'            <Unsigned16 Name="ChildBoneCount">{ndesc}</Unsigned16>\n'
            f'        </ObjectPtr>\n')


def main():
    if sys.argv[1:2] in (["-h"], ["--help"]):
        print(__doc__)
        sys.exit(0)
    tpl, glb, out = sys.argv[1:4]
    report_path = sys.argv[sys.argv.index("--report") + 1] if "--report" in sys.argv else None
    doc = load_glb(glb)
    nodes = doc["nodes"]
    joints = doc["skins"][0]["joints"]
    parent = {c: i for i, n in enumerate(nodes) for c in n.get("children", [])}
    W = {}

    def world(i):
        if i not in W:
            W[i] = (world(parent[i]) @ node_m(nodes[i])) if i in parent else node_m(nodes[i])
        return W[i]

    name = {j: nodes[j]["name"] for j in joints}
    by_name = {v: k for k, v in name.items()}
    if "Reference" not in by_name:
        raise SystemExit("GLB skin has no Reference joint")
    ref_inv = np.linalg.inv(ortho(world(by_name["Reference"])))
    kp = [j for j in joints if name[j].startswith("KP_")]
    keep = set(kp)
    for j in kp:  # ancestors up to Reference
        p = parent.get(j)
        while p is not None and p in name:
            keep.add(p)
            p = parent.get(p)
    order = []  # parent-first, Reference first

    def visit(j):
        order.append(j)
        for c in nodes[j].get("children", []):
            if c in keep:
                visit(c)
    visit(by_name["Reference"])
    desc = {}  # ChildBoneCount = descendants (vanilla), not direct children

    def count(j):
        desc[j] = sum(count(c) + 1 for c in nodes[j].get("children", []) if c in keep)
        return desc[j]
    count(by_name["Reference"])
    x = open(tpl, encoding="utf-8-sig").read()
    obj_id = int(sys.argv[sys.argv.index("--id") + 1], 0) if "--id" in sys.argv else int(re.search(r'<Object ID="(\d+)"', x).group(1))
    ptr_base = int(sys.argv[sys.argv.index("--ptr-base") + 1], 0) if "--ptr-base" in sys.argv else obj_id + PTR_OFFSET
    ptr = {j: ptr_base + 2 * i for i, j in enumerate(order)}
    G = {j: ref_inv @ ortho(world(j)) for j in order}
    depth = {}
    blocks, sim, last_len = [], [], []
    for idx, j in enumerate(order):
        fa = parent.get(j) if j != by_name["Reference"] else None
        L = np.linalg.inv(G[fa]) @ G[j] if fa is not None else G[j]
        depth[j] = depth[fa] + 1 if fa is not None else 0
        nchild = sum(1 for c in nodes[j].get("children", []) if c in keep)
        bj = None
        n = name[j]
        chain_i = 0  # position in its KP chain (0 = attached to a body bone)
        q = fa
        while q is not None and name.get(q, "").startswith("KP_"):
            chain_i += 1
            q = parent.get(q)
        if n.startswith("KP_") and not n.endswith("_end") and nchild > 0:
            p = {k: v[min(chain_i, len(v) - 1)] if isinstance(v, list) else v for k, v in params(n).items()}
            if chain_i % p["step"] == 0:
                kids = [c for c in nodes[j].get("children", []) if c in keep]
                tip = np.mean([G[c][:3, 3] for c in kids], axis=0)
                own = None
                if p.get("local"):  # pull along the rest link direction (bone frame), cone centred on the rest pose
                    t = G[j][:3, :3].T @ (tip - G[j][:3, 3])
                    own = [round(float(v), 4) for v in p["local"] * t / np.linalg.norm(t)]
                    yaw = pitch = 0.0
                else:
                    yaw, pitch = rest_offsets(G[j], tip, G[q][:3, 3], p["angle"], p.get("upright", False))  # q = the body bone the chain hangs from
                bj = dict(p, ptr=ptr[j] + 1, yaw=yaw, pitch=pitch, own=own, cd=obj_id + 1 if p.get("collide") else None)
                if p.get("collide") and all(not nodes[c].get("children") for c in kids):
                    last_len.append(float(np.linalg.norm(tip - G[j][:3, 3])))
                sim.append({"bone": n, "chain_index": chain_i, "yaw": yaw, "pitch": pitch, "own_gravity": own,
                            **{k: p[k] for k in ("angle", "coll", "mech", "air", "mass")}})
        # SolvingPriority as in the vanilla hair add-on: 1, 2, ... along a physics chain, 0 for body bones
        blocks.append(bone_block(ptr[j], n, ptr[fa] if fa is not None else None, G[j], L, idx, desc[j],
                                 min(chain_i + 1, 255) if n.startswith("KP_") else 0, bj))
    x = re.sub(r'<Object ID="\d+"', lambda _: f'<Object ID="{obj_id}"', x, count=1)  # --id: build_mod.PHYS_ID
    a = x.index('    <DynamicSmallArray Name="Bones" Type="ObjectPtr">')
    b = x.index('    <ObjectPtr Name="RootBone" PointerType="Link">')
    root_ptr = ptr[by_name["Reference"]]
    tail = re.sub(r'<Link Name="RootBone" Path="\d+">\d+</Link>', f'<Link Name="RootBone" Path="{root_ptr}">{root_ptr}</Link>', x[b:])
    pos = {j: i for i, j in enumerate(order)}
    key = zlib.crc32(b"".join(struct.pack("<Ii", zlib.crc32(name[j].encode()), pos.get(parent.get(j), -1) if i else -1)
                              for i, j in enumerate(order)))
    old = re.search(r'<Unsigned32 Name="SkeletonKey">(\d+)<', tail).group(1)
    assert str(key) != old, "hierarchy key equals the template's"
    tail = re.sub(r'(<Unsigned32 Name="Skeleton(?:Hierarchy)?Key">)\d+(<)', lambda m: f"{m.group(1)}{key}{m.group(2)}", tail)
    y = x[:a] + '    <DynamicSmallArray Name="Bones" Type="ObjectPtr">\n' + "".join(blocks) + "    </DynamicSmallArray>\n" + tail
    open(out, "w", encoding="utf-8").write(y)
    if last_len:  # skirt collision objects next to the skeleton (build_mod --phys embeds them too)
        scale = float(sys.argv[sys.argv.index("--capsule-scale") + 1]) if "--capsule-scale" in sys.argv else 1.0
        for xml, kind in zip(collision_xml(obj_id, float(np.mean(last_len)), scale), ("BallJointCommonData", "LiteRagdoll")):
            open(out.replace(".Skeleton.xml", f".{kind}.xml"), "w", encoding="utf-8").write(xml)
    rep = {"bones": len(order), "kp": len(kp), "simulated": len(sim), "skeleton_key": key, "joints": sim}
    if report_path:
        json.dump(rep, open(report_path, "w"), indent=1)
    print(f"PHYS_SKEL bones {len(order)} (KP {len(kp)}), ball joints {len(sim)}, key {key} -> {out}")


if __name__ == "__main__":
    main()
