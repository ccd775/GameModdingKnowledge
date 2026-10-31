"""BuildTable / schema-XML helpers (AnvilToolkit schema XML, type="1"). ACU copy of ACOd/scripts/bt_tool.py.
Unity: compile-xml of vanilla XML is byte-identical (2026-10-24), so the Odyssey null-ref fix is off (FIX_NULL_REFS).

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


FIX_NULL_REFS = False  # Odyssey needed it; Unity tables recompile byte-identical without it


def fix_null_refs(x):
    if not FIX_NULL_REFS:
        return x
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


COLTYPE_RE = re.compile(r'<Unsigned32 Name="ColumnID">(\d+)</Unsigned32>.*?<DynamicProperty Name="Type"[^>]*ObjectType="(\w+)"', re.S)


def add_cell(r, col, objtype, oid, path):
    """append a Reference cell to the row's own DynamicProperties (Syndicate: a row without the column, e.g. Lydia's
    head row has no hair add-on skeleton cell 14)"""
    cell = (f'                <DynamicProperty Name="{col}" ArrayType="Bool" BaseType="Reference" ObjectType="{objtype}" Flags="00000000">\n'
            f'                    <Reference Type="{objtype}" PointerType="External" ReferenceType="0" Path="{path or ""}">{oid}</Reference>\n'
            f'                </DynamicProperty>\n')
    i = r.find("<DynamicProperties>")
    if i >= 0:
        j = r.index("</DynamicProperties>", i)
        k = r.rindex("\n", 0, j) + 1
        return r[:k] + cell + r[k:]
    i = r.index("<DynamicProperties />")
    ind = r[r.rindex("\n", 0, i) + 1:i]
    return r[:i] + "<DynamicProperties>\n" + cell + ind + "</DynamicProperties>" + r[i + len("<DynamicProperties />"):]


def edit(src, dst, drops, sets, clear_dynres=False, quiet=False, add_missing=False):
    """add_missing: a --set column without a cell in a row gets one (type from the column definition)"""
    x = open(src, encoding="utf-8-sig").read()
    head, rows = split_rows(x)
    coltype = dict(COLTYPE_RE.findall(head))
    n_drop = n_set = n_add = 0
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
        r = CELL_RE.sub(repl, r)
        if add_missing:
            have = {m.group(1) for m in ANYCELL_RE.finditer(r)}
            for col, (oid, path) in sets.items():
                if col not in have:
                    if col not in coltype:
                        raise SystemExit(f"{src}: no column {col} to add a cell to")
                    r = add_cell(r, col, coltype[col], oid, path)
                    n_add += 1
        out.append(r)
    y = head + "".join(out)
    n_dyn = 0
    if clear_dynres:
        y, n_dyn = DYNRES_RE.subn('<DynamicSmallArray Name="DynamicResources" Type="Handle" />', y)
    y = fix_null_refs(y)
    open(dst, "w", encoding="utf-8-sig").write(y)
    if not quiet:
        print(f"edit: dropped {n_drop} cells, set {n_set} cells, added {n_add} cells, cleared {n_dyn} DynamicResources -> {dst}")


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
