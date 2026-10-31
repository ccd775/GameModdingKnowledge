# UE 5.7 editor Python: Karin textures as virtual textures (the game's character materials sample VT) and the Karin
# MIs as layer-0 overrides only (layer 1 = the parent's fabric detail, left untouched), assigned to every Karin mesh.
import unreal, sys
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
tools = unreal.AssetToolsHelpers.get_asset_tools()
lib = unreal.PBZModToolsLibrary
args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
MOD = "/HuaShira/Mods/KarinPBZ"
TG = unreal.TextureGroup
TCS = unreal.TextureCompressionSettings

def reimport(png, name):
    t = unreal.AssetImportTask()
    t.filename = png; t.destination_path = MOD + "/Textures"; t.destination_name = name
    t.replace_existing = True; t.automated = True; t.save = False; t.factory = unreal.TextureFactory()
    tools.import_asset_tasks([t])
    return unreal.load_asset(MOD + "/Textures/" + name)
SPEC = {   # name: (srgb, compression, lod group, no alpha)
    "Karin_Body": (True, TCS.TC_DEFAULT, TG.TEXTUREGROUP_PROJECT02, True),
    "Karin_Face": (True, TCS.TC_DEFAULT, TG.TEXTUREGROUP_PROJECT02, True),
    "Karin_Hair": (True, TCS.TC_DEFAULT, TG.TEXTUREGROUP_PROJECT02, True),
    "Karin_Costume": (True, TCS.TC_DEFAULT, TG.TEXTUREGROUP_PROJECT02, True),
    "Karin_FlatN": (False, TCS.TC_NORMALMAP, TG.TEXTUREGROUP_PROJECT02, False),
    "Karin_ARM": (False, TCS.TC_DEFAULT, TG.TEXTUREGROUP_CHARACTER_SPECULAR, True),
    "Karin_ARMMatte": (False, TCS.TC_DEFAULT, TG.TEXTUREGROUP_CHARACTER_SPECULAR, True),
    "Karin_SCMT": (False, TCS.TC_DEFAULT, TG.TEXTUREGROUP_CHARACTER_SPECULAR, False),
    "Karin_Gray": (True, TCS.TC_DEFAULT, TG.TEXTUREGROUP_PROJECT02, True),
}
TEX = {}
for n, (srgb, comp, group, noalpha) in SPEC.items():
    tex = reimport(RUN + "/textures/" + n + ".png", "T_" + n) if n in ("Karin_FlatN", "Karin_ARM", "Karin_ARMMatte", "Karin_Gray", "Karin_SCMT") else unreal.load_asset(MOD + "/Textures/T_" + n)
    tex.set_editor_property("srgb", srgb)
    tex.set_editor_property("compression_settings", comp)
    tex.set_editor_property("lod_group", group)
    tex.set_editor_property("compression_no_alpha", noalpha)
    tex.set_editor_property("virtual_texture_streaming", True)
    eal.save_loaded_asset(tex)
    TEX[n] = tex
    L("tex", n, tex.blueprint_get_size_x(), "vt", tex.get_editor_property("virtual_texture_streaming"))

LAYER = 1
SKIN = [("Normal", "Karin_FlatN"), ("Mix", "Karin_ARM"), ("SCMT_Map", "Karin_SCMT")]
CLOTH = [("Normal", "Karin_FlatN"), ("Mix", "Karin_ARM")]
# Mix is AO / roughness / metallic (the vanilla T_ZeroHun_Cloth_02_ARM). The costume (skirt, pullover, socks) is fully
# rough: at 0.67 the dark mauve skirt showed MSM_Cloth sheen patches that read as wet.
COSTUME = [("Normal", "Karin_FlatN"), ("Mix", "Karin_ARMMatte")]
SPECS = {"MI_Karin_Skin": ("Karin_Body", SKIN, [("SkinMicroNormalIntensity", 0.3)]),
         "MI_Karin_Face": ("Karin_Face", SKIN, [("SkinMicroNormalIntensity", 0.2)]),
         "MI_Karin_Hair": ("Karin_Hair", CLOTH, []),
         "MI_Karin_Costume": ("Karin_Costume", COSTUME, [])}
