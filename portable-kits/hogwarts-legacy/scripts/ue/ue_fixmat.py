# ue_fixmat.py — re-assign the host MIs to every imported mesh (M + F configs) without re-importing.
# Configs: HL_UE_BUILD_CONFIGS (paths joined by os.pathsep), else <HL_WORK>/ue_build_m.json and ue_build_f.json.
import unreal, json, os
eal = unreal.EditorAssetLibrary
def log(*a): unreal.log_warning('[HLK] ' + ' '.join(str(x) for x in a))
def config_paths():
    if os.environ.get('HL_UE_BUILD_CONFIGS'): return os.environ['HL_UE_BUILD_CONFIGS'].split(os.pathsep)
    if os.environ.get('HL_WORK'): return [os.path.join(os.environ['HL_WORK'], n) for n in ('ue_build_m.json', 'ue_build_f.json')]
    raise RuntimeError('set HL_UE_BUILD_CONFIGS or HL_WORK')
for cfgp in config_paths():
    cfg = json.load(open(cfgp))
    MIS = {k: unreal.load_asset(v) for k, v in cfg['material_instances'].items()}
    for m in cfg['meshes']:
        for p in m['paths']:
            mesh = unreal.load_asset(p)
            if mesh is None: log('MISSING', p); continue
            mats = []
            for s in mesh.get_editor_property('materials'):
                slot = str(s.get_editor_property('material_slot_name'))
                s.set_editor_property('material_interface', MIS.get(slot) or MIS['Empty'])
                mats.append(s)
            mesh.set_editor_property('materials', mats)
            eal.save_loaded_asset(mesh, only_if_is_dirty=False)
            got = [(str(s.get_editor_property('material_slot_name')), (s.get_editor_property('material_interface') or unreal.Object()).get_name()) for s in unreal.load_asset(p).get_editor_property('materials')]
            log('mat', p.rsplit('/', 1)[1], got)
log('FIXMAT DONE')
