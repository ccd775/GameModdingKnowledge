# fit.py — fit Karin_Original onto the Hogwarts Legacy biped skeleton and write FBX parts for UE 4.27.
# blender -b --factory-startup --python fit.py -- <config.json>
# config: karin_fbx, skel_json (HL bones for this gender), head_json, ref_meshes [json...], out_dir, params{...}
import bpy, bmesh, sys, json, math, os
import numpy as np
from mathutils import Matrix, Vector, Quaternion, kdtree

cfg = json.load(open(sys.argv[sys.argv.index('--') + 1], encoding='utf-8'))
P = cfg.get('params', {})
OUT = cfg['out_dir']; os.makedirs(OUT, exist_ok=True)
log = open(os.path.join(OUT, 'fit_log.txt'), 'w', encoding='utf-8')
def L(*a):
    s = ' '.join(str(x) for x in a); print(s); log.write(s + '\n'); log.flush()

# ------------------------------------------------------------------ HL skeleton (UE cm -> Blender m, y flipped)
def qmat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
def hl_globals(bones):
    G = []
    for b in bones:
        M = np.eye(4); M[:3, :3] = qmat(b['r']) * np.array(b['s']); M[:3, 3] = b['t']
        G.append(M if b['parent'] < 0 else G[b['parent']] @ M)
    return G
FLIP = np.diag([1.0, -1.0, 1.0])
def ue2bl_p(p): return np.array([p[0], -p[1], p[2]]) * 0.01
def bl2ue_p(p): return np.array([p[0], -p[1], p[2]]) * 100.0

skel = json.load(open(cfg['skel_json']))['bones']
HG = hl_globals(skel)
HI = {b['name']: i for i, b in enumerate(skel)}
def H(n): return ue2bl_p(HG[HI[n]][:3, 3])

# ------------------------------------------------------------------ Karin import, bake transforms
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=cfg['karin_fbx'], use_anim=False)
karm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
for o in bpy.data.objects: o.select_set(True)
bpy.context.view_layer.objects.active = karm
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
kmeshes = [o for o in bpy.data.objects if o.type == 'MESH']
KB = {b.name: b for b in karm.data.bones}
KREST = {b.name: np.array(b.matrix_local) for b in karm.data.bones}   # world (armature at identity)
def KH(n): return KREST[n][:3, 3].copy()
L('karin height (head top) z=', max(max((o.matrix_world @ v.co).z for v in o.data.vertices) for o in kmeshes))

# ------------------------------------------------------------------ mesh data (base + shape keys) in world space
class MD: pass
mdata = {}
for o in kmeshes:
    me = o.data
    d = MD(); d.obj = o
    d.co = np.array([v.co[:] for v in me.vertices])
    d.keys = []
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks[1:]:
            d.keys.append((kb.name, np.array([p.co[:] for p in kb.data])))
    gi = {g.index: g.name for g in o.vertex_groups}
    W = [dict() for _ in me.vertices]
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 0 and gi[g.group] in KB: W[v.index][gi[g.group]] = W[v.index].get(gi[g.group], 0) + g.weight
    d.w = W
    # loop normals incl. the author's custom ones (the face's are smoothed for anime shading)
    if hasattr(me, 'calc_normals_split'): me.calc_normals_split()
    ln = np.zeros(len(me.loops) * 3); me.loops.foreach_get('normal', ln); d.ln = ln.reshape(-1, 3)
    lv = np.zeros(len(me.loops), int); me.loops.foreach_get('vertex_index', lv); d.lv = lv
    mdata[o.name] = d
L('meshes', {k: (len(v.co), len(v.keys)) for k, v in mdata.items()})

# ------------------------------------------------------------------ step 1: repose Karin (T -> HL A-pose) with Karin's own rig
SIDES = ('Left', 'Right')
def chain_targets():
    t = []  # (karin bone, karin child joint name (for dir), hl from, hl to)
    t += [('Spine', 'Chest', 'Spine', 'Spine2'), ('Chest', 'Neck', 'Spine2', 'Neck'), ('Neck', 'Head', 'Neck', 'Head')]
    for s in SIDES:
        t += [(f'{s}Shoulder', f'{s}UpperArm', f'{s}Shoulder', f'{s}Arm'),
              (f'{s}UpperArm', f'{s}LowerArm', f'{s}Arm', f'{s}ForeArm'),
              (f'{s}LowerArm', f'{s}Hand', f'{s}ForeArm', f'{s}Hand'),
              (f'{s}UpperLeg', f'{s}LowerLeg', f'{s}UpLeg', f'{s}Leg'),
              (f'{s}LowerLeg', f'{s}Foot', f'{s}Leg', f'{s}Foot'),
              (f'{s}Foot', f'{s}ToeBase', f'{s}Foot', f'{s}ToeBase'),
              (f'{s}ToeBase', f'{s}ToeBase_end', f'{s}ToeBase', f'{s}ToeBaseEnd')]
        for kf, hf in (('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Little', 'Pinky'), ('Thumb', 'Thumb')):
            t += [(f'{s}{kf}Proximal', f'{s}{kf}Intermediate', f'{s}Hand{hf}1', f'{s}Hand{hf}2'),
                  (f'{s}{kf}Intermediate', f'{s}{kf}Distal', f'{s}Hand{hf}2', f'{s}Hand{hf}3'),
                  (f'{s}{kf}Distal', f'{s}{kf}Distal_end', f'{s}Hand{hf}3', f'{s}Hand{hf}4')]
    return t
