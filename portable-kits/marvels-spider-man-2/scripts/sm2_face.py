"""T7 expressions: Karin's face skinned to the facial rig of the SM2 unmasked head models.

  python sm2_face.py --family peter|miles|young [--render]     # -> Work/build_face/<family>/face.npz (+ png)

The unmasked heads (hero_peterparker_head, hero_milesmorales_head, hero_peterparker_young_head) carry ~500
FACIAL_* joints that dialogue / cutscene animation drives. Karin's face goes into the head model; every face
vertex copies the skin weights of the nearest original-head vertices of the same region (upper / lower eyelid,
upper / lower lip, brow, tongue) after a landmark warp of Karin's face onto the original one; irises follow the
*_EyeParallel joints. How much of that motion a vertex takes (alpha) comes from Karin's own blendshapes: what her
blink / mouth / brow / tongue shapes never move stays rigid on 'head' (anime faces only deform there).

Placement: the face of the family's reference fit (Work/build_sig/<sig>/karin_geo.npz of the reference suit) in
that suit's head-joint frame, re-expressed in the head model's bind pose through its own head joint.
"""
import argparse, json, os, struct, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M                   # noqa: E402
import sm2_build_model as SB            # noqa: E402
import vrm as vrmmod                    # noqa: E402
from sm2_fit import TPS                 # noqa: E402
from sm2_karin_geo import WORK, vrm_path   # noqa: E402
from sm2_common import load_index, load_toc, extract, REPORTS   # noqa: E402

FAMILIES = {   # head model, reference suit (its fit fixes Karin's head in the head-joint frame)
    'peter': ('characters/hero/hero_peterparker/head/hero_peterparker_head.model',
              'characters/hero/hero_spiderman_advanced/hero_spiderman_advanced.model'),
    'miles': ('characters/hero/hero_milesmorales/head/hero_milesmorales_head.model',
              'characters/hero/hero_spiderman_miles_updated/hero_spiderman_miles_updated.model'),
    'young': ('characters/hero/hero_peterparker_young/head/hero_peterparker_young_head.model',
              'characters/hero/hero_peterparker_young/hero_peterparker_young.model'),
}
GAZE = 0.6          # iris share on *_EyeParallel (Karin's own LookLeft moves the iris ~6 mm; game gaze is larger)
LIDS = False        # eyelids on the rig: off. The original lid joints travel ~1 cm, Karin's anime lids need ~4 cm;
                    # transferred weights give a torn half-blink (build_face/*/poses.png), static eyes look better
SHAPES = {'blink': 'blink', 'mouth': 'kuchi_A', 'tongue': 'bero_be-', 'brow': 'mayu_up', 'smile': 'kuchi_smile_1'}
PETER_CLASS = {   # region -> joint-name fragments of the original head's dominant joints
    'lidUp': ('EyelidUpper',), 'lidLo': ('EyelidLower', 'EyesackLower'), 'brow': ('Forehead',),
    'lipUp': ('LipUpper', 'MouthUpper', 'LipCorner'), 'lipLo': ('LipLower', 'MouthLower', 'Chin', 'LipCorner'),
    'tongue': ('Tongue',),
}
SIDED = ('lidUp', 'lidLo', 'brow')


def family_of(path):
    n = path.split('/')[2]
    if 'young' in n:
        return 'young'
    return 'miles' if 'miles' in n else 'peter'


# ------------------------------------------------------------------ Karin side
def karin_face(v):
    """-> dict(P (VRM bind), T, UV, eyeL/eyeR weights, deltas {key: (n,3)}) of the Karin_Face primitive"""
    ni = [i for i, nd in v.mesh_nodes() if nd.get('name') == 'Body'][0]
    mesh = v.js['meshes'][v.nodes[ni]['mesh']]
    names = mesh['extras']['targetNames']
    k = [i for i, pr in enumerate(mesh['primitives']) if v.js['materials'][pr['material']]['name'] == 'Karin_Face'][0]
    prim = [p for p in v.primitives() if p['node'] == ni and p['prim'] == k][0]
    pr = mesh['primitives'][k]
    eye = {}
    for side, bone in (('L', 'leftEye'), ('R', 'rightEye')):
        node = v.human[bone]
        eye[side] = np.where(prim['joints'] == node, prim['weights'], 0).sum(1)
    D = {key: v.accessor(pr['targets'][names.index(n)]['POSITION']) for key, n in SHAPES.items()}
    return dict(P=prim['pos'], T=prim['tris'], UV=prim['uv'], eye=eye, D=D)


