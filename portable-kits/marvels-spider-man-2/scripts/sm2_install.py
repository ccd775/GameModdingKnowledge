"""Headless installer for MSM2 .stage (v2) mods, following Overstrike's MetaInstaller_I29 + StageInstaller_I29_V2:
  1. toc.BAK is created once from the pristine toc; every install starts by copying toc.BAK over toc.
  2. mod i is written to d/mods/mod<i> (raw, uncompressed) and appended to the toc archive list.
  3. each asset: find-or-insert in its span, set archive/offset/size, header (in place if same length, else
     appended), texture meta (set or insert); then assets are sorted by id inside every span; toc saved.
Pure stdlib (runs on the test PC's Python 3.12).

  python sm2_install.py --game "<game folder>" install a.stage [b.stage ...]
  python sm2_install.py --game ... uninstall          # toc <- toc.BAK, delete d/mods/mod*
  python sm2_install.py --game ... status
"""
import argparse, bisect, glob, hashlib, json, os, shutil, struct, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sm2_dat1 import DAT1           # noqa: E402
from sm2_stage import read_stage    # noqa: E402

TOC_MAGIC = 0x34E89035
T_SPANS, T_IDS, T_SIZES, T_ARCH = 0xEDE8ADA9, 0x506D7B8A, 0x65BCF461, 0x398ABFF0
T_TEXIDS, T_TEXMETA, T_TEXHDR, T_HDRS = 0x36A6C8CC, 0xC9FB9DDA, 0x62297090, 0x654BDED9


