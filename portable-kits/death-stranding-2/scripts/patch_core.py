"""Patch a ds2_pc_mi-produced group core so that replaced meshes stay consistent.

ds2_pc_mi_022 updates vertex/index counts and Primitive.EndIndex only. This fixes, in place (fixed-size fields):
  * RegularSkinnedMeshResource.StreamingDataSource.Length  -> size of the NN_OFFSET_mesh.stream it imported
  * PrimitiveSkinInfo.VertexCount (+ CsNbt*/CsNrm* -> VsNbt, VertexComputeNbtCount = -1 when the count changed)
  * PrimitiveResource.BoundingBox and MeshHierarchyInfo.LocalBounds of replaced meshes
  * SkinnedMeshBoneBoundingBoxes of the mesh and its ModelParts (per-joint union, joint-local space)

python patch_core.py <jobs.json>
jobs.json: {"gid": 50108, "core": "<tool output core>", "pristine": "<original core>", "streams": "<dir>",
            "out": "<patched core, default: in place>",
            "meshes": [{"index": 144, "prims": {"0": "a.ascii#0", ...}, "ibm": {"<joint>": 4x4, ...}}, ...]}
  prim values are "<ascii path>#<submesh index>"; the ascii starts with the full-skeleton header used for import,
  so bone indices are skeleton joint indices. "ibm" (optional) overwrites those joints' inverse bind matrices in the
  mesh's joint bindings (face levers, build_ds2.py FACE_LEVER); "ibm_post" right-multiplies them (ear particles,
  build_ds2.py HAIR_EAR_SCALE).
  "no_cast_shadow" (optional, per mesh): clear DrawFlags bits 0-1 (EShadowCastMode 3 -> 0; Sam's eye-area meshes
  carry 0x...48 against 0x...4B).
  "fields" (optional): [{"index": obj, "path": [field, element, ...], "fmt": "<B", "value": v | "scale": f}] for plain
  values in groups without meshes ("meshes": [], "core" a copy of the pristine core).
  "rename_vars" (optional): {"<VariableIDHash>": new id} in every render effect's variable bindings: the game drives
  some shader variables by that id on all of a wearer's meshes (timefall CorrosionRate); renamed, it finds nothing to
  drive and the material keeps its own value. The shader-side BindingNameHash stays.
"""
import argparse
import json
import os
import struct
import sys

import numpy as np

from ds2ascii import read_meshes
from graph import Graph, game_root
from group import read_group
from roundtrip import read_span

VS_NBT = 3
CS_TYPES = (4, 5, 6, 7)  # CsNrm, CsNbt, CsNrmGen, CsNbtGen


def mat44(m):
    return np.array([[m['Col%d' % c][k] for c in range(4)] for k in 'XYZW'])


def box_of(b):
    return np.array([b['Min'][c] for c in 'XYZ']), np.array([b['Max'][c] for c in 'XYZ'])


class Patcher:
    def __init__(self, data):
        self.data = data

    def i32(self, pos, v):
        struct.pack_into('<i', self.data, pos, int(v))

    def mat(self, m, a):
        """Mat44 m (Col0..Col3 of Vec4) <- 4x4 array a (inverse of mat44())."""
        for c in range(4):
            for k, comp in enumerate('XYZW'):
                struct.pack_into('<f', self.data, m['Col%d' % c]['__pos__'][comp], float(a[k][c]))

    def box(self, b, lo, hi):
        for corner, val in (('Min', lo), ('Max', hi)):
            p = b[corner]['__pos__']
            for k, c in enumerate('XYZ'):
                struct.pack_into('<f', self.data, p[c], float(val[k]))
            # Vec3 also stores W: primitive boxes keep W == Z, bone boxes keep W == 1; preserve whichever applies
            if 'W' in p and b[corner].get('W') == b[corner].get('Z'):
                struct.pack_into('<f', self.data, p['W'], float(val[2]))


