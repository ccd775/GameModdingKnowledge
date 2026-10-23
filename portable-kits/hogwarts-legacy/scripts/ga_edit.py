# ga_edit.py <in.uasset> <out.uasset> <remove_key> [...]
# Remove entries from the OutfitItems map of a cooked UE4.27 (legacy, tagged-property) GearAppearanceItemDefinition.
# Fixes the MapProperty tag size, the export SerialSize/SerialOffset and BulkDataStartOffset. Writes .uasset + .uexp.
import argparse, struct, sys, os

ap = argparse.ArgumentParser(description='remove entries from the OutfitItems map of a cooked GearAppearance DA')
ap.add_argument('src'); ap.add_argument('dst'); ap.add_argument('remove_key', nargs='*', help='OutfitItems keys to drop')
args = ap.parse_args()
src, dst, remove = args.src, args.dst, set(args.remove_key)
ua = bytearray(open(src, 'rb').read()); ue = bytearray(open(os.path.splitext(src)[0] + '.uexp', 'rb').read())

# ---- summary
o = 0
tag, lfv = struct.unpack_from('<Ii', ua, o); o += 8
if lfv != -4: o += 4
o += 8
ncv = struct.unpack_from('<i', ua, o)[0]; o += 4 + ncv * 20
total_header = struct.unpack_from('<i', ua, o)[0]; o += 4
l = struct.unpack_from('<i', ua, o)[0]; o += 4 + (l if l >= 0 else -2 * l)
flags = struct.unpack_from('<I', ua, o)[0]; o += 4
name_count, name_off = struct.unpack_from('<ii', ua, o); o += 8
# (no LocalizationId for FilterEditorOnly packages)
o += 8  # gatherable text
export_count, export_off, import_count, import_off = struct.unpack_from('<iiii', ua, o)
names = []
p = name_off
for i in range(name_count):
    ln = struct.unpack_from('<i', ua, p)[0]; p += 4
    if ln >= 0: s = ua[p:p + ln - 1].decode('latin1'); p += ln
    else: s = ua[p:p - 2 * ln - 2].decode('utf-16le'); p += -2 * ln
    p += 4  # hashes
    names.append(s)
NONE = names.index('None')
def nm(b, off):
    i, n = struct.unpack_from('<ii', b, off); return names[i] + ('' if n == 0 else f'_{n - 1}')

# ---- tagged property walker (on uexp)
def read_tag(b, off):
    name = nm(b, off); off += 8
    if name == 'None': return None, off
    typ = nm(b, off); off += 8
    size, aidx = struct.unpack_from('<ii', b, off); off += 8
    extra = {}
    if typ == 'StructProperty': extra['struct'] = nm(b, off); off += 8 + 16
    elif typ == 'BoolProperty': off += 1
    elif typ in ('ByteProperty', 'EnumProperty'): off += 8
    elif typ in ('ArrayProperty', 'SetProperty'): extra['inner'] = nm(b, off); off += 8
    elif typ == 'MapProperty': extra['key'] = nm(b, off); extra['val'] = nm(b, off + 8); off += 16
    hasguid = b[off]; off += 1
    if hasguid: off += 16
    return dict(name=name, type=typ, size=size, extra=extra, value_off=off), off + size
def skip_struct(b, off):
    while True:
        t, off = read_tag(b, off)
        if t is None: return off

# exports: assume a single export (the data asset) in the uexp
ex_size_off = export_off + 28; ex_offs_off = export_off + 36
serial_size, serial_off = struct.unpack_from('<qq', ua, ex_size_off)
start = serial_off - total_header
off = start; found = None
while True:
    t, nxt = read_tag(ue, off)
    if t is None: break
    if t['name'] == 'OutfitItems': found = (off, t)
    off = nxt
assert found, 'OutfitItems not found'
tag_off, t = found
assert t['extra']['key'] == 'NameProperty' and t['extra']['val'] == 'StructProperty', t
v = t['value_off']
nrem, = struct.unpack_from('<i', ue, v); assert nrem == 0
num, = struct.unpack_from('<i', ue, v + 4)
entries = []; q = v + 8
for i in range(num):
    k = nm(ue, q); e0 = q; q = skip_struct(ue, q + 8); entries.append((k, e0, q))
print('entries', [e[0] for e in entries])
keep = [e for e in entries if e[0] not in remove]
body = b''.join(bytes(ue[e[1]:e[2]]) for e in keep)
newval = struct.pack('<ii', 0, len(keep)) + body
delta = len(newval) - t['size']
# tag size field is located at tag_off + 16
struct.pack_into('<i', ue, tag_off + 16, len(newval))
ue[v:v + t['size']] = newval
struct.pack_into('<q', ua, ex_size_off, serial_size + delta)
# BulkDataStartOffset: find the int64 == old value in the summary region before the name map
old_bdso = None
for i in range(0, name_off - 8):
    if struct.unpack_from('<q', ua, i)[0] == total_header + len(ue) - delta - 4 or struct.unpack_from('<q', ua, i)[0] == total_header + len(ue) - delta:
        old_bdso = (i, struct.unpack_from('<q', ua, i)[0]); break
if old_bdso: struct.pack_into('<q', ua, old_bdso[0], old_bdso[1] + delta)
print('removed', [e[0] for e in entries if e[0] in remove], 'delta', delta, 'bdso', old_bdso)
open(dst, 'wb').write(ua); open(os.path.splitext(dst)[0] + '.uexp', 'wb').write(ue)