def classify(kf):
    """-> (cls [n] str, alpha [n]) in VRM space"""
    P, D = kf['P'], kf['D']
    n = len(P)
    cls = np.array(['other'] * n, dtype=object)
    alpha = np.zeros(n)
    mag = {k: np.linalg.norm(d, axis=1) for k, d in D.items()}
    mx = {k: m.max() for k, m in mag.items()}
    mouth = mag['mouth'] > 0.1 * mx['mouth']
    cls[mouth] = np.where(D['mouth'][mouth, 1] < 0, 'lipLo', 'lipUp')
    alpha[mouth] = np.clip(mag['mouth'][mouth] / (0.5 * mx['mouth']), 0, 1)
    brow = mag['brow'] > 0.2 * mx['brow']
    cls[brow] = 'brow'
    alpha[brow] = 1.0
    if LIDS:
        lid = (mag['blink'] > 0.1 * mx['blink']) & ~brow
        cls[lid] = np.where(D['blink'][lid, 1] < 0, 'lidUp', 'lidLo')
        alpha[lid] = np.clip(mag['blink'][lid] / (0.5 * mx['blink']), 0, 1)
    tongue = mag['tongue'] > 0.2 * mx['tongue']
    cls[tongue] = 'tongue'
    alpha[tongue] = 1.0
    for side in ('L', 'R'):
        e = kf['eye'][side] > 0          # VRM binds the irises 0.3 eye bone + 0.7 head
        cls[e] = 'eye' + side
        alpha[e] = GAZE
    return cls, alpha


def smooth(alpha, T, cls, it=2):
    """average alpha over triangle neighbours inside the same region (softens the alpha edge, keeps regions apart)"""
    n = len(alpha)
    for _ in range(it):
        acc = np.zeros(n)
        cnt = np.zeros(n)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            i, j = T[:, a], T[:, b]
            same = cls[i] == cls[j]
            np.add.at(acc, i[same], alpha[j[same]]); np.add.at(cnt, i[same], 1)
            np.add.at(acc, j[same], alpha[i[same]]); np.add.at(cnt, j[same], 1)
        alpha = np.where(cnt > 0, 0.5 * alpha + 0.5 * acc / np.maximum(cnt, 1), alpha)
    return alpha


# ------------------------------------------------------------------ head model side
class Head:
    def __init__(self, raw):
        self.raw = raw
        self.m = m = M.Model(raw)
        self.names = [j['name'] for j in m.joints]
        self.ix = {n: i for i, n in enumerate(self.names)}
        self.W = m.joint_world()
        lk = SB.looks(m)
        look = lk.get('head') or lk['Default']
        mats = [m.materials[m.meshes[i].material & 0xFFFF][0].lower() for i in look[0]]
        self.skin_i = max(look[0], key=lambda i: m.meshes[i].vertex_count)
        self.teeth_i = next((i for i, mt in zip(look[0], mats) if 'teeth' in mt), None)
        self.eye_i = next((i for i, mt in zip(look[0], mats) if mt.endswith('eye.material')), None)
        self.skin = m.decode(m.meshes[self.skin_i])
        self.teeth = m.decode(m.meshes[self.teeth_i]) if self.teeth_i is not None else None

    def pos(self, n):
        return self.W[self.ix[n]][3, :3]

    def classes(self, d):
        dom = d['joints'][np.arange(len(d['pos'])), d['weights'].argmax(1)]
        out = np.array(['other'] * len(dom), dtype=object)
        for c, frags in PETER_CLASS.items():
            hit = np.array([any(f in self.names[j] for f in frags) for j in dom])
            out[hit & (out == 'other')] = c
        return out


