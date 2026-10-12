#!/usr/bin/env python3
"""Rise of the Ronin game data: root.rdb / root.rdx, IDRK .fdata entries, kidsobjdb and KTID texture tables.
Standard library only (plus g1m_tool.py from this folder).

  extract  copy resources out of the game data by hash (named the way RONPATCHER/root expects)
  slots    a model's KTID texture table: slot -> G1T hash, which of them a mod root overrides, and how
  usage    for every G1T in a mod root: which OTHER character models bind it, and whether the mod changed it.
           A replacement that rewrites a texture other models share changes those models too (the Karin template
           set the global 1x1 default 0x1E76FD2D from 1.0 to 0, and NPC skin turned white).

The game data directory is the one holding root.rdb, root.rdx and 0x<hash>.fdata (`fdata_package_dx12`).
The same _DRK / IDRK / KTID / kidsobjdb layout is used by DYNASTY WARRIORS: ORIGINS.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import struct
import sys
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import g1m_tool  # noqa: E402

G1T_TYPES = {0xAFBEC60C, 0xAD57EBBA}
KTID_TYPES = {0x8E39AA37, 0xBE144B78}
KIDSOBJDB_TYPE = 0x20A6A0BB
G1M_TYPE = 0x563BDEF1
CHARACTER_EDITOR_DB = 0xB290631C     # kidsobjdb: CharacterEditor model -> KTID texture table links
SLOT_TYPES = {1: 'COLOR', 2: 'SHADING', 3: 'NORMAL', 5: 'DIRT'}   # material slot `type`; others are unnamed


def hx(v):
    return f'0x{v:08X}'


def align4(v):
    return (v + 3) & ~3


@dataclass(frozen=True)
class Record:
    file_hash: int
    type_hash: int
    file_size: int
    rdb_offset: int
    entry_size: int
    flags: int
    internal: bool
    fdata_id: int | None
    fdata_hash: int | None
    fdata_offset: int | None
    fdata_full_size: int | None


def parse_rdx(path):
    data = Path(path).read_bytes()
    if len(data) % 8:
        raise ValueError(f'{path}: length is not a multiple of 8')
    return {struct.unpack_from('<H', data, i)[0]: struct.unpack_from('<I', data, i + 4)[0] for i in range(0, len(data), 8)}


def parse_rdb(rdb_path, rdx_path):
    data = Path(rdb_path).read_bytes()
    if data[:4] != b'_DRK':
        raise ValueError(f'{rdb_path}: not a _DRK resource table')
    rdx = parse_rdx(rdx_path)
    pos, out = struct.unpack_from('<I', data, 8)[0], {}
    while pos < len(data):
        pos = align4(pos)
        if pos >= len(data):
            break
        if data[pos:pos + 4] != b'IDRK':
            raise ValueError(f'{rdb_path}: no IDRK entry at {pos:#x}')
        entry_size = struct.unpack_from('<Q', data, pos + 8)[0]
        trailer = struct.unpack_from('<I', data, pos + 0x10)[0]
        file_size = struct.unpack_from('<Q', data, pos + 0x18)[0]
        file_hash, type_hash, flags = struct.unpack_from('<3I', data, pos + 0x24)
        internal, fid, foff, ffull = False, None, None, None
        if trailer == 0xD:
            p = pos + entry_size - 0xD
            internal = struct.unpack_from('<H', data, p)[0] == 0x401
            foff, ffull, fid = struct.unpack_from('<I', data, p + 2)[0], struct.unpack_from('<I', data, p + 6)[0], \
                struct.unpack_from('<H', data, p + 0xA)[0]
        elif trailer == 0x11:
            p = pos + entry_size - 0x11
            internal = struct.unpack_from('<H', data, p)[0] == 0x401
            foff = data[p + 2] << 32 | struct.unpack_from('<I', data, p + 6)[0]
            ffull, fid = struct.unpack_from('<I', data, p + 0xA)[0], struct.unpack_from('<H', data, p + 0xE)[0]
        out[file_hash] = Record(file_hash, type_hash, file_size, pos, entry_size, flags, internal, fid,
                                rdx.get(fid) if fid is not None else None, foff, ffull)
        pos += entry_size
    return out


def read_entry(record, game_dir):
    """Decoded bytes of an internal resource (stored or zlib chunked)."""
    if not record.internal or record.fdata_hash is None:
        raise ValueError(f'{hx(record.file_hash)} is not an internal fdata entry')
    path = Path(game_dir) / f'0x{record.fdata_hash:08x}.fdata'
    with path.open('rb') as f:
        f.seek(record.fdata_offset)
        head = f.read(48)
        if head[:8] != b'IDRK0000':
            raise ValueError(f'{hx(record.file_hash)}: no IDRK0000 entry at {record.fdata_offset:#x} of {path.name}')
        entry_size, packed, size = struct.unpack_from('<3Q', head, 8)
        _kind, name_hash, type_hash, flags = struct.unpack_from('<4I', head, 32)
        if (name_hash, type_hash, size) != (record.file_hash, record.type_hash, record.file_size):
            raise ValueError(f'{hx(record.file_hash)}: fdata entry metadata differs from root.rdb')
        f.seek(record.fdata_offset + entry_size - packed)
        if packed == size:
            out = f.read(size)
        else:
            parts, total = [], 0
            while total < size:
                if flags & 0x100000:
                    n = struct.unpack('<I', f.read(4))[0]
                else:
                    n = struct.unpack('<H', f.read(2))[0]
                    f.read(8)
                parts.append(zlib.decompress(f.read(n)))
                total += len(parts[-1])
            out = b''.join(parts)
    if len(out) != size:
        raise ValueError(f'{hx(record.file_hash)}: decoded {len(out)} bytes, expected {size}')
    return out


@dataclass
class KidsEntry:
    name_hash: int
    type_hash: int
    props: list           # (property name hash, value type, values)
    first_value: int | None
    singleton_ints: list


SCALARS = {0: 'b', 1: 'B', 2: 'h', 3: 'H', 4: 'i', 5: 'I', 8: 'f'}
VECTORS = {10: '4f', 12: '2f', 13: '3f'}


def parse_kidsobjdb(data):
    if data[:8] != b'_DOK0000':
        raise ValueError('not a kidsobjdb')
    pos, out = 28, {}
    while pos < len(data):
        start, magic = pos, data[pos:pos + 8]
        pos += 8
        if magic == b'RDOK0000':
            pos = align4(start + struct.unpack_from('<I', data, pos)[0])
            continue
        if magic != b'IDOK0000':
            raise ValueError(f'unexpected kidsobjdb block {magic!r} at {start:#x}')
        _size, name, typ, n = struct.unpack_from('<4I', data, pos)
        pos += 16
        heads = [struct.unpack_from('<3I', data, pos + 12 * i) for i in range(n)]
        pos += 12 * n
        props, first, singles = [], None, []
        for k, (vt, count, pname) in enumerate(heads):
            fmt = SCALARS.get(vt) or VECTORS.get(vt)
            if fmt is None:
                raise ValueError(f'unsupported kidsobjdb value type {vt} at {start:#x}')
            size = struct.calcsize('<' + fmt)
            vals = [struct.unpack_from('<' + fmt, data, pos + size * i) for i in range(count)]
            vals = [v[0] if len(v) == 1 else v for v in vals]
            pos += size * count
            props.append((pname, vt, vals))
            integer = vt in (0, 1, 2, 3, 4, 5)
            if k == 0 and vals and integer:
                first = int(vals[0]) & 0xFFFFFFFF
            if count == 1 and integer:
                singles.append(int(vals[0]) & 0xFFFFFFFF)
        pos = align4(pos)
        out[name] = KidsEntry(name, typ, props, first, singles)
    return out


def ktid_candidates(model_hash, kids, records):
    """KTID tables linked to a model through the CharacterEditor kidsobjdb."""
    found = set()
    for entry in kids.values():
        if entry.first_value != model_hash:
            continue
        for ref in entry.singleton_ints:
            linked = kids.get(ref)
            if linked is None or linked.first_value is None or linked.first_value <= 10:
                continue
            rec = records.get(linked.first_value)
            if rec is not None and rec.type_hash in KTID_TYPES:
                found.add(linked.first_value)
    return sorted(found)


def parse_ktid(data, kids):
    """KTID payload: (slot index, kidsobjdb entry) pairs; the entry's first value is the G1T hash."""
    if len(data) % 8:
        raise ValueError('KTID payload is not a multiple of 8 bytes')
    out = {}
    for pos in range(0, len(data), 8):
        index, ref = struct.unpack_from('<2I', data, pos)
        linked = kids.get(ref)
        if linked is None or linked.first_value is None:
            raise ValueError(f'KTID entry {index} references unknown object {hx(ref)}')
        out[index] = linked.first_value
    return out


