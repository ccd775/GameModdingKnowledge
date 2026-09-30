"""Pack the used UV regions of several source textures into one texture page.

Each mesh is split into UV islands (triangles connected through shared vertices; the glTF buffers split
vertices at UV seams). An island's bounding box in source pixels, grown by a margin, is a piece; pieces of
the same image that touch are merged, so texels shared by overlapping islands (mirrored parts) stay shared.
The pieces are shelf-packed at the largest common scale that fits the page (never above the source
resolution), each with a gutter of real neighbouring source texels, and the empty page is filled by
push-pull so mip levels do not bleed a background colour into the islands.
"""
import numpy as np
from PIL import Image


def uv_islands(tris, n_verts):
    parent = np.arange(n_verts)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for t in tris:
        r0, r1, r2 = find(t[0]), find(t[1]), find(t[2])
        parent[r1] = r0
        parent[find(r2)] = r0
    return np.array([find(i) for i in range(n_verts)])


def _merge_rects(rects):
    """rects: list of [x0, y0, x1, y1, members]; merge until no two overlap."""
    rects = [list(r) for r in rects]
    changed = True
    while changed:
        changed = False
        rects.sort(key=lambda r: r[0])
        out = []
        for r in rects:
            for o in out:
                if r[0] < o[2] and o[0] < r[2] and r[1] < o[3] and o[1] < r[3]:
                    o[0], o[1] = min(o[0], r[0]), min(o[1], r[1])
                    o[2], o[3] = max(o[2], r[2]), max(o[3], r[3])
                    o[4] = o[4] + r[4]
                    changed = True
                    break
            else:
                out.append(r)
        rects = out
    return rects


