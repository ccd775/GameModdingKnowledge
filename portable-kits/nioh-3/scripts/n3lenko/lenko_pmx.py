"""Full PMX 2.0 reader for the Lenko build: geometry, skin weights, per-face material, vertex morph offsets, plus the
metadata pmx_read.parse gives (bones, materials, rigid bodies, joints).
PMX space: Y up, the model faces -Z, +X is the character's left, MMD units.
usage (check): lenko_pmx.py <file.pmx>"""
import argparse
import struct
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / 'n3ichel'))
import pmx_read  # noqa: E402


class _R:
    def __init__(self, b):
        self.b, self.p = b, 0

    def take(self, fmt):
        v = struct.unpack_from('<' + fmt, self.b, self.p)
        self.p += struct.calcsize('<' + fmt)
        return v if len(v) > 1 else v[0]

    def text(self):
        n = self.take('i')
        s = self.b[self.p:self.p + n]
        self.p += n
        return s.decode('utf-16-le' if self.enc == 0 else 'utf-8')


def load(path):
    """dict: meta (pmx_read.parse), pos (n,3), nrm (n,3), uv (n,2) PMX convention (v down), bi (n,4) bone ids (-1 none),
    bw (n,4), faces (m,3), face_mat (m,), morphs {name: (vertex ids, offsets (k,3))} (vertex morphs only)."""
    meta = pmx_read.parse(str(path))
    r = _R(Path(path).read_bytes())
    assert r.take('4s') == b'PMX '
    r.take('f')
    n = r.take('B')
    g = r.take(f'{n}B')
    r.enc, addl, vsz, tsz, msz, bsz, mosz, rsz = g[:8]
    bfmt = {1: 'b', 2: 'h', 4: 'i'}[bsz]
    for _ in range(4):
        r.text()
    nv = r.take('i')
    pos = np.zeros((nv, 3)); nrm = np.zeros((nv, 3)); uv = np.zeros((nv, 2))
    bi = -np.ones((nv, 4), np.int64); bw = np.zeros((nv, 4))
    for i in range(nv):
        v = r.take('8f')
        pos[i], nrm[i], uv[i] = v[:3], v[3:6], v[6:8]
        r.p += 16 * addl
        t = r.take('B')
        if t == 0:
            bi[i, 0] = r.take(bfmt); bw[i, 0] = 1.0
        elif t in (1, 3):                      # BDEF2 / SDEF (SDEF read as BDEF2)
            bi[i, :2] = r.take(bfmt * 2); w = r.take('f'); bw[i, :2] = (w, 1 - w)
            if t == 3:
                r.p += 36
        else:
            bi[i] = r.take(bfmt * 4); bw[i] = r.take('4f')
        r.take('f')
    nf = r.take('i')
    faces = np.array(struct.unpack_from('<' + {1: 'B', 2: 'H', 4: 'I'}[vsz] * nf, r.b, r.p), np.int64).reshape(-1, 3)
    r.p += nf * vsz
    face_mat = np.concatenate([np.full(m['faces'], i) for i, m in enumerate(meta['materials'])])
    assert len(face_mat) == len(faces)
    # skip textures, materials, bones to reach the morphs
    for _ in range(r.take('i')):
        r.text()
    for _ in range(r.take('i')):
        r.text(); r.text(); r.p += 16 + 12 + 4 + 12 + 1 + 16 + 4 + 2 * tsz + 1
        shared = r.take('B'); r.p += 1 if shared else tsz
        r.text(); r.take('i')
    for _ in range(r.take('i')):
        r.text(); r.text(); r.p += 12 + bsz + 4
        fl = r.take('H')
        r.p += bsz if fl & 1 else 12
        if fl & 0x300:
            r.p += bsz + 4
        if fl & 0x400:
            r.p += 12
        if fl & 0x800:
            r.p += 24
        if fl & 0x2000:
            r.p += 4
        if fl & 0x20:
            r.p += bsz + 8
            for _ in range(r.take('i')):
                r.p += bsz
                if r.take('B'):
                    r.p += 24
    vfmt = {1: 'B', 2: 'H', 4: 'i'}[vsz]
    morphs = {}
    for _ in range(r.take('i')):
        name = r.text(); r.text(); r.take('B'); kind = r.take('B'); k = r.take('i')
        if kind == 1:
            ids = np.zeros(k, np.int64); off = np.zeros((k, 3))
            for j in range(k):
                ids[j] = r.take(vfmt); off[j] = r.take('3f')
            morphs[name] = (ids, off)
        elif kind in (0, 9):
            r.p += k * (mosz + 4)
        elif kind == 2:
            r.p += k * (bsz + 28)
        elif 3 <= kind <= 7:
            r.p += k * (vsz + 16)
        elif kind == 8:
            r.p += k * (msz + 1 + 112)
        elif kind == 10:
            r.p += k * (rsz + 1 + 24)
        else:
            raise ValueError(f'morph kind {kind}')
    return {'meta': meta, 'pos': pos, 'nrm': nrm, 'uv': uv, 'bi': bi, 'bw': bw, 'faces': faces, 'face_mat': face_mat,
            'morphs': morphs}


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('pmx')
    d = load(ap.parse_args().pmx)
    w = (d['bw'] * (d['bi'] >= 0)).sum(1)
    print('vertices', len(d['pos']), 'faces', len(d['faces']), 'weight sum range', w.min(), w.max(),
          'morphs', len(d['morphs']))
