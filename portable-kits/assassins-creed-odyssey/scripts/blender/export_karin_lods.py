"""Prepare the fitted Karin for AnvilToolkit import and export LOD GLBs (Blender 5.0, background).
Copied from ACShadow/scripts (2026-10-19) for Odyssey; adds the aco_* profiles below.

blender -b <karin_fit.blend> --python export_karin_lods.py -- <out_dir> [--ratios 1,1,0.5,0.25,0.12] [--profile naoe|yasuke|original_naoe|original_yasuke|aco_tex1|aco_pt] [--keep-full <face mesh,...>]

Writes <out_dir>/karin_lod<i>.glb and <out_dir>/export_report.json.
- materials renamed to donor Material IDs (decimal) by atlas
- one joined mesh, triangulated, white vertex colour, <= 4 normalized weights
- armature pruned to used bones + their ancestors (keeps mesh bone count < 256 -> 8-bit indices)
"""
import bpy, bmesh, sys, os, json

argv = sys.argv[sys.argv.index("--") + 1:]
out_dir = argv[0]
ratios = [float(r) for r in (argv[argv.index("--ratios") + 1].split(",") if "--ratios" in argv else "1,1,0.5,0.25,0.12".split(","))]
os.makedirs(out_dir, exist_ok=True)

PROFILE = argv[argv.index("--profile") + 1] if "--profile" in argv else "naoe"
ATLAS_OF = {  # source material -> donor Material ID (naoe: Karin_PicodraTech -> Naoe Iconic donors)
    "Body": "2186735722113", "Karin_Face": "2186735722113", "Karin_Alpha": "2186735722113",   # Skin_Face -> Greaves_NaoeIconicSuneate_A
    "Hair": "2186735659022", "Karin_Hair_Transparent": "2186735659022",                        # Hair_Head -> Arm_L_NaoeIconicGlove
    "ClothA_Blue": "2186735713815", "Costume": "2186735713815", "Karin_Costume": "2186735713815",  # Clothing_A -> Dress_NaoeIconicKosode
    "ClothB_Blue": "2186735706061", "Costume_1": "2186735706061", "Costume_Metalic": "2186735706061",  # Clothing_B -> Skirt_NaoeIconicSkirt
}

if PROFILE == "yasuke":  # Karin_UnendingFlame -> Yasuke Iconic arm donors (Cutout/Opaque pairs share one donor)
    ATLAS_OF = {f"Atlas_{a}_{k}": mid for a, mid in (("Fabric", "2178119334991"), ("Hair", "2178119332333"),
                ("LeatherRope", "2178119687249"), ("Metal", "2178119338899"), ("SkinFace", "2264003604344"))
                for k in ("Cutout", "Opaque")}
# Karin_Original (Unity FBX, 5 textures). None = drop those faces: the Karin_Alpha overlays (tears, blush, "shy"
# lines) sit inside the head in the neutral pose and only come out through expression shape keys.
if PROFILE == "original_naoe":  # -> the four Naoe Iconic donors of the PicodraTech build
    ATLAS_OF = {"Karin_Face": "2186735722113", "Karin_Body": "2186735706061", "Karin_Hair": "2186735659022",
                "Karin_Hair_Transparent": "2186735659022", "Karin_Costume": "2186735713815", "Karin_Alpha": None}
if PROFILE == "original_yasuke":  # -> four of the five Yasuke Iconic arm donors (KoteBend unused)
    ATLAS_OF = {"Karin_Face": "2264003604344", "Karin_Body": "2178119687249", "Karin_Hair": "2178119332333",
                "Karin_Hair_Transparent": "2178119332333", "Karin_Costume": "2178119334991", "Karin_Alpha": None}
# Odyssey (ACOd): aco_pack_atlas.py already put every face into one material named by the target Material ID
if PROFILE == "aco_atlas":
    ATLAS_OF = {"1426570796496": "1426570796496"}   # ACD_CHF_PLA_Kassandra_Head (skin, body + head of Kassandra)
