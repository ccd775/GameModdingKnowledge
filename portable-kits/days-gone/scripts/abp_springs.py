"""Add per-bone AnimDynamics "spring bone" nodes to a cooked AnimBlueprint (game format, Deacon_VimBlueprint).

Why per bone (UE 4.11 AnimNode_AnimDynamics.cpp / AnimPhysicsSolver.cpp):
- the linear spring pulls a body's CoM towards its own joint (rest length 0, force through the pivot): no restoring
  torque, a chain under gravity just droops (t20 fox tail);
- the Cone limit only constrains the body's X axis; KO_* bones point along -Y, so the swing about X is free (t20 twin
  tails = pendulums);
- in a chain the angular spring target and the Angular limit frame of the 2nd+ bodies are component space / the parent
  body frame with identity rest offset, so a curved chain is pulled straight.
A single-body node instead nails its body to the animated joint and uses the animated bone rotation as the frame of both
the Angular limit and the angular spring target. Nodes run root to tip; each one writes its bone, so the next node's
animated joint already follows the simulated parent. Gravity 0 (VRM spring bones have gravityPower 0): the shape is
held by the angular spring (k = I_pivot * omega^2, box mass 1), damping = 1 - exp(-lambda) on linear and angular
momentum (absolute drag, like VRM dragForce; lambda <= ~13 because the solver computes (1 - d)^dt in float).
Planar limits keep CoMs out of the head, torso and thighs: "radial" planes (normal = horizontal direction from a
vertical axis to the rest CoM, at the CoM minus a margin) and "thigh" planes (normal = from the thigh axis UpLeg->Leg to
the rest CoM, at min(radius, rest distance - margin) from the axis), both in the driving bone's frame.

Graph surgery (UE 4.11 AnimNodeBase.cpp / AnimBlueprintGeneratedClass.cpp / AnimInstanceProxy.cpp): AnimNodeProperties
is the class field chain (Children -> Next) filtered to anim node structs; FPoseLink::LinkID indexes it directly, while
RootAnimNodeIndex, the baked state machine indices and the node indices compiled into the ubergraph
(GetInstanceAssetPlayerTime, GetRelevantAnimTime, ...) count from the end (Num - 1 - i). t21 appended the new nodes at the
chain tail: every reverse index moved by M, state machines pointed at other nodes and the graph recursed until the stack
overflowed (load crash; dump: one return address 80000x on a 10 MB stack). Now the new StructProperty exports go to the
chain head (class Children), every old pose LinkID gets +M and all reverse indices stay valid untouched. The new chain is
spliced in front of an existing node: new[0] takes its old input, it takes new[M-1]. CDO tags are copied from a template
node (no exposed inputs), planar limit elements from another node. Bone names go in as UE FNames (KO_Skirt_0 = KO_Skirt #1).

cfg "drivers" (optional) adds AnimNode_BoneDrivenController nodes in front of the spring nodes (Karin's eyelid bones,
Scripts/blink_rig.py): each maps a source bone's local translation/rotation change from its ref pose through
clamp((v - range[0]) / (range[1] - range[0])) * multiplier and adds it to one translation axis of the target bone (its
parent's space). The graph has no such node to clone: the property export clones a node property with its Struct set to a
new ScriptStruct import, the CDO tag is written from scratch (only non-default members; the stock 4.11 member set, which
the game exe carries: bAffectTargetTranslationX, RemappedMin, EDrivenBoneModificationMode). In game these nodes had no
effect at all (t28b-e: a constant 15 cm Head lift did nothing), so the blink uses "copies" instead.

cfg "copies" (optional) adds AnimNode_CopyBone nodes in front of everything else, cloned from the graph's own CopyBone
node (RightHandProp -> ref04): source, target, ControlSpace (BCS_ParentBoneSpace copies the local transform numbers) and
the translation / rotation / scale switches.

usage: abp_springs.py <in AnimBP.uasset> <mesh.uasset> <cfg.json> <out.uasset> [report.json]
"""
import argparse, hashlib, json, math, re, struct, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg, refskel