CHAINS = chain_targets()
CHAIN_BY_BONE = {c[0]: c for c in CHAINS}

def rot_between(a, b):
    a = a / np.linalg.norm(a); b = b / np.linalg.norm(b)
    v = np.cross(a, b); c = float(np.dot(a, b))
    if c < -0.9999:
        ax = np.cross(a, [1, 0, 0]);
        if np.linalg.norm(ax) < 1e-6: ax = np.cross(a, [0, 1, 0])
        ax /= np.linalg.norm(ax); return np.array(Matrix.Rotation(math.pi, 3, Vector(ax)))
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]])
    return np.eye(3) + vx + vx @ vx * (1 / (1 + c))
def frame(fwd, side):
    f = fwd / np.linalg.norm(fwd); s = side - f * np.dot(side, f); s /= np.linalg.norm(s); u = np.cross(f, s)
    return np.stack([f, s, u], 1)

# FK: world pose matrices; we rotate bones in hierarchy order so each chain direction matches HL direction
order = [b.name for b in karm.data.bones]  # parents first
POSE = {}
for n in order:
    b = KB[n]
    if b.parent is None: POSE[n] = KREST[n].copy(); continue
    par = b.parent.name
    local = np.linalg.inv(KREST[par]) @ KREST[n]
    M = POSE[par] @ local
    if n in CHAIN_BY_BONE:
        _, kc, hf, ht = CHAIN_BY_BONE[n]
        if kc in KREST and hf in HI and ht in HI:
            ck = M @ np.linalg.inv(KREST[n]) @ np.append(KH(kc), 1)
            cur = ck[:3] - M[:3, 3]
            tgt = H(ht) - H(hf)
            R = rot_between(cur, tgt)
            if n.endswith('Hand') is False and n.endswith('Foot') and False: pass
            M = M.copy(); M[:3, :3] = R @ M[:3, :3]
    if n in ('LeftHand', 'RightHand'):
        s = n[:-4]
        cur_f = (M @ np.linalg.inv(KREST[n]) @ np.append(KH(s + 'MiddleProximal'), 1))[:3] - M[:3, 3]
        cur_s = (M @ np.linalg.inv(KREST[n]) @ np.append(KH(s + 'LittleProximal'), 1))[:3] - (M @ np.linalg.inv(KREST[n]) @ np.append(KH(s + 'IndexProximal'), 1))[:3]
        tgt_f = H(s + 'HandMiddle1') - H(s + 'Hand'); tgt_s = H(s + 'HandPinky1') - H(s + 'HandIndex1')
        R = frame(tgt_f, tgt_s) @ frame(cur_f, cur_s).T
        M = M.copy(); M[:3, :3] = R @ M[:3, :3]
    POSE[n] = M
SKIN = {n: POSE[n] @ np.linalg.inv(KREST[n]) for n in order}

def lbs(co, W):
    names = sorted({b for wd in W for b in wd})
    if not names: return co.copy()
    Wm = np.zeros((len(W), len(names))); col = {b: j for j, b in enumerate(names)}
    for i, wd in enumerate(W):
        for b, w in wd.items(): Wm[i, col[b]] = w
    tot = Wm.sum(1); none = tot <= 0; tot[none] = 1; Wm /= tot[:, None]
    out = np.zeros_like(co)
    for j, b in enumerate(names):
        Sb = SKIN[b]; out += Wm[:, j:j+1] * (co @ Sb[:3, :3].T + Sb[:3, 3])
    out[none] = co[none]
    return out
for d in mdata.values():
    d.co1 = lbs(d.co, d.w)
    d.keys1 = [(n, lbs(k, d.w)) for n, k in d.keys] if P.get('keep_shape_keys', True) else []
