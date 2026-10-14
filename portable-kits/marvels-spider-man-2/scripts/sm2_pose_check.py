"""Offline pose check of a Karin fit: skirt vs. legs in crouch / sit / stride, textured renders.

  python sm2_pose_check.py <fit karin_geo.npz> [--png out.png] [--poses crouch,sit,stride]

The fit's hero model (karin_geo.json 'model') gives the bind pose; appended dynamics joints follow their parents
rigidly. Metric: body / tights vertices of the hip and thigh that the skirt covers at rest (skirt vertex within
8 cm along the body normal) and that end up outside the skirt in the pose ('through' = signed gap < 0).
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import i30_model as M                   # noqa: E402
import render as R                      # noqa: E402
import vrm as vrmmod                    # noqa: E402
from sm2_karin_geo import WORK, vrm_path, axis_angle   # noqa: E402

TEX = {'body': 'Karin_Body', 'costume': 'Karin_Costume', 'hair': 'Karin_Hair', 'hair_alpha': 'Karin_Hair',
       'face': 'Karin_Face'}
LEG = ('pelvis', 'LF_upleg', 'RT_upleg', 'LF_uplegTwist', 'RT_uplegTwist')


def load(npz):
    z = np.load(npz)
    parts = {}
    for k in z.files:
        part, f = k.split('__')
        parts.setdefault(part, {})[f] = z[k]
    meta = parts.pop('_meta')
    dyn = parts.pop('_dyn', None)
    return parts, [str(x) for x in meta['joint_names']], np.asarray(meta['parents']), dyn


def bind_worlds(npz, names):
    rep = json.load(open(os.path.join(os.path.dirname(npz), 'karin_geo.json')))
    m = M.Model(open(os.path.join(WORK, 'native', rep['model']), 'rb').read())
    W = np.array(m.joint_world())
    _, _, _, dyn = load(npz)
    if dyn is not None:
        W = np.concatenate([W, dyn['world']])
    assert len(W) == len(names)
    return W


def pose_worlds(W, par, edits):
    """edits {joint: R (col-vector, world)} about the joint's posed pivot, applied in joint order; children follow"""
    Lb = [W[j] if par[j] < 0 else W[j] @ np.linalg.inv(W[par[j]]) for j in range(len(W))]
    P = [None] * len(W)
    for j in range(len(W)):
        P[j] = Lb[j] if par[j] < 0 else Lb[j] @ P[par[j]]
        if j in edits:
            p = P[j][3, :3].copy()
            Mx = np.eye(4)
            Mx[:3, :3] = edits[j].T
            Mx[3, :3] = p - p @ edits[j].T
            P[j] = P[j] @ Mx
    return np.array(P)


def skin(P, N, J, Wt, S):
    H = np.c_[P, np.ones(len(P))]
    po = np.zeros((len(P), 3))
    no = np.zeros((len(P), 3))
    for k in range(J.shape[1]):
        Sk = S[J[:, k]]
        po += Wt[:, k:k + 1] * np.einsum('vi,vij->vj', H, Sk)[:, :3]
        no += Wt[:, k:k + 1] * np.einsum('vi,vij->vj', N, Sk[:, :3, :3])
    return po, no / np.linalg.norm(no, axis=1, keepdims=True).clip(1e-9)


def poses(names, W):
    """hero frame: x = character's left, y up, z forward (checked against the face below)"""
    ix = {n: i for i, n in enumerate(names)}
    X = np.array([1.0, 0, 0])

    def legs(flex, abd, knee, tilt=0.0):
        ed = {}
        if tilt:
            ed[ix['pelvis']] = axis_angle(X, np.radians(tilt))
        for s, sg in (('LF_', 1), ('RT_', -1)):
            fl, ab, kn = (flex[0], abd[0], knee[0]) if s == 'LF_' else (flex[1], abd[1], knee[1])
            Rt = axis_angle(np.array([0, 0, 1.0]), np.radians(-sg * ab)) @ axis_angle(X, np.radians(-fl))
            ed[ix[s + 'upleg']] = Rt
            ed[ix[s + 'loleg']] = axis_angle(Rt @ X, np.radians(kn))
        return ed
    return {
        'rest': {},
        'crouch': legs((115, 115), (30, 30), (140, 140), tilt=25),
        'perch': legs((110, 110), (50, 50), (150, 150), tilt=40),       # wall-crawl / perch: knees wide
        'sit': legs((90, 90), (10, 10), (90, 90)),
        'stride': legs((65, -25), (5, 5), (45, 20)),
    }