def chain_bones(rs, root):
    N, P = rs['names'], rs['parents']
    i = N.index(root); out = []
    while True:
        kids = [j for j, p in enumerate(P) if p == i]
        if not kids: break
        assert len(kids) == 1, (N[i], [N[k] for k in kids])
        out.append((i, kids[0])); i = kids[0]
    return out          # (bone, child) pairs; the leaf is only a length marker

def quat_from_matrix(R):
    t = np.trace(R)
    if t > 0:
        s = math.sqrt(t + 1.0) * 2; w = 0.25 * s
        x = (R[2, 1] - R[1, 2]) / s; y = (R[0, 2] - R[2, 0]) / s; z = (R[1, 0] - R[0, 1]) / s
    elif R[0, 0] > R[1, 1] and R[0, 0] > R[2, 2]:
        s = math.sqrt(1.0 + R[0, 0] - R[1, 1] - R[2, 2]) * 2
        w = (R[2, 1] - R[1, 2]) / s; x = 0.25 * s; y = (R[0, 1] + R[1, 0]) / s; z = (R[0, 2] + R[2, 0]) / s
    elif R[1, 1] > R[2, 2]:
        s = math.sqrt(1.0 + R[1, 1] - R[0, 0] - R[2, 2]) * 2
        w = (R[0, 2] - R[2, 0]) / s; x = (R[0, 1] + R[1, 0]) / s; y = 0.25 * s; z = (R[1, 2] + R[2, 1]) / s
    else:
        s = math.sqrt(1.0 + R[2, 2] - R[0, 0] - R[1, 1]) * 2
        w = (R[1, 0] - R[0, 1]) / s; x = (R[0, 2] + R[2, 0]) / s; y = (R[1, 2] + R[2, 1]) / s; z = 0.25 * s
    return [x, y, z, w]

def frame_z(n):
    """rotation matrix whose Z column is n"""
    n = n / np.linalg.norm(n)
    a = np.array([1.0, 0, 0]) if abs(n[0]) < 0.9 else np.array([0, 1.0, 0])
    x = np.cross(a, n); x /= np.linalg.norm(x); y = np.cross(n, x)
    return np.stack([x, y, n], axis=1)

def plane(rs, spec, com, side, dir_com=None):
    """-> (driving bone, quat xyzw, translation) in the driving bone's frame, rest clearance, normal (cs).
    Thigh planes: dir_com (a neighbouring plate's CoM) sets the normal, the offset still comes from this CoM's
    projection; None when that plane would sit less than min_off from the thigh axis."""
    N, C = rs['names'], rs['component']
    lower = {n.lower(): i for i, n in enumerate(N)}
    kind = spec['kind']
    if kind == 'radial':
        b = lower[spec['bone'].lower()]
        c = np.array([spec['center'][0], spec['center'][1], com[2]])
        n = com - c; n[2] = 0; dist = np.linalg.norm(n); n /= dist
        off = dist - spec['margin']; p = c + n * off
    elif kind == 'thigh':
        up, leg = spec['up'].replace('#', side), spec['leg'].replace('#', side)
        b = lower[up.lower()]
        a0, a1 = C[b][:3, 3], C[lower[leg.lower()]][:3, 3]
        u = (a1 - a0) / np.linalg.norm(a1 - a0)
        foot = a0 + u * np.dot(com - a0, u)
        dp = (com if dir_com is None else dir_com) - a0
        n = dp - u * np.dot(dp, u); n /= np.linalg.norm(n)
        dist = float(np.dot(com - foot, n))
        off = min(spec['radius'], dist - spec['margin'])
        if off < spec.get('min_off', 2.0):
            return None
        p = foot + n * off
    else:
        raise ValueError(kind)
    R, t = C[b][:3, :3], C[b][:3, 3]
    n_loc = R.T @ n; p_loc = R.T @ (p - t)
    return N[b], quat_from_matrix(frame_z(n_loc)), p_loc.tolist(), float(dist - off), n

