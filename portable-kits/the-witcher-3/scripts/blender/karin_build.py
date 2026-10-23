"""Karin_Original -> Witcher 3 man_base mesh (native-rest route).

Run:  blender --background --factory-startup --python scripts/blender/karin_build.py -- '{"stage":"all"}'
      (W3_WORK, W3_GAME_DIR, W3_SOURCE_FBX set, see scripts/w3paths.py; any CFG key can be overridden in the JSON)

The game skeleton (man_base.w2rig) and its rest pose stay untouched (animations carry bone
translations). Karin's geometry is fitted onto the man_base joints with per-bone affine maps
(linear-blend, Karin's own weights), then weights are re-targeted to man_base bones following the
vanilla Geralt body weighting habits (roll bones carry forearm twist, etc.).
"""
import bpy
import json
import math
import os
import sys
import importlib
import addon_utils
from mathutils import Matrix, Vector, Quaternion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))   # kit scripts/
import w3paths  # noqa: E402

ARGS = {}
if '--' in sys.argv:
    tail = sys.argv[sys.argv.index('--') + 1:]
    if tail:
        ARGS = json.loads(tail[0])

CFG = {
    'karin_fbx': None,          # None -> W3_SOURCE_FBX
    'uncook': None,             # None -> <W3_WORK>\uncook\
    'rig': r'characters\base_entities\man_base\man_base.w2rig',
    'depot_out': None,          # None -> <W3_WORK>\build\depot\
    'mesh_depot': r'characters\models\karin\karin_body.w2mesh',
    'tex_depot_dir': r'characters\models\karin\textures',
    'png_dir': None,            # None -> <W3_WORK>\karin_src\textures
    'blend_out': None,          # None -> <W3_WORK>\blend\karin_fit.blend
    'report': None,             # None -> <W3_WORK>\scratch\karin_build_report.json
    # fitting
    'torso_w_ratio': 1.00,     # hips width scale relative to torso vertical scale
    'torso_d_ratio': 1.00,     # hips depth scale relative to torso vertical scale
    'chest_w_ratio': 0.88,     # chest width (waist = mean of hips and chest); 1.0 made the upper body look fat
    'chest_d_ratio': 0.92,
    'head_scale': 1.50,
    'neck_cross': 1.50,
    'neck_along': 1.50,        # neck stretch along its axis (None -> full man_base length, ~2.0: too long)
    'arm_cross': 1.38,
    # narrow shoulders: the upper arm hangs from a pivot arm_root_inset inside the man_base shoulder joint
    # (horizontal, carried by the clavicle). The arm/shoulder region is fitted in Geralt's idle pose and solved
    # back to the bind pose through the final weights, so the idle stance shows exactly that shape (v0.3.0 rotated
    # a fixed offset back to the bind pose; shoulderRoll barely turns in the idle, which left a notch at the arm root)
    'arm_root_inset': 0.05,
    'arm_root_lift': 0.0,
    'idle_anim': [r'animations\man\movement\man_geralt_movement.w2anims', 'locomotion_idle', 0],
    'ua_shoulder_roll': True,  # upper arm root weighted to shoulderRoll like vanilla (False: bicep2/bicep only)
    'hand_scale': 1.40,
    'leg_cross': 1.50,
    'foot_h': 1.30,
    'foot_v': None,            # None -> ankle height match
    'shoulder_shift_frac': 1.0,  # clavicle region shifted this share of the way to the arm pivot
    'forearm_twist_frac': 1.0,
    'tail_scale': 0.75,
    'ear_scale': 1.0,
    'albedo_scale': 0.82,      # pure-white anime albedo glows under W3 character lighting
    'spec_rgb': 0.08,
    'tex_size': 2048,
    'physics': True,
    'face': True,
    'face_mesh_depot': r'characters\models\karin\karin_face.w2mesh',
    'face_spec': None,          # None -> <W3_WORK>\build\karin_face_spec.json
    'w3fac_template': None,     # None -> <uncook>characters\models\geralt\head\model\h_01_mg__geralt.w3fac.json
    'face_poses': 129,
    'face_bones': 100,          # mimic skeleton = 6 anchors + 2 x bones (placer + bone) -> 206
    'face_k_near': 4,
    'face_sig_gain': 6.0,
    'face_smooth': 0.005,
    'face_rounds': 5,
    'face_act_thr': 0.0008,
    'face_sigma': 1.2,
    'face_lambda': 1e-4,
    'face_side_width': 0.012,
    # skirt below the hip joints partly skinned to the thighs (sphere collisions alone let a raised thigh
    # pass between the skirt nodes): weight share ramps from skirt_follow_top above the hip joints to
    # skirt_thigh_follow at skirt_follow_full below them, split left/right over skirt_follow_split (m)
    'skirt_thigh_follow': 0.6,
    'skirt_follow_top': 0.03,
    'skirt_follow_full': 0.15,
    'skirt_follow_split': 0.025,
    'dyng_margin': 0.015,
    'dyng_collide_per_node': 2,
    'dyng_head_centre': (0.03, -0.02, 0.0),
    'dyng_spec': None,          # None -> <W3_WORK>\build\karin_dyng_spec.json
    'stage': 'all',
}
CFG.update(ARGS)
for _key, _default in (('karin_fbx', w3paths.source_fbx), ('uncook', lambda: w3paths.work_dir('uncook')),
                       ('depot_out', lambda: w3paths.work_dir('build', 'depot')),
                       ('png_dir', lambda: w3paths.work('karin_src', 'textures')),
                       ('blend_out', lambda: w3paths.work('blend', 'karin_fit.blend')),
                       ('report', lambda: w3paths.work('scratch', 'karin_build_report.json')),
                       ('face_spec', lambda: w3paths.work('build', 'karin_face_spec.json')),
                       ('w3fac_template', lambda: CFG['uncook'] + r'characters\models\geralt\head\model\h_01_mg__geralt.w3fac.json'),
                       ('dyng_spec', lambda: w3paths.work('build', 'karin_dyng_spec.json'))):
    if CFG.get(_key) is None:
        CFG[_key] = _default()
REPORT = {'cfg': CFG}

MOD = w3paths.addon_module()


def log(*a):
    print('[karin_build]', *a, flush=True)


# ----------------------------------------------------------------------------- setup
def setup_addon():
    addon_utils.enable(MOD, default_set=True)
    prefs = bpy.context.preferences.addons[MOD].preferences
    prefs.witcher_game_path = w3paths.game()
    prefs.uncook_path = CFG['uncook']
    prefs.wolvenkit = w3paths.wolvenkit_cli()


def import_target_rig():
    irig = importlib.import_module(MOD + '.importers.import_rig')
    before = set(bpy.data.objects)
    irig.import_w3_rig(CFG['uncook'] + CFG['rig'], ns='')
    arm = [o for o in set(bpy.data.objects) - before if o.type == 'ARMATURE'][0]
    arm.name = 'man_base'
    return arm


def idle_pose(tarm):
    """{man_base bone: world transform bind -> Geralt's idle pose} from a vanilla animation frame; the armature
    is returned to its rest pose afterwards."""
    dca = importlib.import_module(MOD + '.CR2W.dc_anims')
    ia = importlib.import_module(MOD + '.importers.import_anims')
    path, name, frame = CFG['idle_anim']
    path = CFG['uncook'] + path
    aset = dca.load_bin_anims_single(path, name, rigPath=CFG['uncook'] + CFG['rig'])
    entry = [e for e in aset.animations if e.animation.name == name][0]
    ia.import_anim(bpy.context, path, entry, override_select=tarm)
    bpy.context.scene.frame_set(frame)
    mw = tarm.matrix_world
    G = {pb.name: (mw @ pb.matrix) @ (mw @ pb.bone.matrix_local).inverted() for pb in tarm.pose.bones}
    tarm.animation_data_clear()
    for pb in tarm.pose.bones:
        pb.matrix_basis = Matrix.Identity(4)
    bpy.context.view_layer.update()
    return G


def import_karin():
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=CFG['karin_fbx'])
    new = set(bpy.data.objects) - before
    karm = [o for o in new if o.type == 'ARMATURE'][0]
    meshes = [o for o in new if o.type == 'MESH']
    return karm, meshes


# ----------------------------------------------------------------------------- math helpers
RZ = Matrix.Rotation(math.pi, 4, 'Z')


def T(v):
    return Matrix.Translation(Vector(v))


