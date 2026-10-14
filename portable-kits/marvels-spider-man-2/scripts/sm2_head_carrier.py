"""Head-actor carrier for Karin's spring chains (all-suits route B, SOP/PLAN_ALL_SUITS_PHYSICS.md).

  python -B sm2_head_carrier.py --base ../../Output/Karin_SM2_v1/Karin_Original.stage [--delta d.stage] [--out full.stage]
         [--family peter|miles] [--suit <suit model> ...] [--cat-actor | --never-cull] [--joint-bsphere 1.0] [--map-body]
         [--masked] [--blank-prop]     (v2 = --never-cull --joint-bsphere 1.0 --map-body --masked --blank-prop)

Why: T18 showed that extra HeroSuitAddition components on hero_spiderman.actor are ignored (the game reads one), so the
cat-prop route covers one suit. Every masked Peter / Miles suit instead spawns actors/hma_hed_base/hma_hed_base.actor as its
head actor (Peter: loadout item vanityhedspiderman1.config; Miles: HeadManager.HeadActor default, unverified). That actor
has its own AnimControllerComponent and its model characters/test/test_i20Hero/test_i20_Head.model (14 joints, one 1 mm
quad) is used by nothing else. This puts the chain joints / triangles / dynamics into that model (like sm2_prop_test does
for the cat backpack) and removes the chain triangles from the given suits.

Placement: HeadManager copies a_body, chest, neck, head, LF/RT_clavicle (+root for Miles) into the head actor
(AutoMatchJoints false). Bind rotations of head / a_body match between test_i20_Head and the suits, so joints and
triangles are translated: head-carried by (test head - suit head), pelvis-carried by (test a_body - suit pelvis).
BODY_JOINTS (pelvis, spine, spine_helper1) are added under a_body; with --map-body (T22) they are also added to the
hero actors' HeadManager joint map, else they ride on a_body (T21: the tail detached when crouching / crawling).
Peter and Miles fits differ by (0, +4.3, -20.8) mm in head-local coordinates: one shared model fits one family exactly.
Ported from the workflow prototype carrier-actors/head_carrier_build.py (2026-10-13).
"""
import argparse, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M                 # noqa: E402
import sm2_build_model as SB          # noqa: E402
import sm2_dyn as SD                  # noqa: E402
import sm2_face as SF                 # noqa: E402
import sm2_stage                      # noqa: E402
import sm2_batch as B                 # noqa: E402
import sm2_prop_test as P             # noqa: E402
from sm2_common import load_index, load_toc, extract, REPORTS   # noqa: E402

HEAD_MODEL = 'characters/test/test_i20Hero/test_i20_Head.model'
# hip joints added to the carrier (pelvis: tail chain root; spine / spine_helper1: up to 0.6 of the tail-root weights).
# They follow the body only when the hero actors' HeadManager maps them (T22, map_body_joints_actor); before that they
# rode on a_body (T21: tail detached when crouching / crawling, gap at the tail root).
BODY_JOINTS = ('pelvis', 'spine', 'spine_helper1')
T19_SUITS = ['characters/hero/hero_spiderman_advanced/hero_spiderman_advanced.model',
             'characters/hero/hero_spiderman_miles_advanced/hero_spiderman_miles_advanced.model']


def carried_by(names, par):
    """fit joint index -> 'head' / 'pelvis' / None (first of the two found walking up the parents)"""
    out = []
    for i in range(len(names)):
        j = i
        while j >= 0 and names[j] not in ('head', 'pelvis'):
            j = int(par[j])
        out.append(names[j] if j >= 0 else None)
    return out


