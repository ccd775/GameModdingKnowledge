"""ACU copy of ACOd/scripts/face_rig.py (2026-10-24); the game bones are mapped in GAME_BONES below (Unity head rig:
Fx_LowerJaw, mid upper-lid bones 2303269748 (L) / 1933977111 (R), Fx_Eye_Left / Right). The Odyssey notes that follow
(lid rest angle, --blink-open, lever model) are the method's history.

ACOd notes: the Shadows facial bone names map to Kassandra's head skeleton bones; Odyssey gameplay (v4/v5 in game,
2026-10-19): the lid bone rests ~4-6 deg closed and blinks to ~12 deg, so --blink-open moves the open state to that
rest: the lid's mesh bind is also turned by --blink-open about c and the fit uses --blink-angle minus --blink-open.

Rig Karin's mouth, eyelids and eyes to the game's facial bones from her own shape keys (Blender 5.0, background).

blender -b <fit.blend> --python face_rig.py -- <source.blend> <out.blend> [--key kuchi_A] [--blink-angle 40] [--no-blink]
        [--no-eyes] [--eye-scale 0.5] [--eye-depth 1.4] [--report <json>]

The fit meshes keep the source vertex order and the head is fitted rigidly (scale + rotation), so each source shape-key
delta maps into fit space through one similarity transform per mesh (Umeyama on the basis, residual ~0).
Every channel is a rotation about the lateral axis (+Z in the Naoe frame: fwd +X, up -Y; + = front goes down). Per
vertex: d = the rotation's displacement, s = shape-key delta, w = clamp(<s,d>/<d,d>, 0, 1); the vertex keeps its other
weights scaled by (1 - w).
- Mouth: FB_Jaw_M (head skeleton, loaded by every head row; animated in dialogue), pivot = its head, the angle with the
  smallest residual against `kuchi_A`.
- Blink (v2, 2026-10-07): the game's eyelid bones pivot at the human eyeball centre c, which lies ON Karin's flatter eye
  surface (rigid skinning to them explains 0.3 % of her blink key). v1 (KP_Lid follower bones copying the eyelid
  through a Reflex Orientation constraint in the add-on skeleton) did nothing in game (user, v1.9). v2 skins the lid
  straight to the animated FB_EyelidTop_<side>_02 like the jaw, with a bind offset: the mesh bind of that bone is
  moved to a virtual pivot p behind the eye (u = c - p) and each lid vertex (weight w, rest of its weight on static
  bones) is stored at v - w u. The game puts the bone at c, so at rest the vertex is back at v; when the lid bone turns
  by R about c the vertex moves by  w (R-I)(v-c) + w (1-w) (R-I) u  — the lever u turns the small rotation into the
  downward slide of Karin's lid. p and the per-vertex w are fitted to `blink_<side>` at --blink-angle (40 deg closes
  vanilla Naoe's lids). The blend keeps the lid bones posed at the game rest (c) so it still displays correctly;
  export_karin_lods.py exports with the armature in rest position. Assumes the engine skins with the mesh's own bind
  matrices (skeleton rest edits never changed the skinning, 2026-09-27).
"""
import bpy, sys, json, math, zlib
import numpy as np
from mathutils import Matrix, Vector

