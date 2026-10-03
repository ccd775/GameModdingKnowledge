"""Build a Watch Dogs char01 replacer from a humanoid VRM, without ZModeler, Blender or texconv.

  python build_from_vrm.py --vrm MODEL.vrm --profile PROFILE.json --base-fat OLD.fat --out-dir OUT
         [--package --pack NAME --friendly-id ID --name TEXT --version X
          [--description TEXT] [--author NAME] [--modconfig FILE] [--zip-date YYYY-MM-DD]] [--force]

--base-fat is an existing char01 replacer pack whose char01.xbg was exported by ZModeler (that layout is the
writer's template) and whose XBTs serve as texture donors.  Steps:
  1. take the template XBG and the donor XBTs out of the base pack (OUT/base/);
  2. compose the slot textures and the UV layout from the profile (vrm_textures, OUT/textures/);
  3. fit the model (vrm_fit), move the char01 joints (xbg_skeleton_patch), map the weights (vrm_weights),
     write char01.xbg with LOD1 = LOD0 and read it back (OUT/char01.xbg, OUT/template_fitted.xbg);
  4. encode every composed texture into its low and high stream donors (xbt_encode, OUT/xbt/);
  5. with --package: replace those entries in the base pack, write modconfig.json and the ZIP (package_mod).
OUT/build_report.json records the inputs' hashes, the fit, the skeleton change, the readback and the textures.
The profile's "chains" hold the secondary-bone rules described in vrm_weights.py.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import build_xbg_from_fbx  # noqa: E402
import char01_paths  # noqa: E402
import fbx_to_xbg  # noqa: E402
import package_mod  # noqa: E402
import vrm_assemble  # noqa: E402
import vrm_fit  # noqa: E402
import vrm_model  # noqa: E402
import vrm_textures  # noqa: E402
import vrm_weights  # noqa: E402
import xbg_codec  # noqa: E402
import xbg_model  # noqa: E402
import xbg_skeleton_patch  # noqa: E402
import xbt_encode  # noqa: E402
import xbt_tool  # noqa: E402
from repack_fat8 import path_hash  # noqa: E402
from xbg_skeleton import Skeleton  # noqa: E402


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest().upper()


def extract_base(base_fat: Path, out: Path) -> tuple[Path, dict[str, Path], dict[str, tuple[int, int]]]:
    """Template XBG, donor XBT per stream name, and the high-stream size per slot."""
    entries = package_mod.entries_of(base_fat.read_bytes(), base_fat.with_suffix(".dat").read_bytes())
    out.mkdir(parents=True, exist_ok=True)
    h = path_hash(char01_paths.XBG)
    if h not in entries:
        raise SystemExit(f"base pack has no {char01_paths.XBG} ({h:08X})")
    template = out / "char01.xbg"
    template.write_bytes(entries[h])
    donors, sizes = {}, {}
    for key, (slot, kind) in char01_paths.TEXTURES.items():
        for path in char01_paths.texture_paths(key):
            if path_hash(path) in entries:
                donor = out / (char01_paths.stream_name(path) + ".xbt")
                donor.write_bytes(entries[path_hash(path)])
                donors[char01_paths.stream_name(path)] = donor
                if kind == "d":  # the last existing stream is the high one
                    dds = xbt_tool.parse_xbt(donor.read_bytes()).dds
                    sizes[slot] = (dds.width, dds.height)
    return template, donors, sizes


def build_xbg(vrm: Path, template_path: Path, profile: dict, layout: dict, out: Path) -> tuple[dict, list]:
    sk = Skeleton(template_path)
    fit = vrm_fit.build_fit(vrm, sk)
    base = xbg_model.load(template_path)
    patched, skel_report = xbg_skeleton_patch.patch_positions(base.data, base, sk, fit.aiden_world)
    fitted = out / "template_fitted.xbg"
    fitted.write_bytes(patched)
    template = xbg_model.load(fitted)
    sk2 = Skeleton(fitted)
    for name, p in fit.aiden_world.items():
        if np.abs(sk2.head(name) - p).max() > 1e-5:
            raise SystemExit(f"patched skeleton misplaces {name}")
    mat_names = [mt.get("name", f"material{i}") for i, mt in enumerate(fit.vrm.json["materials"])]
    slot_of = {k: v["slot"] for k, v in layout["materials"].items()}
    rect_of = {k: tuple(v["rect"]) for k, v in layout["materials"].items()}
    slot_files = [p.split("\\")[-1] for p in fbx_to_xbg.template_material_paths(template)]
    rules = vrm_weights.compile_rules(profile.get("chains", []))
    levels = vrm_weights.chain_levels(fit.vrm.parent, set(fit.human_node.values()))
    weights = [vrm_weights.map_part(fit, part, sk, rules=rules, levels=levels) for part in fit.parts]
    slots = [slot_of[mat_names[p.material]] for p in fit.parts]
    rects = [rect_of[mat_names[p.material]] for p in fit.parts]
    mesh = vrm_assemble.build_mesh(fit.parts, weights, slots, rects, slot_files,
                                   tuple(layout.get("vertex_color_rgba", (1.0, 1.0, 1.0, 1.0))), layout.get("uv1", "zero"))
    lod0 = vrm_assemble.convert(mesh, template)
    lods = [lod0, lod0]  # LOD1 reuses LOD0
    data = xbg_codec.encode(template, lods)
    check = build_xbg_from_fbx.verify(data, lods, out / "char01.xbg")
    report = {
        "scale": fit.scale, "facing": "+Z (VRM 1.0)" if np.array_equal(fit.axes, vrm_fit.G2X) else "-Z (turned 180 degrees)",
        "skeleton": skel_report,
        "parts": [{"part": p.name, "material": mat_names[p.material], "slot": s, "rect": list(r),
                   "vertices": len(p.positions), "triangles": len(p.triangles)} for p, s, r in zip(fit.parts, slots, rects)],
        "submeshes": [{"slot": s.material, "vertices": len(s.positions), "triangles": len(s.triangles)} for s in lod0],
        "xbg_bytes": len(data), "xbg_sha256": sha(data), "readback": check,
    }
    return report, lods


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a Watch Dogs char01 replacer from a humanoid VRM (no ZModeler/Blender/texconv).")
    ap.add_argument("--vrm", required=True, type=Path)
    ap.add_argument("--profile", required=True, type=Path, help="material slots and chain rules (JSON)")
    ap.add_argument("--base-fat", required=True, type=Path, help="existing char01 replacer FAT with a ZModeler-layout char01.xbg")
    ap.add_argument("--out-dir", required=True, type=Path)
    ap.add_argument("--package", action="store_true", help="also write the ModManager package and ZIP")
    ap.add_argument("--pack")
    ap.add_argument("--friendly-id")
    ap.add_argument("--name")
    ap.add_argument("--version")
    ap.add_argument("--description", default=None)
    ap.add_argument("--author", default=None)
    ap.add_argument("--modconfig", type=Path, default=None)
    ap.add_argument("--zip-date", default="1980-01-01")
    ap.add_argument("--force", action="store_true", help="write into a non-empty output directory")
    args = ap.parse_args()
    if args.package and not all((args.pack, args.friendly_id, args.name, args.version)):
        ap.error("--package needs --pack, --friendly-id, --name and --version")
    out = args.out_dir
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit(f"refusing to write into non-empty {out} (use --force)")
    profile = json.loads(args.profile.read_text(encoding="utf-8"))

    template, donors, sizes = extract_base(args.base_fat, out / "base")
    m = vrm_model.load(args.vrm)
    layout = vrm_textures.compose(m, profile, out / "textures", sizes)
    report, _ = build_xbg(args.vrm, template, profile, layout, out)

    replacements = {path_hash(char01_paths.XBG): (out / "char01.xbg").read_bytes()}
    textures = {}
    for key, png in layout["textures"].items():
        streams = [p for p in char01_paths.texture_paths(key) if char01_paths.stream_name(p) in donors]
        if not streams:
            raise SystemExit(f"base pack has no donor for {key}")
        for path in streams:
            name = char01_paths.stream_name(path)
            target = out / "xbt" / f"{name}.xbt"
            info = xbt_encode.encode(out / "textures" / png, donors[name], target)
            replacements[path_hash(path)] = target.read_bytes()
            textures[name] = {"size": info["size"], "mips": info["mips"], "format": info["format"],
                              "psnr_top": info["psnr_top"], "sha256": sha(target.read_bytes())}
    result = {
        "schema": "watchdogs.build_from_vrm.v1",
        "vrm": args.vrm.name, "vrm_sha256": sha(args.vrm.read_bytes()),
        "base_fat_sha256": sha(args.base_fat.read_bytes()), "template_sha256": sha(template.read_bytes()),
        **report, "textures": textures, "layout_warnings": layout.get("warnings", []),
    }
    if args.package:
        cfg = package_mod.make_config(args.base_fat, args.modconfig, args.pack, args.friendly_id, args.name, args.version,
                                      args.description, args.author)
        y, mo, d = (int(x) for x in args.zip_date.split("-"))
        result["package"] = package_mod.package(args.base_fat, replacements, out, cfg, args.pack, (y, mo, d, 0, 0, 0))
    (out / "build_report.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: result[k] for k in ("scale", "facing", "skeleton", "submeshes", "xbg_sha256")}, indent=1))
    for w in result["layout_warnings"]:
        print("WARNING", w)
    print("READBACK", report["readback"]["status"])
    if report["readback"]["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