def view_rot(yaw, pitch):
    ry = axis_angle(np.array([0, 1.0, 0]), np.radians(yaw))
    rx = axis_angle(np.array([1.0, 0, 0]), np.radians(pitch))
    return rx @ ry


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('npz')
    ap.add_argument('--png')
    ap.add_argument('--poses', default='rest,crouch,perch,sit,stride')
    a = ap.parse_args()
    parts, names, par, _ = load(a.npz)
    W = bind_worlds(a.npz, names)
    face_z = parts['face']['P'][:, 2].mean() - W[names.index('head')][3, 2]
    assert face_z > 0, 'expected +z forward'
    v = vrmmod.Vrm(vrm_path())
    imgs = {im.get('name'): np.asarray(v.image(i).convert('RGB'), np.float64) for i, im in enumerate(v.js['images'])}

    def cols(key, d):
        if key not in TEX:
            return None
        a_ = imgs[TEX[key]]
        T = d['T'].reshape(-1, 3)
        c = d['UV'][T].mean(1)
        x = np.clip((c[:, 0] % 1) * a_.shape[1], 0, a_.shape[1] - 1).astype(int)
        y = np.clip((c[:, 1] % 1) * a_.shape[0], 0, a_.shape[0] - 1).astype(int)
        return a_[y, x]

    # covered pairs at rest
    cs = parts['costume']
    sk = cs.get('S', np.zeros(len(cs['P']))) > 0.5
    if not sk.any():
        raise SystemExit('fit has no costume__S (skirt weights); refit with the current sm2_karin_geo')
    legj = [names.index(n) for n in LEG if n in names]
    srcs = []
    for key in ('body', 'costume'):
        d = parts[key]
        dom = d['J'][np.arange(len(d['P'])), d['W'].argmax(1)]
        m = np.isin(dom, legj) & (d['P'][:, 1] < cs['P'][sk, 1].max())
        if key == 'costume':
            m &= ~sk
        srcs.append((key, np.where(m)[0]))
    Qs = cs['P'][sk]
    from scipy.spatial import cKDTree
    tree = cKDTree(Qs)
    pairs = []
    for key, idx in srcs:
        Pb, Nb = parts[key]['P'][idx], parts[key]['N'][idx]
        dist, qi = tree.query(Pb)
        gap = ((Qs[qi] - Pb) * Nb).sum(1)
        ok = (dist < 0.08) & (gap > 0.002)
        pairs.append((key, idx[ok], np.where(sk)[0][qi[ok]]))
    ncov = sum(len(p[1]) for p in pairs)

    sel = [p for p in a.poses.split(',') if p]
    tiles, report = [], {}
    VIEWS = (('back-top', view_rot(180, 40)), ('back-left', view_rot(135, 30)), ('side', view_rot(90, 10)),
             ('front', view_rot(0, 10)))
    for pname in sel:
        Wp = pose_worlds(W, par, poses(names, W)[pname])
        S = np.linalg.inv(W) @ Wp
        posed = {k: skin(d['P'], d['N'], d['J'], d['W'], S) for k, d in parts.items() if k in TEX}
        thr = []
        for key, bi, qi in pairs:
            pb, nb = posed[key][0][bi], posed[key][1][bi]
            q = posed['costume'][0][qi]
            thr.append(((q - pb) * nb).sum(1))
        thr = np.concatenate(thr)
        report[pname] = dict(covered=int(ncov), through=int((thr < 0).sum()), through_pct=round(100 * float((thr < 0).mean()), 1),
                             depth_p95_mm=round(1000 * float(np.percentile(np.maximum(-thr, 0), 95)), 1))
        print(pname, report[pname], flush=True)
        if not a.png:
            continue
        hips = Wp[names.index('pelvis')][3, :3]
        for vname, Rv in VIEWS:
            meshes = []
            for k, (pp, _) in posed.items():
                c = cols(k, parts[k])
                meshes.append(((pp - hips) @ Rv.T, parts[k]['T'].reshape(-1, 3), c))
            lo = np.array([-0.45, -0.75, -1.0]); hi = np.array([0.45, 0.55, 1.0])
            tmp = a.png + '.tmp.png'
            im = R.render_mesh(meshes, tmp, W=320, H=420, bounds=(lo, hi), views=((0, 1, 1),))
            tiles.append((f'{pname} {vname}', im.copy()))
        os.remove(tmp)
    if a.png:
        cols_n = len(VIEWS)
        sheet = Image.new('RGB', (320 * cols_n, 420 * (len(tiles) // cols_n)), 'white')
        for i, (t, im) in enumerate(tiles):
            x, y = 320 * (i % cols_n), 420 * (i // cols_n)
            sheet.paste(im, (x, y))
            ImageDraw.Draw(sheet).text((x + 6, y + 4), t, fill=(200, 0, 0))
        sheet.save(a.png)
        print('wrote', a.png)
    json.dump(report, open(os.path.splitext(a.png or a.npz)[0] + '_pose.json', 'w'), indent=1)


if __name__ == '__main__':
    main()
