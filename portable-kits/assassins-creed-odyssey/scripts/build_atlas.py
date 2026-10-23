"""Build the 2x2 Karin_Original atlas (see aco_pack_atlas.py) and its BC7 DDS.

  python build_atlas.py <src_tex dir> <out_dir> [--size 4096] [--texconv <texconv.exe>]

Writes <out_dir>/karin_atlas.png and karin_atlas.dds (BC7 sRGB, full mip chain, DirectXTex texconv from --texconv or
ACO_TEXCONV).
"""
import argparse
import os
import subprocess

from PIL import Image

LAYOUT = (("Karin_Face.png", 0, 0), ("Karin_Body.png", 1, 0), ("Karin_Hair.png", 0, 1), ("Karin_Costume.png", 1, 1))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src_tex")
    ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=4096)
    ap.add_argument("--texconv", default=os.environ.get("ACO_TEXCONV"), help="texconv.exe (default: ACO_TEXCONV)")
    a = ap.parse_args()
    if not a.texconv:
        raise SystemExit("set ACO_TEXCONV (DirectXTex texconv.exe) or pass --texconv")
    src, out = a.src_tex, a.out_dir
    size = a.size
    half = size // 2
    os.makedirs(out, exist_ok=True)
    atlas = Image.new("RGB", (size, size))
    for name, cx, cy in LAYOUT:
        im = Image.open(os.path.join(src, name)).convert("RGB").resize((half, half), Image.LANCZOS)
        atlas.paste(im, (cx * half, cy * half))
    png = os.path.join(out, "karin_atlas.png")
    atlas.save(png)
    subprocess.run([a.texconv, "-nologo", "-y", "-f", "BC7_UNORM_SRGB", "-srgb", "-m", "0", "-bc", "q", "-o", out, png],
                   check=True, stdout=subprocess.DEVNULL)
    print("ATLAS", png, os.path.join(out, "karin_atlas.dds"))


if __name__ == "__main__":
    main()
