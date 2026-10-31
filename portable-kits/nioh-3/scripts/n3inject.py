#!/usr/bin/env python3
"""Install / remove resource overrides in Nioh 3 by rewriting root.rdb / root.rdx (no DLL, no hooks).

Same scheme as eArmada8's yumia_fdata_tools (used by Nioh 3 mods on Nexus): every override file
`0x<hash>.<ext>` goes, stored uncompressed, into one new container `0x<fdata>.fdata`; root.rdx gets one
more container slot; each overridden root.rdb record is rebuilt to point at it. The record keeps its
original type, entry_type and parameter block; the fdata entry keeps the original entry's parameter block.

  install  <package> <mod dir> [--fdata 0x4b415249]   start from root.rdb/rdx.original (created on first use)
  restore  <package>                                  put the .original files back, delete our container
  verify   <package> <mod dir>                        decode every override through root.rdb and compare bytes

Writes only root.rdb, root.rdx, their .original backups (once), and the new container in <package>.
n3inject.json records the root.rdb / root.rdx it wrote: if the game later replaced them (update, file verification),
the .original backups are stale; install then backs up the game's current files instead, and restore leaves them.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata  # noqa: E402

DEFAULT_FDATA = 0x4B415249   # 'KARI'
STATE = 'n3inject.json'


def mod_files(mod_dir):
    out = {}
    for p in sorted(Path(mod_dir).iterdir()):
        stem = p.stem.lower()
        if p.is_file() and stem.startswith('0x') and len(stem) == 10:
            h = int(stem, 16)
            if h in out:
                raise SystemExit(f'duplicate override for {stem}: {out[h].name} and {p.name}')
            out[h] = p
    if not out:
        raise SystemExit(f'no 0x<hash>.* files in {mod_dir}')
    return out


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def replaced_by_game(pkg):
    """True when root.rdb / root.rdx are neither what our last install wrote nor the backups (the game rewrote them)."""
    pkg = Path(pkg); state = pkg / STATE
    written = json.loads(state.read_text()).get('written') if state.exists() else None
    if not written:
        return False
    return any(sha(pkg / n) not in (w, sha(pkg / f'{n}.original') if (pkg / f'{n}.original').exists() else None)
               for n, w in written.items())


def originals(pkg):
    pkg = Path(pkg)
    stale = replaced_by_game(pkg)
    if stale:
        print('root.rdb / root.rdx were replaced by the game since the last install: backing up the current files')
    for name in ('root.rdb', 'root.rdx'):
        o = pkg / f'{name}.original'
        if stale or not o.exists():
            shutil.copy2(pkg / name, o)
    return pkg / 'root.rdb.original', pkg / 'root.rdx.original'


def fdata_entry_parts(rec, pkg):
    """(entry_type field, parameter block) of the vanilla fdata entry for this record."""
    path = Path(pkg) / f'0x{rec.fdata_hash:08x}.fdata'
    with path.open('rb') as f:
        f.seek(rec.fdata_offset)
        head = f.read(48)
        assert head[:8] == b'IDRK0000', path
        entry_size, packed, _size = struct.unpack_from('<3Q', head, 8)
        entry_type = struct.unpack_from('<I', head, 32)[0]
        params = f.read(entry_size - packed - 48)
    return entry_type, params


def rdb_record_parts(rdb, rec):
    """(entry_type, parameter block) of the vanilla root.rdb record."""
    p = rec.rdb_offset
    trailer = struct.unpack_from('<Q', rdb, p + 0x10)[0]
    entry_type = struct.unpack_from('<I', rdb, p + 0x20)[0]
    params = rdb[p + 0x30:p + rec.entry_size - trailer]
    return entry_type, bytes(params)


def cmd_install(a):
    pkg = Path(a.package)
    rdb_o, rdx_o = originals(pkg)
    rdb = rdb_o.read_bytes()
    recs = ktdata.parse_rdb(rdb_o, rdx_o)
    rdx = ktdata.parse_rdx(rdx_o)
    files = mod_files(a.mod)
    if a.fdata in rdx.values():
        raise SystemExit(f'container 0x{a.fdata:08x} already listed in the vanilla root.rdx')
    slot = max(rdx) + 1

    container = bytearray(b'PDRK0000' + struct.pack('<2I', 0x10, 0))
    new_records, manifest = {}, []
    for h, path in files.items():
        rec = recs.get(h)
        if rec is None:
            raise SystemExit(f'0x{h:08x} ({path.name}) is not in root.rdb')
        if not rec.internal:
            raise SystemExit(f'0x{h:08x} is an external .file resource; not supported')
        data = path.read_bytes()
        f_type, f_params = fdata_entry_parts(rec, pkg)
        r_type, r_params = rdb_record_parts(rdb, rec)
        offset = len(container)
        entry = b'IDRK0000' + struct.pack('<3Q', 0x30 + len(f_params) + len(data), len(data), len(data)) \
            + struct.pack('<4I', f_type, h, rec.type_hash, 0) + f_params + data
        container += entry
        container += b'\0' * (-len(container) % 0x10)
        rec_bytes = b'IDRK0000' + struct.pack('<3Q', 0x3D + len(r_params), 0xD, len(data)) \
            + struct.pack('<4I', r_type, h, rec.type_hash, 0x20000) + r_params \
            + struct.pack('<H2IHI', 0x401, offset, len(entry), slot, 0)
        new_records[h] = rec_bytes
        manifest.append({'hash': f'0x{h:08x}', 'file': path.name, 'type': f'0x{rec.type_hash:08X}', 'size': len(data),
                         'vanilla_size': rec.file_size, 'sha256': hashlib.sha256(data).hexdigest()})
    struct.pack_into('<I', container, 12, len(container))

    out = bytearray(rdb[:32])
    pos = struct.unpack_from('<I', rdb, 8)[0]
    assert pos == 32, pos
    while pos < len(rdb):
        size = struct.unpack_from('<Q', rdb, pos + 8)[0]
        aligned = size + (-size % 4)
        h = struct.unpack_from('<I', rdb, pos + 0x24)[0]
        out += new_records.get(h, rdb[pos:pos + aligned])
        pos += aligned
    (pkg / f'0x{a.fdata:08x}.fdata').write_bytes(container)
    (pkg / 'root.rdx').write_bytes(rdx_o.read_bytes() + struct.pack('<HhI', slot, -1, a.fdata))
    (pkg / 'root.rdb').write_bytes(out)
    (pkg / STATE).write_text(json.dumps({'fdata': f'0x{a.fdata:08x}', 'slot': slot, 'files': manifest,
                                         'written': {n: sha(pkg / n) for n in ('root.rdb', 'root.rdx')}}, indent=1))
    print(f'installed {len(files)} overrides into 0x{a.fdata:08x}.fdata (slot {slot}, {len(container)} bytes)')
    return verify(pkg, files)


def verify(pkg, files):
    recs = ktdata.parse_rdb(pkg / 'root.rdb', pkg / 'root.rdx')
    bad = 0
    for h, path in files.items():
        got = ktdata.read_entry(recs[h], pkg)
        ok = got == path.read_bytes()
        bad += not ok
        print(('ok  ' if ok else 'BAD ') + f'0x{h:08x} {len(got)}')
    vanilla = ktdata.parse_rdb(pkg / 'root.rdb.original', pkg / 'root.rdx.original')
    def where(r):   # rdb_offset / entry_size shift whenever an earlier record changes length
        return r and (r.type_hash, r.file_size, r.internal, r.fdata_hash, r.fdata_offset, r.fdata_full_size)
    changed = [h for h in vanilla if where(vanilla[h]) != where(recs.get(h))]
    extra = sorted(set(changed) - set(files))
    print(f'records changed: {len(changed)} (unexpected: {len(extra)}) total {len(recs)} vs {len(vanilla)}')
    return 1 if bad or extra or len(recs) != len(vanilla) else 0


def cmd_verify(a):
    return verify(Path(a.package), mod_files(a.mod))


def cmd_restore(a):
    pkg = Path(a.package)
    state = pkg / STATE
    stale = replaced_by_game(pkg)
    for name in ('root.rdb', 'root.rdx'):
        o = pkg / f'{name}.original'
        if o.exists():
            if stale:
                o.unlink()                  # older than the game's current files: never copy it back
            else:
                shutil.copy2(o, pkg / name)
    if stale:
        print('root.rdb / root.rdx were replaced by the game since the install: kept them, dropped the old backups')
    if state.exists():
        f = pkg / (json.loads(state.read_text())['fdata'] + '.fdata')
        if f.exists():
            f.unlink()
        state.unlink()
    if not stale:
        print('restored vanilla root.rdb / root.rdx')
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('install'); p.add_argument('package'); p.add_argument('mod')
    p.add_argument('--fdata', type=lambda s: int(s, 16), default=DEFAULT_FDATA)
    p = sub.add_parser('verify'); p.add_argument('package'); p.add_argument('mod')
    p = sub.add_parser('restore'); p.add_argument('package')
    a = ap.parse_args(argv)
    return {'install': cmd_install, 'verify': cmd_verify, 'restore': cmd_restore}[a.cmd](a)


if __name__ == '__main__':
    sys.exit(main())
