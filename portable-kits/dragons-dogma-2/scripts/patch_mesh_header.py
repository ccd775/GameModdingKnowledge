"""Patch a DD2 V3 (.mesh.260421070) header: content flags (offset 22) to the equipment-mesh value.

usage: python patch_mesh_header.py <mesh> [--flags 4099]
"""
import argparse
import struct

ap = argparse.ArgumentParser()
ap.add_argument("mesh")
ap.add_argument("--flags", type=int, default=4099)  # IsSkinning | HasJoint | UseRTVertexAnimation (like tops_001_bd_f)
a = ap.parse_args()
b = bytearray(open(a.mesh, "rb").read())
magic, ver = struct.unpack_from("<II", b, 0)
assert magic == 0x4853454D and ver == 251205828, (hex(magic), ver)
old = struct.unpack_from("<H", b, 22)[0]
struct.pack_into("<H", b, 22, a.flags)
open(a.mesh, "wb").write(b)
print(f"{a.mesh}: flags {old} -> {a.flags}")