def build_head_carrier(f, raw_head, mat_path):
    """f: sm2_prop_test.chain_fit of a suit of the family the carrier is aligned to"""
    hm0 = M.Model(raw_head)
    hn0 = [j['name'] for j in hm0.joints]
    HW = hm0.joint_world()
    m = M.Model(f['raw'])
    Ws = m.joint_world()
    sn = [j['name'] for j in m.joints]
    names, par, dyn, move = f['names'], f['par'], f['dyn'], f['move']
    sh = {'head': HW[hn0.index('head')][3, :3] - Ws[sn.index('head')][3, :3],
          'pelvis': HW[hn0.index('a_body')][3, :3] - Ws[sn.index('pelvis')][3, :3]}
    print('  shift head (mm)', np.round(sh['head'] * 1000, 1), 'pelvis (mm)', np.round(sh['pelvis'] * 1000, 1))
    cb = carried_by(names, par)
    add = []
    for nm in BODY_JOINTS:     # suit order: parents (a_body or an earlier entry) come first
        w = Ws[sn.index(nm)].copy()
        w[3, :3] += sh['pelvis']
        jp = m.joints[sn.index(nm)]['parent']
        add.append(dict(name=nm, parent=sn[jp], world=w, u2=m.joints[sn.index(nm)]['u2'] & 0x7F))
    raw_h = P.add_named_joints(raw_head, add)
    dw = []
    for nm, w in zip(dyn['names'], dyn['world']):
        w = np.array(w, dtype=np.float64)
        w[3, :3] += sh[cb[names.index(nm)]]
        dw.append(w)
    dyn_h = dict(dyn, world=dw)
    raw_h = SD.add_dyn_joints(raw_h, dyn_h)
    hm = M.Model(raw_h)
    vs = np.zeros((len(move['P']), 3))
    wsum = np.zeros(len(move['P']))
    for k in range(move['J'].shape[1]):
        jk, wk = move['J'][:, k], move['W'][:, k]
        for root in ('head', 'pelvis'):
            sel = np.array([cb[j] == root for j in jk]) & (wk > 0)
            vs[sel] += wk[sel, None] * sh[root]
            wsum[sel] += wk[sel]
    vs /= np.maximum(wsum, 1e-9)[:, None]
    hpart, hfb = P.remap_loose(dict(move, P=move['P'] + vs), names, par, hm)
    hn = [j['name'] for j in hm.joints]
    hhj = hn.index('head')
    hlk = SB.looks(hm)
    hmi0 = hm.meshes[(hlk.get('body') or hlk.get('Default'))[0][0]].material & 0xFFFF
    out, _ = SB.build(raw_h, {'body': hpart}, hm.joint_world()[hhj][3, :3], hhj,
                      mat_override={hmi0: (mat_path, 'karin_atlas')}, keep_materials=False,
                      mat_for_part={'body': hmi0}, drop_parts=B.DROP, share_blocks=True, strip_extra=B.STRIP)
    out = SD.attach_dynamics(out, dyn_h)
    out = SD.set_bsphere_radius(out, P.PROP_RADIUS)
    print(f'  head carrier {len(out)} B, joints {M.Model(out).njoints}, fallbacks {hfb}')
    return out


HEAD_ACTOR = 'actors/hma_hed_base/hma_hed_base.actor'
CAT_ACTOR = 'characters/prop/prop_backpack_cat/prop_backpack_spidercat.actor'


def cat_style_head_actor(raw_cat, raw_head_actor):
    """T20: hma_hed_base.actor rebuilt as a copy of the cat prop actor (AnimController with prop_backpack_cat.animset,
    ModelInstFlags IsHero, SimpleAnimated Backpack_Tail_Loop: the setup that simulates continuously, T15-T17) whose
    model is the head carrier. T19: with the original head actor (only animset missing, PerformanceType kTypeHead, no
    IsHero, no animation) the chains settled once and froze."""
    import math, struct
    import i30_actor as A
    import i30_actor_edit as E
    model = A.Actor(raw_head_actor)
    model_path = model.string(struct.unpack_from('<I', model.sec[A.SEC_BUILT])[0])
    act = A.Actor(raw_cat)
    assert act.save() == raw_cat
    old = E.set_model(act, model_path)
    b0, n0 = act.hdr_b, len(A.Actor(raw_cat).D)
    out = act.save()
    act.hdr_b = (b0 & 0xF0000000) | min(0x0FFFFFFF, math.ceil((b0 & 0x0FFFFFFF) * len(out[16:]) / n0))
    out = act.save()
    b, bad = E.verify(out)
    assert not bad, bad
    assert b.string(struct.unpack_from('<I', b.sec[A.SEC_BUILT])[0]) == model_path
    print(f'  head actor: cat prop copy, model {old} -> {model_path}; {len(raw_head_actor)} -> {len(out)} B, '
          f'components {[c.name for c in b.components]}')
    return out


