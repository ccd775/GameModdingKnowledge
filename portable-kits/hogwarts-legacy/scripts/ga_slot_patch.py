# ga_slot_patch.py <in.uasset> <out.uasset> <src_index> <dst_index...>
# GearAppearance OutfitItems: copy the CharacterPiece reference of entry <src_index> into the entries <dst_index...>
# (0-based, serialized order). Used to fill Socks/Shoes with the emptied Lower piece: removing those entries makes the
# game fall back to bare legs in the character's own skin. Same-size edit of ObjectProperty values in the .uexp.
import argparse, struct, sys, shutil
ap = argparse.ArgumentParser(description='copy the CharacterPiece ref of one OutfitItems entry into others (same-size edit)')
ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('src_index', type=int)
ap.add_argument('dst_index', type=int, nargs='*', help='0-based, serialized order')
args = ap.parse_args()
src, dst = args.src, args.dst; si = args.src_index; dis = args.dst_index
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
pat = struct.pack('<iiiiiib', names.index('CharacterPiece'), 0, names.index('ObjectProperty'), 0, 4, 0, 0)
offs, i = [], ue.find(pat)
while i >= 0: offs.append(i + len(pat)); i = ue.find(pat, i + 1)
vals = [struct.unpack_from('<i', ue, o)[0] for o in offs]
print('CharacterPiece refs', vals)
for d in dis:
    struct.pack_into('<i', ue, offs[d], vals[si]); print(f'entry {d}: {vals[d]} -> {vals[si]}')
shutil.copyfile(src, dst); open(dst[:-7] + '.uexp', 'wb').write(ue)