argv = sys.argv[sys.argv.index("--") + 1:]
src_path, out_path = argv[0], argv[1]
KEY = argv[argv.index("--key") + 1] if "--key" in argv else "kuchi_A"
BLINK = "--no-blink" not in argv
EYES = "--no-eyes" not in argv
EYE_K = float(argv[argv.index("--eye-scale") + 1]) if "--eye-scale" in argv else 0.5
EYE_DEPTH = float(argv[argv.index("--eye-depth") + 1]) if "--eye-depth" in argv else 1.4
THETA = math.radians(float(argv[argv.index("--blink-angle") + 1]) if "--blink-angle" in argv else 40.0)
# Odyssey (2026-10-19, v4 in game: lids closed <= 1/4 at --blink-angle 40, the mouth barely moved): --jaw-angle fits the
# mouth with the same bind-offset lever as the lids, so kuchi_A is reached at that (small, speech-size) jaw angle
JAW_ANGLE = math.radians(float(argv[argv.index("--jaw-angle") + 1])) if "--jaw-angle" in argv else None
BLINK_OPEN = math.radians(float(argv[argv.index("--blink-open") + 1])) if "--blink-open" in argv else 0.0
# --lid-bone-L/R <id>: drive that side's lid from another head bone (e.g. the upper crease bones xB1A846F5 / x86260864:
# blink 40 deg like the lid's 49.5, but half its sideways twist in the lid-follow/expression poses, v6 in game)
LID_BONE = {s: str(int(argv[argv.index(f"--lid-bone-{s}") + 1], 0)) for s in ("L", "R") if f"--lid-bone-{s}" in argv}
# AC Unity (CN_U_Arno_Head_Rig, identified from Arno's head mesh weights with head_bones.py, docs/STATUS.md):
# Fx_LowerJaw carries the chin / lower lip, the mid upper-lid bones sit on the eye centres (+-0.035, -0.072, 1.725),
# Fx_Eye_Left / Right turn the (separate) eye mesh. Left = +X in the raw frame.
GAME_BONES = {"FB_Jaw_M": "Fx_LowerJaw", "FB_EyelidTop_L_02": "2303269748", "FB_EyelidTop_R_02": "1933977111",
              "FB_Eyeball_L": "Fx_Eye_Left", "FB_Eyeball_R": "Fx_Eye_Right"}
fb = lambda n: GAME_BONES.get(n, n)
JAW = fb("FB_Jaw_M")
rig = bpy.data.objects["NaoeRig"]
for n in (JAW, fb("FB_EyelidTop_L_02"), fb("FB_EyelidTop_R_02")):
    if n not in rig.data.bones:
        raise SystemExit(f"{n} not in the fit rig")
fit_objs = {o.name: o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig}
with bpy.data.libraries.load(src_path) as (df, dt):
    names = list(df.objects)
    dt.objects = list(names)
src = {n: o for n, o in zip(names, dt.objects) if o and o.type == 'MESH'}
FITC = {n: np.array([fo.matrix_world @ v.co for v in fo.data.vertices]) for n, fo in fit_objs.items()}  # before any bake


def umeyama(A, B):  # B ~ s R A + t
    ma, mb = A.mean(0), B.mean(0)
    A0, B0 = A - ma, B - mb
    U, S, Vt = np.linalg.svd(B0.T @ A0 / len(A))
    D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt
    s = (S * np.diag(D)).sum() / (A0 ** 2).sum(1).mean()
    return s, R, mb - s * R @ ma


def disp(P, piv, phi):
    c, s = math.cos(phi), math.sin(phi)
    d = P - piv
    return np.stack([d[:, 0] * c - d[:, 1] * s - d[:, 0], d[:, 0] * s + d[:, 1] * c - d[:, 1], np.zeros(len(P))], 1)


def weights(P, S, piv, phi):
    D = disp(P, piv, phi)
    w = np.clip((S * D).sum(1) / np.maximum((D * D).sum(1), 1e-12), 0.0, 1.0)
    return w, ((S - w[:, None] * D) ** 2).sum()


def deltas(key):  # [(fit object, moving vertex indices, fit positions, fit-space deltas)]
    out = []
    for name, fo in fit_objs.items():
        so = src.get(name)
        if not so or not so.data.shape_keys or key not in so.data.shape_keys.key_blocks or len(so.data.vertices) != len(fo.data.vertices):
            continue
        kb = so.data.shape_keys.key_blocks
        basis = np.array([v.co for v in kb[0].data])
        fitc = FITC[name]
        s, R, t = umeyama(basis, fitc)
        if np.linalg.norm((s * (R @ basis.T)).T + t - fitc, axis=1).max() > 0.0005:
            continue  # not a rigid copy of the source (body parts bent by the fit)
        S = (s * (R @ (np.array([v.co for v in kb[key].data]) - basis).T)).T
        mv = np.where(np.linalg.norm(S, axis=1) > 0.0003)[0]
        if len(mv):
            out.append((fo, mv, fitc[mv], S[mv]))
    if not out:
        raise SystemExit(f"no fit mesh carries shape key {key}")
    return out