def never_cull_actor(raw):
    """AnimControllerComponent.NeverCull = true (same length): the camera distance is then never computed and the
    AnimDynamics distance gate always passes (wf2: AC+0x48 |= 8 at 0x1428c6749). hma_hed_base.actor has it false."""
    import i30_actor as A
    import i30_actor_edit as E
    a = A.Actor(raw)
    assert a.save() == raw
    f = a.component('AnimControllerComponent')[0].obj.field('NeverCull')
    assert f is not None, 'no NeverCull field to flip'
    f.value = 1
    out = a.save()
    b, bad = E.verify(out)
    assert not bad and len(out) == len(raw), bad
    assert b.component('AnimControllerComponent')[0].obj['NeverCull'] == 1
    print('  head actor: NeverCull false -> true, bytes changed', [i for i in range(len(raw)) if raw[i] != out[i]])
    return out


def blank_model(raw):
    """every mesh degenerate (sm2_batch's blanked-head build), joints / animation untouched"""
    m = M.Model(raw)
    out, _ = SB.build(raw, {}, m.joint_world()[0][3, :3], 0, blank=True)
    print(f'  blank {len(raw)} -> {len(out)} B, {len(m.meshes)} meshes degenerate')
    return out


# every actor whose HeadManager spawns hma_hed_base with an explicit CustomJointMap (the symbiote Peter boss wears a
# Karin suit loadout on hero_spiderman_base). hero_spiderman_invisible and the ui proxies have no map (auto match).
HERO_ACTORS = ['actors/hrm_bdy_firsthero/hero_spiderman.actor', 'actors/hrm_bdy_firsthero/hero_milesmorales.actor',
               'characters/boss/boss_symbiote_pete/actors/boss_symbiote_pete.actor']


