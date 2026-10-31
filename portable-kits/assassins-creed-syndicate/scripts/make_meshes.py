"""Karin_Original meshes (and physics skeletons) for both twins: fit -> face rig -> LOD export -> import -> Karin_Phys.

  python make_meshes.py <out_root> [--stage 1|2] [--twins jacob,evie] [--face-args "..."] [--no-face]

Inputs: ACS_SRC_BLEND (prep_karin_original.py output, same FBX as AC Unity), the fit-frame
probe GLBs <out_root>/probe/<twin>_fitframe.glb (export-glb of ACVI_CHR_SHR_Male / _Female + the twin's head LOD0 +
an outfit body + its body add-on + the twin's head skeleton, then glb_names.py and glb_rotate.py +90; kit README).
Machine paths (portable kit): ACS_BLENDER, ACS_SRC_BLEND, ACS_TEMPLATES (ACVI_CHR_P_JacobFrye_Hair.Skeleton.xml) and
the build_mod.py variables (import-glb runs through the harness) are checked first; --phys-roots / ACS_PHYS_ROOTS
(comma-separated Karin chain roots) for stage 2.
Writes <out_root>/<twin>/karin_lod0..3.Mesh (the mesh_root of build_mod.py) and, for stage 2,
<out_root>/<twin>/Karin_Phys_<twin>.Skeleton.xml (+ .BallJointCommonData.xml / .LiteRagdoll.xml).
Stage 1 = no physics chains, no face rig (every Karin bone collapses onto the base skeleton).
Both twins share the base-skeleton joint positions (ACVI_CHR_SHR_Male == _Female, hips 0.96, head 1.6654), so the
body fit is identical; the face rig follows each twin's own head skeleton (Jacob's eyes 2.2 cm higher than Evie's).
"""
import argparse
import os
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_mod  # noqa: E402

# machine paths (portable kit): environment variables, checked in main() before anything is written
BLENDER = os.environ.get("ACS_BLENDER", "")  # Blender 5.0.1 blender.exe
SRC = os.environ.get("ACS_SRC_BLEND", "")    # karin_original_src.blend (prep_karin_original.py)
BLENDER_SCRIPTS = os.path.join(HERE, "blender")
FIT_ARGS = ["--scale", "auto", "--ground", "0.0", "--foot-scale", "1.0", "--foot-squash", "0.8",
            "--hide-band", "body_2:0.20:0.46:0.15"]  # knee skin under the over-knee socks (top z 0.524), 2026-10-30
SPLIT_NORMALS = "skirt:40"  # flat pleat panels, sharp folds (the toon normals smudged the skirt in game), 2026-10-30
HAIR_TEMPLATE = os.path.join(os.environ.get("ACS_TEMPLATES", ""), "ACVI_CHR_P_JacobFrye_Hair.Skeleton.xml")


def sh(cmd, log):
    with open(log, "w", encoding="utf-8") as f:
        r = subprocess.run(cmd, stdout=f, stderr=subprocess.STDOUT)
    txt = open(log, encoding="utf-8", errors="replace").read()
    keep = [l for l in txt.splitlines() if l.startswith(("FIT", "FACE", "EXPORT", "PHYS_SKEL", "wrote", "Traceback", "Error"))]
    print("\n".join("    " + l[:300] for l in keep))
    if r.returncode != 0 or "Traceback" in txt:
        raise SystemExit(f"failed: {' '.join(cmd[:4])} ... (log {log})")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_root", help="holds probe/<twin>_fitframe.glb; gets <twin>/karin_lod0..3.Mesh")
    ap.add_argument("--stage", type=int, default=2, choices=(1, 2))
    ap.add_argument("--twins", default=",".join(build_mod.CHARS))
    ap.add_argument("--face-args", default="", help="extra face_rig.py arguments (one string)")
    ap.add_argument("--no-face", action="store_true")
    ap.add_argument("--phys-roots", default=os.environ.get("ACS_PHYS_ROOTS", ""),
                    help="comma-separated chain roots for fit_karin.py --phys (stage 2; default ACS_PHYS_ROOTS)")
    a = ap.parse_args()
    need = ["ACS_BLENDER", "ACS_SRC_BLEND", "ACS_TEMPLATES"] + list(build_mod.ENV)
    missing = [n for n in dict.fromkeys(need) if not os.environ.get(n)]
    if missing or (a.stage >= 2 and not a.phys_roots):
        raise SystemExit("set " + ", ".join(missing + ([] if a.phys_roots or a.stage < 2 else ["ACS_PHYS_ROOTS"]))
                         + " (see the kit README)")
    out = os.path.abspath(a.out_root)
    stage = a.stage
    twins = a.twins.split(",")
    face_args = shlex.split(a.face_args)
    for twin in twins:
        c = build_mod.CHARS[twin]
        d = os.path.join(out, twin)
        os.makedirs(d, exist_ok=True)
        probe = os.path.join(out, "probe", f"{twin}_fitframe.glb")
        fit = os.path.join(d, "fit.blend")
        print(twin, "fit")
        phys = ["--phys", a.phys_roots.strip()] if stage >= 2 else []
        sh([BLENDER, "-b", "--factory-startup", "--python", os.path.join(BLENDER_SCRIPTS, "fit_karin.py"), "--", probe, SRC, fit,
            *FIT_ARGS, *phys], os.path.join(d, "fit.log"))
        src_blend = fit
        if stage >= 2 and not a.no_face:
            print(twin, "face")
            src_blend = os.path.join(d, "fit_face.blend")
            sh([BLENDER, "-b", fit, "--python", os.path.join(BLENDER_SCRIPTS, "face_rig.py"), "--", SRC, src_blend,
                "--report", os.path.join(d, "face.json"), *face_args], os.path.join(d, "face.log"))
        print(twin, "export")
        sh([BLENDER, "-b", src_blend, "--python", os.path.join(BLENDER_SCRIPTS, "export_karin_lods.py"), "--", d,
            "--ratios", "1,0.5,0.25,0.12", "--profile", "acs_weapon", "--mat-base", hex(c["base"]), "--keep-full", "Body",
            "--split-normals", SPLIT_NORMALS],
           os.path.join(d, "export.log"))
        for i, lod in enumerate(c["lods"]):
            g, ga = os.path.join(d, f"karin_lod{i}.glb"), os.path.join(d, f"karin_lod{i}_acs.glb")
            subprocess.run([sys.executable, "-B", os.path.join(HERE, "glb_rotate.py"), g, ga, "-90"], check=True,
                           stdout=subprocess.DEVNULL)
            line = build_mod.run("import-glb", ga, "0", os.path.join(d, f"karin_lod{i}.Mesh"), f"{lod:016X}").splitlines()[-1]
            print("   ", line[:200])
        if stage >= 2:
            print(twin, "physics skeleton")
            pid = c["base"] + build_mod.PHYS
            sh([sys.executable, "-B", os.path.join(HERE, "acs_phys_skel.py"), HAIR_TEMPLATE,
                os.path.join(d, "karin_lod0_acs.glb"), os.path.join(d, f"Karin_Phys_{twin}.Skeleton.xml"),
                "--id", str(pid), "--report", os.path.join(d, "phys_report.json")], os.path.join(d, "phys.log"))
    print("MESHES_OK", out)


if __name__ == "__main__":
    main()