def M3to4(m3):
    m = m3.to_4x4()
    return m


def axis_scale(d, along, cross):
    """3x3: scale `along` on unit axis d, `cross` perpendicular."""
    d = Vector(d).normalized()
    m = Matrix.Identity(3) * cross
    outer = Matrix(((d.x * d.x, d.x * d.y, d.x * d.z), (d.y * d.x, d.y * d.y, d.y * d.z), (d.z * d.x, d.z * d.y, d.z * d.z)))
    for i in range(3):
        for j in range(3):
            m[i][j] += (along - cross) * outer[i][j]
    return m


def min_rot(a, b):
    return Vector(a).normalized().rotation_difference(Vector(b).normalized()).to_matrix()


def frame(a, b):
    a = Vector(a).normalized()
    b = (Vector(b) - a * a.dot(Vector(b))).normalized()
    c = a.cross(b)
    return Matrix((a, b, c)).transposed()  # columns a,b,c


def twist_angle(R, axis):
    """twist of rotation R around unit axis (swing-twist decomposition)."""
    q = R.to_quaternion()
    axis = Vector(axis).normalized()
    p = Vector((q.x, q.y, q.z))
    proj = axis * p.dot(axis)
    tw = Quaternion((q.w, proj.x, proj.y, proj.z))
    if tw.magnitude < 1e-9:
        return 0.0
    tw.normalize()
    ang = 2 * math.atan2(Vector((tw.x, tw.y, tw.z)).dot(axis), tw.w)
    if ang > math.pi:
        ang -= 2 * math.pi
    if ang < -math.pi:
        ang += 2 * math.pi
    return ang


# ----------------------------------------------------------------------------- fitting
SIDES = (('Left', 'l_'), ('Right', 'r_'))
FINGERS = (('Thumb', 'thumb'), ('Index', 'index'), ('Middle', 'middle'), ('Ring', 'ring'), ('Little', 'pinky'))
SEGS = ('Proximal', 'Intermediate', 'Distal')


ARM_ROOT_BIND = {}   # side prefix -> bind-space image (through the bicep) of the idle upper arm root


def build_fit(karm, tarm, G):
    """G: idle pose (idle_pose). Returns M (Karin bone -> bind-space affine), S, Q and N (Karin bone -> idle-space
    affine for the bones fitted in the idle pose)."""
    kb = karm.data.bones
    tb = tarm.data.bones

    def S(name):
        return (RZ @ karm.matrix_world @ kb[name].head_local).to_3d()

    def Q(name):
        return (tarm.matrix_world @ tb[name].head_local).to_3d()

    M = {}
    N = {}
    info = {}
    # --- torso affine: Karin hip-joint line -> man_base thigh joints, Karin Neck -> neck
    s_leg_z = (S('LeftUpperLeg').z + S('RightUpperLeg').z) / 2
    t_leg_z = (Q('l_thigh').z + Q('r_thigh').z) / 2
    kv = (Q('neck').z - t_leg_z) / (S('Neck').z - s_leg_z)
    # spine lines (y as function of z)
    s_y0, s_y1 = S('Hips').y, S('Neck').y
    s_z0, s_z1 = S('Hips').z, S('Neck').z
    t_y0, t_y1 = Q('pelvis').y, Q('neck').y
    t_z0, t_z1 = Q('pelvis').z, Q('neck').z

    def torso_affine(w_ratio, d_ratio):
        sx, sy = kv * w_ratio, kv * d_ratio

        def torso_map(p):
            z = t_leg_z + (p.z - s_leg_z) * kv
            ys = s_y0 + (p.z - s_z0) * (s_y1 - s_y0) / (s_z1 - s_z0)
            yt = t_y0 + (z - t_z0) * (t_y1 - t_y0) / (t_z1 - t_z0)
            return Vector((p.x * sx, (p.y - ys) * sy + yt, z))

        # affine matrix from 4 points
        o = torso_map(Vector((0, 0, 0)))
        ex = torso_map(Vector((1, 0, 0))) - o
        ey = torso_map(Vector((0, 1, 0))) - o
        ez = torso_map(Vector((0, 0, 1))) - o
        return Matrix(((ex.x, ey.x, ez.x, o.x), (ex.y, ey.y, ez.y, o.y), (ex.z, ey.z, ez.z, o.z), (0, 0, 0, 1)))

    # hips keep the full ratio (legs sit on the man_base hip joints, the skirt is tuned against them); waist and
    # chest are slimmer so the girl's upper body is not scaled thicker than her head and limbs
    wr = (CFG['torso_w_ratio'], (CFG['torso_w_ratio'] + CFG['chest_w_ratio']) / 2, CFG['chest_w_ratio'])
    dr = (CFG['torso_d_ratio'], (CFG['torso_d_ratio'] + CFG['chest_d_ratio']) / 2, CFG['chest_d_ratio'])
    for b, w, d in zip(('Hips', 'Spine', 'Chest'), wr, dr):
        M[b] = torso_affine(w, d)
    A_C = M['Chest']
    info['torso'] = {'kv': kv, 'w': [kv * w for w in wr], 'd': [kv * d for d in dr]}

    # --- neck & head
    # Karin's short neck stretched to the full man_base neck-head distance looks long and thin: stretch it by
    # neck_along only and let the head sit that much below the man_base head joint
    d_s = S('Head') - S('Neck')
    d_t = Q('head') - Q('neck')
    along = CFG['neck_along'] or d_t.length / d_s.length
    head_pos = Q('neck') + d_t.normalized() * (d_s.length * along)
    R = min_rot(d_s, d_t)
    A = axis_scale(d_s, along, CFG['neck_cross'])
    M['Neck'] = T(Q('neck')) @ M3to4(R @ A) @ T(-S('Neck'))
    M['Head'] = T(head_pos) @ M3to4(Matrix.Identity(3) * CFG['head_scale']) @ T(-S('Head'))
    info['neck'] = {'along': along, 'full_along': d_t.length / d_s.length, 'head_drop': (Q('head') - head_pos).length}

    # --- arms
    for side, p in SIDES:
        sh, ua, la, ha = side + 'Shoulder', side + 'UpperArm', side + 'LowerArm', side + 'Hand'
        # the man_base shoulder joints are far wider than a girl's: the upper arm hangs from a pivot P
        # arm_root_inset inside the joint (toward the clavicle's inner end), carried by the clavicle
        J = Q(p + 'bicep')
        E = Q(p + 'forearm')
        h = Q(p + 'shoulder') - J
        P = J + Vector((h.x, h.y, 0)).normalized() * CFG['arm_root_inset'] + Vector((0, 0, CFG['arm_root_lift']))
        # clavicle: chest affine + shift toward the pivot
        delta = P - (A_C @ S(ua))
        M[sh] = T(delta * CFG['shoulder_shift_frac']) @ A_C
        # upper arm on the man_base bone (bind pose, root on the joint): source of the weights and of the idle fit
        ds = S(la) - S(ua)
        dt = E - J
        R_ua = min_rot(ds, dt)
        M[ua] = T(J) @ M3to4(R_ua @ axis_scale(ds, dt.length / ds.length, CFG['arm_cross'])) @ T(-S(ua))
        # idle pose: the bicep carries that arm, then it is re-aimed about the elbow so its root sits on the pivot
        Gb = G[p + 'bicep']
        Pi, Ji, Ei = G[p + 'shoulder'] @ P, Gb @ J, Gb @ E
        u0, u1 = Ei - Ji, Ei - Pi
        N[ua] = T(Ei) @ M3to4(min_rot(u0, u1) @ axis_scale(u0, u1.length / u0.length, 1.0)) @ T(-Ei) @ Gb @ M[ua]
        ARM_ROOT_BIND[p] = Gb.inverted() @ Pi
        # hand frame
        a_s = S(side + 'MiddleProximal') - S(ha)
        b_s = S(side + 'IndexProximal') - S(side + 'LittleProximal')
        a_t = Q(p + 'middle1') - Q(p + 'hand')
        b_t = Q(p + 'index1') - Q(p + 'pinky1')
        R_h = frame(a_t, b_t) @ frame(a_s, b_s).transposed()
        # lower arm: minimal from upper arm, plus share of the hand twist
        ds2 = S(ha) - S(la)
        dt2 = Q(p + 'hand') - Q(p + 'forearm')
        R_la0 = min_rot(R_ua @ ds2, dt2) @ R_ua
        tw = twist_angle(R_h @ R_la0.inverted(), dt2)
        R_la = Matrix.Rotation(tw * CFG['forearm_twist_frac'], 3, dt2.normalized()) @ R_la0
        M[la] = T(Q(p + 'forearm')) @ M3to4(R_la @ axis_scale(ds2, dt2.length / ds2.length, CFG['arm_cross'])) @ T(-S(la))
        M[ha] = T(Q(p + 'hand')) @ M3to4(R_h @ (Matrix.Identity(3) * CFG['hand_scale'])) @ T(-S(ha))
        info[side + 'Arm'] = {'ua_along': dt.length / ds.length, 'la_along': dt2.length / ds2.length,
                              'hand_twist_deg': math.degrees(tw), 'shoulder_delta': list(delta),
                              'pivot_offset': list(P - J), 'idle_root_offset': list(Pi - Ji),
                              'idle_ua_along': u1.length / ds.length,
                              'idle_elbow_err': (Ei - G[p + 'forearm'] @ E).length}
        # fingers
        for kf, tf in FINGERS:
            R_par = R_h
            for i, seg in enumerate(SEGS):
                kname = side + kf + seg
                tname = p + tf + str(i + 1)
                if i < 2:
                    ks_next = side + kf + SEGS[i + 1]
                    ds_f = S(ks_next) - S(kname)
                    dt_f = Q(p + tf + str(i + 2)) - Q(tname)
                    along = dt_f.length / ds_f.length
                else:
                    end = kname + '_end'
                    ds_f = (S(end) - S(kname)) if end in kb else (S(kname) - S(side + kf + SEGS[i - 1]))
                    dt_f = Q(tname) - Q(p + tf + str(i))
                    along = CFG['hand_scale']
                R_f = min_rot(R_par @ ds_f, dt_f) @ R_par
                M[kname] = T(Q(tname)) @ M3to4(R_f @ axis_scale(ds_f, along, CFG['hand_scale'])) @ T(-S(kname))
                R_par = R_f
    # --- legs
    for side, p in SIDES:
        ul, ll, ft, toe = side + 'UpperLeg', side + 'LowerLeg', side + 'Foot', side + 'ToeBase'
        ds = S(ll) - S(ul)
        dt = Q(p + 'shin') - Q(p + 'thigh')
        R_ul = min_rot(ds, dt)
        M[ul] = T(Q(p + 'thigh')) @ M3to4(R_ul @ axis_scale(ds, dt.length / ds.length, CFG['leg_cross'])) @ T(-S(ul))
        ds2 = S(ft) - S(ll)
        dt2 = Q(p + 'foot') - Q(p + 'shin')
        R_ll = min_rot(R_ul @ ds2, dt2) @ R_ul
        M[ll] = T(Q(p + 'shin')) @ M3to4(R_ll @ axis_scale(ds2, dt2.length / ds2.length, CFG['leg_cross'])) @ T(-S(ll))
        # foot: keep the sole flat, yaw to the man_base toe direction, ankle height preserved
        fs = S(toe) - S(ft)
        ftg = Q(p + 'toe') - Q(p + 'foot')
        yaw = math.atan2(ftg.y, ftg.x) - math.atan2(fs.y, fs.x)
        fv = CFG['foot_v'] or (Q(p + 'foot').z / S(ft).z)
        A = Matrix.Diagonal((CFG['foot_h'], CFG['foot_h'], fv))
        M[ft] = T(Q(p + 'foot')) @ M3to4(Matrix.Rotation(yaw, 3, 'Z') @ A) @ T(-S(ft))
        M[toe] = M[ft]
        info[side + 'Leg'] = {'ul_along': dt.length / ds.length, 'll_along': dt2.length / ds2.length,
                              'foot_v': fv, 'foot_yaw_deg': math.degrees(yaw)}
    # eyes follow head
    for e in ('LeftEye', 'RightEye'):
        M[e] = M['Head']
    # secondary subtrees with their own extra scale about their root joint (tail, ears)
    for root, key in (('Tail', 'tail_scale'), ('Ear_L', 'ear_scale'), ('Ear_R', 'ear_scale')):
        k = CFG.get(key, 1.0)
        if root not in kb or abs(k - 1.0) < 1e-6:
            continue
        parent_M = M[kb[root].parent.name]
        Ms = parent_M @ T(S(root)) @ M3to4(Matrix.Identity(3) * k) @ T(-S(root))
        stack = [kb[root]]
        while stack:
            b = stack.pop()
            M[b.name] = Ms
            stack.extend(b.children)
    # every other Karin bone: nearest fitted ancestor
    for b in kb:
        if b.name in M:
            continue
        a = b.parent
        while a is not None and a.name not in M:
            a = a.parent
        M[b.name] = M[a.name] if a is not None else M['Hips']
    REPORT['fit'] = info
    return M, S, Q, N


