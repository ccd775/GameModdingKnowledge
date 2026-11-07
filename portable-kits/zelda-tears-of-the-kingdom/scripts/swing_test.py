"""v6c offline swing: rotate borrowed cloth bones about their real hinge lines (bphcl fixed particles, game space m)."""
import json, sys, numpy as np
import argparse   # portable kit: --help
_ap = argparse.ArgumentParser(description=__doc__)
_ap.add_argument('out_dir', help='where sw_<case>.json are written when tag is not empty')
_ap.add_argument('head_export', help='TotkMdl export JSON of the built Head model')
_ap.add_argument('tag', nargs='?', default='', help='non-empty: also write the posed JSONs')
_a = _ap.parse_args(); sp, src, tag = _a.out_dir, _a.head_export, _a.tag
def hinge(a, b): a, b = np.array(a), np.array(b); return a, (b - a) / np.linalg.norm(b - a)
H = {  # bone -> (point on hinge line, unit axis); positive angle: Momi swings to +x, Hair_Back swings back (-z)
    'Momi_A_2_L': ((0.100, 1.6055, 0.046), np.array([0, 0, 1.0])), 'Momi_A_2_R': ((-0.100, 1.6055, 0.046), np.array([0, 0, 1.0])),
    'Hair_Back_L': hinge((0.032, 1.553, -0.064), (0.127, 1.545, -0.032)),
    'Hair_Back_R': hinge((-0.126, 1.545, -0.032), (-0.033, 1.553, -0.064)),
}
def R(axis, deg):
    a = np.radians(deg); K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + np.sin(a) * K + (1 - np.cos(a)) * K @ K
CASES = {'rest': (0, 0), 'run25': (0, 25), 'run45': (0, 45), 'stop15': (0, -15), 'side30': (30, 0), 'mix30': (30, 30)}
d0 = json.load(open(src))
def pose(momi, back):
    S = {}
    for b, (p, ax) in H.items():
        ang = momi if b.startswith('Momi') else back
        M = np.eye(4); Rm = R(ax, ang); p = np.array(p); M[:3, :3] = Rm; M[:3, 3] = p - Rm @ p
        for nm in ([b] if b.startswith('Momi') else [b + '_1', b + '_2', b + '_3']): S[nm] = M
    d = json.loads(json.dumps(d0)); out = {}
    for mdl in d['models']:
        for s in mdl['shapes']:
            P = np.c_[np.array(s['pos']), np.ones(len(s['pos']))]; o = np.zeros((len(P), 3))
            for v, (names, ws) in enumerate(zip(s['boneNames'], s['boneWeights'])):
                o[v] = sum(w * ((S[n] @ P[v])[:3] if n in S else P[v, :3]) for n, w in zip(names, ws) if w != 0)
            out[s['name']] = (P[:, :3], o, s); s['pos'] = o.tolist()
        mdl['shapes'] = [s for s in mdl['shapes'] if s['name'] in ('KarinOri_Face', 'KarinOri_Hair', 'KarinOri_HairAcce', 'KarinOri_Neck')]
    return d, out
# metrics: L ear = hair verts with a Hair_Back_L_1 or Momi_A_2_L weight < 0 above 1.70; tip = highest; base = (0.07, 1.688, 0)
d, out = pose(0, 0); P0, _, s = out['KarinOri_Hair']
ear = np.array([any(n in ('Momi_A_2_L', 'Hair_Back_L_1') and w < 0 for n, w in zip(ns, ws)) and P0[i, 1] > 1.70
                for i, (ns, ws) in enumerate(zip(s['boneNames'], s['boneWeights']))])
tip = np.where(ear)[0][np.argmax(P0[ear, 1])]; base = np.array([0.07, 1.688, 0.0])
bang = np.array([any(n.startswith('Momi') and w > 0 for n, w in zip(ns, ws)) and abs(P0[i, 0]) < 0.03 and P0[i, 1] > 1.53
                 for i, (ns, ws) in enumerate(zip(s['boneNames'], s['boneWeights']))])
btip = np.where(bang)[0][np.argmin(P0[bang, 1])] if bang.any() else None
print(f'L ear verts {ear.sum()} tip {P0[tip].round(3)} len0 {np.linalg.norm(P0[tip]-base)*100:.1f} cm; centre-bang verts {bang.sum()}')
for c, (m, b) in CASES.items():
    d, out = pose(m, b); _, P1, _ = out['KarinOri_Hair']
    dt = (P1[tip] - P0[tip]) * 100; dl = (np.linalg.norm(P1[tip] - base) - np.linalg.norm(P0[tip] - base)) * 100
    bt = (P1[btip] - P0[btip]) * 100 if btip is not None else np.zeros(3)
    print(f'{c:7s} momi {m:+3d} back {b:+3d}: ear tip d(x,y,z) {dt.round(1)} cm, length {dl:+.1f} cm | centre bang tip {bt.round(1)}')
    if tag: json.dump(d, open(f'{sp}/sw_{c}.json', 'w'))
