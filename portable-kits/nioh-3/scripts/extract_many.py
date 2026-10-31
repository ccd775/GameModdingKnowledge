"""Extract many vanilla resources (from root.rdb.original when present), skipping ones that fail to decode.
usage: extract_many.py <package> <out dir> <hash list file | hash> [...]"""
import argparse
import dataclasses
import struct
import sys
from pathlib import Path

ap = argparse.ArgumentParser(description=__doc__)
ap.add_argument('package'); ap.add_argument('out', help='output dir')
ap.add_argument('hashes', nargs='+', metavar='hash_or_list_file')
args = ap.parse_args()

sys.path.insert(0, str(Path(__file__).resolve().parent))
import ktdata  # noqa: E402

pk, out = Path(args.package), Path(args.out)
rdb = pk / 'root.rdb.original' if (pk / 'root.rdb.original').exists() else pk / 'root.rdb'
rdx = pk / 'root.rdx.original' if (pk / 'root.rdx.original').exists() else pk / 'root.rdx'
recs = ktdata.parse_rdb(rdb, rdx)
hashes = []
for a in args.hashes:
    hashes += Path(a).read_text().split() if Path(a).is_file() else [a]
out.mkdir(parents=True, exist_ok=True)
ok = bad = 0
for a in hashes:
    h = int(a, 16)
    r = recs[h]
    try:
        data = ktdata.read_entry(r, pk)
    except ValueError as e:
        # some records (e.g. type 0x563BDEF1 models) store the packed size in root.rdb; take the entry header's size
        with (pk / f'0x{r.fdata_hash:08x}.fdata').open('rb') as f:
            f.seek(r.fdata_offset); head = f.read(48)
        size = struct.unpack_from('<3Q', head, 8)[2]
        try:
            data = ktdata.read_entry(dataclasses.replace(r, file_size=size), pk)
            print(f'0x{h:08x} header size {size} (rdb says {r.file_size})')
        except Exception as e2:  # noqa: BLE001
            print(f'0x{h:08x} FAIL {e} / {e2}'); bad += 1; continue
    p = out / f'0x{h:08x}.{ktdata.extension(data, recs[h])}'
    if not p.exists():
        p.write_bytes(data)
    ok += 1
print('ok', ok, 'failed', bad)
