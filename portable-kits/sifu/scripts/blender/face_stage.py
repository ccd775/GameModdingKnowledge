# Face rig for build_karin.py: Karin's face skinned to Sifu's joint-based facial rig.
#  1. landmarks on the W head (from facial bone positions) and on Karin's face (from her shape-key regions),
#  2. thin-plate-spline warp W -> Karin; facial bones placed at warped W positions, eyes at Karin's eye joints,
#  3. facial weights transferred from the warped W head mesh (k-NN, smoothed) onto Karin's face,
#  4. eyelid pivots + weights re-fitted so the game's "Facial Blink" pose reproduces Karin's own blink shape key,
#     mouth weights re-fitted against Karin's kuchi_* keys for the phoneme poses.
# Everything is computed in UE space (cm, left-handed) via sifu_common conversions.
import math
import json
import numpy as np
import bpy
from mathutils import Vector, Matrix, Quaternion
from mathutils.kdtree import KDTree
import sifu_common as sc

FACE_BONES_EXCLUDE = {"head", "neck_01", "neck_02"}
BLINK_GAIN = 1.4
SHAPE_KEYS = ["blink", "kuchi_A", "kuchi_I", "kuchi_U", "kuchi_E", "kuchi_O", "mayu_up", "mayu_sad_1", "mayu_angry_1", "><"]
# pose name -> list of (karin shape key, factor) used as the fitting target
POSE_TARGETS = {
    "Facial Blink": [("blink", 1.0)],
    "Facial Phoneme_Ah": [("kuchi_A", 0.6)],
    "Facial Phoneme_Oh": [("kuchi_O", 0.7)],
    "Facial Phoneme_W": [("kuchi_U", 0.7)],
    "Facial Phoneme_Eh": [("kuchi_E", 0.7)],
    "Facial Phoneme_Ch": [("kuchi_I", 1.0)],
}
LID_BONES = ["upperLids_01_{s}", "upperLids_02_{s}", "upperLids_03_{s}", "lowerLids_01_{s}", "lowerLids_02_{s}",
             "lowerLids_03_{s}", "cornerLids_out_{s}", "conerLids_in_{s}"]
# Karin's eyes are layered plates (visible iris plate ~6.3 cm in front of her eye joint) weighted 30 % LeftEye/RightEye
# in the source. The game's eye look-at blend space (Grunt_M_EyeLookAt_BS, gaze +-50 deg) turns eye_l/eye_r up to
# ~46 deg; the avatar's own LookLeft/Right/Up/Down keys shift the plates at most 0.57 cm (built scale). This uniform
# eye share gives that shift at the game's extreme gaze (0.12 * 6.3 * sin 46 deg).
EYE_WEIGHT = 0.12


def record_shape_keys(face_obj):
    """Store selected shape-key deltas as point attributes (survive face deletion). Call before shape_key_clear."""
    me = face_obj.data
    kb = me.shape_keys.key_blocks
    basis = [k.co.copy() for k in kb["Basis"].data]
    for name in SHAPE_KEYS:
        if name not in kb:
            continue
        a = me.attributes.new("sk_" + name.replace("><", "xx"), "FLOAT_VECTOR", "POINT")
        for i, k in enumerate(kb[name].data):
            a.data[i].vector = k.co - basis[i]


def _key_deltas(face_obj, name, factor):
    a = face_obj.data.attributes.get("sk_" + name.replace("><", "xx"))
    if a is None:
        return None
    R = face_obj.matrix_world.to_3x3()
    return np.array([list(sc.C3 @ (R @ d.vector) * factor) for d in a.data])


# ---------------------------------------------------------------------------------------------------------------------
def _tps_fit(src, dst, reg=1e-3):
    n = len(src)
    K = np.linalg.norm(src[:, None, :] - src[None, :, :], axis=2)
    P = np.hstack([np.ones((n, 1)), src])
    A = np.zeros((n + 4, n + 4))
    A[:n, :n] = K + reg * np.eye(n)
    A[:n, n:] = P
    A[n:, :n] = P.T
    b = np.zeros((n + 4, 3))
    b[:n] = dst
    coef = np.linalg.solve(A, b)
    return src, coef


