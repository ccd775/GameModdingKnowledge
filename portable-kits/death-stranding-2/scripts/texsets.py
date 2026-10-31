"""Describe the texture sets a mesh's materials use: python texsets.py <gid>:<mesh idx> [...]

For every primitive: shading group -> render effect texture bindings -> textures, with the texture set's source
descriptions (paths) and per-entry packing so the role of each texture (colour, normal, roughness...) is visible.
"""
import argparse
import sys

from graph import Graph, game_root
from group import read_group

CACHE = {}
PIXEL = {}


def obj(g, ref):
    if ref[1] not in CACHE:
        CACHE[ref[1]] = read_group(g, ref[1])
    return CACHE[ref[1]][ref[2]]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('meshes', nargs='+', metavar='<gid>:<mesh idx>')
    meshes = ap.parse_args().meshes
    g = Graph(game_root())
    enum = {v['value']: v['name'] for v in g.db.types['EPixelFormat']['values']}
    ttype = {v['value']: v['name'] for v in g.db.types['ETextureSetType']['values']} if 'ETextureSetType' in g.db.types else {}
    for a in meshes:
        gid, idx = map(int, a.split(':'))
        m = obj(g, ('Ref', gid, idx))
        print('== mesh %s' % a)
        for pi, sg_ref in enumerate(m['ShadingGroups']):
            sg = obj(g, sg_ref)
            re = obj(g, sg['RenderEffect'])
            texs = []
            for ts in re['TechniqueSets']:
                for t in ts['RenderTechniques']:
                    for tb in t['TextureBindings']:
                        if tb.get('TextureResource'):
                            texs.append(tuple(tb['TextureResource'][1:]))
            texs = sorted(set(texs))
            print('  prim %d shading group %s effect %s: %d textures' % (pi, sg_ref[1:], sg['RenderEffect'][1:], len(texs)))
            sets = {}
            for t in texs:
                to = obj(g, ('Ref',) + t)
                if to['__type__'] != 'Texture':
                    print('    %s %s' % (t, to['__type__']))
                    continue
                h = to['Header']
                parent = to['TextureSetParent']
                print('    tex %d:%d %dx%d %s set=%s' % (t[0], t[1], h['Width'] & 0x3FFF, h['Height'] & 0x3FFF,
                                                    enum.get(h['PixelFormat'], h['PixelFormat']), parent[1:] if parent else None))
                if parent:
                    sets[tuple(parent[1:])] = 1
            for s in sets:
                so = obj(g, ('Ref',) + s)
                print('    set %s:' % (s,))
                for d in so['TextureDesc']:
                    if d['Path']:
                        print('       desc type=%s %s %dx%d' % (ttype.get(d['TextureType'], d['TextureType']), d['Path'].split('/')[-1], d['Width'], d['Height']))
                for e in so['Entries']:
                    print('       entry tex=%s packing=0x%08x type=%s cs=%d' % (e['Texture'][1:] if e['Texture'] else None,
                                                                          e['PackingInfo'], ttype.get(e['TextureType'], e['TextureType']), e['ColorSpace']))


if __name__ == '__main__':
    main()
