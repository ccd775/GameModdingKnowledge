"""Render TotkMdl export JSONs (game space, Y up) in Blender with textures, front/side/back views.
usage: blender -b --factory-startup -P blender_preview.py -- <out_prefix> <tex_map.json> <model.json> [<model.json> ...] [--offset X model.json ...]
tex_map.json: {"texture name": "png path"}  (material _a0 lookup)
"""
import bpy, sys, json, math
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index('--') + 1:]
prefix, texmap_path = argv[0], argv[1]
texmap = json.load(open(texmap_path, encoding='utf-8'))
items = []
off = 0.0
i = 2
cam_override = None
icon = None
while i < len(argv):
    if argv[i] == '--icon': icon = (float(argv[i + 1]), float(argv[i + 2]), float(argv[i + 3]), float(argv[i + 4])); i += 5; continue
    if argv[i] == '--offset': off = float(argv[i + 1]); i += 2; continue
    if argv[i] == '--cam': cam_override = tuple(float(x) for x in argv[i + 1:i + 4]); i += 4; continue
    items.append((argv[i], off)); i += 1

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
C = Matrix(((1, 0, 0), (0, 0, -1), (0, 1, 0)))  # game (x, y, z) -> blender (x, -z, y)
img_cache = {}
def material_for(texname):
    key = texname or 'none'
    if key in bpy.data.materials: return bpy.data.materials[key]
    m = bpy.data.materials.new(key); m.use_nodes = True
    bsdf = m.node_tree.nodes['Principled BSDF']
    bsdf.inputs['Roughness'].default_value = 0.8
    path = texmap.get(texname)
    if path:
        if path not in img_cache: img_cache[path] = bpy.data.images.load(path)
        t = m.node_tree.nodes.new('ShaderNodeTexImage'); t.image = img_cache[path]
        m.node_tree.links.new(t.outputs['Color'], bsdf.inputs['Base Color'])
    else:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.2, 0.8, 1)
    return m

for path, ox in items:
    d = json.load(open(path, encoding='utf-8'))
    for mdl in d['models']:
        mats = {m['name']: m for m in mdl['materials']}
        for s in mdl['shapes']:
            P = [C @ Vector(p) + Vector((ox, 0, 0)) for p in s['pos']]
            F = s['faces']
            tris = [(F[k], F[k + 1], F[k + 2]) for k in range(0, len(F) - 2, 3)]
            me = bpy.data.meshes.new(s['name']); me.from_pydata(P, [], tris); me.update()
            uvl = me.uv_layers.new()
            for poly in me.polygons:
                for li in poly.loop_indices:
                    u, v = s['uv0'][me.loops[li].vertex_index]
                    uvl.data[li].uv = (u, 1 - v)
            tex = next((t['name'] for t in mats.get(s['material'], {}).get('textures', []) if t['sampler'] == '_a0'), None)
            me.materials.append(material_for(tex))
            ob = bpy.data.objects.new(s['name'], me); scene.collection.objects.link(ob)
            for p in me.polygons: p.use_smooth = True

world = bpy.data.worlds.new('w'); scene.world = world; world.use_nodes = True
world.node_tree.nodes['Background'].inputs['Color'].default_value = (0.6, 0.6, 0.65, 1)
world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
sun = bpy.data.objects.new('sun', bpy.data.lights.new('sun', 'SUN')); scene.collection.objects.link(sun)
sun.rotation_euler = (math.radians(50), 0, math.radians(30)); sun.data.energy = 3
scene.render.engine = 'BLENDER_EEVEE_NEXT' if 'BLENDER_EEVEE_NEXT' in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties['engine'].enum_items] else 'BLENDER_EEVEE'
scene.render.resolution_x, scene.render.resolution_y = 900, 1100
cam = bpy.data.objects.new('cam', bpy.data.cameras.new('cam')); scene.collection.objects.link(cam); scene.camera = cam
cam.data.type = 'ORTHO'
xs = [ox for _, ox in items]; cx = (min(xs) + max(xs)) / 2 if xs else 0
cam.data.ortho_scale = max(2.1, (max(xs) - min(xs)) + 1.4) if xs else 2.1
cz = 0.95
if icon:
    # icon: centre x, centre y (game), ortho scale, yaw degrees; transparent 512x512 front 3/4 view
    scene.render.film_transparent = True
    scene.render.resolution_x = scene.render.resolution_y = 512
    cam.data.ortho_scale = icon[2]
    yaw = math.radians(icon[3])
    cam.location = (icon[0] + 5 * math.sin(yaw), -5 * math.cos(yaw), icon[1])
    cam.rotation_euler = (math.radians(90), 0, yaw)
    scene.render.filepath = f'{prefix}.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath)
    raise SystemExit(0)
if cam_override:
    cx, cz, cam.data.ortho_scale = cam_override[0], cam_override[1], cam_override[2]
for name, loc, rot in (('front', (cx, -5, cz), (90, 0, 0)), ('side', (cx + 5, 0, cz), (90, 0, 90)), ('back', (cx, 5, cz), (90, 0, 180)), ('top', (cx, 0, cz + 5), (0, 0, 0))):
    cam.location = loc; cam.rotation_euler = tuple(math.radians(a) for a in rot)
    scene.render.filepath = f'{prefix}_{name}.png'
    bpy.ops.render.render(write_still=True)
    print('RENDERED', scene.render.filepath)