def landmarks_karin(P, cls):
    L = {}
    for side, sx in (('L', 1), ('R', -1)):
        for c in ('eye', 'brow'):
            sel = (cls == (c + side)) if c == 'eye' else ((cls == c) & (np.sign(P[:, 0]) == sx))
            if sel.any():
                L[c + side] = P[sel].mean(0)
    mouth = (cls == 'lipUp') | (cls == 'lipLo')
    front = mouth & (P[:, 2] > np.percentile(P[mouth, 2], 70))
    F = P[front]
    L['cornerL'], L['cornerR'] = F[F[:, 0].argmax()], F[F[:, 0].argmin()]
    for c in ('lipUp', 'lipLo'):
        s = (cls == c) & front & (np.abs(P[:, 0]) < 0.3 * (F[:, 0].max() - F[:, 0].min()))
        if s.any():
            L[c + 'C'] = P[s].mean(0)
    return L


def landmarks_head(h, cls):
    P = h.skin['pos']
    L = {}
    for side, sx in (('L', 1), ('R', -1)):
        e = h.pos(f'FACIAL_{side}_Eye')
        L['eye' + side] = e + [0, 0, 0.0125]
        q = e + [0, 0.02, 0.012]
        L['brow' + side] = P[np.linalg.norm(P - q, axis=1).argmin()]
        L['corner' + side] = h.pos(f'FACIAL_{side}_LipCorner')
    L['lipUpC'] = h.pos('FACIAL_C_LipUpper')
    L['lipLoC'] = h.pos('FACIAL_C_LipLower')
    return L


def transfer(h, Pk, cls, alpha, warp):
    """-> J [n,8], W [n,8] head-model joint indices"""
    head = h.ix['head']
    n = len(Pk)
    U = warp(Pk)
    hc = h.classes(h.skin)
    src = {c: (h.skin['pos'][hc == c], h.skin['joints'][hc == c], h.skin['weights'][hc == c]) for c in PETER_CLASS}
    if h.teeth is not None:
        tc = h.classes(h.teeth)
        src['tongue'] = (h.teeth['pos'][tc == 'tongue'], h.teeth['joints'][tc == 'tongue'], h.teeth['weights'][tc == 'tongue'])
    rows = []
    for i in range(n):
        acc = {}
        c = cls[i]
        a = float(alpha[i])
        if c in ('eyeL', 'eyeR'):
            acc[h.ix[f'FACIAL_{c[-1]}_EyeParallel']] = a
        elif c in src and len(src[c][0]) and a > 0:
            SP, SJ, SW = src[c]
            if c in SIDED:
                keep = np.sign(SP[:, 0]) == np.sign(U[i, 0])
                SP, SJ, SW = SP[keep], SJ[keep], SW[keep]
            dd = np.linalg.norm(SP - U[i], axis=1)
            nn = np.argsort(dd)[:4]
            iw = 1.0 / (dd[nn] + 1e-4)
            iw /= iw.sum()
            for k, wk in zip(nn, iw):
                for j, w in zip(SJ[k], SW[k]):
                    if w > 0:
                        acc[int(j)] = acc.get(int(j), 0.0) + a * wk * w
        else:
            a = 0.0
        acc[head] = acc.get(head, 0.0) + (1 - a)
        rows.append(sorted(acc.items(), key=lambda x: -x[1])[:8])
    J = np.zeros((n, 8), np.int64)
    W = np.zeros((n, 8))
    for i, r in enumerate(rows):
        for k, (j, w) in enumerate(r):
            J[i, k], W[i, k] = j, w
    W[W < 0.75 / 256] = 0
    W /= W.sum(1, keepdims=True)
    return J, W, U


# ------------------------------------------------------------------ build
def ref_fit(ref_model, fit_dir='build_sig'):
    targets = json.load(open(os.path.join(REPORTS, 'targets.json')))
    sig = targets[ref_model]['sig']
    return sig, np.load(os.path.join(WORK, fit_dir, sig, 'karin_geo.npz'))


