"""Read the reference skeleton of a cooked UE 4.11 skeletal mesh (stock or game format).

FReferenceSkeleton is serialized as TArray<FMeshBoneInfo> (cooked: FName + int32 parent, 12 bytes) followed by
TArray<FTransform> (quat xyzw, translation, scale: 40 bytes). It is located by structure: a bone count N, N bone infos
whose first parent is -1 and every other parent is a smaller index, then the same N and N transforms.

read(path) -> dict(names, parents, local (N,4,4) row-major matrices, component (N,4,4), info_offset, pose_offset)
"""
import argparse, struct, sys
import numpy as np
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg

def quat_mat(x, y, z, w):
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])

def find(pkg, data):
    names = len(pkg.names)
    for o in range(0, len(data) - 16):
        n = struct.unpack_from('<i', data, o)[0]
        if not 2 <= n <= 4096 or o + 4 + 12 * n + 4 > len(data):
            continue
        ok = True
        for i in range(n):
            ni, num, par = struct.unpack_from('<iii', data, o + 4 + 12 * i)
            if not (0 <= ni < names and 0 <= num < 1000000 and (par == -1 if i == 0 else 0 <= par < i)):
                ok = False; break
        if ok and struct.unpack_from('<i', data, o + 4 + 12 * n)[0] == n:
            return o, n
    raise ValueError('reference skeleton not found')

def read(path):
    pkg = upkg.Package(open(path, 'rb').read())
    e = max(range(len(pkg.exports)), key=lambda i: pkg.exports[i]['SerialSize'])
    data = pkg.export_data(e)
    o, n = find(pkg, data)
    names, parents = [], []
    for i in range(n):
        ni, num, par = struct.unpack_from('<iii', data, o + 4 + 12 * i)
        names.append(pkg.name((ni, num))); parents.append(par)
    po = o + 4 + 12 * n + 4
    local = np.zeros((n, 4, 4)); comp = np.zeros((n, 4, 4))
    for i in range(n):
        x, y, z, w, tx, ty, tz, sx, sy, sz = struct.unpack_from('<10f', data, po + 40 * i)
        m = np.eye(4); m[:3, :3] = quat_mat(x, y, z, w) * np.array([sx, sy, sz]); m[:3, 3] = (tx, ty, tz)
        local[i] = m
        comp[i] = m if parents[i] < 0 else comp[parents[i]] @ m
    return {'names': names, 'parents': parents, 'local': local, 'component': comp,
            'info_offset': pkg.exports[e]['SerialOffset'] + o, 'pose_offset': pkg.exports[e]['SerialOffset'] + po}

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('mesh', help='cooked skeletal mesh or Skeleton .uasset')
    ap.add_argument('filter', nargs='?', help='only bones whose name contains this')
    args = ap.parse_args()
    r = read(args.mesh)
    print(len(r['names']), 'bones')
    for i, (nm, p) in enumerate(zip(r['names'], r['parents'])):
        if args.filter is None or args.filter in nm:
            print(i, nm, r['names'][p] if p >= 0 else '-', np.round(r['component'][i][:3, 3], 2))
