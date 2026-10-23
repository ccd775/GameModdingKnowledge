"""Machine paths of the Witcher 3 kit (new file for the portable kit; the project scripts had them written in).

W3_GAME_DIR    game install folder (holds bin\\x64_dx12 and content\\content0\\bundles)
W3_WORK        work root outside any synced folder, filled by tools/prepare.ps1:
                 uncook\\        vanilla extracts (man_base.w2rig, Geralt meshes / w3fac / half-tail dyng, movement anims)
                 extract_items\\ every vanilla items\\bodyparts\\geralt_items template
                 scratch\\       bundle listing all_bundles.tsv, item JSONs, build logs and report
                 build\\         depot\\ (Blender output), templates\\, stage_m1\\, mods\\<ModName>\\content
                 blend\\         karin_fit.blend
                 karin_src\\     textures\\*.png written by karin_build.py
                 tools\\wk7\\     WolvenKit 7 CLI copy
W3_SOURCE_FBX  source model: an FBX of the VRM that Blender's FBX importer reads cleanly
               (the project used Karin(Clone)_BlenderSafe.fbx)
W3_ADDON_MODULE  optional, Blender module name of the Witcher3-Blender-Tools add-on
               (default bl_ext.user_default.witcher3_tools = installed as a Blender 4.2+ extension)

A missing variable stops the calling script with the variable's name; there is no fallback to a local path. The
functions only read the environment when called, so importing this module never fails.
"""
import os

ADDON_MODULE_DEFAULT = 'bl_ext.user_default.witcher3_tools'


def env(name, what):
    value = os.environ.get(name, '')
    if not value:
        raise SystemExit('Set %s to %s (see portable-kits/the-witcher-3/README.md)' % (name, what))
    return value


def game(*parts):
    return os.path.join(env('W3_GAME_DIR', 'the game install folder (holds content\\content0\\bundles)'), *parts)


def work(*parts):
    return os.path.join(env('W3_WORK', 'the work root filled by tools/prepare.ps1'), *parts)


def work_dir(*parts):
    """work() with a trailing separator (the add-on and karin_build.py join depot paths onto it)."""
    return os.path.join(work(*parts), '')


def source_fbx():
    return env('W3_SOURCE_FBX', 'the source model FBX (e.g. Karin(Clone)_BlenderSafe.fbx)')


def addon_module():
    return os.environ.get('W3_ADDON_MODULE') or ADDON_MODULE_DEFAULT


def wolvenkit_cli():
    return work('tools', 'wk7', 'WolvenKit.CLI.exe')
