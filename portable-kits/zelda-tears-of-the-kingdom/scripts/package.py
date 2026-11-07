"""Assemble the yuzu mod folder and its merged RESTBL.
usage: python package.py <mod_dir> --vanilla <restbl.zs> [--merge <other mod restbl.zs> ...] [--extra <romfs-like dir> ...]
yuzu LayeredFS: the alphabetically first mod folder wins on collisions, so this mod's RESTBL carries the
vanilla table plus every other enabled mod's changes (max per entry) plus our own entries.
"""
import os, shutil, sys, json
sys.path.insert(0, os.path.dirname(__file__))
import totkfs

_WORK = os.environ.get('TOTK_WORK') or '<set TOTK_WORK>'   # portable kit: the work tree (see the kit README)
BUILD = os.path.join(_WORK, 'work', 'build')
ROMFS = os.path.join(_WORK, 'romfs')
RSTB_NAME = 'ResourceSizeTable.Product.120.rsizetable.zs'

def align(n, a=0x20): return (n + a - 1) // a * a
def est_bfres(raw_size): return align(raw_size) * 2 + 0x10000   # ST-resaved (fully decompressed) BFRES, generous
def est_txtg(file_size): return align(file_size) + 256          # matches vanilla entries exactly
def est_pack(raw): return align(raw) + 384                       # matches vanilla entries
def est_bntx(raw): return align(raw) + 256

def load_rt(p): return totkfs.Restbl(totkfs.zs_decompress(open(p, 'rb').read()))

def main(mod_dir, vanilla, merges=(), extras=()):
    romfs = os.path.join(mod_dir, 'romfs')
    if os.path.exists(romfs): shutil.rmtree(romfs)
    rt = load_rt(vanilla); van = load_rt(vanilla)
    changes = {}
    for m in merges:  # carry other mods' RESTBL edits
        o = load_rt(m); n = 0
        for c, s in o.crc.items():
            if van.crc.get(c) != s and s > rt.crc.get(c, 0): rt.crc[c] = s; n += 1
        for k, s in o.names.items():
            if van.names.get(k) != s and s > rt.names.get(k, 0): rt.names[k] = s; n += 1
        print('merged', m, n, 'entries')
    def put(key, size):
        old = rt.get(key); new = max(old or 0, size); rt.set(key, new); changes[key] = (old, new)
    for sub in ('Model', 'TexToGo'): os.makedirs(os.path.join(romfs, sub), exist_ok=True)
    for f in sorted(os.listdir(os.path.join(BUILD, 'out'))):
        if not f.endswith('.bfres.mc'): continue
        shutil.copy2(os.path.join(BUILD, 'out', f), os.path.join(romfs, 'Model', f))
        put('Model/' + f[:-3], est_bfres(os.path.getsize(os.path.join(BUILD, 'out', f[:-3]))))
    for f in sorted(os.listdir(os.path.join(BUILD, 'tex'))):
        if not f.endswith('.txtg'): continue
        shutil.copy2(os.path.join(BUILD, 'tex', f), os.path.join(romfs, 'TexToGo', f))
        put('TexToGo/' + f, est_txtg(os.path.getsize(os.path.join(BUILD, 'tex', f))))
    for d in extras:
        for root, _, files in os.walk(d):
            for f in files:
                src = os.path.join(root, f)
                rel = os.path.relpath(src, d).replace('\\', '/')
                dst = os.path.join(romfs, rel)
                os.makedirs(os.path.dirname(dst), exist_ok=True); shutil.copy2(src, dst)
                if rel.endswith('.pack.zs'):
                    put(rel[:-3], est_pack(len(totkfs.zs_decompress(open(src, 'rb').read(), f, ROMFS))))
                elif rel.endswith('.bntx.zs'):
                    put(rel[:-3], est_bntx(len(totkfs.zs_decompress(open(src, 'rb').read(), f, ROMFS))))
    os.makedirs(os.path.join(romfs, 'System', 'Resource'), exist_ok=True)
    data = totkfs.zs_compress(rt.to_bytes())
    open(os.path.join(romfs, 'System', 'Resource', RSTB_NAME), 'wb').write(data)
    json.dump({k: list(v) for k, v in changes.items()}, open(os.path.join(BUILD, 'restbl_changes.json'), 'w'), indent=1)
    for k, (o, n) in changes.items(): print(f'{k}: {o} -> {n}')
    print('restbl entries', len(rt.crc), 'collisions', len(rt.names), 'size', len(data))

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mod_dir'); ap.add_argument('--vanilla', required=True)
    ap.add_argument('--merge', nargs='+', action='extend', default=[])
    ap.add_argument('--extra', nargs='+', action='extend', default=[])
    a = ap.parse_args()
    main(a.mod_dir, a.vanilla, a.merge, a.extra)
