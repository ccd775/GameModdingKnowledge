"""Clear the CET-compatible bit of .NET SDK apphosts on Windows builds without the CET kernel fix.

Windows 10 19044 without that fix refuses .NET 10 SDK tools (csc.exe, VBCSCompiler.exe, MSBuild.exe apphosts) with
"Your Windows doesn't fully support CET". This clears bit 0 of the IMAGE_DEBUG_TYPE_EX_DLLCHARACTERISTICS entry (type
20) in the PE debug directory of each given exe and keeps the original as <exe>.cet.bak. Use it only on a private copy
of the SDK, never on a system-wide dotnet.

usage: python clear_cet_flag.py <exe> [<exe> ...]
"""
import argparse
import struct, sys, shutil
def clear(path):
    b = bytearray(open(path,'rb').read())
    pe = struct.unpack_from('<I', b, 0x3c)[0]
    assert b[pe:pe+4] == b'PE\0\0'
    nsec = struct.unpack_from('<H', b, pe+6)[0]
    optsz = struct.unpack_from('<H', b, pe+20)[0]
    opt = pe+24
    magic = struct.unpack_from('<H', b, opt)[0]
    ddir = opt + (112 if magic == 0x20b else 96)
    dbg_rva, dbg_size = struct.unpack_from('<II', b, ddir + 6*8)
    secs = opt + optsz
    def rva2off(rva):
        for i in range(nsec):
            s = secs + i*40
            vs, va, rs, raw = struct.unpack_from('<IIII', b, s+8)
            if va <= rva < va + max(vs, rs):
                return rva - va + raw
        raise ValueError(rva)
    off = rva2off(dbg_rva)
    changed = 0
    for i in range(dbg_size // 28):
        e = off + i*28
        typ = struct.unpack_from('<I', b, e+12)[0]
        if typ == 20:
            ptr = struct.unpack_from('<I', b, e+24)[0]
            val = struct.unpack_from('<I', b, ptr)[0]
            print(path, 'EX_DLLCHARACTERISTICS', hex(val))
            if val & 1:
                struct.pack_into('<I', b, ptr, val & ~1); changed += 1
    if changed:
        shutil.copy2(path, path + '.cet.bak')
        open(path,'wb').write(b)
    print('changed', changed)
if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Clear the CET-compatible bit of PE files (keeps <exe>.cet.bak).")
    ap.add_argument("exe", nargs="+", help="apphost exe of a private .NET SDK copy")
    for p in ap.parse_args().exe: clear(p)
