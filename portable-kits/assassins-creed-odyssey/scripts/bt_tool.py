"""BuildTable / schema-XML helpers for Odyssey (AnvilToolkit schema XML, type="1").

  python bt_tool.py show <table.xml>
  python bt_tool.py edit <in.xml> <out.xml> [--drop COL[,COL...]] [--set COL=ID[:PATH] ...] [--clear-dynres]
  python bt_tool.py lodsel <in.LODSelector.xml> <out.xml> --lod I=ID[:PATH] [...]

edit: --drop removes the row cell (DynamicProperty Name="COL", any value type incl. GraphicVisualProperty) from every
      BuildRow; --set rewrites the referenced ID (and Path) of a Handle/Reference cell in every row that has it;
      --clear-dynres empties every row's DynamicResources (handles the engine loads with the row, e.g. hair meshes).
lodsel: points LOD descriptor I (0-based) at another GraphicObject.
Every write also adds ReferenceType="1" to null References that lack it: the exporter drops the attribute and
compile-xml would then write 0 instead of the vanilla 1 (4 bytes differ on the Kassandra VisualMaster otherwise).
"""
import re
import sys

CELL_RE = re.compile(r'\s*<DynamicProperty Name="(\d+)"[^>]*>\s*<(Handle|Reference)\b[^>]*>[^<]*</\2>\s*</DynamicProperty>')
ANYCELL_RE = re.compile(r'\s*<DynamicProperty Name="(\d+)"[^>]*>(?:(?!<DynamicProperty[ >]).)*?</DynamicProperty>', re.S)
DYNRES_RE = re.compile(r'<DynamicSmallArray Name="DynamicResources" Type="Handle">.*?</DynamicSmallArray>', re.S)
NULL_RE = re.compile(r'<Reference (?![^>]*ReferenceType=)([^>]*PointerType="Null"[^>]*)/>')


def fix_null_refs(x):
    return NULL_RE.sub(lambda m: f'<Reference {m.group(1).rstrip()} ReferenceType="1" />', x)


def split_rows(x):
    parts = re.split(r'(?=<BaseObject ID="\d+" Type="BuildRow">)', x)
    return parts[0], parts[1:]


def show(path):
    x = open(path, encoding="utf-8-sig").read()
    cols = re.findall(r'<Unsigned32 Name="ColumnID">(\d+)</Unsigned32>.*?<DynamicProperty Name="Type"[^>]*ObjectType="(\w+)"', x, re.S)
    print("columns", cols)
    _, rows = split_rows(x)
    for i, r in enumerate(rows):
        w = re.search(r'Name="Weight">([^<]+)', r)
        tags = re.findall(r'EngineTagSave">(\d+)', r)
        print(f"row {i} w={w.group(1) if w else '?'} tags={tags}")
        for m in ANYCELL_RE.finditer(r):
            if m.group(1) == "Type":
                continue
            path = re.search(r'(?:<Handle|<Reference)[^>]*External[^>]*Path="([^"]*)"|<Handle[^>]*Path="([^"]*)"', m.group(0))
            val = re.search(r'>(\d+)</(?:Handle|Reference)', m.group(0))
            p = (path.group(1) or path.group(2)).split("\\")[-1] if path else ""
            print("   ", m.group(1), p, val.group(1) if val else "")


def edit(src, dst, drops, sets, clear_dynres=False):
    x = open(src, encoding="utf-8-sig").read()
    head, rows = split_rows(x)
    n_drop = n_set = 0
    out = []
    for r in rows:
        def drop(m):
            nonlocal n_drop
            if m.group(1) in drops:
                n_drop += 1
                return ""
            return m.group(0)
        r = ANYCELL_RE.sub(drop, r)

        def repl(m):
            nonlocal n_set
            col = m.group(1)
            if col in sets:
                n_set += 1
                oid, path = sets[col]
                s = re.sub(r'>\d+</', lambda _: f'>{oid}</', m.group(0))
                if path is not None:
                    s = re.sub(r'Path="[^"]*"', lambda _: f'Path="{path}"', s)
                return s
            return m.group(0)
        out.append(CELL_RE.sub(repl, r))
    y = head + "".join(out)
    n_dyn = 0
    if clear_dynres:
        y, n_dyn = DYNRES_RE.subn('<DynamicSmallArray Name="DynamicResources" Type="Handle" />', y)
    y = fix_null_refs(y)
    open(dst, "w", encoding="utf-8-sig").write(y)
    print(f"edit: dropped {n_drop} cells, set {n_set} cells, cleared {n_dyn} DynamicResources -> {dst}")


def lodsel(src, dst, lods):
    x = open(src, encoding="utf-8-sig").read()
    descs = re.split(r'(?=<BaseObject ID="\d+" Type="LODDescriptor">)', x)
    for i, (oid, path) in lods.items():
        d = descs[i + 1]
        m = re.search(r'<Reference Name="Object"[^>]*>\d+</Reference>', d)
        s = re.sub(r'>\d+</', lambda _: f'>{oid}</', m.group(0))
        if path is not None:
            s = re.sub(r'Path="[^"]*"', lambda _: f'Path="{path}"', s)
        descs[i + 1] = d.replace(m.group(0), s)
    open(dst, "w", encoding="utf-8-sig").write(fix_null_refs("".join(descs)))
    print(f"lodsel: {sorted(lods)} -> {dst}")


def parse_sets(items):
    sets = {}
    for it in items:
        col, rest = it.split("=", 1)
        oid, _, path = rest.partition(":")
        sets[col] = (oid, path or None)
    return sets


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("show")
    p.add_argument("table_xml")
    p = sub.add_parser("edit")
    p.add_argument("in_xml")
    p.add_argument("out_xml")
    p.add_argument("--drop", help="COL[,COL...]")
    p.add_argument("--set", action="append", default=[], help="COL=ID[:PATH] (repeatable)")
    p.add_argument("--clear-dynres", action="store_true")
    p = sub.add_parser("lodsel")
    p.add_argument("in_xml")
    p.add_argument("out_xml")
    p.add_argument("--lod", action="append", default=[], help="I=ID[:PATH] (repeatable)")
    a = ap.parse_args()
    if a.cmd == "show":
        show(a.table_xml)
    elif a.cmd == "edit":
        drops = set(a.drop.split(",")) if a.drop else set()
        edit(a.in_xml, a.out_xml, drops, parse_sets(a.set), a.clear_dynres)
    else:
        lods = {int(k): v for k, v in parse_sets(a.lod).items()}
        lodsel(a.in_xml, a.out_xml, lods)
