"""Editing helpers on top of actorfmt: add components (HeroSuitAddition clones) with consistent strings / refs /
offsets, and a re-decode consistency check."""
import os, sys, struct
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from i30_actor import (Actor, Obj, Field, Str, Component, crc32, crc64, T_OBJ, T_STR, T_BOOL,   # noqa: E402
                      SEC_PRIUS_DATA)

BS = chr(92)
EXT_HASH = {'.actor': 0x37E72F50, '.config': 0xA9F149C4, '.model': 0xA4070B70, '.animset': 0xD1AD9F7C,
            '.conduit': 0xEA7EFDD4, '.material': 0xB5AAFACC}


def bfs_fields(o):
    """fields in the order the original builder wrote their name strings: breadth first over nested objects"""
    out, q = [], [o]
    while q:
        nq = []
        for ob in q:
            for f in ob.fields:
                out.append(f)
                if f.type == T_OBJ:
                    nq += f.value if f.flags & 1 else [f.value]
        q = nq
    return out


def deep_copy(o):
    n = Obj()
    for f in o.fields:
        v = f.value
        if f.type == T_OBJ:
            v = [deep_copy(x) for x in v] if f.flags & 1 else deep_copy(v)
        elif f.type == T_STR:
            v = [Str(x.s, x.h32, x.h64) for x in v] if f.flags & 1 else Str(v.s, v.h32, v.h64)
        elif f.flags & 1:
            v = list(v)
        n.fields.append(Field(f.name, f.name_off, f.hash, f.flags, f.unk, f.type, v))
    return n


def make_field(name, type_, value, array=False):
    n = len(value) if array else 1
    return Field(name, None, crc32(name), (n << 4) | (1 if array else 0), 0, type_, value)


def asset_ref_obj(path, autoload=None):
    """AssetReferenceDef {AssetPath, Autoload}; Autoload omitted = default true (as in the originals)"""
    o = Obj([make_field('AssetPath', T_STR, Str(path))])
    if autoload is not None:
        o.fields.append(make_field('Autoload', T_BOOL, bool(autoload)))
    return o


def asset_paths(o, autoload_only=True):
    """paths the builder lists in the refs section: File strings and AssetReferenceDef with Autoload true (default);
    AssetReferenceDef with Autoload false is NOT listed (checked: prop_backpack_spidercat.actor is not a ref)."""
    out = []
    for f in o.fields:
        vals = f.value if f.flags & 1 else [f.value]
        if f.type == T_OBJ:
            for v in vals:
                ap = v.field('AssetPath')
                if ap is not None and ap.type == T_STR and {x.name for x in v.fields} <= {'AssetPath', 'Autoload'}:
                    if ap.value.s and (not autoload_only or v.get('Autoload', True)):
                        out.append(ap.value.s)
                else:
                    out += asset_paths(v, autoload_only)
        elif f.type == T_STR:
            out += [v.s for v in vals if '/' in v.s and '.' in v.s.rsplit('/', 1)[-1]]
    return out


def add_component(actor, name, obj, cid, after=None):
    """insert a component after index `after` (default: append). Name strings (one per field occurrence, BFS order,
    then the component name, like the builder) and new ref rows are appended to the strings block, so no existing
    absolute string offset moves; section / component data offsets are recomputed by Actor.save()."""
    for f in bfs_fields(obj):
        f.name_off = actor.add_string(f.name)
    c = Component(cid, name, actor.add_string(name), crc32(name), 0, 0, 0, 0xFFFFFFFF, obj, None)
    i = len(actor.components) if after is None else after + 1
    actor.components.insert(i, c)
    known = {r[0]: k for k, r in enumerate(actor.refs)}
    last = -1
    for cc in actor.components[:i]:
        if cc.obj is not None:
            for pth in asset_paths(cc.obj):
                last = max(last, known.get(crc64(pth), -1))
    at = last + 1
    for pth in asset_paths(obj):
        h = crc64(pth)
        if h in {r[0] for r in actor.refs}:
            continue
        ext = '.' + pth.rsplit('.', 1)[-1].lower()
        actor.refs.insert(at, [h, actor.add_string(pth.replace('/', BS)), EXT_HASH[ext]])
        at += 1
    return c


def new_component_id(actor, seed):
    """unique 64-bit component id. Originals look like GUIDs: the same template component keeps its id across actors
    (AnimControllerComponent 379758E12781680C in hero and prop actors), two components of one type differ."""
    used = {c.id for c in actor.components}
    k = 0
    while True:
        cid = crc64('%s#%d' % (seed, k)) & 0x7FFFFFFFFFFFFFFF
        if cid not in used:
            return cid
        k += 1


