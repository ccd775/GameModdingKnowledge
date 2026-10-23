"""Write a CDyngResource (.w3dyng) WolvenKit JSON from a karin_build dyng spec.

Usage: python make_dyng.py <spec.json> <template.w3dyng.json> <out.w3dyng.json>

The template is the vanilla c_02_mg__half_tail.w3dyng JSON; every array is replaced. Like the vanilla
hair, every node gets a collision entry (radius 0, height 0.006, identity offset) - the height doubles as
the orientation radius that lets a node aim its X axis at its child (triangles a->b).
"""
import copy
import json
import sys


def scalar(proto, value):
    e = copy.deepcopy(proto)
    e['_value'] = value
    return e


def vec4(proto, vals):
    e = copy.deepcopy(proto)
    for k, v in zip('XYZW', vals):
        e['_vars'][k]['_value'] = float(v)
    return e


def matrix(proto, rows):
    e = copy.deepcopy(proto)
    for ax, row in zip('XYZW', rows):
        for k, v in zip('XYZW', row):
            e['_vars'][ax]['_vars'][k]['_value'] = float(v)
    return e


def main():
    import argparse
    ap = argparse.ArgumentParser(description='CDyngResource WolvenKit JSON from a karin_build dyng spec.')
    ap.add_argument('spec')
    ap.add_argument('template', help='vanilla c_02_mg__half_tail.w3dyng JSON')
    ap.add_argument('out')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    d = json.load(open(a.template, encoding='utf-8'))
    out = a.out
    res = d['_chunks']['CDyngResource #0']['_vars']
    sk = d['_chunks']['CSkeleton #1']['_vars']
    nodes = spec['nodes']

    def fill(var, values, maker):
        proto = res[var]['_elements'][0]
        res[var]['_elements'] = [maker(proto, v) for v in values]

    fill('nodeNames', [n['name'] for n in nodes], scalar)
    fill('nodeParents', [n['parent'] for n in nodes], scalar)
    fill('nodeMasses', [n['mass'] for n in nodes], scalar)
    fill('nodeStifnesses', [n['stiffness'] for n in nodes], scalar)
    fill('nodeDistances', [n['distance'] for n in nodes], scalar)
    fill('nodeTransforms', [[r + [0.0] for r in n['local'][:3]] + [n['local'][3] + [1.0]] for n in nodes], matrix)
    links = spec['links']
    fill('linkTypes', [l['type'] for l in links], scalar)
    fill('linkLengths', [l['length'] for l in links], scalar)
    fill('linkAs', [l['a'] for l in links], scalar)
    fill('linkBs', [l['b'] for l in links], scalar)
    tris = spec['triangles']
    fill('triangleAs', [t[0] for t in tris], scalar)
    fill('triangleBs', [t[1] for t in tris], scalar)
    fill('triangleCs', [t[2] for t in tris], scalar)
    fill('collisionParents', [n['name'] for n in nodes], scalar)
    fill('collisionRadiuses', [0.0 for _ in nodes], scalar)
    fill('collisionHeights', [0.006 for _ in nodes], scalar)
    ident = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    fill('collisionTransforms', [ident for _ in nodes], matrix)

    # embedded skeleton
    bproto = sk['bones']['_elements'][0]
    pproto = sk['parentIndices']['_elements'][0]
    rproto = sk['rigdata']['_elements'][0]
    bones, parents, rig = [], [], []
    for n in nodes:
        b = copy.deepcopy(bproto)
        cname = b['_vars']['nameAsCName']
        cname['_value'] = n['name']
        # vanilla SSkeletonBone carries a String 'name' before 'nameAsCName'; WolvenKit 7's reader drops it,
        # and a skeleton written without it makes the dangle component (and every mesh skinned to it) vanish
        b['_vars'] = {'name': {'_type': 'String', '_value': n['name']}, 'nameAsCName': cname}
        bones.append(b)
        parents.append(scalar(pproto, n['parent_index']))
        r = copy.deepcopy(rproto)
        r['_vars']['Position'] = vec4(rproto['_vars']['Position'], n['pos'] + [1.0])
        r['_vars']['Rotation'] = vec4(rproto['_vars']['Rotation'], n['rot'])
        r['_vars']['Scale'] = vec4(rproto['_vars']['Scale'], [1.0, 1.0, 1.0, 1.0])
        rig.append(r)
    sk['bones']['_elements'] = bones
    sk['parentIndices']['_elements'] = parents
    sk['rigdata']['_elements'] = rig
    json.dump(d, open(out, 'w', encoding='utf-8'), indent=1)
    print(f'wrote {out}: nodes={len(nodes)} links={len(links)} triangles={len(tris)}')


if __name__ == '__main__':
    main()
