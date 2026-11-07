"""Build Karin_Original -> TotK Armor_1061 (Head / RaulSkin_Upper / Lower) model edits.

Inputs : $TOTK_WORK/src/karin_dump.npz (blender_dump_karin.py), base armor bfres (+ TotkMdl info JSON).
Outputs: edit JSON per model + replaced .bfres.mc via TotkMdl, and a report.
"""
import json, os, sys, math, collections, subprocess
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from retarget import frame_rot, similarity, blend_transform, rot_between
import tk

if __name__ == '__main__':   # portable kit: --help, and check TOTK_WORK before anything is written
    import argparse
    argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter).parse_args()
    tk.need_work()
WORK = os.path.join(tk.WORK_ROOT, 'work', 'build')
os.makedirs(WORK, exist_ok=True)
BASE = {  # base models (03_kalin = ST resave of vanilla 1061 skeleton/materials)
    'Head': os.path.join(tk.WORK_ROOT, 'ref', '03_kalin', 'Model', 'Armor_1061.Armor_1061_Head.bfres'),
    'Upper': os.path.join(tk.WORK_ROOT, 'ref', '03_kalin', 'Model', 'Armor_1061.Armor_1061_RaulSkin_Upper.bfres'),
    'Lower': os.path.join(tk.WORK_ROOT, 'ref', '03_kalin', 'Model', 'Armor_1061.Armor_1061_Lower.bfres'),
}
OUTNAME = {'Head': 'Armor_1061.Armor_1061_Head.bfres.mc', 'Upper': 'Armor_1061.Armor_1061_RaulSkin_Upper.bfres.mc',
           'Lower': 'Armor_1061.Armor_1061_Lower.bfres.mc'}
TEX = {  # material role -> texture name (new names, so they never collide with 03_kalin)
    'face': 'KarinOri_Face_Alb', 'hair': 'KarinOri_Hair_Alb', 'body': 'KarinOri_Body_Alb', 'costume': 'KarinOri_Costume_Alb',
}
NRM, SPM = 'KarinOri_Flat_Nrm', 'KarinOri_Skin_Spm'
S_BODY = 1.38   # uniform scale of Karin's body before per-segment alignment
S_HEAD = 1.40   # head (and everything attached to it) scale. v7: was 1.30, but the per-segment stretch to Link's long
                # torso/neck makes the body's effective scale 1.405 (feet -> Head joint), so the head read ~7% small
APP_REF_S_HEAD = 1.30  # APPENDAGES y0/y1 were tuned at this head scale; rescaled about the Head joint at build time
HEAD_DROP = -0.058  # metres; head geometry sits this far below Link's Head joint. v7b: was -0.04; chin -> shoulder
                    # joint line measured 9.7 cm vs 7.9 cm from Karin's proportions (x1.405), neck read ~1.8 cm long
