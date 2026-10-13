# 构建流水线

项目用两台机器：本机跑 Blender（构建、预览、Kawaii 离线模拟）；远程测试机装游戏、UE 5.1.1 和 PalExport，跑提取、
UE 导入、cook、打包和实机测试。两边也可以是同一台机器。具体命令和环境变量见
[便携工具包](../../portable-kits/palworld/README.md)。

```text
提取参照（PalExport + usmap）
  → Blender：build_pal.py（网格、权重、物理链、面部变形、physics.json）
  → gen_ue_config.py（材质与贴图配置、脸型 / 发型路径表）
  → 预览（render_preview / render_views / render_keys）
  → Kawaii 离线模拟（kawaii_sim.py，导出解析后的物理参数）
  → UE：ue_import.py（网格、贴图、材质实例、占位资产）→ ue_build_abp.py（服装层 AnimBP）
  → cook_and_pack.ps1（cook、按白名单分三个 pak、repak V11）
  → verify_paks.ps1（PalExport 读回）
  → 安装、实机测试 → 发行包
```

## 0. 一次性准备

- 编译 PalExport（CUE4Parse 命令行，net10.0）。读游戏需要 usmap 和 Oodle 的 `oo2core_9_win64.dll`。
- 提取参照（都是游戏资源，不进仓库）：
  - `list` 列出 `Pal/Content/Pal/Model/Character/Player/` 下的资产，存成文本：脸型、发型路径表从这里生成；
  - `export ue` 导出 OldCloth001 网格（`.uemodel`）——Blender 构建以它的骨架为准；
  - `json` dump `ABP_F_OldCloth001_Implimentation`、`ABP_Player`、`BP_Player_Female`、服装数据表、骨架；
  - `export ue` 导出玩家动画（`.ueanim`，例如 `AS_Player_Female_Jog_None`、`AS_Player_Female_Sprint`），给离线模拟和姿势预览用；
  - `mappings <正则>` 按名字查 usmap 里的结构和枚举（例如 `KawaiiPhysics`、`PalSkinType`），用来对照 Kawaii 版本和游戏枚举。
- UE 5.1.1 内容工程 `Pal`：插件 PythonScriptPlugin、EditorScriptingUtilities、KawaiiPhysics 1.17.1、PalModTools（项目自写，
  见 [开发工具](DEV_TOOLING.md)）。用 UnrealBuildTool 编一次插件。
- Blender 4.2.23，装 UEFormat 插件（`io_scene_ueformat`）读 `.uemodel` / `.ueanim`；FBX 导出用自带的 `io_scene_fbx`。

## 1. Blender 构建（`build_pal.py`）

`blender --background --factory-startup --python build_pal.py -- <run_dir> [--scale 1.30]`

1. 导入原版 OldCloth001 的 `.uemodel`，取 65 根基础骨（去掉 `F_OldCloth001_*` 服装骨）。
2. 导入 Karin 的 VRM；身体对象 `body_2, hair, kemomimi, tail, pullover, skirt, underwear, knee-socks, shoes`，脸是 VRM 里叫
   `Body` 的对象（带 237 个形态键）。
3. 算新骨架：朝向等于原版，位置用 Karin 的（×1.30，米 → 厘米）；每根 Karin 骨一个刚体变换把网格重摆上去（线性蒙皮）。
4. 权重映射到 PalHuman 骨；Karin 的 Spine / Chest 按高度分给 `spine_01..03`。
5. 物理链改名，落到游戏骨架的 NPC 配件链上（[角色拟合](CHARACTER_FIT.md) §3）。
6. 面部：按配方把形态键合成 11 个游戏形变，写到头部网格上。
7. 裙子加反向面（双面）；材质槽改名、合并；导出贴图。
8. 从 VRM 的碰撞体生成胶囊，写 `physics.json`（几何；动力学的默认值会被 `physics_tune.json` 覆盖）。
9. 不可见网格（头上一个很小的三角形）给发型用。
10. 导出 `Karin_Body.fbx`、`Karin_Head.fbx`、`Hidden.fbx`（单位缩放 0.01，不加叶骨），保存 `build.blend` 和 `report.json`。

`report.json` 是离线闸门：骨数（r3 为 189）、顶点数、未映射的顶点组（必须为空）、关节错位（0）、每个形变的最大位移、
材质槽、物理组与胶囊、警告列表。

## 2. UE 配置（`gen_ue_config.py`）

`python gen_ue_config.py <run_dir> <player_asset_list.txt>` 写 `ue_config.json` 和 4×4 的辅助贴图：