def write(data, bone, piv, phi):
    n_set = 0
    for fo, mv, Pm, Sm in data:
        w, _ = weights(Pm, Sm, piv, phi)
        g = fo.vertex_groups.get(bone) or fo.vertex_groups.new(name=bone)
        gi = {x.index: x for x in fo.vertex_groups}
        for vi, wv in zip(mv, w):
            if wv < 0.02:
                continue
            v = fo.data.vertices[int(vi)]
            for el in v.groups:  # scale the existing influences
                if el.group != g.index:
                    gi[el.group].add([v.index], el.weight * (1.0 - wv), 'REPLACE')
            g.add([v.index], float(wv), 'REPLACE')
            n_set += 1
    return n_set


report: dict = {"follow": []}  # "follow" (v1 Orientation followers) stays empty
# --- mouth ---------------------------------------------------------------------------------------------------------
data = deltas(KEY)
P = np.concatenate([d[2] for d in data]); S = np.concatenate([d[3] for d in data])
piv = np.array(rig.matrix_world @ rig.data.bones[JAW].head_local)
if JAW_ANGLE is None:
  grid = [math.radians(a) for a in np.arange(2.0, 40.01, 0.5)]
  phi = grid[int(np.argmin([weights(P, S, piv, g)[1] for g in grid]))]
  err = weights(P, S, piv, phi)[1]
  n = write(data, JAW, piv, phi)
  report["jaw"] = {"key": KEY, "pivot": piv.round(5).tolist(), "phi_deg": round(math.degrees(phi), 2),
                   "explained": round(1 - err / (S ** 2).sum(), 4), "weighted": n}
  print(f"FACE jaw {KEY}: angle {math.degrees(phi):.1f} deg, explained {report['jaw']['explained']:.3f}, {n} verts")

# --- bind offset (shared by lids and eyes) -------------------------------------------------------------------------
done = set()  # (mesh, vertex) already on a bind-offset bone: a second one would rescale the first weight under its offset
offsets = {}  # bone -> lever u (world): its mesh bind moves to c - u
prerot = {}   # bone -> angle (rad, + = closing about the lateral +Z) its mesh bind is turned by about c (--blink-open)


def bake(fo, idx, w, bone, u):
    """Weight vertices idx of fit mesh fo to bone with w (other influences scaled by 1 - w) and store them at v - w u."""
    g = fo.vertex_groups.get(bone) or fo.vertex_groups.new(name=bone)
    gi = {x.index: x for x in fo.vertex_groups}
    me = fo.data
    normals = [tuple(cn.vector) for cn in me.corner_normals]  # keep the shading of the moved vertices
    u_loc = fo.matrix_world.inverted().to_3x3() @ Vector(u.tolist())
    keys = me.shape_keys.key_blocks if me.shape_keys else []
    n_set, off_max = 0, 0.0
    for vi, wv in zip(idx, w):
        if wv < 0.01 or (fo.name, int(vi)) in done:
            continue
        done.add((fo.name, int(vi)))
        v = me.vertices[int(vi)]
        for el in v.groups:  # scale the existing (static) influences
            if el.group != g.index:
                gi[el.group].add([v.index], el.weight * (1.0 - wv), 'REPLACE')
        g.add([v.index], float(wv), 'REPLACE')
        v.co = v.co - float(wv) * u_loc
        for kb in keys:
            kb.data[v.index].co = kb.data[v.index].co - float(wv) * u_loc
        off_max = max(off_max, wv * float(np.linalg.norm(u)))
        n_set += 1
    me.normals_split_custom_set(normals)
    offsets[bone] = u
    return n_set, off_max


def rig_bone(name):  # fit-rig bones without a known name carry their decimal ID as name
    for n in (name, str(zlib.crc32(name.encode()))):
        if n in rig.data.bones:
            return n
    raise SystemExit(f"{name} not in the fit rig")


