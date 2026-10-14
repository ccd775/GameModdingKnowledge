"""Shared helpers for the SM2 project: paths, ALERT import, toc loading, name index.

Environment: SM2_GAME = game folder (toc, dagstr; no default, needed by load_toc and sm2_index.py);
SM2_WORK = work folder for native/, reports/, build_* (default: the folder above scripts/);
SM2_ALERT = ALERT checkout that provides dat1lib (default: ext/ALERT in the folder above scripts/).
dat1lib is imported on first use, so the scripts' --help works without ALERT."""
import os, sys, json, re, struct
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
WORK = os.environ.get('SM2_WORK') or KIT
PROJECT = os.path.dirname(WORK)
ALERT = os.environ.get('SM2_ALERT') or os.path.join(KIT, 'ext', 'ALERT')
if ALERT not in sys.path:
    sys.path.insert(0, ALERT)

GAME = os.environ.get('SM2_GAME')
NATIVE = os.path.join(WORK, 'native')
REPORTS = os.path.join(WORK, 'reports')
INDEX = os.path.join(NATIVE, 'asset_index.json')


def game_dir():
    if not GAME:
        raise SystemExit('SM2_GAME is not set: point it at the game folder (the one with toc and dagstr)')
    return GAME


def alert():
    """ALERT's dat1lib (GPLv3, not bundled), imported on first use."""
    try:
        import dat1lib
        import dat1lib.crc64     # noqa: F401
    except ImportError as e:
        raise SystemExit(f'ALERT dat1lib not found in {ALERT}: clone https://github.com/Tkachov/ALERT there '
                         'or set SM2_ALERT') from e
    return dat1lib


def load_toc(path=None):
    dat1lib = alert()
    path = path or os.path.join(game_dir(), 'toc')
    with open(path, 'rb') as f:
        toc = dat1lib.read(f)
    toc.set_archives_dir(game_dir())
    return toc


def norm(p):
    return p.replace('/', chr(92)).lower()


def asset_id(path):
    return alert().crc64.hash(path)


def load_index():
    with open(INDEX, encoding='utf-8') as f:
        return json.load(f)


def header_at(toc, off):
    """i30 asset header (variable length, see Overstrike AssetHeadersSection_I30)."""
    buf = toc.get_asset_headers_section()._raw
    pairs = buf[off + 5]
    extra = struct.unpack_from('<H', buf, off + 6)[0]
    return bytes(buf[off:off + 8 + pairs * 8 + extra])


def entry(toc, i):
    """ALERT's get_asset_entry_by_index assumes 36-byte (i29) headers; i30 headers are variable length."""
    import dat1lib.types.toc2 as t2
    sz = toc.get_sizes_section().entries[i]
    header = header_at(toc, sz.header_offset) if sz.header_offset >= 0 else None
    return t2.AssetEntry(i, toc.get_assets_section().ids[i], sz.archive_index, sz.offset, sz.value, header)


def find_entry(toc, aid, span=None):
    """Return (index, entry) of asset id in the given span (default: first match)."""
    ids = toc.get_assets_section().ids
    spans = toc.get_spans_section().entries
    rng = range(len(ids))
    if span is not None:
        s = spans[span]
        rng = range(s.asset_index, s.asset_index + s.count)
    for i in rng:
        if ids[i] == aid:
            return i, entry(toc, i)
    return None, None


def extract(toc, path_or_id, span=0):
    aid = path_or_id if isinstance(path_or_id, int) else asset_id(path_or_id)
    i, e = find_entry(toc, aid, span)
    if e is None:
        raise KeyError(f'{path_or_id} not found in span {span}')
    return bytes(toc.extract_asset(e)), e
