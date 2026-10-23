# hair_override_patch.py <in.uasset> <out.uasset>
# Points every MeshOverrides[].Mesh of a hair CharacterPiece (hood-up / hat-type variants) at its DefaultMesh,
# so the replaced hair is shown under hoods and hats too. Same-size edit of the ObjectProperty values in the .uexp.
import argparse, struct, sys, shutil
ap = argparse.ArgumentParser(description='point every MeshOverrides[].Mesh of a hair CharacterPiece DA at its DefaultMesh')
ap.add_argument('src'); ap.add_argument('dst')
args = ap.parse_args()
src, dst = args.src, args.dst
ua = open(src, 'rb').read(); ue = bytearray(open(src[:-7] + '.uexp', 'rb').read())
p = 0
def i32():
    global p; v = struct.unpack_from('<i', ua, p)[0]; p += 4; return v
def fstr():
    global p; n = i32()
    if n == 0: return ''
    if n < 0: s = ua[p:p - n * 2].decode('utf-16le'); p += -n * 2; return s[:-1]
    s = ua[p:p + n].decode('latin1'); p += n; return s[:-1]
i32(); i32(); i32(); i32(); i32()  # tag, legacy ver, UE3 ver, UE4 ver, licensee
ncv = i32(); p += 20 * ncv           # custom versions
i32(); fstr(); i32()                # total header size, folder, package flags
ncount = i32(); p = i32()
names = []
for _ in range(ncount): names.append(fstr()); p += 4
def tag(name):  # FPropertyTag of a non-array ObjectProperty: Name, Type, Size=4, ArrayIndex=0, HasGuid=0
    return struct.pack('<iiiiiib', names.index(name), 0, names.index('ObjectProperty'), 0, 4, 0, 0)
def find_all(pat):
    out, i = [], ue.find(pat)
    while i >= 0: out.append(i + len(pat)); i = ue.find(pat, i + 1)
    return out
dm = find_all(tag('DefaultMesh')); assert len(dm) == 1, dm
default = struct.unpack_from('<i', ue, dm[0])[0]
hits = find_all(tag('Mesh'))
for off in hits:
    old = struct.unpack_from('<i', ue, off)[0]; struct.pack_into('<i', ue, off, default)
    print(f'Mesh @{off}: {old} -> {default}')
assert hits, 'no MeshOverrides'
shutil.copyfile(src, dst); open(dst[:-7] + '.uexp', 'wb').write(ue)
