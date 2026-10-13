# Per-model build profiles for build_karin.py and its stages. "karin_original" is the reference profile: its values
# are the constants the released v6 build was made with, so it reproduces that build.
#
# Source conventions after source_prep.load(): meters, identity object transforms, VRM humanoid bone names
# ("Hips", "LeftUpperArm", ...), the face mesh named "Body" and the skin mesh "body_2", material slots renamed to the
# profile's UE slot names ("Karin_Face" / "Karin_Body" are the skin slots; everything else renders as cloth).
#
# Dynamics chains ("dyn"): each chain rides spare Base_skeleton bones (the RigidBody node is keyed by skeleton bone
# index, so only skeleton bones can be simulated; the parent is fixed by the skeleton):
#   head:     cloth_head_A_l_01..03, cloth_head_A_r_01..03, cloth_head_A_01..05, accessories_head_01_l/r
#   spine_03: cloth_spine_03_A_01..03, accessories_spine_03_01_l/r      spine_02: accessories_spine_02_01_l/r
#   pelvis:   cloth_pelvis_A_01..05, cloth_pelvis_A_l_01..05, cloth_pelvis_A_r_01..05, 23 accessories_pelvis_* singles,
#             thigh_sleeve_l/r -> calf_sleeve_l/r
#   limbs:    upperarm_sleeve_01..04_*, lowerarm_sleeve_01..04_*, accessories_lowerarm_*_01_*, thigh/calf_sleeve_01..04_*
# New-style chain keys: root (source bone), path (explicit source bones, default = deepest descendant path),
# subtree (vertices of the whole subtree, default False = path bones only), hosts, fracs (host joints along the chain,
# 0..1), rscale (collision radius scale), blend (fraction over which the chain takes over from the vertex's own
# weights before the first host joint), tune (dyn_tuning parameters).
import copy
import os

# Root of the source model folders (Karin_Original/, Karin_Y_BlenderSafe/, ...): environment variable SIFU_MODELS_DIR.
# Plain Python (no bpy): make_textures.py and package_release.py import this file too.
M = os.environ.get("SIFU_MODELS_DIR", "<SIFU_MODELS_DIR>")

# ---- tuning presets (dyn_tuning.apply); masses per host bone are filled by length ------------------------------------
T_TWIN = dict(freq=1.3, zeta=0.45, lin_damp=8.0, ang_damp=4.0, swing=40, swing_rest=30, twist=6,
              collide=["head", "neck_01", "spine_02", "spine_03", "upperarm_l", "upperarm_r"])
T_TAIL = dict(freq=1.5, zeta=0.45, lin_damp=8.0, ang_damp=4.0, swing=30, swing_rest=25, twist=5,
              collide=["pelvis", "spine_01"])
T_SIDE = dict(freq=2.0, zeta=0.5, lin_damp=8.0, ang_damp=4.0, swing=25, swing_rest=25, twist=5,
              collide=["head", "spine_03"])
T_PANEL = dict(freq=1.6, zeta=0.5, lin_damp=8.0, ang_damp=4.0, swing=35, swing_rest=30, twist=5,
               collide=["pelvis", "thigh_l", "thigh_r", "spine_01"])
T_CABLE = dict(freq=1.2, zeta=0.45, lin_damp=8.0, ang_damp=4.0, swing=35, swing_rest=30, twist=8,
               collide=["pelvis", "spine_01", "spine_02", "thigh_l", "thigh_r"])
T_RIBBON = dict(freq=1.4, zeta=0.45, lin_damp=8.0, ang_damp=4.0, swing=35, swing_rest=30, twist=8,
                collide=["pelvis", "spine_01", "thigh_l", "thigh_r"])


def _t(base, masses, **kw):
    t = dict(base, masses=masses, **kw)
    n = len(masses)
    t["swing"] = [base["swing"]] + [base["swing_rest"]] * (n - 1)
    del t["swing_rest"]
    return t


