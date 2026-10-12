# 技术合同

版本号与偏移全部是 `build-sensitive`（build `24831693` 实测，`25290080` 复核相同）。

## 1. 整包格式（TU3.2 起）

2026-09 前后的更新（社区称 TU3.2）把整个游戏重打包为**单个约 65 GB 的 `re_chunk_000.pak`**，
`patch_001..015` 都是 144 字节的空包（KPKA 4.1，0 条目）。

| 资源 | 旧版（≤2025-03 文件表） | TU3.2 / 2026-10 |
| --- | --- | --- |
| PAK | KPKA 4.2 多 patch | KPKA **4.2 feature `0x68`**（`0x40` = entry remap 表；`0x20` chunk 表；`0x08` 加密条目） |
| Mesh | `.mesh.231011879` / `.240423143` | **`.mesh.260421070`**（内部版本 `251205828`，REE-Lib 称 `DD2_V3`） |
| TEX | `.tex.760230703` | **`.tex.251211553`** |
| MDF | `.mdf2.40` | **`.mdf2.51`** |
| GPU Cloth | `.gpuc.231011972` | **`.gpuc.260421224`** |
| Chain | `.chain.54` | **`.chain.55`** |
| CLSP | `.clsp.3` | 不变 |
| FBXSKEL | `.fbxskel.6` | **`.fbxskel.8`** |
| PFB / USER | `.pfb.17` / `.user.2` | **`.pfb.18` / `.user.3`** |
| JCNS | `.jcns.24` | **`.jcns.36`** |

- 路径表：旧的 `DD2_STM_Release.list`（Ekey REE.PAK.Tool，2025-03）按新版本号改写后命中约 22.4 万 / 27.9 万条；
  REE-Lib-Resources 的 `dd2_files.list`（2026-09-02，27.8 万条）更全。
- 2026-09-23 时的工具状况：
  - ree-pak-cli 0.2.9 / 0.7.2 **不支持 feature `0x40`**，dump 出的全是垃圾条目。
  - RE Mesh Editor 0.66（2026-04 停更）只认 `231011879` / `240423143`，不认 `260421070`。
  - kagenocookie 的 RE-Engine-Lib（REE-Lib）在 2026-09 已支持新 PAK / Mesh / TEX / GPUC，本项目以它为读写核心，
    自写 CLI `DD2Tool`（见 [开发工具](DEV_TOOLING.md) §1）。
  - REE-Lib-Resources 的 `dd2/rsz_template.json`（2026-06）与 TU3.2 的类 CRC 不符，PFB / USER 解析失败；
    改 prefab 前需用 REFramework 重新导出 il2cpp dump 生成模板。本项目的方案不改 prefab，所以绕开了这一点。
- 网格路线：Blender + RE Mesh Editor 0.66 导出旧版 `240423143` → `DD2Tool meshconv … "DD2"` 转成 `260421070`。
  社区有 RE Mesh Editor 的 TU3.2 分支（miqote69、GitExplode）可作备选。
- TU3.2 mesh 合同：无顶点色元素（只有 pos / nortan / uv / uv2 / weight）；头部 `+72` 必须写 shape-key buffer 的大小，
  否则报「can't create a GPU buffer」；头部 flags 写 `4099`（`patch_mesh_header.py`）。**每个 LOD 槽都要有几何**
  （缺 LOD 会崩，可复用同一几何）。

## 2. 加载路线

- TU3.2 默认**不再加载 patch pak**（只有带 `/Environment/Package/Remastered:false` 启动参数时才加载）。
- REFramework nightly ≥01421 会自动注入 `<game>/pak_mods/*.pak`（注入到 `re_chunk_000.pak.sub_000.pak` 家族）；
  **LooseFileLoader 在 TU3.2 上无效**。
- 发行物 = `pak_mods/<Mod>.pak`（资源放在**自己的独立路径**，如 `natives/STM/Character/_karin/`，不覆盖任何原生文件）
  + `reframework/autorun/<mod>.lua`。前置 `dinput8.dll`（REFramework）。
- REFramework 01424 退出游戏时会崩溃或卡住（上游已知问题），不影响存档。日志里启动扫描有大量小写 "exception"，
  判断脚本异常要搜 `Exception occurred|hook error`。

## 3. 人类角色的资源结构

- 人类是 **kit 拼装**：`natives/stm/character/_kit/`
  - `body/body_000_{f,m}/body_000_{f,m}.mesh` —— **全体同性别人类共用的唯一身体网格**；`body_0xx/2xx/6xx/8xx_{f,m}`
    只有贴图 / MDF（肤色、体表变体）。
  - `head/head_XXX_{f,m}/`、`hair/hair_XXX/`、`beard/`、`makeup/`、`fur/`。
  - `_equipment/{tops,pants,helm,mantle,facewear,backpack,underwear}/NNN/`：tops 拆 `am`（手臂）/ `bd`（躯干）/ `bt` / `wb`，
    pants 拆 `lg` / `wl`；每件有 `_f` / `_m` 网格，**女版常借用男版 MDF**。
  - 骨架：`_kit/_common/skeleton/body_000_{f,m}.fbxskel.8`。
- `body_000_f.mesh`：23,050 顶点 / 192 骨（128 deform）/ 材质 `hand_mat, body_mat, nail_mat, vfx_mat`，2 LOD，
  带 `ShapeKeyWeights`（DD2 次级权重 = 捏脸 / 体型编辑骨），全部骨 `useSecondaryWeight=1`。Y-up，女性 Hip 高 0.967 m，
  `Head_0` 高 1.628 m；肘部前屈的 A-pose。