POSED_J = {n: (SKIN[n] @ np.append(KH(n), 1))[:3] for n in order}
L('step1 posed. LeftHand', POSED_J['LeftHand'], 'HL', H('LeftHand'))

# ------------------------------------------------------------------ step 2: TPS warp from posed Karin joints to HL joints
g_perp = P.get('g_perp', 1.3); g_head = P.get('g_head', 1.15); g_hand = P.get('g_hand', 1.2); g_foot = P.get('g_foot', 1.2)
src, dst = [], []
def add(a, b): src.append(np.asarray(a, float)); dst.append(np.asarray(b, float))
def perp_basis(d):
    d = d / np.linalg.norm(d); a = np.cross(d, [0, 0, 1]) if abs(d[2]) < 0.9 else np.cross(d, [1, 0, 0])
    a /= np.linalg.norm(a); b = np.cross(d, a); return a, b
def seg(kf, kt, hf, ht, radius, gp, ts=(0, 0.25, 0.5, 0.75, 1.0)):
    seg_pts(POSED_J[kf], POSED_J[kt], H(hf), H(ht), radius, gp, ts)
def seg_pts(pk0, pk1, ph0, ph1, radius, gp, ts=(0, 0.25, 0.5, 0.75, 1.0)):
    dk = pk1 - pk0; dh = ph1 - ph0
    R = rot_between(dk, dh); a, b = perp_basis(dk)
    for t in ts:
        add(pk0 + dk * t, ph0 + dh * t)
        for ang in (0, 90, 180, 270):
            off = (math.cos(math.radians(ang)) * a + math.sin(math.radians(ang)) * b) * radius
            add(pk0 + dk * t + off, ph0 + dh * t + R @ off * gp)
def rigid(center_k, center_h, R, s, radius, n=14):
    pts = [np.array(v) for v in ((1,0,0),(-1,0,0),(0,1,0),(0,-1,0),(0,0,1),(0,0,-1),(1,1,1),(1,1,-1),(1,-1,1),(1,-1,-1),(-1,1,1),(-1,1,-1),(-1,-1,1),(-1,-1,-1))][:n]
    add(center_k, center_h)
    for p in pts:
        off = p / np.linalg.norm(p) * radius; add(center_k + off, center_h + R @ off * s)

# torso: anchored at the leg roots, not the Hips joint. Karin's hip joints sit ~11 cm under her Hips bone, HL's ~6 cm,
# so Hips->Hips squeezed the pelvis and stretched the waist 2-3x; leg-root midpoint -> neck is a near-uniform scale.
leg_k = (POSED_J['LeftUpperLeg'] + POSED_J['RightUpperLeg']) / 2; leg_h = (H('LeftUpLeg') + H('RightUpLeg')) / 2
# neck: HL's shoulder joints sit far below the head (male chin->shoulder ~15 cm vs Karin's ~7 cm scaled), so pinning the
# arms there stretches the neck. Offsets (metres, +z up) lower the neck base and head and raise the shoulder line.
UP = np.array([0, 0, 1.0])
neck_h = H('Neck') + UP * P.get('neck_offset', 0.0); head_h = H('Head') + np.asarray(P.get('head_offset', [0, 0, 0]), float)
arm_off = UP * P.get('shoulder_offset', 0.0)
# HL shoulder joints are 1.7x (F) / 2.1x (M) wider than Karin's; shoulder_in pulls the arm roots that fraction of the way
# back toward Karin's own (head-scaled) shoulder width. The arm still pivots on HL's joint, slightly outside the mesh.
def arm_root(s):
    h = H(s + 'Arm') + arm_off; kx = abs(POSED_J[s + 'UpperArm'][0]) * g_head * np.sign(h[0])
    h[0] += (kx - h[0]) * P.get('shoulder_in', 0.0); return h