# ---- reference profile: Karin_Original (released v6) ------------------------------------------------------------------
KARIN_ORIGINAL = {
    "name": "karin_original",
    "src": f"{M}/Karin_Original/Karin(Clone).vrm",
    "asset_dir": "Karin",
    "pak": "pakchunk99-KarinOriginal_P",
    "head_m": 1.0508,
    "face_mesh": "Body",
    "skin_mesh": "body_2",
    "thigh_meshes": ["knee-socks"],
    "alpha_mat": "Karin_Alpha",
    "fold_prefix": [("Hair_", "head"), ("Ribbon_L", "head"), ("Ribbon_R", "head"), ("Ear_", "head"), ("Cheek", "head"),
                    ("Tail", "pelvis"), ("Skirt_", "pelvis"), ("Ribbon_camisole", "spine_03"), ("Ribbon_tops_", "spine_03"),
                    ("Ribbon_hand_L", "lowerarm_twist_04_l"), ("Ribbon_hand_R", "lowerarm_twist_04_r"),
                    ("Shoes_tag_L", "foot_l"), ("Shoes_tag_R", "foot_r")],
    "fold_ancestor": False,
    "torso_targets": ("body_2", "pullover", "underwear", "skirt", "Proxy_Skirt"),
    "cloth_chains": "default",   # cloth_stage.CHAINS (section split only)
    "skirt": "default",          # cloth_stage.SKIRT
    "dyn": "default",            # dyn_stage.CHAINS / dyn_tuning.CHAINS
}

# ---- PicodraTech outfit (jacket with hem panels, headphone cables, back ribbon) ----------------------------------------
_PANEL_HOSTS = {("A", "L"): "accessories_pelvis_01_l", ("B", "L"): "accessories_pelvis_02_l",
                ("C", "L"): "accessories_pelvis_03_l", ("D", "L"): "accessories_pelvis_04_l",
                ("A", "R"): "accessories_pelvis_01_r", ("B", "R"): "accessories_pelvis_02_r",
                ("C", "R"): "accessories_pelvis_03_r", ("D", "R"): "accessories_pelvis_04_r"}


def _picodra_dyn(N, twin_masses, tail_masses, twin_collide=()):
    """N: source bone names -- twin(S), side(S), tail, panel(X, S) -> 4-bone path, back -> 4-bone path, code(S),
    ribbon (root of the long back ribbon). S in L/R."""
    twin = _t(T_TWIN, twin_masses)
    twin["collide"] = twin["collide"] + list(twin_collide)
    dyn = []
    for S, s in (("L", "l"), ("R", "r")):
        dyn.append({"name": f"Hair_tail_{S}", "root": N["twin"](S), "hosts": [f"cloth_head_A_{s}_0{i}" for i in (1, 2, 3)],
                    "fracs": [0.0, 0.3, 0.62], "rscale": 0.55, "tune": twin})
    dyn.append({"name": "Tail", "root": N["tail"], "hosts": [f"cloth_pelvis_A_0{i}" for i in range(1, 6)],
                "fracs": [0.0, 0.2, 0.4, 0.6, 0.8], "rscale": 0.55, "tune": _t(T_TAIL, tail_masses)})
    for S, s in (("L", "l"), ("R", "r")):
        dyn.append({"name": f"Hair_side_{S}", "root": N["side"](S), "hosts": [f"accessories_head_01_{s}"], "fracs": [0.15],
                    "rscale": 0.6, "centers": [0.12, 0.75], "tune": _t(T_SIDE, [0.1])})
    # hem panels: one pendulum each, hinged at the waist; the subtree brings the pocket strings along
    for (X, S), host in _PANEL_HOSTS.items():
        path = N["panel"](X, S)
        dyn.append({"name": f"Outer{X}_{S}", "root": path[0], "path": path, "subtree": True, "hosts": [host],
                    "fracs": [0.25], "rscale": 0.35, "blend": 0.12, "tune": _t(T_PANEL, [0.3])})
    dyn.append({"name": "OuterB", "root": N["back"][0], "path": N["back"], "hosts": ["accessories_pelvis_01"],
                "fracs": [0.25], "rscale": 0.35, "blend": 0.12, "tune": _t(T_PANEL, [0.3])})
    for S, s in (("L", "l"), ("R", "r")):
        dyn.append({"name": f"Code_{S}", "root": N["code"](S), "hosts": [f"cloth_pelvis_A_{s}_0{i}" for i in range(1, 6)],
                    "fracs": [0.4, 0.52, 0.64, 0.76, 0.88], "rscale": 0.8, "blend": 0.15,
                    "tune": _t(T_CABLE, [0.08, 0.07, 0.06, 0.05, 0.04])})
    dyn.append({"name": "Back_Ribbon", "root": N["ribbon"], "subtree": True,
                "hosts": ["cloth_spine_03_A_01", "cloth_spine_03_A_02", "cloth_spine_03_A_03"],
                "fracs": [0.0, 0.3, 0.6], "rscale": 0.5, "blend": 0.05, "tune": _t(T_RIBBON, [0.15, 0.12, 0.1])})
    return dyn


