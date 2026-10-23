"""Build Karin's physics skeleton for AC Odyssey: Kassandra's hair skeleton (ACD_CHF_PLA_Hair_NEW, Hair table col 3,
Kassandra-only) rebuilt as Reference-rooted parent chains + the KP_* bones of fit_karin.py --phys + one Reflex3 Physics
record (type 21) per simulated KP bone.

python aco_phys_skel.py <out_skel.xml> --binds <mesh-bones dump of LOD0> --fit <fit report json> [--params <json>]
                        [--report <json>] [--template <Hair_NEW xml>] [--base <Unisex_BaseSkeleton xml>]

Portable kit: the vanilla XML exports are read from the project layout under ACO_WORK unless --template and --base
are given.

- Template = vanilla Hair_NEW XML (Object ID, SkeletonKey/HierarchyKey and the non-bone fields are kept; Shadows ran
  replaced skeletons with the old key too). Base-bone blocks are copied from ACD_Unisex_BaseSkeleton (same frame as
  the vanilla Female_Boobs add-on: Reference-rooted, Hips at the origin, root default local position (0, 0, 0.964)).
- KP bone global = the Karin LOD0 mesh bind (AcoHarness mesh-bones: row-vector 3x3 + translation, mesh frame
  X = left, -Y = forward, Z = up, ground origin) mapped to the skeleton frame (X = forward, Y = left, Z up, Hips
  origin); local = inv(father global) * global, so rest pose == bind.
- Odyssey Reflex3 blob (decoded 2026-10-19, docs/STATUS.md): f32 3.1 + records [u8 type][body]. Physics = type 21,
  377 bytes: boneID, parentID, M0 = parent^-1*bone (row-major [R|t]), M1 = M0, M2 = the parent's mesh-frame bind,
  M3 = M4 = M0, then 00 00 00 01 | A min,max | 01 | B min,max | com | 0 | 0 | gf | gravity | 01 00 00 | u32 depth.
  Vanilla chain bones run along local +X, +Y = forward (sagittal), +Z = right; from the vanilla ponytail limits
  (B = [-1.05, 0] on a tail hanging behind the head) B = swing about local Z (+ = tip toward +Y, forward) and
  A = swing about local Y. gf (vanilla 0.1-1.0, ponytail 0.25 at the root -> 1.0 at the tip) is assumed to be a
  gravity factor; its meaning is not confirmed.
"""
import argparse, json, math, os, re, struct, sys, zlib

import numpy as np

WORK = os.environ.get("ACO_WORK", "")  # portable kit: project work folder with the vanilla XML exports (or --template/--base)
TEMPLATE = os.path.join(WORK, "x2", "p1", "xml", "19511_-_ACD_CHF_PLA_Hair_NEW", "0_-_ACD_CHF_PLA_Hair_NEW.Skeleton.xml")
BASE = os.path.join(WORK, "x2", "p1", "xml", "19895_-_ACD_CHR_Playable_BaseEntity_Female", "10_-_ACD_Unisex_BaseSkeleton.Skeleton.xml")
HIPS_H = 0.9639999866485596  # RootBoneDefaultLocalPosition z of Reference-rooted vanilla skeletons
PTR0 = 4160749568           # inlined object IDs: 0xF8000000 + index

