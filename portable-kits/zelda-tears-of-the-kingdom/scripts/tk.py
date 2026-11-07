"""Small wrappers: run TotkMdl, load its JSON, compute world bind matrices."""
import json, os, subprocess
import numpy as np
from retarget import quat_to_mat

# Portable kit: the work tree is $TOTK_WORK (src/, ref/, romfs/, romfs_st/, romfs_anim/, work/); TotkMdl.exe sits
# in a Switch Toolbox folder, $TOTK_ST_DIR (default $TOTK_WORK/tools/st_headless). See the kit README.
WORK_ROOT = os.environ.get('TOTK_WORK') or '<set TOTK_WORK>'
ST_DIR = os.environ.get('TOTK_ST_DIR') or os.path.join(WORK_ROOT, 'tools', 'st_headless')
TOTKMDL = os.path.join(ST_DIR, 'TotkMdl.exe')
ROMFS = os.path.join(WORK_ROOT, 'romfs')   # local partial copy of the vanilla romfs (Shader/, Model/, TexToGo/, Pack/ ...)
# What TotkMdl/Switch Toolbox sees as the game path: no TexToGo/ — ST's TexToGoFolder throws on some vanilla .txtg
# (tiny CmnTex_*), which breaks loading any model that references them.
ROMFS_ST = os.path.join(WORK_ROOT, 'romfs_st')

def need_work():
    if not os.path.isdir(WORK_ROOT):
        raise SystemExit('Set TOTK_WORK to the work tree (see the kit README) first.')

def run(*args):
    r = subprocess.run([TOTKMDL, *args], capture_output=True, text=True, encoding='utf-8', errors='replace')
    out = (r.stdout or '') + (r.stderr or '')
    if r.returncode != 0 or 'ERROR' in out:
        raise RuntimeError(out[-4000:])
    return out

def export(model_path, out_json, verts=True):
    run('export' if verts else 'info', model_path, ROMFS_ST, out_json)
    return json.load(open(out_json, encoding='utf-8'))

def world_mats(model):
    bones = model['bones']
    W = [None] * len(bones)
    def get(i):
        if W[i] is not None: return W[i]
        b = bones[i]
        L = np.eye(4)
        L[:3, :3] = quat_to_mat(b['quat']) * np.array(b['scale'])[None, :]
        L[:3, 3] = b['pos']
        W[i] = L if b['parent'] < 0 else get(b['parent']) @ L
        return W[i]
    for i in range(len(bones)): get(i)
    return {bones[i]['name']: W[i] for i in range(len(bones))}
