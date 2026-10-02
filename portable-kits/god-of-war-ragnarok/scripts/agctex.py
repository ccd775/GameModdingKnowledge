"""Tile/detile PS5 (AGC) textures through the game's own libSceAgcTextureTool.dll.
The DLL is loaded on first use from the game folder (gamedir.py), so importing this module needs neither."""
import ctypes, os, struct
from gamedir import game_root
P = ctypes.c_void_p
_api = None


def _lib():
    """Load the DLL and bind its functions once (Windows only: the DLL ships with the game)."""
    global _api
    if _api is None:
        game = game_root()
        path = os.path.join(game, 'libSceAgcTextureTool.dll')
        if not os.path.isfile(path):
            raise SystemExit(f'{path} not found: texture tiling needs the DLL from the game folder')
        keep = os.add_dll_directory(game)
        dll = ctypes.WinDLL(path)
        def _f(name, res, *args):
            fn = getattr(dll, name); fn.restype = res; fn.argtypes = list(args); return fn
        _api = dict(
            keep=keep, dll=dll,
            ctor=_f('??0Texture@Agc@TextureTool@sce@@QEAA@XZ', P, P),
            initT=_f('?initializeWithTSharp@Texture@Agc@TextureTool@sce@@QEAAHPEBU1Core@24@PEAE@Z', ctypes.c_int, P, P, P),
            getDataSize=_f('?getDataSize@Texture@Agc@TextureTool@sce@@QEBA_KXZ', ctypes.c_uint64, P),
            getSize=_f('?getSize@Texture@Agc@TextureTool@sce@@QEBA_KXZ', ctypes.c_uint64, P),
            detile=_f('?detileRegion@Texture@Agc@TextureTool@sce@@QEBA?AW4Error@34@PEAE_KIIAEAUSurfaceRegion@AgcGpuAddress@4@@Z', ctypes.c_int, P, P, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, P),
            tile=_f('?tileRegion@Texture@Agc@TextureTool@sce@@QEAA?AW4Error@34@PEBE_KIIAEAUSurfaceRegion@AgcGpuAddress@4@@Z', ctypes.c_int, P, P, ctypes.c_uint64, ctypes.c_uint32, ctypes.c_uint32, P))
    return _api

class Region(ctypes.Structure):
    _fields_ = [('left', ctypes.c_uint32), ('top', ctypes.c_uint32), ('front', ctypes.c_uint32),
                ('right', ctypes.c_uint32), ('bottom', ctypes.c_uint32), ('back', ctypes.c_uint32)]

class AgcTexture:
    def __init__(self, tsharp, data_size=None):
        api = _lib()
        self.obj = ctypes.create_string_buffer(0x10000)
        api['ctor'](self.obj)
        self.ts = ctypes.create_string_buffer(bytes(tsharp), 64)
        self.buf = None
        self.tsharp = tsharp
        # dummy init to query size
        tmp = ctypes.create_string_buffer(16)
        r = api['initT'](self.obj, self.ts, tmp)
        self.init_result = r
        self.size = api['getSize'](self.obj)
        self.data_size = api['getDataSize'](self.obj)
    def attach(self, data=None):
        n = max(self.size, self.data_size)
        self.buf = ctypes.create_string_buffer(n)
        if data is not None:
            ctypes.memmove(self.buf, data, min(len(data), n))
        r = _lib()['initT'](self.obj, self.ts, self.buf)
        assert r == 0, r
        return self
    def detile(self, mip, w, h, bpe, block=4, slice_=0):
        bw = max(1, (w + block - 1)//block); bh = max(1, (h + block - 1)//block)
        out = ctypes.create_string_buffer(bw*bh*bpe)
        reg = Region(0, 0, 0, bw, bh, 1)
        r = _lib()['detile'](self.obj, out, len(out), slice_, mip, ctypes.byref(reg))
        return r, out.raw
    def tile(self, mip, w, h, bpe, src, block=4, slice_=0):
        bw = max(1, (w + block - 1)//block); bh = max(1, (h + block - 1)//block)
        reg = Region(0, 0, 0, bw, bh, 1)
        s = ctypes.create_string_buffer(bytes(src), len(src))
        r = _lib()['tile'](self.obj, s, len(src), slice_, mip, ctypes.byref(reg))
        return r
    def raw(self):
        return self.buf.raw[:self.data_size]

def parse_tsharp(t):
    w = struct.unpack_from('<8I', t, 0)
    fmt = (w[1] >> 20) & 0x1ff
    width = (((w[1] >> 30) & 3) | ((w[2] & 0xfff) << 2)) + 1
    height = ((w[2] >> 14) & 0x3fff) + 1
    dst = [(w[3] >> s) & 7 for s in (0, 3, 6, 9)]
    base_level = (w[3] >> 12) & 0xf; last_level = (w[3] >> 16) & 0xf
    sw = (w[3] >> 20) & 0x1f; typ = (w[3] >> 28) & 0xf
    return dict(words=w, fmt=fmt, width=width, height=height, dst=dst, base=base_level, last=last_level, sw=sw, type=typ)

def set_tsharp_dims(ts, width, height, last_level):
    w = list(struct.unpack_from('<8I', ts, 0))
    wm, hm = width - 1, height - 1
    w[1] = (w[1] & ~(3 << 30)) | ((wm & 3) << 30)
    w[2] = (w[2] & ~0xfff) | (wm >> 2)
    w[2] = (w[2] & ~(0x3fff << 14)) | (hm << 14)
    w[3] = (w[3] & ~(0xf << 16)) | (last_level << 16)
    return struct.pack('<8I', *[x & 0xffffffff for x in w]) + bytes(ts[32:])
