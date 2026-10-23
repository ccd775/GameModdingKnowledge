# da_animclass.py <in DA.uasset> <out DA.uasset> <AnimBP package path>
# Gives a CharacterPiece DA an AnimClass (like the vanilla robe DAs): the piece then runs its own anim instance
# (our ABP: copy pose from the attached parent + AnimDynamics) instead of following the body through master pose.
# Adds the package/class/CDO imports, a SerializationBeforeCreate preload dependency on the CDO, and the tagged
# ObjectProperty before the export's terminating None.
import struct, sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from uasset import Package

def top_level_none(p, data):
    # walk FPropertyTags; return the offset of the terminating None
    o = 0
    def fn(at): return p.nstr(struct.unpack_from('<ii', data, at))
    while True:
        name = fn(o)
        if name == 'None': return o
        typ = fn(o + 8); size, idx = struct.unpack_from('<ii', data, o + 16); o += 24
        if typ == 'StructProperty': o += 8 + 16
        elif typ == 'BoolProperty': o += 1
        elif typ in ('ByteProperty', 'EnumProperty', 'ArrayProperty', 'SetProperty', 'OptionalProperty'): o += 8
        elif typ == 'MapProperty': o += 16
        has_guid = data[o]; o += 1 + (16 if has_guid else 0)
        o += size

def add_anim_class(src, dst, abp_path):
    p = Package(src)
    short = abp_path.rsplit('/', 1)[1]
    pkg = p.add_import('/Script/CoreUObject', 'Package', 0, abp_path)
    cls = p.add_import('/Script/Engine', 'AnimBlueprintGeneratedClass', pkg, short + '_C')
    cdo = p.add_import(abp_path, short + '_C', pkg, 'Default__' + short + '_C')
    e = p.exports[0]
    data = bytearray(e['data'])
    at = top_level_none(p, data)
    assert data[at + 8:] == b'\0\0\0\0', 'unexpected export tail %r' % bytes(data[at + 8:])
    prop = p.prop_tag('AnimClass', 'ObjectProperty', 4) + struct.pack('<i', cls)
    data[at:at] = prop; e['data'] = bytes(data)
    # preload: SerializationBeforeCreate list of export 0 gets the CDO first (vanilla robe DA order)
    ins = e['first_dep'] + e['deps'][0] + e['deps'][1]
    p.preload.insert(ins, cdo); e['deps'][2] += 1
    for other in p.exports[1:]:
        if other['first_dep'] >= ins: other['first_dep'] += 1
    p.preload_count = len(p.preload)
    p.write(dst)
    return p

if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(description='give a CharacterPiece DA an AnimClass (import, property, preload dependency)')
    ap.add_argument('src', help='DA .uasset (.uexp beside it)'); ap.add_argument('dst', help='output .uasset')
    ap.add_argument('abp', help='anim blueprint package path, e.g. /Game/RiggedObjects/Characters/Human/Karin_F/ABP_Karin_F_Body')
    args = ap.parse_args()
    p = add_anim_class(args.src, args.dst, args.abp); Package(args.dst).dump()
