import bpy, sys, numpy as np
src = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src, use_anim=False)
o = bpy.data.objects['Body']; mw = np.array(o.matrix_world); ks = o.data.shape_keys.key_blocks
base = np.array([v.co[:] for v in ks[0].data]) @ mw[:3, :3].T + mw[:3, 3]
for name in sys.argv[sys.argv.index('--') + 2].split(','):
    co = np.array([v.co[:] for v in ks[name].data]) @ mw[:3, :3].T + mw[:3, 3]; d = co - base; m = np.linalg.norm(d, axis=1); sel = m > 1e-4
    for side, s in (('L', base[:, 0] > 0), ('R', base[:, 0] < 0)):
        q = sel & s
        if q.any(): print('%-12s %s n=%4d mean d=(%+.4f %+.4f %+.4f) max=%.4f' % (name, side, q.sum(), *d[q].mean(0), m[q].max()))