# Karin_Original body/rig (canonical bone names) + PicodraTech outfit
OPT = {
    "name": "opt",
    "src": f"{M}/Karin_Original_PicodraTech/Karin_Original_PicodraTech_Optimized.blend",
    "asset_dir": "Karin_OPT",
    "pak": "pakchunk99-KarinOriginalPicodraTech_P",
    "head_m": 1.0508,
    "face_mesh": "Body",
    "skin_mesh": "body_2",
    "thigh_meshes": ["Socks"],
    "alpha_mat": "Karin_Alpha",
    "fold_prefix": [],
    "fold_ancestor": True,
    "torso_exclude": ("Body", "hair", "kemomimi", "tail", "Halo", "Head_Acc"),
    "materials": {"Karin_Face": "Karin_Face", "Karin_Body": "Karin_Body", "Karin_Hair": "Karin_Hair",
                  "Karin_Hair_Transparent": "Karin_Hair", "Karin_Costume": "Karin_ClothA", "ClothA_Pink": "Karin_ClothA",
                  "ClothA_Black": "Karin_ClothA", "ClothB_Pink": "Karin_ClothB", "Karin_Alpha": "Karin_Alpha"},
    "tex_dir": f"{M}/Karin_Original_PicodraTech/textures",
    "slots": {"Karin_Face": {"page": "atlas-00", "kind": "face"},
              "Karin_Body": {"page": "atlas-00", "kind": "skin"},
              "Karin_Hair": {"page": "atlas-01", "kind": "hair"},
              "Karin_ClothA": {"page": "atlas-02", "kind": "cloth"},
              "Karin_ClothB": {"page": "atlas-03", "kind": "cloth"}},
    "tex_files": {"color": "{page}-color-alpha.png"},
    "cull_alpha": 0.05,
    "cloth_chains": [],
    "skirt": None,
    "dyn": _picodra_dyn({"twin": lambda S: f"Hair_tail_{S}", "side": lambda S: f"Hair_side_{S}", "tail": "Tail",
                         "panel": lambda X, S: [f"Outer{X}_{S}", f"Outer{X}_{S}_001", f"Outer{X}_{S}_002", f"Outer{X}_{S}_003"],
                         "back": ["OuterB", "OuterB_001", "OuterB_002", "OuterB_003"],
                         "code": lambda S: f"Code_{S}", "ribbon": "Back_Ribbon_003"},
                        [0.25, 0.2, 0.15], [0.4, 0.3, 0.25, 0.2, 0.1]),
}

