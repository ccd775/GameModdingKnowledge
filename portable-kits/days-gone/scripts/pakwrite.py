"""Write a UE 4.11 pak (version 3) from a directory tree.
usage: pakwrite.py <srcDir> <out.pak> [--mount ../../../BendGame/Content/] [--store]
Files are stored under their path relative to srcDir. zlib with 64 KiB blocks unless --store."""
import argparse, hashlib, os, struct, sys, zlib

BLOCK = 0x10000

def fstr(s):
    b = s.encode('ascii') + b'\0'
    return struct.pack('<i', len(b)) + b

def entry_bytes(off, size, usize, comp, sha, blocks, bs):
    b = struct.pack('<qqqi', off, size, usize, comp) + sha
    if comp:
        b += struct.pack('<i', len(blocks)) + b''.join(struct.pack('<qq', s, e) for s, e in blocks)
    return b + struct.pack('<BI', 0, bs)

def main(a):
    src, out = a[0], a[1]
    mount = a[a.index('--mount') + 1] if '--mount' in a else '../../../BendGame/Content/'
    store = '--store' in a
    files = []
    for root, _, fs in os.walk(src):
        for f in fs:
            p = os.path.join(root, f)
            files.append((os.path.relpath(p, src).replace(os.sep, '/'), p))
    files.sort()
    index = []
    with open(out, 'wb') as o:
        for name, p in files:
            data = open(p, 'rb').read()
            off = o.tell()
            if store or not data:
                payload, comp, blocks, bs = data, 0, [], 0
                hdr = len(entry_bytes(0, 0, 0, 0, b'\0' * 20, [], 0))
            else:
                chunks = [zlib.compress(data[i:i + BLOCK], 9) for i in range(0, len(data), BLOCK)]
                hdr = len(entry_bytes(0, 0, 0, 1, b'\0' * 20, [(0, 0)] * len(chunks), 0))
                blocks, pos = [], off + hdr
                for c in chunks:
                    blocks.append((pos, pos + len(c))); pos += len(c)
                payload, comp, bs = b''.join(chunks), 1, min(BLOCK, len(data))
            sha = hashlib.sha1(payload).digest()
            o.write(entry_bytes(0, len(payload), len(data), comp, sha, blocks, bs))
            assert o.tell() == off + hdr
            o.write(payload)
            index.append(fstr(name) + entry_bytes(off, len(payload), len(data), comp, sha, blocks, bs))
        idx = fstr(mount) + struct.pack('<i', len(index)) + b''.join(index)
        io = o.tell()
        o.write(idx)
        o.write(struct.pack('<IIqq', 0x5A6F12E1, 3, io, len(idx)) + hashlib.sha1(idx).digest())
    print(f'wrote {out}: {len(files)} files, mount {mount}')

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('out')
    ap.add_argument('--mount', help='mount point (default ../../../BendGame/Content/)')
    ap.add_argument('--store', action='store_true', help='no compression')
    ap.parse_args()                      # checks the arguments; main() reads the same list (make_pak.py calls it)
    main(sys.argv[1:])
