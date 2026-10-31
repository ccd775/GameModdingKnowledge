# UE 5.7 editor Python (after ue_cloth.py): the mod's Hun_CopyPose and Hun_CopyPose_Head for the adult face.
# The face is on the lash card (gameplay) and, collapsed inside the head, on the head (Hun_Head_New, restored by its
# morph KarinFaceShow). In gameplay the head component's own anim blueprint does not drive its morphs (blinks added to
# Hun_CopyPose and Hun_CopyPose_Head never showed there, while the same overlay on the lash card did), and the body
# (the leader, PBZ_ABP_Hun_Base) carries no face curves. The cutscene actors (BP_Seq_Hun*, BP_Seq_Young_Hun) run the
# head's Hun_CopyPose and hide the lash card (bInfluencedByMainHairMode). So both classes are rebuilt as the vanilla
# pose copy (Hun_CopyPose_Head: plus DefaultSlot from neck_01 down) with
#   - a looping curve-only blink (A_Karin_Blink) by max value, except on cutscene actors (owning actor class name
#     contains "BP_Seq"; their face animation blinks) -> the lash-card face blinks in gameplay;
#   - KarinFaceShow at 1 always (A_Karin_FaceShow) -> the head's face appears wherever its own anim drives it.
# Each class is first built with the gate "!Actor" and run in the editor world on a plain actor (must not blink, must
# show), then with the real gate (must blink and show). PBZModToolsLibrary.TestCopyPoseAnim reads the anim instance's
# curve; its morph value is the SetMorphTarget override, always 0 here.
#   UnrealEditor-Cmd ProjectPBZ.uproject -run=pythonscript -script="ue_blink.py"
import unreal, json

L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.PBZModToolsLibrary
HUN = "/HuaShira/Characters/Hero/Hero_Hun"
MOD = "/HuaShira/Mods/KarinPBZ"
unreal.AssetRegistryHelpers.get_asset_registry().search_all_assets(True)   # headless runs start before the scan ends
skel = unreal.load_asset(HUN + "/Hun_Skin_Skeleton")

# 14 s loop, five blinks (one double), about 21 per minute; a blink closes in 70 ms, holds 40 ms, opens in 150 ms
LOOP = 14.0
BLINKS = [1.0, 5.2, 8.6, 8.95, 12.3]
keys = [[0.0, 0.0]]
for t in BLINKS:
    keys += [[t, 0.0], [t + 0.07, 1.0], [t + 0.11, 1.0], [t + 0.26, 0.0]]
keys.append([LOOP, 0.0])
curves = {"CTRL_expressions_eyeBlinkL": keys, "CTRL_expressions_eyeBlinkR": keys}

anim_path = MOD + "/Anim/A_Karin_Blink"
if not eal.does_asset_exist(anim_path):
    fac = unreal.AnimSequenceFactory()
    fac.set_editor_property("target_skeleton", skel)
    tools.create_asset("A_Karin_Blink", MOD + "/Anim", unreal.AnimSequence, fac)
anim = unreal.load_asset(anim_path)
L("blink sequence", lib.set_curve_sequence(anim, LOOP, json.dumps(curves)))
eal.save_loaded_asset(anim)
show_path = MOD + "/Anim/A_Karin_FaceShow"
if not eal.does_asset_exist(show_path):
    fac = unreal.AnimSequenceFactory()
    fac.set_editor_property("target_skeleton", skel)
    tools.create_asset("A_Karin_FaceShow", MOD + "/Anim", unreal.AnimSequence, fac)
show = unreal.load_asset(show_path)
L("show sequence", lib.set_curve_sequence(show, 1.0, json.dumps({"KarinFaceShow": [[0.0, 1.0], [1.0, 1.0]]})))
eal.save_loaded_asset(show)

head = unreal.load_asset(HUN + "/SkinParts/Hun_Head_New")
ok = True
for name, slot, slot_root in (("Hun_CopyPose", "", ""), ("Hun_CopyPose_Head", "DefaultSlot", "neck_01")):
    abp_path = HUN + "/" + name
    if not eal.does_asset_exist(abp_path):
        fac = unreal.AnimBlueprintFactory()
        fac.set_editor_property("target_skeleton", skel)
        fac.set_editor_property("parent_class", unreal.AnimInstance)
        tools.create_asset(name, HUN, unreal.AnimBlueprint, fac)
    abp = unreal.load_asset(abp_path)
    for gate, want in (("!Actor", 0.0), ("!BP_Seq", 1.0)):
        res = lib.build_copy_pose_overlay_anim_bp(abp, anim, gate, slot, slot_root, show)
        L(name, gate, res)
        ok = ok and not res.startswith("ERROR")
        # 1.09 s is inside the first blink (closed from 1.07 to 1.11 s)
        for curve, expect in (("CTRL_expressions_eyeBlinkL", want), ("KarinFaceShow", 1.0)):
            t = lib.test_copy_pose_anim(eal.load_blueprint_class(abp_path), head, 1.09, 33, curve)
            L(name, gate, "test", curve, t)
            try:
                r = json.loads(t)
                good = abs(r["weight"] - want) < 0.01 and abs(r["curve"] - expect) < 0.05
            except Exception:
                good = False
            ok = ok and good
    eal.save_loaded_asset(abp)
if ok:
    L("BLINK_OK")
