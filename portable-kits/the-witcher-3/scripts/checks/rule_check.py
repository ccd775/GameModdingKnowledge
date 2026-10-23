"""For each look-at node A (triangle A->B) of a dyng spec: roll difference between its bind frame and the frame
the 'keep the dyng parent's Z (or Y)' rule would build with X aimed at B.

Usage: python rule_check.py <karin_dyng_spec.json>     (numpy)
The game keeps Z (errZrule = 0 for every node is the target; karin_build.py builds look-at frames that way).
"""
import json, sys
import numpy as np
spec = json.load(open(sys.argv[1]))
nodes = spec['nodes']
W = []
for n in nodes:
    L = np.eye(4); L[:3, 0], L[:3, 1], L[:3, 2], L[:3, 3] = n['local'][0], n['local'][1], n['local'][2], n['local'][3]
    W.append((W[n['parent_index']] if n['parent_index'] >= 0 else np.eye(4)) @ L)
def roll_err(a, axis):
    Ra = W[a][:3, :3]; Rp = W[nodes[a]['parent_index']][:3, :3]
    x = Ra[:, 0]
    ref = Rp[:, axis] - (Rp[:, axis] @ x) * x
    ref /= np.linalg.norm(ref)
    # angle between bind axis and rule axis, both perpendicular to x
    own = Ra[:, axis]
    return np.degrees(np.arctan2(np.cross(ref, own) @ x, ref @ own))
groups = {}
for t in spec['triangles']:
    a = t[0]
    nm = nodes[a]['name']
    key = nm.split('_0')[0]
    groups.setdefault(key, []).append((nm, roll_err(a, 2), roll_err(a, 1), nodes[a]['parent']))
for k, v in groups.items():
    print(k)
    for nm, ez, ey, par in v:
        print(f'   {nm:22s} parent={par:10s} errZrule={ez:7.1f}  errYrule={ey:7.1f}')
