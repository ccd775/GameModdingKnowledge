# 材质与贴图

## 1. 母材质与只改第 0 层

- 材质实例挂在游戏的材质实例下（在内容工程里是同路径的占位，cook 后游戏用自己的原件）：皮肤和脸用
  `/Game/PBZContent/Characters/Hero/Hun_New_V2b/Material/MI_ZeroHun_Head_b`，头发和服装用 `.../MI_ZeroHun_Cloth_02_b`。
- 游戏的角色材质是分层材质（`MA_Character` / `MAI_Skin` 链）。**只覆盖第 0 层**（关联类型 layer、索引 0）：`Albedo`、`Normal`、`Mix`、`SCMT_Map`，
  皮肤另加 `SkinMicroNormalIntensity`（身体 0.3、脸 0.2）。插件 `SetMaterialTextureParameter` / `SetMaterialScalarParameter` 带关联和索引参数，
  Python 的 MaterialEditingLibrary 做不到这一点。
- 已证伪：覆盖第 1 层 → 网格不可见；覆盖全局参数 → 整件发白（`runtime-rejected`）。
- `Mix` 是 AO / 粗糙度 / 金属度（与原版 `T_ZeroHun_Cloth_02_ARM` 相同）。头发用 `Karin_ARM`；服装用 `Karin_ARMMatte`（255, 255, 0：粗糙度 1.0 而不是 0.67），
  否则裙子在 MSM_Cloth 下有一层光泽。`Normal` 目前都是平法线 `Karin_FlatN`（两个模型都还没用法线贴图）。

## 2. 贴图必须是虚拟纹理

`Hun` 的全部贴图都是 VT，材质采样 VT；普通贴图 → 材质实例退回白色。`ue_fixmats.py` 给每张贴图设 `virtual_texture_streaming`、压缩设置和贴图组
（法线 `TC_NORMALMAP`；Mix / SCMT 线性、`TEXTUREGROUP_CHARACTER_SPECULAR`）。

## 3. 雨水湿润

游戏的角色湿润曲线（`CharacterWetCurve_Hun`）走 MA_Character 链。布料和头发的材质实例把全局参数 `Wetness Min`、`Wetness Max`、
`RainDrops | StaticDrops Intensity`、`RainDrops | DrippingDrop Intensity` 设成 0（默认 0.6 / 0.6 / 1 / 1）；`Wetness Limit` 只在皮肤链上有。
内容工程里的占位母材质没有这些参数，编辑器不列出来；cook 后的材质实例保留覆盖（读回确认）。

## 4. 亮度

动漫风的近白反照率在游戏光照下过曝。`ue_brightness.py` 设贴图的 `adjust_brightness`：Karin_Original 头发 / 服装 0.78、身体 / 脸 0.9；
PicodraTech 的头发、尾巴合成图、两张服装图集 0.78，皮肤脸图集 0.9。这是 `case-derived` 的值，用户认可了 Karin_Original 的颜色。

## 5. 材质槽

- Karin_Original：`MI_Karin_Skin`、`MI_Karin_Face`、`MI_Karin_Hair`、`MI_Karin_Costume`；布料段的槽（`MI_Karin_Skirt`、`MI_Karin_HairTail`、`MI_Karin_Tail`、
  `MI_Karin_Ear`、`MI_Karin_HairFront`、`MI_Karin_SkirtSim`）在 `ue_fixmats.py` / `ue_cloth.py` 里映射到这四个材质实例之一。头发和耳朵段关投影（插件 `SetSectionCastShadow`）。
- PicodraTech：源 blend 按材质合并成 10 个网格，图集 4 × 4096（ColorAlpha + Normal，服装另有 Emission）。槽：`MI_Karin_{Skin,Face}`（皮肤脸图集）、`Hair`、
  `Tail`（合成图）、`ClothA`、`ClothB`；小材质并进 ClothA / ClothB（HairTrans → Hair，Costume / KCostume → ClothA，Costume1 / Metal → ClothB）。
  `materials.json` 写「材质实例 → 贴图 + 类别（skin / face / hair / costume）」和布料段的别名，UE 脚本的分支都读它。
- PicodraTech 的 blend 材质给服装加了 0.42–0.44 的常量灰色自发光，所以 blend 里那只长袜看起来是白的；图集和 VRM 是蓝的。游戏里不加自发光（未经用户判断）。
