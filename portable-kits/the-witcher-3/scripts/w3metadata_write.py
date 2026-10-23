"""Witcher 3 Remastered (5.x) metadata.store v7 writer.

Layout (reverse-engineered from content/metadata.store of 5.0.1048522, see PROJECT_STATE):
  'VTM\x03'... magic 03 56 54 4D, i32 version=7, i32 maxSizeInBundle, i32 maxSizeInMemory,
  VLQ strtab size + strtab bytes
  VLQ n + FileInfo[n]   8 x u32: nameOff, pathHash(0), sizeInBundle, sizeInMemory, firstEntry,
                                 firstBuffer, numBuffers, compression
  VLQ n + FileEntry[n]  u64 offset, u32 sizeInBundle, u32 nextEntry, u32 fileId, u32 bundleId
  VLQ n + BundleInfo[n] u64 dataBlockSize, u32 dataBlockOffset, u32 nameOff, u32 firstEntry, u32 numEntries
  VLQ n + u32 bufferFileIds[n]
  VLQ n + DirInit[n]    i32 nameOff, i32 parentDir
  VLQ n + FileInit[n]   i32 fileId, i32 dirId, i32 nameOff   (non-buffer files, by fileId)
  VLQ n + Hash[n]       u64 fnv1a64(path), u64 fileId        (non-buffer files, sorted by hash)
Index 0 of FileInfo/FileEntry/BundleInfo is a null record.
"""
import re
import struct
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import w3bundle  # noqa: E402

BS = '\\'
BUFFER_RE = re.compile(r'^(.*)\.(\d+)\.buffer$')


def vlq(value):
    out = bytearray()
    neg = value < 0
    value = abs(value)
    b = value & 0x3F
    value >>= 6
    if neg:
        b |= 0x80
    cont = value != 0
    if cont:
        b |= 0x40
    out.append(b)
    while cont:
        b = value & 0x7F
        value >>= 7
        cont = value != 0
        if cont:
            b |= 0x80
        out.append(b)
    return bytes(out)


def fnv1a64(data):
    h = 0xcbf29ce484222325
    for c in data:
        h ^= c
        h = (h * 0x100000001b3) & 0xFFFFFFFFFFFFFFFF
    return h


def build_store(bundles, version=7, exclude=None):
    """bundles: list of (store_relative_bundle_path, absolute_bundle_file).
    exclude: optional predicate(name) for TOC items to leave out (the vanilla uncensored store drops '_censored')."""
    strtab = bytearray(b'\0')

    def add_str(s):
        off = len(strtab)
        strtab.extend(s.encode('latin-1') + b'\0')
        return off

    files = [None]          # fileId -> dict
    file_index = {}
    entries = [None]
    bundle_infos = [None]
    for bi, (rel, path) in enumerate(bundles, 1):
        name_off = add_str(rel)
        _v, hdr, items = w3bundle.read_toc(path)
        bundle_size = struct.unpack_from('<Q', hdr, 8)[0]
        toc_end = 0x20 + struct.unpack_from('<I', hdr, 16)[0]
        first = len(entries)
        for it in items:
            name = it.name.lower()
            if exclude and exclude(name):
                continue
            fid = file_index.get(name)
            if fid is None:
                fid = len(files)
                file_index[name] = fid
                files.append({'name': name, 'first': 0, 'off': add_str(name)})
            f = files[fid]
            entries.append([it.offset, it.zsize, f['first'], fid, bi])
            f['first'] = len(entries) - 1
            f['zsize'] = it.zsize
            f['size'] = it.size
            f['comp'] = 1 if it.comp else 0
        bundle_infos.append((bundle_size - toc_end, toc_end, name_off, first, len(entries) - first))

    # buffers
    buffers_of = {}
    is_buffer = set()
    for fid, f in enumerate(files[1:], 1):
        m = BUFFER_RE.match(f['name'])
        if m and m.group(1) in file_index:
            is_buffer.add(fid)
            buffers_of.setdefault(file_index[m.group(1)], []).append((int(m.group(2)), fid))
    buffer_list = []
    for fid, f in enumerate(files[1:], 1):
        lst = sorted(buffers_of.get(fid, []))
        f['fbuf'] = len(buffer_list) if lst else 0
        f['nbuf'] = len(lst)
        buffer_list.extend(b for _n, b in lst)

    # dirs and file inits (non-buffer files)
    root_off = len(strtab)
    strtab.extend(b'\0')
    dirs = [(root_off, 0)]
    dir_index = {'': 0}
    file_inits = []
    for fid, f in enumerate(files[1:], 1):
        if fid in is_buffer:
            continue
        parts = f['name'].split(BS)
        parent = 0
        key = ''
        for p in parts[:-1]:
            key = key + BS + p if key else p
            d = dir_index.get(key)
            if d is None:
                d = len(dirs)
                dir_index[key] = d
                dirs.append((add_str(p), parent))
            parent = d
        prefix_len = len(f['name']) - len(parts[-1])
        file_inits.append((fid, parent, f['off'] + prefix_len))
    hashes = sorted((fnv1a64(files[fid]['name'].encode('latin-1')), fid) for fid, _d, _n in file_inits)

    non_buf = [f for i, f in enumerate(files[1:], 1) if i not in is_buffer]
    max_b = max((f['zsize'] for f in non_buf), default=0)
    max_m = max((f['size'] for f in non_buf), default=0)

    out = bytearray(b'\x03VTM')
    out += struct.pack('<iii', version, max_b, max_m)
    out += vlq(len(strtab)) + strtab
    out += vlq(len(files))
    out += b'\0' * 32
    for f in files[1:]:
        out += struct.pack('<8I', f['off'], 0, f['zsize'], f['size'], f['first'], f['fbuf'], f['nbuf'], f['comp'])
    out += vlq(len(entries))
    out += b'\0' * 24
    for e in entries[1:]:
        out += struct.pack('<QIIII', *e)
    out += vlq(len(bundle_infos))
    out += b'\0' * 24
    for b in bundle_infos[1:]:
        out += struct.pack('<QIIII', *b)
    out += vlq(len(buffer_list))
    for b in buffer_list:
        out += struct.pack('<I', b)
    out += vlq(len(dirs))
    for n, p in dirs:
        out += struct.pack('<iI', n, p)
    out += vlq(len(file_inits))
    for t in file_inits:
        out += struct.pack('<iii', *t)
    out += vlq(len(hashes))
    for h, fid in hashes:
        out += struct.pack('<QQ', h, fid)
    return bytes(out)


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('content_dir', help='folder that will hold metadata.store (bundle paths are stored relative to it)')
    ap.add_argument('-o', '--out')
    a = ap.parse_args()
    root = os.path.abspath(a.content_dir)
    bundles = []
    for r, _d, fns in os.walk(root):
        for fn in sorted(fns):
            if fn.lower().endswith('.bundle'):
                full = os.path.join(r, fn)
                bundles.append((os.path.relpath(full, root).replace(os.sep, BS), full))
    bundles.sort(key=lambda x: x[0].lower())
    data = build_store(bundles)
    out = a.out or os.path.join(root, 'metadata.store')
    open(out, 'wb').write(data)
    print(f'wrote {out}: {len(data)} bytes, bundles={[b for b, _ in bundles]}')


if __name__ == '__main__':
    main()
