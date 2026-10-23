# ue_import.py — run inside UE 4.27: UE4Editor-Cmd Phoenix.uproject -run=pythonscript -script=<this>
# Builds stub references (skeleton, physics assets, master material, MIs) and imports the Karin meshes/textures
# at the vanilla Hogwarts Legacy package paths. Config: the file named by HL_UE_BUILD (build_mod.py import sets it to
# <work>/ue_build.json), else <HL_WORK>/ue_build.json.
import unreal, json, os

def config_path():
    if os.environ.get('HL_UE_BUILD'): return os.environ['HL_UE_BUILD']
    if os.environ.get('HL_WORK'): return os.path.join(os.environ['HL_WORK'], 'ue_build.json')
    raise RuntimeError('set HL_UE_BUILD (path of ue_build.json) or HL_WORK')
cfg = json.load(open(config_path()))
FIT = cfg['fit_dir']; TEX = cfg['tex_dir']
at = unreal.AssetToolsHelpers.get_asset_tools()
eal = unreal.EditorAssetLibrary
def log(*a): unreal.log_warning('[HLK] ' + ' '.join(str(x) for x in a))

def run_import(filename, dest_path, dest_name, options=None):
    t = unreal.AssetImportTask()
    t.set_editor_property('filename', filename); t.set_editor_property('destination_path', dest_path)
    t.set_editor_property('destination_name', dest_name); t.set_editor_property('automated', True)
    t.set_editor_property('replace_existing', True); t.set_editor_property('save', True)
    if options is not None: t.set_editor_property('options', options)
    at.import_asset_tasks([t])
    paths = list(t.get_editor_property('imported_object_paths'))
    log('imported', filename, '->', paths)
    return paths

def fbx_ui(skeleton=None, physics=False, morphs=False):
    o = unreal.FbxImportUI()
    o.set_editor_property('import_mesh', True); o.set_editor_property('import_as_skeletal', True)
    o.set_editor_property('mesh_type_to_import', unreal.FBXImportType.FBXIT_SKELETAL_MESH)
    o.set_editor_property('import_materials', False); o.set_editor_property('import_textures', False)
    o.set_editor_property('import_animations', False); o.set_editor_property('create_physics_asset', physics)
    if skeleton is not None: o.set_editor_property('skeleton', skeleton)
    d = o.get_editor_property('skeletal_mesh_import_data')
    d.set_editor_property('import_morph_targets', morphs)
    d.set_editor_property('normal_import_method', unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS)
    d.set_editor_property('normal_generation_method', unreal.FBXNormalGenerationMethod.MIKK_T_SPACE)
    d.set_editor_property('update_skeleton_reference_pose', False)
    d.set_editor_property('use_t0_as_ref_pose', False)
    d.set_editor_property('import_meshes_in_bone_hierarchy', True)
    d.set_editor_property('convert_scene', True); d.set_editor_property('force_front_x_axis', False)
    d.set_editor_property('convert_scene_unit', False)
    return o

def ensure_dir(p):
    if not eal.does_directory_exist(p): eal.make_directory(p)

# ---------------------------------------------------------------- stubs: skeleton + physics assets
SKEL = '/Game/RiggedObjects/Characters/Biped_Skeleton'
if not eal.does_asset_exist(SKEL):
    run_import(FIT + '/Skeleton.fbx', '/Game/_Stub', 'SkelProxy', fbx_ui(physics=True))
    ensure_dir('/Game/RiggedObjects/Characters')
    eal.rename_asset('/Game/_Stub/SkelProxy_Skeleton', SKEL)
    eal.rename_asset('/Game/_Stub/SkelProxy_PhysicsAsset', '/Game/RiggedObjects/Characters/Biped_PhysicsAsset')
    eal.duplicate_asset('/Game/RiggedObjects/Characters/Biped_PhysicsAsset', '/Game/RiggedObjects/Characters/SK_Biped_Physics_Shadows')
skeleton = unreal.load_asset(SKEL)
PA = '/Game/RiggedObjects/Characters/Biped_PhysicsAsset'
for dst in (PA, '/Game/RiggedObjects/Characters/SK_Biped_Physics_Shadows'):
    if not eal.does_asset_exist(dst):  # stub only (not packaged): any physics asset at the vanilla path
        src = unreal.load_asset('/Engine/Tutorial/SubEditors/TutorialAssets/Character/TutorialTPP_PhysicsAsset.TutorialTPP_PhysicsAsset')
        log('phys stub', dst, eal.duplicate_loaded_asset(src, dst))
phys = unreal.load_asset('/Game/RiggedObjects/Characters/Biped_PhysicsAsset')
shadow = unreal.load_asset('/Game/RiggedObjects/Characters/SK_Biped_Physics_Shadows')

# ---------------------------------------------------------------- stubs: master material + material instances
MM = '/Game/RiggedObjects/MasterMaterials/MM_Prop'
if not eal.does_asset_exist(MM):
    ensure_dir('/Game/RiggedObjects/MasterMaterials')
    at.create_asset('MM_Prop', '/Game/RiggedObjects/MasterMaterials', unreal.Material, unreal.MaterialFactoryNew())
