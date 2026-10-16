"""Minimal UE4 package (.uasset) reader/writer for Days Gone classic.

Handles stock UE 4.11 cooked packages (FileVersionUE4 498, licensee 0) and Bend's game packages (FileVersionUE4 500,
licensee 34, name entries with the 4-byte hash pair). Supports reading the summary, name/import/export maps and
tagged properties, appending names/imports, patching export data, and writing the package back with all header
offsets shifted.

    python upkg.py dump <file.uasset>            summary, names, imports, exports
    python upkg.py props <file.uasset> [export]  tagged-property tree of one export (default: first)
"""
import argparse, struct, sys, io, json

def rd(f, fmt):
    s = struct.calcsize('<' + fmt)
    return struct.unpack('<' + fmt, f.read(s))

def rstr(f):
    n = rd(f, 'i')[0]
    if n == 0: return ''
    if n < 0: return f.read(-n * 2).decode('utf-16le').rstrip('\0')
    return f.read(n).decode('latin1').rstrip('\0')

def wstr(s):
    if s == '': return struct.pack('<i', 0)
    try:
        b = s.encode('ascii') + b'\0'
        return struct.pack('<i', len(b)) + b
    except UnicodeEncodeError:
        b = s.encode('utf-16le') + b'\0\0'
        return struct.pack('<i', -(len(b) // 2)) + b

# summary fields in file order: (name, fmt or special)
class Package:
    def __init__(self, data):
        self.data = data
        f = io.BytesIO(data)
        s = {}
        s['Tag'], s['Legacy'] = rd(f, 'Ii')
        s['UE3'] = rd(f, 'i')[0] if s['Legacy'] != -4 else None
        s['Ver'], s['Licensee'] = rd(f, 'ii')
        n = rd(f, 'i')[0]
        s['CustomVersions'] = [(f.read(16), rd(f, 'i')[0]) for _ in range(n)]
        self._off = {}   # offset-field name -> position of the field in the summary
        def field(name, fmt='i'):
            self._off[name] = (f.tell(), fmt)
            s[name] = rd(f, fmt)[0]
        field('TotalHeaderSize')
        s['FolderName'] = rstr(f)
        s['PackageFlags'] = rd(f, 'I')[0]
        field('NameCount'); field('NameOffset')
        field('GatherableTextDataCount'); field('GatherableTextDataOffset')
        field('ExportCount'); field('ExportOffset')
        field('ImportCount'); field('ImportOffset')
        field('DependsOffset')
        field('StringAssetReferencesCount'); field('StringAssetReferencesOffset')
        field('ThumbnailTableOffset')
        s['Guid'] = f.read(16)
        n = rd(f, 'i')[0]
        self._gen = f.tell()
        s['Generations'] = [rd(f, 'ii') for _ in range(n)]
        def ever():
            ma, mi, pa, cl = rd(f, 'HHHI'); br = rstr(f)
            return (ma, mi, pa, cl, br)
        s['SavedByEngineVersion'] = ever()
        s['CompatibleWithEngineVersion'] = ever()
        s['CompressionFlags'] = rd(f, 'I')[0]
        n = rd(f, 'i')[0]; assert n == 0, 'compressed chunks not supported'
        s['PackageSource'] = rd(f, 'I')[0]
        n = rd(f, 'i')[0]
        s['AdditionalPackagesToCook'] = [rstr(f) for _ in range(n)]
        if s['Legacy'] > -7:
            s['NumTextureAllocations'] = rd(f, 'i')[0]; assert s['NumTextureAllocations'] == 0
        field('AssetRegistryDataOffset')
        field('BulkDataStartOffset', 'q')
        field('WorldTileInfoDataOffset')
        n = rd(f, 'i')[0]
        s['ChunkIDs'] = list(rd(f, '%di' % n)) if n else []
        self.summary_end = f.tell()
        self.s = s
        self.hashes = s['Ver'] >= 504 or s['Licensee'] >= 34
        # names
        f.seek(s['NameOffset'])
        self.names = []
        for _ in range(s['NameCount']):
            nm = rstr(f)
            h = f.read(4) if self.hashes else b''
            self.names.append(nm)
        self.name_end = f.tell()
        # imports
        f.seek(s['ImportOffset'])
        self.imports = []
        for _ in range(s['ImportCount']):
            cp, cpn, cn, cnn, outer, on, onn = rd(f, 'iiiiiii')
            self.imports.append({'ClassPackage': (cp, cpn), 'ClassName': (cn, cnn), 'Outer': outer, 'Name': (on, onn)})
        # exports
        f.seek(s['ExportOffset'])
        self.exports = []
        for _ in range(s['ExportCount']):
            pos = f.tell()
            cls, sup, outer, on, onn, flags, size, off = rd(f, 'iiiiiIii')
            rest = f.read(4 * 3 + 16 + 4 + 4 + 4)
            self.exports.append({'Class': cls, 'Super': sup, 'Outer': outer, 'Name': (on, onn), 'Flags': flags,
                                 'SerialSize': size, 'SerialOffset': off, 'rest': rest, 'pos': pos})
        self.export_end = f.tell()

    # ---------------------------------------------------------------- helpers
    def name(self, nn):
        i, num = nn
        b = self.names[i]
        return b if num == 0 else '%s_%d' % (b, num - 1)
    def name_index(self, s, add=True):
        if s in self.names: return self.names.index(s)
        if not add: raise KeyError(s)
        self.names.append(s); return len(self.names) - 1
    def ref(self, idx):
        if idx == 0: return None
        if idx < 0:
            im = self.imports[-idx - 1]
            return 'import:%s %s' % (self.name(im['ClassName']), self.obj_path(idx))
        return 'export:%s' % self.name(self.exports[idx - 1]['Name'])
    def obj_path(self, idx):
        parts = []
        while idx != 0:
            e = self.imports[-idx - 1] if idx < 0 else self.exports[idx - 1]
            parts.append(self.name(e['Name'])); idx = e['Outer']
        return '.'.join(reversed(parts))
    def find_import(self, cls, path):
        for i, im in enumerate(self.imports):
            if self.name(im['ClassName']) == cls and self.obj_path(-i - 1) == path:
                return -i - 1
        return None
    def add_import(self, class_package, class_name, outer, name):
        """append an import (names added as needed); returns its package index"""
        def fn(s):
            return (self.name_index(s), 0)
        self.imports.append({'ClassPackage': fn(class_package), 'ClassName': fn(class_name), 'Outer': outer,
                             'Name': fn(name)})
        return -len(self.imports)
    def ensure_object_import(self, package_path, class_package, class_name):
        """/Game/A/B/obj -> imports Package '/Game/A/B/obj' + object 'obj' of class_name; returns object index.
        '/Game/A/B/pkg.obj' names the object explicitly."""
        objname = package_path.rsplit('/', 1)[1]
        if '.' in objname:
            package_path, objname = package_path.rsplit('.', 1)
        pk = None
        for i, im in enumerate(self.imports):
            if self.name(im['ClassName']) == 'Package' and self.name(im['Name']) == package_path and im['Outer'] == 0:
                pk = -i - 1
        if pk is None:
            pk = self.add_import('/Script/CoreUObject', 'Package', 0, package_path)
        for i, im in enumerate(self.imports):
            if im['Outer'] == pk and self.name(im['Name']) == objname:
                return -i - 1
        return self.add_import(class_package, class_name, pk, objname)
    def export_data(self, i=0):
        e = self.exports[i]
        return self.data[e['SerialOffset']:e['SerialOffset'] + e['SerialSize']]

    # ---------------------------------------------------------------- write
    def add_export(self, like, name, outer):
        """append an export that copies export `like`'s class/flags/table tail; its data goes into write()'s list"""
        t = self.exports[like]
        self.exports.append({'Class': t['Class'], 'Super': t['Super'], 'Outer': outer, 'Name': name, 'Flags': t['Flags'],
                             'SerialSize': 0, 'SerialOffset': None, 'rest': t['rest'], 'pos': None})
        return len(self.exports)   # package index of the new export

    def write(self, export_datas=None):
        """rebuild the package; export_datas: optional list of replacement bytes per export (required for exports
        appended with add_export, which are written after the existing ones and get empty depends-map entries)"""
        s, d = self.s, self.data
        n_old = s['ExportCount']
        n_new = len(self.exports) - n_old
        dep_end = None
        if n_new:
            assert export_datas and len(export_datas) == len(self.exports), 'appended exports need their data'
            assert s['ExportOffset'] + 72 * n_old == self.export_end == s['DependsOffset'], 'unexpected export/depends layout'
            o = s['DependsOffset']
            for _ in range(n_old):
                o += 4 + 4 * struct.unpack_from('<i', d, o)[0]
            dep_end = o
        old_names_len = self.name_end - s['NameOffset']
        nb = b''.join(wstr(n) + (b'\0\0\0\0' if self.hashes else b'') for n in self.names)
        # hashes are only used for fast lookup; the loader recomputes them -> zero is accepted? keep originals
        if self.hashes:
            nb = self._names_with_hashes()
        ib = b''.join(struct.pack('<iiiiiii', *im['ClassPackage'], *im['ClassName'], im['Outer'], *im['Name'])
                      for im in self.imports)
        old_imports_len = s['ImportCount'] * 28
        assert s['NameOffset'] < s['ImportOffset'] < s['ExportOffset'], 'unexpected table order'
        d_names = len(nb) - old_names_len
        d_imp = len(ib) - old_imports_len
        d_exp = 72 * n_new          # export table entries
        d_dep = 4 * n_new           # empty depends-map arrays
        def shift(off):
            if off <= 0: return off
            o = off
            if off >= self.name_end: o += d_names
            if off >= s['ImportOffset'] + old_imports_len: o += d_imp
            if n_new and off >= self.export_end: o += d_exp
            if n_new and off >= dep_end: o += d_dep
            return o
        # export data
        datas = export_datas or [self.export_data(i) for i in range(len(self.exports))]
        hdr_end_old = s['TotalHeaderSize']
        # body = everything after the header that is not export data is kept in place relative to exports
        first = min(e['SerialOffset'] for e in self.exports[:n_old])
        assert first == hdr_end_old, 'export data must start at TotalHeaderSize'
        # rebuild export data area in original order of offsets, appended exports last
        order = sorted(range(n_old), key=lambda i: self.exports[i]['SerialOffset']) + list(range(n_old, len(self.exports)))
        new_hdr_end = shift(hdr_end_old)
        body = b''; new_off = {}
        cur = new_hdr_end
        for i in order:
            new_off[i] = cur; body += datas[i]; cur += len(datas[i])
        last = self.exports[order[n_old - 1]]
        tail = d[last['SerialOffset'] + last['SerialSize']:]   # bulk data etc.
        d_body = (new_hdr_end + len(body)) - (last['SerialOffset'] + last['SerialSize'])
        # exports table
        eb = b''
        for i, e in enumerate(self.exports):
            eb += struct.pack('<iiiiiIii', e['Class'], e['Super'], e['Outer'], *e['Name'], e['Flags'], len(datas[i]),
                              new_off[i]) + e['rest']
        # assemble header
        out = bytearray(d[:self.summary_end])
        def setf(name, val):
            pos, fmt = self._off[name]
            struct.pack_into('<' + fmt, out, pos, val)
        setf('NameCount', len(self.names)); setf('ImportCount', len(self.imports)); setf('ExportCount', len(self.exports))
        for k in ('GatherableTextDataOffset', 'ExportOffset', 'ImportOffset', 'DependsOffset',
                  'StringAssetReferencesOffset', 'ThumbnailTableOffset', 'AssetRegistryDataOffset',
                  'WorldTileInfoDataOffset'):
            setf(k, shift(s[k]))
        setf('TotalHeaderSize', new_hdr_end)
        bdo = s['BulkDataStartOffset']
        setf('BulkDataStartOffset', bdo + (new_hdr_end - hdr_end_old) + (d_body - (new_hdr_end - hdr_end_old)) if bdo > 0 else bdo)
        # generations: last generation counts
        g = list(s['Generations'])
        if g:
            ec, nc = g[-1]
            struct.pack_into('<ii', out, self._gen + 8 * (len(g) - 1), len(self.exports), len(self.names))
        # header body between summary end and TotalHeaderSize, with tables replaced
        pre = d[self.summary_end:s['NameOffset']]
        mid1 = d[self.name_end:s['ImportOffset']]
        mid2 = d[s['ImportOffset'] + old_imports_len:s['ExportOffset']]
        post = d[self.export_end:hdr_end_old]
        if n_new:
            post = d[self.export_end:dep_end] + b'\0\0\0\0' * n_new + d[dep_end:hdr_end_old]
        out += pre + nb + mid1 + ib + mid2 + eb + post
        assert len(out) == new_hdr_end, (len(out), new_hdr_end)
        out += body + tail
        return bytes(out)

    def _names_with_hashes(self):
        # keep original hashes for unchanged names; compute UE's hashes for new or rewritten ones
        f = io.BytesIO(self.data); f.seek(self.s['NameOffset'])
        orig = []
        for _ in range(self.s['NameCount']):
            nm = rstr(f); orig.append((nm, f.read(4)))
        out = b''
        for i, n in enumerate(self.names):
            h = orig[i][1] if i < len(orig) and orig[i][0] == n else ue_name_hashes(n)
            out += wstr(n) + h
        return out

# UE4 FCrc::Strihash_DEPRECATED (non-case-preserving) and FCrc::StrCrc32 (case-preserving), each truncated to 16 bits
def _crc_table():
    t = []
    for i in range(256):
        c = i << 24
        for _ in range(8):
            c = ((c << 1) ^ 0x04C11DB7) if c & 0x80000000 else (c << 1)
        t.append(c & 0xFFFFFFFF)
    return t
_CRC = _crc_table()
def _crc32_full(i):
    c = 0
    for _ in range(8): pass
    return c
def _strihash(s):
    h = 0
    for ch in s:
        c = ord(ch.upper()) & 0xFF
        h = ((h >> 8) & 0x00FFFFFF) ^ _CRC[(h ^ c) & 0xFF]
    return h & 0xFFFF
def _strcrc32(s):
    # FCrc::StrCrc32 uses CRCTablesSB8 (reflected 0xEDB88320) on each 32-bit char
    crc = 0xFFFFFFFF
    for ch in s:
        c = ord(ch)
        for _ in range(4):
            crc = (crc >> 8) ^ _CRC32R[(crc ^ c) & 0xFF]
            c >>= 8
    return (~crc) & 0xFFFF
_CRC32R = []
for i in range(256):
    c = i
    for _ in range(8):
        c = (c >> 1) ^ 0xEDB88320 if c & 1 else c >> 1
    _CRC32R.append(c)
def ue_name_hashes(s):
    return struct.pack('<HH', _strihash(s), _strcrc32(s))

# ---------------------------------------------------------------- tagged properties
class Prop:
    def __init__(self, name, typ, size, aidx, extra, start, vstart, vend):
        self.name, self.type, self.size, self.aidx, self.extra = name, typ, size, aidx, extra
        self.start, self.vstart, self.vend = start, vstart, vend
        self.children = None
    def __repr__(self):
        return '%s:%s[%d]@%d+%d %s' % (self.name, self.type, self.aidx, self.vstart, self.size, self.extra or '')

def parse_props(pkg, data, pos=0, end=None, depth=0):
    """returns list of Prop for a tagged property stream starting at pos; stops at None"""
    f = io.BytesIO(data); f.seek(pos)
    out = []
    end = len(data) if end is None else end
    while f.tell() < end:
        start = f.tell()
        ni, nn = rd(f, 'ii')
        nm = pkg.name((ni, nn))
        if nm == 'None': break
        ti, tn = rd(f, 'ii'); typ = pkg.name((ti, tn))
        size, aidx = rd(f, 'ii')
        extra = None
        if typ == 'StructProperty':
            extra = pkg.name(rd(f, 'ii')); f.read(16)
        elif typ == 'BoolProperty':
            extra = f.read(1)[0]
        elif typ in ('ByteProperty',):
            extra = pkg.name(rd(f, 'ii'))
        elif typ == 'ArrayProperty':
            extra = pkg.name(rd(f, 'ii'))
        elif typ == 'MapProperty':
            extra = (pkg.name(rd(f, 'ii')), pkg.name(rd(f, 'ii')))
        if pkg.s['Ver'] >= 503:
            if f.read(1)[0]: f.read(16)
        vstart = f.tell()
        p = Prop(nm, typ, size, aidx, extra, start, vstart, vstart + size)
        if typ == 'StructProperty' and extra not in ('Vector', 'Rotator', 'Guid', 'LinearColor', 'Color', 'Vector2D',
                                                      'Quat', 'Box', 'IntPoint', 'Transform', 'StringAssetReference'):
            p.children = parse_props(pkg, data, vstart, vstart + size, depth + 1)
        elif typ == 'ArrayProperty' and extra == 'StructProperty':
            g = io.BytesIO(data); g.seek(vstart)
            cnt = rd(g, 'i')[0]
            # the inner struct tag (VER_UE4_INNER_ARRAY_TAG_INFO) is not in Bend's version 500 nor stock 4.11
            if pkg.s['Ver'] > 500:
                parse_inner_tag(pkg, g)
            items = []
            ipos = g.tell()
            for _ in range(cnt):
                ch = parse_props(pkg, data, ipos, vstart + size, depth + 1)
                items.append(ch)
                ipos = ch.end if hasattr(ch, 'end') else ipos
            p.children = items
        f.seek(vstart + size)
        out.append(p)
    out = PList(out); out.end = f.tell() + 0 if False else f.tell()
    return out

class PList(list):
    end = 0

def parse_inner_tag(pkg, g):
    # array of structs: an inner property tag precedes the items
    ni, nn = rd(g, 'ii'); ti, tn = rd(g, 'ii'); size, aidx = rd(g, 'ii')
    sname = pkg.name(rd(g, 'ii')); g.read(16)
    if pkg.s['Ver'] >= 503:
        if g.read(1)[0]: g.read(16)
    return (pkg.name((ni, nn)), pkg.name((ti, tn)), size, sname)

def dump_props(pkg, data, props, ind=0):
    for p in props:
        val = ''
        if p.type == 'ObjectProperty':
            v = struct.unpack_from('<i', data, p.vstart)[0]; val = '%d %s' % (v, pkg.ref(v))
        elif p.type in ('IntProperty',):
            val = struct.unpack_from('<i', data, p.vstart)[0]
        elif p.type == 'FloatProperty':
            val = struct.unpack_from('<f', data, p.vstart)[0]
        elif p.type == 'BoolProperty':
            val = p.extra
        elif p.type == 'NameProperty':
            val = pkg.name(struct.unpack_from('<ii', data, p.vstart))
        print('  ' * ind + '%s (%s%s) @%d = %s' % (p.name, p.type, '/' + str(p.extra) if p.extra not in (None, 0, 1) else '', p.vstart, val))
        if p.children is not None:
            if p.type == 'ArrayProperty':
                for k, ch in enumerate(p.children):
                    print('  ' * (ind + 1) + '[%d]' % k)
                    dump_props(pkg, data, ch, ind + 2)
            else:
                dump_props(pkg, data, p.children, ind + 1)

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('cmd', choices=('dump', 'props')); ap.add_argument('path')
    ap.add_argument('export', nargs='?', type=int, default=0, help='props: export index (default 0)')
    args = ap.parse_args()
    cmd, path = args.cmd, args.path
    pkg = Package(open(path, 'rb').read())
    if cmd == 'dump':
        s = dict(pkg.s); s.pop('Guid'); s.pop('CustomVersions')
        print(json.dumps({k: (v if not isinstance(v, bytes) else v.hex()) for k, v in s.items()}, indent=0, default=str))
        print('names', len(pkg.names), 'hashes', pkg.hashes)
        for i, im in enumerate(pkg.imports):
            print('imp %d %s %s outer=%d %s' % (-i - 1, pkg.name(im['ClassPackage']), pkg.name(im['ClassName']), im['Outer'], pkg.obj_path(-i - 1)))
        for i, e in enumerate(pkg.exports):
            print('exp %d %s class=%s outer=%d size=%d off=%d' % (i + 1, pkg.name(e['Name']), pkg.ref(e['Class']), e['Outer'], e['SerialSize'], e['SerialOffset']))
    elif cmd == 'props':
        i = args.export
        data = pkg.export_data(i)
        props = parse_props(pkg, data)
        dump_props(pkg, data, props)
