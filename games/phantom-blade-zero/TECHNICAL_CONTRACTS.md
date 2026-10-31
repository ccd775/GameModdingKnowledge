# 技术合同

快照：Steam App `4115450`，buildid `26266538`，引擎 `5.7.4-301524+42ecbfa37f78`（exe 文件版本 `CL-301524_JKS-17219`）。
除标明 `invariant` 的条目外都是 `build-sensitive`。

## 1. 游戏与容器

- 真正的 exe 是 `PBZ\platform\steam\PBZ.exe`（约 511 MB，加了保护：节名改成 `.xcode` / `.ecode` / `.debug`）；`PBZ\steam\PBZ.exe` 只是启动壳。
- 内容根 `ProjectPBZ`。资源在 IoStore：`ProjectPBZ-Windows.{utoc,ucas,pak}` 和 `_s1` … `_s65`；索引加密，Oodle 压缩，**没有 `.sig`**。
- CUE4Parse 用 `GAME_UE5_7` 读得开（需要 AES 密钥、Oodle DLL、usmap，见 §3）。

## 2. mod 怎么被加载

- 放进 `ProjectPBZ\Content\Paks\~mods\`：`z_<名>_P.utoc` + `z_<名>_P.ucas` + `z_<名>_P.pak`。`_P` 后缀和 `~mods` 让它排在原版之后、优先级更高。
- 引擎是**挂载 `.pak` 时**才去找同名的 `.utoc`。所以除了 IoStore 容器，还要一个只装一个小文本文件的普通 pak
  （项目里是 `Content/Mods/KarinPBZ/KarinPBZ.txt`，568 字节）。不用 UE4SS 或其它加载器。`invariant`（UE 5 IoStore 的通用行为）。
- 容器用 UnrealPak 的 IoStore 模式从**自己工程的 cook 输出**做：`-CreateGlobalContainer`（临时、丢弃）、自己 cook 的
  `packagestore.manifest` 和 `scriptobjects.bin`、`-ResponseFile` 里逐个列出要收的包（挂载点 `../../../ProjectPBZ/Plugins/HuaShira/Content/`
  和 `../../../ProjectPBZ/Content/`）、`-compressionformats=Oodle`。见便携包 `tools/mkcontainer.ps1`。
- **cook 必须带版本号**（UE 默认）。无版本号的包让这个改过的引擎在加载时崩溃（`runtime-rejected`）。
- 不需要游戏的 `.sig`，也不需要加密自己的容器。

## 3. 密钥与反射信息

- AES 密钥用 AESDumpster 从 exe 里扫出来。**密钥不随库发布**；工具从环境变量 `PBZX_AES` 读。
- usmap：UE4SS 3.0.1（2026-10-12 版）的 AOB 扫描找不到 GUObjectArray 和 GNatives；原版 Dumper-7 找不到 GObjects 直接 `exit(1)`。
  做法（[开发工具](DEV_TOOLING.md) §2）：
  1. `objscan` 在运行中的游戏里找到 GUObjectArray：RVA `0xDDB3C50`（在 `.debug` 节）；`FChunkedFixedUObjectArray` 字段重排过：
     `MaxChunks +0`、`NumChunks +4`、`Objects +8`、`NumElements +0x10`、`MaxElements +0x14`；`FUObjectItem` 步长 24，Object 指针在 +8。
  2. 给 Dumper-7 打补丁：用上面的布局、ini 放在 exe 旁边、跳过 `InitTextOffsets`（它调用 ProcessEvent，游戏会崩），先写 mappings。
  3. 这样导出的 usmap 每个结构体都带着全部继承属性：Dumper-7 把 `FField::Next` 解析成了 `PropertyLinkNext`（偏移 0x48）。
     `usmap_fix.py` 按 (名字, 类型) 去掉继承项（这个 build 去掉 134 345 条），之后骨骼网格、蓝图、数据表都能正确解析。
- 游戏骨架里有全部 43 个面部形变名对应的曲线（`CTRL_expressions_*`），所以形变按这些名字命名就会被驱动（[面部](FACE.md)）。

## 4. 目标资产：玩家「魂」

- 玩家角色 = 魂 = `Hun`。插件 `HuaShira` 下 `Characters/Hero/Hero_Hun`。
- 外观由数据表 `DT_PBZAppearanceTable` 决定。默认两行：
  - `普通服装`（HunBody）：身体 `SkinParts/Hun_Body_Simple`、布料网格 `Hun_Cloth`、Chaos 布料资产 `Cloth/CA_Hun_{UpperCloth,Skirt,Cape}`；
  - `10年前服装`（HunBodyClimax，序章刚结束、左殇 boss 那一段）：同一身体，`CA_Hun_{UpperCloth,Skirt,Cape}_Climax`、帽子 `Hun_Hat_01`、`Hun_Scarf_Climax`。
  - 其它服装（MoTian、YaYu、FengXue、ZhuiMing、GuYou、JiGuanMoQu）有各自的身体网格，没有替换。
- 头 `SkinParts/Hun_Head_New`（MetaHuman，带 DNA，后处理 `Hun_Head_PostProcess_AnimBP` 跑 RigLogic），另有 `CA_Hun_Hair01`、
  帽子 `Hats/Hun_Hat_00`、`Hun_Scarf`、`Hun_Hair_Band`、`Hun_BrowLashCard`（睫毛片，是头的子组件）。
- 部件组件由代码创建，用 `Hun_CopyPose` / `Hun_CopyPose_Head`（Copy Pose From Mesh，复制曲线）跟随领导者。
- **领导者是身体网格本身**：`普通服装` 的 `BodyMeshAsset` 装在 `CharacterMesh0` 上（动画类 `PBZ_ABP_Hun_Base`）。隐形网格 `Hun_Invs`
  （1130 根骨、3 个顶点、带角色物理资产 `Hero_Hun_PhysicsAsset`）曾被当成领导者，这个假设被实机证伪（`rejected`，[面部](FACE.md) §4）。
- **武器跟着身体的骨走。** 原版 `Hun_Body_Simple` 264 根骨，比 `Hun_Invs` 多 `weapon_l_child`、`weapon_r_child`、`ik_weapon_l_child`、
  `ik_weapon_r_child`（`weapon_l/r`、`ik_weapon_l/r` 的单位子骨，重定向 Animation；在 `Hun_Skin_Skeleton` 里是 1130–1133）。
  醉剑（武器 ChiZheCanJian 的醉态，`BP_Weapon_Hun_ChiZheZuiJian`）的醉态攻击动画 `Hun_ChiZheCanJian_Drunk_Attack_E` 驱动
  `weapon_r_child`（还有曲线 `weapon_r_child_translation_y`）。身体缺这几根骨时，用户报告醉剑的剑消失、攻击没有判定
  （`runtime-rejected`，v2）；v3 补回后读回确认 264 根骨，未进游戏复测。规则（`invariant`）：**替换领导者网格时，原版网格的骨一根不能少**。
  原版 `Hun_Body_Climax` 只有 1130 根骨、不含这几根；项目的 Climax 身体是成年身体的副本，现在也是 264 根。
- `BP_Renewal_Hun_Climax`（`BP_Renewal_Hun` 的子类）有自己的 `CharacterMesh0` = `Hero_Hun_Climax/SkinParts/Hun_Body_Climax`，要一起换。
- 序章：`BP_Renewal_Hun_Young`，领导者 `Young_Hun/SkinParts/Hun_Young_Body`（1207 根骨，全部 Animation 重定向 = 原版比例，没有链骨），
  头 `Hun_Young_Head`，头发 `Hun_young_Hair`、睫毛片 `Hun_Young_BrowLashCard`、布料 `CA_Hun_Young*`。
- 过场：`Animation/Seqs/ActorForSeqs/BP_Seq_Hun`、`BP_Seq_Hun_Climax`、`BP_Seq_Young_Hun` 用同样的网格，但头发是 groom（`Hun_New_V1/Mesh/*`、
  `Hun_Young/Mesh/V02/Hair/*`），并有「主头发模式」开关（[面部](FACE.md) §5）。

## 5. 骨架与重定向

- `Hun_Skin_Skeleton`：1134 根骨 = MetaHuman 式身体 + 843 根 `FACIAL_*` + 链骨（`Hair_0..3`、`bns_skirt_0..2_l/r`、`bns_skirt_3`、
  `bns_frontSkirtArmorRibbon`、`bns_ribbon_0`、`bns_cloak`、袖子）。重定向：身体与链骨 AnimationScaled，手 / 手指 / IK 为 Animation，球骨为 Skeleton。
  动画给每一根链骨打了关键帧。
- 构建规则（`build_pbz.py` 的骨架合同）：每个绑定关节 = 父关节 + 原版方向 × 长度；有 Karin 对应关节的用 Karin 的长度，
  Animation 骨用原版偏移，辅助骨用按比例缩放的原版偏移；**绑定朝向保持原版**（动画带的是绝对局部旋转），网格按区域刚体变换摆到这副骨架上。
- 链骨被游戏的动画和后处理节点摆姿势，所以 Karin 的头发、裙子不能挂在链骨上（会被拉长），物理改用 Chaos 布料（[物理](PHYSICS.md) §1）。
- 少年魂：骨架全部 Animation 重定向，网格比例改不了；躯干沿脊柱拉到原版长度，保留 Karin 的脖子长度（头的枢轴高约 1.7 cm）。
- 眼睛：Karin 的眼睛区域跟头走（原版眼根骨在 4–6 cm 之外，权重给眼根会斗鸡眼）。

## 6. 占位与隐藏

- 占位（cook 但不进容器）：`Hun_Skin_Skeleton`、`Hats/Hun_Hat_Skeleton`、`PA_Hun`、`Hero_Hun_PhysicsAsset`、`Rig/ABP_Hun_PostProcess`、
  `/Game/PBZContent/...` 下的母材质实例。骨架占位由第一次导入领导者网格时生成，再改名到游戏路径。
- 隐藏：一个三角形的骨骼网格存成游戏资产名（`Hun_Cloth`、`Hun_Scarf(_Climax)`、`Hun_Hair_Band`、帽子、`CA_Hun_*` 布料资产名、少年魂的头发和睫毛片）。
  类型不对（游戏按 UChaosClothAsset / UGroomAsset 加载）时组件拿不到资产，安全不崩（`runtime-confirmed`）。
- 过场的 15 个 groom 资产也用同样的占位隐藏（`ue_grooms.py`）。它们在 `ProjectPBZ/Content/PBZContent/...` 下，容器挂载点是 `../../../ProjectPBZ/Content/`。
  UnrealPak 对它们会报 `Failed to obtain package name from file name`（`.uexp` 名字和包名不对应的警告），无害。

## 7. 材质（摘要）

- 游戏的角色材质实例是分层材质。只覆盖第 0 层（关联 layer、索引 0）的 Albedo、Normal、Mix、SCMT_Map（皮肤另加 SkinMicroNormalIntensity）。
- 贴图必须是虚拟纹理（`Hun` 的全部贴图都是 VT），否则材质实例退回白色。细节见 [材质与贴图](MATERIALS_AND_TEXTURES.md)。

## 8. build 变化时

重新 dump 并与上一 build 比较：`Hun_Body_Simple` / `Hun_Body_Climax` / `Hun_Invs` / `Hun_Head_New` / `Hun_Young_Body` 的参考骨架（`skel`）、
`Hun_Skin_Skeleton` 的重定向模式、`DT_PBZAppearanceTable`、`BP_Renewal_Hun(_Climax|_Young)`（含字节码，`PBZX_SCRIPT=1`）、`Hun_CopyPose(_Head)`、
母材质实例的参数名。usmap 要用新 exe 重新导出再修正。安装脚本按 buildid 提示不一致。
