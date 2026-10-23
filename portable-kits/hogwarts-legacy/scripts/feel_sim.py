# feel_sim.py <dyn_nodes.json> <part> <root bone> : planar small-angle model of one per-bone AnimDynamics chain.
# Each node: I*th'' = -K*(th - th_parent) - c*I*th' - D*(A_anchor) ; anchor accel A_k = A_{k-1} + L_{k-1}*th_{k-1}''
# Input: start running (0 -> 600 cm/s in 0.25 s), run 2 s, stop in 0.2 s; sim acc = clamp(v*vs + a*as).
# Prints tip-angle metrics: peak at start, trailing while running, after stop: peak, overshoots, time to stay < 3 deg.
import argparse, json, sys, math
ap = argparse.ArgumentParser(description='planar small-angle model of one AnimDynamics chain from dyn_nodes.json')
ap.add_argument('nodes', help='dyn_nodes.json'); ap.add_argument('part', help='e.g. KarinHair')
ap.add_argument('root', help='bone-name prefix of the chain, e.g. Hair_tail_L')
args = ap.parse_args()
import numpy as np
nodes = [n for n in json.load(open(args.nodes))[args.part] if n['BoundBone']['BoneName'].startswith(args.root)]
N = len(nodes)
D = np.array([-n['LocalJointOffset']['X'] for n in nodes]); R = np.array([n['BoxExtents']['X'] for n in nodes])
b = np.array([n['BoxExtents']['Y'] for n in nodes])
I = (R * R + b * b) / 12 + D * D
K = np.array([n['AngularSpringConstant'] for n in nodes])
c = np.array([-math.log(1 - n['AngularDampingOverride']) for n in nodes])
L = np.append(R[:-1] - R[1:], 0)                  # joint-to-next-joint distance
vs = nodes[0]['ComponentLinearVelScale']['X']; as_ = nodes[0]['ComponentLinearAccScale']['X']; cl = nodes[0]['ComponentAppliedLinearAccClamp']['X']
lim = math.radians(nodes[0]['ConstraintSetup']['AngularLimitsMax']['Z'])
dt = 1 / 240; T = 6.0; th = np.zeros(N); om = np.zeros(N); out = []
def vel(t):
    if t < 0.25: return 600 * t / 0.25
    if t < 2.25: return 600
    if t < 2.45: return 600 * (1 - (t - 2.25) / 0.2)
    return 0
for s in range(int(T / dt)):
    t = s * dt; a = (vel(t + dt) - vel(t - dt)) / (2 * dt)
    ext = float(np.clip(vel(t) * vs + a * as_, -cl, cl))
    A = ext; acc = np.zeros(N)
    for k in range(N):
        par = th[k - 1] if k else 0.0
        acc[k] = (-K[k] * (th[k] - par) - c[k] * I[k] * om[k] - D[k] * A) / I[k]
        A = A + L[k] * acc[k]
    om += acc * dt; th += om * dt
    for k in range(N):                              # per-node limit relative to parent
        par = th[k - 1] if k else 0.0
        if abs(th[k] - par) > lim: th[k] = par + math.copysign(lim, th[k] - par); om[k] = om[k - 1] if k else 0
    out.append((t, math.degrees(th[-1])))
o = np.array(out); tip = o[:, 1]
start = np.abs(tip[o[:, 0] < 1.0]).max(); run = tip[(o[:, 0] > 1.8) & (o[:, 0] < 2.25)].mean()
after = o[o[:, 0] >= 2.25]; pk = np.abs(after[:, 1]).max()
sgn = np.sign(after[:, 1]); cross = int((np.diff(sgn[np.abs(after[:, 1]) > 1]) != 0).sum())
settle = next((after[i, 0] - 2.25 for i in range(len(after)) if np.all(np.abs(after[i:, 1]) < 3)), float('nan'))
f = math.sqrt(K[0] / I[0]) / 2 / math.pi
print('%-12s nodes %d f %.2f Hz | start peak %5.1f deg | running trail %5.1f | after stop peak %5.1f, swings past centre %d, settles <3deg in %.2f s' % (args.root, N, f, start, run, pk, cross, settle))
