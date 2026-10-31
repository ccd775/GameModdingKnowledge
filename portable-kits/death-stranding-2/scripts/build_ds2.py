"""Build Karin_Original -> Death Stranding 2 Sam (Porter body variant, group 50108) replacement meshes and pages.

Slots (all in group 50108, skeleton 50118:0, LOD0/1/2 = meshes 144/73/392 and boots 218/364/90, 453/614/194):
  head  (face, hair, ears)          -> body mesh primitive with the gloves material  (page A -> texture 0x180)
  feet  (shoes, feet below ankles)  -> boot meshes, right / left                     (page B -> texture 0x8)
  body  (everything else)           -> body mesh primitive with the body material    (page B -> texture 0x10)
  coat  (skirt, tail)               -> Porter's long coat 50110:234/124/73, coat material primitive (page C -> 50110 0xE8);
                                       weighted to the coat's Cloth_PBD particles so they swing with its simulation
  hair  (ears, bangs, side locks)   -> Sam's hair cover 50121 LodMesh 82 (meshes 85/38/27/56, skeleton 67700), hair
                                       material; weighted to the Hair_PBD particles around the skull; texture pieces
                                       go into the free space of Sam's hair atlas (group 67704, tool key A60)
  face  (with --face only)          -> Sam's face skin 50120 LodMesh 1 LOD2..4 (186/229/45, skeleton 67711, his skin
                                       material; LOD0/1 carry ZivaRT and are relinked to 186); page F replaces his face
                                       textures (group 67673, tool key F9A); mouth and eyelids are weighted to the
                                       facial joints that DS2's rig moves for "mouth open" / "eye closed", fitted to
                                       Karin's own shape keys (face_motion.json from face_motion.py)
Every other Porter mesh is collapsed (vertex/index counts kept); see make_mod_ds2.ps1 for the import.

Outputs in --work: ascii/*.ascii, jobs.json, page_A/B/C.png, rough_A/B/C.png, hair_<tex>.png, fit_report.json
"""
import argparse
import json
import os
import re
import sys
import time

import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import distance_transform_edt
from scipy.spatial import cKDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import ds2ascii as H  # noqa: E402
import fit_ds2 as F  # noqa: E402
from atlas import build_page  # noqa: E402
from vrm import Vrm  # noqa: E402

# ---------------------------------------------------------------- Porter layout (build-sensitive, DS2.exe 1.0.48.0)
BODY_MESH = {0: 144, 1: 73, 2: 392}
BOOT_MESH = {'R': {0: 218, 1: 364, 2: 90}, 'L': {0: 453, 1: 614, 2: 194}}
BODY_FILE, BOOT_FILE = '7E9D_8.ascii', {'R': '7E9D_1.ascii', 'L': '7E9D_3.ascii'}
COAT_MESH, COAT_FILE = {0: 234, 1: 124, 2: 73}, '47CD_0.ascii'   # group 50110, skeleton 50118:0
HAIR_MESH = {0: 85, 1: 38, 2: 27, 3: 56}   # group 50121 LodMesh 82 (Sam's hair cover part 0), skeleton 67700:0
SKEL_FILES = {'47CC': '47CC_skel_0.ascii', '47CD': '47CD_skel_26.ascii', '19FF': '19FF_skel_0.ascii',
              '1A0C': '1A0C_skel_0.ascii', 'B6B': 'B6B_skel_301.ascii'}
# equipped boots (--boot-ref): boot item 11's uppers in the player group 31123 (tool key B6B, skeleton 31123:301, same
# inverse bind matrices as Porter's boots for their six joints). Karin's shoes (the R / L slots) are padded to each
# mesh's vertex / triangle count, so only the mesh streams change and 31123's 130 MB core stays out of the package
# (make_mod_ds2.ps1 checks); every other boot part links to these (make_links.sh v10)
BOOT_ITEM_MESH = {'L': {0: 33600, 1: 5899, 2: 30270}, 'R': {0: 29579, 1: 17027, 2: 37070}}
# player-group hair (also --boot-ref): parts 3800 / 4000 / 15014 / 13272 of ArtPartsModel 31123:38907 (skeleton 474),
# Sam's hair with its own fuzz textures. v32 took them for the shower hair; it wasn't (that is the scene stand-in 12706,
# collapsed by build_karin.ps1), but they stay collapsed in place (stream-only) in case another state shows them.
SHOWER_HAIR = {0: (32944, 20532, 20239, 29705), 1: (42268, 33301, 21339, 32826), 2: (19018, 18908, 42223, 35858),
               3: (24183, 44434, 34876, 7562)}
# paint-atlas UV for every Karin vertex (extra_uvs): the atlas corner farthest from the vanilla charts (painted charts
# bleed a few texels, and the atlas keeps the stains Sam gathered in the save), pushed 2 out on each axis so her
# triangles stay off the atlas while wrap, mirror and clamp addressing all still sample that corner texel
PAINT_INSET, PAINT_RES = 0.5 / 256, 256
HIPS, HEAD = 'JNT_C_B_001_Hips', 'JNT_C_B_008_Head'
# Sam's hair atlas (texture set 67704:0, tool key A60): (texture, size, what Karin's pieces get there)
HAIR_TEX = {'2': (2048, 'colour'), '8': (4096, 'alpha'), '10': (1024, 'normal'), '7': (2048, 'median'),
            'F': (2048, 'median'), '1': (256, 'median'), '3': (512, 'median')}

