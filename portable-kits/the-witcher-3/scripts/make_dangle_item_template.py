"""Karin item template with a dangle component, made by minimally patching the WolvenKit JSON of the vanilla
hair item items/bodyparts/geralt_items/coif/c_01_mg__witcher.w2ent (CItemEntity + CAnimDangleComponent
'c_02_mg__half_tail' + CMeshComponent 'c_02_mg__hair_tie' + 5 CFurComponents, all skinned to the dangle).

Only resource paths and the mesh bounding box change; component names, constraint parameters and the chunk
layout stay vanilla (a generator that dropped/renamed components produced an invisible item in-game).
--fur stub   : fur components keep existing but render the given stub mesh
--fur drop   : fur components (and their skinning attachments) are removed

Usage: python make_dangle_item_template.py <in.json> <out.json> <dyng depot> <mesh depot> <stub depot>
       [--fur stub|drop] [--bbox minx miny minz maxx maxy maxz] [--wind w] [--gravity g] [--dampening d]
"""
import argparse
import json

DYNG_PROPS = ('dyng', 'animSet', 'drawlinks', 'drawcolls', 'drawlimits', 'dampening', 'gravity', 'speed', 'planeCollision',
              'useOffsets', 'shake', 'wind', 'max_links_iterations')   # CAnimDangleConstraint_Dyng property order


def ref_of(e):
    return e.get('_vars', {}).get('_reference', {}).get('_value')


def patch(cr2w, a):
    chunks = cr2w['_chunks']
    tie_key = None
    for k, c in chunks.items():
        v = c['_vars']
        if c['_type'] == 'CAnimDangleConstraint_Dyng':
            v['dyng']['_vars']['_depotPath']['_value'] = a.dyng
            if a.wind is not None:
                v['wind']['_value'] = a.wind   # vanilla 3.0 blows long/heavy chains sideways
            # Karin's VRM spring bones have gravityPower 0: chains keep their modelled shape and only swing
            # from motion. dampening: unset in vanilla (0.95 in the Blender add-on's solver); 0.985 made the chains
            # swing more but stop in odd shapes.
            for key in ('gravity', 'dampening'):
                if getattr(a, key) is not None:
                    v[key] = {'_type': 'Float', '_value': getattr(a, key)}
            # keep the class property order
            items = sorted(v.items(), key=lambda kv: DYNG_PROPS.index(kv[0]) if kv[0] in DYNG_PROPS else len(DYNG_PROPS))
            v.clear()
            v.update(items)
        elif c['_type'] == 'CMeshComponent' and tie_key is None:
            tie_key = k
            v['mesh']['_vars']['_depotPath']['_value'] = a.mesh
            for key, vals in (('Min', a.bbox[:3]), ('Max', a.bbox[3:])):
                for ax, val in zip('XYZ', vals):
                    v['boundingBox']['_vars'][key]['_vars'][ax]['_value'] = val
        elif c['_type'] == 'CFurComponent' and 'mesh' in v:   # 'halftail_gap' has only a fur resource
            v['mesh']['_vars']['_depotPath']['_value'] = a.stub
        fcd = v.get('flatCompiledData')
        if fcd:
            patch(fcd, a)
    if a.fur == 'drop':
        fur = {k for k, c in chunks.items() if c['_type'] == 'CFurComponent'}
        atts = {k for k, c in chunks.items() if c['_type'] == 'CMeshSkinningAttachment' and ref_of(c['_vars']['child']) in fur}
        drop = fur | atts
        for k in drop:
            del chunks[k]
        for c in chunks.values():
            v = c['_vars']
            for arr in ('Components', 'AttachmentsChild', 'AttachmentsReference'):
                if arr in v:
                    v[arr]['_elements'] = [e for e in v[arr]['_elements'] if ref_of(e) not in drop]
    # imports: dyng, meshes, (fur resources kept as they are)
    imps = []
    for imp in cr2w.get('_imports', []):
        cls = imp['_className']
        if cls == 'CDyngResource':
            imp = dict(imp, _depotPath=a.dyng)
        elif cls == 'CMesh':
            continue
        elif cls == 'CFurMeshResource' and a.fur == 'drop':
            continue
        imps.append(imp)
    imps.append({'_className': 'CMesh', '_depotPath': a.mesh, '_flags': 0})
    if a.fur == 'stub':
        imps.append({'_className': 'CMesh', '_depotPath': a.stub, '_flags': 0})
    cr2w['_imports'] = imps


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('dyng')
    ap.add_argument('mesh')
    ap.add_argument('stub')
    ap.add_argument('--fur', choices=('stub', 'drop'), default='stub')
    ap.add_argument('--bbox', type=float, nargs=6, default=[-0.8, -0.8, -0.05, 0.8, 0.5, 2.2])
    ap.add_argument('--wind', type=float, default=None)
    ap.add_argument('--gravity', type=float, default=None)
    ap.add_argument('--dampening', type=float, default=None)
    a = ap.parse_args()
    d = json.load(open(a.src, encoding='utf-8'))
    patch(d, a)
    json.dump(d, open(a.dst, 'w', encoding='utf-8'), indent=1)
    print('wrote', a.dst, list(d['_chunks'].keys()))


if __name__ == '__main__':
    main()
