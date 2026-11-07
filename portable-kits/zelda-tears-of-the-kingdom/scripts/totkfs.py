"""TotK container helpers: zstd (+ZsDic dictionaries), SARC, RESTBL."""
import struct, zlib, os
import zstandard as zs

_dicts = None

def load_dicts(romfs):
    """ZsDic.pack.zs is a zstd SARC holding zs.zsdic, pack.zsdic, bcett.byml.zsdic."""
    global _dicts
    if _dicts is None:
        raw = zs.ZstdDecompressor().decompress(open(os.path.join(romfs, 'Pack', 'ZsDic.pack.zs'), 'rb').read(), max_output_size=64 << 20)
        _dicts = {name: zs.ZstdCompressionDict(data) for name, data in sarc_read(raw).items()}
    return _dicts

def dict_for(name, romfs):
    d = load_dicts(romfs)
    if name.endswith('.pack.zs'): return d.get('pack.zsdic')
    if name.endswith('.bcett.byml.zs'): return d.get('bcett.byml.zsdic')
    if name.endswith('.rsizetable.zs'): return None
    return d.get('zs.zsdic')

def zs_decompress(data, name=None, romfs=None):
    dic = dict_for(name, romfs) if (name and romfs) else None
    dctx = zs.ZstdDecompressor(dict_data=dic) if dic else zs.ZstdDecompressor()
    return dctx.decompress(data, max_output_size=512 << 20)

def zs_compress(data, name=None, romfs=None, level=16):
    dic = dict_for(name, romfs) if (name and romfs) else None
    cctx = zs.ZstdCompressor(level=level, dict_data=dic) if dic else zs.ZstdCompressor(level=level)
    return cctx.compress(data)

# ---------------- SARC ----------------
def _hash(name, key):
    h = 0
    for c in name.encode('utf-8'):
        h = (h * key + (c if c < 128 else c - 256)) & 0xFFFFFFFF
    return h

def sarc_read(data):
    assert data[:4] == b'SARC', data[:4]
    bom = data[6:8]
    e = '<' if bom == b'\xff\xfe' else '>'
    hdr_size, bom_, file_size, data_off, ver = struct.unpack_from(e + 'HHIIH', data, 4)
    off = hdr_size
    assert data[off:off + 4] == b'SFAT'
    sfat_hsize, count, key = struct.unpack_from(e + 'HHI', data, off + 4)
    nodes = []
    p = off + sfat_hsize
    for i in range(count):
        h, attr, beg, end = struct.unpack_from(e + 'IIII', data, p); p += 16
        nodes.append((h, attr, beg, end))
    assert data[p:p + 4] == b'SFNT'
    sfnt_hsize = struct.unpack_from(e + 'H', data, p + 4)[0]
    names_off = p + sfnt_hsize
    out = {}
    for h, attr, beg, end in nodes:
        if attr & 0x01000000:
            noff = names_off + (attr & 0xFFFF) * 4
            name = data[noff:data.index(b'\0', noff)].decode('utf-8')
        else:
            name = '%08x' % h
        out[name] = data[data_off + beg:data_off + end]
    return out

def _align_for(name, blob):
    # conservative: 8, with known formats needing more
    if blob[:4] in (b'FRES', b'BNTX', b'BNSH', b'FSHA'): return 0x1000
    if blob[:4] in (b'BYML', b'YB\x00\x00', b'BY\x00\x00', b'YB\x07\x00') or blob[:2] in (b'YB', b'BY'): return 8
    if blob[:4] == b'SARC': return 0x2000
    return 8

def sarc_write(files, key=0x65, min_align=8):
    names = sorted(files.keys(), key=lambda n: _hash(n, key))
    nt = bytearray(); name_offs = {}
    for n in names:
        name_offs[n] = len(nt) // 4
        nt += n.encode('utf-8') + b'\0'
        while len(nt) % 4: nt += b'\0'
    sfat = bytearray(struct.pack('<4sHHI', b'SFAT', 0xC, len(names), key))
    data = bytearray(); entries = []
    max_align = min_align
    for n in names:
        blob = files[n]
        al = max(min_align, _align_for(n, blob)); max_align = max(max_align, al)
        while len(data) % al: data += b'\0'
        beg = len(data); data += blob; entries.append((n, beg, len(data)))
    for n, beg, end in entries:
        sfat += struct.pack('<IIII', _hash(n, key), 0x01000000 | name_offs[n], beg, end)
    sfnt = bytearray(struct.pack('<4sHH', b'SFNT', 8, 0)) + nt
    head_len = 0x14 + len(sfat) + len(sfnt)
    data_off = (head_len + max_align - 1) // max_align * max_align
    out = bytearray(struct.pack('<4sHHIIHH', b'SARC', 0x14, 0xFEFF, 0, data_off, 0x100, 0))
    out += sfat + sfnt
    out += b'\0' * (data_off - len(out))
    out += data
    struct.pack_into('<I', out, 8, len(out))
    return bytes(out)

# ---------------- RESTBL ----------------
class Restbl:
    """RESTBL: magic 'RESTBL', u32 version, u32 string_size (0xA0), u32 crc_count, u32 name_count,
    crc entries (u32 crc32, u32 size) sorted by crc, name entries (char[string_size], u32 size)."""
    def __init__(self, data):
        assert data[:6] == b'RESTBL', data[:6]
        self.version, self.strsize, ncrc, nname = struct.unpack_from('<IIII', data, 6)
        off = 0x16
        self.crc = {}
        for i in range(ncrc):
            c, s = struct.unpack_from('<II', data, off); off += 8
            self.crc[c] = s
        self.names = {}
        for i in range(nname):
            n = data[off:off + self.strsize].split(b'\0')[0].decode('utf-8'); off += self.strsize
            s = struct.unpack_from('<I', data, off)[0]; off += 4
            self.names[n] = s

    def get(self, path):
        if path in self.names: return self.names[path]
        return self.crc.get(zlib.crc32(path.encode('utf-8')) & 0xFFFFFFFF)

    def set(self, path, size):
        if path in self.names: self.names[path] = size; return
        self.crc[zlib.crc32(path.encode('utf-8')) & 0xFFFFFFFF] = size

    def to_bytes(self):
        out = bytearray(b'RESTBL' + struct.pack('<IIII', self.version, self.strsize, len(self.crc), len(self.names)))
        for c in sorted(self.crc): out += struct.pack('<II', c, self.crc[c])
        for n in sorted(self.names):
            b = n.encode('utf-8'); out += b + b'\0' * (self.strsize - len(b)) + struct.pack('<I', self.names[n])
        return bytes(out)