APP_REF_HEAD_DROP = -0.04  # APPENDAGES y0/y1 were tuned at this drop
# v7c legs: Karin's leg cross-sections came out ~2% under the effective height scale and the thighs are stretched 6%
# longer than her proportions -> read thin. Extra scale perpendicular to the segment (thigh, calf).
LEG_RADIAL = {'UpperLeg': 1.10, 'LowerLeg': 1.06}
# v7c shoulders: the arm pivots are Link's Arm_1 (+-18.3 cm vs Karin's proportional +-10.5) and cannot move (anims drive
# Link's joints; an arm built inward only rides up ~0.94 d when hanging). Arms-down silhouette was ~7 cm/side wider than
# her proportions with a flat, square top (4 cm above the joint: 20.1 vs 10.9 cm half-width). In the bind T-pose the top
# half of the sleeve becomes the OUTER side when the arm hangs, so squash everything above the arm axis toward it
# (shoulder cap + sleeve, torso/arm objects only, hands excluded), ramping in from the neck side.
SHOULDER_SQUASH = 0.5      # remaining fraction of the height above the arm axis
SHOULDER_X0 = 0.05         # |x| (game, m) where the squash starts ramping in; full from Arm_1 x - 0.02
SHOULDER_OBJS = ('Body', 'body_2', 'pullover', 'underwear')
# skirt rig (v3): weights follow Link's Skirt_{1,2,3}_<col>_Armor *segments* (pivot k drives y in [pivot k+1, pivot k]),
# the waistband above Skirt_1's pivot is rigid on Waist; plus a little thigh follow and an in-skirt body shrink.
SK_BLEND = 0.02     # half-width (m) of the linear blend around each skirt pivot
LEG_FOLLOW = 0.45   # Leg_1 weight at the hem (ramps as sqrt from 0 at Skirt_1 pivot)
SK_MARGIN = 0.012   # min clearance (m) kept between body/underwear and the skirt's inner surface in the rest pose
FACE_RIG = True     # v4: fit face shape keys onto Link's face bones (face_rig.py)
BLINK = True        # v5: eye area on signed / amplified eyelid weights (face_rig.fit_blink; float skin weights)
# v6 head appendages: borrow Armor_1061_Head cloth outputs (bphcl: which sim mesh drives which bone, fixed/free particles):
#   Hair_2 cloth -> Momi_A_2_L/R: Link's sideburn strands, fixed at y 1.605, hanging to ~1.38 just in front of the ears
#   Acce_Front   -> Hair_Acce_F_Armor: 2.4 cm pendant fixed at (0, 1.633, 0.146) (forehead)
#   Acce_Side_1  -> Hair_Acce_2_L/R_Armor: 4.4 cm pendant fixed at (+-0.104, 1.586, 0.092) (temple)
#   Earring_3    -> Earrings_2_L/R_Armor: 3.4 cm pendant fixed at (+-0.153, 1.585, -0.043) (v6 ears; dropped in v6b)
# Each borrowed bone is a hanging pendulum whose rotation is about its fixed point. Hanging parts follow it with a
# positive weight; the upright fox ears use a NEGATIVE weight (tip lags on acceleration and leans further when the head
# tilts, like a springy upright appendage; Head gets 1 + g, float skin weights as in v5).
# v6b: LBS of a rotation about a pivot below the ear lengthens it by ~ |g| (1 - cos th) d (stretch / sway ~ tan(th/2)).
# The one-point earring pendants swing ~60 deg (and can spin) -> ears visibly stretched in game; now the two-point-hinged
# Momi sideburn strands (heavier, no spin) at half the gain: ~2.7 cm tip sway / +1 cm at 30 deg, +3.5 cm at 60 deg.
# v6c: cloth bones are driven by particle triangles (bphcl SimpleMeshBoneDeformer). Pendants = 1 fixed + 2 free particles
# = ball joint: free spin about the vertical has no restoring force, so a twisted forehead pendant left the bangs
# flipped up in game. Momi_A_2 = ladder off two fixed points along z = hinge, swings sideways only (ears felt stiff on
# run/stop). Bangs now all on Momi; ears add Hair_Back_L/R_1 (hinge off two fixed points at the nape, axis ~x, swings
# fore-aft; its line passes ~3 cm behind the ear axis, so ~0.28 cm first-order stretch per cm of tip sway).
# v6d: dropped Hair_Back_L/R_1 from the ears again: while running the back hair is swept far back (~60-90 deg) and the
# ears stretched radially in game. Negative-weight LBS scales the ear by ~|1 + g (e^{i th} - 1)|, so any large-swing
# source stretches; ears stay on the sideways Momi hinge only (-0.3).
# (karin bones, link bone, gain, mode, y0, y1): weight = gain * ramp(y), ramp 0 at y0 -> 1 at y1 (game space, m)
APPENDAGES = [
    (('Hair_side_L', 'Hair_side_L_001', 'Hair_side_L_002'), 'Momi_A_2_L', 1.0, 'hang', 1.603, 1.580),  # cheek locks
    (('Hair_side_R', 'Hair_side_R_001', 'Hair_side_R_002'), 'Momi_A_2_R', 1.0, 'hang', 1.603, 1.580),
    (('Hair_front', 'Hair_front_001'), 'Momi_A_2_L', 0.3, 'hang', 1.620, 1.570),                      # centre bangs (v6c)
    (('Hair_front', 'Hair_front_001'), 'Momi_A_2_R', 0.3, 'hang', 1.620, 1.570),
    (('Hair_front_L',), 'Momi_A_2_L', 0.7, 'hang', 1.610, 1.565),                                     # side bangs (v6c)
    (('Hair_front_R',), 'Momi_A_2_R', 0.7, 'hang', 1.610, 1.565),
    (('Ear_L', 'Ear_L_001'), 'Momi_A_2_L', -0.3, 'up', 1.700, 1.865),                                # fox ears: sideways
    (('Ear_R', 'Ear_R_001'), 'Momi_A_2_R', -0.3, 'up', 1.700, 1.865),
]

# ---------------------------------------------------------------- skeleton maps
HUMANOID = {
    'Hips': 'Waist', 'Spine': 'Spine_1', 'Chest': 'Spine_2', 'Neck': 'Neck', 'Head': 'Head',
    'LeftUpperLeg': 'Leg_1_L', 'LeftLowerLeg': 'Leg_2_L', 'LeftFoot': 'Ankle_L', 'LeftToeBase': 'Toe_L',
    'RightUpperLeg': 'Leg_1_R', 'RightLowerLeg': 'Leg_2_R', 'RightFoot': 'Ankle_R', 'RightToeBase': 'Toe_R',
}
for s, l in (('Left', 'L'), ('Right', 'R')):
    HUMANOID.update({f'{s}Shoulder': f'Clavicle_{l}', f'{s}UpperArm': f'Arm_1_{l}', f'{s}LowerArm': f'Arm_2_{l}', f'{s}Hand': f'Wrist_{l}'})
    for kf, lf in (('Thumb', 'A'), ('Index', 'B'), ('Middle', 'C'), ('Ring', 'D'), ('Little', 'E')):
        for kj, lj in (('Proximal', 1), ('Intermediate', 2), ('Distal', 3)):
            HUMANOID[f'{s}{kf}{kj}'] = f'Finger_{lf}_{lj}_{l}'
