# Bake ambient occlusion per texture atlas of the built Karin mesh and write Sifu ComboMaps (R rough, G metal, B AO, A mask).
# blender -b karin_sifu.blend --python bake_ao.py -- <out_dir> [size] [profile]
# With a profile that has atlas "slots", one AO image per atlas page is written instead (AO_<page>.png, linear grey);
# make_textures.py turns those into the per-slot ComboMaps.
import sys, os
import bpy
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import profiles
args = sys.argv[sys.argv.index("--") + 1:]
OUT = args[0]
SIZE = int(args[1]) if len(args) > 1 else 1024
P = profiles.activate(args[2] if len(args) > 2 else None)
os.makedirs(OUT, exist_ok=True)
# atlas -> (materials sharing that UV atlas, roughness 0-255, mask alpha, AO strength)
ATLAS = {
    "Face": (["Karin_Face"], 140, 230, 0.6),
    "Skin": (["Karin_Body"], 150, 230, 0.8),
    "Hair": (["Karin_Hair", "Karin_Hair_Transparent", "Karin_TwinTail_L", "Karin_TwinTail_R", "Karin_SideHair_L",
              "Karin_SideHair_R", "Karin_Tail"], 115, 255, 0.9),
    "Costume": (["Karin_Costume", "Karin_Skirt"], 205, 255, 1.0),
}
PAGE_MODE = bool(P.get("slots"))
if PAGE_MODE:   # atlas page -> slots on it (strength 1: make_textures.py applies the per-kind AO strength)
    ATLAS = {}
    for slot, spec in P["slots"].items():
        ATLAS.setdefault(spec["page"], ([], 0, 255, 1.0))[0].append(slot)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = 64
sc.render.bake.margin = 8
sc.world = sc.world or bpy.data.worlds.new("World")
for o in bpy.data.objects:
    if o.type == "MESH" and o.name.startswith("Proxy_"):
        o.hide_render = True
meshes = [o for o in bpy.data.objects if o.type == "MESH" and not o.name.startswith("Proxy_")]
for name, (mats, rough, alpha, strength) in ATLAS.items():
    img = bpy.data.images.new("AO_" + name, SIZE, SIZE, alpha=False, float_buffer=False)
    users = []
    for m in mats:
        mat = bpy.data.materials.get(m)
        if not mat:
            continue
        mat.use_nodes = True
        nt = mat.node_tree
        node = nt.nodes.new("ShaderNodeTexImage")
        node.image = img
        node.name = "BAKE_TARGET"
        nt.nodes.active = node
        users.append(mat)
    objs = [o for o in meshes if any(s.material in users for s in o.material_slots)]
    # other materials on those objects must also have an active image node, or the bake errors: give them a dummy
    dummy = bpy.data.images.new("dummy_" + name, 8, 8)
    for o in objs:
        for s in o.material_slots:
            if s.material and s.material not in users:
                s.material.use_nodes = True
                nt = s.material.node_tree
                n = nt.nodes.get("BAKE_DUMMY") or nt.nodes.new("ShaderNodeTexImage")
                n.name = "BAKE_DUMMY"
                n.image = dummy
                nt.nodes.active = n
    bpy.ops.object.select_all(action="DESELECT")
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.bake(type="AO", use_selected_to_active=False)
    px = np.array(img.pixels[:]).reshape(SIZE, SIZE, 4)[::-1, :, 0]
    if PAGE_MODE:
        oimg = bpy.data.images.new("AO_" + name, SIZE, SIZE, alpha=False)
        oimg.colorspace_settings.name = "Non-Color"
        g = np.zeros((SIZE, SIZE, 4), np.float32)
        g[..., 0] = g[..., 1] = g[..., 2] = px
        g[..., 3] = 1.0
        oimg.pixels[:] = g[::-1].reshape(-1)
        oimg.filepath_raw = os.path.join(OUT, f"AO_{name}.png")
        oimg.file_format = "PNG"
        oimg.save()
        print("BAKED", name, len(objs), float(px.mean()))
        for m in users:
            m.node_tree.nodes.remove(m.node_tree.nodes["BAKE_TARGET"])
        continue
    ao = 1.0 - strength * (1.0 - px)
    ao = np.clip(ao, 0, 1) ** 0.8
    out = np.zeros((SIZE, SIZE, 4), np.float32)
    out[..., 0] = rough / 255.0
    out[..., 1] = 0.0
    out[..., 2] = ao
    out[..., 3] = alpha / 255.0
    oimg = bpy.data.images.new("S_" + name, SIZE, SIZE, alpha=True)
    oimg.colorspace_settings.name = "Non-Color"
    oimg.pixels[:] = out[::-1].reshape(-1)
    oimg.filepath_raw = os.path.join(OUT, f"T_Karin_{name}_S.png")
    oimg.file_format = "PNG"
    oimg.save()
    print("BAKED", name, len(objs), float(ao.mean()))
    for m in users:
        nt = m.node_tree
        nt.nodes.remove(nt.nodes["BAKE_TARGET"])
print("BAKE_DONE")