if PROFILE == "aco_tex1":  # new ACD_Tex1 materials 0x2A0CA5A0001..4 inside the BodyKassandra container (build_v1.py)
    ATLAS_OF = {"Karin_Face": "2889612918785", "Karin_Body": "2889612918786", "Karin_Hair": "2889612918787",
                "Karin_Hair_Transparent": "2889612918787", "Karin_Costume": "2889612918788", "Karin_Alpha": None}
if PROFILE == "aco_pt":  # Karin_PicodraTech (2026-10-24): one ACD_Tex1 material 0x2A0CA5B0001..4 per 4096 atlas
    # (build_mod.py --model pt); Karin_Alpha (Body.010: blush/tear overlays, the only faces that use the atlas alpha) dropped
    ATLAS_OF = {"Body": "2889612984321", "Karin_Face": "2889612984321", "Karin_Alpha": None,                 # Skin_Face
                "Hair": "2889612984322", "Karin_Hair_Transparent": "2889612984322",                            # Hair_Head
                "ClothA_Blue": "2889612984323", "Costume": "2889612984323", "Karin_Costume": "2889612984323",  # Clothing_A
                "ClothB_Blue": "2889612984324", "Costume_1": "2889612984324", "Costume_Metalic": "2889612984324"}  # Clothing_B
rig = bpy.data.objects["NaoeRig"]
# face_rig.py poses the eyelid bones away from their (bind-offset) rest; the LOD normal transfer below reads the
# evaluated full mesh, so evaluate everything at the rest position (the stored vertices = what the GLB carries)
rig.data.pose_position = 'REST'
meshes = [o for o in bpy.data.objects if o.type == 'MESH' and o.parent == rig and not o.name.startswith("NaoeHeadRef")]
for o in [o for o in bpy.data.objects if o.name.startswith("NaoeHeadRef") or (o.type == 'MESH' and o not in meshes)]:
    bpy.data.objects.remove(o)

donor_mats = {}
def donor(mid):
    if mid not in donor_mats:
        m = bpy.data.materials.get(mid) or bpy.data.materials.new(mid)
        donor_mats[mid] = m
    return donor_mats[mid]
dropped = {}
for o in meshes:
    drop = set()
    for i, slot in enumerate(o.material_slots):
        src = slot.material.name.split(".")[0] if slot.material else None
        if src not in ATLAS_OF:
            raise SystemExit(f"unmapped material {src} on {o.name}")
        if ATLAS_OF[src] is None:
            drop.add(i)
            continue
        slot.material = donor(ATLAS_OF[src])
    if drop:
        bm = bmesh.new(); bm.from_mesh(o.data)
        faces = [f for f in bm.faces if f.material_index in drop]
        bmesh.ops.delete(bm, geom=faces, context='FACES')
        bm.to_mesh(o.data); bm.free()
        dropped[o.name] = len(faces)
print("EXPORT dropped faces", dropped)

# --keep-full <mesh,...>: those meshes (the face) are not decimated in the lower LODs
KEEP_FULL = argv[argv.index("--keep-full") + 1].split(",") if "--keep-full" in argv else []
KEEP_GROUP = "_keep_full"
for o in meshes:
    if o.name in KEEP_FULL:
        o.vertex_groups.new(name=KEEP_GROUP).add(list(range(len(o.data.vertices))), 1.0, 'REPLACE')
missing = set(KEEP_FULL) - {o.name for o in meshes}
if missing:
    raise SystemExit(f"--keep-full: no mesh {sorted(missing)}")

bpy.ops.object.select_all(action='DESELECT')
for o in meshes:
    o.select_set(True)
bpy.context.view_layer.objects.active = meshes[0]
bpy.ops.object.join()
karin = bpy.context.view_layer.objects.active
karin.name = "Karin"
me = karin.data
# merge duplicate material slots
bpy.ops.object.material_slot_remove_unused()
# vertex colour
for ca in list(me.color_attributes):
    me.color_attributes.remove(ca)
