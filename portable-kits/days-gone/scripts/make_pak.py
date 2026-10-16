"""Assemble the Karin pak from cooked UE 4.11 assets and patched game packages.

usage: python make_pak.py <cooked_content_root> <out.pak> [--stage <dir>] [--normals npz [--positions npz]] [--phys uasset]
       [--skeleton uasset] [--extra <Content-relative path, e.g. Animation/X/Y>=<file.uasset>]...

- mesh   : cooked /Game/Characters/Deacon/parts/head/deacon_head_standard, skeleton import retargeted to the game's
           deacon_master_Skeleton, root bones' local pose set to the reference mod's layout
- textures: cooked /Game/Karin/Materials/Karin_*
- MIs    : copies of game MIs (their cooked static-permutation shader maps stay valid) with texture imports
           retargeted to Karin's textures / game blank textures, saved as /Game/Karin/Materials/MI_Karin_*; the export
           keeps the game MI's name and, when it has an inline shader map, the header keeps its exact size
           (retarget_inplace) because the game cannot load such an MI once its export moved inside the file
- looks  : every Deacon look's master part -> Karin mesh + MIs, other parts' meshes null
Game packages (DgExport raw) come from DG_CACHE: raw/BendGame/Content/... (the game MIs) and
looks/BendGame/Content/Characters/Deacon/looks/*.uasset (the 66 looks); the script stops when DG_CACHE is not set.
"""
import argparse, json, os, shutil, sys
TOOLS = os.path.dirname(os.path.abspath(__file__))     # the package / pak tools sit next to this script in the kit
sys.path.insert(0, TOOLS)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import upkg, shader_skips, retarget_inplace, dgpaths
from retarget_imports import retarget
from fix_root_pose import main as fix_root_pose
from patch_looks import patch as patch_look

MESH = "/Game/Characters/Deacon/parts/head/deacon_head_standard"
D = "/Game/Characters/Deacon/parts/head/"
BLANK_N = "/Game/Characters/Shared/BlankTextures/normal_blank_n"
BLACK = "/Game/Characters/Shared/detail_maps/char_blk"
KM = "/Game/Karin/Materials/"

# Deacon's material map (S/R/DPM/T) follows Deacon's head UVs and puts his pores/cavities on Karin -> neutral map
BLANK_M = "/Game/Characters/Shared/BlankTextures/material_roughNonMetal_m"
SKIN = {D + "deacon_head_n": BLANK_N, D + "deacon_head_wrinkle_delta_0": BLANK_N, D + "deacon_head_wrinkle_delta_1": BLANK_N,
        **{D + "deacon_head_wrinkle_mask_%d" % i: BLACK for i in range(5)},
        "/Game/Characters/Shared/Maps/char_m_head_m": BLANK_M}
# mesh slot order (FBX import): Face, Alpha, Body, Hair, Costume
MIS = [
    ("MI_Karin_Face", "Characters/Deacon/parts/head/mi_deacon_head.uasset", {D + "deacon_head_c": KM + "Karin_Face", **SKIN}),
    ("MI_Karin_Alpha", "Characters/Deacon/parts/head/mi_deacon_eyelash_hair.uasset",
     {"/Game/Characters/Shared/eyes/eyelashes_c": KM + "Karin_Alpha", "/Game/Characters/Shared/eyes/eyelashes_n": BLANK_N}),
    ("MI_Karin_Body", "Characters/Deacon/parts/head/mi_deacon_head.uasset", {D + "deacon_head_c": KM + "Karin_Body", **SKIN}),
    ("MI_Karin_Hair", "Characters/Deacon/parts/head/mi_deacon_head.uasset", {D + "deacon_head_c": KM + "Karin_Hair", **SKIN}),
    ("MI_Karin_Costume", "Characters/Deacon/parts/head/mi_deacon_head.uasset", {D + "deacon_head_c": KM + "Karin_Costume", **SKIN}),
]