def suit_addition(suit_loadout, actor_to_add, autoload_actor=False, skin_item_config=None, show_looks=(), hide_looks=()):
    """minimal HeroSuitAddition object (fields alphabetical like the originals; defaults omitted like the originals)"""
    fs = [make_field('ActorToAdd', T_OBJ, asset_ref_obj(actor_to_add, autoload_actor))]
    if hide_looks:
        fs.append(make_field('HideLooks', T_STR, [Str(x) for x in hide_looks], True))
    if show_looks:
        fs.append(make_field('ShowLooks', T_STR, [Str(x) for x in show_looks], True))
    if skin_item_config:
        fs.append(make_field('SkinItemConfig', T_STR, Str(skin_item_config)))
    fs.append(make_field('SuitLoadout', T_OBJ, asset_ref_obj(suit_loadout)))
    return Obj(fs)


def clone_suit_addition(actor, suit_loadout, src_index=None, actor_to_add=None, strip_cat=False):
    """clone the (last) HeroSuitAddition with another SuitLoadout / ActorToAdd and insert it right after the source.
    strip_cat: keep only ActorToAdd, SkinItemConfig, SuitLoadout (drop cat / Iron Arms finisher, cat mask, looks)."""
    if src_index is None:
        src_index = max(i for i, c in enumerate(actor.components) if c.name == 'HeroSuitAddition')
    o = deep_copy(actor.components[src_index].obj)
    o.field('SuitLoadout').value.field('AssetPath').value = Str(suit_loadout)
    if actor_to_add:
        o.field('ActorToAdd').value.field('AssetPath').value = Str(actor_to_add)
    if strip_cat:
        o.fields = [f for f in o.fields if f.name in ('ActorToAdd', 'SkinItemConfig', 'SuitLoadout')]
    cid = new_component_id(actor, 'HeroSuitAddition:' + suit_loadout)
    return add_component(actor, 'HeroSuitAddition', o, cid, after=src_index)


def verify(data):
    """re-decode and check every count / offset / size / hash. Returns (actor, [problems])."""
    bad = []
    a = Actor(data)            # itself checks: header A size == DAT1 size, sorted table, strings padding, every
    D = data[16:]              # component object parses to exactly data_size, object/strings padding is zero
    if len(D) != struct.unpack_from('<I', D, 8)[0]:
        bad.append('file length != DAT1 size')
    spans = sorted((o, o + s, t) for t, (o, s) in a._offs.items())
    for (o0, e0, t0), (o1, e1, t1) in zip(spans, spans[1:]):
        if e0 > o1:
            bad.append('sections %08X / %08X overlap' % (t0, t1))
    bad += ['section %08X not 16-aligned' % t for o, e, t in spans if o % 16]
    if spans[0][0] < a.str_base + len(a.strings):
        bad.append('first section overlaps the strings block')
    do, ds = a._offs[SEC_PRIUS_DATA]
    if ds % 16:
        bad.append('component data section size not padded to 16')
    prev_end = do
    for c in a.components:
        if c.name_hash != crc32(c.name):
            bad.append('component %s name hash' % c.name)
        if c.tailword != 0xFFFFFFFF or c.zero != 0:
            bad.append('component %s reserved words' % c.name)
        if c.data_off:
            if not (prev_end <= c.data_off and c.data_off + c.size <= do + ds and c.data_off % 16 == 0):
                bad.append('component %s data not inside / in order / aligned' % c.name)
            prev_end = c.data_off + c.size
        if c.obj is None:
            continue
        for f in bfs_fields(c.obj):
            if f.hash != crc32(f.name):
                bad.append('%s.%s name hash' % (c.name, f.name))
            vals = f.value if f.flags & 1 else [f.value]
            if (f.flags & 1 and len(vals) != f.flags >> 4) or (not f.flags & 1 and f.flags >> 4 != 1):
                bad.append('%s.%s count' % (c.name, f.name))
            if f.type == T_STR:
                for v in vals:
                    if v.h32 != (crc32(v.s) if v.s else 0) or v.h64 != (crc64(v.s) if v.s else 0):
                        bad.append('%s.%s string hash %r' % (c.name, f.name, v.s))
    if len({c.id for c in a.components}) != len(a.components):
        bad.append('duplicate component ids')
    have = {r[0] for r in a.refs}
    for r in a.refs:
        if crc64(a.string(r[1])) != r[0]:
            bad.append('ref hash %016X != crc64(%s)' % (r[0], a.string(r[1])))
    for c in a.components:
        if c.obj is not None:
            bad += ['component %s path %s not in refs' % (c.name, p) for p in asset_paths(c.obj) if crc64(p) not in have]
    return a, bad


def set_model(actor, model_path):
    """retarget an actor to another .model: ActorBuilt (32FAC8E0) holds the absolute string offset of the model path
    (backslashes), refs row with the old model hash is replaced (crc64, own string copy, crc32('.model') A4070B70)."""
    from i30_actor import SEC_BUILT
    old = actor.string(struct.unpack_from('<I', actor.sec[SEC_BUILT])[0])
    p = model_path.replace('/', BS)
    actor.sec[SEC_BUILT] = struct.pack('<I', actor.add_string(p)) + actor.sec[SEC_BUILT][4:]
    for r in actor.refs:
        if r[0] == crc64(old):
            r[:] = [crc64(p), actor.add_string(p), EXT_HASH['.model']]
    return old
