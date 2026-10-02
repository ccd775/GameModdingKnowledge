"""Minimal binary FBX (7.x) reader/writer that round-trips byte for byte; arrays decode to numpy on demand."""
import struct, zlib
import numpy as np

ARR = {b'f': ('<f4', 4), b'd': ('<f8', 8), b'l': ('<i8', 8), b'i': ('<i4', 4), b'b': ('?', 1)}
SCALAR = {b'Y': 2, b'C': 1, b'I': 4, b'F': 4, b'D': 8, b'L': 8}


class Prop:
    __slots__ = ('code', 'raw', 'enc', 'array', 'dirty')

    def __init__(self, code, raw, enc=None):
        self.code, self.raw, self.enc, self.array, self.dirty = code, raw, enc, None, False

    def value(self):
        c = self.code
        if c in ARR:
            if self.array is None:
                n, enc, clen = struct.unpack_from('<III', self.raw, 0)
                data = self.raw[12:12 + clen]
                if enc == 1:
                    data = zlib.decompress(data)
                self.array = np.frombuffer(data, ARR[c][0], n).copy()
            return self.array
        if c in (b'S', b'R'):
            return self.raw[4:]
        return struct.unpack('<' + {b'Y': 'h', b'C': 'b', b'I': 'i', b'F': 'f', b'D': 'd', b'L': 'q'}[c], self.raw)[0]

    def set_array(self, arr):
        self.array = np.ascontiguousarray(arr, ARR[self.code][0]); self.dirty = True

    def encode(self):
        if not self.dirty:
            return self.code + self.raw
        n, enc, _ = struct.unpack_from('<III', self.raw, 0)
        data = self.array.tobytes()
        if enc == 1:
            data = zlib.compress(data, 9)
        return self.code + struct.pack('<III', len(self.array), enc, len(data)) + data


class Node:
    __slots__ = ('name', 'props', 'children', 'has_null')

    def __init__(self, name, props, children, has_null):
        self.name, self.props, self.children, self.has_null = name, props, children, has_null

    def find(self, name):
        return [c for c in self.children if c.name == name]


class FBX:
    def __init__(self, path):
        d = open(path, 'rb').read()
        assert d[:21] == b'Kaydara FBX Binary  \x00', 'not a binary FBX'
        self.version = struct.unpack_from('<I', d, 23)[0]
        self.wide = self.version >= 7500
        self.head = d[:27]
        self.top, off = self._read_list(d, 27, len(d))
        self.tail = d[off:]
        self.body_len = off

    def _rec_head(self, d, o):
        if self.wide:
            end, np_, plen = struct.unpack_from('<QQQ', d, o); o += 24
        else:
            end, np_, plen = struct.unpack_from('<III', d, o); o += 12
        nl = d[o]; o += 1
        return end, np_, plen, d[o:o + nl], o + nl

    def _read_list(self, d, o, limit):
        nodes = []
        while o < limit:
            end, np_, plen, name, p = self._rec_head(d, o)
            if end == 0:                     # null record terminating a nested list / the top level
                o = p
                return nodes, o
            props = []
            q = p
            for _ in range(np_):
                c = d[q:q + 1]; q += 1
                if c in ARR:
                    n, enc, clen = struct.unpack_from('<III', d, q)
                    props.append(Prop(c, d[q:q + 12 + clen])); q += 12 + clen
                elif c in (b'S', b'R'):
                    ln = struct.unpack_from('<I', d, q)[0]
                    props.append(Prop(c, d[q:q + 4 + ln])); q += 4 + ln
                else:
                    props.append(Prop(c, d[q:q + SCALAR[c]])); q += SCALAR[c]
            assert q == p + plen
            children, has_null = [], False
            if q < end:
                children, q2 = self._read_list(d, q, end)
                has_null = True
                assert q2 == end, (name, q2, end)
            nodes.append(Node(name, props, children, has_null))
            o = end
        return nodes, o

    def _write_list(self, nodes, start, top):
        out = bytearray()
        for n in nodes:
            pb = b''.join(p.encode() for p in n.props)
            hsize = (24 if self.wide else 12) + 1 + len(n.name)
            body_start = start + len(out) + hsize + len(pb)
            child = self._write_list(n.children, body_start, False) if (n.children or n.has_null) else b''
            end = body_start + len(child)
            fmt = '<QQQ' if self.wide else '<III'
            out += struct.pack(fmt, end, len(n.props), len(pb)) + bytes([len(n.name)]) + n.name + pb + child
        out += bytes(25 if self.wide else 13)          # null record closing this list (nested or top level)
        return bytes(out)

    def save(self, path):
        body = self.head + self._write_list(self.top, 27, True)
        # footer: 16-byte id, 4 zero bytes, padding to a 16-byte boundary (a full 16 when already aligned),
        # version, 120 zero bytes, 16-byte magic -- recomputed because the padding depends on the file length
        foot_id, tail_after_pad = self.tail[:16], self.tail[-140:]       # version + 120 zeros + magic
        assert struct.unpack_from('<I', tail_after_pad, 0)[0] == self.version and self.tail[16:20] == bytes(4)
        # keep the original file's padding rule: same residue of (pad end) mod 16 as the source file
        pad0 = len(self.tail) - 16 - 4 - 140
        residue = (self.body_len + 20 + pad0) % 16
        ofs = len(body) + 16 + 4
        pad = (residue - ofs) % 16
        if pad == 0 and pad0 >= 16:
            pad = 16
        open(path, 'wb').write(body + foot_id + bytes(4) + bytes(pad) + tail_after_pad)

    def objects(self):
        return [n for n in self.top if n.name == b'Objects'][0].children