# newer Karin base (knee-long twin tails, big tail; ".L" bone names, VRM-merged meshes) + PicodraTech outfit
PT = {
    "name": "pt",
    "src": f"{M}/Karin_PicodraTech/Karin_PT_Unified_Atlas.blend",
    "asset_dir": "Karin_PT",
    "pak": "pakchunk99-KarinPicodraTech_P",
    "head_m": 1.0508,
    "drop_meshes": ["Body.010"],            # Karin_Alpha overlay only
    "mesh_renames": {"Body": "hair", "Body.009": "Body", "Body.003": "body_2", "Body.001": "ClothB", "Body.006": "ClothA",
                     "Body.002": "Costume", "Body.005": "HairRibbons", "Body.007": "Ornament_Metal", "Body.008": "Ornament"},
    "face_mesh": "Body",
    "skin_mesh": "body_2",
    "thigh_meshes": ["ClothA"],
    "alpha_mat": "Karin_Alpha",
    "fold_prefix": [],
    "fold_ancestor": True,
    "torso_exclude": ("Body", "hair", "HairRibbons", "Ornament_Metal", "Ornament"),
    "materials": {"Karin_Face": "Karin_Face", "Body": "Karin_Body", "Karin_Alpha": "Karin_Alpha",
                  "Hair": "Karin_Hair", "Karin_Hair_Transparent": "Karin_Hair",
                  "ClothA_Blue": "Karin_ClothA", "Costume": "Karin_ClothA", "Karin_Costume": "Karin_ClothA",
                  "ClothB_Blue": "Karin_ClothB", "Costume_1": "Karin_ClothB", "Costume_Metalic": "Karin_ClothB",
                  "Dots Stroke": "Karin_ClothB"},
    "tex_dir": f"{M}/Karin_PicodraTech/textures",
    "slots": {"Karin_Face": {"page": "Skin_Face", "kind": "face"},
              "Karin_Body": {"page": "Skin_Face", "kind": "skin"},
              "Karin_Hair": {"page": "Hair_Head", "kind": "hair"},
              "Karin_ClothA": {"page": "Clothing_A", "kind": "cloth"},
              "Karin_ClothB": {"page": "Clothing_B_Accessories", "kind": "cloth"}},
    "tex_files": {"color": "Karin_PT_Atlas_{page}_ColorAlpha_4096.png"},
    "cull_alpha": 0.05,
    "cloth_chains": [],
    "skirt": None,
    "dyn": _picodra_dyn({"twin": lambda S: f"Hair_Tail.{S}", "side": lambda S: f"Hair_Side_1.{S}", "tail": "Tail_1",
                         "panel": lambda X, S: [f"Outer{X}.{S}", f"Outer{X}_2.{S}", f"Outer{X}_3.{S}", f"Outer{X}_4.{S}"],
                         "back": ["OuterB", "OuterB_2", "OuterB_3", "OuterB_4"],
                         "code": lambda S: f"Code.{S}", "ribbon": "Back_Ribbon_4"},
                        [0.4, 0.3, 0.25], [0.6, 0.5, 0.4, 0.3, 0.2], twin_collide=("pelvis", "spine_01", "thigh_l", "thigh_r")),
}

def _base_dyn(N, twin_masses=(0.4, 0.3, 0.25), tail_masses=(0.6, 0.5, 0.4, 0.3, 0.2)):
    """Twin tails, fox tail and side hair of the newer Karin base (knee-long twin tails, big tail)."""
    twin = _t(T_TWIN, list(twin_masses))
    twin["collide"] = twin["collide"] + ["pelvis", "spine_01", "thigh_l", "thigh_r"]
    dyn = []
    for S, s in (("L", "l"), ("R", "r")):
        dyn.append({"name": f"Hair_tail_{S}", "root": N["twin"](S), "hosts": [f"cloth_head_A_{s}_0{i}" for i in (1, 2, 3)],
                    "fracs": [0.0, 0.3, 0.62], "rscale": 0.55, "tune": twin})
    dyn.append({"name": "Tail", "root": N["tail"], "hosts": [f"cloth_pelvis_A_0{i}" for i in range(1, 6)],
                "fracs": [0.0, 0.2, 0.4, 0.6, 0.8], "rscale": 0.55, "tune": _t(T_TAIL, list(tail_masses))})
    for S, s in (("L", "l"), ("R", "r")):
        dyn.append({"name": f"Hair_side_{S}", "root": N["side"](S), "hosts": [f"accessories_head_01_{s}"], "fracs": [0.15],
                    "rscale": 0.6, "centers": [0.12, 0.75], "tune": _t(T_SIDE, [0.1])})
    return dyn


