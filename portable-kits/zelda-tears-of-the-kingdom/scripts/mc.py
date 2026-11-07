"""MeshCodec (.mc) helpers: MCPK header + magicless zstd (matches Switch Toolbox MeshCodec.cs)."""
import struct, sys, zstandard as zs

def mc_decompress(data: bytes) -> bytes:
    magic, ver, flags = struct.unpack_from('<4sII', data, 0)
    assert magic == b'MCPK', magic
    size = (flags >> 5) << (flags & 0xf)
    return zs.ZstdDecompressor(format=zs.FORMAT_ZSTD1_MAGICLESS).decompress(data[12:], max_output_size=size)

def mc_compress(raw: bytes, level: int = 19) -> bytes:
    n = len(raw)
    aligned = (-n) % 0x1000
    flags = (((n + aligned) >> 0xc) << 5) + 0xc
    params = zs.ZstdCompressionParameters.from_level(level, format=zs.FORMAT_ZSTD1_MAGICLESS,
                                                      write_content_size=False, write_checksum=False, write_dict_id=False)
    comp = zs.ZstdCompressor(compression_params=params).compress(raw)
    return b'MCPK' + bytes([1, 1, 0, 0]) + struct.pack('<I', flags) + comp

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__ + ' d = decompress a .bfres.mc, c = compress.')
    ap.add_argument('op', choices=('d', 'c')); ap.add_argument('src'); ap.add_argument('dst')
    a = ap.parse_args(); op, src, dst = a.op, a.src, a.dst
    data = open(src, 'rb').read()
    out = mc_decompress(data) if op == 'd' else mc_compress(data)
    open(dst, 'wb').write(out)
    print(op, src, len(data), '->', dst, len(out))
