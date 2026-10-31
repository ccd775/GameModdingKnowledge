# UE 5.7 editor Python: hidden stand-ins under the cutscene groom asset names (wrong class -> GroomComponents get no
# asset), explicitly saved.
import unreal
L = lambda *a: unreal.log("[PBZ] " + " ".join(str(x) for x in a))
eal = unreal.EditorAssetLibrary
H, Y = "/HuaShira/Characters/Hero/Hero_Hun", "/HuaShira/Characters/Hero/Young_Hun"
unreal.AssetRegistryHelpers.get_asset_registry().search_all_assets(True)   # headless runs start before the scan ends
GROOMS = {Y + "/SkinParts/Hun_young_Hair": ["/Game/PBZContent/Characters/Hero/Hun_Young/Mesh/V02/Hair/" + n for n in
              ("Hun_Young_Brow", "Hun_Young_Lash", "HunYoung_Hair_A", "HunYoung_Hair_B", "HunYoung_Hair_Bangs", "HunYoung_Hair_C", "HunYoung_Hair_Tails")],
          H + "/SkinParts/Hun_Cloth": ["/Game/PBZContent/Characters/Hero/Hun_New_V1/Mesh/" + n for n in
              ("Hun_Brow_V01", "Hun_Lash_V01", "Normal_Hair_Bangs", "Normal_Hair_End", "Normal_Hair_Main_Top", "Normal_Hair_Ponytail",
               "Normal_Hair_Sideburn", "Normal_Hair_Top_Hairline")]}
for src, dsts in GROOMS.items():
    for d in dsts:
        if eal.does_asset_exist(d): eal.delete_asset(d)
        a = eal.duplicate_asset(src, d)
        ok = eal.save_asset(d, only_if_is_dirty=False)
        L("groom stand-in", d, a is not None, ok)
L("GROOMS_OK")
