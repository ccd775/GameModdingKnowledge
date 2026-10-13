# 技术合同

证据：CUE4Parse（PalExport）配社区 usmap `Mappings_1.0.5` 的 dump，游戏 exe 的字符串，UE 5.1.1 编辑器里的实测，以及
远程测试机上的实机结果。除特别注明外都是 `build-sensitive`（build `25246127`）。

## 1. 容器与加载

- 游戏资源只有一个 legacy pak：`Pal\Content\Paks\Pal-Windows.pak`（约 39 GB，pak V11，未加密）。没有 IoStore。
- Cook 是 unversioned 的：读任何资产都要 usmap。本项目用 PalworldModding/UsefulFiles 的 `Mappings_1.0.5.usmap`；
  版本不对时属性解析会错位或直接失败。UE4SS 也能现场 dump usmap（项目备了一份，最终没用到）。
- Mod：`Pal\Content\Paks\~mods\<名字>_P.pak`，挂载点 `../../../`，包内路径以 `Pal/Content/...` 开头。不需要 `.sig`，
  不需要 UE4SS。用 repak `pack --version V11` 打包。
- 内容工程必须叫 `Pal`，cook 出来的路径才是 `Pal/Content/...`。`DefaultGame.ini`：`bUseIoStore=False`、
  `bShareMaterialShaderCode=False`。

## 2. 玩家角色的组成

`BP_Player_Female` 的组件：

| 组件 | 网格 | 动画 |
| --- | --- | --- |
| `CharacterMesh0` | 身体 = 当前服装的网格；无护甲时为 `SK_Player_Female_Outfit_OldCloth001` | `ABP_Player`，内含链接层 `ClothLayer`（§4） |
| `HeadMesh` | `SK_Player_Female_HeadNNN`（角色创建时选的脸型） | `ABP_Player_Head`：CopyPoseFromMesh + `EyeLocationFix`（读 `PalPlayerHeadAnimInstance.PlayerEyeLocation*`） |
| `HairMesh` | `SK_Player_HairNNN`（不分男女） | `ABP_Player_Hair`：CopyPoseFromMesh + 链接层 `HairLayer` → 各发型的 `Imp_Hair/ABP_Player_HairNNN_Implementation`（KawaiiPhysics，骨 `hair_01..26`） |
| `HairAttachAccessory`、`PalFacial` | 发饰挂点、面部组件（§5） | |

资产路径（`/Game/Pal/Model/Character/Player/`）：`Outfit/SK_Player_Female_Outfit_OldCloth001/…`、
`Head/HeadNNN/SK_Player_Female_HeadNNN`（本快照 26 个，另有 Male 系列）、`Hair/HairNNN/SK_Player_HairNNN`（37 个）。
头和头发都从身体复制姿势，所以 Karin 的头发、兽耳放进身体网格也能正常跟随；脸单独放在头部网格里，才能被面部组件驱动。

## 3. 骨架与重定向

- 所有人形共用 `/Game/Pal/Model/Character/Skeleton/Human/SK_PalHuman_Skeleton`：4079 根骨，其中绝大部分是各 NPC 的
  配件链（头发、裙、披风、饰带）。原版 OldCloth001 网格只有 73 根骨。
- 平移重定向：4075 根骨为 `Skeleton`，root / pelvis 为 `Animation` / `AnimationScaled`。所以**网格自己的 bind 姿势决定比例**，
  换比例不需要 AnimBP 改骨（这一点和剑星相反）。
- 玩家动画（idle、jog、sprint、dance、damage、jump）只有 65 根基础骨的轨道，没有曲线。动画写的是绝对局部旋转，所以
  网格的 bind 朝向必须逐骨等于原版；位置可以换成新角色的（`invariant`，对这类重定向设置）。
- 网格骨必须是骨架的子集且父骨一致；这也是 KawaiiPhysics 的前提（[Kawaii 物理](KAWAII_PHYSICS.md) §1）。
- 物理资产：`/Game/Pal/Model/Character/Player/Body/Female/SK_Player_Female_PhysicsAsset`，网格引用游戏自带的即可。

## 4. 服装层（次级物理挂在这里）

- `DT_CharacterCreationMeshPresetTable_Equipments` 的 `Default_EquipBody`（女性 TypeA）把
  `/Game/Pal/Blueprint/Character/Player/Imp_Cloth/ABP_F_OldCloth001_Implimentation` 链接进 `ABP_Player` 的 `ClothLayer`。
  注意原名拼写是 `Implimentation`。
