"""Minimal Decima (Death Stranding 2 PC) RTTI reader, ported from Odradek (ShadelessFox).

Reads objects serialized with the binary RTTI format using Odradek's types.json.
Only generic types are supported; types with custom extra binary data must be
handled by callbacks registered in EXTRA.
"""
import json
import struct

import lz4.block

import jolt
import riglogic


def murmur3_x64_128_low64(data: bytes, seed: int = 42) -> int:
    """MurmurHash3 x64 128, returns the low 64 bits (Decima type hashes)."""
    c1, c2 = 0x87C37B91114253D5, 0x4CF5AD432745937F
    m = 0xFFFFFFFFFFFFFFFF
    n = len(data)
    h1 = h2 = seed

    def rotl(x, r):
        return ((x << r) | (x >> (64 - r))) & m

    def fmix(k):
        k ^= k >> 33
        k = (k * 0xFF51AFD7ED558CCD) & m
        k ^= k >> 33
        k = (k * 0xC4CEB9FE1A85EC53) & m
        k ^= k >> 33
        return k

    nblocks = n // 16
    for i in range(nblocks):
        k1, k2 = struct.unpack_from('<QQ', data, i * 16)
        k1 = (k1 * c1) & m; k1 = rotl(k1, 31); k1 = (k1 * c2) & m; h1 ^= k1
        h1 = rotl(h1, 27); h1 = (h1 + h2) & m; h1 = (h1 * 5 + 0x52DCE729) & m
        k2 = (k2 * c2) & m; k2 = rotl(k2, 33); k2 = (k2 * c1) & m; h2 ^= k2
        h2 = rotl(h2, 31); h2 = (h2 + h1) & m; h2 = (h2 * 5 + 0x38495AB5) & m
    tail = data[nblocks * 16:]
    k1 = k2 = 0
    for i in range(len(tail) - 1, -1, -1):
        if i >= 8:
            k2 ^= tail[i] << ((i - 8) * 8)
        else:
            k1 ^= tail[i] << (i * 8)
    if len(tail) > 8:
        k2 = (k2 * c2) & m; k2 = rotl(k2, 33); k2 = (k2 * c1) & m; h2 ^= k2
    if len(tail) > 0:
        k1 = (k1 * c1) & m; k1 = rotl(k1, 31); k1 = (k1 * c2) & m; h1 ^= k1
    h1 ^= n; h2 ^= n
    h1 = (h1 + h2) & m; h2 = (h2 + h1) & m
    h1 = fmix(h1); h2 = fmix(h2)
    h1 = (h1 + h2) & m
    return h1


def type_hash(name: str) -> int:
    return murmur3_x64_128_low64(('00000001_' + name).encode())


class Reader:
    __slots__ = ('buf', 'pos')

    def __init__(self, buf, pos=0):
        self.buf = buf
        self.pos = pos

    def remaining(self):
        return len(self.buf) - self.pos

    def u8(self):
        v = self.buf[self.pos]; self.pos += 1; return v

    def i8(self):
        v = struct.unpack_from('<b', self.buf, self.pos)[0]; self.pos += 1; return v

    def i16(self):
        v = struct.unpack_from('<h', self.buf, self.pos)[0]; self.pos += 2; return v

    def u16(self):
        v = struct.unpack_from('<H', self.buf, self.pos)[0]; self.pos += 2; return v

    def i32(self):
        v = struct.unpack_from('<i', self.buf, self.pos)[0]; self.pos += 4; return v

    def u32(self):
        v = struct.unpack_from('<I', self.buf, self.pos)[0]; self.pos += 4; return v

    def i64(self):
        v = struct.unpack_from('<q', self.buf, self.pos)[0]; self.pos += 8; return v

    def u64(self):
        v = struct.unpack_from('<Q', self.buf, self.pos)[0]; self.pos += 8; return v

    def f16(self):
        v = struct.unpack_from('<e', self.buf, self.pos)[0]; self.pos += 2; return v

    def f32(self):
        v = struct.unpack_from('<f', self.buf, self.pos)[0]; self.pos += 4; return v

    def f64(self):
        v = struct.unpack_from('<d', self.buf, self.pos)[0]; self.pos += 8; return v

    def bytes(self, n):
        v = bytes(self.buf[self.pos:self.pos + n]); self.pos += n; return v


ATOM_FMT = {
    'bool': ('<B', 1), 'wchar': ('<H', 2), 'tchar': ('<H', 2),
    'uint8': ('<B', 1), 'int8': ('<b', 1), 'uint16': ('<H', 2), 'int16': ('<h', 2),
    'uint': ('<I', 4), 'int': ('<i', 4), 'uint32': ('<I', 4), 'int32': ('<i', 4), 'ucs4': ('<I', 4),
    'uint64': ('<Q', 8), 'int64': ('<q', 8), 'uintptr': ('<Q', 8),
    'HalfFloat': ('<e', 2), 'float': ('<f', 4), 'double': ('<d', 8),
}


