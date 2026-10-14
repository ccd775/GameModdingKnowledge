"""Offline check of a --face (T7) stage: reads the models back out of the .stage.

  python sm2_verify_face.py ../builds/t7_face_test.stage [--sheet ../reports/t7_faces.png]

Per target model: body slot (body look / Default slot 0) and, for suits, the static face in the mask look; the
family head model's rigged face is carried into the model's bind space through the two 'head' joints.
- suits: mask face vs head-model face, vertex by vertex (same Karin face vertices) -> must coincide (< 1 mm)
- every face mesh: weight sums, 0x80 flags on weighted joints, joints used
- sheet: per model, masked (body + mask face) and unmasked (body + head face) front close-ups of the head
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M              # noqa: E402
import sm2_build_model as SB       # noqa: E402
import sm2_stage                   # noqa: E402
import sm2_face as SF              # noqa: E402
from sm2_common import REPORTS     # noqa: E402


def slot_mesh(m, look):
    lk = SB.looks(m)
    if look not in lk or not lk[look][0]:
        return None
    d = m.decode(m.meshes[lk[look][0][0]])
    d['T'] = d['idx'].reshape(-1, 3)
    return d


def skin_check(m, d):
    ws = d['weights'].sum(1)
    used = np.unique(d['joints'][d['weights'] > 0])
    unflag = [m.joints[j]['name'] for j in used if not m.joints[j]['u2'] & 0x80]
    return dict(verts=len(d['pos']), wsum_err=float(np.abs(ws - 1).max()), joints=len(used), unflagged=unflag[:5])


def head_world(m):
    return m.joint_world()[[j['name'] for j in m.joints].index('head')]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage')
    ap.add_argument('--sheet')
    a = ap.parse_args()
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    heads = {f: hp for f, (hp, _) in SF.FAMILIES.items()}
    names = {sm2_stage.crc64_path(p): p for p in list(targets) + list(heads.values())}
    _, entries = sm2_stage.read_stage(a.stage)
    models = {names[aid]: M.Model(h + data) for span, aid, h, _, data in entries if not span and aid in names}
    hm = {f: models[p] for f, p in heads.items() if p in models}
    bad, tiles = 0, []
    for f, m in hm.items():
        d = slot_mesh(m, 'Default')
        r = skin_check(m, d)
        ok = r['wsum_err'] < 0.01 and not r['unflagged']
        bad += not ok
        print(('ok  ' if ok else 'BAD ') + f'head {f}: {r}')
    for p, m in sorted(models.items()):
        if p in heads.values():
            continue
        fam = SF.family_of(p)
        body = slot_mesh(m, 'body' if 'body' in SB.looks(m) else 'Default')
        mask = slot_mesh(m, 'mask')
        h = hm.get(fam)
        line = {'body': skin_check(m, body)}
        ok = line['body']['wsum_err'] < 0.01 and not line['body']['unflagged']
        hf = None
        if h is not None:
            hd = slot_mesh(h, 'Default')
            C = np.linalg.inv(head_world(h)) @ head_world(m)
            hf = dict(pos=(np.c_[hd['pos'], np.ones(len(hd['pos']))] @ C)[:, :3], T=hd['T'])
        if mask is not None and len(mask['pos']) > 3:
            line['mask'] = skin_check(m, mask)
            if hf is not None and len(hf['pos']) == len(mask['pos']):
                e = np.linalg.norm(hf['pos'] - mask['pos'], axis=1)
                line['mask_vs_head_mm'] = (round(float(np.median(e)) * 1000, 2), round(float(e.max()) * 1000, 2))
                ok &= e.max() < 1e-3
            else:
                ok = False
        bad += not ok
        print(('ok  ' if ok else 'BAD ') + p.split('/')[-1], line)
        tiles.append((p.split('/')[-1], m, body, mask, hf))
    print(bad, 'bad')
    if a.sheet:
        import render as R
        tmp = a.sheet + '.tmp.png'
        rows = []
        for name, m, body, mask, hf in tiles:
            hp = head_world(m)[3, :3]
            zoom = (hp + [-0.16, -0.12, -0.2], hp + [0.16, 0.22, 0.2])
            ims = []
            for meshes in ([(body['pos'], body['T'], (170, 170, 200))] + ([(mask['pos'], mask['T'], (240, 200, 190))] if mask is not None else []),
                           [(body['pos'], body['T'], (170, 170, 200))] + ([(hf['pos'], hf['T'], (190, 240, 190))] if hf is not None else [])):
                ims.append(R.render_mesh(meshes, tmp, W=260, H=280, bounds=zoom, views=((0, 1, 1),)).copy())
            rows.append((name, ims))
        os.remove(tmp)
        sheet = Image.new('RGB', (520, 280 * len(rows)), 'white')
        for i, (name, ims) in enumerate(rows):
            sheet.paste(ims[0], (0, 280 * i)); sheet.paste(ims[1], (260, 280 * i))
            dr = ImageDraw.Draw(sheet)
            dr.text((4, 280 * i + 4), name + '  masked | unmasked (head model)', fill=(200, 0, 0))
        sheet.save(a.sheet)
        print(a.sheet)


if __name__ == '__main__':
    main()
