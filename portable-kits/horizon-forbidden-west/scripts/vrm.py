"""Minimal VRM 1.0 / glTF binary loader (numpy)."""
import io
import json
import struct

import numpy as np
from PIL import Image

CTYPE = {5120: 'i1', 5121: 'u1', 5122: '<i2', 5123: '<u2', 5125: '<u4', 5126: '<f4'}
NCOMP = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
THUMB_V0 = {'ThumbProximal': 'ThumbMetacarpal', 'ThumbIntermediate': 'ThumbProximal'}   # VRM 0.x -> 1.0


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


class Vrm:
    def __init__(self, path):
        d = open(path, 'rb').read()
        jl = struct.unpack_from('<I', d, 12)[0]
        self.js = js = json.loads(d[20:20 + jl])
        bo = 20 + jl
        bl = struct.unpack_from('<I', d, bo)[0]
        self.bin = d[bo + 8:bo + 8 + bl]
        self.nodes = js['nodes']
        n = len(self.nodes)
        self.parent = [-1] * n
        for i, nd in enumerate(self.nodes):
            for c in nd.get('children', []):
                self.parent[c] = i
        self.local = []
        for nd in self.nodes:
            m = np.eye(4)
            if 'matrix' in nd:
                m = np.array(nd['matrix']).reshape(4, 4).T
            else:
                t = nd.get('translation', [0, 0, 0])
                r = nd.get('rotation', [0, 0, 0, 1])
                s = nd.get('scale', [1, 1, 1])
                m[:3, :3] = quat_to_mat(r) * np.array(s)[None, :]
                m[:3, 3] = t
            self.local.append(m)
        self.world = [None] * n
        for i in range(n):
            self._world(i)
        self.world = np.array(self.world)
        self.names = [nd.get('name', f'node{i}') for i, nd in enumerate(self.nodes)]
        ext = js.get('extensions', {})
        if 'VRMC_vrm' in ext:
            hb = ext['VRMC_vrm']['humanoid']['humanBones']
            self.human = {k: v['node'] for k, v in hb.items()}
        else:
            # VRM 0.x: a bone list whose thumb names sit one joint further out than VRM 1.0, and the model
            # faces -Z; turn it 180 degrees about y so everything downstream sees the VRM 1.0 frame
            self.human = {}
            for b in ext['VRM']['humanoid']['humanBones']:
                name = b['bone']
                for old, new in THUMB_V0.items():
                    if name.endswith(old):
                        name = name[:-len(old)] + new
                self.human[name] = b['node']
            self.world = np.diag([-1.0, 1.0, -1.0, 1.0]) @ self.world
        self.node_human = {v: k for k, v in self.human.items()}

    def _world(self, i):
        if self.world[i] is not None:
            return self.world[i]
        p = self.parent[i]
        w = self.local[i] if p < 0 else self._world(p) @ self.local[i]
        self.world[i] = w
        return w

    def _view(self, bv_idx, byte_offset, dt, nc, cnt):
        bv = self.js['bufferViews'][bv_idx]
        off = bv.get('byteOffset', 0) + byte_offset
        stride = bv.get('byteStride', 0) or dt.itemsize * nc
        if stride == dt.itemsize * nc:
            return np.frombuffer(self.bin, dt, cnt * nc, off).reshape(cnt, nc)
        raw = np.frombuffer(self.bin, 'u1', stride * (cnt - 1) + dt.itemsize * nc, off)
        return np.lib.stride_tricks.as_strided(raw, (cnt, dt.itemsize * nc), (stride, 1)).copy().view(dt).reshape(cnt, nc)

    def accessor(self, idx):
        a = self.js['accessors'][idx]
        dt = np.dtype(CTYPE[a['componentType']])
        nc = NCOMP[a['type']]
        cnt = a['count']
        if 'bufferView' in a:
            arr = self._view(a['bufferView'], a.get('byteOffset', 0), dt, nc, cnt)
        else:
            arr = np.zeros((cnt, nc), dt)
        arr = arr.astype(np.float64) if dt.kind == 'f' else arr.copy()
        if 'sparse' in a:   # e.g. morph targets: only the moved vertices are stored
            sp = a['sparse']
            ii, vv = sp['indices'], sp['values']
            ind = self._view(ii['bufferView'], ii.get('byteOffset', 0), np.dtype(CTYPE[ii['componentType']]), 1,
                             sp['count']).ravel().astype(np.int64)
            arr[ind] = self._view(vv['bufferView'], vv.get('byteOffset', 0), dt, nc, sp['count'])
        if a.get('normalized') and dt.kind in 'ui':
            arr = arr.astype(np.float64) / np.iinfo(dt).max
            if dt.kind == 'i':   # glTF: signed normalized values clamp at -1 (e.g. -128 / 127)
                arr = np.maximum(arr, -1.0)
        return arr

    def image(self, idx):
        im = self.js['images'][idx]
        bv = self.js['bufferViews'][im['bufferView']]
        raw = self.bin[bv.get('byteOffset', 0):bv.get('byteOffset', 0) + bv['byteLength']]
        img = Image.open(io.BytesIO(raw))
        img.load()
        return img

    def mesh_nodes(self):
        return [(i, nd) for i, nd in enumerate(self.nodes) if 'mesh' in nd]

    def primitives(self):
        """Yield dicts with bind-pose world positions (skinned rest), normals, uv, joints(node ids), weights."""
        out = []
        for ni, nd in self.mesh_nodes():
            mesh = self.js['meshes'][nd['mesh']]
            skin = self.js['skins'][nd['skin']] if 'skin' in nd else None
            if skin:
                joints = skin['joints']
                ibm = self.accessor(skin['inverseBindMatrices']).reshape(-1, 4, 4).transpose(0, 2, 1)
                skin_mats = np.array([self.world[j] @ ibm[k] for k, j in enumerate(joints)])
            for pi, pr in enumerate(mesh['primitives']):
                at = pr['attributes']
                P = self.accessor(at['POSITION'])
                N = self.accessor(at['NORMAL']) if 'NORMAL' in at else None
                UV = self.accessor(at['TEXCOORD_0']) if 'TEXCOORD_0' in at else None
                idx = self.accessor(pr['indices']).ravel().astype(np.int64)
                rec = dict(node=ni, mesh=mesh.get('name'), prim=pi, material=pr.get('material'),
                           mat_name=self.js['materials'][pr['material']]['name'] if 'material' in pr else None,
                           tris=idx.reshape(-1, 3), uv=UV)
                if skin:
                    J = self.accessor(at['JOINTS_0']).astype(np.int64)
                    W = self.accessor(at['WEIGHTS_0'])
                    ws = W.sum(1, keepdims=True)
                    ws[ws == 0] = 1
                    W = W / ws
                    # skin to bind (should be identity-ish for rest pose, but apply for correctness)
                    M = np.einsum('vk,vkij->vij', W, skin_mats[J])
                    Ph = np.concatenate([P, np.ones((len(P), 1))], 1)
                    rec['pos'] = np.einsum('vij,vj->vi', M, Ph)[:, :3]
                    if N is not None:
                        Nit = np.linalg.inv(M[:, :3, :3]).transpose(0, 2, 1)
                        Nn = np.einsum('vij,vj->vi', Nit, N)
                        rec['normal'] = Nn / np.linalg.norm(Nn, axis=1, keepdims=True).clip(1e-12)
                    rec['joints'] = np.array(joints)[J]
                    rec['weights'] = W
                else:
                    M = self.world[ni]
                    rec['pos'] = (np.concatenate([P, np.ones((len(P), 1))], 1) @ M.T)[:, :3]
                    if N is not None:
                        Nit = np.linalg.inv(M[:3, :3]).T
                        Nn = N @ Nit.T
                        rec['normal'] = Nn / np.linalg.norm(Nn, axis=1, keepdims=True).clip(1e-12)
                    rec['joints'] = np.full((len(P), 4), ni)
                    rec['weights'] = np.tile([1.0, 0, 0, 0], (len(P), 1))
                out.append(rec)
        return out