# --- eyes (2026-10-07) ----------------------------------------------------------------------------------------------
# Karin's iris/highlight vertices are skinned to her own eye bone (VRM Eye.L / LeftEye...). The game turns
# FB_Eyeball_<side> (head skeleton, pivot c = the human eyeball centre, on Karin's eye surface).
# With one uniform weight k and the bind-offset lever u = (c - p) / (1 - k) the iris moves EXACTLY by
#   k (R-I)(v-c) + k (1-k) (R-I) u = k (R-I)(v - p),
# i.e. along a sphere about p, scaled by k (for small angles her eye turns k x the game's angle). All Karin models
# share one head, but their rigs place the eye bone differently (PicodraTech 5.7 cm, UnendingFlame 7.2 cm behind the
# iris), so p is NOT taken from the rig: p = iris centre - depth x iris width straight behind it (--eye-depth 1.4), and
# k = 0.5 (--eye-scale): the iris moves 0.7 iris widths per radian of the game's eye turn on every model (user
# 2026-10-07 on v2.1: PT 0.45 / UF 0.38 with each rig's own pivot moved "a little too little"). The source eye weights
# only shape the distribution (vertex weight = k s / max(s); UnendingFlame: 0.3 everywhere). Only the front layer of
# the group is measured: VRoid keeps expression variants of the iris hidden 4-6 cm behind the face.
if EYES:
    arm = next((o for o in dt.objects if o and o.type == 'ARMATURE'), None)
    if arm is None:
        raise SystemExit("no armature in the source")

    def eye_side(n):
        n = n.lower()
        if "eye" not in n or any(x in n for x in ("lid", "brow", "lash", "high", "light", "white")):
            return None
        if ".l" in n or "left" in n or n.endswith("_l"):
            return "L"
        if ".r" in n or "right" in n or n.endswith("_r"):
            return "R"
        return None
    src_eye = {}
    for b in arm.data.bones:
        sd = eye_side(b.name)
        if sd and sd not in src_eye:
            src_eye[sd] = b
    def world(o):  # appended objects are not evaluated: their matrix_world is identity
        m = o.matrix_basis.copy()
        while o.parent:
            m = o.parent.matrix_basis @ o.matrix_parent_inverse @ m
            o = o.parent
        return m

    for side in ("L", "R"):
        if side not in src_eye:
            raise SystemExit(f"no {side} eye bone in the source armature")
        sb = src_eye[side]
        bone = rig_bone(fb(f"FB_Eyeball_{side}"))
        c = np.array(rig.matrix_world @ rig.data.bones[bone].head_local)
        hits = []
        for name, fo in fit_objs.items():
            so = src.get(name)
            if not so or sb.name not in so.vertex_groups or len(so.data.vertices) != len(fo.data.vertices):
                continue
            gidx = so.vertex_groups[sb.name].index
            sw = np.array([next((e.weight for e in v.groups if e.group == gidx), 0.0) for v in so.data.vertices])
            idx = np.where(sw > 0.01)[0]
            if not len(idx):
                continue
            basis = np.array([v.co for v in so.data.vertices])
            fitc = FITC[name]
            s_, R_, t_ = umeyama(basis, fitc)
            if np.linalg.norm((s_ * (R_ @ basis.T)).T + t_ - fitc, axis=1).max() > 0.0005:
                continue
            ph = np.array(world(so).inverted() @ (world(arm) @ sb.head_local))
            hits.append((fo, idx, sw[idx], fitc[idx], s_ * R_ @ ph + t_))  # last item: the rig's own pivot (report only)
        if not hits:
            raise SystemExit(f"no rigid fit mesh carries the {sb.name} weights")
        P = np.concatenate([h[3] for h in hits]); Wsrc = np.concatenate([h[2] for h in hits])
        p_rig = hits[0][4]
        smax = float(Wsrc.max())  # source weights only give the distribution (UnendingFlame: 0.3 everywhere, 0.7 Head)
        core = P[(Wsrc >= 0.5 * smax) & (P[:, 0] >= P[:, 0].max() - 0.012)]  # visible front layer (forward = +X)
        width = float(np.percentile(core[:, 2], 98) - np.percentile(core[:, 2], 2))  # lateral (+Z) iris width
        p = core.mean(0) - np.array([EYE_DEPTH * width, 0.0, 0.0])  # straight behind the iris centre (forward = +X)
        dist = EYE_DEPTH * width
        lid = np.concatenate([d[2][np.linalg.norm(d[3], axis=1) > 0.3 * np.linalg.norm(d[3], axis=1).max()]
                              for d in deltas(f"blink_{side}")])
        opening = float(np.percentile(lid[:, 2], 98) - np.percentile(lid[:, 2], 2))
        k = EYE_K
        u = (c - p) / (1.0 - k)
        n_set, off_max = 0, 0.0
        for fo, idx, sw, _, _ in hits:
            a, b = bake(fo, idx, k * sw / smax, bone, u)
            n_set += a; off_max = max(off_max, b)
        report[f"eye_{side}"] = {"bone": bone, "source_bone": sb.name, "c": c.round(5).tolist(), "eye_pivot": p.round(5).tolist(), "rig_pivot": p_rig.round(5).tolist(),
                                 "k": round(k, 4), "iris_width": round(width, 4), "eye_opening": round(opening, 4),
                                 "pivot_dist": round(dist, 4),
                                 "bind": (c - u).round(5).tolist(), "weighted": n_set, "max_offset": round(off_max, 4)}
        print(f"FACE eye {side}: {sb.name} -> {bone}, k {k:.3f} (iris {width*100:.1f} cm in a {opening*100:.1f} cm opening, "
              f"pivot {dist*100:.1f} cm behind), "
              f"{n_set} verts, max offset {off_max:.3f} m")

