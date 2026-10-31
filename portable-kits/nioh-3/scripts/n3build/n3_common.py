"""Shared helpers for the Nioh 3 Karin_Original build: paths, game skeletons, axis conversion, weight packing.

Nioh 3 G1M facts this build relies on (measured on v2.0.0.2, see PROJECT_STATE.md):
- joint palettes store the G1MS *storage index* (not the bone id); bone ids 0-24 = storage 0-24, ids 100.. follow.
- player skeleton bone ids: hips 2, thigh 3/4, knee 5/6, ankle 7/8, spine 9, chest 10, neck 11, head 12,
  clavicle 13/14, upper arm 15/16, elbow 17/18, wrist 19/20, toe 23/24; left hand fingers thumb 100-108-118,
  index 102-110-120, middle 104-112-122, ring 114-124-128, little 116-126-130 (right = +1). +X is the character's left,
  +Z forward, Y up, units cm, arms in a ~45 deg A pose.
"""
import json
import os
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import g1m_tool as gt  # noqa: E402

class BuildPath(os.PathLike):
    """<N3_BUILD>/<parts>. The build directory comes from the N3_BUILD environment variable, read when the path is
    used (joined paths stay lazy), so importing a build script and --help work without it."""

    def __init__(self, *parts):
        self._parts = parts

    def path(self):
        root = os.environ.get('N3_BUILD')
        if not root:
            raise SystemExit('N3_BUILD is not set: point it at the build directory (orig/, source/, face/, tex/, ...)')
        return Path(root).joinpath(*self._parts)

    def __truediv__(self, other):
        return BuildPath(*self._parts, other)

    def __fspath__(self):
        return os.fspath(self.path())

    def __str__(self):
        return str(self.path())

    def __getattr__(self, name):          # read_bytes, write_text, mkdir, glob, parent, ...
        if name.startswith('_'):
            raise AttributeError(name)
        return getattr(self.path(), name)


BUILD = BuildPath()
ORIG = BUILD / 'orig'
CHEST = '0x5548953f'          # ninja chest piece: carries all of Karin
BODY = '0x4ba258df'           # female base body: skeleton + skin-weight reference
# source shape keys applied on top of the prefab's mix, (name, z_keep, z_full): weight 0 at source z >= z_keep, 1 at
# z <= z_full, linear between. kisekae_UppeLeg 2 collapses the thigh skin inside the knee socks (rings z 0.42 / 0.45 /
# 0.48 / 0.523-0.525 m; the sock tops are level at 0.524). Applied whole (build22) it also pulled in the ring at the
# sock opening and the bare skin above narrowed into the sock like a cone; the mask keeps that ring where it is.
# 'kisekae_UppeLeg 1' is the bare skin above the socks and stays off.
EXTRA_SHAPE_KEYS = {'body_2': (('kisekae_UppeLeg 2', 0.515, 0.49),)}


def load_model(h):
    data = (ORIG / f'{h}.g1m').read_bytes()
    return data, gt.embedded_models(data)[-1]


def skeleton(model):
    """{bone id: {'storage', 'world' 4x4, 'pos', 'parent' (bone id or None)}}"""
    joints, by_id = gt.skeleton(model)
    st2id = {s: b for b, s in by_id.items()}
    out = {}
    for b, s in by_id.items():
        j = joints[s]
        out[b] = {'storage': s, 'world': np.array(j['world'], float), 'pos': np.array(j['world_p'], float),
                  'parent': st2id.get(j['parent']) if j['parent'] >= 0 else None}
    return out


def to_game_axes(p):
    """Blender world (Z up, facing -Y, left +X) -> game (Y up, facing +Z, left +X)."""
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2], -p[..., 1]], -1)


def load_source(src_dir=None):
    """source.json / source.npz, plus EXTRA_SHAPE_KEYS applied on top of the prefab's key mix, masked by height (deltas
    from blender_shapekeys.py are relative to Basis, so they add)."""
    src_dir = Path(src_dir or BUILD / 'source')
    meta = json.loads((src_dir / 'source.json').read_text(encoding='utf-8'))
    arr = dict(np.load(src_dir / 'source.npz'))
    if EXTRA_SHAPE_KEYS:
        info = json.loads((src_dir / 'shapekeys.json').read_text(encoding='utf-8'))
        deltas = np.load(src_dir / 'shapekeys.npz')
        for m in meta['meshes']:
            for name, z_keep, z_full in EXTRA_SHAPE_KEYS.get(m['name'], ()):
                assert name not in dict(m['shape_keys_applied']), f'{m["name"]}: {name} already applied'
                i = next(k['index'] for k in info[m['name']] if k['name'] == name)
                co = arr[m['key'] + '__co']
                w = np.clip((z_keep - co[:, 2]) / (z_keep - z_full), 0, 1)[:, None]
                arr[m['key'] + '__co'] = (co + w * deltas[f'{m["name"]}__{i}']).astype(co.dtype)
                m['shape_keys_applied'].append([name, f'z mask {z_keep} -> {z_full}'])
    return meta, arr


def pack_weights(d, k=8, step=2 ** -11):
    """dict bone->weight -> (ids[k], weights[k]) sorted desc, quantised to `step`, summing exactly to 1."""
    items = sorted(((b, w) for b, w in d.items() if w > 0), key=lambda x: -x[1])[:k]
    tot = sum(w for _, w in items)
    q = [int(round(w / tot / step)) for _, w in items]
    q[0] += int(round(1 / step)) - sum(q)
    while q and q[-1] <= 0:
        q.pop(); items.pop()
        q[0] += int(round(1 / step)) - sum(q)
    ids = [b for b, _ in items] + [items[0][0]] * (k - len(items))
    ws = [x * step for x in q] + [0.0] * (k - len(q))
    return ids, ws
