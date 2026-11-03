# Build Lenko (Lenko06.pmx, MMD) for Phantom Blade Zero (Blender 4.2 background). Fork of build_pt.py (Karin_PicodraTech):
# same skeleton contract, face morph scheme, two-face setup, cloth sections and exports; the source is a PMX imported
# with the vendored mmd_tools, its MMD rig normalised to the VRM-1 humanoid names the joint fitting uses.
#
# Usage:
#   blender --background --factory-startup --python build_lenko.py -- <run_dir> [--scale S] [--variant adult|young]
#
# Default scale: Lenko's eye height matched to Karin_Original's in game (1.0994 m x 1.30 = 142.92 cm), as build_pt.py.
#
# Output in <run_dir> (file names are the pipeline's: the UE scripts import Karin_*.fbx):
#   Karin_Leader.fbx  -> Hun_Invs        (invisible leader mesh, every skeleton bone)
#   Karin_Body.fbx    -> Hun_Body_Simple (body, outfit, hair; cloth sections and their simulation shells)
#   Karin_Head.fbx    -> Hun_Head_New    (adult: face behind a hidden first section, shown by KarinFaceShow)
#   Karin_Face.fbx    -> Hun_BrowLashCard (adult: the same face, plain)
#   Empty.fbx, Hat_Empty.fbx, cloth.json, cloth_collision.json, materials.json, textures/*.png, report.json, build.blend
#
# Model-specific edits:
#   - The jacket below the belt is shortened uniformly (vertical scale about the belt's lower edge, blended over 2 cm)
#     so its hem ends a little above the skirt hem at every azimuth (user request); the pigs in its pockets are scaled
#     down about their top so they stay inside the shortened pockets.
#   - Pleated skirt and jacket hem: their render sections are made of loose strips (63 / 52 pieces), so each is bound to
#     a generated smooth shell that is simulated instead (sim_slot, as Karin_Original's skirt); the pocket pigs share the
#     jacket's section (one texture packed from the jacket and pig textures) so they ride on the pockets.
import bpy, sys, os, json, math, collections
import numpy as np
from mathutils import Matrix, Vector, Quaternion

argv = sys.argv[sys.argv.index("--") + 1:]
RUN = os.path.abspath(argv[0])
VARIANT = argv[argv.index("--variant") + 1] if "--variant" in argv else "adult"
VCFG = {
    "adult": dict(uemodel="ue/Hun_Invs.uemodel", skel="c/Hun_Skin_Skeleton.Hun_Skin_Skeleton.skel.json",
                  ref="g/Hun_Invs.Hun_Invs.skel.json", body="c/Hun_Body_Simple.Hun_Body_Simple.skel.json",
                  leader=True, cloth=True, face_fbx="Karin_Head", face_slot0=True, face_show=True, suffix=""),
    "young": dict(uemodel="ue/Hun_Young_Skeleton.uemodel", skel="y/Hun_Young_Skeleton.Hun_Young_Skeleton.skel.json",
                  ref="y/Hun_Young_Body.Hun_Young_Body.skel.json", body="y/Hun_Young_Body.Hun_Young_Body.skel.json",
                  leader=False, cloth=True, face_fbx="Karin_Head", face_slot0=False, face_show=False, suffix="_Young"),
}[VARIANT]
def _need(name, what):
    v = os.environ.get(name)
    if not v: raise SystemExit(f"set {name}: {what}")
    return v
