"""T15 feasibility test: Karin's spring chains on an attached prop actor instead of the suit skin.

  python sm2_prop_test.py --base ../builds/t14_karin_static.stage --out ../builds/t15_prop_test.stage [--delta d.stage]
  (--delta: only the two rebuilt assets; install as `install <full stage already on the PC> d.stage` -> mod0, mod1)

Why: AnimDynamics only keep running on models driven by their own AnimControllerComponent. The suit model is a skin of
the player base model and only simulates for the settle after a reset (T10/T11); the base model itself did not either
(T12/T13). Miles' Spider-Cat suit gets an attached actor through hero_spiderman.actor's HeroSuitAddition
(prop_backpack_spidercat.actor: AnimControllerComponent IsHero + its own dynamics). This test puts the triangles that hang
on Karin's chains (twin tails, side / front hair, ears, ribbons, tail) into that prop model with the chains and their
dynamics, blanks the backpack, and removes those triangles from the Spider-Cat suit body. Everything else = --base stage.

Prop space = suit space translated by -(suit backpack_attach) (checked: spine .. chest bind positions differ by exactly
that, no rotation). 'head' and 'pelvis' are added to the prop (children of neck / a_body) so the chains have their real
parents if the prop copies hero joints by name; if it does not, they ride the neck / attach point.
"""
import argparse, json, os, struct, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M                 # noqa: E402
import i30_joints as IJ               # noqa: E402
import sm2_build_model as SB          # noqa: E402
import sm2_dyn as SD                  # noqa: E402
import sm2_face as SF                 # noqa: E402
import sm2_stage                      # noqa: E402
import sm2_batch as B                 # noqa: E402
from i30_build import split_asset, save_model   # noqa: E402
from sm2_common import load_index, load_toc, extract, REPORTS   # noqa: E402
from sm2_karin_geo import WORK        # noqa: E402

SUIT = 'characters/hero/hero_spiderman_miles_spidercat/hero_spiderman_miles_spidercat.model'
PROP = 'characters/prop/prop_backpack_cat/prop_backpack_spidercat.model'
MOVE = 0.5              # a triangle goes to the prop when one of its vertices has >= this weight on karin_* joints
PROP_RADIUS = 2.0       # ModelBuilt bsphere radius of the prop (backpack 0.40 m; Karin's twin tails are ~1 m long)


def subset(d, tris):
    used = np.unique(tris)
    lut = -np.ones(len(d['P']), np.int64)
    lut[used] = np.arange(len(used))
    out = {k: d[k][used] for k in ('P', 'N', 'UV', 'J', 'W')}
    out['T'] = lut[tris].reshape(-1)
    return out


def remap_loose(d, names, par, model, root='a_body'):
    """sm2_batch.remap, but source joints with no ancestor in the target map to its root (unused ones only matter)"""
    tn = [j['name'] for j in model.joints]
    ix = {n: i for i, n in enumerate(tn)}
    lut = np.zeros(len(names), np.int64)
    fb = {}
    for i, n in enumerate(names):
        j = i
        while j >= 0 and names[j] not in ix:
            j = int(par[j])
        lut[i] = ix[names[j]] if j >= 0 else ix[root]
        if j != i:
            fb[n] = names[j] if j >= 0 else root
    used = set(np.unique(d['J'][d['W'] > 0]).tolist())
    return dict(d, J=lut[d['J']]), {k: v for k, v in fb.items() if names.index(k) in used}


def add_named_joints(raw, new):
    """new: [dict(name, parent name, world row 4x4, u2)] appended with i30_joints (mirror entries for 0x01)"""
    m = M.Model(raw)
    ix = {j['name']: i for i, j in enumerate(m.joints)}
    Wm = m.joint_world()
    header, d = split_asset(raw)
    base = d.string_base()
    lst = []
    for k, nj in enumerate(new):
        ix[nj['name']] = len(m.joints) + k
        lst.append(dict(name=nj['name'], parent=ix[nj['parent']], world=nj['world'], u2=nj['u2']))
    IJ.add_joints(d, lst, lambda j: Wm[j])
    h, body = save_model(header, d, base)
    return h + body


def family_of(suit):
    """same rule as sm2_batch (sm2_face.family_of: 'miles' in the folder name), so hero_spiderman_milesmorales is Miles"""
    return SF.family_of(suit)


def chain_fit(asset, targets, suit, family=None):
    """fit (dynamics variant) of the suit's signature, aligned to the family reference face like sm2_batch --face,
    split into triangles that stay on the suit body and triangles that hang on karin_* chains (-> prop)"""
    family = family or family_of(suit)
    fr = os.path.join(WORK, 'build_sig_dyn')
    npz = os.path.join(fr, targets[suit]['sig'], 'karin_geo.npz')
    parts, names, par = B.load_fit(npz)
    dyn = SD.load(npz)
    ref = SF.FAMILIES[family][1]
    ref_local, _ = B.head_local(B.load_fit(os.path.join(fr, targets[ref]['sig'], 'karin_geo.npz'))[0]['face']['P'],
                                M.Model(asset(ref)))
    raw = asset(suit)
    fix = B.head_fix(parts, names, par, dyn, M.Model(raw), ref_local)
    face = dict(parts['face'], UV=B.atlas_uv('face', parts['face']['UV']), T=parts['face']['T'].reshape(-1))
    merged = B.merge_atlas(parts, exclude=('face',))
    karin = np.array([n.startswith('karin_') for n in names])
    share = np.where(karin[merged['J']], merged['W'], 0).sum(1)
    T = merged['T'].reshape(-1, 3)
    mv = (share[T] >= MOVE).any(1)
    print(f'{suit.split("/")[-1]}: head fix {fix[0] * 1000:.1f} -> {fix[1] * 1000:.2f} mm; '
          f'triangles: suit {int((~mv).sum())}, prop {int(mv.sum())}')
    return dict(suit=suit, raw=raw, names=names, par=par, dyn=dyn, face=face,
                stay=subset(merged, T[~mv]), move=subset(merged, T[mv]))


