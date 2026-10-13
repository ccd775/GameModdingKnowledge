# Write <run>/ue_config.json and the 4x4 helper textures used by ue/ue_import.py.
# Usage: python gen_ue_config.py <run_dir> <player_asset_list.txt>
import argparse, json, os, re, sys

_parser = argparse.ArgumentParser(description="Write <run>/ue_config.json and the 4x4 helper textures used by "
                                  "scripts/ue/ue_import.py (needs numpy and Pillow).")
_parser.add_argument("run_dir", help="build_pal.py run folder (textures/ is created or extended)")
_parser.add_argument("listing", help="PalExport 'list' output for Pal/Content/Pal/Model/Character/Player/ (one package file per line)")
_args = _parser.parse_args()
import numpy as np
from PIL import Image

RUN, LISTING = _args.run_dir, _args.listing
TEX = os.path.join(RUN, "textures")
os.makedirs(TEX, exist_ok=True)

def flat(name, rgba):
    a = np.zeros((4, 4, 4), np.uint8); a[:] = [int(round(c * 255)) for c in rgba]
    Image.fromarray(a, "RGBA").save(os.path.join(TEX, name + ".png"))
    return name + ".png"

# MetallicRoughnessOcclusionSpecular (R metal, G roughness, B occlusion, A spec) from vanilla means:
# body skin G .39, head .36, hair .63, outfit cloth .98 (B is cavity AO; ours is flat so 1).
helpers = {
    "T_Karin_FlatN": ((0.5, 0.5, 1.0, 1.0), False, True),
    "T_Karin_Black": ((0.0, 0.0, 0.0, 1.0), False, False),
    "T_Karin_SkinM": ((0.0, 0.40, 1.0, 1.0), False, False),
    "T_Karin_HairM": ((0.0, 0.60, 1.0, 1.0), False, False),
    "T_Karin_CostumeM": ((0.0, 0.85, 1.0, 1.0), False, False),
    "T_Karin_SkinSSS": ((0.69, 0.38, 0.31, 1.0), True, False),   # vanilla T_Player_Female_Body_SSS mean
}
textures = {}
for n, (rgba, srgb, normal) in helpers.items():
    textures[n] = {"file": flat(n, rgba), "srgb": srgb, "normal": normal}
for n, f in (("T_Karin_Body", "Karin_Body.png"), ("T_Karin_Face", "Karin_Face.png"), ("T_Karin_Hair", "Karin_Hair.png"),
             ("T_Karin_Costume", "Karin_Costume.png")):
    textures[n] = {"file": f, "srgb": True, "normal": False}

SKIN = "/Game/Pal/Material/Character/Common/MI_PalLit_HumanSkin"
HAIR = "/Game/Pal/Model/Character/Player/Hair/Hair001/MI_Player_Hair001"
CLOTH = "/Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/v01/MI_Player_Female_Outfit_OldCloth001_v01_M01"
skin_tex = {"MetallicRoughnessOcclusionSpecularTexture": "T_Karin_SkinM", "Normal Map": "T_Karin_FlatN",
            "Override Normal Map 1": "T_Karin_FlatN", "Override Normal Map 2": "T_Karin_FlatN",
            "Override Normal Mask 1": "T_Karin_Black", "Override Normal Mask 2": "T_Karin_Black",
            "Override Normal Mask 3": "T_Karin_Black", "BaseColor Mask": "T_Karin_Black", "Subsurface Texture": "T_Karin_SkinSSS"}
materials = {
    "MI_Karin_Skin": {"parent": SKIN, "textures": dict(skin_tex, **{"Base Texture": "T_Karin_Body"}), "scalars": {}},
    "MI_Karin_Face": {"parent": SKIN, "textures": dict(skin_tex, **{"Base Texture": "T_Karin_Face"}), "scalars": {}},
    "MI_Karin_Hair": {"parent": HAIR, "textures": {"Base Texture": "T_Karin_Hair", "MetallicRoughnessOcclusionSpecularTexture": "T_Karin_HairM",
                                                    "Normal Map": "T_Karin_FlatN", "BaseColor Mask": "T_Karin_Black"}, "scalars": {}},
    "MI_Karin_Costume": {"parent": CLOTH, "textures": {"Base Texture": "T_Karin_Costume", "MetallicRoughnessOcclusionSpecularTexture": "T_Karin_CostumeM",
                                                        "Normal Map": "T_Karin_FlatN", "BaseColor Mask": "T_Karin_Black"}, "scalars": {}},
}

lst = open(LISTING, encoding="utf-8", errors="ignore").read().splitlines()
def paths(rx):
    out = []
    for l in lst:
        m = re.match(r"^Pal/Content/(" + rx + r")\.uasset$", l.strip())
        if m: out.append("/Game/" + m.group(1))
    return sorted(out)
heads = paths(r"Pal/Model/Character/Player/Head/Head\d+/SK_Player_Female_Head\d+")
hairs = paths(r"Pal/Model/Character/Player/Hair/Hair\d+/SK_Player_Hair\d+")
cfg = {
    "textures": textures,
    "materials": materials,
    "slot_map": {},
    "hidden_material": "MI_Karin_Skin",
    "head_paths": heads,
    "hair_paths": hairs,
    # vanilla OldCloth001 socket; Karin's torso is ~0.85x as deep -> offset scaled
    "body_sockets": [{"name": "Socket_BackWeapon_R", "bone": "spine_03", "loc": [8.96 * 0.85, -20.18 * 0.85, 11.84 * 0.85],
                      "rot": [-90.0, 0.0, -170.0], "scale": [1, 1, 1]}],
}
json.dump(cfg, open(os.path.join(RUN, "ue_config.json"), "w", encoding="utf-8"), indent=1)
print("heads", len(heads), "hairs", len(hairs))