def rig(family, asset, fit_dir='build_sig'):
    hpath, ref = FAMILIES[family]
    v = vrmmod.Vrm(vrm_path())
    kf = karin_face(v)
    sig, z = ref_fit(ref, fit_dir)
    Pfit, Nfit = z['face__P'], z['face__N']
    assert len(Pfit) == len(kf['P'])
    X = np.linalg.lstsq(np.c_[kf['P'], np.ones(len(Pfit))], Pfit, rcond=None)[0]   # VRM -> fit (similarity)
    rm = M.Model(asset(ref))
    Wr = rm.joint_world()[[j['name'] for j in rm.joints].index('head')]
    h = Head(asset(hpath))
    Wh = h.W[h.ix['head']]
    C = np.linalg.inv(Wr) @ Wh                       # ref-suit bind -> head-model bind, through the head joint
    Ph = (np.c_[Pfit, np.ones(len(Pfit))] @ C)[:, :3]
    Nh = Nfit @ C[:3, :3]
    Nh /= np.linalg.norm(Nh, axis=1, keepdims=True)
    lin = X[:3] @ C[:3, :3]                          # VRM delta -> head-model delta
    cls, alpha = classify(kf)
    alpha = smooth(alpha, kf['T'], cls)
    hc = h.classes(h.skin)
    Lk, Lh = landmarks_karin(Ph, cls), landmarks_head(h, hc)
    keys = sorted(set(Lk) & set(Lh))
    src = np.array([Lk[k] for k in keys])
    dst = np.array([Lh[k] for k in keys])
    warp = TPS(src, dst, reg=1e-8)
    J, W, U = transfer(h, Ph, cls, alpha, warp)
    face = dict(P=Ph, N=Nh, UV=kf['UV'], T=kf['T'], J=J, W=W)
    info = dict(family=family, head=hpath, ref=ref, sig=sig, landmarks=keys,
                landmark_err_after_warp=float(np.abs(warp(src) - dst).max()),
                classes={c: int((cls == c).sum()) for c in sorted(set(cls))},
                joints_used=len(np.unique(J[W > 0])))
    return h, face, dict(kf=kf, cls=cls, alpha=alpha, lin=lin, U=U), info


# ------------------------------------------------------------------ offline pose check
def pose_worlds(model, W, edits):
    """edits {joint idx: (R col-vector 3x3, t world)} applied about the joint's posed pivot; children follow"""
    n = len(W)
    par = [j['parent'] for j in model.joints]
    Lb = [W[j] if par[j] < 0 else W[j] @ np.linalg.inv(W[par[j]]) for j in range(n)]
    P = [None] * n
    for j in range(n):
        P[j] = Lb[j] if par[j] < 0 else Lb[j] @ P[par[j]]
        if j in edits:
            R, t = edits[j]
            p = P[j][3, :3].copy()
            Mx = np.eye(4)
            Mx[:3, :3] = R.T
            Mx[3, :3] = p - p @ R.T + t
            P[j] = P[j] @ Mx
    return np.array(P)


def skin_pose(Pv, J, Wt, Wb, Wp):
    S = np.linalg.inv(Wb) @ Wp
    H = np.c_[Pv, np.ones(len(Pv))]
    out = np.zeros((len(Pv), 3))
    for k in range(J.shape[1]):
        out += Wt[:, k:k + 1] * np.einsum('vi,vij->vj', H, S[J[:, k]])[:, :3]
    return out


def rotx(deg):
    a = np.radians(deg)
    return np.array([[1, 0, 0], [0, np.cos(a), -np.sin(a)], [0, np.sin(a), np.cos(a)]])


def roty(deg):
    a = np.radians(deg)
    return np.array([[np.cos(a), 0, np.sin(a)], [0, 1, 0], [-np.sin(a), 0, np.cos(a)]])


