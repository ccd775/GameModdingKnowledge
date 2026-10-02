"""Generic GoWR character replacement: plan which source parts go into which MESH defs, per MG group and LOD."""
import collections
from encode import capacity
from build_mesh import root_buffer
from geometry import subset

RATIOS = ['0.9', '0.8', '0.75', '0.7', '0.6', '0.5', '0.4', '0.3', '0.22', '0.16', '0.12', '0.08', '0.06',
          '0.04', '0.03', '0.025', '0.02', '0.015']


def room_finder(ms, gpu_len):
    """def index -> (vertex room, index room) measured from the shipped in-place layout."""
    by = collections.defaultdict(list)
    for m in ms:
        by[m.hash].append(m)
    def caps(di):
        m = ms[di]
        sib = sorted(by[m.hash], key=lambda s: s.buf_offs[0] if s.buf_count else 0)
        k = [s.i for s in sib].index(di)
        if k + 1 < len(sib):
            nxt = sib[k + 1].buf_offs[0]
        elif m.hash == 0:
            nxt = gpu_len
        else:
            try:
                nxt = len(root_buffer(m.hash))
            except KeyError:                  # hash already bumped by a previous mod
                nxt = len(root_buffer(m.hash - 1))
        return capacity(m, nxt)
    return caps


def plan_groups(groups, group_parts, caps, geos):
    """group_parts: {group id: [part set for the largest slot, part set for the next, ...]}.
    Every LOD list of the group gets the same parts; sets beyond the slot count share the last slot."""
    plan, chosen = {}, {}
    levels = ['full'] + [r for r in RATIOS if r in geos]
    for gid, part_sets in group_parts.items():
        for lod_i, lod in enumerate(groups[gid]['lods']):
            slots = sorted(lod['meshes'], key=lambda i: -caps(i)[0])
            if not slots:
                continue
            assign = {}
            for k, ps in enumerate(part_sets):
                assign.setdefault(slots[min(k, len(slots) - 1)], []).extend(ps)
            # a secondary slot too small even for the coarsest level hands its parts to the main slot; the main
            # slot then drops parts from the end of its list (lowest priority) until the rest fits
            picks, dropped = {}, []
            for s in [s for s in assign if s != slots[0]]:
                picked = fit_parts(assign[s], levels, geos, *caps(s))
                if picked is None:
                    assign.setdefault(slots[0], []).extend(assign.pop(s))
                else:
                    picks[s] = picked
            if slots[0] in assign:
                parts = list(assign[slots[0]])
                while parts and fit_parts(parts, levels, geos, *caps(slots[0])) is None:
                    dropped.insert(0, parts.pop())
                if not parts:
                    raise SystemExit(f'group {gid} lod {lod_i}: nothing fits slot {slots[0]} {caps(slots[0])}')
                picks[slots[0]] = fit_parts(parts, levels, geos, *caps(slots[0]))
            for s, picked in picks.items():
                vcap, icap = caps(s)
                plan[s] = ('mixed', picked)
                chosen[s] = dict(group=gid, lod=lod_i, dist=round(lod['dist'], 1), room=(vcap, icap),
                                 levels={p: k for p, k in picked}, verts=sum(_size(geos, k, p)[0] for p, k in picked))
                if s == slots[0] and dropped:
                    chosen[s]['dropped'] = dropped
    return plan, chosen


_SIZE_CACHE = {}


def _size(geos, key, part):
    k = (key, part)
    if k not in _SIZE_CACHE:
        g = subset(geos[key], [part])
        _SIZE_CACHE[k] = (len(g['P']), len(g['IDX']) * 3)
    return _SIZE_CACHE[k]


def fit_parts(parts, levels, geos, vcap, icap):
    """Pick a detail level per part: the best common level that fits all parts, then spend the leftover room
    upgrading parts in list order (earlier = higher priority)."""
    def total(keys):
        v = sum(_size(geos, k, p)[0] for p, k in zip(parts, keys))
        i = sum(_size(geos, k, p)[1] for p, k in zip(parts, keys))
        return v, i
    base = None
    for key in levels:
        v, i = total([key] * len(parts))
        if v <= vcap and i <= icap:
            base = key
            break
    if base is None:
        return None
    keys = [base] * len(parts)
    for n in range(len(parts)):
        for key in levels[:levels.index(keys[n])]:
            trial = keys[:n] + [key] + keys[n + 1:]
            v, i = total(trial)
            if v <= vcap and i <= icap:
                keys = trial
                break
    return list(zip(parts, keys))
