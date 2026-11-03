"""Ichel (Snowbreak, MMD conversion 尘白.fbx) -> the source format the Nioh 3 build reads (source.json / .npz /
shapekeys.json / .npz in $N3_BUILD/source), from the raw Blender exports of the FBX.

usage: ichel_source.py <raw dir> <model dir>
  raw dir:   ko_extract_source.py + blender_shapekeys.py output for 尘白.fbx (one mesh 'Body' + a 'Cylinder' proxy)
  model dir: the folder with the original PMX and the PNG textures

What it does
- The FBX merged the PMX's 24 materials into 7 by texture. Every FBX triangle is matched to its PMX triangle (same
  texture, UV centroid, position as a weak tie-break: the FBX was re-posed to a T pose, so positions only agree on the
  trunk) and the mesh is split by PMX material into the parts the conform treats differently (MESHES).
- 眼睛1 (eye shadow) and 表情 (blush / expression overlay) are alpha-blended overlays and are left out; the chest
  shader only alpha-tests. The 'Cylinder' (a hair-collision proxy, material phy_hair) is left out. The tail (尾巴) is
  not in the FBX (only its bones are), so there is no tail.
- Humanoid bones are renamed to the names n3_conform-style code expects (HUMANOID) and finger tips are added
  (`<finger>Distal_end`, extrapolated, no weights). Physics bones keep their FBX names.
- UVs: the chest piece (胸口) has whole triangles at u in (1, 1.23] (texture wrap); they are shifted by -1, any
  other corner is clamped to [0, 1] (an atlas cannot wrap).
- Face shape keys: the MMD morphs of the face mesh, plus side-split keys under the names n3_face.py maps
  (blink_L/R, mayu_up_L/R, mayu_down_L/R, kuchi_A, kuchi_smile_1_L/R). +X is the character's left.
"""
import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / 'n3build'))
import pmx_read  # noqa: E402
from n3_common import BUILD  # noqa: E402

PMX = '伊切尔 捕猎演习a1.0.pmx'
MESHES = {   # mesh -> PMX materials
    'Body': ['脸', '眉毛', '牙齿', '舌头', '口腔', '眼白', '眼睛'],      # face: n3_face.py rigs it (name kept)
    'hair': ['头发', '头发1'],
    'skin': ['皮肤'],
    'clothes': ['衣服', '胸口'],
    'collar': ['脖饰'],
    'sleeves': ['袖子'],        # upper-arm puff sleeves (sleeve physics rings Yxz / Zxz)
    'sleeves1': ['袖子1'],      # forearm sleeves down over the wrist
    'skirt': ['裙子'],
    'panties': ['胖次'],
    'legwear': ['腿饰'],        # left thigh band
    'shoes': ['鞋子'],
    'ears': ['耳朵'],
    'headwear': ['头饰'],
}
LEFT_OUT = ('眼睛1', '表情', '尾巴')
FBX_TEXTURE = {'口腔': '脸.png', '眼睛': '眼睛.png', '眼睛1': '眼睛1.png', '表情': '表情.png', '皮肤': '皮肤.png',
               '头发1': '头发.png', '胸口': '衣服a.png'}
PMX_TEX_INDEX = {'口腔': 3, '眼睛': 5, '眼睛1': 6, '表情': 7, '皮肤': 8, '头发1': 0, '胸口': 9}
FINGERS = {'Thumb': ('1Thumb0', '1Thumb1', '1Thumb2'), 'Index': ('1IndexFinger1', '1IndexFinger2', '1IndexFinger3'),
           'Middle': ('1MiddleFinger1', '1MiddleFinger2', '1MiddleFinger3'),
           'Ring': ('1RingFinger1', '1RingFinger2', '1RingFinger3'),
           'Little': ('1LittleFinger1', '1LittleFinger2', '1LittleFinger3')}
SEGS = ('Proximal', 'Intermediate', 'Distal')


def humanoid():
    m = {'Hips': 'Hips', 'Spine': 'Spine', 'Chest': 'Chest', 'Neck': 'Neck', 'Head': 'Head',
         'Eye_L.001': 'LeftEye', 'Eye_R.001': 'RightEye'}
    for side, s in (('Left', 'L'), ('Right', 'R')):
        m.update({f'{side} shoulder': f'{side}Shoulder', f'{side} arm': f'{side}UpperArm',
                  f'{side} elbow': f'{side}LowerArm', f'{side} wrist': f'{side}Hand',
                  f'{side} leg': f'{side}UpperLeg', f'{side} knee': f'{side}LowerLeg',
                  f'{side} ankle': f'{side}Foot', f'{side} toe': f'{side}ToeBase'})
        for f, names in FINGERS.items():
            for n, seg in zip(names, SEGS):
                m[f'{n}_{s}1'] = f'{side}{f}{seg}'
    return m


SIDE_RAMP = 0.005     # m: side-split keys blend over |x| < this