# ---------------------------------------------------------------- Karin_Original (case constants, same model as HFW)
HEAD_BONES = ('head', 'leftEye', 'rightEye', 'jaw')
COVERED_BODY = ('body_2', 'knee-socks')
COVER_MARGIN = 1.0
LEG_BONES = tuple(f'{s}{b}' for s in ('left', 'right') for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes'))
FOOT_BONES = ('leftFoot', 'leftToes', 'rightFoot', 'rightToes')
SKIRT_MAX_LEG = 0.45
HEAD_MESHES = {'Body', 'hair', 'kemomimi'}        # page A, gloves material primitive
FEET_MESHES = {'shoes'}
CLOTH_MESHES = {'skirt', 'tail'}                  # page C, coat material primitive
CLOTH_SIGMA, CLOTH_ARC_R = 6.0, 20.0              # cm: particle blend, Gaussian in (arc length around the body, height)
# particle rows the skirt waist / hem follow (coat rows ~8 cm apart). v12 ran the hem down to the z 70 row at full
# weight: running knees pushed the long coat's front flaps forward and the skirt stretched down flat like an apron.
# Now upper rows only, at most 0.8, and the front third mostly keeps the thigh weights.
SKIRT_CLOTH_Z = (107.0, 85.0)
SKIRT_CLOTH_MAX, SKIRT_FRONT_CLOTH = 0.8, 0.25
TAIL_CLOTH_Z = (99.0, 60.0)                       # back-centre particle rows the tail root / tip follow
# v12-v14: with the 6 cm row blend every tail ring followed mostly one particle row, and the rows' differing motion
# left dark spots one row apart along the tail in shade; 14 cm blends three to four rows
TAIL_SIGMA_Z = 14.0
TWIN_BELT_Z = (129.0, 112.0)                      # Belt_PBD heights the twin tails' middle / tips follow
# hair slot: ears, bangs and side locks (Karin bone chains) on Sam's Hair_PBD particles; root on the head, the part
# past HAIR_U0 of the way from the chain's root node to its tip nodes blends to the particles nearest each vertex
# (Gaussian in cm), at most HAIR_CLOTH_MAX. The way along is geometric: the ear chains have two bones only.
HAIR_SLOT_MESHES = {'kemomimi'}
# True: ears, bangs and side locks on the head page with the rest of her head, rigid on the head (v26). In a long save
# the game greys the body, coat and gloves materials (vanilla Sam is caked in grey dust there too); the hair material
# only where its paint mask allows (make_dds AA4 2), which v15-v25 left white in the cells her pieces use. With the
# mask open (v27) they stay here on the Hair_PBD particles and grey with the rest; True empties Sam's hair LodMesh and
# keeps its atlas alpha 0 everywhere.
HAIR_ON_HEAD = False
HAIR_SLOT_MATS = {'Karin_Hair', 'Karin_Hair_Transparent'}
HAIR_CHAINS = {'Ear_L': ('Ear_L', ('Ear_L.001_end',)), 'Ear_R': ('Ear_R', ('Ear_R.001_end',)),
               'Hair_front': ('Hair_front_root', ('Hair_front_L_end', 'Hair_front_001_end', 'Hair_front_R_end')),
               'Hair_side_L': ('Hair_side_L', ('Hair_side_L.002_end',)),
               'Hair_side_R': ('Hair_side_R', ('Hair_side_R.002_end',))}
HAIR_U0, HAIR_UW, HAIR_CLOTH_MAX, HAIR_SIGMA = 0.15, 0.6, 0.8, 4.0
# ears: each Hair_PBD joint is the tip of one of Sam's hair strands (hair PBD body 67699:2, 34 ribbons of 4 x 2
# points hanging from the crown), its frame turned by the ribbon's last segment. The ear tips stand ~20 cm above those
# tips: when a strand tip lags back the frame tilts forward and the ear tip flicked forward about twice as far, the wrong
# way (v15-v18 "twitching"). Now each ear follows one mix of its HAIR_EAR_N nearest particles (Gaussian about the ear
# root), the same for all its vertices, from the root up (HAIR_EAR_UW of the way to full), and those particles only
# lend their position: their inverse bind matrices scale about the particle by HAIR_EAR_SCALE (stored vertex positions
# compensate, see the hair job), so a vertex follows the strand tips' lag with a lever of a few cm instead of 20.
# Bangs and side locks keep turning with the other particles.
HAIR_EAR_SIGMA, HAIR_EAR_N, HAIR_EAR_UW, HAIR_EAR_MAX, HAIR_EAR_SCALE = 7.0, 4, 0.6, 0.9, 0.02
# how far those strands may swing: their points' MaxDistance (from the animated pose, ~0.5 cm mid-strand, 3-4 cm at the
# tip) times HAIR_EAR_SWING, and the body's procedural fluctuation off (made the ears tremble). Core-only patches of the
# hair PBD body 67699:2 (Sam's own hair cards are transparent), written to <work>/fields.json for make_mod_ds2.ps1.
HAIR_EAR_SWING = 2.0
HAIR_PBD_BODY = (67699, 2)
# face slot (--face): Karin's face primitive, Sam's face skin LODs, and per RigLogic control (face_motion.json) the
# Karin shape key it should reproduce and the facial joints (name pattern) a vertex may follow. A vertex follows the
# one joint that best reproduces its shape-key delta, with w = clamp(<S, D> / <D, D>, 0, 1); the rest stays on Head.
FACE_PRIM = ('Body', 'Karin_Face')
# anime face shading (both builds): her normals diffused over ~FACE_NRM_RADIUS (nose, mouth and eye sockets stop
# shading themselves), blended back to her own normals within FACE_NRM_BLEND of the face's outer edge (jaw / hairline
# seams). The face build also stops the face skin meshes casting shadows (DrawFlags bits 0-1, EShadowCastMode 3 -> 0,
# as Sam's 0x...48 meshes), so the nose throws none on her lip.
FACE_NRM_RADIUS, FACE_NRM_BLEND = 3.0, 1.5
FACE_MESH = {2: 186, 3: 229, 4: 45}
FACE_FITS = {'jaw': ('kuchi_A', r'Chin|LipLower|LipCorner|LipUpper|Jawline|UnderChin|Teeth|Tongue'),
             'blink_L': ('blink_L', r'_F_\d+_(Eyelid|Eyelashes|EyeCorner|EyeLashes)'),
             'blink_R': ('blink_R', r'_F_\d+_(Eyelid|Eyelashes|EyeCorner|EyeLashes)')}
# Karin's lids travel ~4 cm, Sam's lid joints ~1.2 cm (a 44 deg turn about the eyeball centre). Lever (ACS face_rig.py):
# this joint's inverse bind matrix is shifted by u (forward / up, searched on FACE_LEVER_GRID) and each lid vertex with
# weight w on it is stored at v - w u; at rest the game puts the joint back so the vertex is at v, and the turn moves it
# by w (R - I)(v - c + (1 - w) u): the lever turns the small rotation into the long slide of her lid.
# Lever candidates per control, the best fit wins. The blink is raw control 10 / 11 (eyeBlink, MetaHuman order; v17f
# fitted 32 / 33 = eyeLookDown by mistake and closed a third). EyelidUpperA turns 32 deg on a blink but 44 on a full
# look down, EyelidUpperB_002 25 / 7: on A her lids would also close whenever Sam looks down.
FACE_LEVER = {f'blink_{s}': tuple(f'JNT_{s}_F_00{i}_EyelidUpper{ab}' for i in range(4) for ab in 'AB') for s in 'LR'}
# lever u (cm, model space: sideways x, forward y, up z); a longer lever also magnifies the joint's other turns (lid
# twist when the eyes look aside)
FACE_LEVER_GRID = [np.array([sx, fwd, upz]) for sx in np.arange(-6.0, 6.01, 3.0) for fwd in np.arange(0.0, 60.01, 3.0)
                   for upz in np.arange(-8.0, 8.01, 2.0)]
# face_motion.json eyeLookDown / Left / Right and the full 1.0 blink, reported per blink fit: how far each closes her
# lid (along the shape key) and the 95th percentile lid vertex travel (cm)
FACE_DIAG = {f'blink_{s}': (f'look_{s}', f'lookl_{s}', f'lookr_{s}', f'blink1_{s}') for s in 'LR'}
# Sam's face textures (group 67673, tool key F9A): set 3 is the base (wm0), sets 0-2 the wrinkle-map variants the skin
# shader blends towards in expressions; all colours get Karin's face and all normals go flat, so the blend is a no-op
FACE_TEX = {'1E': (2048, 'colour'), '17': (2048, 'colour'), '1F': (2048, 'colour'), '1C': (2048, 'colour'),
            '4': (4096, 'normal'), '1A': (1024, 'normal'), '14': (1024, 'normal'), '13': (1024, 'normal'),
            '1B': (512, 'median'), '5': (512, 'median'), '1D': (1024, 'median'), '6': (512, 'median')}
# Texture set "Roughness" channel; higher reads glossier in game (vanilla Porter fabric p50 82, Sam's face p50 156; cloth
# at 170 showed hard highlights on the skirt and socks in v1-v5).
ROUGH = {'Karin_Body': 115, 'Karin_Face': 115, 'Karin_Costume': 60, 'Karin_Hair': 100, 'shoes': 90}
COVER_RULES = [   # (mesh, covering meshes, max distance cm in source scale)
    ('body_2', ('pullover', 'underwear', 'skirt', 'knee-socks', 'shoes'), 4.0),
    ('underwear', ('pullover', 'skirt'), 3.0),
]


DOUBLE_SIDED = {'skirt'}          # seen from inside when the camera is low
SUBDIVIDE = {'tail': 2}           # coarse curved surfaces: in-game shadows cut blotches into low-poly geometry
PHONG_ALPHA = 0.75


def subdivide(p, levels):
    """Splits every triangle into four, levels times; edge midpoints are Phong-tessellated so the surface rounds
    out instead of staying faceted. Weights of a midpoint are the endpoint average, top four kept."""
    for _ in range(levels):
        P, N, UV, J, W, T = p['pos'], p['normal'], p['uv'], p['joints'], p['weights'], p['tris']
        edges = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
        uniq, inv = np.unique(edges, axis=0, return_inverse=True)
        a, b = uniq[:, 0], uniq[:, 1]
        m = (P[a] + P[b]) / 2
        pa = m - ((m - P[a]) * N[a]).sum(1, keepdims=True) * N[a]
        pb = m - ((m - P[b]) * N[b]).sum(1, keepdims=True) * N[b]
        Pm = (1 - PHONG_ALPHA) * m + PHONG_ALPHA * (pa + pb) / 2
        Nm = N[a] + N[b]
        Nm /= np.linalg.norm(Nm, axis=1, keepdims=True).clip(1e-12)
        Jm, Wm = np.zeros((len(uniq), 4), J.dtype), np.zeros((len(uniq), 4), W.dtype)
        for e in range(len(uniq)):
            acc = {}
            for v in (a[e], b[e]):
                for j, w in zip(J[v], W[v]):
                    if w > 0:
                        acc[j] = acc.get(j, 0.0) + w / 2
            top = sorted(acc.items(), key=lambda t: -t[1])[:4]
            s = sum(w for _, w in top)
            for k, (j, w) in enumerate(top):
                Jm[e, k], Wm[e, k] = j, w / s
        n = len(P)
        mid = n + inv.reshape(3, -1).T          # columns: ab, bc, ca
        ab, bc, ca = mid[:, 0], mid[:, 1], mid[:, 2]
        p['tris'] = np.concatenate([np.stack([T[:, 0], ab, ca], 1), np.stack([ab, T[:, 1], bc], 1),
                                    np.stack([ca, bc, T[:, 2]], 1), np.stack([ab, bc, ca], 1)])
        p['pos'], p['normal'] = np.concatenate([P, Pm]), np.concatenate([N, Nm])
        p['uv'] = np.concatenate([UV, (UV[a] + UV[b]) / 2])
        p['joints'], p['weights'] = np.concatenate([J, Jm]), np.concatenate([W, Wm])


def double_side(p):
    """Back faces as separate triangles with reversed winding and flipped normals."""
    n = len(p['pos'])
    p['tris'] = np.concatenate([p['tris'], p['tris'][:, ::-1] + n])
    p['normal'] = np.concatenate([p['normal'], -p['normal']])
    for k in ('pos', 'uv', 'joints', 'weights'):
        p[k] = np.concatenate([p[k], p[k]])


def keep_triangles(p, keep):
    used, inv = np.unique(p['tris'][keep], return_inverse=True)
    for k in ('pos', 'normal', 'uv', 'joints', 'weights'):
        if p.get(k) is not None:
            p[k] = p[k][used]
    if 'morph' in p:
        p['morph'] = {k: v[used] for k, v in p['morph'].items()}
    p['tris'] = inv.reshape(-1, 3)


def hide_under_cover(prims, anc_cache):
    body, cover = COVERED_BODY
    socks = [p for p in prims if p['mesh'] == cover]
    top = min(p['pos'][:, 1].max() for p in socks) * 100.0 - COVER_MARGIN
    dropped = 0
    for p in prims:
        if p['mesh'] != body:
            continue
        dom = p['joints'][np.arange(len(p['pos'])), p['weights'].argmax(1)]
        leg = np.isin(np.vectorize(anc_cache.get, otypes=[object])(dom), LEG_BONES)
        hidden = leg & (p['pos'][:, 1] * 100.0 < top)
        keep = ~hidden[p['tris']].all(1)
        dropped += int((~keep).sum())
        keep_triangles(p, keep)
    return dropped


def _cone(n, deg, k):
    a = np.cross(n, [0.0, 1.0, 0.0])
    if np.linalg.norm(a) < 1e-3:
        a = np.cross(n, [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    b = np.cross(n, a)
    t = np.radians(deg)
    ph = np.linspace(0, 2 * np.pi, k + 1)[:-1]
    ring = np.cos(t) * n + np.sin(t) * (np.cos(ph)[:, None] * a + np.sin(ph)[:, None] * b)
    return np.concatenate([n[None], ring])


def enclosed(P, N, tri_xyz, dist, cone_deg=40.0, rays=6):
    """Per vertex: every ray of a cone around its normal hits one of the triangles within dist."""
    v0 = tri_xyz[:, 0]
    e1 = tri_xyz[:, 1] - v0
    e2 = tri_xyz[:, 2] - v0
    C = tri_xyz.mean(1)
    reach = dist + np.linalg.norm(tri_xyz - C[:, None], axis=2).max()
    tree = cKDTree(C)
    out = np.zeros(len(P), bool)
    for i, cand in enumerate(tree.query_ball_point(P, reach)):
        if not cand:
            continue
        c = np.asarray(cand)
        d = _cone(N[i], cone_deg, rays)[:, None, :]
        pv = np.cross(d, e2[c][None])
        det = (e1[c][None] * pv).sum(2)
        ok = np.abs(det) > 1e-12
        inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
        tv = P[i] - v0[c]
        u = (tv[None] * pv).sum(2) * inv
        qv = np.cross(tv, e1[c])
        w = (qv[None] * d).sum(2) * inv
        t = (e2[c] * qv).sum(1)[None] * inv
        hit = ok & (u >= 0) & (w >= 0) & (u + w <= 1) & (t > 1e-6) & (t < dist)
        out[i] = hit.any(1).all()
    return out


def hide_covered(prims, rules):
    out = {}
    for mesh, covers, dist in rules:
        targets = [p for p in prims if p['mesh'] == mesh]
        cov = [p for p in prims if p['mesh'] in covers]
        X = np.concatenate([p['pos'][p['tris']] for p in cov])
        n = 0
        for p in targets:
            hidden = enclosed(p['pos'], p['normal'], X, dist / 100.0)
            keep = ~hidden[p['tris']].all(1)
            n += int((~keep).sum())
            keep_triangles(p, keep)
        out[mesh] = n
    return out


# ---------------------------------------------------------------- weights
def region_roots():
    r = {'JNT_C_B_001_Hips': 'torso', 'JNT_C_B_006_Neck': 'neck', 'JNT_C_B_008_Head': 'head'}
    for k in range(2, 6):
        r[f'JNT_C_B_00{k}_Spine'] = 'torso'
    r['JNT_C_B_007_Neck'] = 'neck'
    for S in ('L', 'R'):
        r.update({f'JNT_{S}_B_000_Shoulder': 'torso', f'JNT_{S}_B_001_Arm': f'{S}_upper', f'JNT_{S}_B_002_Arm': f'{S}_fore',
                  f'JNT_{S}_B_003_Hand': f'{S}_hand', f'JNT_{S}_B_100_Leg': f'{S}_thigh', f'JNT_{S}_B_101_Leg': f'{S}_shin',
                  f'JNT_{S}_B_102_Foot': f'{S}_foot'})
    return r


REGION_ROOTS = region_roots()
HUMAN_REGION = {'hips': 'torso', 'spine': 'torso', 'chest': 'torso', 'upperChest': 'torso', 'neck': 'neck',
                'leftShoulder': 'torso', 'rightShoulder': 'torso',
                'leftUpperArm': 'L_upper', 'leftLowerArm': 'L_fore', 'leftHand': 'L_hand',
                'rightUpperArm': 'R_upper', 'rightLowerArm': 'R_fore', 'rightHand': 'R_hand',
                'leftUpperLeg': 'L_thigh', 'leftLowerLeg': 'L_shin', 'leftFoot': 'L_foot', 'leftToes': 'L_foot',
                'rightUpperLeg': 'R_thigh', 'rightLowerLeg': 'R_shin', 'rightFoot': 'R_foot', 'rightToes': 'R_foot'}


def is_pbd(name):
    return 'PBD' in name or 'Pbd' in name


def bone_region(names, parents, b):
    while b >= 0:
        if names[b] in REGION_ROOTS:
            return REGION_ROOTS[names[b]]
        b = parents[b]
    return None


class Donors:
    """Vanilla Sam LOD0 vertices (PBD weights removed) grouped by body region."""

    def __init__(self, meshes, names, parents, k=4):
        nb = len(names)
        pbd = np.array([is_pbd(n) for n in names])
        P, W = [], []
        for m in meshes:
            for pos, bi, bw in zip(m['pos'], m['bi'], m['bw']):
                w = np.zeros(nb)
                for b, x in zip(bi, bw):
                    if x == x and x > 0:
                        w[b] += x
                w[pbd] = 0
                s = w.sum()
                if s < 0.4:
                    continue
                P.append(pos * 100.0)
                W.append(w / s)
        P, W = np.array(P), np.array(W)
        reg = np.array([bone_region(names, parents, int(np.argmax(w))) for w in W], dtype=object)
        self.k = k
        self.pools = {}
        for r in set(reg) - {None}:
            sel = reg == r
            self.pools[r] = (cKDTree(P[sel]), W[sel])

    def query(self, region, X):
        tree, W = self.pools[region]
        d, i = tree.query(X, k=self.k)
        wd = 1.0 / np.maximum(d, 0.3) ** 2
        wd /= wd.sum(1, keepdims=True)
        return np.einsum('vk,vkb->vb', wd, W[i])


def map_weights(p, vrm_names, human_nodes, donors, idx, skirt_z, nb, J_cm):
    """Per Karin influence: humanoid region -> nearest vanilla donors of that region (weights incl. procedural
    helper joints); fingers / head direct; skirt panels between the waist and the thighs; tail on the hips."""
    P = p['P']
    acc = np.zeros((len(P), nb))
    for k in range(4):
        jk = p['joints'][:, k]
        wk = p['weights'][:, k]
        for j in np.unique(jk[wk > 0]):
            sel = np.where((jk == j) & (wk > 0))[0]
            w = wk[sel]
            x = P[sel]
            name = vrm_names[j]
            h = p['hanc_of'][j]
            if name.startswith('Skirt'):
                zw, zh = skirt_z
                t = np.clip((zw - x[:, 2]) / max(zw - zh, 1e-3), 0, 1)
                a = SKIRT_MAX_LEG * t * t * (3 - 2 * t)
                s_left = 1 / (1 + np.exp(x[:, 0] / 4.0))     # model left is -x
                acc[sel] += (w * (1 - a))[:, None] * donors.query('torso', x)
                acc[sel] += (w * a * s_left)[:, None] * donors.query('L_thigh', x)
                acc[sel] += (w * a * (1 - s_left))[:, None] * donors.query('R_thigh', x)
            elif name.startswith('Tail') or (h == 'hips' and j != human_nodes['hips']):
                acc[sel, idx[HIPS]] += w
            elif h in HEAD_BONES:
                acc[sel, idx[HEAD]] += w
            elif h in F.HUMAN2GOT and h not in HUMAN_REGION:   # fingers
                acc[sel, F.HUMAN2GOT[h]] += w
            elif HUMAN_REGION.get(h) == 'neck' and 'neck' not in donors.pools:
                # Porter's body meshes carry no neck skin (it lives in the shared head groups): blend the two
                # neck joints by height between the lower neck joint and the head joint
                n0, n1 = idx['JNT_C_B_006_Neck'], idx['JNT_C_B_007_Neck']
                t = np.clip((x[:, 2] - J_cm[n0, 2]) / (J_cm[idx[HEAD], 2] - J_cm[n0, 2]), 0, 1)
                acc[sel, n0] += w * (1 - t)
                acc[sel, n1] += w * t
            elif h in HUMAN_REGION:
                acc[sel] += w[:, None] * donors.query(HUMAN_REGION[h], x)
            else:
                raise ValueError(f'no Sam joint for {name} (humanoid {h})')
    return acc


def smoothstep(t):
    t = np.clip(t, 0, 1)
    return t * t * (3 - 2 * t)


def cloth_weights(theta, zt, part, part_pos, centre, nb, sigma_z=CLOTH_SIGMA):
    """Particles around the body axis at angle theta (atan2(x, y) about centre) and height zt, Gaussian-blended."""
    pth = np.arctan2(part_pos[:, 0] - centre[0], part_pos[:, 1] - centre[1])
    dth = (theta[:, None] - pth[None] + np.pi) % (2 * np.pi) - np.pi
    d2 = (dth * CLOTH_ARC_R / CLOTH_SIGMA) ** 2 + ((zt[:, None] - part_pos[None, :, 2]) / sigma_z) ** 2
    w = np.exp(-(d2 - d2.min(1, keepdims=True)))
    out = np.zeros((len(theta), nb))
    out[:, part] = w / w.sum(1, keepdims=True)
    return out


def chain_param(p, names, parent, prefix):
    """Per vertex: skin weight m on the bone chain whose names start with prefix, and u = 0 at the chain root ..
    1 at its tip (weighted bone depth along the chain)."""
    def depth(j):
        d = -1
        while j >= 0 and names[j].startswith(prefix):
            d += 1
            j = parent[j]
        return max(d, 0)
    on = np.vectorize(lambda j: names[j].startswith(prefix))(p['joints'])
    dep = np.vectorize(depth)(p['joints'])
    w = np.where(on, p['weights'], 0.0)
    m = w.sum(1)
    if not (w > 0).any():
        return m, np.zeros(len(m))
    return m, (dep * w).sum(1) / np.maximum(m, 1e-9) / max(dep[w > 0].max(), 1)


def anime_face_normals(p):
    """Smooth p['N'] in place (see FACE_NRM_RADIUS); returns (diffusion steps, outer edge vertices)."""
    from scipy import sparse
    from scipy.sparse.csgraph import connected_components
    from scipy.spatial import cKDTree
    _, inv = np.unique(np.round(p['P'] * 1000).astype(np.int64), axis=0, return_inverse=True)
    inv = inv.ravel()
    nw = inv.max() + 1
    T = inv[p['tris']]
    e = np.sort(np.concatenate([T[:, [0, 1]], T[:, [1, 2]], T[:, [2, 0]]]), 1)
    e, cnt = np.unique(e[e[:, 0] != e[:, 1]], axis=0, return_counts=True)
    adj = sparse.coo_matrix((np.ones(2 * len(e)), (np.r_[e[:, 0], e[:, 1]], np.r_[e[:, 1], e[:, 0]])),
                            shape=(nw, nw)).tocsr()
    Pw = np.zeros((nw, 3))
    Pw[inv] = p['P']
    N0 = np.zeros((nw, 3))
    np.add.at(N0, inv, p['N'])
    N0 /= np.linalg.norm(N0, axis=1, keepdims=True).clip(1e-12)
    step = float(np.median(np.linalg.norm(Pw[e[:, 0]] - Pw[e[:, 1]], axis=1)))
    k = int(min(400, (FACE_NRM_RADIUS / max(step, 1e-3)) ** 2))
    N = N0.copy()
    for _ in range(k):
        N = N + adj @ N
        N /= np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
    b = e[cnt == 1]                                  # boundary edges; the longest loop is the outer edge
    bg = sparse.coo_matrix((np.ones(len(b)), (b[:, 0], b[:, 1])), shape=(nw, nw))
    _, lab = connected_components(bg, directed=False)
    bv = np.unique(b)
    outer = bv[lab[bv] == np.bincount(lab[bv]).argmax()]
    t = smoothstep(cKDTree(Pw[outer]).query(Pw)[0] / FACE_NRM_BLEND)[:, None]
    Nf = (1 - t) * N0 + t * N
    p['N'] = (Nf / np.linalg.norm(Nf, axis=1, keepdims=True).clip(1e-12))[inv]
    return k, len(outer)


def restrict(acc, allowed, parents):
    """Move weight on joints outside a slot mesh's JointIndexList to their nearest allowed ancestor."""
    allowed = set(allowed)
    out = np.zeros_like(acc)
    for j in np.nonzero(acc.any(0))[0]:
        a = j
        while a >= 0 and a not in allowed:
            a = parents[a]
        if a < 0:
            raise ValueError(f'joint {j} has no allowed ancestor')
        out[:, a] += acc[:, j]
    return out


def quantize(acc, nmax):
    top = np.argsort(-acc, axis=1)[:, :nmax]
    tw = np.take_along_axis(acc, top, 1)
    tw[tw < 0.5 / 255] = 0
    s = tw.sum(1, keepdims=True)
    if (s <= 0).any():
        raise ValueError('vertex without weights')
    return top.astype(np.int64), tw / s


def in_atlas(u):
    u = np.asarray(u)
    return np.abs(u).max() >= 1e-6 and u.min() >= -1e-3 and u.max() <= 1 + 1e-3


_CORNERS = {}


def paint_corner(peers, k):
    """Paint-atlas corner (cx, cy) farthest from the charts of UV set k over all primitives of a mesh, and that
    distance in texels at PAINT_RES."""
    key = (tuple(p['name'] for p in peers), k)
    if key not in _CORNERS:
        img = Image.new('L', (PAINT_RES, PAINT_RES), 0)
        dr = ImageDraw.Draw(img)
        for p in peers:
            if p['nuv'] > k and in_atlas(p['uv'][k]):
                P = np.asarray(p['uv'][k]) * PAINT_RES
                for f in p['faces']:
                    dr.polygon([tuple(P[i]) for i in f], fill=255)
        d = distance_transform_edt(np.array(img) == 0)
        dist = {c: d[-1 if c[1] else 0, -1 if c[0] else 0] for c in ((0, 0), (1, 0), (0, 1), (1, 1))}
        c = max(dist, key=dist.get)
        _CORNERS[key] = c, dist[c]
        print(f'[paint] {peers[0]["name"]} uv{k}: corner {c}, {dist[c]:.0f} texels from the charts', flush=True)
    return _CORNERS[key]


def extra_uvs(tmpl, uv0, peers=None):
    """UV sets after the texture set, by what the vanilla slot mesh keeps there: constant zero stays zero; a set
    inside [0, 1] is the character paint atlas (runtime mud, blood, sand, wetness) and gets the cleanest corner of the
    atlas pushed off it (PAINT_INSET), so no paint lands on Karin; anything else (the coat's and suit's set 1) feeds
    the material's decal / detail layers and gets the vanilla median, a spot without decals. v12-v14 had the page UVs
    in every set: the coat's decal layer printed round dark spots across the white tail; v15 copied Sam's per-vertex
    set 1: faint logo strokes. v15-v22 sampled the atlas at corner (0, 0), 3-7 texels from the body and coat charts:
    in a long save the stains bled there and greyed her whole body. peers: all primitives of the mesh (one atlas)."""
    out = [uv0]
    for k in range(1, tmpl['nuv']):
        u = np.asarray(tmpl['uv'][k])
        if np.abs(u).max() < 1e-6:
            out.append(np.zeros_like(uv0))
        elif in_atlas(u):
            c, _ = paint_corner(peers or [tmpl], k)
            out.append(np.tile([x + 2 - PAINT_INSET if x else PAINT_INSET - 2 for x in c], (len(uv0), 1)))
        else:
            out.append(np.tile(np.median(u, 0), (len(uv0), 1)))
    return out


def winding_sign(pos, nrm, faces):
    """+1 when (b-a)x(c-a) points along the vertex normals (counter-clockwise seen from outside), -1 otherwise."""
    a, b, c = pos[faces[:, 0]], pos[faces[:, 1]], pos[faces[:, 2]]
    fn = np.cross(b - a, c - a)
    vn = nrm[faces].sum(1)
    return 1 if np.median(np.sign((fn * vn).sum(1))) > 0 else -1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--vrm', required=True)
    ap.add_argument('--ref', required=True, help='porter work dir: ref.json, lod0..lod2 exports')
    ap.add_argument('--coat-ref', required=True, help='coat group 50110 export dir: lod0..lod2')
    ap.add_argument('--hair-ref', required=True, help='hair group 50121 export dir: lod0..lod3')
    ap.add_argument('--hair-tex', required=True, help='vanilla hair atlas textures A60_<tex>.dds (group 67704)')
    ap.add_argument('--hair-used', required=True, help='mask (png) of the hair atlas cells vanilla hair cards use')
    ap.add_argument('--boot-ref', help='player group 31123 export dir (lod0..lod2): equipped boots carry her shoes')
    ap.add_argument('--face', action='store_true', help='face slot (expressions); without it the face stays on page A')
    ap.add_argument('--face-ref', help='face group 50120 export dir: lod2..lod4')
    ap.add_argument('--face-tex', help='vanilla face textures F9A_<tex>.dds (group 67673)')
    ap.add_argument('--face-motion', help='face_motion.json (face_motion.py)')
    ap.add_argument('--skeletons', required=True, help='dir with 47CC_skel_0.ascii etc.')
    ap.add_argument('--work', required=True)
    ap.add_argument('--scale', type=float, default=1.3)
    ap.add_argument('--head-scale', type=float, default=None)
    ap.add_argument('--neck-drop', type=float, default=0.0)
    ap.add_argument('--shoulder-fit', type=float, default=0.3)
    ap.add_argument('--arm-drop', type=float, default=2.0)
    ap.add_argument('--src-max', type=int, default=2048)
    ap.add_argument('--lods', default='0,1,2')
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    t0 = time.time()
    report = vars(args).copy()

    ref = json.load(open(os.path.join(args.ref, 'ref.json')))
    names, parents = ref['names'], ref['parents']
    idx = {n: i for i, n in enumerate(names)}
    world = np.tile(np.eye(4), (len(names), 1, 1))
    for j, w in ref['world'].items():
        world[int(j)] = np.array(w)
    world[:, :3, 3] *= 100.0      # cm
    J = world[:, :3, 3]
    F.set_skeleton(names)
    missing = [h for h, i in F.HUMAN2GOT.items() if str(i) not in ref['world']]
    if missing:
        raise SystemExit(f'no bind pose for {missing}')

    vrm = Vrm(args.vrm)
    prims = [p for p in vrm.primitives() if p['mat_name'] != 'Karin_Alpha']
    for p in prims:
        if args.face and (p['mesh'], p['mat_name']) == FACE_PRIM:
            p['morph'] = {key: vrm.morph(p, key) for key, _ in FACE_FITS.values()}
        keep_triangles(p, np.ones(len(p['tris']), bool))
    anc_cache = {j: F.humanoid_ancestor(vrm, j) or '' for j in range(len(vrm.nodes))}
    report['hidden_leg_tris'] = hide_under_cover(prims, anc_cache)
    report['hidden_covered_tris'] = hide_covered(prims, COVER_RULES)
    print('[cull]', report['hidden_leg_tris'], report['hidden_covered_tris'], flush=True)
    for p in prims:
        if p['mesh'] in SUBDIVIDE:
            n0 = len(p['tris'])
            subdivide(p, SUBDIVIDE[p['mesh']])
            print(f'[subdivide] {p["mesh"]} {n0} -> {len(p["tris"])} tris', flush=True)
        if p['mesh'] in DOUBLE_SIDED:
            double_side(p)
            print(f'[double-sided] {p["mesh"]} {len(p["tris"])} tris', flush=True)
    report['double_sided'] = sorted(DOUBLE_SIDED)
    report['subdivided'] = SUBDIVIDE

    tps, info = F.build_warp(vrm, world, scale=args.scale, head_scale=args.head_scale, neck_drop=args.neck_drop,
                             shoulder_fit=args.shoulder_fit, arm_drop=args.arm_drop, prims=prims, hands='rigid')
    report['ring_r'] = {k: round(v, 2) for k, v in info['ring_r'].items()}
    hs, hn, A_head = info['maps']['head']
    for p in prims:
        p['hanc'] = np.vectorize(anc_cache.get, otypes=[object])(p['joints'])
        P0 = F.gltf_to_got(p['pos'])
        N0 = np.stack([-p['normal'][:, 0], p['normal'][:, 2], p['normal'][:, 1]], 1)
        P = tps(P0)
        Jac = tps.jacobian(P0)
        f = sum(np.where(np.isin(p['hanc'][:, k], HEAD_BONES), p['weights'][:, k], 0) for k in range(4))
        P = f[:, None] * (hn + (P0 - hs) @ A_head.T) + (1 - f[:, None]) * P
        Jac = f[:, None, None] * A_head + (1 - f[:, None, None]) * Jac
        hw, hp, hj = np.zeros(len(P0)), np.zeros_like(P0), np.zeros((len(P0), 3, 3))
        for k in range(4):
            for h in np.unique(p['hanc'][:, k]):
                sel = (p['hanc'][:, k] == h) & (p['weights'][:, k] > 0)
                if not h or not F.is_hand(h) or not sel.any():
                    continue
                w = p['weights'][sel, k]
                ms, mn, A = info['maps'][h]
                hp[sel] += w[:, None] * (mn + (P0[sel] - ms) @ A.T)
                hj[sel] += w[:, None, None] * A
                hw[sel] += w
        P = hp + (1 - hw)[:, None] * P
        Jac = hj + (1 - hw)[:, None, None] * Jac
        p['P'], p['P0'] = P, P0
        N = np.einsum('vji,vj->vi', np.linalg.inv(Jac), N0)
        p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)

    # ground contact: lowest vanilla boot point
    lod0 = os.path.join(args.ref, 'lod0')
    boots = H.read_meshes(os.path.join(lod0, BOOT_FILE['R']))[1] + H.read_meshes(os.path.join(lod0, BOOT_FILE['L']))[1]
    floor = min(float(m['pos'][np.unique(m['faces']), 2].min()) for m in boots) * 100.0
    report['floor_cm'] = floor

    def frac(p, nn):
        return sum(np.where(np.isin(p['hanc'][:, k], nn), p['weights'][:, k], 0) for k in range(4))
    for side in ('left', 'right'):
        leg_nodes = [f'{side}{b}' for b in ('UpperLeg', 'LowerLeg', 'Foot', 'Toes')]
        foot_nodes = [f'{side}Foot', f'{side}Toes']
        sole = min(p['P'][frac(p, foot_nodes) > 0.5, 2].min() for p in prims if (frac(p, foot_nodes) > 0.5).any())
        lift = floor - sole
        zk = J[F.HUMAN2GOT[f'{side}UpperLeg'], 2]
        za = J[F.HUMAN2GOT[f'{side}Foot'], 2]
        for p in prims:
            m = frac(p, leg_nodes)
            zb = p['P'][:, 2].copy()
            ramp = np.clip((zk - zb) / (zk - za), 0, 1)
            p['P'][:, 2] += lift * ramp * m
            dramp = np.where((zb > za) & (zb < zk), -1.0 / (zk - za), 0.0)
            s = 1 + lift * m * dramp
            N = p['N'].copy()
            N[:, 2] /= s
            p['N'] = N / np.linalg.norm(N, axis=1, keepdims=True).clip(1e-12)
        report[f'{side}_foot_lift_cm'] = float(lift)
    for p in prims:
        if (p['mesh'], p['mat_name']) == FACE_PRIM:
            k, n_outer = anime_face_normals(p)
            print(f'[face normals] {k} diffusion steps, {n_outer} outer edge vertices', flush=True)
    allP = np.concatenate([p['P'] for p in prims])
    report['fitted_bbox_cm'] = [allP.min(0).round(1).tolist(), allP.max(0).round(1).tolist()]
    print(f'[fit] {time.time() - t0:.0f}s bbox {report["fitted_bbox_cm"]} lifts',
          round(report['left_foot_lift_cm'], 2), round(report['right_foot_lift_cm'], 2), flush=True)

    # ---- weights (skeleton 50118 joint indices)
    donor_meshes = []
    for f in (BODY_FILE, '7E9D_5.ascii', BOOT_FILE['R'], BOOT_FILE['L'], '7E9D_0.ascii', '7E9D_2.ascii'):
        donor_meshes += [m for m in H.read_meshes(os.path.join(lod0, f))[1] if '_sm_2_' not in m['name'] or f != BODY_FILE]
    donors = Donors(donor_meshes, names, parents)
    skirt = [p['P'][:, 2] for p in prims if p['mesh'] == 'skirt']
    skirt_z = (max(z.max() for z in skirt), min(z.min() for z in skirt))
    report['skirt_z_cm'] = [float(z) for z in skirt_z]
    for p in prims:
        p['hanc_of'] = anc_cache
        p['acc'] = map_weights(p, vrm.names, vrm.human, donors, idx, skirt_z, len(names), J)
    # skirt and tail hand over from the hips to the coat's cloth particles: skirt by height, panel by angle around the
    # body; tail along its bone chain down the back centre
    coat_jl = {int(k): v for k, v in ref['coat_joint_lists'].items()}
    pbd = sorted({j for l in coat_jl.values() for j in l if 'Cloth_PBD' in names[j]})
    part = np.array([j for j in pbd if j not in {parents[k] for k in pbd}])   # their shared parent is no particle
    part_pos = J[part]
    centre = part_pos[:, :2].mean(0)
    report['cloth'] = dict(particles=len(part), centre=centre.round(1).tolist())
    for p in prims:
        if p['mesh'] not in CLOTH_MESHES:
            continue
        x = p['P']
        if p['mesh'] == 'skirt':
            t = np.clip((skirt_z[0] - x[:, 2]) / (skirt_z[0] - skirt_z[1]), 0, 1)
            theta = np.arctan2(x[:, 0] - centre[0], x[:, 1] - centre[1])
            back = smoothstep((np.abs(theta) - 0.6) / 0.9)          # 0 within ~35 deg of the front centre
            c = SKIRT_CLOTH_MAX * smoothstep((t - 0.1) / 0.5) * (SKIRT_FRONT_CLOTH + (1 - SKIRT_FRONT_CLOTH) * back)
            z0, z1 = SKIRT_CLOTH_Z
        else:
            m, u = chain_param(p, vrm.names, vrm.parent, 'Tail')
            t = m * u
            theta = np.full(len(x), np.pi)
            (z0, z1), c = TAIL_CLOTH_Z, smoothstep((t - 0.05) / 0.35)
        cw = cloth_weights(theta, z0 + t * (z1 - z0), part, part_pos, centre, len(names),
                           CLOTH_SIGMA if p['mesh'] == 'skirt' else TAIL_SIGMA_Z)
        p['acc'] = (1 - c)[:, None] * p['acc'] + c[:, None] * cw
        report['cloth'][p['mesh']] = dict(verts=len(x), mean_cloth=round(float(c.mean()), 3), full=int((c > 0.999).sum()))
    # twin tails: lower halves follow the body mesh's Belt_PBD chain on their side (3 particles each, x ~ +-29 cm,
    # z 129 -> 112); the upper halves stay on the head
    belts = sorted(j for j in ref['joint_lists'][str(BODY_MESH[0])] if 'Belt_PBD' in names[j])
    for p in prims:
        if p['mesh'] != 'hair':
            continue
        for prefix in ('Hair_tail_L', 'Hair_tail_R'):
            m, u = chain_param(p, vrm.names, vrm.parent, prefix)
            sel = np.where(m > 0)[0]
            if not len(sel):
                continue
            x = p['P'][sel]
            side = np.sign(x[:, 0].mean())
            chain = np.array([j for j in belts if np.sign(J[j, 0]) == side])
            t = np.clip((u[sel] - 0.3) / 0.7, 0, 1)
            zt = TWIN_BELT_Z[0] + t * (TWIN_BELT_Z[1] - TWIN_BELT_Z[0])
            d2 = (zt[:, None] - J[chain, 2][None]) ** 2
            w = np.exp(-(d2 - d2.min(1, keepdims=True)) / CLOTH_SIGMA ** 2)
            bw = np.zeros((len(sel), len(names)))
            bw[:, chain] = w / w.sum(1, keepdims=True)
            c = m[sel] * smoothstep((u[sel] - 0.25) / 0.45)
            p['acc'][sel] = (1 - c)[:, None] * p['acc'][sel] + c[:, None] * bw
            report['cloth'][prefix] = dict(verts=len(sel), z=[round(float(x[:, 2].min()), 1), round(float(x[:, 2].max()), 1)],
                                           belt=[names[j] for j in chain], mean_cloth=round(float(c.mean()), 3))
    # hair slot (skeleton 67700 joint indices): ears, bangs and side locks stay rigid on the head at their roots and
    # blend along their chains to the Hair_PBD particles nearest each vertex (bind pose)
    hr = ref['hair']
    hnames, hparents = hr['names'], hr['parents']
    hJ = np.zeros((len(hnames), 3))
    for j, w in hr['world'].items():
        hJ[int(j)] = np.array(w)[:3, 3] * 100.0
    hair_allowed = set.intersection(*(set(hr['joint_lists'][str(m)]) for m in HAIR_MESH.values()))
    hpart = np.array(sorted(j for j in hair_allowed if 'Hair_PBD' in hnames[j]))
    hhead = hnames.index(HEAD)
    report['hair'] = dict(particles=len(hpart), head_bind_cm=hJ[hhead].round(2).tolist())

    def head_point(name):   # a Karin node's bind position through the rigid head fit (cm, DS2 frame)
        return hn + (F.gltf_to_got(vrm.world[vrm.names.index(name)][:3, 3]) - hs) @ A_head.T
    ear_mix = {}
    for prefix, (root, _) in HAIR_CHAINS.items():
        if prefix.startswith('Ear'):
            e = np.exp(-((hJ[hpart] - head_point(root)) ** 2).sum(1) / HAIR_EAR_SIGMA ** 2)
            e[np.argsort(-e)[HAIR_EAR_N:]] = 0
            ear_mix[prefix] = e / e.sum()
    ear_part = np.any([m > 0 for m in ear_mix.values()], 0)
    hscale = {int(hpart[k]): hJ[hpart[k]] for k in np.nonzero(ear_part)[0]}   # particle joint -> bind position (cm)
    report['hair']['ear_particles'] = [hnames[j][8:11] for j in hscale]
    for p in prims:
        if p['mesh'] not in HAIR_SLOT_MESHES and not (p['mesh'] == 'hair' and p['mat_name'] in HAIR_SLOT_MATS):
            continue
        x = p['P']
        d2 = ((x[:, None, :] - hJ[hpart][None]) ** 2).sum(2)
        d2[:, ear_part] = np.inf    # the ears' particles lend position only: bangs and side locks keep the others
        pw = np.exp(-(d2 - d2.min(1, keepdims=True)) / HAIR_SIGMA ** 2)
        pw /= pw.sum(1, keepdims=True)
        hacc = np.zeros((len(x), len(hnames)))
        hacc[:, hhead] = 1.0
        on = np.zeros(len(x))
        for prefix, (root, tips) in HAIR_CHAINS.items():
            m = chain_param(p, vrm.names, vrm.parent, prefix)[0]
            sel = np.where(m > 0)[0]
            if not len(sel):
                continue
            r0 = head_point(root)
            d = np.mean([head_point(t) for t in tips], 0) - r0
            u = np.clip((x - r0) @ d / (d @ d), 0, 1)
            on[sel] = np.maximum(on[sel], m[sel])
            if prefix.startswith('Ear'):
                mix = np.tile(ear_mix[prefix], (len(sel), 1))
                c = HAIR_EAR_MAX * m[sel] * smoothstep(u[sel] / HAIR_EAR_UW)
            else:
                mix = pw[sel]
                c = HAIR_CLOTH_MAX * m[sel] * smoothstep((u[sel] - HAIR_U0) / HAIR_UW)
            hacc[sel] *= (1 - c)[:, None]
            hacc[np.ix_(sel, hpart)] += c[:, None] * mix
            share = mix.mean(0)
            report['hair'][prefix] = dict(verts=len(sel), mean_cloth=round(float(c.mean()), 3),
                                          z=[round(float(x[sel, 2].min()), 1), round(float(x[sel, 2].max()), 1)],
                                          particles={hnames[hpart[k]][8:11]: round(float(share[k]), 2)
                                                     for k in np.argsort(-share)[:5]})
        p['hacc'], p['hair_on'] = hacc, on
    # face slot (skeleton 67711 joint indices): rigid on Head; mouth and eyelid vertices follow the facial joint that
    # best reproduces the matching shape key when DS2's rig plays that control at 1.0
    if args.face:
        fr = ref['face']
        fnames, fparents = fr['names'], fr['parents']
        fhead = fnames.index(HEAD)
        motion = json.load(open(args.face_motion))
        report['face'] = {}
        levers = {}                                  # lever joint -> u (cm)
        near = set(fr['joint_lists'][str(FACE_MESH[2])])
        for p in prims:
            if (p['mesh'], p['mat_name']) != FACE_PRIM:
                continue
            x = p['P']
            facc = np.zeros((len(x), len(fnames)))
            facc[:, fhead] = 1.0
            foff = np.zeros_like(x)                  # lever offsets (cm): stored position = x - foff
            fcar = np.full(len(x), -1)               # lever joint per vertex
            for control, (key, pattern) in FACE_FITS.items():
                S = F.gltf_to_got(p['morph'][key]) @ A_head.T
                mv = np.where(np.linalg.norm(S, axis=1) > 0.005)[0]
                # only joints of the near face mesh (186, LOD0-2 through the links): v19f's left lever 000_EyelidUpperA
                # exists in LOD4 only, so up close the lid fell back to its parent
                lever_cands = [fnames.index(n) for n in FACE_LEVER.get(control, ()) if fnames.index(n) in near]
                cands = [int(j) for j in motion[control] if re.search(pattern, fnames[int(j)]) and
                         int(j) not in lever_cands and int(j) in near]
                V, Sv = x[mv], S[mv]
                best = np.zeros(len(mv)); bj = np.full(len(mv), -1); bw = np.zeros(len(mv))
                for j in cands:
                    Dm = np.array(motion[control][str(j)])
                    D = V @ Dm[:3, :3].T + Dm[:3, 3] - V
                    sd, dd = (Sv * D).sum(1), (D * D).sum(1)
                    w = np.clip(sd / np.maximum(dd, 1e-9), 0, 1)
                    gain = 2 * w * sd - w * w * dd
                    up = gain > best
                    best[up], bj[up], bw[up] = gain[up], j, w[up]

                def closure(mot, bj, bw, lu):   # how far the fitted vertices travel along her shape key at mot = 1.0
                    disp = np.zeros_like(V)
                    for j in np.unique(bj[bj >= 0]):
                        if str(j) not in mot:
                            continue
                        k = bj == j
                        Y = V[k] + ((1 - bw[k])[:, None] * lu[j] if j in lu else 0)
                        Dm = np.array(mot[str(j)])
                        disp[k] = bw[k][:, None] * (Y @ Dm[:3, :3].T + Dm[:3, 3] - Y)
                    return [round(float((disp * Sv).sum() / max(float((Sv ** 2).sum()), 1e-9)), 3),
                            round(float(np.percentile(np.linalg.norm(disp, axis=1), 95)), 2)]

                def closures(bj, bw, lu):
                    return {c: closure(motion[c], bj, bw, lu) for c in (control,) + FACE_DIAG.get(control, ())
                            if c in motion}
                ss = float((Sv ** 2).sum())
                lu, tried, top = {}, {}, None
                Wg = np.linspace(0, 1, 51)
                for lever in lever_cands:
                    if str(lever) not in motion[control]:
                        continue
                    Dm = np.array(motion[control][str(lever)])
                    R, t = Dm[:3, :3], Dm[:3, 3]
                    cand = None
                    for u in FACE_LEVER_GRID:
                        Y = V[None] + (1 - Wg)[:, None, None] * u
                        disp = Wg[:, None, None] * (Y @ R.T + t - Y)
                        gain = 2 * (disp * Sv[None]).sum(2) - (disp ** 2).sum(2)
                        gl, wi = gain.max(0), gain.argmax(0)
                        tot = np.maximum(gl, best).sum()
                        if cand is None or tot > cand[0]:
                            cand = (tot, u, gl, Wg[wi])
                    tot, u, gl, wl = cand
                    use = gl > best
                    cbj, cbw = np.where(use, lever, bj), np.where(use, wl, bw)
                    tried[lever] = dict(fit=round(float(tot) / max(ss, 1e-9), 3), u_cm=u.round(1).tolist(),
                                        close=closures(cbj, cbw, {lever: u}))
                    if top is None or tot > top[0]:
                        top = (tot, lever, u, gl, wl)
                lever_rep = {}
                if top:
                    _, lever, u, gl, wl = top
                    use = gl > best
                    best[use], bj[use], bw[use] = gl[use], lever, wl[use]
                    foff[mv[use]] = wl[use][:, None] * u
                    fcar[mv[use]] = lever
                    levers[lever] = lu[lever] = u
                    lever_rep = dict(joint=fnames[lever], u_cm=u.round(2).tolist(), verts=int(use.sum()),
                                     tried={fnames[k][8:]: v for k, v in tried.items()})
                close = closures(bj, bw, lu)
                ok = bj >= 0
                v, j, w = mv[ok], bj[ok], bw[ok]
                facc[v] *= (1 - w)[:, None]
                facc[v, j] += w
                report['face'][control] = dict(key=key, moving=len(mv), followed=int(ok.sum()),
                                               max_cm=round(float(np.linalg.norm(S, axis=1).max()), 2),
                                               fit=round(float(best.sum()) / max(ss, 1e-9), 3), close=close,
                                               lever=lever_rep,
                                               joints=sorted({fnames[k] for k in np.unique(j)})[:12])
            p['facc'], p['foff'], p['fcar'] = facc, foff, fcar
        print(f'[face] {report["face"]}', flush=True)
    print(f'[weights] {time.time() - t0:.0f}s cloth {report["cloth"]} hair {report["hair"]}', flush=True)

    # ---- slot of every triangle: head / hair / R / L (feet) / body / coat
    for p in prims:
        nt = len(p['tris'])
        if p['mesh'] in HAIR_SLOT_MESHES:
            slot = np.full(nt, 'head' if HAIR_ON_HEAD else 'hair', dtype=object)
        elif args.face and (p['mesh'], p['mat_name']) == FACE_PRIM:
            slot = np.full(nt, 'face', dtype=object)
        elif p['mesh'] in HEAD_MESHES:
            slot = np.full(nt, 'head', dtype=object)
            if 'hair_on' in p and not HAIR_ON_HEAD:   # bangs and side locks: every triangle touching their chains
                slot[(p['hair_on'][p['tris']] > 0.02).any(1)] = 'hair'
        elif p['mesh'] in CLOTH_MESHES:
            slot = np.full(nt, 'coat', dtype=object)
        else:
            foot = frac(p, FOOT_BONES) > 0.5
            is_foot = foot[p['tris']].sum(1) >= 2
            if p['mesh'] in FEET_MESHES:
                is_foot[:] = True
            cx = p['P'][p['tris']].mean(1)[:, 0]
            slot = np.where(is_foot, np.where(cx > 0, 'R', 'L'), 'body').astype(object)
        p['slot'] = slot

    # ---- pages: A head (gloves texture 0x180), B body + boots (textures 0x10 and 0x8), C cloth (coat texture 50110:0xE8)
    def img(i, size=None):
        im = vrm.image(vrm.js['textures'][vrm.js['materials'][i]['pbrMetallicRoughness']['baseColorTexture']['index']]['source']).convert('RGBA')
        return im.resize((size, size), Image.LANCZOS) if size and im.size[0] > size else im
    mat_index = {m['name']: i for i, m in enumerate(vrm.js['materials'])}
    imgs = {n: img(mat_index[n], args.src_max) for n in ('Karin_Face', 'Karin_Body', 'Karin_Hair', 'Karin_Costume')}
    imgs['Karin_Hair_Transparent'] = imgs['Karin_Hair']
    pages = {}
    key = {'Karin_Hair_Transparent': 'Karin_Hair'}
    page_of_slot = {'head': 'A', 'body': 'B', 'R': 'B', 'L': 'B', 'coat': 'C', 'hair': 'H', 'face': 'F'}
    def page_items(pg, image=lambda p: imgs[p['mat_name']]):
        """(prim, its triangles on page pg) and build_page items; a prim can span pages (hair: A and H)."""
        sel = [(p, np.isin(p['slot'], [s for s, q in page_of_slot.items() if q == pg])) for p in prims]
        sel = [(p, k) for p, k in sel if k.any()]
        return sel, [dict(img=image(p), uv=p['uv'], tris=p['tris'][k], key=key.get(p['mat_name'], p['mat_name']))
                     for p, k in sel]
    for pg in ('A', 'B', 'C'):
        sel, items = page_items(pg)
        page, uvs, st = build_page(items, (2048, 2048), mask_merge=True)
        for (p, _), uv in zip(sel, uvs):
            p['puv_' + pg] = uv
        page.convert('RGB').save(os.path.join(args.work, f'page_{pg}.png'))
        rough = Image.new('L', (2048, 2048), ROUGH['Karin_Costume'])
        dr = ImageDraw.Draw(rough)
        for p, tk in sel:
            r = ROUGH.get(p['mesh'], ROUGH.get(p['mat_name'], ROUGH['Karin_Costume']))
            uv = p['puv_' + pg] * 2048
            for t in p['tris'][tk]:
                dr.polygon([(float(uv[k][0]), float(uv[k][1])) for k in t], fill=r, outline=r)
        rough.save(os.path.join(args.work, f'rough_{pg}.png'))
        pages[pg] = st
        print(f'[page {pg}] scale {st["scale"]:.3f} pieces {st["pieces"]} fill {st["fill"]:.2f}', flush=True)
    # page H: Sam's hair atlas. Karin's pieces go into the cells no Sam hair card uses (--hair-used, a coarse mask of
    # every vanilla hair mesh's UVs); their colour, alpha and a flat normal are pasted over the vanilla textures, the
    # other maps get the vanilla medians of the used area. Alpha is 0 everywhere else, so every Sam hair card on this
    # atlas (the player's and the cutscene copies) turns invisible.
    hair_used = np.asarray(Image.open(args.hair_used).convert('L')) > 0
    sel, items = page_items('H')
    if items:
        page, uvs, st = build_page(items, (2048, 2048), mask_merge=True, free=~hair_used)
        for (p, _), uv in zip(sel, uvs):
            p['puv_H'] = uv
        alpha_img = {n: Image.merge('RGB', [im.getchannel('A')] * 3) for n, im in imgs.items()}
        apage = build_page(page_items('H', lambda p: alpha_img[p['mat_name']])[1], (2048, 2048), mask_merge=True,
                           free=~hair_used)[0]
        filled = st.pop('filled')
        rgb = np.asarray(page.convert('RGB'))
        alpha = np.asarray(apage.convert('L'))
    else:   # HAIR_ON_HEAD: vanilla maps, alpha 0 everywhere
        filled = np.zeros(hair_used.shape, bool)
        rgb, alpha = np.zeros(hair_used.shape + (3,), np.uint8), np.zeros(hair_used.shape, np.uint8)
        st = dict(scale=0.0, pieces=0, fill=0.0)
    for tex, (size, kind) in HAIR_TEX.items():
        src = [f for f in os.listdir(args.hair_tex) if f.upper() in (f'A60_{tex}.DDS', f'A60_{tex}_DX10.DDS')][0]
        van = np.asarray(Image.open(os.path.join(args.hair_tex, src)).convert('RGBA')).copy()
        f = np.asarray(Image.fromarray(filled).resize((size, size), Image.NEAREST))
        u = np.asarray(Image.fromarray(hair_used).resize((size, size), Image.NEAREST))
        med = np.median(van[u], 0).round().astype(np.uint8)
        if kind == 'alpha':
            a = np.asarray(Image.fromarray(alpha).resize((size, size), Image.BILINEAR))
            Image.fromarray(np.where(f, a, 0).astype(np.uint8), 'L').save(os.path.join(args.work, f'hair_{tex}.png'))
            continue
        ours = np.tile(med, (size, size, 1))
        if kind == 'colour':
            ours = np.dstack([np.asarray(Image.fromarray(rgb).resize((size, size), Image.LANCZOS)),
                              np.full((size, size), 255, np.uint8)])          # alpha channel = AO
        elif kind == 'normal':
            ours[..., :2] = 128
        out = np.where(f[..., None], ours, van).astype(np.uint8)
        Image.fromarray(out, 'RGBA').save(os.path.join(args.work, f'hair_{tex}.png'))
    pages['H'] = st
    print(f'[page H] scale {st["scale"]:.3f} pieces {st["pieces"]} fill {st["fill"]:.3f}', flush=True)

    def face_tmpl(lod):
        d = os.path.join(args.face_ref, f'lod{lod}')
        return d, sorted(((int(re.match(r'mesh_\d+_sm_(\d+)_', s['name']).group(1)), s)
                          for f in sorted(os.listdir(d)) if f.startswith('1A10_') and f.endswith('.ascii')
                          for s in H.read_meshes(os.path.join(d, f))[1]
                          if s['name'].startswith(f'mesh_{FACE_MESH[lod]}_sm_')), key=lambda t: t[0])
    # page F: Sam's face textures. Colours = Karin's face page, normals flat, the other maps the vanilla medians over
    # the area Sam's face UVs cover
    for f in os.listdir(args.work):
        if f.startswith('face_') and f.endswith('.png'):
            os.remove(os.path.join(args.work, f))
    if args.face:
        sel, items = page_items('F')
        page, uvs, st = build_page(items, (2048, 2048), mask_merge=True)
        for (p, _), uv in zip(sel, uvs):
            p['puv_F'] = uv
        rgb = np.asarray(page.convert('RGB'))
        tm = face_tmpl(2)[1][0][1]
        cover = Image.new('L', (512, 512), 0)
        dr = ImageDraw.Draw(cover)
        for t in np.asarray(tm['faces']):
            dr.polygon([tuple(np.asarray(tm['uv'][0])[k] * 512) for k in t], fill=255, outline=255)
        for tex, (size, kind) in FACE_TEX.items():
            src = [f for f in os.listdir(args.face_tex) if f.upper() in (f'F9A_{tex}.DDS', f'F9A_{tex}_DX10.DDS')][0]
            vim = Image.open(os.path.join(args.face_tex, src))
            van = np.asarray(vim.convert('RGBA'))
            u = np.asarray(cover.resize((size, size), Image.NEAREST)) > 0
            med = np.median(van[u], 0).round().astype(np.uint8)
            if kind == 'colour':
                out = np.dstack([np.asarray(Image.fromarray(rgb).resize((size, size), Image.LANCZOS)),
                                 np.full((size, size), 255, np.uint8)])
            else:
                out = np.tile(med, (size, size, 1))
                if kind == 'normal':
                    out[..., :2] = 128
            im = Image.fromarray(out, 'RGBA')
            (im.getchannel('R') if vim.mode == 'L' else im).save(os.path.join(args.work, f'face_{tex}.png'))
        pages['F'] = st
        print(f'[page F] scale {st["scale"]:.3f} pieces {st["pieces"]} fill {st["fill"]:.2f}', flush=True)
    report['pages'] = pages

    # ---- slot meshes
    def gather(slot):
        P, N, UV, A, T = [], [], [], [], []
        X = {'off': [], 'car': []}
        off = 0
        wkey, uvkey = {'hair': 'hacc', 'face': 'facc'}.get(slot, 'acc'), 'puv_' + page_of_slot[slot]
        for p in prims:
            tsel = p['slot'] == slot
            if not tsel.any():
                continue
            used, inv = np.unique(p['tris'][tsel], return_inverse=True)
            P.append(p['P'][used]); N.append(p['N'][used]); UV.append(p[uvkey][used]); A.append(p[wkey][used])
            T.append(inv.reshape(-1, 3) + off)
            if slot == 'face':
                X['off'].append(p['foff'][used]); X['car'].append(p['fcar'][used])
            off += len(used)
        return dict(P=np.concatenate(P), N=np.concatenate(N), UV=np.concatenate(UV), A=np.concatenate(A),
                    T=np.concatenate(T), **{k: np.concatenate(v) for k, v in X.items() if v})
    jl = {int(k): v for k, v in ref['joint_lists'].items()}
    lods = [int(x) for x in args.lods.split(',')]
    body_allowed = set.intersection(*(set(jl[BODY_MESH[l]]) for l in lods))
    slots = {s: gather(s) for s in ('head', 'body', 'R', 'L', 'coat', 'hair') + (('face',) if args.face else ())
             if any((p['slot'] == s).any() for p in prims)}
    for s, m in slots.items():
        if s == 'face':      # restricted per LOD below (the LOD4 mesh keeps 26 joints)
            continue
        if s in ('head', 'body'):
            allowed = body_allowed
        elif s == 'coat':
            allowed = set.intersection(*(set(coat_jl[COAT_MESH[l]]) for l in lods))
        elif s == 'hair':
            m['A'] = restrict(m['A'], hair_allowed, hparents)
            continue
        else:
            allowed = set.intersection(*(set(jl[BOOT_MESH[s][l]]) for l in lods))
        m['A'] = restrict(m['A'], allowed, parents)
    report['verts'] = {s: len(m['P']) for s, m in slots.items()}
    print('[slots]', report['verts'], flush=True)
    if max(report['verts'].values()) > 65535:
        raise SystemExit('a slot exceeds 16-bit indices')

    # winding: match the vanilla ascii convention (checked on Sam's suit)
    sam = H.read_meshes(os.path.join(lod0, BODY_FILE))[1][0]
    sam_sign = winding_sign(sam['pos'], sam['nrm'], sam['faces'])
    k_sign = winding_sign(slots['body']['P'], slots['body']['N'], slots['body']['T'])
    flip = sam_sign != k_sign
    report['winding'] = dict(sam=sam_sign, karin_gltf=k_sign, flipped=bool(flip))

    def to_sub(m, tmpl, peers=None):
        nw = len(tmpl['bi'][0])
        bi, bw = quantize(m['A'], nw)
        nv = len(m['P'])
        uv0 = np.stack([m['UV'][:, 0], 1.0 - m['UV'][:, 1]], 1)
        BI = [[int(x) for x in r] for r in bi]
        BW = [[float(x) for x in r] for r in bw]
        for r_i, r_w in zip(BI, BW):   # pad unused slots with the last used joint at weight 0
            last = r_i[0]
            for k in range(nw):
                if r_w[k] > 0:
                    last = r_i[k]
                else:
                    r_i[k] = last
        faces = m['T'][:, [0, 2, 1]] if flip else m['T']
        return dict(name=tmpl['name'], nuv=tmpl['nuv'], textures=tmpl['textures'], pos=m['P'] / 100.0, nrm=m['N'],
                    col=np.tile(np.array(tmpl['col'][0]), (nv, 1)), uv=extra_uvs(tmpl, uv0, peers), bi=BI,
                    bw=BW, faces=faces)

    def collapsed(tmpl):
        bi = np.asarray(tmpl['bi'])
        bw = np.asarray(tmpl['bw'])
        dom = bi[np.arange(len(bi)), bw.argmax(1)]
        vals, counts = np.unique(dom, return_counts=True)
        joint = int(vals[counts.argmax()])
        point = tmpl['pos'][dom == joint].mean(0)
        nv, nw = len(tmpl['pos']), len(tmpl['bi'][0])
        return dict(name=tmpl['name'], nuv=tmpl['nuv'], textures=tmpl['textures'], pos=np.tile(point, (nv, 1)),
                    nrm=np.tile([0, 0, 1.0], (nv, 1)), col=np.array(tmpl['col']), uv=[np.full((nv, 2), 0.5)] * tmpl['nuv'],
                    bi=[[joint] * nw] * nv, bw=[[1.0] + [0.0] * (nw - 1)] * nv, faces=tmpl['faces'])

    out_dir = os.path.join(args.work, 'ascii')
    os.makedirs(out_dir, exist_ok=True)
    skel_hdr = {k: H.read_skeleton(os.path.join(args.skeletons, v)) for k, v in SKEL_FILES.items()}
    jobs = []
    for lod in lods:
        d = os.path.join(args.ref, f'lod{lod}')
        log = open(os.path.join(d, 'export.log'), encoding='utf-8-sig', errors='replace').read()
        mesh_skel = {int(m): s for m, s, _ in re.findall(r'Mesh (\d+) with skeleton (\w+) (\w+)', log)}
        for f in sorted(os.listdir(d)):
            if not (f.startswith('7E9D_') and f.endswith('.ascii')):
                continue
            by_mesh = {}   # one export file can hold several meshes (MultiMeshResource members)
            for s in H.read_meshes(os.path.join(d, f))[1]:
                mm = re.match(r'mesh_(\d+)_sm_(\d+)_', s['name'])
                by_mesh.setdefault(int(mm.group(1)), []).append((int(mm.group(2)), s))
            for mid, items in by_mesh.items():
                items.sort(key=lambda t: t[0])
                skel = mesh_skel[mid]
                out = []
                for si, s in items:
                    kind = None
                    if mid == BODY_MESH.get(lod):
                        kind = {'body': 'body', 'gloves': 'head'}.get(ref['materials'][str(mid)][si])
                    for side in ('R', 'L'):
                        if mid == BOOT_MESH[side].get(lod):
                            kind = side
                    out.append(to_sub(slots[kind], s, [p for _, p in items]) if kind else collapsed(s))
                path = os.path.join(out_dir, f'lod{lod}_{mid}.ascii')
                H.write(path, out, bones=skel_hdr[skel])
                jobs.append(dict(group='7e9d', gid=50108, lod=lod, mesh=mid, skel=SKEL_FILES[skel], ascii=path,
                                 prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                                 verts=[len(o['pos']) for o in out]))
        # coat: primitive 0 (coat material) carries the cloth slot, the rest collapses
        d = os.path.join(args.coat_ref, f'lod{lod}')
        mid = COAT_MESH[lod]
        log = open(os.path.join(d, 'export.log'), encoding='utf-8-sig', errors='replace').read()
        skel = re.search(rf'Mesh {mid} with skeleton (\w+) ', log).group(1)
        items = sorted(((int(re.match(r'mesh_\d+_sm_(\d+)_', s['name']).group(1)), s)
                        for s in H.read_meshes(os.path.join(d, COAT_FILE))[1] if s['name'].startswith(f'mesh_{mid}_sm_')),
                       key=lambda t: t[0])
        out = [to_sub(slots['coat'], s, [p for _, p in items]) if si == 0 else collapsed(s) for si, s in items]
        path = os.path.join(out_dir, f'coat_lod{lod}_{mid}.ascii')
        H.write(path, out, bones=skel_hdr[skel])
        jobs.append(dict(group='47cd', gid=50110, lod=lod, mesh=mid, skel=SKEL_FILES[skel], ascii=path,
                         prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                         verts=[len(o['pos']) for o in out]))
    # hair: the LodMesh 82 member of each LOD; primitive 0 (hair material) carries the hair slot, the rest collapses
    for lod, mid in sorted(HAIR_MESH.items()):
        d = os.path.join(args.hair_ref, f'lod{lod}')
        log = open(os.path.join(d, 'export.log'), encoding='utf-8-sig', errors='replace').read()
        skel = re.search(rf'Mesh {mid} with skeleton (\w+) ', log).group(1)
        items = sorted(((int(re.match(r'mesh_\d+_sm_(\d+)_', s['name']).group(1)), s)
                        for f in sorted(os.listdir(d)) if f.startswith('1A0D_') and f.endswith('.ascii')
                        for s in H.read_meshes(os.path.join(d, f))[1] if s['name'].startswith(f'mesh_{mid}_sm_')),
                       key=lambda t: t[0])
        # ear particles: inverse bind matrix x S, S scaling by s about the particle's bind position p; a vertex with
        # weight W on them (sum of w p over them: wp) is stored at (v - (1 - s) wp) / (1 - (1 - s) W) so that it still
        # sits at v at rest, and a particle's turn moves it with a lever s / (1 - (1 - s) W) of the old one
        ibm_post = {}
        if 'hair' not in slots:   # HAIR_ON_HEAD: nothing of hers here
            out = [collapsed(s) for _, s in items]
        else:
            hsl = slots['hair']
            sc = HAIR_EAR_SCALE
            bi, bw = quantize(hsl['A'], len(next(s for si, s in items if si == 0)['bi'][0]))
            W, wp = np.zeros(len(hsl['P'])), np.zeros_like(hsl['P'])
            for j, p0 in hscale.items():
                wj = (bw * (bi == j)).sum(1)
                W += wj
                wp += wj[:, None] * p0
            m = dict(hsl, P=(hsl['P'] - (1 - sc) * wp) / (1 - (1 - sc) * W)[:, None])
            for j, p0 in hscale.items():
                S = np.eye(4) * sc
                S[3, 3] = 1.0
                S[:3, 3] = (1 - sc) * p0 / 100.0
                ibm_post[str(j)] = S.tolist()
            out = [to_sub(m, s, [p for _, p in items]) if si == 0 else collapsed(s) for si, s in items]
        path = os.path.join(out_dir, f'hair_lod{lod}_{mid}.ascii')
        H.write(path, out, bones=skel_hdr[skel])
        jobs.append(dict(group='1a0d', gid=50121, lod=lod, mesh=mid, skel=SKEL_FILES[skel], ascii=path,
                         prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                         verts=[len(o['pos']) for o in out], ibm_post=ibm_post))
    if args.boot_ref:
        b301 = [b['name'] for b in skel_hdr['B6B']]
        remap = np.array([b301.index(b['name']) if b['name'] in b301 else -1 for b in skel_hdr['47CC']])
        for lod in lods:
            d = os.path.join(args.boot_ref, f'lod{lod}')
            for side, meshes in BOOT_ITEM_MESH.items():
                mid = meshes[lod]
                needle = f'mesh_{mid}_sm_0_'
                f = next(f for f in sorted(os.listdir(d)) if f.startswith('B6B_') and f.endswith('.ascii') and
                         needle in open(os.path.join(d, f), encoding='utf-8', errors='replace').read())
                tmpl = next(m for m in H.read_meshes(os.path.join(d, f))[1] if m['name'].startswith(needle))
                sub = to_sub(slots[side], tmpl)
                bi, bw = np.array(sub['bi']), np.array(sub['bw'])
                bi = remap[bi]
                if (bi[bw > 0] < 0).any():
                    raise SystemExit(f'boot {mid}: weights on joints outside skeleton 31123:301')
                bi[bi < 0] = bi[:, :1].repeat(bi.shape[1], 1)[bi < 0]
                nv, nf = len(tmpl['pos']), len(tmpl['faces'])
                v, t = len(sub['pos']), len(sub['faces'])
                if v > nv or t > nf:
                    raise SystemExit(f'boot {mid}: {v} verts / {t} tris exceed the slot ({nv} / {nf})')
                pad = lambda a: np.concatenate([np.asarray(a), np.repeat(np.asarray(a)[:1], nv - v, 0)])
                sub.update(pos=pad(sub['pos']), nrm=pad(sub['nrm']), col=pad(sub['col']), uv=[pad(u) for u in sub['uv']],
                           bi=pad(bi).tolist(), bw=pad(bw).tolist(),
                           faces=np.concatenate([np.asarray(sub['faces']), np.zeros((nf - t, 3), int)]))
                path = os.path.join(out_dir, f'boot_lod{lod}_{mid}.ascii')
                H.write(path, [sub], bones=skel_hdr['B6B'])
                jobs.append(dict(group='b6b', gid=31123, lod=lod, mesh=mid, skel=SKEL_FILES['B6B'], ascii=path,
                                 prims={'0': f'{path}#0'}, verts=[nv], stream_only=True))
                print(f'[boots] lod{lod} {side} mesh {mid}: {v} verts / {t} tris padded to {nv} / {nf}', flush=True)
        for lod, mids in SHOWER_HAIR.items():
            d = os.path.join(args.boot_ref, f'lod{lod}')
            sk = 'B6B_skel_474.ascii' if lod < 3 else 'B6B_skel_474_lod3.ascii'   # the LOD3 export's PBD bind poses differ
            skel474 = H.read_skeleton(os.path.join(args.skeletons, sk))
            for mid in mids:
                needle = f'mesh_{mid}_sm_'
                f = next(f for f in sorted(os.listdir(d)) if f.startswith('B6B_') and f.endswith('.ascii') and
                         needle in open(os.path.join(d, f), encoding='utf-8', errors='replace').read())
                items = sorted(((int(re.match(r'mesh_\d+_sm_(\d+)_', m['name']).group(1)), m)
                                for m in H.read_meshes(os.path.join(d, f))[1] if m['name'].startswith(needle)),
                               key=lambda t: t[0])
                out = [collapsed(m) for _, m in items]
                path = os.path.join(out_dir, f'shower_lod{lod}_{mid}.ascii')
                H.write(path, out, bones=skel474)
                jobs.append(dict(group='b6b', gid=31123, lod=lod, mesh=mid, skel=sk, ascii=path,
                                 prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                                 verts=[len(o['pos']) for o in out], stream_only=True))
        print(f'[shower hair] {sum(len(m) for m in SHOWER_HAIR.values())} meshes collapsed', flush=True)
    # face: Sam's face skin LOD2..4 carry Karin's face, weights restricted to each mesh's own joint list
    for lod, mid in sorted(FACE_MESH.items()) if args.face else ():
        d, items = face_tmpl(lod)
        log = open(os.path.join(d, 'export.log'), encoding='utf-8-sig', errors='replace').read()
        skel = re.search(rf'Mesh {mid} with skeleton (\w+) ', log).group(1)
        allowed = ref['face']['joint_lists'][str(mid)]
        fs = slots['face']
        lev = {j: u for j, u in levers.items() if j in allowed}   # a lever only where its joint is in the mesh
        A = restrict(fs['A'], allowed, ref['face']['parents'])
        # stored position = v - sum over lever joints of (exported weight) u: taken from the quantized weights the
        # mesh really gets (v18f used the fit's offsets; weight that restrict() moved onto a lever joint, or that a later
        # fit rescaled, then sat up to 30 cm off at rest)
        bi, bw = quantize(A, len(next(s for si, s in items if si == 0)['bi'][0]))
        offs = np.zeros_like(fs['P'])
        for j, u in lev.items():
            offs += (bw * (bi == j)).sum(1)[:, None] * u
        old = np.where(np.isin(fs['car'], list(lev))[:, None], fs['off'], 0.0)
        miss = np.linalg.norm(offs - old, axis=1)
        print(f'[face] lod{lod} mesh {mid}: lever offsets differ from the fit by > 0.5 cm on {int((miss > 0.5).sum())} '
              f'verts (max {miss.max():.1f} cm)', flush=True)
        m = dict(fs, P=fs['P'] - offs, A=A)
        ibm = {}
        for j, u in lev.items():
            T = np.eye(4)
            T[:3, 3] = u / 100.0
            ibm[str(j)] = (np.linalg.inv(np.array(ref['face']['world'][str(j)])) @ T).tolist()
        out = [to_sub(m, s, [p for _, p in items]) if si == 0 else collapsed(s) for si, s in items]
        path = os.path.join(out_dir, f'face_lod{lod}_{mid}.ascii')
        H.write(path, out, bones=skel_hdr[skel])
        jobs.append(dict(group='1a10', gid=50120, lod=lod, mesh=mid, skel=SKEL_FILES[skel], ascii=path,
                         prims={str(si): f'{path}#{k}' for k, (si, _) in enumerate(items)},
                         verts=[len(o['pos']) for o in out], ibm=ibm, no_cast_shadow=True))
    json.dump(jobs, open(os.path.join(args.work, 'jobs.json'), 'w'), indent=1)
    gid, oi = HAIR_PBD_BODY
    fields = [dict(index=oi, path=['UseFluctuation'], fmt='<B', value=0)]
    for j in hscale:
        strand = int(hnames[j][8:11]) - 1                 # Hair_PBD_NNN drives strand NNN - 1 (points 8 (NNN - 1) ..)
        fields += [dict(index=oi, path=['Vertices', strand * 8 + r, 'MaxDistance'], fmt='<f', scale=HAIR_EAR_SWING)
                   for r in range(8)]
    json.dump({str(gid): fields}, open(os.path.join(args.work, 'fields.json'), 'w'), indent=1)
    json.dump(report, open(os.path.join(args.work, 'fit_report.json'), 'w'), indent=1, default=float)
    print('[ascii]', len(jobs), 'meshes', f'{time.time() - t0:.0f}s', 'winding', report['winding'])


if __name__ == '__main__':
    main()
