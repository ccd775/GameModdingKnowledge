# uasset.py — minimal UE 4.27 cooked (legacy, unversioned summary, tagged properties) package reader/writer.
# Parses the summary, name/import/export maps and preload dependencies so names, imports and export bytes can be
# added or changed; write() recomputes every header offset and export SerialOffset. Sections it doesn't model are
# carried as opaque bytes (they hold no absolute offsets in cooked packages).
import struct

TAG = 0x9E2A83C1

class R:
    def __init__(s, b, p=0): s.b = b; s.p = p
    def i32(s): v = struct.unpack_from('<i', s.b, s.p)[0]; s.p += 4; return v
    def u32(s): v = struct.unpack_from('<I', s.b, s.p)[0]; s.p += 4; return v
    def i64(s): v = struct.unpack_from('<q', s.b, s.p)[0]; s.p += 8; return v
    def u16(s): v = struct.unpack_from('<H', s.b, s.p)[0]; s.p += 2; return v
    def raw(s, n): v = s.b[s.p:s.p + n]; s.p += n; return v
    def fstr(s):
        n = s.i32()
        if n == 0: return ''
        if n < 0: v = s.b[s.p:s.p - n * 2].decode('utf-16le'); s.p += -n * 2; return v[:-1]
        v = s.b[s.p:s.p + n].decode('latin1'); s.p += n; return v[:-1]

