# 技术合同

除标注外均为游戏版本 `1613387`（Steam buildid `20773316`）上的实测。

## 1. 游戏与容器

- 引擎：WB 改过的 UE 4.27（工程名 `Phoenix`）。shipping exe 的段名被加固工具改过（`.ecode`、`.xpdata` 等），没有 PDB；
  `.pdata` 还能用来找函数边界。
- 资源是 IoStore：`Phoenix\Content\Paks\*.pak/.utoc/.ucas`（toc 版本 `PartitionSize`，container header `Initial`）。
- mod 放 `Phoenix\Content\Paks\~mods\`（没有就新建），三件套同名，命名沿用社区惯例 `zzz_<名字>_P`。
  游戏关闭时才能替换；同一资产路径被两个 mod 替换时只有一个生效。
- retoc 0.1.5：`to-legacy --version UE4_27 [--no-shaders] --filter <名字> <Paks目录> <输出>` 取原版资产（`--filter` 要写准确的资产名），
  `to-zen --version UE4_27 <legacy树> <out.utoc>` 打包，`verify` 校验。
- legacy 包用原版 UE 4.27 编辑器 cook（`-CookAll`，**不加** `-unversioned`）；带版本的序列化让 retoc 和 CUE4Parse 都能读。
- 游戏自带官方 mod 系统（Creator Kit 制作），本项目不用它；`~mods` 下的包照常加载（§8）。

## 2. 2025-01-30 更新后的骨骼网格格式

官方公告称这次更新改了「数据序列化 + 光追」。之后几乎所有旧网格 mod 失效（用户描述；本项目的旧版参考 mod 也要补丁后才能用）。

- `FSkelMeshRenderSection` 在 `bCastShadow` 之后多一个 uint32（值 1，推测是光追可见性）。原版 4.27 cook 的网格在每个 render section 的
  这个位置插入 `01 00 00 00`，然后修正导出表的 `SerialSize`、后续导出的 `SerialOffset` 和摘要里的 `BulkDataStartOffset`，
  游戏就能正常加载渲染（`runtime-confirmed`：用户本人在游戏里看到并验收）。CUE4Parse 已有这条规则（`GAME_HogwartsLegacy`，`FSkelMeshSection` +4）。
- 插入位置要去重：同一个包被解析两次会得到重复的 section 位置（HLMeshProbe 的 `patch` 用 `Distinct()`），否则校验失败。
- 骨影响数 ≤ 4（Creator Kit 的要求；本项目一直遵守）。旧的参考 mod 每顶点 6 个影响、渲染成灰色，
  但灰色的确定原因是材质槽为空（[排障手册](TROUBLESHOOTING.md) §2），超过 4 是否一定出问题没有单独测。
- 网格的参考姿势逐骨写成游戏的值：男 = `Biped_Skeleton`，女 = 女性网格自己的参考姿势（有 112 根骨与 `Biped_Skeleton` 不同，最多差 13 cm）。
  cook 后用 HLMeshProbe 按骨名写回 `FinalRefBonePose`（40 字节的 FTransform：四元数、平移、缩放）。不写回的效果没单独测。
- 形变目标（`UMorphTarget`）的格式与原版 4.27 相同，补丁器只需要整体平移后续导出的偏移。

## 3. 材质

- HL 的 `UMaterialInterface` 在导出末尾多一个 20 字节的 `FSHAHash`（CUE4Parse 读作 `CustomGameData`），每个材质实例都不同。
  自建的材质实例没有正确的哈希，**不新建**；借用游戏已有的材质实例（父材质 `MM_Prop`，贴图参数 D / N / MRO），
  在原贴图路径上 cook 自己的贴图来替换。
- 宿主：上衣 → 黑魔法套装上衣的材质实例（服装贴图），裤子 → 皮肤，面罩 → 脸，围巾 → 头发，帽子 → 透明图集（遮罩、双面）。
  这几个部件本身换成空模型，所以借它们的材质不会露出原样。
- 女性黑魔法套装（豪华版）没有自己的材质实例，直接用男版的 `MI_HUM_M_*DarkArtsDeluxe01*` 和贴图。只替换女性体型时，
  把原版材质实例的 legacy 包按字节克隆到游戏里没人用的 `_F` 路径，替换都等长（`Upper_M`→`Upper_F`、`HUM_M_`→`HUM_F_`），
  哈希和着色器图保持原样，贴图参数和流送数据随之指向 cook 在 `_F` 路径上的 Karin 贴图；男版的材质和贴图保持原版
  （`runtime-confirmed`，发行 v1.0 / v1.1）。
- UE 占位工程里材质实例只是占位（父材质是空的 `MM_Prop` 占位），只用来让网格的材质槽有正确的引用路径，不进包。

## 4. 骨架

- `/Game/RiggedObjects/Characters/Biped_Skeleton`：260 根骨 + 7 根虚拟骨（运行时网格和骨架的骨数都按 +7 计）。
  原版头部网格用其中 140 根；身体部件用 105–117 根。骨架里有给布料 / 动力学用的 `dress_01..04_*`（8 个方向）、`LegDyn`、`HoodDyn`。
- **网格的每根骨都必须在它引用的骨架里。** 运行时按骨名把网格骨映射到骨架，找不到就是 -1；游戏的分层混合（按骨骼分层混合）
  拿它去查按骨架索引的权重表，读到无效数据而崩溃（`runtime-rejected` → 修复后 `runtime-confirmed`，[排障手册](TROUBLESHOOTING.md) §1）。
  编辑器里导入时会自动把缺的骨补进骨架，所以占位工程里看不出问题。
- `CopyPoseFromMesh` 直接用骨架 → 姿势的索引表，要求网格的每根骨都在它的骨架里。带动态骨的网格因此用自带骨架：
  `/Game/RiggedObjects/Characters/Human/Karin_<F|M>/SK_Karin_<F|M>_Skeleton`（游戏骨 + 95 根动态骨，无虚拟骨），随包发布。
  动画按骨名从身体复制，所以不需要游戏骨架的 GUID。
- FBX 里骨架对象必须叫 `Armature`：UE 只在根节点名字正好是 `Armature` 时把它剥掉，否则多出一根根骨。

## 5. 装备外观与角色部件

- 装备外观 `Data/GearAppearances/<槽>/DA_GA_<槽>_<NNN>_<M|F>` → `OutfitItems`（Upper / Lower / Socks / Shoes）→ 角色部件数据资产
  `DA_HUM_<M|F>_<部件>_*_Master`。部件按披风类型用 `MeshOverrides` 选网格变体（披风 A → `_Master_A`，RoyaltyRobe → `_Master_B`，B → 不换）。
- 黑魔法套装：`GA_Outfit_072`（服装）、`Back_112`（披风，`DA_HUM_*_Robe_DarkArtsDeluxe01_Master`，动画类 `ABP_Robe_ClothJoints`）、
  `Hand_003`、`Neck_011`、`Face_035`、`Head_073/074`。
- **腿部皮肤在袜子部件里。** 从 `OutfitItems` 删掉 Socks / Shoes，游戏会退回到存档肤色的光腿，穿过替换模型；
  改成让这两项的 `CharacterPiece` 指向空的裤子部件（等长修改）。
- 发型部件的 `MeshOverrides`：拉起兜帽 → 共用的 `HoodHair`，帽型 A / B → 共用的 `Kit_Up_HatA/B`，帽型 D → 空。
  替换后的头配上这些共用网格就是光头；把每个覆盖都指回 `DefaultMesh`（等长修改），不要替换共用网格（NPC 也在用）。
- 数据资产都是带标签属性（tagged property）的 legacy 包；改长度时要修属性标签的大小、导出的 `SerialSize` 和 `BulkDataStartOffset`。

## 6. 动画类与次级物理的宿主

- 没有 `AnimClass` 的角色部件用主姿势（master pose）跟随身体，网格上的 `PostProcessAnimBlueprint` **不会运行**。
- 有 `AnimClass` 的部件（披风、`*_Dynamics` 合并服装）自己跑动画实例：类里是 `CopyPoseFromMesh`（`bUseAttachedParent`）复制身体姿势，
  动力学在网格的 `*_PP` 后处理蓝图里。原版头发和裙子多数用 Chaos 布料，`dress_*` / `HoodDyn` 用单骨 AnimDynamics，模拟空间 Component。
- 注入 `AnimClass`：在部件数据资产里加 `ObjectProperty AnimClass` → import `ABP_X_C`（`/Script/Engine.AnimBlueprintGeneratedClass`），
  再把 CDO import `Default__ABP_X_C` 加进该导出的 SerializationBeforeCreate 预加载依赖。游戏接受原版 4.27 编译的动画蓝图
  （`runtime-confirmed`：v9 起物理在游戏里运行）。
- 本项目给上衣和两个发型的数据资产注入动画类；头部不注入（它跑游戏自己的面部动画）。

## 7. 面部、捏脸预设与存档

- 头部网格（`Biped_Skeleton`，140 根骨）有 144 个 FACS 风格的形变（`eye_blink_l`、`jaw_drop_mid`、`brows_up_in_l` …）。
  头部数据资产的 `FacialPoseAsset`（`SK_Young_M_Head_Master_Facial_Anim_PoseAsset`，42 个姿势：口型、眨眼、挑眉、眯眼、头 / 眼的俯仰偏转）
  输出 108 条曲线，按名字驱动形变，骨骼只动一点（下巴、牙、舌、眼几度）。替换的头只要有同名形变就能动（[表情](FACE.md)）。
- 头部数据资产只引用网格和面部姿势资产，没有 `AnimClass`；头部的动画类由角色蓝图给出，里面有按骨骼分层混合。
- 捏脸预设表 `Data/AvatarPresets/DT_AvatarPresets`（PresetType、Gender、DA、SortOrder）。女性脸型：第 1 个 = `Face001`（Emily，
  `AVA_YF_Head_Emily/SK_Young_F_Head_Emily_Master`），第 14 个 = `Face014`（Amita）。女性发型：第 8 个 = `Hair008`（`StuHair13` 低发髻），
  第 17 个 = `Hair037`（`StuHair18 PrincessLong_Bangs1`）；第 10 个是不带刘海的长直发，网格不同。男性测试存档：`FaceMale002` → `AVA_YM_Head_SC_AL`，
  `HairMale003` → `StuHair03 ShavedBob`。
- 霍格莫德发廊（`UI_BP_Salon`）只能改发型、眉毛、肤色，**脸型只能在创建角色时选**。
- 存档在 `%LOCALAPPDATA%\Hogwarts Legacy\Saved\SaveGames\<id>\`，`HL-<角色>-<槽>.sav`；`SaveGameList.sav` 列出角色和 `CharacterPresetData`。
  加一个外来存档：放成新的角色槽 `HL-0N-00.sav`；Steam 云会在启动时还原旧的 `SaveGameList.sav`，进程出现后立刻删掉它，游戏会按文件重建列表。

## 8. 崩溃报告器

- 游戏崩溃时写 `%LOCALAPPDATA%\Hogwarts Legacy\Saved\Crashes\<GUID>\`：`CrashContext.runtime-xml`（无符号的调用栈 `PCallStack`、模块表、启动后秒数）、
  `CrashUserData.json`、`Phoenix-Game-Shipping-<pid>_<时间>.dmp`（约 120 MB 的 minidump，含异常记录、寄存器、栈附近和寄存器指向的部分内存）。
  `Saved\Logs` 里没有游戏日志（只有 NGX）。
- `CrashUserData.json` 里有 `UnofficialModsPresent`（`~mods` 有包时为 `true`）和 `AnyModsInstalled` / `AnyModsActive`（官方 mod 系统）。
  弹窗里「建议卸载模组、改用官方模组」的话是按这个字段加的，**任何崩溃都会这样说**；没有发现主动检测或拦截非官方 mod 的迹象，
  `~mods` 下的包会照常加载运行。