def _shelf_pack(sizes, W, H):
    """First-fit decreasing-height shelves. sizes: [(w, h)]; returns [(x, y)] or None."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    shelves = []   # [y, height, x_used]
    pos = [None] * len(sizes)
    y_top = 0
    for i in order:
        w, h = sizes[i]
        if w > W:
            return None
        for s in shelves:
            if h <= s[1] and s[2] + w <= W:
                pos[i] = (s[2], s[0])
                s[2] += w
                break
        else:
            if y_top + h > H:
                return None
            shelves.append([y_top, h, w])
            pos[i] = (0, y_top)
            y_top += h
    return pos


def _push_pull(rgb, mask):
    """Fill pixels where mask is False from coarser averages of the filled ones."""
    if mask.all() or not mask.any():
        return rgb
    h, w = mask.shape
    m = mask.astype(np.float64)
    c = rgb * m[..., None]
    if h <= 1 or w <= 1:
        return np.where(mask[..., None], rgb, c.sum((0, 1)) / max(m.sum(), 1))
    h2, w2 = (h + 1) // 2, (w + 1) // 2
    cp = np.zeros((h2 * 2, w2 * 2, c.shape[2]))
    mp = np.zeros((h2 * 2, w2 * 2))
    cp[:h, :w] = c
    mp[:h, :w] = m
    cs = cp.reshape(h2, 2, w2, 2, -1).sum((1, 3))
    ms = mp.reshape(h2, 2, w2, 2).sum((1, 3))
    coarse = np.where(ms[..., None] > 0, cs / np.maximum(ms, 1e-9)[..., None], 0)
    coarse = _push_pull(coarse, ms > 0)
    up = np.repeat(np.repeat(coarse, 2, 0), 2, 1)[:h, :w]
    return np.where(mask[..., None], rgb, up)


def build_page(items, size, gutter=4, margin_src=2):
    """items: list of dict(img=PIL image, uv=(V,2), tris=(T,3), key=image id).
    Returns (page PIL RGBA of `size`, [new uv per item], info)."""
    W, H = size
    pieces = []   # per image key: rects
    by_key = {}
    for ii, it in enumerate(items):
        sw, sh = it['img'].size
        uv = it['uv']
        isl = uv_islands(it['tris'], len(uv))
        used = np.unique(it['tris'])
        for r in np.unique(isl[used]):
            vs = used[isl[used] == r]
            px = uv[vs] * [sw, sh]
            x0, y0 = np.floor(px.min(0)).astype(int) - margin_src
            x1, y1 = np.ceil(px.max(0)).astype(int) + margin_src
            by_key.setdefault(it['key'], []).append([x0, y0, x1, y1, [(ii, vs)]])
    for key, rects in by_key.items():
        for r in _merge_rects(rects):
            pieces.append(dict(key=key, rect=r[:4], members=r[4]))
    img_of = {it['key']: it['img'] for it in items}

    def sizes(s):
        out = []
        for p in pieces:
            x0, y0, x1, y1 = p['rect']
            out.append((max(1, int(np.ceil((x1 - x0) * s))) + 2 * gutter, max(1, int(np.ceil((y1 - y0) * s))) + 2 * gutter))
        return out

    lo, hi = 0.0, 1.0
    if _shelf_pack(sizes(hi), W, H) is not None:
        lo = hi
    else:
        for _ in range(30):
            mid = (lo + hi) / 2
            if _shelf_pack(sizes(mid), W, H) is not None:
                lo = mid
            else:
                hi = mid
    s = lo
    if s <= 0:
        raise ValueError('pieces do not fit the page')
    sz = sizes(s)
    pos = _shelf_pack(sz, W, H)
    page = np.zeros((H, W, 4), np.float64)
    filled = np.zeros((H, W), bool)
    new_uv = [it['uv'].copy() for it in items]
    # opaque before resampling: Pillow resizes RGBA premultiplied, which would blacken texels with alpha 0
    # (the armour materials are opaque, the page alpha is discarded anyway)
    src_arr = {}
    for k, im in img_of.items():
        a = np.asarray(im.convert('RGBA'), np.float64).copy()
        a[..., 3] = 255
        src_arr[k] = a
    for p, (pw, ph), (px, py) in zip(pieces, sz, pos):
        x0, y0, x1, y1 = p['rect']
        iw, ih = pw - 2 * gutter, ph - 2 * gutter
        sx, sy = iw / (x1 - x0), ih / (y1 - y0)
        # the whole cell (gutter included) samples the source box [x0 - g/sx, x1 + g/sx] x [...], i.e. page
        # x = px + g + (source x - x0) * sx: exactly the transform the UVs get below. The crop around the box is
        # edge-replicated outside the image and wide enough for the resampling filter.
        a = src_arr[p['key']]
        bx0, by0 = x0 - gutter / sx, y0 - gutter / sy
        bx1, by1 = x1 + gutter / sx, y1 + gutter / sy
        m = int(np.ceil(3 / min(sx, sy))) + 2
        cx0, cy0 = int(np.floor(bx0)) - m, int(np.floor(by0)) - m
        cx1, cy1 = int(np.ceil(bx1)) + m, int(np.ceil(by1)) + m
        pad = max(0, -cx0, -cy0, cx1 - a.shape[1], cy1 - a.shape[0])
        ap = np.pad(a, ((pad, pad), (pad, pad), (0, 0)), mode='edge') if pad else a
        crop = Image.fromarray(ap[cy0 + pad:cy1 + pad, cx0 + pad:cx1 + pad].astype(np.uint8), 'RGBA')
        cell = crop.resize((pw, ph), Image.LANCZOS, box=(bx0 - cx0, by0 - cy0, bx1 - cx0, by1 - cy0))
        page[py:py + ph, px:px + pw] = np.asarray(cell, np.float64)
        filled[py:py + ph, px:px + pw] = True
        for ii, vs in p['members']:
            sw, sh = img_of[p['key']].size
            src_px = items[ii]['uv'][vs] * [sw, sh]
            new_uv[ii][vs, 0] = (px + gutter + (src_px[:, 0] - x0) * sx) / W
            new_uv[ii][vs, 1] = (py + gutter + (src_px[:, 1] - y0) * sy) / H
    page = _push_pull(page, filled)
    out = Image.fromarray(np.clip(np.round(page), 0, 255).astype(np.uint8), 'RGBA')
    return out, new_uv, dict(scale=s, pieces=len(pieces), fill=float(filled.mean()))
