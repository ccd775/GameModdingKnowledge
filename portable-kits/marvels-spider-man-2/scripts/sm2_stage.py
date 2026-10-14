"""Overstrike .stage (format_version 2, game MSM2) reader/writer. Pure stdlib so it also runs on the test PC.

Zip layout: info.json + "<span>/<ASSETID16HEX>" entries. Each entry is either raw archive bytes or an
STG wrapper: u32 'STG\\0' | u32 flags (1 = install header, 2 = install texture meta) | u32 header size |
u32 texture meta size | header | pad16 | texture meta | pad16 | archive bytes.
"""
import io, json, struct, zipfile

STG_MAGIC = 0x00475453
FLAG_HEADER, FLAG_TEXMETA = 1, 2


def crc64_path(path):
    """Asset id of a path (CRC64.Hash after normalisation: lowercase, '\\' -> '/', repeated '/' collapsed)."""
    from crc64_table import TABLE
    p = path.lower().replace(chr(92), '/')
    while '//' in p:
        p = p.replace('//', '/')
    data = p.encode('utf-8')
    v = 0xC96C5795D7870F42
    for b in data:
        v = TABLE[(v ^ b) & 0xFF] ^ (v >> 8)
    return (v >> 2) | 0x8000000000000000


def stg_wrap(data, header=None, texmeta=None):
    flags = (FLAG_HEADER if header is not None else 0) | (FLAG_TEXMETA if texmeta is not None else 0)
    if not flags:
        return bytes(data)
    out = bytearray(struct.pack('<IIII', STG_MAGIC, flags, len(header or b''), len(texmeta or b'')))
    for blob in (header, texmeta):
        if blob is not None:
            out += blob
            out += bytes(-len(out) % 16)
    out += data
    return bytes(out)


def stg_unwrap(blob):
    """-> (header|None, texmeta|None, data)"""
    if len(blob) >= 16 and struct.unpack_from('<I', blob, 0)[0] == STG_MAGIC:
        flags, hs, ts = struct.unpack_from('<III', blob, 4)
        p = 16
        header = blob[p:p + hs]
        p += hs
        p += -p % 16
        tm = blob[p:p + ts]
        p += ts
        p += -p % 16
        return (header if flags & FLAG_HEADER else None, tm if flags & FLAG_TEXMETA else None, blob[p:])
    return None, None, blob


def write_stage(path, assets, name, author, description=''):
    """assets: list of (span, asset_id:int, data, header|None, texmeta|None). Entries are stored, not deflated
    where large, to keep packing fast; Overstrike reads both."""
    info = {'game': 'MSM2', 'format_version': 2, 'name': name, 'author': author}
    if description:
        info['description'] = description
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as z:
        z.writestr('info.json', json.dumps(info, indent=1))
        for span, aid, data, header, texmeta in assets:
            z.writestr(f'{span}/{aid:016X}', stg_wrap(data, header, texmeta))


def read_stage(path):
    """-> (info, [(span, asset_id, header, texmeta, data)]) in zip order (Overstrike installs in zip order)."""
    out = []
    with zipfile.ZipFile(path) as z:
        info = json.loads(z.read('info.json')) if 'info.json' in z.namelist() else {}
        for e in z.infolist():
            if e.filename.endswith('/') or e.filename == 'info.json':
                continue
            top, _, rest = e.filename.replace(chr(92), '/').partition('/')
            if not top.isdigit() or not rest:
                continue
            span = int(top)
            if len(rest) == 16 and all(c in '0123456789abcdefABCDEF' for c in rest):
                aid = int(rest, 16)
            else:
                aid = crc64_path(rest)
            h, t, d = stg_unwrap(z.read(e))
            out.append((span, aid, h, t, d))
    return info, out
