# dyn_params.py <fit_dir> <params.json> <out.json>
# Turns fit.py's dynamic chains (dyn_chains.json + skel_ext.json, UE space) into AnimDynamics node settings per part.
# Single-bone nodes, parents first (HL's own setup): each body is limited and sprung around its animated frame, which
# already carries the simulated parent. Chain mode can't be used: its links are limited around a straight
# continuation and their spring target is the fixed sim-space X axis. Long chains simulate every n-th bone (sim_every);
# the bones in between follow rigidly, which keeps the per-node lag from piling up along the strand.
# Each body stands in for the rest of its strand (rod of length R from the joint, COM at com_frac * R, default
# R/2, mass 1). Per category:
#   defl  total static bend of the chain (deg) under 1 g of sideways acceleration, split evenly over its nodes
#         -> stiffness K + gravity's own restoring stiffness = 980 * (R/2) / angle;
#   freq  swing frequency -> moment of inertia I = stiffness / w^2, realised through the box cross size;
#   zeta  damping ratio -> d = 1 - exp(-2 zeta w).
# AnimDynamics semantics (UE 4.27 AnimPhysicsSolver / AnimNode_AnimDynamics):
#   spring: AngularMomentum += -k * angle * dt; damping: momentum *= (1 - d)^dt, on both linear and angular momentum
#   and in absolute sim space (so it also lags rotations of the parent); component motion:
#   acc = -(vel * VelScale) - (acc * AccScale), clamped per axis; twist is always locked.
#   limits: Swing.Y < 0 when the body's X tilts toward its frame's +Z, Swing.Z > 0 when it tilts toward +Y.
# Collision: Outer spherical limits on the nearest point of each collider segment, radius capped by the body's rest
# distance so nothing starts inside and the rest shape is kept.
import argparse, json, sys, math
ap = argparse.ArgumentParser(description='AnimDynamics node settings per part from fit.py output and dyn.json')
ap.add_argument('fit_dir', help='fit.py out_dir (dyn_chains.json, skel_ext.json)')
ap.add_argument('params', help='dyn.json')
ap.add_argument('out', help='dyn_nodes.json to write')
args = ap.parse_args()
import numpy as np

fit_dir, params_path, out_path = args.fit_dir, args.params, args.out
chains = json.load(open(fit_dir + '/dyn_chains.json'))
bones = json.load(open(fit_dir + '/skel_ext.json'))['bones']
PRM = json.load(open(params_path, encoding='utf-8'))
G_CM = 980.0

def qmat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
G = []
for b in bones:
    M = np.eye(4); M[:3, :3] = qmat(b['r']) * np.array(b['s']); M[:3, 3] = b['t']
    G.append(M if b['parent'] < 0 else G[b['parent']] @ M)
IDX = {b['name']: i for i, b in enumerate(bones)}
def pos(n): return G[IDX[n]][:3, 3]

def category(root):
    for cat, prefixes in PRM['categories'].items():
        if any(root.startswith(p) for p in prefixes): return cat
    return 'default'

def vec(v): return {'X': float(v[0]), 'Y': float(v[1]), 'Z': float(v[2])}

def collider_limits(com, S):
    # Outer spheres near this body. Collider entries: [bone, end bone|null, t0, t1, max radius] puts one sphere on the
    # segment point nearest the body's rest COM; [bone, end bone, [t, ...], max radius] puts spheres at fixed points
    # along the segment (thighs: the points that sweep into the skirt when the leg swings, not the hip joint).
    out = []
    for cl in S.get('colliders', []):
        bone, end = cl[0], cl[1]; a = pos(bone)
        if isinstance(cl[2], list):
            ts, rmax = cl[2], cl[3]
        else:
            rmax = cl[4]
            ts = [float(np.clip(np.dot(com - a, pos(end) - a) / np.dot(pos(end) - a, pos(end) - a), cl[2], cl[3]))] if end else [0.0]
        for t in ts:
            q = a + (pos(end) - a) * t if end else a
            dist = float(np.linalg.norm(com - q))
            if dist > rmax + S.get('collider_reach', 12): continue
            r = min(rmax, dist - S['body_radius'] - 0.3)
            if r < 2.0: continue
            off = (np.linalg.inv(G[IDX[bone]]) @ np.append(q, 1))[:3]
            out.append({'DrivingBone': {'BoneName': bone}, 'SphereLocalOffset': vec(off), 'LimitRadius': round(r, 2), 'LimitType': 'Outer'})
    return out

def swing_limits(i, S, outward):
    # AngularLimitsMin/Max (X = twist, locked anyway). With an outward direction, the swing that tilts X toward it
    # gets limit_out and the opposite one limit_in; the other swing axis gets limit_side.
    lo = S.get('limit', 15)
    if outward is None or 'limit_out' not in S:
        return vec([0, -lo, -lo]), vec([0, lo, lo]), None
    R = G[i][:3, :3]; x, y, z = R[:, 0], R[:, 1], R[:, 2]
    o = outward - np.dot(outward, x) * x; o /= np.linalg.norm(o)
    oy, oz = float(np.dot(o, y)), float(np.dot(o, z))
    out_, in_, side = S['limit_out'], S['limit_in'], S['limit_side']
    if abs(oz) >= abs(oy):  # tilt toward +Z <=> Swing.Y < 0
        mn, mx = ([0, -out_, -side], [0, in_, side]) if oz > 0 else ([0, -in_, -side], [0, out_, side])
    else:                   # tilt toward +Y <=> Swing.Z > 0
        mn, mx = ([0, -side, -in_], [0, side, out_]) if oy > 0 else ([0, -side, -out_], [0, side, in_])
    return vec(mn), vec(mx), max(abs(oy), abs(oz))