def poses(h):
    ix, names = h.ix, h.names
    jaw = next(n for n in ('FACIAL_C_Jaw', 'FACIAL_C_LowerLipRotation') if n in ix)
    I3 = np.eye(3)
    sel = lambda frag: [i for i, n in enumerate(names) if frag in n and n.count('_') <= 3]
    out = {'rest': {}, 'jaw_open': {ix[jaw]: (rotx(14), np.zeros(3))}}
    out['blink'] = {i: (rotx(28), np.zeros(3)) for s in 'LR' for i in [ix.get(f'FACIAL_{s}_EyelidUpperA'), ix.get(f'FACIAL_{s}_EyelidUpperB'),
                                                                      ix.get(f'FACIAL_{s}_EyelidUpperFurrow')] if i is not None}
    out['brow_up'] = {i: (I3, np.array([0, 0.006, 0])) for i in sel('Forehead')}
    out['look_left'] = {ix[f'FACIAL_{s}_EyeParallel']: (roty(18), np.zeros(3)) for s in 'LR'}
    out['smile'] = {ix[f'FACIAL_{s}_LipCorner']: (I3, np.array([0.004 * (1 if s == 'L' else -1), 0.005, -0.002])) for s in 'LR'}
    return out


def tri_colors(img, UV, T):
    a = np.asarray(img.convert('RGB'), np.float64)
    H, Wd = a.shape[:2]
    c = UV[T].mean(1)
    x = np.clip((c[:, 0] % 1) * Wd, 0, Wd - 1).astype(int)
    y = np.clip((c[:, 1] % 1) * H, 0, H - 1).astype(int)
    return a[y, x]


def render(h, face, aux, out_png):
    import render as R
    v = vrmmod.Vrm(vrm_path())
    img = {im.get('name'): v.image(i) for i, im in enumerate(v.js['images'])}['Karin_Face']
    cols = tri_colors(img, face['UV'], face['T'])
    sk = h.skin
    lo = np.minimum(face['P'].min(0), sk['pos'].min(0))
    hi = np.maximum(face['P'].max(0), sk['pos'].max(0))
    zoom = (np.array([lo[0], h.pos('head')[1] - 0.06, lo[2]]), np.array([hi[0], h.pos('head')[1] + 0.12, hi[2]]))
    tiles = []
    for name, ed in poses(h).items():
        Wp = pose_worlds(h.m, h.W, ed)
        Pk = skin_pose(face['P'], face['J'], face['W'], h.W, Wp)
        Pp = skin_pose(sk['pos'], sk['joints'], sk['weights'], h.W, Wp)
        T = sk['idx'].reshape(-1, 3)
        a = R.render_mesh([(Pp, T, np.array([200.0, 200, 200]))], os.devnull + '.png' if False else out_png + '.tmp.png',
                          W=300, H=360, bounds=zoom, views=((0, 1, 1),))
        b = R.render_mesh([(Pk, face['T'], cols)], out_png + '.tmp.png', W=300, H=360, bounds=zoom, views=((0, 1, 1),))
        tiles.append((name, a.copy(), b.copy()))
    os.remove(out_png + '.tmp.png')
    sheet = Image.new('RGB', (600, 360 * len(tiles)), 'white')
    from PIL import ImageDraw
    for r, (name, a, b) in enumerate(tiles):
        sheet.paste(a, (0, 360 * r)); sheet.paste(b, (300, 360 * r))
        ImageDraw.Draw(sheet).text((6, 360 * r + 4), name, fill=(200, 0, 0))
    sheet.save(out_png)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--family', choices=FAMILIES, required=True)
    ap.add_argument('--render', action='store_true')
    a = ap.parse_args()
    idx, toc = load_index(), load_toc()
    asset = lambda p: extract(toc, int(idx[p.replace('/', chr(92))]['id'], 16), 0)[0]
    h, face, aux, info = rig(a.family, asset)
    out = os.path.join(WORK, 'build_face', a.family)
    os.makedirs(out, exist_ok=True)
    np.savez_compressed(os.path.join(out, 'face.npz'), **face)
    json.dump(info, open(os.path.join(out, 'face.json'), 'w'), indent=1)
    print(json.dumps(info, indent=1))
    if a.render:
        render(h, face, aux, os.path.join(out, 'poses.png'))
        print(os.path.join(out, 'poses.png'))


if __name__ == '__main__':
    main()