- 骨名：`root, Hip, Spine_0..2, Neck_0/1, Head_0, L/R_Arm_Clavicle/Upper/Lower/Hand, L/R_Hand_{Thumb,Index,Middle,Ring,Pinky}F_1..3,
  L/R_Leg_Upper/Lower/Ankle/Foot/Toes`，另有大量 `*_Twist_*`、`*Offset`、`C_*_Edit_*`（体型编辑）、`Prop_*`（道具挂点）。
  男性身体多 `L/R_Armor_Shoulder(Offset)`；兽人身体带 ShellFur。
- Hip 静止系（找身体前后左右时用）：Hip 局部 X = 上、Y = 角色右（−x）、Z = 前。
- 装备下的皮肤靠 **furmask 贴图**（在身体 UV 空间合成后给 `body_mat` 采样）隐藏，不删几何。
- 原生 chain 资源：身体 `body_chain.chain`（胸部 / 腰钩 / 背挂点），头发 `hair_001/011.chain`，披风 `mantle_523_f.chain`，
  身体碰撞 `body_female.clsp`。

## 4. 运行时对象（读档后的玩家，探针实测）

- 玩家根 GameObject `ch000000_00`：身体 `via.render.Mesh`（`body_000_f.mesh` +
  `AppSystem/CharaEdit/ch000/Material/Runtime/body_runtime_human.mdf2`）、`via.motion.Chain`（`body_chain.chain`）、
  `app.PartSwapper`、`app.BodyEditor`……
- 子 GO：`head`（内含 `Eyebrows`、`Hair`、`HairSwap`）、`Underwear`、`PantsWl/PantsWlSub`、`TopsAm/TopsWb`、武器、灯笼……
  装备子 GO 都带 `via.render.SharedSkeleton`。菜单 / 装备预览用 `MockupModel_ch000000_00`（`app.MockupCtrl`）。
- 隐藏槽位：`app.PartSwapper:set_HideSwapObjects(mask)` + `forceUpdateStatusOfSwapObjects()`。`SwapObjects` 掩码（取自 TU3.2 前的类型 dump，只实测了 8191）
  Hair=1 / Beard=2 / Eyebrows=4 / Tops=120 / Pants=128 / Helm=256 / Mantle=512 / Backpack=1024 / Facewear=2048 /
  Underwear=4096 / NoOutfit=4088 / Naked=8184 / **Newborn=8191**（实测隐藏发 / 眉 / 须 / 全部装备 / 内衣；头部网格要单独
  `set_Enabled(false)`）。
- 身体 Mesh 的 PartsEnable 默认只开 group 0；自定义网格的其它组要 `setPartsEnable(i, true)`（`getPartsEnableCount` = 256）。
- 体型：`PartSwapper:get_Meta()` → `app.CharacterEditDefine.MetaData` 的 `_Gender` / `_Species`（`app.Gender.Female`、
  `app.Species.Human`）。网格路径只分男女、皮肤材质路径只分人 / 兽人，判断体型要看 MetaData，不能看路径。

## 5. 贴图与材质

- 贴图通道（量测 DD2 装备贴图）：
  - `ALBD` = BC1/BC7 sRGB 颜色（A=1）；
  - `NRMR` = RG 法线 XY（OpenGL / +Y，curl 检验）、B 法线 Z、A 粗糙度（Null 贴图为 0.5）；
  - `ATOC` / `ATOS` = R alpha、G 透光、B AO（BC1）。
  - DirectX（−Y）约定的源法线转换时翻 G。大于 2K 的贴图会被降采样。
- 材质母版：`MaterialShader/Master/Character_Default.mmtr`（模板取 `body_001_f.mdf2.51` 的 `nail_mat`），贴图槽
  `BaseDielectricMap / NormalRoughnessMap / AlphaTranslucentOcclusionCavityMap`；flag `BaseAlphaTestEnable`、
  `BaseTwoSideEnable`；参数 `AlphaTestRef`。装备常用的 `Character_Recolor.mmtr` 是遮罩调色流程，不适合直接贴图。
- 身体的 4 个原生材质名（`body_mat/hand_mat/nail_mat/vfx_mat`）要留在替换网格里（零面积兼容桩），MDF 中这 4 条从运行时
  `body_runtime_human.mdf2` 复制——游戏的材质系统按名字找它们（[构建流水线](BUILD_PIPELINE.md) §5）。

## 6. 版本更新的影响（2026-10，build 25290080 + DLC「Dark Arisen」）

- `re_chunk_000.pak` 整包重写（31.9 万条目，remap 表 24.3 万条），**格式版本全部不变**（旧路径表只丢 38 条，后缀全部相同）。
  本项目依赖的原生文件（身体 mesh、运行时 MDF、`body_001_f.mdf2`、`body_chain.chain`、`body_female.clsp`、
  `hair_001/011.chain`、`mantle_523_f.chain`、`body_000_f.fbxskel`）逐字节相同。
- DLC 是 `<game>/dlc/re_dlc_stm_2593290.pak`（26.9 GB，11.4 万条，KPKA 4.2 feature `0x28`）+ `re_dlc_stm_2593280.pak`（2 条）；
  覆盖约 4.9 万个已知路径，对本项目引用的文件逐字节相同。`pak_mods` 注入在 DLC pak 之后，独立路径不受影响。
- 所有 hook / 字段 / 枚举名都在；`SwapObjects` 枚举不变（Newborn=8191 仍覆盖全部槽位）。结论：Mod 无需重建。
- 复核方法：新 TOC → 用旧路径表 resolve → 比较依赖文件哈希 → 冷启动看脚本「失败即关闭」检查有无缺项。
- 新版本首次启动：Steam 弹 Capcom EULA；标题依次弹「已应用附加内容」「新增困难模式」两条公告；每次读档后弹
  「还有未收取的附加内容」。自动化脚本要处理这些弹窗。
