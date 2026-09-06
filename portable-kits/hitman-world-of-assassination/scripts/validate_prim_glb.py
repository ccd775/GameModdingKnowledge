#!/usr/bin/env python3
"""Validate a GLB before rebuilding it as a weighted HITMAN PRIM.

The checks mirror the structural assumptions made by RPKG Tool 2.34.0's
``rebuild_prim_in`` path. The input GLB is never modified.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable


TOOL_NAME = "validate_prim_glb"
SCHEMA_VERSION = 1

GLB_MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942

BYTE = 5120
UNSIGNED_BYTE = 5121
SHORT = 5122
UNSIGNED_SHORT = 5123
UNSIGNED_INT = 5125
FLOAT = 5126

TRIANGLES = 4
FILENAME_RE = re.compile(r"^[0-9A-Fa-f]{16}\.PRIM\.glb$")
MESH_SUFFIX_RE = re.compile(r"_(\d+)$")

REQUIRED_ATTRIBUTES = {
    "POSITION": (FLOAT, "VEC3"),
    "NORMAL": (FLOAT, "VEC3"),
    "TEXCOORD_0": (FLOAT, "VEC2"),
    "JOINTS_0": (UNSIGNED_BYTE, "VEC4"),
    "WEIGHTS_0": (FLOAT, "VEC4"),
}


@dataclass
class ParsedGlb:
    path: Path
    file_size: int = 0
    sha256: str | None = None
    header_version: int | None = None
    declared_length: int | None = None
    json_chunk_count: int = 0
    bin_chunk_count: int = 0
    document: dict[str, Any] | None = None
    issues: list[dict[str, Any]] = field(default_factory=list)


def make_issue(
    severity: str,
    code: str,
    message: str,
    location: str | None = None,
    **details: Any,
) -> dict[str, Any]:
    issue: dict[str, Any] = {
        "severity": severity,
        "code": code,
        "message": message,
    }
    if location is not None:
        issue["location"] = location
    issue.update(details)
    return issue


def read_glb(path: Path) -> ParsedGlb:
    parsed = ParsedGlb(path=path.resolve())
    try:
        data = path.read_bytes()
    except OSError as exc:
        parsed.issues.append(
            make_issue("error", "file_read_error", str(exc), str(path))
        )
        return parsed

    parsed.file_size = len(data)
    parsed.sha256 = hashlib.sha256(data).hexdigest()

    if len(data) < 12:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_header_truncated",
                "GLB header is shorter than 12 bytes.",
                "header",
                actual_size=len(data),
            )
        )
        return parsed

    magic, version, declared_length = struct.unpack_from("<4sII", data, 0)
    parsed.header_version = version
    parsed.declared_length = declared_length

    if magic != GLB_MAGIC:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_magic_invalid",
                "File does not have the GLB magic value 'glTF'.",
                "header.magic",
                actual=magic.hex(),
            )
        )
        return parsed

    if version != 2:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_version_invalid",
                "GLB container version must be 2.",
                "header.version",
                actual=version,
                expected=2,
            )
        )

    if declared_length != len(data):
        parsed.issues.append(
            make_issue(
                "error",
                "glb_length_mismatch",
                "GLB declared length does not match the file size.",
                "header.length",
                actual=len(data),
                declared=declared_length,
            )
        )

    chunks: list[tuple[int, bytes]] = []
    offset = 12
    scan_limit = min(declared_length, len(data))
    while offset < scan_limit:
        if offset + 8 > scan_limit:
            parsed.issues.append(
                make_issue(
                    "error",
                    "glb_chunk_header_truncated",
                    "A GLB chunk header is truncated.",
                    f"byte[{offset}]",
                )
            )
            break
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        chunk_end = offset + chunk_length
        if chunk_end > scan_limit:
            parsed.issues.append(
                make_issue(
                    "error",
                    "glb_chunk_truncated",
                    "A GLB chunk extends beyond the declared container length.",
                    f"byte[{offset - 8}]",
                    chunk_length=chunk_length,
                )
            )
            break
        chunks.append((chunk_type, data[offset:chunk_end]))
        offset = chunk_end

    if offset != scan_limit:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_chunk_layout_invalid",
                "GLB chunks do not exactly fill the declared container length.",
                "chunks",
                parsed_until=offset,
                expected_end=scan_limit,
            )
        )

    parsed.json_chunk_count = sum(1 for chunk_type, _ in chunks if chunk_type == JSON_CHUNK)
    parsed.bin_chunk_count = sum(1 for chunk_type, _ in chunks if chunk_type == BIN_CHUNK)

    if not chunks or chunks[0][0] != JSON_CHUNK:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_json_chunk_not_first",
                "The first GLB chunk must be JSON.",
                "chunks[0]",
            )
        )

    if parsed.json_chunk_count != 1:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_json_chunk_count",
                "A GLB must contain exactly one JSON chunk.",
                "chunks",
                actual=parsed.json_chunk_count,
                expected=1,
            )
        )
        if parsed.json_chunk_count == 0:
            return parsed

    json_payload = next(payload for chunk_type, payload in chunks if chunk_type == JSON_CHUNK)
    try:
        decoded = json_payload.rstrip(b"\x00 \t\r\n").decode("utf-8")
        document = json.loads(decoded)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        parsed.issues.append(
            make_issue(
                "error",
                "glb_json_invalid",
                f"Could not decode the GLB JSON chunk: {exc}",
                "chunks.JSON",
            )
        )
        return parsed

    if not isinstance(document, dict):
        parsed.issues.append(
            make_issue(
                "error",
                "gltf_root_invalid",
                "The glTF JSON root must be an object.",
                "$",
            )
        )
        return parsed

    parsed.document = document
    return parsed


def as_list(
    document: dict[str, Any],
    key: str,
    issues: list[dict[str, Any]],
) -> list[Any]:
    value = document.get(key, [])
    if isinstance(value, list):
        return value
    issues.append(
        make_issue(
            "error",
            "gltf_collection_invalid",
            f"glTF '{key}' must be an array.",
            key,
            actual_type=type(value).__name__,
        )
    )
    return []


def is_index(value: Any, values: list[Any]) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 0 <= value < len(values)


def get_accessor(
    accessor_index: Any,
    accessors: list[Any],
    issues: list[dict[str, Any]],
    location: str,
) -> dict[str, Any] | None:
    if not is_index(accessor_index, accessors):
        issues.append(
            make_issue(
                "error",
                "accessor_reference_invalid",
                "Accessor reference is missing or outside the accessors array.",
                location,
                accessor=accessor_index,
            )
        )
        return None
    accessor = accessors[accessor_index]
    if not isinstance(accessor, dict):
        issues.append(
            make_issue(
                "error",
                "accessor_invalid",
                "Accessor must be a JSON object.",
                f"accessors[{accessor_index}]",
            )
        )
        return None
    return accessor


def validate_accessor_shape(
    accessor: dict[str, Any],
    accessor_index: int,
    expected_component: int,
    expected_type: str,
    issues: list[dict[str, Any]],
    semantic: str,
) -> None:
    location = f"accessors[{accessor_index}]"
    if accessor.get("componentType") != expected_component:
        issues.append(
            make_issue(
                "error",
                "accessor_component_type_invalid",
                f"{semantic} has an RPKG-incompatible component type.",
                location,
                semantic=semantic,
                actual=accessor.get("componentType"),
                expected=expected_component,
            )
        )
    if accessor.get("type") != expected_type:
        issues.append(
            make_issue(
                "error",
                "accessor_element_type_invalid",
                f"{semantic} has an RPKG-incompatible accessor type.",
                location,
                semantic=semantic,
                actual=accessor.get("type"),
                expected=expected_type,
            )
        )
    count = accessor.get("count")
    if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
        issues.append(
            make_issue(
                "error",
                "accessor_count_invalid",
                f"{semantic} accessor count must be a positive integer.",
                location,
                semantic=semantic,
                actual=count,
            )
        )


def mesh_suffix(name: Any) -> int | None:
    if not isinstance(name, str):
        return None
    match = MESH_SUFFIX_RE.search(name)
    return int(match.group(1)) if match else None


def collect_skin_joint_names(
    document: dict[str, Any],
    skin_indices: Iterable[int] | None = None,
) -> tuple[set[str], dict[int, list[str]]]:
    nodes = document.get("nodes", [])
    skins = document.get("skins", [])
    if not isinstance(nodes, list) or not isinstance(skins, list):
        return set(), {}

    selected = range(len(skins)) if skin_indices is None else sorted(set(skin_indices))
    all_names: set[str] = set()
    names_by_skin: dict[int, list[str]] = {}
    for skin_index in selected:
        if not is_index(skin_index, skins) or not isinstance(skins[skin_index], dict):
            continue
        names: list[str] = []
        joints = skins[skin_index].get("joints", [])
        if not isinstance(joints, list):
            continue
        for joint in joints:
            if is_index(joint, nodes) and isinstance(nodes[joint], dict):
                name = nodes[joint].get("name")
                if isinstance(name, str) and name:
                    names.append(name)
                    all_names.add(name)
        names_by_skin[skin_index] = names
    return all_names, names_by_skin


def carrier_profile(path: Path) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    parsed = read_glb(path)
    issues = list(parsed.issues)
    if parsed.document is None:
        return None, issues

    meshes = parsed.document.get("meshes", [])
    suffixes: list[int] = []
    if isinstance(meshes, list):
        for mesh in meshes:
            if isinstance(mesh, dict):
                suffix = mesh_suffix(mesh.get("name"))
                if suffix is not None:
                    suffixes.append(suffix)
    joint_names, _ = collect_skin_joint_names(parsed.document)
    return {
        "path": str(parsed.path),
        "sha256": parsed.sha256,
        "mesh_suffixes": sorted(suffixes),
        "joint_names": sorted(joint_names),
    }, issues


def validate_glb(
    path: Path,
    *,
    require_meta: bool = True,
    carrier_path: Path | None = None,
    joint_policy: str = "subset",
) -> dict[str, Any]:
    parsed = read_glb(path)
    issues = list(parsed.issues)
    document = parsed.document

    meta_path = path.parent / "metas" / f"{path.name}.meta"
    resource_meta_path = path.parent / "metas" / f"{path.stem}.meta"
    template_meta_found = meta_path.is_file()
    resource_meta_found = resource_meta_path.is_file()
    meta_found = template_meta_found and resource_meta_found

    if not FILENAME_RE.fullmatch(path.name):
        issues.append(
            make_issue(
                "error",
                "prim_glb_filename_invalid",
                "RPKG rebuild input must be named 16HEX.PRIM.glb.",
                "filename",
                actual=path.name,
            )
        )
    if require_meta and not meta_found:
        if not template_meta_found:
            issues.append(
                make_issue(
                    "error",
                    "prim_glb_meta_missing",
                    "Required metas/16HEX.PRIM.glb.meta rebuild template is missing.",
                    str(meta_path),
                )
            )
        if not resource_meta_found:
            issues.append(
                make_issue(
                    "error",
                    "prim_resource_meta_missing",
                    "Required metas/16HEX.PRIM.meta resource metadata is missing.",
                    str(resource_meta_path),
                )
            )

    mesh_reports: list[dict[str, Any]] = []
    skin_reports: list[dict[str, Any]] = []
    suffixes: list[int] = []
    used_skin_indices: set[int] = set()
    morph_primitive_count = 0
    total_vertices = 0
    animation_count = 0

    if document is not None:
        asset = document.get("asset")
        if not isinstance(asset, dict) or asset.get("version") != "2.0":
            issues.append(
                make_issue(
                    "error",
                    "gltf_asset_version_invalid",
                    "glTF asset.version must be exactly '2.0'.",
                    "asset.version",
                    actual=asset.get("version") if isinstance(asset, dict) else None,
                    expected="2.0",
                )
            )

        meshes = as_list(document, "meshes", issues)
        nodes = as_list(document, "nodes", issues)
        skins = as_list(document, "skins", issues)
        accessors = as_list(document, "accessors", issues)
        animations = as_list(document, "animations", issues)
        animation_count = len(animations)

        if animation_count:
            issues.append(
                make_issue(
                    "error",
                    "animations_present",
                    "Production PRIM GLB must not contain animations.",
                    "animations",
                    count=animation_count,
                )
            )

        unsupported_extensions = sorted(
            set(document.get("extensionsRequired", []))
            & {"KHR_draco_mesh_compression", "EXT_meshopt_compression"}
        ) if isinstance(document.get("extensionsRequired", []), list) else []
        if unsupported_extensions:
            issues.append(
                make_issue(
                    "error",
                    "compressed_mesh_extension_unsupported",
                    "RPKG rebuild input must not require compressed mesh extensions.",
                    "extensionsRequired",
                    extensions=unsupported_extensions,
                )
            )

        mesh_to_nodes: dict[int, list[int]] = {index: [] for index in range(len(meshes))}
        for node_index, node in enumerate(nodes):
            if not isinstance(node, dict) or "mesh" not in node:
                continue
            mesh_index = node.get("mesh")
            if not is_index(mesh_index, meshes):
                issues.append(
                    make_issue(
                        "error",
                        "mesh_reference_invalid",
                        "Node mesh reference is outside the meshes array.",
                        f"nodes[{node_index}].mesh",
                        mesh=mesh_index,
                    )
                )
                continue
            mesh_to_nodes[mesh_index].append(node_index)
            skin_index = node.get("skin")
            if not is_index(skin_index, skins):
                issues.append(
                    make_issue(
                        "error",
                        "mesh_node_skin_missing",
                        "Every weighted mesh node must reference a valid skin.",
                        f"nodes[{node_index}].skin",
                        mesh=mesh_index,
                        skin=skin_index,
                    )
                )
            else:
                used_skin_indices.add(skin_index)

            node_weights = node.get("weights")
            if isinstance(node_weights, list) and node_weights:
                issues.append(
                    make_issue(
                        "error",
                        "node_morph_weights_present",
                        "Production PRIM GLB must not contain node morph weights.",
                        f"nodes[{node_index}].weights",
                    )
                )

        for mesh_index, mesh in enumerate(meshes):
            location = f"meshes[{mesh_index}]"
            report: dict[str, Any] = {
                "mesh_index": mesh_index,
                "name": mesh.get("name") if isinstance(mesh, dict) else None,
                "suffix": None,
                "node_indices": mesh_to_nodes.get(mesh_index, []),
                "primitive_count": 0,
                "vertex_count": None,
                "triangle_count": None,
                "attributes": [],
            }
            mesh_reports.append(report)

            if not isinstance(mesh, dict):
                issues.append(
                    make_issue("error", "mesh_invalid", "Mesh must be a JSON object.", location)
                )
                continue

            suffix = mesh_suffix(mesh.get("name"))
            report["suffix"] = suffix
            if suffix is None:
                issues.append(
                    make_issue(
                        "error",
                        "mesh_suffix_invalid",
                        "Mesh name must end in an underscore followed by a decimal object index.",
                        f"{location}.name",
                        actual=mesh.get("name"),
                    )
                )
            else:
                suffixes.append(suffix)

            refs = mesh_to_nodes.get(mesh_index, [])
            if len(refs) != 1:
                issues.append(
                    make_issue(
                        "error",
                        "mesh_node_reference_count",
                        "Every mesh must be referenced by exactly one mesh node.",
                        location,
                        node_references=refs,
                        expected_count=1,
                    )
                )

            mesh_weights = mesh.get("weights")
            if isinstance(mesh_weights, list) and mesh_weights:
                issues.append(
                    make_issue(
                        "error",
                        "mesh_morph_weights_present",
                        "Production PRIM GLB must not contain mesh morph weights.",
                        f"{location}.weights",
                    )
                )

            primitives = mesh.get("primitives")
            if not isinstance(primitives, list):
                issues.append(
                    make_issue(
                        "error",
                        "mesh_primitives_invalid",
                        "Mesh primitives must be an array.",
                        f"{location}.primitives",
                    )
                )
                continue
            report["primitive_count"] = len(primitives)
            if len(primitives) != 1:
                issues.append(
                    make_issue(
                        "error",
                        "mesh_primitive_count",
                        "RPKG rebuild accepts exactly one primitive per mesh.",
                        f"{location}.primitives",
                        actual=len(primitives),
                        expected=1,
                    )
                )
            if not primitives:
                continue

            primitive = primitives[0]
            primitive_location = f"{location}.primitives[0]"
            if not isinstance(primitive, dict):
                issues.append(
                    make_issue(
                        "error",
                        "primitive_invalid",
                        "Mesh primitive must be a JSON object.",
                        primitive_location,
                    )
                )
                continue

            mode = primitive.get("mode", TRIANGLES)
            if mode != TRIANGLES:
                issues.append(
                    make_issue(
                        "error",
                        "primitive_mode_invalid",
                        "PRIM rebuild input must use TRIANGLES mode.",
                        f"{primitive_location}.mode",
                        actual=mode,
                        expected=TRIANGLES,
                    )
                )

            targets = primitive.get("targets")
            if isinstance(targets, list) and targets:
                morph_primitive_count += 1
                issues.append(
                    make_issue(
                        "error",
                        "morph_targets_present",
                        "Production PRIM GLB must not contain morph targets.",
                        f"{primitive_location}.targets",
                        count=len(targets),
                    )
                )

            index_accessor_index = primitive.get("indices")
            index_accessor = get_accessor(
                index_accessor_index,
                accessors,
                issues,
                f"{primitive_location}.indices",
            )
            if index_accessor is not None:
                validate_accessor_shape(
                    index_accessor,
                    index_accessor_index,
                    UNSIGNED_SHORT,
                    "SCALAR",
                    issues,
                    "INDICES",
                )
                index_count = index_accessor.get("count")
                if isinstance(index_count, int) and index_count > 0:
                    report["triangle_count"] = index_count // 3
                    if index_count % 3:
                        issues.append(
                            make_issue(
                                "error",
                                "index_count_not_triangular",
                                "Triangle index count must be divisible by three.",
                                f"accessors[{index_accessor_index}].count",
                                actual=index_count,
                            )
                        )

            attributes = primitive.get("attributes")
            if not isinstance(attributes, dict):
                issues.append(
                    make_issue(
                        "error",
                        "primitive_attributes_invalid",
                        "Primitive attributes must be a JSON object.",
                        f"{primitive_location}.attributes",
                    )
                )
                continue
            report["attributes"] = sorted(attributes)

            attribute_accessors: dict[str, tuple[int, dict[str, Any]]] = {}
            for semantic, (component_type, element_type) in REQUIRED_ATTRIBUTES.items():
                if semantic not in attributes:
                    issues.append(
                        make_issue(
                            "error",
                            "required_attribute_missing",
                            f"Required weighted PRIM attribute {semantic} is missing.",
                            f"{primitive_location}.attributes",
                            semantic=semantic,
                        )
                    )
                    continue
                accessor_index = attributes[semantic]
                accessor = get_accessor(
                    accessor_index,
                    accessors,
                    issues,
                    f"{primitive_location}.attributes.{semantic}",
                )
                if accessor is None:
                    continue
                attribute_accessors[semantic] = (accessor_index, accessor)
                validate_accessor_shape(
                    accessor,
                    accessor_index,
                    component_type,
                    element_type,
                    issues,
                    semantic,
                )

            position_entry = attribute_accessors.get("POSITION")
            if position_entry is not None:
                vertex_count = position_entry[1].get("count")
                report["vertex_count"] = vertex_count
                if isinstance(vertex_count, int) and vertex_count > 0:
                    total_vertices += vertex_count
                    if vertex_count >= 65536:
                        issues.append(
                            make_issue(
                                "error",
                                "vertex_count_exceeds_uint16",
                                "Mesh vertex count must be less than 65536 for RPKG uint16 indices.",
                                f"accessors[{position_entry[0]}].count",
                                actual=vertex_count,
                                maximum=65535,
                            )
                        )
                    for semantic, (accessor_index, accessor) in attribute_accessors.items():
                        if accessor.get("count") != vertex_count:
                            issues.append(
                                make_issue(
                                    "error",
                                    "attribute_count_mismatch",
                                    f"{semantic} count must match POSITION count.",
                                    f"accessors[{accessor_index}].count",
                                    semantic=semantic,
                                    actual=accessor.get("count"),
                                    expected=vertex_count,
                                )
                            )

            has_joints_1 = "JOINTS_1" in attributes
            has_weights_1 = "WEIGHTS_1" in attributes
            if has_joints_1 != has_weights_1:
                issues.append(
                    make_issue(
                        "error",
                        "extended_weights_pair_missing",
                        "JOINTS_1 and WEIGHTS_1 must either both exist or both be absent.",
                        f"{primitive_location}.attributes",
                    )
                )
            if has_joints_1 and has_weights_1:
                for semantic, expected_component in (
                    ("JOINTS_1", UNSIGNED_BYTE),
                    ("WEIGHTS_1", FLOAT),
                ):
                    accessor_index = attributes[semantic]
                    accessor = get_accessor(
                        accessor_index,
                        accessors,
                        issues,
                        f"{primitive_location}.attributes.{semantic}",
                    )
                    if accessor is None:
                        continue
                    validate_accessor_shape(
                        accessor,
                        accessor_index,
                        expected_component,
                        "VEC4",
                        issues,
                        semantic,
                    )
                    if position_entry is not None and accessor.get("count") != position_entry[1].get("count"):
                        issues.append(
                            make_issue(
                                "error",
                                "attribute_count_mismatch",
                                f"{semantic} count must match POSITION count.",
                                f"accessors[{accessor_index}].count",
                                semantic=semantic,
                                actual=accessor.get("count"),
                                expected=position_entry[1].get("count"),
                            )
                        )

            unsupported_weight_sets = sorted(
                semantic
                for semantic in attributes
                if re.fullmatch(r"(?:JOINTS|WEIGHTS)_\d+", semantic)
                and semantic not in {"JOINTS_0", "WEIGHTS_0", "JOINTS_1", "WEIGHTS_1"}
            )
            if unsupported_weight_sets:
                issues.append(
                    make_issue(
                        "error",
                        "weight_set_unsupported",
                        "RPKG rebuild supports only JOINTS/WEIGHTS sets 0 and 1.",
                        f"{primitive_location}.attributes",
                        semantics=unsupported_weight_sets,
                    )
                )

            color_accessor_index = attributes.get("COLOR_0")
            if color_accessor_index is None:
                issues.append(
                    make_issue(
                        "warning",
                        "color_0_missing",
                        "COLOR_0 is absent; RPKG may fill carrier vertex colour with white.",
                        f"{primitive_location}.attributes",
                    )
                )
            else:
                color_accessor = get_accessor(
                    color_accessor_index,
                    accessors,
                    issues,
                    f"{primitive_location}.attributes.COLOR_0",
                )
                if color_accessor is not None:
                    if color_accessor.get("componentType") not in {UNSIGNED_BYTE, UNSIGNED_SHORT}:
                        issues.append(
                            make_issue(
                                "error",
                                "color_component_type_invalid",
                                "COLOR_0 must use unsigned byte or unsigned short components.",
                                f"accessors[{color_accessor_index}]",
                                actual=color_accessor.get("componentType"),
                            )
                        )
                    if color_accessor.get("type") != "VEC4" or color_accessor.get("normalized") is not True:
                        issues.append(
                            make_issue(
                                "error",
                                "color_format_invalid",
                                "COLOR_0 must be normalized VEC4 data.",
                                f"accessors[{color_accessor_index}]",
                                actual_type=color_accessor.get("type"),
                                normalized=color_accessor.get("normalized"),
                            )
                        )
                    if position_entry is not None and color_accessor.get("count") != position_entry[1].get("count"):
                        issues.append(
                            make_issue(
                                "error",
                                "attribute_count_mismatch",
                                "COLOR_0 count must match POSITION count.",
                                f"accessors[{color_accessor_index}].count",
                                semantic="COLOR_0",
                                actual=color_accessor.get("count"),
                                expected=position_entry[1].get("count"),
                            )
                        )

        duplicate_suffixes = sorted({suffix for suffix in suffixes if suffixes.count(suffix) > 1})
        if duplicate_suffixes:
            issues.append(
                make_issue(
                    "error",
                    "mesh_suffix_duplicate",
                    "Mesh object suffixes must be unique.",
                    "meshes",
                    suffixes=duplicate_suffixes,
                )
            )
        expected_suffixes = list(range(len(meshes)))
        if sorted(suffixes) != expected_suffixes:
            issues.append(
                make_issue(
                    "error",
                    "mesh_suffixes_not_contiguous",
                    "Mesh suffixes must form the complete contiguous range 0..mesh_count-1.",
                    "meshes",
                    actual=sorted(suffixes),
                    expected=expected_suffixes,
                )
            )

        for skin_index in sorted(used_skin_indices):
            skin = skins[skin_index]
            report: dict[str, Any] = {
                "skin_index": skin_index,
                "joint_count": 0,
                "joint_names": [],
            }
            skin_reports.append(report)
            location = f"skins[{skin_index}]"
            if not isinstance(skin, dict):
                issues.append(
                    make_issue("error", "skin_invalid", "Skin must be a JSON object.", location)
                )
                continue
            joints = skin.get("joints")
            if not isinstance(joints, list) or not joints:
                issues.append(
                    make_issue(
                        "error",
                        "skin_joints_missing",
                        "Used skin must contain at least one joint.",
                        f"{location}.joints",
                    )
                )
                continue
            report["joint_count"] = len(joints)
            if len(joints) > 256:
                issues.append(
                    make_issue(
                        "error",
                        "skin_joint_count_exceeds_ubyte",
                        "Skin has more than 256 joints but RPKG reads JOINTS as unsigned bytes.",
                        f"{location}.joints",
                        actual=len(joints),
                        maximum=256,
                    )
                )

            names: list[str] = []
            for joint_position, joint_index in enumerate(joints):
                joint_location = f"{location}.joints[{joint_position}]"
                if not is_index(joint_index, nodes):
                    issues.append(
                        make_issue(
                            "error",
                            "skin_joint_reference_invalid",
                            "Skin joint reference is outside the nodes array.",
                            joint_location,
                            joint=joint_index,
                        )
                    )
                    continue
                joint_node = nodes[joint_index]
                name = joint_node.get("name") if isinstance(joint_node, dict) else None
                if not isinstance(name, str) or not name:
                    issues.append(
                        make_issue(
                            "error",
                            "skin_joint_name_missing",
                            "Every skin joint node must have a non-empty name for BORG mapping.",
                            f"nodes[{joint_index}].name",
                        )
                    )
                    continue
                names.append(name)
            report["joint_names"] = names
            duplicate_names = sorted({name for name in names if names.count(name) > 1})
            if duplicate_names:
                issues.append(
                    make_issue(
                        "error",
                        "skin_joint_name_duplicate",
                        "Skin joint names must be unique for deterministic BORG mapping.",
                        f"{location}.joints",
                        names=duplicate_names,
                    )
                )

            inverse_bind_index = skin.get("inverseBindMatrices")
            if inverse_bind_index is None:
                issues.append(
                    make_issue(
                        "warning",
                        "inverse_bind_matrices_missing",
                        "Skin has no inverseBindMatrices accessor.",
                        f"{location}.inverseBindMatrices",
                    )
                )
            else:
                inverse_bind = get_accessor(
                    inverse_bind_index,
                    accessors,
                    issues,
                    f"{location}.inverseBindMatrices",
                )
                if inverse_bind is not None:
                    validate_accessor_shape(
                        inverse_bind,
                        inverse_bind_index,
                        FLOAT,
                        "MAT4",
                        issues,
                        "inverseBindMatrices",
                    )
                    if inverse_bind.get("count") != len(joints):
                        issues.append(
                            make_issue(
                                "error",
                                "inverse_bind_count_mismatch",
                                "inverseBindMatrices count must match skin joint count.",
                                f"accessors[{inverse_bind_index}].count",
                                actual=inverse_bind.get("count"),
                                expected=len(joints),
                            )
                        )

    carrier: dict[str, Any] | None = None
    if carrier_path is not None:
        carrier, carrier_issues = carrier_profile(carrier_path)
        for carrier_issue in carrier_issues:
            issues.append(
                make_issue(
                    "error",
                    "carrier_invalid",
                    f"Carrier GLB is invalid: {carrier_issue['message']}",
                    carrier_issue.get("location", str(carrier_path)),
                    carrier_code=carrier_issue["code"],
                )
            )
        if carrier is not None:
            if sorted(suffixes) != carrier["mesh_suffixes"]:
                issues.append(
                    make_issue(
                        "error",
                        "carrier_mesh_slots_mismatch",
                        "Production mesh suffixes do not match the carrier mesh slots.",
                        "meshes",
                        actual=sorted(suffixes),
                        expected=carrier["mesh_suffixes"],
                    )
                )

            target_joint_names = {
                name for report in skin_reports for name in report.get("joint_names", [])
            }
            carrier_joint_names = set(carrier["joint_names"])
            unknown_names = sorted(target_joint_names - carrier_joint_names)
            missing_names = sorted(carrier_joint_names - target_joint_names)
            if unknown_names:
                issues.append(
                    make_issue(
                        "error",
                        "joint_name_not_in_carrier",
                        "Production skin contains joint names absent from the carrier BORG table.",
                        "skins",
                        names=unknown_names,
                    )
                )
            if missing_names:
                severity = "error" if joint_policy == "exact" else "warning"
                issues.append(
                    make_issue(
                        severity,
                        "carrier_joint_names_missing",
                        "Production skin omits joint names present in the carrier.",
                        "skins",
                        names=missing_names,
                        policy=joint_policy,
                    )
                )

    errors = [issue for issue in issues if issue["severity"] == "error"]
    warnings = [issue for issue in issues if issue["severity"] == "warning"]

    return {
        "schema_version": SCHEMA_VERSION,
        "tool": TOOL_NAME,
        "source": {
            "path": str(parsed.path),
            "size": parsed.file_size,
            "sha256": parsed.sha256,
        },
        "valid": not errors,
        "error_count": len(errors),
        "warning_count": len(warnings),
        "container": {
            "header_version": parsed.header_version,
            "declared_length": parsed.declared_length,
            "json_chunk_count": parsed.json_chunk_count,
            "bin_chunk_count": parsed.bin_chunk_count,
            "asset_version": (
                document.get("asset", {}).get("version")
                if isinstance(document, dict) and isinstance(document.get("asset"), dict)
                else None
            ),
        },
        "meta": {
            "required": require_meta,
            "path": str(meta_path.resolve()),
            "found": meta_found,
            "template_found": template_meta_found,
            "resource_path": str(resource_meta_path.resolve()),
            "resource_found": resource_meta_found,
        },
        "summary": {
            "mesh_count": len(mesh_reports),
            "mesh_suffixes": sorted(suffixes),
            "total_vertices": total_vertices,
            "used_skin_count": len(skin_reports),
            "joint_counts": [report["joint_count"] for report in skin_reports],
            "animation_count": animation_count,
            "morph_primitive_count": morph_primitive_count,
        },
        "meshes": mesh_reports,
        "skins": skin_reports,
        "carrier": carrier,
        "errors": errors,
        "warnings": warnings,
    }


def human_summary(report: dict[str, Any]) -> str:
    status = "PASS" if report["valid"] else "FAIL"
    source = report["source"]
    container = report["container"]
    summary = report["summary"]
    meta = report["meta"]

    if not meta["required"]:
        meta_status = "found (not required)" if meta["found"] else "not required"
    else:
        meta_status = "found" if meta["found"] else "missing"

    lines = [
        f"{status}: {source['path']}",
        (
            "  GLB: container={} asset={} size={} sha256={}".format(
                container["header_version"],
                container["asset_version"],
                source["size"],
                source["sha256"] or "unavailable",
            )
        ),
        (
            "  Meshes: count={} suffixes={} total_vertices={}".format(
                summary["mesh_count"],
                summary["mesh_suffixes"],
                summary["total_vertices"],
            )
        ),
        (
            "  Skins: used={} joint_counts={} animations={} morph_primitives={}".format(
                summary["used_skin_count"],
                summary["joint_counts"],
                summary["animation_count"],
                summary["morph_primitive_count"],
            )
        ),
        (
            "  Meta: {} (template={}, resource={})".format(
                meta_status,
                meta["path"],
                meta["resource_path"],
            )
        ),
    ]
    if report.get("carrier") is not None:
        lines.append(f"  Carrier: {report['carrier']['path']}")
    lines.append(
        f"  Result: {report['error_count']} error(s), {report['warning_count']} warning(s)"
    )
    for issue in report["errors"] + report["warnings"]:
        location = f" [{issue['location']}]" if "location" in issue else ""
        lines.append(
            f"  {issue['severity'].upper()} {issue['code']}{location}: {issue['message']}"
        )
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate a weighted HITMAN PRIM GLB before RPKG Tool rebuild."
    )
    parser.add_argument("glb", type=Path, help="Production 16HEX.PRIM.glb file")
    parser.add_argument(
        "--carrier",
        type=Path,
        help="Optional original RPKG-exported carrier GLB for slot and joint-name checks",
    )
    parser.add_argument(
        "--joint-policy",
        choices=("subset", "exact"),
        default="subset",
        help="Carrier joint comparison policy (default: subset)",
    )
    parser.add_argument(
        "--skip-meta",
        action="store_true",
        help="Do not require sibling metas/16HEX.PRIM.glb.meta",
    )
    parser.add_argument(
        "--json-out",
        metavar="PATH",
        help="Write the JSON report to PATH, or '-' for stdout",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable summary",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = validate_glb(
            args.glb,
            require_meta=not args.skip_meta,
            carrier_path=args.carrier,
            joint_policy=args.joint_policy,
        )
    except Exception as exc:  # Defensive boundary for CI callers.
        print(f"{TOOL_NAME}: internal error: {exc}", file=sys.stderr)
        return 2

    json_text = json.dumps(report, indent=2, ensure_ascii=True) + "\n"
    if args.json_out == "-":
        sys.stdout.write(json_text)
        if not args.quiet:
            print(human_summary(report), file=sys.stderr)
    else:
        if args.json_out:
            try:
                Path(args.json_out).write_text(json_text, encoding="utf-8")
            except OSError as exc:
                print(f"{TOOL_NAME}: could not write JSON report: {exc}", file=sys.stderr)
                return 2
        if not args.quiet:
            print(human_summary(report))

    return 0 if report["valid"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
