"""Witcher 3 metadata.store reader (v6 layout per WolvenKit Metadata_Store.cs; v7 as written by w3metadata_write.py:
FileEntry grows to 24 bytes and BundleInfo starts with a u64 data block size)."""
import struct
import sys


class R:
    def __init__(self, data):
        self.d = data
        self.p = 0

    def u32(self):
        v = struct.unpack_from('<I', self.d, self.p)[0]
        self.p += 4
        return v

    def i32(self):
        v = struct.unpack_from('<i', self.d, self.p)[0]
        self.p += 4
        return v

    def vlq(self):
        b1 = self.d[self.p]
        self.p += 1
        sign = b1 & 0x80
        nxt = b1 & 0x40
        size = b1 & 0x3F
        off = 6
        while nxt:
            b = self.d[self.p]
            self.p += 1
            size |= (b & 0x7F) << off
            nxt = b & 0x80
            off += 7
        return -size if sign else size

    def raw(self, n):
        v = self.d[self.p:self.p + n]
        self.p += n
        return v


def read_store(path, verbose=True):
    with open(path, 'rb') as f:
        d = f.read()
    r = R(d)
    magic = r.raw(4)
    assert magic == b'\x03VTM', magic
    st = {}
    st['version'] = r.i32()
    st['max_in_bundle'] = r.i32()
    st['max_in_memory'] = r.i32()
    sts = r.vlq()
    st['string_table'] = r.raw(sts)
    if verbose:
        print('version', st['version'], 'maxB', st['max_in_bundle'], 'maxM', st['max_in_memory'], 'strtab', sts, 'pos', r.p)

    def arr(name, size):
        n = r.vlq()
        start = r.p
        data = r.raw(n * size)
        st[name] = (n, data)
        if verbose:
            print(f'{name}: count={n} elem={size} at {start} -> {r.p} (left {len(d) - r.p})')
        return n, data

    arr('file_infos', 32)
    arr('file_entries', 24 if st['version'] >= 7 else 20)   # v7: u64 offset, u32 size, next, file id, bundle id
    arr('bundle_infos', 24)
    nb = r.vlq()
    st['buffers'] = [r.u32() for _ in range(nb)]
    if verbose:
        print('buffers', nb, 'pos', r.p)
    arr('dir_inits', 8)
    arr('file_inits', 12)
    arr('hashes', 16)
    st['tail'] = d[r.p:]
    if verbose:
        print('end pos', r.p, 'len', len(d))
    return st


def strtab_at(st, off):
    t = st['string_table']
    e = t.index(b'\0', off)
    return t[off:e].decode('latin-1')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='Print the tables of a Witcher 3 metadata.store (debugging).')
    ap.add_argument('store')
    st = read_store(ap.parse_args().store)
    v7 = st['version'] >= 7
    n, data = st['bundle_infos']
    for i in range(min(n, 40)):
        if v7:   # u64 dataBlockSize, u32 dataBlockOffset, nameOff, firstEntry, numEntries
            dbs, dbo, name, first, num = struct.unpack_from('<QIIII', data, i * 24)
            print('bundle', i, strtab_at(st, name), first, num, dbs, dbo)
        else:
            name, first, num, dbs, dbo, burst = struct.unpack_from('<6I', data, i * 24)
            print('bundle', i, strtab_at(st, name), first, num, dbs, dbo, burst)
    n, data = st['file_infos']
    for i in range(min(n, 5)):
        vals = struct.unpack_from('<8I', data, i * 32)
        print('file', i, strtab_at(st, vals[0]), vals[1:])
    n, data = st['file_entries']
    for i in range(min(n, 5)):
        print('entry', i, struct.unpack_from('<QIIII', data, i * 24) if v7 else struct.unpack_from('<5I', data, i * 20))
    n, data = st['dir_inits']
    for i in range(min(n, 5)):
        print('dir', i, struct.unpack_from('<2i', data, i * 8))
    n, data = st['file_inits']
    for i in range(min(n, 5)):
        print('finit', i, struct.unpack_from('<3i', data, i * 12))
    n, data = st['hashes']
    for i in range(min(n, 5)):
        print('hash', i, struct.unpack_from('<2Q', data, i * 16))
    print('tail', len(st['tail']), st['tail'][:64].hex())
