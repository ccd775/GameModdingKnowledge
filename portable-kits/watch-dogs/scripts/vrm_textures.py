"""Compose the char01 slot textures and the UV layout for a VRM, driven by a profile.

  python vrm_textures.py MODEL.vrm PROFILE.json OUT_DIR [--force]

Profile "materials": {VRM material name: {"slot": "head" | "coat" | "hair" | "lashes", "spec": "skin" | "cloth" | "hair"}}.
Every material a mesh uses must be listed.  Per slot, materials are grouped by base-colour texture in profile order:
  * one texture    -> used as is; every material keeps the full UV square;
  * two textures   -> stacked top / bottom, each squeezed into its half with an edge-replicated gutter;
  * three or more  -> a grid with ceil(sqrt(n)) columns.
Atlases are composed at twice the donor's high-stream width (gutter = width / 128).  The lashes slot holds one
texture, cropped to the UV region its geometry uses and resized to four times the donor size.  Coat and hair
get flat normal maps and constant specular per region (skin / cloth / hair); the head keeps the base mod's
normal and specular unless the profile sets "replace_head_maps": true.  xbt_encode.py resizes to the donors.
Writes <slot>_<d|n|s>.png and layout.json (slot index and UV rectangle per material, texture key -> PNG).
"""

from __future__ import annotations

import argparse
import io
import json
import math
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import char01_paths  # noqa: E402
import vrm_model  # noqa: E402

FLAT_N = (255, 128, 0, 128)  # DXT5nm-style flat normal, as in the Karin 1.3 base head normal
SPEC = {"skin": (49, 8, 99), "cloth": (82, 0, 82), "hair": (0, 12, 198)}  # Karin 1.3 base per-region constants
DEFAULT_SPEC = {"head": "skin", "coat": "cloth", "hair": "hair"}
# high-stream donor sizes of the Karin 1.3.0 base; the builder passes the real donor sizes
DEFAULT_SIZE = {"head": (1024, 1024), "coat": (2048, 2048), "hair": (512, 512), "lashes": (256, 128)}
GUTTER = 128  # atlas width / GUTTER = gutter pixels per side
SLOTS = ("head", "coat", "hair", "lashes")


def fit_into(img: Image.Image, w: int, h: int, g: int) -> np.ndarray:
    """Resize to (w-2g, h-2g) and pad by edge replication to (w, h)."""
    core = np.asarray(img.convert("RGB").resize((w - 2 * g, h - 2 * g), Image.LANCZOS))
    return np.pad(core, ((g, g), (g, g), (0, 0)), mode="edge")