# Per-chain parameters: regex matched at the start of the KP name (first match wins). Fields:
#   off      no constraint (rigid on its parent)      root   also simulate the chain root (parent = body bone)
#   step     simulate every step-th link (the ones between ride rigidly)
#   a, b     [min, max] swing (rad); a = about local Y (sideways), b = about local Z (+ = tip forward)
#   com      CenterOfMass (m); com_rel = fraction of the length the joint carries (own + rigid followers)
#   gf       gravity factor (number, or [root, tip] ramp over the simulated joints)   gravity  m/s^2
# v4 (2026-10-19, first Odyssey build): values inside the vanilla ranges (hair/ponytail/skirt/quiver samples);
# Shadows lessons: few simulated joints on long chains, com ~0.2 m, ears/tail would sag under world gravity.
DEFAULT_PARAMS = [
    ("KP_Hair_tail", {"step": 2, "com_rel": 0.6, "a": [-0.35, 0.35], "b": [-0.6, 0.1], "gf": [0.25, 1.0]}),
    ("KP_Hair_side", {"a": [-0.2, 0.2], "b": [-0.3, 0.1], "com_rel": 0.6, "gf": 0.5}),
    ("KP_Hair_front", {"a": [-0.12, 0.12], "b": [-0.12, 0.08], "com_rel": 0.6, "gf": 0.3}),
    ("KP_Cheek", {"a": [-0.15, 0.15], "b": [-0.15, 0.1], "com_rel": 0.6, "gf": 0.3}),
    ("KP_Ribbon_hand", {"a": [-0.3, 0.3], "b": [-0.3, 0.3], "com_rel": 0.6, "gf": 0.6}),
    ("KP_Ribbon_(camisole|tops)", {"root": True, "a": [-0.25, 0.25], "b": [-0.25, 0.25], "com_rel": 0.6, "gf": 0.6}),
    ("KP_Ribbon", {"a": [-0.3, 0.3], "b": [-0.3, 0.1], "com_rel": 0.6, "gf": 0.6}),
    ("KP_Shoes_tag", {"root": True, "a": [-0.3, 0.3], "b": [-0.3, 0.3], "com_rel": 0.6, "gf": 0.6}),
    # v5 (user on v4: thighs come out through the front panels when running): panels may only swing away from the
    # body (b > 0 = toward +Y = forward/outward on the front, b < 0 on the back, whose +Y points into the body)
    ("KP_Skirt_(0|1_[LR]|2_[LR])", {"a": [-0.15, 0.15], "b": [0.0, 0.3], "com_rel": 0.6, "gf": 0.5}),
    ("KP_Skirt_3_[LR]", {"a": [-0.15, 0.15], "b": [0.0, 0.25], "com_rel": 0.6, "gf": 0.5}),
    ("KP_Skirt_4_[LR]", {"a": [-0.15, 0.15], "b": [-0.15, 0.15], "com_rel": 0.6, "gf": 0.5}),
    ("KP_Skirt", {"a": [-0.15, 0.15], "b": [-0.3, 0.0], "com_rel": 0.6, "gf": 0.5}),            # 5-8: back
    # v5 (user on v4: "tail and ears show no visible physics" - they were off): small limits / low gravity factor so
    # the upright ears and the backward tail do not sag much under world gravity
    # v6 (user on v5: tail "尚可，稍微再柔软一点", ears "不够明显，可以再柔弱一些")
    ("KP_Ear", {"root": True, "a": [-0.25, 0.25], "b": [-0.25, 0.25], "com_rel": 0.6, "gf": 0.5}),
    ("KP_Tail", {"step": 2, "a": [-0.35, 0.35], "b": [-0.3, 0.3], "com_rel": 0.6, "gf": [0.3, 0.75]}),
    ("*", {"a": [-0.2, 0.2], "b": [-0.2, 0.2], "com_rel": 0.5, "gf": 0.5, "gravity": 9.8, "root": False}),
]


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def vec(s):
    return [float(v) for v in s.strip("() ").split(",")]


def quat_to_m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


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


def m4(R, t):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = t
    return M


# skeleton frame (X fwd, Y left, Z up, Hips origin) -> mesh frame (X left, -Y fwd, Z up, ground origin)
T = m4(np.array([[0.0, 1, 0], [-1, 0, 0], [0, 0, 1]]), [0, 0, HIPS_H])


def parse_bones(xml):
    out = []
    for m in re.finditer(r'(        <ObjectPtr ID="(\d+)" Type="Bone" PointerType="Inlined">\n.*?\n        </ObjectPtr>\n)', xml, re.S):
        blk = m.group(1)
        g = lambda k: re.search(rf'Name="{k}">([^<]*)<', blk).group(1)
        nm, bid = re.search(r'<Hash32 Name="BoneID" HashValue="([^"]*)">(\d+)<', blk).groups()
        fat = re.search(r'<Link Name="FatherBone" Path="(\d+)"', blk)
        out.append(dict(block=blk, ptr=int(m.group(2)), name=nm, id=int(bid), father=int(fat.group(1)) if fat else None,
                        G=m4(quat_to_m(vec(g("GlobalRotation"))), vec(g("GlobalPosition"))[:3])))
    byptr = {b["ptr"]: b for b in out}
    for b in out:
        b["fname"] = byptr[b["father"]]["name"] if b["father"] in byptr else None
    return out


