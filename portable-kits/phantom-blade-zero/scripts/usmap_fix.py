"""usmap_fix.py <in.usmap> <out.usmap> [--dump regex]

Dumper-7 on Phantom Blade Zero picks FProperty::PropertyLinkNext (0x48) as FField::Next, so every struct's property list
is its whole PropertyLink chain (own + all inherited). This rewrites each struct to its own properties only: inherited
entries are removed by (name, type) against the cleaned lists of its ancestors, then schema indices are renumbered.
Writes an uncompressed usmap (version kept).
"""
import argparse, io, re, struct, sys

def rd(f, fmt):
    return struct.unpack('<' + fmt, f.read(struct.calcsize('<' + fmt)))

# EMappingsTypeFlags: 8 Array, 9 Struct, 24 Map, 25 Set, 26 Enum, 28 Optional
def read_type(f):
    t = f.read(1)[0]
    if t == 9:
        return (t, rd(f, 'i')[0])
    if t in (8, 25, 28):
        return (t, read_type(f))
    if t == 24:
        return (t, read_type(f), read_type(f))
    if t == 26:
        inner = read_type(f)
        return (t, inner, rd(f, 'i')[0])
    return (t,)

def write_type(o, ty):
    o.write(bytes([ty[0]]))
    t = ty[0]
    if t == 9: o.write(struct.pack('<i', ty[1]))
    elif t in (8, 25, 28): write_type(o, ty[1])
    elif t == 24: write_type(o, ty[1]); write_type(o, ty[2])
    elif t == 26: write_type(o, ty[1]); o.write(struct.pack('<i', ty[2]))

def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n\n', 1)[1], formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='usmap written by Dumper-7 (uncompressed or zstd)')
    ap.add_argument('dst', help='fixed usmap (uncompressed)')
    ap.add_argument('--dump', metavar='REGEX', help='print the cleaned property lists of matching structs')
    a = ap.parse_args()
    src, dst = a.src, a.dst
    dump = re.compile(a.dump) if a.dump else None
    raw = open(src, 'rb').read()
    f = io.BytesIO(raw)
    magic, ver = rd(f, 'HB')
    assert magic == 0x30C4, hex(magic)
    hasver = rd(f, 'i')[0] if ver >= 1 else 0
    assert hasver == 0, 'versioning block not supported'
    comp, csz, usz = rd(f, 'BII')
    body = f.read(csz)
    if comp == 3:
        import zstandard   # only zstd-compressed inputs need it
        body = zstandard.ZstdDecompressor().decompress(body, max_output_size=usz)
    elif comp != 0: raise SystemExit(f'compression {comp} not supported')
    b = io.BytesIO(body)
    nnames = rd(b, 'I')[0]
    names = []
    for _ in range(nnames):
        n = rd(b, 'H')[0] if ver >= 3 else b.read(1)[0]
        names.append(b.read(n).decode('utf-8', 'replace'))
    nenums = rd(b, 'I')[0]
    enums = []
    for _ in range(nenums):
        en = rd(b, 'i')[0]
        cnt = rd(b, 'H')[0] if ver >= 2 else b.read(1)[0]
        mem = [rd(b, 'Qi') for _ in range(cnt)] if ver >= 4 else [rd(b, 'i')[0] for _ in range(cnt)]
        enums.append((en, mem))
    nstructs = rd(b, 'I')[0]
    structs = {}
    order = []
    for _ in range(nstructs):
        sn, sup = rd(b, 'ii')
        pc, spc = rd(b, 'HH')
        props = []
        for _ in range(spc):
            idx, adim, pn = rd(b, 'HBi')
            props.append((adim, pn, read_type(b)))
        structs[sn] = (sup, props)
        order.append(sn)
    assert b.read() == b'', 'trailing data'
    byname = {names[k]: k for k in structs}

    own = {}
    def get_own(sn):
        if sn in own: return own[sn]
        sup, props = structs[sn]
        inherited = []
        s = sup
        while s != -1:
            key = s if s in structs else byname.get(names[s])
            if key is None: break
            inherited += get_own(key)
            s = structs[key][0]
        pool = {}
        for p in inherited: pool[(p[1], p[2])] = pool.get((p[1], p[2]), 0) + 1
        mine = []
        for p in props:
            k = (p[1], p[2])
            if pool.get(k, 0) > 0: pool[k] -= 1
            else: mine.append(p)
        missing = sum(pool.values())
        if missing: print(f'warn {names[sn]}: {missing} inherited props not found in its list')
        own[sn] = mine
        return mine
    removed = 0
    for sn in order:
        removed += len(structs[sn][1]) - len(get_own(sn))
    print(f'names {nnames} enums {nenums} structs {nstructs}; removed {removed} inherited entries')

    if dump:
        tn = dict(enumerate(['Byte','Bool','Int','Float','Object','Name','Delegate','Double','Array','Struct','Str','Text',
            'Interface','MulticastDelegate','WeakObject','LazyObject','AssetObject','SoftObject','UInt64','UInt32','UInt16',
            'Int64','Int16','Int8','Map','Set','Enum','FieldPath','Optional','Utf8Str','AnsiStr']))
        def tstr(ty):
            s = tn.get(ty[0], str(ty[0]))
            if ty[0] == 9: s += f'<{names[ty[1]]}>'
            elif ty[0] in (8, 25, 28): s += f'<{tstr(ty[1])}>'
            elif ty[0] == 24: s += f'<{tstr(ty[1])},{tstr(ty[2])}>'
            elif ty[0] == 26: s += f'<{names[ty[2]]}>'
            return s
        for sn in order:
            if dump.search(names[sn]):
                sup = structs[sn][0]
                print(f'struct {names[sn]} : {names[sup] if sup != -1 else "-"}')
                i = 0
                for adim, pn, ty in own[sn]:
                    print(f'   [{i}] {names[pn]} {tstr(ty)}' + (f' x{adim}' if adim > 1 else '')); i += adim

    o = io.BytesIO()
    o.write(struct.pack('<I', nnames))
    for n in names:
        e = n.encode('utf-8'); o.write(struct.pack('<H', len(e)) if ver >= 3 else bytes([len(e)])); o.write(e)
    o.write(struct.pack('<I', nenums))
    for en, mem in enums:
        o.write(struct.pack('<i', en)); o.write(struct.pack('<H', len(mem)) if ver >= 2 else bytes([len(mem)]))
        for m in mem: o.write(struct.pack('<Qi', *m) if ver >= 4 else struct.pack('<i', m))
    o.write(struct.pack('<I', nstructs))
    for sn in order:
        sup = structs[sn][0]; props = own[sn]
        o.write(struct.pack('<ii', sn, sup))
        o.write(struct.pack('<HH', sum(p[0] for p in props), len(props)))
        i = 0
        for adim, pn, ty in props:
            o.write(struct.pack('<HBi', i, adim, pn)); write_type(o, ty); i += adim
    data = o.getvalue()
    with open(dst, 'wb') as w:
        w.write(struct.pack('<HB', 0x30C4, ver))
        if ver >= 1: w.write(struct.pack('<i', 0))
        w.write(struct.pack('<BII', 0, len(data), len(data)))
        w.write(data)
    print(f'wrote {dst} ({len(data)} bytes)')

if __name__ == '__main__':
    main()
