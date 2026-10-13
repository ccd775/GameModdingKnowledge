# Shared helpers for the Palworld Karin pipeline (Blender 4.2 background).
import bpy, sys, os
# Machine paths come from the environment (unset: a <PAL_...> placeholder, so loading fails with file-not-found):
#   PAL_BLENDER_ADDONS  folder holding io_scene_ueformat/, used only when the UEFormat add-on cannot be enabled by name
#   PAL_CACHE           PalExport "export ue" output folder (it contains Pal/Content/Pal/Model/Character/Player/...)
#   PAL_SOURCE_VRM      the source VRM (Karin(Clone).vrm in the Karin case)
ADDONS = os.environ.get("PAL_BLENDER_ADDONS", "<PAL_BLENDER_ADDONS>")
CACHE_UE = os.path.join(os.environ.get("PAL_CACHE", "<PAL_CACHE>"), r"Pal\Content\Pal\Model\Character\Player")
KARIN_VRM = os.environ.get("PAL_SOURCE_VRM", "<PAL_SOURCE_VRM>")

def enable_ueformat():
    import addon_utils
    if addon_utils.enable("io_scene_ueformat", default_set=True): return
    if ADDONS not in sys.path:
        sys.path.insert(0, ADDONS)
    import io_scene_ueformat
    try:
        io_scene_ueformat.register()
    except ValueError:
        pass  # already registered

def import_uemodel(path, scale=1.0, morphs=False):
    s = bpy.context.scene.uf_settings
    s.scale_factor = scale
    s.import_sockets = False
    s.import_morph_targets = morphs
    before = set(bpy.data.objects)
    bpy.ops.uf.import_uemodel(filepath=path, files=[{"name": os.path.basename(path)}], directory=os.path.dirname(path))
    return [o for o in bpy.data.objects if o not in before]