def cells(n: int, size: int) -> list[tuple[int, int, int, int]]:
    """(x, y, w, h) per texture: two textures stacked top/bottom, more in a grid."""
    if n == 2:
        return [(0, 0, size, size // 2), (0, size // 2, size, size // 2)]
    cols = math.ceil(math.sqrt(n))
    rows = math.ceil(n / cols)
    cw, ch = size // cols, size // rows
    return [((j % cols) * cw, (j // cols) * ch, cw, ch) for j in range(n)]


def material_images(m: vrm_model.Vrm) -> tuple[dict, dict]:
    """Material index -> (image key, PIL image, label); factor-only materials get a 4x4 solid image."""
    images, out = {}, {}
    for i, mat in enumerate(m.json.get("materials", [])):
        pbr = mat.get("pbrMetallicRoughness", {})
        tex = pbr.get("baseColorTexture")
        if tex is not None:
            src = m.json["textures"][tex["index"]]["source"]
            if src not in images:
                images[src] = Image.open(io.BytesIO(m.image_bytes(src)))
            out[i] = (src, images[src], m.json["images"][src].get("name", f"image{src}"))
        else:
            rgba = tuple(int(round(255 * c)) for c in pbr.get("baseColorFactor", [1, 1, 1, 1]))
            out[i] = (f"factor{i}", Image.new("RGBA", (4, 4), rgba), f"baseColorFactor{list(rgba)}")
    return out, images


def uv_islands(tri: np.ndarray, n: int) -> np.ndarray:
    """Island id per vertex: vertices joined by triangles (glTF splits vertices on UV seams)."""
    parent = np.arange(n)

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    for a, b, c in tri:
        ra, rb, rc = find(a), find(b), find(c)
        parent[rb] = ra
        parent[find(rc)] = ra
    return np.array([find(i) for i in range(n)])


def shelf_pack(sizes: list[tuple[int, int]], width: int, height: int, gap: int) -> list[tuple[int, int]] | None:
    """Positions for rectangles (tallest first, left to right in rows), or None when they do not fit."""
    order = sorted(range(len(sizes)), key=lambda i: (-sizes[i][1], -sizes[i][0]))
    pos: list = [None] * len(sizes)
    x = y = row_h = 0
    for i in order:
        w, h = sizes[i]
        if w + gap > width:
            return None
        if x + w + gap > width:
            x, y, row_h = 0, y + row_h, 0
        if y + h + gap > height:
            return None
        pos[i] = (x + gap, y + gap)
        x += w + gap
        row_h = max(row_h, h + gap)
    return pos


def repack_slot(m: vrm_model.Vrm, prims: list[int], images: dict, canvas: tuple[int, int], rgba: bool,
                pad_px: int = 6, gap: int = 4, density: dict | None = None) -> tuple[Image.Image, dict, list]:
    """Copy every UV island of the given primitives (each from its material's base-colour image) into one canvas,
    uniformly scaled as large as the shelf packing allows (never above the source resolution); density maps a
    primitive to an extra scale factor (e.g. 2 for a part that is large on screen).  Pixels outside the islands'
    triangles are then refilled from the nearest island pixel, so filtering and mip levels never mix in what lay
    around the island in the source atlas (black there).  Returns the canvas, the new UVs per primitive and the
    placed rectangles (primitive, canvas box)."""
    W, H = canvas
    density = density or {}
    items = []  # (prim, vertex index array, source image, source box)
    for pi in prims:
        p = m.primitives[pi]
        img = images[p.material][1]
        iw, ih = img.size
        isl = uv_islands(p.triangles, len(p.uv0))
        used_v = np.unique(p.triangles)
        for root in np.unique(isl[used_v]):
            vs = used_v[isl[used_v] == root]
            uv = p.uv0[vs]
            x0 = max(int(np.floor(uv[:, 0].min() * iw)) - pad_px, 0)
            y0 = max(int(np.floor(uv[:, 1].min() * ih)) - pad_px, 0)
            x1 = min(int(np.ceil(uv[:, 0].max() * iw)) + pad_px, iw)
            y1 = min(int(np.ceil(uv[:, 1].max() * ih)) + pad_px, ih)
            items.append((pi, vs, img, (x0, y0, max(x1, x0 + 1), max(y1, y0 + 1))))
    src = [(b[2] - b[0], b[3] - b[1]) for *_, b in items]
    fac = [float(density.get(it[0], 1.0)) for it in items]

    def attempt(s):
        return shelf_pack([(max(1, int(np.ceil(w * s * f))), max(1, int(np.ceil(h * s * f))))
                           for (w, h), f in zip(src, fac)], W, H, gap)

    best = (1.0 / max(fac), attempt(1.0 / max(fac)))  # never above the source resolution
    if best[1] is None:
        lo, hi, best = 0.0, 1.0, None
        for _ in range(20):  # largest uniform scale that packs
            mid = (lo + hi) / 2
            pos = attempt(mid)
            if pos is not None:
                best, lo = (mid, pos), mid
            else:
                hi = mid
        if best is None:
            raise ValueError("UV islands do not fit the slot canvas")
    s, pos = best
    mode = "RGBA" if rgba else "RGB"
    out = Image.new(mode, (W, H), (0, 0, 0, 0) if rgba else (0, 0, 0))
    new_uv = {pi: m.primitives[pi].uv0.copy() for pi in prims}
    boxes = []
    for (pi, vs, img, (x0, y0, x1, y1)), (px, py), f in zip(items, pos, fac):
        w, h = max(1, int(np.ceil((x1 - x0) * s * f))), max(1, int(np.ceil((y1 - y0) * s * f)))
        out.paste(img.convert(mode).crop((x0, y0, x1, y1)).resize((w, h), Image.LANCZOS), (px, py))
        iw, ih = img.size
        sx, sy = w / (x1 - x0), h / (y1 - y0)
        uv = m.primitives[pi].uv0[vs]
        new_uv[pi][vs, 0] = (px + (uv[:, 0] * iw - x0) * sx) / W
        new_uv[pi][vs, 1] = (py + (uv[:, 1] * ih - y0) * sy) / H
        boxes.append((pi, (px, py, px + w, py + h)))
    # coverage of the islands' own triangles (grown by 2 px); everything else is refilled from the nearest covered
    # pixel, so bilinear filtering and the mip levels only ever see island colours
    from PIL import ImageDraw
    from scipy import ndimage
    mask_img = Image.new("L", (W, H), 0)
    draw = ImageDraw.Draw(mask_img)
    for pi in prims:
        uvp = new_uv[pi] * np.array([W, H])
        for tri in m.primitives[pi].triangles:
            draw.polygon([tuple(uvp[k]) for k in tri], fill=255)
    filled = ndimage.binary_dilation(np.asarray(mask_img) > 0, iterations=2)
    px_arr = np.asarray(out).copy()
    iy, ix = ndimage.distance_transform_edt(~filled, return_distances=False, return_indices=True)
    rgb = px_arr[..., :3][iy, ix]
    px_arr[..., :3] = rgb
    out = Image.fromarray(px_arr, mode)
    return out, new_uv, boxes


def compose(m: vrm_model.Vrm, profile: dict, out: Path, sizes: dict | None = None) -> dict:
    sizes = {**DEFAULT_SIZE, **(sizes or {})}
    mats = profile["materials"]
    names = [mt.get("name", f"material{i}") for i, mt in enumerate(m.json.get("materials", []))]
    used = sorted({p.material for p in m.primitives})
    missing = [names[i] for i in used if names[i] not in mats]
    if missing:
        raise ValueError(f"profile does not assign a slot to materials {missing}")
    bad = {k: v.get("slot") for k, v in mats.items() if v.get("slot") not in SLOTS}
    if bad:
        raise ValueError(f"unknown slots {bad}; use one of {SLOTS}")
    images, _ = material_images(m)
    index = {n: i for i, n in enumerate(names)}
    layout = {"vertex_color_rgba": [1.0, 1.0, 1.0, 1.0], "uv1": "zero", "materials": {}, "textures": {}, "warnings": [],
              "_uv": {}}  # primitive index -> repacked UVs (not written to layout.json)
    out.mkdir(parents=True, exist_ok=True)

    def save(img: Image.Image, slot: str, kind: str):
        name = f"{slot}_{kind}.png"
        img.save(out / name)
        layout["textures"][char01_paths.texture_key(slot, kind)] = name

    for slot in SLOTS:
        members = [n for n, v in mats.items() if v["slot"] == slot and n in index and index[n] in used]
        if not members:
            continue
        if slot in profile.get("repack_slots", []):
            # one canvas per slot holding every UV island of its materials, whatever atlas page they came from
            prims = [i for i, p in enumerate(m.primitives) if names[p.material] in members]
            if slot == "lashes":
                canvas = (4 * sizes["lashes"][0], 4 * sizes["lashes"][1])
            else:  # "texture_size" raises the diffuse above the donor's size (xbt_encode.encode(..., top=...))
                top = profile.get("texture_size", {}).get(slot, sizes[slot])
                canvas = (2 * top[0], 2 * top[1])
            dens = {pi: f for pi in prims for prefix, f in profile.get("repack_density", {}).items()
                    if m.node_names[m.prim_node[pi]].startswith(prefix)}
            img, new_uv, boxes = repack_slot(m, prims, images, canvas, rgba=slot == "lashes", density=dens)
            save(img, slot, "d")
            layout["_uv"].update(new_uv)
            for n in members:
                layout["materials"][n] = {"slot": char01_paths.SLOT_INDEX[slot], "rect": [0.0, 0.0, 1.0, 1.0],
                                          "source_texture": "repacked"}
            layout.setdefault("repacked", {})[slot] = {"islands": len(boxes), "canvas": list(canvas),
                                                       "coverage": round(sum((b[2] - b[0]) * (b[3] - b[1]) for _, b in boxes)
                                                                         / (canvas[0] * canvas[1]), 3)}
            if slot != "lashes" and (slot != "head" or profile.get("replace_head_maps")):
                spec_px = Image.new("RGB", canvas, SPEC[DEFAULT_SPEC[slot]])
                for pi, box in boxes:
                    kind = mats[names[m.primitives[pi].material]].get("spec", DEFAULT_SPEC[slot])
                    spec_px.paste(SPEC[kind], box)
                save(spec_px, slot, "s")
                save(Image.new("RGBA", sizes[slot], FLAT_N), slot, "n")
            continue
        groups: dict = {}
        for n in members:
            key, img, label = images[index[n]]
            groups.setdefault(key, {"img": img, "label": label, "materials": []})["materials"].append(n)
        keys = list(groups)
        if slot == "lashes":
            if len(keys) > 1:
                raise ValueError(f"the lashes slot takes one texture, got {[groups[k]['label'] for k in keys]}")
            g = groups[keys[0]]
            uv = np.vstack([p.uv0 for p in m.primitives if names[p.material] in g["materials"]])
            pad = 0.01
            c0 = np.clip(uv.min(0) - pad, 0, 1)
            c1 = np.clip(uv.max(0) + pad, 0, 1)
            a = g["img"].convert("RGBA")
            W, H = a.size
            box = (int(c0[0] * W), int(c0[1] * H), int(np.ceil(c1[0] * W)), int(np.ceil(c1[1] * H)))
            crop = a.crop(box)
            c0 = np.array([box[0] / W, box[1] / H])
            c1 = np.array([box[2] / W, box[3] / H])
            lw, lh = sizes["lashes"]
            save(crop.resize((4 * lw, 4 * lh), Image.LANCZOS), slot, "d")
            size = c1 - c0
            rect = [float(-c0[0] / size[0]), float(-c0[1] / size[1]), float(-c0[0] / size[0] + 1 / size[0]),
                    float(-c0[1] / size[1] + 1 / size[1])]
            for n in g["materials"]:
                layout["materials"][n] = {"slot": char01_paths.SLOT_INDEX[slot], "rect": rect, "source_texture": g["label"]}
            layout["alpha_crop_uv"] = [c0.tolist(), c1.tolist()]
            continue
        kinds = [mats[groups[k]["materials"][0]].get("spec", DEFAULT_SPEC[slot]) for k in keys]
        if slot in profile.get("crop_slots", []):
            # atlas pages shared between slots: keep only the UV region this slot's materials use, so that e.g. the
            # face does not spend its slot on the body skin packed next to it
            crops = {}
            for k in keys:
                g = groups[k]
                uv = np.vstack([p.uv0 for p in m.primitives if names[p.material] in g["materials"]])
                W, H = g["img"].size
                c0 = np.clip(uv.min(0) - 0.004, 0, 1)
                c1 = np.clip(uv.max(0) + 0.004, 0, 1)
                box = (int(c0[0] * W), int(c0[1] * H), int(np.ceil(c1[0] * W)), int(np.ceil(c1[1] * H)))
                g["img"] = g["img"].crop(box)
                crops[k] = (np.array([box[0] / W, box[1] / H]), np.array([box[2] / W, box[3] / H]))
            layout.setdefault("crops", {})[slot] = {groups[k]["label"]: [crops[k][0].tolist(), crops[k][1].tolist()]
                                                    for k in keys}
        else:
            crops = {}
        if len(keys) == 1:
            save(groups[keys[0]]["img"].convert("RGB"), slot, "d")
            rects = [[0.0, 0.0, 1.0, 1.0]]
            spec = Image.new("RGB", sizes[slot], SPEC[kinds[0]])
        else:
            S = 2 * sizes[slot][0]
            G = S // GUTTER
            canvas = np.zeros((S, S, 3), np.uint8)
            spec_px = np.zeros((S, S, 3), np.uint8)
            rects = []
            for k, kind, (x, y, w, h) in zip(keys, kinds, cells(len(keys), S)):
                canvas[y:y + h, x:x + w] = fit_into(groups[k]["img"], w, h, G)
                spec_px[y:y + h, x:x + w] = SPEC[kind]
                rects.append([(x + G) / S, (y + G) / S, (x + w - G) / S, (y + h - G) / S])
            save(Image.fromarray(canvas), slot, "d")
            spec = Image.fromarray(spec_px)
            outside = [n for n in members if any(
                (p.uv0.min() < -1e-4 or p.uv0.max() > 1 + 1e-4) for p in m.primitives if names[p.material] == n)]
            if outside:
                layout["warnings"].append(f"{slot}: UVs outside 0..1 (tiling) cannot be atlased cleanly: {outside}")
        for k, rect in zip(keys, rects):
            if k in crops:  # material UV -> cropped image -> cell: u' = x0 + (u - c0) * (x1 - x0) / (c1 - c0)
                c0, c1 = crops[k]
                s = (np.array(rect[2:]) - np.array(rect[:2])) / (c1 - c0)
                o = np.array(rect[:2]) - c0 * s
                rect = [float(o[0]), float(o[1]), float(o[0] + s[0]), float(o[1] + s[1])]
            for n in groups[k]["materials"]:
                layout["materials"][n] = {"slot": char01_paths.SLOT_INDEX[slot], "rect": [float(r) for r in rect],
                                          "source_texture": groups[k]["label"]}
        if slot != "head" or profile.get("replace_head_maps"):
            save(spec, slot, "s")
            save(Image.new("RGBA", sizes[slot], FLAT_N), slot, "n")
    (out / "layout.json").write_text(json.dumps({k: v for k, v in layout.items() if k != "_uv"}, indent=1) + "\n",
                                     encoding="utf-8")
    return layout


def main() -> None:
    ap = argparse.ArgumentParser(description="Compose char01 slot textures and the UV layout for a VRM.")
    ap.add_argument("vrm", type=Path)
    ap.add_argument("profile", type=Path)
    ap.add_argument("out_dir", type=Path)
    ap.add_argument("--force", action="store_true", help="write into a non-empty output directory")
    args = ap.parse_args()
    if args.out_dir.exists() and any(args.out_dir.iterdir()) and not args.force:
        raise SystemExit(f"refusing to write into non-empty {args.out_dir} (use --force)")
    layout = compose(vrm_model.load(args.vrm), json.loads(args.profile.read_text(encoding="utf-8")), args.out_dir)
    print(json.dumps(layout["materials"], indent=1))
    for w in layout["warnings"]:
        print("WARNING", w)


if __name__ == "__main__":
    main()