def node_specs(rs, cfg):
    N, C = rs['names'], rs['component']
    specs = []
    for g in cfg['groups']:
        for root in g['chains']:
            side = 'Left' if root.endswith('_L') or '_L_' in root else 'Right' if root.endswith('_R') or '_R_' in root else None
            for k, (i, j) in enumerate(chain_bones(rs, root)):
                L = float(np.linalg.norm(C[j][:3, 3] - C[i][:3, 3]))
                com_f = g.get('com', 0.5)
                d = com_f * L
                w = g.get('width', 2.0)
                box = [w, L, g.get('thick', w)]
                I = (L * L + box[2] ** 2) / 12 + d * d          # about the bone's X axis through the joint
                om = g['omega'][min(k, len(g['omega']) - 1)] if isinstance(g['omega'], list) else g['omega']
                lim = g['limit'][min(k, len(g['limit']) - 1)]
                axis_dir = (C[j][:3, 3] - C[i][:3, 3]) / L
                com = C[i][:3, 3] + axis_dir * d
                planes = []
                for ps in (g.get('planes', []) if cfg.get('planes', True) else []):
                    if k < ps.get('from_segment', 0): continue
                    sides = [side] if side else ['Left', 'Right']
                    if ps['kind'] == 'radial':
                        if 'max_z' in ps and com[2] > ps['max_z']: continue
                        if 'min_z' in ps and com[2] < ps['min_z']: continue
                        sides = [None]
                    # "neighbors": also the normals of the adjacent plates in g['ring'] (same segment), so a thigh
                    # pushing one plate pushes its neighbours too and no gap opens between them (t24: side-rear)
                    dirs = [None]
                    if ps['kind'] == 'thigh' and ps.get('neighbors') and root in g.get('ring', []):
                        ring = g['ring']; r = ring.index(root)
                        nbs = [ring[r - 1], ring[(r + 1) % len(ring)]]
                        if not g.get('ring_closed', True):   # open arc: the ends have one neighbour
                            nbs = [ring[x] for x in (r - 1, r + 1) if 0 <= x < len(ring)]
                        for nb in nbs:
                            ni, nj = chain_bones(rs, nb)[k]
                            dirs.append(C[ni][:3, 3] + (C[nj][:3, 3] - C[ni][:3, 3]) * com_f)
                    for sd in sides:
                        for dc in dirs:
                            res = plane(rs, ps, com, sd, dc)
                            if res is None: continue
                            db, q, t, clear, n = res
                            planes.append({'bone': db, 'quat': q, 'pos': t, 'clear': round(clear, 2), 'normal': np.round(n, 2).tolist()})
                lam = g['drag']
                specs.append({'bone': N[i], 'len': round(L, 2), 'box': box, 'offset': [0.0, d, 0.0], 'k': I * om * om,
                              'damping': 1.0 - math.exp(-lam), 'limit': lim, 'gravity': g.get('gravity', 0.0),
                              'planes': planes, 'com': np.round(com, 1).tolist()})
    return specs

def sub(p, *path):
    for n in path:
        p = {c.name: c for c in p.children}[n]
    return p

def fname(pkg, s):
    """FName bytes as UE stores them: a trailing _<number> without leading zeros is the instance number
    (bone KO_Skirt_0 = name 'KO_Skirt' number 1, KO_Ribbon_hand_L_1 = 'KO_Ribbon_hand_L' 2; KO_Skirt_0_001 stays whole)"""
    m = re.match(r'^(.+)_(0|[1-9][0-9]{0,8})$', s)
    if m:
        return struct.pack('<ii', pkg.name_index(m.group(1)), int(m.group(2)) + 1)
    return struct.pack('<ii', pkg.name_index(s), 0)

def pose_links(prop):
    """LinkID value offsets of every FPoseLink / FComponentSpacePoseLink inside a parsed node tag, including the
    elements of pose link arrays (BlendPose / BlendPoses: 880 of the 2480 links; t22 missed them -> A-pose)"""
    for ch in prop.children or []:
        if ch.type == 'IntProperty' and ch.name == 'LinkID':
            yield ch.vstart
        elif ch.type == 'StructProperty' and ch.children:
            yield from pose_links(ch)
        elif ch.type == 'ArrayProperty' and ch.children:
            for el in ch.children:
                if isinstance(el, list):
                    yield from pose_links(type('E', (), {'children': el}))

