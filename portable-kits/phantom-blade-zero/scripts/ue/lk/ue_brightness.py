# UE 5.7 editor Python: tone down the colour textures (near-white anime albedo blows out under the game's lighting).
# Lenko fork: textures and factors from the run's materials.json ("brightness", written by build_lenko.py; the factors
# are Karin_Original's: 0.78 hair / costume, 0.9 skin / face).
#   UnrealEditor-Cmd ProjectPBZ.uproject -run=pythonscript -script="ue_brightness.py <run_dir>"
import unreal, sys, json
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
args = [a for a in sys.argv[1:] if not a.startswith("-")]
RUN = args[0].replace("\\", "/")
for n, b in json.load(open(RUN + "/materials.json", encoding="utf-8"))["brightness"].items():
    t = unreal.load_asset("/HuaShira/Mods/KarinPBZ/Textures/T_" + n)
    assert t, "no texture T_" + n
    t.set_editor_property("adjust_brightness", b)
    unreal.EditorAssetLibrary.save_loaded_asset(t)
    L(n, "brightness", t.get_editor_property("adjust_brightness"))
L("BRIGHTNESS_OK")
