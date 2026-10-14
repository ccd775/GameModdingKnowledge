"""Batch build: Karin into every Peter / Miles suit and outfit model (Work/reports/targets.json).

  python sm2_batch.py --out ../builds/karin_all.stage [--only regex] [--no-share] [--refit] [--dyn]

- one fit per skeleton signature (sm2_karin_geo --model <representative>), cached in Work/build_sig/<sig>/
- Karin merged into one mesh: UVs packed into a 2x2 atlas (face | body / hair | costume), one material
- weights remapped to each model by joint name (missing joints fall back to their nearest present ancestor)
- every LOD record of the body look's first slot shows Karin and shares one geometry block; all other
  meshes degenerate (knife props kept); strands / morphs stripped; unmasked heads blanked
- --dyn: hair / ears / ribbons / tail spring chains become appended joints driven by ModelAnimDynamicsDef (sm2_dyn)
- --face (T7): Karin's face leaves the body slot; suits show it (static) in their 'mask' look, the unmasked head
  models get it skinned to their facial rig (sm2_face); every fit of a family is snapped to the family reference
  fit in the head-joint frame (head_fix) so the one shared head model lines up with every body's hair
"""
import argparse, bisect, json, os, re, struct, subprocess, sys, time
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M              # noqa: E402
import sm2_assets as A             # noqa: E402
import sm2_build_model as SB       # noqa: E402
import sm2_stage                   # noqa: E402
import sm2_install as I            # noqa: E402
import sm2_dyn as SD               # noqa: E402
import sm2_face as SF              # noqa: E402
import vrm as vrmmod               # noqa: E402
from sm2_common import load_index, load_toc, extract, game_dir, REPORTS   # noqa: E402
from sm2_karin_geo import WORK, vrm_path                                  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = 'characters/hero/karin_original'
BASES = {   # player skeleton drivers (actors/hrm_bdy_firsthero/hero_*.actor); the suit skins copy joint poses by name
    'peter': 'characters/hero/hero_spiderman_base/hero_spiderman_base.model',
    'miles': 'characters/hero/hero_spiderman_miles_base/hero_spiderman_miles_base.model',
}
HEADS = ['characters/hero/hero_peterparker/head/hero_peterparker_head.model',
         'characters/hero/hero_milesmorales/head/hero_milesmorales_head.model',
         'characters/hero/hero_peterparker_young/head/hero_peterparker_young_head.model']
ATLAS = {'face': (0, 0), 'body': (1, 0), 'hair': (0, 1), 'hair_alpha': (0, 1), 'costume': (1, 1)}
ATLAS_IMG = {(0, 0): 'Karin_Face', (1, 0): 'Karin_Body', (0, 1): 'Karin_Hair', (1, 1): 'Karin_Costume'}
GLOSS = {(0, 0): (100, 56, 0, 255), (1, 0): (100, 56, 0, 255), (0, 1): (70, 60, 0, 255), (1, 1): (50, 60, 0, 255)}
DROP = ('face_alpha',)
TPL_MAT = 'characters/boss/boss_kraven/materials/boss_kraven_gauntlet.material'
TPL_TEX = {'c4096': 'characters/boss/boss_lizard_skin/textures/boss_lizard_skin_head_c.texture',
           'n': 'characters/shared/shared_civ_female/textures/civ_female_cau_legs_n.texture',
           'g': 'characters/boss/boss_kraven/textures/boss_kraven_gauntlet_g.texture',
           'm': 'characters/boss/boss_kraven/textures/boss_kraven_gauntlet_m.texture'}
STRIP = SB.STRAND_TAGS + SB.MORPH_TAGS


def tex_path(n):
    return f'{ROOT}/textures/{n}.texture'


def load_fit(npz_path):
    z = np.load(npz_path)
    parts = {}
    for k in z.files:
        part, f = k.split('__')
        parts.setdefault(part, {})[f] = z[k]
    meta = parts.pop('_meta')
    parts.pop('_dyn', None)
    return parts, [str(x) for x in meta['joint_names']], meta['parents']


