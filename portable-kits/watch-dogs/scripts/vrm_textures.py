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
    layout = {"vertex_color_rgba": [1.0, 1.0, 1.0, 1.0], "uv1": "zero", "materials": {}, "textures": {}, "warnings": []}
    out.mkdir(parents=True, exist_ok=True)

    def save(img: Image.Image, slot: str, kind: str):
        name = f"{slot}_{kind}.png"
        img.save(out / name)
        layout["textures"][char01_paths.texture_key(slot, kind)] = name

    for slot in SLOTS:
        members = [n for n, v in mats.items() if v["slot"] == slot and n in index and index[n] in used]
        if not members:
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
            for n in groups[k]["materials"]:
                layout["materials"][n] = {"slot": char01_paths.SLOT_INDEX[slot], "rect": [float(r) for r in rect],
                                          "source_texture": groups[k]["label"]}
        if slot != "head" or profile.get("replace_head_maps"):
            save(spec, slot, "s")
            save(Image.new("RGBA", sizes[slot], FLAT_N), slot, "n")
    (out / "layout.json").write_text(json.dumps(layout, indent=1) + "\n", encoding="utf-8")
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