def anim_chain(pkg, head):
    """export indices of the class field chain from head (Next at data offset 12) and the anim node names in it"""
    fields, order, i = [], [], head
    while i >= 0:
        fields.append(i)
        e = pkg.exports[i]
        if pkg.ref(e['Class']).endswith('StructProperty'):
            sn = pkg.obj_path(struct.unpack_from('<i', pkg.export_data(i), 36)[0]).split('.')[-1]
            if 'AnimNode_' in sn or 'AnimationNode_' in sn:
                order.append(pkg.name(e['Name']))
        i = struct.unpack_from('<i', pkg.export_data(i), 12)[0] - 1
    return fields, order

def driver_blob(nm, name, drv, link):
    """CDO tag of one AnimNode_BoneDrivenController (Bend version 500 tags: no property guid byte)"""
    def tag(n, typ, val, extra=b''):
        return nm(n) + nm(typ) + struct.pack('<ii', len(val), 0) + extra + val
    def ftag(n, v): return tag(n, 'FloatProperty', struct.pack('<f', float(v)))
    def btag(n, v): return nm(n) + nm('BoolProperty') + struct.pack('<ii', 0, 0) + bytes([1 if v else 0])
    def stag(n, sname, inner): return tag(n, 'StructProperty', inner + nm('None'), nm(sname) + bytes(16))
    def bone(n, b): return stag(n, 'BoneReference', tag('BoneName', 'NameProperty', nm(b)))
    r0, r1 = drv['range']
    remap = drv.get('remap', [0, 1])
    inner = (stag('ComponentPose', 'ComponentSpacePoseLink', tag('LinkID', 'IntProperty', struct.pack('<i', link)))
             + ftag('Alpha', 1.0)
             + bone('SourceBone', drv['source'])
             + tag('SourceComponent', 'ByteProperty', nm('EComponentType::' + drv['component']), nm('EComponentType'))
             + ftag('Multiplier', drv['multiplier'])
             + btag('bUseRange', True)
             + ftag('RangeMin', r0) + ftag('RangeMax', r1)
             + ftag('RemappedMin', remap[0]) + ftag('RemappedMax', remap[1])
             + bone('TargetBone', drv['target'])
             + btag('bAffectTargetTranslation' + drv['axis'], True))
    return stag(name, 'AnimNode_BoneDrivenController', inner)

