"""Minimal PMX 2.0/2.1 reader: header, vertices (count only + skin), faces, textures, materials, bones, morphs
(names / kinds), rigid bodies, joints.  usage: pmx.py <file.pmx> [out.json]"""
import argparse
import json
import struct


class R:
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

    def idx(self, size, unsigned=False):
        return self.take({1: 'B' if unsigned else 'b', 2: 'H' if unsigned else 'h', 4: 'i'}[size])


def parse(path):
    r = R(open(path, 'rb').read())
    assert r.take('4s') == b'PMX '
    ver = r.take('f')
    n = r.take('B')
    g = list(r.take(f'{n}B'))
    r.enc, addl_uv, vsz, tsz, msz, bsz, mosz, rsz = g[:8]
    out = {'version': ver, 'globals': g}
    out['name'] = r.text(); out['name_en'] = r.text(); out['comment'] = r.text(); out['comment_en'] = r.text()
    nv = r.take('i')
    skin_types = {}
    for _ in range(nv):
        r.p += 32 + 16 * addl_uv
        t = r.take('B')
        skin_types[t] = skin_types.get(t, 0) + 1
        if t == 0:
            r.p += bsz
        elif t == 1:
            r.p += 2 * bsz + 4
        elif t == 2 or t == 4:
            r.p += 4 * bsz + 16
        elif t == 3:
            r.p += 2 * bsz + 4 + 36
        r.p += 4
    out['vertices'] = nv; out['skin_types'] = skin_types
    nf = r.take('i'); r.p += nf * vsz; out['face_indices'] = nf
    out['textures'] = [r.text() for _ in range(r.take('i'))]
    mats = []
    for _ in range(r.take('i')):
        m = {'name': r.text(), 'name_en': r.text()}
        m['diffuse'] = r.take('4f'); m['specular'] = r.take('3f'); m['spec_power'] = r.take('f'); m['ambient'] = r.take('3f')
        m['flags'] = r.take('B'); m['edge'] = r.take('4f'); m['edge_size'] = r.take('f')
        m['tex'] = r.idx(tsz); m['sphere'] = r.idx(tsz); m['sphere_mode'] = r.take('B')
        shared = r.take('B'); m['toon'] = r.take('B') if shared else r.idx(tsz); m['toon_shared'] = shared
        m['memo'] = r.text(); m['faces'] = r.take('i') // 3
        mats.append(m)
    out['materials'] = mats
    bones = []
    for _ in range(r.take('i')):
        b = {'name': r.text(), 'name_en': r.text(), 'pos': r.take('3f'), 'parent': r.idx(bsz), 'layer': r.take('i')}
        fl = r.take('H'); b['flags'] = fl
        b['tail'] = r.idx(bsz) if fl & 1 else r.take('3f')
        if fl & 0x300:
            b['inherit'] = (r.idx(bsz), r.take('f'))
        if fl & 0x400:
            b['fixed_axis'] = r.take('3f')
        if fl & 0x800:
            b['local_axes'] = (r.take('3f'), r.take('3f'))
        if fl & 0x2000:
            b['ext_parent'] = r.take('i')
        if fl & 0x20:
            ik = {'target': r.idx(bsz), 'loops': r.take('i'), 'limit': r.take('f'), 'links': []}
            for _ in range(r.take('i')):
                lk = {'bone': r.idx(bsz)}
                if r.take('B'):
                    lk['lim'] = (r.take('3f'), r.take('3f'))
                ik['links'].append(lk)
            b['ik'] = ik
        bones.append(b)
    out['bones'] = bones
    morphs = []
    for _ in range(r.take('i')):
        mo = {'name': r.text(), 'name_en': r.text(), 'panel': r.take('B'), 'kind': r.take('B')}
        n = r.take('i'); mo['n'] = n
        k = mo['kind']
        if k == 0 or k == 9:
            sub = []
            for _ in range(n):
                sub.append((r.idx(mosz), r.take('f')) if k == 0 else (r.idx(mosz), r.take('f')))
            mo['sub'] = sub
        elif k == 1:
            r.p += n * (vsz + 12)
        elif k == 2:
            r.p += n * (bsz + 28)
        elif 3 <= k <= 7:
            r.p += n * (vsz + 16)
        elif k == 8:
            mats_ = []
            for _ in range(n):
                mi = r.idx(msz); op = r.take('B'); vals = r.take('28f')
                mats_.append((mi, op, vals))
            mo['mat'] = mats_
        elif k == 10:
            r.p += n * (rsz + 1 + 24)
        morphs.append(mo)
    out['morphs'] = morphs
    for _ in range(r.take('i')):           # display frames
        r.text(); r.text(); r.take('B')
        for _ in range(r.take('i')):
            t = r.take('B'); r.p += bsz if t == 0 else mosz
    rbs = []
    for _ in range(r.take('i')):
        rb = {'name': r.text(), 'name_en': r.text(), 'bone': r.idx(bsz), 'group': r.take('B'), 'nocollide': r.take('H'),
              'shape': r.take('B'), 'size': r.take('3f'), 'pos': r.take('3f'), 'rot': r.take('3f'), 'mass': r.take('f'),
              'lin_damp': r.take('f'), 'ang_damp': r.take('f'), 'restitution': r.take('f'), 'friction': r.take('f'),
              'mode': r.take('B')}
        rbs.append(rb)
    out['rigid_bodies'] = rbs
    js = []
    for _ in range(r.take('i')):
        j = {'name': r.text(), 'name_en': r.text(), 'type': r.take('B'), 'a': r.idx(rsz), 'b': r.idx(rsz),
             'pos': r.take('3f'), 'rot': r.take('3f'), 'lin_lo': r.take('3f'), 'lin_hi': r.take('3f'),
             'ang_lo': r.take('3f'), 'ang_hi': r.take('3f'), 'spring_lin': r.take('3f'), 'spring_ang': r.take('3f')}
        js.append(j)
    out['joints'] = js
    out['tail_bytes'] = len(r.b) - r.p
    return out


