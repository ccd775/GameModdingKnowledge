# Torso skin weights taken from the game's W mesh, for build_karin.py (Blender 4.2).
# W splits each vertex's pelvis/spine weight smoothly over pelvis, spine_01, spine_02 and spine_03 as a function of
# the height along the spine (s: 0 = pelvis joint, 1 = spine_01, 2 = spine_02, 3 = spine_03, 4 = neck_01) and of the
# direction around the body (front / side / back). Karin's own rig put the crop-top hem on spine_03 and the skin just
# under it on spine_01, so leaning animations opened the midriff. Applying W's profile to skin and clothes alike keeps
# the hem, the skin and the skirt waistband bending together, exactly as the game's animations expect.
# Only the pelvis/spine share of each vertex is redistributed; other influences (thighs, clavicles...) are untouched.
import math
import bpy
import numpy as np

FAM = ["pelvis", "spine_01", "spine_02", "spine_03"]
JOINTS = ["pelvis", "spine_01", "spine_02", "spine_03", "neck_01"]
S_GRID = np.arange(-1.0, 3.76, 0.25)
SECTOR_DEG = np.array([0.0, 90.0, 180.0])   # front, side, back
TARGETS = ("body_2", "pullover", "underwear", "skirt", "Proxy_Skirt")
FADE = (-1.5, -0.5)   # s range over which the W profile fades in (below: the vertex keeps its own pelvis/spine split)
SKIRT_LIKE = ("skirt", "Proxy_Skirt")   # render skirt first: its top defines the waistband for both
SKIRT_BAND = (0.3, 0.8)                 # profile fully on within 0.3 of the skirt top in s, off below 0.8
# In front and over the hips the yoke lies on the skin down to the crotch: it follows that skin (spine_01 ~0.4-0.5) or
# leaning runs push the belly/hips through it. Blends from this value (<= 70 deg) to SKIRT_BAND (>= 120 deg, the back).
SKIRT_BAND_FRONT = (1.3, 2.8)
SKIRT_BAND_ANG = (70.0, 120.0)


def _s_of(z, zj):
    if z <= zj[1]:
        return (z - zj[0]) / (zj[1] - zj[0])
    for i in range(1, len(zj) - 1):
        if z <= zj[i + 1]:
            return i + (z - zj[i]) / (zj[i + 1] - zj[i])
    return len(zj) - 1 + (z - zj[-1]) / (zj[-1] - zj[-2])


def _angle(x, y, fwd):
    """Unsigned angle (deg) between the horizontal direction (x, y) from the spine axis and the facing direction."""
    n = math.hypot(x, y)
    if n < 1e-6:
        return 90.0
    c = (x * fwd[0] + y * fwd[1]) / n
    return math.degrees(math.acos(max(-1.0, min(1.0, c))))


def measure_w(w_glb):
    """Import the W glTF, return the profile table [sector, s, FAM] (rows sum to 1)."""
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=w_glb)
    objs = [o for o in bpy.data.objects if o not in before]
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    mesh = [o for o in objs if o.type == "MESH" and o.name.startswith("SK_")][0]
    head = {n: arm.matrix_world @ arm.data.bones[n].head_local for n in JOINTS + ["foot_l", "ball_l"]}
    zj = [head[n].z for n in JOINTS]
    axis = head["pelvis"]
    f = head["ball_l"] - head["foot_l"]
    fwd = np.array([f.x, f.y]) / math.hypot(f.x, f.y)
    acc = np.zeros((3, len(S_GRID), len(FAM)))
    cnt = np.zeros((3, len(S_GRID)))
    gname = {g.index: g.name for g in mesh.vertex_groups}
    for v in mesh.data.vertices:
        ws = np.array([0.0] * len(FAM))
        for e in v.groups:
            n = gname[e.group]
            if n in FAM:
                ws[FAM.index(n)] += e.weight
        tot = ws.sum()
        if tot < 0.5:
            continue
        co = mesh.matrix_world @ v.co
        s = _s_of(co.z, zj)
        if s < S_GRID[0] - 0.125 or s > S_GRID[-1] + 0.125:
            continue
        k = int(round((s - S_GRID[0]) / 0.25))
        a = _angle(co.x - axis.x, co.y - axis.y, fwd)
        sec = 0 if a < 50 else (2 if a > 130 else 1)
        acc[sec, k] += ws / tot
        cnt[sec, k] += 1
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    table = np.zeros_like(acc)
    for sec in range(3):
        have = [k for k in range(len(S_GRID)) if cnt[sec, k] >= 5]
        for k in range(len(S_GRID)):
            src = min(have, key=lambda j: abs(j - k))
            table[sec, k] = acc[sec, src] / cnt[sec, src]
        sm = table[sec].copy()
        for k in range(1, len(S_GRID) - 1):
            sm[k] = 0.25 * table[sec, k - 1] + 0.5 * table[sec, k] + 0.25 * table[sec, k + 1]
        table[sec] = sm / sm.sum(axis=1, keepdims=True)
    return table, cnt


