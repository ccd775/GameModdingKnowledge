"""Convert Karin atlases to DD2 Character_Default texture sets (.tex.251211553).

Per atlas:  <name>_ALBD (BC7 sRGB: RGB colour, A=1 dielectric)
            <name>_NRMR (BC7: RG normal XY in DD2/OpenGL convention, B normal Z, A roughness)
            <name>_ATOC (BC1: R alpha, G translucency=1, B occlusion=1)
Channel semantics were measured on DD2 textures (see SOP section 5.2).

usage: python build_karin_textures.py <out_natives_root> --src <image dir> --work-dir <dir> [--size 2048]
       [--profile picodra|original] [--native-dir <dir>] [--texconv <texconv.exe>] [--dd2tool <DD2Tool.exe>]
  --src: picodra = the model's textures folder (the *_4096.png atlases below); original: the images written by
  scripts/blender/prepare_karin_original.py (<out_dir>/images; no normal maps: flat normals). A page smaller than
  --size keeps its own size.
  --work-dir: temporary PNG/DDS go to <work-dir>/tex_tmp, the manifest to <work-dir>/<manifest name> (or --manifest).
  --native-dir (or DD2_NATIVE_DIR): DD2Tool extract output with natives/stm/character/... (the template .tex).
  --texconv / --dd2tool (or the TEXCONV / DD2TOOL environment variables; default: found on PATH).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
TEXCONV = None    # texconv.exe (DirectXTex), set by main()
DD2TOOL = None    # DD2Tool.exe (dd2tool/ of this kit), set by main()
TEMPLATE_TEX = None   # set by main(): the native .tex whose header dds2tex reuses
TEMPLATE_REL = "natives/stm/character/_kit/_equipment/pants/002/wl_002_0_0_ALBD.tex.251211553"

# per model: native dir, manifest name, atlas key -> (colour png, normal png or None, roughness 0..1, flip normal green)
PROFILES = {
    "picodra": {
        "native_dir": "Character/_karin/tex", "manifest": "karin_textures.json",
        "atlases": {
            "karin_clotha": ("Karin_PT_Atlas_Clothing_A_ColorAlpha_4096.png", "Karin_PT_Atlas_Clothing_A_Normal_4096.png", 0.75, True),
            "karin_clothb": ("Karin_PT_Atlas_Clothing_B_Accessories_ColorAlpha_4096.png", "Karin_PT_Atlas_Clothing_B_Accessories_Normal_4096.png", 0.7, True),
            "karin_hair": ("Karin_PT_Atlas_Hair_Head_ColorAlpha_4096.png", "Karin_PT_Atlas_Hair_Head_Normal_4096.png", 0.65, True),
            "karin_skin": ("Karin_PT_Atlas_Skin_Face_ColorAlpha_4096.png", None, 0.6, False),
        },
    },
    "original": {
        "native_dir": "Character/_karin_original/tex", "manifest": "karin_original_textures.json",
        "atlases": {
            "karin_skin": ("Karin_Body.png", None, 0.6, False),
            "karin_face": ("Karin_Face.png", None, 0.6, False),
            "karin_eyealpha": ("Karin_Alpha.png", None, 0.5, False),
            "karin_hair": ("Karin_Hair.png", None, 0.65, False),
            "karin_costume": ("Karin_Costume.png", None, 0.75, False),
        },
    },
}


def bleed(rgb, alpha, levels=12):
    """Push-pull colour dilation into transparent texels so mips do not pick up black fringes."""
    h, w = alpha.shape
    m = (alpha > 0.5).astype(np.float32)
    pyr = [(rgb * m[..., None], m)]
    c, a = pyr[0]
    for _ in range(levels):
        if min(c.shape[:2]) <= 2:
            break
        hh, ww = c.shape[0] // 2, c.shape[1] // 2
        c = c[:hh * 2, :ww * 2].reshape(hh, 2, ww, 2, 3).sum(axis=(1, 3))
        a = a[:hh * 2, :ww * 2].reshape(hh, 2, ww, 2).sum(axis=(1, 3))
        pyr.append((c, a))
    # pull: fill from coarse to fine
    filled = pyr[-1][0] / np.maximum(pyr[-1][1], 1e-6)[..., None]
    for c, a in reversed(pyr[:-1]):
        up = np.repeat(np.repeat(filled, 2, axis=0), 2, axis=1)
        up = np.pad(up, ((0, c.shape[0] - up.shape[0]), (0, c.shape[1] - up.shape[1]), (0, 0)), mode="edge")
        own = c / np.maximum(a, 1e-6)[..., None]
        wgt = np.clip(a, 0, 1)[..., None]
        filled = own * wgt + up * (1 - wgt)
    out = rgb.copy()
    hole = m < 0.5
    out[hole] = filled[hole]
    return out


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"{cmd}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def to_tex(png, fmt, out_tex, tmp):
    run([TEXCONV, "-nologo", "-y", "-dx10", "-m", "0", "-f", fmt, "-bc", "q" if fmt.startswith("BC7") else "d", "-o", tmp, png])
    dds = Path(tmp) / (Path(png).stem + ".dds")
    out_tex.parent.mkdir(parents=True, exist_ok=True)
    print(run([DD2TOOL, "dds2tex", TEMPLATE_TEX, dds, out_tex]).strip())


def tool(ap, given, env, name):
    path = given or os.environ.get(env) or shutil.which(name)
    if not path or not Path(path).is_file():
        ap.error(f"{name} not found: pass --{name.split('.')[0].lower()} or set {env}")
    return Path(path)


def main():
    global TEXCONV, DD2TOOL, TEMPLATE_TEX
    ap = argparse.ArgumentParser()
    ap.add_argument("out_root")
    ap.add_argument("--size", type=int, default=2048)
    ap.add_argument("--profile", default="picodra", choices=sorted(PROFILES))
    ap.add_argument("--src", required=True, help="folder with the profile's source images")
    ap.add_argument("--work-dir", required=True, help="temporary images (tex_tmp/) and the manifest")
    ap.add_argument("--manifest", help="manifest path (default: <work-dir>/<profile manifest name>)")
    ap.add_argument("--native-dir", default=os.environ.get("DD2_NATIVE_DIR"),
                    help="DD2Tool extract output folder with natives/stm (default: DD2_NATIVE_DIR)")
    ap.add_argument("--texconv", help="texconv.exe (default: TEXCONV or PATH)")
    ap.add_argument("--dd2tool", help="DD2Tool.exe (default: DD2TOOL or PATH)")
    a = ap.parse_args()
    if not a.native_dir:
        ap.error("set --native-dir or DD2_NATIVE_DIR to the folder DD2Tool extract wrote (it holds natives/stm)")
    TEMPLATE_TEX = Path(a.native_dir) / TEMPLATE_REL
    if not TEMPLATE_TEX.is_file():
        ap.error(f"template texture not found: {TEMPLATE_TEX}")
    TEXCONV = tool(ap, a.texconv, "TEXCONV", "texconv.exe")
    DD2TOOL = tool(ap, a.dd2tool, "DD2TOOL", "DD2Tool.exe")
    prof = PROFILES[a.profile]
    SRC, NATIVE_DIR = Path(a.src), prof["native_dir"]
    if not SRC.is_dir():
        ap.error(f"--src is not a folder: {SRC}")
    manifest_path = Path(a.manifest) if a.manifest else Path(a.work_dir) / prof["manifest"]
    out_root = Path(a.out_root)
    tmp = Path(a.work_dir) / "tex_tmp"
    tmp.mkdir(parents=True, exist_ok=True)
    manifest = {}
    for key, (col, nrm, rough, flip) in prof["atlases"].items():
        im = Image.open(SRC / col).convert("RGBA")
        size = min(a.size, max(im.size))
        arr = np.asarray(im).astype(np.float32) / 255.0
        rgb, alpha = arr[..., :3], arr[..., 3]
        rgb = bleed(rgb, alpha)
        S = (size, size)
        albd = Image.fromarray((np.dstack([rgb, np.ones_like(alpha)]) * 255 + 0.5).astype(np.uint8), "RGBA").resize(S, Image.LANCZOS)
        p = tmp / f"{key}_ALBD.png"
        albd.save(p)
        to_tex(p, "BC7_UNORM_SRGB", out_root / NATIVE_DIR / f"{key}_ALBD.tex.251211553", tmp)

        if nrm:
            n = np.asarray(Image.open(SRC / nrm).convert("RGB").resize(S, Image.LANCZOS)).astype(np.float32) / 255.0
            v = n * 2 - 1
            if flip:
                v[..., 1] = -v[..., 1]
            v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
            n = v * 0.5 + 0.5
        else:
            n = np.zeros((size, size, 3), np.float32)
            n[..., 0] = 0.5
            n[..., 1] = 0.5
            n[..., 2] = 1.0
        nrmr = np.dstack([n, np.full(n.shape[:2], rough, np.float32)])
        p = tmp / f"{key}_NRMR.png"
        Image.fromarray((nrmr * 255 + 0.5).astype(np.uint8), "RGBA").save(p)
        to_tex(p, "BC7_UNORM", out_root / NATIVE_DIR / f"{key}_NRMR.tex.251211553", tmp)

        al = np.asarray(Image.fromarray((alpha * 255 + 0.5).astype(np.uint8), "L").resize(S, Image.LANCZOS)).astype(np.float32) / 255.0
        atoc = np.dstack([al, np.ones_like(al), np.ones_like(al), np.ones_like(al)])
        p = tmp / f"{key}_ATOC.png"
        Image.fromarray((atoc * 255 + 0.5).astype(np.uint8), "RGBA").save(p)
        to_tex(p, "BC1_UNORM", out_root / NATIVE_DIR / f"{key}_ATOC.tex.251211553", tmp)
        manifest[key] = {s: f"{NATIVE_DIR}/{key}_{s}.tex" for s in ("ALBD", "NRMR", "ATOC")}
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=1), encoding="utf-8")
    print("TEXTURES_DONE")


if __name__ == "__main__":
    sys.exit(main())
