# UE 5.1 editor Python (-run=pythonscript): build the cloth-layer physics ABP that replaces
# /Game/Pal/Blueprint/Character/Player/Imp_Cloth/ABP_F_OldCloth001_Implimentation.
#   UnrealEditor-Cmd Pal.uproject -run=pythonscript -script="<PAL_WORK_ROOT>/scripts/ue_build_abp.py <PAL_WORK_ROOT>/builds/<run> [physics.json]"
#   (or tools/run_py.ps1 <PAL_WORK_ROOT>/scripts/ue_build_abp.py "<PAL_WORK_ROOT>/builds/<run> [physics.json]" <log>)
# The optional second argument is the resolved physics file exported by scripts/kawaii_sim.py (export=...): the
# run's physics.json geometry merged with scripts/physics_tune.json, i.e. exactly the settings that were simulated.
#
# Game contract (ABP_Player / DT_CharacterCreationMeshPresetTable_Equipments):
#   * ABP_Player has a LinkedAnimLayer "ClothLayer" of interface ALI_HumanCloth; the default body (OldCloth001, TypeA)
#     links ABP_F_OldCloth001_Implimentation_C into it. Vanilla graph: InPose -> LocalToComponent -> Kawaii* ->
#     ComponentToLocal -> Root. The layer runs on the main body mesh, i.e. on our Karin mesh.
#   * The game's KawaiiPhysics (1.17.x, same property layout as 1.17.1) collects chains from the skeleton asset, so every
#     root below is a bone of SK_PalHuman_Skeleton (chosen in build_pal.py).
import unreal, sys, os, json, math

