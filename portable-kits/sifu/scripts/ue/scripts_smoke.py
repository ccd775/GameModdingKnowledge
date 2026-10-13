# Usage: ue_run.ps1 scripts_smoke.py <out.json>   (engine version + SifuModToolsLibrary functions: plugin loaded?)
import unreal, json, os
ARGS = json.load(open(os.environ["SIFU_PY_ARGS"], encoding="utf-8-sig"))
out = {"engine": unreal.SystemLibrary.get_engine_version(),
       "lib": [n for n in dir(unreal.SifuModToolsLibrary) if not n.startswith('_')]}
open(ARGS[0], "w").write(json.dumps(out, indent=1))
