"""Write Karin's CMimicFace (.w3fac) WolvenKit JSON from the face spec of karin_build.py.

Template: Geralt's h_01_mg__geralt.w3fac JSON (WolvenKit 7). Kept: the 6 anchor bones (torso3, l/r_shoulder,
neck, head, hroll) with their rig data, the float-track skeleton (148 tracks), normalBlendAreas, neck/head
indices. Replaced: face bones (placer_kf_NN child of head with the rest offset, kf_NN child of the placer
with identity rest, like Geralt's placer/bone pairs), mapping (the kf bones) and the mimic poses
(translation-only EngineQsTransforms of the kf bones in placer space), scaled by face_pose_map.POSE_GAIN.

Every SSkeletonBone / SSkeletonTrack also gets a String 'name' (WolvenKit drops it when reading); run
fix_cr2w_skeleton_names.py on the converted file.

Usage: python make_w3fac.py <face_spec.json> <template.w3fac.json> <out.w3fac.json>
"""
import copy
import json
import sys

from face_pose_map import POSE_GAIN


def named(elem, name):
    e = copy.deepcopy(elem)
    cname = e['_vars']['nameAsCName']
    cname['_value'] = name
    e['_vars'] = {'name': {'_type': 'String', '_value': name}, 'nameAsCName': cname}
    return e


def rig(proto, pos, rot=(0.0, 0.0, 0.0, 1.0)):
    r = copy.deepcopy(proto)
    for k, v in zip('XYZW', list(pos) + [1.0]):
        r['_vars']['Position']['_vars'][k]['_value'] = float(v)
    for k, v in zip('XYZW', rot):
        r['_vars']['Rotation']['_vars'][k]['_value'] = float(v)
    for k in 'XYZW':
        r['_vars']['Scale']['_vars'][k]['_value'] = 1.0
    return r


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Karin's CMimicFace WolvenKit JSON from the karin_build face spec.")
    ap.add_argument('spec')
    ap.add_argument('template', help="Geralt's h_01_mg__geralt.w3fac JSON")
    ap.add_argument('out')
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding='utf-8'))
    d = json.load(open(a.template, encoding='utf-8'))
    out = a.out
    mf = d['_chunks']['CMimicFace #0']['_vars']
    sk = d['_chunks']['CSkeleton #1']['_vars']
    tsk = d['_chunks']['CSkeleton #2']['_vars']
    tb = sk['bones']['_elements']
    tp = sk['parentIndices']['_elements']
    tr = sk['rigdata']['_elements']
    tnames = [e['_vars']['nameAsCName']['_value'] for e in tb]
    anchors = spec['anchors']
    if tnames[:len(anchors)] != anchors:
        raise SystemExit(f'template anchor order {tnames[:6]} != {anchors}')
    bones, parents, rigdata = [], [], []
    for i, n in enumerate(anchors):
        bones.append(named(tb[i], n))
        parents.append(copy.deepcopy(tp[i]))
        rigdata.append(copy.deepcopy(tr[i]))
    head = anchors.index('head')
    pproto = tp[0]
    mapping = []
    for fb in spec['bones']:
        pi = len(bones)
        bones.append(named(tb[0], 'placer_' + fb['name']))
        p = copy.deepcopy(pproto)
        p['_value'] = head
        parents.append(p)
        rigdata.append(rig(tr[6], fb['local']))
        bi = len(bones)
        bones.append(named(tb[0], fb['name']))
        p = copy.deepcopy(pproto)
        p['_value'] = pi
        parents.append(p)
        rigdata.append(rig(tr[6], (0.0, 0.0, 0.0)))
        mapping.append(bi)
    sk['bones']['_elements'] = bones
    sk['parentIndices']['_elements'] = parents
    sk['rigdata']['_elements'] = rigdata
    tsk['bones']['_elements'] = [named(e, e['_vars']['nameAsCName']['_value']) for e in tsk['bones']['_elements']]
    tsk['tracks']['_elements'] = [named(e, e['_vars']['nameAsCName']['_value']) for e in tsk['tracks']['_elements']]
    mproto = mf['mapping']['_elements'][0]
    mf['mapping']['_elements'] = []
    for m in mapping:
        e = copy.deepcopy(mproto)
        e['_value'] = m
        mf['mapping']['_elements'].append(e)
    poses = mf['mimicPoses']['_elements']
    if len(poses) != len(spec['poses']):
        raise SystemExit(f'pose count {len(spec["poses"])} != template {len(poses)}')
    nonzero = 0
    for pose, name, tlist in zip(poses, spec['pose_names'], spec['poses']):
        gain = POSE_GAIN.get(name, 1.0)
        elems = []
        for t in tlist:
            t = [x * gain for x in t]
            if max(abs(x) for x in t) < 1e-6:
                elems.append({'_type': 'EngineQsTransform', '_vars': {}})
            else:
                nonzero += 1
                elems.append({'_type': 'EngineQsTransform',
                              '_vars': {k: {'_type': 'Float', '_value': float(v)} for k, v in zip('XYZ', t)}})
        pose['_elements'] = elems
    json.dump(d, open(out, 'w', encoding='utf-8'), indent=1)
    print(f'wrote {out}: bones={len(bones)} mapped={len(mapping)} poses={len(poses)} nonzero={nonzero}')


if __name__ == '__main__':
    main()