args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
PHYS = json.load(open(args[1] if len(args) > 1 else os.path.join(RUN, "physics.json"), encoding="utf-8"))
L = lambda *a: unreal.log("[KARIN] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
G = unreal.PalGraphLib

SKEL = "/Game/Pal/Model/Character/Skeleton/Human/SK_PalHuman_Skeleton"
BODY = "/Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001"
ALI_DIR, ALI_NAME = "/Game/Pal/Blueprint/Character/Player/Female", "ALI_HumanCloth"
ABP_DIR, ABP_NAME = "/Game/Pal/Blueprint/Character/Player/Imp_Cloth", "ABP_F_OldCloth001_Implimentation"
LAYER = "ClothLayer"
skel = unreal.load_asset(SKEL)
body = unreal.load_asset(BODY)
assert skel and body

# ---------------------------------------------------------------- dummy anim layer interface (never packaged)
ali_path = ALI_DIR + "/" + ALI_NAME
if not eal.does_asset_exist(ali_path):
    f = unreal.AnimLayerInterfaceFactory()
    f.set_editor_property("target_skeleton", skel)
    ali = tools.create_asset(ALI_NAME, ALI_DIR, unreal.AnimBlueprint, f)
    L("graphs before", list(G.list_graphs(ali)))
    g = G.get_graph(ali, LAYER)
    if g is None:
        # a fresh interface may come with a default layer; reuse it under our name if present
        g = G.add_anim_layer_graph(ali, LAYER)
    nodes = G.get_nodes(g)
    root = next((n for n in nodes if n.get_class().get_name() == "AnimGraphNode_Root"), None)
    if root is None:
        root = G.add_node(g, "/Script/AnimGraph.AnimGraphNode_Root", 400, 0)
    inp = next((n for n in nodes if n.get_class().get_name() == "AnimGraphNode_LinkedInputPose"), None)
    if inp is None:
        inp = G.add_node(g, "/Script/AnimGraph.AnimGraphNode_LinkedInputPose", 0, 0)
    G.set_property(inp, "Node.Name", "InPose")
    G.reconstruct(inp)
    L("ali connect", G.connect(inp, "Pose", root, "Result"))
    L("ali compile", G.compile(ali))
    L("ali graphs", list(G.list_graphs(ali)))
    eal.save_loaded_asset(ali)
ali = unreal.load_asset(ali_path)

# ---------------------------------------------------------------- implementation ABP
abp_path = ABP_DIR + "/" + ABP_NAME
if eal.does_asset_exist(abp_path):
    eal.delete_asset(abp_path)
f = unreal.AnimBlueprintFactory()
f.set_editor_property("target_skeleton", skel)
f.set_editor_property("parent_class", unreal.AnimInstance)
abp = tools.create_asset(ABP_NAME, ABP_DIR, unreal.AnimBlueprint, f)
ok = G.implement_interface(abp, ali_path + "." + ALI_NAME + "_C")
L("implement", ok, list(G.list_graphs(abp)))
g = G.get_graph(abp, LAYER)
assert g, "no ClothLayer graph after implementing the interface"
nodes = G.get_nodes(g)
root = next(n for n in nodes if n.get_class().get_name() == "AnimGraphNode_Root")
inp = next(n for n in nodes if n.get_class().get_name() == "AnimGraphNode_LinkedInputPose")
L("layer nodes", [n.get_class().get_name() for n in nodes])

# ---------------------------------------------------------------- bind pose (component space) for collision setup
ref = {}
for line in G.get_ref_pose(body):
    name, parent, t, q = line.split("|")
    t = [float(x) for x in t.split()]; q = [float(x) for x in q.split()]
    ref[name] = (parent, unreal.Transform(unreal.Vector(*t), unreal.Quat(*q).rotator(), unreal.Vector(1, 1, 1)))
CS = {}
def cs(n):
    if n not in CS:
        p, tr = ref[n]
        CS[n] = tr if not p else tr * cs(p)   # UE: child * parent
    return CS[n]

def capsule_local(bone, a, b):
    """Kawaii capsule (axis = local Z of OffsetRotation) through component-space points a, b, in bone space."""
    inv = cs(bone).inverse()
    pa = inv.transform_location(unreal.Vector(*a)); pb = inv.transform_location(unreal.Vector(*b))
    mid = (pa + pb) * 0.5
    d = pb - pa
    length = d.length()
    d = d.normal()
    # rotation taking +Z onto d
    rot = unreal.MathLibrary.make_rot_from_z(d)
    return mid, rot, length

# ---------------------------------------------------------------- Kawaii nodes
KP = "/Script/KawaiiPhysicsEd.AnimGraphNode_KawaiiPhysics"
prev, prev_pin = inp, "Pose"
x = 300
report = []
for group in PHYS["groups"]:
    n = G.add_node(g, KP, x, 0); x += 350
    roots = group["roots"]
    G.set_property(n, "Node.RootBone", '(BoneName="%s")' % roots[0])
    for i, r in enumerate(roots[1:]):
        G.set_property(n, "Node.AdditionalRootBones[%d].RootBone" % i, '(BoneName="%s")' % r)
    s = group["settings"]
    G.set_property(n, "Node.PhysicsSettings",
                   "(Damping=%g,Stiffness=%g,WorldDampingLocation=%g,WorldDampingRotation=%g,Radius=%g,LimitAngle=%g)" %
                   (s["damping"], s["stiffness"], s["world_loc"], s["world_rot"], s["radius"], s["limit_angle"]))
    G.set_property(n, "Node.DummyBoneLength", str(group.get("dummy", 0.0)))
    G.set_property(n, "Node.BoneForwardAxis", "X_Positive")
    gx, gy, gz = group.get("gravity", [0, 0, 0])
    G.set_property(n, "Node.Gravity", "(X=%g,Y=%g,Z=%g)" % (gx, gy, gz))
    G.set_property(n, "Node.TeleportDistanceThreshold", "300.0")
    G.set_property(n, "Node.TeleportRotationThreshold", "10.0")
    for key, prop in (("stiffness_curve", "StiffnessCurveData"), ("damping_curve", "DampingCurveData"),
                      ("limit_angle_curve", "LimitAngleCurveData")):
        if group.get(key):   # (time, value) multipliers over LengthRateFromRoot
            keys = ",".join("(Time=%g,Value=%g)" % tuple(k) for k in group[key])
            G.set_property(n, "Node.%s.EditorCurveData.Keys" % prop, "(%s)" % keys)
    ci = 0
    for c in group.get("capsules", []):
        mid, rot, length = capsule_local(c["bone"], c["a"], c["b"])
        p = "Node.CapsuleLimits[%d]" % ci
        G.set_property(n, p + ".DrivingBone", '(BoneName="%s")' % c["bone"])
        G.set_property(n, p + ".Radius", str(c["radius"]))
        G.set_property(n, p + ".Length", str(length))
        G.set_property(n, p + ".OffsetLocation", "(X=%f,Y=%f,Z=%f)" % (mid.x, mid.y, mid.z))
        G.set_property(n, p + ".OffsetRotation", "(Pitch=%f,Yaw=%f,Roll=%f)" % (rot.pitch, rot.yaw, rot.roll))
        ci += 1
    si = 0
    for c in group.get("spheres", []):
        inv = cs(c["bone"]).inverse()
        pl = inv.transform_location(unreal.Vector(*c["center"]))
        p = "Node.SphericalLimits[%d]" % si
        G.set_property(n, p + ".DrivingBone", '(BoneName="%s")' % c["bone"])
        G.set_property(n, p + ".Radius", str(c["radius"]))
        G.set_property(n, p + ".OffsetLocation", "(X=%f,Y=%f,Z=%f)" % (pl.x, pl.y, pl.z))
        G.set_property(n, p + ".LimitType", "Outer")
        si += 1
    G.reconstruct(n)
    r = G.connect(prev, prev_pin, n, "ComponentPose")
    report.append((group["name"], roots[0], len(roots), ci, si, r))
    prev, prev_pin = n, "Pose"
L("root connect", G.connect(prev, prev_pin, root, "Result"))
for r in report: L("node", *r)
res = G.compile(abp)
L("compile", res)
assert "errors=0" in res, res
for n in G.get_nodes(g):
    if n.get_class().get_name() == "AnimGraphNode_KawaiiPhysics":
        L("check", G.get_property(n, "Node.RootBone"), "add", G.get_property(n, "Node.AdditionalRootBones")[:200],
          "caps", G.get_property(n, "Node.CapsuleLimits")[:300])
        L("check", G.get_property(n, "Node.PhysicsSettings"), "grav", G.get_property(n, "Node.Gravity"),
          "stiffcurve", G.get_property(n, "Node.StiffnessCurveData")[:200])
eal.save_loaded_asset(abp)
open(os.path.join(RUN, "abp_graph.txt"), "w", encoding="utf-8").write(G.export_graph(g))
L("ABP_OK")