def geometry(path):
    """positions (n,3), uvs (n,2), faces (m,3), per-face PMX material index"""
    import numpy as np
    r = R(open(path, 'rb').read())
    assert r.take('4s') == b'PMX '
    r.take('f')
    n = r.take('B')
    g = list(r.take(f'{n}B'))
    r.enc, addl_uv, vsz, tsz, msz, bsz, mosz, rsz = g[:8]
    for _ in range(4):
        r.text()
    nv = r.take('i')
    P = np.zeros((nv, 3)); UV = np.zeros((nv, 2))
    for i in range(nv):
        v = r.take('8f'); P[i] = v[:3]; UV[i] = v[6:8]
        r.p += 16 * addl_uv
        t = r.take('B')
        r.p += {0: bsz, 1: 2 * bsz + 4, 2: 4 * bsz + 16, 3: 2 * bsz + 40, 4: 4 * bsz + 16}[t] + 4
    nf = r.take('i')
    F = np.array(struct.unpack_from('<' + {1: 'B', 2: 'H', 4: 'i'}[vsz] * nf, r.b, r.p)).reshape(-1, 3)
    r.p += nf * vsz
    for _ in range(r.take('i')):
        r.text()
    fm = []
    for mi in range(r.take('i')):
        r.text(); r.text(); r.p += 16 + 12 + 4 + 12 + 1 + 16 + 4 + 2 * tsz + 1
        shared = r.take('B'); r.p += 1 if shared else tsz
        r.text(); fm += [mi] * (r.take('i') // 3)
    return P, UV, F, np.array(fm)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('pmx'); ap.add_argument('out_json', nargs='?', help='also write everything parse() read')
    args = ap.parse_args()
    d = parse(args.pmx)
    if args.out_json:
        json.dump(d, open(args.out_json, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('version', d['version'], 'globals', d['globals'], 'name', d['name'], '/', d['name_en'])
    print('vertices', d['vertices'], d['skin_types'], 'faces', d['face_indices'] // 3, 'tail', d['tail_bytes'])
    print('textures', d['textures'])
    for m in d['materials']:
        print('MAT', m['name'], m['faces'], 'tex', m['tex'], 'sphere', m['sphere'], m['sphere_mode'], 'toon', m['toon'],
              m['toon_shared'], 'flags', hex(m['flags']), 'diffuse', [round(x, 3) for x in m['diffuse']])
    print('bones', len(d['bones']), 'morphs', len(d['morphs']), 'rigid', len(d['rigid_bodies']), 'joints', len(d['joints']))
    print('morphs', [(m['name'], m['panel'], m['kind']) for m in d['morphs']])
