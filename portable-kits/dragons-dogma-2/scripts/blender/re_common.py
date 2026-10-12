"""Shared helpers for DD2 Karin Blender scripts (RE Mesh Editor 0.66 based).

RE Mesh Editor: either installed in Blender itself, or found through the DD2_BLENDER_ADDONS environment variable (the
folder that contains the re_mesh_editor add-on package; it is put on sys.path before enabling the add-on).
"""
import os
import sys
from pathlib import Path

import addon_utils
import bpy

ADDONS = os.environ.get("DD2_BLENDER_ADDONS") or None


def enable_re_mesh_editor():
    if ADDONS and ADDONS not in sys.path:
        sys.path.insert(0, ADDONS)
    mod = addon_utils.enable("re_mesh_editor", default_set=False, persistent=False)
    if mod is None:
        raise RuntimeError("could not enable re_mesh_editor (install RE Mesh Editor 0.66 in Blender, or set "
                           "DD2_BLENDER_ADDONS to the folder that contains it); DD2_BLENDER_ADDONS=" + str(ADDONS))
    return mod


def import_re_mesh(path, shadow=True):
    from re_mesh_editor.modules.mesh.blender_re_mesh import importREMeshFile
    before = set(bpy.data.collections.keys())
    options = {
        "clearScene": False, "createCollections": True, "loadMaterials": False, "loadMDFData": False,
        "loadShellFur": False, "loadUnusedTextures": False, "loadUnusedProps": False, "useBackfaceCulling": False,
        "reloadCachedTextures": False, "mdfPath": "", "importAllLODs": True, "importBlendShapes": False,
        "rotate90": True, "mergeArmature": "", "importArmatureOnly": False, "mergeGroups": False,
        "importShadowMeshes": shadow, "importOcclusionMeshes": False, "importBoundingBoxes": False,
    }
    if importREMeshFile(str(Path(path).resolve()), options) is False:
        raise RuntimeError("import failed: " + str(path))
    new = [bpy.data.collections[n] for n in bpy.data.collections.keys() if n not in before]
    root = next(c for c in new if c.get("~TYPE") == "RE_MESH_COLLECTION")
    arm = next((o for o in root.all_objects if o.type == "ARMATURE"), None)
    return root, arm


def export_re_mesh(collection, path, preserve_bone_matrices=True):
    from re_mesh_editor.modules.mesh.blender_re_mesh import exportREMeshFile
    opts = dict(targetCollection=collection.name, selectedOnly=False, exportAllLODs=True, exportBlendShapes=False,
                rotate90=True, useBlenderMaterialName=False, preserveBoneMatrices=preserve_bone_matrices,
                exportBoundingBoxes=False, autoSolveRepeatedUVs=True, preserveSharpEdges=False)
    if not exportREMeshFile(str(path), opts):
        raise RuntimeError("export failed: " + str(path))
