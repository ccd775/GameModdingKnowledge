import json, struct, numpy as np
CT = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
NC = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4, 'MAT4': 16}
class GLB:
    def __init__(self, path):
        d = open(path, 'rb').read()
        self.raw = d
        jl = struct.unpack_from('<I', d, 12)[0]
        self.json = json.loads(d[20:20 + jl])
        o = 20 + jl
        bl, bt = struct.unpack_from('<I4s', d, o)
        assert bt == b'BIN\0', bt
        self.bin_off = o + 8
        self.bin = bytearray(d[o + 8:o + 8 + bl])
    def acc_view(self, ai):
        a = self.json['accessors'][ai]
        bv = self.json['bufferViews'][a['bufferView']]
        n, nc = a['count'], NC[a['type']]
        dt = np.dtype(CT[a['componentType']])
        stride = bv.get('byteStride', dt.itemsize * nc)
        start = bv.get('byteOffset', 0) + a.get('byteOffset', 0)
        return a, bv, start, stride, n, nc, dt
    def read_sparse(self, ai):
        """(indices, values) of a sparse accessor without bufferView (implicit zeros elsewhere)."""
        a = self.json['accessors'][ai]; sp = a['sparse']; nc = NC[a['type']]
        iv = self.json['bufferViews'][sp['indices']['bufferView']]; vv = self.json['bufferViews'][sp['values']['bufferView']]
        idx = np.frombuffer(self.bin, CT[sp['indices']['componentType']], sp['count'], iv.get('byteOffset', 0) + sp['indices'].get('byteOffset', 0))
        val = np.frombuffer(self.bin, CT[a['componentType']], sp['count'] * nc, vv.get('byteOffset', 0) + sp['values'].get('byteOffset', 0)).reshape(-1, nc)
        return idx.astype(np.int64), val.copy()
    def read(self, ai):
        a = self.json['accessors'][ai]
        if 'bufferView' not in a:
            out = np.zeros((a['count'], NC[a['type']]), CT[a['componentType']])
            idx, val = self.read_sparse(ai); out[idx] = val
            return out
        a, bv, start, stride, n, nc, dt = self.acc_view(ai)
        assert 'sparse' not in a
        if stride == dt.itemsize * nc:
            return np.frombuffer(self.bin, dt, n * nc, start).reshape(n, nc).copy()
        return np.stack([np.frombuffer(self.bin, dt, nc, start + i * stride) for i in range(n)])
    def write(self, ai, arr):
        a, bv, start, stride, n, nc, dt = self.acc_view(ai)
        arr = np.ascontiguousarray(arr, dt).reshape(n, nc)
        assert stride == dt.itemsize * nc
        self.bin[start:start + arr.nbytes] = arr.tobytes()
    def save(self, path):
        d = bytearray(self.raw)
        d[self.bin_off:self.bin_off + len(self.bin)] = self.bin
        open(path, 'wb').write(bytes(d))