def match_pmx(meta, arr, model_dir):
    """PMX material index per FBX Body triangle."""
    pj = pmx_read.parse(str(model_dir / PMX))
    P, UV, F, FM = pmx_read.geometry(str(model_dir / PMX))
    pairs = [('首', 'Neck'), ('頭', 'Head'), ('左足', 'Left leg'), ('右足', 'Right leg'), ('上半身', 'Spine'),
             ('上半身2', 'Chest'), ('左ひざ', 'Left knee'), ('右ひざ', 'Right knee')]
    pb = {b['name']: np.array(b['pos']) for b in pj['bones']}
    fb = {b['name']: np.array(b['head']) for b in meta['bones']}
    X = np.array([pb[a][[0, 2, 1]] for a, _ in pairs]); Y = np.array([fb[b] for _, b in pairs])
    mx, my = X.mean(0), Y.mean(0)
    s = np.sqrt(((Y - my) ** 2).sum() / ((X - mx) ** 2).sum())
    pc = (s * P[:, [0, 2, 1]] + (my - s * mx))[F].mean(1)
    puv = UV[F].mean(1); puv[:, 1] = 1 - puv[:, 1]
    ptex = np.array([pj['materials'][i]['tex'] for i in FM])
    k = 'Body'
    m = next(x for x in meta['meshes'] if x['name'] == k)
    lv, luv, tris, tm = arr[k + '__loop_vertex'], arr[k + '__loop_uv'], arr[k + '__tris'], arr[k + '__tri_material']
    fc = arr[k + '__co'][lv[tris]].mean(1); fuv = luv[tris].mean(1)
    out = np.zeros(len(tris), int); worst = 0.0
    for fi, x in enumerate(m['materials']):
        sel = tm == fi
        cand = np.nonzero(ptex == PMX_TEX_INDEX[x['name'].split('.')[0]])[0]
        d, i = cKDTree(np.c_[puv[cand], 0.02 * pc[cand]]).query(np.c_[fuv[sel], 0.02 * fc[sel]])
        out[sel] = FM[cand[i]]; worst = max(worst, float(d.max()))
    names = [x['name'] for x in pj['materials']]
    counts = {n: int((out == i).sum()) for i, n in enumerate(names)}
    for i, x in enumerate(pj['materials']):          # every PMX material accounted for exactly
        assert counts[x['name']] in (0, x['faces']), (x['name'], counts[x['name']], x['faces'])
    return out, names, counts, worst