# --- blink ---------------------------------------------------------------------------------------------------------
def lid_fit(P, S, c, u, wg, th=None):  # per-vertex best w for the bind-offset model; returns (w, residual)
    th = THETA - BLINK_OPEN if th is None else th
    A = disp(P, c, th)                                      # (R-I)(v-c)
    T = disp(np.array([c]), c - u, th)[0]                   # (R-I)u
    D = wg[:, None, None] * A[None] + (wg * (1 - wg))[:, None, None] * T[None, None]
    E = ((S[None] - D) ** 2).sum(2)                         # (grid, verts)
    k = E.argmin(0)
    return wg[k], E[k, np.arange(len(P))].sum()


if BLINK:
    lids = {}
    WG = np.linspace(0.0, 1.0, 101)
    for side in ("L", "R"):
        bone = LID_BONE.get(side) or fb(f"FB_EyelidTop_{side}_02")
        if bone not in rig.data.bones:
            raise SystemExit(f"{bone} not in the fit rig")
        data = deltas(f"blink_{side}")
        P = np.concatenate([d[2] for d in data]); S = np.concatenate([d[3] for d in data])
        c = np.array(rig.matrix_world @ rig.data.bones[bone].head_local)
        cand = []
        sc = max(1.0, 40.0 / math.degrees(THETA - BLINK_OPEN))  # lever grid grows as the calibration angle shrinks
        for dx in np.arange(0.0, 0.4 * sc + 1e-9, 0.01 * sc):  # virtual pivot behind (-X) and above/below (Y) the eye
            for dy in np.arange(-0.2 * sc, 0.2 * sc + 1e-9, 0.01 * sc):
                u = np.array([dx, -dy, 0.0])
                cand.append((lid_fit(P, S, c, u, WG[::4])[1], float(np.linalg.norm(u)), u))
        e_min = min(x[0] for x in cand)
        _, _, u = min((x for x in cand if x[0] <= e_min * 1.02 + 1e-12), key=lambda x: x[1])  # shortest good lever
        w, e = lid_fit(P, S, c, u, WG)
        lids[side] = (bone, data, c, u)
        report[f"blink_{side}"] = {"bone": bone, "c": c.round(5).tolist(), "pivot": (c - u).round(5).tolist(),
                                   "angle_deg": round(math.degrees(THETA), 2), "open_deg": round(math.degrees(BLINK_OPEN), 2),
                                   "explained": round(1 - e / (S ** 2).sum(), 4)}
        prerot[bone] = BLINK_OPEN
    for side, (bone, data, c, u) in lids.items():
        n_set, off_max, skipped = 0, 0.0, 0
        for fo, mv, Pm, Sm in data:
            w, _ = lid_fit(Pm, Sm, c, u, WG)
            skipped += sum(1 for vi, wv in zip(mv, w) if wv >= 0.01 and (fo.name, int(vi)) in done)
            a, b = bake(fo, mv, w, bone, u)
            n_set += a; off_max = max(off_max, b)
        report[f"blink_{side}"].update(weighted=n_set, max_offset=round(off_max, 4), skipped_eye_verts=skipped)
        print(f"FACE blink {side}: pivot {np.round(c - u, 4)} (lever {np.linalg.norm(u):.3f} m), "
              f"explained {report[f'blink_{side}']['explained']:.3f}, {n_set} verts, max offset {off_max:.3f} m, "
              f"{skipped} eye verts left to the eye")