seg_pts(leg_k, POSED_J['Neck'], leg_h, neck_h, 0.08, g_perp, ts=(0, 0.2, 0.4, 0.6, 0.8, 1.0))
seg_pts(POSED_J['Neck'], POSED_J['Head'], neck_h, head_h, 0.03, g_head, ts=(0, 0.5))
L('torso scale', np.linalg.norm(neck_h - leg_h) / np.linalg.norm(POSED_J['Neck'] - leg_k), 'arm roots', [arm_root(s).round(3) for s in SIDES])
for s in SIDES:
    seg_pts(POSED_J[s + 'UpperArm'], POSED_J[s + 'LowerArm'], arm_root(s), H(s + 'ForeArm'), 0.035, g_perp)
    seg(s + 'LowerArm', s + 'Hand', s + 'ForeArm', s + 'Hand', 0.03, g_perp)
    seg(s + 'UpperLeg', s + 'LowerLeg', s + 'UpLeg', s + 'Leg', 0.06, g_perp)
    seg(s + 'LowerLeg', s + 'Foot', s + 'Leg', s + 'Foot', 0.045, g_perp)
    # hand: rigid similarity about the wrist
    Rh = np.eye(3)
    rigid(POSED_J[s + 'Hand'], H(s + 'Hand'), Rh, g_hand, 0.04)
    for kf, hf in (('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Little', 'Pinky'), ('Thumb', 'Thumb')):
        for i, (ka, ha) in enumerate(((kf + 'Proximal', hf + '1'), (kf + 'Intermediate', hf + '2'), (kf + 'Distal', hf + '3'), (kf + 'Distal_end', hf + '4'))):
            kp = POSED_J.get(s + ka); hp = H(s + 'Hand' + ha) if (s + 'Hand' + ha) in HI else None
            if kp is not None and hp is not None:
                # finger joints: keep Karin's finger shape scaled around the wrist (avoid crushing fingers)
                add(kp, H(s + 'Hand') + (kp - POSED_J[s + 'Hand']) * g_hand)
    # foot: rigid similarity about the ankle
    rigid(POSED_J[s + 'Foot'], H(s + 'Foot'), np.eye(3), g_foot, 0.05)
    add(POSED_J[s + 'ToeBase'], H(s + 'Foot') + (POSED_J[s + 'ToeBase'] - POSED_J[s + 'Foot']) * g_foot)
    add(POSED_J[s + 'ToeBase_end'], H(s + 'Foot') + (POSED_J[s + 'ToeBase_end'] - POSED_J[s + 'Foot']) * g_foot)
    # shoulder joint ring
    rigid(POSED_J[s + 'UpperArm'], arm_root(s), np.eye(3), g_perp, 0.03, n=6)
# head: rigid, scaled, pivot on head joint; sample a big sphere so the whole head (hair/ears) stays rigid
hc_k = POSED_J['Head'] + np.array([0, 0, 0.08]); hc_h = H('Head') + np.array([0, 0, 0.08 * g_head]) + P.get('head_offset', [0, 0, 0])
rigid(POSED_J['Head'], H('Head') + P.get('head_offset', [0, 0, 0]), np.eye(3), g_head, 0.03)
rigid(hc_k, hc_h, np.eye(3), g_head, 0.10)
rigid(hc_k, hc_h, np.eye(3), g_head, 0.16)

S = np.array(src); D = np.array(dst)
# drop duplicate control points
_, uidx = np.unique(np.round(S, 5), axis=0, return_index=True); S = S[np.sort(uidx)]; D = D[np.sort(uidx)]
N = len(S)
K = np.linalg.norm(S[:, None, :] - S[None, :, :], axis=2)  # phi(r) = r (3D biharmonic)
lam = P.get('tps_lambda', 1e-4)
A = np.zeros((N + 4, N + 4)); A[:N, :N] = K + lam * np.eye(N); Pm = np.hstack([np.ones((N, 1)), S]); A[:N, N:] = Pm; A[N:, :N] = Pm.T
rhs = np.zeros((N + 4, 3)); rhs[:N] = D
coef = np.linalg.solve(A, rhs)
def tps(X):
    out = np.empty_like(X)
    for i in range(0, len(X), 4096):
        x = X[i:i + 4096]
        U = np.linalg.norm(x[:, None, :] - S[None, :, :], axis=2)
        out[i:i + 4096] = U @ coef[:N] + coef[N] + x @ coef[N + 1:]
    return out
L('TPS control points', N, 'max ctrl residual', np.abs(tps(S) - D).max())
for d in mdata.values():
    d.co2 = tps(d.co1)
    d.keys2 = [(n, tps(k)) for n, k in d.keys1]

# normals follow the deformation: n' ~ J^-T n, J = (TPS Jacobian by central differences) @ (blended LBS rotation)
def lbs_jac(W):
    J = np.tile(np.eye(3), (len(W), 1, 1))
    for i, wd in enumerate(W):
        t = sum(wd.values())
        if t > 0: J[i] = sum(w / t * SKIN[b][:3, :3] for b, w in wd.items())
    return J
for d in mdata.values():
    h = 1e-3; Jt = np.empty((len(d.co1), 3, 3))
    for a in range(3):
        e = np.zeros(3); e[a] = h
        Jt[:, :, a] = (tps(d.co1 + e) - tps(d.co1 - e)) / (2 * h)
    M = np.transpose(np.linalg.inv(Jt @ lbs_jac(d.w)), (0, 2, 1))
    n2 = np.einsum('lij,lj->li', M[d.lv], d.ln)
    d.ln2 = n2 / np.maximum(np.linalg.norm(n2, axis=1, keepdims=True), 1e-12)
