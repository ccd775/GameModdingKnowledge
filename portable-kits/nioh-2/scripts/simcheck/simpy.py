"""Python port of the generated sim_a.hlsl (build 4) + skinning of the palette-B meshes, for offline checks."""
from v3 import *          # noqa: F401,F403  (common: meta, arr, conf, mesh, pose2, outer_grid, lookup, BODY, ...)
import importlib
importlib.reload(nb)
nb._CONF_JOINTS.update(cj['karin_joints_game'])
CH_GW = nb.retarget_hair_and_skirt(meta, arr, conf)        # also fills nb.SKIRT_FIELD
_, CHAIN_TOKS = nb.sim_tokens()
GJ = json.load(open('data/joints.json'))['joints']


def palette_B():
    order = lambda ts: sorted(ts, key=lambda t: (t[0] != 'g', int(t[1:])))  # noqa: E731
    toks = set()
    for n in nb.PAL_B_MESHES:
        for d in CH_GW[n]:
            toks |= set(d)
    toks |= {c[2] for c in nb.SIM_CHAINS if c[2] != 'field'} | {c[0] for c in nb.SIM_COLLIDERS.values()}
    for c in nb.SIM_CHAINS:
        if c[2] == 'field':
            for n in c[3]:
                toks |= set(nb.joint_weights('field', np.array(nb._CONF_JOINTS[n], float)))
    return order(toks)


USED_B = palette_B()
CH, JOINTS, JW, COL = nb.sim_layout(USED_B, CHAIN_TOKS, GJ)
P_TOT = sum(x['n'] for x in CH)


def tokmat(T, t):
    return T.get(t, T.get('__root__', np.eye(4)))


def jframe(T, j):
    m = np.zeros((4, 4))
    for pi, w in JW[j]:
        m += w * tokmat(T, USED_B[pi])
    m[3] = [0, 0, 0, 1]
    return m


def xf(m, p):
    return m[:3, :3] @ p + m[:3, 3]


def rot_between(a, b):
    v = np.cross(a, b); c = np.dot(a, b)
    if c < -0.9999:
        x = np.cross(a, [1, 0, 0] if abs(a[0]) < 0.9 else [0, 1, 0]); x /= np.linalg.norm(x)
        return 2 * np.outer(x, x) - np.eye(3)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx / (1 + c)


class Sim:
    def __init__(self, overrides=None):
        self.cur = None; self.old = None
        self.over = overrides or {}

    def step(self, T, Tp):
        """T, Tp: token -> 4x4 this / last frame. Returns {sim token: 4x4}."""
        bones = {}
        if self.cur is None:
            self.cur = [None] * P_TOT; self.old = [None] * P_TOT
        for ci, c in enumerate(CH):
            prm = dict(c); prm.update(self.over.get(c['key'], {}))
            n, j0, p0 = c['n'], c['j0'], c['p0']
            F = [jframe(T, j0 + k) for k in range(n + 1)]
            r = [xf(F[k], JOINTS[j0 + k]) for k in range(n + 1)]
            rp = [xf(jframe(Tp, j0 + k), JOINTS[j0 + k]) for k in range(n + 1)]
            seg = [0] + [np.linalg.norm(r[k] - r[k - 1]) for k in range(1, n + 1)]
            cols = [(xf(tokmat(T, USED_B[cc['tok']]), cc['a']), xf(tokmat(T, USED_B[cc['tok']]), cc['b']), cc['r'], cc['name'])
                    for cc in COL]
            reset = any(self.cur[p0 + k - 1] is None or np.linalg.norm(self.cur[p0 + k - 1] - r[k]) > 80 for k in range(1, n + 1))
            p = [r[0]] + [None] * n; q = [r[0]] + [None] * n
            for k in range(1, n + 1):
                if reset:
                    p[k] = r[k].copy(); q[k] = r[k].copy(); continue
                dr = r[k] - rp[k]; lag = dr * prm['inertia']; ll = np.linalg.norm(lag)
                if ll > prm['lag']:
                    lag = lag * prm['lag'] / ll
                carry = dr - lag
                cur = self.cur[p0 + k - 1] + carry; old = self.old[p0 + k - 1] + carry
                stiff = prm['k0'] + (prm['k1'] - prm['k0']) * ((k - 1) / (n - 1) if n > 1 else 0)
                np_ = cur + (cur - old) * prm['damp'] - np.array([0, prm['grav'], 0])
                p[k] = np_ + (r[k] - np_) * stiff; q[k] = cur
            for it in range(3):
                for k in range(1, n + 1):
                    rd = (r[k] - r[k - 1]) / np.linalg.norm(r[k] - r[k - 1]); dd = p[k] - p[k - 1]
                    cm = prm['cosmax']
                    if np.dot(rd, dd / np.linalg.norm(dd)) < cm:
                        perp = dd - rd * np.dot(dd, rd); pl = np.linalg.norm(perp)
                        if pl > 1e-5:
                            p[k] = p[k - 1] + (rd * cm + perp / pl * np.sqrt(1 - cm * cm)) * np.linalg.norm(dd)
                    for a, b, rad, nm in cols:
                        if nm not in c['cols']:
                            continue
                        ab = b - a; t = np.clip(np.dot(p[k] - a, ab) / max(np.dot(ab, ab), 1e-6), 0, 1)
                        cp = a + t * ab; d = p[k] - cp; l = np.linalg.norm(d)
                        if 1e-4 < l < rad:
                            p[k] = cp + d * (rad / l)
                    d = p[k] - p[k - 1]; l = np.linalg.norm(d)
                    p[k] = p[k - 1] + (d / l if l > 1e-5 else (r[k] - r[k - 1]) / np.linalg.norm(r[k] - r[k - 1])) * seg[k]
            for k in range(1, n + 1):
                self.cur[p0 + k - 1] = p[k]; self.old[p0 + k - 1] = q[k]
            for k in range(n):
                a = xf(F[k], JOINTS[j0 + k + 1]) - r[k]
                ah = a / np.linalg.norm(a); d = p[k + 1] - p[k]
                Sa = np.eye(3) + (np.linalg.norm(d) / np.linalg.norm(a) - 1) * np.outer(ah, ah)
                R = rot_between(ah, d / np.linalg.norm(d)) @ Sa
                M = np.eye(4); M[:3, :3] = R @ F[k][:3, :3]; M[:3, 3] = R @ (F[k][:3, 3] - r[k]) + p[k]
                bones[USED_B[c['tok'] + k]] = M
        return bones


def packed(gw):
    out = []
    for d in gw:
        ids, ws = nb.pack_weights(d, 4)
        out.append(dict(zip(ids, ws)) if len(set(ids)) == len(ids) else {i: sum(w for j, w in zip(ids, ws) if j == i) for i in set(ids)})
    return out


SKIRT_GW = packed(CH_GW['skirt'])


def skin_all(P, gw, T, bones):
    out = np.zeros_like(P)
    for i, d in enumerate(gw):
        acc = np.zeros(3)
        for t, w in d.items():
            M = bones[t] if t in bones else tokmat(T, t)
            acc += w * (M[:3, :3] @ P[i] + M[:3, 3])
        out[i] = acc
    return out
