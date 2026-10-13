# Source model loading for build_karin.py: brings any profile source (.vrm/.glb/.fbx/.blend) into the state the
# Karin_Original VRM import is in (see profiles.py): meters, identity object transforms, VRM humanoid bone names,
# role mesh names, profile material slots, shape-key mix baked into the base shape.
import os
import re
import bpy
import numpy as np

HUMANOID = ("Hips", "Spine", "Chest", "UpperChest", "Neck", "Head")
SIDED = {"Shoulder", "UpperArm", "LowerArm", "Hand", "UpperLeg", "LowerLeg", "Foot", "ToeBase", "Eye"}
for _f in ("Thumb", "Index", "Middle", "Ring", "Little"):
    for _k in ("Proximal", "Intermediate", "Distal"):
        SIDED.add(_f + _k)
ALIAS = {"Toes": "ToeBase", "Toe": "ToeBase"}


def canonical(name):
    """VRM humanoid name for a bone name in any of the usual spellings, or None."""
    if name in HUMANOID:
        return name
    m = re.match(r"^(Left|Right)(.+)$", name)
    if m:
        side, base = m.group(1), m.group(2)
    else:
        m = re.match(r"^(.+)[._]([LRlr])$", name)
        if not m:
            return None
        base, side = m.group(1), ("Left" if m.group(2) in "Ll" else "Right")
    base = ALIAS.get(base, base)
    return side + base if base in SIDED else None


def _load_objects(path):
    ext = os.path.splitext(path)[1].lower()
    before = set(bpy.data.objects)
    if ext == ".blend":
        with bpy.data.libraries.load(path, link=False) as (src, dst):
            dst.objects = list(src.objects)
        for o in dst.objects:
            if o is not None:
                bpy.context.scene.collection.objects.link(o)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    else:
        bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def _bake_shape_mix(o):
    """Make the current shape-key mix the base shape. Returns the non-zero keys that were baked."""
    kb = o.data.shape_keys.key_blocks
    used = [(k.name, round(k.value, 3)) for k in list(kb)[1:] if abs(k.value) > 1e-6 and not k.mute]
    if not used:
        return []
    n = len(o.data.vertices)
    basis = np.zeros(n * 3)
    kb[0].data.foreach_get("co", basis)
    mix = basis.copy()
    for k in list(kb)[1:]:
        if abs(k.value) <= 1e-6 or k.mute:
            continue
        ref = k.relative_key
        a, b = np.zeros(n * 3), np.zeros(n * 3)
        k.data.foreach_get("co", a)
        ref.data.foreach_get("co", b)
        mix += k.value * (a - b)
    # rebase every key on the new basis (keeps the face keys usable as deltas), then reset the values
    for k in list(kb)[1:]:
        a = np.zeros(n * 3)
        k.data.foreach_get("co", a)
        k.data.foreach_set("co", a + (mix - basis))
        k.value = 0.0
    kb[0].data.foreach_set("co", mix)
    o.data.vertices.foreach_set("co", mix)
    o.data.update()
    return used


def _bone_parented_to_skin(o, arm):
    """Objects parented to a bone (no armature modifier) get a full-weight group on that bone."""
    if o.parent is arm and o.parent_type == "BONE" and not any(m.type == "ARMATURE" for m in o.modifiers):
        g = o.vertex_groups.new(name=o.parent_bone)
        g.add(list(range(len(o.data.vertices))), 1.0, "REPLACE")
        mod = o.modifiers.new("Armature", "ARMATURE")
        mod.object = arm
        return True
    return False


