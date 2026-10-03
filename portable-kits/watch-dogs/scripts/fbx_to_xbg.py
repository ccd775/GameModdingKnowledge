"""Convert FBX LOD meshes into xbg_codec.Submesh lists (ZModeler-free path)."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

import fbx_mesh
import xbg_codec
import xbg_model


@dataclass
class Conventions:
    # p_xbg = (p @ axes) * scale, where p is the mesh-local control point
    # (ZModeler's "Blender" axis conversion cancels the FBX model rotation)
    # or the FBX global position when apply_model_matrix is set.
    axes: np.ndarray = field(default_factory=lambda: np.diag([-1.0, -1.0, 1.0]))
    scale: float = 1.0
    apply_model_matrix: bool = False
    flip_v: bool = True  # stored v = 1 - v
    reverse_winding: bool = True  # FBX polygons are CCW, XBG triangles are CW
    weight_limit: int = 4


def quantize_weights(skin: list[tuple[str, float]], limit: int) -> tuple[list[str], list[int]]:
    merged: dict[str, float] = {}
    for name, w in skin:
        merged[name] = merged.get(name, 0.0) + w
    ranked = sorted(((w, n) for n, w in merged.items() if w > 0), key=lambda t: (-t[0], t[1]))
    total = sum(w for w, _ in ranked)  # all influences: no renormalization after the cut
    items = ranked[:limit]
    if not items or total <= 0:
        raise ValueError("vertex without skin weights")
    # ZModeler: every non-dominant weight is truncated, the dominant one
    # receives the remainder so the bytes sum to exactly 255.
    q = [0] + [int(np.float32(w / total) * np.float32(255.0)) for w, _ in items[1:]]
    q[0] = 255 - sum(q)
    keep = [(n, w) for (_, n), w in zip(items, q) if w > 0]
    return [n for n, _ in keep], [w for _, w in keep]


def template_material_paths(template: xbg_model.Xbg) -> list[str]:
    import struct

    d = template.data
    p = 0x8C
    (n,) = struct.unpack_from("<I", d, p)
    p += 4
    paths = []
    for _ in range(n):
        _, ln = struct.unpack_from("<II", d, p)
        paths.append(d[p + 8 : p + 8 + ln].rstrip(b"\0").decode("ascii"))
        p += 8 + ((ln + 3) & ~3)
    return paths


def material_slots(template: xbg_model.Xbg, fbx_materials: list[str]) -> list[tuple[int, int]]:
    """Map each FBX material (named after its .material.bin) to (slot, vertex type).

    Materials are matched by file name against the template material path
    table.  A single leftover FBX material is paired with the single leftover
    slot (the runtime template may already carry the private hair material).
    """
    paths = [p.split("\\")[-1].lower() for p in template_material_paths(template)]
    vtype = {desc.material: desc.vertex_type for desc in template.lods[0]}
    slots: list[int | None] = []
    for name in fbx_materials:
        base = name.lower()
        slots.append(paths.index(base) if base in paths else None)
    free = [i for i in range(len(paths)) if i not in slots]
    missing = [k for k, s in enumerate(slots) if s is None]
    if len(missing) == 1 and len(free) == 1:
        slots[missing[0]] = free[0]
    elif missing:
        raise KeyError(f"cannot map FBX materials {fbx_materials} onto template {paths}")
    return [(s, vtype[s]) for s in slots]  # type: ignore[index]


def convert_lod(
    mesh: fbx_mesh.FbxMesh,
    template: xbg_model.Xbg,
    conv: Conventions,
    color_layer: bool = True,
) -> list[xbg_codec.Submesh]:
    node_b = {n["name"]: n["b"] for n in template.nodes}
    slots = material_slots(template, mesh.materials)
    if conv.apply_model_matrix:
        m = mesh.model_matrix
        rot = m[:3, :3] / np.linalg.norm(m[:3, :3], axis=1, keepdims=True)
        gp = mesh.control_points @ m[:3, :3] + m[3, :3]
    else:
        rot = np.eye(3)
        gp = mesh.control_points
    gp = (gp @ conv.axes) * conv.scale
    gn = mesh.corner_normal @ rot @ conv.axes
    gn /= np.linalg.norm(gn, axis=1, keepdims=True)

    # per control point skin
    cp_bones = np.full((len(gp), 4), -1, dtype=np.int64)
    cp_w = np.zeros((len(gp), 4), dtype=np.uint8)
    for i, inf in enumerate(mesh.skin):
        names, ws = quantize_weights(inf, conv.weight_limit)
        for k, (nm, w) in enumerate(zip(names, ws)):
            if nm not in node_b:
                raise KeyError(f"bone {nm!r} not in template skeleton")
            cp_bones[i, k] = node_b[nm]
            cp_w[i, k] = w

    uv0 = mesh.corner_uv[0].copy()
    uv1 = mesh.corner_uv[1].copy() if len(mesh.corner_uv) > 1 else np.zeros_like(uv0)
    if conv.flip_v:
        uv0[:, 1] = 1.0 - uv0[:, 1]
        uv1[:, 1] = 1.0 - uv1[:, 1]
    if mesh.corner_color is not None and color_layer:
        rgba = np.clip(np.round(mesh.corner_color * 254.0), 0, 255).astype(np.uint8)
        rgba[:, 3] = 255
        color = rgba[:, [2, 1, 0, 3]]
    else:
        color = np.tile(np.array([254, 254, 254, 255], np.uint8), (len(uv0), 1))

    subs = []
    tri_corner = np.arange(len(mesh.corner_cp)).reshape(-1, 3)
    for local_mat, (slot, vtype) in enumerate(slots):
        tris = tri_corner[mesh.tri_material == local_mat]
        if len(tris) == 0:
            continue
        corners = tris.reshape(-1)
        cp = mesh.corner_cp[corners]
        # dedupe on the encoded representation of every per-vertex attribute
        key = np.column_stack(
            [
                cp,
                xbg_codec._normal_bytes(gn[corners])[:, :3].astype(np.int64),
                xbg_codec.c_round(uv0[corners] * xbg_codec.UV_ONE),
                xbg_codec.c_round(uv1[corners] * xbg_codec.UV_ONE),
                color[corners].astype(np.int64),
            ]
        )
        _, first, inverse = np.unique(key, axis=0, return_index=True, return_inverse=True)
        order = np.argsort(first)  # first-appearance order
        rank = np.empty_like(order)
        rank[order] = np.arange(len(order))
        local = rank[inverse.reshape(-1)].reshape(-1, 3)
        src = corners[first[order]]
        if conv.reverse_winding:
            local = local[:, [0, 2, 1]]
        vcp = mesh.corner_cp[src]
        subs.append(
            xbg_codec.Submesh(
                material=slot,
                vertex_type=vtype,
                positions=gp[vcp],
                normals=gn[src],
                uv0=uv0[src],
                uv1=uv1[src],
                color=color[src],
                weights=cp_w[vcp],
                bones=cp_bones[vcp],
                triangles=local,
            )
        )
    subs.sort(key=lambda s: s.material)
    return subs
