"""Append joints to an i30 .model (used for the AnimDynamics chains).

Conventions (checked against Black Cat / Venom dynamics joints):
- ModelJoint 16 B: i16 parent, u16 index, u16 u1 (= number of descendants), u16 u2 flags (0x80 skinned; dynamics joints
  use 0x81 when weighted, 0x01 for chain tips), u32 crc32(name, case kept), u32 name offset relative to the entry.
  Names follow the entry table.
- ModelBindPose 48 B: scale3, 0, quat xyzw, pos3, 0 (local to the parent). quat -> column-vector R; the row-vector local
  matrix is R^T, i.e. world_row = L @ parent_world_row.
- ModelInvBindPose 64 B: inverse of the row-vector world matrix.
- ModelJointLookup: (crc32, index) sorted by crc32, then a (0xFFFFFFFF, 0xFFFFFFFF) sentinel.
- ModelJointHierarchy: u16 0, joint count, mirror count, leaf count; ModelLeafIds = the childless joints.
- ModelMirrorIds: u16 pairs (kind << 12 | joint, mirror joint), sorted by joint; centre joints map to themselves (kind 3),
  each left/right pair is listed once. Every joint with u2 bit 0x01 appears in it (all originals, incl. Black Cat's
  dynamics joints). T9 appended 0x01 joints without entries and they rendered pinned at the model origin in game.

Originals list joints in DFS preorder with contiguous subtrees (survey_joint_order.py: 378/378). New joints are appended
at the end (each chain contiguous, ancestors' u1 left alone), which keeps parent < child but puts the chains outside
their parent's index range. If the runtime ever needs strict contiguity, switch to inserting + reindexing.
"""
import os, struct, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get('SM2_ALERT') or os.path.join(os.path.dirname(HERE), 'ext', 'ALERT'))

T_JOINT, T_BIND, T_INVBIND = 0x15DF9D3B, 0xDCC88A19, 0x2C2CA205
T_HIER, T_LOOKUP, T_LEAF, T_MIRROR = 0x90CDB60C, 0xEE31971C, 0xB7380E8C, 0xC5354B60
MIRROR_SELF = 3


def joint_hash(name):
    import dat1lib.crc32 as c32   # ALERT, imported on first use
    return c32.hash(name, False)


def m2q(R):
    """column-vector rotation matrix -> quat xyzw"""
    t = np.trace(R)
    if t > 0:
        s = np.sqrt(t + 1) * 2
        q = [(R[2, 1] - R[1, 2]) / s, (R[0, 2] - R[2, 0]) / s, (R[1, 0] - R[0, 1]) / s, s / 4]
    else:
        i = int(np.argmax(np.diag(R)))
        j, k = (i + 1) % 3, (i + 2) % 3
        s = np.sqrt(1 + R[i, i] - R[j, j] - R[k, k]) * 2
        q = [0.0] * 4
        q[i] = s / 4
        q[j] = (R[j, i] + R[i, j]) / s
        q[k] = (R[k, i] + R[i, k]) / s
        q[3] = (R[k, j] - R[j, k]) / s
    q = np.array(q)
    return q / np.linalg.norm(q)


def aim_frame(pos, target, up_hint):
    """row-vector 4x4 world matrix: X toward target, Y as close to up_hint as possible"""
    x = target - pos
    x = x / np.linalg.norm(x)
    y = up_hint - x * (up_hint @ x)
    if np.linalg.norm(y) < 1e-6:
        y = np.array([0.0, 0.0, 1.0]) - x * x[2]
    y = y / np.linalg.norm(y)
    z = np.cross(x, y)
    W = np.eye(4)
    W[0, :3], W[1, :3], W[2, :3], W[3, :3] = x, y, z, pos
    return W


