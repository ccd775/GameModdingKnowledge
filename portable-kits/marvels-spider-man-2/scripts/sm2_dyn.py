"""Glue between the fitted spring chains (sm2_karin_geo --dyn) and a target .model:
  add_dyn_joints(raw, dyn)      append the chain joints (i30_joints) -> raw
  attach_dynamics(raw, dyn)     add ModelAnimDynamicsDef + chain name strings, set the ModelBuilt flag -> raw
dyn = dict(names=[joint names], parents=[parent joint name], world=[row 4x4], chains=[dict(joints=[names], key, params)])
"""
import struct
import numpy as np

import i30_model as M
import i30_joints as IJ
import i30_dynamics as ID
from i30_build import split_asset, save_model, T_BUILT

T_MAT = 0x3250BB80
U2_DYN = 0x01            # dynamics joints in the originals: 0x01 (+0x80 when weighted, set by the model builder)


def load(npz):
    import json
    z = np.load(npz)
    if '_dyn__world' not in z.files:
        return None
    names = [str(x) for x in z['_meta__joint_names']]
    par = z['_meta__parents']
    W = z['_dyn__world']
    n0 = len(names) - len(W)
    from sm2_karin_geo import DYN_SPRINGS        # current chain parameters win over the ones saved at fit time
    chains = [dict({k: v for k, v in c.items() if k in ('joints', 'key')}, **DYN_SPRINGS.get(c['key'], {}))
              for c in json.loads(str(z['_dyn__chains']))]
    return dict(names=names[n0:], parents=[names[p] for p in par[n0:]], world=list(W), chains=chains)


def add_dyn_joints(raw, dyn, plain=False):
    """plain: u2 0x00 (no 0x01, no mirror entry) - ordinary procedural joints, for A/B tests without dynamics"""
    m = M.Model(raw)
    have = [j['name'] for j in m.joints]
    Wm = m.joint_world()
    header, d = split_asset(raw)
    base = d.string_base()
    n0 = len(have)
    ix = {n: i for i, n in enumerate(have)}
    new = []
    for i, nm in enumerate(dyn['names']):
        assert nm not in ix
        ix[nm] = n0 + i
        new.append(dict(name=nm, parent=ix[dyn['parents'][i]], world=dyn['world'][i], u2=0 if plain else U2_DYN))
    IJ.add_joints(d, new, lambda j: Wm[j])
    h, body = save_model(header, d, base)
    return h + body


def attach_dynamics(raw, dyn):
    m = M.Model(raw)
    ix = {j['name']: i for i, j in enumerate(m.joints)}
    header, d = split_asset(raw)
    base = d.string_base()
    d.set(ID.T_DYN, b'', after=T_MAT)                 # table grows first, so offsets below are final
    strings = bytearray(d.strings)
    chains = []
    for c in dyn['chains']:
        off = d.string_base() + len(strings)
        strings += f'karin_{c["key"]}'.encode() + bytes(1)
        cc = {k: v for k, v in c.items() if k not in ('joints', 'key')}
        chains.append(dict(cc, joints=[ix[n] for n in c['joints']], name_off=off))
    strings += bytes(-len(strings) % 4)
    d.strings = bytes(strings)
    d.sections[ID.T_DYN] = ID.build(m, chains)
    b = bytearray(d.get(T_BUILT))
    struct.pack_into('<I', b, 0, struct.unpack_from('<I', b, 0)[0] | ID.BUILT_HAS_DYNAMICS)
    d.sections[T_BUILT] = bytes(b)
    h, body = save_model(header, d, base)
    return h + body


BSPHERE_RADIUS_F32 = 11   # ModelBuilt as f32: [8..10] bounding-sphere centre, [11] radius, [12..14] box half extents


def set_bsphere_radius(raw, radius):
    """AnimDynamics only update within (bsphere radius x AnimDynamicsUpdateMultiplier) of the camera (exe string); the
    player base models have a 3-vertex placeholder mesh (radius 0.19 m), so their simulation only ran on resets (T12)."""
    header, d = split_asset(raw)
    base = d.string_base()
    b = bytearray(d.get(T_BUILT))
    struct.pack_into('<f', b, 4 * BSPHERE_RADIUS_F32, max(radius, struct.unpack_from('<f', b, 4 * BSPHERE_RADIUS_F32)[0]))
    d.sections[T_BUILT] = bytes(b)
    h, body = save_model(header, d, base)
    return h + body


T_JOINT_BSPHERES = 0x0AD3A708   # ModelJointBspheres: 16 B header (u32 count, 12 B 0), then 20 B per entry: f32 centre xyz,
                                # f32 radius, u32 joint * 64 (wf2 head-path survey)


def set_joint_bsphere_radius(raw, radius):
    """raise every ModelJointBspheres radius to >= radius (same length). The runtime bounding sphere of an animated model
    instance is rebuilt from these each frame (ModelBuilt's is not used for it), and AnimDynamics step only while
    camera distance < radius * AnimDynamicsUpdateMultiplier (default 50) unless the AnimController has NeverCull
    (wf2 2026-10-13: gate at 0x1428e256a; test_i20_Head's 0.5 / 0.7 mm spheres froze the T19 / T20 chains)."""
    m = M.Model(raw)
    hl = 8 + raw[5] * 8 + struct.unpack_from('<H', raw, 6)[0]
    o, _ = m.sec_off(T_JOINT_BSPHERES)
    b = bytearray(raw)
    n, = struct.unpack_from('<I', b, hl + o)
    for i in range(n):
        p = hl + o + 16 + 20 * i + 12
        struct.pack_into('<f', b, p, max(struct.unpack_from('<f', b, p)[0], radius))
    return bytes(b)

