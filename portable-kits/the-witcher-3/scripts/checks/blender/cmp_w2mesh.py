"""Content comparison of w2mesh files that ignores vertex order (the add-on's exporter does not keep it from run to
run): vertex multiset (position to 1e-6 m + {bone name: weight} to 1e-4), face multiset (corner vertices), UV multiset,
vertex-group names. The first mesh is the reference.
blender -b --factory-startup --python scripts/checks/blender/cmp_w2mesh.py -- <man_base.w2rig> <mesh A> <mesh B> [...]
Prints one 'CMP <path> {...}' line per mesh after the first, then 'CMP DONE'."""
import bpy, sys, os, importlib, addon_utils, json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))   # kit scripts/
import w3paths  # noqa: E402
argv = sys.argv[sys.argv.index('--') + 1:]
MOD = w3paths.addon_module()
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable(MOD, default_set=True)
irig = importlib.import_module(MOD + '.importers.import_rig')
imesh = importlib.import_module(MOD + '.importers.import_mesh')
irig.import_w3_rig(argv[0], ns='')
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]


def load(path):
    before = set(bpy.data.objects)
    imesh.import_mesh(path, do_import_mats=False, do_import_armature=True, target_armature=arm)
    objs = sorted([o for o in set(bpy.data.objects) - before if o.type == 'MESH'], key=lambda o: o.name)
    out = []
    for o in objs:
        me = o.data
        gi = {g.index: g.name for g in o.vertex_groups}
        uv = me.uv_layers[0].data if me.uv_layers else None
        verts = [(tuple(round(c, 6) for c in v.co), tuple(sorted((gi[g.group], round(g.weight, 4)) for g in v.groups if g.weight > 0)))
                 for v in me.vertices]
        uvs = [tuple(round(c, 6) for c in d.uv) for d in uv] if uv else []
        polys = [tuple(p.vertices) for p in me.polygons]
        out.append((len(me.vertices), verts, uvs, polys, sorted(gi.values())))
    for o in objs:
        bpy.data.objects.remove(o, do_unlink=True)
    return out


ref = load(argv[1])
for path in argv[2:]:
    cur = load(path)
    res = {'submeshes': [len(ref), len(cur)]}
    for k, (a, b) in enumerate(zip(ref, cur)):
        fa = sorted(tuple(sorted(a[1][i] for i in p)) for p in a[3])
        fb = sorted(tuple(sorted(b[1][i] for i in p)) for p in b[3])
        res[str(k)] = {'verts': [a[0], b[0]], 'ordered_equal': a[1] == b[1],
                       'vertex_multiset_equal': sorted(a[1]) == sorted(b[1]),
                       'face_multiset_equal': fa == fb, 'uv_multiset_equal': sorted(a[2]) == sorted(b[2]),
                       'groups_equal': a[4] == b[4]}
    print('CMP', path, json.dumps(res))
print('CMP DONE')
