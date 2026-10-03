"""Build a Watch Dogs char01 XBG directly from an FBX handoff, without ZModeler.

  python build_xbg_from_fbx.py --fbx X.fbx --template-xbg T.xbg --output OUT.xbg
      [--lod0 NAME --lod1 NAME] [--report OUT.json] [--force]

The template supplies header constants, material tables, the char01
skeleton and the constant skeleton/physics block; every mesh-dependent field
(palette, bounds, descriptors, GPU buffers) is regenerated.  The output is
decoded again and compared with the intended data before it is accepted.
An existing output or report is refused unless --force is given.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).parent))
import fbx_mesh  # noqa: E402
import fbx_reader  # noqa: E402
import fbx_to_xbg  # noqa: E402
import xbg_codec  # noqa: E402
import xbg_model  # noqa: E402



def verify(out: bytes, lods: list[list[xbg_codec.Submesh]], path: Path) -> dict:
    path.write_bytes(out)
    x = xbg_model.load(path)
    scale, back = xbg_codec.decode(x)
    rows = []
    inv = np.float32(1.0) / np.float32(scale)
    for li, (want, got) in enumerate(zip(lods, back)):
        for a, b in zip(want, got):
            # exact comparison of what was meant to be stored vs what was read back
            q_want = np.clip(xbg_codec.c_round(a.positions.astype(np.float32) * inv), -32767, 32767)
            q_got = np.round(b.positions / scale).astype(np.int64)
            uv_want = [np.clip(xbg_codec.c_round(u * xbg_codec.UV_ONE), -32767, 32767) for u in (a.uv0, a.uv1)]
            uv_got = [np.round(u * xbg_codec.UV_ONE).astype(np.int64) for u in (b.uv0, b.uv1)]
            rows.append(
                {
                    "lod": li,
                    "material": a.material,
                    "vertices": len(a.positions),
                    "triangles": len(a.triangles),
                    "max_position_error_m": float(np.abs(a.positions - b.positions).max()),
                    "positions_equal": bool(np.array_equal(q_want, q_got)),
                    "normals_equal": bool(np.array_equal(xbg_codec._normal_bytes(a.normals), xbg_codec._normal_bytes(b.normals))),
                    "uv_equal": bool(all(np.array_equal(w, g) for w, g in zip(uv_want, uv_got))),
                    "color_equal": bool(np.array_equal(a.color, b.color)),
                    "triangles_equal": bool(np.array_equal(a.triangles, b.triangles)),
                    "weights_equal": bool(np.array_equal(a.weights, b.weights)),
                    "bones_equal": bool(np.array_equal(np.where(a.weights > 0, a.bones, -1), b.bones)),
                }
            )
    flags = ("positions_equal", "normals_equal", "uv_equal", "color_equal", "triangles_equal", "weights_equal", "bones_equal")
    ok = all(all(r[k] for k in flags) for r in rows)
    return {"status": "PASS" if ok else "FAIL", "position_scale": scale, "submeshes": rows}


def main() -> None:
    ap = argparse.ArgumentParser(description="Build a Watch Dogs char01 XBG from an FBX handoff without ZModeler.")
    ap.add_argument("--fbx", required=True, type=Path)
    ap.add_argument("--template-xbg", required=True, type=Path)
    ap.add_argument("--output", required=True, type=Path)
    ap.add_argument("--lod0", default=None)
    ap.add_argument("--lod1", default=None)
    ap.add_argument("--report", type=Path, default=None)
    ap.add_argument("--force", action="store_true", help="overwrite an existing output/report")
    args = ap.parse_args()
    if args.output.resolve() == args.template_xbg.resolve():
        raise SystemExit("refusing to overwrite the template")
    for target in (args.output, args.report):
        if target is not None and target.exists() and not args.force:
            raise SystemExit(f"refusing to overwrite existing {target} (use --force)")

    template = xbg_model.load(args.template_xbg)
    scene = fbx_reader.load(args.fbx)
    models = fbx_mesh.mesh_models(scene)
    names = [args.lod0 or next(n for n in models if "LOD0" in n), args.lod1 or next(n for n in models if "LOD1" in n)]
    conv = fbx_to_xbg.Conventions()
    lods = [fbx_to_xbg.convert_lod(fbx_mesh.extract(scene, models[n]), template, conv) for n in names]
    out = xbg_codec.encode(template, lods)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    check = verify(out, lods, args.output)
    report = {
        "schema": "watchdogs.xbg_writer.build.v1",
        "fbx": str(args.fbx),
        "fbx_sha256": hashlib.sha256(args.fbx.read_bytes()).hexdigest().upper(),
        "template": str(args.template_xbg),
        "template_sha256": hashlib.sha256(template.data).hexdigest().upper(),
        "lod_models": names,
        "output": str(args.output),
        "output_bytes": len(out),
        "output_sha256": hashlib.sha256(out).hexdigest().upper(),
        "faces": [sum(len(s.triangles) for s in subs) for subs in lods],
        "readback": check,
    }
    if args.report:
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: report[k] for k in ("output_sha256", "output_bytes", "faces")}, indent=1))
    print("READBACK", check["status"])
    if check["status"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
