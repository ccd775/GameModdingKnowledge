"""Ghost of Tsushima PC archives: DSAR (Nixxes, LZ4 blocks) and PSARC read/write.

DSAR wraps a complete PSARC byte stream. Vanilla PSARC entries are sorted by md5(name),
so files are resolved through the hash instead of manifest order.
"""
import bisect
import hashlib
import os
import re
import struct
import zlib

import lz4.block

BLOCK = 0x10000


class _DsarStream:
    def __init__(self, path):
        self.f = open(path, 'rb')
        magic, _ver, nblk, _hdr, total = struct.unpack('<4sIIIQ', self.f.read(24))
        if magic != b'DSAR':
            raise ValueError('not a DSAR file')
        self.f.seek(0x20)
        self.blocks = [struct.unpack('<QQIIB7x', self.f.read(32)) for _ in range(nblk)]
        self.starts = [b[0] for b in self.blocks]
        self.size = total
        self.cache = {}

    def _block(self, i):
        if i not in self.cache:
            _uoff, coff, usz, csz, kind = self.blocks[i]
            if csz == 0:
                data = bytes(usz)
            else:
                self.f.seek(coff)
                raw = self.f.read(csz)
                data = lz4.block.decompress(raw, uncompressed_size=usz) if kind == 3 else raw
            if len(self.cache) > 64:
                self.cache.clear()
            self.cache[i] = data
        return self.cache[i]

    def read(self, off, n):
        out = bytearray()
        while n > 0:
            i = bisect.bisect_right(self.starts, off) - 1
            data = self._block(i)
            chunk = data[off - self.blocks[i][0]:off - self.blocks[i][0] + n]
            out += chunk
            off += len(chunk)
            n -= len(chunk)
        return bytes(out)


class _FileStream:
    def __init__(self, path):
        self.f = open(path, 'rb')

    def read(self, off, n):
        self.f.seek(off)
        return self.f.read(n)


class Psarc:
    def __init__(self, path):
        with open(path, 'rb') as fh:
            magic = fh.read(4)
        self.s = _DsarStream(path) if magic == b'DSAR' else _FileStream(path)
        (magic, _vmaj, _vmin, self.comp, toclen, entsz, nent,
         self.blksz, self.flags) = struct.unpack('>4sHH4sIIIII', self.s.read(0, 32))
        if magic != b'PSAR':
            raise ValueError('not a PSARC stream')
        toc = self.s.read(32, toclen - 32)
        self.entries = []
        for i in range(nent):
            e = toc[i * entsz:(i + 1) * entsz]
            self.entries.append((e[:16], struct.unpack('>I', e[16:20])[0],
                                 int.from_bytes(e[20:25], 'big'), int.from_bytes(e[25:30], 'big')))
        rest = toc[nent * entsz:]
        bw = 2 if self.blksz <= 0x10000 else (3 if self.blksz <= 0x1000000 else 4)
        self.blocksizes = [int.from_bytes(rest[i:i + bw], 'big') for i in range(0, len(rest) - bw + 1, bw)]
        manifest = self._extract(self.entries[0]).decode('utf-8', 'replace')
        self.names = [n for n in re.split(r'[\n\x00]', manifest) if n]
        by_md5 = {e[0]: e for e in self.entries[1:]}
        self.files = {}
        for n in self.names:
            e = by_md5.get(hashlib.md5(n.encode()).digest())
            if e is not None:
                self.files[n] = e

    def _extract(self, e):
        _md5, blk, usize, off = e
        out = bytearray()
        while len(out) < usize:
            cs = self.blocksizes[blk] or self.blksz
            blk += 1
            data = self.s.read(off, cs)
            off += cs
            if cs == min(self.blksz, usize - len(out)):
                try:
                    out += zlib.decompress(data)
                except zlib.error:
                    out += data
            else:
                out += zlib.decompress(data)
        return bytes(out[:usize])

    def extract(self, name):
        return self._extract(self.files[name])


ALIGN = 8192          # start of files >= ALIGN_MIN bytes (as in the working v1.0 archive)
ALIGN_MIN = 0x10000


def _layout(manifest, datas, toclen):
    """Block table / body for a given TOC length. Only the manifest is zlib-compressed:
    the game streams file data as stored blocks (vanilla and v1.0 never compress data)."""
    block_sizes = []
    body = bytearray()
    entries = []
    comp = zlib.compress(manifest, 9)
    if len(comp) < len(manifest) and len(manifest) <= BLOCK:
        entries.append((0, len(manifest), toclen))
        block_sizes.append(len(comp))
        body += comp
    else:
        raise ValueError('manifest must fit one compressed block')
    for data in datas:
        pos = toclen + len(body)
        if len(data) >= ALIGN_MIN and pos % ALIGN:
            gap = ALIGN - pos % ALIGN
            block_sizes.append(gap)          # zero padding block, as in vanilla/v1.0 archives
            body += bytes(gap)
            pos += gap
        entries.append((len(block_sizes), len(data), pos))
        for i in range(0, len(data), BLOCK):
            chunk = data[i:i + BLOCK]
            body += chunk
            block_sizes.append(len(chunk) % BLOCK)
    return entries, block_sizes, body


def write_psarc(path, files):
    """files: list of (archive_name, bytes); names use absolute '/...' paths (flag 2)."""
    names = [n for n, _ in files]
    if any(len(d) == 0 for _, d in files):
        raise ValueError('empty files are not supported')
    manifest = '\n'.join(names).encode()
    md5s = [bytes(16)] + [hashlib.md5(n.encode()).digest() for n in names]
    nent = 1 + len(files)
    toclen = 32 + 30 * nent
    for _ in range(16):
        entries, block_sizes, body = _layout(manifest, [d for _, d in files], toclen)
        new_toclen = 32 + 30 * nent + 2 * len(block_sizes)
        if new_toclen == toclen:
            break
        toclen = new_toclen
    else:
        raise RuntimeError('PSARC layout did not converge')
    out = bytearray(struct.pack('>4sHH4sIIIII', b'PSAR', 1, 4, b'zlib', toclen, 30, nent, BLOCK, 2))
    for md5, (blk, usize, off) in zip(md5s, entries):
        out += md5 + struct.pack('>I', blk) + usize.to_bytes(5, 'big') + off.to_bytes(5, 'big')
    for bs in block_sizes:
        out += struct.pack('>H', bs)
    out += body
    with open(path, 'wb') as f:
        f.write(out)
    return len(out)


def extract_to(archive_dir, names, out_dir, index):
    """Extract named files from the vanilla archives in archive_dir; index maps name -> archive."""
    os.makedirs(out_dir, exist_ok=True)
    opened = {}
    for n in names:
        arc = index[n]
        if arc not in opened:
            opened[arc] = Psarc(os.path.join(archive_dir, arc + '.psarc'))
        dst = os.path.join(out_dir, n.lstrip('/'))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(opened[arc].extract(n))


def build_index(archive_dir, prefixes=('gapack_',)):
    index = {}
    for fn in sorted(os.listdir(archive_dir)):
        if not fn.endswith('.psarc') or not fn.startswith(prefixes):
            continue
        try:
            a = Psarc(os.path.join(archive_dir, fn))
        except ValueError:
            continue
        for n in a.files:
            index.setdefault(n, fn[:-6])
    return index