def model_slots(model):
    """{texture index: [(texture set, slot type, submeshes using the set, any of them visible)]} of one G1M."""
    by_set = defaultdict(list)
    for s in model.submeshes:
        by_set[s['material']].append(s)
    out = defaultdict(list)
    for tset, slots in enumerate(model.materials):
        subs = by_set.get(tset, [])
        visible = any(s['vertex_count'] > 3 and s['index_count'] > 3 and not g1m_tool.is_hidden(model, s) for s in subs)
        for slot in slots:
            out[slot['index']].append((tset, slot['type'], [s['id'] for s in subs], visible))
    return out


class GameData:
    def __init__(self, game_dir):
        self.dir = Path(game_dir)
        self.records = parse_rdb(self.dir / 'root.rdb', self.dir / 'root.rdx')
        self._kids = None

    def read(self, h):
        if h not in self.records:
            raise KeyError(f'{hx(h)} is not in root.rdb')
        return read_entry(self.records[h], self.dir)

    @property
    def kids(self):
        if self._kids is None:
            self._kids = parse_kidsobjdb(self.read(CHARACTER_EDITOR_DB))
        return self._kids


def extension(data, record):
    if data[:4] in (b'_M1G', b'_H1G'):
        return 'g1m'     # the player-face G1H is also overridden as 0x<hash>.g1m (confirmed in game)
    if data[:4] == b'GT1G' or record.type_hash in G1T_TYPES:
        return 'g1t'
    if record.type_hash in KTID_TYPES:
        return 'ktid'
    if record.type_hash == KIDSOBJDB_TYPE:
        return 'kidsobjdb'
    return 'bin'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def cmd_extract(args):
    game = GameData(args.game_data)
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for h in args.hash:
        data = game.read(h)
        path = out / f'0x{h:08x}.{extension(data, game.records[h])}'
        if path.exists():
            raise SystemExit(f'refusing to overwrite {path}')
        path.write_bytes(data)
        rows.append({'hash': hx(h), 'file': path.name, 'type': hx(game.records[h].type_hash), 'bytes': len(data),
                     'sha256': sha(data)})
    print(json.dumps(rows, indent=1))