class W:
    def __init__(s): s.b = bytearray()
    def i32(s, v): s.b += struct.pack('<i', v)
    def u32(s, v): s.b += struct.pack('<I', v)
    def i64(s, v): s.b += struct.pack('<q', v)
    def u16(s, v): s.b += struct.pack('<H', v)
    def raw(s, v): s.b += v
    def fstr(s, v):
        if v == '': s.i32(0); return
        try: e = (v + '\0').encode('latin1'); s.i32(len(e)); s.b += e
        except UnicodeEncodeError: e = (v + '\0').encode('utf-16le'); s.i32(-(len(e) // 2)); s.b += e

def name_hash(s):
    # FNameEntry hashes (non-case-preserving + case-preserving) are only used by the editor loader; cooked loaders
    # (and retoc) recompute them, so zeros are accepted. Keep existing values for untouched names.
    return 0

class Package:
    def __init__(s, uasset_path):
        s.path = uasset_path
        ua = open(uasset_path, 'rb').read(); s.uexp = bytearray(open(uasset_path[:-7] + '.uexp', 'rb').read())
        r = R(ua)
        assert r.u32() == TAG
        s.legacy = r.i32(); assert s.legacy == -7, s.legacy
        s.ue3 = r.i32(); s.ue4 = r.i32(); s.lic = r.i32()
        ncv = r.i32(); s.custom = [r.raw(20) for _ in range(ncv)]
        s.total_header = r.i32(); s.folder = r.fstr(); s.pkg_flags = r.u32()
        name_count = r.i32(); name_off = r.i32()
        s.gtd_count = r.i32(); s.gtd_off = r.i32()
        export_count = r.i32(); export_off = r.i32()
        import_count = r.i32(); import_off = r.i32()
        s.depends_off = r.i32()
        s.soft_count = r.i32(); s.soft_off = r.i32()
        s.searchable_off = r.i32(); s.thumb_off = r.i32()
        s.guid = r.raw(16)
        gen = r.i32(); s.generations = [(r.i32(), r.i32()) for _ in range(gen)]
        s.saved_ver = s._engver(r); s.compat_ver = s._engver(r)
        s.compression = r.u32(); assert r.i32() == 0  # compressed chunks
        s.pkg_source = r.u32()
        n = r.i32(); s.additional = [r.fstr() for _ in range(n)]
        s.ar_off = r.i32(); s.bulk_start = r.i64(); s.wtile_off = r.i32()
        n = r.i32(); s.chunk_ids = [r.i32() for _ in range(n)]
        s.preload_count = r.i32(); s.preload_off = r.i32()
        s.summary_end = r.p
        # name map
        r.p = name_off; s.names = []; s.name_hashes = []
        for _ in range(name_count): s.names.append(r.fstr()); s.name_hashes.append(r.u32())
        # imports
        r.p = import_off; s.imports = []
        for _ in range(import_count):
            s.imports.append(dict(class_package=(r.i32(), r.i32()), class_name=(r.i32(), r.i32()), outer=r.i32(), object_name=(r.i32(), r.i32())))
        # exports
        r.p = export_off; s.exports = []
        for _ in range(export_count):
            e = dict(cls=r.i32(), sup=r.i32(), tmpl=r.i32(), outer=r.i32(), name=(r.i32(), r.i32()), flags=r.u32(),
                     size=r.i64(), offset=r.i64(), forced=r.i32(), nfc=r.i32(), nfs=r.i32(), pguid=r.raw(16), pflags=r.u32(),
                     nalfeg=r.i32(), is_asset=r.i32(), first_dep=r.i32(), deps=[r.i32() for _ in range(4)])
            s.exports.append(e)
        # opaque blocks between the export map and the preload dependencies (depends map, soft refs, searchable names,
        # thumbnails, asset registry data, world tile info), kept in order with their summary fields
        s.mid_start = r.p
        s.mid = ua[r.p:s.preload_off] if s.preload_off > 0 else ua[r.p:s.total_header]
        if s.preload_off > 0:
            r.p = s.preload_off
            s.preload = [r.i32() for _ in range(max(0, s.preload_count))]
        else: s.preload = []
        s.tail = ua[r.p:s.total_header]
        # export payloads
        for e in s.exports:
            o = e['offset'] - s.total_header; e['data'] = bytes(s.uexp[o:o + e['size']])
        s.old_data_total = sum(e['size'] for e in s.exports)
        last = max(e['offset'] + e['size'] for e in s.exports) - s.total_header
        s.uexp_tail = bytes(s.uexp[last:])

    @staticmethod
    def _engver(r): return (r.u16(), r.u16(), r.u16(), r.u32(), r.fstr())
    @staticmethod
    def _wengver(w, v): w.u16(v[0]); w.u16(v[1]); w.u16(v[2]); w.u32(v[3]); w.fstr(v[4])

    # ---------------------------------------------------------------- helpers
    def name(self, n):
        if n not in self.names: self.names.append(n); self.name_hashes.append(name_hash(n))
        return self.names.index(n)
    def fname(self, n): return (self.name(n), 0)
    def nstr(self, fn): return self.names[fn[0]] + ('' if fn[1] == 0 else '_%d' % (fn[1] - 1))
    def import_path(self, i):
        im = self.imports[i]; parts = [self.nstr(im['object_name'])]
        while im['outer'] < 0: im = self.imports[-im['outer'] - 1]; parts.append(self.nstr(im['object_name']))
        return '.'.join(reversed(parts))
    def find_import(self, cls_name, obj_name, outer=None):
        for i, im in enumerate(self.imports):
            if self.nstr(im['class_name']) == cls_name and self.nstr(im['object_name']) == obj_name and (outer is None or im['outer'] == outer):
                return -(i + 1)
        return None
    def add_import(self, class_package, class_name, outer, object_name):
        f = self.find_import(class_name, object_name, outer)
        if f is not None: return f
        self.imports.append(dict(class_package=self.fname(class_package), class_name=self.fname(class_name), outer=outer, object_name=self.fname(object_name)))
        return -len(self.imports)
    def dump(self):
        print('names', len(self.names), 'imports', len(self.imports), 'exports', len(self.exports), 'preload', len(self.preload), 'header', self.total_header)
        for i, im in enumerate(self.imports):
            print('  import %d: %s %s outer=%d %s' % (-(i + 1), self.nstr(im['class_package']), self.nstr(im['class_name']), im['outer'], self.nstr(im['object_name'])))
        for i, e in enumerate(self.exports):
            d = e['deps']; dep = self.preload[e['first_dep']:e['first_dep'] + sum(d)] if e['first_dep'] >= 0 else []
            print('  export %d: %s cls=%d outer=%d size=%d first_dep=%d deps=%s -> %s' % (i + 1, self.nstr(e['name']), e['cls'], e['outer'], e['size'], e['first_dep'], d, dep))

    # ---------------------------------------------------------------- tagged property helpers
    def prop_tag(self, name, type_name, size, extra=b''):
        # FPropertyTag (UE4.27): Name, Type, Size, ArrayIndex, [type-specific], HasPropertyGuid
        w = W(); n = self.fname(name); t = self.fname(type_name)
        w.i32(n[0]); w.i32(n[1]); w.i32(t[0]); w.i32(t[1]); w.i32(size); w.i32(0); w.raw(extra); w.raw(b'\0')
        return bytes(w.b)
    def none_tag(self):
        n = self.fname('None'); return struct.pack('<ii', *n)

    # ---------------------------------------------------------------- write
    def write(self, out_uasset):
        def build(total_header):
            w = W()
            w.u32(TAG); w.i32(self.legacy); w.i32(self.ue3); w.i32(self.ue4); w.i32(self.lic)
            w.i32(len(self.custom)); [w.raw(c) for c in self.custom]
            w.i32(total_header); w.fstr(self.folder); w.u32(self.pkg_flags)
            fix = {}
            def slot(key): fix[key] = len(w.b); w.i32(0)
            w.i32(len(self.names)); slot('name_off')
            w.i32(self.gtd_count); w.i32(self.gtd_off)
            w.i32(len(self.exports)); slot('export_off')
            w.i32(len(self.imports)); slot('import_off')
            slot('depends_off')
            w.i32(self.soft_count); slot('soft_off')
            slot('searchable_off'); slot('thumb_off')
            w.raw(self.guid)
            w.i32(len(self.generations)); [(w.i32(len(self.exports)), w.i32(len(self.names))) for _ in self.generations]
            self._wengver(w, self.saved_ver); self._wengver(w, self.compat_ver)
            w.u32(self.compression); w.i32(0); w.u32(self.pkg_source)
            w.i32(len(self.additional)); [w.fstr(a) for a in self.additional]
            slot('ar_off'); fix['bulk_start'] = len(w.b); w.i64(0); slot('wtile_off')
            w.i32(len(self.chunk_ids)); [w.i32(c) for c in self.chunk_ids]
            w.i32(len(self.preload) if self.preload_count >= 0 else self.preload_count); slot('preload_off')
            pos = {}
            pos['name_off'] = len(w.b)
            for n, h in zip(self.names, self.name_hashes): w.fstr(n); w.u32(h)
            pos['import_off'] = len(w.b)
            for im in self.imports:
                w.i32(im['class_package'][0]); w.i32(im['class_package'][1]); w.i32(im['class_name'][0]); w.i32(im['class_name'][1])
                w.i32(im['outer']); w.i32(im['object_name'][0]); w.i32(im['object_name'][1])
            pos['export_off'] = len(w.b)
            export_entry_pos = []
            for e in self.exports:
                export_entry_pos.append(len(w.b))
                w.i32(e['cls']); w.i32(e['sup']); w.i32(e['tmpl']); w.i32(e['outer']); w.i32(e['name'][0]); w.i32(e['name'][1]); w.u32(e['flags'])
                w.i64(len(e['data'])); w.i64(0); w.i32(e['forced']); w.i32(e['nfc']); w.i32(e['nfs']); w.raw(e['pguid']); w.u32(e['pflags'])
                w.i32(e['nalfeg']); w.i32(e['is_asset']); w.i32(e['first_dep']); [w.i32(d) for d in e['deps']]
            # opaque middle: shift its summary offsets by how far it moved
            shift = len(w.b) - self.mid_start
            for key in ('depends_off', 'soft_off', 'searchable_off', 'thumb_off', 'ar_off', 'wtile_off'):
                old = getattr(self, key)
                pos[key] = old + shift if old > 0 else old
            w.raw(self.mid)
            pos['preload_off'] = len(w.b) if self.preload_off > 0 else self.preload_off
            for d in self.preload: w.i32(d)
            w.raw(self.tail)
            hdr = len(w.b)
            for key, at in fix.items():
                if key == 'bulk_start': continue
                struct.pack_into('<i', w.b, at, pos[key] if pos.get(key, 0) is not None else 0)
            off = hdr
            for e, at in zip(self.exports, export_entry_pos):
                struct.pack_into('<q', w.b, at + 36, off); e['_new_offset'] = off; off += len(e['data'])
            bulk = self.bulk_start + (hdr - self.total_header) + (off - hdr - self.old_data_total) if self.bulk_start > 0 else self.bulk_start
            struct.pack_into('<q', w.b, fix['bulk_start'], bulk)
            return w, hdr
        w, hdr = build(self.total_header)
        w, hdr2 = build(hdr); assert hdr2 == hdr
        struct.pack_into('<i', w.b, 4 * 5 + 4 + 20 * len(self.custom), hdr)
        open(out_uasset, 'wb').write(w.b)
        open(out_uasset[:-7] + '.uexp', 'wb').write(b''.join(e['data'] for e in self.exports) + self.uexp_tail)
        return out_uasset

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='dump a UE 4.27 legacy cooked package; with a second path, write it back and compare')
    ap.add_argument('uasset'); ap.add_argument('roundtrip_out', nargs='?', help='write the parsed package here and compare')
    args = ap.parse_args(); src, dst = args.uasset, args.roundtrip_out
    p = Package(src); p.dump(); print(p.names)
    if dst is not None:  # round-trip check
        p.write(dst)
        a = open(src, 'rb').read(); b = open(dst, 'rb').read()
        print('roundtrip uasset identical:', a == b, len(a), len(b))
        a = open(src[:-7] + '.uexp', 'rb').read(); b = open(dst[:-7] + '.uexp', 'rb').read()
        print('roundtrip uexp identical:', a == b)
