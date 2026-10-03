"""Turn fitted VRM parts (vrm_fit.Part) into writer input (an fbx_mesh.FbxMesh) and char01 submeshes."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import fbx_mesh  # noqa: E402
import fbx_to_xbg  # noqa: E402

AXES = np.diag([-1.0, -1.0, 1.0])  # XBG <-> FBX mesh-local (its own inverse)


def build_mesh(parts, part_weights, part_slot, part_uv_rect, slot_material_names, color_rgba=None, uv1_mode="zero"):
    """parts: vrm_fit.Part list; part_weights: per part list[dict bone->w]; part_slot: per part slot index;
    part_uv_rect: per part (u0, v0, u1, v1) atlas rectangle in stored (top-left origin) UV space;
    slot_material_names: .material.bin file name per slot.
    Returns an fbx_mesh.FbxMesh whose material list is indexed by slot."""
    cps, corner_cp, normals, uv0s, skins, tri_mat = [], [], [], [], [], []
    base = 0
    for part, wts, slot, rect in zip(parts, part_weights, part_slot, part_uv_rect):
        n = len(part.positions)
        cps.append(part.positions @ AXES)
        u0, v0, u1, v1 = rect
        uv = np.column_stack([u0 + part.uv[:, 0] * (u1 - u0), v0 + part.uv[:, 1] * (v1 - v0)])
        tri = part.triangles + base
        corner_cp.append(tri.reshape(-1))
        normals.append(part.normals[part.triangles.reshape(-1)] @ AXES)
        uv0s.append(uv[part.triangles.reshape(-1)])
        skins.extend([sorted(d.items(), key=lambda kv: -kv[1]) for d in wts])
        tri_mat.append(np.full(len(part.triangles), slot))
        base += n
    corner_cp = np.concatenate(corner_cp)
    uv_stored = np.vstack(uv0s)
    uv_fbx = np.column_stack([uv_stored[:, 0], 1.0 - uv_stored[:, 1]])  # convert_lod flips v back
    uv1 = uv_fbx.copy() if uv1_mode == "uv0" else np.zeros_like(uv_fbx)
    color = None
    if color_rgba is not None:
        color = np.tile(np.asarray(color_rgba, float), (len(corner_cp), 1))
    return fbx_mesh.FbxMesh(
        name="vrm_model",
        model_matrix=np.eye(4),
        control_points=np.vstack(cps),
        corner_cp=corner_cp,
        corner_normal=np.vstack(normals),
        corner_uv=[uv_fbx, uv1],
        uv_names=["UVSet0", "UVSet1"],
        corner_color=color,
        tri_material=np.concatenate(tri_mat),
        materials=list(slot_material_names),
        skin=skins,
        polygon_tri_count=np.ones(len(corner_cp) // 3, dtype=np.int64),
    )


def convert(mesh, template):
    return fbx_to_xbg.convert_lod(mesh, template, fbx_to_xbg.Conventions())
