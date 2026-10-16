"""Retarget package imports without growing the package header.

Days Gone material instances carry an inline shader map whose loading breaks when the export moves inside the file
(the header grew by 236 bytes -> LowLevelFatalError "Invalid BufferCount=0 ... MI_*.uasset"; byte-identical copies at
another path load fine). So instead of appending names, this rewrites the name-table strings that only the retargeted
imports use, and pads the names left over so the name table keeps its byte length. Import/export table sizes and every
offset stay unchanged.

retarget(pkg, {old_package_path: new_package_path, ...}) -> report dict
- the object import under each package import is renamed to the new path's last segment ('/Game/A/B' -> 'B', or
  '/Game/A/B.Obj' -> package '/Game/A/B', object 'Obj')
- raises ValueError when the strings cannot be balanced (no spare names, or the new names are too long)
"""

def _split(path):
    pk, last = path.rsplit('/', 1)
    if '.' in last:
        last, obj = last.split('.', 1)
        return pk + '/' + last, obj
    return path, last

def retarget(pkg, mapping):
    imps = pkg.imports
    pairs = []   # (package import index, object import index, new package path, new object name)
    for i, im in enumerate(imps):
        if pkg.name(im['ClassName']) != 'Package' or im['Outer'] != 0:
            continue
        old = pkg.name(im['Name'])
        if old not in mapping:
            continue
        new_pk, new_obj = _split(mapping[old])
        objs = [j for j, ob in enumerate(imps) if ob['Outer'] == -i - 1]
        if len(objs) != 1:
            raise ValueError('%s: expected one object import, found %d' % (old, len(objs)))
        pairs.append((i, objs[0], new_pk, new_obj))
    missing = set(mapping) - {pkg.name(imps[i]['Name']) for i, _, _, _ in pairs}
    if missing:
        raise ValueError('imports not found: %s' % sorted(missing))
    touched = {i for i, _, _, _ in pairs} | {j for _, j, _, _ in pairs}
    # name slots referenced only through the Name field of retargeted imports are free to rewrite
    refs = {}
    for k, im in enumerate(imps):
        for field in ('ClassPackage', 'ClassName', 'Name'):
            refs.setdefault(im[field][0], set()).add((k, field))
    for e in pkg.exports:
        refs.setdefault(e['Name'][0], set()).add(('export', 'Name'))
    pool = sorted({imps[k]['Name'][0] for k in touched
                   if all(r[0] in touched and r[1] == 'Name' for r in refs[imps[k]['Name'][0]])})
    old_len = sum(len(pkg.names[s]) for s in pool)
    # assign: reuse an existing name outside the pool, else take a slot from the pool (prefer the import's own slot)
    assigned = {}   # new string -> slot
    free = list(pool)
    def slot_for(s, prefer):
        if s in assigned:
            return assigned[s]
        for k, n in enumerate(pkg.names):
            if n == s and k not in pool:
                assigned[s] = k; return k
        k = prefer if prefer in free else (free[0] if free else None)
        if k is None:
            raise ValueError('no free name slot for %s' % s)
        free.remove(k); pkg.names[k] = s; assigned[s] = k
        return k
    for i, j, new_pk, new_obj in pairs:
        imps[i]['Name'] = (slot_for(new_pk, imps[i]['Name'][0]), 0)
        imps[j]['Name'] = (slot_for(new_obj, imps[j]['Name'][0]), 0)
    used = sum(len(pkg.names[k]) for k in pool if k not in free)
    budget = old_len - used
    if not free:
        if budget:
            raise ValueError('name table would change by %d chars and no spare slot is left' % -budget)
    else:
        if budget < len(free):
            raise ValueError('new names are %d chars too long' % (len(free) - budget))
        # spare slots keep a unique, unused string of the remaining length
        for n, k in enumerate(free):
            ln = budget // len(free) + (1 if n < budget % len(free) else 0)
            tag = '~pad%d~' % n
            pkg.names[k] = (tag + 'x' * ln)[:ln] if ln >= len(tag) else ('%d' % n + 'x' * ln)[:ln]
    return {'pool': len(pool), 'spare': len(free), 'pad_chars': budget if free else 0,
            'pairs': [(pkg.obj_path(-j - 1)) for _, j, _, _ in pairs]}
