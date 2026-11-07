import bpy, sys, os
argv = sys.argv[sys.argv.index('--')+1:]
src, outdir = argv
os.makedirs(outdir, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src)
for im in bpy.data.images:
    if im.size[0] == 0: continue
    name = os.path.splitext(os.path.basename(im.filepath))[0] or im.name
    p = os.path.join(outdir, name + '.png')
    im.filepath_raw = p
    im.file_format = 'PNG'
    try:
        im.save()
        print('SAVED', p, tuple(im.size), im.packed_file is not None)
    except Exception as e:
        print('FAIL', im.name, e)
