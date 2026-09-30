"""Offline verification of a built PSARC: structure, capacities, hiding, textured and posed renders.

    python verify.py BUILT.psarc [--reference OLD_MOD.psarc] [--game DIR] [--renders DIR]
"""
import argparse
import os
import sys

import numpy as np
import texture2ddecoder as t2d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_karin import ALL_RANKS, GAME_DEFAULT, HIDE_MESHES, ROLES  # noqa: E402
from gotarc import Psarc  # noqa: E402
from gotfmt import (FMT_U8X4, HIDE_SCALE, Xmesh, Xpps, decode_record, mip_sizes, quat_to_mat,  # noqa: E402
                    sps_header)
from render import render_mesh  # noqa: E402

DEC = {'BC1': t2d.decode_bc1, 'BC3': t2d.decode_bc3, 'BC4': t2d.decode_bc4, 'BC5': t2d.decode_bc5,
       'BC7': t2d.decode_bc7}


def decode_top(data):
    h = sps_header(data)
    sz = mip_sizes(h['kind'], h['w'], h['h'], 1)[0]
    raw = DEC[h['kind']](data[h['data_offset']:h['data_offset'] + sz], h['w'], h['h'])
    return np.frombuffer(raw, 'u1').reshape(h['h'], h['w'], 4)[:, :, [2, 1, 0, 3]]


def posed_world(sk, edits):
    """edits: {bone: 3x3 local rotation applied after bind rotation}."""
    n = sk['num']
    world = [None] * n

    def get(i):
        if world[i] is None:
            m = np.eye(4)
            R = quat_to_mat(sk['rot'][i])
            if i in edits:
                R = R @ edits[i]
            m[:3, :3] = R * sk['scl'][i][None, :]
            m[:3, 3] = sk['pos'][i]
            p = sk['parents'][i]
            world[i] = m if p == -1 else get(p) @ m
        return world[i]

    for i in range(n):
        get(i)
    return np.array(world)


def axis_rot(axis, deg):
    a = np.asarray(axis, float)
    a /= np.linalg.norm(a)
    t = np.radians(deg)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + np.sin(t) * K + (1 - np.cos(t)) * K @ K