col = me.color_attributes.new("Color", 'BYTE_COLOR', 'CORNER')
for d in col.data:
    d.color = (1, 1, 1, 1)
# uv: keep only first
while len(me.uv_layers) > 1:
    me.uv_layers.remove(me.uv_layers[1])
me.uv_layers[0].name = "UVMap"
# triangulate
bm = bmesh.new(); bm.from_mesh(me)
bmesh.ops.triangulate(bm, faces=bm.faces[:])
bm.to_mesh(me); bm.free()

used = set(karin.vertex_groups.keys())
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode='EDIT')
eb = rig.data.edit_bones
keep = set()
for n in used:
    b = eb.get(n)
    while b is not None:
        keep.add(b.name); b = b.parent
for b in list(eb):
    if b.name not in keep:
        eb.remove(b)
bpy.ops.object.mode_set(mode='OBJECT')

report = {"bones": sorted(keep), "bone_count": len(keep), "lods": []}
base_faces = len(me.polygons)
for i, r in enumerate(ratios):
    obj = karin
    if r < 1.0:
        obj = karin.copy(); obj.data = karin.data.copy(); bpy.context.scene.collection.objects.link(obj)
        dm = obj.modifiers.new("dec", 'DECIMATE'); dm.ratio = r; dm.use_collapse_triangulate = True
        if KEEP_FULL:  # weight-1 vertices of the group are left out of the collapse
            dm.vertex_group = KEEP_GROUP; dm.invert_vertex_group = True
        # keep armature modifier last for evaluation order
        obj.modifiers.move(len(obj.modifiers) - 1, 0)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier="dec")
        # the collapse drops the authored (toon) custom normals: copy them back from the full mesh onto the kept face.
        # Without this the decimated Yasuke face showed nose/mouth shadow blotches in game (2026-10-07; 25 deg mean
        # error). Only the face: on thin two-sided hair cards the nearest-corner transfer picks the back side (dark).
        if KEEP_FULL:
            nt = obj.modifiers.new("nrm", 'DATA_TRANSFER'); nt.object = karin; nt.vertex_group = KEEP_GROUP
            nt.use_loop_data = True; nt.data_types_loops = {'CUSTOM_NORMAL'}; nt.loop_mapping = 'NEAREST_POLYNOR'
            obj.modifiers.move(len(obj.modifiers) - 1, 0)
            bpy.ops.object.modifier_apply(modifier="nrm")
    if obj is not karin and obj.vertex_groups.get(KEEP_GROUP):  # karin keeps it for the next LODs (a group
        obj.vertex_groups.remove(obj.vertex_groups[KEEP_GROUP])  # without a bone is not exported as a joint)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True); obj.select_set(True)
    bpy.context.view_layer.objects.active = rig
    path = os.path.join(out_dir, f"karin_lod{i}.glb")
    bpy.ops.export_scene.gltf(
        filepath=path, export_format='GLB', use_selection=True, export_yup=True, export_apply=False,
        export_texcoords=True, export_normals=True, export_tangents=True, export_materials='EXPORT',
        export_image_format='NONE', export_vertex_color='ACTIVE', export_all_vertex_colors=True,
        export_extras=True, export_skins=True, export_influence_nb=4, export_all_influences=False,
        export_def_bones=False, export_leaf_bone=False, export_morph=False, export_animations=False,
        export_rest_position_armature=True, export_cameras=False, export_lights=False)
    report["lods"].append({"file": path, "ratio": r, "faces": len(obj.data.polygons), "verts": len(obj.data.vertices)})
    if obj is not karin:
        bpy.data.objects.remove(obj)
json.dump(report, open(os.path.join(out_dir, "export_report.json"), "w"), indent=1)
print("EXPORT_LODS_OK", report["bone_count"], [(l["faces"], l["verts"]) for l in report["lods"]])