def main(cooked, out_pak, stage=None, normals=None, phys=None, skeleton=None, extra=(), positions=None):
    RAW, LOOKS = dgpaths.raw_content(), dgpaths.looks_dir()     # under DG_CACHE; stops before anything is written
    stage = stage or os.path.splitext(out_pak)[0] + "_stage"
    if os.path.isdir(stage): shutil.rmtree(stage)
    report = {}
    def dst(game_path):
        p = os.path.join(stage, *game_path[len("/Game/"):].split("/")) + ".uasset"
        os.makedirs(os.path.dirname(p), exist_ok=True)
        return p
    # mesh
    src = os.path.join(cooked, *MESH[len("/Game/"):].split("/")) + ".uasset"
    pkg = upkg.Package(open(src, "rb").read())
    retarget(pkg, MESH + "_Skeleton", "/Game/Characters/Deacon/deacon_master_Skeleton")
    tmp = dst(MESH) + ".tmp"
    open(tmp, "wb").write(pkg.write())
    fix_root_pose(tmp, dst(MESH)); os.remove(tmp)
    if normals:   # VRM custom normals (UE imported with "Compute Normals"); needs numpy -> run with Blender's python
        import numpy as np, skelmesh_normals
        data, report["mesh_normals"] = skelmesh_normals.patch(open(dst(MESH), "rb").read(), np.load(normals))
        open(dst(MESH), "wb").write(data)
        if positions:   # vertex moves (Scripts/skirt_body_shrink.py); located with the normals dump's positions
            import skelmesh_positions
            data, report["mesh_positions"] = skelmesh_positions.patch(open(dst(MESH), "rb").read(),
                                                                      np.load(normals)["pos"], np.load(positions))
            open(dst(MESH), "wb").write(data)
    # textures
    for f in os.listdir(os.path.join(cooked, "Karin", "Materials")):
        if f.startswith("Karin_") and f.endswith(".uasset"):
            shutil.copy2(os.path.join(cooked, "Karin", "Materials", f), dst(KM + f[:-7]))
    # MIs
    mi_objects = []
    for name, src_rel, retargets in MIS:
        raw = open(os.path.join(RAW, src_rel), "rb").read()
        pkg = upkg.Package(raw)
        # MIs with an inline shader map break in game when their export moves inside the file (header growth), so the
        # name table is rewritten in place; the export keeps its game name and the looks import it by that name
        has_shader_map = bool(shader_skips.skip_records(pkg))
        try:
            how = retarget_inplace.retarget(pkg, retargets)
        except ValueError as e:
            if has_shader_map:
                raise SystemExit("%s: cannot retarget in place (%s)" % (name, e))
            pkg = upkg.Package(raw)
            for o, n in retargets.items():
                retarget(pkg, o, n)
            how = "header grows (%s)" % e
        data = pkg.write()
        q = upkg.Package(data)
        if has_shader_map:
            assert q.s['TotalHeaderSize'] == pkg.s['TotalHeaderSize'] and len(data) == len(raw), name
        report[name] = {"textures": [q.obj_path(-i - 1) for i, im in enumerate(q.imports)
                                     if q.name(im['ClassName']) == 'Texture2D'],
                        "shader_map": has_shader_map, "retarget": how, "size": [len(raw), len(data)]}
        open(dst(KM + name), "wb").write(data)
        mi_objects.append(KM + name + "." + q.name(q.exports[0]['Name']))
    # looks
    cfg = {"mesh": MESH, "materials": mi_objects}
    looks = {}
    for f in sorted(os.listdir(LOOKS)):
        data, rep = patch_look(os.path.join(LOOKS, f), cfg)
        open(dst("/Game/Characters/Deacon/looks/" + f[:-7]), "wb").write(data)
        looks[f] = rep["master"]
    report["looks"] = len(looks)
    if phys:   # player PhysicsAssetOverride with the chain bodies (pytools/physchain.py)
        shutil.copy2(phys, dst("/Game/Characters/Deacon/deacon_master_PhysicsAsset2"))
        report["physics_asset"] = phys
    if skeleton:   # game Skeleton with face_* in AnimationRelative mode (pytools/skel_retarget.py)
        shutil.copy2(skeleton, dst("/Game/Characters/Deacon/deacon_master_Skeleton"))
        report["skeleton"] = skeleton
    for game_path, f in extra:   # other patched game assets, e.g. the AnimBP with retargeted AnimDynamics nodes
        if not game_path.startswith("/Game/"):   # "Animation/..." form: Git Bash rewrites a leading "/Game/"
            game_path = "/Game/" + game_path
        shutil.copy2(f, dst(game_path))
        report.setdefault("extra", []).append(game_path)
    sys.path.insert(0, TOOLS)
    from pakwrite import main as pakwrite
    pakwrite([stage, out_pak])
    json.dump(report, open(out_pak + ".report.json", "w"), indent=1)
    print(json.dumps(report, indent=1)[:2000])

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("cooked", help="cooked content root: <project>/Saved/Cooked/WindowsNoEditor/BendGame/Content")
    ap.add_argument("out_pak")
    ap.add_argument("--stage", help="staging folder (default <out_pak without .pak>_stage; emptied first)")
    ap.add_argument("--normals", help="loop normals npz (scripts/blender/dump_loop_normals.py)")
    ap.add_argument("--positions", help="vertex moves npz (scripts/blender/skirt_body_shrink.py); needs --normals")
    ap.add_argument("--phys", help="PhysicsAsset override .uasset (physchain.py, rejected route)")
    ap.add_argument("--skeleton", help="game Skeleton .uasset (skel_retarget.py)")
    ap.add_argument("--extra", action="append", default=[], metavar="PATH=FILE",
                    help="other game asset, e.g. Animation/Deacon/Deacon_VimBlueprint=<file.uasset>")
    args = ap.parse_args()
    main(args.cooked, args.out_pak, args.stage, args.normals, args.phys, args.skeleton,
         [tuple(x.split("=", 1)) for x in args.extra], args.positions)
