#!/usr/bin/env python3
"""Rescale Source VTA positions while preserving topology, normals, and flex frames."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path


TIME_RE = re.compile(r"^time\s+(\d+)(?:\s+#\s*(.*))?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--reference-smd", required=True, type=Path)
    parser.add_argument("--input-units-per-meter", required=True, type=float)
    parser.add_argument("--output-units-per-meter", required=True, type=float)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--expected-nodes", required=True, type=int)
    parser.add_argument("--expected-frames", required=True, type=int)
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest().upper()


def bounds(points: list[tuple[float, float, float]]) -> dict[str, list[float]]:
    if not points:
        raise ValueError("Cannot calculate empty coordinate bounds")
    return {
        "min": [min(point[axis] for point in points) for axis in range(3)],
        "max": [max(point[axis] for point in points) for axis in range(3)],
    }


def read_smd_triangle_bounds(path: Path) -> dict[str, list[float]]:
    section = None
    triangle_line = 0
    positions = []
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if line in {"nodes", "skeleton", "triangles", "end"}:
            section = None if line == "end" else line
            triangle_line = 0
            continue
        if section != "triangles" or not line:
            continue
        if triangle_line == 0:
            triangle_line = 1
            continue
        fields = line.split()
        if len(fields) < 10:
            raise ValueError(f"Malformed SMD vertex line: {line}")
        positions.append(tuple(float(fields[index]) for index in (1, 2, 3)))
        triangle_line = 0 if triangle_line == 3 else triangle_line + 1
    return bounds(positions)


def main() -> None:
    args = parse_args()
    source = args.input.resolve()
    output = args.output.resolve()
    reference_smd = args.reference_smd.resolve()
    report_path = args.report.resolve()
    if source == output:
        raise ValueError("Input and output VTA paths must differ")
    if output.exists() or report_path.exists() or output == report_path:
        raise ValueError("Use distinct, new output and report paths")
    if args.expected_nodes < 1 or args.expected_frames < 1:
        raise ValueError("Expected nodes and frames must be positive")
    for value, label in (
        (args.input_units_per_meter, "input units per meter"),
        (args.output_units_per_meter, "output units per meter"),
    ):
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError(f"Invalid {label}: {value}")
    ratio = args.output_units_per_meter / args.input_units_per_meter

    section = None
    node_count = 0
    skeleton_frames = []
    vertex_frames = []
    current_vertex_frame = None
    vertex_entries = 0
    base_positions = []
    output_lines = []
    for raw in source.read_text(encoding="ascii").splitlines():
        line = raw.strip()
        if line in {"nodes", "skeleton", "vertexanimation", "end"}:
            section = None if line == "end" else line
            current_vertex_frame = None if line == "end" else current_vertex_frame
            output_lines.append(line)
            continue
        match = TIME_RE.match(line)
        if match:
            frame = int(match.group(1))
            if section == "skeleton":
                skeleton_frames.append((frame, match.group(2)))
            elif section == "vertexanimation":
                vertex_frames.append(frame)
                current_vertex_frame = frame
            output_lines.append(line)
            continue
        if section == "nodes" and line:
            node_count += 1
            output_lines.append(line)
            continue
        if section == "vertexanimation" and line:
            fields = line.split()
            if len(fields) != 7:
                raise ValueError(f"Malformed VTA vertex line: {line}")
            vertex_index = int(fields[0])
            position = tuple(float(fields[index]) * ratio for index in (1, 2, 3))
            if current_vertex_frame == 0:
                base_positions.append(position)
            output_lines.append(
                f"{vertex_index} {position[0]:.6f} {position[1]:.6f} "
                f"{position[2]:.6f} {fields[4]} {fields[5]} {fields[6]}"
            )
            vertex_entries += 1
            continue
        output_lines.append(line)

    if node_count != args.expected_nodes:
        raise ValueError(f"Expected {args.expected_nodes} VTA nodes, found {node_count}")
    expected_frames = list(range(args.expected_frames))
    if [item[0] for item in skeleton_frames] != expected_frames:
        raise ValueError("Skeleton frames do not match the declared contract")
    if vertex_frames != expected_frames:
        raise ValueError("Vertex frames do not match the declared contract")
    shape_names = [item[1] for item in skeleton_frames[1:]]
    if any(not name for name in shape_names) or len(set(shape_names)) != args.expected_frames - 1:
        raise ValueError("Expected a unique name for each shape frame")

    vta_bounds = bounds(base_positions)
    smd_bounds = read_smd_triangle_bounds(reference_smd)
    maximum_bound_error = max(
        abs(vta_bounds[edge][axis] - smd_bounds[edge][axis])
        for edge in ("min", "max")
        for axis in range(3)
    )
    if maximum_bound_error > 2.0e-5:
        raise ValueError(
            "Rescaled VTA base bounds do not match the reference SMD: "
            f"{maximum_bound_error}"
        )

    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n".join(output_lines) + "\n", encoding="ascii", newline="\n")
    report = {
        "schema": "karin-l4d2-vta-rescale/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "input": {
            "path": str(source),
            "bytes": source.stat().st_size,
            "sha256": sha256_file(source),
            "units_per_meter": args.input_units_per_meter,
        },
        "output": {
            "path": str(output),
            "bytes": output.stat().st_size,
            "sha256": sha256_file(output),
            "units_per_meter": args.output_units_per_meter,
        },
        "reference_smd": {
            "path": str(reference_smd),
            "sha256": sha256_file(reference_smd),
        },
        "scale_ratio": ratio,
        "nodes": node_count,
        "frames": len(vertex_frames),
        "shape_frames": len(vertex_frames) - 1,
        "shape_names": shape_names,
        "vertex_entries": vertex_entries,
        "base_vertices": len(base_positions),
        "vta_base_bounds": vta_bounds,
        "smd_triangle_bounds": smd_bounds,
        "maximum_bound_error": maximum_bound_error,
    }
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"VTA_OUTPUT={output}")
    print(f"VTA_REPORT={report_path}")


if __name__ == "__main__":
    main()
