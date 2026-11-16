"""Turns a player's KarinMod_data_<version>.zip (release/collect.ps1) into a tool root for this pipeline.

python sparse_root.py <zip> <root> [<tool dir with ds2_pc_mi_022.exe and Decima_pack_ds2.exe>]
(default tool dir: DS2_MODDING/tools/ds2_modtool)

<root>/LocalCacheWinGame gets the zip's package tree: the cut-down DSAR files as they are (chunks the player's copy
didn't send have csize 0, so reading them fails), each <name>.karin_ranges rebuilt as a sparse plain file <name>,
streaming_graph.core plus the vanilla copy streaming_graph.core.org that ds2_pc_mi and Decima_pack read, and the tools
with a decima.ini naming the root. The report files (report.json, groups.tsv, types.txt, collect.json) go to <root>.
"""
import ctypes
import json
import msvcrt
import os
import shutil
import struct
import sys
import zipfile

FSCTL_SET_SPARSE = 0x900C4


def set_sparse(f):
    h = msvcrt.get_osfhandle(f.fileno())
    ret = ctypes.c_ulong()
    if not ctypes.windll.kernel32.DeviceIoControl(ctypes.c_void_p(h), FSCTL_SET_SPARSE, None, 0, None, 0,
                                                  ctypes.byref(ret), None):
        raise OSError('FSCTL_SET_SPARSE failed: %d' % ctypes.GetLastError())


def main():
    src, root = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3:
        tools = sys.argv[3]
    elif os.environ.get('DS2_MODDING'):
        tools = os.path.join(os.environ['DS2_MODDING'], 'tools', 'ds2_modtool')
    else:
        raise SystemExit('set DS2_MODDING (the modding workspace holding tools\\ds2_modtool) or pass the tool dir')
    lc = os.path.join(root, 'LocalCacheWinGame')
    if os.path.exists(lc):
        raise SystemExit('%s exists; remove it first' % lc)
    z = zipfile.ZipFile(src)
    n_dsar = n_plain = 0
    for info in z.infolist():
        name = info.filename
        if not name.startswith('LocalCacheWinGame/'):
            with z.open(info) as i, open(os.path.join(root, name), 'wb') as o:
                shutil.copyfileobj(i, o)
            continue
        dst = os.path.join(root, *name.split('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if name.endswith('.karin_ranges'):
            with z.open(info) as i, open(dst[:-len('.karin_ranges')], 'wb') as o:
                magic, ver, total, count = struct.unpack('<iiqi', i.read(20))
                assert magic == 0x474E524B and ver == 1, (name, magic, ver)
                rs = [struct.unpack('<qq', i.read(16)) for _ in range(count)]
                set_sparse(o)
                o.truncate(total)
                for off, ln in rs:
                    o.seek(off)
                    left = ln
                    while left:
                        b = i.read(min(left, 1 << 22))
                        assert b, name
                        o.write(b)
                        left -= len(b)
            n_plain += 1
        else:
            with z.open(info) as i, open(dst, 'wb') as o:
                shutil.copyfileobj(i, o, 1 << 22)
            if name.endswith(('.core', '.stream')) and not name.endswith(('streaming_graph.core', 'streaming_links.stream')):
                n_dsar += 1
    pkg = os.path.join(lc, 'package')
    shutil.copyfile(os.path.join(pkg, 'streaming_graph.core'), os.path.join(pkg, 'streaming_graph.core.org'))
    for t in ('ds2_pc_mi_022.exe', 'Decima_pack_ds2.exe'):
        shutil.copyfile(os.path.join(tools, t), os.path.join(lc, t))
    with open(os.path.join(lc, 'decima.ini'), 'w', newline='') as f:   # as setup_cleanroot.ps1 writes it
        f.write(os.path.abspath(lc) + '\\\r\n')
    meta = json.load(open(os.path.join(root, 'collect.json'), encoding='utf-8'))
    print('%s: exe %s, %d full groups, %d object-only groups, %d DSAR + %d sparse plain files, missing groups %s, '
          'missing files %s' % (root, meta['exe_version'], len(meta['full']), len(meta['core_only']), n_dsar, n_plain,
                                meta['missing'], meta['missing_files']))


if __name__ == '__main__':
    if sys.argv[1:2] in (['-h'], ['--help']) or len(sys.argv) < 3:
        print(__doc__)
        raise SystemExit(0 if sys.argv[1:2] in (['-h'], ['--help']) else 2)
    main()