# ----------------------------------------------------------------------------- weights
HUMANOID_ANCESTOR_TARGET = {}


def nearest_humanoid(kb, name, humanoid):
    b = kb[name]
    while b is not None and b.name not in humanoid:
        b = b.parent
    return b.name if b is not None else 'Hips'


def hat(t, pts):
    """pts: [(t0, name0), (t1, name1), ...] ascending. Returns {name: w} (partition of unity)."""
    if t <= pts[0][0]:
        return {pts[0][1]: 1.0}
    if t >= pts[-1][0]:
        return {pts[-1][1]: 1.0}
    for (t0, n0), (t1, n1) in zip(pts, pts[1:]):
        if t0 <= t <= t1:
            f = (t - t0) / (t1 - t0) if t1 > t0 else 1.0
            out = {}
            out[n0] = out.get(n0, 0) + (1 - f)
            out[n1] = out.get(n1, 0) + f
            return out
    return {pts[-1][1]: 1.0}


def make_retarget(Q):
    def seg_t(v, a, b):
        d = Q(b) - Q(a)
        return (v - Q(a)).dot(d) / d.length_squared

    spine = [(Q('pelvis').z + 0.15, 'pelvis'), (Q('torso').z + 0.15, 'torso'), (Q('torso2').z + 0.10, 'torso2'), (Q('torso3').z + 0.05, 'torso3')]

    def retarget(kname, w, v):
        """Karin humanoid bone + weight + fitted position -> {man_base bone: weight}."""
        out = {}

        def add(d, scale=1.0):
            for n, x in d.items():
                out[n] = out.get(n, 0) + x * w * scale

        if kname in ('Hips', 'Spine', 'Chest'):
            add(hat(v.z, spine))
        elif kname == 'Neck':
            add({'neck': 1})
        elif kname in ('Head', 'LeftEye', 'RightEye'):
            add({'head': 1})
        else:
            for side, p in SIDES:
                if not kname.startswith(side):
                    continue
                part = kname[len(side):]
                if part == 'Shoulder':
                    add({p + 'shoulder': 1})
                elif part == 'UpperArm':
                    t = seg_t(v, p + 'bicep', p + 'forearm')
                    pts = [(0.0, p + 'shoulderRoll'), (0.25, p + 'bicep2'), (0.6, p + 'bicep')]
                    add(hat(t, pts if CFG['ua_shoulder_roll'] else pts[1:]))
                elif part == 'LowerArm':
                    t = seg_t(v, p + 'forearm', p + 'hand')
                    add(hat(t, [(0.0, p + 'elbowRoll'), (0.3, p + 'forearmRoll1'), (0.65, p + 'forearmRoll2'), (0.95, p + 'handRoll')]))
                elif part == 'Hand':
                    add({p + 'hand': 1})
                elif part == 'UpperLeg':
                    t = seg_t(v, p + 'thigh', p + 'shin')
                    # top: legRoll (front) / legRoll2 (back)
                    front = 1.0 if v.y > Q(p + 'thigh').y else 0.0
                    top = {p + 'legRoll': front, p + 'legRoll2': 1 - front}
                    h = hat(t, [(0.0, 'TOP'), (0.35, p + 'thigh'), (0.9, p + 'thigh'), (1.0, p + 'kneeRoll')])
                    for n, x in h.items():
                        if n == 'TOP':
                            add(top, x)
                        else:
                            add({n: x})
                elif part == 'LowerLeg':
                    t = seg_t(v, p + 'shin', p + 'foot')
                    add(hat(t, [(0.0, p + 'kneeRoll'), (0.2, p + 'shin')]))
                elif part == 'Foot':
                    add({p + 'foot': 1})
                elif part == 'ToeBase':
                    add({p + 'toe': 1})
                else:
                    for kf, tf in FINGERS:
                        for i, seg in enumerate(SEGS):
                            if part == kf + seg:
                                add({p + tf + str(i + 1): 1})
        if not out:
            raise KeyError(kname)
        return out
    return retarget