mm = unreal.load_asset(MM)
MIS = {}
for slot, path in cfg['material_instances'].items():
    if not eal.does_asset_exist(path):
        folder, name = path.rsplit('/', 1); ensure_dir(folder)
        at.create_asset(name, folder, unreal.MaterialInstanceConstant, unreal.MaterialInstanceConstantFactoryNew())
    mi = unreal.load_asset(path); mi.set_editor_property('parent', mm); eal.save_loaded_asset(mi)
    MIS[slot] = mi

# ---------------------------------------------------------------- textures (real content)
for t in cfg['textures']:
    folder, name = t['path'].rsplit('/', 1); ensure_dir(folder)
    run_import(TEX + '/' + t['src'], folder, name)
    tex = unreal.load_asset(t['path'])
    kind = t['kind']
    if kind == 'D':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_BC7)
        tex.set_editor_property('srgb', True); tex.set_editor_property('compression_no_alpha', not t.get('alpha', False))
        tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    elif kind == 'N':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_NORMALMAP)
        tex.set_editor_property('srgb', False); tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER_NORMAL_MAP)
    elif kind == 'MRO':
        tex.set_editor_property('compression_settings', unreal.TextureCompressionSettings.TC_MASKS)
        tex.set_editor_property('srgb', False); tex.set_editor_property('lod_group', unreal.TextureGroup.TEXTUREGROUP_CHARACTER_SPECULAR)
    eal.save_loaded_asset(tex)

# ---------------------------------------------------------------- skeletal meshes
def set_materials(mesh, physics=False):
    # array elements come back as struct copies: modify each and write a new list back
    mats = []
    for m in mesh.get_editor_property('materials'):
        slot = str(m.get_editor_property('material_slot_name'))
        m.set_editor_property('material_interface', MIS.get(slot) or MIS['Empty'])
        mats.append(m)
    mesh.set_editor_property('materials', mats)
    log('materials', mesh.get_name(), [(str(m.get_editor_property('material_slot_name')), m.get_editor_property('material_interface').get_name()) for m in mesh.get_editor_property('materials')])
    if physics:
        mesh.set_editor_property('physics_asset', phys)
        try: mesh.set_editor_property('shadow_physics_asset', shadow)
        except Exception as e: log('no shadow_physics_asset', e)
    mesh.set_editor_property('positive_bounds_extension', unreal.Vector(20, 20, 20))
    mesh.set_editor_property('negative_bounds_extension', unreal.Vector(20, 20, 20))
    eal.save_loaded_asset(mesh)

# ---------------------------------------------------------------- Karin skeleton (shipped): HL bones + Karin's dynamic chains.
# Pieces with an AnimClass copy the body pose by bone name and need every mesh bone in their skeleton.
KSKEL = cfg.get('karin_skeleton')
karin_skel = None
if KSKEL:
    for m in cfg['meshes']:  # meshes bound to the old skeleton go first so it can be replaced
        if m.get('skeleton') == 'karin':
            for p in m['paths']:
                if eal.does_asset_exist(p): eal.delete_asset(p)
    kfolder, kname = KSKEL.rsplit('/', 1)
    if eal.does_directory_exist(kfolder): eal.delete_directory(kfolder)
    ensure_dir(kfolder)
    run_import(FIT + '/Skeleton.fbx', kfolder, kname + 'Proxy', fbx_ui())
    log('karin skeleton rename', eal.rename_asset(kfolder + '/' + kname + 'Proxy_Skeleton', KSKEL))
    eal.delete_asset(kfolder + '/' + kname + 'Proxy')
    karin_skel = unreal.load_asset(KSKEL)
    log('karin skeleton', karin_skel)

for m in cfg['meshes']:
    paths = m['paths']; first = paths[0]
    folder, name = first.rsplit('/', 1); ensure_dir(folder)
    if eal.does_asset_exist(first): eal.delete_asset(first)  # a reimport keeps the asset's old import settings (e.g. no morphs)
    run_import(FIT + '/' + m['fbx'], folder, name, fbx_ui(skeleton=karin_skel if m.get('skeleton') == 'karin' else skeleton, morphs=m.get('morphs', False)))
    if m.get('morphs'): log('morphs', first, len(unreal.load_asset(first).get_all_morph_target_names()))
    mesh = unreal.load_asset(first)
    if mesh is None: log('IMPORT FAILED', first); continue
    set_materials(mesh, m.get('physics', False))
    for p in paths[1:]:
        f2 = p.rsplit('/', 1)[0]; ensure_dir(f2)
        if eal.does_asset_exist(p): eal.delete_asset(p)
        eal.duplicate_asset(first, p)
    log('mesh done', paths)

# ---------------------------------------------------------------- anim blueprints: copy the body pose + AnimDynamics chains
if cfg.get('abps'):
    nodes = json.load(open(cfg['dyn_nodes']))
    copy_pose = json.dumps({'bUseAttachedParent': True, 'bCopyCurves': True})
    for a in cfg['abps']:
        if eal.does_asset_exist(a['path']): eal.delete_asset(a['path'])
        abp = unreal.HLKToolsLibrary.create_dynamics_anim_blueprint(a['path'], karin_skel, copy_pose, json.dumps(nodes.get(a['part'], [])))
        log('abp', a['path'], abp is not None, len(nodes.get(a['part'], [])), 'nodes', eal.save_loaded_asset(abp) if abp else 'FAILED')

eal.save_directory('/Game', only_if_is_dirty=False, recursive=True)
log('ALL DONE')