def _quicksort(items, cmp):
    state = [0]

    def partition(left, right):
        start = left - 1
        end = right
        while True:
            start += 1
            while start < end and cmp(items[start], items[right]) < 0:
                start += 1
            end -= 1
            while end > start and cmp(items[right], items[end]) < 0:
                end -= 1
            if start >= end:
                break
            items[start], items[end] = items[end], items[start]
        items[start], items[right] = items[right], items[start]
        return start

    def qs(left, right):
        if left < right:
            state[0] = (0x19660D * state[0] + 0x3C6EF35F) & 0xFFFFFFFF
            pivot = (state[0] >> 8) % (right - left)
            items[left + pivot], items[right] = items[right], items[left + pivot]
            start = partition(left, right)
            qs(left, start - 1)
            qs(start + 1, right)

    qs(0, len(items) - 1)


class TypeDB:
    def __init__(self, types_path, extensions_path=None):
        with open(types_path, 'r', encoding='utf-8') as f:
            self.types = json.load(f)
        self.extends = {}
        if extensions_path:
            with open(extensions_path, 'r', encoding='utf-8') as f:
                ext = json.load(f)
            self.extends = ext.get('extends', {})
            for k, v in ext.get('types', {}).items():
                self.types.setdefault(k, v)
        self.by_hash = {}
        for name, t in self.types.items():
            if t['kind'] == 'compound':
                self.by_hash[type_hash(name)] = name
        self._plans = {}

    def _collect(self, name, offset, out):
        t = self.types[name]
        for b in t.get('bases', []):
            if b['offset'] < 0:
                continue
            self._collect(b['type'], offset + b['offset'], out)
        for a in t.get('attrs', []):
            if 'category' in a:
                continue
            out.append((a, offset + a['offset']))

    def plan(self, name):
        p = self._plans.get(name)
        if p is None:
            attrs = []
            self._collect(name, 0, attrs)

            def cmp(o1, o2):
                p1 = o1[0].get('property', False)
                p2 = o2[0].get('property', False)
                if p1:
                    if not p2:
                        return 1
                    return (o1[0]['name'] > o2[0]['name']) - (o1[0]['name'] < o2[0]['name'])
                if p2:
                    return -1
                return (o1[1] > o2[1]) - (o1[1] < o2[1])

            _quicksort(attrs, cmp)
            p = [(a['name'], a['type']) for a, _ in attrs if (a['flags'] & 2) == 0]
            self._plans[name] = p
        return p

    def is_subclass(self, name, base):
        if name == base:
            return True
        for b in self.types[name].get('bases', []):
            if b['offset'] >= 0 and self.is_subclass(b['type'], base):
                return True
        return False


class Obj(dict):
    """A deserialized compound; `__type__` holds the type name."""

    def __repr__(self):
        return '<%s %s>' % (self.get('__type__'), {k: v for k, v in self.items() if k != '__type__'})