L('normals carried', {k: len(v.ln2) for k, v in mdata.items()})

# ------------------------------------------------------------------ dynamic chains: Karin's skirt/tail/hair/ear/ribbon bones stay real
# bones (parented under HL bones) so the piece's anim blueprint can run AnimDynamics on them. Bone frames: X along the chain.
DYN_PREFIX = ('Skirt_', 'Tail', 'Hair_tail_', 'Hair_side_', 'Hair_front', 'Ear_', 'Ribbon_')
DYN_STATIC = ('Skirt_root', 'Hair_front_root', 'Ribbon_hand_L_root', 'Ribbon_hand_R_root')
HL_PARENT = {'Hips': 'Hips', 'Spine': 'Spine1', 'Chest': 'Spine3', 'Neck': 'Spine3', 'Head': 'Head', 'LeftHand': 'LeftHand', 'RightHand': 'RightHand'}
def is_dyn(n): return P.get('dynamics', True) and n in KB and n.startswith(DYN_PREFIX) and '_end' not in n
DYN = [n for n in order if is_dyn(n)]  # parents first
def dyn_parent(n):
    p = KB[n].parent.name
    return p if is_dyn(p) else HL_PARENT[p]
DYNJ = dict(zip(DYN, tps(np.array([POSED_J[n] for n in DYN])))) if DYN else {}
def dyn_dir(n):
    kids = [c.name for c in KB[n].children]
    tgt = [k for k in kids if is_dyn(k)] or [k for k in kids if '_end' in k]
    if tgt:
        c = tgt[0]; cp = DYNJ[c] if c in DYNJ else tps(POSED_J[c][None])[0]
        return cp - DYNJ[n]
    par = dyn_parent(n); return DYNJ[n] - (DYNJ[par] if par in DYNJ else H(par))
def ue_frame(d_bl):
    x = np.array([d_bl[0], -d_bl[1], d_bl[2]]); x /= np.linalg.norm(x)
    # Y horizontal, Z = outward-up in the bone's vertical plane (dyn_params' asymmetric skirt limits rely on it)
    up = np.array([0, 0, 1.0]) if abs(x[2]) < 0.999 else np.array([1.0, 0, 0])
    y = np.cross(up, x); y /= np.linalg.norm(y); z = np.cross(x, y)
    return np.stack([x, y, z], 1)
def mat2quat(R):
    R = R / np.linalg.norm(R, axis=0)
    q = Quaternion(Matrix(R.tolist()).to_quaternion()); return [q.x, q.y, q.z, q.w]
DYNG = {}  # UE-space global transforms of the dynamic bones
skel_ext = [dict(b) for b in skel]; ext_idx = {b['name']: i for i, b in enumerate(skel)}
for n in DYN:
    G = np.eye(4); G[:3, :3] = ue_frame(dyn_dir(n)); G[:3, 3] = bl2ue_p(DYNJ[n]); DYNG[n] = G
    par = dyn_parent(n); Gp = DYNG[par] if par in DYNG else HG[HI[par]]
    loc = np.linalg.inv(Gp) @ G
    ext_idx[n] = len(skel_ext)
    skel_ext.append({'name': n, 'parent': ext_idx[par], 't': loc[:3, 3].tolist(), 'r': mat2quat(loc[:3, :3]), 's': [1.0, 1.0, 1.0]})
json.dump({'bones': skel_ext}, open(os.path.join(OUT, 'skel_ext.json'), 'w'))
# chains for the anim blueprints: start at a simulated bone whose parent isn't simulated, follow single children
def simulated(n): return n in DYNG and n not in DYN_STATIC
chains = []
for n in DYN:
    if not simulated(n) or simulated(dyn_parent(n)): continue
    c = [n]
    while True:
        kids = [k.name for k in KB[c[-1]].children if simulated(k.name)]
        if len(kids) != 1: break
        c.append(kids[0])
    lens = [float(np.linalg.norm(DYNG[c[i + 1]][:3, 3] - DYNG[c[i]][:3, 3])) for i in range(len(c) - 1)] or [float(np.linalg.norm(dyn_dir(n)) * 100)]
    chains.append({'root': c[0], 'end': c[-1], 'bones': c, 'parent': dyn_parent(n), 'seg_len': float(np.mean(lens))})
L('dynamic bones', len(DYN), 'chains', [(c['root'], len(c['bones']), round(c['seg_len'], 1)) for c in chains])