def _tps_apply(model, pts):
    src, coef = model
    n = len(src)
    K = np.linalg.norm(pts[:, None, :] - src[None, :, :], axis=2)
    P = np.hstack([np.ones((len(pts), 1)), pts])
    return K @ coef[:n] + P @ coef[n:]


def _quat(q):
    x, y, z, w = q
    return Quaternion((w, x, y, z))


def _nnls(A, b, iters=200):
    """Small projected-gradient non-negative least squares (A: m x n)."""
    n = A.shape[1]
    x = np.full(n, 1.0 / max(n, 1))
    AtA, Atb = A.T @ A, A.T @ b
    L = np.linalg.norm(AtA, 2) + 1e-9
    for _ in range(iters):
        x = np.maximum(0.0, x - (AtA @ x - Atb) / L)
        s = x.sum()
        if s > 1.0:
            x /= s
    return x


def run(face_obj, arm, pos, world, w_bones, w_world_bl, w_glb, pose_asset_json, karin_eyes_bl, factor, report):
    """face_obj: Karin face mesh (already skinned: Head/eyes). pos/world: Sifu joint positions & matrices (Blender cm),
    modified in place for facial bones (the caller rebuilds bone matrices from `world`). Returns weights dict
    {vertex index: [(bone, w), ...]} for the face mesh."""
    C = sc.C3
    to_ue = lambda v: np.array(list(C @ v))
    w_pos_ue = {n: to_ue(w_world_bl[n].translation) for n in w_world_bl}
    w_rot_ue = {n: (C @ w_world_bl[n].to_3x3() @ C) for n in w_world_bl}
    head_ue = to_ue(pos["head"])

    # ---- Karin face data (UE space) -------------------------------------------------------------------------------
    fme = face_obj.data
    mats = [m.name if m else "" for m in fme.materials]
    fco = np.array([to_ue(face_obj.matrix_world @ v.co) for v in fme.vertices])
    face_v = np.zeros(len(fco), bool)
    for p in fme.polygons:
        if mats[p.material_index] == "Karin_Face":
            face_v[list(p.vertices)] = True
    keys = {k: _key_deltas(face_obj, k, factor) for k in SHAPE_KEYS}
    mag = {k: (np.linalg.norm(v, axis=1) if v is not None else None) for k, v in keys.items()}

    def region(k, side=None, thr=0.05):
        m = mag[k] > thr
        if side == "l":
            m &= fco[:, 0] > 0.3
        elif side == "r":
            m &= fco[:, 0] < -0.3
        return np.where(m & face_v)[0]

    # UE: +Y forward (face), +Z up, X = character left?  (Blender left = +X, UE X = Blender X)
    def front_point(xz, idx=None):
        idx = np.arange(len(fco)) if idx is None else idx
        cand = idx[np.hypot(fco[idx, 0] - xz[0], fco[idx, 2] - xz[1]) < 0.8]
        if len(cand) == 0:
            cand = idx[np.argsort(np.hypot(fco[idx, 0] - xz[0], fco[idx, 2] - xz[1]))[:5]]
        return fco[cand[np.argmax(fco[cand, 1])]]

    K = {}
    for s, sgn in (("l", 1), ("r", -1)):
        eye = region("blink", s)
        ex = np.percentile(fco[eye, 0], [6, 94]) if sgn > 0 else np.percentile(fco[eye, 0], [94, 6])
        ez = np.percentile(fco[eye, 2], [6, 94])
        cx, cz = (ex[0] + ex[1]) / 2, (ez[0] + ez[1]) / 2
        K[f"eye_front_{s}"] = front_point((cx, cz), eye)
        K[f"lid_in_{s}"] = front_point((ex[0], cz), eye)
        K[f"lid_out_{s}"] = front_point((ex[1], cz), eye)
        K[f"lid_up_{s}"] = front_point((cx, ez[1]), eye)
        K[f"lid_lo_{s}"] = front_point((cx, ez[0]), eye)
        brow = region("mayu_up", s)
        K[f"brow_{s}"] = fco[brow].mean(0)
    mouth = region("kuchi_A")
    mx = np.percentile(np.abs(fco[mouth, 0]), 95)
    mz = np.median(fco[mouth, 2])
    K["lip_corner_l"] = front_point((mx * 0.75, mz), mouth)
    K["lip_corner_r"] = front_point((-mx * 0.75, mz), mouth)
    K["lip_up"] = front_point((0.0, np.percentile(fco[mouth, 2], 80)), mouth)
    K["lip_lo"] = front_point((0.0, np.percentile(fco[mouth, 2], 20)), mouth)
    fidx = np.where(face_v)[0]
    cen = fidx[np.abs(fco[fidx, 0]) < 0.7]
    K["nose"] = fco[cen[np.argmax(fco[cen, 1])]]
    low = cen[fco[cen, 2] < np.percentile(fco[fidx, 2], 12)]
    K["chin"] = fco[low[np.argmax(fco[low, 1])]] if len(low) else fco[cen[np.argmin(fco[cen, 2])]]
    K["forehead"] = front_point((0.0, float(fco[region("mayu_up"), 2].mean()) + 3.5), fidx)
    for s, sgn in (("l", 1), ("r", -1)):
        jz = np.percentile(fco[fidx, 2], 15)
        side = fidx[(np.sign(fco[fidx, 0]) == sgn) & (np.abs(fco[fidx, 2] - jz) < 1.0)]
        K[f"jaw_{s}"] = fco[side[np.argmax(np.abs(fco[side, 0]))]] if len(side) else fco[fidx[0]]

    # ---- W landmarks (from the W head mesh + bones) ---------------------------------------------------------------------
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=w_glb)
    wobjs = [o for o in bpy.data.objects if o not in before]
    wm = [o for o in wobjs if o.type == "MESH" and o.name.startswith("SK_")][0]
    wme = wm.data
    wmats = [m.name.split(".")[0] if m else "" for m in wme.materials]
    keep_mats = {"MI_MainChar_W_Head_Dyn", "MI_MainChar_Teeth", "MI_MainChar_EyeShadow"}
    wv = sorted({v for p in wme.polygons if wmats[p.material_index] in keep_mats for v in p.vertices})
    wco = np.array([to_ue(wm.matrix_world @ wme.vertices[i].co) for i in wv])
    wvg = {g.index: g.name for g in wm.vertex_groups}
    wweights = [{wvg[g.group]: g.weight for g in wme.vertices[i].groups if g.weight > 1e-3} for i in wv]

    def wfront(xz):
        cand = np.where(np.hypot(wco[:, 0] - xz[0], wco[:, 2] - xz[1]) < 0.5)[0]
        if len(cand) == 0:
            cand = np.argsort(np.hypot(wco[:, 0] - xz[0], wco[:, 2] - xz[1]))[:5]
        return wco[cand[np.argmax(wco[cand, 1])]]

    def wb(n):
        p = w_pos_ue[n]
        return wfront((p[0], p[2]))

    W = {}
    for s in ("l", "r"):
        W[f"eye_front_{s}"] = wb(f"eye_{s}")
        W[f"lid_in_{s}"] = wb(f"conerLids_in_{s}")
        W[f"lid_out_{s}"] = wb(f"cornerLids_out_{s}")
        W[f"lid_up_{s}"] = wb(f"upperLids_02_{s}")
        W[f"lid_lo_{s}"] = wb(f"lowerLids_02_{s}")
        W[f"brow_{s}"] = wb(f"brows_02_{s}")
        W[f"lip_corner_{s}"] = wb(f"cornerLips_00_{s}")
        W[f"jaw_{s}"] = wb(f"masseter_01_{s}")
    W["lip_up"] = wb("upperLips_00_mid")
    W["lip_lo"] = wb("lowerLips_00_mid")
    W["nose"] = wb("noseTip_00_mid")
    W["chin"] = wb("chin_00_mid")
    W["forehead"] = wb("forehead_00_mid")
    names = sorted(K)
    src = np.array([W[n] for n in names])
    dst = np.array([K[n] for n in names])
    # anchor the back/top of the head so the warp stays rigid away from the face
    w_head = w_pos_ue["head"]
    for off in ((0, -12, 4), (0, -8, 14), (9, -4, 6), (-9, -4, 6), (0, -2, -6)):
        o = np.array(off, float)
        src = np.vstack([src, w_head + o * 1.0])
        dst = np.vstack([dst, head_ue + o * report.get("head_ratio", 1.36)])
    model = _tps_fit(src, dst)
    report["face_landmarks"] = {n: [round(float(x), 2) for x in K[n]] for n in names}
    report["face_landmark_err_cm"] = float(np.abs(_tps_apply(model, src) - dst).max())

    # ---- facial bone positions ----------------------------------------------------------------------------------------
    face_bones = [b["name"] for b in w_bones if b["parent"] >= 0 and _is_face(b["name"], w_bones)]
    warped = _tps_apply(model, np.array([w_pos_ue[n] for n in face_bones]))
    for n, p in zip(face_bones, warped):
        pos[n] = C @ Vector(p)
    pos["eye_l"], pos["eye_r"] = karin_eyes_bl

    # ---- weight transfer (k-NN on the warped W head) -----------------------------------------------------------------------
    wco_w = _tps_apply(model, wco)
    kd = KDTree(len(wco_w))
    for i, p in enumerate(wco_w):
        kd.insert(p, i)
    kd.balance()
    face_bone_set = set(face_bones) | {"head", "jaw", "lowerTeeth", "upperTeeth", "tongue_01", "tongue_02", "tongue_03", "eye_l", "eye_r"}
    eye_groups = {g.index: g.name for g in face_obj.vertex_groups}
    weights = {}
    for vi in range(len(fco)):
        vgrp = {eye_groups[g.group]: g.weight for g in fme.vertices[vi].groups}
        if max(vgrp.get("eye_l", 0), vgrp.get("eye_r", 0), vgrp.get("LeftEye", 0), vgrp.get("RightEye", 0)) > 0.0:
            continue  # eye plates: no W skin transfer (brow/teeth bones leaked in); eye share added at the end
        if not face_v[vi]:
            continue
        nn = kd.find_n(fco[vi], 6)
        acc, tot = {}, 0.0
        for _, idx, d in nn:
            wgt = 1.0 / (d + 0.2) ** 2
            tot += wgt
            for b, w in wweights[idx].items():
                if b in face_bone_set:
                    acc[b] = acc.get(b, 0.0) + w * wgt
        if not acc:
            continue
        s = sum(acc.values())
        weights[vi] = {b: w / s for b, w in acc.items()}

    # ---- blink: eyelid pivots + weights fitted to Karin's blink ---------------------------------------------------------------
    pa = json.load(open(pose_asset_json))[0]["Properties"]["PoseContainer"]
    tracks = pa["Tracks"]
    pnames = [p["DisplayName"] for p in pa["PoseNames"]]

    def pose(nm):
        p = pa["Poses"][pnames.index(nm)]
        out = {}
        for kv in p["TrackToBufferIndex"]:
            t = p["LocalSpacePose"][kv["Value"]]
            tr, q = t["Translation"], t["Rotation"]
            out[tracks[int(kv["Key"])]] = (np.array([tr["X"], tr["Y"], tr["Z"]]), _quat((q["X"], q["Y"], q["Z"], q["W"])))
        return out

    head_R = np.array(w_rot_ue["head"])  # == our head rotation (W orientations kept)

    def bone_disp(bname, pose_d, pts, pivot=None):
        """Component-space displacement of points rigidly bound to `bname` under an additive pose (parent=head)."""
        if bname not in pose_d:
            return np.zeros_like(pts)
        dt, dq = pose_d[bname]
        Rl = np.array(dq.to_matrix())
        Rc = head_R @ Rl @ head_R.T            # additive rotation acts in the parent (head) frame
        tc = head_R @ dt
        p = (C @ pos[bname]) if pivot is None else pivot
        p = np.array(list(p))
        return (pts - p) @ Rc.T + p + tc - pts

    blink = pose("Facial Blink")
    tgt = keys["blink"] * BLINK_GAIN  # overshoot the fit: a shared rigid pivot otherwise under-closes the big anime lids
    fitted = {}
    for s in ("l", "r"):
        eye_idx = np.array([v for v in region("blink", s) if v in weights or face_v[v]])
        lids = [b.format(s=s) for b in LID_BONES]
        lid_pos = {b: np.array(list(C @ pos[b])) for b in lids}
        nearest_lid = {v: min(lids, key=lambda b: np.linalg.norm(fco[v] - lid_pos[b])) for v in eye_idx}
        # assign each eye-region vertex to its nearest lid bone set by the W transfer, then fit pivots per bone
        for b in lids:
            if b not in blink:
                continue
            dt, dq = blink[b]
            Rl = np.array(dq.to_matrix())
            Rc = head_R @ Rl @ head_R.T
            tc = head_R @ dt
            own = [v for v in eye_idx if nearest_lid.get(v) == b]
            if len(own) < 4:
                continue
            P = fco[own]
            T = tgt[own]
            # minimise sum |(Rc-I)(P - p) + tc - T|^2 over p  (rank-2, regularised toward the warped pivot)
            M = Rc - np.eye(3)
            p0 = np.array(list(C @ pos[b]))
            A = np.vstack([np.kron(np.ones((len(P), 1)), -M), 0.005 * np.eye(3)])
            rhs = np.concatenate([(T - (P @ M.T) - tc).reshape(-1), 0.005 * p0])
            p = np.linalg.lstsq(A, rhs, rcond=None)[0]
            # keep the pivot inside the head (no further than 12 cm behind the lid)
            if np.linalg.norm(p - P.mean(0)) > 14.0:
                p = P.mean(0) + (p - P.mean(0)) * (14.0 / np.linalg.norm(p - P.mean(0)))
            fitted[b] = p
            pos[b] = C @ Vector(p)
        # per-vertex weights (NNLS over lid bones + head(0)) for the blink target
        for v in eye_idx:
            cols, used = [], []
            for b in lids:
                if b in blink:
                    cols.append(bone_disp(b, blink, fco[v:v + 1])[0])
                    used.append(b)
            if not used:
                continue
            A = np.array(cols).T
            x = _nnls(A, tgt[v])
            prior = weights.get(v, {})
            other = {b: w for b, w in prior.items() if b not in used}
            rest = max(0.0, 1.0 - x.sum())
            so = sum(other.values())
            new = {b: float(w) for b, w in zip(used, x) if w > 1e-3}
            for b, w in other.items():
                new[b] = new.get(b, 0.0) + (rest * w / so if so > 0 else 0.0)
            if so == 0 and rest > 0:
                new["head"] = new.get("head", 0.0) + rest
            weights[v] = new
    report["blink_pivots_cm"] = {b: [round(float(x), 2) for x in p] for b, p in fitted.items()}

    # ---- mouth: shared weights fitted to Karin's kuchi_* keys for the phoneme poses ------------------------------------
    mouth_set = set()
    for k in ("kuchi_A", "kuchi_O", "kuchi_U", "kuchi_E", "kuchi_I"):
        if mag[k] is not None:
            mouth_set |= set(np.where((mag[k] > 0.03) & face_v)[0].tolist())
    mouth_idx = sorted(mouth_set)
    fit_poses = [(nm, sum(keys[k] * f for k, f in tg), 1.0) for nm, tg in POSE_TARGETS.items() if nm != "Facial Blink"]
    for nm in ("Facial PainStrong01", "Facial EffortStrong01", "Facial SurprisedStrong01", "Facial PainLight01"):
        fit_poses.append((nm, np.zeros_like(fco), 0.35))
    P_cache = {nm: pose(nm) for nm, _, _ in fit_poses}
    lip_bones = sorted({b for v in mouth_idx for b in weights.get(v, {}) if b not in ("head",) and not b.startswith(("eye_", "upperLids", "lowerLids"))})
    for v in mouth_idx:
        rows, rhs = [], []
        for nm, T, wt in fit_poses:
            D = np.array([bone_disp(b, P_cache[nm], fco[v:v + 1])[0] for b in lip_bones]).T  # 3 x nb
            rows.append(D * wt)
            rhs.append(T[v] * wt)
        A = np.vstack(rows + [0.15 * np.eye(len(lip_bones))])
        prior = np.array([weights.get(v, {}).get(b, 0.0) for b in lip_bones])
        b_ = np.concatenate(rhs + [0.15 * prior])
        x = _nnls(A, b_, iters=400)
        new = {b: float(w) for b, w in zip(lip_bones, x) if w > 1e-3}
        keep = {b: w for b, w in weights.get(v, {}).items() if b not in lip_bones}
        rest = max(0.0, 1.0 - sum(new.values()))
        sk = sum(keep.values())
        for b, w in keep.items():
            new[b] = new.get(b, 0.0) + (rest * w / sk if sk > 0 else 0.0)
        if sk == 0 and rest > 0:
            new["head"] = new.get("head", 0.0) + rest
        weights[v] = new
    report["mouth_fit_bones"] = lip_bones

    # ---- damp realistic mid-face deformation on the smooth anime face --------------------------------------------------
    soft = ("cheek", "nasolabial", "masseter", "lowerCheek", "cheekbone", "drepessor", "lowerOrbital", "sternocleido", "neckFat", "throat")
    eye_all = set(region("blink").tolist())
    for v, ws in weights.items():
        if v in mouth_set or v in eye_all:
            continue
        moved = 0.0
        for b in list(ws):
            if b.startswith(soft):
                moved += ws[b] * 0.5
                ws[b] *= 0.5
        if moved > 0:
            ws["head"] = ws.get("head", 0.0) + moved

    # ---- eyes: one uniform eye-bone share on every eye-plate vertex (a partial share tears the iris plate) -------------
    n_eye = 0
    for vi in range(len(fco)):
        vgrp = {eye_groups[g.group]: g.weight for g in fme.vertices[vi].groups}
        side = [s for s, k in (("l", "LeftEye"), ("r", "RightEye")) if vgrp.get(k, 0) > 0]
        if not side:
            continue
        ws = {b: w for b, w in weights.get(vi, {"head": 1.0}).items() if not b.startswith("eye_")}
        tot = sum(ws.values()) or 1.0
        ws = {b: w / tot * (1.0 - EYE_WEIGHT) for b, w in ws.items()}
        ws[f"eye_{side[0]}"] = EYE_WEIGHT
        weights[vi] = ws
        n_eye += 1
    report["eye_plate_verts"] = n_eye

    # ---- fit quality report -------------------------------------------------------------------------------------------------
    def evaluate(nm, target):
        P = pose(nm)
        err, ref = [], []
        for v, ws in weights.items():
            d = np.zeros(3)
            for b, w in ws.items():
                d += w * bone_disp(b, P, fco[v:v + 1])[0]
            err.append(np.linalg.norm(d - target[v]))
            ref.append(np.linalg.norm(target[v]))
        err, ref = np.array(err), np.array(ref)
        m = ref > 0.2
        return {"rms_err": float(np.sqrt((err[m] ** 2).mean())) if m.any() else 0.0,
                "rms_target": float(np.sqrt((ref[m] ** 2).mean())) if m.any() else 0.0}
    report["face_fit"] = {nm: evaluate(nm, sum(keys[k] * f for k, f in tg)) for nm, tg in POSE_TARGETS.items()}
    for nm in ("Facial PainStrong01", "Facial EffortStrong01", "Facial SurprisedStrong01"):
        report["face_fit"][nm + " (motion vs zero)"] = evaluate(nm, np.zeros_like(fco))

    for o in wobjs:
        bpy.data.objects.remove(o, do_unlink=True)
    return {int(v): ws for v, ws in weights.items()}   # blink-fit keys are numpy ints


def _is_face(name, w_bones):
    by = {b["name"]: b for b in w_bones}
    names = [b["name"] for b in w_bones]
    b = by[name]
    while b["parent"] >= 0:
        p = names[b["parent"]]
        if p == "head":
            return name not in ("cloth_head_A_01",) and not name.startswith(("cloth_", "accessories_"))
        if p in ("neck_02",) and name in ("sternocleidomastoid_mid_l", "sternocleidomastoid_mid_r", "throat_00_mid"):
            return False
        b = by[p]
    return False