class TOC:
    def __init__(self, path):
        raw = open(path, 'rb').read()
        assert struct.unpack_from('<I', raw, 0)[0] == TOC_MAGIC, 'not an i29/i30 toc'
        self.d = DAT1(raw, 8)
        g = self.d.get
        s = g(T_SPANS)
        self.spans = [list(struct.unpack_from('<II', s, 8 * i)) for i in range(len(s) // 8)]
        ids = g(T_IDS)
        self.ids = list(struct.unpack(f'<{len(ids) // 8}Q', ids))
        sz = g(T_SIZES)
        self.sizes = [list(struct.unpack_from('<IIIi', sz, 16 * i)) for i in range(len(sz) // 16)]   # size, arch, off, hdr
        a = g(T_ARCH)
        self.archives = [bytes(a[66 * i:66 * (i + 1)]) for i in range(len(a) // 66)]
        t = g(T_TEXIDS)
        self.tex_ids = list(struct.unpack(f'<{len(t) // 8}Q', t))
        self.tex_meta = bytearray(g(T_TEXMETA))
        self.headers = bytearray(g(T_HDRS))

    # -- archives
    def archive_name(self, i):
        return self.archives[i][:40].split(b'\0')[0].decode('ascii')

    def add_archive(self, filename):
        fn = filename.encode('ascii')
        assert len(fn) < 40
        e = fn + bytes(40 - len(fn)) + struct.pack('<QQIHI', 2678794514496, 2678794514496, 3844228203, 32763, 0)
        self.archives.append(e)
        return len(self.archives) - 1

    # -- assets
    def header_len(self, off):
        return 8 + self.headers[off + 5] * 8 + struct.unpack_from('<H', self.headers, off + 6)[0]

    def get_header(self, i):
        off = self.sizes[i][3]
        return None if off == -1 else bytes(self.headers[off:off + self.header_len(off)])

    def find(self, span, aid):
        st, cnt = self.spans[span]
        j = bisect.bisect_left(self.ids, aid, st, st + cnt)
        return j if j < st + cnt and self.ids[j] == aid else None

    def find_or_add(self, span, aid):
        j = self.find(span, aid)
        if j is not None:
            return j, False
        st, cnt = self.spans[span]
        j = bisect.bisect_left(self.ids, aid, st, st + cnt)
        self.spans[span][1] += 1
        for k in range(span + 1, len(self.spans)):
            self.spans[k][0] += 1
        self.ids.insert(j, aid)
        self.sizes.insert(j, [0, 0, 0, -1])
        return j, True

    def overwrite(self, span, aid, archive, offset, size, header, texmeta):
        j, added = self.find_or_add(span, aid)
        e = self.sizes[j]
        e[1], e[2], e[0] = archive, offset, size
        if header is not None:
            old = e[3]
            if old != -1 and self.header_len(old) == len(header):
                self.headers[old:old + len(header)] = header
            else:
                e[3] = len(self.headers)
                self.headers += header
        if texmeta is not None:
            assert len(texmeta) == 72
            k = bisect.bisect_left(self.tex_ids, aid)
            if k < len(self.tex_ids) and self.tex_ids[k] == aid:
                self.tex_meta[72 * k:72 * k + 72] = texmeta
            else:
                self.tex_ids.insert(k, aid)
                self.tex_meta[72 * k:72 * k] = texmeta
        return added

    def sort(self):
        for st, cnt in self.spans:
            rows = sorted(zip(self.ids[st:st + cnt], self.sizes[st:st + cnt]), key=lambda r: r[0])
            self.ids[st:st + cnt] = [r[0] for r in rows]
            self.sizes[st:st + cnt] = [r[1] for r in rows]

    def save(self, path):
        d = self.d
        d.set(T_SPANS, b''.join(struct.pack('<II', *s) for s in self.spans))
        d.set(T_IDS, struct.pack(f'<{len(self.ids)}Q', *self.ids))
        d.set(T_SIZES, b''.join(struct.pack('<IIIi', *s) for s in self.sizes))
        d.set(T_ARCH, b''.join(self.archives))
        d.set(T_TEXIDS, struct.pack(f'<{len(self.tex_ids)}Q', *self.tex_ids))
        d.set(T_TEXMETA, bytes(self.tex_meta))
        d.set(T_TEXHDR, struct.pack('<I', len(self.tex_ids)))
        d.set(T_HDRS, bytes(self.headers))
        body = d.save()
        with open(path, 'wb') as f:
            f.write(struct.pack('<II', TOC_MAGIC, len(body)) + body)


def sha1(p):
    return hashlib.sha1(open(p, 'rb').read()).hexdigest()


def install(game, stages, log):
    toc_p, bak_p = os.path.join(game, 'toc'), os.path.join(game, 'toc.BAK')
    if not os.path.exists(bak_p):
        shutil.copyfile(toc_p, bak_p)
        log(f'created toc.BAK (sha1 {sha1(bak_p)[:12]})')
    shutil.copyfile(bak_p, toc_p)
    mods = os.path.join(game, 'd', 'mods')
    os.makedirs(mods, exist_ok=True)
    for old in glob.glob(os.path.join(mods, 'mod*')):
        os.remove(old)
    toc = TOC(toc_p)
    report = []
    for i, st in enumerate(stages):
        info, assets = read_stage(st)
        rel = 'd' + chr(92) + 'mods' + chr(92) + f'mod{i}'
        ai = toc.add_archive(rel)
        with open(os.path.join(mods, f'mod{i}'), 'wb') as f:
            for span, aid, header, texmeta, data in assets:
                off = f.tell()
                f.write(data)
                added = toc.overwrite(span, aid, ai, off, len(data), header, texmeta)
                report.append(dict(mod=i, span=span, id=f'{aid:016X}', size=len(data), added=added,
                                   header=header is not None, texmeta=texmeta is not None))
        log(f'mod{i}: {info.get("name")} -> {len(assets)} assets')
    toc.sort()
    toc.save(toc_p)
    log(f'toc saved: {len(toc.ids)} assets, {len(toc.archives)} archives, sha1 {sha1(toc_p)[:12]}')
    return report


def uninstall(game, log):
    toc_p, bak_p = os.path.join(game, 'toc'), os.path.join(game, 'toc.BAK')
    if os.path.exists(bak_p):
        shutil.copyfile(bak_p, toc_p)
        log('toc restored from toc.BAK')
    for old in glob.glob(os.path.join(game, 'd', 'mods', 'mod*')):
        os.remove(old)
        log(f'removed {old}')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', required=True)
    ap.add_argument('cmd', choices=['install', 'uninstall', 'status'])
    ap.add_argument('stages', nargs='*')
    ap.add_argument('--report')
    a = ap.parse_args()
    log = lambda s: print(s, flush=True)
    if a.cmd == 'install':
        rep = install(a.game, a.stages, log)
        if a.report:
            json.dump(rep, open(a.report, 'w'), indent=1)
    elif a.cmd == 'uninstall':
        uninstall(a.game, log)
    else:
        toc = TOC(os.path.join(a.game, 'toc'))
        mods = [toc.archive_name(i) for i in range(len(toc.archives)) if 'mods' in toc.archive_name(i)]
        log(f'toc sha1 {sha1(os.path.join(a.game, "toc"))[:12]}, archives {len(toc.archives)}, mod archives {mods}, '
            f'toc.BAK {"present" if os.path.exists(os.path.join(a.game, "toc.BAK")) else "absent"}')


if __name__ == '__main__':
    main()
