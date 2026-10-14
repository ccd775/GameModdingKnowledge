import numpy as np
from PIL import Image, ImageDraw

def _raster(img, zb, x, y, z, tris, colors, shade):
    H, W = zb.shape
    for k in range(len(tris)):
        i0, i1, i2 = tris[k]
        xs = np.array([x[i0], x[i1], x[i2]]); ys = np.array([y[i0], y[i1], y[i2]]); zs = np.array([z[i0], z[i1], z[i2]])
        x0 = int(max(0, np.floor(xs.min()))); x1 = int(min(W - 1, np.ceil(xs.max())))
        y0 = int(max(0, np.floor(ys.min()))); y1 = int(min(H - 1, np.ceil(ys.max())))
        if x1 < x0 or y1 < y0:
            continue
        d = (xs[1] - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (ys[1] - ys[0])
        if abs(d) < 1e-9:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w1 = ((gx - xs[0]) * (ys[2] - ys[0]) - (xs[2] - xs[0]) * (gy - ys[0])) / d
        w2 = ((xs[1] - xs[0]) * (gy - ys[0]) - (gx - xs[0]) * (ys[1] - ys[0])) / d
        w0 = 1 - w1 - w2
        inside = (w1 >= -1e-6) & (w2 >= -1e-6) & (w0 >= -1e-6)
        if not inside.any():
            continue
        zz = w0 * zs[0] + w1 * zs[1] + w2 * zs[2]
        sub = zb[y0:y1 + 1, x0:x1 + 1]
        m = inside & (zz > sub)
        sub[m] = zz[m]
        c = colors[k] * shade[k]
        img[y0:y1 + 1, x0:x1 + 1][m] = np.clip(c, 0, 255).astype(np.uint8)

def render_mesh(meshes, out, joints=None, W=500, H=900, bounds=None, views=((1, 2, 1), (0, 2, 1)), texfn=None):
    """meshes: list of (verts, tris, color or per-tri colors array). views: (h_axis, v_axis, sign)."""
    allv = np.concatenate([m[0] for m in meshes])
    lo, hi = (allv.min(0), allv.max(0)) if bounds is None else bounds
    imgs = []
    for (ah, av, sh) in views:
        img = np.full((H, W, 3), 255, np.uint8)
        zb = np.full((H, W), -1e18)
        ad = 3 - ah - av
        sp_h = (hi[ah] - lo[ah]) * 1.04 + 1e-6
        sp_v = (hi[av] - lo[av]) * 1.04 + 1e-6
        s = min(W / sp_h, H / sp_v)
        cx = (hi[ah] + lo[ah]) / 2; cy = (hi[av] + lo[av]) / 2
        # depth: toward viewer. view looks along -ad for ad axis positive toward camera
        dsign = 1.0 if (ah, av) != (0, 2) else -1.0
        if (ah, av) == (1, 2):
            dsign = 1.0 if sh > 0 else -1.0
        for verts, tris, col in meshes:
            P = verts
            x = sh * (P[:, ah] - cx) * s + W / 2
            y = H / 2 - (P[:, av] - cy) * s
            z = P[:, ad] * dsign
            a = P[tris[:, 1]] - P[tris[:, 0]]; b = P[tris[:, 2]] - P[tris[:, 0]]
            n = np.cross(a, b); n /= (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
            L = np.zeros(3); L[ad] = dsign; L[av] = 0.5; L[ah] = 0.3 * sh; L /= np.linalg.norm(L)
            shade = np.abs(n @ L) * 0.7 + 0.3
            cols = np.asarray(col, dtype=np.float64)
            if cols.ndim == 1:
                cols = np.tile(cols, (len(tris), 1))
            _raster(img, zb, x, y, z, tris, cols, shade)
        im = Image.fromarray(img)
        dr = ImageDraw.Draw(im)
        if joints is not None:
            for j in joints:
                px = sh * (j[ah] - cx) * s + W / 2; py = H / 2 - (j[av] - cy) * s
                dr.ellipse([px - 3, py - 3, px + 3, py + 3], outline=(255, 0, 0), width=2)
        imgs.append(im)
    out_im = Image.new('RGB', (W * len(imgs), H), 'white')
    for i, im in enumerate(imgs):
        out_im.paste(im, (i * W, 0))
    out_im.save(out)
    return out_im
