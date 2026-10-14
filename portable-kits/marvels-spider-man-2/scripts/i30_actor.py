"""i30 (Spider-Man 2 PC) .actor reader / writer (ported 2026-10-13 from the all-suits workflow prototype actorfmt.py;
re-encodes all 11,477 shipped actors byte-exactly, see test_actor_roundtrip.py).

Layout (verified on all hrm_bdy_firsthero actors, see roundtrip.py):
  asset header 16 B : u32 0x521BEEB8 | u8 0 | u8 pairs=1 | u16 extra=0 | (u32 A, u32 B); A low 30 bits = DAT1 size
  DAT1              : magic 'DAT1', u32 type 0x521BEEB8, u32 size, u16 nsec, u16 nunk; section table (tag, off, size) sorted by tag;
                      strings block (C strings, absolute offsets from DAT1 start); sections in data order, 16-aligned
  0x135832C8 ActorPriusBuilt     : 32 B per component  (u64 instance id, u32 name_off, u32 crc32(name), u32 0,
                                   u32 data_off (ABSOLUTE DAT1 offset, 0 = no data), u32 data_size (unpadded), u32 0xFFFFFFFF)
  0x6D4301EF ActorPriusBuiltData : component blobs, each one serialized object, 16-aligned, zero padding between blobs
  serialized object : u32 0, u32 0x03150044, u32 n_children, u32 data_len, then
                      n x (u32 crc32(name), u16 flags (bit0 array, >>4 count), u8 0, u8 node type), n x u32 name_off (ABSOLUTE
                      DAT1 offset into the strings block, one string per occurrence), align4 (blob-relative), values
                      packed WITHOUT alignment (u8/u16/bool/f32 may sit at odd offsets, nested objects start anywhere),
                      align4 (blob-relative; data_len includes it)
  string value      : u32 len, u32 crc32, u64 crc64, bytes, NUL, zero pad so that (len + 1 + pad) % 4 == 0
                      (length-relative, NOT position-relative; inline in the blob, NOT in the strings block)
  empty array       : one 0 byte
"""
import struct, sys, os

sys.path.insert(0, os.environ.get('SM2_ALERT') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'ext', 'ALERT'))

DAT1_MAGIC = 0x44415431
ACTOR_TYPE = 0x521BEEB8
SEC_PRIUS = 0x135832C8
SEC_PRIUS_DATA = 0x6D4301EF
SEC_REFS = 0x3AB204B9
SEC_BUILT = 0x32FAC8E0
SEC_OBJECT = 0x364A6C7C
MARK = 0x03150044

T_U8, T_U16, T_U32, T_I8, T_I16, T_I32, T_F32, T_STR, T_OBJ, T_BOOL, T_ID, T_NULL = (
    0x00, 0x01, 0x02, 0x04, 0x05, 0x06, 0x08, 0x0A, 0x0D, 0x0F, 0x11, 0x13)
SCALAR = {T_U8: '<B', T_U16: '<H', T_U32: '<I', T_I8: '<b', T_I16: '<h', T_I32: '<i', T_F32: '<f', T_BOOL: '<B',
          T_ID: '<Q'}


def crc32(s):
    import dat1lib.crc32 as _crc32   # ALERT, imported on first use (stored hashes are re-used without it)
    return _crc32.hash(s, False)


def crc64(s):
    import dat1lib.crc64 as _crc64
    # asset-id hash (ALERT crc64: lower case, separators normalised); a leading '/' is ignored too
    # (hero_spiderman_invisible.actor stores '/conduits/aud_hero_foley.conduit' with the hash of the path without it)
    return _crc64.hash(s.lstrip('/' + chr(92)))


def pad(n, a):
    return (a - n % a) % a


# ---------------------------------------------------------------- serialized objects

class Str:
    """inline string value; keeps the stored hashes so unmodified data re-encodes byte-exactly"""
    __slots__ = ('s', 'h32', 'h64')

    def __init__(self, s, h32=None, h64=None):
        self.s = s
        self.h32 = (crc32(s) if s else 0) if h32 is None else h32
        self.h64 = (crc64(s) if s else 0) if h64 is None else h64

    def __repr__(self):
        return repr(self.s)


class Field:
    __slots__ = ('name', 'name_off', 'hash', 'flags', 'unk', 'type', 'value')

    def __init__(self, name, name_off, hash_, flags, unk, type_, value):
        self.name, self.name_off, self.hash, self.flags, self.unk, self.type, self.value = (
            name, name_off, hash_, flags, unk, type_, value)

    @property
    def is_array(self):
        return bool(self.flags & 1)


