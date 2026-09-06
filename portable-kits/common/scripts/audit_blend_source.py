#!/usr/bin/env python3
"""Read-only structural audit for the .blend currently opened by Blender."""

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import bpy
from mathutils import Vector


EPSILON = 1.0e-8
WEIGHT_SUM_TOLERANCE = 1.0e-4


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="Destination JSON path")
    return parser.parse_args(argv)


def sha256_file(path):
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest().upper()


def rounded(value, digits=8):
    return round(float(value), digits)


def vector_values(value):
    return [rounded(component) for component in value]


def matrix_values(value):
    return [[rounded(component) for component in row] for row in value]


def optional_name(value):
    return value.name if value is not None else None


def image_path_record(image):
    raw_path = image.filepath or ""
    try:
        resolved_path = bpy.path.abspath(raw_path, library=image.library) if raw_path else ""
    except Exception:
        resolved_path = ""
    packed_file = getattr(image, "packed_file", None)
    packed_files = getattr(image, "packed_files", None)
    packed_tile_count = len(packed_files) if packed_files is not None else (1 if packed_file else 0)
    packed_bytes = 0
    if packed_files is not None:
        for packed in packed_files:
            packed_bytes += int(getattr(packed, "size", 0) or 0)
    elif packed_file is not None:
        packed_bytes = int(getattr(packed_file, "size", 0) or 0)

    return {
        "name": image.name,
        "source": image.source,
        "size": [int(image.size[0]), int(image.size[1])],
        "file_format": image.file_format,
        "alpha_mode": image.alpha_mode,
        "colorspace": image.colorspace_settings.name,
        "filepath_raw": raw_path,
        "filepath_resolved": os.path.normpath(resolved_path) if resolved_path else "",
        "external_exists": bool(resolved_path and os.path.isfile(resolved_path)),
        "packed": bool(packed_tile_count),
        "packed_tile_count": packed_tile_count,
        "packed_bytes": packed_bytes,
        "library": optional_name(image.library),
    }


def modifier_record(modifier):
    record = {
        "name": modifier.name,
        "type": modifier.type,
        "show_viewport": bool(modifier.show_viewport),
        "show_render": bool(modifier.show_render),
    }
    for attr in ("object", "vertex_group", "use_deform_preserve_volume"):
        if not hasattr(modifier, attr):
            continue
        value = getattr(modifier, attr)
        record[attr] = optional_name(value) if attr == "object" else value
    return record


def uv_layer_record(layer):
    coordinates = layer.data
    if coordinates:
        min_u = min(item.uv.x for item in coordinates)
        min_v = min(item.uv.y for item in coordinates)
        max_u = max(item.uv.x for item in coordinates)
        max_v = max(item.uv.y for item in coordinates)
        bounds = [rounded(min_u), rounded(min_v), rounded(max_u), rounded(max_v)]
    else:
        bounds = None
    return {
        "name": layer.name,
        "active": bool(layer.active),
        "active_render": bool(layer.active_render),
        "active_clone": bool(layer.active_clone),
        "loop_count": len(coordinates),
        "bounds": bounds,
    }


def armature_targets_for_mesh(obj):
    targets = []
    for modifier in obj.modifiers:
        if modifier.type == "ARMATURE" and modifier.object is not None:
            targets.append(modifier.object)
    if obj.parent is not None and obj.parent.type == "ARMATURE":
        targets.append(obj.parent)
    unique = {}
    for target in targets:
        unique[target.name_full] = target
    return [unique[name] for name in sorted(unique)]


