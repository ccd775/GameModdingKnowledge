import bpy, sys, os
src = sys.argv[sys.argv.index('--')+1]; out = sys.argv[sys.argv.index('--')+2]
os.makedirs(out, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src, use_anim=False)
for m in bpy.data.materials:
    if not m.use_nodes: continue
    for n in m.node_tree.nodes:
        if n.type == 'TEX_IMAGE' and n.image:
            im = n.image
            print('MATTEX', m.name, n.label or n.name, im.name, im.size[:], im.packed_file is not None, im.filepath, 'alpha', im.alpha_mode, 'ch', im.channels, 'depth', im.depth)
for im in bpy.data.images:
    if im.size[0] == 0: continue
    p = os.path.join(out, im.name.replace('.', '_') + '.png')
    im.filepath_raw = p; im.file_format = 'PNG'
    try:
        im.save(); print('SAVED', p, im.size[:], im.channels)
    except Exception as e:
        print('FAIL', im.name, e)