class Obj:
    """ordered list of Field"""

    def __init__(self, fields=None):
        self.fields = fields or []

    def __getitem__(self, k):
        for f in self.fields:
            if f.name == k:
                return f.value
        raise KeyError(k)

    def get(self, k, d=None):
        for f in self.fields:
            if f.name == k:
                return f.value
        return d

    def field(self, k):
        for f in self.fields:
            if f.name == k:
                return f
        return None

    def to_py(self):
        def cv(v):
            if isinstance(v, Obj):
                return v.to_py()
            if isinstance(v, Str):
                return v.s
            if isinstance(v, list):
                return [cv(x) for x in v]
            return v
        return {f.name: cv(f.value) for f in self.fields}


class Reader:
    def __init__(self, buf, base, strings_fn):
        self.b, self.base, self.S = buf, base, strings_fn   # base = absolute position of buf[0] (for alignment)

    def obj(self, p):
        zero, mark, n, dlen = struct.unpack_from('<4I', self.b, p)
        if zero != 0 or mark != MARK:
            raise ValueError('bad object header at %d: %08X %08X' % (p, zero, mark))
        p += 16
        start = p
        hdr = [struct.unpack_from('<IHBB', self.b, p + 8 * i) for i in range(n)]
        p += 8 * n
        offs = list(struct.unpack_from('<%dI' % n, self.b, p))
        p += 4 * n
        p += pad(p, 4)
        o = Obj()
        for (h, fl, unk, t), so in zip(hdr, offs):
            if fl & 1:
                cnt = fl >> 4
                if cnt == 0:
                    if self.b[p] != 0:
                        raise ValueError('empty array byte != 0 at %d' % p)
                    p += 1
                    v = []
                else:
                    v = []
                    for _ in range(cnt):
                        x, p = self.node(p, t)
                        v.append(x)
            else:
                if fl >> 4 != 1:
                    raise ValueError('scalar with count %d at %d' % (fl >> 4, p))
                v, p = self.node(p, t)
            o.fields.append(Field(self.S(so), so, h, fl, unk, t, v))
        end = start + dlen
        if p > end:
            raise ValueError('object overrun: %d > %d' % (p, end))
        tail = bytes(self.b[p:end])
        if any(tail) or len(tail) != pad(p, 4):
            raise ValueError('object tail at %d is %s, expected %d zero bytes' % (p, tail.hex(), pad(p, 4)))
        return o, end

    def node(self, p, t):
        if t in SCALAR:
            fmt = SCALAR[t]
            v = struct.unpack_from(fmt, self.b, p)[0]
            if t == T_BOOL:
                v = bool(v)
            return v, p + struct.calcsize(fmt)
        if t == T_STR:
            ln, h32, h64 = struct.unpack_from('<IIQ', self.b, p)
            p += 16
            s = bytes(self.b[p:p + ln]).decode('utf-8')
            if any(self.b[p + ln:p + ln + 1 + pad(ln + 1, 4)]):
                raise ValueError('non-zero string padding at %d' % (p + ln))
            p += ln + 1 + pad(ln + 1, 4)
            return Str(s, h32, h64), p
        if t == T_OBJ:
            return self.obj(p)
        if t == T_NULL:
            return None, p + 1
        raise ValueError('unknown node type %02X at %d' % (t, p))


class Writer:
    def __init__(self):
        self.b = bytearray()

    def align(self, a):
        self.b += bytes(pad(len(self.b), a))

    def obj(self, o):
        hp = len(self.b)
        self.b += bytes(16)
        start = len(self.b)
        for f in o.fields:
            self.b += struct.pack('<IHBB', f.hash, f.flags, f.unk, f.type)
        for f in o.fields:
            self.b += struct.pack('<I', f.name_off)
        self.align(4)
        for f in o.fields:
            if f.flags & 1:
                if len(f.value) == 0:
                    self.b += b'\0'
                for x in f.value:
                    self.node(x, f.type)
            else:
                self.node(f.value, f.type)
        self.align(4)
        struct.pack_into('<4I', self.b, hp, 0, MARK, len(o.fields), len(self.b) - start)

    def node(self, v, t):
        if t in SCALAR:
            self.b += struct.pack(SCALAR[t], int(v) if t == T_BOOL else v)
        elif t == T_STR:
            raw = v.s.encode('utf-8')
            self.b += struct.pack('<IIQ', len(raw), v.h32, v.h64) + raw + b'\0' + bytes(pad(len(raw) + 1, 4))
        elif t == T_OBJ:
            self.obj(v)
        elif t == T_NULL:
            self.b += b'\0'
        else:
            raise ValueError('type %02X' % t)


