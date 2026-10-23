import bpy, sys, numpy as np
src = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=src, use_anim=False)
o = bpy.data.objects['Body']; mw = np.array(o.matrix_world)
ks = o.data.shape_keys.key_blocks
base = np.array([v.co[:] for v in ks[0].data]); base = base @ mw[:3, :3].T + mw[:3, 3]
want = sys.argv[sys.argv.index('--') + 2].split(',')
for k in ks[1:]:
    if want != [''] and not any(k.name.startswith(w) for w in want): continue
    co = np.array([v.co[:] for v in k.data]) @ mw[:3, :3].T + mw[:3, 3]
    d = co - base; m = np.linalg.norm(d, axis=1); sel = m > 1e-4
    if not sel.any(): print('%-22s none' % k.name); continue
    c = (base[sel] * m[sel, None]).sum(0) / m[sel].sum()
    print('%-22s n=%5d max=%.4f centroid=(%+.3f %+.3f %+.3f) xspan=(%+.3f..%+.3f)' % (k.name, sel.sum(), m.max(), *c, base[sel, 0].min(), base[sel, 0].max()))
