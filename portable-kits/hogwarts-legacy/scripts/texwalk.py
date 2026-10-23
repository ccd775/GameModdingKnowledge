# texwalk.py <uexp> <pf_name_offset> <header_size>: walk cooked FTexturePlatformData (UE4.27 layout)
import argparse, struct, sys
ap = argparse.ArgumentParser(description='walk cooked FTexturePlatformData (UE 4.27 layout) from a PF_ name offset')
ap.add_argument('uexp'); ap.add_argument('pf_name_offset', type=int); ap.add_argument('header_size', type=int)
args = ap.parse_args()
ue = open(args.uexp, 'rb').read(); p = args.pf_name_offset; hdr = args.header_size
def r(fmt):
    global p; v = struct.unpack_from(fmt, ue, p); p += struct.calcsize(fmt); return v if len(v) > 1 else v[0]
print('fname', r('<ii')); skip = r('<q'); print('skip', skip, '-> uexp', skip - hdr)
print('size', r('<ii'), 'packed', hex(r('<I')))
n = r('<i'); print('pf', ue[p:p + n]); p += n
print('firstmip', r('<i')); nm = r('<i'); print('nmips', nm)
for i in range(nm):
    cooked = r('<i'); fl = r('<I'); cnt = r('<i'); sod = r('<i'); off = r('<q')
    inline = (fl & 0x40) or not (fl & 0x1)
    if not (fl & 0x1) and not (fl & 0x100):
        p += sod  # inline payload
    sx, sy, sz = r('<iii')
    print(' mip', i, 'cooked', cooked, 'flags', hex(fl), 'cnt', cnt, 'sod', sod, 'off', off, 'size', sx, sy, sz)
print('bIsVirtual @%d' % p, r('<i'))
print('pos after', p, 'skip(uexp)', skip - hdr, 'diff', p - (skip - hdr))
print('tail hex:', ue[p:p + 48].hex(' '))
print('end region:', ue[skip - hdr:].hex(' '))