def build(abp_path, mesh_path, cfg, out_path):
    rs = refskel.read(mesh_path)
    specs = node_specs(rs, cfg)
    drivers = cfg.get('drivers', [])
    copies = cfg.get('copies', [])
    for dv in drivers + copies:
        assert dv['source'] in rs['names'] and dv['target'] in rs['names'], dv
    C = len(copies)
    D = C + len(drivers)          # copies, then drivers, then springs
    M = D + len(specs)
    pkg = upkg.Package(open(abp_path, 'rb').read())
    GC = next(i for i, e in enumerate(pkg.exports) if pkg.ref(e['Class']).endswith('AnimBlueprintGeneratedClass'))
    cdo = next(i for i, e in enumerate(pkg.exports) if pkg.name(e['Name']).startswith('Default__'))
    d = bytearray(pkg.export_data(cdo))
    P = upkg.parse_props(pkg, bytes(d))
    allnodes = [p for p in P if p.type == 'StructProperty' and ('AnimNode_' in (p.extra or '') or 'AnimationNode_' in (p.extra or ''))]
    nodes = {p.name: p for p in allnodes if p.extra == 'AnimNode_AnimDynamics'}
    def node(suffix):
        k = [n for n in nodes if n.endswith(suffix)]; assert len(k) == 1, suffix; return nodes[k[0]]
    tmpl, ptmpl, before = node(cfg['template_node']), node(cfg['plane_template_node']), node(cfg['insert_before'])
    nm = lambda s: fname(pkg, s)
    # --- class: Children (after the tagged props: None, guid flag, Next, SuperStruct, Children)
    gd = bytearray(pkg.export_data(GC))
    G = upkg.parse_props(pkg, bytes(gd))
    g_end = G[-1].vend
    assert pkg.name(struct.unpack_from('<ii', gd, g_end)) == 'None'
    children_off = g_end + 20
    head = struct.unpack_from('<i', gd, children_off)[0] - 1
    _, order = anim_chain(pkg, head)
    n0 = len(order)
    assert len(order) == len(set(order)) and before.name in order
    root_rev = struct.unpack_from('<i', gd, {g.name: g for g in G}['RootAnimNodeIndex'].vstart)[0]
    prop_like = next(i for i, e in enumerate(pkg.exports) if pkg.name(e['Name']) == tmpl.name and e['Outer'] == GC + 1)
    # --- template blobs (offsets relative to the tag start)
    T0, tb = tmpl.start, bytes(d[tmpl.start:tmpl.vend])
    F = {c.name: c for c in tmpl.children}
    S = {c.name: c for c in F['ConstraintSetup'].children}
    pl = F['PlanarLimits']; assert struct.unpack_from('<i', d, pl.vstart)[0] == 0
    PF = {c.name: c for c in ptmpl.children}['PlanarLimits']
    assert struct.unpack_from('<i', d, PF.vstart)[0] == 1
    E0, eb = PF.vstart + 4, bytes(d[PF.vstart + 4:PF.vend])
    el = {c.name: c for c in PF.children[0]}
    e_bone = sub(el['DrivingBone'], 'BoneReference', 'BoneName').vstart - E0
    TP = {c.name: c for c in upkg.parse_props(pkg, bytes(d), el['PlaneTransform'].vstart, el['PlaneTransform'].vend)}
    e_rot, e_pos, e_scl = TP['Rotation'].vstart - E0, TP['Translation'].vstart - E0, TP['Scale3D'].vstart - E0
    # --- pose links index AnimNodeProperties directly (FPoseLinkBase::AttemptRelink), the root / baked state machine /
    # script node indices count from the end (Num - 1 - i). New nodes go to the chain head, so only the direct pose
    # links of the old nodes move (+M); every reverse index keeps pointing at the same node.
    old_links = {}
    for p in allnodes:
        for off in pose_links(p):
            v = struct.unpack_from('<i', d, off)[0]
            old_links[off] = v
            if v >= 0:
                struct.pack_into('<i', d, off, v + M)
    before_off = sub(before, 'ComponentPose', 'LinkID').vstart
    old_input = old_links[before_off]
    assert old_input >= 0
    blobs, names = [], []
    if C:
        cbn = next(p for p in allnodes if p.extra == 'AnimNode_CopyBone')
        cprop = next(i for i, e in enumerate(pkg.exports) if pkg.name(e['Name']) == cbn.name and e['Outer'] == GC + 1)
        CB0, cbb = cbn.start, bytes(d[cbn.start:cbn.vend])
        CF = {c.name: c for c in cbn.children}
        assert sub(CF['EvaluateGraphExposedInputs'], 'BoundFunction') and \
            pkg.name(struct.unpack_from('<ii', d, sub(CF['EvaluateGraphExposedInputs'], 'BoundFunction').vstart)) == 'None'
    for k, cp in enumerate(copies):
        pname = 'AnimGraphNode_CopyBone_' + hashlib.md5(('karin:copy:' + cp['target']).encode()).hexdigest().upper()
        names.append(pname)
        b = bytearray(cbb)
        o = lambda p: p.vstart - CB0
        b[0:8] = nm(pname)
        b[o(sub(CF['SourceBone'], 'BoneName')):o(sub(CF['SourceBone'], 'BoneName')) + 8] = nm(cp['source'])
        b[o(sub(CF['TargetBone'], 'BoneName')):o(sub(CF['TargetBone'], 'BoneName')) + 8] = nm(cp['target'])
        for key, flag in (('bCopyTranslation', 'translation'), ('bCopyRotation', 'rotation'), ('bCopyScale', 'scale')):
            b[o(CF[key]) - 1] = 1 if cp.get(flag, False) else 0
        b[o(CF['ControlSpace']):o(CF['ControlSpace']) + 8] = nm(cp.get('space', 'BCS_ParentBoneSpace'))
        struct.pack_into('<i', b, o(sub(CF['ComponentPose'], 'LinkID')), old_input + M if k == 0 else k - 1)
        struct.pack_into('<f', b, o(CF['Alpha']), 1.0)
        blobs.append(bytes(b))
    for k, dv in enumerate(drivers):
        k += C
        pname = 'AnimGraphNode_BoneDrivenController_' + hashlib.md5(('karin:' + dv['target']).encode()).hexdigest().upper()
        names.append(pname)
        blobs.append(driver_blob(nm, pname, dv, old_input + M if k == 0 else k - 1))
    for k, s in enumerate(specs):
        k += D
        b = bytearray(tb)
        o = lambda p: p.vstart - T0
        def put_name(p, v): b[o(p):o(p) + 8] = nm(v)
        def put_bool(p, v): b[o(p) - 1] = 1 if v else 0
        def put_f(p, v): struct.pack_into('<f', b, o(p), float(v))
        def put_i(p, v): struct.pack_into('<i', b, o(p), int(v))
        def put_v(p, v): struct.pack_into('<3f', b, o(p), *map(float, v))
        pname = 'AnimGraphNode_AnimDynamics_' + hashlib.md5(('karin:' + s['bone']).encode()).hexdigest().upper()
        names.append(pname)
        b[0:8] = nm(pname)
        put_bool(F['bChain'], False)
        put_name(sub(F['BoundBone'], 'BoneReference', 'BoneName'), s['bone'])
        put_name(sub(F['ChainEnd'], 'BoneReference', 'BoneName'), 'None')
        put_v(F['BoxExtents'], s['box']); put_v(F['LocalJointOffset'], s['offset'])
        put_f(F['GravityScale'], s['gravity'])
        put_bool(F['bLinearSpring'], False); put_f(F['LinearSpringConstant'], 0)
        put_bool(F['bAngularSpring'], True); put_f(F['AngularSpringConstant'], s['k'])
        put_bool(F['bEnableWind'], False)
        put_bool(F['bOverrideLinearDamping'], True); put_f(F['LinearDampingOverride'], s['damping'])
        put_bool(F['bOverrideAngularDamping'], True); put_f(F['AngularDampingOverride'], s['damping'])
        put_bool(F['bDoUpdate'], True); put_bool(F['bDoEval'], True)
        for a in 'XYZ':
            put_name(S['Linear%sLimitType' % a], 'AnimPhysLinearConstraintType::Limited')
        put_v(S['LinearAxesMin'], [0, 0, 0]); put_v(S['LinearAxesMax'], [0, 0, 0])
        put_bool(S['bLinearFullyLocked'], True)
        put_name(S['AngularConstraintType'], 'AnimPhysAngularConstraintType::Angular')
        put_name(S['TwistAxis'], 'AnimPhysTwistAxis::AxisY')
        put_f(S['ConeAngle'], 0)
        a = s['limit']
        put_v(S['AngularLimitsMin'], [-a, 0, -a]); put_v(S['AngularLimitsMax'], [a, 0, a])
        put_name(S['AngularTargetAxis'], 'AnimPhysTwistAxis::AxisY')
        put_v(S['AngularTarget'], [0, 1, 0])
        put_bool(F['bUsePlanarLimit'], cfg.get('use_planar', True))
        put_name(F['CollisionType'], 'AnimPhysCollisionType::CoM'); put_f(F['SphereCollisionRadius'], 0)
        put_i(sub(F['ComponentPose'], 'LinkID'), old_input + M if k == 0 else k - 1)
        put_f(F['Alpha'], 1.0); put_i(F['LODThreshold'], -1)
        # planar limits (variable size: splice the array value, fix the array and node tag sizes)
        els = b''
        for p in s['planes']:
            e = bytearray(eb)
            e[e_bone:e_bone + 8] = nm(p['bone'])
            struct.pack_into('<4f', e, e_rot, *p['quat']); struct.pack_into('<3f', e, e_pos, *p['pos'])
            struct.pack_into('<3f', e, e_scl, 1, 1, 1)
            els += bytes(e)
        val = struct.pack('<i', len(s['planes'])) + els
        a0, a1, a2 = pl.start - T0, pl.vstart - T0, pl.vend - T0
        tag = bytearray(b[a0:a1]); struct.pack_into('<i', tag, 16, len(val))
        b = b[:a0] + tag + val + b[a2:]
        struct.pack_into('<i', b, 16, len(b) - (tmpl.vstart - T0))
        blobs.append(bytes(b))
    # --- CDO: relink the old node (link false: the new nodes load but are unreachable), append the new tags
    head_link = M - 1 if cfg.get('link', True) else old_input + M
    struct.pack_into('<i', d, before_off, head_link)
    end = P[-1].vend
    assert pkg.name(struct.unpack_from('<ii', d, end)) == 'None'
    d = d[:end] + b''.join(blobs) + d[end:]
    # --- property exports at the chain head: Children -> new[0] -> ... -> new[M-1] -> old head
    datas = [pkg.export_data(i) for i in range(len(pkg.exports))]
    base = pkg.export_data(prop_like)
    assert pkg.obj_path(struct.unpack_from('<i', base, 36)[0]).endswith('AnimNode_AnimDynamics')
    bdc = None
    if D > C:
        agr = next(-i - 1 for i, im in enumerate(pkg.imports)
                   if pkg.name(im['ClassName']) == 'Package' and pkg.name(im['Name']) == '/Script/AnimGraphRuntime')
        bdc = pkg.find_import('ScriptStruct', '/Script/AnimGraphRuntime.AnimNode_BoneDrivenController') or \
            pkg.add_import('/Script/CoreUObject', 'ScriptStruct', agr, 'AnimNode_BoneDrivenController')
    new_idx = []
    for k, pname in enumerate(names):
        new_idx.append(pkg.add_export(cprop if k < C else prop_like, struct.unpack('<ii', nm(pname)), GC + 1))
        datas.append(None)
    for k, idx in enumerate(new_idx):
        b = bytearray(pkg.export_data(cprop) if k < C else base)
        struct.pack_into('<i', b, 12, new_idx[k + 1] if k + 1 < M else head + 1)
        if C <= k < D:
            struct.pack_into('<i', b, 36, bdc)       # StructProperty::Struct
        datas[idx - 1] = bytes(b)
    struct.pack_into('<i', gd, children_off, new_idx[0])
    datas[GC] = bytes(gd)
    datas[cdo] = bytes(d)
    out = pkg.write(datas)
    open(out_path, 'wb').write(out)
    # --- verify on the written package
    q = upkg.Package(out)
    qg = q.export_data(GC)
    _, qorder = anim_chain(q, struct.unpack_from('<i', qg, children_off)[0] - 1)
    assert qorder == names + order, 'chain order'
    QG = {g.name: g for g in upkg.parse_props(q, qg)}
    assert struct.unpack_from('<i', qg, QG['RootAnimNodeIndex'].vstart)[0] == root_rev
    assert qorder[len(qorder) - 1 - root_rev] == order[n0 - 1 - root_rev]
    qd = q.export_data(cdo)
    Q = upkg.parse_props(q, qd)
    assert len(Q) == len(P) + M
    qn = {p.name: p for p in Q}
    nchk = 0
    for p in allnodes:
        olds = [(k, old_links[k]) for k in pose_links(p)]
        news = list(pose_links(qn[p.name]))
        assert len(olds) == len(news), p.name
        for (off_old, v_old), off_new in zip(olds, news):
            v_new = struct.unpack_from('<i', qd, off_new)[0]
            if off_old == before_off:
                assert v_new == head_link; continue
            assert (v_old < 0 and v_new == v_old) or qorder[v_new] == order[v_old], (p.name, v_old, v_new)
            nchk += 1
    for k, pname in enumerate(names):
        lid = struct.unpack_from('<i', qd, sub(qn[pname], 'ComponentPose', 'LinkID').vstart)[0]
        assert qorder[lid] == (order[old_input] if k == 0 else names[k - 1])
        if k < C:
            ch = {c.name: c for c in qn[pname].children}
            assert qn[pname].extra == 'AnimNode_CopyBone', qn[pname]
            assert q.name(struct.unpack_from('<ii', qd, sub(ch['TargetBone'], 'BoneName').vstart)) == copies[k]['target']
            assert q.name(struct.unpack_from('<ii', qd, sub(ch['SourceBone'], 'BoneName').vstart)) == copies[k]['source']
            pidx = next(i for i, e in enumerate(q.exports) if q.name(e['Name']) == pname)
            assert q.obj_path(struct.unpack_from('<i', q.export_data(pidx), 36)[0]).endswith('AnimNode_CopyBone')
        elif k < D:
            ch = {c.name: c for c in qn[pname].children}
            assert qn[pname].extra == 'AnimNode_BoneDrivenController', qn[pname]
            assert q.name(struct.unpack_from('<ii', qd, sub(ch['TargetBone'], 'BoneName').vstart)) == drivers[k - C]['target']
            pidx = next(i for i, e in enumerate(q.exports) if q.name(e['Name']) == pname)
            assert q.obj_path(struct.unpack_from('<i', q.export_data(pidx), 36)[0]) == \
                '/Script/AnimGraphRuntime.AnimNode_BoneDrivenController'
        else:
            assert len({c.name: c for c in qn[pname].children}['PlanarLimits'].children) == len(specs[k - D]['planes'])
    if cfg.get('link', True):
        assert qorder[head_link] == names[-1]
    return {'anim_nodes_before': n0, 'added': M, 'old_input': old_input, 'links_checked': nchk,
            'copies': [dict(cp, name=n) for cp, n in zip(copies, names)],
            'drivers': [dict(dv, name=n) for dv, n in zip(drivers, names[C:])],
            'nodes': [dict(s, k=round(s['k'], 1), damping=round(s['damping'], 6), name=n) for s, n in zip(specs, names[D:])]}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('abp', help='cooked AnimBlueprint (game format), e.g. Deacon_VimBlueprint.uasset')
    ap.add_argument('mesh', help='cooked Karin mesh (its reference skeleton has the KO_* / KB_* bones)')
    ap.add_argument('cfg', help='springs JSON, e.g. configs/springs_t31.json')
    ap.add_argument('out', help='output AnimBlueprint .uasset')
    ap.add_argument('report', nargs='?', help='optional report JSON')
    args = ap.parse_args()
    rep = build(args.abp, args.mesh, json.load(open(args.cfg)), args.out)
    txt = json.dumps(rep, indent=1)
    if args.report:
        open(args.report, 'w').write(txt)
    print('added', rep['added'], 'nodes before', rep['anim_nodes_before'], 'old nodes; pose links checked', rep['links_checked'])
    for cp in rep['copies']:
        print('copy   %-16s <- %s %s t%d r%d s%d' % (cp['target'], cp['source'], cp.get('space', 'BCS_ParentBoneSpace'),
              cp.get('translation', False), cp.get('rotation', False), cp.get('scale', False)))
    for dv in rep['drivers']:
        print('driver %-16s <- %s %s range %s x %.3f' % (dv['target'], dv['source'], dv['component'], dv['range'], dv['multiplier']))
    for n in rep['nodes']:
        print('%-22s L %5.1f k %8.1f lim %4.1f planes %s' % (n['bone'], n['len'], n['k'], n['limit'],
              ', '.join('%s c%.1f' % (p['bone'], p['clear']) for p in n['planes'])))