def strip_body(f, mat_path):
    """the suit body without the chain triangles (static build, karin_* weights fall back to head / pelvis)"""
    m = M.Model(f['raw'])
    part, fb = B.remap(f['stay'], f['names'], f['par'], m)
    sparts = {'body': part, 'face': B.remap(f['face'], f['names'], f['par'], m)[0]}
    hj = [j['name'] for j in m.joints].index('head')
    hp = m.joint_world()[hj][3, :3]
    lk = SB.looks(m)
    mi0 = m.meshes[(lk.get('body') or lk.get('Default'))[0][0]].material & 0xFFFF
    out, _ = SB.build(f['raw'], sparts, hp, hj, mat_override={mi0: (mat_path, 'karin_atlas')}, keep_materials=False,
                      mat_for_part={'body': mi0, 'face': mi0}, drop_parts=B.DROP, share_blocks=True,
                      strip_extra=B.STRIP, extra_slots={'mask': 'face'})
    print('  body', len(out), 'B, fallbacks', sorted(set(fb.values())))
    return out


def build_prop(f, raw_prop, mat_path, off=None):
    """prop model: head / pelvis + chain joints in prop space (suit space - off; default the suit's backpack_attach),
    the chain triangles and Karin's dynamics"""
    m = M.Model(f['raw'])
    Ws = m.joint_world()
    sn = [j['name'] for j in m.joints]
    if off is None:
        off = Ws[sn.index('backpack_attach')][3, :3].copy()
    shift = lambda W: np.vstack([W[:3], np.r_[W[3, :3] - off, 1.0]])
    raw_prop = add_named_joints(raw_prop, [
        dict(name='head', parent='neck', world=shift(Ws[sn.index('head')]), u2=m.joints[sn.index('head')]['u2'] & 0x7F),
        dict(name='pelvis', parent='a_body', world=shift(Ws[sn.index('pelvis')]), u2=m.joints[sn.index('pelvis')]['u2'] & 0x7F),
    ])
    dyn_p = dict(f['dyn'], world=[shift(np.asarray(w)) for w in f['dyn']['world']])
    raw_prop = SD.add_dyn_joints(raw_prop, dyn_p)
    pm = M.Model(raw_prop)
    mv_p = dict(f['move'], P=f['move']['P'] - off)
    ppart, pfb = remap_loose(mv_p, f['names'], f['par'], pm)
    pn = [j['name'] for j in pm.joints]
    phj = pn.index('head')
    plk = SB.looks(pm)
    pmi0 = pm.meshes[(plk.get('body') or plk.get('Default'))[0][0]].material & 0xFFFF
    out, _ = SB.build(raw_prop, {'body': ppart}, pm.joint_world()[phj][3, :3], phj,
                      mat_override={pmi0: (mat_path, 'karin_atlas')}, keep_materials=False,
                      mat_for_part={'body': pmi0}, drop_parts=B.DROP, share_blocks=True, strip_extra=B.STRIP)
    out = SD.attach_dynamics(out, dyn_p)
    out = SD.set_bsphere_radius(out, PROP_RADIUS)
    print('  prop', len(out), 'B, fallbacks', pfb)
    return out


def stage_entry(r):
    """asset bytes (toc header + data) -> (header, data) as sm2_stage stores them"""
    hl = 8 + r[5] * 8 + struct.unpack_from('<H', r, 6)[0]
    return r[:hl], r[hl:]


def write_with(base, out_path, rep, delta=None, name=None, description=None):
    """stage = base stage with the assets in rep {asset id: bytes} replaced / added; delta: also a stage of rep only.
    name / description: stage info for out_path (default: the base stage's)"""
    info, items = sm2_stage.read_stage(base)
    info = dict(info, **{k: v for k, v in (('name', name), ('description', description)) if v})
    out, seen = [], set()
    for span, aid, h, t, d in items:
        if span == 0 and aid in rep:
            h, d = stage_entry(rep[aid])
            seen.add(aid)
        out.append((span, aid, d, h, t))
    for aid, r in rep.items():
        if aid not in seen:
            h, d = stage_entry(r)
            out.append((0, aid, d, h, None))
    if out_path:
        sm2_stage.write_stage(out_path, out, info.get('name', 'Karin'), info.get('author', ''), info.get('description', ''))
        print('wrote', out_path, len(out), 'assets')
    if delta:
        dl = []
        for aid, r in rep.items():
            h, d = stage_entry(r)
            dl.append((0, aid, d, h, None))
        sm2_stage.write_stage(delta, dl, 'Karin physics delta', info.get('author', ''),
                              'suit + prop only; install after the base stage')
        print('wrote', delta, len(dl), 'assets', os.path.getsize(delta), 'B')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--delta', help='also write a stage with only the two rebuilt assets (install after --base as mod1)')
    a = ap.parse_args()
    idx = load_index()
    toc = load_toc()
    asset = lambda p: extract(toc, int(idx[p.replace('/', chr(92))]['id'], 16), 0)[0]
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    mat_path = f'{B.ROOT}/materials/karin_atlas.material'
    f = chain_fit(asset, targets, SUIT, 'miles')
    suit_out = strip_body(f, mat_path)
    prop_out = build_prop(f, asset(PROP), mat_path)
    write_with(a.base, a.out, {sm2_stage.crc64_path(SUIT): suit_out, sm2_stage.crc64_path(PROP): prop_out}, a.delta)


if __name__ == '__main__':
    main()
