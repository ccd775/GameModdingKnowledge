"""Machine paths of the Days Gone kit (new file for the portable kit; the project scripts had them written in).

DG_CACHE       local cache root, filled with DgExport (tools/dgx_run.ps1) on the build machine and copied over:
                 deacon_master_Skeleton.deacon_master_Skeleton.skel.json   DgExport skel of the game Skeleton
                 anim/raw/animj/BendGame/Content/Animation/Deacon/...      raw face mood / viseme / ref pose anims
                 ue/BendGame/Content/Characters/Deacon/parts/head/deacon_head_standard.uemodel   DgExport export ue
                 raw/BendGame/Content/Characters/Deacon/parts/head/mi_deacon_*.uasset          raw game MIs
                 looks/BendGame/Content/Characters/Deacon/looks/*.uasset   the 66 raw Deacon looks
DG_MODELS_DIR  source model root, holds Karin_Original/Karin(Clone).vrm

A missing variable stops the calling script with the variable's name; there is no fallback to a local path. The
functions only read the environment when called, so importing this module never fails.
"""
import os

SKEL_JSON = 'deacon_master_Skeleton.deacon_master_Skeleton.skel.json'
ANIM_DIR = ('anim', 'raw', 'animj', 'BendGame', 'Content', 'Animation', 'Deacon')
HEAD_UEMODEL = ('ue', 'BendGame', 'Content', 'Characters', 'Deacon', 'parts', 'head', 'deacon_head_standard.uemodel')
RAW_CONTENT = ('raw', 'BendGame', 'Content')
LOOKS_DIR = ('looks', 'BendGame', 'Content', 'Characters', 'Deacon', 'looks')
KARIN_VRM = ('Karin_Original', 'Karin(Clone).vrm')


def env(name, what):
    value = os.environ.get(name, '')
    if not value:
        raise SystemExit('Set %s to %s (see portable-kits/days-gone/README.md)' % (name, what))
    return value


def cache(*parts):
    return os.path.join(env('DG_CACHE', 'the local cache root (DgExport output and raw game packages)'), *parts)


def models(*parts):
    return os.path.join(env('DG_MODELS_DIR', 'the source model root (holds Karin_Original/Karin(Clone).vrm)'), *parts)


def skel_json():
    return cache(SKEL_JSON)


def anim_dir():
    return cache(*ANIM_DIR)


def head_uemodel():
    return cache(*HEAD_UEMODEL)


def raw_content():
    return cache(*RAW_CONTENT)


def looks_dir():
    return cache(*LOOKS_DIR)


def karin_vrm():
    return models(*KARIN_VRM)
