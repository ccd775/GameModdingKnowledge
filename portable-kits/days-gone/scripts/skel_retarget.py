"""Set the translation retargeting mode of bones in a cooked Skeleton asset (game format).

The Skeleton export's BoneTree (TArray<FBoneNode>, one per reference-skeleton bone) holds
TranslationRetargetingMode as a ByteProperty enum (FName value). Only the FName changes, so the property layout stays
the same; the new enum name is appended to the name table.

usage (numpy): skel_retarget.py <in Skeleton.uasset> <out.uasset> <regex>=<Animation|AnimationRelative|Skeleton|AnimationScaled> ...
"""
import argparse, re, struct, sys
sys.path.insert(0, __import__("os").path.dirname(__import__("os").path.abspath(__file__)))
import upkg, refskel

def patch(src, dst, rules):
    pkg = upkg.Package(open(src, "rb").read())
    sk = next(i for i, e in enumerate(pkg.exports) if pkg.ref(e["Class"]).endswith(".Skeleton"))
    d = bytearray(pkg.export_data(sk))
    o, n = refskel.find(pkg, bytes(d))
    names = [pkg.name(struct.unpack_from("<ii", d, o + 4 + 12 * i)[:2]) for i in range(n)]
    bt = next(p for p in upkg.parse_props(pkg, bytes(d)) if p.name == "BoneTree")
    assert len(bt.children) == n, (len(bt.children), n)
    changed = {}
    for i, el in enumerate(bt.children):
        for pat, mode in rules:
            if re.search(pat, names[i]):
                c = next(c for c in el if c.name == "TranslationRetargetingMode")
                d[c.vstart:c.vstart + 8] = struct.pack("<ii", pkg.name_index("EBoneTranslationRetargetingMode::" + mode), 0)
                changed[names[i]] = mode
                break
    datas = [pkg.export_data(i) for i in range(len(pkg.exports))]
    datas[sk] = bytes(d)
    out = pkg.write(datas)
    open(dst, "wb").write(out)
    return changed

if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("src"); ap.add_argument("dst")
    ap.add_argument("rules", nargs="*", metavar="regex=mode")
    args = ap.parse_args()
    rules = [tuple(a.split("=", 1)) for a in args.rules]
    ch = patch(args.src, args.dst, rules)
    print(len(ch), "bones changed", sorted(set(ch.values())))
