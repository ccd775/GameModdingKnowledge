"""Prepare Karin_Original (the FBX) as a build source for build_karin_body.py.

The PicodraTech source is a blend in these conventions, which build_karin_body.py relies on:
- armature and meshes at identity, Z-up, metres; rest pose = pose (no posed bones);
- humanoid bones named Hips / Spine / Chest / Neck / Head / Eye.L / Shoulder.L / UpperArm.L / LowerArm.L / Hand.L /
  UpperLeg.L / LowerLeg.L / Foot.L / Toes.L / <Finger><Proximal|Intermediate|Distal>.L (vertex groups follow);
- the saved shape-key mix is kept (the builder bakes it).
The FBX (a Unity VRM export: cm, Y-up, armature object scaled 0.01) is converted to that and saved as a blend, the
packed textures are written out byte for byte, and the bone hierarchy goes to an inventory file for the chain spec.

usage: blender -b --factory-startup --python prepare_karin_original.py -- <out_dir> <Karin(Clone)_BlenderSafe.fbx>
  writes <out_dir>/karin_original_src.blend, <out_dir>/images/*.png, <out_dir>/inventory.json
  The FBX must be the exact file this was written for (SRC_SHA256 below): bone names, material images and the rest
  pose checks are specific to it.
"""
import hashlib
import json
import sys
from pathlib import Path

import bpy
from mathutils import Matrix

SRC = None  # the FBX, second argument after --
SRC_SHA256 = "0B6E268D9399A9921E52FF6E4FA97938922C4C7DFEAE05FECB9EBCB4486418DA"

# FBX (Unity humanoid) bone -> PicodraTech-blend name
RENAME = {n: n for n in ("Hips", "Spine", "Chest", "Neck", "Head")}
for side, s in (("Left", "L"), ("Right", "R")):
    RENAME.update({
        f"{side}Eye": f"Eye.{s}", f"{side}Shoulder": f"Shoulder.{s}", f"{side}UpperArm": f"UpperArm.{s}",
        f"{side}LowerArm": f"LowerArm.{s}", f"{side}Hand": f"Hand.{s}", f"{side}UpperLeg": f"UpperLeg.{s}",
        f"{side}LowerLeg": f"LowerLeg.{s}", f"{side}Foot": f"Foot.{s}", f"{side}ToeBase": f"Toes.{s}",
    })
    for f in ("Thumb", "Index", "Middle", "Ring", "Little"):
        for p in ("Proximal", "Intermediate", "Distal"):
            RENAME[f"{side}{f}{p}"] = f"{f}{p}.{s}"

