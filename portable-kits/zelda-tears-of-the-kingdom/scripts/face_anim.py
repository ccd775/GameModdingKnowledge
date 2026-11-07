"""Evaluate TotK player face animations (FSKA) on the face bones, in Head space.

pose(anim, frame) -> {bone: skin matrix S = W_pose @ inv(W_rest)} for every face bone, with Head and its ancestors at rest
(face anims are layered on top of the body: only the face-bone locals change).
"""
import json, math, os, pickle, re, sys
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import fska
from retarget import quat_to_mat

WORK_ROOT = os.environ.get('TOTK_WORK') or '<set TOTK_WORK>'   # portable kit: the work tree (see the kit README)
ANIM_FILE = os.path.join(WORK_ROOT, 'romfs_anim', 'Model', 'Player_Animation.anim.bfres')
SKEL_JSON = os.path.join(WORK_ROOT, 'work', 'anim_skel.json')   # TotkMdl info of Player_Animation.Skeleton.bfres.mc
CACHE = os.path.join(WORK_ROOT, 'work', 'face_anims.pkl')
FACE_RX = re.compile(r'^(Cheek_|Chin|Lip_|Teeth_|Eye|Eyebrow_|Eyelid_|Nose|Face_Root)')


def euler_mat(x, y, z):
    cx, sx, cy, sy, cz, sz = math.cos(x), math.sin(x), math.cos(y), math.sin(y), math.cos(z), math.sin(z)
    Rx = np.array([[1, 0, 0], [0, cx, -sx], [0, sx, cx]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    Rz = np.array([[cz, -sz, 0], [sz, cz, 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


class Skeleton:
    def __init__(self, path=SKEL_JSON):
        bones = json.load(open(path))['models'][0]['bones']
        self.names = [b['name'] for b in bones]
        self.idx = {n: i for i, n in enumerate(self.names)}
        self.parent = [b['parent'] for b in bones]
        self.local = []
        for b in bones:
            L = np.eye(4); L[:3, :3] = quat_to_mat(b['quat']) * np.array(b['scale'])[None, :]; L[:3, 3] = b['pos']
            self.local.append(L)
        self.world = [None] * len(bones)
        for i in range(len(bones)): self._w(i, self.local, self.world)

    def _w(self, i, local, out):
        if out[i] is not None: return out[i]
        p = self.parent[i]
        out[i] = local[i] if p < 0 else self._w(p, local, out) @ local[i]
        return out[i]

    def posed(self, overrides):
        """overrides: {bone: local 4x4}; returns world matrices list."""
        local = [overrides.get(n, self.local[i]) for i, n in enumerate(self.names)]
        out = [None] * len(local)
        for i in range(len(local)): self._w(i, local, out)
        return out


def load_face_anims():
    if os.path.exists(CACHE): return pickle.load(open(CACHE, 'rb'))
    r = fska.Reader(open(ANIM_FILE, 'rb').read())
    A = [a for a in r.anims(lambda n: bool(n and FACE_RX.match(n))) if any(b['curves'] for b in a['bones'])]
    pickle.dump(A, open(CACHE, 'wb'))
    return A


def bone_local(b, t, rest_local):
    """Local matrix of animated bone b at frame t (curves override base; missing parts from base, then rest)."""
    rot = list(b['base'].get('rotate', (None,) * 4))[:3]
    tr = list(b['base'].get('translate', (None,) * 3))
    for c in b['curves']:
        o = c['offset']
        if 0x20 <= o <= 0x28: rot[(o - 0x20) // 4] = fska.eval_curve(c, t)
        elif 0x10 <= o <= 0x18: tr[(o - 0x10) // 4] = fska.eval_curve(c, t)
    L = rest_local.copy()
    if all(v is not None for v in rot): L[:3, :3] = euler_mat(*rot)
    if all(v is not None for v in tr): L[:3, 3] = tr
    return L


def pose(skel, anim, t):
    ov = {}
    for b in anim['bones']:
        if b['name'] in skel.idx: ov[b['name']] = bone_local(b, t, skel.local[skel.idx[b['name']]])
    W = skel.posed(ov)
    return {n: W[i] @ np.linalg.inv(skel.world[i]) for i, n in enumerate(skel.names) if FACE_RX.match(n)}