# ---------------------------------------------------------------- actor container

class Component:
    def __init__(self, cid, name, name_off, name_hash, zero, data_off, size, tailword, obj=None, raw=None):
        self.id, self.name, self.name_off, self.name_hash, self.zero = cid, name, name_off, name_hash, zero
        self.data_off, self.size, self.tailword, self.obj, self.raw = data_off, size, tailword, obj, raw


class Actor:
    def __init__(self, data):
        self.header = bytes(data[:16])
        magic, z, pairs, extra = struct.unpack_from('<IBBH', data, 0)
        if magic != ACTOR_TYPE or pairs != 1 or extra != 0:
            raise ValueError('unexpected asset header %s' % data[:16].hex())
        self.hdr_a, self.hdr_b = struct.unpack_from('<II', data, 8)
        D = bytes(data[16:])
        self.trailer = b''
        m, typ, size, n, nunk = struct.unpack_from('<IIIHH', D, 0)
        if m != DAT1_MAGIC or typ != ACTOR_TYPE:
            raise ValueError('not an actor DAT1')
        if (self.hdr_a & 0x3FFFFFFF) != size:
            raise ValueError('header A size %d != DAT1 size %d' % (self.hdr_a & 0x3FFFFFFF, size))
        self.trailer = D[size:]
        self.tags = []
        offs = {}
        for i in range(n):
            t, o, s = struct.unpack_from('<III', D, 16 + 12 * i)
            self.tags.append(t)
            offs[t] = (o, s)
        if self.tags != sorted(self.tags):
            raise ValueError('section table not sorted')
        p = 16 + 12 * n
        self.unknowns = D[p:p + 8 * nunk]
        p += 8 * nunk
        self.str_base = p
        order = sorted(self.tags, key=lambda t: offs[t][0])
        blk = D[p:offs[order[0]][0]]
        # strings block = C strings up to the last NUL; what follows is the zero padding to the 16-aligned first section
        self.strings = blk.rstrip(b'\0') + b'\0'
        if offs[order[0]][0] != p + len(self.strings) + pad(p + len(self.strings), 16):
            raise ValueError('strings block padding is not "align 16"')
        self.order = order
        self.sec = {t: D[offs[t][0]:offs[t][0] + offs[t][1]] for t in self.tags}
        self._offs = offs
        self.D = D
        # components
        self.components = []
        pd = self.sec.get(SEC_PRIUS, b'')
        do = offs.get(SEC_PRIUS_DATA, (0, 0))[0]
        for i in range(len(pd) // 32):
            cid, no, nh, z0, off, sz, tw = struct.unpack_from('<QIIIIII', pd, 32 * i)
            c = Component(cid, self.string(no), no, nh, z0, off, sz, tw)
            if off:
                rel = off - do
                blob = self.sec[SEC_PRIUS_DATA]
                c.raw = blob[rel:rel + sz]
                r = Reader(blob, do, self.string)
                c.obj, end = r.obj(rel)
                if end - rel != sz:
                    raise ValueError('component %s: object size %d != %d' % (c.name, end - rel, sz))
            self.components.append(c)
        self.refs = []
        rd = self.sec.get(SEC_REFS, b'')
        for i in range(len(rd) // 16):
            h, so, ext = struct.unpack_from('<QII', rd, 16 * i)
            self.refs.append([h, so, ext])

    # strings block -------------------------------------------------
    def string(self, off):
        p = off - self.str_base
        if p < 0 or p >= len(self.strings):
            raise ValueError('string offset %d outside block' % off)
        e = self.strings.index(b'\0', p)
        return self.strings[p:e].decode('utf-8')

    def add_string(self, s):
        """append (no dedupe, like the original builder: one string per occurrence); returns absolute offset"""
        off = self.str_base + len(self.strings)
        self.strings += s.encode('utf-8') + b'\0'
        return off

    def find_string(self, s):
        k = self.strings.find(b'\0' + s.encode('utf-8') + b'\0')
        if self.strings.startswith(s.encode('utf-8') + b'\0'):
            return self.str_base
        return None if k < 0 else self.str_base + k + 1

    # components ----------------------------------------------------
    def component(self, name):
        return [c for c in self.components if c.name == name]

    # refs ------------------------------------------------------------
    def add_ref(self, path, ext_hash):
        """asset reference row (crc64(path), string off, crc32(extension)) unless already present"""
        h = crc64(path)
        for r in self.refs:
            if r[0] == h:
                return r
        r = [h, self.add_string(path), ext_hash]
        self.refs.append(r)
        return r

    # save --------------------------------------------------------------
    def save(self, reencode=True):
        n = len(self.tags)
        str_end = self.str_base + len(self.strings)
        # pass 1: section sizes (component data needs absolute offsets -> lay out first)
        sec = dict(self.sec)
        if SEC_PRIUS in sec:
            sec[SEC_PRIUS] = bytes(32 * len(self.components))   # placeholder, same size
        if SEC_REFS in sec:
            sec[SEC_REFS] = b''.join(struct.pack('<QII', *r) for r in self.refs)
        offs = {}
        pos = str_end
        for t in self.order:
            pos += pad(pos, 16)
            offs[t] = pos
            if t == SEC_PRIUS_DATA:
                blob = bytearray()
                for c in self.components:
                    if c.obj is None and c.raw is None:
                        c.data_off, c.size = 0, 0
                        continue
                    blob += bytes(pad(len(blob), 16))
                    if reencode and c.obj is not None:
                        w = Writer()
                        w.obj(c.obj)
                        data = bytes(w.b)
                    else:
                        data = c.raw
                    c.data_off, c.size = pos + len(blob), len(data)
                    blob += data
                blob += bytes(pad(len(blob), 16))      # section size includes the tail padding (hero_hailey etc.)
                sec[t] = bytes(blob)
            pos += len(sec[t])
        if SEC_PRIUS in sec:
            sec[SEC_PRIUS] = b''.join(struct.pack('<QIIIIII', c.id, c.name_off, c.name_hash, c.zero, c.data_off, c.size,
                                                  c.tailword) for c in self.components)
        size = pos
        out = bytearray(struct.pack('<IIIHH', DAT1_MAGIC, ACTOR_TYPE, size, n, len(self.unknowns) // 8))
        for t in sorted(self.tags):
            out += struct.pack('<III', t, offs[t], len(sec[t]))
        out += self.unknowns + self.strings
        for t in self.order:
            out += bytes(offs[t] - len(out))
            out += sec[t]
        assert len(out) == size
        a = (self.hdr_a & 0xC0000000) | size
        hdr = struct.pack('<IBBHII', ACTOR_TYPE, 0, 1, 0, a, self.hdr_b)
        return hdr + bytes(out) + self.trailer


def load(path):
    return Actor(open(path, 'rb').read())


def dump_obj(o, ind='  ', out=print):
    for f in o.fields:
        tn = {T_U8: 'u8', T_U16: 'u16', T_U32: 'u32', T_I8: 'i8', T_I16: 'i16', T_I32: 'i32', T_F32: 'f32', T_STR: 'str',
              T_OBJ: 'obj', T_BOOL: 'bool', T_ID: 'id64', T_NULL: 'null'}.get(f.type, '%02X' % f.type)
        arr = '[%d]' % (f.flags >> 4) if f.flags & 1 else ''
        head = '%s%s: %s%s (hash %08X name@%d flags %04X unk %d)' % (ind, f.name, tn, arr, f.hash, f.name_off, f.flags, f.unk)
        vals = f.value if f.flags & 1 else [f.value]
        if f.type == T_OBJ:
            out(head)
            for i, v in enumerate(vals):
                if f.flags & 1:
                    out('%s  [%d]' % (ind, i))
                dump_obj(v, ind + '    ', out)
        else:
            def fmt(v):
                if isinstance(v, Str):
                    return '%r (crc32 %08X%s, crc64 %016X%s)' % (
                        v.s, v.h32, '' if v.h32 == (crc32(v.s) if v.s else 0) else ' MISMATCH',
                        v.h64, '' if v.h64 == (crc64(v.s) if v.s else 0) else ' MISMATCH')
                if f.type == T_ID:
                    return '0x%016X' % v
                return repr(v)
            out(head + ' = ' + ', '.join(fmt(v) for v in vals))
