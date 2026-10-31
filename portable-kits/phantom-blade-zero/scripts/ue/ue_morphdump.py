# UE 5.7 editor Python: morph targets of the Karin face meshes (the adult face is the lash card mesh) and their delta stats.
import unreal, json
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
for p in ("/HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_Body_Simple", "/HuaShira/Characters/Hero/Hero_Hun_Climax/SkinParts/Hun_Body_Climax",
          "/HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_Head_New", "/HuaShira/Characters/Hero/Hero_Hun/SkinParts/Hun_BrowLashCard",
          "/HuaShira/Characters/Hero/Young_Hun/SkinParts/Hun_Young_Head"):
    m = unreal.load_asset(p)
    d = json.loads(unreal.PBZModToolsLibrary.dump_morph_targets(m))
    L("MORPHS", p.rsplit("/", 1)[1], len(d), "max_n", max([v["max_n"] for v in d.values()] or [0]),
      "clothing", len(m.get_editor_property("mesh_clothing_assets")), "slots", [str(x.get_editor_property("material_slot_name")) for x in m.get_editor_property("materials")])
L("MORPHDUMP_OK")