# ------------------------------------------------------------------ weights: Karin bones -> HL bone groups, twist split from vanilla
GROUPS = {}
def G_(k, hl): GROUPS[k] = hl
G_('Hips', ['Hips', 'Spine', 'Spine1']); G_('Spine', ['Spine', 'Spine1', 'Spine2', 'Spine3']); G_('Chest', ['Spine', 'Spine1', 'Spine2', 'Spine3'])
G_('Neck', ['Neck', 'Neck1', 'Spine3']); G_('Head', ['Head'])
for s in SIDES:
    G_(s + 'Shoulder', [s + 'Shoulder', 'Spine3', 'Neck'])  # trapezius blends into the spine like HL's own meshes
    G_(s + 'UpperArm', [s + 'Arm', s + 'ArmTwist1', s + 'ArmTwist2'])
    G_(s + 'LowerArm', [s + 'ForeArm', s + 'ForeArmTwist1', s + 'ForeArmTwist2', s + 'ForeArmTwist3'])
    G_(s + 'Hand', [s + 'Hand', s + 'InHandIndex', s + 'InHandMiddle', s + 'InHandRing', s + 'InHandPinky'])
    for kf, hf in (('Index', 'Index'), ('Middle', 'Middle'), ('Ring', 'Ring'), ('Little', 'Pinky'), ('Thumb', 'Thumb')):
        G_(s + kf + 'Proximal', [s + 'Hand' + hf + '1']); G_(s + kf + 'Intermediate', [s + 'Hand' + hf + '2']); G_(s + kf + 'Distal', [s + 'Hand' + hf + '3'])
    G_(s + 'UpperLeg', [s + 'UpLeg', s + 'UpLegTwist1', s + 'UpLegTwist2'])
    G_(s + 'LowerLeg', [s + 'Leg', s + 'LegTwist1'])
    G_(s + 'Foot', [s + 'Foot']); G_(s + 'ToeBase', [s + 'ToeBase'])
def hl_group_for(kname):
    if kname in GROUPS: return GROUPS[kname]
    n = kname
    for side, pre in (('_L', 'Left'), ('_R', 'Right')):
        pass
    if n.startswith(('Hair', 'Ear', 'Cheek', 'LeftEye', 'RightEye', 'Ribbon_L', 'Ribbon_R')): return ['Head']
    if n.startswith(('Ribbon_camisole', 'Ribbon_tops')): return ['Spine3']
    if n.startswith('Ribbon_hand_L'): return ['LeftHand']
    if n.startswith('Ribbon_hand_R'): return ['RightHand']
    if n.startswith('Shoes_tag_L'): return ['LeftFoot']
    if n.startswith('Shoes_tag_R'): return ['RightFoot']
    if n.startswith('Tail'): return ['Hips']
    if n.startswith('Skirt'): return ['SKIRT']
    return ['Hips']

# vanilla reference (HL weights) for splitting inside a group
refP, refW = [], []
for rj in cfg.get('ref_meshes', []):
    d = json.load(open(rj)); bones = [b['name'] for b in d['bones']]
    pos = np.array(d['pos']).reshape(-1, 3); bi = np.array(d['bi']).reshape(-1, 4); bw = np.array(d['bw']).reshape(-1, 4)
    for i in range(len(pos)):
        wd = {}
        for k in range(4):
            if bw[i, k] > 0: wd[bones[bi[i, k]]] = wd.get(bones[bi[i, k]], 0) + bw[i, k]
        refP.append(ue2bl_p(pos[i])); refW.append(wd)
L('reference verts', len(refP))
kd = kdtree.KDTree(len(refP))
for i, p in enumerate(refP): kd.insert(p, i)
kd.balance()
def split(group, p):
    if len(group) == 1: return {group[0]: 1.0}
    for (co, i, dist) in kd.find_n(p, 24):
        wd = refW[i]; s = {b: wd.get(b, 0) for b in group}; t = sum(s.values())
        if t > 0.05 and dist < 0.12: return {b: w / t for b, w in s.items() if w > 0}
    return {group[0]: 1.0}

hips_z = H('Hips')[2]
def skirt_w(p):
    # skirt follows the pelvis at the waist and the thighs toward the hem
    z0 = hips_z; z1 = H('LeftLeg')[2] * 0.5 + H('LeftUpLeg')[2] * 0.5
    t = min(1.0, max(0.0, (z0 - p[2]) / max(1e-4, z0 - z1)))
    leg = P.get('skirt_leg', 0.65) * t
    side = 'Left' if p[0] > 0 else 'Right'
    f = min(1.0, abs(p[0]) / 0.06)  # center seam splits evenly
    w = {'Hips': 1 - leg}
    w[side + 'UpLeg'] = w.get(side + 'UpLeg', 0) + leg * (0.5 + 0.5 * f)
    other = 'Right' if side == 'Left' else 'Left'
    if f < 1: w[other + 'UpLeg'] = leg * (0.5 - 0.5 * f)
    return w