if JAW_ANGLE is not None:
    WG = np.linspace(0.0, 1.0, 101)
    data = deltas(KEY)  # the blink section reused data / P / S
    P = np.concatenate([d[2] for d in data]); S = np.concatenate([d[3] for d in data])
    # lever <= --jaw-lever (default 0.3 m): longer levers fit kuchi_A with tiny weights (v5 try: 1.7 m, w < 0.01 -> the
    # mouth was left unrigged); a short lever keeps the chin/lip weights substantial (rigid jaw + amplification)
    LMAX = float(argv[argv.index("--jaw-lever") + 1]) if "--jaw-lever" in argv else 0.3
    cand = []
    for dx in np.arange(-LMAX, LMAX + 1e-9, LMAX / 30):  # pivot in the sagittal plane around the jaw joint
        for dy in np.arange(-LMAX, LMAX + 1e-9, LMAX / 30):
            u = np.array([dx, -dy, 0.0])
            cand.append((lid_fit(P, S, piv, u, WG[::4], JAW_ANGLE)[1], float(np.linalg.norm(u)), u))
    e_min = min(x[0] for x in cand)
    _, _, u = min((x for x in cand if x[0] <= e_min * 1.02 + 1e-12), key=lambda x: x[1])
    w, e = lid_fit(P, S, piv, u, WG, JAW_ANGLE)
    n_set, off_max = 0, 0.0
    for fo, mv, Pm, Sm in data:
        wv, _ = lid_fit(Pm, Sm, piv, u, WG, JAW_ANGLE)
        a, b = bake(fo, mv, wv, JAW, u)
        n_set += a; off_max = max(off_max, b)
    report["jaw"] = {"key": KEY, "pivot": (piv - u).round(5).tolist(), "c": piv.round(5).tolist(), "angle_deg": round(math.degrees(JAW_ANGLE), 2),
                     "explained": round(1 - e / (S ** 2).sum(), 4), "weighted": n_set, "max_offset": round(off_max, 4)}
    print(f"FACE jaw {KEY} (bind offset at {math.degrees(JAW_ANGLE):.1f} deg): pivot {np.round(piv - u, 4)} (lever {np.linalg.norm(u):.3f} m), "
          f"explained {report['jaw']['explained']:.3f}, {n_set} verts, max offset {off_max:.3f} m")

# mesh bind of every bind-offset bone -> c - u (same orientation); the pose puts it back on the game rest (c)
if offsets:
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    eb = rig.data.edit_bones
    rest_c = {}
    for bone, u in offsets.items():
        b = eb[bone]
        b.use_connect = False
        rest_c[bone] = b.matrix.copy()
        if prerot.get(bone):  # bind = Trans(-u) Rot_c(open) rest: skinning sees Rot_c(angle - open) Trans(u)
            c = Vector(np.array(rig.matrix_world @ rig.data.bones[bone].head_local).tolist())
            rw = Matrix.Translation(c) @ Matrix.Rotation(prerot[bone], 4, 'Z') @ Matrix.Translation(-c)
            b.transform(rig.matrix_world.inverted() @ rw @ rig.matrix_world)
        d = rig.matrix_world.inverted().to_3x3() @ Vector((-u).tolist())
        b.head += d; b.tail += d
    bpy.ops.object.mode_set(mode='POSE')
    for bone, m in rest_c.items():
        rig.pose.bones[bone].matrix = m
    bpy.context.view_layer.update()
    bpy.ops.object.mode_set(mode='OBJECT')

for o in src.values():  # drop the appended source objects before saving
    me = o.data
    bpy.data.objects.remove(o)
    if me.users == 0:
        bpy.data.meshes.remove(me)
bpy.ops.wm.save_as_mainfile(filepath=out_path)
if "--report" in argv:
    json.dump(report, open(argv[argv.index("--report") + 1], "w"), indent=1)
print("FACE_RIG_OK", out_path)