T_STRING = dict(freq=0.6, zeta=0.45, lin_damp=8.0, ang_damp=4.0, swing=40, swing_rest=30, twist=8,
                collide=["pelvis", "thigh_l", "thigh_r"])
T_SLEEVE = dict(freq=1.2, zeta=0.5, lin_damp=8.0, ang_damp=4.0, swing=45, swing_rest=30, twist=5,
                collide=["pelvis", "spine_01", "spine_02", "thigh_l", "thigh_r"])
T_LONGPANEL = dict(freq=1.2, zeta=0.5, lin_damp=8.0, ang_damp=4.0, swing=30, swing_rest=25, twist=5,
                   collide=["pelvis", "spine_01", "thigh_l", "thigh_r", "calf_l", "calf_r"])

# newer Karin base + urban jacket worn at the elbows, goggles, shorts
UMB = {
    "name": "umb",
    "src": f"{M}/Karin_Umbrella/Karin_Umbrella_Unified_Atlas.blend",
    "asset_dir": "Karin_UMB",
    "hang": ["himo_root.L", "himo_root.R"],
    "pak": "pakchunk99-KarinUmbrella_P",
    "head_m": 1.0508,
    "mesh_renames": {"Body_base": "body_2"},
    "face_mesh": "Body",
    "skin_mesh": "body_2",
    "thigh_meshes": ["Socks"],
    "alpha_mat": "Karin_Alpha",
    "fold_prefix": [],
    "fold_ancestor": True,
    "torso_exclude": ("Body", "Hair_Main", "Hair_Accessories", "kemomimi", "tail", "Costume_Ornaments",
                      "Reve_urbaine_MA2_goggles"),
    "materials": {"Karin_Face": "Karin_Face", "Karin_Alpha": "Karin_Alpha", "Body": "Karin_Body",
                  "Hair": "Karin_Hair", "Karin_Hair": "Karin_Hair", "Karin_Hair_Transparent": "Karin_Hair",
                  "Karin_Costume": "Karin_Hair", "Costume": "Karin_Hair", "Costume_Metalic": "Karin_Hair",
                  "base_color_MA1_arctic_": "Karin_Jacket", "base_color_MA1_metal_arctic_": "Karin_Jacket",
                  "base_color_MA1_sakura_": "Karin_Jacket",
                  "base_color_MA2_alfa_arctic_": "Karin_Gear", "base_color_MA2_warning_red_": "Karin_Gear",
                  "Black_Metal": "Karin_Gear", "Mat_Acc_Cord": "Karin_Gear", "Mat_Acc_Leather": "Karin_Gear",
                  "Mat_Underwear_Cloth": "Karin_Gear", "Mat_Underwear_Cord": "Karin_Gear", "Mat_UnderwearBelt": "Karin_Gear",
                  "Mat_UnderwearMetal": "Karin_Gear", "Pants_and_Others": "Karin_Gear", "Plastic": "Karin_Gear",
                  "Plastic_White": "Karin_Gear", "ST2_Orange_03": "Karin_Gear", "Tops_and_Socks_White": "Karin_Gear"},
    "tex_dir": f"{M}/Karin_Umbrella/textures",
    "slots": {"Karin_Face": {"page": "Skin_Face", "kind": "face"},
              "Karin_Body": {"page": "Skin_Face", "kind": "skin"},
              "Karin_Hair": {"page": "Hair_Accessories", "kind": "hair"},
              "Karin_Jacket": {"page": "Urban_Jacket", "kind": "cloth"},
              "Karin_Gear": {"page": "Gear_Clothing", "kind": "cloth"}},
    "tex_files": {"color": "Karin_Umbrella_Atlas_{page}_ColorAlpha_4096.png"},
    "cull_alpha": 0.05,
    "cloth_chains": [],
    "skirt": None,
    "dyn": _base_dyn({"twin": lambda S: f"Hair_tail.{S}", "side": lambda S: f"Hair_side.{S}", "tail": "Tail_1"}) + [
        # strings hanging from the jacket sleeves at the elbows
        {"name": f"himo_{S}", "root": f"himo_root.{S}", "hosts": [f"upperarm_sleeve_01_{s}"], "fracs": [0.05],
         "rscale": 0.6, "blend": 0.05, "tune": _t(T_STRING, [0.05])}
        for S, s in (("L", "l"), ("R", "r"))
    ],
}

