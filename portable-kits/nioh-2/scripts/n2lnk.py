#!/usr/bin/env python3
"""Nioh 2 PC archive reader (archive/archive_XX.lnk, magic K300). Standard library only, read-only.

Layout (measured on the Complete Edition, 2021-02-05 build):
  header 0x20: 'K300', u32 0, u64 entry count, u64 file size, u64 alignment (0x800)
  entries:     count x (u64 offset, u64 size, u64 stored size, u64 zip flag)
  zip flag 0:  stored as is; otherwise compressed (format probed by `unpack`).

  index   <archive dir> <out.jsonl>            one line per entry: archive, entry, offset, size, zsize, zip, magic
  extract <archive dir> <arch> <entry> <out>   write one entry (decompressed)
  many    <archive dir> <list.txt> <out dir>   lines "arch entry [name]"
  locate  <archive dir> <arch> <offset>        which entry holds a byte offset
"""
import json
import os
import struct
import sys
import zlib


def table(path):
    with open(path, 'rb') as f:
        head = f.read(0x20)
        if head[:4] != b'K300':
            raise ValueError(f'{path}: not K300')
        count, fsize, align = struct.unpack_from('<QQQ', head, 8)
        raw = f.read(count * 32)
    ents = [struct.unpack_from('<QQQQ', raw, i * 32) for i in range(count)]
    return ents, fsize, align


def arch_path(adir, a):
    return os.path.join(adir, f'archive_{int(a):02d}.lnk')


def unpack(f, off, size, zsize, zip_):
    """Return decompressed bytes of one entry. Compressed entries are 16 KB chunks:
    u32 (compressed size | 0x8000, or raw size without the flag), zlib / raw data, padded to 16 bytes."""
    f.seek(off)
    data = f.read(zsize)
    if not zip_:
        return data[:size]
    out = bytearray()
    pos = 0
    while len(out) < size and pos + 4 <= len(data):
        n = struct.unpack_from('<I', data, pos)[0]
        pos += 4
        if n & 0x8000:
            n &= 0x7FFF
            out += zlib.decompress(data[pos:pos + n])
        else:
            out += data[pos:pos + n]
        pos += n
        pos += (-pos) % 16
    if len(out) != size:
        raise ValueError(f'entry at {off:#x}: got {len(out)} of {size} bytes')
    return bytes(out)


def head_bytes(f, off, size, zsize, zip_, n=64):
    if not zip_:
        f.seek(off)
        return f.read(min(n, size))
    f.seek(off)
    data = f.read(min(zsize, 1 << 16))
    for start in (4, 8, 12, 16, 0):
        try:
            d = zlib.decompressobj()
            return d.decompress(data[start:], n)
        except zlib.error:
            continue
    return b'?' * 4


def cmd_index(adir, out):
    with open(out, 'w', encoding='utf-8') as o:
        for a in range(100):
            p = arch_path(adir, a)
            if not os.path.exists(p):
                continue
            ents, fsize, align = table(p)
            with open(p, 'rb') as f:
                for i, (off, size, zsize, zip_) in enumerate(ents):
                    hb = head_bytes(f, off, size, zsize, zip_)
                    rec = {'a': a, 'e': i, 'off': off, 'size': size, 'zsize': zsize, 'zip': zip_,
                           'magic': hb[:8].hex(), 'zhead': ''}
                    if zip_:
                        f.seek(off)
                        rec['zhead'] = f.read(16).hex()
                    o.write(json.dumps(rec) + '\n')
            print(f'archive_{a:02d}: {len(ents)} entries', flush=True)


def cmd_extract(adir, a, e, out):
    ents, _, _ = table(arch_path(adir, a))
    off, size, zsize, zip_ = ents[int(e)]
    with open(arch_path(adir, a), 'rb') as f:
        data = unpack(f, off, size, zsize, zip_)
    with open(out, 'wb') as o:
        o.write(data)
    print(f'{out}: {len(data)} bytes')


def cmd_many(adir, lst, outdir):
    os.makedirs(outdir, exist_ok=True)
    tabs = {}
    for line in open(lst, encoding='utf-8'):
        parts = line.split()
        if len(parts) < 2:
            continue
        a, e = int(parts[0]), int(parts[1])
        name = parts[2] if len(parts) > 2 else f'{a:02d}_{e:06d}.bin'
        if a not in tabs:
            tabs[a] = table(arch_path(adir, a))[0]
        off, size, zsize, zip_ = tabs[a][e]
        with open(arch_path(adir, a), 'rb') as f:
            data = unpack(f, off, size, zsize, zip_)
        with open(os.path.join(outdir, name), 'wb') as o:
            o.write(data)
        print(name, len(data))


def cmd_locate(adir, a, offset):
    ents, _, _ = table(arch_path(adir, a))
    offset = int(offset, 0)
    for i, (off, size, zsize, zip_) in enumerate(ents):
        if off <= offset < off + max(zsize, size):
            print(a, i, hex(off), size, zsize, zip_)
            return
    print('not found')


def main(argv):
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('index', help='one JSON line per entry of every archive_XX.lnk')
    p.add_argument('adir', metavar='archive_dir'); p.add_argument('out', metavar='out.jsonl')
    p = sub.add_parser('extract', help='write one entry (decompressed)')
    p.add_argument('adir', metavar='archive_dir'); p.add_argument('a', metavar='arch'); p.add_argument('e', metavar='entry')
    p.add_argument('out')
    p = sub.add_parser('many', help='extract the entries listed as "arch entry [name]" lines')
    p.add_argument('adir', metavar='archive_dir'); p.add_argument('lst', metavar='list.txt'); p.add_argument('outdir', metavar='out_dir')
    p = sub.add_parser('locate', help='which entry holds a byte offset')
    p.add_argument('adir', metavar='archive_dir'); p.add_argument('a', metavar='arch'); p.add_argument('offset')
    args = vars(ap.parse_args(argv))
    {'index': cmd_index, 'extract': cmd_extract, 'many': cmd_many, 'locate': cmd_locate}[args.pop('cmd')](**args)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
