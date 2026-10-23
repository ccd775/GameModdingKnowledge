"""Item template with a single CMeshComponent, derived from the WolvenKit JSON of
items/bodyparts/geralt_items/trunk/bare/t_01_mg__body.w2ent.

Usage: python make_mesh_item_template.py <in.json> <out.json> <mesh depot path> <component name> minx miny minz maxx maxy maxz
"""
import json
import sys


def patch(cr2w, mesh, comp, bbox):
    for imp in cr2w.get('_imports', []):
        if imp['_className'] == 'CMesh':
            imp['_depotPath'] = mesh
    for c in cr2w['_chunks'].values():
        v = c['_vars']
        if c['_type'] == 'CMeshComponent':
            v['name']['_value'] = comp
            v['mesh']['_vars']['_depotPath']['_value'] = mesh
            for key, vals in (('Min', bbox[:3]), ('Max', bbox[3:])):
                for ax, val in zip('XYZ', vals):
                    v['boundingBox']['_vars'][key]['_vars'][ax]['_value'] = val
        fcd = v.get('flatCompiledData')
        if fcd:
            patch(fcd, mesh, comp, bbox)


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Item template with a single CMeshComponent.')
    ap.add_argument('src')
    ap.add_argument('dst')
    ap.add_argument('mesh', help='mesh depot path')
    ap.add_argument('comp', help='component name')
    ap.add_argument('bbox', type=float, nargs=6, metavar='B', help='minx miny minz maxx maxy maxz')
    a = ap.parse_args()
    src, dst, mesh, comp = a.src, a.dst, a.mesh, a.comp
    bbox = a.bbox
    d = json.load(open(src, encoding='utf-8'))
    patch(d, mesh, comp, bbox)
    json.dump(d, open(dst, 'w', encoding='utf-8'), indent=1)
    print('wrote', dst)


if __name__ == '__main__':
    main()