out = {}
for c in chains:
    cat = category(c['root']); S = dict(PRM['defaults']); S.update(PRM['settings'].get(cat, {}))
    bl = c['bones']; n = len(bl)
    seglen = [float(np.linalg.norm(pos(bl[k + 1]) - pos(bl[k]))) for k in range(n - 1)] + [c['seg_len']]
    tip = pos(bl[-1]) + G[IDX[bl[-1]]][:3, 0] * seglen[-1]
    w = 2 * math.pi * S['freq']; s = S['gravity']
    sim = list(range(0, n, S.get('sim_every', 1)))
    ang = math.radians(S['defl'] / len(sim))
    nodes = []; info = []
    for k in sim:
        bn = bl[k]; i = IDX[bn]; p = pos(bn)
        R = sum(seglen[k:]); D = R * S.get('com_frac', 0.5)  # skirt: COM near the hem, where collisions matter
        d = tip - p; d /= np.linalg.norm(d)
        cosp = max(0.0, -d[2]); sinp = math.sqrt(max(0.0, 1 - d[2] * d[2]))
        k_hang = G_CM * s * D * cosp                       # gravity's restoring stiffness around a hanging rest
        k_tot = max(G_CM * D / ang, k_hang)
        K = k_tot - k_hang
        I_j = max(k_tot / (w * w), R * R / 12 + D * D + 1)  # can't go below a thin rod's inertia
        b = math.sqrt(max(12 * (I_j - D * D) - R * R, 4.0))
        w_act = math.sqrt(k_tot / I_j)
        cdamp = 2 * S['zeta'] * w_act
        damp = min(0.99999, 1 - math.exp(-cdamp))  # float32 1-d must stay > 0 or momentum is wiped each step
        com = p + G[i][:3, 0] * D
        outward = None
        if S.get('outward_from'):
            o = p - pos(S['outward_from']); o[2] = 0
            outward = o / np.linalg.norm(o) if np.linalg.norm(o) > 1e-3 else None
        amin, amax, dom = swing_limits(i, S, outward)
        lims = collider_limits(com, S)
        nodes.append({
            'BoundBone': {'BoneName': bn}, 'ChainEnd': {'BoneName': 'None'}, 'bChain': False,
            'BoxExtents': vec([R, round(b, 2), round(b, 2)]), 'LocalJointOffset': vec([-D, 0, 0]),
            'GravityScale': s, 'SimulationSpace': 'Component',
            'ComponentLinearAccScale': vec([S['acc']] * 3), 'ComponentLinearVelScale': vec([S['vel']] * 3),
            'ComponentAppliedLinearAccClamp': vec([S['acc_clamp']] * 3),
            'bOverrideAngularDamping': True, 'AngularDampingOverride': round(damp, 6),
            'bOverrideLinearDamping': True, 'LinearDampingOverride': round(damp, 6),
            'NumSolverIterationsPreUpdate': S['iters'][0], 'NumSolverIterationsPostUpdate': S['iters'][1],
            'bAngularSpring': bool(K > 0), 'AngularSpringConstant': round(K, 1),
            'ConstraintSetup': {
                'LinearXLimitType': 'Limited', 'LinearYLimitType': 'Limited', 'LinearZLimitType': 'Limited',
                'LinearAxesMin': vec([0, 0, 0]), 'LinearAxesMax': vec([0, 0, 0]),
                'AngularConstraintType': 'Angular', 'TwistAxis': 'AxisX',
                'AngularLimitsMin': amin, 'AngularLimitsMax': amax,
                'AngularTargetAxis': 'AxisX', 'AngularTarget': vec([1, 0, 0]),
            },
            'CollisionType': 'CustomSphere', 'SphereCollisionRadius': S['body_radius'],
            'bUseSphericalLimits': bool(lims), 'SphericalLimits': lims,
            'bEnableWind': False,
        })
        sag = math.degrees(G_CM * s * D * sinp / k_tot)
        info.append('%s R%.0f K%.0f b%.0f f%.2f z%.2f sag%.1f sph%d%s' % (bn.replace(c['root'], '~'), R, K, b, w_act / 2 / math.pi, -math.log(1 - damp) / 2 / w_act, sag, len(lims), '' if dom is None else ' dom%.2f' % dom))
    for part in c['parts']:
        out.setdefault(part, []).extend(nodes)
    print('%-14s %-8s' % (c['root'], cat), ' | '.join(info))
print('nodes per part', {k: len(v) for k, v in out.items()})
json.dump(out, open(out_path, 'w'), indent=1)
