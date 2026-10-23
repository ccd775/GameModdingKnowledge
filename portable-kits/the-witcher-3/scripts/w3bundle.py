"""Witcher 3 (Remastered 5.x) bundle reader/extractor/writer.

Bundle layout (header v5, as found in content/content0/bundles on 5.0.1048522):
  0x00 'POTATO70'
  0x08 u64 bundle size
  0x10 u32 TOC size (bytes, after the 0x20 header)
  0x14 u16 version (5)
  0x16 u32 TOC size + 0x20
  0x20 TOC entries, 304 bytes each:
       0x000 name[256] (latin-1, NUL padded)
       0x100 hash[16]
       0x110 u64 page offset, u32 size, u32 zsize, u32 crc, u8 compression, pad to 304
Legacy v3 entries are 320 bytes (see WolvenKit Bundle.cs).
"""
import argparse
import fnmatch
import os
import struct
import sys
import zlib

HEADER_SIZE = 0x20
ENTRY_V5 = 304
ENTRY_V3 = 320


class Item:
    __slots__ = ("name", "hash", "offset", "size", "zsize", "crc", "comp", "raw_tail")


def read_toc(path):
    with open(path, "rb") as f:
        hdr = f.read(HEADER_SIZE)
        if hdr[:8] != b"POTATO70":
            raise ValueError(f"{path}: not a bundle")
        version = struct.unpack_from("<H", hdr, 20)[0]
        if version == 5:
            toc_size = struct.unpack_from("<I", hdr, 16)[0]
            esz = ENTRY_V5
        else:
            toc_size = struct.unpack_from("<I", hdr, 16)[0]
            esz = ENTRY_V3
        toc = f.read(toc_size)
    items = []
    for i in range(toc_size // esz):
        row = toc[i * esz:(i + 1) * esz]
        it = Item()
        it.name = row[:0x100].split(b"\0", 1)[0].decode("latin-1")
        it.hash = row[0x100:0x110]
        if version == 5:
            it.offset, it.size, it.zsize, it.crc, it.comp = struct.unpack_from("<QIIIB", row, 0x110)
            it.raw_tail = row[0x125:]
        else:
            _empty, it.size, it.zsize, it.offset, _d, _t = struct.unpack_from("<6I", row, 0x110)
            it.crc, it.comp = struct.unpack_from("<2I", row, 0x138)
            it.raw_tail = b""
        items.append(it)
    return version, hdr, items


def decompress(data, comp, size):
    if comp == 0:
        return data
    if comp == 1:
        return zlib.decompress(data)
    if comp in (4, 5):
        import lz4.block
        return lz4.block.decompress(data, uncompressed_size=size)
    if comp == 2:
        import cramjam
        return bytes(cramjam.snappy.decompress_raw(data))
    if comp == 3:
        raise NotImplementedError("doboz compression")
    raise NotImplementedError(f"compression {comp}")


def read_item(bundle_path, it):
    with open(bundle_path, "rb") as f:
        f.seek(it.offset)
        data = f.read(it.zsize)
    out = decompress(data, it.comp, it.size)
    if len(out) != it.size:
        raise ValueError(f"{it.name}: size mismatch {len(out)} != {it.size}")
    return out


def iter_bundles(paths):
    for p in paths:
        if os.path.isdir(p):
            for root, _d, files in os.walk(p):
                for fn in sorted(files):
                    if fn.endswith(".bundle"):
                        yield os.path.join(root, fn)
        else:
            yield p


def cmd_list(args):
    for b in iter_bundles(args.bundles):
        version, _hdr, items = read_toc(b)
        for it in items:
            if args.pattern and not fnmatch.fnmatch(it.name.lower(), args.pattern.lower()):
                continue
            if args.verbose:
                print(f"{os.path.basename(b)}\tv{version}\t{it.comp}\t{it.size}\t{it.zsize}\t{it.offset}\t{it.crc:08x}\t{it.hash.hex()}\t{it.name}")
            else:
                print(f"{os.path.basename(b)}\t{it.size}\t{it.name}")


def cmd_extract(args):
    os.makedirs(args.out, exist_ok=True)
    n = 0
    for b in iter_bundles(args.bundles):
        _v, _h, items = read_toc(b)
        for it in items:
            if not any(fnmatch.fnmatch(it.name.lower(), p.lower()) for p in args.pattern):
                continue
            dst = os.path.join(args.out, it.name.replace("\\", os.sep))
            if os.path.exists(dst) and not args.overwrite:
                continue
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            with open(dst, "wb") as f:
                f.write(read_item(b, it))
            n += 1
            if args.verbose:
                print(f"{os.path.basename(b)} -> {it.name}")
    print(f"extracted {n} files", file=sys.stderr)


def _align(pos, a):
    return (pos + a - 1) // a * a


def write_bundle(out_path, files, compression=0, version=5):
    """files: list of (depot_path, bytes). Writes an uncompressed (or zlib) v5 bundle."""
    import hashlib
    files = sorted(files, key=lambda x: x[0].lower())
    esz = ENTRY_V5 if version == 5 else ENTRY_V3
    toc_size = esz * len(files)
    data_start = _align(HEADER_SIZE + toc_size, 4096)
    payloads = []
    for name, raw in files:
        if compression == 1:
            z = zlib.compress(raw, 9)
            if len(z) >= len(raw):
                z, c = raw, 0
            else:
                c = 1
        else:
            z, c = raw, 0
        payloads.append((name, raw, z, c))
    toc = bytearray()
    offsets = []
    pos = data_start
    for name, raw, z, c in payloads:
        offsets.append(pos)
        pos = _align(pos + len(z), 4096)
    total = offsets[-1] + len(payloads[-1][2]) if payloads else data_start
    for (name, raw, z, c), off in zip(payloads, offsets):
        nb = name.replace("/", "\\").lower().encode("latin-1")
        if len(nb) >= 0x100:
            raise ValueError(f"path too long: {name}")
        row = bytearray(esz)
        row[:len(nb)] = nb
        row[0x100:0x110] = hashlib.md5(raw).digest()
        crc = zlib.crc32(raw) & 0xFFFFFFFF  # vanilla TOC stores CRC32 of the uncompressed data
        if version == 5:
            struct.pack_into("<QIIIB", row, 0x110, off, len(raw), len(z), crc, c)
        else:
            struct.pack_into("<6I", row, 0x110, 0, len(raw), len(z), off, 0, 0)
            struct.pack_into("<2I", row, 0x138, crc, c)
        toc += row
    with open(out_path, "wb") as f:
        hdr = bytearray(HEADER_SIZE)
        hdr[:8] = b"POTATO70"
        if version == 5:
            struct.pack_into("<QI", hdr, 8, total, toc_size)
            struct.pack_into("<HI", hdr, 20, 5, toc_size + HEADER_SIZE)
        else:
            struct.pack_into("<III", hdr, 8, total, 0, toc_size)
            hdr[20:32] = bytes([0x03, 0x00, 0x01, 0x00, 0x00, 0x13, 0x13, 0x13, 0x13, 0x13, 0x13, 0x13])
        f.write(hdr)
        f.write(toc)
        for (name, raw, z, c), off in zip(payloads, offsets):
            cur = f.tell()
            if off > cur:
                f.write(b"\0" * (off - cur))
            f.write(z)
    return total


def cmd_pack(args):
    files = []
    root = os.path.abspath(args.root)
    for r, _d, fns in os.walk(root):
        for fn in sorted(fns):
            full = os.path.join(r, fn)
            rel = os.path.relpath(full, root).replace(os.sep, "\\").lower()
            with open(full, "rb") as fh:
                files.append((rel, fh.read()))
    total = write_bundle(args.out, files, compression=args.compression, version=args.version)
    print(f"packed {len(files)} files -> {args.out} ({total} bytes)")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("list")
    p.add_argument("bundles", nargs="+")
    p.add_argument("-p", "--pattern")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_list)
    p = sub.add_parser("extract")
    p.add_argument("bundles", nargs="+")
    p.add_argument("-p", "--pattern", action="append", required=True)
    p.add_argument("-o", "--out", required=True)
    p.add_argument("--overwrite", action="store_true")
    p.add_argument("-v", "--verbose", action="store_true")
    p.set_defaults(func=cmd_extract)
    p = sub.add_parser("pack")
    p.add_argument("root")
    p.add_argument("out")
    p.add_argument("--compression", type=int, default=0)
    p.add_argument("--version", type=int, default=5)
    p.set_defaults(func=cmd_pack)
    args = ap.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