# child used to define a segment direction (source, target)
SEG_CHILD = {'Hips': ('Spine', None), 'Spine': ('Chest', 'Spine_2'), 'Chest': ('Neck', 'Neck'), 'Neck': ('Head', 'Head')}
for s, l in (('Left', 'L'), ('Right', 'R')):
    SEG_CHILD.update({f'{s}Shoulder': (f'{s}UpperArm', f'Arm_1_{l}'), f'{s}UpperArm': (f'{s}LowerArm', f'Arm_2_{l}'),
                      f'{s}LowerArm': (f'{s}Hand', f'Wrist_{l}'), f'{s}Hand': (f'{s}MiddleProximal', f'Finger_C_1_{l}'),
                      f'{s}UpperLeg': (f'{s}LowerLeg', f'Leg_2_{l}'), f'{s}LowerLeg': (f'{s}Foot', f'Ankle_{l}'),
                      f'{s}Foot': (f'{s}ToeBase', f'Toe_{l}')})
    for kf, lf in (('Thumb', 'A'), ('Index', 'B'), ('Middle', 'C'), ('Ring', 'D'), ('Little', 'E')):
        SEG_CHILD[f'{s}{kf}Proximal'] = (f'{s}{kf}Intermediate', f'Finger_{lf}_2_{l}')
        SEG_CHILD[f'{s}{kf}Intermediate'] = (f'{s}{kf}Distal', f'Finger_{lf}_3_{l}')
STRETCH = {f'{s}{p}' for s in ('Left', 'Right') for p in ('UpperArm', 'LowerArm', 'UpperLeg', 'LowerLeg')} | {'Spine', 'Chest'}

def load_targets():
    mats, infos = {}, {}
    for k, p in BASE.items():
        j = os.path.join(WORK, f'base_{k}.json')
        if not os.path.exists(j): tk.run('info', p, tk.ROMFS_ST, j)
        infos[k] = json.load(open(j, encoding='utf-8'))['models'][0]
        for n, M in tk.world_mats(infos[k]).items():
            mats.setdefault(n, M)
    return mats, infos