class TypeReader:
    """Generic RTTI reader. `pointer_hook(info_name, ptr_type, reader)` handles pointers."""

    def __init__(self, db: TypeDB, pointer_hook=None, extra=None):
        self.db = db
        self.pointer_hook = pointer_hook
        self.extra = extra or {}

    def read(self, tname, r: Reader):
        t = self.db.types[tname]
        kind = t['kind']
        if kind == 'atom':
            return self.read_atom(tname, r)
        if kind == 'compound':
            return self.read_compound(tname, r)
        if kind == 'container':
            return self.read_container(t, r)
        if kind in ('enum', 'enum flags'):
            size = t['size']
            return {1: r.i8, 2: r.i16, 4: r.i32}[size]()
        if kind == 'pointer':
            return self.read_pointer(tname, t, r)
        raise NotImplementedError('kind %s (%s)' % (kind, tname))

    def read_atom(self, tname, r):
        base = self.db.types[tname]['base_type']
        f = ATOM_FMT.get(base)
        if f is not None:
            v = struct.unpack_from(f[0], r.buf, r.pos)[0]
            r.pos += f[1]
            return v
        if base == 'String':
            n = r.i32()
            if n == 0:
                return ''
            r.i32()  # crc32
            return r.bytes(n).decode('utf-8', 'replace')
        if base == 'WString':
            n = r.i32()
            return r.bytes(n * 2).decode('utf-16-le', 'replace')
        if base == 'StringHash':
            size = r.i32()
            assert size == 4, size
            return r.i32()
        if base == 'uint128':
            return int.from_bytes(r.bytes(16), 'little')
        if base == 'MotionMatchingVecN':
            return struct.unpack_from('<72f', r.bytes(288))
        raise NotImplementedError('atom %s (%s)' % (tname, base))

    def read_container(self, t, r):
        count = r.i32()
        item = t['item_type']
        it = self.db.types[item]
        hashed = t['type'] in ('HashMap', 'HashSet')
        if not hashed and it['kind'] == 'atom':
            base = it['base_type']
            f = ATOM_FMT.get(base)
            if f is not None:
                if base in ('uint8', 'int8'):
                    return r.bytes(count)
                fmt = '<%d%s' % (count, f[0][1])
                v = list(struct.unpack_from(fmt, r.buf, r.pos))
                r.pos += count * f[1]
                return v
        out = []
        for _ in range(count):
            if hashed:
                r.pos += 4
            out.append(self.read(item, r))
        return out

    def read_pointer(self, tname, t, r):
        present = r.u8()
        if not present:
            return None
        if t['type'] == 'UUIDRef':
            return ('UUIDRef', self.read_compound('GGUUID', r))
        if self.pointer_hook:
            return self.pointer_hook(tname, t, r)
        return (t['type'], None)

    def read_compound(self, tname, r):
        obj = Obj(__type__=tname)
        pos = {}
        for name, atype in self.db.plan(tname):
            pos[name] = r.pos
            obj[name] = self.read(atype, r)
        cb = self._extra_for(tname)
        if cb is not None:
            pos['__extra__'] = r.pos
            cb(self, r, obj)
        obj['__pos__'] = pos  # byte position of every serialized attribute (for in-place patching)
        return obj

    def _extra_for(self, tname):
        # The most specific type with a registered extension callback wins.
        if tname in self.extra:
            return self.extra[tname]
        if tname in UNSUPPORTED_EXTRA:
            raise NotImplementedError('extra data for %s' % tname)
        for b in self.db.types[tname].get('bases', []):
            if b['offset'] >= 0:
                cb = self._extra_for(b['type'])
                if cb is not None:
                    return cb
        return None

    def read_object(self, r):
        h = r.u64()
        size = r.i32()
        tname = self.db.by_hash[h]
        start = r.pos
        obj = self.read_compound(tname, r)
        assert r.pos - start == size, (tname, r.pos - start, size)
        nlinks = r.i32()
        assert nlinks == 0, nlinks
        return obj


# ---------------------------------------------------------------- extra data callbacks

def _x_vertex_array(tr, r, obj):
    n = r.i32(); ns = r.i32(); streaming = r.u8()
    streams = []
    for _ in range(ns):
        s = {'Flags': r.i32(), 'Stride': r.i32()}
        ne = r.i32()
        s['Elements'] = [dict(Offset=r.u8(), StorageType=r.u8(), SlotsUsed=r.u8(), Element=r.u8()) for _ in range(ne)]
        s['Hash'] = r.bytes(16)
        s['DataOffset'] = r.pos
        s['Data'] = None if streaming else r.bytes(s['Stride'] * n)
        streams.append(s)
    obj.update(Count=n, IsStreaming=bool(streaming), Streams=streams)


def _x_index_array(tr, r, obj):
    n = r.i32(); flags = r.i32(); fmt = r.i32(); streaming = r.i32()
    h = r.bytes(16)
    stride = 2 if fmt == 0 else 4
    obj.update(Count=n, Flags=flags, Format=fmt, IsStreaming=bool(streaming), Hash=h, DataOffset=r.pos,
               Data=None if streaming else r.bytes(n * stride))


def _x_data_buffer(tr, r, obj):
    n = r.i32()
    if n == 0:
        obj['Count'] = 0
        return
    streaming = r.i32(); flags = r.i32(); fmt = r.i32(); stride = r.i32()
    obj.update(Count=n, IsStreaming=bool(streaming), Flags=flags, Format=fmt, Stride=stride,
               Data=None if streaming else r.bytes(stride * n))


def _x_texture_info(r):
    hdr = dict(Type=r.i16(), Width=r.u16(), Height=r.u16(), NumSurfaces=r.u16(), NumMips=r.u8(),
               PixelFormat=r.u8(), Unk0A=r.u8(), ColorSpace=r.u8(), Unk0C=r.u8(), Unk0D=r.u8(),
               Unk0E=r.u8(), Unk0F=r.u8(), Hash=r.bytes(16))
    total = r.i32(); emb = r.i32(); strm = r.i32(); smips = r.i32()
    data = dict(TotalSize=total, EmbeddedSize=emb, StreamedSize=strm, StreamedMips=smips,
                EmbeddedDataOffset=r.pos, EmbeddedData=r.bytes(total - 12))
    return dict(Header=hdr, Data=data)


