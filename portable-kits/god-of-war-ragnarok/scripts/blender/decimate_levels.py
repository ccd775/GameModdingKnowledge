"""Export decimated copies of a fitted (pose-baked) character for distance LODs.

Usage: blender --background --python decimate_levels.py -- <fitted.blend> <out_root> <ratio> [<ratio> ...]
Writes <out_root>/r<ratio>/<mesh>.npz plus summary.json in the same layout as fit_karin.py.
"""
import bpy, sys, os, json
import numpy as np

argv = sys.argv[sys.argv.index('--') + 1:]
BLEND, OUT = argv[0], argv[1]
RATIOS = [float(x) for x in argv[2:]]


def export(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    summary = {'meshes': {}}
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        me = o.data
        me.calc_loop_triangles()
        V = np.array([v.co[:] for v in me.vertices], np.float32)
        nl = len(me.loops)
        lv = np.zeros(nl, np.int32); me.loops.foreach_get('vertex_index', lv)
        ln = np.zeros(nl * 3, np.float32); me.corner_normals.foreach_get('vector', ln)
        uv = np.zeros(nl * 2, np.float32); me.uv_layers.active.data.foreach_get('uv', uv)
        nt = len(me.loop_triangles)
        tl = np.zeros(nt * 3, np.int32); me.loop_triangles.foreach_get('loops', tl)
        tm = np.zeros(nt, np.int32); me.loop_triangles.foreach_get('material_index', tm)
        wi, ww, wv = [], [], []
        for v in me.vertices:
            for g in v.groups:
                if g.weight > 1e-5:
                    wv.append(v.index); wi.append(g.group); ww.append(g.weight)
        np.savez_compressed(os.path.join(out_dir, f'{o.name}.npz'), V=V, loop_v=lv, loop_n=ln.reshape(-1, 3),
                            loop_uv=uv.reshape(-1, 2), tri_loops=tl.reshape(-1, 3), tri_mat=tm,
                            w_vert=np.array(wv, np.int32), w_group=np.array(wi, np.int32), w_weight=np.array(ww, np.float32))
        summary['meshes'][o.name] = dict(groups=[g.name for g in o.vertex_groups],
                                         materials=[s.material.name if s.material else '' for s in o.material_slots],
                                         verts=len(V), tris=nt)
    json.dump(summary, open(os.path.join(out_dir, 'summary.json'), 'w'), indent=1)


for r in RATIOS:
    bpy.ops.wm.open_mainfile(filepath=BLEND)
    for o in [o for o in bpy.data.objects if o.type == 'MESH']:
        bpy.context.view_layer.objects.active = o
        md = o.modifiers.new('dec', 'DECIMATE')
        md.decimate_type = 'COLLAPSE'
        md.ratio = r
        md.use_collapse_triangulate = True
        bpy.ops.object.modifier_apply(modifier=md.name)
    export(os.path.join(OUT, f'r{r:g}'))
    print('LEVEL DONE', r)