def world_axis_edit(bind_world, bone, axis, deg):
    """Rotation about a world axis expressed in the bone's local frame."""
    R = bind_world[bone][:3, :3]
    R = R / np.linalg.norm(R, axis=0)
    return R.T @ axis_rot(axis, deg) @ R


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('psarc')
    ap.add_argument('--reference')
    ap.add_argument('--game', default=GAME_DEFAULT, help='game folder; default: GOT_GAME_DIR')
    ap.add_argument('--renders', default=None)
    args = ap.parse_args()
    if not args.game or not os.path.isdir(os.path.join(args.game, 'cache_pc', 'psarc')):
        ap.error('--game (or GOT_GAME_DIR) must be the game folder containing cache_pc\\psarc')
    out_dir = args.renders or os.path.join(os.path.dirname(os.path.abspath(args.psarc)), 'renders')
    os.makedirs(out_dir, exist_ok=True)
    a = Psarc(args.psarc)
    names = list(a.files)
    problems = []
    # container contract (vanilla + working v1.0): only the manifest may be zlib; file data stored raw,
    # files >= 64 KiB start on an 8192-byte boundary
    for i, (_md5, blk, usize, off) in enumerate(a.entries):
        stored = 0
        for b in range(blk, blk + (usize + 0xFFFF) // 0x10000):
            stored += a.blocksizes[b] or a.blksz
        if i > 0 and stored != usize:
            problems.append(f'entry {i} data is compressed ({stored} stored for {usize})')
        if i > 0 and usize >= 0x10000 and off % 8192:
            problems.append(f'entry {i} not 8192-aligned (offset {off})')
    print('files', len(names))
    if args.reference:
        ref = set(Psarc(args.reference).files)
        print('same file set as reference:', ref == set(names), 'missing:', sorted(ref - set(names))[:5],
              'extra:', sorted(set(names) - ref)[:5])
        if ref != set(names):
            problems.append('file set differs from reference')
    arc_dir = os.path.join(args.game, 'cache_pc', 'psarc')
    van = Psarc(os.path.join(arc_dir, 'gapack_misc_h.psarc'))
    vans = [van] + [Psarc(os.path.join(arc_dir, f'{n}.psarc')) for n in ('gapack_meshes', 'gapack_bitmaps_h_armor_0')]
    for n in names:
        va = next((v for v in vans if n in v.files), None)
        if va is None:
            problems.append(f'{n} has no vanilla counterpart')
        elif va.files[n][2] != a.files[n][2]:
            problems.append(f'{n} size {a.files[n][2]} != vanilla {va.files[n][2]}')
    vxp = Xpps(van.extract('/hero.xpps'))
    xp = Xpps(a.extract('/hero.xpps'))
    sk = xp.skeleton(0)
    if len(xp.data) != len(vxp.data):
        problems.append(f'xpps size {len(xp.data)} != vanilla {len(vxp.data)}')
        diff = np.array([True])
    else:
        diff = np.frombuffer(bytes(xp.data), 'u1') != np.frombuffer(bytes(vxp.data), 'u1')
    print('xpps bytes changed', int(diff.sum()), 'same size', len(xp.data) == len(vxp.data))
    for role, (_, hs) in ROLES.items():
        if any(xp.mesh(h).textures != xp.mesh(hs[0]).textures for h in hs):
            problems.append(f'role {role} parts do not share textures')
    # all-ranks
    xm = Xmesh(a.extract(ALL_RANKS))
    slot_hashes = {h: role for role, (_, hs) in ROLES.items() for h in hs}
    meshes = []
    tex = {}
    for role, (mtl, _hs) in ROLES.items():
        dn = [n for n in names if n.startswith(f'/bitmaps/{mtl}.msac.d.')]
        tex[role] = decode_top(a.extract(dn[0]))
    all_bones = []
    for r in xm.records:
        m = xp.mesh(r.hash)
        d = decode_record(xm, r, m)
        t = d['tris']
        live = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
        if r.hash in slot_hashes:
            if m.asset != 0:
                problems.append(f'slot {r.hash:016x} not in asset 0 (asset {m.asset})')
            if len(live) == 0:
                if abs(m.scale - HIDE_SCALE) > 1e-12:
                    problems.append(f'unused slot {r.hash:016x} not hidden')
                print(f'  (unused slot {r.hash:016x}, hidden)')
                continue
            used = np.unique(live)
            P = d['pos']
            vm = vxp.mesh(r.hash)
            if m.bbox_min != vm.bbox_min or m.bbox_max != vm.bbox_max:
                problems.append(f'bbox of {r.hash:016x} changed (must stay vanilla like v1.0)')
            b = d['bones'][used]
            if b.min() < -1 or b.max() > 654 or (b[:, 0] < 0).any():
                problems.append(f'bone indices out of range {r.hash:016x}')
            u8 = [(ai, stride) for ai, (fmt, stride, _c) in enumerate(m.attrs) if fmt == FMT_U8X4]
            if not u8:
                problems.append(f'no U8X4 weight stream {r.hash:016x}')
            else:
                ai, stride = u8[-1]
                raw = xm.attr(r, ai, stride, m.vertex_count)[used, :3].astype(np.int64)
                if (raw.sum(1) > 255).any():
                    problems.append(f'raw weights w1+w2+w3 > 255 {r.hash:016x}')
            role = slot_hashes[r.hash]
            img = tex[role]
            uv = d['uvs'][0][live].mean(1)
            px = np.clip((uv * [img.shape[1], img.shape[0]]).astype(int), 0, [img.shape[1] - 1, img.shape[0] - 1])
            cols = img[px[:, 1], px[:, 0], :3].astype(float)
            meshes.append(dict(pos=P, tris=live, cols=cols, bones=d['bones'], weights=d['weights']))
            all_bones.append(np.unique(d['bones'][used][d['weights'][used] > 0]))
            print(f'  {role:8s} {r.hash:016x} tris {len(live):6d} verts {len(used):6d}/{m.vertex_count}')
        else:
            if len(live):
                problems.append(f'record {r.hash:016x} should be hidden but has {len(live)} tris')
            if abs(m.scale - HIDE_SCALE) > 1e-12:
                problems.append(f'record {r.hash:016x} scale not hidden')
    print('bones used', len(np.unique(np.concatenate(all_bones))))
    for n in HIDE_MESHES:
        x = Xmesh(a.extract(f'/meshes/{n}.xmesh'))
        if any(x.data[x.buf:]):
            problems.append(f'{n} not fully cleared')
        for r in x.records:
            for m in xp.by_hash.get(r.hash, []):
                if m.scale != HIDE_SCALE:
                    problems.append(f'{n} record {r.hash:016x} scale not hidden')
    for n in names:
        if n.startswith('/bitmaps/'):
            d = a.extract(n)
            h = sps_header(d)
            if len(d) != h['data_offset'] + sum(mip_sizes(h['kind'], h['w'], h['h'], h['mips'])):
                problems.append(f'{n} size mismatch')
    print('PROBLEMS:', problems or 'none')

    # renders
    bind = np.array(posed_world(sk, {}))
    lo = np.array([-60, -95, -2.0])
    hi = np.array([60, 95, 212.0])
    rm = [(m['pos'], m['tris'], m['cols']) for m in meshes]
    render_mesh(rm, os.path.join(out_dir, 'bind_textured.png'), W=520, H=900, bounds=(lo, hi),
                views=((1, 2, 1), (0, 2, 1), (1, 2, -1)))
    inv_bind = np.linalg.inv(bind)
    down = {499: world_axis_edit(bind, 499, (1, 0, 0), -75), 546: world_axis_edit(bind, 546, (1, 0, 0), 75),
            505: world_axis_edit(bind, 505, (0, 0, 1), -40), 553: world_axis_edit(bind, 553, (0, 0, 1), 40)}
    twist = dict(down)
    for b, f in ((508, 0.3), (509, 0.6), (510, 0.85), (513, 1.0)):
        twist[b] = world_axis_edit(bind, b, (0, 1, 0), 90 * f)
    for b, f in ((556, 0.3), (557, 0.6), (558, 0.85), (561, 1.0)):
        twist[b] = world_axis_edit(bind, b, (0, 1, 0), 90 * f)
    poses = {
        'arms_down': down,
        'wrist_twist': twist,
        'walk': {**down, 595: world_axis_edit(bind, 595, (0, 1, 0), -45), 596: world_axis_edit(bind, 596, (0, 1, 0), 70),
                 616: world_axis_edit(bind, 616, (0, 1, 0), 25), 7: world_axis_edit(bind, 7, (0, 0, 1), 15),
                 10: world_axis_edit(bind, 10, (0, 1, 0), 10), 17: world_axis_edit(bind, 17, (0, 0, 1), 30)},
        'ride': {595: world_axis_edit(bind, 595, (0, 1, 0), -70) @ world_axis_edit(bind, 595, (1, 0, 0), 25),
                 616: world_axis_edit(bind, 616, (0, 1, 0), -70) @ world_axis_edit(bind, 616, (1, 0, 0), -25),
                 596: world_axis_edit(bind, 596, (0, 1, 0), 80), 617: world_axis_edit(bind, 617, (0, 1, 0), 80),
                 499: world_axis_edit(bind, 499, (1, 0, 0), -60) @ world_axis_edit(bind, 499, (0, 0, 1), -40),
                 546: world_axis_edit(bind, 546, (1, 0, 0), 60) @ world_axis_edit(bind, 546, (0, 0, 1), 40),
                 505: world_axis_edit(bind, 505, (0, 0, 1), -70), 553: world_axis_edit(bind, 553, (0, 0, 1), 70)},
    }
    for pname, edits in poses.items():
        W = posed_world(sk, edits)
        skin = W @ inv_bind
        pm = []
        for m in meshes:
            P = np.concatenate([m['pos'], np.ones((len(m['pos']), 1))], 1)
            b = np.where(m['bones'] >= 0, m['bones'], 0)
            M = np.einsum('vk,vkij->vij', m['weights'], skin[b])
            pm.append((np.einsum('vij,vj->vi', M, P)[:, :3], m['tris'], m['cols']))
        allp = np.concatenate([p[0] for p in pm])
        render_mesh(pm, os.path.join(out_dir, f'pose_{pname}.png'), W=520, H=900,
                    bounds=(allp.min(0) - 5, allp.max(0) + 5), views=((1, 2, 1), (0, 2, 1)))
    print('renders in', out_dir)
    return 1 if problems else 0


if __name__ == '__main__':
    sys.exit(main())
