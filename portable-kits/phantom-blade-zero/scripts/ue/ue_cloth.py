# UE 5.7 editor Python (run after the imports and ue_fixmats.py): materials for the cloth slots, the cloth collision
# physics asset, Chaos clothing on the skirt / twin tails / tail / ears sections of the body, no shadows from the hair
# (they blacked out the face under the bangs). adult: Hun_Body_Simple, then copied to Hun_Body_Climax (body of
# BP_Renewal_Hun_Climax). young: Hun_Young_Body, plus hidden stand-ins for the groom assets of the cutscene actors
# (BP_Seq_Young_Hun and the adult Seq hairstyles), which are bound to the original heads.
#   UnrealEditor-Cmd ProjectPBZ.uproject -run=pythonscript -script="ue_cloth.py <run_dir> <adult|young>"
import unreal, sys, json

args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
VARIANT = args[1]
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
lib = unreal.PBZModToolsLibrary
MOD = "/HuaShira/Mods/KarinPBZ"
H, Y = "/HuaShira/Characters/Hero/Hero_Hun", "/HuaShira/Characters/Hero/Young_Hun"
unreal.AssetRegistryHelpers.get_asset_registry().search_all_assets(True)   # headless runs start before the scan ends

MIS = {n: unreal.load_asset(MOD + "/Materials/" + n) for n in ("MI_Karin_Skin", "MI_Karin_Face", "MI_Karin_Hair", "MI_Karin_Costume")}
MIS.update({"MI_Karin_Skirt": MIS["MI_Karin_Costume"], "MI_Karin_HairTail": MIS["MI_Karin_Hair"], "MI_Karin_Tail": MIS["MI_Karin_Hair"],
            "MI_Karin_Ear": MIS["MI_Karin_Hair"], "MI_Karin_HairFront": MIS["MI_Karin_Hair"],
            "MI_Karin_SkirtSim": MIS["MI_Karin_Costume"]})   # simulation shell of the skirt, not rendered
SFX, PA_NAME = ("", "PA_Karin_ClothCollide") if VARIANT == "adult" else ("_Young", "PA_Karin_ClothCollide_Young")
body = unreal.load_asset(H + "/SkinParts/Hun_Body_Simple" if VARIANT == "adult" else Y + "/SkinParts/Hun_Young_Body")
out = []
for m in body.get_editor_property("materials"):
    slot = str(m.get_editor_property("material_slot_name"))
    m.set_editor_property("material_interface", MIS.get(slot, MIS["MI_Karin_Skin"]))
    out.append(m)
body.set_editor_property("materials", out)
L("materials", [str(m.get_editor_property("material_slot_name")) for m in out])

# cloth collision: kinematic capsules on the young skeleton (shipped with the mod)
coll = json.load(open(RUN + "/cloth_collision" + SFX + ".json", encoding="utf-8"))
pa_path = MOD + "/" + PA_NAME
# reuse the asset (build_physics_asset clears it): deleting it while the old clothing still references it makes the
# next save of the body assert in the async loader
pa = unreal.load_asset(pa_path) if eal.does_asset_exist(pa_path) else lib.create_physics_asset(MOD, PA_NAME, body)
L("collision PA", lib.build_physics_asset(pa, body, json.dumps(coll)))
eal.save_loaded_asset(pa)

L("removed clothing", lib.remove_all_clothing(body))
for c in json.load(open(RUN + "/cloth" + SFX + ".json", encoding="utf-8")):
    # "collide": false -> no collision asset (the ears sit partly inside the head sphere)
    L("cloth", c["slot"], lib.create_cloth_from_slot(body, c["slot"], c["name"], pa if c.get("collide", True) else None, float(c["max_distance"]),
                                                      json.dumps(c["mask"]), json.dumps(c.get("config", {}))))
# solver iterations and substeps (one solver for all cloth on the mesh): at 1 / 1 the ear shells crumpled and the
# thigh and buttock colliders were resolved once per frame
L("solver 3 iterations, 2 substeps on", lib.set_cloth_solver(body, 3, 2), "clothing assets")
L("no shadow", {s: lib.set_section_cast_shadow(body, s, False) for s in ("MI_Karin_Hair", "MI_Karin_HairFront", "MI_Karin_Ear")})
eal.save_loaded_asset(body)
if VARIANT == "adult":
    climax_path = "/HuaShira/Characters/Hero/Hero_Hun_Climax/SkinParts/Hun_Body_Climax"
    if eal.does_asset_exist(climax_path): eal.delete_asset(climax_path)
    climax = eal.duplicate_asset(body.get_path_name().split(".")[0], climax_path)
    lib.set_mesh_physics_asset(climax, unreal.load_asset(H + "/Hero_Hun_PhysicsAsset"))
    eal.save_loaded_asset(climax)
    L("climax body", climax.get_path_name(), len(climax.get_editor_property("mesh_clothing_assets")), "clothing assets")

# hidden stand-ins under the groom asset names (wrong class -> the GroomComponents get no asset)
GROOMS = {} if VARIANT == "adult" else {Y + "/SkinParts/Hun_young_Hair": ["/Game/PBZContent/Characters/Hero/Hun_Young/Mesh/V02/Hair/" + n for n in
              ("Hun_Young_Brow", "Hun_Young_Lash", "HunYoung_Hair_A", "HunYoung_Hair_B", "HunYoung_Hair_Bangs", "HunYoung_Hair_C", "HunYoung_Hair_Tails")],
          H + "/SkinParts/Hun_Cloth": ["/Game/PBZContent/Characters/Hero/Hun_New_V1/Mesh/" + n for n in
              ("Hun_Brow_V01", "Hun_Lash_V01", "Normal_Hair_Bangs", "Normal_Hair_End", "Normal_Hair_Main_Top", "Normal_Hair_Ponytail",
               "Normal_Hair_Sideburn", "Normal_Hair_Top_Hairline")]}
for src, dsts in GROOMS.items():
    for d in dsts:
        if eal.does_asset_exist(d): eal.delete_asset(d)
        eal.duplicate_asset(src, d)
        L("groom stand-in", d)
unreal.EditorAssetLibrary.save_directory("/HuaShira", only_if_is_dirty=True, recursive=True)
unreal.EditorAssetLibrary.save_directory("/Game", only_if_is_dirty=True, recursive=True)
L("CLOTH_OK", VARIANT)
