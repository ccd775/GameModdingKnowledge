"""Build a ModelAnimDynamicsDef (ADD1CBD3) section; layout in SOP/FORMAT_NOTES.md (section "动力学").

chain = dict(joints=[j0 .. jtip] (global joint indices, each the parent of the next), name_off=<abs DAT1 string offset>,
             type=0, mass=0.1, mass_end=0.1, damping=0.01, cone=30.0, cone_end=20.0, gravity=(0, -9.80665, 0),
             cone_scale=(1, 1, 1, 1))     # -Y, +Y, -Z, +Z
j0 is pinned to its animated parent; every following joint is a simulated particle.
"""
import math, struct
import numpy as np

T_DYN = 0xADD1CBD3
BUILT_HAS_DYNAMICS = 0x20000000      # ModelBuilt word 0; set exactly when ADD1CBD3 exists (11/11 surveyed)
BEND_K = (0.8, 0.9)                   # constant in every original
TETHER_SLACK = 1.01
TETHER_COMPAT = True                  # see build(): reproduce the shipped tether slot filling


def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def qmul(a, b):
    x1, y1, z1, w1 = a
    x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


def arc(u, v):
    """shortest rotation quat taking unit u to unit v (180 deg: about Z, as the originals do for -X)"""
    c = float(np.dot(u, v))
    if c < -0.999999:
        return np.array([0.0, 0.0, 1.0, 0.0])
    ax = np.cross(u, v)
    q = np.array([ax[0], ax[1], ax[2], 1 + c])
    return q / np.linalg.norm(q)


def pad16(b):
    return b + bytes(-len(b) % 16)


def build(model, chains):
    """model: i30_model.Model with the chain joints present. -> section bytes"""
    W = model.joint_world()
    pos = W[:, 3, :3]
    par = [j['parent'] for j in model.joints]
    loc = model.bind_local
    T0, T1, T3, T5, T6 = [], [], [], [], []
    all_teth, slots = [], []
    np_ = nl = nt = 0
    for c in chains:
        js = c['joints']
        for a, b in zip(js, js[1:]):
            assert par[b] == a, (a, b)
        n = len(js) - 1                                   # links
        p0, l0 = np_, nl
        mass = [c.get('mass', 0.1) + (c.get('mass_end', c.get('mass', 0.1)) - c.get('mass', 0.1)) * (i / max(n - 1, 1))
                for i in range(n)]
        inv = [0.0] + [1.0 / m for m in mass]              # per particle; particle 0 pinned
        ny, py, nz, pz = c.get('cone_scale', (1, 1, 1, 1))
        for j in js:
            T0.append(struct.pack('<3f', *pos[j]))
        for i in range(n):
            ja, jb = js[i], js[i + 1]
            ang = math.radians(c.get('cone', 30.0) + (c.get('cone_end', 20.0) - c.get('cone', 30.0)) * (i / max(n - 1, 1)))
            s, co = math.sin(ang), math.cos(ang)
            q = np.array(loc[ja]['rot'])
            d = np.array(loc[jb]['pos'])
            ln = float(np.linalg.norm(pos[jb] - pos[ja]))
            dn = d / max(np.linalg.norm(d), 1e-9)
            qc = qmul(q, arc(np.array([1.0, 0, 0]), dn))
            T1.append(struct.pack('<HHHHI', p0 + i, p0 + i + 1, ja, jb, par[ja])
                      + struct.pack('<11f', inv[i], inv[i + 1], ln, co, s, -s * ny, s * py, -s * nz, s * pz, qc[0], qc[1])
                      + struct.pack('<2f', qc[2], qc[3]))
            T6.append(struct.pack('<HHHHI', i, i + 1, ja, jb, par[ja]) + struct.pack('<3f', *dn) + struct.pack('<4f', *q))
            # bend: root type against the animated parent joint, then particle triplets
            if i == 0:
                a_pos, a = pos[par[ja]], par[ja]
                rec = struct.pack('<HHHH', a, p0, p0 + 1, 1)
                ia = 0.0
            else:
                a_pos, a = pos[js[i - 1]], p0 + i - 1
                rec = struct.pack('<HHHH', a, p0 + i, p0 + i + 1, 0)
                ia = inv[i - 1]
            u, v = a_pos - pos[ja], pos[jb] - pos[ja]
            cosb = float(u @ v / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-12))
            T3.append(rec + struct.pack('<6f', ia, inv[i + 1], float(np.linalg.norm(pos[jb] - a_pos)), cosb, *BEND_K))
        # tethers: root -> particles 1, 3, 5 ..., max distance = path length * 1.01, global particle indices.
        # Slots start at the chain's first link. The shipped builder fills chain c's slot t with entry t of the
        # model-wide list (so every chain repeats chain 0's first tethers); reproduced as is (TETHER_COMPAT).
        teth = []
        for t in range((n + 1) // 2):
            b = 2 * t + 1
            path = sum(float(np.linalg.norm(pos[js[i + 1]] - pos[js[i]])) for i in range(b))
            teth.append(struct.pack('<HHff', p0, p0 + b, inv[b], path * TETHER_SLACK))
        all_teth.extend(teth)
        slots.append((l0, n, len(teth)))
        r = np.array(loc[js[0]]['pos'])
        g = c.get('gravity', (0.0, -9.80665, 0.0))
        # (type, first link) (links, tether cum) (tethers, tether slot) (bends, FIRST PARTICLE) (particles, 0) (0, 1) ...
        # until 2026-10-13 this wrote (bends, first link) (particles, first particle): wrong from chain 1 on (T10 froze)
        T5.append(struct.pack('<HHHHHHHHHHHHHHI', c.get('type', 0), l0, n, nt, len(teth), l0, n, p0, len(js), 0, 0, 1,
                              p0, js[0], par[js[0]])
                  + struct.pack('<3fi4f', *r, -1, 0, 0, 0, 0)
                  + struct.pack('<HHHH', l0, n, js[-1], par[js[-1]])
                  + struct.pack('<4f3ffI', *loc[js[-1]]['rot'], *g, c.get('damping', 0.01), c['name_off']))
        np_ += len(js)
        nl += n
        nt += len(teth)
    T2, cum = [], 0
    for l0, n, k in slots:
        T2 += (all_teth[:k] if TETHER_COMPAT else all_teth[cum:cum + k]) + [bytes(12)] * (n - k)
        cum += k
    assert all(len(x) == 64 for x in T1) and all(len(x) == 40 for x in T6) and all(len(x) == 32 for x in T3)
    assert all(len(x) == 108 for x in T5) and all(len(x) == 12 for x in T2)
    tabs = [b''.join(T0), b''.join(T1), b''.join(T2), b''.join(T3), None, b''.join(T5), b''.join(T6)]
    body = b''
    offs = [0]
    for t in tabs:
        if t is None:
            offs.append(-1)
            continue
        offs.append(len(body))
        body += pad16(t)
    counts = (np_, nl, nt, nl, 0, len(chains), nl, 0)
    return struct.pack('<8H8i', *counts, *offs) + body