def mesh_record(obj):
    mesh = obj.data
    mesh.calc_loop_triangles()
    targets = armature_targets_for_mesh(obj)
    target_bones = {
        bone.name for armature in targets for bone in armature.data.bones
    }
    deform_bones = {
        bone.name
        for armature in targets
        for bone in armature.data.bones
        if bone.use_deform
    }
    group_names = {group.index: group.name for group in obj.vertex_groups}

    unweighted_any = 0
    unweighted_target_bones = 0
    over_four_target_bones = 0
    max_any_influences = 0
    max_target_bone_influences = 0
    max_deform_bone_influences = 0
    weight_sum_max_error = 0.0
    weight_sum_over_tolerance = 0
    positive_non_bone_group_names = set()
    positive_bone_group_names = set()

    for vertex in mesh.vertices:
        positive = [entry for entry in vertex.groups if entry.weight > EPSILON]
        any_count = len(positive)
        target = [entry for entry in positive if group_names.get(entry.group) in target_bones]
        deform = [entry for entry in positive if group_names.get(entry.group) in deform_bones]
        target_count = len(target)
        deform_count = len(deform)
        max_any_influences = max(max_any_influences, any_count)
        max_target_bone_influences = max(max_target_bone_influences, target_count)
        max_deform_bone_influences = max(max_deform_bone_influences, deform_count)
        if any_count == 0:
            unweighted_any += 1
        if targets and target_count == 0:
            unweighted_target_bones += 1
        if target_count > 4:
            over_four_target_bones += 1
        if target_count:
            error = abs(sum(entry.weight for entry in target) - 1.0)
            weight_sum_max_error = max(weight_sum_max_error, error)
            if error > WEIGHT_SUM_TOLERANCE:
                weight_sum_over_tolerance += 1
        for entry in positive:
            group_name = group_names.get(entry.group, "<missing-group-index>")
            if group_name in target_bones:
                positive_bone_group_names.add(group_name)
            else:
                positive_non_bone_group_names.add(group_name)

    shape_key_blocks = []
    if mesh.shape_keys is not None:
        shape_key_blocks = [block.name for block in mesh.shape_keys.key_blocks]

    world_corners = [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
    world_bounds = {
        "min": vector_values([min(point[i] for point in world_corners) for i in range(3)]),
        "max": vector_values([max(point[i] for point in world_corners) for i in range(3)]),
    }

    return {
        "name": obj.name,
        "data": mesh.name,
        "parent": optional_name(obj.parent),
        "matrix_world": matrix_values(obj.matrix_world),
        "dimensions": vector_values(obj.dimensions),
        "world_bounds": world_bounds,
        "vertices": len(mesh.vertices),
        "edges": len(mesh.edges),
        "polygons": len(mesh.polygons),
        "triangles": len(mesh.loop_triangles),
        "loops": len(mesh.loops),
        "material_slots": [optional_name(material) for material in mesh.materials],
        "uv_layers": [uv_layer_record(layer) for layer in mesh.uv_layers],
        "shape_key_block_count": len(shape_key_blocks),
        "shape_key_blocks": shape_key_blocks,
        "modifiers": [modifier_record(modifier) for modifier in obj.modifiers],
        "vertex_group_count": len(obj.vertex_groups),
        "armature_targets": [target.name for target in targets],
        "target_bone_count": len(target_bones),
        "deform_bone_count": len(deform_bones),
        "unweighted_vertices_any_positive_group": unweighted_any,
        "unweighted_vertices_target_bones": unweighted_target_bones if targets else None,
        "vertices_over_four_target_bone_influences": over_four_target_bones,
        "maximum_any_positive_group_influences": max_any_influences,
        "maximum_target_bone_influences": max_target_bone_influences,
        "maximum_deform_bone_influences": max_deform_bone_influences,
        "target_weight_sum_max_error": rounded(weight_sum_max_error, 10),
        "target_weight_sum_vertices_over_1e_4": weight_sum_over_tolerance,
        "positive_bone_group_count": len(positive_bone_group_names),
        "positive_non_bone_group_names": sorted(positive_non_bone_group_names),
    }


def armature_record(obj, attached_meshes):
    bones = obj.data.bones
    return {
        "name": obj.name,
        "data": obj.data.name,
        "parent": optional_name(obj.parent),
        "matrix_world": matrix_values(obj.matrix_world),
        "bone_count": len(bones),
        "deform_bone_count": sum(1 for bone in bones if bone.use_deform),
        "root_bones": sorted(bone.name for bone in bones if bone.parent is None),
        "attached_meshes": sorted(attached_meshes.get(obj.name, [])),
        "object_constraints": [constraint.type for constraint in obj.constraints],
        "pose_bone_constraint_count": sum(
            len(pose_bone.constraints) for pose_bone in obj.pose.bones
        ),
        "bones": [
            {
                "name": bone.name,
                "parent": optional_name(bone.parent),
                "use_deform": bool(bone.use_deform),
                "head_local": vector_values(bone.head_local),
                "tail_local": vector_values(bone.tail_local),
            }
            for bone in bones
        ],
    }


def material_record(material):
    image_nodes = []
    if material.use_nodes and material.node_tree is not None:
        for node in material.node_tree.nodes:
            if node.type == "TEX_IMAGE":
                image_nodes.append(
                    {
                        "node": node.name,
                        "image": optional_name(node.image),
                        "interpolation": node.interpolation,
                        "extension": node.extension,
                        "projection": node.projection,
                    }
                )
    return {
        "name": material.name,
        "use_nodes": bool(material.use_nodes),
        "node_count": len(material.node_tree.nodes) if material.node_tree else 0,
        "image_nodes": image_nodes,
        "library": optional_name(material.library),
    }


def main():
    args = parse_args()
    source_path = os.path.abspath(bpy.data.filepath)
    if not source_path or not os.path.isfile(source_path):
        raise RuntimeError("Blender must open a saved .blend before running this audit")

    source_stat = os.stat(source_path)
    source_sha256 = sha256_file(source_path)
    meshes = [mesh_record(obj) for obj in sorted(bpy.data.objects, key=lambda item: item.name) if obj.type == "MESH"]

    attached_meshes = {}
    for mesh in meshes:
        for armature_name in mesh["armature_targets"]:
            attached_meshes.setdefault(armature_name, []).append(mesh["name"])
    armatures = [
        armature_record(obj, attached_meshes)
        for obj in sorted(bpy.data.objects, key=lambda item: item.name)
        if obj.type == "ARMATURE"
    ]

    all_world_mins = [mesh["world_bounds"]["min"] for mesh in meshes]
    all_world_maxs = [mesh["world_bounds"]["max"] for mesh in meshes]
    if meshes:
        scene_min = [min(value[axis] for value in all_world_mins) for axis in range(3)]
        scene_max = [max(value[axis] for value in all_world_maxs) for axis in range(3)]
        scene_dimensions = [scene_max[i] - scene_min[i] for i in range(3)]
    else:
        scene_min = scene_max = scene_dimensions = [0.0, 0.0, 0.0]

    images = [image_path_record(image) for image in sorted(bpy.data.images, key=lambda item: item.name)]
    object_type_counts = Counter(obj.type for obj in bpy.data.objects)
    file_version = getattr(bpy.data, "version", None)
    file_version_string = ".".join(str(part) for part in file_version) if file_version else None

    report = {
        "schema": "l4d2-source-audit/v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "method": "Blender background read-only audit; no save operator invoked",
        "source": {
            "path": source_path,
            "size_bytes": source_stat.st_size,
            "mtime_utc": datetime.fromtimestamp(source_stat.st_mtime, timezone.utc).isoformat(),
            "sha256": source_sha256,
        },
        "blender": {
            "runtime_version": bpy.app.version_string,
            "runtime_version_tuple": list(bpy.app.version),
            "build_hash": bpy.app.build_hash.decode("ascii", "replace") if isinstance(bpy.app.build_hash, bytes) else str(bpy.app.build_hash),
            "loaded_file_version": file_version_string,
        },
        "scene": {
            "name": bpy.context.scene.name,
            "unit_system": bpy.context.scene.unit_settings.system,
            "unit_scale_length": bpy.context.scene.unit_settings.scale_length,
            "length_unit": bpy.context.scene.unit_settings.length_unit,
            "fps": bpy.context.scene.render.fps,
            "frame_start": bpy.context.scene.frame_start,
            "frame_end": bpy.context.scene.frame_end,
            "world_mesh_bounds": {
                "min": [rounded(value) for value in scene_min],
                "max": [rounded(value) for value in scene_max],
                "dimensions": [rounded(value) for value in scene_dimensions],
            },
        },
        "totals": {
            "objects": len(bpy.data.objects),
            "object_type_counts": dict(sorted(object_type_counts.items())),
            "meshes": len(meshes),
            "armatures": len(armatures),
            "bones": sum(item["bone_count"] for item in armatures),
            "deform_bones": sum(item["deform_bone_count"] for item in armatures),
            "vertices": sum(item["vertices"] for item in meshes),
            "polygons": sum(item["polygons"] for item in meshes),
            "triangles": sum(item["triangles"] for item in meshes),
            "material_datablocks": len(bpy.data.materials),
            "material_slots": sum(len(item["material_slots"]) for item in meshes),
            "unique_slotted_materials": len({name for item in meshes for name in item["material_slots"] if name}),
            "uv_layers": sum(len(item["uv_layers"]) for item in meshes),
            "shape_key_blocks": sum(item["shape_key_block_count"] for item in meshes),
            "unweighted_vertices_any_positive_group": sum(item["unweighted_vertices_any_positive_group"] for item in meshes),
            "unweighted_vertices_target_bones": sum((item["unweighted_vertices_target_bones"] or 0) for item in meshes),
            "vertices_over_four_target_bone_influences": sum(item["vertices_over_four_target_bone_influences"] for item in meshes),
            "maximum_any_positive_group_influences": max((item["maximum_any_positive_group_influences"] for item in meshes), default=0),
            "maximum_target_bone_influences": max((item["maximum_target_bone_influences"] for item in meshes), default=0),
            "maximum_deform_bone_influences": max((item["maximum_deform_bone_influences"] for item in meshes), default=0),
            "target_weight_sum_max_error": max((item["target_weight_sum_max_error"] for item in meshes), default=0.0),
            "target_weight_sum_vertices_over_1e_4": sum(item["target_weight_sum_vertices_over_1e_4"] for item in meshes),
            "images": len(images),
            "packed_images": sum(1 for image in images if image["packed"]),
            "missing_external_images": sum(1 for image in images if image["filepath_raw"] and not image["external_exists"]),
            "libraries": len(bpy.data.libraries),
        },
        "meshes": meshes,
        "armatures": armatures,
        "materials": [material_record(material) for material in sorted(bpy.data.materials, key=lambda item: item.name)],
        "images": images,
        "libraries": [
            {
                "name": library.name,
                "filepath_raw": library.filepath,
                "filepath_resolved": bpy.path.abspath(library.filepath),
                "external_exists": os.path.isfile(bpy.path.abspath(library.filepath)),
            }
            for library in sorted(bpy.data.libraries, key=lambda item: item.name)
        ],
    }

    output_path = Path(args.output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    source_sha256_after = sha256_file(source_path)
    if source_sha256_after != source_sha256:
        raise RuntimeError("Source hash changed during the read-only audit")
    print("AUDIT_JSON=" + str(output_path))
    print("SOURCE_SHA256=" + source_sha256)


if __name__ == "__main__":
    main()
