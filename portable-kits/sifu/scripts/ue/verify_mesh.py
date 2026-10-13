# Usage: ue_run.ps1 verify_mesh.py <out.json>   (writes the LOD0 section summary of the imported SK_W_MainChar_01)
import json, os, unreal
ARGS = json.load(open(os.environ["SIFU_PY_ARGS"], encoding="utf-8-sig"))
mesh = unreal.EditorAssetLibrary.load_asset("/Game/Characters/MainChar/W/Meshes/SK_W_MainChar_01")
open(ARGS[0], "w").write(unreal.SifuModToolsLibrary.dump_sections(mesh))
unreal.log("VERIFY_DONE")
