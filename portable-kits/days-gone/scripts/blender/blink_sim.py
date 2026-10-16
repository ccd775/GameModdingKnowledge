# Face-joint skinning simulation on a build.blend (Blender 4.2 background, numpy only): what Deacon's face anims do
# to Karin's mesh. Shared by blink_rig.py.
#
# Every face_* joint is a child of Head and its retarget mode is AnimationRelative, so in game its local transform is
# (anim rotation, anim translation + Karin rest - Deacon rest). A face mood is additive (local space): delta rotation
# q_mood * q_base^-1 and delta translation t_mood - t_base against dcn_ref_pose frame 0, applied in Head space. With
# Karin's rest joint position p (Head space), a vertex skinned to joint j moves by (dR_j - I)(v - p_j) + dt_j.
import sys, json, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # the kit's scripts/
import refskel, anim_pertrack

FLIP = np.array([1.0, -1.0, 1.0])          # UE component space <-> Blender (x, -y, z)


def qmat(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def qmul(a, b):
    x1, y1, z1, w1 = a; x2, y2, z2, w2 = b
    return np.array([w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2, w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                     w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2, w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2])


class Rig:
    """Head frame and Karin's face joint rest positions from the cooked mesh, Deacon's skeleton names for anim tracks"""
    def __init__(self, cooked_mesh, skel_json):
        rs = refskel.read(cooked_mesh)
        self.names, C = rs["names"], rs["component"]
        ix = {n: i for i, n in enumerate(self.names)}
        H = C[ix["Head"]]
        self.head_R = H[:3, :3] / np.linalg.norm(H[:3, :3], axis=0)     # Head local axes (columns) in UE space
        self.head_t = H[:3, 3]
        self.joint_pos = {n: C[i][:3, 3] for n, i in ix.items()}         # UE component space
        self.skel_names = [b["name"] for b in json.load(open(skel_json))["bones"]]

    def axis_blender(self, local_axis):
        """a Head-local direction as a Blender-space vector"""
        return (self.head_R @ np.asarray(local_axis, float)) * FLIP

    def mood_deltas(self, anim, base, frame=-1, base_frame=0):
        """{joint: (dR 3x3, dt 3) in Head space} of anim[frame] against base[base_frame] (both decoded by anim_pertrack)"""
        A = {self.skel_names[t["bone_index"]]: t for t in anim["tracks"]}
        Bs = {self.skel_names[t["bone_index"]]: t for t in base["tracks"]}
        out = {}
        for n, t in A.items():
            if n not in Bs or not (n.startswith("face_") or n in ("Jaw", "LeftEye", "RightEye")):
                continue
            b = Bs[n]
            q = qmul(t["q"][frame], b["q"][base_frame] * np.array([-1, -1, -1, 1.0]))
            out[n] = (qmat(q / np.linalg.norm(q)), t["t"][frame] - b["t"][base_frame])
        return out

    def displacement(self, co_blender, weights, deltas):
        """per-vertex displacement (Blender space) of LBS with the face joint deltas; weights = list of {bone: w}"""
        Rh = self.head_R
        disp = np.zeros_like(co_blender)
        cache = {}
        for n, (dR, dt) in deltas.items():
            if n not in self.joint_pos:
                continue
            # Head-space delta -> UE component space: v' = Rh dR Rh^T (v - p) + p + Rh dt
            Rc = Rh @ dR @ Rh.T
            cache[n] = (Rc, self.joint_pos[n], Rh @ dt)
        for i, wd in enumerate(weights):
            v = co_blender[i] * FLIP
            acc = np.zeros(3)
            for n, w in wd.items():
                c = cache.get(n)
                if c is None:
                    continue
                Rc, p, t = c
                acc += w * ((Rc - np.eye(3)) @ (v - p) + t)
            disp[i] = acc * FLIP
        return disp
