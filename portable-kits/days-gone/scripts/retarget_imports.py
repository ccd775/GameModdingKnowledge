"""Rename import object paths in a cooked package, e.g. point a mesh at the game's skeleton.
usage: retarget_imports.py <in.uasset> <out.uasset> <old_package_path>=<new_package_path> ...
The package import and its object import (same short name as the package) are both renamed."""
import argparse, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg

def retarget(pkg, old, new):
    old_obj, new_obj = old.rsplit('/', 1)[1], new.rsplit('/', 1)[1]
    hit = 0
    for i, im in enumerate(pkg.imports):
        if pkg.name(im['ClassName']) == 'Package' and pkg.name(im['Name']) == old:
            im['Name'] = (pkg.name_index(new), 0); hit += 1
            for j, ob in enumerate(pkg.imports):
                if ob['Outer'] == -i - 1 and pkg.name(ob['Name']) == old_obj:
                    ob['Name'] = (pkg.name_index(new_obj), 0); hit += 1
    if hit != 2: raise SystemExit('retarget %s: %d imports changed' % (old, hit))

if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('mappings', nargs='*', metavar='old_package_path=new_package_path')
    args = ap.parse_args()
    pkg = upkg.Package(open(args.src, 'rb').read())
    for a in args.mappings:
        o, n = a.split('=')
        retarget(pkg, o, n)
    out = pkg.write()
    q = upkg.Package(out)
    for i in range(len(q.imports)): print('imp', -i - 1, q.obj_path(-i - 1))
    open(args.dst, 'wb').write(out)
