"""GoWR PC WAD (WTOC v2) reader. Offset resolution ported from GOWTool (gowr-pc branch, src/Wad.cpp)."""
import struct, collections

ENTRY = 0x90

class Entry:
    __slots__ = ('idx','group','type','size','h1','h2','name','raw','bitset','unk2_20','flush','offset','offset2','abs')
    def __init__(self, idx, raw):
        self.idx = idx
        self.raw = raw
        self.group, self.type, self.size = struct.unpack_from('<HHI', raw, 0)
        self.h1, self.h2 = struct.unpack_from('<QQ', raw, 8)
        self.name = raw[0x18:0x50].split(b'\0')[0].decode('latin1')
        self.bitset = raw[0x6F]
        self.unk2_20 = raw[0x50 + 20]
        self.flush = raw[0x72]
        self.offset = struct.unpack_from('<I', raw, 0x78)[0]
        self.offset2 = struct.unpack_from('<I', raw, 0x88)[0]
        self.abs = None
    def __repr__(self):
        return f'<{self.idx} {self.group}/{self.type} {self.name} size={self.size:#x} abs={self.abs if self.abs is None else hex(self.abs)}>'

class Wad:
    def __init__(self, data):
        if data[:4] == b'\x04\x22\x4d\x18':
            import lz4.frame
            data = lz4.frame.decompress(data)
        self.data = data
        assert data[:4] == b'WTOC', data[:4]
        self.header = data[:0x40]
        self.ver, self.count = struct.unpack_from('<II', data, 4)
        self.entries = [Entry(i, data[0x40+i*ENTRY:0x40+(i+1)*ENTRY]) for i in range(self.count)]
        self.base = 0x40 + self.count*ENTRY
        self._resolve()

    def _resolve(self):
        E = self.entries
        read_off = self.base
        bits_offs = collections.defaultdict(int)
        flushq = collections.OrderedDict()
        def q(k):
            if k not in flushq:
                flushq[k] = collections.deque()
                # keep map ordering like std::map (sorted keys)
            return flushq[k]
        def flush_all():
            nonlocal read_off
            for k in sorted(flushq.keys()):
                dq = flushq[k]
                if not dq and True:
                    pass
            # emulate std::map iteration in sorted key order
        for i, e in enumerate(E):
            if e.flush == 1:
                if e.name != 'autopad':
                    q(e.bitset).append(i)
                if e.unk2_20 != 0:
                    q(8).append(i)
                for k in sorted(flushq.keys()):
                    dq = flushq[k]
                    read_off -= bits_offs[k]
                    temp = bits_offs[k]
                    while dq:
                        j = dq.popleft()
                        f = E[j]
                        if k == 8 and f.bitset != 8:
                            temp = f.offset2 + 16
                            bits_offs[k] = f.offset2 + 16
                        else:
                            f.abs = read_off + f.offset
                            bits_offs[k] = f.offset + f.size
                            temp = f.offset + f.size
                    read_off += temp
                if e.name == 'autopad':
                    e.abs = read_off
                    read_off += e.size
            else:
                q(e.bitset).append(i)
                if e.unk2_20 != 0:
                    q(8).append(i)
        for k in sorted(flushq.keys()):
            dq = flushq[k]
            if dq:
                read_off -= bits_offs[k]
                temp = 0
                while dq:
                    j = dq.popleft()
                    f = E[j]
                    if k == 8 and f.bitset != 8:
                        temp = f.offset2 + 16
                        bits_offs[k] = f.offset2 + 16
                    else:
                        f.abs = read_off + f.offset
                        bits_offs[k] = f.offset + f.size
                        temp = f.offset + f.size
                read_off += temp
        self.end = read_off

    def get(self, e):
        if isinstance(e, int): e = self.entries[e]
        return self.data[e.abs:e.abs+e.size]

    def find(self, name, type=None):
        return [e for e in self.entries if e.name == name and (type is None or e.type == type)]

    def test(self):
        bad = []
        for e in self.entries:
            if e.abs is None or e.abs + e.size > len(self.data):
                bad.append((e, 'range')); continue
            b = self.get(e)
            if e.type == 1 and e.name.startswith('MESH_') and struct.unpack_from('<I', b, 0)[0] != 655372: bad.append((e,'mesh'))
            if e.type == 1 and e.name.startswith('MG_') and struct.unpack_from('<I', b, 0)[0] != 65548: bad.append((e,'mg'))
            if e.name == 'DCClientGUID' and not all(chr(c) in '.-0123456789ABCDEFabcdefghijklmnopqrstuvwxyzGHIJKLMNOPQRSTUVWXYZ' for c in b[:-1]): bad.append((e,'guid'))
        return bad

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='List the entries of a GoWR PC WAD (plain or LZ4) and check their ranges.')
    ap.add_argument('wad')
    w = Wad(open(ap.parse_args().wad, 'rb').read())
    for e in w.entries:
        print(e)
    print('count', w.count, 'base', hex(w.base), 'end', hex(w.end), 'len', hex(len(w.data)))
    bad = w.test()
    print('bad', len(bad), bad[:10])
