#!/usr/bin/env python3
"""Which game resources did Nioh3.exe read, per phase? (ETW Microsoft-Windows-Kernel-File -> tracerpt CSV)

Phases are delimited by marker files `MARK_<nn>_<name>.txt` created during the trace. Every Read event of the
game process on a package container (0x<hash>.fdata or data/xx/0x<hash>.file) is mapped back to the root.rdb
records whose stored byte range it overlaps.

usage: etw_reads.py <trace.csv> <package dir> <out.json> [--patched]   (game process = PID opening most containers)
Writes JSON: {phases: [{name, t0, resources: {hash: {type, size, bytes_read, first_t}}}]} and prints a summary.
"""
import argparse
import bisect
import csv
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata  # noqa: E402

TYPE_NAMES = {0x563BDEF1: 'g1m', 0xBEF563DD: 'g1m_meshlet', 0xAFBEC60C: 'g1t', 0xAD57EBBA: 'g1t_stream', 0x8E39AA37: 'ktid',
              0x20A6A0BB: 'kidsobjdb', 0x6FA91671: 'g1a', 0x7BCD279F: 'g1s', 0x54738C76: 'g1co', 0xA8D88566: 'g1cox',
              0x7461C7CA: 'g1h', 0x5C3E543C: 'swg', 0x27BC54B7: 'rigbin', 0x17614AF5: 'g1mx', 0x79C724C2: 'g1p',
              0xB340861A: 'mtl', 0x56EFE45C: 'grp', 0x1AB40AE8: 'oid', 0x753AA042: 'oidsq', 0x8D735C52: 'oboro',
              0x786DCD84: 'g1n', 0xB097D41F: 'g1e', 0x193D2E44: 'grbf', 0x32AC9403: 'g1fpose', 0x2BCC0C02: 'g1frani',
              0xDB0AE0AA: 'g1ii', 0x4D0102AC: 'g1em', 0x1A6300FD: 'g1es', 0xF20DE437: 'texinfo'}
CONTAINER = re.compile(r'\\(0x[0-9a-f]{8})\.(fdata|file)$', re.I)
MARK = re.compile(r'\\MARK_(\d+)_([^\\]+)\.txt$', re.I)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('trace', help='tracerpt CSV'); ap.add_argument('package'); ap.add_argument('out', help='output JSON')
    ap.add_argument('--patched', action='store_true', help='map through the installed root.rdb, not the .original backup')
    args = ap.parse_args()
    csv_path, pkg, out = Path(args.trace), Path(args.package), Path(args.out)
    patched = args.patched                     # map through the installed (modded) table instead of the vanilla backup
    orig = (pkg / 'root.rdb.original').exists() and not patched
    recs = ktdata.parse_rdb(pkg / ('root.rdb.original' if orig else 'root.rdb'), pkg / ('root.rdx.original' if orig else 'root.rdx'))
    by_container = defaultdict(list)          # container hash -> sorted [(start, end, file hash)]
    for r in recs.values():
        if r.internal and r.fdata_hash is not None:
            by_container[r.fdata_hash].append((r.fdata_offset, r.fdata_offset + r.fdata_full_size, r.file_hash))
        elif not r.internal:
            by_container[r.file_hash].append((0, 1 << 62, r.file_hash))
    starts = {}
    for k, v in by_container.items():
        v.sort()
        starts[k] = [s for s, _, _ in v]

    fileobj = {}       # FileObject -> container hash
    marks = []         # (t, name)
    pids = defaultdict(int)
    reads = []         # (t, container, offset, size)
    with csv_path.open(encoding='utf-8', errors='replace', newline='') as f:
        for row in csv.reader(f, skipinitialspace=True):
            if not row or not row[0].startswith('Microsoft-Windows-Kernel-File'):
                continue
            eid = row[1].strip()
            if eid == '12':                                     # Create: Irp, FileObject, Thread, Options, Attr, Share, FileName
                name = row[24] if len(row) > 24 else ''
                m = MARK.search(name)
                if m:
                    marks.append((int(row[15]), f'{m.group(1)}_{m.group(2)}'))
                    continue
                c = CONTAINER.search(name)
                if c:
                    fileobj[row[19].strip()] = int(c.group(1), 16)
                    pids[row[8].strip()] += 1
            elif eid == '15':                                   # Read: ByteOffset, Irp, FileObject, FileKey, Thread, IOSize, ...
                fo = row[20].strip()
                if fo in fileobj:
                    reads.append((int(row[15]), fileobj[fo], int(row[18], 0), int(row[23], 0), row[8].strip()))
    game_pid = max(pids, key=lambda k: pids[k])
    marks.sort()
    print('game pid', game_pid, 'container opens', dict(pids), 'reads', len(reads), 'marks', [m[1] for m in marks])

    phases = [{'name': 'before_' + (marks[0][1] if marks else 'end'), 't0': 0, 'resources': {}}] + \
             [{'name': n, 't0': t, 'resources': {}} for t, n in marks]
    tstarts = [p['t0'] for p in phases]
    for t, cont, off, size, pid in sorted(reads):
        if pid != game_pid or cont not in by_container:
            continue
        ph = phases[bisect.bisect_right(tstarts, t) - 1]
        lst, st = by_container[cont], starts[cont]
        i = max(bisect.bisect_right(st, off) - 1, 0)
        while i < len(lst) and lst[i][0] < off + size:
            s, e, h = lst[i]
            if e > off:
                r = recs[h]
                d = ph['resources'].setdefault(f'0x{h:08x}', {'type': TYPE_NAMES.get(r.type_hash, f'{r.type_hash:08X}'),
                                                             'size': r.file_size, 'stored': r.fdata_full_size,
                                                             'container': f'0x{cont:08x}', 'bytes_read': 0, 'first_t': t})
                d['bytes_read'] += min(e, off + size) - max(s, off)
            i += 1
    out.write_text(json.dumps({'game_pid': game_pid, 'phases': phases}, indent=1))
    for p in phases:
        c = defaultdict(int)
        for v in p['resources'].values():
            c[v['type']] += 1
        print(p['name'], len(p['resources']), dict(sorted(c.items(), key=lambda x: -x[1])[:12]))


if __name__ == '__main__':
    main()
