"""Integrity scan of Nioh 2 K300 archives (read-only): every compressed chunk must inflate (zlib adler32), every
entry must decode to its declared size; uncompressed data is flagged when a whole 4 KiB-aligned file page is zero
(the corruption signature seen on this disk). Also checks loose files in the game dir for zero pages.
usage: n2verify.py <game dir> <out.txt>"""
import os
import struct
import sys
import time
import zlib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import n2lnk  # noqa: E402

PAGE = 4096
ZERO = bytes(PAGE)


def zero_pages(buf, base):
    first = (-base) % PAGE
    return [base + i for i in range(first, len(buf) - PAGE + 1, PAGE) if buf[i:i + PAGE] == ZERO]


def main(gdir, out):
    adir = os.path.join(gdir, 'archive')
    log = open(out, 'w', encoding='utf-8')
    t0 = time.time()
    tot_bad = 0
    for a in range(64):
        p = n2lnk.arch_path(adir, a)
        if not os.path.exists(p):
            continue
        ents, fsize, align = n2lnk.table(p)
        bad = zp = 0
        with open(p, 'rb') as f:
            for e, (off, size, zs, z) in enumerate(ents):
                if zs == 0:
                    continue
                f.seek(off)
                data = f.read(zs)
                try:
                    if z:
                        pos = got = 0
                        while got < size and pos + 4 <= len(data):
                            n = struct.unpack_from('<I', data, pos)[0]
                            pos += 4
                            if n & 0x8000:
                                got += len(zlib.decompress(data[pos:pos + (n & 0x7FFF)]))
                                n &= 0x7FFF
                            else:
                                got += n
                                zz = zero_pages(data[pos:pos + n], off + pos)
                                if zz:
                                    zp += 1
                                    log.write(f'ZEROPAGE a{a:02d} e{e} raw-chunk pages {[hex(x) for x in zz[:4]]}\n')
                            pos += n
                            pos += (-pos) % 16
                        if got != size:
                            raise ValueError(f'size {got} != {size}')
                    else:
                        zz = zero_pages(data, off)
                        if zz and size > 2 * PAGE:
                            zp += 1
                            log.write(f'ZEROPAGE a{a:02d} e{e} raw size {size} pages {len(zz)} first {hex(zz[0])}\n')
                except Exception as ex:  # noqa: BLE001
                    bad += 1
                    log.write(f'BAD a{a:02d} e{e} off {off:#x} size {size} zs {zs}: {ex}\n')
        tot_bad += bad
        log.write(f'archive_{a:02d}: {len(ents)} entries, bad {bad}, zero-page flags {zp}, {time.time() - t0:.0f}s\n')
        log.flush()
    for name in sorted(os.listdir(gdir)):
        fp = os.path.join(gdir, name)
        if os.path.isfile(fp) and os.path.getsize(fp) > 2 * PAGE and not name.lower().endswith(('.txt', '.ini')):
            zz = zero_pages(open(fp, 'rb').read(), 0)
            log.write(f'file {name}: {os.path.getsize(fp)} bytes, zero pages {len(zz)} {[hex(x) for x in zz[:6]]}\n')
    log.write(f'DONE bad={tot_bad} {time.time() - t0:.0f}s\n')
    log.close()


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('gdir', metavar='game_dir', help='the Nioh 2 folder (archive/ inside)')
    ap.add_argument('out', metavar='out.txt')
    a = ap.parse_args()
    main(a.gdir, a.out)
