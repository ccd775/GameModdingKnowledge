"""Karin textures for the ninja chest's texture set 0: one 4096 BC7 colour atlas + neutral constants.
Slots (KTID 0xA154A11C, set 0; none drawn by another model - ktdata usage audit 2026-10-28):
  COLOR   0x8B541440  BC7 2048 -> 4096 atlas (2x2: costume, hair / face, body skin), alpha 255
  NORMAL  0x7F1EB597  BC1 2048 -> flat (128,128,255)
  SHADING 0xE0739E0C  BC7 2048 -> vanilla mean (10,10,10,160)
  slot 49 0x52244783  BC5 1024 -> (0,0): R = detail-array layer (x17), G = detail strength (vanilla); 0 = no detail
Kept vanilla: slot 24 detail-normal array 0xAD4F6A70 (UV independent); DIRT 0xAF626E1D and slot 47 0xE3E99A7E are
shared with the sibling top 0x6EC977DE.
Output: BUILD/g1t/*.g1t (+ atlas.png, report.json)
usage: n3_textures.py   (BUILD = N3_BUILD; texconv at BUILD/toolchain/texconv.exe, templates in BUILD/tex/)"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from n3_common import BUILD, load_source

TOOLS = Path(__file__).resolve().parent.parent
TEXCONV = BUILD / 'toolchain' / 'texconv.exe'
CONSTANTS = {'0x7f1eb597': '128,128,255,255', '0xe0739e0c': '10,10,10,160', '0x52244783': '0,0,0,255'}


def coverage(meta, arr, material, size):
    """Mask of the source texture texels covered by the triangles of every mesh using `material` (UV space)."""
    from PIL import ImageDraw
    mask = Image.new('L', (size, size), 0); draw = ImageDraw.Draw(mask)
    for m in meta['meshes']:
        names = [x['name'] for x in m['materials']]
        if material not in names:
            continue
        k = m['key']; uv = arr[k + '__loop_uv']; tris = arr[k + '__tris']; tm = arr[k + '__tri_material']
        for t in tris[tm == names.index(material)]:
            pts = [(float(uv[l][0]) * size, (1 - float(uv[l][1])) * size) for l in t]
            draw.polygon(pts, fill=255, outline=255)
    return np.asarray(mask) > 0


def push_pull(img, mask):
    """Fill uncovered texels from covered ones (mask-weighted mip pyramid down, then back up)."""
    a = np.asarray(img, np.float64) / 255.0
    w = mask.astype(np.float64)
    levels = []
    c, ww = a * w[..., None], w
    while min(ww.shape) > 1:
        levels.append((c, ww))
        h, wd = ww.shape[0] // 2, ww.shape[1] // 2
        c = c[:2 * h, :2 * wd].reshape(h, 2, wd, 2, -1).sum((1, 3))
        ww = ww[:2 * h, :2 * wd].reshape(h, 2, wd, 2).sum((1, 3))
    col = c / np.maximum(ww, 1e-9)[..., None]
    for c, ww in reversed(levels):
        up = np.repeat(np.repeat(col, 2, 0), 2, 1)[:ww.shape[0], :ww.shape[1]]
        own = c / np.maximum(ww, 1e-9)[..., None]
        col = np.where((ww > 0)[..., None], own, up)
    out = np.where(mask[..., None], a, col)
    return Image.fromarray(np.clip(out * 255 + 0.5, 0, 255).astype(np.uint8))


def atlas_png(out):
    meta, arr = load_source()
    size, regs = json.loads((BUILD / 'atlas_uv.json').read_text())['A']
    img = Image.new('RGB', (size, size), (128, 128, 128))
    src = {}
    for m in meta['meshes']:
        for mat in m['materials']:
            tex = next((t['image'] for t in mat['textures'] if t['image'].startswith('Standard_')), None)
            if tex and mat['name'] in regs:
                src[mat['name']] = meta['textures'][tex]['file']
    done, stats = {}, {}
    for name, (x, y, w, h) in regs.items():
        if name not in src:
            continue
        im = Image.open(BUILD / 'source' / 'textures' / src[name]).convert('RGB')
        key = (x, y)
        cov = coverage(meta, arr, name, im.size[0])
        if key in done:                       # a second material on the same texture: union its coverage
            cov |= done[key][1]
        done[key] = (im, cov)
    for (x, y), (im, cov) in done.items():
        w, h = next((r[2], r[3]) for r in regs.values() if (r[0], r[1]) == (x, y))
        filled = push_pull(im, cov)
        img.paste(filled.resize((w, h), Image.LANCZOS), (x, y))
        stats[f'{x},{y}'] = round(float(cov.mean()), 3)
    img.save(out)
    return {'sources': {k: src.get(k) for k in regs}, 'uv_coverage': stats}


def run(cmd):
    r = subprocess.run([str(c) for c in cmd], capture_output=True, text=True)
    if r.returncode:
        raise SystemExit(f'{cmd[0]} failed: {r.stdout[-800:]} {r.stderr[-800:]}')
    return r.stdout


def main():
    out = BUILD / 'g1t'; out.mkdir(exist_ok=True)
    for f in out.glob('*'):
        f.unlink()
    report = {'atlas_sources': atlas_png(out / 'atlas.png')}
    run([TEXCONV, '-nologo', '-y', '-f', 'BC7_UNORM', '-m', '11', '-dx10', '-bc', 'q', '-o', out, out / 'atlas.png'])
    run([sys.executable, '-B', TOOLS / 'n3_g1t_resize.py', BUILD / 'tex' / '0x8b541440.g1t', out / 'atlas.dds',
         '--output', out / '0x8b541440.g1t'])
    for h, rgba in CONSTANTS.items():
        run([sys.executable, '-B', TOOLS / 'n3_g1t.py', 'constant', BUILD / 'tex' / f'{h}.g1t', '--rgba', rgba,
             '--output', out / f'{h}.g1t'])
    # read back: decode mip 0 of the atlas and compare with the PNG
    dds = out / 'readback.dds'
    run([sys.executable, '-B', TOOLS / 'n3_g1t.py', 'dds', out / '0x8b541440.g1t', '--output', dds, '--mip', '0'])
    run([TEXCONV, '-nologo', '-y', '-ft', 'png', '-f', 'R8G8B8A8_UNORM', '-o', out, dds])
    a = np.asarray(Image.open(out / 'readback.png').convert('RGB'), float)
    b = np.asarray(Image.open(out / 'atlas.png').convert('RGB'), float)
    report['readback_mean_abs_diff'] = round(float(np.abs(a - b).mean()), 3)
    report['files'] = {f.name: f.stat().st_size for f in out.glob('0x*.g1t')}
    (out / 'report.json').write_text(json.dumps(report, indent=1))
    print(json.dumps(report, indent=1))


if __name__ == '__main__':
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    main()