def root_files(root):
    return {p.name.lower(): p for p in Path(root).iterdir() if p.is_file()} if root else {}


def cmd_slots(args):
    game = GameData(args.game_data)
    mod, base = root_files(args.mod_root), root_files(args.baseline_root)
    model = g1m_tool.parse(game.read(args.model))
    used = model_slots(model)
    tables = []
    for ktid in ([args.ktid] if args.ktid else ktid_candidates(args.model, game.kids, game.records)):
        slots = parse_ktid(game.read(ktid), game.kids)
        rows = []
        for index in sorted(slots):
            name = f'0x{slots[index]:08x}.g1t'
            row = {'slot': index, 'g1t': hx(slots[index]),
                   'uses': [{'texture_set': t, 'type': SLOT_TYPES.get(k, k), 'submeshes': s, 'visible': v}
                            for t, k, s, v in used.get(index, [])]}
            if name in mod:
                data = mod[name].read_bytes()
                row['mod'] = 'same as game' if slots[index] in game.records and data == game.read(slots[index]) else 'changed'
                if name in base:
                    row['vs_baseline'] = 'same' if data == base[name].read_bytes() else 'changed'
            rows.append(row)
        tables.append({'ktid': hx(ktid), 'slots': rows})
    report = {'model': hx(args.model), 'tables': tables}
    text = json.dumps(report, indent=1)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
    print(text)


