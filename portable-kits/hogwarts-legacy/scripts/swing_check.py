# swing_check.py <fit_dir>  (after dyn_params.py has written <fit_dir>/dyn_nodes.json)
# Kinematic check: swing a thigh forward/back, let each skirt node rotate outward (parents first) until its COM clears
# the swung collider spheres (as the hard Outer limits would), then sample each chain polyline against the thigh capsule.
import argparse, json, math, sys
ap = argparse.ArgumentParser(description='kinematic skirt / thigh clearance check on dyn_nodes.json')
ap.add_argument('fit_dir', help='fit dir with skel_ext.json, dyn_chains.json and dyn_nodes.json')
fit = ap.parse_args().fit_dir
import numpy as np
nodes = json.load(open(fit + '/dyn_nodes.json'))['KarinBody']
bones = json.load(open(fit + '/skel_ext.json'))['bones']; chains = json.load(open(fit + '/dyn_chains.json'))
def qmat(q):
    x, y, z, w = q
    return np.array([[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)], [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)], [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]])
G = []
for b in bones:
    M = np.eye(4); M[:3, :3] = qmat(b['r']); M[:3, 3] = b['t']; G.append(M if b['parent'] < 0 else G[b['parent']] @ M)
IDX = {b['name']: i for i, b in enumerate(bones)}
def rodr(ax, a):
    ax = ax / np.linalg.norm(ax); K = np.array([[0, -ax[2], ax[1]], [ax[2], 0, -ax[0]], [-ax[1], ax[0], 0]])
    return np.eye(3) + math.sin(a) * K + (1 - math.cos(a)) * K @ K
ND = {n['BoundBone']['BoneName']: n for n in nodes}
THR = 8.3  # thigh surface radius (p90 measured 8.2-8.5)
for side in ('Left', 'Right'):
  for phi in (55, 70, -30):
    hip = G[IDX[side + 'UpLeg']][:3, 3]; knee = G[IDX[side + 'Leg']][:3, 3]
    Rsw = rodr(np.array([1.0, 0, 0]), math.radians(phi))    # sign checked below: +phi moves the knee to +Y (front)
    knee2 = hip + Rsw @ (knee - hip)
    if phi > 0: assert knee2[1] > knee[1], 'swing sign'
    def swung(bone, off):  # sphere centre after the swing (only the thigh's own bones move)
        p = G[IDX[bone]][:3, :3] @ np.array([off['X'], off['Y'], off['Z']]) + G[IDX[bone]][:3, 3]
        return hip + Rsw @ (p - hip) if bone == side + 'UpLeg' else p
    def depth(p):  # penetration into the swung thigh capsule (t in 0..0.6)
        ab = knee2 - hip; t = np.clip(np.dot(p - hip, ab) / np.dot(ab, ab), 0, 0.6)
        return THR - np.linalg.norm(p - (hip + ab * t))
    before = after = 0; worst_b = worst_a = 0; samples = 0; blocked = 0
    for c in chains:
        if not c['root'].startswith('Skirt_'): continue
        bl = c['bones']; P = [G[IDX[b]][:3, 3].copy() for b in bl]
        tip = P[-1] + G[IDX[bl[-1]]][:3, 0] * c['seg_len']; pts = P + [tip]
        def poly(pts): return [pts[i] + (pts[i + 1] - pts[i]) * s for i in range(len(pts) - 1) for s in np.linspace(0, 1, 6)]
        for q in poly(pts):
            d = depth(q); samples += 1
            if d > 0: before += 1; worst_b = max(worst_b, d)
        # resolve: node k rotates outward about its joint (axis = joint frame Y, sign toward +Z) until COM clears
        cur = [p.copy() for p in pts]
        for k, b in enumerate(bl):
            n = ND[b]; R = np.linalg.norm(cur[-1] - cur[k]); D = -n['LocalJointOffset']['X']
            ax = G[IDX[b]][:3, 1]; lim = math.radians(-n['ConstraintSetup']['AngularLimitsMin']['Y'])
            sph = [(swung(s['DrivingBone']['BoneName'], s['SphereLocalOffset']), s['LimitRadius'] + n['SphereCollisionRadius']) for s in n['SphericalLimits']]
            best = None
            for a in np.linspace(0, lim, 41):
                Rr = rodr(ax, -a)  # tilting X toward +Z is a rotation about Y by -a
                com = cur[k] + Rr @ ((cur[-1] - cur[k]) / R) * D
                if all(np.linalg.norm(com - cc) >= rr for cc, rr in sph): best = Rr; break
            if best is None: best = rodr(ax, -lim); blocked += 1
            for j in range(k + 1, len(cur)): cur[j] = cur[k] + best @ (cur[j] - cur[k])
        for q in poly(cur):
            d = depth(q)
            if d > 0: after += 1; worst_a = max(worst_a, d)
    print('%-5s thigh %+d deg: samples inside thigh before %d (max %.1f cm) after %d (max %.1f cm); nodes at limit %d' % (side, phi, before, worst_b, after, worst_a, blocked))
