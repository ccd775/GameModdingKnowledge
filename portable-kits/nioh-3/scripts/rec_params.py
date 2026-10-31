"""Dump the root.rdb record parameter block and the fdata entry parameter block of resources.
usage: rec_params.py <package> <hash> [...]"""
import argparse, struct, sys
from pathlib import Path
ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package'); ap.add_argument('hashes', nargs='+', metavar='hash')
args = ap.parse_args()
sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata
pkg = Path(args.package)
rdb_p = pkg / 'root.rdb.original' if (pkg / 'root.rdb.original').exists() else pkg / 'root.rdb'
rdx_p = pkg / 'root.rdx.original' if (pkg / 'root.rdx.original').exists() else pkg / 'root.rdx'
rdb = rdb_p.read_bytes(); recs = ktdata.parse_rdb(rdb_p, rdx_p)
for a in args.hashes:
    r = recs[int(a, 16)]; p = r.rdb_offset
    trailer = struct.unpack_from('<Q', rdb, p + 0x10)[0]
    print(a, 'type %08X size %d entry_size %d trailer %d flags %08X entry_type %08X' % (r.type_hash, r.file_size, r.entry_size, trailer, r.flags, struct.unpack_from('<I', rdb, p + 0x20)[0]))
    params = rdb[p + 0x30:p + r.entry_size - trailer]
    print('  rdb params', len(params), params.hex())
    with (pkg / f'0x{r.fdata_hash:08x}.fdata').open('rb') as f:
        f.seek(r.fdata_offset); head = f.read(48)
        es, packed, size = struct.unpack_from('<3Q', head, 8); k4 = struct.unpack_from('<4I', head, 32)
        fp = f.read(es - packed - 48)
    print('  fdata hdr', es, packed, size, ['%08X' % x for x in k4], 'params', len(fp), fp.hex())
