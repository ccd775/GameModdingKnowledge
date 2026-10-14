"""i30 .texture: asset = toc header | DAT1 (TextureBuilt 4EDE3593) | SD mip data. HD mips live in another span.
toc keeps 72 bytes of texture meta per texture id (C9FB9DDA, sorted like 36A6C8CC).
Header layout follows Overstrike TextureHeaderSection_I30."""
import struct, sys, os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sm2_dat1 import DAT1        # noqa: E402

T_TEXHDR = 0x4EDE3593
MAGIC = 0x3E7886C8


def split(raw):
    pairs = raw[5]
    extra = struct.unpack_from('<H', raw, 6)[0]
    hl = 8 + 8 * pairs + extra
    return raw[:hl], raw[hl:]


class Texture:
    def __init__(self, raw):
        self.header, body = split(raw)
        self.d = DAT1(body)
        self.dat_size = self.d.size
        self.raw = body[self.d.size:]
        h = self.d.get(T_TEXHDR)
        self.hdr = h
        (self.sd_len, self.hd_len, self.hd_w, self.hd_h, self.sd_w, self.sd_h, self.array_size, self.planes) = \
            struct.unpack_from('<IIHHHHHB', h, 0)
        self.kind = h[18:24]            # per-role bytes (0x91 colour, 0x12 normal, 0x93/0x94 0x02 gloss, 0x10 mask)
        self.fmt = h[24]                # DXGI format
        self.has_hd_flag = h[25]        # 0x80 when an HD part exists
        self.sd_mips = h[26]
        self.hd_mips = h[27]
        self.tail = h[28:32]

    def describe(self):
        return (f'hdr {self.header.hex()} dat1 {self.dat_size} sections {[hex(t) for t in self.d.tags]} '
                f'sd {self.sd_w}x{self.sd_h} mips {self.sd_mips} len {self.sd_len} raw {len(self.raw)} | '
                f'hd {self.hd_w}x{self.hd_h} mips {self.hd_mips} len {self.hd_len} | fmt {self.fmt} '
                f'array {self.array_size} kind {self.kind.hex()} texhdr {self.hdr.hex()}')
