"""Rewrite the local ref pose of the two root bones of a cooked Deacon-skeleton mesh to the reference mod's layout:
'Armature' = -90 deg about X, 'Align' = identity. Component-space poses are unchanged (identity * R == R * identity),
so the inverse bind matrices stay valid. Every serialized copy of the [Armature, Align] transform pair is patched.
usage: fix_root_pose.py <in.uasset> <out.uasset>"""
import argparse, struct, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg

def tr(q, t=(0, 0, 0), s=(1, 1, 1)):
    return struct.pack('<10f', *q, *t, *s)

def main(src, dst):
    pkg = upkg.Package(open(src, 'rb').read())
    d = bytearray(pkg.export_data(0))
    h = 0.70710677
    found = []
    one = struct.pack('<f', 1.0)
    i = 0
    while True:
        i = d.find(one, i)
        if i < 0: break
        i -= 12          # candidate quaternion start (w = 1)
        if i < 0: i += 16; continue
        a = struct.unpack_from('<10f', d, i)
        if not all(abs(x) < 1e-4 for x in a[0:3]):
            i += 16; continue
        b = struct.unpack_from('<10f', d, i + 40) if i + 80 <= len(d) else None
        if b and all(abs(x) < 1e-4 for x in a[4:7]) and all(abs(x - 1) < 1e-4 for x in a[7:10]) \
                and abs(abs(b[0]) - h) < 1e-3 and abs(abs(b[3]) - h) < 1e-3 and abs(b[1]) < 1e-4 and abs(b[2]) < 1e-4 \
                and b[0] * b[3] < 0 and all(abs(x) < 1e-3 for x in b[4:7]):
            found.append(i)
        i += 16
    if not found: raise SystemExit('root pose pair not found')
    for i in found:
        d[i:i + 80] = tr((-h, 0, 0, h)) + tr((0, 0, 0, 1))
    print('patched', len(found), 'copies at', found)
    open(dst, 'wb').write(pkg.write([bytes(d)]))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src', help='cooked mesh .uasset'); ap.add_argument('dst', help='output .uasset')
    args = ap.parse_args()
    main(args.src, args.dst)
