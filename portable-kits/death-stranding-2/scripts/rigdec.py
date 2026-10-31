"""Decode the DS2 RigLogic joint matrix of Sam's face (FacialRigSettingWithLODResource 34853:315).

load() -> (graph, riglogic, M, names, dna_to_skel, skeleton 67692)
  M[attr, input]: joint attribute deltas (DNA joint * 9 + tx ty tz rx ry rz sx sy sz; metres / radians, Euler 'xyz')
  per unit input (258 raw controls, then 476 PSDs). Storage: float16, 16-row blocks, column-major inside a block
  (an 8-row block at the end).
  dna_to_skel: DNA joint -> skeleton joint (67692 = the first 299 joints of 67711), from the facial rig component's
  LOD0 CorrespondingJoints (skeleton joint -> slot in PerLodJointIndexes[0], which holds the DNA joint). Matching
  joints by their neutral transform is ambiguous where joints share a pivot (eye centre, zero-offset helpers).
"""
import sys

import numpy as np

from graph import Graph, clean_root
from group import read_group

RIG = (34853, 315)          # FacialRigSettingWithLODResource (Sam)
COMPONENT = (50108, 49)     # Porter's FacialRigModelComponentResource


def load():
    g = Graph(clean_root())
    rs = read_group(g, RIG[0])[RIG[1]]
    rl = rs['RigLogic']
    st = rl['joints']['storage']
    vals = st['values'].astype(np.int16).view(np.float16).astype(np.float32)
    ii, oi = st['input_indices'], st['output_indices']
    M = np.zeros((len(rl['joints']['neutral_values']), int(ii.max()) + 1), np.float32)
    for (vo, io, oo, lo, vs, isz, a4, a8) in st['joint_groups']:
        if vs == 0:
            continue
        cols = ii[io:io + isz]
        rows = vs // isz
        outs = oi[oo:oo + rows]
        blk = np.zeros((rows, isz), np.float32)
        off, r0 = vo, 0
        while r0 < rows:
            b = min(16, rows - r0)
            blk[r0:r0 + b] = vals[off:off + b * isz].reshape(isz, b).T
            off += b * isz
            r0 += b
        for r in range(rows):
            M[outs[r], cols] += blk[r]
    sk = read_group(g, 67692)[0]
    names = [j['Name'] for j in sk['Joints']]
    cj = read_group(g, COMPONENT[0])[COMPONENT[1]]['FacialRigLODModelInfo'][0]['CorrespondingJoints']
    lod0 = rs['PerLodJointIndexes'][0]
    d2s = {int(lod0[c]): j for j, c in enumerate(cj) if c >= 0}
    return g, rl, M, names, d2s, sk


if __name__ == '__main__':
    import argparse
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    g, rl, M, names, d2s, sk = load()
    print('matrix', M.shape, 'DNA joints mapped', len(d2s), file=sys.stderr)
