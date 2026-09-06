#!/usr/bin/env python3
"""Compare a production PRIM GLB with the GLB extracted after an RPKG round-trip."""

from __future__ import annotations

import argparse
import json
import struct
from pathlib import Path
from typing import Any


JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
COMPONENT_FORMAT = {
    5120: "b",
    5121: "B",
    5122: "h",
    5123: "H",
    5125: "I",
    5126: "f",
}
TYPE_COMPONENTS = {
    "SCALAR": 1,
    "VEC2": 2,
    "VEC3": 3,
    "VEC4": 4,
    "MAT4": 16,
}
FLOAT_THRESHOLDS = {
    "POSITION": 5.0e-5,
    "NORMAL": 1.0e-2,
    "TEXCOORD_0": 5.0e-5,
    # PRIM stores the four influences as a jointly normalized byte tuple.
    "WEIGHTS_0": 3.0 / 255.0 + 1.0e-6,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("roundtrip", type=Path)
    parser.add_argument("--json-out", type=Path)
    return parser.parse_args()


def read_glb(path: Path) -> tuple[dict[str, Any], bytes]:
    data = path.read_bytes()
    if len(data) < 20 or data[:4] != b"glTF":
        raise ValueError(f"Not a GLB: {path}")
    version, declared_length = struct.unpack_from("<II", data, 4)
    if version != 2 or declared_length != len(data):
        raise ValueError(f"Invalid GLB header: {path}")

    document = None
    binary = None
    offset = 12
    while offset < len(data):
        chunk_length, chunk_type = struct.unpack_from("<II", data, offset)
        offset += 8
        payload = data[offset : offset + chunk_length]
        offset += chunk_length
        if chunk_type == JSON_CHUNK:
            document = json.loads(payload.rstrip(b"\x00 \t\r\n").decode("utf-8"))
        elif chunk_type == BIN_CHUNK:
            binary = payload
    if document is None or binary is None:
        raise ValueError(f"GLB must contain JSON and BIN chunks: {path}")
    return document, binary


def normalized_value(value: int, component_type: int) -> float:
    if component_type == 5120:
        return max(value / 127.0, -1.0)
    if component_type == 5121:
        return value / 255.0
    if component_type == 5122:
        return max(value / 32767.0, -1.0)
    if component_type == 5123:
        return value / 65535.0
    raise ValueError(f"Unsupported normalized component type: {component_type}")


def read_accessor(
    document: dict[str, Any], binary: bytes, accessor_index: int
) -> list[tuple[int | float, ...]]:
    accessor = document["accessors"][accessor_index]
    if "sparse" in accessor:
        raise ValueError("Sparse accessors are not supported")
    view = document["bufferViews"][accessor["bufferView"]]
    component_type = int(accessor["componentType"])
    component_format = COMPONENT_FORMAT[component_type]
    components = TYPE_COMPONENTS[accessor["type"]]
    element = struct.Struct("<" + component_format * components)
    stride = int(view.get("byteStride", element.size))
    offset = int(view.get("byteOffset", 0)) + int(accessor.get("byteOffset", 0))
    normalized = bool(accessor.get("normalized", False))

    values: list[tuple[int | float, ...]] = []
    for index in range(int(accessor["count"])):
        unpacked = element.unpack_from(binary, offset + index * stride)
        if normalized:
            values.append(tuple(normalized_value(value, component_type) for value in unpacked))
        else:
            values.append(tuple(unpacked))
    return values


def skin_joint_names(document: dict[str, Any]) -> list[str]:
    skins = document.get("skins", [])
    if len(skins) != 1:
        raise ValueError(f"Expected one skin, found {len(skins)}")
    nodes = document["nodes"]
    return [nodes[index]["name"] for index in skins[0]["joints"]]


def float_comparison(
    source: list[tuple[int | float, ...]],
    roundtrip: list[tuple[int | float, ...]],
    threshold: float,
) -> dict[str, Any]:
    if len(source) != len(roundtrip):
        return {
            "status": "fail",
            "source_count": len(source),
            "roundtrip_count": len(roundtrip),
            "reason": "count mismatch",
        }
    differences = [
        abs(float(left) - float(right))
        for source_value, roundtrip_value in zip(source, roundtrip)
        for left, right in zip(source_value, roundtrip_value)
    ]
    maximum = max(differences, default=0.0)
    mean = sum(differences) / len(differences) if differences else 0.0
    return {
        "status": "pass" if maximum <= threshold else "fail",
        "source_count": len(source),
        "roundtrip_count": len(roundtrip),
        "component_count": len(differences),
        "maximum_absolute_error": maximum,
        "mean_absolute_error": mean,
        "threshold": threshold,
    }


def exact_comparison(
    source: list[tuple[int | float, ...]],
    roundtrip: list[tuple[int | float, ...]],
) -> dict[str, Any]:
    mismatch_count = sum(left != right for left, right in zip(source, roundtrip))
    mismatch_count += abs(len(source) - len(roundtrip))
    return {
        "status": "pass" if mismatch_count == 0 else "fail",
        "source_count": len(source),
        "roundtrip_count": len(roundtrip),
        "mismatch_count": mismatch_count,
    }


def named_joint_comparison(
    source: list[tuple[int | float, ...]],
    roundtrip: list[tuple[int | float, ...]],
    source_names: list[str],
    roundtrip_names: list[str],
) -> dict[str, Any]:
    source_named = [tuple(source_names[int(value)] for value in values) for values in source]
    roundtrip_named = [tuple(roundtrip_names[int(value)] for value in values) for values in roundtrip]
    return exact_comparison(source_named, roundtrip_named)


def compare(source_path: Path, roundtrip_path: Path) -> dict[str, Any]:
    source_document, source_binary = read_glb(source_path)
    roundtrip_document, roundtrip_binary = read_glb(roundtrip_path)
    source_meshes = source_document.get("meshes", [])
    roundtrip_meshes = roundtrip_document.get("meshes", [])
    errors: list[str] = []
    mesh_reports = []

    if len(source_meshes) != len(roundtrip_meshes):
        errors.append("mesh count differs")
    source_joint_names = skin_joint_names(source_document)
    roundtrip_joint_names = skin_joint_names(roundtrip_document)
    if set(source_joint_names) != set(roundtrip_joint_names):
        errors.append("skin joint-name sets differ")

    for mesh_index, (source_mesh, roundtrip_mesh) in enumerate(
        zip(source_meshes, roundtrip_meshes)
    ):
        report: dict[str, Any] = {
            "mesh_index": mesh_index,
            "source_name": source_mesh.get("name"),
            "roundtrip_name": roundtrip_mesh.get("name"),
            "attributes": {},
        }
        mesh_reports.append(report)
        if source_mesh.get("name") != roundtrip_mesh.get("name"):
            errors.append(f"mesh {mesh_index} name differs")
        source_primitives = source_mesh.get("primitives", [])
        roundtrip_primitives = roundtrip_mesh.get("primitives", [])
        if len(source_primitives) != 1 or len(roundtrip_primitives) != 1:
            errors.append(f"mesh {mesh_index} does not have one primitive in both files")
            continue
        source_primitive = source_primitives[0]
        roundtrip_primitive = roundtrip_primitives[0]

        source_indices = read_accessor(
            source_document, source_binary, source_primitive["indices"]
        )
        roundtrip_indices = read_accessor(
            roundtrip_document, roundtrip_binary, roundtrip_primitive["indices"]
        )
        report["indices"] = exact_comparison(source_indices, roundtrip_indices)
        if report["indices"]["status"] != "pass":
            errors.append(f"mesh {mesh_index} triangle indices differ")

        for semantic in (
            "POSITION",
            "NORMAL",
            "TEXCOORD_0",
            "WEIGHTS_0",
            "JOINTS_0",
            "COLOR_0",
        ):
            source_accessor = source_primitive.get("attributes", {}).get(semantic)
            roundtrip_accessor = roundtrip_primitive.get("attributes", {}).get(semantic)
            if source_accessor is None or roundtrip_accessor is None:
                report["attributes"][semantic] = {"status": "fail", "reason": "missing"}
                errors.append(f"mesh {mesh_index} {semantic} is missing")
                continue
            source_values = read_accessor(source_document, source_binary, source_accessor)
            roundtrip_values = read_accessor(
                roundtrip_document, roundtrip_binary, roundtrip_accessor
            )
            if semantic in FLOAT_THRESHOLDS:
                result = float_comparison(
                    source_values, roundtrip_values, FLOAT_THRESHOLDS[semantic]
                )
            elif semantic == "JOINTS_0":
                result = named_joint_comparison(
                    source_values,
                    roundtrip_values,
                    source_joint_names,
                    roundtrip_joint_names,
                )
                result["raw_indices_exact"] = source_values == roundtrip_values
            else:
                result = exact_comparison(source_values, roundtrip_values)
            report["attributes"][semantic] = result
            if result["status"] != "pass":
                errors.append(f"mesh {mesh_index} {semantic} differs beyond policy")

    return {
        "schema_version": 1,
        "status": "pass" if not errors else "fail",
        "source": str(source_path.resolve()),
        "roundtrip": str(roundtrip_path.resolve()),
        "source_joint_count": len(source_joint_names),
        "roundtrip_joint_count": len(roundtrip_joint_names),
        "joint_order_exact": source_joint_names == roundtrip_joint_names,
        "thresholds": FLOAT_THRESHOLDS,
        "errors": errors,
        "meshes": mesh_reports,
    }


def main() -> int:
    args = parse_args()
    report = compare(args.source.resolve(), args.roundtrip.resolve())
    rendered = json.dumps(report, ensure_ascii=True, indent=2) + "\n"
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0 if report["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