def texture_usages(game, textures):
    """{texture hash: [dict(model, ktid, index, texture_set, type, visible)]} over every character model."""
    ref_to_tex = {e.name_hash: e.first_value for e in game.kids.values() if e.first_value in textures}
    ktid_models = defaultdict(set)
    for e in game.kids.values():
        rec = game.records.get(e.first_value) if e.first_value is not None else None
        if rec is None or rec.type_hash != G1M_TYPE:
            continue
        for ref in e.singleton_ints:
            linked = game.kids.get(ref)
            if linked is not None and linked.first_value in game.records and \
                    game.records[linked.first_value].type_hash in KTID_TYPES:
                ktid_models[linked.first_value].add(e.first_value)
    hits, failed = defaultdict(set), 0
    for rec in game.records.values():
        if rec.type_hash not in KTID_TYPES or not rec.internal:
            continue
        try:
            payload = read_entry(rec, game.dir)
        except (OSError, ValueError, zlib.error):
            failed += 1
            continue
        for pos in range(0, len(payload) - 7, 8):
            index, ref = struct.unpack_from('<2I', payload, pos)
            if ref in ref_to_tex:
                hits[ref_to_tex[ref]].add((rec.file_hash, index))
    cache, out = {}, defaultdict(list)
    for tex, pairs in hits.items():
        for ktid, index in sorted(pairs):
            for m in sorted(ktid_models.get(ktid, ())):
                if m not in cache:
                    try:
                        cache[m] = model_slots(g1m_tool.parse(game.read(m)))
                    except (OSError, ValueError, KeyError, struct.error, zlib.error):
                        cache[m] = None
                for tset, typ, _subs, visible in (cache[m] or {}).get(index, []):
                    out[tex].append({'model': hx(m), 'ktid': hx(ktid), 'index': index, 'texture_set': tset,
                                     'type': SLOT_TYPES.get(typ, typ), 'visible': visible})
    return out, {'ktid_unreadable': failed, 'models_parsed': sum(v is not None for v in cache.values())}


def cmd_usage(args):
    game = GameData(args.game_data)
    mod = root_files(args.mod_root)
    own = set(args.own_models or ())
    textures = {int(n[2:10], 16): p for n, p in mod.items() if n.endswith('.g1t')}
    usages, scan = texture_usages(game, set(textures))
    rows = []
    for h, path in sorted(textures.items()):
        data = path.read_bytes()
        state = 'not in game' if h not in game.records else ('same as game' if data == game.read(h) else 'changed')
        others = sorted({u['model'] for u in usages.get(h, []) if u['visible'] and int(u['model'], 16) not in own})
        mine = sorted({(u['model'], u['type'], u['visible']) for u in usages.get(h, []) if int(u['model'], 16) in own})
        rows.append({'g1t': hx(h), 'mod': state, 'other_visible_models': len(others), 'examples': others[:8],
                     'own_models': [list(x) for x in mine]})
    rows.sort(key=lambda r: (r['mod'] != 'changed', -r['other_visible_models']))
    risky = [r['g1t'] for r in rows if r['mod'] == 'changed' and r['other_visible_models']]
    report = {'mod_root': Path(args.mod_root).name, 'scan': scan, 'changed_and_shared': risky, 'textures': rows}
    text = json.dumps(report, indent=1)
    if args.output:
        Path(args.output).write_text(text, encoding='utf-8')
    print(text if not args.output else f'{len(risky)} changed textures are drawn by other models -> {args.output}')


def main(argv=None):
    hexint = lambda s: int(s, 16)  # noqa: E731
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('extract'); p.add_argument('--game-data', required=True)
    p.add_argument('--hash', type=hexint, action='append', required=True, help='repeatable, e.g. 0x1E76FD2D')
    p.add_argument('--output', required=True)
    p = sub.add_parser('slots'); p.add_argument('--game-data', required=True); p.add_argument('--model', type=hexint, required=True)
    p.add_argument('--ktid', type=hexint, help='skip discovery through the CharacterEditor kidsobjdb')
    p.add_argument('--mod-root', help='a RONPATCHER/root to compare'); p.add_argument('--baseline-root')
    p.add_argument('--output')
    p = sub.add_parser('usage'); p.add_argument('--game-data', required=True); p.add_argument('--mod-root', required=True)
    p.add_argument('--own-models', type=lambda s: [int(x, 16) for x in s.split(',')],
                   help='the models the mod replaces, e.g. 0x65152725,0x8DC92828,0xD462CD01')
    p.add_argument('--output')
    args = ap.parse_args(argv)
    {'extract': cmd_extract, 'slots': cmd_slots, 'usage': cmd_usage}[args.cmd](args)
    return 0


if __name__ == '__main__':
    sys.exit(main())
