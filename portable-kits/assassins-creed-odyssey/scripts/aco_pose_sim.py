"""Pose simulator (2026-10-19): apply Kassandra head-skeleton poses (PoseGroups = absolute local transforms) to a skinned
GLB with linear blend skinning, using the GLB's own binds (as the game does).
  import aco_pose_sim as sim; S = sim.Skel(); M = sim.Mesh("work/mesh_v6/karin_lod0_ody.glb", 0, [0], S)
  moved = M.skin(S.pose_globals(pose_id, weight), vertex_indices)   # rest: M.skin(S.G0, idx)
Karin: skin 0 / mesh 0 of *_ody.glb; vanilla head: work/fit/kassandra_fit_skeleton.glb skin 1 / mesh 1 (half scale)."""
import os, re, sys, json, struct, math, zlib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import aco_phys_skel as A

def load(path):
    b = open(path, "rb").read()
    jl = struct.unpack_from("<I", b, 12)[0]
    j = json.loads(b[20:20 + jl]); data = b[20 + jl + 8:]
    def acc(i):
        a = j["accessors"][i]; bv = j["bufferViews"][a["bufferView"]]
        comp = {5126: "<f4", 5123: "<u2", 5121: "u1", 5125: "<u4"}[a["componentType"]]
        n = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}[a["type"]]
        stride = bv.get("byteStride")
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        it = np.dtype(comp).itemsize
        if stride and stride != it * n:
            raw = np.frombuffer(data, "u1", stride * a["count"], off).reshape(a["count"], stride)[:, :it * n]
            return np.frombuffer(raw.tobytes(), comp).reshape(a["count"], n)
        return np.frombuffer(data, comp, a["count"] * n, off).reshape(a["count"], n)
    return j, acc


# Kassandra's head skeleton XML (AnvilToolkit export). Portable kit: ACO_HEAD_SKELETON_XML, else the project layout
# under ACO_WORK, else pass Skel(path)
HEADXML = os.environ.get("ACO_HEAD_SKELETON_XML") or (os.path.join(
    os.environ["ACO_WORK"], "x1", "p1", "xml", "18988_-_ACD_CHF_PLA_Kassandra_Head", "0_-_ACD_CHF_PLA_Kassandra_Head.Skeleton.xml")
    if os.environ.get("ACO_WORK") else None)
PRE = r'<Hash32 Name="BoneID" HashValue="[^"]*">(\d+)</Hash32>\s*<Vector4 Name="LocalPosition">([^<]*)</Vector4>\s*<Quaternion Name="LocalRotation">([^<]*)</Quaternion>'


def bid_of(name):
    return int(name) if name.isdigit() else zlib.crc32(name.encode())


class Skel:
    def __init__(self, path=None):
        path = path or HEADXML
        if not path:
            raise SystemExit("set ACO_HEAD_SKELETON_XML (or ACO_WORK) or pass Skel(<head skeleton xml>)")
        x = open(path, encoding="utf-8-sig").read()
        bones = A.parse_bones(x)
        byptr = {b["ptr"]: b for b in bones}
        self.order = [b["id"] for b in bones]
        self.parent = {b["id"]: (byptr[b["father"]]["id"] if b["father"] in byptr else None) for b in bones}
        self.L0 = {}
        for b in bones:
            lp = A.vec(re.search(r'Name="LocalPosition">([^<]*)<', b["block"]).group(1))[:3]
            lr = A.vec(re.search(r'Name="LocalRotation">([^<]*)<', b["block"]).group(1))
            self.L0[b["id"]] = A.m4(A.quat_to_m(lr), lp)
        self.Gxml = {b["id"]: b["G"] for b in bones}
        self.root_G = {b["id"]: b["G"] for b in bones if self.parent[b["id"]] is None}
        self.G0 = self.globals({})
        pg = x[x.index('Name="PoseGroups"'):]
        self.poses = {}
        for m in re.finditer(r'<Unsigned32 Name="PoseID">(\d+)</Unsigned32>(.*?)</DynamicSmallArray>', pg, re.S):
            d = {}
            for bm in re.finditer(PRE, m.group(2)):
                bid = int(bm.group(1))
                if bid in self.L0:
                    d[bid] = A.m4(A.quat_to_m(A.vec(bm.group(3))), A.vec(bm.group(2))[:3])
            self.poses[int(m.group(1))] = d

    def globals(self, locals_):
        G = {}
        for b in self.order:
            p = self.parent[b]
            L = locals_.get(b, self.L0[b])
            G[b] = L if p is None else G[p] @ L
            if p is None:
                G[b] = self.root_G[b] if b not in locals_ else self.root_G[b] @ np.linalg.inv(self.L0[b]) @ L
        return G

    def pose_globals(self, pid, weight=1.0):
        """weight blends each bone's local from rest toward the pose (slerp-free: rotation via axis-angle scaling)."""
        loc = {}
        for b, L in self.poses[pid].items():
            if weight == 1.0:
                loc[b] = L
            else:
                L0 = self.L0[b]
                dR = L0[:3, :3].T @ L[:3, :3]
                ang = math.acos(max(-1, min(1, (np.trace(dR) - 1) / 2)))
                if ang > 1e-9:
                    ax = np.array([dR[2, 1] - dR[1, 2], dR[0, 2] - dR[2, 0], dR[1, 0] - dR[0, 1]]) / (2 * math.sin(ang))
                    dR = rodrigues(ax, ang * weight)
                loc[b] = A.m4(L0[:3, :3] @ dR, L0[:3, 3] + weight * (L[:3, 3] - L0[:3, 3]))
        return self.globals(loc)


def rodrigues(ax, a):
    ax = ax / np.linalg.norm(ax)
    K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K


class Mesh:
    def __init__(self, path, skin, meshes, skel, ref=0x606D2579):
        j, acc = load(path)
        sk = j["skins"][skin]
        self.ids = [bid_of(j["nodes"][i]["name"]) for i in sk["joints"]]
        ibm = acc(sk["inverseBindMatrices"]).reshape(-1, 4, 4)
        self.B = [np.linalg.inv(m.T.astype(float)) for m in ibm]
        P, J, W = [], [], []
        for mi in meshes:
            for prim in j["meshes"][mi]["primitives"]:
                a = prim["attributes"]
                P.append(acc(a["POSITION"]).astype(float)); J.append(acc(a["JOINTS_0"]).astype(int)); W.append(acc(a["WEIGHTS_0"]).astype(float))
        self.P, self.J, self.W = np.vstack(P), np.vstack(J), np.vstack(W)
        self.W = self.W / np.maximum(self.W.sum(1, keepdims=True), 1e-9)
        self.skel = skel
        k = self.ids.index(ref)
        self.T = self.B[k] @ np.linalg.inv(skel.G0[ref])  # head frame -> mesh frame

    def joint(self, bid):
        return self.ids.index(bid)

    def wof(self, bid):
        if bid not in self.ids:
            return np.zeros(len(self.P))
        return (self.W * (self.J == self.ids.index(bid))).sum(1)

    def skin(self, G, idx):
        out = np.zeros((len(idx), 3))
        Ph = np.c_[self.P[idx], np.ones(len(idx))]
        for k in range(4):
            jj = self.J[idx, k]; ww = self.W[idx, k]
            for j in np.unique(jj[ww > 0]):
                sel = (jj == j) & (ww > 0)
                b = self.ids[j]
                M = self.T @ G[b] @ np.linalg.inv(self.B[j]) if b in G else np.eye(4)
                out[sel] += ww[sel, None] * (Ph[sel] @ M.T)[:, :3]
        return out
