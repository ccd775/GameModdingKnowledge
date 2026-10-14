"""Offline readback of every .model in a .stage: decode the body look LOD0 Karin mesh and check its skin.

  python sm2_verify_stage.py ../builds/t5_karin_all.stage [--sheet ../reports/t5_readback.png] [--only regex]

Checks per model: weights sum to 1, every weighted joint has the 0x80 deform flag, distance from each vertex to its
dominant joint (median / p99, and how many vertices are > 0.7 m away: a bad joint remap), all LODs of the slot share one block.
"""
import argparse, json, os, re, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M              # noqa: E402
import render                      # noqa: E402
import sm2_build_model as SB       # noqa: E402
import sm2_stage                   # noqa: E402
from sm2_common import REPORTS     # noqa: E402
from sm2_karin_geo import gltf_to_got   # noqa: E402


def check(raw):
    m = M.Model(raw)
    lk = SB.looks(m)
    main = lk.get('body') or lk.get('Default')
    mi = max(main[0], key=lambda i: m.meshes[i].vertex_count)
    me = m.meshes[mi]
    d = m.decode(me)
    J, W = d['joints'], d['weights']
    wsum = W.sum(1)
    used = np.unique(J[W > 0])
    unflagged = [m.joints[j]['name'] for j in used if not m.joints[j]['u2'] & 0x80]
    dom = J[np.arange(len(J)), W.argmax(1)]
    jw = m.joint_world()[:, 3, :3]
    dist = np.linalg.norm(d['pos'] - jw[dom], axis=1)
    blocks = {m.meshes[lod[0]].block_off for lod in main if lod}
    return m, d, dict(mesh=mi, verts=me.vertex_count, tris=me.index_count // 3, joints=len(m.joints),
                      wsum_err=float(np.abs(wsum - 1).max()), unflagged=unflagged,
                      dist_med=float(np.median(dist)), dist_p99=float(np.percentile(dist, 99)), far=int((dist > 0.7).sum()),
                      lod_blocks=len(blocks), max_joint=int(J.max()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('stage')
    ap.add_argument('--sheet', default=None)
    ap.add_argument('--only', default=None)
    a = ap.parse_args()
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    names = {sm2_stage.crc64_path(p): p for p in targets}
    _, entries = sm2_stage.read_stage(a.stage)
    tiles, bad = [], []
    for span, aid, h, _, data in entries:
        p = names.get(aid)
        if span or p is None or (a.only and not re.search(a.only, p)):
            continue
        m, d, r = check(h + data)
        ok = r['wsum_err'] < 0.01 and not r['unflagged'] and r['far'] <= r['verts'] // 200 and r['lod_blocks'] == 1
        if not ok:
            bad.append(p)
        print(f'{"ok " if ok else "BAD"} {p.split("/")[-1]:52s} v{r["verts"]} j{r["joints"]:4d} maxj {r["max_joint"]:3d} '
              f'wErr {r["wsum_err"]:.4f} dist {r["dist_med"]:.3f}/{r["dist_p99"]:.3f} far {r["far"]} blocks {r["lod_blocks"]} '
              f'{("unflagged " + str(r["unflagged"][:4])) if r["unflagged"] else ""}', flush=True)
        if a.sheet:
            v = gltf_to_got(d['pos'])
            im = render.render_mesh([(v, d['idx'].reshape(-1, 3), (235, 200, 185))], os.path.join(REPORTS, '_tile.png'),
                                    W=160, H=300, views=((1, 2, 1),))
            im = im if isinstance(im, Image.Image) else Image.open(os.path.join(REPORTS, '_tile.png'))
            ImageDraw.Draw(im).text((2, 2), p.split('/')[-1][:26], fill=(200, 0, 0) if not ok else (0, 0, 0))
            tiles.append(im.convert('RGB'))
    if a.sheet and tiles:
        os.remove(os.path.join(REPORTS, '_tile.png'))
        cols = 12
        sheet = Image.new('RGB', (cols * tiles[0].width, -(-len(tiles) // cols) * tiles[0].height), 'white')
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * t.width, (i // cols) * t.height))
        sheet.save(a.sheet)
        print(a.sheet)
    print(f'{len(bad)} bad', bad)


if __name__ == '__main__':
    main()