- 平法线、全黑遮罩；`MetallicRoughnessOcclusionSpecular` 按原版均值取粗糙度（皮肤 0.40、头发 0.60、服装 0.85）；
  SSS 颜色取原版女性身体 SSS 贴图的均值；
- 四个材质实例及其父级（[技术合同](TECHNICAL_CONTRACTS.md) §6）；
- 从资产列表里找出全部女性脸型和全部发型路径；
- 原版网格上的插槽 `Socket_BackWeapon_R`（`spine_03`，背负武器）按 Karin 躯干厚度 ×0.85 补回新网格。

## 3. 预览

- `render_preview.py` / `render_views.py`：全身正、侧、背和腿部特写；
- `render_keys.py`：面部形变网格图，挑配方用；
- `probe_run_pose.py`：用游戏动画把 `build.blend` 摆到屈髋最大的帧，渲染髋部五个视角（裙子不模拟，看最坏情况）。

## 4. 物理调参（`kawaii_sim.py`）

见 [Kawaii 物理](KAWAII_PHYSICS.md) §4。产出 `physics_rN.json`：run 的 `physics.json` 几何 + `physics_tune.json` 动力学的
合并结果，也就是被模拟过的那一份参数。AnimBP 只从这份文件生成。

## 5. UE 导入与 AnimBP

用 `UnrealEditor-Cmd Pal.uproject -run=pythonscript -script="<脚本> <参数>"` 无界面运行（`run_py.ps1` 包了一层，
并从日志里筛出 `[KARIN]` 行）。

- `ue_import.py <run>`：
  - 第一次导入身体时不给骨架，让导入器从 FBX 建骨架和物理资产，再改名搬到游戏的骨架、物理资产路径上当占位；
    之后的导入都用这个占位骨架。
  - 重新导入前先删旧资产（否则旧材质槽、旧骨留在网格里）。
  - 贴图、占位母材质、占位父 MIC、自己的 MI（`/Game/Mods/KarinPal/`）；按槽名指定材质；挂物理资产和插槽。
  - 脸只导入一次（Head001），再复制到每个女性脸型路径；不可见网格同样从 Hair001 复制到每个发型路径。
- `ue_build_abp.py <run> [physics_rN.json]`：建占位 `ALI_HumanCloth`（第一次），重建 `ABP_F_OldCloth001_Implimentation`，
  按参数文件串 Kawaii 节点、设属性和胶囊，编译必须 `errors=0`，最后在日志里读回参数，并把图导出成 `abp_graph.txt`。

只改物理参数时只跑 `ue_build_abp.py`。

## 6. Cook 与打包（`cook_and_pack.ps1`）

- `-run=cook -targetplatform=Windows -unversioned -iterate`；日志里没有 `Success - 0 error` 就停。
- 按白名单从 cooked 目录挑文件，分三个包：

| 包 | 内容 |
| --- | --- |
| `Karin_Body_P` | OldCloth001 网格、`ABP_F_OldCloth001_Implimentation`、`/Game/Mods/KarinPal/*`（MI、贴图） |
| `Karin_Face_P` | `Head/*/SK_Player_Female_Head*` |
| `Karin_HideHair_P` | `Hair/*/SK_Player_Hair*` |

- 占位资产（骨架、物理资产、父材质、`ALI_HumanCloth`）会被 cook，但不进包。
- `repak pack --version V11 --mount-point ../../../`；打印每个包的大小和 SHA256 前缀。`-Install` 复制到 `~mods`（游戏要关着）。
- iterate cook 只改 AnimBP 时日志显示的耗时可能只有零点几分钟：以 `Packages Cooked` 和成功标记为准，再读回 pak 核对参数。

## 7. 读回（`verify_paks.ps1`）

PalExport 指向自己的 pak 目录（不是游戏目录）：列文件；`skel` 核对身体骨数、脸型的形变名、隐藏发型的顶点数；
`json` 核对 AnimBP 的节点、根骨、胶囊、`PhysicsSettings` 和曲线，以及 MI 的父级和贴图引用。

## 8. 发行

```text
KarinPal_rN/
  README.md                      安装、卸载、各包作用、幻化用法、冲突、SHA256、版本记录
  Pal/Content/Paks/~mods/
    Karin_Body_P.pak
    Karin_Face_P.pak
    Karin_HideHair_P.pak
```

把 `Pal` 文件夹合并到游戏根目录即安装。另打一个同内容的 zip，用 `testzip` 检查，pak 的 SHA256 与构建机输出比对。