HUMANOID = set(['Hips', 'Spine', 'Chest', 'Neck', 'Head', 'LeftEye', 'RightEye'])
for _s, _p in SIDES:
    HUMANOID.update(_s + x for x in ('Shoulder', 'UpperArm', 'LowerArm', 'Hand', 'UpperLeg', 'LowerLeg', 'Foot', 'ToeBase'))
    for _kf, _tf in FINGERS:
        HUMANOID.update(_s + _kf + seg for seg in SEGS)


# ----------------------------------------------------------------------------- mesh processing
def blend4(pairs):
    """weighted sum of 4x4 matrices"""
    out = Matrix(((0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0), (0, 0, 0, 0)))
    for m, w in pairs:
        out += m * w
    return out


def process_mesh(o, karm, M, retarget, keep=frozenset(), samples=None, capture_keys=None, G=None, N=None):
    """keep: Karin secondary bones that stay as their own (dyng) bones instead of collapsing onto the
    humanoid ancestor. samples: optional list collecting (fitted position, dominant target bone).
    capture_keys: shape keys whose fitted displacement fields are returned (result['capture']).
    G, N: idle pose and idle-space affines (build_fit) for the vertices solved in the idle pose."""
    me = o.data
    kb = karm.data.bones
    local_deltas = {}
    if me.shape_keys and capture_keys:
        kbk = me.shape_keys.key_blocks
        basis = kbk[0]
        for name in capture_keys:
            if name in kbk:
                local_deltas[name] = [kbk[name].data[i].co - basis.data[i].co for i in range(len(me.vertices))]
    # bake basis shape, drop shape keys
    if me.shape_keys:
        basis = me.shape_keys.key_blocks[0]
        for i, v in enumerate(me.vertices):
            v.co = basis.data[i].co
        o.shape_key_clear()
    gname = {g.index: g.name for g in o.vertex_groups}
    mw = RZ @ o.matrix_world
    nmw = mw.to_3x3().inverted().transposed()
    new_pos = []
    lin = []
    new_w = []
    unweighted = 0
    idle_solved = idle_skipped = 0
    for v in me.vertices:
        p = mw @ v.co
        acc = Vector((0, 0, 0))
        L = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
        tot = 0.0
        ws = []
        for g in v.groups:
            n = gname.get(g.group)
            if n is None or n not in kb or g.weight <= 1e-6:
                continue
            ws.append((n, g.weight))
            tot += g.weight
        if tot <= 0:
            unweighted += 1
            ws = [('Hips', 1.0)]
            tot = 1.0
        for n, w in ws:
            w /= tot
            Mb = M[n]
            acc += w * (Mb @ p)
            L += Mb.to_3x3() * w
        # weights -> man_base
        tw = {}
        parts = []      # (karin bone, humanoid or None for dyng bones, weight, {man_base bone: weight})
        for n, w in ws:
            w /= tot
            if n in keep:
                tw[n] = tw.get(n, 0) + w
                parts.append((n, None, w, None))
                continue
            hn = nearest_humanoid(kb, n, HUMANOID)
            r = retarget(hn, w, acc)
            parts.append((n, hn, w, r))
            for tn, tx in r.items():
                tw[tn] = tw.get(tn, 0) + tx
        top = sorted(tw.items(), key=lambda x: -x[1])[:4]
        s = sum(x for _, x in top)
        final = [(n, x / s) for n, x in top if x / s > 1e-4]
        # arm/shoulder region: Karin's own skinning evaluated in the idle pose (N for the bones fitted there, the
        # retargeted man_base bones carrying M elsewhere), solved back to the bind pose through the final weights
        if N and any(hn in N for _, hn, _, _ in parts):
            if any(hn is None for _, hn, _, _ in parts):
                idle_skipped += 1
            else:
                tgt = Vector((0, 0, 0))
                Lt = Matrix(((0, 0, 0), (0, 0, 0), (0, 0, 0)))
                for n, hn, w, r in parts:
                    if hn in N:
                        A = N[hn]
                    else:
                        A = blend4((G[tn], x / w) for tn, x in r.items()) @ M[n]
                    tgt += w * (A @ p)
                    Lt += A.to_3x3() * w
                Binv = blend4((G[tn], x) for tn, x in final).inverted()
                acc = Binv @ tgt
                L = Binv.to_3x3() @ Lt
                idle_solved += 1
        new_pos.append(acc)
        lin.append(L)
        new_w.append(final)
        if samples is not None:
            samples.append((acc.copy(), top[0][0], o.name))
    capture = None
    if capture_keys is not None:
        import numpy as np
        m3 = mw.to_3x3()
        capture = {'pos': np.array([tuple(p) for p in new_pos]), 'keys': {},
                   'base_weights': new_w}
        for name, dl in local_deltas.items():
            capture['keys'][name] = np.array([tuple(lin[i] @ (m3 @ d)) for i, d in enumerate(dl)])
    # normals (corner normals before moving vertices)
    corner_n = [Vector(cn.vector) for cn in me.corner_normals]
    loop_v = [l.vertex_index for l in me.loops]
    # write positions (object space = identity transform later)
    for v, p in zip(me.vertices, new_pos):
        v.co = p
    new_n = []
    for li, vi in enumerate(loop_v):
        n = (nmw @ corner_n[li])
        n = (lin[vi].inverted_safe().transposed() @ n).normalized()
        new_n.append(n)
    # clear transform
    o.parent = None
    o.matrix_world = Matrix.Identity(4)
    me.normals_split_custom_set(new_n)
    # replace vertex groups
    for g in list(o.vertex_groups):
        o.vertex_groups.remove(g)
    groups = {}
    for vi, lst in enumerate(new_w):
        for n, x in lst:
            if n not in groups:
                groups[n] = o.vertex_groups.new(name=n)
            groups[n].add([vi], x, 'REPLACE')
    for m in list(o.modifiers):
        o.modifiers.remove(m)
    # uv & colors
    while len(me.uv_layers) > 1:
        me.uv_layers.remove(me.uv_layers[-1])
    if me.uv_layers:
        me.uv_layers[0].name = 'UVMap'
    for ca in list(me.color_attributes):
        me.color_attributes.remove(ca)
    return {'verts': len(me.vertices), 'unweighted': unweighted, 'groups': sorted(groups), 'capture': capture,
            'idle_solved': idle_solved, 'idle_skipped': idle_skipped}


def skirt_follow_thighs(o, Q):
    """Blend the processed skirt below the hip joints toward l_thigh / r_thigh so a raised thigh carries the
    skirt instead of passing through it; the dyng bones keep the rest of each vertex weight."""
    a_max = CFG['skirt_thigh_follow']
    if a_max <= 0:
        return 0
    hip_z = (Q('l_thigh').z + Q('r_thigh').z) / 2
    z0, z1 = hip_z + CFG['skirt_follow_top'], hip_z - CFG['skirt_follow_full']
    groups = {g.name: g for g in o.vertex_groups}
    for n in ('l_thigh', 'r_thigh'):
        if n not in groups:
            groups[n] = o.vertex_groups.new(name=n)
    gname = {g.index: g.name for g in o.vertex_groups}
    count = 0
    for v in o.data.vertices:
        t = min(1.0, (z0 - v.co.z) / (z0 - z1))
        if t <= 0:
            continue
        a = a_max * t * t * (3 - 2 * t)
        wl = 1.0 / (1.0 + math.exp(v.co.x / CFG['skirt_follow_split']))   # character's left = -x
        ws = {gname[g.group]: g.weight for g in v.groups if g.weight > 0}
        new = {k: x * (1 - a) for k, x in ws.items()}
        new['l_thigh'] = new.get('l_thigh', 0.0) + a * wl
        new['r_thigh'] = new.get('r_thigh', 0.0) + a * (1 - wl)
        top = sorted(new.items(), key=lambda kv: -kv[1])[:4]
        s = sum(x for _, x in top)
        for k in ws:
            groups[k].remove([v.index])
        for k, x in top:
            if x / s > 1e-4:
                groups[k].add([v.index], x / s, 'REPLACE')
        count += 1
    return count


