"""Assemble a Witcher 3 (5.x) local mod from a staging tree.

Usage:
  python build_mod.py stage <staging_root> --empty <empty.w2ent> [--head <head.w2ent>] [--extra <dir>]
                      [--listing <all_bundles.tsv>]
  python build_mod.py pack <staging_root> <mod_dir>

'stage' writes, for every vanilla items\\bodyparts\\geralt_items template (except scabbards),
either the empty template or (for heads) the head template, then copies --extra trees on top.
The template list comes from the bundle listing written by tools/prepare.ps1
(`w3bundle.py list -v`; default <W3_WORK>/scratch/all_bundles.tsv).
'pack' writes <mod_dir>/content/blob0.bundle from the staging tree.
"""
import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import w3bundle  # noqa: E402
import w3paths  # noqa: E402

BS = chr(92)


def vanilla_bodypart_templates(listing):
    out = set()
    for line in open(listing, encoding='utf-8-sig'):
        name = line.rstrip('\r\n').split('\t')[8].lower()
        if not name.endswith('.w2ent'):
            continue
        parts = name.split(BS)
        if 'geralt_items' not in parts or 'bodyparts' not in parts:
            continue
        cat = parts[parts.index('geralt_items') + 1]
        if cat == 'scabbards':
            continue
        out.add((name, cat))
    return sorted(out)


def cmd_stage(a):
    if os.path.exists(a.root):
        shutil.rmtree(a.root)
    empty = open(a.empty, 'rb').read()
    head = open(a.head, 'rb').read() if a.head else empty
    coif = open(a.coif, 'rb').read() if a.coif else empty
    counts = {}
    for name, cat in vanilla_bodypart_templates(a.listing or w3paths.work('scratch', 'all_bundles.tsv')):
        data = head if cat == 'heads' else coif if cat == 'coif' else empty
        dst = os.path.join(a.root, name.replace(BS, os.sep))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        with open(dst, 'wb') as f:
            f.write(data)
        counts[cat] = counts.get(cat, 0) + 1
    for extra in a.extra or []:
        for r, _d, fns in os.walk(extra):
            for fn in fns:
                src = os.path.join(r, fn)
                dst = os.path.join(a.root, os.path.relpath(src, extra))
                os.makedirs(os.path.dirname(dst), exist_ok=True)
                shutil.copyfile(src, dst)
                counts['extra'] = counts.get('extra', 0) + 1
    print('staged', counts)


def cmd_pack(a):
    files = []
    root = os.path.abspath(a.root)
    for r, _d, fns in os.walk(root):
        for fn in sorted(fns):
            full = os.path.join(r, fn)
            rel = os.path.relpath(full, root).replace(os.sep, BS).lower()
            files.append((rel, open(full, 'rb').read()))
    content = os.path.join(a.mod_dir, 'content')
    os.makedirs(content, exist_ok=True)
    out = os.path.join(content, 'blob0.bundle')
    total = w3bundle.write_bundle(out, files, compression=a.compression)
    print(f'packed {len(files)} files -> {out} ({total} bytes)')


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest='cmd', required=True)
    p = sub.add_parser('stage')
    p.add_argument('root')
    p.add_argument('--empty', required=True)
    p.add_argument('--head')
    p.add_argument('--coif', help='template written to every coif (hairstyle) path')
    p.add_argument('--extra', action='append')
    p.add_argument('--listing', help='bundle listing (w3bundle.py list -v); default <W3_WORK>/scratch/all_bundles.tsv')
    p.set_defaults(func=cmd_stage)
    p = sub.add_parser('pack')
    p.add_argument('root')
    p.add_argument('mod_dir')
    p.add_argument('--compression', type=int, default=1)
    p.set_defaults(func=cmd_pack)
    a = ap.parse_args()
    a.func(a)


if __name__ == '__main__':
    main()