def hl_weights(d):
    out = []
    for i, wd in enumerate(d.w):
        p = d.co2[i]; acc = {}
        tot = sum(wd.values()) or 1
        for kb, w in wd.items():
            if kb in DYNG: acc[kb] = acc.get(kb, 0) + w / tot; continue
            grp = hl_group_for(kb)
            sub = skirt_w(p) if grp == ['SKIRT'] else split(grp, p)
            for hb, sw in sub.items(): acc[hb] = acc.get(hb, 0) + w / tot * sw
        if not acc: acc = {'Hips': 1.0}
        top = sorted(acc.items(), key=lambda kv: -kv[1])[:4]
        t = sum(w for _, w in top)
        out.append({b: w / t for b, w in top if w / t > 0.004})
    return out
for d in mdata.values(): d.hw = hl_weights(d)

# ------------------------------------------------------------------ build HL armature + output parts
def build_armature(name):
    arm = bpy.data.armatures.new(name); ob = bpy.data.objects.new(name, arm); bpy.context.scene.collection.objects.link(ob)
    bpy.context.view_layer.objects.active = ob; bpy.ops.object.mode_set(mode='EDIT')
    eb = {}
    for i, b in enumerate(skel):
        e = arm.edit_bones.new(b['name']); h = ue2bl_p(HG[i][:3, 3])
        kids = [j for j, c in enumerate(skel) if c['parent'] == i]
        if kids:
            t = np.mean([ue2bl_p(HG[j][:3, 3]) for j in kids], axis=0)
            if np.linalg.norm(t - h) < 0.005: t = h + np.array([0, 0, 0.03])
        else:
            t = h + (h - ue2bl_p(HG[b['parent']][:3, 3])) * 0.3 if b['parent'] >= 0 else h + np.array([0, 0, 0.1])
            if np.linalg.norm(t - h) < 0.005: t = h + np.array([0, 0, 0.02])
        e.head = Vector(h); e.tail = Vector(t); eb[i] = e
    for i, b in enumerate(skel):
        if b['parent'] >= 0: eb[i].parent = eb[b['parent']]
    named = {b['name']: eb[i] for i, b in enumerate(skel)}
    for n in DYN:  # joint positions only; their ref pose (frames) comes from skel_ext.json at the patch step
        e = arm.edit_bones.new(n); h = DYNJ[n]; d = dyn_dir(n)
        e.head = Vector(h); e.tail = Vector(h + d / max(np.linalg.norm(d), 1e-6) * max(0.01, min(0.08, np.linalg.norm(d))))
        e.parent = named[dyn_parent(n)]; named[n] = e
    bpy.ops.object.mode_set(mode='OBJECT')
    return ob