- 该蓝图实现接口 `/Game/Pal/Blueprint/Character/Player/Female/ALI_HumanCloth`，层图为
  `InPose → LocalToComponent → KawaiiPhysics ×3 → ComponentToLocal → Root`，运行在身体网格上。
- 替换做法：同路径新建 AnimBP（父类 `AnimInstance`，目标骨架为占位骨架），实现占位的 `ALI_HumanCloth`，在 `ClothLayer`
  里串 7 个 Kawaii 节点（脚本把 `InPose` 直接连到第一个节点的 `ComponentPose`，编译 0 错误，游戏里物理运行）。
  `ABP_Player` 和数据表都不用改。
- 游戏里的 KawaiiPhysics ≈ 1.17.1：属性布局与 1.17.1 一致（含 `CustomExternalForces`），只有 `TargetFrameRate` 的 FName
  大小写和曲线字段是否带 `_DEPRECATED` 不同。编辑器工程装 KawaiiPhysics 1.17.1 源码插件；游戏自带模块，mod 不带插件。
  节点类 `/Script/KawaiiPhysicsEd.AnimGraphNode_KawaiiPhysics`。

## 5. 面部组件

- C++ 的 `PalFacialComponent` 按名字驱动头部网格的形变：眼型 Default / Close / HalfClose / Pain / Smile / Anger / Trouble /
  GuruGuru，嘴型 Default / Pain / Smile / Anger，另有说话张嘴。
- 形变名（在 `Palworld-Win64-Shipping.exe` 里连续出现）：`eye_halfclose`、`eye_close`、`eye_pain`、`eye_smile`、`eye_anger`、
  `eye_trouble`、`eye_guruguru`、`mouth_smile`、`mouth_pain`、`mouth_anger`、`mouth_open`。
- 原版玩家脸只有 `eye_close`、`eye_halfclose`、`mouth_open`（另有 `BS_Torso_*`）；新脸可以把 11 个都做上。
- 玩家的蒙太奇里没有面部通知，眨眼由组件自动触发（用户实机看到了 Karin 眨眼）。其余表情由 C++ 按状态触发，本项目没有
  在游戏里逐个确认。玩家眼睛材质没有表情贴图。

## 6. 材质

- 自己的材质实例挂在游戏的材质实例下，只覆盖贴图参数，不引入新的静态开关组合，运行时直接用游戏的着色器：
  - 皮肤、脸：`/Game/Pal/Material/Character/Common/MI_PalLit_HumanSkin`
  - 头发：`/Game/Pal/Model/Character/Player/Hair/Hair001/MI_Player_Hair001`
  - 服装：`/Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/v01/MI_Player_Female_Outfit_OldCloth001_v01_M01`
- 贴图参数名：`Base Texture`、`Subsurface Texture`、`MetallicRoughnessOcclusionSpecularTexture`（R 金属、G 粗糙、B AO、A 高光）、
  `BaseColor Mask`、`Override Normal Mask 1..3`、`Normal Map`、`Override Normal Map 1..2`。
- 编辑器里这些父级是同路径的占位：一个拥有同名参数的占位母材质（参数默认值用自己的贴图，采样器类型才对得上）加上同名
  占位 MIC。占位不打包。
- 未解决：游戏里 Karin 的头发偏淡紫（贴图均值本身偏粉；父 MI 的色调或角色创建的发色是否叠加，未查）。

## 7. 幻化（护甲外观）

- 身体替换只作用于默认服装。穿上身体护甲时，网格换成护甲的，Karin 的身体、头发都看不到，只剩脸。
- 游戏自带幻化（v0.5.0，2025-03 加入）：建造「古典式化妆台」→ 交互「更改角色的外观装备」→ 身体、头部外观选
  「初期装备」（文本键 `CHARACTER_DRESSING_NAKEDRESS_*`，简中「游戏开始时的样子」）。这样穿任何护甲都显示 Karin，
  也不显示头盔。外观只改外观，不影响属性。
- 证据级：`reference-inferred`（游戏文本 + 网上攻略；攻略称该科技 22 级解锁，1.0 后未核实）。测试存档才 1 级，agent 没有
  在游戏里走过这一流程。有了它，就不需要把头发挪到发型槽（那样只为「护甲外观 + Karin 头发」才有意义）。

## 8. 覆盖范围与副作用

- 发型网格不分男女：隐藏发型的包会让男性角色也没有头发。只玩男性角色时不要装它。
- 男性脸型、男性服装都没替换；角色要选女性。
- 联机时只有装了 mod 的客户端看得到替换效果。
- 与替换 OldCloth001、女性脸型、玩家发型的其它 mod 冲突（包括用户自己的参考 mod）。