# material -> the packed image that carries its colour (and its alpha, if it has a real one)
IMAGES = {
    "Karin_Body": "Standard_5_Karin_Body__068b4464__068b4464__fbx_rgb",
    "Karin_Face": "Standard_1_Karin_Face__9838578e__9838578e__fbx_rgb",
    "Karin_Alpha": "UnityTexture_3_Karin_Alpha__88100961",
    "Karin_Hair": "Standard_10_Karin_Hair__1e553117__1e553117__fbx_rgb",
    "Karin_Costume": "Standard_16_Karin_Costume__3b9b5651__3b9b5651__fbx_rgb",
}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    global SRC
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    if len(argv) != 2:
        raise SystemExit("usage: blender -b --factory-startup --python prepare_karin_original.py -- <out_dir> <fbx>")
    out = Path(argv[0])
    SRC = Path(argv[1])
    if not SRC.is_file():
        raise SystemExit(f"source FBX not found: {SRC}")
    out.mkdir(parents=True, exist_ok=True)
    src_sha = sha(SRC)
    assert src_sha == SRC_SHA256, ("source FBX changed", src_sha)
    report: dict = {"source": str(SRC), "source_sha256": src_sha}

    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.fbx(filepath=str(SRC), use_image_search=False, automatic_bone_orientation=False)
    arms = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    assert len(arms) == 1
    arm = arms[0]
    meshes = sorted((o for o in bpy.context.scene.objects if o.type == "MESH"), key=lambda o: o.name)

    # the imported pose must be the rest pose (the builder reads pose-bone heads and bakes the pose into the meshes)
    dev = 0.0
    for pb in arm.pose.bones:
        d = pb.matrix_basis - Matrix.Identity(4)
        dev = max(dev, max(abs(x) for row in d for x in row))
        pb.matrix_basis = Matrix.Identity(4)
    report["pose_deviation_cleared"] = dev
    assert dev < 1e-3, ("the FBX pose is not its rest pose", dev)

    # bake object transforms: everything at identity, Z-up metres
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.data.transform(mw, shape_keys=True)
        o.matrix_world = Matrix.Identity(4)
        for m in o.modifiers:
            if m.type == "ARMATURE":
                m.object = arm
    mw = arm.matrix_world.copy()
    for o in list(bpy.context.scene.objects):
        if o.type == "EMPTY":  # PhysBone colliders / anchor: not needed
            bpy.data.objects.remove(o, do_unlink=True)
    arm.data.transform(mw)
    arm.matrix_world = Matrix.Identity(4)
    arm.name = "Karin_Original_Armature"
    bpy.context.view_layer.update()

    # humanoid names
    missing = [n for n in RENAME if n not in arm.data.bones]
    assert not missing, missing
    for old, new in RENAME.items():
        if old != new:
            arm.data.bones[old].name = new
    for o in meshes:
        for old, new in RENAME.items():
            vg = o.vertex_groups.get(old)
            if vg is not None and old != new:
                vg.name = new
    hips = arm.data.bones["Hips"]
    report["hips_head"] = list(hips.head_local)
    report["upperarm_l_dir"] = list((arm.data.bones["UpperArm.L"].tail_local - arm.data.bones["UpperArm.L"].head_local).normalized())
    assert abs(hips.head_local.z - 0.7494) < 0.01, hips.head_local

    # meshes: world bounds, materials, weighted groups, saved shape-key mix
    rows = {}
    for o in meshes:
        me = o.data
        zs = [v.co.z for v in me.vertices]
        used = set()
        for v in me.vertices:
            for g in v.groups:
                if g.weight > 0:
                    used.add(o.vertex_groups[g.group].name)
        unknown = [n for n in used if n not in arm.data.bones]
        assert not unknown, (o.name, unknown)
        keys = me.shape_keys
        rows[o.name] = {"verts": len(me.vertices), "materials": [m.name for m in me.materials],
                        "z": [round(min(zs), 4), round(max(zs), 4)], "weighted": sorted(used),
                        "shape_mix": {k.name: k.value for k in keys.key_blocks[1:] if k.value} if keys else {}}
    report["meshes"] = rows

    # packed textures, byte for byte
    imgdir = out / "images"
    imgdir.mkdir(exist_ok=True)
    report["images"] = {}
    for mat, name in IMAGES.items():
        im = bpy.data.images[name]
        assert im.packed_file is not None, name
        data = bytes(im.packed_file.data)
        assert data[:8] == b"\x89PNG\r\n\x1a\n", name
        p = imgdir / f"{mat}.png"
        p.write_bytes(data)
        report["images"][mat] = {"image": name, "size": list(im.size), "file": p.name,
                                 "sha256": hashlib.sha256(data).hexdigest().upper()}

    inv = {"armatures": [{"name": arm.name, "bones": [
        {"name": b.name, "parent": b.parent.name if b.parent else None,
         "head": [round(c, 6) for c in b.head_local], "tail": [round(c, 6) for c in b.tail_local]}
        for b in arm.data.bones]}]}
    (out / "inventory.json").write_text(json.dumps(inv, indent=1), encoding="utf-8")
    bpy.ops.wm.save_as_mainfile(filepath=str(out / "karin_original_src.blend"))
    report["blend_sha256"] = sha(out / "karin_original_src.blend")
    (out / "prepare_report.json").write_text(json.dumps(report, indent=1, ensure_ascii=False), encoding="utf-8")
    print("PREPARE_DONE", out)


main()