def _x_texture(tr, r, obj):
    obj.update(_x_texture_info(r))


def _x_texture_list(tr, r, obj):
    entries = []
    for _ in range(r.i32()):
        e = dict(StreamingOffset=r.i32(), StreamingLength=r.i32())
        e['Texture'] = _x_texture_info(r)
        entries.append(e)
    obj['Entries'] = entries


def _x_ui_texture(tr, r, obj):
    # one byte, the small and big textures' serialized sizes, then each texture that has a size (checked: every UI
    # texture of the shower scene 6744 parses to exactly its size)
    obj['Unk00'] = r.u8()
    sizes = r.i32(), r.i32()
    for key, size in zip(('SmallTexture', 'BigTexture'), sizes):
        start = r.pos
        obj[key] = _x_texture_info(r) if size > 0 else None
        assert r.pos - start == size, (key, size, r.pos - start)


def _x_ziva(tr, r, obj):
    n = r.i32()
    obj['DataOffset'] = r.pos
    obj['Data'] = r.bytes(n)


def _x_shader(tr, r, obj):
    obj['Size'] = r.i32()
    obj['Unk04'] = tr.read_compound('GGUUID', r)
    obj['Unk14'] = tr.read_compound('GGUUID', r)
    # Odradek reads this one with a plain reader, so it does not consume a group locator.
    obj['Unk24'] = TypeReader.read_compound(tr, 'StreamingDataSource', r)


def _x_localized_text(tr, r, obj):
    # One (text, alt text, subtitle mode) entry per written language (ELanguage minus Unknown: 27 in 1.0.48).
    texts = []
    for _ in range(27):
        text = r.bytes(r.u16()).decode('utf-8', 'replace')
        alt = r.bytes(r.u16()).decode('utf-8', 'replace')
        texts.append((text, alt, r.u8()))
    obj['Texts'] = texts


def _x_physics_shape(tr, r, obj):
    obj['Shape'] = jolt.read_physics_shape(r)


def _x_ragdoll(tr, r, obj):
    obj['Ragdoll'] = jolt.read_ragdoll(r)


def _x_facial_rig(tr, r, obj):
    obj['RigLogic'] = riglogic.read(r)


# Types whose binary form carries extra data that this reader cannot parse (Odradek has callbacks for them).
UNSUPPORTED_EXTRA = {
    'UITextureFrames', 'DebugMouseCursorPS4',
}

EXTRA = {
    'VertexArrayResource': _x_vertex_array,
    'IndexArrayResource': _x_index_array,
    'DataBufferResource': _x_data_buffer,
    'Texture': _x_texture,
    'TextureList': _x_texture_list,
    'UITexture': _x_ui_texture,
    'ZivaRTResource': _x_ziva,
    'ShaderResource': _x_shader,
    'LocalizedTextResource': _x_localized_text,
    'PhysicsShapeResource': _x_physics_shape,
    'PhysicsRagdollResource': _x_ragdoll,
    'FacialRigSettingWithLODResource': _x_facial_rig,
}


# ---------------------------------------------------------------- DirectStorage archives

class DSAR:
    """Random access to a DirectStorage (DSAR, LZ4 chunks) archive."""

    def __init__(self, path):
        self.f = open(path, 'rb')
        hdr = self.f.read(32)
        magic, vmaj, vmin, nchunks, first, total = struct.unpack_from('<IHHIIQ', hdr)
        if magic != 0x52415344:  # 'DSAR'
            self.chunks = None
            self.f.seek(0, 2)
            self.size = self.f.tell()
            return
        raw = self.f.read(nchunks * 32)
        self.chunks = []
        for i in range(nchunks):
            off, coff, size, csize, typ = struct.unpack_from('<QQIIB', raw, i * 32)
            assert typ == 3, typ
            self.chunks.append((off, coff, size, csize))
        self.size = total
        self._starts = [c[0] for c in self.chunks]
        self._cache = {}

    def _chunk(self, i):
        d = self._cache.get(i)
        if d is None:
            off, coff, size, csize = self.chunks[i]
            self.f.seek(coff)
            src = self.f.read(csize)
            d = lz4.block.decompress(src, uncompressed_size=size) if csize != size else src
            if len(self._cache) > 64:
                self._cache.clear()
            self._cache[i] = d
        return d

    def read(self, offset, length):
        if self.chunks is None:
            self.f.seek(offset)
            return self.f.read(length)
        import bisect
        out = bytearray()
        i = bisect.bisect_right(self._starts, offset) - 1
        while length > 0:
            off, coff, size, csize = self.chunks[i]
            d = self._chunk(i)
            s = offset - off
            take = min(length, size - s)
            out += d[s:s + take]
            offset += take
            length -= take
            i += 1
        return bytes(out)

    def close(self):
        self.f.close()