# ----------------------------------------------------------------------------- materials / textures
def find_image(mat, prefer=None):
    imgs = []
    for n in mat.node_tree.nodes if mat.use_nodes else []:
        if n.type == 'TEX_IMAGE' and n.image:
            imgs.append(n.image)
    if prefer:
        for i in imgs:
            if prefer in i.name:
                return i
    return imgs[0] if imgs else None


def image_pixels(img):
    import numpy as np
    w, h = img.size
    a = np.empty(w * h * 4, dtype=np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(h, w, 4)


def new_image(name, arr):
    import numpy as np
    h, w, _ = arr.shape
    img = bpy.data.images.new(name, w, h, alpha=True)
    img.pixels.foreach_set(np.ascontiguousarray(arr, dtype=np.float32).ravel())
    return img


def prep_textures(mats):
    """returns {material_name: (diffuse_depot_path, enableMask)} and exports xbm files."""
    import ctypes
    # texconv (WIC) needs COM on this thread; Blender --background does not initialise it
    ctypes.windll.ole32.CoInitializeEx(None, 0)
    exm = importlib.import_module(MOD + '.exporters.export_xbm')
    out = {}
    size = CFG['tex_size']
    texdir = os.path.join(CFG['depot_out'], CFG['tex_depot_dir'])
    os.makedirs(texdir, exist_ok=True)
    pngdir = CFG['png_dir']
    os.makedirs(pngdir, exist_ok=True)
    plan = {
        'Karin_Body': ('karin_body_d', None, False),
        'Karin_Face': ('karin_face_d', None, False),
        'Karin_Costume': ('karin_costume_d', None, False),
        'Karin_Hair': ('karin_hair_d', None, False),
        'Karin_Hair_Transparent': ('karin_hair_a_d', 'Clipping', True),
        'Karin_Alpha': ('karin_alpha_d', None, True),
    }
    for mname, (stem, alpha_src, masked) in plan.items():
        mat = mats.get(mname)
        if mat is None:
            continue
        img = find_image(mat, 'Hair__' if mname == 'Karin_Hair_Transparent' else None)
        arr = image_pixels(img).copy()
        if alpha_src:
            aimg = find_image(mat, alpha_src)
            aarr = image_pixels(aimg)
            arr[:, :, 3] = aarr[:, :, 0]
        arr[:, :, :3] *= CFG['albedo_scale']
        new = new_image(stem, arr)
        if new.size[0] > size:
            new.scale(size, size)
        new.filepath_raw = os.path.join(pngdir, stem + '.png')
        new.file_format = 'PNG'
        new.save()
        group = 'CharacterDiffuseWithAlpha' if masked else 'CharacterDiffuse'
        xbm = os.path.join(texdir, stem + '.xbm')
        exm.export_xbm(new, xbm, texture_group=group)
        out[mname] = (os.path.join(CFG['tex_depot_dir'], stem + '.xbm'), masked)
        REPORT.setdefault('textures', {})[mname] = {'xbm': xbm, 'size': list(new.size), 'group': group,
                                                    'alpha_mean': float(arr[:, :, 3].mean())}
    return out


def material_dicts(tex):
    dicts = {}
    for mname, (path, masked) in tex.items():
        props = [
            {'name': 'Diffuse', 'type': 'TEX_IMAGE', 'value': path},
            {'name': 'SpecularColor', 'type': 'RGB', 'value': '{0} ; {0} ; {0} ; 1.0'.format(CFG['spec_rgb'])},  # 0..1, builder scales to 255
            {'name': 'RSpecBase', 'type': 'VALUE', 'value': 0.6},
            {'name': 'RSpecScale', 'type': 'VALUE', 'value': 0.0},
        ]
        dicts[mname] = {'name': mname, 'witcher_props': {'name': mname, 'enableMask': masked, 'local': True,
                                                        'base_custom': r'engine\materials\graphs\pbr_std.w2mg',
                                                        'input_props': props}}
    return dicts


# ----------------------------------------------------------------------------- physics (dyng)
RZ90 = Matrix.Rotation(math.radians(90), 4, 'Z')
# W3 world matrix = Blender bone.matrix_local @ RZ90 (addon rig import with rot90 compensation ON)

DYNG_GROUPS = [
    # anchor_depth: nodes with depth <= anchor_depth (root = 0) stay pinned to the animation.
    # dist(depth) = d0 + dstep * (depth - anchor_depth - 1): how far a node may leave its animated position
    # (this, not the stiffness, capped the swing in v0.1.0); mass interpolated root -> tip. Without gravity a twin
    # tail with a 0.42 m tip cap got stuck flared out after a sprint stop (0.21 m: half raised for ~7 s, likely caught
    # over the upper arm collision); 0.18 m returned to its shape.
    # stiff: pull back to the animated (modelled) shape. With the constraint's gravity off (Karin's VRM springs have
    # none) it is the only force holding the shape: 0.1-0.3 left chains floating wherever motion put them; vanilla
    # shape-keeping hair uses 1-4 (Yennefer's curls 2.0), plain hanging hair 0 + gravity.
    # The stiffness target is dyng parent x local, so a simulated parent drags its child's target along: chained
    # parents with look-ats stayed flared out (stiffness 10), chained parents without look-ats settled in a twisted
    # shape (v0.4.0). Simulated nodes therefore hang directly from the chain's animated anchor (head, pelvis, ...),
    # like the vanilla shape-keeping braids (Filippa: braid nodes parented to torso3, look-ats along the braid);
    # links and look-at triangles still follow Karin's chain. lookat=False drops the triangles of a group.
    # collide_n / margin override dyng_collide_per_node / dyng_margin for the group; shape_links=n adds rigid links
    # from each node to the chain nodes 2..n levels up; nodes with depth <= snug_depth keep >= 98 % of their rest
    # distance from every collision proxy (they can only move away from the body).
    # Head chains: without shape links the twin tails and side hair rested twisted after running (v0.4.2, like the
    # tail before); the bangs and side hair hang 0.5-3 cm off the face, so they collide with head_c.
    dict(name='twintail', roots=['Hair_tail_L', 'Hair_tail_R'], anchor_depth=0, d0=0.03, dstep=0.03, mass=(1.0, 0.6), stiff=2.0,
         shape_links=3, collide=['back_hi', 'back_mid', 'back_lo', 'hips', 'l_arm_c', 'r_arm_c']),
    dict(name='side', roots=['Hair_side_L', 'Hair_side_R'], anchor_depth=0, d0=0.025, dstep=0.025, mass=(1.0, 0.7), stiff=2.0,
         shape_links=3, collide=['head_c']),
    dict(name='front', roots=['Hair_front_root'], anchor_depth=0, d0=0.02, dstep=0.02, mass=(1.0, 0.8), stiff=2.0,
         shape_links=3, collide=['head_c']),
    dict(name='ribbon_head', roots=['Ribbon_L', 'Ribbon_R'], anchor_depth=0, d0=0.035, dstep=0.035, mass=(0.8, 0.6), stiff=2.0,
         shape_links=3, collide=[]),
    # ears: root and middle pinned (a free middle let the tips sag at rest), only the tip node wobbles
    dict(name='ear', roots=['Ear_L', 'Ear_R'], anchor_depth=1, d0=0.015, dstep=0.01, mass=(0.6, 0.5), stiff=3.0, collide=[]),
    # tail: hangs from the pelvis, so its caps are absolute. Within its cap a node is barely pulled back: after a
    # sprint stop the tail stayed wherever it was thrown, folded at the root, with stiffness 0.7 or 1.4 (caps 0.05 +
    # 0.06/node), with dampening 0.985 (worse), and raised ~20 deg with stiffness 2 and caps 0.04 + 0.05/node.
    # Rigid shape links (shape_links) keep the modelled bend, so it can only swing as a whole about its root.
    dict(name='tail', roots=['Tail'], anchor_depth=0, d0=0.035, dstep=0.04, mass=(1.0, 0.6), stiff=2.0, shape_links=3,
         collide=['hips', 'l_thigh_c1', 'r_thigh_c1', 'l_thigh_c2', 'r_thigh_c2']),
    # skirt: waist ring and the first segment (above the hip joints) follow the body (a hanging sim there
    # collapses onto the hips); the hem segments swing and must have room to be pushed out by a raised thigh.
    # The hip-level ring (depth 3) could drift 2.4-4.1 cm inward to its proxies; the pinned segment above looks at
    # it and turned into the hips, which sit 1-1.5 cm under it: the side of the hips showed through when walking
    # (v0.4.3; scripts/checks/blender/skirt_walk_sink.py). snug_depth keeps that ring at its rest clearance.
    dict(name='skirt', roots=['Skirt_root'], anchor_depth=2, d0=0.06, dstep=0.09, mass=(0.6, 0.5), stiff=2.0, ring=True,
         collide=['hips', 'l_thigh_c0', 'l_thigh_c1', 'l_thigh_c2', 'l_knee_c', 'r_thigh_c0', 'r_thigh_c1', 'r_thigh_c2', 'r_knee_c'],
         collide_n=5, margin=0.03, snug_depth=3),
    dict(name='ribbon_misc', roots=['Ribbon_camisole', 'Ribbon_tops_L', 'Ribbon_tops_R', 'Ribbon_hand_L_root', 'Ribbon_hand_R_root'],
         anchor_depth=0, d0=0.025, dstep=0.025, mass=(0.6, 0.5), stiff=2.0, collide=[]),
]
DYNG_SKIP_W3 = ('Root', 'Trajectory', 'Reference')
HUMANOID_TO_W3 = {'Head': 'head', 'Neck': 'neck', 'Hips': 'pelvis', 'LeftHand': 'l_hand', 'RightHand': 'r_hand'}


def w3_world(tarm, name):
    return tarm.matrix_world @ tarm.data.bones[name].matrix_local @ RZ90


def frame_from_x(xdir, pos):
    x = Vector(xdir).normalized()
    ref = Vector((0, 1, 0)) if abs(x.dot(Vector((0, 1, 0)))) < 0.9 else Vector((0, 0, 1))
    z = x.cross(ref).normalized()
    y = z.cross(x).normalized()
    m = Matrix((x, y, z)).transposed().to_4x4()
    m.translation = pos
    return m


def build_dyng_spec(karm, tarm, M, S, Q, samples):
    """Returns (spec dict, {karin bone: W3 world matrix} for dyng bones)."""
    kb = karm.data.bones
    nodes = []          # dicts: name, parent, world, mass, stiff, dist
    index = {}

    def add(name, parent, world, mass=1.0, stiff=0.0, dist=0.0):
        index[name] = len(nodes)
        nodes.append({'name': name, 'parent': parent, 'world': world, 'mass': mass, 'stiffness': stiff, 'distance': dist})

    # 1) anchors: man_base skeleton (hierarchy order)
    # man_base bones except the root helpers (like the vanilla Ves body dyng: top node pelvis, parent 'Root').
    # The same helpers are removed from the export armature so every mesh bone exists in the dyng skeleton.
    for b in tarm.data.bones:
        if b.name in DYNG_SKIP_W3 or b.name.startswith('IK_'):
            continue
        add(b.name, b.parent.name if b.parent else 'Root', w3_world(tarm, b.name))

    # 2) Karin chains
    def w3_parent_of(kname):
        hp = nearest_humanoid(kb, kname, HUMANOID)
        if hp in HUMANOID_TO_W3:
            return HUMANOID_TO_W3[hp]
        if hp in ('Hips', 'Spine', 'Chest'):
            z = (M[kname] @ S(kname)).z
            return min(('torso', 'torso2', 'torso3'), key=lambda n: abs(Q(n).z - z))
        raise KeyError(kname)

    fitted = {}
    groups_nodes = {}
    for g in DYNG_GROUPS:
        lst = []
        for root in g['roots']:
            if root not in kb:
                continue
            # BFS with depth
            stack = [(kb[root], 0)]
            order = []
            while stack:
                b, dep = stack.pop(0)
                order.append((b, dep))
                stack.extend((c, dep + 1) for c in b.children)
            maxdep = max(dep for _, dep in order)
            anchor = w3_parent_of(root)
            for b, dep in order:
                pos = M[b.name] @ S(b.name)
                kids = [c for c in b.children]
                if kids:
                    xdir = (M[kids[0].name] @ S(kids[0].name)) - pos
                else:
                    xdir = pos - (M[b.parent.name] @ S(b.parent.name))
                if xdir.length < 1e-6:
                    xdir = Vector((0, 0, -1))
                pinned = dep <= g['anchor_depth']
                dparent = b.parent.name if pinned and dep > 0 else anchor
                world = None
                if g.get('lookat', True) and len(kids) == 1:
                    # look-at node: the game aims X at the child and keeps Z as close as it can to the dyng parent's Z
                    # (sign kept). A bind frame with another roll is rolled at rest: frames from frame_from_x sat
                    # ~175 deg off on the twin tails / side hair / head ribbons (curls turned outward, side hair
                    # sticking out behind the head); offline renders with that roll matched the game.
                    x = xdir.normalized()
                    pz = nodes[index[dparent]]['world'].to_3x3().col[2]
                    z = pz - x * pz.dot(x)
                    if z.length > 0.1:
                        z.normalize()
                        world = Matrix((x, z.cross(x), z)).transposed().to_4x4()
                        world.translation = pos
                if world is None and dep == 0:
                    world = frame_from_x(xdir, pos)
                elif world is None:
                    # parallel transport: the parent frame swung onto xdir, no twist about the bone (frame_from_x
                    # flipped the tail 180 deg twice and the game rendered a pinched S-shaped tail)
                    pr = fitted[b.parent.name].to_3x3()
                    world = (min_rot(pr.col[0], xdir) @ pr).to_4x4()
                    world.translation = pos
                fitted[b.name] = world
                if pinned:
                    add(b.name, dparent, world, mass=g['mass'][0], stiff=0.0, dist=0.0)
                else:
                    f = (dep - g['anchor_depth'] - 1) / max(1, maxdep - g['anchor_depth'] - 1)
                    mass = g['mass'][0] + (g['mass'][1] - g['mass'][0]) * f
                    dist = g['d0'] + g['dstep'] * (dep - g['anchor_depth'] - 1)
                    add(b.name, dparent, world, mass=mass, stiff=g['stiff'], dist=dist)
                lst.append((b.name, dep))
        groups_nodes[g['name']] = lst

    # 3) collision proxies (anchors) with radii measured on the fitted body
    import statistics
    body = [(p, bone) for p, bone, oname in samples if oname not in ('hair', 'skirt', 'tail', 'kemomimi', 'Body')]

    def radius_around(center, axis, bones, band=0.05, pct=0.9):
        ds = []
        for p, bone in body:
            if bone not in bones:
                continue
            d = p - center
            if axis is not None:
                along = d.dot(axis)
                if abs(along) > band:
                    continue
                d = d - axis * along
            ds.append(d.length)
        if not ds:
            return 0.0
        ds.sort()
        return ds[min(len(ds) - 1, int(len(ds) * pct))]

    proxies = {}
    for side, p in SIDES:
        thigh_bones = {p + 'thigh', p + 'legRoll', p + 'legRoll2', p + 'kneeRoll'}
        a, b = Q(p + 'thigh'), Q(p + 'shin')
        ax = (b - a).normalized()
        for key, t in (('c0', 0.12), ('c1', 0.3), ('c2', 0.65)):
            c = a + (b - a) * t
            proxies[p + 'thigh_' + key] = (p + 'thigh', c, radius_around(c, ax, thigh_bones))
        c = Q(p + 'shin')
        proxies[p + 'knee_c'] = (p + 'shin', c, radius_around(c, ax, thigh_bones | {p + 'shin'}))
        a, b = ARM_ROOT_BIND.get(p, Q(p + 'bicep')), Q(p + 'forearm')
        ax = (b - a).normalized()
        c = a + (b - a) * 0.35
        proxies[p + 'arm_c'] = (p + 'bicep', c, radius_around(c, ax, {p + 'bicep', p + 'bicep2', p + 'shoulderRoll'}))
    up = Vector((0, 0, 1))
    spine_bones = {'pelvis', 'torso', 'torso2', 'torso3'}
    hz = (Q('l_thigh').z + Q('r_thigh').z) / 2 - 0.03
    c = Vector((0, Q('pelvis').y, hz))
    proxies['hips'] = ('pelvis', c, radius_around(c, up, spine_bones | {'l_legRoll', 'r_legRoll', 'l_legRoll2', 'r_legRoll2'}, pct=0.9))
    for key, bn in (('back_lo', 'torso'), ('back_mid', 'torso2'), ('back_hi', 'torso3')):
        c = Q(bn)
        proxies[key] = (bn, c, radius_around(c, up, spine_bones, pct=0.6))
    # head: the centre (head bone space, X up, Y forward) where (hair - centre) best matches the face normal under the
    # bangs and side hair (mean 14 deg; scripts/checks/blender/face_geom.py). The radius reaches the farthest face vertex, so
    # each hair node keeps >= 98 % of its rest distance from the centre and cannot swing into the face.
    c = w3_world(tarm, 'head') @ Vector(CFG['dyng_head_centre'])
    proxies['head_c'] = ('head', c, max((p - c).length for p, bone, oname in samples if oname == 'Body'))
    for name, (par, c, r) in proxies.items():
        world = Matrix.Translation(c)
        add(name, par, world)
        nodes[index[name]]['radius'] = r

    # 4) links, triangles
    links = []
    tris = []
    for g in DYNG_GROUPS:
        lst = groups_nodes[g['name']]
        names = set(n for n, _ in lst)
        for n, dep in lst:
            b = kb[n]
            if dep == 0:
                continue
            pa = b.parent.name
            if nodes[index[n]]['distance'] > 0 or nodes[index[pa]]['distance'] > 0:
                L = (nodes[index[n]]['world'].translation - nodes[index[pa]]['world'].translation).length
                links.append((0, L, index[pa], index[n]))
            # shape links: rigid links at the bind distance to the chain node 2..shape_links levels up (vanilla
            # skip links, length = bind distance), so the chain cannot fold
            up = b.parent
            for _ in range(2, g.get('shape_links', 0) + 1):
                up = up.parent if up is not None and up.name in names else None
                if up is None or up.name not in names:
                    break
                L = (nodes[index[n]]['world'].translation - nodes[index[up.name]]['world'].translation).length
                links.append((0, L, index[up.name], index[n]))
            # orientation (look-at) only along single-child chains, like the vanilla hair: a fork root
            # (Skirt_root, Hair_front_root, Ribbon_hand_*_root) aiming at one child twists everything on it
            if g.get('lookat', True) and sum(1 for c in kb[pa].children if c.name in names) == 1:
                tris.append((index[pa], index[n], -1))
        # rings: neighbouring chains at the same depth (skirt)
        if g.get('ring'):
            by_dep = {}
            for n, dep in lst:
                if nodes[index[n]]['distance'] > 0:
                    by_dep.setdefault(dep, []).append(n)
            for dep, ns in by_dep.items():
                ns.sort(key=lambda n: math.atan2(nodes[index[n]]['world'].translation.y - Q('pelvis').y, nodes[index[n]]['world'].translation.x))
                for a_, b_ in zip(ns, ns[1:] + ns[:1]):
                    L = (nodes[index[a_]]['world'].translation - nodes[index[b_]]['world'].translation).length
                    links.append((2, L * 1.15, index[a_], index[b_]))
        # collision spheres: type 1 (keep at least `length`) from the nearest proxy anchors to each simulated node
        cands = [pr for pr in g['collide'] if pr in proxies]
        for n, dep in lst:
            if nodes[index[n]]['distance'] <= 0 or not cands:
                continue
            pn = nodes[index[n]]['world'].translation
            near = sorted(cands, key=lambda pr: (pn - nodes[index[pr]]['world'].translation).length - nodes[index[pr]]['radius'])
            for pr in near[:g.get('collide_n', CFG['dyng_collide_per_node'])]:
                pc = nodes[index[pr]]['world'].translation
                rest = (pn - pc).length
                r = rest if dep <= g.get('snug_depth', -1) else nodes[index[pr]]['radius'] + g.get('margin', CFG['dyng_margin'])
                links.append((1, min(r, rest * 0.98), index[pr], index[n]))

    # 5) locals
    out_nodes = []
    for nd in nodes:
        pw = nodes[index[nd['parent']]]['world'] if nd['parent'] in index else Matrix.Identity(4)
        loc = pw.inverted() @ nd['world']
        q = loc.to_quaternion()
        out_nodes.append({'name': nd['name'], 'parent': nd['parent'], 'parent_index': index.get(nd['parent'], -1),
                          'mass': nd['mass'], 'stiffness': nd['stiffness'], 'distance': nd['distance'],
                          'local': [list(loc.col[0][:3]), list(loc.col[1][:3]), list(loc.col[2][:3]), list(loc.translation)],
                          'pos': list(loc.translation), 'rot': [q.x, q.y, q.z, q.w], 'radius': nd.get('radius', 0.0)})
    spec = {'nodes': out_nodes, 'links': [{'type': t, 'length': L, 'a': a, 'b': b} for t, L, a, b in links],
            'triangles': [list(t) for t in tris], 'proxies': {k: [v[0], list(v[1]), v[2]] for k, v in proxies.items()}}
    REPORT['dyng'] = {'nodes': len(out_nodes), 'links': len(links), 'triangles': len(tris),
                      'sim_nodes': sum(1 for n in out_nodes if n['distance'] > 0),
                      'proxy_radii': {k: round(v[2], 4) for k, v in proxies.items()}}
    return spec, fitted


def add_dyng_bones(tarm, fitted, names):
    """Add Karin dyng bones (W3 world matrices) to the export armature and drop the root helper bones
    that are not part of the dyng skeleton."""
    bpy.context.view_layer.objects.active = tarm
    with bpy.context.temp_override(active_object=tarm, object=tarm, selected_objects=[tarm]):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = tarm.data.edit_bones
        for b in list(eb):
            if b.name in DYNG_SKIP_W3 or b.name.startswith('IK_'):
                eb.remove(b)
        inv = tarm.matrix_world.inverted()
        for n in names:
            b = eb.new(n)
            b.head = (0, 0, 0)
            b.tail = (0, 0.02, 0)
            b.matrix = inv @ fitted[n] @ RZ90.inverted()
        bpy.ops.object.mode_set(mode='OBJECT')
    # verify
    worst = 0.0
    for n in names:
        w = w3_world(tarm, n)
        d = (w - fitted[n])
        worst = max(worst, max(abs(d[i][j]) for i in range(4) for j in range(4)))
    REPORT['dyng_bone_matrix_err'] = worst



# ----------------------------------------------------------------------------- face (mimic)
FACE_ANCHORS = ('torso3', 'l_shoulder', 'r_shoulder', 'neck', 'head', 'hroll')


def mimic_tracks():
    d = json.load(open(CFG['w3fac_template'], encoding='utf-8'))
    tr = d['_chunks']['CSkeleton #2']['_vars']['tracks']['_elements']
    return [e['_vars']['nameAsCName']['_value'] for e in tr]


def build_face(face_obj, cap, tarm, tex):
    """Karin's face shape keys -> W3 mimic rig: face bones, weights, per-pose translations (karin_face.solve)."""
    import numpy as np
    import karin_face
    import face_pose_map
    tracks = mimic_tracks()[:CFG['face_poses']]
    P = cap['pos']
    targets = []
    for name in tracks:
        t = np.zeros_like(P)
        for key, w, side in face_pose_map.POSE_MAP.get(name, []):
            if key not in cap['keys']:
                raise KeyError(f'face shape key {key} missing')
            t += w * karin_face.side_mask(P, side, CFG['face_side_width'])[:, None] * cap['keys'][key]
        targets.append((name, t))
    np.savez_compressed(CFG['face_spec'].replace('.json', '_targets.npz'), P=P, names=np.array([n for n, _ in targets]),
                        T=np.stack([t for _, t in targets]))
    res = karin_face.solve(P, targets, n_bones=CFG['face_bones'], act_thr=CFG['face_act_thr'],
                           k_near=CFG['face_k_near'], sigma_scale=CFG['face_sigma'], lam=CFG['face_lambda'],
                           sig_gain=CFG['face_sig_gain'], smooth=CFG['face_smooth'], rounds=CFG['face_rounds'])
    REPORT['face'] = {'bones': len(res['bones']), 'spacing': res['spacing'], 'active': res['n_active'],
                      'region': res['n_region'], 'history': res.get('history'),
                      'errors': [(n, round(e, 3), round(m, 4)) for n, e, m in res['errors'] if m > 0]}
    names = ['kf_%02d' % i for i in range(len(res['bones']))]
    Hw = w3_world(tarm, 'head')
    Rh = Hw.to_3x3()
    hp = Hw.translation
    # face rig armature: mimic anchors + placer/bone pairs (W3 world = head rotation at the bone position)
    fa = tarm.copy()
    fa.data = tarm.data.copy()
    fa.name = 'karin_face_rig'
    bpy.context.scene.collection.objects.link(fa)
    bpy.context.view_layer.objects.active = fa
    with bpy.context.temp_override(active_object=fa, object=fa, selected_objects=[fa]):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = fa.data.edit_bones
        for b in list(eb):
            if b.name not in FACE_ANCHORS:
                eb.remove(b)
        inv = fa.matrix_world.inverted()
        for n, c in zip(names, res['bones']):
            W3 = Rh.to_4x4()
            W3.translation = Vector(tuple(c))
            for bn, par in (('placer_' + n, 'head'), (n, 'placer_' + n)):
                b = eb.new(bn)
                b.head = (0, 0, 0)
                b.tail = (0, 0.01, 0)
                b.matrix = inv @ W3 @ RZ90.inverted()
                b.parent = eb[par]
        bpy.ops.object.mode_set(mode='OBJECT')
    # weights: (1 - activity) x original head/neck weights + face bone kernel weights
    W = res['weights']
    a = res['activity']
    for g in list(face_obj.vertex_groups):
        face_obj.vertex_groups.remove(g)
    groups = {}
    for v, base in enumerate(cap['base_weights']):
        d = {}
        for n, w in base:
            n = n if n in FACE_ANCHORS else 'head'
            d[n] = d.get(n, 0.0) + w * (1.0 - a[v])
        for j in np.nonzero(W[v] > 1e-5)[0]:
            d[names[j]] = d.get(names[j], 0.0) + float(W[v, j])
        top = sorted(d.items(), key=lambda x: -x[1])[:4]
        ssum = sum(x for _, x in top)
        for n, x in top:
            if x / ssum < 1e-4:
                continue
            if n not in groups:
                groups[n] = face_obj.vertex_groups.new(name=n)
            groups[n].add([v], x / ssum, 'REPLACE')
    for m in list(face_obj.modifiers):
        face_obj.modifiers.remove(m)
    face_obj.parent = fa
    face_obj.modifiers.new('Armature', 'ARMATURE').object = fa
    face_obj.name = 'karin_face_lod0'
    ms = face_obj.witcherui_MeshSettings
    ms.item_repo_path = CFG['face_mesh_depot']
    ms.isTwoSided = True
    ms.autohideDistance = 120.0
    # w3fac spec: placer locals in head space, pose translations in placer (= head) space
    RhT = Rh.transposed()
    spec = {'anchors': list(FACE_ANCHORS),
            'bones': [{'name': n, 'local': list(RhT @ (Vector(tuple(c)) - hp))} for n, c in zip(names, res['bones'])],
            'poses': [[list(RhT @ Vector(tuple(t))) for t in tr] for tr in res['trans']],
            'pose_names': tracks}
    json.dump(spec, open(CFG['face_spec'], 'w'), indent=1)
    return face_obj, fa

# ----------------------------------------------------------------------------- main
def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    setup_addon()
    tarm = import_target_rig()
    G = idle_pose(tarm)
    karm, meshes = import_karin()
    log('karin meshes', [m.name for m in meshes])
    M, S, Q, N = build_fit(karm, tarm, G)
    log('fit', json.dumps(REPORT['fit'], default=str))
    retarget = make_retarget(Q)
    mats = {m.name: m for m in bpy.data.materials}
    tex = prep_textures(mats) if CFG['stage'] in ('all', 'tex') else {}
    REPORT['meshes'] = {}
    keep = set()
    if CFG['physics']:
        kb = karm.data.bones
        for g in DYNG_GROUPS:
            for root in g['roots']:
                if root in kb:
                    stack = [kb[root]]
                    while stack:
                        b = stack.pop()
                        keep.add(b.name)
                        stack.extend(b.children)
    samples = []
    face_obj, face_cap, face_keys = None, None, None
    if CFG['face']:
        import face_pose_map
        face_keys = face_pose_map.needed_keys()
    for o in meshes:
        cap_keys = face_keys if (CFG['face'] and o.name == 'Body') else None
        r = process_mesh(o, karm, M, retarget, keep=keep, samples=samples, capture_keys=cap_keys, G=G, N=N)
        if cap_keys is not None:
            face_obj, face_cap = o, r.pop('capture')
        else:
            r.pop('capture', None)
        if o.name == 'skirt':
            r['thigh_follow_verts'] = skirt_follow_thighs(o, Q)
        REPORT['meshes'][o.name] = r
        log('processed', o.name, r['verts'])
    if CFG['physics']:
        spec, fitted = build_dyng_spec(karm, tarm, M, S, Q, samples)
        json.dump(spec, open(CFG['dyng_spec'], 'w'), indent=1)
        log('dyng', json.dumps(REPORT['dyng']))
    # join
    for o in bpy.data.objects:
        o.select_set(False)
    main_obj = [o for o in meshes if o.name == 'body_2'][0]
    body_parts = [o for o in meshes if o is not face_obj]
    with bpy.context.temp_override(active_object=main_obj, selected_editable_objects=body_parts, object=main_obj):
        bpy.ops.object.join()
    obj = main_obj
    obj.name = 'karin_body_lod0'
    obj.data.name = 'karin_body_lod0'
    # remove Karin armature + empties
    for o in list(bpy.data.objects):
        if o not in (obj, tarm, face_obj):
            bpy.data.objects.remove(o, do_unlink=True)
    if CFG['physics']:
        weighted = sorted(g.name for g in obj.vertex_groups if g.name in keep)
        add_dyng_bones(tarm, fitted, weighted)
        REPORT['dyng']['mesh_dyng_bones'] = len(weighted)
        REPORT['dyng']['mesh_total_bones'] = len(tarm.data.bones)
    obj.parent = tarm
    mod = obj.modifiers.new('Armature', 'ARMATURE')
    mod.object = tarm
    ms = obj.witcherui_MeshSettings
    ms.item_repo_path = CFG['mesh_depot']
    ms.isTwoSided = True
    ms.autohideDistance = 120.0
    REPORT['final'] = {'verts': len(obj.data.vertices), 'tris': sum(len(p.vertices) - 2 for p in obj.data.polygons),
                       'materials': [m.name for m in obj.data.materials], 'groups': [g.name for g in obj.vertex_groups]}
    os.makedirs(os.path.dirname(CFG['blend_out']), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=CFG['blend_out'])
    face_arm = None
    if face_obj is not None:
        face_obj, face_arm = build_face(face_obj, face_cap, tarm, tex)
        log('face', json.dumps({k: v for k, v in REPORT['face'].items() if k != 'errors'}))
    bpy.ops.wm.save_as_mainfile(filepath=CFG['blend_out'])
    if CFG['stage'] == 'all':
        export(obj, tarm, tex)
        if face_obj is not None:
            export(face_obj, face_arm, tex, path_key='face_mesh_depot', rot90=True)
    json.dump(REPORT, open(CFG['report'], 'w'), indent=1, default=str)
    log('DONE')


def export(obj, tarm, tex, path_key='mesh_depot', rot90=None):
    em = importlib.import_module(MOD + '.exporters.export_mesh')
    dicts = material_dicts(tex)

    def patched(mesh_bl, mesh_obj=None, material_slot_indices=None):
        out = []
        slots = list(material_slot_indices or [])
        for idx, mat in enumerate(mesh_bl.materials):
            if not mat:
                continue
            d = json.loads(json.dumps(dicts[mat.name]))
            if idx < len(slots):
                d['material_slot_index'] = int(slots[idx])
            out.append(d)
        return out

    em.get_mesh_material_info = patched
    path = os.path.join(CFG['depot_out'], CFG[path_key])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    em.do_export_mesh(bpy.context, path, armature=tarm, meshes=[obj], col_tri_meshes=[], export_col_tri=False,
                      keep_intermediate_json=False, use_native_writer=True, strip_material_names=False,
                      tangent_space_mode='MIKKTSPACE', tangent_handedness_mode='AUTO', rotate_bones_90=rot90)
    REPORT.setdefault('export', {})[path_key] = {'path': path, 'size': os.path.getsize(path)}
    log('exported', path, os.path.getsize(path))


main()
