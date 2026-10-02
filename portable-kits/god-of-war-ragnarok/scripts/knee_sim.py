"""Simulate knee flexion with the data the game actually gets: decode the skin (head slot) and sock (feet slot) meshes
from a built r_freyavalkyrie00 + lodpack, skin them with linear blend skinning on Freya's bind skeleton while the
shin subtrees rotate about the knees, and count skin vertices that end up in front of the sock surface.
usage: knee_sim.py OUT [OUT ...] --base-wad W   (OUT = build_valk_final.py output; W = original r_freyavalkyrie00.wad)"""
import sys, os, json, argparse, numpy as np
from scipy.spatial import cKDTree
from wad import Wad
from mesh import parse_mesh
from decode import decode, skin_of
from packs import read_lodpack_toc
from rig import parse_rig

# Case constants (Freya companion, game build 18979360; see build_valk_final.py)
SHIN_BONES = (55, 62)          # FK shin bones; they and everything below them rotate about the knee
SKIN_SLOT = '280'              # head LOD0 def that carries Karin's body skin
SOCK_SLOTS = ('32', '34')      # feet slot LOD0 (shoes+socks ~0.5-0.8) and LOD1 (~0.2-0.4)
KNEE_HEIGHT = 0.53             # bind-pose knee height of the Freya rig

ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('out', nargs='+', help='build output folder(s) with r_freyavalkyrie00.wad and KarinOriginalFreya.lodpack')
ap.add_argument('--base-wad', required=True, help='original r_freyavalkyrie00.wad (bind skeleton; LZ4 is fine)')
args = ap.parse_args()
w0 = Wad(open(args.base_wad, 'rb').read())
n, par, mats, ibm, _ = parse_rig(w0.get([e for e in w0.entries if e.name == 'goProtofreyaValkyrie00'][0]))
Wb = [None] * n
for i in range(n):
    Wb[i] = mats[i] if par[i] < 0 else mats[i] @ Wb[par[i]]
Wb = np.array(Wb)
kids = {i: [] for i in range(n)}
for i, p in enumerate(par):
    if p >= 0:
        kids[p].append(i)


def subtree(r):
    out, st = [], [r]
    while st:
        b = st.pop(); out.append(b); st += kids[b]
    return out


def skin_mats(angle):
    """Row-vector skinning matrices: identity except the shin subtrees (FK 55/62 and everything below), rotated about
    the knee joint so the ankle swings backwards (+Z) -- a flexed knee."""
    M = np.tile(np.eye(4), (n, 1, 1))
    for shin in SHIN_BONES:
        piv = Wb[shin][3, :3]
        a = np.radians(angle)
        R = np.array([[1, 0, 0], [0, np.cos(a), np.sin(a)], [0, -np.sin(a), np.cos(a)]])   # rotate about X
        T = np.eye(4); T[:3, :3] = R; T[3, :3] = piv - piv @ R
        if (np.array([0, 0.084 - 0.529, 0]) @ R)[2] < 0:     # make sure the shin tip goes to +Z (backwards)
            R = R.T; T[:3, :3] = R; T[3, :3] = piv - piv @ R
        for b in subtree(shin):
            M[b] = T
    return M


def load(out):
    w = Wad(open(out + '/r_freyavalkyrie00.wad', 'rb').read())
    ms = parse_mesh(w.get([e for e in w.entries if e.name == 'MESH_freyavalkyrie00_0' and e.type == 1][0]))
    g, mem, _ = read_lodpack_toc(out + '/KarinOriginalFreya.lodpack.toc')
    lp = open(out + '/KarinOriginalFreya.lodpack', 'rb').read()
    def mesh(di):
        m = ms[di]; gi, mo, size = mem[m.hash]
        o, idx = decode(m, lp[g[gi][0] + mo: g[gi][0] + mo + size])
        P = np.array([x[:3] for x in [v for k, v in o.items() if k[0] == 0][0]])
        N = np.array([x[0][:3] for x in [v for k, v in o.items() if k[0] == 1][0]])
        return P, N, skin_of(m, o), np.array(idx).reshape(-1, 3)
    return mesh


def pose(P, N, sk, M):
    Ph = np.c_[P, np.ones(len(P))]
    out, nout = np.zeros_like(P), np.zeros_like(N)
    for vi, inf in enumerate(sk):
        acc = np.zeros(4); nacc = np.zeros(3)
        for j, wt in inf:
            if wt <= 0:
                continue
            acc += wt * (Ph[vi] @ M[j]); nacc += wt * (N[vi] @ M[j][:3, :3])
        out[vi] = acc[:3]; nout[vi] = nacc / max(np.linalg.norm(nacc), 1e-9)
    return out, nout


res = {}
for out in args.out:
    mesh = load(out)
    rep = json.load(open(out + '/mesh_report.json'))['chosen']
    skin_slot = SKIN_SLOT
    rows = []
    for sock_slot in SOCK_SLOTS:
        Ps, Ns, sks, Fs = mesh(int(sock_slot))
        Pb, Nb, skb, Fb = mesh(int(skin_slot))
        # skin vertices of the legs between ankle and sock top (bind pose), excluding the feet inside the shoes
        top = Ps[:, 1].max()
        leg = (Pb[:, 1] > 0.12) & (Pb[:, 1] < top - 0.04) & (np.abs(Pb[:, 0]) > 0.03)
        for ang in (0, 30, 60, 90):
            M = skin_mats(ang)
            ps, ns = pose(Ps, Ns, sks, M)
            pb, _ = pose(Pb[leg], Nb[leg], [skb[i] for i in np.nonzero(leg)[0]], M)
            # sock points that cover each skin vertex are chosen in the bind pose (same patch of leg), so a folded
            # surface from the other side of the joint can never be picked as "nearest" once the knee bends
            _, kk = cKDTree(Ps).query(Pb[leg], k=6)
            sd = np.sum((pb[:, None, :] - ps[kk]) * ns[kk], axis=2)
            s = np.median(sd, axis=1); d = np.zeros(len(s))
            outside = s > 0.001
            knee_zone = np.abs(Pb[leg][:, 1] - KNEE_HEIGHT) < 0.08
            rows.append(dict(sock_slot=sock_slot, sock_levels=rep[sock_slot]['levels'], angle=ang, legs=int(leg.sum()),
                             outside=int(outside.sum()), outside_knee=int((outside & knee_zone).sum()),
                             worst_mm=round(float(s[outside].max() * 1000), 1) if outside.any() else 0.0))
    res[os.path.basename(out.rstrip('/'))] = rows
    for r in rows:
        print(os.path.basename(out.rstrip('/')), r)
