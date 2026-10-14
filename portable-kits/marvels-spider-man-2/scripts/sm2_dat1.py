"""DAT1 container read/write, byte-compatible with Overstrike's DAT1.cs (Save(): sections in original offset
order, 16-byte aligned; table sorted by tag; unknowns + strings block preserved)."""
import struct

MAGIC = 0x44415431


class DAT1:
    def __init__(self, data, base=0):
        d = data
        self.magic, self.unk1, self.size, self.n, self.nunk = struct.unpack_from('<IIIHH', d, base)
        if self.magic != MAGIC:
            raise ValueError('not DAT1')
        self.tags, off, siz = [], {}, {}
        for i in range(self.n):
            t, o, s = struct.unpack_from('<III', d, base + 16 + 12 * i)
            self.tags.append(t)
            off[t], siz[t] = o, s
        p = base + 16 + 12 * self.n
        self.unknowns = bytes(d[p:p + 8 * self.nunk])
        p += 8 * self.nunk
        mn = min(off.values()) if off else self.size
        self.strings = bytes(d[p:base + mn])
        self.order = sorted(self.tags, key=lambda t: off[t])
        self.sections = {t: bytes(d[base + off[t]:base + off[t] + siz[t]]) for t in self.tags}

    def has(self, t):
        return t in self.sections

    def get(self, t):
        return self.sections.get(t)

    def set(self, t, data, after=None):
        """Replace or add a section. New sections go after `after` (tag) in data order, else at the end."""
        if t not in self.sections:
            self.tags.append(t)
            if after is not None and after in self.order:
                self.order.insert(self.order.index(after) + 1, t)
            else:
                self.order.append(t)
        self.sections[t] = bytes(data)

    def remove(self, t):
        if t in self.sections:
            del self.sections[t]
            self.tags.remove(t)
            self.order.remove(t)

    def string_base(self):
        return 16 + 12 * len(self.tags) + len(self.unknowns)

    def save(self, align=None):
        """align: {tag: bytes} overrides (default 16). Models need MODEL_ALIGN (observed in all originals)."""
        align = align or {}
        n = len(self.tags)
        off = 16 + 12 * n + len(self.unknowns) + len(self.strings)
        offs = {}
        for t in self.order:
            a = align.get(t, 16)
            if off % a:
                off += a - off % a
            offs[t] = off
            off += len(self.sections[t])
        out = bytearray(struct.pack('<IIIHH', self.magic, self.unk1, off, n, len(self.unknowns) // 8))
        for t in sorted(self.tags):
            out += struct.pack('<III', t, offs[t], len(self.sections[t]))
        out += self.unknowns + self.strings
        for t in self.order:
            out += bytes(offs[t] - len(out))
            out += self.sections[t]
        return bytes(out)


# ModelLook, ModelLookGroup, ModelSubset, ModelSubsetGeomData, ModelLocator start on 64 bytes in every original
MODEL_ALIGN = {0x06EB7EFC: 64, 0x4CCEA4AD: 64, 0x78D9CBDE: 64, 0xF4EA9E18: 64, 0x9F614FAB: 64}