def fmt(v):
    return "( " + ", ".join(repr(float(x)) if x != 0 else "0" for x in v) + " )"


def bone_block(tpl, ptr, name, bid, father_ptr, G, L, index, nchild):
    b = tpl
    b = re.sub(r'<ObjectPtr ID="\d+" Type="Bone"', f'<ObjectPtr ID="{ptr}" Type="Bone"', b, count=1)
    b = re.sub(r'<Hash32 Name="BoneID" HashValue="[^"]*">\d+<', f'<Hash32 Name="BoneID" HashValue="{name}">{bid}<', b)
    fat = ('<ObjectPtr Name="FatherBone" PointerType="Null" />' if father_ptr is None else
           f'<ObjectPtr Name="FatherBone" PointerType="Link">\n                <Link Name="FatherBone" Path="{father_ptr}">{father_ptr}</Link>\n            </ObjectPtr>')
    b = re.sub(r'<ObjectPtr Name="FatherBone" PointerType="Null" />|<ObjectPtr Name="FatherBone" PointerType="Link">.*?</ObjectPtr>', lambda m: fat, b, count=1, flags=re.S)
    b = re.sub(r'<Link Name="MirrorBone" Path="\d+">\d+</Link>', f'<Link Name="MirrorBone" Path="{ptr}">{ptr}</Link>', b)
    for tag, val in (("GlobalPosition", fmt(list(G[:3, 3]) + [0])), ("GlobalRotation", fmt(m_to_quat(G[:3, :3]))),
                     ("LocalPosition", fmt(list(L[:3, 3]) + [0])), ("LocalRotation", fmt(m_to_quat(L[:3, :3])))):
        b = re.sub(rf'(Name="{tag}">)[^<]*(<)', lambda m: m.group(1) + val + m.group(2), b, count=1)
    b = re.sub(r'(<Unsigned16 Name="Index">)\d+(<)', lambda m: f"{m.group(1)}{index}{m.group(2)}", b)
    b = re.sub(r'(<Unsigned16 Name="ChildBoneCount">)\d+(<)', lambda m: f"{m.group(1)}{nchild}{m.group(2)}", b)
    return b


def read_binds(path):
    """-> {crc32 bone id: 4x4 column-convention global bind, mesh frame}. A .glb (the *_ody.glb fed to import-glb) gives
    every skin joint, also KP chain roots without skinned vertices (inv of the inverse bind matrices; identical to the
    imported Mesh binds); otherwise an AcoHarness mesh-bones dump: id, name, tx,ty,tz, 9 floats (row-vector 3x3)."""
    out = {}
    if path.lower().endswith(".glb"):
        b = open(path, "rb").read()
        jl = struct.unpack_from("<I", b, 12)[0]
        j = json.loads(b[20:20 + jl])
        data = b[20 + jl + 8:]
        sk = j["skins"][0]
        acc = j["accessors"][sk["inverseBindMatrices"]]
        bv = j["bufferViews"][acc["bufferView"]]
        ibm = np.frombuffer(data, "<f4", acc["count"] * 16, bv.get("byteOffset", 0) + acc.get("byteOffset", 0)).reshape(-1, 4, 4)
        for i, node in enumerate(sk["joints"]):
            out[zlib.crc32(j["nodes"][node]["name"].encode())] = np.linalg.inv(ibm[i].T.astype(float))
        return out
    for line in open(path):
        p = line.rstrip("\n").split("\t")
        if len(p) < 4:
            continue
        t = [float(v) for v in p[2].split(",")]
        r = np.array([float(v) for v in p[3].split(",")]).reshape(3, 3)
        out[int(p[0])] = m4(r.T, t)
    return out


