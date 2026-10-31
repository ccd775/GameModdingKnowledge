# UE 5.7 editor Python: tone down Karin's colour textures (near-white anime albedo blows out under the game's lighting).
import unreal
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
for n, b in (("Karin_Hair", 0.78), ("Karin_Costume", 0.78), ("Karin_Body", 0.9), ("Karin_Face", 0.9)):
    t = unreal.load_asset("/HuaShira/Mods/KarinPBZ/Textures/T_" + n)
    t.set_editor_property("adjust_brightness", b)
    unreal.EditorAssetLibrary.save_loaded_asset(t)
    L(n, "brightness", t.get_editor_property("adjust_brightness"))
L("BRIGHTNESS_OK")