def atlas_uv(key, uv):
    qx, qy = ATLAS[key]
    return np.stack([(uv[:, 0] + qx) * 0.5, (uv[:, 1] + qy) * 0.5], 1)


def merge_atlas(parts, exclude=()):
    acc = {k: [] for k in ('P', 'N', 'UV', 'T', 'J', 'W')}
    off = 0
    for key, d in parts.items():
        if key in DROP or key in exclude:
            continue
        acc['P'].append(d['P']); acc['N'].append(d['N'])
        acc['UV'].append(atlas_uv(key, d['UV']))
        acc['J'].append(d['J']); acc['W'].append(d['W'])
        acc['T'].append(d['T'].reshape(-1) + off)
        off += len(d['P'])
    k = max(j.shape[1] for j in acc['J'])
    acc['J'] = [np.pad(j, ((0, 0), (0, k - j.shape[1]))) for j in acc['J']]
    acc['W'] = [np.pad(w, ((0, 0), (0, k - w.shape[1]))) for w in acc['W']]
    return {k2: np.concatenate(v) for k2, v in acc.items()}


def head_local(P, model):
    Wh = model.joint_world()[[j['name'] for j in model.joints].index('head')]
    return (np.c_[P, np.ones(len(P))] @ np.linalg.inv(Wh))[:, :3], Wh