# ---------------------------------------------------------------- main
def main():
    D = np.load(os.path.join(tk.WORK_ROOT, 'src', 'karin_dump.npz'))
    meta = json.loads(str(D['meta']))
    KB = meta['bones']; KI = {n: i for i, n in enumerate(KB)}
    kparent = D['bone_parent']
    kmat = D['bone_mats'].astype(np.float64)
    kpos = kmat[:, :3, 3]
    LW, infos = load_targets()
    lpos = {n: M[:3, 3] for n, M in LW.items()}
    for n in list(lpos):  # right-hand fingers live in Link's separate right-hand model: mirror the left ones
        if n.endswith('_L') and n[:-2] + '_R' not in lpos:
            p = lpos[n].copy(); p[0] = -p[0]; lpos[n[:-2] + '_R'] = p

    # ---- per Karin bone similarity transforms
    def humanoid_anchor(i):
        while i >= 0 and KB[i] not in HUMANOID: i = kparent[i]
        return i
    T = np.zeros((len(KB), 4, 4))
    fwd = np.array([0, 0, 1.0]); up = np.array([0, 1.0, 0])
    for n, ln in HUMANOID.items():
        i = KI[n]
        ps, pd = kpos[i], lpos[ln]
        s = S_HEAD if n in ('Head',) else S_BODY
        ch = SEG_CHILD.get(n)
        if ch and ch[1] is not None:
            ds = kpos[KI[ch[0]]] - ps; dd = lpos[ch[1]] - pd
        elif n == 'Hips':
            ds = kpos[KI['Spine']] - ps; dd = lpos['Spine_2'] - lpos['Spine_1']
        else:  # leaves: Head, distal fingers, toes -> continue parent's direction
            par = kparent[i]; ds = ps - kpos[par]
            pl = HUMANOID.get(KB[par]); dd = pd - lpos[pl] if pl else ds
        is_finger = any(k in n for k in ('Thumb', 'Index', 'Middle', 'Ring', 'Little'))
        if n in ('Hips', 'Spine', 'Chest', 'Neck', 'Head'):
            R = frame_rot(ds, fwd, dd, fwd)
            if n == 'Head': R = np.eye(3)  # keep the face upright as authored
        elif is_finger or n.endswith('Hand'):
            R = frame_rot(ds, up, dd, up)
        else:
            R = frame_rot(ds, fwd, dd, fwd)
        stretch, sdir, radial = 1.0, None, LEG_RADIAL.get(n.replace('Left', '').replace('Right', ''), 1.0)
        if n in STRETCH and ch and ch[1] is not None:
            stretch = float(np.clip(np.linalg.norm(dd) / (s * np.linalg.norm(ds)), 0.75, 1.35)); sdir = ds
        if n == 'Head': pd = pd + np.array([0, HEAD_DROP, 0])  # Link's neck is long; seat the head lower
        if radial != 1.0 and sdir is None: sdir = ds
        T[i] = similarity(ps, pd, R, s, sdir, stretch, radial)
    for i in range(len(KB)):
        if KB[i] not in HUMANOID:
            a = humanoid_anchor(i)
            T[i] = T[a] if a >= 0 else np.eye(4)

    pos, nrm = D['pos'].astype(np.float64), D['nrm'].astype(np.float64)
    w_idx, w_val = D['w_idx'], D['w_val']
    new_pos, new_nrm = blend_transform(pos, nrm, w_idx, w_val, T)

    # ---- v7c shoulder squash (see SHOULDER_*): above Link's arm axis, scale height toward it
    objs_ = [o if isinstance(o, str) else o.get('name') for o in meta['objects']]
    vobj_ = np.full(len(pos), -1)
    for a, b, c, _mi, oi in D['tris']: vobj_[[a, b, c]] = oi
    okobj = np.isin(vobj_, [objs_.index(o) for o in SHOULDER_OBJS])
    hand_ids = {i for i, n in enumerate(KB) if any(k in n for k in ('Hand', 'Thumb', 'Index', 'Middle', 'Ring', 'Little'))}
    hand_m = np.array([sum(float(w) for i, w in zip(w_idx[v], w_val[v]) if i in hand_ids) for v in range(len(pos))])
    head_ids = {KI['Neck'], KI['Head']}; ch = True                 # Neck/Head subtree (face, hair, ears) is never squashed
    while ch:
        ch = False
        for i in range(len(KB)):
            if kparent[i] in head_ids and i not in head_ids: head_ids.add(i); ch = True
    head_m = np.array([sum(float(w) for i, w in zip(w_idx[v], w_val[v]) if i in head_ids) for v in range(len(pos))])
    ax_y = lpos['Arm_1_L'][1]; x1 = lpos['Arm_1_L'][0] - 0.02
    t = np.clip((np.abs(new_pos[:, 0]) - SHOULDER_X0) / (x1 - SHOULDER_X0), 0, 1); t = t * t * (3 - 2 * t)
    g = t * (1 - np.clip(hand_m + head_m, 0, 1)) * okobj * (new_pos[:, 1] > ax_y)
    k = 1 - (1 - SHOULDER_SQUASH) * g
    new_pos[:, 1] = ax_y + (new_pos[:, 1] - ax_y) * k
    new_nrm[:, 1] /= k; new_nrm /= np.linalg.norm(new_nrm, axis=1, keepdims=True)   # inverse-transpose of the squash
    print(f'shoulder squash: {int((g > 0.01).sum())} verts (axis y {ax_y:.3f}, ramp |x| {SHOULDER_X0}..{x1:.3f})')
    json.dump({KB[i]: (T[i] @ np.append(kpos[i], 1.0))[:3].round(5).tolist() for i in range(len(KB))},
              open(os.path.join(WORK, 'karin_bones_game.json'), 'w'), indent=0)  # Karin joints in game space (rig design)

    # ---- weights -> Link bones
    # physics chains
    def chain(prefix_list):
        return {n: k for k, n in enumerate(prefix_list)}
    tailL = chain(['Hair_tail_L'] + [f'Hair_tail_L_00{k}' for k in range(1, 6)])
    tailR = chain(['Hair_tail_R'] + [f'Hair_tail_R_00{k}' for k in range(1, 6)])
    animal_tail = chain(['Tail'] + [f'Tail_00{k}' for k in range(1, 6)])
    CHAINS = [  # (karin chain, karin length, link bones)
        (tailL, 6, ['Hair_Back_L_1', 'Hair_Back_L_2', 'Hair_Back_L_3']),
        (tailR, 6, ['Hair_Back_R_1', 'Hair_Back_R_2', 'Hair_Back_R_3']),
        # v6: side (cheek) locks moved off Hair_Side_A/B (behind the ears, weak) onto Momi_A_2 (APPENDAGES)
        (animal_tail, 6, ['Skirt_1_BC_Armor', 'Skirt_2_BC_Armor', 'Skirt_3_BC_Armor']),
    ]
    # skirt columns by azimuth
    link_cols = ['FC', 'FL', 'L', 'BL', 'BC', 'BR', 'R', 'FR']
    waist = lpos['Waist']
    def az(p, c): return math.degrees(math.atan2(p[0] - c[0], p[2] - c[2])) % 360
    link_az = {c: az(lpos[f'Skirt_1_{c}_Armor'], waist) for c in link_cols}
    hips_k = kpos[KI['Hips']]
    skirt_map = {}  # karin bone -> list[(link bone, w)]
    karin_cols = ['Skirt_0'] + [f'Skirt_{k}_{s}' for k in range(1, 8) for s in ('L', 'R')] + ['Skirt_8']
    for col in karin_cols:
        a = az(kpos[KI[col]], hips_k)
        dists = sorted(((abs((a - link_az[c] + 180) % 360 - 180), c) for c in link_cols))
        (d0, c0), (d1, c1) = dists[0], dists[1]
        w0 = d1 / (d0 + d1) if d0 + d1 > 1e-6 else 1.0
        for lvl, nm in enumerate([col, col + '_001', col + '_002']):
            skirt_map[nm] = [(f'Skirt_{lvl + 1}_{c0}_Armor', w0), (f'Skirt_{lvl + 1}_{c1}_Armor', 1 - w0)]
    skirt_map['Skirt_root'] = [('Waist', 1.0)]

    RIGID = {}  # remaining non-humanoid karin bones -> link bone
    for n in KB:
        if n in HUMANOID or n in skirt_map or any(n in c[0] for c in CHAINS): continue
        a = humanoid_anchor(KI[n])
        RIGID[n] = HUMANOID[KB[a]] if a >= 0 else 'Waist'
    RIGID.update({'Ribbon_hand_R_root': 'Wrist_R', 'Ribbon_hand_R_1': 'Wrist_R', 'Ribbon_hand_R_2': 'Wrist_R'})

    def link_weights(v):
        acc = collections.defaultdict(float)
        chain_acc = {}
        for i, w in zip(w_idx[v], w_val[v]):
            if i < 0 or w <= 0: continue
            n = KB[i]
            if n in HUMANOID: acc[HUMANOID[n]] += w; continue
            if n in skirt_map:
                for ln, f in skirt_map[n]: acc[ln] += w * f
                continue
            hit = False
            for ci, (cm, clen, lbones) in enumerate(CHAINS):
                if n in cm:
                    a = chain_acc.setdefault(ci, [0.0, 0.0]); a[0] += w; a[1] += w * cm[n]; hit = True; break
            if hit: continue
            acc[RIGID.get(n, 'Waist')] += w
        for ci, (W, J) in chain_acc.items():
            cm, clen, lbones = CHAINS[ci]
            u = (J / W) / max(clen - 1, 1) * (len(lbones) - 1)
            k0 = int(min(math.floor(u), len(lbones) - 2)); f = u - k0
            acc[lbones[k0]] += W * (1 - f); acc[lbones[k0 + 1]] += W * f
        return acc

    # forearm / shin twist split using the assist bones (helpers driven by the game)
    def twist(acc, p):
        for l in ('L', 'R'):
            w = acc.get(f'Arm_2_{l}', 0)
            if w > 0:
                a, b = lpos[f'Arm_2_{l}'], lpos[f'Wrist_{l}']
                t = float(np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1))
                acc[f'Arm_2_{l}'] = w * (1 - t); acc[f'Wrist_Assist_{l}'] = acc.get(f'Wrist_Assist_{l}', 0) + w * t
            w = acc.get(f'Leg_2_{l}', 0)
            if w > 0:
                a, b = lpos[f'Leg_2_{l}'], lpos[f'Ankle_{l}']
                t = float(np.clip(np.dot(p - a, b - a) / np.dot(b - a, b - a), 0, 1)) ** 2
                acc[f'Leg_2_{l}'] = w * (1 - t * 0.6); acc[f'Ankle_Assist_{l}'] = acc.get(f'Ankle_Assist_{l}', 0) + w * t * 0.6
        return acc

    nv = len(pos)
    LWts = [twist(link_weights(v), new_pos[v]) for v in range(nv)]

    # ---- v6 head appendages (see APPENDAGES): the Karin weight mass on each group (mapped rigidly to Head above) is
    # re-split between Head and the borrowed cloth bone by the vertex's height
    app_stats = collections.Counter()
    gidx = [{KI[n] for n in bones} for bones, *_ in APPENDAGES]
    yh = float((T[KI['Head']] @ np.append(kpos[KI['Head']], 1.0))[1])        # head scale pivot (game y)
    yh_ref = yh - (HEAD_DROP - APP_REF_HEAD_DROP)                              # head joint y when APPENDAGES were tuned
    rs = lambda y: yh + (y - yh_ref) * S_HEAD / APP_REF_S_HEAD
    app = [(b, lb, g, md, rs(y0), rs(y1)) for b, lb, g, md, y0, y1 in APPENDAGES]
    print('appendage ramps (game y):', [(lb, round(y0, 3), round(y1, 3)) for _b, lb, _g, _m, y0, y1 in app])
    for v in range(nv):
        for gi, (bones, lbone, gain, _mode, y0, y1) in enumerate(app):
            m = sum(float(w) for i, w in zip(w_idx[v], w_val[v]) if i in gidx[gi] and w > 0)
            if m <= 0: continue
            t = float(np.clip((new_pos[v, 1] - y0) / (y1 - y0), 0, 1))
            t = t * t * (3 - 2 * t)                     # smoothstep
            f = gain * t
            if f == 0: continue
            acc = LWts[v]
            acc['Head'] = acc.get('Head', 0) - m * f
            acc[lbone] = acc.get(lbone, 0) + m * f
            app_stats[lbone] += 1
    print('appendages (verts per borrowed bone):', dict(app_stats))

    # ---- v3 skirt rig + in-skirt shrink (see SK_* constants)
    objs = meta['objects']
    vobj = np.full(nv, -1)
    for a, b, c, mi, oi in D['tris']: vobj[[a, b, c]] = oi
    sk_v = np.where(vobj == objs.index('skirt'))[0]
    sk_p = new_pos[sk_v]
    hem, sk_top = float(sk_p[:, 1].min()), float(sk_p[:, 1].max())
    piv = {c: [float(lpos[f'Skirt_{k}_{c}_Armor'][1]) for k in (1, 2, 3)] for c in link_cols}
    p0_avg = float(np.mean([piv[c][0] for c in link_cols]))

    def chain_weights(y, col):
        bones = ['Waist'] + [f'Skirt_{k}_{col}_Armor' for k in (1, 2, 3)]
        ps = piv[col]
        for k, pk in enumerate(ps):          # blend zones around each pivot
            if abs(y - pk) < SK_BLEND:
                t = (pk + SK_BLEND - y) / (2 * SK_BLEND)
                return {bones[k]: 1 - t, bones[k + 1]: t}
        r = sum(1 for pk in ps if y < pk)    # segment index: 0 above pivot 1 ... 3 below pivot 3
        return {bones[r]: 1.0}

    def col_split(p):
        a = az(p, waist)
        (d0, c0), (d1, c1) = sorted(((abs((a - link_az[c] + 180) % 360 - 180), c) for c in link_cols))[:2]
        return a, c0, c1, (d1 / (d0 + d1) if d0 + d1 > 1e-6 else 1.0)

    for v in sk_v:
        p = new_pos[v]; y = float(p[1])
        a, c0, c1, w0 = col_split(p)
        acc = collections.defaultdict(float)
        for c, wc in ((c0, w0), (c1, 1 - w0)):
            for n, w in chain_weights(y, c).items(): acc[n] += wc * w
        lf = LEG_FOLLOW * float(np.clip((p0_avg - y) / max(p0_avg - hem, 1e-3), 0, 1)) ** 0.5
        if lf > 0:
            fl = 0.5 + 0.5 * math.sin(math.radians(a))   # +x (azimuth 90) is Link's left
            for n in list(acc): acc[n] *= 1 - lf
            acc['Leg_1_L'] += lf * fl; acc['Leg_1_R'] += lf * (1 - fl)
        LWts[v] = acc

    # body / underwear pressing against the skirt from inside: pull radially (about Waist's vertical axis) to keep SK_MARGIN
    wall = np.abs(new_nrm[sk_v][:, 1]) < 0.7          # skip horizontal caps (e.g. the waistband's top fan, r ~ 2 cm)
    sk_p = sk_p[wall]
    sk_r = np.hypot(sk_p[:, 0] - waist[0], sk_p[:, 2] - waist[2])
    sk_a = np.degrees(np.arctan2(sk_p[:, 0] - waist[0], sk_p[:, 2] - waist[2]))
    shrink_oi = {objs.index('body_2'), objs.index('underwear')}
    moved = []
    for v in np.where(np.isin(vobj, list(shrink_oi)))[0]:
        p = new_pos[v]
        if not (hem - 0.005 < p[1] < sk_top): continue
        da = np.abs((sk_a - math.degrees(math.atan2(p[0] - waist[0], p[2] - waist[2])) + 180) % 360 - 180)
        near = (np.abs(sk_p[:, 1] - p[1]) < 0.015) & (da < 12)
        if not near.any(): continue
        rn = sk_r[near]; rn = rn[rn > 0.6 * np.median(rn)]
        lim = float(rn.min()) - SK_MARGIN
        r0 = math.hypot(p[0] - waist[0], p[2] - waist[2])
        lim = max(lim, r0 - 0.03)                       # never pull more than 3 cm
        r = math.hypot(p[0] - waist[0], p[2] - waist[2])
        if r > lim and r > 1e-6:
            f = max(lim, 0.0) / r
            new_pos[v, 0] = waist[0] + (p[0] - waist[0]) * f; new_pos[v, 2] = waist[2] + (p[2] - waist[2]) * f
            moved.append(r - lim)
    print(f'skirt v3: {len(sk_v)} skirt verts, hem {hem:.3f} top {sk_top:.3f}; shrunk {len(moved)} body verts, '
          f'max {max(moved, default=0) * 100:.1f} cm, mean {np.mean(moved) * 100 if moved else 0:.1f} cm')

    # ---- v4 face rig: Karin's shape keys fitted onto Link's face bones (driven by TotK's Face_* / Voice_* anims)
    if FACE_RIG:
        import face_rig
        SK = np.load(os.path.join(tk.WORK_ROOT, 'src', 'karin_shapekeys.npz'))
        sk_names = json.loads(str(SK['names'])); sk_idx = SK['idx']; sk_d = SK['deltas'].astype(np.float64)
        face_mask = np.zeros(nv, bool)
        fi = objs.index('Body')
        for a, b, c, mi, oi in D['tris']:
            if oi == fi and meta['materials'][mi] != 'Karin_Alpha': face_mask[[a, b, c]] = True
        sel = np.where(face_mask[sk_idx])[0]              # rows of the shape-key arrays that are drawn face verts
        fv = sk_idx[sel]
        pl = face_rig.poses()
        def to_game(delta):                                  # same per-vertex retarget transform as the geometry
            moved_p, _ = blend_transform(pos[fv] + delta, nrm[fv], w_idx[fv], w_val[fv], T)
            return moved_p - new_pos[fv]
        targets = []
        for an, t, tgt, lam, S in pl:
            d = np.zeros((len(fv), 3))
            for k, coef in tgt.items(): d += coef * sk_d[sk_names.index(k)][sel]
            targets.append(to_game(d))
        eye = np.zeros(len(fv), bool)
        for k in face_rig.EYE_KEYS:
            if k in sk_names: eye |= np.linalg.norm(sk_d[sk_names.index(k)][sel], axis=1) > 1e-4
        # position groups (UV-seam duplicates share one weight set) + triangle adjacency between groups
        gkey = {}; grp = np.array([gkey.setdefault(tuple(np.round(p * 1e5).astype(int)), len(gkey)) for p in new_pos[fv]])
        ng = len(gkey); row_of = {int(v): i for i, v in enumerate(fv)}
        nb = [set() for _ in range(ng)]
        for a, b, c, mi, oi in D['tris']:
            if oi != fi or a not in row_of or b not in row_of or c not in row_of: continue
            ga, gb, gc = grp[row_of[a]], grp[row_of[b]], grp[row_of[c]]
            nb[ga] |= {gb, gc}; nb[gb] |= {ga, gc}; nb[gc] |= {ga, gb}
        first = {}
        for i, g in enumerate(grp): first.setdefault(g, i)
        rep = np.array([first[g] for g in range(ng)])
        gfrozen = np.zeros(ng, bool)
        for i, g in enumerate(grp): gfrozen[g] |= eye[i]
        adjg = [np.array(sorted(s - {g})) for g, s in enumerate(nb)]
        FWg = face_rig.fit(new_pos[fv][rep], [t[rep] for t in targets], pl, LW, frozen=gfrozen)
        FWg = face_rig.smooth(FWg, adjg, gfrozen)
        print(f'face rig: eye-area verts {int(eye.sum())}, position groups {ng}')
        if BLINK:  # v5: eye area -> signed eyelid weights (float _w0 on the face shape)
            Pg = new_pos[fv][rep]; Tg = to_game(sk_d[sk_names.index(face_rig.BLINK_KEY)][sel])[rep]
            eg = np.where(gfrozen)[0]
            lid_poses = face_rig.eyelid_poses()
            BW = face_rig.fit_blink(Pg, Tg, eg, adjg, poses=lid_poses)
            for g, d in BW.items(): FWg[g] = d
            print(f'blink: {len(BW)} of {len(eg)} eye-area groups on eyelid bones ({len(lid_poses)} eyelid poses);',
                  face_rig.blink_report(Pg, Tg, BW))
            print('blink: other poses', face_rig.other_pose_report(Pg, Tg, BW, lid_poses))
            np.savez_compressed(os.path.join(WORK, 'blink_fit.npz'), P=Pg, T=Tg, eg=eg,
                                adj=np.array(json.dumps([a.tolist() for a in adjg])), weights=json.dumps({int(k): v for k, v in BW.items()}))
        FW = [FWg[g] for g in grp]
        for v, d in zip(fv, FW):
            if not d: continue
            s = sum(d.values()); acc = LWts[v]
            for n in list(acc): acc[n] *= 1 - s
            for n, w in d.items(): acc[n] = acc.get(n, 0) + w
        nrig = sum(1 for d in FW if d)
        print(f'face rig: {len(fv)} face verts, {nrig} weighted to face bones')
        for an, t, tmean, emean, tmaxx in face_rig.residual_report(new_pos[fv], targets, pl, FW):
            print(f'   {an:22s} f{t:<3d} target mean {tmean:.2f} cm (max {tmaxx:.2f}) -> residual mean {emean:.2f} cm')
        np.savez_compressed(os.path.join(WORK, 'face_fit.npz'), fv=fv, P=new_pos[fv],
                            targets=np.array(targets), weights=json.dumps(FW))

    # ---- partition triangles into model/shape buckets
    objs, mats = meta['objects'], meta['materials']
    LOWER_BONES = {'Leg_1_L', 'Leg_2_L', 'Ankle_L', 'Toe_L', 'Leg_1_R', 'Leg_2_R', 'Ankle_R', 'Toe_R', 'Knee_L', 'Knee_R',
                   'Ankle_Assist_L', 'Ankle_Assist_R'}
    RIGHT_HAND = {n for n in HUMANOID.values() if n.startswith('Finger_') and n.endswith('_R')} | {'Wrist_R'}
    buckets = collections.defaultdict(list)
    dropped = collections.Counter()
    for a, b, c, mi, oi in D['tris']:
        on, mn = objs[oi], mats[mi]
        if mn == 'Karin_Alpha': dropped['alpha_overlay'] += 1; continue
        vs = (a, b, c)
        # right hand: the game draws Link's own right hand (separate model); drop Karin's
        rh = sum(sum(LWts[v].get(n, 0) for n in RIGHT_HAND) for v in vs) / 3
        if rh > 0.5 and on in ('body_2',): dropped['right_hand'] += 1; continue
        if on in ('Body',): key = ('Head', 'face')
        elif on in ('hair', 'kemomimi'): key = ('Head', 'costume' if mn == 'Karin_Costume' else 'hair')
        else:
            low = sum(sum(w for n, w in LWts[v].items() if n in LOWER_BONES) for v in vs) / 3
            model = 'Lower' if (low > 0.5 and on not in ('skirt', 'tail')) else 'Upper'
            role = 'body' if mn == 'Karin_Body' else ('hair' if mn == 'Karin_Hair' else 'costume')
            if on == 'body_2' and model == 'Upper':
                head_w = sum(LWts[v].get('Head', 0) for v in vs) / 3
                if head_w > 0.5: key = ('Head', 'body')
                else: key = (model, role)
            else:
                key = (model, role)
        buckets[key].append((a, b, c))
    print('buckets', {k: len(v) for k, v in buckets.items()}, 'dropped', dict(dropped))

    SHAPES = {  # (model, role) -> (shape name, material slot, texture)
        ('Head', 'face'): ('KarinOri_Face', 'Mt_Head_1061', TEX['face']),
        ('Head', 'hair'): ('KarinOri_Hair', 'Mt_Head_Paint_1061', TEX['hair']),
        ('Head', 'costume'): ('KarinOri_HairAcce', 'Mt_Head_Tekari_1061', TEX['costume']),
        ('Head', 'body'): ('KarinOri_Neck', 'Mt_Upper_Skin', TEX['body']),
        ('Upper', 'body'): ('KarinOri_Body', 'Mt_Upper_Skin_0', TEX['body']),
        ('Upper', 'costume'): ('KarinOri_Clothes', 'Mt_Upper_L_1061', TEX['costume']),
        ('Upper', 'hair'): ('KarinOri_Tail', 'Mt_Upper_R_1061', TEX['hair']),
        ('Lower', 'body'): ('KarinOri_Legs', 'Mt_Upper_Skin', TEX['body']),
        ('Lower', 'costume'): ('KarinOri_Socks', 'Mt_Lower_1061', TEX['costume']),
    }
    DYE_BOUND_MATS = {'Mt_Head_1061', 'Mt_Head_Paint_1061', 'Mt_Upper_L_1061', 'Mt_Upper_Acce_L_1061', 'Mt_Upper_R_1061',
                      'Mt_Upper_Acce_R_1061', 'Mt_Hair_1061', 'Mt_Lower_1061', 'Mt_Face'}
    SKIN_SRC = {'Head': 'Mt_Upper_Skin', 'Upper': 'Mt_Upper_Skin_0', 'Lower': 'Mt_Upper_Skin'}
    TEMPLATE = {'Head': 'Scene.003', 'Upper': 'Scene.009_0', 'Lower': 'Scene.012'}
    report = {}
    for model in ('Head', 'Upper', 'Lower'):
        info = infos[model]
        bone_names = {b['name'] for b in info['bones']}
        edit = {'delete': [s['name'] for s in info['shapes'] if s['name'] != TEMPLATE[model]],
                'copyMaterials': {}, 'samplerTextures': {}, 'newShapes': [], 'shapes': {}}
        used_bones = set()
        first = True
        for (m, role), tris in sorted(buckets.items()):
            if m != model: continue
            sname, mat, tex = SHAPES[(m, role)]
            if mat != SKIN_SRC[model]: edit['copyMaterials'][mat] = SKIN_SRC[model]
            edit['samplerTextures'][mat] = {'_a0': tex, '_n0': NRM, '_s0': SPM}
            tris = np.array(tris)
            uniq, inv = np.unique(tris.ravel(), return_inverse=True)
            bones, weights = [], []
            signed = False
            for v in uniq:
                acc = {n: w for n, w in LWts[v].items() if abs(w) > 1e-4}
                missing = [n for n in acc if n not in bone_names]
                for n in missing:  # fall back to the parent chain inside this model
                    w = acc.pop(n); fb = 'Head' if model == 'Head' else ('Waist' if model == 'Lower' else 'Spine_2')
                    acc[fb] = acc.get(fb, 0) + w
                items = sorted(acc.items(), key=lambda kv: -abs(kv[1]))[:4]
                if any(w < 0 or w > 1 for _, w in items):
                    # signed blink weights (v5): no renormalisation; round, then put the rounding remainder on the
                    # largest-magnitude weight so the sum is exactly 1 (the rest pose depends on it at |w| ~ 10)
                    signed = True
                    ws = [round(float(w), 6) for _, w in items]
                    ws[0] = round(ws[0] + 1.0 - sum(ws), 6)
                else:
                    tot = sum(w for _, w in items) or 1
                    ws = [round(float(w) / float(tot), 5) for _, w in items]
                bones.append([n for n, _ in items]); weights.append(ws)
                used_bones.update(n for n, _ in items)
            P = new_pos[uniq]; N = new_nrm[uniq]; UV = D['uv'][uniq].astype(np.float64).copy()
            UV[:, 1] = 1.0 - UV[:, 1]  # Blender UV (origin bottom-left) -> BFRES (origin top-left)
            shp = {'pos': np.round(P, 6).ravel().tolist(), 'nrm': np.round(N, 5).ravel().tolist(), 'uv0': np.round(UV, 6).ravel().tolist(),
                   'bones': bones, 'weights': weights, 'faces': inv.astype(int).tolist()}
            if signed:  # vanilla 8_8_8_8_UNorm can't hold w < 0 or > 1
                shp['weightFormat'] = 'Format_32_32_32_32_Single'
                report[f'{model}/{sname}/weightFormat'] = shp['weightFormat']
            target = sname
            if first:  # reuse the template shape for the first bucket (keeps a valid vertex buffer layout)
                edit['delete'] = [s['name'] for s in info['shapes'] if s['name'] != TEMPLATE[model]]
                edit.setdefault('rename', {})[TEMPLATE[model]] = sname
                target = TEMPLATE[model]
                # shape keeps the template's material; point it at this bucket's material
                edit['shapeMaterial'] = {TEMPLATE[model]: mat}
                first = False
            else:
                edit['newShapes'].append({'name': sname, 'template': TEMPLATE[model], 'material': mat})
            edit['shapes'][target] = shp
            report[f'{model}/{sname}'] = {'verts': int(len(uniq)), 'tris': int(len(tris)), 'material': mat, 'texture': tex}
        edit['smoothBones'] = sorted(used_bones)
        report[f'{model}/smoothBones'] = sorted(used_bones)
        # Model/Armor_1061.anim.bfres.zs plays Head/Upper/Lower_ftp (dye texture pattern, frame 0 = undyed) on these
        # material names and rewrites their _a0 to Armor_1061_{Upper,Lower}_Alb.<dye>; rename ours so it can't bind.
        edit['renameMaterials'] = {mat: 'Mt_' + sname for (m, _), (sname, mat, _) in SHAPES.items()
                                   if m == model and mat in DYE_BOUND_MATS}
        report[f'{model}/renameMaterials'] = edit['renameMaterials']
        ep = os.path.join(WORK, f'edit_{model}.json')
        json.dump(edit, open(ep, 'w'))
        out = os.path.join(WORK, 'out', OUTNAME[model])
        os.makedirs(os.path.dirname(out), exist_ok=True)
        log = tk.run('replace', BASE[model], tk.ROMFS_ST, ep, out)
        open(os.path.join(WORK, f'log_{model}.txt'), 'w', encoding='utf-8').write(log)
        print(model, 'ok', os.path.getsize(out))
    json.dump(report, open(os.path.join(WORK, 'report.json'), 'w'), indent=1)
    print(json.dumps({k: v for k, v in report.items() if 'smooth' not in k}, indent=1))

if __name__ == '__main__':
    main()
