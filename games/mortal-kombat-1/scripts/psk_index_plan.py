"""Read-only native chunk audit: match FULL PSK wedge-index streams and emit a new plan.

This identifies byte ranges, not runtime usage or complete LOD coverage. No game data
or engine offsets are embedded. Review the plan before mk1_checks hide-indices.
"""
import argparse
import hashlib
import itertools
import json
import struct
from pathlib import Path


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_psk(path):
    blob = Path(path).read_bytes()
    pos, vertex_count, indices = 0, None, None
    while pos < len(blob):
        if len(blob) - pos < 32:
            raise ValueError('Truncated PSK header')
        name, _flag, size, count = struct.unpack_from('<20s3i', blob, pos)
        name = name.rstrip(b'\0')
        pos += 32
        if size < 0 or count < 0 or pos + size * count > len(blob):
            raise ValueError('Invalid PSK chunk length')
        if name == b'VTXW0000':
            if vertex_count is not None or size != 16:
                raise ValueError('Unsupported or duplicate wedge chunk')
            vertex_count = count
        if name in (b'FACE0000', b'FACE3200'):
            fmt, expected = ('<3H', 12) if name == b'FACE0000' else ('<3I', 18)
            if indices is not None or size != expected:
                raise ValueError('Unsupported or duplicate face chunk')
            indices = [v for i in range(count) for v in struct.unpack_from(fmt, blob, pos + i * size)]
        pos += size * count
    if not indices or not vertex_count or max(indices) >= vertex_count:
        raise ValueError('Missing/out-of-range PSK wedge indices')
    return blob, vertex_count, indices


def create_plan(chunk, psks):
    raw = Path(chunk).read_bytes()
    if not psks:
        raise ValueError('At least one independent PSK is required')
    rows, evidence = {}, []
    for psk in psks:
        blob, vertex_count, indices = read_psk(psk)
        matching_offsets = set()
        for width, code in ((2, 'H'), (4, 'I')):
            if max(indices) >= 1 << (width * 8):
                continue
            header = bytes([width]) + struct.pack('<II', width, len(indices))
            candidates = []
            cursor = 0
            while True:
                found = raw.find(header, cursor)
                if found < 0:
                    break
                offset = found + len(header)
                end = offset + len(indices) * width
                if end <= len(raw):
                    candidates.append((offset, raw[offset:end]))
                cursor = found + 1
            if not candidates:
                continue
            for order in itertools.permutations(range(3)):
                packed = struct.pack('<' + str(len(indices)) + code,
                                     *(indices[i+k] for i in range(0, len(indices), 3) for k in order))
                for offset, data in candidates:
                    if packed != data:
                        continue
                    matching_offsets.add(offset)
                    key = (offset, width, len(indices))
                    if key not in rows:
                        rows[key] = {'offset': offset, 'width': width, 'count': len(indices),
                                     'vertex_count': vertex_count, 'buffer_sha256': digest(data),
                                     'evidence': []}
                    proof = {'psk': str(psk), 'psk_sha256': digest(blob), 'permutation': list(order)}
                    if proof not in rows[key]['evidence']:
                        rows[key]['evidence'].append(proof)
        if not matching_offsets:
            raise ValueError(f'No complete stream match for {psk}; prefix/count matches are insufficient')
        evidence.append({'psk': str(psk), 'sha256': digest(blob), 'vertices': vertex_count,
                         'triangles': len(indices)//3, 'matching_offsets': sorted(matching_offsets)})
    buffers = sorted(rows.values(), key=lambda row: row['offset'])
    for a, b in zip(buffers, buffers[1:]):
        if a['offset'] + a['width'] * a['count'] > b['offset']:
            raise ValueError('Overlapping candidate ranges; manual audit required')
    return {'source_sha256': digest(raw), 'buffers': buffers, 'psk_evidence': evidence,
            'scope': 'Complete supplied PSK streams only; all-LOD/runtime coverage NOT established'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('chunk', type=Path)
    ap.add_argument('output', type=Path)
    ap.add_argument('--psk', type=Path, action='append', required=True)
    args = ap.parse_args()
    if args.output.exists():
        raise ValueError('Output must be new; refusing overwrite')
    plan = create_plan(args.chunk, args.psk)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(plan, stream, indent=2)
    print(json.dumps({'buffers': len(plan['buffers']), 'psks': len(args.psk), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
