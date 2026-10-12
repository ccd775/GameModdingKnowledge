#!/usr/bin/env python3
"""Split a native shader package (shader_dx12/0x<hash>.file, an IDRK entry) into its DXBC/DXIL blobs.

With --dxc (dxc.exe from the Windows SDK) the first pixel shader, the first vertex shader and the first skinning vertex
shader (one that declares BLENDWEIGHT) are disassembled to text. That is how the 8-weight skinning rule was read:
the vertex shader uses the first 7 stored weights and gives the 8th bone the remainder, then normalises N and T.

  python shader_dump.py <shader_dx12/0x00b6c7f0.file> --output <new dir> [--dxc <dxc.exe>]
"""
from __future__ import annotations

import argparse
import json
import struct
import subprocess
import sys
import zlib
from pathlib import Path


def unpack(data):
    """Payload of a stand-alone IDRK0000 entry (stored or zlib chunked)."""
    if data[:8] != b'IDRK0000':
        raise ValueError('not an IDRK0000 entry')
    total, packed, size = struct.unpack_from('<3Q', data, 8)
    flags = struct.unpack_from('<I', data, 44)[0]
    pos = total - packed
    if packed == size:
        return data[pos:pos + size]
    parts, n = [], 0
    while n < size:
        if flags & 0x100000:
            k = struct.unpack_from('<I', data, pos)[0]; pos += 4
        else:
            k = struct.unpack_from('<H', data, pos)[0]; pos += 10
        parts.append(zlib.decompress(data[pos:pos + k])); pos += k
        n += len(parts[-1])
    if n != size:
        raise ValueError(f'decoded {n} bytes, expected {size}')
    return b''.join(parts)


def blobs(data):
    """Every DXBC container: offset, size, shader stage (0 pixel, 1 vertex, ...), whether it reads BLENDWEIGHT."""
    out, pos = [], 0
    while (pos := data.find(b'DXBC', pos)) >= 0:
        size, count = struct.unpack_from('<2I', data, pos + 24)
        blob = data[pos:pos + size]
        if len(blob) != size or size < 32 + 4 * count:
            pos += 4
            continue
        offsets = struct.unpack_from(f'<{count}I', blob, 32)
        dxil = [o for o in offsets if o + 12 <= size and blob[o:o + 4] == b'DXIL']
        stage = struct.unpack_from('<I', blob, dxil[0] + 8)[0] >> 16 if dxil else None
        out.append({'offset': pos, 'size': size, 'stage': stage, 'blend_weights': b'BLENDWEIGHT' in blob})
        pos += size
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('shader_file')
    ap.add_argument('--output', required=True, help='a new directory')
    ap.add_argument('--dxc', help='dxc.exe for -dumpbin disassembly')
    args = ap.parse_args(argv)
    out = Path(args.output)
    if out.exists():
        raise SystemExit(f'refusing to reuse {out}')
    data = unpack(Path(args.shader_file).read_bytes())
    found = blobs(data)
    out.mkdir(parents=True)
    picks = {}
    for b in found:
        key = {0: 'pixel', 1: 'vertex-skin' if b['blend_weights'] else 'vertex'}.get(b['stage'])
        if key and key not in picks:
            picks[key] = b
    for name, b in picks.items():
        path = out / f'{name}.dxil'
        path.write_bytes(data[b['offset']:b['offset'] + b['size']])
        b['file'] = path.name
        if args.dxc:
            r = subprocess.run([args.dxc, '-dumpbin', str(path)], capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(r.stderr)
            (out / f'{name}.txt').write_text(r.stdout, encoding='utf-8')
    (out / 'index.json').write_text(json.dumps({'source': Path(args.shader_file).name, 'blobs': found}, indent=1),
                                    encoding='utf-8')
    print(json.dumps({'blobs': len(found), 'stages': sorted({b['stage'] for b in found if b['stage'] is not None}),
                      'written': sorted(picks)}))
    return 0


if __name__ == '__main__':
    sys.exit(main())
