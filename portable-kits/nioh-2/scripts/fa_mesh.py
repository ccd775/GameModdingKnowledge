"""Decode vb/ib dumps of a frame analysis draw into numpy arrays."""
import json
import os

import numpy as np

FMT = {'R32G32B32_FLOAT': ('<f4', 3), 'R32G32B32A32_FLOAT': ('<f4', 4), 'R32G32_FLOAT': ('<f4', 2), 'R32_FLOAT': ('<f4', 1),
       'R16G16B16A16_FLOAT': ('<f2', 4), 'R16G16_FLOAT': ('<f2', 2), 'R8G8B8A8_UINT': ('u1', 4), 'R8G8B8A8_UNORM': ('u1', 4),
       'B8G8R8A8_UNORM': ('u1', 4), 'R16G16B16A16_SINT': ('<i2', 4), 'R16G16B16A16_UINT': ('<u2', 4), 'R32G32B32A32_UINT': ('<u4', 4)}


def load_draw(fadir, rec):
    """returns dict semantic -> array (vertex count x n), plus 'ib' (triangles) and vb hashes."""
    out = {}
    nverts = None
    for k in ('vb0', 'vb1', 'vb2'):
        if k not in rec or 'buf' not in rec[k]:
            continue
        slot = int(k[2:])
        stride = int(rec[k]['hdr']['stride'])
        raw = open(os.path.join(fadir, rec[k]['buf']), 'rb').read()
        n = len(raw) // stride
        nverts = n if nverts is None else min(nverts, n)
        arr = np.frombuffer(raw[:n * stride], dtype=np.uint8).reshape(n, stride)
        for lay in rec[k]['layout']:
            name, rest = lay.split(':', 1)
            fmt, loc = rest.split('@')
            s, off = loc.split('+')
            if int(s) != slot or fmt not in FMT:
                continue
            off = int(off)
            if name in ('BLENDWEIGHT1', 'BLENDINDICES1', 'TEXCOORD1') and off == 0 and fmt == 'R32G32B32_FLOAT' and name not in ('TEXCOORD1',):
                continue  # 3DMigoto placeholder elements
            if name == 'TEXCOORD1' and off == 0:
                continue
            dt, cnt = FMT[fmt]
            size = np.dtype(dt).itemsize * cnt
            if off + size > stride:
                continue
            out[name] = arr[:, off:off + size].copy().view(dt).reshape(n, cnt)
    if 'ib' in rec and 'buf' in rec['ib']:
        fmt = rec['ib']['hdr'].get('format', '')
        dt = '<u2' if 'R16' in fmt else '<u4'
        ib = np.frombuffer(open(os.path.join(fadir, rec['ib']['buf']), 'rb').read(), dtype=dt)
        first = int(rec['ib']['hdr'].get('first index', 0))
        cnt = int(rec['ib']['hdr'].get('index count', len(ib)))
        out['tris'] = ib[first:first + cnt].reshape(-1, 3).astype(np.int64)
    out['nverts'] = nverts
    return out
