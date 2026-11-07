"""Minimal BYML (v2-v7, little endian) reader/writer for TotK bgyml files."""
import struct

class Byml:
    def __init__(self, data):
        self.d = data
        assert data[:2] in (b'YB', b'BY'), data[:2]
        self.e = '<' if data[:2] == b'YB' else '>'
        self.version, kt, st, root = struct.unpack_from(self.e + 'HIII', data, 2)
        self.keys = self._strtab(kt) if kt else []
        self.strs = self._strtab(st) if st else []
        self.root = self._node(root) if root else None

    def _u24(self, off):
        b = self.d[off:off + 3]
        return int.from_bytes(b, 'little' if self.e == '<' else 'big')

    def _strtab(self, off):
        n = self._u24(off + 1)
        offs = struct.unpack_from(self.e + f'{n + 1}I', self.d, off + 4)
        return [self.d[off + o:self.d.index(b'\0', off + o)].decode('utf-8') for o in offs[:n]]

    def _node(self, off):
        t = self.d[off]
        n = self._u24(off + 1)
        if t == 0xC0:  # array
            types = self.d[off + 4:off + 4 + n]
            voff = off + 4 + ((n + 3) & ~3)
            return [self._val(types[i], voff + 4 * i) for i in range(n)]
        if t == 0xC1:  # dict
            out = {}
            for i in range(n):
                p = off + 4 + 8 * i
                k = self._u24(p); vt = self.d[p + 3]
                out[self.keys[k]] = self._val(vt, p + 4)
            return out
        raise ValueError(f'node type {t:#x} at {off:#x}')

    def _val(self, t, p):
        e = self.e
        if t in (0xC0, 0xC1): return self._node(struct.unpack_from(e + 'I', self.d, p)[0])
        if t == 0xA0: return self.strs[struct.unpack_from(e + 'I', self.d, p)[0]]
        if t == 0xD0: return bool(struct.unpack_from(e + 'I', self.d, p)[0])
        if t == 0xD1: return struct.unpack_from(e + 'i', self.d, p)[0]
        if t == 0xD2: return struct.unpack_from(e + 'f', self.d, p)[0]
        if t == 0xD3: return ('u32', struct.unpack_from(e + 'I', self.d, p)[0])
        if t in (0xD4, 0xD5, 0xD6):
            o = struct.unpack_from(e + 'I', self.d, p)[0]
            fmt = {0xD4: 'q', 0xD5: 'Q', 0xD6: 'd'}[t]
            v = struct.unpack_from(e + fmt, self.d, o)[0]
            return ('u64', v) if t == 0xD5 else (('i64', v) if t == 0xD4 else ('f64', v))
        if t == 0xFF: return None
        if t == 0xA1:
            o = struct.unpack_from(e + 'I', self.d, p)[0]; ln = struct.unpack_from(e + 'I', self.d, o)[0]
            return ('bin', self.d[o + 4:o + 4 + ln])
        raise ValueError(f'value type {t:#x}')

def dump(v, ind=0):
    pad = '  ' * ind
    if isinstance(v, dict):
        return '\n'.join(f'{pad}{k}:' + ('\n' + dump(x, ind + 1) if isinstance(x, (dict, list)) and x else f' {x!r}') for k, x in v.items())
    if isinstance(v, list):
        return '\n'.join(f'{pad}-' + ('\n' + dump(x, ind + 1) if isinstance(x, (dict, list)) and x else f' {x!r}') for x in v)
    return pad + repr(v)

def load(data): return Byml(data).root
