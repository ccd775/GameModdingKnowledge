"""Minimal PE inspector: sections and imported DLL names (no third-party deps)."""
import argparse, struct
ap = argparse.ArgumentParser(description=__doc__); ap.add_argument('exe', help='PE file')
args = ap.parse_args()
d = open(args.exe, 'rb').read()
pe = struct.unpack_from('<I', d, 0x3C)[0]
nsec = struct.unpack_from('<H', d, pe + 6)[0]
optsz = struct.unpack_from('<H', d, pe + 20)[0]
opt = pe + 24
magic = struct.unpack_from('<H', d, opt)[0]
ep = struct.unpack_from('<I', d, opt + 16)[0]
ddir = opt + (112 if magic == 0x20b else 96)
imp_rva = struct.unpack_from('<I', d, ddir + 8)[0]
secs = []
for i in range(nsec):
    s = pe + 24 + optsz + i * 40
    name = d[s:s+8].rstrip(b'\0').decode('latin1')
    vsz, va, rsz, raw = struct.unpack_from('<4I', d, s + 8)
    ch = struct.unpack_from('<I', d, s + 36)[0]
    secs.append((name, va, vsz, raw, rsz, ch))
    print(f'{name:10s} va={va:#x} vsz={vsz:#x} raw={raw:#x} rsz={rsz:#x} ch={ch:#x}')
print('entry', hex(ep))
def off(rva):
    for n, va, vsz, raw, rsz, ch in secs:
        if va <= rva < va + max(vsz, rsz):
            return rva - va + raw
p = off(imp_rva)
while p is not None:
    oft, ts, fc, name_rva, ft = struct.unpack_from('<5I', d, p)
    if name_rva == 0: break
    o = off(name_rva); print('import', d[o:d.index(b'\0', o)].decode())
    p += 20
