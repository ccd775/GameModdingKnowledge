"""Per-channel stats of G1T textures (mip 0, layer 0): n3_g1t dds -> texconv PNG -> Pillow.
usage: tex_stats.py <work dir> <file.g1t> [...] [--texconv <texconv.exe>]"""
import argparse, glob, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('work', help='scratch dir for DDS / PNG'); ap.add_argument('files', nargs='+', metavar='file.g1t', help='files or glob patterns')
ap.add_argument('--texconv', default=str(here / 'texconv.exe'), help='DirectXTex texconv (default: next to this script)')
args = ap.parse_args()
import numpy as np
from PIL import Image
work = Path(args.work); work.mkdir(exist_ok=True)
for f in [g for a in args.files for g in (sorted(glob.glob(a)) or [a])]:
    f = Path(f); dds = work / (f.stem + '.dds'); png = work / (f.stem + '.png')
    for p in (dds, png):
        if p.exists(): p.unlink()
    r = subprocess.run([sys.executable, '-B', str(here / 'n3_g1t.py'), 'dds', str(f), '--output', str(dds), '--mip', '0', '--layer', '0'], capture_output=True, text=True)
    if r.returncode:
        print(f.name, 'DDS FAIL', r.stderr[-200:]); continue
    r = subprocess.run([args.texconv, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-o', str(work), str(dds)], capture_output=True, text=True)
    if not png.exists():
        print(f.name, 'PNG FAIL', r.stdout[-200:]); continue
    a = np.asarray(Image.open(png).convert('RGBA'), float)
    print(f'{f.name} {a.shape[1]}x{a.shape[0]} mean={a.reshape(-1,4).mean(0).round(1).tolist()} std={a.reshape(-1,4).std(0).round(1).tolist()} min={a.reshape(-1,4).min(0).astype(int).tolist()} max={a.reshape(-1,4).max(0).astype(int).tolist()}')
