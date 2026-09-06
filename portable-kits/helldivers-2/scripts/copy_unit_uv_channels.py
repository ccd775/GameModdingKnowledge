#!/usr/bin/env python3
"""Copy one Unit UV component into other components for selected materials.

Run this through the Blender version supported by the selected HD2SDK. The
script pins the complete input triplet, edits only GPU vertex-component bytes,
and refuses material-shared vertices unless explicitly allowed.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import shutil
import sys
from pathlib import Path


UNIT_TYPE_ID = 0xE0A48D0BE9A7453F


def parse_uint64(value: str) -> int:
    parsed = int(value, 0)
    if not 0 <= parsed <= 0xFFFFFFFFFFFFFFFF:
        raise argparse.ArgumentTypeError(f"outside uint64 range: {value}")
    return parsed


def parse_sha256(value: str) -> str:
    normalized = value.lower()
    if len(normalized) != 64 or any(c not in "0123456789abcdef" for c in normalized):
        raise argparse.ArgumentTypeError(f"invalid SHA-256: {value}")
    return normalized


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else sys.argv[1:]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-patch", required=True, type=Path)
    parser.add_argument("--output-patch", required=True, type=Path)
    parser.add_argument("--sdk-dir", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--material-id", required=True, action="append", type=parse_uint64)
    parser.add_argument("--source-uv", required=True, type=int)
    parser.add_argument("--target-uv", required=True, action="append", type=int)
    parser.add_argument("--expected-patch-sha256", required=True, type=parse_sha256)
    parser.add_argument("--expected-gpu-sha256", required=True, type=parse_sha256)
    parser.add_argument("--expected-stream-sha256", required=True, type=parse_sha256)
    parser.add_argument("--expected-output-gpu-sha256", type=parse_sha256)
    parser.add_argument("--expected-unit-count", type=int)
    parser.add_argument("--expected-mesh-count", type=int)
    parser.add_argument("--expected-vertex-count", type=int)
    parser.add_argument(
        "--require-zero-targets",
        action="store_true",
        help="Refuse any selected vertex whose target component is not all-zero.",
    )
    parser.add_argument(
        "--allow-shared-vertices",
        action="store_true",
        help="Allow vertices referenced by both selected and unselected materials.",
    )
    return parser.parse_args(argv)


def companion(path: Path, suffix: str) -> Path:
    return Path(f"{path}{suffix}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def load_sdk(directory: Path):
    init = directory / "__init__.py"
    if not init.is_file():
        raise FileNotFoundError(f"HD2SDK __init__.py not found: {init}")
    token = hashlib.sha1(str(directory).encode("utf-8")).hexdigest()[:12]
    module_name = f"hd2sdk_unit_uv_copy_{token}"
    spec = importlib.util.spec_from_file_location(
        module_name,
        init,
        submodule_search_locations=[str(directory)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"could not create module spec for {init}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def component_offsets(stream_info) -> tuple[dict[int, tuple[object, int]], int]:
    offset = 0
    uv_components: dict[int, tuple[object, int]] = {}
    for component in stream_info.Components:
        size = int(component.GetSize())
        if component.TypeName() == "uv":
            index = int(component.Index)
            if index in uv_components:
                raise RuntimeError(f"duplicate UV component index {index}")
            uv_components[index] = (component, offset)
        offset += size
    stride = int(stream_info.VertexStride)
    if offset > stride:
        raise RuntimeError(f"component bytes {offset} exceed vertex stride {stride}")
    return uv_components, stride


def material_vertex_sets(raw_mesh, selected_ids: set[int]) -> tuple[set[int], set[int]]:
    flat_indices = [int(index) for triangle in raw_mesh.Indices for index in triangle]
    selected: set[int] = set()
    other: set[int] = set()
    for material in raw_mesh.Materials:
        start = int(material.StartIndex)
        end = start + int(material.NumIndices)
        if start < 0 or end > len(flat_indices):
            raise RuntimeError(
                f"material index range [{start}, {end}) exceeds {len(flat_indices)}"
            )
        try:
            material_id = int(material.MatID)
        except (TypeError, ValueError):
            material_id = None
        destination = selected if material_id in selected_ids else other
        destination.update(flat_indices[start:end])
    return selected, other


def require_expected(label: str, actual: int, expected: int | None) -> None:
    if expected is not None and actual != expected:
        raise RuntimeError(f"{label}: expected {expected}, found {actual}")


def main() -> None:
    args = parse_args()
    source = args.source_patch.resolve()
    output = args.output_patch.resolve()
    report_path = args.report.resolve()
    source_gpu_path = companion(source, ".gpu_resources")
    source_stream_path = companion(source, ".stream")
    output_gpu_path = companion(output, ".gpu_resources")
    output_stream_path = companion(output, ".stream")

    source_paths = {source, source_gpu_path, source_stream_path}
    output_paths = {output, output_gpu_path, output_stream_path, report_path}
    if source_paths & output_paths:
        raise RuntimeError("source and output/report paths must be distinct")
    existing = sorted(str(path) for path in output_paths if path.exists())
    if existing:
        raise FileExistsError("refusing to overwrite: " + ", ".join(existing))
    for required in source_paths:
        if not required.is_file():
            raise FileNotFoundError(required)

    selected_materials = set(args.material_id)
    target_uvs = sorted(set(args.target_uv))
    if args.source_uv < 0 or any(index < 0 for index in target_uvs):
        raise RuntimeError("UV indices must be non-negative")
    if args.source_uv in target_uvs:
        raise RuntimeError("source UV cannot also be a target UV")

    expected_source_hashes = {
        "patch": args.expected_patch_sha256,
        "gpu_resources": args.expected_gpu_sha256,
        "stream": args.expected_stream_sha256,
    }
    source_hashes = {
        "patch": sha256_file(source),
        "gpu_resources": sha256_file(source_gpu_path),
        "stream": sha256_file(source_stream_path),
    }
    if source_hashes != expected_source_hashes:
        raise RuntimeError(
            "source triplet does not match pinned hashes: "
            + json.dumps(source_hashes, sort_keys=True)
        )

    sdk = load_sdk(args.sdk_dir.resolve())
    toc = sdk.StreamToc()
    if not toc.FromFile(str(source)):
        raise RuntimeError(f"could not parse patch: {source}")

    manager = sdk.Global_TocManager
    old_patch = manager.ActivePatch
    old_patches = list(manager.Patches)
    manager.ActivePatch = toc
    manager.Patches = [toc]

    source_gpu = source_gpu_path.read_bytes()
    writes: dict[int, bytes] = {}
    units_report: list[dict[str, object]] = []
    unit_ids: set[int] = set()
    total_meshes = 0
    total_vertices = 0
    total_shared = 0
    all_targets_zero = True
    try:
        for file_id, entry in sorted(toc.TocDict.get(UNIT_TYPE_ID, {}).items()):
            entry.Load(False, False)
            unit = entry.LoadedData
            meshes_report: list[dict[str, object]] = []
            for raw_mesh in unit.RawMeshes:
                selected_vertices, other_vertices = material_vertex_sets(
                    raw_mesh, selected_materials
                )
                if not selected_vertices:
                    continue

                shared = selected_vertices & other_vertices
                if shared and not args.allow_shared_vertices:
                    raise RuntimeError(
                        f"Unit 0x{int(file_id):016x} mesh {raw_mesh.MeshInfoIndex} "
                        f"has {len(shared)} vertices shared with unselected materials"
                    )

                mesh_info = unit.MeshInfoArray[
                    unit.DEV_MeshInfoMap[raw_mesh.MeshInfoIndex]
                ]
                if not mesh_info.Sections:
                    raise RuntimeError("mesh has no sections")
                stream_info = unit.StreamInfoArray[mesh_info.StreamIndex]
                uv_components, stride = component_offsets(stream_info)
                required_uvs = {args.source_uv, *target_uvs}
                missing = required_uvs - set(uv_components)
                if missing:
                    raise RuntimeError(
                        f"Unit 0x{int(file_id):016x} mesh {raw_mesh.MeshInfoIndex} "
                        f"is missing UV components {sorted(missing)}; "
                        f"found {sorted(uv_components)}"
                    )

                source_component, source_offset = uv_components[args.source_uv]
                component_size = int(source_component.GetSize())
                for target_uv in target_uvs:
                    target_component, _ = uv_components[target_uv]
                    if (
                        int(target_component.Format) != int(source_component.Format)
                        or int(target_component.GetSize()) != component_size
                    ):
                        raise RuntimeError(
                            f"Unit 0x{int(file_id):016x} mesh {raw_mesh.MeshInfoIndex} "
                            f"UV{target_uv} is incompatible with UV{args.source_uv}"
                        )

                vertex_offset = int(mesh_info.Sections[0].VertexOffset)
                vertex_buffer_offset = int(stream_info.VertexBufferOffset)
                unit_gpu_start = int(entry.GpuResourceOffset)
                unit_gpu_end = unit_gpu_start + int(entry.GpuResourceSize)
                before_zero_counts = {f"uv{index}": 0 for index in target_uvs}
                mesh_vertex_starts: list[int] = []

                for vertex_index in sorted(selected_vertices):
                    if vertex_index < 0 or vertex_index >= len(raw_mesh.VertexPositions):
                        raise RuntimeError(
                            f"vertex {vertex_index} is outside mesh vertex count "
                            f"{len(raw_mesh.VertexPositions)}"
                        )
                    vertex_start = (
                        unit_gpu_start
                        + vertex_buffer_offset
                        + (vertex_offset + vertex_index) * stride
                    )
                    mesh_vertex_starts.append(vertex_start)
                    source_start = vertex_start + source_offset
                    source_end = source_start + component_size
                    if source_start < unit_gpu_start or source_end > unit_gpu_end:
                        raise RuntimeError("source UV range exceeds Unit GPU payload")
                    source_bytes = source_gpu[source_start:source_end]
                    if len(source_bytes) != component_size:
                        raise RuntimeError("source UV range exceeds GPU sidecar")

                    for target_uv in target_uvs:
                        _, target_offset = uv_components[target_uv]
                        target_start = vertex_start + target_offset
                        target_end = target_start + component_size
                        if target_start < unit_gpu_start or target_end > unit_gpu_end:
                            raise RuntimeError("target UV range exceeds Unit GPU payload")
                        before = source_gpu[target_start:target_end]
                        if len(before) != component_size:
                            raise RuntimeError("target UV range exceeds GPU sidecar")
                        if not any(before):
                            before_zero_counts[f"uv{target_uv}"] += 1
                        else:
                            all_targets_zero = False
                            if args.require_zero_targets:
                                raise RuntimeError(
                                    f"Unit 0x{int(file_id):016x} mesh "
                                    f"{raw_mesh.MeshInfoIndex} vertex {vertex_index} "
                                    f"UV{target_uv} is not zero"
                                )
                        previous = writes.get(target_start)
                        if previous is not None and previous != source_bytes:
                            raise RuntimeError(
                                f"conflicting writes at GPU offset {target_start}"
                            )
                        writes[target_start] = source_bytes

                total_meshes += 1
                total_vertices += len(selected_vertices)
                total_shared += len(shared)
                unit_ids.add(int(file_id))
                meshes_report.append(
                    {
                        "mesh_info_index": int(raw_mesh.MeshInfoIndex),
                        "lod_index": int(raw_mesh.LodIndex),
                        "vertex_count": len(raw_mesh.VertexPositions),
                        "selected_referenced_vertices": len(selected_vertices),
                        "shared_with_unselected_material_vertices": len(shared),
                        "vertex_stride": stride,
                        "uv_component_format": int(source_component.Format),
                        "uv_component_size": component_size,
                        "uv_component_offsets": {
                            f"uv{index}": uv_components[index][1]
                            for index in sorted(required_uvs)
                        },
                        "selected_vertex_gpu_span": [
                            min(mesh_vertex_starts),
                            max(mesh_vertex_starts) + stride,
                        ],
                        "before_zero_counts": before_zero_counts,
                    }
                )
            if meshes_report:
                units_report.append(
                    {
                        "unit_id": f"0x{int(file_id):016x}",
                        "gpu_range": [
                            int(entry.GpuResourceOffset),
                            int(entry.GpuResourceOffset + entry.GpuResourceSize),
                        ],
                        "meshes": meshes_report,
                    }
                )
    finally:
        manager.ActivePatch = old_patch
        manager.Patches = old_patches

    if not writes or not unit_ids:
        raise RuntimeError("no selected-material UV components were found")
    require_expected("target Unit count", len(unit_ids), args.expected_unit_count)
    require_expected("target mesh count", total_meshes, args.expected_mesh_count)
    require_expected("target referenced vertex count", total_vertices, args.expected_vertex_count)

    candidate_gpu = bytearray(source_gpu)
    changed_bytes = 0
    changed_min: int | None = None
    changed_max: int | None = None
    for start, data in sorted(writes.items()):
        before = source_gpu[start : start + len(data)]
        for relative, (left, right) in enumerate(zip(before, data)):
            if left != right:
                absolute = start + relative
                changed_bytes += 1
                changed_min = absolute if changed_min is None else min(changed_min, absolute)
                changed_max = absolute + 1 if changed_max is None else max(changed_max, absolute + 1)
        candidate_gpu[start : start + len(data)] = data
    if changed_bytes == 0:
        raise RuntimeError("requested transform is a no-op")

    candidate_gpu_hash = hashlib.sha256(candidate_gpu).hexdigest()
    if (
        args.expected_output_gpu_sha256 is not None
        and candidate_gpu_hash != args.expected_output_gpu_sha256
    ):
        raise RuntimeError(
            f"output GPU hash mismatch: expected {args.expected_output_gpu_sha256}, "
            f"constructed {candidate_gpu_hash}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, output)
    output_gpu_path.write_bytes(candidate_gpu)
    shutil.copyfile(source_stream_path, output_stream_path)

    output_hashes = {
        "patch": sha256_file(output),
        "gpu_resources": sha256_file(output_gpu_path),
        "stream": sha256_file(output_stream_path),
    }
    checks = {
        "source_triplet_pinned": source_hashes == expected_source_hashes,
        "target_material_found": bool(unit_ids),
        "shared_vertices_zero_or_explicitly_allowed": total_shared == 0
        or args.allow_shared_vertices,
        "targets_all_zero_when_required": not args.require_zero_targets
        or all_targets_zero,
        "patch_byte_identical": output_hashes["patch"] == source_hashes["patch"],
        "stream_byte_identical": output_hashes["stream"] == source_hashes["stream"],
        "gpu_size_unchanged": output_gpu_path.stat().st_size == len(source_gpu),
        "gpu_matches_constructed_candidate": output_gpu_path.read_bytes()
        == bytes(candidate_gpu),
        "written_components_match_source": all(
            candidate_gpu[start : start + len(data)] == data
            for start, data in writes.items()
        ),
        "gpu_bytes_changed": changed_bytes > 0,
    }
    report = {
        "schema": "hd2-unit-uv-channel-copy-v1",
        "passed": all(checks.values()),
        "source": str(source),
        "output": str(output),
        "sdk_dir": str(args.sdk_dir.resolve()),
        "source_hashes": source_hashes,
        "output_hashes": output_hashes,
        "transform": {
            "material_ids": [f"0x{value:016x}" for value in sorted(selected_materials)],
            "source_uv": args.source_uv,
            "target_uvs": target_uvs,
            "scope": "vertices referenced by selected material IDs",
            "shared_vertex_policy": "allow" if args.allow_shared_vertices else "refuse",
            "require_zero_targets": args.require_zero_targets,
        },
        "counts": {
            "units": len(unit_ids),
            "meshes": total_meshes,
            "selected_referenced_vertices": total_vertices,
            "shared_with_unselected_material_vertices": total_shared,
            "unique_component_writes": len(writes),
            "component_bytes_written": sum(len(data) for data in writes.values()),
            "gpu_bytes_changed": changed_bytes,
            "changed_gpu_bounding_range": [changed_min, changed_max],
        },
        "checks": checks,
        "units": units_report,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        "UNIT_UV_CHANNEL_COPY_COMPLETE",
        json.dumps(
            {
                "passed": report["passed"],
                "counts": report["counts"],
                "output_hashes": output_hashes,
                "report": str(report_path),
            }
        ),
    )
    if not report["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
