"""Offline skirt-vs-body penetration test: synthetic leg poses, LBS of body + skirt, (angle, height) radius grid."""
import json, os, sys
import numpy as np
N2 = os.environ.get('N2_BUILD')   # the build directory (the project's _build kit)
if not N2:
    raise SystemExit('N2_BUILD is not set: point it at the build directory (source/, build1/, data/)')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # scripts/ (n2_build.py)
os.chdir(N2)
import n2_build as nb

meta = json.load(open('source/source.json', encoding='utf-8'))
arr = dict(np.load('source/source.npz'))
conf = dict(np.load('build1/conformed.npz', allow_pickle=True))
cj = json.load(open('build1/conform.json'))
nb._CONF_JOINTS.update(cj['karin_joints_game'])
Q = {k: np.array(v, float) for k, v in json.load(open('data/joints.json'))['joints'].items()}
LEG = {'L': [11, 13, 9, 10, 31, 29, 30, 14, 15, 16], 'R': [12, 19, 17, 18, 34, 32, 33, 20, 21, 22]}
AX = np.array([0.0, 1.85])   # pelvis vertical axis (x, z)


def mesh(name):
    m = next(m for m in meta['meshes'] if m['name'] == name)
    k = m['key']
    P = conf[k + '__pos'].astype(float)
    tris = arr[k + '__loop_vertex'][arr[k + '__tris']]
    gw = [json.loads(x) for x in conf[k + '__gw']]
    return P, tris, gw, m


def rot(axis, deg):
    a = np.asarray(axis, float); a /= np.linalg.norm(a); t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def about(R, c):
    M = np.eye(4); M[:3, :3] = R; M[:3, 3] = c - R @ c; return M


def pose(flexL=0, flexR=0, abdL=0, abdR=0):
    """flex: + = thigh forward (rotation about +X... sign chosen so + lifts the knee forward); abd: + = outward."""
    T = {}
    for s, flex, abd in (('L', flexL, abdL), ('R', flexR, abdR)):
        sx = 1 if s == 'L' else -1
        R = rot([0, 0, 1], sx * abd) @ rot([1, 0, 0], -flex)
        M = about(R, Q['hip_' + s])
        for g in LEG[s]:
            T[f'g{g}'] = M
    return T


def skin(P, gw, T):
    out = np.zeros_like(P)
    for i, d in enumerate(gw):
        tot = sum(d.values())
        acc = np.zeros(3)
        for t, w in d.items():
            M = T.get(t)
            acc += w * (P[i] if M is None else M[:3, :3] @ P[i] + M[:3, 3])
        out[i] = acc / tot
    return out


def cyl(P):
    d = P[:, [0, 2]] - AX
    return np.degrees(np.arctan2(d[:, 0], d[:, 1])) % 360, np.hypot(d[:, 0], d[:, 1])


def outer_grid(P, tris, nphi=90, y0=70, y1=125, dy=1.0, ns=6):
    """max skirt radius per (angle, height) cell from dense barycentric samples of the triangles."""
    g = np.full((nphi, int((y1 - y0) / dy)), np.nan)
    a = P[tris[:, 0]]; b = P[tris[:, 1]]; c = P[tris[:, 2]]
    pts = []
    for i in range(ns + 1):
        for j in range(ns + 1 - i):
            u, v = i / ns, j / ns
            pts.append(a + u * (b - a) + v * (c - a))
    S = np.concatenate(pts)
    phi, r = cyl(S)
    ii = (phi / (360 / nphi)).astype(int) % nphi; jj = ((S[:, 1] - y0) / dy).astype(int)
    ok = (jj >= 0) & (jj < g.shape[1])
    for i, j, rr in zip(ii[ok], jj[ok], r[ok]):
        if not (g[i, j] >= rr):
            g[i, j] = rr
    return g


def lookup(g, P, nphi=90, y0=70, dy=1.0):
    phi, r = cyl(P)
    ii = (phi / (360 / nphi)).astype(int) % nphi; jj = ((P[:, 1] - y0) / dy).astype(int)
    ok = (jj >= 0) & (jj < g.shape[1])
    out = np.full(len(P), np.nan)
    out[ok] = g[ii[ok], jj[ok]]
    return out, r


def pose2(flexL=0, flexR=0, abdL=0, abdR=0, twist=0, bend=0, pivot_y=110.0):
    """legs as pose(), plus spine (g1, g2, g3 and up) twisted about the vertical axis / bent forward about the pelvis."""
    T = pose(flexL, flexR, abdL, abdR)
    R = rot([1, 0, 0], bend) @ rot([0, 1, 0], twist)
    M = about(R, np.array([0.0, pivot_y, 1.85]))
    for g in (1, 2, 3, 4, 5, 6, 7, 8):
        T[f'g{g}'] = M
    return T