WORK = _need("PBZ_WORK", "folder with the vanilla dumps (ue/*.uemodel, c/ g/ y/ *.skel.json), see BUILD_PIPELINE.md")
PMX = _need("PBZ_SOURCE_PMX", "Lenko06.pmx (its tex/ folder next to it)")
HELPER_TEX = _need("PBZ_HELPER_TEXTURES", "textures/ of a build_pbz.py run (Karin_FlatN, Karin_ARM, Karin_ARMMatte, Karin_Gray, Karin_SCMT .png)")
MMD_TOOLS = _need("PBZ_MMD_TOOLS", "folder holding the mmd_tools package (4.5.x Blender extension) and its opencc dependency")
os.makedirs(RUN, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
TEXSRC = os.path.join(os.path.dirname(PMX), "tex")
UF_ADDONS = os.environ.get("PBZ_BLENDER_ADDONS", "")   # folder holding io_scene_ueformat when the addon is not installed
REPORT = {"variant": VARIANT, "warnings": []}

bpy.ops.wm.read_factory_settings(use_empty=True)
import addon_utils
if not addon_utils.enable("io_scene_ueformat", default_set=True):
    sys.path.insert(0, UF_ADDONS)
    import io_scene_ueformat
    io_scene_ueformat.register()
addon_utils.enable("io_scene_fbx", default_set=True)
sys.path.insert(0, MMD_TOOLS)   # mmd_tools 4.5.14 (Blender extension) + its opencc dependency
import mmd_tools
mmd_tools.register()

def import_uemodel(path):
    s = bpy.context.scene.uf_settings
    s.scale_factor = 1.0; s.import_sockets = False; s.import_morph_targets = False
    before = set(bpy.data.objects)
    bpy.ops.uf.import_uemodel(filepath=path, files=[{"name": os.path.basename(path)}], directory=os.path.dirname(path))
    return [o for o in bpy.data.objects if o not in before]

def norm(v):
    n = np.linalg.norm(v)
    return v / n if n > 1e-9 else v
def smooth(x, a, b):
    t = np.clip((np.asarray(x, dtype=float) - a) / (b - a), 0.0, 1.0)
    return t * t * (3 - 2 * t)

# ---------------------------------------------------------------- vanilla skeleton (Blender = UE with Y negated)
v_objs = import_uemodel(os.path.join(WORK, VCFG["uemodel"]))
v_arm = next(o for o in v_objs if o.type == "ARMATURE")
for o in v_objs:
    if o.type == "MESH": bpy.data.objects.remove(o, do_unlink=True)
# 醉剑 fix (build_pbz.py): bones of the vanilla body missing from the vanilla leader model (weapon_l/r_child,
# ik_weapon_l/r_child, identity children of the weapon bones) are added on their parents so the body keeps every
# vanilla bone; the leader mesh keeps the vanilla set.
_vbody = json.load(open(os.path.join(WORK, VCFG["body"]), encoding="utf-8"))["bones"]
_have = {b.name.lower() for b in v_arm.data.bones}
EXTRA = []
for b in _vbody:
    if b["name"].lower() in _have or b["parent"] < 0: continue
    assert np.abs(b["t"]).max() < 1e-3 and abs(abs(b["q"][3]) - 1.0) < 1e-6, "non-identity extra bone " + b["name"]
    EXTRA.append((b["name"], _vbody[b["parent"]]["name"]))
if EXTRA:
    bpy.ops.object.select_all(action="DESELECT")
    v_arm.select_set(True); bpy.context.view_layer.objects.active = v_arm
    bpy.ops.object.mode_set(mode="EDIT")
    eb = {e.name.lower(): e for e in v_arm.data.edit_bones}
    for n, p in EXTRA:
        pe = eb[p.lower()]
        e = v_arm.data.edit_bones.new(n)
        e.head = pe.head.copy(); e.tail = pe.tail.copy(); e.roll = pe.roll; e.parent = pe
        eb[n.lower()] = e
    bpy.ops.object.mode_set(mode="OBJECT")
EXTRA = [n for n, _ in EXTRA]
REPORT["body_bones_added"] = EXTRA
VM = {b.name: (v_arm.matrix_world @ b.matrix_local) for b in v_arm.data.bones}
VPAR = {b.name: (b.parent.name if b.parent else None) for b in v_arm.data.bones}
ORDER = [b.name for b in v_arm.data.bones]                      # parents first
LOW = {n.lower(): n for n in ORDER}
def V(n): return LOW[n.lower()]                                  # exact vanilla spelling
def vp(n): return np.array(VM[V(n)].translation)
SK = json.load(open(os.path.join(WORK, VCFG["skel"]), encoding="utf-8"))
RT = {b["name"].lower(): b["retarget"] for b in SK["bones"]}
INVS = json.load(open(os.path.join(WORK, VCFG["ref"]), encoding="utf-8"))["bones"]
SKQ = {b["name"].lower(): b["q"] for b in INVS}
SKP = {b["name"].lower(): (INVS[b["parent"]]["name"].lower() if b["parent"] >= 0 else None) for b in INVS}
BODY_SET = [b["name"] for b in json.load(open(os.path.join(WORK, VCFG["body"]), encoding="utf-8"))["bones"]]
BODY_BONES = [V(n) for n in BODY_SET if n.lower() in LOW]
REPORT["body_bones"] = len(BODY_BONES)

# ---------------------------------------------------------------- Lenko (PMX)
before = set(bpy.data.objects)
bpy.ops.mmd_tools.import_model(filepath=PMX, scale=0.08, types={"MESH", "ARMATURE", "MORPHS"}, clean_model=False,
                               remove_doubles=False, log_level="WARNING")
new = [o for o in bpy.data.objects if o not in before]
k_arm = next(o for o in new if o.type == "ARMATURE")
src = next(o for o in new if o.type == "MESH" and o.data.shape_keys)
for o in new:
    if o not in (k_arm, src) and o.type == "MESH": bpy.data.objects.remove(o, do_unlink=True)
# world transforms baked into the data (the root empty and the armature may carry the import scale)
for o in (k_arm, src):
    mw = o.matrix_world.copy(); o.parent = None; o.matrix_world = mw
    if o.data.users > 1: o.data = o.data.copy()   # mmd_tools keeps a second user of the mesh
bpy.ops.object.select_all(action="DESELECT")
for o in (k_arm, src): o.select_set(True)
bpy.context.view_layer.objects.active = k_arm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
for o in [o for o in bpy.data.objects if o.type == "EMPTY"]: bpy.data.objects.remove(o, do_unlink=True)
k_arm.name = "KarinArmature"; k_arm.data.name = "KarinArmature"
for g in [g for g in src.vertex_groups if g.name.startswith("mmd_")]:   # mmd_tools edge scale / vertex order
    src.vertex_groups.remove(g)

# MMD rig -> VRM-1 humanoid names (the joint fitting's contract). The D bones (足D, ひざD, 足首D) carry the leg weights
# and the twist bones (腕捩*, 手捩*) the arm's: their weights go to the plain bone of the segment; 足先EX is the ball.
MERGE = {}
for s in ("L", "R"):
    MERGE.update({f"足D.{s}": f"足.{s}", f"ひざD.{s}": f"ひざ.{s}", f"足首D.{s}": f"足首.{s}", f"つま先.{s}": f"足先EX.{s}",
                  f"腰キャンセル.{s}": "下半身", f"肩P.{s}": f"肩.{s}", f"肩C.{s}": f"肩.{s}", f"ダミー.{s}": f"手首.{s}",
                  f"手先.{s}": f"手首.{s}"})
    for t in ("", "1", "2", "3"):
        MERGE[f"腕捩{t}.{s}"] = f"腕.{s}"; MERGE[f"手捩{t}.{s}"] = f"ひじ.{s}"
for n in ("全ての親", "センター", "グルーブ", "腰", "操作中心"):
    MERGE[n] = "下半身"
BONE_RENAME = {"下半身": "Hips", "上半身": "Spine", "上半身3": "Chest", "上半身2": "UpperChest", "首": "Neck", "頭": "Head"}
for s, S in (("L", "Left"), ("R", "Right")):
    BONE_RENAME.update({f"目.{s}": f"{S}Eye", f"肩.{s}": f"{S}Shoulder", f"腕.{s}": f"{S}UpperArm", f"ひじ.{s}": f"{S}LowerArm",
                        f"手首.{s}": f"{S}Hand", f"足.{s}": f"{S}UpperLeg", f"ひざ.{s}": f"{S}LowerLeg", f"足首.{s}": f"{S}Foot",
                        f"足先EX.{s}": f"{S}ToeBase"})
    for jp, f in (("親指", "Thumb"), ("人指", "Index"), ("中指", "Middle"), ("薬指", "Ring"), ("小指", "Little")):
        segs = ("０", "１", "２") if jp == "親指" else ("１", "２", "３")
        for seg, nm in zip(segs, ("Proximal", "Intermediate", "Distal")):
            BONE_RENAME[f"{jp}{seg}.{s}"] = f"{S}{f}{nm}"
PARENT = {"Spine": "Hips", "Chest": "Spine", "UpperChest": "Chest", "Neck": "UpperChest", "Head": "Neck"}
for S in ("Left", "Right"):
    PARENT.update({f"{S}Shoulder": "UpperChest", f"{S}UpperArm": f"{S}Shoulder", f"{S}LowerArm": f"{S}UpperArm",
                   f"{S}Hand": f"{S}LowerArm", f"{S}UpperLeg": "Hips", f"{S}LowerLeg": f"{S}UpperLeg", f"{S}Foot": f"{S}LowerLeg",
                   f"{S}ToeBase": f"{S}Foot", f"{S}Eye": "Head"})
_names = {b.name for b in k_arm.data.bones}
assert all(k in _names for k in list(MERGE.values()) + list(BONE_RENAME)), sorted(set(list(MERGE.values()) + list(BONE_RENAME)) - _names)

def vgroups(obj):
    names = {g.index: g.name for g in obj.vertex_groups}
    return [[(names[g.group], g.weight) for g in v.groups if g.weight > 1e-6] for v in obj.data.vertices]
def top8(acc):
    items = sorted(acc.items(), key=lambda kv: -kv[1])[:8]
    tot = sum(w for _, w in items) or 1.0
    return [(n, w / tot) for n, w in items if w / tot > 1e-4]
def write_groups(obj, rows):
    for g in list(obj.vertex_groups):
        obj.vertex_groups.remove(g)
    groups = {}
    for i, row in enumerate(rows):
        for n, w in row:
            g = groups.get(n) or obj.vertex_groups.new(name=n)
            groups[n] = g
            g.add([i], w, "REPLACE")
merged = []
for row in vgroups(src):
    acc = collections.defaultdict(float)
    for n, w in row:
        n = MERGE.get(n, n)
        acc[BONE_RENAME.get(n, n)] += w
    merged.append(top8(acc))
for m in list(src.modifiers): src.modifiers.remove(m)
bpy.ops.object.select_all(action="DESELECT")
k_arm.select_set(True); bpy.context.view_layer.objects.active = k_arm
bpy.ops.object.mode_set(mode="EDIT")
ebs = k_arm.data.edit_bones
for b in ebs:
    if b.name in BONE_RENAME: b.name = BONE_RENAME[b.name]
for c, p in PARENT.items():
    ebs[c].use_connect = False; ebs[c].parent = ebs[p]
ebs["Hips"].parent = None
bpy.ops.object.mode_set(mode="OBJECT")
write_groups(src, merged)
_bones = {b.name for b in k_arm.data.bones}
REPORT["groups_not_rig_bones"] = sorted({n for r in merged for n, _ in r} - _bones)

# one object per role (material groups); only the face keeps the shape keys (the morphs move no other vertex)
ROLES = {"Body": ["Lenko_Face", "Lenko_Face_edge", "Lenko_eyes_edge"], "skin": ["Lenko_Body"], "fhair": ["Lenko_Fhair"],
         "bhair": ["Lenko_Bhair"], "cloth": ["Lenko_Cloth", "Lenko_Cloth_h"], "pig": ["Lenko_Pig_l"], "pig2": ["Lenko_coat_Pig_l"],
         "skirt": ["Lenko_Skirt", "Lenko_Skirt_h"], "armband": ["Lenko_Skirt_l"], "leg": ["Lenko_Leg"], "coat": ["Lenko_Coat_l"]}
assert sorted(m.name for m in src.data.materials) == sorted(x for v in ROLES.values() for x in v), [m.name for m in src.data.materials]
k_meshes = {}
for role, mats in ROLES.items():
    bpy.ops.object.select_all(action="DESELECT")
    src.select_set(True); bpy.context.view_layer.objects.active = src
    idx = {i for i, m in enumerate(src.data.materials) if m.name in mats}
    sel = np.array([p.material_index in idx for p in src.data.polygons])
    if sel.all():
        k_meshes[role] = src; break
    bpy.ops.object.mode_set(mode="EDIT"); bpy.ops.mesh.select_all(action="DESELECT"); bpy.ops.object.mode_set(mode="OBJECT")
    src.data.polygons.foreach_set("select", sel)
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.separate(type="SELECTED")
    bpy.ops.object.mode_set(mode="OBJECT")
    o = next(x for x in bpy.context.selected_objects if x is not src)
    k_meshes[role] = o
for role, o in k_meshes.items():
    o.name = role; o.data.name = role
    me = o.data
    for i in reversed(range(len(me.materials))):   # drop slots of other roles
        if not any(p.material_index == i for p in me.polygons):
            o.active_material_index = i
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.material_slot_remove()
    if me.shape_keys and role != "Body":
        kb = me.shape_keys.key_blocks
        base = np.zeros(len(me.vertices) * 3); kb[0].data.foreach_get("co", base)
        for k in kb[1:]:
            a = np.zeros(len(me.vertices) * 3); k.data.foreach_get("co", a)
            assert np.abs(a - base).max() < 1e-6, f"morph {k.name} moves {role}"
        o.shape_key_clear()
    uvs = me.uv_layers   # one UV map, one name: the join merges maps by name and UE samples channel 0
    while len(uvs) > 1: uvs.remove(uvs[-1])
    uvs[0].name = "UVMap"
BODY_MESHES = ["skin", "fhair", "bhair", "cloth", "pig", "pig2", "skirt", "armband", "leg", "coat"]
HEAD_MESHES = ["Body"]
assert sorted(k_meshes) == sorted(BODY_MESHES + HEAD_MESHES), sorted(k_meshes)
KB = {b.name: b for b in k_arm.data.bones}
def descendants(*names):
    out = set()
    stack = [KB[n] for n in names]
    while stack:
        b = stack.pop(); out.add(b.name); stack.extend(b.children)
    return out
ROWS0 = {n: vgroups(o) for n, o in k_meshes.items()}   # source weights (merged / renamed), per role
def vfrac0(name, bones):
    return np.array([sum(w for n, w in row if n in bones) / max(sum(w for _, w in row), 1e-9) for row in ROWS0[name]])
def wco(obj):
    return np.array([list(obj.matrix_world @ v.co) for v in obj.data.vertices])

# ---------------------------------------------------------------- scale (eye height as Karin_Original's in game)
EYE_Z = (KB["LeftEye"].head_local.z + KB["RightEye"].head_local.z) / 2.0
SCALE = float(argv[argv.index("--scale") + 1]) if "--scale" in argv else 142.92 / (100.0 * EYE_Z)
REPORT["scale"] = round(SCALE, 4); REPORT["source_eye_height_m"] = round(EYE_Z, 4)

# ---------------------------------------------------------------- jacket below the belt: uniform shortening
# Source space (metres, before the re-pose). ZB is the belt's lower edge (Lenko_Skirt_h band 1.039-1.065 m, read off
# the model). Below it z -> ZB - g(ZB - z), g(d) = k d + (1 - k) h(d): slope 1 at the belt easing to k over BLEND, so the
# jacket does not kink there. k is the largest factor that leaves the jacket hem MARGIN above the skirt hem in every 15
# degree azimuth sector where both exist. The sleeves (arm-weighted verts) are not touched.
ZB, BLEND, MARGIN_CM = 1.040, 0.020, 0.5   # margin 1.0 until 2026-11-03 ("外套缩得有点过短了")
ARMB = descendants("LeftShoulder", "RightShoulder")
SKB = {b.name for b in k_arm.data.bones if b.name.startswith("sk")}
def h_blend(d):
    t = np.clip(d / BLEND, 0.0, None)
    return np.where(t < 1.0, d - BLEND * (t ** 3 - t ** 4 / 2.0), BLEND / 2.0)
def g_short(d, k): return k * d + (1.0 - k) * h_blend(d)
coat_o, pig_o, skirt_o = k_meshes["coat"], k_meshes["pig"], k_meshes["skirt"]
cco = wco(coat_o); armf = vfrac0("coat", ARMB)
jb = (armf < 0.5)
sko = wco(skirt_o)
def components(obj, mask):
    """Vertex sets of the connected pieces of the masked faces."""
    par = {}
    def f(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    for p in obj.data.polygons:
        if not mask[p.index]: continue
        vs = list(p.vertices)
        for v in vs: par.setdefault(v, v)
        for v in vs[1:]: par[f(v)] = f(vs[0])
    out = collections.defaultdict(set)
    for v in par: out[f(v)].add(v)
    return list(out.values())
# The pleats (Lenko_Skirt in front, Lenko_Skirt_h under the jacket) on the skirt chains, without the pieces that hang
# below the hem: the long ribbon (sk.044-046) and the strap loop on the left hip (streamer ribbon.004).
_skf = vfrac0("skirt", SKB | {"streamer ribbon.004", "pig"})
_hang = vfrac0("skirt", {"sk.044", "sk.045", "sk.046", "streamer ribbon.004"})
_fm = np.array([float(np.mean(_skf[list(p.vertices)])) > 0.5 for p in skirt_o.data.polygons])
PLEAT_V = sorted(v for comp in components(skirt_o, _fm) if not any(_hang[x] > 0.3 for x in comp) for v in comp)
pleat_v = np.array(PLEAT_V)
AX = np.array([0.0, float(sko[pleat_v, 1].mean())])
def azim(p): return np.degrees(np.arctan2(p[:, 0] - AX[0], -(p[:, 1] - AX[1])))
margin = MARGIN_CM / (100.0 * SCALE)
a_s, a_c = azim(sko[pleat_v]), azim(cco[jb])
# 2026-11-03 (user: "外套缩得有点过短了"): one factor for the whole jacket left it 1 cm above the skirt hem only on the
# binding side and up to 6 cm above it at the back. k now varies with azimuth: per 15 degree sector the largest factor
# that keeps the hem MARGIN above the skirt hem there, made symmetric (min with the mirrored sector), each sector
# replaced by the minimum over itself and its neighbours, then interpolated linearly between sector centres (so no
# vertex gets more than its own sector's factor). Not finer: a 5 degree sector often holds only part of a pleat strip,
# its "skirt hem" jumps up to the waistband and k collapses (tried 2026-11-03: hem 9 cm higher).
SEC = 15
kraw, sectors = {}, {}
for a0 in range(-180, 180, SEC):
    ms, mc = (a_s >= a0) & (a_s < a0 + SEC), (a_c >= a0) & (a_c < a0 + SEC)
    if not ms.any() or not mc.any(): continue
    hs, hc = float(sko[pleat_v][ms, 2].min()), float(cco[jb][mc, 2].min())
    T = ZB - hs - margin; D = ZB - hc
    kk = (T - BLEND / 2.0) / (D - BLEND / 2.0) if D > BLEND else 1.0
    kraw[a0] = float(np.clip(kk, 0.3, 1.0))
    sectors[a0] = {"skirt_hem": round(hs, 4), "jacket_hem": round(hc, 4), "k_raw": round(min(kk, 1.0), 4)}
A0S = list(range(-180, 180, SEC))
def _near(a0):   # sectors with no skirt or no jacket (the open front) take the nearest measured one
    return kraw[min(kraw, key=lambda b: min(abs(b - a0), 360 - abs(b - a0)))]
kfill = {a0: kraw.get(a0, _near(a0)) for a0 in A0S}
ksym = {a0: min(kfill[a0], kfill[((-a0 - SEC + 180) % 360) - 180]) for a0 in A0S}
KSEC = {a0: min(ksym[a0], ksym[((a0 - SEC + 180) % 360) - 180], ksym[((a0 + SEC + 180) % 360) - 180]) for a0 in A0S}
_kc = np.array([a0 + SEC / 2.0 for a0 in A0S]); _kv = np.array([KSEC[a0] for a0 in A0S])
def k_at(a):
    return np.interp(np.asarray(a, dtype=float), np.r_[_kc[-1] - 360, _kc, _kc[0] + 360], np.r_[_kv[-1], _kv, _kv[0]])
for a0 in sectors: sectors[a0]["k"] = round(KSEC[a0], 4)
K_SHORT = float(min(KSEC.values()))
def fz(z, k): return np.where(z < ZB, ZB - g_short(ZB - z, k), z)
mv = jb & (cco[:, 2] < ZB)
kv_ = k_at(azim(cco))
newc = cco.copy(); newc[mv, 2] = fz(cco[mv, 2], kv_[mv])
# resulting hem clearance per sector (cm, source space scaled to game cm)
_a_new = azim(newc[jb])
for a0 in sectors:
    mc = (_a_new >= a0) & (_a_new < a0 + SEC)
    if mc.any(): sectors[a0]["margin_cm"] = round((float(newc[jb][mc, 2].min()) - sectors[a0]["skirt_hem"]) * 100 * SCALE, 2)
# pocket pigs: per side, scaled about the top of the pig (kept where the pocket opening goes) so the pig's bottom stays
# 0.5 cm above the shortened pocket's bottom (the highest jacket vertex under the pig's central footprint)
pco = wco(pig_o); newp = pco.copy(); pig_rep = {}
for side in (1.0, -1.0):
    m = pco[:, 0] * side > 0
    P = pco[m]; lo, hi = P.min(0), P.max(0); c = (lo + hi) / 2.0; ext = (hi - lo) / 4.0
    fm = jb & (np.abs(cco[:, 0] - c[0]) < ext[0]) & (np.abs(cco[:, 1] - c[1]) < ext[1]) & (cco[:, 2] < lo[2])
    zpb = float(cco[fm, 2].max()) if fm.any() else lo[2] - 0.03
    kp_ = float(k_at(azim(c[None, :]))[0])
    top = np.array([c[0], c[1], hi[2]]); top2 = np.array([c[0], c[1], float(fz(np.array([hi[2]]), kp_)[0])])
    s = (top2[2] - float(fz(np.array([zpb]), kp_)[0]) - 0.005) / (hi[2] - lo[2])
    s = float(np.clip(s, kp_, 1.0))
    newp[m] = top2 + s * (P - top)
    pig_rep["left" if side > 0 else "right"] = {"pocket_bottom": round(zpb, 4), "k": round(kp_, 4), "scale": round(s, 3), "lift_cm": round((top2[2] - top[2]) * 100, 2)}
for o, a in ((coat_o, newc), (pig_o, newp)):
    inv = np.array(o.matrix_world.inverted())
    loc = (np.c_[a, np.ones(len(a))] @ inv.T)[:, :3]
    o.data.vertices.foreach_set("co", loc.ravel()); o.data.update()
REPORT["jacket_shorten"] = {"belt_z": ZB, "k_min": round(K_SHORT, 4), "k_max": round(float(max(KSEC.values())), 4),
                            "moved_verts": int(mv.sum()), "margin_cm": MARGIN_CM,
                            "hem_before_after": [round(float(cco[jb, 2].min()), 4), round(float(newc[jb, 2].min()), 4)],
                            "sectors": sectors, "pigs": pig_rep}

G = Matrix.Scale(100.0 * SCALE, 4)   # both face -Y in Blender; metres -> cm
Gn = np.array(G)
def kp(n): return np.array(G @ (k_arm.matrix_world @ KB[n].head_local))
def ktail(n): return np.array(G @ (k_arm.matrix_world @ KB[n].tail_local))

def swing(a, b):
    q = Vector(norm(a)).rotation_difference(Vector(norm(b)))
    return np.array(q.to_matrix())
def rigid(R, src_, dst):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = dst - R @ src_
    return M
def apply(M, p): return M[:3, :3] @ p + M[:3, 3]
def ue(p): return np.array([p[0], -p[1], p[2]])   # UE component space = Blender with Y negated

# ---------------------------------------------------------------- joint correspondence (vanilla name -> Lenko bone)
KMAP = {"neck_01": "Neck", "head": "Head", "eye_l_root": "LeftEye", "eye_r_root": "RightEye"}
for s, S in (("l", "Left"), ("r", "Right")):
    KMAP.update({f"clavicle_{s}": f"{S}Shoulder", f"upperarm_{s}": f"{S}UpperArm", f"lowerarm_{s}": f"{S}LowerArm",
                 f"hand_{s}": f"{S}Hand", f"thigh_{s}": f"{S}UpperLeg", f"calf_{s}": f"{S}LowerLeg", f"foot_{s}": f"{S}Foot",
                 f"ball_{s}": f"{S}ToeBase"})
    for pf, kf in (("thumb", "Thumb"), ("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little")):
        for i, seg in enumerate(("Proximal", "Intermediate", "Distal")):
            KMAP[f"{pf}_0{i + 1}_{s}"] = f"{S}{kf}{seg}"
KMAP = {V(k): v for k, v in KMAP.items()}
INV = {v: k for k, v in KMAP.items()}
SEGCHILD = {"neck_01": "head"}
for s in "lr":
    SEGCHILD.update({f"clavicle_{s}": f"upperarm_{s}", f"upperarm_{s}": f"lowerarm_{s}", f"lowerarm_{s}": f"hand_{s}",
                     f"hand_{s}": f"middle_01_{s}", f"thigh_{s}": f"calf_{s}", f"calf_{s}": f"foot_{s}", f"foot_{s}": f"ball_{s}"})
    for pf in ("thumb", "index", "middle", "ring", "pinky"):
        SEGCHILD[f"{pf}_01_{s}"] = f"{pf}_02_{s}"; SEGCHILD[f"{pf}_02_{s}"] = f"{pf}_03_{s}"
SEGCHILD = {V(a): V(b) for a, b in SEGCHILD.items()}

# ---------------------------------------------------------------- new bind joints (as build_pt.py)
P0 = (kp("LeftUpperLeg") + kp("RightUpperLeg")) / 2.0      # pelvis at the hip joints (vanilla thighs are lateral)
P0[0] = 0.0
TORSO = [V(n) for n in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01")]
r_torso = np.linalg.norm(kp("Neck") - P0) / max(np.linalg.norm(vp("neck_01") - vp("pelvis")), 1e-6)
r_neck = np.linalg.norm(kp("Head") - kp("Neck")) / max(np.linalg.norm(vp("head") - vp("neck_01")), 1e-6)
NEW, RATIO, LEN = {}, {}, {}
KM = {}
SEGSCALE = {}   # Lenko bone -> 3x3 applied in its region before the rotation (filled once the joints are placed)

def offset(n):
    p = VPAR[n]
    return vp(n) - vp(p)

def place(n):
    p = VPAR[n]
    if p is None:
        NEW[n] = vp(n); RATIO[n] = 1.0; return
    off = offset(n); vlen = np.linalg.norm(off); vdir = norm(off)
    mode = RT.get(n.lower(), "AnimationScaled")
    if mode == "Animation":
        NEW[n] = NEW[p] + off
    elif n == V("pelvis"):
        NEW[n] = P0.copy()
    elif n in TORSO:
        NEW[n] = NEW[p] + vdir * vlen * r_torso
    elif n in (V("neck_02"), V("head")):
        NEW[n] = NEW[p] + vdir * vlen * r_neck
    elif n in LEN:
        NEW[n] = NEW[p] + vdir * LEN[n]
    else:
        NEW[n] = NEW[p] + vdir * vlen * RATIO.get(p, 1.0)
    RATIO[n] = RATIO.get(p, 1.0)
    if n == V("pelvis"): RATIO[n] = r_torso
    if n in TORSO: RATIO[n] = r_torso
    if n in (V("neck_01"), V("neck_02"), V("head")): RATIO[n] = r_neck

def region(kname):
    """Rigid transform taking Lenko bone kname's region into the new bind pose."""
    if kname in KM: return KM[kname]
    kb = KB[kname]
    if kname == "Hips":
        M = rigid(np.eye(3), P0, NEW[V("pelvis")])
    elif kname in ("Spine", "Chest"):
        a, b = kp("Neck") - P0, NEW[V("neck_01")] - NEW[V("pelvis")]
        R = swing(a, b)
        S = np.eye(3) + (np.linalg.norm(b) / np.linalg.norm(a) - 1.0) * np.outer(norm(a), norm(a))
        M = np.eye(4); M[:3, :3] = R @ S; M[:3, 3] = NEW[V("pelvis")] - R @ S @ P0
    elif kname in ("LeftEye", "RightEye"):
        M = region(kb.parent.name)
    elif kname == "Head" and RT.get(V("head").lower()) == "Animation":
        M = region(kb.parent.name)
    elif kname in INV and INV[kname] in NEW:
        n = INV[kname]
        c = SEGCHILD.get(n)
        st_ = seg_start(n)
        if n in PC:   # shoulder: the chest's rotation, then the swing onto the arm root (no twist against the chest)
            U_, _, Vt_ = np.linalg.svd(region(kb.parent.name)[:3, :3]); Rp = U_ @ Vt_
            R = swing(Rp @ (kp(KMAP[c]) - kp(kname)), seg_end(n) - st_) @ Rp
        elif c is not None and c in KMAP and c in NEW:
            R = swing(kp(KMAP[c]) - kp(kname), seg_end(n) - st_)
        elif kb.parent is not None:
            R = region(kb.parent.name)[:3, :3]
        else:
            R = np.eye(3)
        M = rigid(R, kp(kname), st_)
        if kname in SEGSCALE:   # forearm stretched to the vanilla wrist, hand and fingers scaled (see SEGSCALE)
            M[:3, :3] = R @ SEGSCALE[kname]; M[:3, 3] = st_ - M[:3, :3] @ kp(kname)
    elif kb.parent is not None:
        M = region(kb.parent.name)
    else:
        M = np.eye(4)
    KM[kname] = M
    return M

def proj_len(n, target):
    p = VPAR[n]
    return max(float(np.dot(target - NEW[p], norm(offset(n)))), 0.5)

# ---- shoulders (2026-11-03, user: "肩膀过宽了 ... 像是健壮成年男性的肩宽"). The clavicle used to be placed with Lenko's
# clavicle head projected onto the vanilla spine_05 -> clavicle line: that head sat 5.9 cm (adult) / 4.9 cm (young) off
# Lenko's own, and the shoulder mesh, moved rigidly onto it, put her arms that much further out. Now the shoulder mesh
# stays where her chest puts it (natural clavicle head PC, see seg_start) and the arm root is aimed at her own
# shoulder joint T:
# - adult (clavicle and upperarm translations AnimationScaled: the game keeps the mesh's bone lengths, the directions
#   come from the animation): the two lengths spine_05 -> clavicle and clavicle -> upperarm are solved (least squares
#   along the vanilla directions) so that the upperarm joint lands on T (clavicle at least 40% of hers: lateral
#   position exact, see below); half of the residual height is taken up as a mesh offset.
# - young (every bone Animation: vanilla joint positions): the arm mesh is moved a fraction of the way from the vanilla
#   shoulder joint toward T (capped), the offset halving at the elbow and gone at the wrist, so the hands still meet
#   the weapon; the arm still turns about the vanilla joint.
SHOULDER_FIT = all(RT.get(V(f"{b}_l").lower()) != "Animation" for b in ("clavicle", "upperarm"))
SHOULDER_F = float(argv[argv.index("--shoulder-f") + 1]) if "--shoulder-f" in argv else (0.5 if SHOULDER_FIT else 0.6)
SHOULDER_CAP = 4.0   # cm, largest mesh offset of the arm root from its joint
LEN_FIXED, OFS, PC = set(), {}, {}
CLAV = {V("clavicle_l"): "Left", V("clavicle_r"): "Right"}
def nat(S, what):
    """Lenko's own shoulder points carried by her chest region: clavicle head ('Shoulder') or arm root ('UpperArm')."""
    return apply(region(KB[f"{S}Shoulder"].parent.name), kp(f"{S}{what}"))
def seg_start(n): return PC[n] if n in PC else NEW[n] + OFS.get(n, 0.0)
def seg_end(n):
    c = SEGCHILD[n]
    return NEW[c] + OFS.get(c, 0.0)

for n in ORDER:
    p = VPAR[n]
    if p is not None and n in KMAP and RT.get(n.lower()) != "Animation" and n not in TORSO and n not in (V("neck_01"), V("head")) \
            and n not in LEN_FIXED:
        k = KMAP[n]
        kparent = KB[k].parent.name
        pn = INV.get(kparent)
        if pn is not None and pn == p and SEGCHILD.get(p) == n:
            LEN[n] = float(np.linalg.norm(kp(k) - kp(kparent)))
        else:
            KM.clear()
            LEN[n] = proj_len(n, apply(region(kparent), kp(k)))
        if SHOULDER_FIT and n in CLAV:
            S = CLAV[n]; up = SEGCHILD[n]
            KM.clear()
            T = nat(S, "UpperArm")
            d1, d2 = norm(offset(n)), norm(offset(up)); rhs = T - NEW[p]
            L_cl = float(np.linalg.norm(kp(f"{S}UpperArm") - kp(f"{S}Shoulder")))
            a_, b_ = (float(x) for x in np.linalg.lstsq(np.c_[d1, d2], rhs, rcond=None)[0])
            # Lenko's arm root is high (anime shoulders): reaching it exactly wants a clavicle of 0.5 cm, which moves the
            # clavicle pivot out next to the arm root (a shrug would then push the shoulder top by the neck down). The
            # clavicle keeps at least 40% of her length, the lateral position of the joint matches hers exactly and the
            # height left over is shared between a steeper shoulder slope and a mesh offset (SHOULDER_F)
            if b_ < 0.4 * L_cl:
                b_ = 0.4 * L_cl
                a_ = float((rhs[0] - b_ * d2[0]) / d1[0]) if abs(d1[0]) > 0.2 else float(np.dot(rhs - b_ * d2, d1))
            if a_ < 1.0: a_ = 1.0; b_ = max(float(np.dot(rhs - a_ * d1, d2)), 0.4 * L_cl)
            REPORT.setdefault("shoulder", {})[S] = {"len_before": [round(LEN[n], 2), round(L_cl, 2)],
                                                    "len_after": [round(float(a_), 2), round(float(b_), 2)]}
            LEN[n] = float(a_); LEN[up] = float(b_); LEN_FIXED.add(up)
    place(n)
KM.clear()
for n, c in SEGCHILD.items():
    if n in NEW and c in NEW:
        vl = np.linalg.norm(vp(c) - vp(n))
        if vl > 1e-6: RATIO[n] = np.linalg.norm(NEW[c] - NEW[n]) / vl
for n in ORDER:
    if n not in KMAP and n not in TORSO and VPAR[n] is not None and RT.get(n.lower()) != "Animation" and n != V("pelvis") \
            and n not in (V("neck_02"), V("head")) and n not in LEN:
        p = VPAR[n]
        NEW[n] = NEW[p] + norm(offset(n)) * np.linalg.norm(offset(n)) * RATIO.get(p, 1.0)
    elif VPAR[n] is not None and RT.get(n.lower()) == "Animation":
        NEW[n] = NEW[VPAR[n]] + offset(n)
# shoulder mesh at Lenko's own clavicle head; arm root aimed at her own shoulder joint (see SHOULDER_FIT above)
for cl, S in CLAV.items():
    up, lo = SEGCHILD[cl], SEGCHILD[SEGCHILD[cl]]
    KM.clear()
    T, PC[cl] = nat(S, "UpperArm"), nat(S, "Shoulder")
    o = SHOULDER_F * (T - NEW[up])
    if np.linalg.norm(o) > SHOULDER_CAP: o = o * SHOULDER_CAP / np.linalg.norm(o)
    OFS[up], OFS[lo] = o, 0.5 * o
    REPORT.setdefault("shoulder", {}).setdefault(S, {}).update({
        "natural_root": [round(float(x), 2) for x in ue(T)], "joint_root": [round(float(x), 2) for x in ue(NEW[up])],
        "mesh_root": [round(float(x), 2) for x in ue(NEW[up] + o)], "mesh_offset_cm": round(float(np.linalg.norm(o)), 2),
        "clavicle_pivot": [round(float(x), 2) for x in ue(NEW[cl])], "clavicle_head_mesh": [round(float(x), 2) for x in ue(PC[cl])]})
KM.clear()
# Joints kept at vanilla offsets (Animation retargeting: hands and fingers on the adult, every bone on the young
# player) do not meet Lenko's segment ends: placed rigidly, the skin stretched or folded over the gap (adult wrist 4 cm,
# palm 3.5 cm). Each limb segment is stretched along its axis onto its child joint, and the hand and fingers are scaled
# up by the palm ratio (at most 1.3; the rest stays as stretch between the palm and the finger roots).
for s, S in (("l", "Left"), ("r", "Right")):
    hd_ = V(f"hand_{s}")
    for seg in ("clavicle", "upperarm", "lowerarm", "thigh", "calf", "foot"):
        n_ = V(f"{seg}_{s}"); c_ = SEGCHILD[n_]
        a_ = kp(KMAP[c_]) - kp(KMAP[n_]); b_ = seg_end(n_) - seg_start(n_)
        st = float(np.linalg.norm(b_) / np.linalg.norm(a_))
        if abs(st - 1.0) > 0.02:
            SEGSCALE[KMAP[n_]] = np.eye(3) + (st - 1.0) * np.outer(norm(a_), norm(a_))
            REPORT.setdefault("segment_stretch", {})[n_] = round(st, 3)
    pr = float(np.median([np.linalg.norm(NEW[V(f"{f}_01_{s}")] - NEW[hd_]) / np.linalg.norm(kp(f"{S}{F}Proximal") - kp(f"{S}Hand"))
                          for f, F in (("index", "Index"), ("middle", "Middle"), ("ring", "Ring"), ("pinky", "Little"))]))
    sh = float(np.clip(pr, 1.0, 1.3))
    for nm in [f"{S}Hand"] + [f"{S}{F}{g}" for F in ("Thumb", "Index", "Middle", "Ring", "Little") for g in ("Proximal", "Intermediate", "Distal")]:
        SEGSCALE[nm] = sh * np.eye(3)
    REPORT.setdefault("hand_fix", {})[s] = {"palm_ratio": round(pr, 3), "hand_scale": round(sh, 3)}
KM.clear()
for kb in k_arm.data.bones:
    region(kb.name)
REPORT["ratios"] = {"torso": round(float(r_torso), 3), "neck": round(float(r_neck), 3)}
REPORT["joint_mismatch_cm"] = {n: round(float(np.linalg.norm(apply(region(KB[k].parent.name), kp(k)) - NEW[n])), 2)
                               for n, k in KMAP.items() if KB[k].parent is not None}

def chain_of(head):
    """head and its longest line of descendants (sk.008 also carries the pig bone: the chain goes on to sk.009)."""
    def depth(b): return 1 + max((depth(c) for c in b.children), default=0)
    names = [head]
    while KB[names[-1]].children:
        names.append(max(sorted(KB[names[-1]].children, key=lambda c: c.name), key=depth).name)
    return names

# ---------------------------------------------------------------- chains: skirt panels and the long ribbon
# No Lenko bone maps to a game chain bone (build_pbz.py: the game poses them). The skirt chains (roots under the
# upper body in the MMD rig) blend from the pelvis toward the thighs with depth, the panel in front of / behind a thigh
# mostly that thigh (build_pbz.py); the cloth shell simulates on top. The jacket chains keep their parent (the chest ->
# the spine split, i.e. spine_01 at the hem): a jacket hangs from the shoulders; its shell simulates the legs' push.
def azim1(p): return math.degrees(math.atan2(p[0] - P0[0], -(p[1] - P0[1])))
RENAME = {}
SKIRT_ROOTS = [c.name for c in KB["Spine"].children if c.name.startswith("sk")]
for h in SKIRT_ROOTS:
    kn = chain_of(h)
    a = math.radians(azim1(kp(kn[min(1, len(kn) - 1)])))
    t = min(max((math.sin(a) + 0.6) / 1.2, 0.0), 1.0)
    left = t * t * (3.0 - 2.0 * t)
    reach = 0.7 + 0.3 * abs(math.cos(a))
    for d, k in enumerate(kn):
        wt = (0.0, 0.3, 0.55, 0.75)[min(d, 3)] * reach
        RENAME[k] = [(V("pelvis"), 1.0 - wt), (V("thigh_l"), wt * left), (V("thigh_r"), wt * (1.0 - left))]
        for c in KB[k].children:   # side branches (streamer ribbon.004, pig) follow their chain joint
            if c.name not in kn:
                for cc in descendants(c.name): RENAME[cc] = RENAME[k]
REPORT["skirt_chains"] = {h: len(chain_of(h)) for h in SKIRT_ROOTS}

# ---------------------------------------------------------------- mesh re-pose (LBS of the rigid region transforms)
def lbs(rows, co):
    out = np.zeros_like(co)
    for i, row in enumerate(rows):
        tot = sum(w for _, w in row)
        if tot <= 0:
            out[i] = co[i]; continue
        acc = np.zeros(3)
        for n, w in row:
            Mi = KM.get(n, np.eye(4))
            acc += (w / tot) * (Mi[:3, :3] @ co[i] + Mi[:3, 3])
        out[i] = acc
    return out

def deform(obj, keep_keys):
    me = obj.data
    W = np.array(obj.matrix_world)
    T = Gn @ W
    rows = vgroups(obj)
    def to_cm(a): return (np.c_[a, np.ones(len(a))] @ T.T)[:, :3]
    kept = {}
    if me.shape_keys:
        kb = me.shape_keys.key_blocks
        def kco(key):
            a = np.zeros(len(me.vertices) * 3); key.data.foreach_get("co", a)
            return a.reshape(-1, 3)
        base = kco(kb[0])
        mix = base.copy()
        for key in kb[1:]:
            if key.name in keep_keys:
                kept[key.name] = kco(key) - base
            elif abs(key.value) > 1e-4 and not key.mute:
                mix += (kco(key) - base) * key.value
                REPORT.setdefault("baked_keys", []).append(f"{obj.name}:{key.name}={key.value:.2f}")
        base = mix
        obj.shape_key_clear()
    else:
        base = np.array([list(v.co) for v in me.vertices])
    co = to_cm(base)
    out = lbs(rows, co)
    obj.matrix_world = Matrix.Identity(4)
    me.vertices.foreach_set("co", out.ravel())
    me.update()
    deltas = {}
    for name, d in kept.items():
        moved = lbs(rows, to_cm(base + d))
        deltas[name] = moved - out
    return rows, deltas

# ---------------------------------------------------------------- face morphs named after MetaHuman control curves
# curve -> {MMD morph: weight}; "|L" / "|R" restrict to the character's left (+X) / right (-X) half. The MMD morphs:
# まばたき blink, 笑い smiling eyes, びっくり surprised eyes, あいうえお mouth, 口角上げ/下げ corners up / down,
# 口横広げ wide mouth, 真面目 / 困る / 怒り / 上 / 下 brows (serious, troubled, angry, up, down). Lenko's eyes are
# bone-driven (目.L/R, merged into the head here), so look morphs are made from the iris verts (_Look*, below).
FACE = {
    "CTRL_expressions_eyeBlinkL": {"まばたき|L": 1.0}, "CTRL_expressions_eyeBlinkR": {"まばたき|R": 1.0},
    "CTRL_expressions_eyeSquintInnerL": {"笑い|L": 0.35}, "CTRL_expressions_eyeSquintInnerR": {"笑い|R": 0.35},
    "CTRL_expressions_eyeCheekRaiseL": {"笑い|L": 0.5}, "CTRL_expressions_eyeCheekRaiseR": {"笑い|R": 0.5},
    "CTRL_expressions_eyeWidenL": {"びっくり|L": 0.7}, "CTRL_expressions_eyeWidenR": {"びっくり|R": 0.7},
    "CTRL_expressions_eyeLookUpL": {"_LookUp|L": 1.0}, "CTRL_expressions_eyeLookUpR": {"_LookUp|R": 1.0},
    "CTRL_expressions_eyeLookDownL": {"_LookDown|L": 1.0}, "CTRL_expressions_eyeLookDownR": {"_LookDown|R": 1.0},
    "CTRL_expressions_eyeLookLeftL": {"_LookLeft|L": 1.0}, "CTRL_expressions_eyeLookLeftR": {"_LookLeft|R": 1.0},
    "CTRL_expressions_eyeLookRightL": {"_LookRight|L": 1.0}, "CTRL_expressions_eyeLookRightR": {"_LookRight|R": 1.0},
    "CTRL_expressions_browDownL": {"怒り|L": 0.6, "下|L": 0.4}, "CTRL_expressions_browDownR": {"怒り|R": 0.6, "下|R": 0.4},
    "CTRL_expressions_browLateralL": {"真面目|L": 0.6}, "CTRL_expressions_browLateralR": {"真面目|R": 0.6},
    "CTRL_expressions_browRaiseInL": {"困る|L": 1.0}, "CTRL_expressions_browRaiseInR": {"困る|R": 1.0},
    "CTRL_expressions_browRaiseOuterL": {"上|L": 1.0}, "CTRL_expressions_browRaiseOuterR": {"上|R": 1.0},
    "CTRL_expressions_jawOpen": {"あ": 1.0},
    "CTRL_expressions_mouthCornerPullL": {"口角上げ|L": 1.0}, "CTRL_expressions_mouthCornerPullR": {"口角上げ|R": 1.0},
    "CTRL_expressions_mouthCornerDepressL": {"口角下げ|L": 0.7}, "CTRL_expressions_mouthCornerDepressR": {"口角下げ|R": 0.7},
    "CTRL_expressions_mouthStretchL": {"口横広げ|L": 0.6}, "CTRL_expressions_mouthStretchR": {"口横広げ|R": 0.6},
    "CTRL_expressions_mouthFunnelUL": {"お|L": 0.25}, "CTRL_expressions_mouthFunnelUR": {"お|R": 0.25},
    "CTRL_expressions_mouthFunnelDL": {"お|L": 0.25}, "CTRL_expressions_mouthFunnelDR": {"お|R": 0.25},
    "CTRL_expressions_mouthLipsPurseUL": {"う|L": 0.25}, "CTRL_expressions_mouthLipsPurseUR": {"う|R": 0.25},
    "CTRL_expressions_mouthLipsPurseDL": {"う|L": 0.25}, "CTRL_expressions_mouthLipsPurseDR": {"う|R": 0.25},
    "CTRL_expressions_mouthUpperLipRaiseL": {"え|L": 0.4}, "CTRL_expressions_mouthUpperLipRaiseR": {"え|R": 0.4},
    "CTRL_expressions_mouthLowerLipDepressL": {"え|L": 0.3}, "CTRL_expressions_mouthLowerLipDepressR": {"え|R": 0.3},
}
# ARKit shapes per head part (the game's lip-sync / emotion data, Animation/SoundLip), as build_pt.py
ARKIT = {
    "head_eyeblinkleft": FACE["CTRL_expressions_eyeBlinkL"], "head_eyeblinkright": FACE["CTRL_expressions_eyeBlinkR"],
    "head_eyesquintleft": FACE["CTRL_expressions_eyeSquintInnerL"], "head_eyesquintright": FACE["CTRL_expressions_eyeSquintInnerR"],
    "head_eyewideleft": FACE["CTRL_expressions_eyeWidenL"], "head_eyewideright": FACE["CTRL_expressions_eyeWidenR"],
    "head_eyelookupleft": FACE["CTRL_expressions_eyeLookUpL"], "head_eyelookupright": FACE["CTRL_expressions_eyeLookUpR"],
    "head_eyelookdownleft": FACE["CTRL_expressions_eyeLookDownL"], "head_eyelookdownright": FACE["CTRL_expressions_eyeLookDownR"],
    "head_eyelookoutleft": FACE["CTRL_expressions_eyeLookLeftL"], "head_eyelookinleft": FACE["CTRL_expressions_eyeLookRightL"],
    "head_eyelookoutright": FACE["CTRL_expressions_eyeLookRightR"], "head_eyelookinright": FACE["CTRL_expressions_eyeLookLeftR"],
    "head_browdownleft": FACE["CTRL_expressions_browDownL"], "head_browdownright": FACE["CTRL_expressions_browDownR"],
    "head_browinnerup": {"困る": 1.0},
    "head_browouterupleft": FACE["CTRL_expressions_browRaiseOuterL"], "head_browouterupright": FACE["CTRL_expressions_browRaiseOuterR"],
    "head_cheeksquintleft": FACE["CTRL_expressions_eyeCheekRaiseL"], "head_cheeksquintright": FACE["CTRL_expressions_eyeCheekRaiseR"],
    "head_jawopen": FACE["CTRL_expressions_jawOpen"],
    "head_mouthsmileleft": FACE["CTRL_expressions_mouthCornerPullL"], "head_mouthsmileright": FACE["CTRL_expressions_mouthCornerPullR"],
    "head_mouthfrownleft": FACE["CTRL_expressions_mouthCornerDepressL"], "head_mouthfrownright": FACE["CTRL_expressions_mouthCornerDepressR"],
    "head_mouthstretchleft": FACE["CTRL_expressions_mouthStretchL"], "head_mouthstretchright": FACE["CTRL_expressions_mouthStretchR"],
    "head_mouthfunnel": {"お": 0.7}, "head_mouthpucker": {"う": 0.7},
    "head_mouthupperupleft": FACE["CTRL_expressions_mouthUpperLipRaiseL"], "head_mouthupperupright": FACE["CTRL_expressions_mouthUpperLipRaiseR"],
    "head_mouthlowerdownleft": FACE["CTRL_expressions_mouthLowerLipDepressL"], "head_mouthlowerdownright": FACE["CTRL_expressions_mouthLowerLipDepressR"],
}
FACE.update(ARKIT)
need_keys = set(k.split("|")[0] for m in FACE.values() for k in m if not k.startswith("_"))
face = k_meshes["Body"]
face_keys = set(k.name for k in face.data.shape_keys.key_blocks) if face.data.shape_keys else set()
REPORT["missing_face_keys"] = sorted(need_keys - face_keys)
assert not REPORT["missing_face_keys"], REPORT["missing_face_keys"]
EYE_ROWS = [[w for n, w in row if n in ("LeftEye", "RightEye")] for row in ROWS0["Body"]]
ROWS, DELTAS = {}, {}
for name, obj in k_meshes.items():
    rows, deltas = deform(obj, need_keys if name == "Body" else set())
    ROWS[name] = rows
    if deltas: DELTAS[name] = deltas
# Look morphs: the iris verts (weighted to the eye bones) slide in the face plane; translation keeps them in front of
# the flat anime eye whites (a rotation about the eye joint 4 cm behind would sink them at the sides).
_eyew = np.array([sum(w) for w in EYE_ROWS])
_fv = np.zeros((len(face.data.vertices), 3)); face.data.vertices.foreach_get("co", _fv.ravel())
LOOK = {"_LookUp": (0.0, 0.0, 0.35), "_LookDown": (0.0, 0.0, -0.35), "_LookLeft": (0.45, 0.0, 0.0), "_LookRight": (-0.45, 0.0, 0.0)}   # cm
for k, d in LOOK.items():
    DELTAS["Body"][k] = np.outer(_eyew, np.array(d))
_iris = _fv[_eyew > 0.5]
REPORT["look_morph"] = {"verts": int((_eyew > 0.01).sum()), "iris_extent_cm": [round(float(x), 2) for x in (_iris[_iris[:, 0] > 0].max(0) - _iris[_iris[:, 0] > 0].min(0))]}

# ---------------------------------------------------------------- weights -> Hun bones
SPINE = [V(n) for n in ("spine_01", "spine_02", "spine_03", "spine_04", "spine_05")]
def spine_split(p):
    z = p[2]
    zs = [NEW[n][2] for n in SPINE[1:]]
    w = [1.0]
    for zz in zs:
        w.append(smooth(z, zz - 3.0, zz + 3.0))
    out = {}
    for i, n in enumerate(SPINE):
        nxt = w[i + 1] if i + 1 < len(w) else 0.0
        out[n] = w[i] - nxt
    return out
def neck_split(p):
    z = p[2]; zm = NEW[V("neck_02")][2]
    t = smooth(z, zm - 2.0, zm + 2.0)
    return {V("neck_01"): 1 - t, V("neck_02"): t}

DIRECT = {k: v for k, v in INV.items() if not v.startswith(("eye_",))}
DIRECT["Hips"] = V("pelvis")
DIRECT["LeftEye"] = V("head"); DIRECT["RightEye"] = V("head")
def target_of(kname):
    b = KB[kname]
    while b is not None:
        if b.name in RENAME: return RENAME[b.name]
        if b.name in ("Spine", "Chest", "UpperChest"): return [("SPINE", 1.0)]
        if b.name == "Neck": return [("NECK", 1.0)]
        if b.name in DIRECT: return [(DIRECT[b.name], 1.0)]
        b = b.parent
    return [(V("pelvis"), 1.0)]

def remap(obj, rows):
    pos = np.array([list(v.co) for v in obj.data.vertices])
    acc_all = []
    for i, row in enumerate(rows):
        acc = collections.defaultdict(float)
        for n, w in row:
            for t, f in target_of(n):
                if t == "SPINE":
                    for b, ff in spine_split(pos[i]).items():
                        if ff > 0: acc[b] += w * f * ff
                elif t == "NECK":
                    for b, ff in neck_split(pos[i]).items():
                        if ff > 0: acc[b] += w * f * ff
                else:
                    acc[t] += w * f
        acc_all.append(top8(acc))
    write_groups(obj, acc_all)
    return acc_all
WROWS = {}
for name, obj in k_meshes.items():
    WROWS[name] = remap(obj, ROWS[name])
# the pig hanging on the right hip (on a skirt chain) stays with the pelvis
WROWS["pig2"] = [[(V("pelvis"), 1.0)] for _ in WROWS["pig2"]]
write_groups(k_meshes["pig2"], WROWS["pig2"])

def coords(name): return np.array([list(v.co) for v in k_meshes[name].data.vertices])
# Upper skirt on the skin weights of the tights / body under it (build_pbz.py skin_follow): the waistband would stay
# with the pelvis while the hips and thigh roots move through the upper panels.
def skin_follow(name, src_names, near, far, vmask):
    sp = coords(name)
    ids = np.where(vmask)[0]
    zz = sp[ids, 2]; ztop_, zbot_ = zz.max(), zz.min()
    bp = np.concatenate([coords(n) for n in src_names])
    brows = [r for n in src_names for r in WROWS[n]]
    n_skin = n_mix = 0
    for i in ids:
        hfac = 1.0 - float(smooth(ztop_ - sp[i, 2], 0.35 * (ztop_ - zbot_), 0.7 * (ztop_ - zbot_)))
        d = np.linalg.norm(bp - sp[i], axis=1)
        nn = np.argpartition(d, 8)[:8]
        b = (1.0 - float(smooth(d[nn].min(), near, far))) * hfac
        acc = collections.defaultdict(float)
        for n, w in WROWS[name][i]: acc[n] += (1.0 - b) * w
        iw = 1.0 / np.maximum(d[nn], 0.05); iw /= iw.sum()
        for j, wj in zip(nn, iw):
            for n, w in brows[j]: acc[n] += b * wj * w
        WROWS[name][i] = top8(acc)
        n_skin += b > 0.99; n_mix += 0.01 < b <= 0.99
    write_groups(k_meshes[name], WROWS[name])
    return {"verts": int(len(ids)), "skin": int(n_skin), "mixed": int(n_mix)}
RIB_LOW = {"sk.044", "sk.045", "sk.046"}   # the long ribbon below the skirt (its chain starts on the front-left pleats)
SKIRT_CHAIN = set(RENAME)
REPORT["skirt_skin_follow"] = skin_follow("skirt", ["leg", "skin"], 1.5 * SCALE, 5.0 * SCALE,
                                          (vfrac0("skirt", SKIRT_CHAIN) > 0.01) & (vfrac0("skirt", RIB_LOW) < 0.01))
# Back hair follows the torso (2026-11-03 round 4, user: "快速跑动时，大片头发依然会穿入外套"). The PMX back hair (64 cm,
# down to the hips) is weighted to the head alone, so whenever head and torso turn apart (the run's forward lean, the
# shoulder twist) its skinned place swings through the jacket by several cm, and the cloth's anim drive, max distance
# and backstop all hang on that place. Below the nape it now blends into the upper chest: head alone above neck_01,
# spine_05 alone below spine_05's joint. Rigid with the chest, not split over the spine by height: the hair rests on the
# upper back and hangs free below it, and a split put a kink into every strand at each spine joint whenever the run
# twisted the torso. The twin tails end above the shoulders and stay on the head.
def hair_follow(name):
    P = coords(name); zt, zb = float(NEW[V("neck_01")][2]), float(NEW[V("spine_05")][2])
    n_ = 0
    for i, p in enumerate(P):
        h = float(smooth(p[2], zb, zt))
        if h >= 1.0: continue
        acc = collections.defaultdict(float)
        for b, w in WROWS[name][i]: acc[b] += h * w
        acc[V("spine_05")] += 1.0 - h
        WROWS[name][i] = top8(acc); n_ += 1
    write_groups(k_meshes[name], WROWS[name])
    return {"verts": n_, "of": len(P), "z_head_above": round(zt, 1), "z_torso_below": round(zb, 1)}
REPORT["hair_follow"] = hair_follow("bhair")

# ---------------------------------------------------------------- armatures (vanilla orientations, new joints)
def make_armature(name, keep):
    a = v_arm.copy(); a.data = v_arm.data.copy(); a.name = name; a.data.name = name
    bpy.context.scene.collection.objects.link(a)
    bpy.ops.object.select_all(action="DESELECT")
    a.select_set(True); bpy.context.view_layer.objects.active = a
    bpy.ops.object.mode_set(mode="EDIT")
    eb = a.data.edit_bones
    keepset = set(keep)
    for b in list(eb):
        if b.name not in keepset:
            eb.remove(b)
    to_arm = a.matrix_world.inverted().to_3x3()
    for b in eb:
        d = Vector(NEW[b.name]) - Vector(VM[b.name].translation)
        d = to_arm @ d
        b.head = b.head + d; b.tail = b.tail + d
    bpy.ops.object.mode_set(mode="OBJECT")
    return a
def with_ancestors(names):
    out = set()
    for n in names:
        while n is not None and n not in out:
            out.add(n); n = VPAR[n]
    return [n for n in ORDER if n in out]

body_bones = with_ancestors(BODY_BONES + [b for b, _ in [x for r in RENAME.values() for x in r]])
head_bones = with_ancestors([V("head"), V("eye_l"), V("eye_r"), V("jaw")])
arm_body = make_armature("Armature", body_bones)
arm_head = make_armature("ArmatureHead", head_bones)
arm_lead = make_armature("ArmatureLeader", [n for n in ORDER if n not in EXTRA]) if VCFG["leader"] else None
arm_empty = make_armature("ArmatureEmpty", head_bones)
REPORT["bones"] = {"body": len(body_bones), "head": len(head_bones), "leader": len(ORDER) - len(EXTRA)}

import bmesh

# ---------------------------------------------------------------- cloth sections
# Every simulated part gets its own material slot (ue_cloth.py builds Chaos clothing per slot) and a geometric
# max-distance mask written to cloth.json:
#   MI_Lenko_SkirtCloth  pleated skirt, bound to the generated tube MI_Lenko_SkirtSim (simulated, not rendered)
#   MI_Lenko_Jacket      jacket below the belt + the pocket pigs (texture Lenko_JacketComb), bound to the generated open
#                        sheet MI_Lenko_JacketSim
#   MI_Lenko_Ribbon      the long ribbon on the left hip      MI_Lenko_HairBack  long back hair
#   MI_Lenko_HairTail    twin tails                           MI_Lenko_HairFront bangs and side locks (no colliders)
CLOTH = []
TEXF = {"Lenko_Body": "Lenko_Body_Base_color.png", "Lenko_Face": "Lenko_Face_Base_color.png", "Lenko_Eyes": "Lenko_eyes_Base_color.png",
        "Lenko_HairF": "Lenko_Fhair_Base_color.png", "Lenko_HairB": "Lenko_Bhair_Base_color.png", "Lenko_Cloth": "Lenko_Cloth_Base_color.png",
        "Lenko_Skirt": "Lenko_Skirt_Base_color.png", "Lenko_Coat": "Lenko_Coat_Base_color.png", "Lenko_Pig": "Lenko_Pig_Base_color.png",
        "Lenko_Leg": "Lenko_Leg_Base_color.png"}
texdir = os.path.join(RUN, "textures"); os.makedirs(texdir, exist_ok=True)
def chain_set(*heads):
    out = set()
    for h in heads: out |= set(chain_of(h))
    return out
def vfrac(name, bones):
    return np.array([sum(w for n, w in row if n in bones) / max(sum(w for _, w in row), 1e-9) for row in ROWS[name]])
def fmask(name, bones, thr=0.5):
    f = vfrac(name, bones)
    return np.array([float(np.mean(f[list(p.vertices)])) > thr for p in k_meshes[name].data.polygons])
def new_mat(src_, name):
    m = src_.copy() if src_ else bpy.data.materials.new(name)
    m.name = name
    return m
def set_slot(obj, mat, face_mask):
    me = obj.data
    me.materials.append(mat)
    idx = len(me.materials) - 1
    n = 0
    for f in me.polygons:
        if face_mask[f.index]: f.material_index = idx; n += 1
    return n
def image_px(fn):
    img = bpy.data.images.load(os.path.join(TEXSRC, fn))
    w, h = img.size
    a = np.zeros(w * h * 4, dtype=np.float32); img.pixels.foreach_get(a)
    bpy.data.images.remove(img)
    return a.reshape(h, w, 4)
def uv_islands(obj, mask):
    me = obj.data; uv = me.uv_layers[0].data
    faces = [p for p in me.polygons if mask[p.index]]
    par = {p.index: p.index for p in faces}
    def find(a):
        while par[a] != a: par[a] = par[par[a]]; a = par[a]
        return a
    seen = {}
    for p in faces:
        for l in p.loop_indices:
            k = (me.loops[l].vertex_index, round(uv[l].uv[0], 5), round(uv[l].uv[1], 5))
            if k in seen: par[find(p.index)] = find(seen[k])
            else: seen[k] = p.index
    out = collections.defaultdict(list)
    for p in faces: out[find(p.index)].extend(p.loop_indices)
    return list(out.values())
def combine_texture(name, parts, pad=6, limit=4096):
    """parts: [(object, face mask, source texture file)]. Crops every UV island of the masked faces from its texture,
    packs the crops in shelves on a new power-of-two texture and moves the islands' UVs onto it (build_pt.py)."""
    rects = []
    for obj, mask, fn in parts:
        px = image_px(fn); H, W = px.shape[:2]
        uv = obj.data.uv_layers[0].data
        for loops in uv_islands(obj, mask):
            a = np.array([uv[l].uv for l in loops])
            x0, y0 = np.floor(a.min(0) * (W, H)).astype(int) - pad
            x1, y1 = np.ceil(a.max(0) * (W, H)).astype(int) + pad
            x0, y0, x1, y1 = max(x0, 0), max(y0, 0), min(x1, W), min(y1, H)
            rects.append((px[y0:y1, x0:x1], obj, loops, W, H, x0, y0))
        del px
    area = sum(r[0].shape[0] * r[0].shape[1] for r in rects)
    for s in (1, 2, 4):
        cw = 1 << int(math.ceil(math.log2(max(math.sqrt(area) / s * 1.15, max(r[0].shape[1] for r in rects) / s))))
        x = y = rowh = 0; place_ = []
        for r in sorted(rects, key=lambda r: -r[0].shape[0]):
            h, w = r[0].shape[0] // s, r[0].shape[1] // s
            if x + w > cw: x, y, rowh = 0, y + rowh, 0
            place_.append((r, x, y)); x += w; rowh = max(rowh, h)
        ch = 1 << int(math.ceil(math.log2(max(y + rowh, 1))))
        if cw <= limit and ch <= limit: break
    canvas = np.zeros((ch, cw, 4), dtype=np.float32)
    canvas[:] = np.concatenate([r[0].reshape(-1, 4) for r in rects]).mean(0)
    for (c, obj, loops, W, H, x0, y0), x, y in place_:
        cs = c[:c.shape[0] // s * s, :c.shape[1] // s * s].reshape(c.shape[0] // s, s, c.shape[1] // s, s, 4).mean((1, 3))
        canvas[y:y + cs.shape[0], x:x + cs.shape[1]] = cs
        uv = obj.data.uv_layers[0].data
        for l in loops:
            u, v = uv[l].uv
            uv[l].uv = ((x + (u * W - x0) / s) / cw, (y + (v * H - y0) / s) / ch)
    img = bpy.data.images.new(name, cw, ch, alpha=True)
    img.pixels.foreach_set(canvas.ravel())
    img.filepath_raw = os.path.join(texdir, name + ".png"); img.file_format = "PNG"; img.save()
    return {"size": [cw, ch], "downscale": s, "islands": len(rects), "fill": round(area / s / s / (cw * ch), 2)}
def anchors_for(name, mask, bones, root_pts):
    """Fixed points of a directly simulated section: its verts mostly on non-chain bones (strand roots on the head),
    the verts it shares with the skinned rest, and for a loose piece with neither its vertex nearest a chain root."""
    obj = k_meshes[name]; co = coords(name); f = vfrac(name, bones)
    vin, vout = set(), set()
    for p in obj.data.polygons:
        (vin if mask[p.index] else vout).update(p.vertices)
    fixed = {v for v in vin if f[v] < 0.35} | (vin & vout)
    extra = 0
    for comp in components(obj, mask):
        if comp & fixed: continue
        cl = np.array(sorted(comp))
        d = np.min(np.linalg.norm(co[cl][:, None, :] - root_pts[None, :, :], axis=2), axis=1)
        fixed.add(int(cl[np.argmin(d)])); extra += 1
    fixed = sorted(fixed)
    reach = max(float(np.min(np.linalg.norm(co[fixed][:, None, :] - co[v][None, None, :], axis=2))) for v in sorted(vin)) if fixed else 0.0
    return co[fixed], reach, {"anchors": len(fixed), "loose_pieces": extra, "verts": len(vin), "reach": round(reach, 2)}
def far(anchors, pts):
    return float(max(np.linalg.norm(anchors - p, axis=1).min() for p in pts)) if len(anchors) and len(pts) else 0.0
def rootp(k): return apply(region(k), kp(k))
def chain_len(h):
    kn = chain_of(h)
    pts = [apply(region(k), kp(k)) for k in kn] + [apply(region(kn[-1]), ktail(kn[-1]))]
    return float(sum(np.linalg.norm(pts[i + 1] - pts[i]) for i in range(len(pts) - 1)))

def shell(name, P, W, axis, ncol, nrow, closed, win_deg, z_top=None, min_span=0.6):
    """Smooth simulation surface over a section's render verts P (rows of W = their weight rows): columns at ncol
    azimuths around the vertical axis, nrow rows from the top (z_top or the column's highest vert) to the column's
    hem; radius = outermost render vert near each grid point, smoothed. closed: a tube; else an open sheet over the
    columns the section covers (at least min_span of its height). Weights: inverse-distance mean of the 6 nearest
    render verts (build_pbz.py skirt_shell)."""
    r = np.hypot(P[:, 0] - axis[0], P[:, 1] - axis[1])
    th = np.arctan2(P[:, 0] - axis[0], -(P[:, 1] - axis[1]))
    cols = -math.pi + (np.arange(ncol) + 0.5) * 2.0 * math.pi / ncol
    zmin_all, zmax_all = P[:, 2].min(), P[:, 2].max()
    ztop = np.full(ncol, np.nan); zbot = np.full(ncol, np.nan); WIN = np.zeros(ncol)
    for j, a in enumerate(cols):
        for grow in ((1.0, 2.0, 3.0) if closed else (1.0,)):   # a closed tube widens the window over a gap
            win = math.radians(win_deg * grow)
            m = np.abs((th - a + math.pi) % (2 * math.pi) - math.pi) < win
            if m.sum() >= 4: break
        if m.sum() < 4: continue
        zt = z_top if z_top is not None else P[m, 2].max()
        zb_ = P[m, 2].min()
        if closed or (zt - zb_) >= min_span * (zmax_all - zmin_all if z_top is None else z_top - zmin_all):
            ztop[j], zbot[j], WIN[j] = zt, zb_ - 0.3, win
    have = ~np.isnan(ztop)
    if closed: assert have.all(), "shell %s: empty columns %s" % (name, np.where(~have)[0].tolist())
    R = np.full((nrow, ncol), np.nan); Z = np.full((nrow, ncol), np.nan)
    for j in np.where(have)[0]:
        a = cols[j]
        mj = np.abs((th - a + math.pi) % (2 * math.pi) - math.pi) < WIN[j]
        dz = (ztop[j] - zbot[j]) / (nrow - 1)
        for k in range(nrow):
            z = ztop[j] + (zbot[j] - ztop[j]) * k / (nrow - 1)
            Z[k, j] = z
            m = mj & (np.abs(P[:, 2] - z) < max(0.75 * dz, 0.8))
            if m.any(): R[k, j] = r[m].max()
        col = R[:, j]; ok = ~np.isnan(col)
        if ok.sum() == 0: have[j] = False; continue
        R[:, j] = np.interp(np.arange(nrow), np.where(ok)[0], col[ok])
    def nb(j, s):
        jj = j + s
        if closed: jj %= ncol
        return jj if 0 <= jj < ncol and have[jj] else None
    for _ in range(2):   # 1-2-1 across columns, then down the rows
        R2 = R.copy()
        for j in np.where(have)[0]:
            a_, b_ = nb(j, -1), nb(j, 1)
            R2[:, j] = (R[:, a_ if a_ is not None else j] + 2.0 * R[:, j] + R[:, b_ if b_ is not None else j]) / 4.0
        R = R2
        R[1:-1] = (R[:-2] + 2.0 * R[1:-1] + R[2:]) / 4.0
    Vx, idx = [], {}
    for j in np.where(have)[0]:
        for k in range(nrow):
            idx[(k, j)] = len(Vx)
            Vx.append([axis[0] + R[k, j] * math.sin(cols[j]), axis[1] - R[k, j] * math.cos(cols[j]), Z[k, j]])
    F = []
    for j in np.where(have)[0]:
        j2 = nb(j, 1)
        if j2 is None: continue
        for k in range(nrow - 1):
            F.append((idx[(k, j)], idx[(k, j2)], idx[(k + 1, j2)], idx[(k + 1, j)]))
    me = bpy.data.meshes.new(name)
    me.from_pydata(Vx, [], F); me.update()
    out = float(np.mean([np.dot(np.array(f.normal), norm(np.array([*(np.array(f.center)[:2] - axis), 0.0]))) for f in me.polygons]))
    if out < 0.0:   # faces must face away from the axis (backstop and binding normals)
        me.clear_geometry(); me.from_pydata(Vx, [], [tuple(reversed(f)) for f in F]); me.update()
    for f in me.polygons: f.use_smooth = True
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    me.uv_layers.new(name="UVMap")
    Va = np.array(Vx)
    wrows = []
    for p in Va:
        d = np.linalg.norm(P - p, axis=1)
        nn = np.argpartition(d, 6)[:6]
        iw = 1.0 / np.maximum(d[nn], 0.05); iw /= iw.sum()
        acc = collections.defaultdict(float)
        for j_, wj in zip(nn, iw):
            for n, w in W[j_]: acc[n] += wj * w
        wrows.append(top8(acc))
    write_groups(ob, wrows)
    return ob, wrows, {"verts": len(Vx), "faces": len(F), "columns": int(have.sum()), "rows": nrow, "flipped": out < 0.0,
                       "height": [round(float(np.nanmin(Z)), 2), round(float(np.nanmax(Z)), 2)]}

# weight fractions, slot masks and distance to the arm axes (hair colliders, hair backstop)
def _frac(rows, pred): return np.array([sum(w for n, w in r if pred(n)) / max(sum(w for _, w in r), 1e-9) for r in rows])
_ARMPRE = ("upperarm", "lowerarm", "hand", "thumb", "index", "middle", "ring", "pinky")
def _not_slot(n, slot):
    o_ = k_meshes[n]; idx_ = [i for i, m in enumerate(o_.data.materials) if m and m.name == slot]
    m_ = np.ones(len(o_.data.vertices), bool)
    for p in o_.data.polygons:
        if p.material_index in idx_: m_[list(p.vertices)] = False
    return m_
def _segd(P, a, b):
    d = b - a; t = np.clip(((P - a) @ d) / max(float(d @ d), 1e-9), 0, 1)
    return np.linalg.norm(P - (a + np.outer(t, d)), axis=1)
def _arm_d(P):
    """Distance to the nearest arm axis (upper arm, forearm, hand + fingers), on the arm mesh (shoulder offsets)."""
    d = np.full(len(P), 1e9)
    for s in "lr":
        ua, la, ha = V(f"upperarm_{s}"), V(f"lowerarm_{s}"), V(f"hand_{s}")
        a0, a1, a2 = NEW[ua] + OFS.get(ua, 0.0), NEW[la] + OFS.get(la, 0.0), NEW[ha]
        d = np.minimum(d, np.minimum(np.minimum(_segd(P, a0, a1), _segd(P, a1, a2)), _segd(P, a2, a2 + 0.8 * (a2 - a1))))
    return d

if VCFG["cloth"]:
    # ---- skirt: pleats (Lenko_Skirt / Lenko_Skirt_h faces on the skirt chains), the long ribbon is its own section
    sko_ = k_meshes["skirt"]
    skirt_src = sko_.data.materials[0]
    # the ribbon: Lenko_Skirt_h pieces on the "sk" chain that reach its lower bones (sk.044-046); the chain's upper
    # bones also carry the front-left pleats (Lenko_Skirt), which stay with the skirt
    _sh = [m.name for m in sko_.data.materials].index("Lenko_Skirt_h")
    RIBB = set(chain_of("sk"))
    _low = vfrac("skirt", RIB_LOW)
    rib_comp = set()
    for comp in components(sko_, fmask("skirt", RIBB, 0.5) & np.array([p.material_index == _sh for p in sko_.data.polygons])):
        if any(_low[v] > 0.5 for v in comp): rib_comp |= comp
    m_rib = np.array([p.material_index == _sh and all(v in rib_comp for v in p.vertices) for p in sko_.data.polygons])
    m_sk = fmask("skirt", SKIRT_CHAIN, 0.5) & ~m_rib
    REPORT["cloth_faces"] = {"skirt": set_slot(sko_, new_mat(skirt_src, "MI_Lenko_SkirtCloth"), m_sk),
                             "ribbon": set_slot(sko_, new_mat(skirt_src, "MI_Lenko_Ribbon"), m_rib)}
    # ---- jacket below the belt (+ pocket pigs): faces wholly under the belt's lower edge, not on the arms
    co_ = k_meshes["coat"]
    zcut = float(apply(region("Chest"), np.array(G @ Vector((0.0, 0.0, ZB))))[2])   # the jacket's chains hang from the chest
    cz = coords("coat")[:, 2]
    arm_c = vfrac("coat", ARMB)
    m_jk = np.array([float(cz[list(p.vertices)].max()) < zcut and float(arm_c[list(p.vertices)].mean()) < 0.5 for p in co_.data.polygons])
    pg = k_meshes["pig"]
    m_pg = np.ones(len(pg.data.polygons), dtype=bool)
    REPORT["jacket_texture"] = combine_texture("Lenko_JacketComb", [(co_, m_jk, TEXF["Lenko_Coat"]), (pg, m_pg, TEXF["Lenko_Pig"])])
    jk_mat = new_mat(co_.data.materials[0], "MI_Lenko_Jacket")
    REPORT["cloth_faces"]["jacket"] = set_slot(co_, jk_mat, m_jk)
    REPORT["cloth_faces"]["pocket_pigs"] = set_slot(pg, jk_mat, m_pg)
    REPORT["jacket_cut_cm"] = round(zcut, 2)
    # ---- hair
    fh, bh = k_meshes["fhair"], k_meshes["bhair"]
    TAILS = chain_set("hair.009", "hair.013")
    BACK = chain_set("hair.040", "hair.046", "hair.052", "hair.058")
    FRONTS = chain_set("hair.017", "hair.020", "hair.023", "hair.026", "hair.029", "hair.032", "hair.036")
    m_tail = fmask("fhair", TAILS)
    vf_front = vfrac("fhair", FRONTS)
    m_front = np.array([not m_tail[p.index] and float(vf_front[list(p.vertices)].max()) > 0.02 for p in fh.data.polygons])
    m_back = fmask("bhair", BACK)
    REPORT["cloth_faces"]["hairtail"] = set_slot(fh, new_mat(fh.data.materials[0], "MI_Lenko_HairTail"), m_tail)
    REPORT["cloth_faces"]["hairfront"] = set_slot(fh, new_mat(fh.data.materials[0], "MI_Lenko_HairFront"), m_front)
    REPORT["cloth_faces"]["hairback"] = set_slot(bh, new_mat(bh.data.materials[0], "MI_Lenko_HairBack"), m_back)
    # ---- chest (2026-11-03, user: "胸部也要添加一些物理，不需要太大的幅度"): the top's faces within CHEST_R of each breast
    # apex (frontmost top vertex per side between spine_04 and the neck) are a soft section on a copy of their outer
    # layer. Pinned: the patch boundary and every top vertex within 1.2 cm of other clothing (the tie lies on the chest,
    # the jacket's front edges) so nothing slides through them; free range grows to CHEST_MAX at the apex, a backstop
    # keeps it from sinking in (no skin within 4 cm under the top there).
    from mathutils.kdtree import KDTree
    CHEST_R, CHEST_MAX = 6.5, 3.0   # max 1.2 until round 3 ("胸部的物理也几乎不可见")
    clo = k_meshes["cloth"]; ccc = coords("cloth")
    z_lo_c, z_hi_c = float(NEW[V("spine_04")][2]), float(NEW[V("neck_01")][2]) - 3.0
    apex = []
    for sx in (1.0, -1.0):
        m_ = (ccc[:, 0] * sx > 2.0) & (ccc[:, 0] * sx < 14.0) & (ccc[:, 2] > z_lo_c) & (ccc[:, 2] < z_hi_c)
        apex.append(ccc[m_][int(np.argmin(ccc[m_, 1]))])
    apex = np.array(apex)
    _dap = np.min(np.linalg.norm(ccc[:, None, :] - apex[None, :, :], axis=2), axis=1)
    m_chest = np.array([float(_dap[list(p.vertices)].max()) < CHEST_R for p in clo.data.polygons])
    REPORT["cloth_faces"]["chest"] = set_slot(clo, new_mat(clo.data.materials[0], "MI_Lenko_Chest"), m_chest)
    _vin, _vout = set(), set()
    for p in clo.data.polygons: (_vin if m_chest[p.index] else _vout).update(p.vertices)
    _others = np.concatenate([coords(n) for n in ("skirt", "armband", "coat", "pig2")])
    _kd = KDTree(len(_others))
    for j, p in enumerate(_others): _kd.insert(p, j)
    _kd.balance()
    _touch = {v for v in _vin if _kd.find(ccc[v])[2] < 1.2}
    a_chest_v = sorted((_vin & _vout) | _touch)
    a_chest = ccc[a_chest_v]
    REPORT["chest"] = {"apex": [[round(float(x), 2) for x in ue(a)] for a in apex], "radius": CHEST_R, "max_distance": CHEST_MAX,
                       "faces": int(m_chest.sum()), "anchors": len(a_chest_v), "anchors_touching_clothing": len(_touch),
                       "free_reach": round(far(a_chest, ccc[sorted(_vin)]), 2)}

    a_tail, r_tail, REPORT.setdefault("cloth_fixed", {})["hairtail"] = anchors_for("fhair", m_tail, TAILS, np.array([rootp("hair.009"), rootp("hair.013")]))
    a_front, r_front, REPORT["cloth_fixed"]["hairfront"] = anchors_for("fhair", m_front, FRONTS, np.array([rootp(h) for h in ("hair.017", "hair.020", "hair.023", "hair.026", "hair.029", "hair.032", "hair.036")]))
    a_back, r_back, REPORT["cloth_fixed"]["hairback"] = anchors_for("bhair", m_back, BACK, np.array([rootp(h) for h in ("hair.040", "hair.046", "hair.052", "hair.058")]))
    a_rib, r_rib, REPORT["cloth_fixed"]["ribbon"] = anchors_for("skirt", m_rib, {"sk.044", "sk.045", "sk.046"}, np.array([rootp("sk.045")]))
    # Layered pieces: half the hair pieces are inner sheets lying on a strand (within 0.6 cm), the ribbon is two equal
    # layers plus trim strips. Simulated on their own each would swing on its own anchor (a trim strip pinned at one
    # vertex would hang off the ribbon), so each section simulates a copy of its outer pieces only (sim_slot) and the
    # whole render section is bound to it.
    from mathutils.kdtree import KDTree
    def sim_copy(name, mask, slot):
        obj = k_meshes[name]; co = coords(name)
        pieces = sorted(components(obj, mask), key=lambda c: (-len(c), min(c)))
        kept, kv = [], []
        for c in pieces:
            if kv:
                kd = KDTree(len(kv))
                for j, v in enumerate(kv): kd.insert(co[v], j)
                kd.balance()
                if np.mean([kd.find(co[v])[2] < 0.6 for v in c]) > 0.9: continue
            kept.append(c); kv.extend(sorted(c))
        keep = set(kv)
        vidx = {v: i for i, v in enumerate(sorted(keep))}
        F = [tuple(vidx[v] for v in p.vertices) for p in obj.data.polygons if mask[p.index] and all(v in keep for v in p.vertices)]
        me = bpy.data.meshes.new(slot)
        me.from_pydata([co[v].tolist() for v in sorted(keep)], [], F); me.update()
        ob = bpy.data.objects.new(slot, me); bpy.context.scene.collection.objects.link(ob)
        me.uv_layers.new(name="UVMap")
        me.materials.append(new_mat(None, slot))
        write_groups(ob, [WROWS[name][v] for v in sorted(keep)])
        k_meshes[slot] = ob
        return {"pieces": len(pieces), "simulated": len(kept), "sim_verts": len(keep)}
    REPORT["cloth_sim_copies"] = {
        "ribbon": sim_copy("skirt", m_rib, "MI_Lenko_RibbonSim"),
        "hairtail": sim_copy("fhair", m_tail, "MI_Lenko_HairTailSim"),
        "hairfront": sim_copy("fhair", m_front, "MI_Lenko_HairFrontSim"),
        "hairback": sim_copy("bhair", m_back, "MI_Lenko_HairBackSim"),
        "chest": sim_copy("cloth", m_chest, "MI_Lenko_ChestSim")}
    lt = (chain_len("hair.009") + chain_len("hair.013")) / 2.0
    lb = np.mean([chain_len(h) for h in ("hair.040", "hair.046", "hair.052", "hair.058")])
    ls = (chain_len("hair.026") + chain_len("hair.029")) / 2.0

    # ---- simulation shells
    # the tube over the pleats only (the strap loop and the ribbon would pull its hem down; they bind to it anyway)
    skc = coords("skirt"); _inside = {v for p in sko_.data.polygons if m_sk[p.index] for v in p.vertices}
    sk_v = sorted(set(PLEAT_V) & _inside)
    sk_axis = np.array([0.0, float(skc[sk_v, 1].mean())])
    sk_sh, _, REPORT["skirt_sim"] = shell("skirt_sim", skc[sk_v], [WROWS["skirt"][v] for v in sk_v], sk_axis, 32, 12, True, 12.0)
    jv = sorted({v for p in co_.data.polygons if m_jk[p.index] for v in p.vertices})
    jk_sh, _, REPORT["jacket_sim"] = shell("jacket_sim", coords("coat")[jv], [WROWS["coat"][v] for v in jv], sk_axis, 48, 10, False,
                                           7.5, z_top=zcut + 0.3)
    for ob, slot, alias in ((sk_sh, "MI_Lenko_SkirtSim", None), (jk_sh, "MI_Lenko_JacketSim", None)):
        ob.data.materials.append(new_mat(None, slot))
        k_meshes[ob.name] = ob
    # clearance between the skirt shell and the jacket's render surface above the skirt hem (sides / back)
    jkp = coords("coat")[jv]
    shv = np.array([list(v.co) for v in sk_sh.data.vertices])
    def cyl(p): return np.hypot(p[:, 0] - sk_axis[0], p[:, 1] - sk_axis[1]), np.degrees(np.arctan2(p[:, 0] - sk_axis[0], -(p[:, 1] - sk_axis[1])))
    rs, as_ = cyl(shv); rj, aj = cyl(jkp)
    gaps = []
    for i in range(len(shv)):
        m = (np.abs(jkp[:, 2] - shv[i, 2]) < 1.5) & (np.abs((aj - as_[i] + 180) % 360 - 180) < 6)
        if m.any(): gaps.append(float(rj[m].min() - rs[i]))
    REPORT["jacket_minus_skirt_radius_cm"] = [round(float(np.percentile(gaps, q)), 2) for q in (5, 25, 50)] if gaps else None
    jk_h = REPORT["jacket_sim"]["height"]; jh = jk_h[1] - jk_h[0]
    sk_h = REPORT["skirt_sim"]["height"]; sh = sk_h[1] - sk_h[0]

    # UE 5.7 maps both values exponentially (PBDStiffness.h: (1000^v - 1) / 999 at 120 Hz): stiffness 0.3 pulls ~1.4% of
    # the gap to the animation per frame; damping 0.6 removes ~12% of the velocity difference to the animation per frame
    def drive(k, d=0.6): return {"AnimDriveStiffness": {"Low": k, "High": k}, "AnimDriveDamping": {"Low": d, "High": d}}
    JACKET_TH = 2.0
    def inertia(s): return {"LinearVelocityScale": {"X": s, "Y": s, "Z": s}, "AngularVelocityScale": s}
    def pts(a): return [[round(float(x), 3) for x in ue(p)] for p in a]
    axis_ue = [round(float(sk_axis[0]), 3), round(float(-sk_axis[1]), 3), 0.0]
    gap_lo = max(REPORT["jacket_minus_skirt_radius_cm"][1], 1.0) if REPORT["jacket_minus_skirt_radius_cm"] else 2.0
    # back hair / twin tails backstop (round 4, user: "头发整体的物理效果又显得有点硬了"): a particle may move inward of its
    # skinned place by the gap to the body under it (ray along its outward normal to the torso surface: skin, top, skirt,
    # tights, jacket, pigs; arms and ribbon out) less HAIR_BS_MARGIN, at most HAIR_BS_CAP (keeps the fanned-out rest
    # shape from sagging onto the back). Rounds 2/3 allowed 0 everywhere: the hair only ever swung outward of its rest
    # shape and stopped dead on the way back. The collar flap ledge (which the shell colliders cannot follow) still holds
    # it: the gap there is small. The sim cards are wound to face outward (the copies are not rendered; the plugin
    # orients all normals by one sign, so inward-wound cards had no backstop). Per particle: mask "backstop.per_vertex".
    from mathutils.bvhtree import BVHTree
    HAIR_BS_MARGIN, HAIR_BS_CAP = 1.2, 5.0
    _tv, _tp = [], []
    for n_ in ("skin", "cloth", "skirt", "leg", "coat", "pig", "pig2"):
        c_ = coords(n_); ok_ = (_arm_d(c_) > 7.0) & _not_slot(n_, "MI_Lenko_Ribbon")
        base_ = len(_tv); _tv.extend(c_.tolist())
        _tp.extend([[base_ + v for v in p.vertices] for p in k_meshes[n_].data.polygons if all(ok_[v] for v in p.vertices)])
    _bvh = BVHTree.FromPolygons(_tv, _tp)
    def hair_backstop(slot, min_dot):
        ob = k_meshes[slot]; me = ob.data
        P = np.array([list(v.co) for v in me.vertices])
        out_ = np.c_[P[:, 0] - sk_axis[0], P[:, 1] - sk_axis[1], np.zeros(len(P))]
        out_ /= np.maximum(np.linalg.norm(out_, axis=1, keepdims=True), 1e-9)
        vc = {}
        for ci, comp in enumerate(components(ob, np.ones(len(me.polygons), bool))):
            for v in comp: vc[v] = ci
        score = collections.defaultdict(float)
        for p in me.polygons: score[vc[p.vertices[0]]] += p.area * float(np.dot(np.array(p.normal), out_[list(p.vertices)].mean(0)))
        flip = [p.index for p in me.polygons if score[vc[p.vertices[0]]] < 0.0]
        if flip:
            bm = bmesh.new(); bm.from_mesh(me); bm.faces.ensure_lookup_table()
            bmesh.ops.reverse_faces(bm, faces=[bm.faces[i] for i in flip])
            bm.to_mesh(me); bm.free(); me.update()
        N = np.zeros_like(P)
        for p in me.polygons:
            for v in p.vertices: N[v] += p.area * np.array(p.normal)
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
        D = np.full(len(P), HAIR_BS_CAP); hit = 0
        for i in range(len(P)):
            loc, _, _, dist = _bvh.ray_cast(Vector(P[i].tolist()), Vector((-N[i]).tolist()), 60.0)
            if loc is not None: D[i] = float(np.clip(dist - HAIR_BS_MARGIN, 0.0, HAIR_BS_CAP)); hit += 1
        on = (N * out_).sum(1) > min_dot
        REPORT.setdefault("hair_backstop", {})[slot] = {
            "cards": len(set(vc.values())), "cards_flipped": len({vc[me.polygons[i].vertices[0]] for i in flip}),
            "verts": len(P), "facing_out": int(on.sum()), "ray_hits": hit,
            "dist_cm_p10_50_90": [round(float(np.percentile(D[on], q)), 2) for q in (10, 50, 90)] if on.any() else None,
            "at_zero": int((D[on] <= 0.0).sum()), "at_cap": int((D[on] >= HAIR_BS_CAP).sum())}
        return {"distance": 0.0, "radius": 50.0, "axis": axis_ue, "min_dot": min_dot,
                "per_vertex": [[round(float(x), 3) for x in ue(P[i])] + [round(float(D[i]), 2)] for i in range(len(P))]}
    CLOTH = [
        # skirt: waistband fixed, free range grows to the hem; it sits under the jacket at the sides and back, so its
        # free range stays near the gap between the two (cloth assets do not collide with each other)
        {"slot": "MI_Lenko_SkirtCloth", "name": "Lenko_Skirt", "max_distance": round(float(np.clip(1.5 * gap_lo, 2.5, 0.35 * sh)), 2),
         "mask": {"type": "plane", "anchors": [[0.0, 0.0, round(sk_h[1], 3)]], "dir": [0, 0, -1], "d0": round(0.1 * sh, 2), "d1": round(0.7 * sh, 2),
                  "sim_slot": "MI_Lenko_SkirtSim", "backstop": {"distance": 0.0, "radius": 50.0, "axis": axis_ue, "min_dot": 0.3}},
         "config": {"DampingCoefficient": 0.08, "FrictionCoefficient": 0.2, "CollisionThickness": 2.0, "GravityScale": 0.5,
                    "bUseCCD": True, "bUseLegacyBackstop": False} | inertia(0.8) | drive(0.35)},
        # jacket hem: fixed at the belt, swings outward (backstop), the legs push it through the colliders
        # 2026-11-03 round 3 (user: the jacket hem and what hangs on it showed almost no physics): drive damping 0.6
        # (about 12% of the velocity difference to the animation removed per frame: no lag, no swing) -> 0.15, full
        # inertia, more of the panel free and more range, more weight; own collision asset with the thigh capsules so the
        # legs push the hem (cloth_collision_jacket.json, radius kept clear of the rest shape)
        {"slot": "MI_Lenko_Jacket", "name": "Lenko_Jacket", "max_distance": round(0.45 * jh, 2), "collision": "jacket",
         "mask": {"type": "plane", "anchors": [[0.0, 0.0, round(jk_h[1], 3)]], "dir": [0, 0, -1], "d0": 1.0, "d1": round(0.5 * jh, 2),
                  "sim_slot": "MI_Lenko_JacketSim", "backstop": {"distance": 0.0, "radius": 50.0, "axis": axis_ue, "min_dot": 0.3}},
         "config": {"DampingCoefficient": 0.04, "FrictionCoefficient": 0.2, "CollisionThickness": JACKET_TH, "GravityScale": 0.8,
                    "bUseCCD": True, "bUseLegacyBackstop": False} | inertia(1.0) | drive(0.25, 0.15)},
        {"slot": "MI_Lenko_Ribbon", "name": "Lenko_Ribbon", "max_distance": round(0.35 * r_rib, 2),
         "mask": {"type": "radial", "anchors": pts(a_rib), "d0": 1.0, "d1": round(max(0.9 * r_rib, 3.0), 2), "sim_slot": "MI_Lenko_RibbonSim"},
         "config": {"DampingCoefficient": 0.05, "FrictionCoefficient": 0.1, "CollisionThickness": 1.0, "GravityScale": 0.6}
                   | inertia(1.0) | drive(0.15)},
        # long back hair and twin tails collide with the hair asset (jacket / collar outer surface, sleeves, forearms,
        # cloth_collision_hair.json; its shapes clear the rest hair by the thickness). Round 4 ("头发整体的物理效果又显得有点
        # 硬了"): drive damping 0.6 -> 0.1 (12% -> 0.2% of the velocity difference to the animation per frame: the hair
        # now lags and swings instead of moving with the head like a helmet), the backstop per particle (above), CCD
        # (fast runs tunnelled through the thin shell capsules), back hair thickness 1.0 -> 1.5 (its inner layer cards lie
        # up to 0.6 cm under the simulated ones), a little more weight
        {"slot": "MI_Lenko_HairBack", "name": "Lenko_HairBack", "max_distance": round(0.35 * lb, 2), "collision": "hair",
         "mask": {"type": "radial", "anchors": pts(a_back), "d0": 0.5, "d1": round(max(0.9 * r_back, 3.0), 2), "sim_slot": "MI_Lenko_HairBackSim",
                  "backstop": hair_backstop("MI_Lenko_HairBackSim", 0.2)},
         "config": {"DampingCoefficient": 0.04, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.7,
                    "bUseCCD": True, "bUseLegacyBackstop": False} | inertia(1.0) | drive(0.2, 0.1)},
        {"slot": "MI_Lenko_HairTail", "name": "Lenko_HairTails", "max_distance": round(0.45 * lt, 2), "collision": "hair",
         "mask": {"type": "radial", "anchors": pts(a_tail), "d0": 0.5, "d1": round(max(0.9 * r_tail, 3.0), 2), "sim_slot": "MI_Lenko_HairTailSim",
                  "backstop": hair_backstop("MI_Lenko_HairTailSim", 0.2)},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.1, "CollisionThickness": 1.5, "GravityScale": 0.6,
                    "bUseCCD": True, "bUseLegacyBackstop": False} | inertia(1.0) | drive(0.15, 0.1)},
        # chest: small soft jiggle (pinned ring and contacts, CHEST_MAX at the apex), springs back fast, hardly sags
        {"slot": "MI_Lenko_Chest", "name": "Lenko_Chest", "max_distance": CHEST_MAX, "collide": False,
         "mask": {"type": "radial", "anchors": pts(a_chest), "d0": 0.3, "d1": round(0.55 * CHEST_R, 2), "sim_slot": "MI_Lenko_ChestSim",
                  "backstop": {"distance": 0.0, "radius": 50.0, "axis": [0.0, round(float(-np.mean(apex[:, 1]) - 8.0), 2), 0.0], "min_dot": 0.3}},
         "config": {"DampingCoefficient": 0.03, "FrictionCoefficient": 0.0, "CollisionThickness": 0.5, "GravityScale": 0.1}
                   | inertia(1.0) | drive(0.45, 0.25)},
        {"slot": "MI_Lenko_HairFront", "name": "Lenko_HairFront", "max_distance": round(0.4 * ls, 2), "collide": False,
         "mask": {"type": "radial", "anchors": pts(a_front), "d0": 0.5, "d1": round(max(0.85 * r_front, 3.0), 2), "sim_slot": "MI_Lenko_HairFrontSim"},
         "config": {"DampingCoefficient": 0.05, "FrictionCoefficient": 0.1, "CollisionThickness": 0.5, "GravityScale": 0.3}
                   | inertia(1.0) | drive(0.2, 0.25)},   # bangs: damping 0.6 -> 0.25 (round 4), max range unchanged (no colliders)
    ]
    REPORT["cloth_len"] = {"hairtail": round(lt, 2), "hairback": round(lb, 2), "sidelock": round(ls, 2), "ribbon_reach": round(r_rib, 2),
                           "skirt_h": round(sh, 2), "jacket_h": round(jh, 2)}
    json.dump(CLOTH, open(os.path.join(RUN, f"cloth{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
    REPORT["cloth"] = [{k: c[k] for k in ("slot", "max_distance")} | {"mask": {k: v for k, v in c["mask"].items() if k != "anchors"}} for c in CLOTH]

# ---------------------------------------------------------------- assemble objects
def join(names, newname, arm):
    bpy.ops.object.select_all(action="DESELECT")
    objs = [k_meshes[n] for n in names]
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    if len(objs) > 1: bpy.ops.object.join()
    o = bpy.context.view_layer.objects.active
    o.name = newname; o.data.name = newname
    for m in list(o.modifiers): o.modifiers.remove(m)
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    return o
# collider radii: skin, tights and the top (the jacket, hair, skirt would inflate them)
for n in ("skin", "leg", "cloth"):
    k_meshes[n].vertex_groups.new(name="_coll").add(list(range(len(k_meshes[n].data.vertices))), 1.0, "REPLACE")
# head collision sphere fitted to the face and the head skin (Lenko has no scalp under the hair: the sphere sits in the
# front of the head and leaves the nape to the neck capsule; a sphere as build_pt.py's would push the back hair out)
_hs = coords("skin")[[i for i, r in enumerate(WROWS["skin"]) if sum(w for n, w in r if n == V("head")) > 0.6]]
_hp = np.concatenate([coords("Body"), _hs])
# hair collision (2026-11-03, user: "跑动时，长发很容易穿到外套里面"): point sets for the hair-only colliders built with the
# physics asset below: the outer surface of everything but the hair that stays with the torso (arm-weighted verts out),
# the jacket on each upper arm, and the rest positions of the simulated hair (the colliders stay clear of them)
# sleeves told apart by distance from the arm axes (the off-shoulder jacket's back panel and collar carry arm weights)
OUTER_P = np.concatenate([coords(n)[(_arm_d(coords(n)) > 7.0) & _not_slot(n, "MI_Lenko_Ribbon")]
                          for n in ("skin", "cloth", "skirt", "leg", "coat")])
SLEEVE_P = {s: coords("coat")[_frac(WROWS["coat"], lambda b, s=s: b.lower() == V(f"upperarm_{s}").lower()) > 0.5] for s in "lr"}
FOREARM_P = {(s, n_): coords(n_)[_frac(WROWS[n_], lambda b, s=s: b.lower() in (V(f"lowerarm_{s}").lower(), V(f"hand_{s}").lower())) > 0.5]
             for s in "lr" for n_ in ("coat", "skin")}
JACKET_SIM_P = coords("jacket_sim") if "jacket_sim" in k_meshes else None
HAIR_P = np.concatenate([coords(s) for s in ("MI_Lenko_HairBackSim", "MI_Lenko_HairTailSim") if s in k_meshes]) \
    if "MI_Lenko_HairBackSim" in k_meshes else None
body = join(BODY_MESHES + [n for n in k_meshes if n not in BODY_MESHES + HEAD_MESHES], "SK_Karin_Body", arm_body)   # + the simulation meshes
head = join(HEAD_MESHES, "SK_Karin_Head", arm_head)
bpy.data.objects.remove(k_arm, do_unlink=True)
HEAD_C = np.array([0.0, float(_hp[:, 1].mean()), float(_hp[:, 2].mean())])
HEAD_R = 0.85 * float(np.median(np.linalg.norm(_hp - HEAD_C, axis=1)))
REPORT["head_sphere"] = {"center": [round(float(x), 2) for x in ue(HEAD_C)], "radius": round(HEAD_R, 2), "verts": len(_hp)}

# face morph targets
if "Body" in DELTAS:
    d = DELTAS["Body"]
    head.shape_key_add(name="Basis", from_mix=False)
    base = np.array([list(v.co) for v in head.data.vertices])
    xs = base[:, 0]
    REPORT["face_morphs"] = {}
    for mname, recipe in FACE.items():
        delta = np.zeros_like(base)
        for key, w in recipe.items():
            k, _, part = key.partition("|")
            if k not in d: continue
            dk = d[k] * w
            if part == "L": dk = dk * smooth(xs, -0.3, 0.3)[:, None]
            elif part == "R": dk = dk * (1.0 - smooth(xs, -0.3, 0.3))[:, None]
            delta += dk
        sk_ = head.shape_key_add(name=mname, from_mix=False)
        sk_.data.foreach_set("co", (base + delta).ravel())
        REPORT["face_morphs"][mname] = round(float(np.linalg.norm(delta, axis=1).max()), 3)
    mv_ = np.linalg.norm(d["まばたき"], axis=1)
    REPORT["blink_center_x_abs"] = round(float((np.abs(xs) * mv_).sum() / max(mv_.sum(), 1e-9)), 2)
    REPORT["zero_morphs"] = [k for k, v in REPORT["face_morphs"].items() if v < 1e-3]

# ---------------------------------------------------------------- materials
MAT_RENAME = {"Lenko_Face": "MI_Karin_Face", "Lenko_Face_edge": "MI_Karin_FaceEdge", "Lenko_eyes_edge": "MI_Lenko_Eyes",
              "Lenko_Body": "MI_Karin_Skin", "Lenko_Fhair": "MI_Lenko_HairF", "Lenko_Bhair": "MI_Lenko_HairB",
              "Lenko_Cloth": "MI_Lenko_Cloth", "Lenko_Cloth_h": "MI_Lenko_ClothH", "Lenko_Pig_l": "MI_Lenko_Pig",
              "Lenko_coat_Pig_l": "MI_Lenko_Pig2", "Lenko_Skirt": "MI_Lenko_Skirt", "Lenko_Skirt_h": "MI_Lenko_SkirtH",
              "Lenko_Skirt_l": "MI_Lenko_SkirtL", "Lenko_Leg": "MI_Lenko_Leg", "Lenko_Coat_l": "MI_Lenko_Coat"}
for m in list(bpy.data.materials):
    if m.name in MAT_RENAME: m.name = MAT_RENAME[m.name]
def drop_slots(obj, drop_faces_of=(), merge=None):
    merge = merge or {}
    idx = {s.material.name: i for i, s in enumerate(obj.material_slots) if s.material}
    bm = bmesh.new(); bm.from_mesh(obj.data)
    dels = [f for f in bm.faces if any(f.material_index == idx.get(n, -1) for n in drop_faces_of)]
    bmesh.ops.delete(bm, geom=dels, context="FACES")
    for f in bm.faces:
        for s_, dst in merge.items():
            if f.material_index == idx.get(s_, -1): f.material_index = idx[dst]
    bm.to_mesh(obj.data); bm.free()
    bpy.context.view_layer.objects.active = obj
    for name in list(drop_faces_of) + list(merge):
        for i, s in enumerate(obj.material_slots):
            if s.material and s.material.name == name:
                obj.active_material_index = i
                bpy.ops.object.material_slot_remove(); break
    return len(dels)
# one slot per texture
drop_slots(body, (), {"MI_Lenko_ClothH": "MI_Lenko_Cloth", "MI_Lenko_Pig2": "MI_Lenko_Pig", "MI_Lenko_SkirtH": "MI_Lenko_Skirt",
                      "MI_Lenko_SkirtL": "MI_Lenko_Skirt"})
drop_slots(head, (), {"MI_Karin_FaceEdge": "MI_Karin_Face"})
def prune_slots(obj):
    """Drop material slots no face uses (the role objects kept their source slots; the FBX would carry them)."""
    used = set(np.unique([p.material_index for p in obj.data.polygons]).tolist())
    bpy.context.view_layer.objects.active = obj
    for i in reversed(range(len(obj.material_slots))):
        if i not in used:
            obj.active_material_index = i
            bpy.ops.object.material_slot_remove()
for o in (body, head): prune_slots(o)
REPORT["materials"] = {"body": [s.material.name for s in body.material_slots], "head": [s.material.name for s in head.material_slots]}

# ---------------------------------------------------------------- textures and materials.json
import shutil
for t, fn in TEXF.items():
    shutil.copyfile(os.path.join(TEXSRC, fn), os.path.join(texdir, t + ".png"))
# flat normal / ARM / grey / SCMT helper textures the UE import script expects in every run (Karin_Original's)
for t in ("Karin_FlatN", "Karin_ARM", "Karin_ARMMatte", "Karin_Gray", "Karin_SCMT"):
    shutil.copyfile(os.path.join(HELPER_TEX, t + ".png"), os.path.join(texdir, t + ".png"))
MATS = {"MI_Karin_Skin": ("Lenko_Body", "skin"), "MI_Karin_Face": ("Lenko_Face", "face"), "MI_Lenko_Eyes": ("Lenko_Eyes", "face"),
        "MI_Lenko_HairF": ("Lenko_HairF", "hair"), "MI_Lenko_HairB": ("Lenko_HairB", "hair"), "MI_Lenko_Cloth": ("Lenko_Cloth", "costume"),
        "MI_Lenko_Pig": ("Lenko_Pig", "costume"), "MI_Lenko_Skirt": ("Lenko_Skirt", "costume"), "MI_Lenko_Leg": ("Lenko_Leg", "costume"),
        "MI_Lenko_Coat": ("Lenko_Coat", "costume"), "MI_Lenko_Jacket": ("Lenko_JacketComb", "costume")}
ALIAS = {"MI_Lenko_HairTail": "MI_Lenko_HairF", "MI_Lenko_HairFront": "MI_Lenko_HairF", "MI_Lenko_HairBack": "MI_Lenko_HairB",
         "MI_Lenko_SkirtCloth": "MI_Lenko_Skirt", "MI_Lenko_Ribbon": "MI_Lenko_Skirt", "MI_Lenko_SkirtSim": "MI_Lenko_Skirt",
         "MI_Lenko_JacketSim": "MI_Lenko_Coat", "MI_Lenko_RibbonSim": "MI_Lenko_Skirt", "MI_Lenko_HairTailSim": "MI_Lenko_HairF",
         "MI_Lenko_HairFrontSim": "MI_Lenko_HairF", "MI_Lenko_HairBackSim": "MI_Lenko_HairB",
         "MI_Lenko_Chest": "MI_Lenko_Cloth", "MI_Lenko_ChestSim": "MI_Lenko_Cloth"}
# brightness (ue_brightness.py: near-white anime albedo blows out under the game's lighting; factors as Karin's) and the
# slots that cast no shadow (hair over the face: it blacked out the face under the bangs)
BRIGHT = {t: (0.9 if c in ("skin", "face") else 0.78) for t, c in MATS.values()}
NOSHADOW = ["MI_Lenko_HairF", "MI_Lenko_HairFront", "MI_Lenko_HairTail"]
json.dump({"materials": {k: {"texture": t, "kind": c} for k, (t, c) in MATS.items()}, "alias": ALIAS, "brightness": BRIGHT,
           "noshadow": NOSHADOW},
          open(os.path.join(RUN, f"materials{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
REPORT["slots_unmapped"] = sorted({s.material.name for o in (body, head) for s in o.material_slots} - set(MATS) - set(ALIAS))
assert not REPORT["slots_unmapped"], REPORT["slots_unmapped"]

# ---------------------------------------------------------------- hidden triangles
def tri(name, arm, bone, at, mat):
    m = bpy.data.meshes.new(name)
    m.from_pydata([tuple(at), tuple(at + np.array([0.01, 0, 0])), tuple(at + np.array([0, 0, 0.01]))], [], [(0, 1, 2)])
    m.update()
    o = bpy.data.objects.new(name, m); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(mat)
    o.vertex_groups.new(name=bone).add([0, 1, 2], 1.0, "REPLACE")
    o.parent = arm
    o.modifiers.new("Armature", "ARMATURE").object = arm
    return o
skin = bpy.data.materials.get("MI_Karin_Skin")
leader_tri = tri("SK_Karin_Leader", arm_lead, V("root"), np.array([0.0, 0.0, 0.0]), skin) if arm_lead else None
empty_tri = tri("SK_Hidden", arm_empty, V("head"), NEW[V("head")] + np.array([0, 0, 1.0]), skin)
hat_arm = hat_tri = None
if VARIANT == "adult":
    h_objs = import_uemodel(os.path.join(WORK, "ue", "Hun_Hat_Skeleton.uemodel"))
    hat_arm = next(o for o in h_objs if o.type == "ARMATURE")
    hat_arm.name = "ArmatureHat"; hat_arm.data.name = "ArmatureHat"
    for o in h_objs:
        if o.type == "MESH": bpy.data.objects.remove(o, do_unlink=True)
    hat_tri = tri("SK_HatHidden", hat_arm, hat_arm.data.bones[0].name, np.array([0.0, 0.0, 0.0]), skin)
if VCFG["face_slot0"]:
    # The game gives the adult head component a dynamic instance of its first material (BP_Renewal_Hun
    # RefreshMaterialParamByHead) that rendered the face dark: the head's first section is a hidden triangle (build_pt.py).
    t = tri("SK_HeadSlot0", arm_head, V("head"), NEW[V("head")], bpy.data.materials["MI_Karin_Skin"])
    bpy.ops.object.select_all(action="DESELECT")
    t.select_set(True); head.select_set(True)
    bpy.context.view_layer.objects.active = head
    bpy.ops.object.join()
    me = head.data
    order = [m.name for m in me.materials]
    newo = ["MI_Karin_Skin"] + [n for n in order if n != "MI_Karin_Skin"]
    idx = np.zeros(len(me.polygons), dtype=np.int32); me.polygons.foreach_get("material_index", idx)
    remap_ = np.array([newo.index(n) for n in order], dtype=np.int32)
    mats = [bpy.data.materials[n] for n in newo]
    me.materials.clear()
    for m in mats: me.materials.append(m)
    me.polygons.foreach_set("material_index", remap_[idx]); me.update()
lash_face = None
if VCFG["face_show"]:
    # Gameplay drives the lash card's morphs, the cutscene actors the head's (build_pt.py): the face is on both, the
    # head's copy scaled to 90% around the head joint with a KarinFaceShow morph restoring it.
    lash_face = head.copy(); lash_face.data = head.data.copy(); lash_face.name = "SK_Karin_Face"
    bpy.context.scene.collection.objects.link(lash_face)
    keys = head.data.shape_keys.key_blocks
    n = len(head.data.vertices)
    base = np.zeros(n * 3); keys["Basis"].data.foreach_get("co", base); base = base.reshape(-1, 3)
    c = np.array(NEW[V("head")])
    small = c + (base - c) * 0.9
    for kb in keys[1:]:
        a = np.zeros(n * 3); kb.data.foreach_get("co", a)
        kb.data.foreach_set("co", (a.reshape(-1, 3) - base + small).ravel())
    show = head.shape_key_add(name="KarinFaceShow", from_mix=False)
    show.data.foreach_set("co", base.ravel())
    keys["Basis"].data.foreach_set("co", small.ravel())
    head.data.vertices.foreach_set("co", small.ravel()); head.data.update()
    REPORT["face_show"] = {"verts": n, "collapsed_extent": round(float(np.abs(small - c).max()), 3)}

# ---------------------------------------------------------------- cloth section clean-up
# UE's cloth builder welds coincident verts and refuses a section with a triangle whose corners weld together; exact
# duplicate faces would weld into doubled constraints with cancelling normals (build_pbz.py, two-sided skirt).
def clean_cloth(obj, slots, tol=1e-3):
    idx = {s.material.name: i for i, s in enumerate(obj.material_slots) if s.material}
    want = {idx[n] for n in slots if n in idx}
    bm = bmesh.new(); bm.from_mesh(obj.data)
    bmesh.ops.triangulate(bm, faces=[f for f in bm.faces if f.material_index in want])
    bad, seen, dup = [], set(), 0
    for f in bm.faces:
        if f.material_index not in want: continue
        if min(e.calc_length() for e in f.edges) < tol or f.calc_area() < tol * tol:
            bad.append(f); continue
        key = (f.material_index, tuple(sorted(tuple(round(c, 3) for c in v.co) for v in f.verts)))
        if key in seen: bad.append(f); dup += 1
        else: seen.add(key)
    bmesh.ops.delete(bm, geom=bad, context="FACES_ONLY")
    bm.to_mesh(obj.data); bm.free()
    return {"removed": len(bad), "duplicates": dup}
def weld_report(obj, slots):
    """Per cloth section: particles after a weld at 0.01 mm whose averaged unit face normal is under half a unit
    (they shade dark once the cloth binding rebuilds the render normals)."""
    me = obj.data; idx = {s.material.name: i for i, s in enumerate(obj.material_slots) if s.material}
    out = {}
    co = np.array([list(v.co) for v in me.vertices])
    for s in slots:
        if s not in idx: continue
        acc = collections.defaultdict(lambda: np.zeros(3)); n = collections.Counter()
        for p in me.polygons:
            if p.material_index != idx[s]: continue
            for v in p.vertices:
                k = tuple(np.round(co[v], 3)); acc[k] += np.array(p.normal); n[k] += 1
        mags = np.array([np.linalg.norm(acc[k]) / n[k] for k in acc])
        out[s] = {"particles": len(acc), "weak_normals": int((mags < 0.5).sum())}
    return out
if CLOTH:
    slots = [c["slot"] for c in CLOTH] + [c["mask"]["sim_slot"] for c in CLOTH if "sim_slot" in c["mask"]]
    REPORT["cloth_clean"] = clean_cloth(body, slots)
    REPORT["cloth_welds"] = weld_report(body, [c["mask"].get("sim_slot", c["slot"]) for c in CLOTH])

# ---------------------------------------------------------------- physics asset (UE bone-local shapes, as build_pt.py)
def qmul(a, b):
    ax, ay, az, aw = a; bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by, aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw, aw * bw - ax * bx - ay * by - az * bz)
CROT = {}
def crot(n):
    l = n.lower()
    if l in CROT: return CROT[l]
    p = SKP.get(l)
    q = tuple(SKQ[l])
    CROT[l] = q if p is None else qmul(crot(p), q)
    return CROT[l]
def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
def to_local(n, p_blender):
    R = qmat(crot(n))
    return R.T @ (ue(p_blender) - ue(NEW[n]))
def quat_z_to(d):
    d = norm(d); z = np.array([0.0, 0.0, 1.0])
    c = float(np.dot(z, d))
    if c > 0.99999: return [0.0, 0.0, 0.0, 1.0]
    if c < -0.99999: return [1.0, 0.0, 0.0, 0.0]
    ax = norm(np.cross(z, d)); s = math.sqrt((1 - c) / 2.0); hc = math.sqrt((1 + c) / 2.0)
    return [float(ax[0] * s), float(ax[1] * s), float(ax[2] * s), hc]
def capsule(n, a, b, r, kinematic, **extra):
    la, lb = to_local(n, a), to_local(n, b)
    L = float(np.linalg.norm(lb - la))
    body_ = {"bone": n, "type": "capsule", "center": [round(float(x), 3) for x in (la + lb) / 2.0],
             "quat": quat_z_to(lb - la), "radius": round(float(r), 3), "length": round(max(L, 0.1), 3), "kinematic": kinematic}
    body_.update(extra)
    return body_
bpos = np.array([list(v.co) for v in body.data.vertices])
def seg_dist(p, a, b):
    d = b - a; t = np.clip(((p - a) @ d) / max(np.dot(d, d), 1e-9), 0, 1)
    return np.linalg.norm(p - (a + np.outer(t, d)), axis=1)
gidx = {g.index: g.name for g in body.vertex_groups}
cg = body.vertex_groups["_coll"].index
vbone = collections.defaultdict(list)
for i, v in enumerate(body.data.vertices):
    if not any(g.group == cg for g in v.groups): continue
    best = max((g for g in v.groups if g.group != cg), key=lambda g: g.weight, default=None)
    if best is not None and best.weight > 0.6:
        vbone[gidx[best.group]].append(i)
body.vertex_groups.remove(body.vertex_groups["_coll"])
def radius_for(bone, a, b, default, pct=40):
    ids = vbone.get(bone, [])
    if len(ids) < 20: return default
    d = seg_dist(bpos[ids], a, b)
    return float(np.clip(np.percentile(d, pct), 2.0, 14.0))
COLL = []
def coll(bone, a, b, default, shrink=0.9, pct=40):
    r = radius_for(bone, a, b, default, pct) * shrink
    COLL.append(capsule(bone, a, b, r, True))
pel, s2, s4, nk, hd = (V(n) for n in ("pelvis", "spine_02", "spine_04", "neck_01", "head"))
coll(pel, NEW[V("thigh_l")], NEW[V("thigh_r")], 10.0)
coll(s2, NEW[s2], NEW[V("spine_03")], 10.0)
coll(s4, NEW[s4], NEW[V("spine_05")], 10.0)
coll(nk, NEW[nk], NEW[V("head")], 4.0)
COLL.append({"bone": hd, "type": "sphere", "center": [round(float(x), 3) for x in to_local(hd, HEAD_C)],
             "radius": round(HEAD_R, 2), "kinematic": True})
# The thigh capsule is only kept where no buttock sphere goes on the thigh: the plugin used to start every shape on a bone
# with an empty body (CreateNewBody returns the bone's existing body), so the sphere replaced the capsule in every
# tested build; the plugin now keeps several shapes per bone, and the skirt / jacket keep the colliders they were tested with.
_thigh_caps = {}
for s in "lr":
    th, ca, ft, ua, la = (V(f"{n}_{s}") for n in ("thigh", "calf", "foot", "upperarm", "lowerarm"))
    coll(th, NEW[th], NEW[ca], 7.0, shrink=1.0, pct=85); _thigh_caps[th] = COLL.pop()
    coll(ca, NEW[ca], NEW[ft], 5.0)
    coll(ua, NEW[ua] + OFS.get(ua, 0.0), NEW[la] + OFS.get(la, 0.0), 4.0)   # on the arm mesh (see the shoulder offsets)
for s, sx in (("l", 1.0), ("r", -1.0)):
    th, ca = V(f"thigh_{s}"), V(f"calf_{s}")
    L_ = float(np.linalg.norm(NEW[ca] - NEW[th]))
    ids = np.array(vbone.get(pel, []) + vbone.get(th, []), dtype=int)
    if len(ids) < 20: continue
    p = bpos[ids]
    m = (p[:, 0] * sx > 1.0) & (p[:, 1] > NEW[th][1] + 1.0) & (p[:, 2] > NEW[th][2] - 0.35 * L_) & (p[:, 2] < NEW[th][2] + 0.15 * L_)
    p = p[m]
    if len(p) < 20: continue
    c = np.array([p[:, 0].mean(), NEW[th][1], p[:, 2].mean()])
    r0 = float(np.percentile(np.linalg.norm(p - c, axis=1), 75))
    c[1] += 0.25 * r0
    r = float(np.percentile(np.linalg.norm(p - c, axis=1), 85))
    COLL.append({"bone": th, "type": "sphere", "center": [round(float(x), 3) for x in to_local(th, c)], "radius": round(r, 2), "kinematic": True})
    REPORT.setdefault("buttock_spheres", {})[s] = {"center": [round(float(x), 2) for x in ue(c)], "radius": round(r, 2), "verts": int(len(p))}
for th, cap in _thigh_caps.items():
    if not any(c["bone"] == th for c in COLL): COLL.append(cap)
REPORT["colliders"] = [(c["bone"], c["type"], c["radius"]) for c in COLL]
if VCFG["cloth"]:
    json.dump({"bodies": COLL, "joints": [], "disable_pairs": []}, open(os.path.join(RUN, f"cloth_collision{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)

# ---- hair collision asset (back hair, twin tails): the body asset's capsules sit on the skin, 3-8 cm inside the jacket
# and its collar on the back, so the hair sank into the jacket whenever it fell onto the back (running leans the torso
# forward). Here the back is a stack of horizontal slices. In each, the outline of everything but the hair that stays
# with the torso (not the hip pig, ribbon and pocket pigs) is sampled around the slice's centre every 15 degrees over
# +-66 degrees from straight back (90th percentile radius in a +-9 degree window, the smallest of three thin sub-bands
# over the capsule's height: a surface sloping out downward must not make the capsule stand out above it; none where
# the surface faces up, shoulder and pocket tops), and a chain of capsules runs through those points moved inward
# along their radius by the capsule radius, so the chain's outer side follows the outline without standing out of it.
# The radius is also kept clear of the hair's rest position by the collision thickness. Each slice rides on the torso
# bone at its height (pelvis below the belt: the jacket hem's rest outline; the hem and skirt never go inside it, they
# have a backstop). The upper arms get a capsule over the stretch of arm the jacket covers, inside it. Head sphere and
# neck capsule as the body's.
def _dp(P, tol):
    """Douglas-Peucker simplification of a polyline (rows of P)."""
    if len(P) < 3: return P
    a, b = P[0], P[-1]; ab = b - a; L2 = max(float(ab @ ab), 1e-9)
    t = np.clip(((P - a) @ ab) / L2, 0, 1); d = np.linalg.norm(P - (a + np.outer(t, ab)), axis=1)
    i = int(np.argmax(d))
    if d[i] <= tol: return np.array([a, b])
    return np.vstack([_dp(P[:i + 1], tol)[:-1], _dp(P[i:], tol)])
HAIR_COLL = []
if VCFG["cloth"] and HAIR_P is not None:
    TH = max(c["config"].get("CollisionThickness", 1.0) for c in CLOTH if c.get("collision") == "hair")
    R_C, DZ, ANG, WIN, AMAX = 3.5, 4.5, 15.0, 9.0, 66.0
    SUBZ, SUBH = (-2.75, 0.0, 2.75), 0.75   # outline radius = smallest over three thin sub-bands spanning the capsule's height
    SLOPE = 8.0                              # radius change over those 5.5 cm above which the surface is a ledge: no point
    INSET = 0.8                              # collider surface under the outline: the back hair (thickness 1.0) rests on the jacket
    SPL = [V(n) for n in ("pelvis", "spine_01", "spine_02", "spine_03", "spine_04", "spine_05", "neck_01")]
    lz = np.array([NEW[b][2] for b in SPL])
    def bone_at(z): return SPL[int(np.clip(np.searchsorted(lz[:-1], z, side="right") - 1, 0, len(SPL) - 2))]
    def angdiff(a, b): return np.abs((a - b + 180.0) % 360.0 - 180.0)
    z_lo = float(np.percentile(HAIR_P[:, 2], 1)); z_hi = float(NEW[V("neck_01")][2]) - 4.0   # the nape: neck capsule
    slices = []
    for z in np.arange(z_lo + DZ / 2.0, z_hi, DZ):
        P = OUTER_P[np.abs(OUTER_P[:, 2] - z) < R_C]
        if len(P) < 30: continue
        cx, cy = 0.0, float(np.median(P[:, 1]))
        th = np.degrees(np.arctan2(P[:, 0] - cx, P[:, 1] - cy)); rho = np.hypot(P[:, 0] - cx, P[:, 1] - cy)   # 0 = straight back (+Y)
        H = HAIR_P[np.abs(HAIR_P[:, 2] - z) < DZ / 2.0]
        thH = np.degrees(np.arctan2(H[:, 0] - cx, H[:, 1] - cy)); rhoH = np.hypot(H[:, 0] - cx, H[:, 1] - cy)
        runs, cur = [], []
        why = collections.Counter(); sink = []
        for t in np.arange(-AMAX, AMAX + 1e-6, ANG):
            w = angdiff(th, t) < WIN
            rs = [float(np.percentile(rho[w & sb], 90)) for sb in (np.abs(P[:, 2] - z - dz) < SUBH for dz in SUBZ) if (w & sb).sum() >= 3]
            # surface in all three sub-bands (an upward-facing surface, shoulder or pocket top, has none above it)
            r = min(rs) - INSET if len(rs) == 3 and max(rs) - min(rs) <= SLOPE else None
            if r is None: why["bands" if len(rs) < 3 else "slope"] += 1
            if r is not None:
                hw = angdiff(thH, t) < WIN + 2.0
                if hw.any(): r = min(r, float(np.percentile(rhoH[hw], 2)) - TH - 0.3)
                if r - R_C <= 1.0: why["thin"] += 1
                else: sink.append(rs[1] - r - 1.0)   # how far the back hair (thickness 1.0) can sink into the outline at the slice height
            if r is not None and r - R_C > 1.0:
                tr = math.radians(t)
                cur.append([cx + (r - R_C) * math.sin(tr), cy + (r - R_C) * math.cos(tr), z])
            elif cur: runs.append(np.array(cur)); cur = []
        if cur: runs.append(np.array(cur))
        bn = bone_at(z); nsh = 0
        for run in runs:
            pts_ = _dp(run, 0.8)
            if len(pts_) == 1:
                HAIR_COLL.append({"bone": bn, "type": "sphere", "center": [round(float(x), 3) for x in to_local(bn, pts_[0])],
                                  "radius": R_C, "kinematic": True, "_w": [list(map(float, pts_[0])), list(map(float, pts_[0]))]}); nsh += 1
            for a_, b_ in zip(pts_[:-1], pts_[1:]):
                HAIR_COLL.append(capsule(bn, a_, b_, R_C, True) | {"_w": [list(map(float, a_)), list(map(float, b_))]}); nsh += 1
        slices.append({"z": round(float(z), 1), "bone": bn, "shapes": nsh, "runs": len(runs), "skipped": dict(why),
                       "sink_cm": [round(float(np.min(sink)), 1), round(float(np.max(sink)), 1)] if sink else None})
    sleeves = {}
    for s in "lr":
        ua, la = V(f"upperarm_{s}"), V(f"lowerarm_{s}")
        a_, b_ = NEW[ua] + OFS.get(ua, 0.0), NEW[la] + OFS.get(la, 0.0)
        P = SLEEVE_P[s]
        if len(P) < 20: continue
        ax_ = b_ - a_; L_ = float(np.linalg.norm(ax_)); u_ = ax_ / L_
        tt = (P - a_) @ u_
        t0, t1 = float(np.percentile(tt, 5)), float(np.percentile(tt, 95))
        dd = np.linalg.norm((P - a_) - np.outer(tt, u_), axis=1)
        r_ = float(np.percentile(dd, 25)) - 0.3          # inside the jacket around the arm
        hd_ = seg_dist(HAIR_P, a_ + t0 * u_, a_ + t1 * u_)
        if (hd_ < r_ + TH + 0.3).any(): r_ = min(r_, float(np.percentile(hd_, 0.5)) - TH - 0.3)
        r_ = float(np.clip(r_, 2.0, 9.0))
        p0, p1 = a_ + (t0 + r_) * u_, a_ + max(t1 - r_, t0 + r_) * u_   # hemispherical ends inside the covered stretch
        HAIR_COLL.append(capsule(ua, p0, p1, r_, True) | {"_w": [list(map(float, p0)), list(map(float, p1))]})
        sleeves[s] = {"radius": round(r_, 2), "covered_cm": [round(t0, 1), round(t1, 1)], "arm_cm": round(L_, 1)}
    # forearms (round 4): the back hair fans out to 25 cm from the spine at elbow height and the arms swing back through it
    # when running; elbow to the middle of the hand, sleeve radius where the jacket covers the forearm, else the skin's
    for s in "lr":
        la, ha = V(f"lowerarm_{s}"), V(f"hand_{s}")
        a_, b_ = NEW[la] + OFS.get(la, 0.0), NEW[ha]
        ax_ = b_ - a_; L_ = float(np.linalg.norm(ax_)); u_ = ax_ / L_
        rr = {}
        for n_, q_ in (("coat", 25), ("skin", 75)):
            P = FOREARM_P[(s, n_)]
            tt = (P - a_) @ u_; m_ = (tt > 0.15 * L_) & (tt < 0.9 * L_)
            if m_.sum() >= 20: rr[n_] = float(np.percentile(np.linalg.norm((P[m_] - a_) - np.outer(tt[m_], u_), axis=1), q_)) - 0.3
        r_ = rr.get("coat", rr.get("skin", 3.0))
        p0, p1 = a_, b_ + 4.0 * u_
        hd_ = seg_dist(HAIR_P, p0, p1)
        if (hd_ < r_ + TH + 0.3).any(): r_ = min(r_, float(np.percentile(hd_, 0.5)) - TH - 0.3)
        r_ = float(np.clip(r_, 2.0, 7.0))
        HAIR_COLL.append(capsule(la, p0, p1, r_, True) | {"_w": [list(map(float, p0)), list(map(float, p1))]})
        sleeves["forearm_" + s] = {"radius": round(r_, 2), "from": sorted(rr), "forearm_cm": round(L_, 1)}
    # thighs (round 4): the hair's lower ends hang behind the buttocks and the jacket hem; a leg swinging back pushes the
    # hair as it pushes the hem (the cloth assets do not collide with each other), radius kept clear of the rest hair
    for th, cap in _thigh_caps.items():
        a_, b_ = NEW[th], NEW[V(th.lower().replace("thigh", "calf"))]
        d_ = seg_dist(HAIR_P, a_, b_)
        r_ = max(min(float(cap["radius"]), float(d_.min()) - TH - 0.3), 3.0)
        HAIR_COLL.append(capsule(th, a_, b_, r_, True) | {"_w": [list(map(float, a_)), list(map(float, b_))]})
        sleeves[th] = {"radius": round(r_, 2), "skin_fit": cap["radius"], "rest_clearance_cm": round(float(d_.min()) - r_ - TH, 2)}
    HAIR_COLL += [dict(c) for c in COLL if c["bone"] in (V("head"), V("neck_01"))]
    # bind-pose check: hair particles inside a hair collider (plus thickness)
    def _hair_in(c):
        if "_w" not in c: return np.zeros(len(HAIR_P), bool)
        a_, b_ = np.array(c["_w"][0]), np.array(c["_w"][1])
        return seg_dist(HAIR_P, a_, b_) < c["radius"] + TH - 0.05
    _in = np.zeros(len(HAIR_P), bool)
    for c in HAIR_COLL: _in |= _hair_in(c)
    REPORT["hair_collision"] = {"shapes": len(HAIR_COLL), "thickness": TH, "slices": slices, "sleeve_radius": sleeves,
                                "hair_particles_inside_at_rest": int(_in.sum()), "hair_particles": int(len(HAIR_P)),
                                "world": [[c["_w"][0], c["_w"][1], c["radius"]] for c in HAIR_COLL if "_w" in c]}
    for c in HAIR_COLL: c.pop("_w", None)
    json.dump({"bodies": HAIR_COLL, "joints": [], "disable_pairs": []},
              open(os.path.join(RUN, f"cloth_collision_hair{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)
# ---- jacket collision asset: the body set plus the thigh capsules (the legs push the hem when running), each capsule's
# radius trimmed so the jacket's rest shape stays clear of it by the collision thickness + 0.3 cm
if VCFG["cloth"] and JACKET_SIM_P is not None:
    JTH = next(c["config"]["CollisionThickness"] for c in CLOTH if c["slot"] == "MI_Lenko_Jacket")
    JACKET_COLL, jrep = [dict(c) for c in COLL], {}
    for th, cap in _thigh_caps.items():
        a_, b_ = NEW[th], NEW[V(th.lower().replace("thigh", "calf"))]
        d_ = seg_dist(JACKET_SIM_P, a_, b_)
        r_ = max(min(float(cap["radius"]), float(d_.min()) - JTH - 0.3), 3.0)
        JACKET_COLL.append(capsule(th, a_, b_, r_, True))
        jrep[th] = {"radius": round(r_, 2), "skin_fit": cap["radius"], "rest_clearance_cm": round(float(d_.min()) - r_ - JTH, 2)}
    REPORT["jacket_collision"] = {"shapes": len(JACKET_COLL), "thigh_capsules": jrep}
    json.dump({"bodies": JACKET_COLL, "joints": [], "disable_pairs": []},
              open(os.path.join(RUN, f"cloth_collision_jacket{VCFG['suffix']}.json"), "w", encoding="utf-8"), indent=1)

# ---------------------------------------------------------------- checks
for o, a in ((body, arm_body), (head, arm_head)):
    bones = set(b.name for b in a.data.bones)
    REPORT.setdefault("groups_not_bones", {})[o.name] = [g.name for g in o.vertex_groups if g.name not in bones]
    REPORT.setdefault("verts", {})[o.name] = len(o.data.vertices)
REPORT["new_joints"] = {n: [round(float(x), 2) for x in ue(NEW[n])] for n in
                        [V(x) for x in ("pelvis", "spine_01", "neck_01", "head", "clavicle_l", "upperarm_l", "lowerarm_l",
                                        "hand_l", "thigh_l", "calf_l", "foot_l", "ball_l")]}
assert not any(REPORT["groups_not_bones"].values()), REPORT["groups_not_bones"]

# ---------------------------------------------------------------- export (stock FBX, cm via unit scale 0.01)
bpy.context.scene.unit_settings.scale_length = 0.01
kw = dict(use_selection=True, add_leaf_bones=False, bake_anim=False, use_mesh_modifiers=False,
          mesh_smooth_type="FACE", use_tspace=False, object_types={"ARMATURE", "MESH"})
SFX = VCFG["suffix"]
EXPORTS = [(arm_body, body, f"Karin_Body{SFX}.fbx"), (arm_empty, empty_tri, f"Empty{SFX}.fbx")]
for fn in ("Karin_Head", "Karin_Face"):
    if fn != VCFG["face_fbx"] and not (fn == "Karin_Face" and VCFG["face_show"]) and os.path.exists(os.path.join(RUN, f"{fn}{SFX}.fbx")):
        os.remove(os.path.join(RUN, f"{fn}{SFX}.fbx"))
EXPORTS.append((arm_head, head, f"{VCFG['face_fbx']}{SFX}.fbx"))
if lash_face:
    EXPORTS.append((arm_head, lash_face, f"Karin_Face{SFX}.fbx"))
if arm_lead: EXPORTS.append((arm_lead, leader_tri, "Karin_Leader.fbx"))
if hat_arm: EXPORTS.append((hat_arm, hat_tri, "Hat_Empty.fbx"))
for arm, o, fn in EXPORTS:
    for a_ in [e[0] for e in EXPORTS]:
        if a_ is not arm and a_.name == "Armature": a_.name = "ArmatureTmp"
    arm.name = "Armature"
    bpy.ops.object.select_all(action="DESELECT")
    arm.select_set(True); o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=os.path.join(RUN, fn), **kw)
    arm.name = "Exported_" + fn
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(RUN, f"build{VCFG['suffix']}.blend"))
with open(os.path.join(RUN, f"report{VCFG['suffix']}.json"), "w", encoding="utf-8") as f:
    json.dump(REPORT, f, indent=1, ensure_ascii=False)
print("BUILD_OK", RUN)
