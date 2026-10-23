"""Karin head item: the vanilla head item items/bodyparts/geralt_items/heads/h_01_mg__geralt.w2ent
(CItemEntity + CMimicComponent 'head' + skinned head mesh + eyes mesh + normal-blend wrinkles + wetness),
minimally patched: mimic face -> Karin's w3fac, head mesh -> Karin's face mesh, eyes mesh -> stub, the
normal-blend component/attachments/material removed (Karin's pbr_std face has no wrinkle maps).

Usage: python make_head_item_template.py <in.json> <out.json> <w3fac depot> <face mesh depot> <stub depot>
       [--bbox minx miny minz maxx maxy maxz]
"""
import argparse
import json

DROP_TYPES = ('CNormalBlendComponent', 'CNormalBlendAttachment', 'CMaterialInstance')


def ref_of(e):
    return e.get('_vars', {}).get('_reference', {}).get('_value')


def patch(cr2w, a):
    chunks = cr2w['_chunks']
    drop = {k for k, c in chunks.items() if c['_type'] in DROP_TYPES}
    # the hard attachment that parents the normal-blend component
    for k, c in chunks.items():
        if c['_type'] == 'CHardAttachment' and ref_of(c['_vars'].get('child', {})) in drop:
            drop.add(k)
    for k in drop:
        del chunks[k]
    meshes = 0
    for c in chunks.values():
        v = c['_vars']
        for arr in ('Components', 'AttachmentsChild', 'AttachmentsReference'):
            if arr in v:
                v[arr]['_elements'] = [e for e in v[arr]['_elements'] if ref_of(e) not in drop]
        if c['_type'] == 'CMimicComponent':
            v['mimicFace']['_vars']['_depotPath']['_value'] = a.fac
        elif c['_type'] == 'CMeshComponent':
            path = v['mesh']['_vars']['_depotPath']
            if path['_value'].endswith('h_01_mg__geralt.w2mesh'):
                path['_value'] = a.mesh
                for key, vals in (('Min', a.bbox[:3]), ('Max', a.bbox[3:])):
                    for ax, val in zip('XYZ', vals):
                        v['boundingBox']['_vars'][key]['_vars'][ax]['_value'] = val
                meshes += 1
            else:
                path['_value'] = a.stub
        fcd = v.get('flatCompiledData')
        if fcd:
            patch(fcd, a)
    if 'flatCompiledData' not in str(cr2w.get('_extension', '')) and meshes == 0:
        pass
    cr2w['_imports'] = [
        {'_className': 'CMimicFace', '_depotPath': a.fac, '_flags': 0},
        {'_className': 'CMesh', '_depotPath': a.mesh, '_flags': 0},
        {'_className': 'CMesh', '_depotPath': a.stub, '_flags': 0},
    ]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('fac')
    ap.add_argument('mesh')
    ap.add_argument('stub')
    ap.add_argument('--bbox', type=float, nargs=6, default=[-0.3, -0.35, 1.4, 0.3, 0.35, 2.25])
    a = ap.parse_args()
    d = json.load(open(a.src, encoding='utf-8'))
    patch(d, a)
    json.dump(d, open(a.dst, 'w', encoding='utf-8'), indent=1)
    print('wrote', a.dst, list(d['_chunks'].keys()))


if __name__ == '__main__':
    main()
