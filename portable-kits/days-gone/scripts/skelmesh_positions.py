"""Move vertices of a cooked UE 4.11 skeletal mesh's GPU skin vertex buffer in place (needs numpy).

Same buffer as skelmesh_normals.py (located by matching the reference corner positions). Every buffer vertex whose
position matches an `old` entry (rounded to 0.01 cm, +-0.01 neighbourhood) gets the corresponding `new` position;
normals and tangents are left as they are (the moves are small inward offsets of hidden skin, see
Scripts/skirt_body_shrink.py). Other float copies of the same positions elsewhere in the file are reported, not touched.

patch(data, locate_pos, moves) -> (new_data, report); locate_pos (N,3) = the loop normals dump's 'pos',
moves = dict(old (M,3), new (M,3)) in UE space
"""
import struct
import numpy as np
from skelmesh_normals import find_buffer, STRIDE

def patch(data, locate_pos, moves):
    d = bytearray(data)
    start, n, hit = find_buffer(bytes(d), locate_pos)
    v = np.frombuffer(d, dtype=np.uint8, count=STRIDE * n, offset=start).reshape(n, STRIDE).copy()
    p = v[:, 16:28].copy().view('<f4').astype(np.float64)
    old, new = np.asarray(moves['old'], np.float64), np.asarray(moves['new'], np.float64)
    keys = {}
    for i, k in enumerate(map(tuple, np.round(old, 2))):
        keys.setdefault(k, []).append(i)
    offs = [(a, b, c) for a in (-.01, 0, .01) for b in (-.01, 0, .01) for c in (-.01, 0, .01)]
    moved = 0; used = set(); max_err = 0.0
    for j in range(n):
        q = np.round(p[j], 2)
        cand = keys.get(tuple(q)) or [i for o in offs for i in keys.get(tuple(np.round(q + o, 2)), ())]
        cand = [i for i in cand if np.linalg.norm(old[i] - p[j]) < 1e-2]
        if not cand:
            continue
        i = min(cand, key=lambda i: np.linalg.norm(old[i] - p[j]))
        max_err = max(max_err, float(np.linalg.norm(old[i] - p[j])))
        p[j] = p[j] + (new[i] - old[i])
        used.add(i); moved += 1
    v[:, 16:28] = p.astype('<f4').view(np.uint8).reshape(n, 12)
    d[start:start + STRIDE * n] = v.tobytes()
    # other copies of moved positions outside the buffer (CPU-side vertex data, if the cook kept any)
    end = start + STRIDE * n
    copies = 0
    for i in list(used)[:50]:
        b = struct.pack('<3f', *old[i])
        o = data.find(b)
        while o >= 0:
            if not (start <= o < end):
                copies += 1
            o = data.find(b, o + 1)
    return bytes(d), {'buffer_offset': start, 'vertices': n, 'moved_buffer_vertices': moved,
                      'moves_matched': len(used), 'moves_total': len(old), 'max_match_err': max_err,
                      'other_copies_of_50_sampled': copies}