def _lookup(table, s, a):
    s = min(max(s, S_GRID[0]), S_GRID[-1])
    fk = (s - S_GRID[0]) / 0.25
    k0 = min(int(fk), len(S_GRID) - 2)
    t = fk - k0
    rows = table[:, k0] * (1 - t) + table[:, k0 + 1] * t           # [sector, FAM]
    a = min(max(a, 0.0), 180.0)
    j = 0 if a <= 90.0 else 1
    u = (a - SECTOR_DEG[j]) / 90.0
    return rows[j] * (1 - u) + rows[j + 1] * u


def apply(objs, joints, fwd, table):
    """joints: {name: Vector} Karin joint heads (Blender cm); fwd: facing direction (x, y). Returns per-object counts."""
    zj = [joints[n].z for n in JOINTS]
    axis = joints["pelvis"]
    # The skirt drapes off the body below its waistband: only the band follows the waist skin, the drape keeps its
    # pelvis/thigh anchor (otherwise spine flexion pulls the drape into the buttocks).
    skirt = [o for o in objs if o.name == SKIRT_LIKE[0]]
    s_top = max(_s_of((skirt[0].matrix_world @ v.co).z, zj) for v in skirt[0].data.vertices) if skirt else None
    stats = {}
    for o in objs:
        skirt_like = o.name in SKIRT_LIKE and s_top is not None
        groups = {n: (o.vertex_groups.get(n) or o.vertex_groups.new(name=n)) for n in FAM}
        gname = {g.index: g.name for g in o.vertex_groups}
        n_changed = 0
        for v in o.data.vertices:
            F = sum(e.weight for e in v.groups if gname[e.group] in FAM)
            if F <= 1e-4:
                continue
            co = o.matrix_world @ v.co
            s = _s_of(co.z, zj)
            ang = _angle(co.x - axis.x, co.y - axis.y, fwd)
            dist = _lookup(table, s, ang)
            fade = FADE
            if skirt_like:
                u = min(1.0, max(0.0, (ang - SKIRT_BAND_ANG[0]) / (SKIRT_BAND_ANG[1] - SKIRT_BAND_ANG[0])))
                band = [f * (1.0 - u) + b * u for f, b in zip(SKIRT_BAND_FRONT, SKIRT_BAND)]
                fade = (s_top - band[1], s_top - band[0])
            alpha = min(1.0, max(0.0, (s - fade[0]) / (fade[1] - fade[0])))
            if alpha < 1.0:
                own = np.array([sum(e.weight for e in v.groups if gname[e.group] == n) for n in FAM]) / F
                dist = alpha * dist + (1.0 - alpha) * own
            for n, w in zip(FAM, dist):
                if w * F > 1e-3:
                    groups[n].add([v.index], float(w * F), "REPLACE")
                else:
                    groups[n].remove([v.index])
            n_changed += 1
        stats[o.name] = n_changed
    return stats


def run(w_glb, objs, joints, fwd):
    table, cnt = measure_w(w_glb)
    stats = apply(objs, joints, fwd, table)
    return {"verts": stats, "samples_per_sector": cnt.sum(axis=1).astype(int).tolist(),
            "profile_front": {"%.2f" % s: [round(x, 2) for x in table[0, k]] for k, s in enumerate(S_GRID)}}
