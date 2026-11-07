import bpy, sys, json, mathutils
argv = sys.argv[sys.argv.index('--')+1:]
src, out = argv
bpy.ops.wm.read_factory_settings(use_empty=True)
if src.lower().endswith('.vrm'):
    bpy.ops.import_scene.vrm(filepath=src)
else:
    bpy.ops.import_scene.fbx(filepath=src)
info = {'objects': [], 'armatures': []}
for ob in bpy.data.objects:
    if ob.type == 'MESH':
        me = ob.data
        tris = sum(len(p.vertices) - 2 for p in me.polygons)
        bb = [ob.matrix_world @ mathutils.Vector(c) for c in ob.bound_box]
        mn = [min(v[i] for v in bb) for i in range(3)]; mx = [max(v[i] for v in bb) for i in range(3)]
        info['objects'].append({'name': ob.name, 'verts': len(me.vertices), 'tris': tris,
            'mats': [m.name if m else None for m in me.materials], 'vgroups': len(ob.vertex_groups),
            'shapekeys': len(me.shape_keys.key_blocks) if me.shape_keys else 0,
            'uvs': [u.name for u in me.uv_layers], 'parent': ob.parent.name if ob.parent else None,
            'bbmin': mn, 'bbmax': mx, 'scale': list(ob.scale)})
    elif ob.type == 'ARMATURE':
        bones = []
        for b in ob.data.bones:
            h = ob.matrix_world @ b.head_local; t = ob.matrix_world @ b.tail_local
            bones.append({'name': b.name, 'parent': b.parent.name if b.parent else None, 'head': list(h), 'tail': list(t)})
        info['armatures'].append({'name': ob.name, 'nbones': len(bones), 'bones': bones, 'matrix': [list(r) for r in ob.matrix_world]})
mats = {}
for m in bpy.data.materials:
    imgs = []
    if m.use_nodes:
        for n in m.node_tree.nodes:
            if n.type == 'TEX_IMAGE' and n.image: imgs.append((n.image.name, list(n.image.size)))
    mats[m.name] = imgs
info['materials'] = mats
info['images'] = [(i.name, list(i.size), i.filepath) for i in bpy.data.images]
json.dump(info, open(out, 'w'), indent=1)
print('INVENTORY DONE', len(info['objects']), 'meshes')
