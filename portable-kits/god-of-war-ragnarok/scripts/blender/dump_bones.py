import bpy, sys, json
argv = sys.argv[sys.argv.index('--')+1:]
src, out = argv[0], argv[1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
mw = arm.matrix_world
bones = {}
for b in arm.data.bones:
    bones[b.name] = dict(head=list(mw @ b.head_local), tail=list(mw @ b.tail_local), parent=b.parent.name if b.parent else None,
                         connected=b.use_connect)
meshes = {}
for o in bpy.data.objects:
    if o.type == 'MESH':
        import mathutils
        vs = [o.matrix_world @ v.co for v in o.data.vertices]
        mn = [min(v[i] for v in vs) for i in range(3)]; mx = [max(v[i] for v in vs) for i in range(3)]
        meshes[o.name] = dict(min=mn, max=mx, mw=[list(r) for r in o.matrix_world], parent=o.parent.name if o.parent else None)
json.dump(dict(arm=arm.name, arm_mw=[list(r) for r in mw], bones=bones, meshes=meshes), open(out, 'w'), indent=1)
