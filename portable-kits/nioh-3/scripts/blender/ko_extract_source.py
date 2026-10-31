"""Blender (background) exporter: Karin_Original FBX -> npz meshes + bones + raw textures.

Usage: blender --factory-startup --background --python ko_extract_source.py -- <fbx> <out_dir>
Writes <out_dir>/source.npz, source.json and textures/<image>.png (packed bytes, unmodified).
Coordinates are Blender world space (Z up, metres); nothing is posed or scaled here.
"""
import bpy, sys, json, os
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
fbx, out = argv[0], argv[1]
os.makedirs(os.path.join(out, "textures"), exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=fbx)

arm = next(o for o in bpy.context.scene.objects if o.type == "ARMATURE")
bones = []
for b in arm.data.bones:
    m = arm.matrix_world @ b.matrix_local
    bones.append({"name": b.name, "parent": b.parent.name if b.parent else None,
                  "head": list(arm.matrix_world @ b.head_local), "tail": list(arm.matrix_world @ b.tail_local),
                  "matrix": [list(r) for r in m]})

arrays, meshes, images = {}, [], {}
depsgraph = bpy.context.evaluated_depsgraph_get()
for ob in bpy.context.scene.objects:
    for mod in ob.modifiers:
        mod.show_viewport = False  # keep shape-key mix (the prefab's kisekae state), drop skinning
depsgraph.update()
for ob in sorted((o for o in bpy.context.scene.objects if o.type == "MESH"), key=lambda o: o.name):
    active_keys = [(k.name, k.value) for k in ob.data.shape_keys.key_blocks if k.value > 0 and k.name != "Basis"] if ob.data.shape_keys else []
    me = ob.evaluated_get(depsgraph).to_mesh()
    assert len(me.vertices) == len(ob.data.vertices)
    me.calc_loop_triangles()
    me.calc_normals_split()
    mw = ob.matrix_world
    nm = mw.to_3x3().inverted().transposed()
    nv, nl = len(me.vertices), len(me.loops)
    co = np.empty(nv * 3, np.float32); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    co = (np.array(mw)[:3, :3] @ co.T).T + np.array(mw)[:3, 3]
    lvi = np.empty(nl, np.int32); me.loops.foreach_get("vertex_index", lvi)
    lno = np.empty(nl * 3, np.float32); me.loops.foreach_get("normal", lno); lno = lno.reshape(-1, 3)
    lno = (np.array(nm) @ lno.T).T
    lno /= np.maximum(np.linalg.norm(lno, axis=1, keepdims=True), 1e-12)
    uv = np.empty(nl * 2, np.float32); me.uv_layers.active.data.foreach_get("uv", uv); uv = uv.reshape(-1, 2)
    tris = np.array([t.loops[:] for t in me.loop_triangles], np.int32).reshape(-1, 3)
    tmat = np.array([t.material_index for t in me.loop_triangles], np.int32)
    groups = [g.name for g in ob.vertex_groups]
    wv, wg, ww = [], [], []
    for v in me.vertices:
        for g in v.groups:
            if g.weight > 0:
                wv.append(v.index); wg.append(g.group); ww.append(g.weight)
    key = ob.name.replace(".", "_")
    arrays.update({f"{key}__co": co.astype(np.float32), f"{key}__loop_vertex": lvi, f"{key}__loop_normal": lno.astype(np.float32),
                   f"{key}__loop_uv": uv, f"{key}__tris": tris, f"{key}__tri_material": tmat,
                   f"{key}__w_vertex": np.array(wv, np.int32), f"{key}__w_group": np.array(wg, np.int32),
                   f"{key}__w_weight": np.array(ww, np.float32)})
    mats = []
    for slot in ob.material_slots:
        m = slot.material
        texs = []
        if m and m.use_nodes:
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    links = [l.to_socket.name for o in n.outputs for l in o.links]
                    texs.append({"image": n.image.name, "links": links, "output": [o.name for o in n.outputs if o.links]})
                    images[n.image.name] = n.image
        mats.append({"name": m.name if m else None, "textures": texs})
    meshes.append({"name": ob.name, "key": key, "groups": groups, "materials": mats, "shape_keys_applied": active_keys,
                   "vertices": nv, "loops": nl, "triangles": len(tris), "hidden": ob.hide_get()})

for img in bpy.data.images:
    images.setdefault(img.name, img)
tex_index = {}
for name, img in images.items():
    safe = "".join(c if c.isalnum() or c in "_-" else "_" for c in name)
    path = os.path.join(out, "textures", safe + ".png")
    if img.packed_file is not None:
        data = bytes(img.packed_file.data)
        with open(path, "wb") as f:
            f.write(data)
        tex_index[name] = {"file": os.path.basename(path), "size": list(img.size), "bytes": len(data), "source": "packed"}
    else:
        tex_index[name] = {"file": None, "size": list(img.size), "source": img.filepath}

np.savez_compressed(os.path.join(out, "source.npz"), **arrays)
with open(os.path.join(out, "source.json"), "w", encoding="utf-8") as f:
    json.dump({"fbx": fbx, "armature": arm.name, "bones": bones, "meshes": meshes, "textures": tex_index}, f, ensure_ascii=False, indent=1)
print("EXTRACTED", len(meshes), "meshes", len(bones), "bones", len(tex_index), "images")