def load(P, report):
    """Import the profile source. Returns (armature, meshes)."""
    src = P["src"]
    new = _load_objects(src)
    rep = report.setdefault("source_prep", {"src": src})
    for o in list(new):
        if o.type == "EMPTY" or (o.type == "MESH" and o.name == "Icosphere") or o.type not in ("MESH", "ARMATURE"):
            bpy.data.objects.remove(o, do_unlink=True)
    for name in P.get("drop_meshes", ()):
        if name in bpy.data.objects:
            bpy.data.objects.remove(bpy.data.objects[name], do_unlink=True)
    arms = [o for o in bpy.data.objects if o.type == "ARMATURE"]
    if len(arms) != 1:
        raise RuntimeError(f"expected one armature, got {[a.name for a in arms]}")
    karm = arms[0]
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    if P["name"] == "karin_original":   # the VRM import is already in the reference state
        return karm, meshes

    # rest pose, baked shape-key mixes
    for pb in karm.pose.bones:
        pb.matrix_basis.identity()
    karm.data.pose_position = "POSE"
    baked = {}
    for o in meshes:
        if o.data.shape_keys:
            b = _bake_shape_mix(o)
            if b:
                baked[o.name] = b
    rep["baked_shape_keys"] = baked
    rep["bone_parented"] = [o.name for o in meshes if _bone_parented_to_skin(o, karm)]

    # identity object transforms (world meters): unparent keeping transforms, apply, re-parent without inverse
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        mw = o.matrix_world.copy()
        o.parent = None
        o.matrix_world = mw
    for o in [karm] + meshes:
        o.hide_set(False)
        o.hide_viewport = False
        o.select_set(True)
    bpy.context.view_layer.objects.active = karm
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    for o in meshes:
        o.parent = karm
        o.matrix_parent_inverse.identity()
        arm_mods = [m for m in o.modifiers if m.type == "ARMATURE"]
        if not arm_mods:
            raise RuntimeError(f"{o.name}: no armature modifier")
        for m in arm_mods[1:]:
            o.modifiers.remove(m)
        arm_mods[0].object = karm
        for m in list(o.modifiers):
            if m.type != "ARMATURE":
                o.modifiers.remove(m)

    # canonical humanoid bone names (renaming a bone renames the vertex groups of its meshes)
    renames = dict(P.get("bone_renames", {}))
    for b in karm.data.bones:
        c = canonical(b.name)
        if c and c != b.name and b.name not in renames:
            renames[b.name] = c
    taken = {b.name for b in karm.data.bones}
    for old, new_name in renames.items():
        if new_name in taken and new_name != old:
            raise RuntimeError(f"bone rename {old} -> {new_name}: name exists")
    for old, new_name in renames.items():
        karm.data.bones[old].name = new_name
    for o in meshes:
        names = {g.name for g in o.vertex_groups}
        stale = [old for old in renames if old in names]
        if stale:
            raise RuntimeError(f"{o.name}: vertex groups not renamed {stale[:5]}")
    rep["bone_renames"] = renames
    missing = [n for n in ("Hips", "Spine", "Chest", "Neck", "Head", "LeftUpperArm", "RightUpperLeg", "LeftEye", "LeftToeBase")
               if n not in karm.data.bones]
    if missing:
        raise RuntimeError(f"humanoid bones missing after rename: {missing}")

    # role mesh names (two phases: names may swap)
    mr = P.get("mesh_renames", {})
    for old in mr:
        bpy.data.objects[old].name = "__tmp__" + old
    for old, new_name in mr.items():
        bpy.data.objects["__tmp__" + old].name = new_name
        if bpy.data.objects.get(new_name) is None:
            raise RuntimeError(f"mesh rename {old} -> {new_name} collided")

    # material slots -> profile slots
    mats = P["materials"]
    for m in bpy.data.materials:
        if m.name in mats:
            m.name = "__src__" + m.name
    slot_mats = {}
    unknown = {}
    for o in meshes:
        me = o.data
        src_names = [(m.name[len("__src__"):] if m and m.name.startswith("__src__") else (m.name if m else "")) for m in me.materials]
        own = P.get("mesh_materials", {}).get(o.name, {})     # per-mesh overrides (e.g. face and skin share a material)
        targets = []
        for n in src_names:
            if n not in own and n not in mats:
                unknown[n] = unknown.get(n, 0) + 1
            targets.append(own.get(n, mats.get(n)))
        order = []
        for t in targets:
            if t and t not in order:
                order.append(t)
        idx = np.zeros(len(me.polygons), dtype=np.int32)
        me.polygons.foreach_get("material_index", idx)
        remap = np.array([order.index(t) if t else 0 for t in targets] or [0], dtype=np.int32)
        me.materials.clear()
        for t in order:
            if t not in slot_mats:
                slot_mats[t] = bpy.data.materials.get(t) or bpy.data.materials.new(t)
            me.materials.append(slot_mats[t])
        me.polygons.foreach_set("material_index", remap[np.clip(idx, 0, len(remap) - 1)])
        me.update()
    if unknown:
        raise RuntimeError(f"materials without a profile slot: {unknown}")
    rep["slots"] = sorted(slot_mats)
    if P.get("cull_alpha") is not None:
        rep["culled_transparent_faces"] = _cull_transparent(P, meshes, P["cull_alpha"])
    for o in [o for o in meshes if len(o.data.polygons) == 0]:
        bpy.data.objects.remove(o, do_unlink=True)
    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    return karm, meshes


def _cull_transparent(P, meshes, thr):
    """Delete faces that are fully transparent in their atlas page (the game's cloth material renders opaque)."""
    alpha = {}
    for slot, spec in P["slots"].items():
        page = spec["page"]
        if page in alpha:
            continue
        img = bpy.data.images.load(P["tex_dir"] + "/" + P["tex_files"]["color"].format(page=page))
        w, h = img.size
        px = np.zeros(w * h * 4, np.float32)
        img.pixels.foreach_get(px)
        alpha[page] = px.reshape(h, w, 4)[..., 3].copy()
        bpy.data.images.remove(img)
    out = {}
    for o in meshes:
        me = o.data
        uv = me.uv_layers.active
        if uv is None:
            continue
        uvs = np.zeros(len(me.loops) * 2, np.float32)
        uv.data.foreach_get("uv", uvs)
        uvs = uvs.reshape(-1, 2)
        dead = []
        for p in me.polygons:
            m = me.materials[p.material_index]
            spec = P["slots"].get(m.name) if m else None
            if spec is None:
                continue
            a = alpha[spec["page"]]
            h, w = a.shape
            pts = uvs[p.loop_start:p.loop_start + p.loop_total]
            pts = np.vstack([pts, pts.mean(0), (pts + pts.mean(0)) / 2])
            x = np.clip((pts[:, 0] % 1.0 * w).astype(int), 0, w - 1)
            y = np.clip((pts[:, 1] % 1.0 * h).astype(int), 0, h - 1)
            if a[y, x].max() < thr:
                dead.append(p.index)
        if dead:
            import bmesh
            bm = bmesh.new()
            bm.from_mesh(me)
            bm.faces.ensure_lookup_table()
            bmesh.ops.delete(bm, geom=[bm.faces[i] for i in dead], context="FACES")
            bm.to_mesh(me)
            bm.free()
            me.update()
            out[o.name] = len(dead)
    return out
