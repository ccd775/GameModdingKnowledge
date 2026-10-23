"""Remap Karin_Original's per-texture UVs into one 2x2 atlas and give every face one material (Blender 5.0).

blender -b <fit.blend> --python aco_pack_atlas.py -- <out.blend> <material name> [--drop Karin_Alpha]

Quadrants (Blender UV, v up = image top): Face top-left, Body top-right, Hair (+Hair_Transparent) bottom-left,
Costume bottom-right; u' = u/2 + ou, v' = v/2 + ov. The matching image is built by build_atlas.py.
Faces of --drop materials are deleted (Karin_Alpha: tear/blush overlays that only show through expression keys).
"""
import sys

import bmesh
import bpy

argv = sys.argv[sys.argv.index("--") + 1:]
out_blend, mat_name = argv[0], argv[1]
DROP = set(argv[argv.index("--drop") + 1].split(",")) if "--drop" in argv else set()
QUAD = {"Karin_Face": (0.0, 0.5), "Karin_Body": (0.5, 0.5), "Karin_Hair": (0.0, 0.0),
        "Karin_Hair_Transparent": (0.0, 0.0), "Karin_Costume": (0.5, 0.0)}

target = bpy.data.materials.get(mat_name) or bpy.data.materials.new(mat_name)
report = {}
for o in [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith("NaoeHeadRef")]:
    me = o.data
    names = [s.material.name.split(".")[0] if s.material else None for s in o.material_slots]
    bm = bmesh.new()
    bm.from_mesh(me)
    uv = bm.loops.layers.uv[0]
    dead = []
    for f in bm.faces:
        src = names[f.material_index]
        if src in DROP:
            dead.append(f)
            continue
        if src not in QUAD:
            raise SystemExit(f"unmapped material {src} on {o.name}")
        ou, ov = QUAD[src]
        for loop in f.loops:
            u, v = loop[uv].uv
            if not (-0.001 <= u <= 1.001 and -0.001 <= v <= 1.001):
                raise SystemExit(f"{o.name}: UV ({u:.3f}, {v:.3f}) outside 0..1 on {src}")
            loop[uv].uv = (u * 0.5 + ou, v * 0.5 + ov)
        f.material_index = 0
        report[src] = report.get(src, 0) + 1
    bmesh.ops.delete(bm, geom=dead, context='FACES')
    bm.to_mesh(me)
    bm.free()
    me.materials.clear()
    me.materials.append(target)
print("PACK faces per source material", report)
bpy.ops.wm.save_as_mainfile(filepath=out_blend)
print("PACK_OK", out_blend)
