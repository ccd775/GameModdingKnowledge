"""Compile HLSL files as cs_5_0 with the Mod Enabler's d3dcompiler_46.dll (what 3DMigoto uses at runtime).
usage: c46.py <d3dcompiler_46.dll> <file.hlsl> ..."""
import ctypes, sys
from ctypes import c_void_p, c_char_p, c_size_t, c_uint, POINTER, byref
import argparse
ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
ap.add_argument('dll', metavar='d3dcompiler_46.dll'); ap.add_argument('files', nargs='+', metavar='file.hlsl')
args = ap.parse_args()
dll = ctypes.WinDLL(args.dll)
D3DCompile = dll.D3DCompile
D3DCompile.argtypes = [c_void_p, c_size_t, c_char_p, c_void_p, c_void_p, c_char_p, c_char_p, c_uint, c_uint,
                       POINTER(c_void_p), POINTER(c_void_p)]
class Blob(ctypes.Structure):
    pass
def blob_text(p):
    if not p:
        return ''
    vt = ctypes.cast(p, POINTER(POINTER(c_void_p))).contents
    get_ptr = ctypes.WINFUNCTYPE(c_void_p, c_void_p)(vt[3]); get_size = ctypes.WINFUNCTYPE(c_size_t, c_void_p)(vt[4])
    return ctypes.string_at(get_ptr(p), get_size(p)).decode('utf-8', 'replace')
ok = True
for f in args.files:
    src = open(f, 'rb').read()
    code, err = c_void_p(), c_void_p()
    hr = D3DCompile(src, len(src), f.encode(), None, None, b'main', b'cs_5_0', 1 << 15, 0, byref(code), byref(err))
    msg = blob_text(err.value).strip()
    print(f'{f}: {"OK" if hr == 0 else "FAIL 0x%08x" % (hr & 0xffffffff)}' + (f'\n  {msg[:600]}' if msg else ''))
    ok &= hr == 0
sys.exit(0 if ok else 1)