def head_fix(parts, names, par, dyn, model, ref_local):
    """rigidly move everything carried by the head (blended by its head-subtree weight) so that this fit's face
    matches ref_local (the family reference face, head-joint frame); -> max face error before, after (m)"""
    L, Wh = head_local(parts['face']['P'], model)
    a0, b0 = L.mean(0), ref_local.mean(0)
    U, _, Vt = np.linalg.svd((L - a0).T @ (ref_local - b0))
    R = U @ Vt
    if np.linalg.det(R) < 0:
        U[:, -1] *= -1
        R = U @ Vt
    T = np.eye(4)
    T[:3, :3], T[3, :3] = R, b0 - a0 @ R
    before = float(np.linalg.norm(L - ref_local, axis=1).max())
    after = float(np.linalg.norm(L @ R + T[3, :3] - ref_local, axis=1).max())
    if before < 1e-4:
        return before, after
    C = np.linalg.inv(Wh) @ T @ Wh
    under = np.zeros(len(names), bool)
    for i in range(len(names)):
        j = i
        while j >= 0 and names[j] != 'head':
            j = int(par[j])
        under[i] = j >= 0
    for d in parts.values():
        fh = np.where(under[d['J']], d['W'], 0).sum(1)[:, None]
        d['P'] = (1 - fh) * d['P'] + fh * (np.c_[d['P'], np.ones(len(d['P']))] @ C)[:, :3]
        N = (1 - fh) * d['N'] + fh * (d['N'] @ C[:3, :3])
        d['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
    if dyn:
        on_head = {}
        for nm, pn in zip(dyn['names'], dyn['parents']):
            on_head[nm] = pn == 'head' or on_head.get(pn, False) or (pn in names and under[names.index(pn)])
        dyn['world'] = [np.asarray(w) @ C if on_head[nm] else w for nm, w in zip(dyn['names'], dyn['world'])]
    return before, after


def remap(merged, src_names, src_par, model):
    names = [j['name'] for j in model.joints]
    ix = {n: i for i, n in enumerate(names)}
    lut = np.zeros(len(src_names), np.int64)
    fallbacks = {}
    for i, n in enumerate(src_names):
        j = i
        while j >= 0 and src_names[j] not in ix:
            j = int(src_par[j])
        if j < 0:
            raise ValueError(f'no ancestor of {n} in target')
        lut[i] = ix[src_names[j]]
        if j != i:
            fallbacks[n] = src_names[j]
    used = np.unique(merged['J'][merged['W'] > 0])
    d = dict(merged)
    d['J'] = lut[merged['J']]
    return d, {k: v for k, v in fallbacks.items() if src_names.index(k) in used}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--only', default=None, help='regex over target model paths')
    ap.add_argument('--no-share', action='store_true')
    ap.add_argument('--refit', action='store_true')
    ap.add_argument('--dyn', action='store_true', help='spring chains as AnimDynamics joints')
    ap.add_argument('--dyn-base', action='store_true',
                    help='simulate on the player base models (hero_spiderman_base / _miles_base, driven by the hero anim '
                         'controller); suits only carry the joints and copy their pose by name (T12)')
    ap.add_argument('--base-radius', type=float, default=25.0,
                    help='--dyn-base: ModelBuilt bounding-sphere radius of the base models (m); animdynamics update '
                         'distance = radius x multiplier, the 0.19 m placeholder only simulated on resets (T12). 0 = keep')
    ap.add_argument('--dyn-ab', action='append', default=[], metavar='REGEX=MODE',
                    help='per-model dyn variant for A/B tests: sim (default) | joints (0x01 + mirror, no dynamics) | '
                         'plain (u2 0, no dynamics)')
    ap.add_argument('--face', action='store_true', help='face in the mask look + rigged unmasked heads (T7)')
    ap.add_argument('--name', default='Karin Original (Peter & Miles, all suits)')
    ap.add_argument('--author', default='')
    a = ap.parse_args()
    t0 = time.time()
    log = lambda s: print(f'[{time.time() - t0:6.1f}s] {s}', flush=True)
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    targets_all = dict(targets)
    if a.only:
        targets = {k: v for k, v in targets.items() if re.search(a.only, k)}
    idx = load_index()
    toc = load_toc()
    tocx = I.TOC(os.path.join(game_dir(), 'toc'))

    def asset(path, span=0):
        return extract(toc, int(idx[path.replace('/', chr(92))]['id'], 16), span)[0]

    def meta(path):
        aid = int(idx[path.replace('/', chr(92))]['id'], 16)
        k = bisect.bisect_left(tocx.tex_ids, aid)
        assert tocx.tex_ids[k] == aid
        return bytes(tocx.tex_meta[72 * k:72 * k + 72])

    # 1. fits per skeleton signature
    sigs = {}
    for p, v in targets.items():
        sigs.setdefault(v['sig'], p)
    if a.face or a.dyn_base:   # head_fix / base models use each family's reference fit, so those must be current too
        for _, ref in SF.FAMILIES.values():
            sigs.setdefault(targets_all[ref]['sig'], ref)
    fit_root = os.path.join(WORK, 'build_sig_dyn' if a.dyn else 'build_sig')
    for sig, rep in sorted(sigs.items()):   # all (re)fits first: a later head_fix must not read a stale reference
        d = os.path.join(fit_root, sig)
        if a.refit or not os.path.exists(os.path.join(d, 'karin_geo.npz')):
            os.makedirs(d, exist_ok=True)
            src = os.path.join(WORK, 'native', rep)
            if not os.path.exists(src):
                os.makedirs(os.path.dirname(src), exist_ok=True)
                open(src, 'wb').write(asset(rep))
            r = subprocess.run([sys.executable, '-B', os.path.join(HERE, 'sm2_karin_geo.py'), '--model', rep, '--out', d]
                               + (['--dyn'] if a.dyn else []), capture_output=True, text=True)
            if r.returncode:
                raise SystemExit(r.stdout + r.stderr)
            log(f'refit {sig} <- {rep.split("/")[-1]}')
    fits = {}
    for sig, rep in sorted(sigs.items()):
        npz = os.path.join(fit_root, sig, 'karin_geo.npz')
        parts, src_names, src_par = load_fit(npz)
        dyn = SD.load(npz) if a.dyn else None
        face = None
        if a.face:
            fam = SF.family_of(rep)
            ref = SF.FAMILIES[fam][1]
            rd = os.path.join(fit_root, targets_all[ref]['sig'], 'karin_geo.npz')
            ref_local, _ = head_local(load_fit(rd)[0]['face']['P'], M.Model(asset(ref)))
            fix = head_fix(parts, src_names, src_par, dyn, M.Model(asset(rep)), ref_local)
            face = dict(parts['face'], UV=atlas_uv('face', parts['face']['UV']), T=parts['face']['T'].reshape(-1))
            log(f'  face: family {fam}, head frame vs reference {fix[0] * 1000:.1f} -> {fix[1] * 1000:.2f} mm')
        fits[sig] = (merge_atlas(parts, exclude=('face',) if a.face else ()), src_names, src_par, dyn, face)
        log(f'fit {sig} <- {rep.split("/")[-1]} ({len(fits[sig][0]["P"])} verts)')

    assets = []
    report = dict(models={}, heads=[], textures={}, material=None)
    # 2. textures + material
    tpl = {k: A.TextureTemplate(asset(p), meta(p)) for k, p in TPL_TEX.items()}
    v = vrmmod.Vrm(vrm_path())
    imgs = {im.get('name'): v.image(i) for i, im in enumerate(v.js['images'])}
    atlas = Image.new('RGBA', (4096, 4096))
    g = Image.new('RGBA', (512, 512))
    for (qx, qy), name in ATLAS_IMG.items():
        atlas.paste(imgs[name].convert('RGBA').resize((2048, 2048), Image.Resampling.LANCZOS), (qx * 2048, qy * 2048))
        g.paste(Image.new('RGBA', (256, 256), GLOSS[(qx, qy)]), (qx * 256, qy * 256))
    tex = {'karin_atlas_c': A.build_texture(tpl['c4096'], atlas, 99),
           'karin_atlas_g': A.build_texture(tpl['g'], g, 72),
           'karin_flat_n': A.build_texture(tpl['n'], Image.new('RGBA', (256, 256), (128, 128, 0, 255)), 83),
           'karin_cloth_m': A.build_texture(tpl['m'], Image.new('RGBA', (256, 256), (0, 128, 255, 255)), 71)}
    for n, t in tex.items():
        aid = sm2_stage.crc64_path(tex_path(n))
        assets.append((0, aid, t['span0'], t['header'], t['meta']))
        if t['span1']:
            assets.append((1, aid, t['span1'], None, None))
        report['textures'][tex_path(n)] = t['info']
    mat_path = f'{ROOT}/materials/karin_atlas.material'
    mh, mb = A.build_material(asset(TPL_MAT), dict(g=tex_path('karin_atlas_g'), n=tex_path('karin_flat_n'),
                                                   c=tex_path('karin_atlas_c'), m=tex_path('karin_cloth_m')))
    assets.append((0, sm2_stage.crc64_path(mat_path), mb, mh, None))
    report['material'] = mat_path
    log('textures + material')

    # 3. models
    total = 0
    for p, info in sorted(targets.items()):
        raw = asset(p)
        merged, src_names, src_par, dyn, face = fits[info['sig']]
        mode = next((md for rx, md in (x.rsplit('=', 1) for x in a.dyn_ab) if re.search(rx, p)),
                    'joints' if a.dyn_base else 'sim')
        if dyn:
            raw = SD.add_dyn_joints(raw, dyn, plain=mode == 'plain')
        m = M.Model(raw)
        part, fb = remap(merged, src_names, src_par, m)
        parts, extra = {'body': part}, None
        if face is not None and 'mask' in SB.looks(m):       # civilian outfits: the head model shows the face
            parts['face'] = remap(face, src_names, src_par, m)[0]
            extra = {'mask': 'face'}
        names = [j['name'] for j in m.joints]
        hj = names.index('head')
        hp = m.joint_world()[hj][3, :3]
        lk = SB.looks(m)
        main = (lk.get('body') or lk.get('Default'))
        mi0 = m.meshes[main[0][0]].material & 0xFFFF
        out, rep = SB.build(raw, parts, hp, hj, mat_override={mi0: (mat_path, 'karin_atlas')},
                            keep_materials=False, mat_for_part={'body': mi0, 'face': mi0}, drop_parts=DROP,
                            share_blocks=not a.no_share, strip_extra=STRIP, extra_slots=extra)
        if dyn and mode == 'sim':
            out = SD.attach_dynamics(out, dyn)
        hl = 8 + out[5] * 8 + struct.unpack_from('<H', out, 6)[0]
        assets.append((0, sm2_stage.crc64_path(p), out[hl:], out[:hl], None))
        total += len(out)
        report['models'][p] = dict(bytes=len(out), sig=info['sig'], fallback_joints=fb, face_in_mask=extra is not None,
                                   dyn_mode=mode if dyn else None)
        log(f'{p.split("/")[-1]:55s} {len(out):>9} B  fallbacks {fb if fb else "-"}{"  dyn " + mode if dyn and mode != "sim" else ""}')
    if a.dyn_base:
        for fam, bpath in BASES.items():
            dyn = fits[targets_all[SF.FAMILIES[fam][1]]['sig']][3]
            braw = SD.attach_dynamics(SD.add_dyn_joints(asset(bpath), dyn), dyn)
            if a.base_radius:
                braw = SD.set_bsphere_radius(braw, a.base_radius)
            hl = 8 + braw[5] * 8 + struct.unpack_from('<H', braw, 6)[0]
            assets.append((0, sm2_stage.crc64_path(bpath), braw[hl:], braw[:hl], None))
            report.setdefault('bases', []).append(bpath)
            log(f'base {bpath.split("/")[-1]}: +{len(dyn["names"])} joints, {len(dyn["chains"])} chains ({fam} reference fit), '
                f'bsphere radius {a.base_radius or "kept"}')
    for hpth in HEADS:
        if hpth.replace('/', chr(92)) not in idx:
            continue
        hraw = asset(hpth)
        hm = M.Model(hraw)
        hj2 = [j['name'] for j in hm.joints].index('head')
        fam = next((f for f, (hp_, _) in SF.FAMILIES.items() if hp_ == hpth), None)
        if a.face and fam:
            _, hf, _, hinfo = SF.rig(fam, asset, fit_dir='build_sig_dyn' if a.dyn else 'build_sig')
            hf = dict(hf, UV=atlas_uv('face', hf['UV']), T=hf['T'].reshape(-1))
            lk0 = SB.looks(hm)
            hm0 = hm.meshes[(lk0.get('head') or lk0['Default'])[0][0]].material & 0xFFFF
            hout, _ = SB.build(hraw, {'body': hf}, hm.joint_world()[hj2][3, :3], hj2,
                               mat_override={hm0: (mat_path, 'karin_atlas')}, keep_materials=False,
                               mat_for_part={'body': hm0}, share_blocks=True, strip_extra=STRIP)
            log(f'head {hpth.split("/")[-1]}: rigged face, {hinfo["joints_used"]} joints')
        else:
            hout, _ = SB.build(hraw, {}, hm.joint_world()[hj2][3, :3], hj2, blank=True)
        hl = 8 + hout[5] * 8 + struct.unpack_from('<H', hout, 6)[0]
        assets.append((0, sm2_stage.crc64_path(hpth), hout[hl:], hout[:hl], None))
        report['heads'].append(hpth)
    log(f'{len(report["models"])} models ({total / 1e6:.1f} MB), {len(report["heads"])} heads {"rigged" if a.face else "blanked"}')
    sm2_stage.write_stage(a.out, assets, a.name, a.author,
                          'Karin_Original replaces Peter and Miles in every suit and outfit')
    json.dump(report, open(a.out + '.json', 'w'), indent=1)
    log(f'stage {a.out} ({os.path.getsize(a.out) / 1e6:.1f} MB, {len(assets)} assets)')


if __name__ == '__main__':
    main()
