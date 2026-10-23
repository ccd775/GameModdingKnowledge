"""Build an empty CItemEntity template JSON (no components) from a WolvenKit 7 JSON of
items/bodyparts/geralt_items/trunk/bare/t_01_mg__body.w2ent.

Usage: python make_empty_item_template.py <in.w2ent.json> <out.w2ent.json>
"""
import json
import sys


def strip_components(cr2w):
    chunks = cr2w['_chunks']
    drop = [k for k, c in chunks.items() if c['_type'] not in ('CEntityTemplate', 'CItemEntity')]
    for k in drop:
        del chunks[k]
    for c in chunks.values():
        if c['_type'] == 'CItemEntity':
            c['_vars']['Components']['_elements'] = []
        fcd = c['_vars'].get('flatCompiledData')
        if fcd:
            strip_components(fcd)
    cr2w['_imports'] = []
    return drop


def main():
    import argparse
    ap = argparse.ArgumentParser(description='Empty CItemEntity template JSON (no components).')
    ap.add_argument('src', help='WolvenKit JSON of trunk/bare/t_01_mg__body.w2ent')
    ap.add_argument('dst')
    a = ap.parse_args()
    src, dst = a.src, a.dst
    d = json.load(open(src, encoding='utf-8'))
    dropped = strip_components(d)
    json.dump(d, open(dst, 'w', encoding='utf-8'), indent=1)
    print('dropped chunks:', dropped)


if __name__ == '__main__':
    main()
