"""Run h2_pc_mi_091 over the built ascii meshes and texture pages; collect the mod files.

usage: make_mod.py WORK TOOLDIR(LocalCacheWinGame with h2 exe + pristine core) TEXCONV OUT
"""
import argparse
import json
import os
import shutil
import subprocess

import numpy as np
from PIL import Image

CORE = '02_19A7C73A.core'
ap = argparse.ArgumentParser(description='Run h2_pc_mi_091 over the built ascii meshes and texture pages; '
                                         'collect the mod files.')
ap.add_argument('work', help='build_hfw.py --work folder (jobs.json, ascii/, page_*.png, gloss_B.png)')
ap.add_argument('tooldir', help='dedicated tool folder (not the live game): h2_pc_mi_091.exe, '
                                f'{CORE}.pristine and the exported skeleton ascii files; '
                                'its *.stream and lod*/new_*.ascii files are deleted on every run')
ap.add_argument('texconv', help='DirectXTex texconv.exe')
ap.add_argument('out', help='output folder for the core and streams (emptied first)')
args = ap.parse_args()
work, R, texconv, out = args.work, args.tooldir, args.texconv, args.out
EXE = os.path.join(R, 'h2_pc_mi_091.exe')
for need in (EXE, os.path.join(R, CORE + '.pristine'), texconv, os.path.join(work, 'jobs.json')):
    if not os.path.isfile(need):
        ap.error(f'missing {need}')
dds_dir = os.path.join(work, 'dds')
os.makedirs(dds_dir, exist_ok=True)


def tc(png, fmt, name, size=None, extra=()):
    args = [texconv, '-nologo', '-y', '-m', '0', '-f', fmt, '-o', dds_dir]
    if size:
        args += ['-w', str(size), '-h', str(size)]
    args += list(extra) + [png]
    subprocess.run(args, check=True, capture_output=True)
    src = os.path.join(dds_dir, os.path.splitext(os.path.basename(png))[0] + '.dds')
    dst = os.path.join(dds_dir, name)
    if src != dst:
        shutil.move(src, dst)
    return dst


def solid(name, size, rgba):
    p = os.path.join(dds_dir, name + '.png')
    Image.fromarray(np.tile(np.array(rgba, np.uint8), (size, size, 1)), 'RGBA').save(p)
    return p


# ---- textures
gloss = np.asarray(Image.open(os.path.join(work, 'gloss_B.png')))
nb = np.zeros((2048, 2048, 4), np.uint8)
nb[..., 0] = 128
nb[..., 1] = 128
nb[..., 2] = gloss
nb[..., 3] = 255
Image.fromarray(nb, 'RGBA').save(os.path.join(dds_dir, 'normB.png'))
tex_jobs = [   # (group, texture id, dds)
    ('b2c4', '240', tc(os.path.join(work, 'page_A.png'), 'BC1_UNORM', 'pageA.dds')),
    ('b2c4', '1A', tc(solid('flatA', 2048, (128, 128, 255, 128)), 'BC7_UNORM', 'flatA.dds', extra=('-bc', 'q'))),
    ('b2c4', 'D1', tc(solid('wrc', 1024, (129, 128, 129, 255)), 'BC1_UNORM', 'wrc.dds')),
    ('b2c4', '45', os.path.join(dds_dir, 'wrc.dds')),
    ('b2c4', '98', os.path.join(dds_dir, 'wrc.dds')),
    ('b2c4', '246', tc(solid('wrn', 1024, (127, 127, 255, 255)), 'BC6H_UF16', 'wrn.dds')),
    ('b2c4', '1CD', os.path.join(dds_dir, 'wrn.dds')),
    ('b2c4', 'E0', os.path.join(dds_dir, 'wrn.dds')),
    ('1036', '2', tc(os.path.join(work, 'page_B.png'), 'BC1_UNORM', 'pageB.dds')),
    ('1036', '1', tc(os.path.join(dds_dir, 'normB.png'), 'BC7_UNORM', 'normB.dds', extra=('-bc', 'q'))),
    ('5e9', '8', tc(solid('m5e9', 1024, (126, 0, 74, 255)), 'BC1_UNORM', 'm5e9.dds')),
    ('5e9', '9', os.path.join(dds_dir, 'm5e9.dds')),
]
print('[dds] ok')

# ---- clean tool folder
for f in os.listdir(R):
    if f.endswith('.stream') or (f.endswith('.ascii') and f.startswith(('lod', 'new_'))):
        os.remove(os.path.join(R, f))
shutil.copy(os.path.join(R, CORE + '.pristine'), os.path.join(R, CORE))


def run(args):
    r = subprocess.run([EXE] + args, cwd=R, stdin=subprocess.DEVNULL, capture_output=True, text=True,
                       errors='replace', timeout=900)
    txt = r.stdout + r.stderr
    if 'Unhandled Exception' in txt or r.returncode != 0:
        raise RuntimeError(f'{args}: rc {r.returncode}\n{txt[-3000:]}')
    return txt


log = []
jobs = json.load(open(os.path.join(work, 'jobs.json')))
for j in jobs:
    shutil.copy(os.path.join(work, 'ascii', j['file']), os.path.join(R, j['file']))
    txt = run(['b2c4', str(j['lod']), j['skel'], j['file'], j['mesh'], '0'])
    n_ok = sum(1 for l in txt.splitlines() if l.strip() == 'success!')
    log.append(dict(job=j['file'], success=n_ok, subs=len(j['subs'])))
    print(f"[mesh] {j['file']}: success {n_ok}/{len(j['subs'])}")
    if n_ok != len(j['subs']):
        raise RuntimeError(f"{j['file']}: {n_ok} successes for {len(j['subs'])} submeshes\n{txt[-2000:]}")
for g, t, d in tex_jobs:
    shutil.copy(d, os.path.join(R, 'tex_in.dds'))
    txt = run([g, '0', 'tex_in.dds', t])
    reps = [l for l in txt.splitlines() if l.startswith('Replacing mip')]
    print(f'[tex] {g}_{t}: {len(reps)} mips')
    if not reps:
        raise RuntimeError(f'{g}_{t}: nothing replaced\n{txt[-1500:]}')
    log.append(dict(tex=f'{g}_{t}', mips=len(reps)))

# ---- collect
os.makedirs(out, exist_ok=True)
for f in os.listdir(out):
    os.remove(os.path.join(out, f))
files = [CORE] + sorted(f for f in os.listdir(R) if f.endswith('.stream'))
for f in files:
    shutil.copy(os.path.join(R, f), os.path.join(out, f))
json.dump(log, open(os.path.join(work, 'make_log.json'), 'w'), indent=1)
print('[out]', len(files), 'files ->', out)