PARTS = cfg['parts']  # {part: {"objects": [...], "materials": {karin_mat: slot}}}
def build_part(pname, spec, arm):
    verts, faces, uvs, mats, vw, keys, lnor = [], [], [], [], [], {}, []
    slot_names = []
    for oname in spec['objects']:
        d = mdata[oname]; me = d.obj.data; base = len(verts)
        verts += [tuple(v) for v in d.co2]
        vw += d.hw
        uvl = me.uv_layers.active.data
        for poly in me.polygons:
            kmat = d.obj.material_slots[poly.material_index].material.name
            slot = spec['materials'][kmat]
            if slot not in slot_names: slot_names.append(slot)
            faces.append([base + vi for vi in poly.vertices]); mats.append(slot_names.index(slot))
            uvs.append([tuple(uvl[li].uv) for li in poly.loop_indices])
            lnor += [tuple(d.ln2[li]) for li in poly.loop_indices]
        for kn, kc in d.keys2:
            if kn.startswith('---') or kn == '==': pass
            arr = keys.setdefault(oname + '|' + kn, (base, kc))
    me = bpy.data.meshes.new(pname); me.from_pydata(verts, [], faces); me.update()
    uvlay = me.uv_layers.new(name='UVMap')
    li = 0
    for fi, poly in enumerate(me.polygons):
        for k, l in enumerate(poly.loop_indices): uvlay.data[l].uv = uvs[fi][k]
        poly.material_index = mats[fi]; poly.use_smooth = True
    for sn in slot_names:
        m = bpy.data.materials.get(sn) or bpy.data.materials.new(sn); me.materials.append(m)
    if hasattr(me, 'use_auto_smooth'): me.use_auto_smooth = True  # < 4.1: custom normals need it
    me.normals_split_custom_set(lnor)
    ob = bpy.data.objects.new(pname, me); bpy.context.scene.collection.objects.link(ob)
    for i, wd in enumerate(vw):
        for b, w in wd.items():
            g = ob.vertex_groups.get(b) or ob.vertex_groups.new(name=b); g.add([i], w, 'REPLACE')
    if spec.get('shape_keys'):
        ob.shape_key_add(name='Basis')
        for kname, (base, kc) in keys.items():
            sk = ob.shape_key_add(name=kname.split('|', 1)[1]); co = np.array([v.co for v in sk.data])
            co[base:base + len(kc)] = kc; sk.data.foreach_set('co', co.ravel())
    if spec.get('morph_map_file'):
        # HL facial morphs (driven by name from the face pose asset curves) built from Karin's fitted shape keys
        mmap = {k: v for k, v in json.load(open(spec['morph_map_file'], encoding='utf-8')).items() if not k.startswith('_')}
        ob.shape_key_add(name='Basis'); allv = np.array(verts); made = []
        for hl, entries in mmap.items():
            delta = np.zeros_like(allv); base = 0
            for oname in spec['objects']:
                d = mdata[oname]; kd = dict(d.keys2)
                for e in entries:
                    if e[0] not in kd: L('morph', hl, 'missing key', e[0]); continue
                    dd = (kd[e[0]] - d.co2) * e[1]
                    if len(e) > 2:  # her left is +x; 8 mm blend across the centre line
                        wl = np.clip(0.5 + d.co2[:, 0] / 0.008, 0, 1); dd *= (wl if e[2] == 'L' else 1 - wl)[:, None]
                    delta[base:base + len(d.co2)] += dd
                base += len(d.co2)
            if np.abs(delta).max() < 1e-5: continue
            sk = ob.shape_key_add(name=hl); sk.data.foreach_set('co', (allv + delta).ravel()); made.append(hl)
        L('head morphs', len(made), 'of', len(mmap))
    mod = ob.modifiers.new('Armature', 'ARMATURE'); mod.object = arm; ob.parent = arm
    L('part', pname, 'verts', len(verts), 'faces', len(faces), 'slots', slot_names, 'maxinfl', max(len(w) for w in vw))
    return ob

arm = build_armature('HLArmature')
for o in kmeshes: o.hide_set(True)
karm.hide_set(True)
built = {pn: build_part(pn, spec, arm) for pn, spec in PARTS.items()}
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, 'fit.blend'))
# which part each chain skins (the part's anim blueprint simulates it)
for c in chains:
    c['parts'] = [pn for pn, ob in built.items() if any(ob.vertex_groups.get(b) is not None for b in c['bones'])]
json.dump(chains, open(os.path.join(OUT, 'dyn_chains.json'), 'w'), indent=1)
L('chain parts', {c['root']: c['parts'] for c in chains})

# ------------------------------------------------------------------ export FBX per part (+ skeleton FBX)
def export(objs, path):
    bpy.ops.object.select_all(action='DESELECT')
    arm.select_set(True)
    for o in objs: o.hide_set(False); o.select_set(True)
    bpy.context.view_layer.objects.active = arm
    bpy.ops.export_scene.fbx(filepath=path, use_selection=True, apply_unit_scale=True, apply_scale_options='FBX_SCALE_ALL',
                             object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, use_armature_deform_only=False,
                             bake_anim=False, mesh_smooth_type='FACE', use_mesh_modifiers=False, axis_forward='-Y', axis_up='Z')
for pn, ob in built.items(): export([ob], os.path.join(OUT, pn + '.fbx'))
# skeleton-only fbx: tiny triangle weighted to Hips so UE creates the full bone tree
me = bpy.data.meshes.new('SkelProxy'); me.from_pydata([(0, 0, 0.9), (0.01, 0, 0.9), (0, 0.01, 0.9)], [], [(0, 1, 2)]); me.update()
sp = bpy.data.objects.new('SkelProxy', me); bpy.context.scene.collection.objects.link(sp)
sp.vertex_groups.new(name='Hips').add([0, 1, 2], 1.0, 'REPLACE'); m = sp.modifiers.new('Armature', 'ARMATURE'); m.object = arm; sp.parent = arm
for ob in built.values(): ob.hide_set(True)
export([sp], os.path.join(OUT, 'Skeleton.fbx'))
# fitted vertex dump for checks (UE cm)
for pn, ob in built.items():
    np.save(os.path.join(OUT, pn + '_pos_ue.npy'), np.array([bl2ue_p(np.array(v.co)) for v in ob.data.vertices]))
L('done')