# Rain wetness and drops off for the clothes and hair (the game wets the lower body through CharacterWetCurve_Hun):
# global parameters of the game's MA_Character (defaults 0.6 / 0.6 / 1 / 1), set unchecked because the stand-in
# parents in this project do not carry them
DRY = [("Wetness Min", 0.0), ("Wetness Max", 0.0), ("RainDrops | StaticDrops Intensity", 0.0), ("RainDrops | DrippingDrop Intensity", 0.0)]
GLOBAL = {"MI_Karin_Hair": DRY, "MI_Karin_Costume": DRY}
MIS = {}
for name, (albedo, rest, scalars) in SPECS.items():
    mi = unreal.load_asset(MOD + "/Materials/" + name)
    lib.clear_material_instance_parameters(mi)
    lib.set_material_texture_parameter(mi, "Albedo", LAYER, 0, TEX[albedo])
    for p, t in rest:
        lib.set_material_texture_parameter(mi, p, LAYER, 0, TEX[t])
    for p, v in scalars:
        lib.set_material_scalar_parameter(mi, p, LAYER, 0, v)
    for p, v in GLOBAL.get(name, []):
        lib.set_material_scalar_parameter(mi, p, 0, -1, v)
    unreal.MaterialEditingLibrary.update_material_instance(mi)
    eal.save_loaded_asset(mi)
    MIS[name] = mi
    L(name, lib.dump_material_instance_parameters(mi))

MIS.update({"MI_Karin_Skirt": MIS["MI_Karin_Costume"], "MI_Karin_HairTail": MIS["MI_Karin_Hair"], "MI_Karin_Tail": MIS["MI_Karin_Hair"],
            "MI_Karin_Ear": MIS["MI_Karin_Hair"], "MI_Karin_HairFront": MIS["MI_Karin_Hair"],
            "MI_Karin_SkirtSim": MIS["MI_Karin_Costume"]})   # simulation shell of the skirt, not rendered

def assign(path, default=None):
    mesh = unreal.load_asset(path)
    out = []
    for m in mesh.get_editor_property("materials"):
        slot = str(m.get_editor_property("material_slot_name"))
        m.set_editor_property("material_interface", MIS.get(slot) or MIS[default])
        out.append(m)
    mesh.set_editor_property("materials", out)
    eal.save_loaded_asset(mesh)
    L("assigned", path, [m.get_editor_property("material_interface").get_name() for m in out])
H, Y = "/HuaShira/Characters/Hero/Hero_Hun", "/HuaShira/Characters/Hero/Young_Hun"
for p in (H + "/SkinParts/Hun_Body_Simple", "/HuaShira/Characters/Hero/Hero_Hun_Climax/SkinParts/Hun_Body_Climax", H + "/SkinParts/Hun_Head_New", Y + "/SkinParts/Hun_Young_Body", Y + "/SkinParts/Hun_Young_Head"):
    assign(p)
for p in (H + "/Hun_Invs", H + "/SkinParts/Hun_Cloth", H + "/Hats/Hun_Hat_00", H + "/Hats/Hun_Hat_01", Y + "/SkinParts/Hun_young_Hair"):
    assign(p, "MI_Karin_Skin")
for p in (H + "/SkinParts/Hun_Scarf", H + "/SkinParts/Hun_Scarf_Climax", H + "/SkinParts/Hun_Hair_Band", H + "/SkinParts/Hun_BrowLashCard",
          H + "/SkinParts/Cloth/CA_Hun_UpperCloth", H + "/SkinParts/Cloth/CA_Hun_Skirt", H + "/SkinParts/Cloth/CA_Hun_Cape",
          H + "/SkinParts/Cloth/CA_Hun_UpperCloth_Climax", H + "/SkinParts/Cloth/CA_Hun_Skirt_Climax", H + "/SkinParts/Cloth/CA_Hun_Cape_Climax",
          H + "/SkinParts/Cloth/CA_Hun_Hair01", Y + "/SkinParts/Hun_Young_BrowLashCard", Y + "/SkinParts/Cloth/CA_Hun_YOung_Cloth02",
          Y + "/SkinParts/Cloth/CA_Hun_Young_Hair01", Y + "/SkinParts/Cloth/CA_Hun_Young_Cloth01"):
    assign(p, "MI_Karin_Skin")
if eal.does_directory_exist(MOD + "/Test"):
    eal.delete_directory(MOD + "/Test")
L("FIXMATS_OK")
