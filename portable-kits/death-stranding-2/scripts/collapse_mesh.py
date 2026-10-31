"""Hide a mesh while keeping its vertex and index counts: every vertex of a submesh moves to one point inside the
mesh and is bound 100% to one joint, so all triangles stay degenerate under any pose.

python collapse_mesh.py <in.ascii> <out.ascii> <skeleton.ascii> [--grow=<copies>:<dz>]
--grow is a pipeline test: instead of collapsing, duplicate each submesh with a z offset (changes counts).
"""
import argparse
import sys

import numpy as np

from ds2ascii import read_meshes, read_skeleton, write


def collapse(m):
    bi = np.asarray(m['bi'])
    bw = np.asarray(m['bw'])
    dom = bi[np.arange(len(bi)), bw.argmax(1)]
    vals, counts = np.unique(dom, return_counts=True)
    joint = int(vals[counts.argmax()])
    point = m['pos'][dom == joint].mean(0)
    n = dict(m)
    nv = len(m['pos'])
    slots = len(m['bi'][0])
    n['pos'] = np.tile(point, (nv, 1))
    n['bi'] = [[joint] * slots for _ in range(nv)]
    n['bw'] = [[1.0] + [0.0] * (slots - 1) for _ in range(nv)]
    return n, joint, point


def grow(m, copies, dz):
    n = dict(m)
    nv = len(m['pos'])
    n['pos'] = np.concatenate([m['pos'] + [0, 0, dz * k] for k in range(copies)])
    n['nrm'] = np.concatenate([m['nrm']] * copies)
    n['col'] = np.concatenate([m['col']] * copies)
    n['uv'] = [np.concatenate([u] * copies) for u in m['uv']]
    n['bi'] = m['bi'] * copies
    n['bw'] = m['bw'] * copies
    n['faces'] = np.concatenate([m['faces'] + nv * k for k in range(copies)])
    return n


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('skeleton')
    ap.add_argument('--grow', help='<copies>:<dz>: duplicate each submesh instead of collapsing (pipeline test)')
    a = ap.parse_args()
    src, dst, skel = a.src, a.dst, a.skeleton
    opts = {'grow': a.grow} if a.grow else {}
    bones = read_skeleton(skel)
    _, meshes = read_meshes(src)
    out = []
    for m in meshes:
        if 'grow' in opts:
            c, dz = opts['grow'].split(':')
            out.append(grow(m, int(c), float(dz)))
            print('%s grown x%s' % (m['name'], c))
        else:
            n, joint, point = collapse(m)
            out.append(n)
            print('%s collapsed to joint %d (%s) at %s' % (m['name'], joint, bones[joint]['name'], np.round(point, 3).tolist()))
    write(dst, out, bones)


if __name__ == '__main__':
    main()
