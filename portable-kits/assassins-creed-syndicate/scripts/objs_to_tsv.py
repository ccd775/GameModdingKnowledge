"""Turn `AcuHarness scan-objs` logs into the table list build_mod.py reads.

  python objs_to_tsv.py <out.tsv> <objs.log> [...]

A log holds "== <forge>" headers followed by "OBJ<TAB>objIDHEX<TAB>objName<TAB><dataIDHEX>_<dataName>" lines.
Output rows: forge, data file IDHEX, data file name, object IDHEX (sorted, unique). Lines starting "ERR" are reported.
"""
import argparse


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out_tsv")
    ap.add_argument("logs", nargs="+", help="scan_objs.py logs")
    a = ap.parse_args()
    rows, errs = set(), []
    for log in a.logs:
        forge = None
        for line in open(log, encoding="utf-8", errors="replace"):
            line = line.rstrip("\n")
            if line.startswith("== "):
                forge = line[3:].strip()
            elif line.startswith("OBJ\t"):
                _, oid, _, label = line.split("\t", 3)
                did, name = label.split("_", 1)
                rows.add((forge, did, name, oid))
            elif line.startswith("ERR"):
                errs.append(f"{forge}: {line}")
    with open(a.out_tsv, "w", encoding="utf-8") as f:
        for r in sorted(rows):
            f.write("\t".join(r) + "\n")
    print(f"{len(rows)} rows, {len({(r[0], r[1]) for r in rows})} data files -> {a.out_tsv}")
    for e in errs:
        print("ERR", e)


if __name__ == "__main__":
    main()