def split(meta, arr, keys_info, keys, pmx_mat, names, rename):
    src = next(x for x in meta['meshes'] if x['name'] == 'Body')
    k = 'Body'
    co, lv, ln, luv = arr[k + '__co'], arr[k + '__loop_vertex'], arr[k + '__loop_normal'], arr[k + '__loop_uv'].copy()
    tris, tm = arr[k + '__tris'], arr[k + '__tri_material']
    wv, wg, ww = arr[k + '__w_vertex'], arr[k + '__w_group'], arr[k + '__w_weight']
    # UV wrap of the chest piece
    tu = luv[tris][..., 0]
    shift = tu.min(1) >= 0.999
    luv[np.unique(tris[shift]), 0] -= 1.0
    clamped = int(((luv < 0) | (luv > 1)).any(1).sum())
    luv = np.clip(luv, 0, 1)
    groups = [rename.get(g, g) for g in src['groups']]
    out_meta, out_arr, report = [], {}, {'uv_shifted_triangles': int(shift.sum()), 'uv_clamped_loops': clamped}
    mat_index = {n: i for i, n in enumerate(names)}
    vert_maps = {}
    for mesh, mats in MESHES.items():
        sel = np.isin(pmx_mat, [mat_index[x] for x in mats])
        t = tris[sel]
        loops = np.unique(t)
        lmap = np.full(len(lv), -1); lmap[loops] = np.arange(len(loops))
        verts = np.unique(lv[loops])
        vmap = np.full(len(co), -1); vmap[verts] = np.arange(len(verts))
        wsel = vmap[wv] >= 0
        mv, mg, mw = vmap[wv[wsel]], wg[wsel], ww[wsel]
        # vertices the FBX left without weights (some eye vertices) copy the nearest weighted vertex of the mesh
        has = np.zeros(len(verts), bool); has[mv] = True
        if not has.all():
            near = np.nonzero(has)[0][cKDTree(co[verts][has]).query(co[verts][~has])[1]]
            src_of = dict(zip(np.nonzero(~has)[0], near))
            add = [(v, g, w) for v, s in src_of.items() for g, w in zip(mg[mv == s], mw[mv == s])]
            mv = np.r_[mv, [a for a, _, _ in add]]; mg = np.r_[mg, [b for _, b, _ in add]]
            mw = np.r_[mw, [c for _, _, c in add]]
            report.setdefault('unweighted_vertices_filled', {})[mesh] = int((~has).sum())
        out_arr.update({f'{mesh}__co': co[verts], f'{mesh}__loop_vertex': vmap[lv[loops]].astype(np.int32),
                        f'{mesh}__loop_normal': ln[loops], f'{mesh}__loop_uv': luv[loops].astype(np.float32),
                        f'{mesh}__tris': lmap[t].astype(np.int32), f'{mesh}__tri_material': tm[sel],
                        f'{mesh}__w_vertex': mv.astype(np.int32), f'{mesh}__w_group': mg.astype(np.int32),
                        f'{mesh}__w_weight': mw.astype(np.float32)})
        mats_meta = [dict(x, texture_file=FBX_TEXTURE[x['name'].split('.')[0]]) for x in src['materials']]
        out_meta.append({'name': mesh, 'key': mesh, 'groups': groups, 'materials': mats_meta,
                         'shape_keys_applied': [], 'vertices': len(verts), 'loops': len(loops), 'triangles': len(t),
                         'hidden': False, 'pmx_materials': mats})
        vert_maps[mesh] = verts
        report[mesh] = {'vertices': len(verts), 'triangles': int(len(t))}
    # face shape keys: MMD morphs on the face vertices + side-split keys
    fv = vert_maps['Body']
    x = co[fv][:, 0]
    sl = np.clip(0.5 + x / (2 * SIDE_RAMP), 0, 1)[:, None]
    rows, kz = [], {}
    by_name = {}
    for r in keys_info['Body']:
        name = f'Body__{r["index"]}'
        d = keys[name][fv] if name in keys.files else np.zeros((len(fv), 3), np.float32)
        mag = np.linalg.norm(d, axis=1)
        rows.append({'index': r['index'], 'name': r['name'], 'moved': int((mag > 1e-5).sum()), 'max': float(mag.max())})
        if rows[-1]['moved']:
            kz[name] = d.astype(np.float32)
        by_name[r['name']] = d
    nxt = max(r['index'] for r in rows) + 1
    synth = {'blink': 'まばたき', 'mayu_up': '上', 'mayu_down': '下', 'kuchi_smile_1': '口角上げ'}
    made = []
    for base, mmd in synth.items():
        for side, f in (('L', sl), ('R', 1 - sl)):
            made.append((f'{base}_{side}', by_name[mmd] * f, mmd))
    made.append(('kuchi_A', by_name['あ'], 'あ'))
    for name, d, mmd in made:
        mag = np.linalg.norm(d, axis=1)
        rows.append({'index': nxt, 'name': name, 'moved': int((mag > 1e-5).sum()), 'max': float(mag.max()), 'from': mmd})
        kz[f'Body__{nxt}'] = d.astype(np.float32)
        nxt += 1
    report['face_keys'] = {r['name']: [r['moved'], round(r['max'] * 100, 3)] for r in rows[-len(made):]}
    return out_meta, out_arr, {'Body': rows}, kz, report


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('raw_dir', help='ko_extract_source.py + blender_shapekeys.py output for the FBX')
    ap.add_argument('model_dir', help='the folder with the original PMX and the PNG textures')
    args = ap.parse_args()
    raw, model_dir = Path(args.raw_dir), Path(args.model_dir)
    meta = json.loads((raw / 'source.json').read_text(encoding='utf-8'))
    arr = dict(np.load(raw / 'source.npz'))
    keys_info = json.loads((raw / 'shapekeys.json').read_text(encoding='utf-8'))
    keys = np.load(raw / 'shapekeys.npz')
    pmx_mat, names, counts, worst = match_pmx(meta, arr, model_dir)
    rename = humanoid()
    assert all(b in {x['name'] for x in meta['bones']} for b in rename), 'humanoid bone missing'
    bones = []
    for b in meta['bones']:
        bones.append(dict(b, name=rename.get(b['name'], b['name']),
                          parent=rename.get(b['parent'], b['parent']) if b['parent'] else None, fbx_name=b['name']))
    by = {b['name']: b for b in bones}
    for side in ('Left', 'Right'):            # finger tips: the distal bone continued by 0.75 of the previous segment
        for f in FINGERS:
            d, i = by[f'{side}{f}Distal'], by[f'{side}{f}Intermediate']
            tip = np.array(d['head']) + 0.75 * (np.array(d['head']) - np.array(i['head']))
            bones.append({'name': f'{side}{f}Distal_end', 'parent': d['name'], 'head': tip.tolist(), 'tail': tip.tolist(),
                          'matrix': d['matrix'], 'fbx_name': None})
    out_meta, out_arr, kinfo, kz, report = split(meta, arr, keys_info, keys, pmx_mat, names, rename)
    textures = {}
    for f in sorted(set(FBX_TEXTURE.values())):
        p = model_dir / f
        textures[f] = {'file': str(p), 'bytes': p.stat().st_size}
    dst = BUILD / 'source'
    dst.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(dst / 'source.npz', **out_arr)
    (dst / 'source.json').write_text(json.dumps({'fbx': meta['fbx'], 'armature': meta['armature'], 'bones': bones,
                                                 'meshes': out_meta, 'textures': textures,
                                                 'pmx_material_triangles': counts, 'left_out': LEFT_OUT},
                                                ensure_ascii=False, indent=1), encoding='utf-8')
    np.savez_compressed(dst / 'shapekeys.npz', **kz)
    (dst / 'shapekeys.json').write_text(json.dumps(kinfo, ensure_ascii=False, indent=1), encoding='utf-8')
    print(json.dumps(report, ensure_ascii=False, indent=1))
    print('pmx match worst distance', round(worst, 5), 'bones', len(bones))


if __name__ == '__main__':
    main()
