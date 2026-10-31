"""Find G1Ts read in a trace phase that share a reference texture's format/size and alpha pattern (colour variants).
usage: find_variant.py <reads.json> <phase> <package> <reference.g1t> <work dir> [--texconv <texconv.exe>]"""
import argparse, json, subprocess, sys
from pathlib import Path
here = Path(__file__).resolve().parent
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('reads', help='etw_reads.py JSON'); ap.add_argument('phase'); ap.add_argument('package')
ap.add_argument('reference', help='reference .g1t'); ap.add_argument('work', help='scratch dir for DDS / PNG')
ap.add_argument('--texconv', default=str(here / 'texconv.exe'), help='DirectXTex texconv (default: next to this script)')
args = ap.parse_args()
import numpy as np
from PIL import Image
sys.path.insert(0, str(here))
import ktdata, n3_g1t as g
reads, phase, pkg, ref, work = args.reads, args.phase, args.package, args.reference, args.work
work = Path(work); work.mkdir(exist_ok=True)
pk = Path(pkg)
recs = ktdata.parse_rdb(pk / 'root.rdb.original', pk / 'root.rdx.original')
ph = next(p for p in json.load(open(reads))['phases'] if p['name'] == phase)['resources']

def small_png(blob, tag):
    _, t = g.parse(blob); t = t[0]
    mip = max(0, t['mips'] - 4)                 # 16x16 for a 2048 BC7 with 10 mips
    dds = work / f'{tag}.dds'; png = work / f'{tag}.png'
    for p in (dds, png):
        if p.exists(): p.unlink()
    imgs = g.decode_images(blob, t)
    dds.write_bytes(g.write_dds(t, imgs, mips=[mip], slices=[0]))
    subprocess.run([args.texconv, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-o', str(work), str(dds)], capture_output=True)
    return np.asarray(Image.open(png).convert('RGBA'), float)

refb = Path(ref).read_bytes(); _, rt = g.parse(refb); rt = rt[0]
R = small_png(refb, 'ref')
cands = []
for h, v in ph.items():
    if not v['type'].startswith('g1t'):
        continue
    r = recs[int(h, 16)]
    if not (0.5 * len(refb) < r.file_size < 2.0 * len(refb)):
        continue
    try:
        b = ktdata.read_entry(r, pk); _, t = g.parse(b); t = t[0]
        if (t['format'], t['width'], t['height'], t['mips']) != (rt['format'], rt['width'], rt['height'], rt['mips']):
            continue
        A = small_png(b, 'cand')
    except Exception as e:
        continue
    da = np.abs(A[..., 3] - R[..., 3]).mean(); dc = np.abs(A[..., :3] - R[..., :3]).mean()
    cands.append((da, dc, h, r.file_size))
for da, dc, h, s in sorted(cands)[:15]:
    print(f'{h} size {s} alpha diff {da:.1f} colour diff {dc:.1f}')
print(len(cands), 'same-shape candidates')