# newer Karin base + Tsukiyonomai (asymmetric kimono: long right sleeve, long side/back panels, loincloth, obi ribbons).
# The kunai props (left hand, held in the mouth) are dropped: barehanded fists and the facial animation clip them.
Y = {
    "name": "y",
    "src": f"{M}/Karin_Y_BlenderSafe/Karin_Y_GeneralWorkflow.blend",
    "asset_dir": "Karin_Y",
    "hang": ["TY_Arm_001", "TY_ArmStrap_004_2"],
    "pak": "pakchunk99-KarinY_P",
    "head_m": 1.0508,
    "drop_meshes": ["Kunai_Hand_L", "Kunai_Head"],
    "mesh_renames": {"Body_base": "body_2"},
    "face_mesh": "Body",
    "skin_mesh": "body_2",
    "thigh_meshes": ["Ty_Body_Stocking"],
    "alpha_mat": "Karin_Alpha",
    "fold_prefix": [],
    "fold_ancestor": True,
    "torso_exclude": ("Body", "Hair", "hair", "kemomimi", "tail", "Costume_Ornaments", "Ty_Hair_Stick", "Ty_Mask"),
    "mesh_materials": {"Body": {"Atlas_SkinFace_Opaque": "Karin_Face", "Atlas_SkinFace_Blend": "Karin_Alpha"}},
    "materials": {"Atlas_SkinFace_Opaque": "Karin_Body", "Atlas_SkinFace_Blend": "Karin_Body",
                  "Atlas_HairCostume_Opaque": "Karin_Hair", "Atlas_HairCostume_Blend": "Karin_Hair",
                  "Atlas_ClothUV123_Blend": "Karin_Cloth123", "Atlas_ClothUV123_Opaque": "Karin_Cloth123",
                  "Atlas_ClothUV4567_Blend": "Karin_Cloth4567", "Atlas_ClothUV4567_Opaque": "Karin_Cloth4567",
                  "Atlas_AccentsProps_Opaque": "Karin_Accents", "Atlas_AccentsProps_Blend": "Karin_Accents"},
    "tex_dir": f"{M}/Karin_Y_BlenderSafe/textures",
    "slots": {"Karin_Face": {"page": "SkinFace", "kind": "face"},
              "Karin_Body": {"page": "SkinFace", "kind": "skin"},
              "Karin_Hair": {"page": "HairCostume", "kind": "hair"},
              "Karin_Cloth123": {"page": "ClothUV123", "kind": "cloth"},
              "Karin_Cloth4567": {"page": "ClothUV4567", "kind": "cloth"},
              "Karin_Accents": {"page": "AccentsProps", "kind": "cloth"}},
    "tex_files": {"color": "Atlas_{page}_BaseColor.png"},
    "cull_alpha": 0.05,
    "cloth_chains": [],
    "skirt": None,
    "dyn": _base_dyn({"twin": lambda S: f"Hair_tail_{S}", "side": lambda S: f"Hair_side_{S}", "tail": "Tail"}) + [
        # long right sleeve hanging from the forearm (main body, inner flap, long strap)
        {"name": "Sleeve", "root": "TY_Arm", "subtree": True, "exclude_subtrees": ["TY_ArmStrap"],
         "path": ["TY_Arm", "TY_Arm_001", "TY_Arm_002", "TY_Arm_003", "TY_Arm_008", "TY_Arm_009", "TY_Arm_010",
                  "TY_Arm_013_1", "TY_Arm_013_2"],
         "hosts": ["lowerarm_sleeve_01_r"], "fracs": [0.04], "rscale": 0.12, "blend": 0.04, "tune": _t(T_SLEEVE, [0.6])},
        {"name": "Sleeve_strap", "root": "TY_ArmStrap_004_1", "subtree": True, "hosts": ["lowerarm_sleeve_03_r"],
         "fracs": [0.05], "rscale": 0.4, "blend": 0.05, "tune": _t(T_SLEEVE, [0.2])},
        # long left back panel from the chest to the ankle
        {"name": "OuterSide", "root": "Ty_OuterSide_001", "subtree": True,
         "path": ["Ty_OuterSide_001", "Ty_OuterSide_002_1", "Ty_OuterSide_002_2", "Ty_OuterSide_002_3", "Ty_OuterSide_002_4",
                  "Ty_OuterSide_002_5", "TY_Arm_011", "TY_Arm_012", "TY_Arm_013", "TY_Arm_013_1_001_1", "TY_Arm_013_1_001_2"],
         "hosts": ["cloth_spine_03_A_01", "cloth_spine_03_A_02", "cloth_spine_03_A_03"], "fracs": [0.15, 0.42, 0.7],
         "rscale": 0.35, "blend": 0.1, "tune": _t(T_LONGPANEL, [0.4, 0.3, 0.2])},
        # right side panels from the hip
        {"name": "Cloth_001", "root": "Ty_Cloth_001_1", "subtree": True, "hosts": [f"cloth_pelvis_A_r_0{i}" for i in (1, 2, 3)],
         "fracs": [0.0, 0.3, 0.6], "rscale": 0.35, "blend": 0.02, "tune": _t(T_LONGPANEL, [0.3, 0.25, 0.2])},
        {"name": "Cloth_002", "root": "Ty_Cloth_002_1", "subtree": True, "hosts": [f"cloth_pelvis_A_l_0{i}" for i in (1, 2)],
         "fracs": [0.0, 0.5], "rscale": 0.35, "blend": 0.02, "tune": _t(T_LONGPANEL, [0.2, 0.15])},
        # loincloth flaps
        {"name": "FCloth", "root": "Ty_FCloth_001", "subtree": True, "hosts": ["accessories_pelvis_01"], "fracs": [0.1],
         "rscale": 0.35, "blend": 0.08, "tune": _t(T_PANEL, [0.2])},
        {"name": "BCloth", "root": "Ty_BCloth_001", "subtree": True, "hosts": ["accessories_pelvis_02"], "fracs": [0.1],
         "rscale": 0.35, "blend": 0.08, "tune": _t(T_PANEL, [0.2])},
        # obi ribbons (front right)
        {"name": "Obi_Ribbons", "root": "Ty_Ribbon_006", "subtree": True, "hosts": ["accessories_pelvis_01_r"], "fracs": [0.05],
         "rscale": 0.35, "blend": 0.05, "tune": _t(T_RIBBON, [0.15])},
        {"name": "Obi_Ribbons2", "root": "Ty_Ribbon", "subtree": True, "hosts": ["accessories_pelvis_02_r"], "fracs": [0.05],
         "rscale": 0.35, "blend": 0.05, "tune": _t(T_RIBBON, [0.1])},
    ],
}

PROFILES = {p["name"]: p for p in (KARIN_ORIGINAL, OPT, PT, UMB, Y)}
ACTIVE = KARIN_ORIGINAL


def activate(name):
    global ACTIVE
    ACTIVE = copy.deepcopy(PROFILES[name or "karin_original"])
    return ACTIVE


def get(key, default=None):
    return ACTIVE.get(key, default)