def map_body_joints_actor(raw):
    """T22: HeadManager.CustomJointMap += {j -> j for j in BODY_JOINTS}. The head actor gets the body pose only for
    mapped joints (Peter: a_body chest neck head clavicles; Miles + root), so the carrier's hip joints followed a_body.
    Head models without these joints skip the entries, as test_i20_Head already skips Miles' 'root'. New elements
    reuse the name strings of the first element."""
    import math
    import i30_actor as A
    import i30_actor_edit as E
    a = A.Actor(raw)
    assert a.save() == raw
    hm = a.component('HeadManager')
    assert len(hm) == 1
    f = hm[0].obj.field('CustomJointMap')
    have = {x['BodyJoint'].s for x in f.value}
    for nm in BODY_JOINTS:
        if nm in have:
            continue
        el = E.deep_copy(f.value[0])
        for k in ('BodyJoint', 'HeadJoint'):
            el.field(k).value = A.Str(nm)
        f.value.append(el)
    if len(f.value) == len(have):
        return raw
    f.flags = (len(f.value) << 4) | (f.flags & 0xF)
    before = {c.id: c.obj.to_py() for c in a.components if c.obj is not None and c.name != 'HeadManager'}
    b0, n0 = a.hdr_b, len(A.Actor(raw).D)
    out = a.save()
    a.hdr_b = (b0 & 0xF0000000) | min(0x0FFFFFFF, math.ceil((b0 & 0x0FFFFFFF) * len(out[16:]) / n0))
    out = a.save()
    b, bad = E.verify(out)
    assert not bad, bad
    assert {c.id: c.obj.to_py() for c in b.components if c.obj is not None and c.name != 'HeadManager'} == before
    m = b.component('HeadManager')[0].obj.to_py()['CustomJointMap']
    assert all(x['BodyJoint'] == x['HeadJoint'] for x in m) and {x['BodyJoint'] for x in m} >= set(BODY_JOINTS)
    print(f'  hero actor: CustomJointMap {[x["BodyJoint"] for x in m]}; {len(raw)} -> {len(out)} B')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--base', required=True, help='stage the delta is installed on top of (v1 release stage)')
    ap.add_argument('--delta', help='write a stage with only the changed assets (install after --base)')
    ap.add_argument('--out', help='write the full stage (--base with the changed assets replaced / added)')
    ap.add_argument('--family', choices=('peter', 'miles'), default='peter', help='family the shared carrier is aligned to')
    ap.add_argument('--suit', action='append', help='suits that lose their chain triangles (default: the T19 pair)')
    ap.add_argument('--masked', action='store_true', help='T23: strip every suit of reports/masked_suits.json (91)')
    ap.add_argument('--blank-prop', action='store_true',
                    help='T23: cat backpack prop (v1: Karin chains) -> game prop with all meshes degenerate')
    ap.add_argument('--cat-actor', action='store_true', help='T20: replace hma_hed_base.actor by a copy of the cat prop actor')
    ap.add_argument('--never-cull', action='store_true', help='T21: hma_hed_base.actor AnimController NeverCull = true')
    ap.add_argument('--joint-bsphere', type=float, default=0.0, help='T21: raise the carrier ModelJointBspheres radii (m)')
    ap.add_argument('--map-body', action='store_true', help='T22: add BODY_JOINTS to the hero actors HeadManager joint map')
    ap.add_argument('--name', help='stage name for --out (default: the base stage name)')
    ap.add_argument('--description', help='stage description for --out (default: the base stage description)')
    a = ap.parse_args()
    idx = load_index()
    toc = load_toc()
    asset = lambda p: extract(toc, int(idx[p.replace('/', chr(92)).lower()]['id'], 16), 0)[0]
    idx = {k.lower(): v for k, v in idx.items()}
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    mat_path = f'{B.ROOT}/materials/karin_atlas.material'
    ref = P.chain_fit(asset, targets, SF.FAMILIES[a.family][1], a.family)
    carrier = build_head_carrier(ref, asset(HEAD_MODEL), mat_path)
    if a.joint_bsphere:
        carrier = SD.set_joint_bsphere_radius(carrier, a.joint_bsphere)
        print('  carrier joint bspheres >=', a.joint_bsphere, 'm')
    rep = {sm2_stage.crc64_path(HEAD_MODEL): carrier}
    if a.never_cull:
        rep[sm2_stage.crc64_path(HEAD_ACTOR)] = never_cull_actor(asset(HEAD_ACTOR))
    elif a.cat_actor:
        rep[sm2_stage.crc64_path(HEAD_ACTOR)] = cat_style_head_actor(asset(CAT_ACTOR), asset(HEAD_ACTOR))
    if a.map_body:
        for p in HERO_ACTORS:
            rep[sm2_stage.crc64_path(p)] = map_body_joints_actor(asset(p))
    if a.blank_prop:
        rep[sm2_stage.crc64_path(P.PROP)] = blank_model(asset(P.PROP))
    suits = a.suit or (json.load(open(os.path.join(REPORTS, 'masked_suits.json')))['models'] if a.masked else T19_SUITS)
    for k, s in enumerate(suits):
        print(f'[{k + 1}/{len(suits)}]', end=' ')
        rep[sm2_stage.crc64_path(s)] = P.strip_body(P.chain_fit(asset, targets, s), mat_path)
    assert a.out or a.delta, 'nothing to write'
    P.write_with(a.base, a.out, rep, a.delta, a.name, a.description)


if __name__ == '__main__':
    main()