def params_for(name, table):
    p = {}
    for pat, v in reversed(table):
        if pat == "*" or re.match(pat, name, re.I):
            p.update(v)
    for pat, v in table:  # first match wins over "*"
        if pat != "*" and re.match(pat, name, re.I):
            p.update(v)
            break
    return p


def physics_record(bid, pid, M0, M2, a, b, com, gf, gravity, depth):
    mat = lambda M: struct.pack("<16f", *[float(v) for v in M.reshape(-1)])
    r = bytes([21]) + struct.pack("<II", bid, pid) + mat(M0) + mat(M0) + mat(M2) + mat(M0) + mat(M0)
    r += bytes([0, 0, 0, 1]) + struct.pack("<ff", *a) + bytes([1]) + struct.pack("<ff", *b)
    r += struct.pack("<fffff", com, 0.0, 0.0, gf, gravity) + bytes([1, 0, 0]) + struct.pack("<I", depth)
    assert len(r) == 377
    return r


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_skel_xml")
    ap.add_argument("--binds", required=True, help="Karin LOD0 *_ody.glb or an AcoHarness mesh-bones dump")
    ap.add_argument("--fit", required=True, help="fit report JSON of fit_karin.py --phys (its 'phys' table)")
    ap.add_argument("--params", help="JSON list of [regex, {fields}] rows, matched before DEFAULT_PARAMS")
    ap.add_argument("--report", help="JSON: bone order and the written physics parameters")
    ap.add_argument("--template", help="vanilla ACD_CHF_PLA_Hair_NEW Skeleton XML (default: under ACO_WORK)")
    ap.add_argument("--base", help="vanilla ACD_Unisex_BaseSkeleton Skeleton XML (default: under ACO_WORK)")
    a = ap.parse_args()
    if not WORK and not (a.template and a.base):
        raise SystemExit("set ACO_WORK (project work folder with the vanilla XML exports) or pass --template and --base")
    out_path = a.out_skel_xml
    binds = read_binds(a.binds)
    fit = json.load(open(a.fit))["phys"]
    table = DEFAULT_PARAMS
    if a.params:
        table = [tuple(x) for x in json.load(open(a.params))] + DEFAULT_PARAMS
    tpl_xml = open(a.template or TEMPLATE, encoding="utf-8-sig").read()
    base = {b["name"]: b for b in parse_bones(open(a.base or BASE, encoding="utf-8-sig").read())}
    tpl_bone = parse_bones(tpl_xml)[1]["block"]

    crc = lambda n: zlib.crc32(n.encode())
    used = {n for n in fit if crc(n) in binds}
    for n in list(used):  # keep every KP ancestor of a skinned KP bone
        p = fit[n]["parent"]
        while p in fit and p not in used:
            used.add(p); p = fit[p]["parent"]
    kp_parent = {n: fit[n]["parent"] for n in used}
    need = set()
    for n in used:
        p = kp_parent[n]
        if p not in fit:
            while p:
                need.add(p); p = base[p]["fname"]
    children = {}
    for n in need:
        if base[n]["fname"]:
            children.setdefault(base[n]["fname"], []).append(n)
    for n in used:
        children.setdefault(kp_parent[n], []).append(n)
    border = list(base)
    for k in children:
        children[k].sort(key=lambda c: (c not in base, border.index(c) if c in base else 0, c))

    order = []
    def dfs(n):
        order.append(n)
        for c in children.get(n, []):
            dfs(c)
    dfs("Reference")
    idx = {n: i for i, n in enumerate(order)}
    desc = {n: 0 for n in order}
    for n in reversed(order):
        par = base[n]["fname"] if n in base else kp_parent[n]
        if par in desc:
            desc[par] += desc[n] + 1

    G, blocks = {}, []
    Tinv = np.linalg.inv(T)
    for n in order:
        if n in base:
            G[n] = base[n]["G"]
            par = base[n]["fname"]
            name, bid = n, base[n]["id"]
            tpl = base[n]["block"]
        else:
            G[n] = Tinv @ binds[crc(n)]
            par = kp_parent[n]
            name, bid = n, crc(n)
            tpl = tpl_bone
        L = np.linalg.inv(G[par]) @ G[n] if par else G[n]
        blocks.append(bone_block(tpl, PTR0 + idx[n], name, bid, PTR0 + idx[par] if par else None, G[n], L, idx[n], desc[n]))

    # physics records
    recs, rep = [], {}
    depth = {}
    for n in order:
        if n in base:
            continue
        par = kp_parent[n]
        depth[n] = depth[par] + 1 if par in depth else 0
    kp_children = {}
    for n in used:
        kp_children.setdefault(kp_parent[n], []).append(n)
    for n in order:
        if n in base:
            continue
        P = params_for(n, table)
        d = depth[n]
        if P.get("off") or (d == 0 and not P.get("root")):
            continue
        step = int(P.get("step", 1))
        first = 0 if P.get("root") else 1
        if (d - first) % step:
            continue
        # carried length: own segment + the rigid followers until the next simulated link
        carried, m, k = 0.0, n, 0
        while True:
            carried += fit[m]["len"]
            k += 1
            nxt = [c for c in kp_children.get(m, [])]
            if len(nxt) != 1 or k >= step:
                break
            m = nxt[0]
        com = P["com"] if "com" in P else max(0.03, P["com_rel"] * carried)
        gf = P["gf"]
        if isinstance(gf, list):  # ramp from the first simulated joint to the deepest bone below this one
            q, leaf = n, d
            while kp_children.get(q):
                q = kp_children[q][0]; leaf = depth[q]
            span = max(leaf - first, 1)
            gf = gf[0] + (gf[1] - gf[0]) * (d - first) / span
        par = kp_parent[n]
        M0 = np.linalg.inv(G[par]) @ G[n]
        M2 = binds[crc(par)] if crc(par) in binds else T @ G[par]
        pid = crc(par) if par not in base else base[par]["id"]
        recs.append(physics_record(crc(n), pid, M0, M2, P["a"], P["b"], com, gf, P.get("gravity", 9.8), d))
        rep[n] = {"depth": d, "com": round(com, 3), "gf": round(gf, 3), "a": P["a"], "b": P["b"]}
    blob = struct.pack("<f", 3.1) + b"".join(recs)

    # assemble from the template
    head = tpl_xml[:tpl_xml.index('    <DynamicSmallArray Name="Bones" Type="ObjectPtr">')]
    tail = tpl_xml[tpl_xml.index('    </DynamicSmallArray>\n    <ObjectPtr Name="RootBone"'):]
    tail = re.sub(r'(<Link Name="RootBone" Path=")\d+(">)\d+(<)', lambda m: f"{m.group(1)}{PTR0}{m.group(2)}{PTR0}{m.group(3)}", tail)
    tail = re.sub(r'(Name="RootBoneDefaultLocalPosition">)[^<]*(<)', lambda m: m.group(1) + fmt([0, 0, HIPS_H, 0]) + m.group(2), tail)
    tail = re.sub(r'<ObjectPtr ID="\d+" Name="Reflex3Constraints"', f'<ObjectPtr ID="{PTR0 + len(order)}" Name="Reflex3Constraints"', tail)
    ind = "\n            "
    body = "".join(f"{ind}<Unsigned8>{v}</Unsigned8>" for v in blob)
    tail = re.sub(r'(<DynamicBigArray Name="BinaryData" Type="Unsigned8">).*?(\n        </DynamicBigArray>)',
                  lambda m: m.group(1) + body + m.group(2), tail, count=1, flags=re.S)
    xml = head + '    <DynamicSmallArray Name="Bones" Type="ObjectPtr">\n' + "".join(blocks) + tail
    open(out_path, "w", encoding="utf-8", newline="\n").write(xml)
    print(f"bones {len(order)} (base {sum(n in base for n in order)}, KP {sum(n not in base for n in order)}), "
          f"physics records {len(recs)}, blob {len(blob)} bytes -> {out_path}")
    if a.report:
        json.dump({"order": order, "physics": rep}, open(a.report, "w"), indent=1)


if __name__ == "__main__":
    main()
