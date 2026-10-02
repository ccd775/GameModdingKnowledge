"""Bake body_2's kisekae shape key(s) into the base mesh of Karin_Original's FBX and VRM, then zero the key so that
switching it on later cannot apply it twice. Everything else in both files is left byte-identical
(FBX: re-serialised by fbxbin, which round-trips the source exactly; VRM: only the BIN chunk and accessor min/max).

usage: bake_knee.py <src.fbx> <src.vrm> <out.fbx> <out.vrm> [key ...]   (default key: kisekae_Knee)
"""
import sys, json, struct, argparse
import numpy as np
from fbxbin import FBX
from gltf_util import GLB

MESH = 'body_2'


def fbx_name(n):
    return n.props[1].value().split(b'\x00\x01')[0].decode('utf-8', 'replace')


def bake_fbx(src, dst, keys):
    f = FBX(src)
    objs = f.objects()
    byid = {n.props[0].value(): n for n in objs}
    up = {}
    for c in [n for n in f.top if n.name == b'Connections'][0].children:
        if c.props[0].value() == b'OO':
            up.setdefault(c.props[1].value(), []).append(c.props[2].value())
    report = {}
    for key in keys:
        shape = [n for n in objs if n.name == b'Geometry' and n.props[2].value() == b'Shape' and fbx_name(n) == key]
        assert len(shape) == 1, (key, len(shape))
        shape = shape[0]
        chan = byid[up[shape.props[0].value()][0]]           # BlendShapeChannel
        bs = byid[up[chan.props[0].value()][0]]                # BlendShape
        geo = byid[up[bs.props[0].value()][0]]                 # Mesh geometry
        model = byid[up[geo.props[0].value()][0]]
        assert fbx_name(model) == MESH and geo.props[2].value() == b'Mesh', fbx_name(model)
        sch = {c.name: c for c in shape.children}
        idx = sch[b'Indexes'].props[0].value()
        dv = sch[b'Vertices'].props[0].value().reshape(-1, 3)
        dn = sch[b'Normals'].props[0].value().reshape(-1, 3)
        gch = {c.name: c for c in geo.children}
        vp = gch[b'Vertices'].props[0]
        V = vp.value().reshape(-1, 3).copy()
        V[idx] += dv
        vp.set_array(V.reshape(-1))
        # per-corner normals: add the key's per-vertex normal delta, then re-orthonormalise tangent/binormal
        pvi = gch[b'PolygonVertexIndex'].props[0].value()
        cp = np.where(pvi < 0, ~pvi, pvi)
        dn_full = np.zeros_like(V); dn_full[idx] = dn
        hit = np.isin(cp, idx)
        layers = {}
        for lname, aname in ((b'LayerElementNormal', b'Normals'), (b'LayerElementTangent', b'Tangents'),
                             (b'LayerElementBinormal', b'Binormals')):
            le = [c for c in geo.children if c.name == lname][0]
            lch = {c.name: c for c in le.children}
            assert lch[b'MappingInformationType'].props[0].value() == b'ByPolygonVertex'
            assert lch[b'ReferenceInformationType'].props[0].value() == b'Direct'
            layers[aname] = lch[aname].props[0]
        N = layers[b'Normals'].value().reshape(-1, 3).copy()
        Tn = layers[b'Tangents'].value().reshape(-1, 3).copy()
        B = layers[b'Binormals'].value().reshape(-1, 3).copy()
        hand = np.sign(np.sum(np.cross(N, Tn) * B, axis=1)); hand[hand == 0] = 1
        n2 = N[hit] + dn_full[cp[hit]]
        n2 /= np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
        t2 = Tn[hit] - n2 * np.sum(Tn[hit] * n2, axis=1, keepdims=True)
        t2 /= np.maximum(np.linalg.norm(t2, axis=1, keepdims=True), 1e-12)
        b2 = np.cross(n2, t2) * hand[hit, None]
        N[hit], Tn[hit], B[hit] = n2, t2, b2
        layers[b'Normals'].set_array(N.reshape(-1)); layers[b'Tangents'].set_array(Tn.reshape(-1))
        layers[b'Binormals'].set_array(B.reshape(-1))
        sch[b'Vertices'].props[0].set_array(np.zeros(dv.size))
        sch[b'Normals'].props[0].set_array(np.zeros(dn.size))
        report[key] = dict(verts=int(len(idx)), corners=int(hit.sum()), max_move_cm=float(np.linalg.norm(dv, axis=1).max()))
    f.save(dst)
    return report


def bake_vrm(src, dst, keys):
    g = GLB(src)
    J = g.json
    mesh = [m for m in J['meshes'] if m['name'] == MESH][0]
    names = (mesh.get('extras') or {}).get('targetNames') or mesh['primitives'][0]['extras']['targetNames']
    report = {}
    json_changed = False
    for prim in mesh['primitives']:
        pos_ai = prim['attributes']['POSITION']
        P = g.read(pos_ai)
        for key in keys:
            ti = names.index(key)
            tgt = prim['targets'][ti]
            assert set(tgt) == {'POSITION'}, f'unexpected target attributes {set(tgt)}'
            ai = tgt['POSITION']
            idx, val = g.read_sparse(ai)
            P[idx] += val
            # zero the sparse values in place (indices kept, so morph target count/order is unchanged)
            a = J['accessors'][ai]; sp = a['sparse']; vv = J['bufferViews'][sp['values']['bufferView']]
            o = vv.get('byteOffset', 0) + sp['values'].get('byteOffset', 0)
            g.bin[o:o + val.nbytes] = bytes(val.nbytes)
            a['min'], a['max'] = [0.0, 0.0, 0.0], [0.0, 0.0, 0.0]
            json_changed = True
            report[key] = dict(verts=int(len(idx)), max_move_m=float(np.linalg.norm(val, axis=1).max()))
        g.write(pos_ai, P)
        a = J['accessors'][pos_ai]
        lo, hi = P.min(0).astype(np.float32).tolist(), P.max(0).astype(np.float32).tolist()
        if np.any(np.abs(np.array(lo) - a['min']) > 1e-7) or np.any(np.abs(np.array(hi) - a['max']) > 1e-7):
            a['min'], a['max'] = lo, hi
            report['position_bounds_updated'] = True
    raw = bytearray(g.raw)
    if json_changed:
        js = json.dumps(J, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
        js += b' ' * (-len(js) % 4)
        binc = bytes(g.bin) + bytes(-len(g.bin) % 4)
        out = struct.pack('<4sII', b'glTF', 2, 12 + 8 + len(js) + 8 + len(binc))
        out += struct.pack('<I4s', len(js), b'JSON') + js + struct.pack('<I4s', len(binc), b'BIN\0') + binc
        open(dst, 'wb').write(out)
    else:
        g.save(dst)
    return report


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src_fbx'); ap.add_argument('src_vrm'); ap.add_argument('out_fbx'); ap.add_argument('out_vrm')
    ap.add_argument('keys', nargs='*', metavar='KEY', help='shape keys of body_2 to bake (default: kisekae_Knee)')
    a = ap.parse_args()
    sfbx, svrm, dfbx, dvrm = a.src_fbx, a.src_vrm, a.out_fbx, a.out_vrm
    keys = a.keys or ['kisekae_Knee']
    print('fbx', bake_fbx(sfbx, dfbx, keys))
    print('vrm', bake_vrm(svrm, dvrm, keys))
