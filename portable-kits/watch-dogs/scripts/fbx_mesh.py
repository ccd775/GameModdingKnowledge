"""Extract skinned triangle meshes from a binary FBX into flat per-corner arrays."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

import fbx_reader as fr


@dataclass
class FbxMesh:
    name: str
    model_matrix: np.ndarray  # 4x4, model local -> FBX global (row-vector convention: p @ M)
    control_points: np.ndarray  # (ncp,3) model local
    corner_cp: np.ndarray  # (ncorner,) control point per triangle corner
    corner_normal: np.ndarray  # (ncorner,3) model local
    corner_uv: list[np.ndarray]  # per UV layer (ncorner,2)
    uv_names: list[str]
    corner_color: np.ndarray | None  # (ncorner,4) float
    tri_material: np.ndarray  # (ntri,) material index within this model
    materials: list[str]
    skin: list[list[tuple[str, float]]]  # per control point
    polygon_tri_count: np.ndarray  # triangles per source polygon


def _euler_xyz(deg) -> np.ndarray:
    rx, ry, rz = (math.radians(a) for a in deg)
    cx, sx, cy, sy, cz, sz = math.cos(rx), math.sin(rx), math.cos(ry), math.sin(ry), math.cos(rz), math.sin(rz)
    mx = np.array([[1, 0, 0], [0, cx, sx], [0, -sx, cx]])
    my = np.array([[cy, 0, -sy], [0, 1, 0], [sy, 0, cy]])
    mz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    return mx @ my @ mz  # row-vector convention, XYZ order (X applied first)


def local_matrix(node: fr.Node) -> np.ndarray:
    p = node.props70()
    t = p.get("Lcl Translation", (0.0, 0.0, 0.0))
    r = p.get("Lcl Rotation", (0.0, 0.0, 0.0))
    s = p.get("Lcl Scaling", (1.0, 1.0, 1.0))
    pre = p.get("PreRotation", (0.0, 0.0, 0.0))
    m = np.eye(4)
    m[:3, :3] = np.diag(s) @ _euler_xyz(r) @ _euler_xyz(pre)
    m[3, :3] = t
    return m


def global_matrix(scene: fr.Scene, oid: int) -> np.ndarray:
    m = local_matrix(scene.objects[oid])
    for pid in scene.parent_ids(oid):
        node = scene.objects.get(pid)
        if node is not None and node.name == "Model":
            return m @ global_matrix(scene, pid)
    return m


def _layer(geom: fr.Node, name: str, index: int = 0):
    for le in geom.find_all(name):
        if le.props[0] == index:
            return le
    return None


def _per_corner(le: fr.Node, data_name: str, index_name: str, width: int, poly_ids, corner_cp) -> np.ndarray:
    data = le.value(data_name).reshape(-1, width)
    mapping = le.value("MappingInformationType")
    ref = le.value("ReferenceInformationType")
    if ref in ("IndexToDirect", "Index"):
        data = data[le.value(index_name)]
    if mapping == "ByPolygonVertex":
        return data
    if mapping in ("ByVertex", "ByVertice", "ByControlPoint"):
        return data[corner_cp]
    if mapping == "ByPolygon":
        return data[poly_ids]
    if mapping == "AllSame":
        return np.repeat(data[:1], len(corner_cp), 0)
    raise ValueError(f"unsupported mapping {mapping}")


def extract(scene: fr.Scene, model_id: int) -> FbxMesh:
    model = scene.objects[model_id]
    geom = scene.kids(model_id, "Geometry")[0]
    cps = geom.value("Vertices").reshape(-1, 3).astype(np.float64)
    pvi = geom.value("PolygonVertexIndex").astype(np.int64)
    ends = np.nonzero(pvi < 0)[0]
    cp = np.where(pvi < 0, -pvi - 1, pvi)
    starts = np.r_[0, ends[:-1] + 1]
    poly_of_corner = np.repeat(np.arange(len(ends)), ends - starts + 1)

    nrm = _per_corner(_layer(geom, "LayerElementNormal"), "Normals", "NormalsIndex", 3, poly_of_corner, cp)
    uvs, uv_names = [], []
    k = 0
    while (le := _layer(geom, "LayerElementUV", k)) is not None:
        uvs.append(_per_corner(le, "UV", "UVIndex", 2, poly_of_corner, cp))
        uv_names.append(le.value("Name"))
        k += 1
    col_le = _layer(geom, "LayerElementColor")
    col = None if col_le is None else _per_corner(col_le, "Colors", "ColorIndex", 4, poly_of_corner, cp)
    mat_le = _layer(geom, "LayerElementMaterial")
    poly_mat = np.zeros(len(ends), dtype=np.int64)
    if mat_le is not None:
        m = mat_le.value("Materials").astype(np.int64)
        poly_mat = m if len(m) == len(ends) else np.repeat(m[:1], len(ends))

    # fan triangulation, keeping per-corner references
    tri_corners, tri_mat, per_poly = [], [], []
    for pi, (s, e) in enumerate(zip(starts, ends)):
        n = e - s + 1
        per_poly.append(n - 2)
        for j in range(1, n - 1):
            tri_corners.append((s, s + j, s + j + 1))
            tri_mat.append(poly_mat[pi])
    tri_corners = np.array(tri_corners, dtype=np.int64)
    flat = tri_corners.reshape(-1)

    materials = [fr.obj_name(m) for m in scene.kids(model_id, "Material")]
    skin: list[list[tuple[str, float]]] = [[] for _ in range(len(cps))]
    for d in scene.kids(geom.props[0], "Deformer"):
        for cl in scene.kids(d.props[0], "Deformer"):
            bones = scene.kids(cl.props[0], "Model")
            idx = cl.value("Indexes")
            w = cl.value("Weights")
            if not bones or idx is None:
                continue
            bname = fr.obj_name(bones[0])
            for i, ww in zip(idx, w):
                skin[int(i)].append((bname, float(ww)))

    return FbxMesh(
        name=fr.obj_name(model),
        model_matrix=global_matrix(scene, model_id),
        control_points=cps,
        corner_cp=cp[flat],
        corner_normal=nrm[flat],
        corner_uv=[u[flat] for u in uvs],
        uv_names=uv_names,
        corner_color=None if col is None else col[flat],
        tri_material=np.array(tri_mat, dtype=np.int64),
        materials=materials,
        skin=skin,
        polygon_tri_count=np.array(per_poly),
    )


def mesh_models(scene: fr.Scene) -> dict[str, int]:
    return {fr.obj_name(n): oid for oid, n in scene.objects.items() if n.name == "Model" and n.props[2] == "Mesh"}