def joint_boxes(pos, bi, bw, ibm):
    """Game convention (verified on 50108:514, zero error): box of the vertices whose max-weight joint is j,
    in that joint's local space (inverse bind matrix applied)."""
    boxes = {}
    bi = np.asarray(bi)
    bw = np.asarray(bw)
    dom = bi[np.arange(len(bi)), bw.argmax(1)]
    for j, inv in ibm.items():
        sel = dom == j
        if not sel.any():
            continue
        p = np.c_[pos[sel], np.ones(sel.sum())] @ inv.T
        boxes[j] = (p[:, :3].min(0), p[:, :3].max(0))
    return boxes


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('jobs', help='patch_<gid>.json')
    jobs = json.load(open(ap.parse_args().jobs))
    gid = jobs['gid']
    g = Graph(game_root())
    data = bytearray(open(jobs['core'], 'rb').read())
    objs = read_span(g, gid, bytes(data))
    pristine = read_span(g, gid, open(jobs['pristine'], 'rb').read())
    P = Patcher(data)
    ext = {}

    def other(ref):
        if ref[1] == gid:
            return objs[ref[2]]
        if ref[1] not in ext:
            ext[ref[1]] = read_group(g, ref[1])
        return ext[ref[1]][ref[2]]

    part_boxes = {}
    for o in objs:
        if o['__type__'] == 'ModelPartResource' and o['MeshResource'] and o['BoneBoundingBoxes']:
            part_boxes.setdefault(tuple(o['MeshResource'][1:]), []).append(o['BoneBoundingBoxes'])

    report = []
    for job in jobs['meshes']:
        mi = job['index']
        m = objs[mi]
        assert m['__type__'] == 'RegularSkinnedMeshResource', m['__type__']
        sds = m['StreamingDataSource']
        fi, foff = sds['Locator']
        sname = os.path.join(jobs['streams'], '%02X_%08X_mesh.stream' % (fi, foff))
        if not os.path.exists(sname):
            raise SystemExit('mesh %d: missing stream %s' % (mi, sname))
        size = os.path.getsize(sname)
        P.i32(sds['__pos__']['Length'], size)
        report.append('mesh %d: SDS.Length %d -> %d' % (mi, sds['Length'], size))

        if job.get('no_cast_shadow'):
            df = m['DrawFlags']['Data']
            struct.pack_into('<I', data, m['DrawFlags']['__pos__']['Data'], df & ~3)
            report.append('mesh %d: DrawFlags %08X -> %08X (no cast shadow)' % (mi, df, df & ~3))
        jb = other(m['SkinnedMeshJointBindings'])
        for kind in ('ibm', 'ibm_post'):
            for j, a in job.get(kind, {}).items():
                if m['SkinnedMeshJointBindings'][1] != gid:
                    raise SystemExit('mesh %d: joint bindings in another group, cannot set IBMs' % mi)
                k = list(jb['JointIndexList']).index(int(j))
                if kind == 'ibm_post':
                    a = mat44(jb['InverseBindMatrices'][k]) @ np.asarray(a)
                pos = jb['InverseBindMatrices'][k]
                P.mat(pos, a)
                jb['InverseBindMatrices'][k] = {'Col%d' % c: dict(zip('XYZW', np.asarray(a)[:, c]),
                                                                  __pos__=pos['Col%d' % c]['__pos__']) for c in range(4)}
                report.append('mesh %d: joint %s inverse bind matrix %s' % (
                    mi, j, 'set (lever)' if kind == 'ibm' else 'scaled (position-only particle)'))
        ibm = {j: mat44(x) for j, x in zip(jb['JointIndexList'], jb['InverseBindMatrices'])}
        si = objs[m['SkinInfo'][2]]
        psi = pristine[m['SkinInfo'][2]]
        lo_all, hi_all = box_of(m['MeshHierarchyInfo']['LocalBounds'])
        jboxes = {}
        for pk, src in job['prims'].items():
            pi = int(pk)
            path, sub = src.rsplit('#', 1)
            _, meshes = read_meshes(path, has_skeleton=True)
            sm = meshes[int(sub)]
            pos = sm['pos']
            lo, hi = pos.min(0), pos.max(0)
            lo_all, hi_all = np.minimum(lo_all, lo), np.maximum(hi_all, hi)
            prim = objs[m['Primitives'][pi][2]]
            P.box(prim['BoundingBox'], lo, hi)
            part = si['Parts'][pi]
            nv = len(pos)
            P.i32(part['__pos__']['VertexCount'], nv)
            if nv != psi['Parts'][pi]['VertexCount'] and part['Type'] in CS_TYPES:
                P.i32(part['__pos__']['Type'], VS_NBT)
                P.i32(part['__pos__']['VertexComputeNbtCount'], -1)
                report.append('mesh %d prim %d: SkinInfo type %d -> VsNbt' % (mi, pi, part['Type']))
            report.append('mesh %d prim %d: %d verts, bbox %s %s' % (
                mi, pi, nv, np.round(lo, 3).tolist(), np.round(hi, 3).tolist()))
            for j, (a, b) in joint_boxes(pos, sm['bi'], sm['bw'], ibm).items():
                if j in jboxes:
                    a, b = np.minimum(a, jboxes[j][0]), np.maximum(b, jboxes[j][1])
                jboxes[j] = (a, b)
            unknown = set(np.asarray(sm['bi'])[np.asarray(sm['bw']) > 0.004].tolist()) - set(ibm)
            if unknown:
                raise SystemExit('mesh %d prim %d: weights on joints outside JointIndexList: %s' % (mi, pi, sorted(unknown)))
        P.box(m['MeshHierarchyInfo']['LocalBounds'], lo_all, hi_all)

        parents = [jt['ParentIndex'] for jt in other(m['Skeleton'])['Joints']]
        refs = [m['SkinnedMeshBoneBoundingBoxes']] + part_boxes.get((gid, mi), [])
        for ref in refs:
            if ref is None or ref[1] != gid:
                continue
            bb = objs[ref[2]]
            indices = list(bb['Indices'])
            shared = []
            for j in sorted(jboxes, key=lambda x: bb['UsesIndices'] and indices[x] == 0):
                a, b = jboxes[j]
                k = indices[j] if bb['UsesIndices'] else j
                if bb['UsesIndices'] and k == 0:
                    # joint without a box (Sam had no vertex dominated by it): share the box of its nearest boxed
                    # ancestor; the box is read in each joint's own space, so the union only makes both conservative
                    anc = parents[j]
                    while anc >= 0 and indices[anc] == 0:
                        anc = parents[anc]
                    if anc < 0:   # root joint (PBD particle): any boxed joint, the union keeps both conservative
                        anc = next((x for x in range(len(indices)) if indices[x] != 0), -1)
                    if anc < 0:
                        raise SystemExit('mesh %d: joint %d has no boxed joint to share' % (mi, j))
                    k = indices[anc]
                    indices[j] = k
                    struct.pack_into('<H', data, bb['__pos__']['Indices'] + 4 + 2 * j, k)
                    shared.append((j, anc))
                box = bb['BoneBoundingBoxes'][k]
                olo, ohi = box_of(box)
                lo_n, hi_n = np.minimum(olo, a), np.maximum(ohi, b)
                P.box(box, lo_n, hi_n)
                box['Min'].update(X=lo_n[0], Y=lo_n[1], Z=lo_n[2])   # later joints sharing k union with this
                box['Max'].update(X=hi_n[0], Y=hi_n[1], Z=hi_n[2])
            report.append('mesh %d: bone boxes %d:%d updated %d joints%s' % (
                mi, ref[1], ref[2], len(jboxes), (', joints sharing an ancestor box %s' % shared) if shared else ''))
    for f in jobs.get('fields', []):
        o = objs[f['index']]
        node = o
        for key in f['path'][:-1]:
            node = node[key]
        old = node[f['path'][-1]]
        new = f['value'] if 'value' in f else old * f['scale']
        struct.pack_into(f['fmt'], data, node['__pos__'][f['path'][-1]], new)
        report.append('object %d %s: %s -> %s' % (f['index'], '.'.join(map(str, f['path'])), old, new))
    rename = {int(k): v for k, v in jobs.get('rename_vars', {}).items()}
    for i, o in enumerate(objs if rename else []):
        n = 0
        for ts in o.get('TechniqueSets') or []:
            for t in ts['RenderTechniques']:
                for vb in t.get('VariableBindings') or []:
                    if vb['VariableIDHash'] in rename:
                        struct.pack_into('<I', data, vb['__pos__']['VariableIDHash'], rename[vb['VariableIDHash']])
                        n += 1
        if n:
            report.append('effect %d: %d variable bindings renamed' % (i, n))
    # model parts to hide by default (Porter-only facial parts: Karin's head lives in the body mesh)
    for pi in jobs.get('hide_parts', []):
        o = objs[pi]
        assert o['__type__'] == 'ModelPartResource', (pi, o['__type__'])
        data[o['__pos__']['IsHideAndDisableDefault']] = 1
        report.append('part %d: IsHideAndDisableDefault %d -> 1' % (pi, o['IsHideAndDisableDefault']))
    out = jobs.get('out') or jobs['core']
    open(out, 'wb').write(data)
    # verify the patched span still parses identically in structure
    check = read_span(g, gid, bytes(data))
    assert len(check) == len(objs)
    print('\n'.join(report))


if __name__ == '__main__':
    main()