def add_joints(d, new, parent_world):
    """d: DAT1 of a model (edited in place). new: [dict(name, parent (index in the final list), world (row 4x4), u2)].
    parent_world(i) -> row-vector world matrix of an existing joint i. Returns the index of the first new joint."""
    js = d.get(T_JOINT)
    bp = d.get(T_BIND)
    n0 = len(bp) // 48
    k = len(new)
    worlds = {}
    entries = bytearray()
    names = bytearray(js[16 * n0:])                 # original names, offsets shift by 16 * k
    for i in range(n0):
        p, ix, u1, u2, h, so = struct.unpack_from('<hHHHII', js, 16 * i)
        entries += struct.pack('<hHHHII', p, ix, u1, u2, h, so + 16 * k)
    desc = [0] * k
    for i in range(k - 1, -1, -1):
        p = new[i]['parent'] - n0
        if p >= 0:
            desc[p] += desc[i] + 1
    bind = bytearray(bp)
    inv = bytearray(d.get(T_INVBIND))
    for i, nj in enumerate(new):
        gi = n0 + i
        p = nj['parent']
        assert 0 <= p < gi
        W = np.asarray(nj['world'], np.float64)
        worlds[gi] = W
        Wp = worlds[p] if p >= n0 else parent_world(p)
        L = W @ np.linalg.inv(Wp)
        q = m2q(L[:3, :3].T)
        off = 16 * (n0 + k) + len(names) - 16 * gi
        entries += struct.pack('<hHHHII', p, gi, desc[i], nj['u2'], joint_hash(nj['name']), off)
        names += nj['name'].encode() + bytes(1)
        bind += struct.pack('<12f', 1, 1, 1, 0, *q, *L[3, :3], 0)
        inv += np.linalg.inv(W).astype(np.float32).tobytes()
    out = entries + names
    out += bytes(-len(out) % 4)
    d.sections[T_JOINT] = bytes(out)
    d.sections[T_BIND] = bytes(bind)
    d.sections[T_INVBIND] = bytes(inv)
    # lookup
    lk = d.get(T_LOOKUP)
    pairs = [struct.unpack_from('<II', lk, 8 * i) for i in range(len(lk) // 8)]
    pairs = [x for x in pairs if x != (0xFFFFFFFF, 0xFFFFFFFF)]
    pairs += [(joint_hash(nj['name']), n0 + i) for i, nj in enumerate(new)]
    hs = [x[0] for x in pairs]
    assert len(set(hs)) == len(hs), 'joint hash collision'
    pairs.sort()
    d.sections[T_LOOKUP] = b''.join(struct.pack('<II', *x) for x in pairs) + struct.pack('<II', 0xFFFFFFFF, 0xFFFFFFFF)
    # leaves + hierarchy counts
    leaf0 = list(struct.unpack_from(f'<{len(d.get(T_LEAF)) // 2}H', d.get(T_LEAF), 0))
    hier = bytearray(d.get(T_HIER))
    z, nj_, nm, nl = struct.unpack_from('<4H', hier, 0)
    assert nj_ == n0 and nl == len(leaf0)
    gaining = {nj['parent'] for nj in new if nj['parent'] < n0}       # old leaves that get children stop being leaves
    leaf = [x for x in leaf0 if x not in gaining] + [n0 + i for i in range(k) if desc[i] == 0]
    d.sections[T_LEAF] = struct.pack(f'<{len(leaf)}H', *leaf)
    # mirror: new 0x01 joints mirror onto themselves (their indices are the largest, so the table stays sorted)
    mir = d.get(T_MIRROR)
    assert len(mir) == 4 * nm, 'mirror table / hierarchy count mismatch'
    add = [n0 + i for i, nj in enumerate(new) if nj['u2'] & 1]
    d.sections[T_MIRROR] = mir + b''.join(struct.pack('<2H', MIRROR_SELF << 12 | g, g) for g in add)
    struct.pack_into('<4H', hier, 0, z, n0 + k, nm + len(add), len(leaf))
    d.sections[T_HIER] = bytes(hier)
    return n0
