# 幻兽帕鲁（Palworld）便携包

先读 [游戏知识](../../games/palworld/README.md) 和 [构建流水线](../../games/palworld/BUILD_PIPELINE.md)。pak、玩家角色组成、骨架重定向、服装层动画蓝图和面部组件的约定见 [技术合同](../../games/palworld/TECHNICAL_CONTRACTS.md)；物理节点、胶囊和离线模拟见 [Kawaii 物理](../../games/palworld/KAWAII_PHYSICS.md)；PalExport、编辑器插件和命令行 UE 见 [开发工具](../../games/palworld/DEV_TOOLING.md)。

这是 Karin_Original 替换女性玩家默认服装 `SK_Player_Female_Outfit_OldCloth001`（初期装备）的 Mod（r4）实际使用的工具：Blender 构建脚本与 KawaiiPhysics 离线模拟器、生成 UE 配置的 Python 脚本、UE 5.1 编辑器 Python、编辑器插件 PalModTools 的 C++ 源码、C# 写的 PalExport（CUE4Parse 命令行）、UE 内容工程模板和 PowerShell 工具。

- **游戏版本：** Steam App 1623730，buildid `25246127`，游戏内版本 v1.0.5.102999，UE 5.1.1。资源只有一个 legacy pak `Pal\Content\Paks\Pal-Windows.pak`（pak V11，不加密）。游戏是 unversioned cook，CUE4Parse 读它要配 usmap。
- **Mod 安装：** 三个 `*_P.pak` 放进 `Pal\Content\Paks\~mods\`（没有就新建）；不需要 `.sig`，也不需要 UE4SS。
  - `Karin_Body_P`：OldCloth001 身体网格、服装层动画蓝图 `ABP_F_OldCloth001_Implimentation`（带 KawaiiPhysics 节点）、`/Game/Mods/KarinPal/`（材质实例、贴图）；
  - `Karin_Face_P`：每个女性脸型 `SK_Player_Female_HeadNNN` → Karin 的脸，带 11 个面部变形；
  - `Karin_HideHair_P`：每个玩家发型 `SK_Player_HairNNN` → 一个不可见的三角形（Karin 的头发在身体网格里）。
- **KawaiiPhysics：** 本包**不含**它的源码。从作者仓库 pafuhana1213/KawaiiPhysics（MIT）取 **1.17.1**（`KawaiiPhysics.uplugin` 的 `VersionName` 为 `1.17.1`），整个插件目录放成 `<PAL_PROJECT>\Plugins\KawaiiPhysics\`（里面是 `KawaiiPhysics.uplugin` 和 `Source\KawaiiPhysics`、`Source\KawaiiPhysicsEd`），由 `tools/build_plugin.ps1` 和 PalModTools 一起编译。它依赖引擎自带的 StructUtils 插件（`Pal.uproject` 已启用）。游戏里的 KawaiiPhysics 与 1.17.1 属性布局相同（技术合同）；只用它编译编辑器里的动画蓝图，不进 pak。
- **PalExport：**
  - 源码在 `palexport/`，NuGet 依赖 CUE4Parse 和 CUE4Parse-Conversion `1.2.2.202610`，面向 net10.0（win-x64，`CETCompat=false`），要用 .NET 10 SDK 编译；
  - 请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包；
  - 调用：`PalExport <pak 目录> <usmap 或 -> <oo2core_9_win64.dll> <输出目录> <命令> [参数…]`，引擎版本固定 `GAME_UE5_1`；
  - 命令：`list <正则>`、`json <包>…`、`raw <包>…`、`export <uemodel|gltf|psk> <包>…`（`gltf`、`psk` 以外的写法都按 UEFormat 导出，网格得 `.uemodel`、动画得 `.ueanim`；项目写 `ue`）、`skel <包>…`、`mappings <正则>`（按名字查 usmap 里的结构和枚举）。包路径可写 `/Game/…` 或 `Pal/Content/…`；
  - 可选环境变量 `PALX_EXTRA`：用 `;` 分隔的额外目录，一起挂载（项目原有行为，没改）。
- **外部文件（自备，不随包）：** repak v0.2.3（trumank/repak）的 `repak.exe`；PalworldModding/UsefulFiles 的 usmap（Mappings 1.0.5，对应本 build）；Oodle 的 `oo2core_9_win64.dll`。默认都放在 `<PAL_WORK_ROOT>\tools\` 下，见下表。
- **UE：** 5.1.1（Epic 启动器版，CL 23901901）。编插件要 Visual Studio 的 C++ 生成工具；`build_plugin.ps1` 默认传 `-Compiler=VisualStudio2019`（项目的配置），可用 `-Compiler` 改。内容工程模板在 `ue/PalProj/`（`Pal.uproject` 和 `Config/`），工程名必须是 `Pal`，cook 出来的路径才是 `Pal/Content/…`。插件源码在 `ue/PalModTools/`。
- **Blender：** 4.2.23 LTS，装 UEFormat 插件（h4lfheart/UEFormat 的 `io_scene_ueformat`，项目用的 manifest 版本 0.10.0）读 `.uemodel` / `.ueanim`；它要 `zstandard`，Blender 4.2 自带。脚本按模块名 `io_scene_ueformat` 启用并 import 它，所以要么把 `io_scene_ueformat` 文件夹放进 Blender 的 `4.2\scripts\addons_core\`（项目这样做，`--factory-startup` 下也能启用），要么放在任意目录、用 `PAL_BLENDER_ADDONS` 指向该目录；按 4.2 的“扩展”方式安装时模块名带 `bl_ext.` 前缀，脚本找不到。FBX 导出用 Blender 自带的 `io_scene_fbx`。
- **Python：** 3.10 或更高，只有 `scripts/gen_ue_config.py` 在 Blender 外运行，需要 numpy 和 Pillow（`requirements.txt` 钉 numpy 2.5.2，要 Python 3.12 或更高；Pillow 在根目录的 `requirements.txt`）。本次在 3.14.0、numpy 2.5.2、Pillow 12.3.0 上测试。Blender 脚本用 Blender 自带的 Python 3.11 和 numpy。
- **两台机器：** 项目在本机跑 Blender（构建、预览、离线模拟），在装游戏、UE 5.1.1 和 PalExport 的构建 / 测试机上跑提取、UE 导入、cook、打包和实机测试。两边的路径都用环境变量或参数给，也可以是同一台机器。经 ssh 在构建机上调用 `pwsh -NoProfile -File …` 时，`PAL_*` 要设成构建机的用户环境变量（或每次传参数）。
- **只在 Windows 上：** UE 5.1 编辑器、UnrealBuildTool、PalExport（win-x64）和 PowerShell 工具。Blender 脚本拼接缓存路径时用反斜杠，也只在 Windows 上用过。PowerShell 命令按 PowerShell 7（`pwsh`）写；`> 文件` 重定向在 pwsh 7 里是 UTF-8，`gen_ue_config.py` 读的资产列表要用 pwsh 7 生成。
- **运行位置：** 以下命令都从交接包根目录执行。

## 环境变量与参数

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `PAL_SOURCE_VRM` | `scripts/blender/palcommon.py`，经它影响 `build_pal.py`、`render_keys.py` | 源 VRM（Karin 的是 `Karin_Original/Karin(Clone).vrm`）。没设时路径是 `<PAL_SOURCE_VRM>`，载入会报找不到文件 |
| `PAL_CACHE` | `palcommon.py`，经它影响 `build_pal.py`、`kawaii_sim.py`、`probe_run_pose.py`、`render_preview.py` | PalExport `export ue` 的输出目录，下面是 `Pal\Content\Pal\Model\Character\Player\…`：要有 `Outfit\SK_Player_Female_Outfit_OldCloth001\SK_Player_Female_Outfit_OldCloth001.uemodel`，`render_preview.py` 另要 `Head\Head001\SK_Player_Female_Head001.uemodel`。没设时同上报找不到文件 |
| `PAL_BLENDER_ADDONS` | `palcommon.py` 的 `enable_ueformat()` | 放 `io_scene_ueformat` 文件夹的目录。只在按名字启用插件失败时才加进 `sys.path` |
| `PAL_WORK_ROOT` | `tools/*.ps1` | 构建机工作目录：`tools\`（`PalExport\PalExport.exe`、`repak.exe`、`Mappings.usmap`、`oo2core_9_win64.dll`）、`UEProject\Pal\`、`scripts\`、`builds\<run>\`、`logs\`、`stage\<tag>\`、`out\<tag>\`、`extract\<子目录>\`。各脚本也接受 `-WorkRoot`。路径里不要有空格：`-script="<脚本> <参数>"` 按空格切分参数 |
| `PAL_UE_ROOT` | `run_py.ps1`、`cook_and_pack.ps1`、`build_plugin.ps1` | UE 5.1 安装目录（含 `Engine\`），或 `-UERoot` |
| `PAL_PROJECT` | 同上 | 内容工程目录（含 `Pal.uproject`，插件在它的 `Plugins\` 下），或 `-Project`；默认 `<PAL_WORK_ROOT>\UEProject\Pal` |
| `PAL_GAME_DIR` | `palx_run.ps1`、`cook_and_pack.ps1 -Install` | 游戏安装目录（含 `Pal\Content\Paks`），或 `-GameDir` |
| `PAL_USMAP` | `palx_run.ps1`、`verify_paks.ps1` | usmap 文件，或 `-Usmap`；默认 `<PAL_WORK_ROOT>\tools\Mappings.usmap` |
| `PAL_OODLE` | `palx_run.ps1`、`verify_paks.ps1` | `oo2core_9_win64.dll`，或 `-Oodle`；默认 `<PAL_WORK_ROOT>\tools\oo2core_9_win64.dll` |

其他参数：`palx_run.ps1 -Exe` 和 `verify_paks.ps1 -Exe`（默认 `<PAL_WORK_ROOT>\tools\PalExport\PalExport.exe`），`cook_and_pack.ps1 -Repak`（默认 `<PAL_WORK_ROOT>\tools\repak.exe`）、`-Tag`（默认 `dev`，也可以按位置给）、`-SkipCook`、`-Install`，`verify_paks.ps1 -Tag`，`build_plugin.ps1 -Compiler`，`run_py.ps1 <脚本> "<脚本参数>" <日志>`（按位置）。缺少必需的变量时，各工具在动手前报错并说出变量名。

## 构建流程

以新的一轮 `r5` 为例。每步的原理和检查点见 [构建流水线](../../games/palworld/BUILD_PIPELINE.md)。

### 0. 一次性准备（构建机）

```powershell
$Kit = "portable-kits/palworld"; $T = "$Kit/tools"
$env:PAL_WORK_ROOT = "<构建机工作目录，无空格>"
$env:PAL_UE_ROOT = "<UE_5.1 安装目录>"
$env:PAL_GAME_DIR = "<Steam 库>\steamapps\common\Palworld"
$R = $env:PAL_WORK_ROOT
New-Item -ItemType Directory -Force "$R/tools", "$R/scripts", "$R/builds", "$R/src" | Out-Null
# repak.exe（v0.2.3）、Mappings.usmap（1.0.5）、oo2core_9_win64.dll 放进 $R/tools/（或用 -Repak / PAL_USMAP / PAL_OODLE 指到别处）

# a) PalExport：复制到仓库外编译
Copy-Item -Recurse $Kit/palexport "$R/src/PalExport"
dotnet build "$R/src/PalExport/PalExport.csproj" -c Release -o "$R/tools/PalExport"

# b) 参照数据：输出在 $R/extract/<子目录>/ 下，保持包路径
pwsh -NoProfile -File $T/palx_run.ps1 list list "^Pal/Content/Pal/Model/Character/Player/" > "$R/player_list.txt"
pwsh -NoProfile -File $T/palx_run.ps1 ue export ue /Game/Pal/Model/Character/Player/Outfit/SK_Player_Female_Outfit_OldCloth001/SK_Player_Female_Outfit_OldCloth001 /Game/Pal/Model/Character/Player/Head/Head001/SK_Player_Female_Head001
pwsh -NoProfile -File $T/palx_run.ps1 list list "AS_Player_Female_(Sprint|Jog_None)\.uasset"     # 查动画的完整包路径
pwsh -NoProfile -File $T/palx_run.ps1 anim export ue "<冲刺动画包>" "<慢跑动画包>"                   # .ueanim，给离线模拟和姿势探针
pwsh -NoProfile -File $T/palx_run.ps1 dump json /Game/Pal/Blueprint/Character/Player/Imp_Cloth/ABP_F_OldCloth001_Implimentation   # 可选：原版服装层，对照用

# c) UE 内容工程和插件
Copy-Item -Recurse $Kit/ue/PalProj "$R/UEProject/Pal"
New-Item -ItemType Directory -Force "$R/UEProject/Pal/Plugins" | Out-Null
Copy-Item -Recurse $Kit/ue/PalModTools "$R/UEProject/Pal/Plugins/PalModTools"
# KawaiiPhysics 1.17.1 自己取来，放成 $R/UEProject/Pal/Plugins/KawaiiPhysics/KawaiiPhysics.uplugin（见上文）
pwsh -NoProfile -File $T/build_plugin.ps1                   # EXIT 0，末尾列出两个插件 Binaries\Win64 下的文件
Copy-Item $Kit/scripts/ue/*.py "$R/scripts/"
```

把 `$R/extract/ue`（整个目录，里面是 `Pal/Content/…`）、`.ueanim` 和 `player_list.txt` 复制到本机。

### 1–4. 本机：Blender 构建、UE 配置、预览、离线物理模拟

```powershell
python -m pip install -r requirements.txt -r portable-kits/palworld/requirements.txt
$Kit = "portable-kits/palworld"
$Blender = "<Blender 4.2.23 目录>\blender.exe"
$env:PAL_CACHE = "<复制来的 extract\ue 目录>"
$env:PAL_SOURCE_VRM = "<源模型目录>\Karin_Original\Karin(Clone).vrm"
# $env:PAL_BLENDER_ADDONS = "<放 io_scene_ueformat 的目录>"   # UEFormat 不在 addons_core 里时
$Sprint = "<AS_Player_Female_Sprint.ueanim>"
New-Item -ItemType Directory -Force ../MyMod/runs | Out-Null
$Run = (Resolve-Path ../MyMod/runs).Path + "\r5"          # Blender 的输出目录用绝对路径

# 1. 构建：日志末尾有 BUILD_OK 才算成功
& $Blender --background --factory-startup --python $Kit/scripts/blender/build_pal.py -- $Run *> "$Run.build.log"
Select-String -Quiet BUILD_OK "$Run.build.log"
# 看 $Run/report.json：warnings 为空，groups_not_bones 两个网格都为空，joint_mismatch_cm 为 0，bones（r3 为 189）

# 2. UE 配置：ue_config.json 和 textures/ 下 6 张 4×4 辅助贴图；打印脸型、发型数
python -B $Kit/scripts/gen_ue_config.py $Run "<player_list.txt>"

# 3. 预览（可选）：preview/ 下全身正侧面（旁边是原版）和每个面部变形；probe/ 下髋部五个视角（裙子不模拟，最坏情况）
& $Blender --background --factory-startup "$Run/build.blend" --python $Kit/scripts/blender/render_preview.py -- $Run
& $Blender --background --factory-startup "$Run/build.blend" --python $Kit/scripts/blender/render_views.py -- $Run back:0,400,85:90,0,180:200
& $Blender --background --factory-startup --python $Kit/scripts/blender/render_keys.py -- ../MyMod/keys blink smile kuchi_A
& $Blender --background --factory-startup "$Run/build.blend" --python $Kit/scripts/blender/probe_run_pose.py -- $Run $Sprint sprint

# 4. 离线物理模拟：按 scripts/physics_tune.json 合并、模拟、导出 AnimBP 要用的参数文件
& $Blender --background --factory-startup "$Run/build.blend" --python $Kit/scripts/blender/kawaii_sim.py -- $Run $Sprint r5 "export=$Run/physics_r5.json"
```

- `render_views.py` 每个视角写成 `名字:x,y,z:rx,ry,rz:正交宽度`（相机位置 cm、欧拉角度）。角色面向 −Y。
- `render_keys.py` 渲染源 VRM 脸上的单个形态键（`k00.png`、`k01.png`…），挑面部变形配方用。
- 项目的原始用法里只有 `build_pal.py` 加 `--factory-startup`；`kawaii_sim.py` 加不加结果相同（本次核对过），建议都加，避免载入用户装的第三方插件。

### 5–8. 构建机：UE 导入、动画蓝图、cook / pak、读回、安装

```powershell
# 5. 上传：$Run 下的 Karin_Body.fbx、Karin_Head.fbx、Hidden.fbx、ue_config.json、physics_r5.json 和整个 textures/ 放到 $R/builds/r5/
# 6. 导入网格、贴图、材质实例和占位资产；结尾 [KARIN] IMPORT_OK
pwsh -NoProfile -File $T/run_py.ps1 "$R/scripts/ue_import.py" "$R/builds/r5" "$R/logs/import_r5.log"
#    服装层动画蓝图：一定要给第二个参数（解析后的参数文件）；compile 必须 errors=0，结尾 [KARIN] ABP_OK
pwsh -NoProfile -File $T/run_py.ps1 "$R/scripts/ue_build_abp.py" "$R/builds/r5 $R/builds/r5/physics_r5.json" "$R/logs/abp_r5.log"

# 7. cook 和打包：日志里没有 'Success - 0 error' 就停；打印每个包暂存的文件、大小和 SHA256 前 16 位
pwsh -NoProfile -File $T/cook_and_pack.ps1 -Tag r5            # 输出 $R/out/r5/Karin_Body_P.pak、Karin_Face_P.pak、Karin_HideHair_P.pak

# 8. 读回：PalExport 只挂载自己的 pak（$R/out/r5），dump 到 $R/extract/verify_r5/
pwsh -NoProfile -File $T/verify_paks.ps1 -Tag r5
#    核对：身体骨数、脸型的 11 个形变名、隐藏发型 3 个顶点；AnimBP 的 Kawaii 节点、根骨、胶囊、PhysicsSettings 和曲线；MI 的父级和贴图

# 安装（游戏要关着）：复制到 <PAL_GAME_DIR>\Pal\Content\Paks\~mods\
pwsh -NoProfile -File $T/cook_and_pack.ps1 -Tag r5 -SkipCook -Install
```

- `ue_import.py` 第一次运行时工程里还没有骨架：让导入器从 FBX 建骨架和物理资产，再改名搬到游戏的 `SK_PalHuman_Skeleton`、`SK_Player_Female_PhysicsAsset` 路径上当占位；之后都用这个占位骨架。每次重新导入前先删旧网格。脸只导入一次（Head001），再复制到每个女性脸型路径；不可见网格同样从 Hair001 复制到每个发型路径。
- `ue_build_abp.py` 每次删掉并重建 `ABP_F_OldCloth001_Implimentation`；占位的 `ALI_HumanCloth` 只在第一次建。不给第二个参数时它读 `<run>/physics.json`，那是 `build_pal.py` 的默认动力学，不是调好的参数。
- 占位资产（骨架、物理资产、父材质、`ALI_HumanCloth`）会被 cook，但不在白名单里，不进 pak。
- `-iterate` cook 只改动画蓝图时，日志里的耗时可能只有零点几分钟；以成功标记为准，再用 `verify_paks.ps1` 读回核对参数。

### 只调物理

物理参数的唯一来源是 `scripts/physics_tune.json`（Karin r4 的值）。网格不变时不用重跑 `build_pal.py` 和 `ue_import.py`：

1. 改 `scripts/physics_tune.json`；试方案时也可以不改文件，用 `set.<组>.<键>=<JSON 值>` 临时覆盖（例如 `set.skirt.limit_angle=60`）。
2. 本机跑 `kawaii_sim.py`，比较各方案的 `RESULT` 行；选定后带 `export=<run>/physics_rN.json` 再跑一次。
3. 上传 `physics_rN.json`，跑 `ue_build_abp.py "<run> <physics_rN.json>"`。
4. `cook_and_pack.ps1 -Tag rN`，`verify_paks.ps1 -Tag rN`，`-SkipCook -Install` 安装，实机看。

r4 就是 r3 的网格加 `physics_r4.json`。

### `kawaii_sim.py` 的选项

```text
blender --background <run>/build.blend --python kawaii_sim.py -- <run_dir> <anim.ueanim> <tag> [键=值 …]
```

| 键 | 默认 | 作用 |
| --- | --- | --- |
| `speed` | `700` | 组件前进速度（cm/s），给 Kawaii 的世界移动跟随 |
| `tune` | `scripts/physics_tune.json` | 参数文件 |
| `groups` | `skirt` | 模拟哪些组（逗号分隔）；导出文件总是包含全部组 |
| `loops` | `3` | 动画循环次数，只测最后一圈 |
| `fps` | `60` | 模拟步长 |
| `set.<组>.<键>` | — | 覆盖参数文件里的一个值（值按 JSON 解析） |
| `export` | — | 写出解析后的参数文件（run 的 `physics.json` 几何 + 参数文件的动力学，即被模拟的那一份），`ue_build_abp.py` 从它生成 |
| `render` | `0` | `1`：重跑到最差的一步，在 `<run>/sim/` 渲染四个视角，并打印该步陷进去的顶点、关节到胶囊的距离和胶囊位置 |
| `dumpbones` | `skirtA_0,skirtB_0` | `render=1` 时打印哪些骨（名字片段，只看右侧 `_r`） |
| `bind` | — | `1`：不用动画，固定在 bind 姿势 |
| `nopen` | — | `1`：不算穿模指标 |
| `dbg` | — | 组名：每 15 步打印该组前 9 根骨的角度和位置 |

`RESULT` 行：最后一圈里每帧平均有多少裙摆顶点（裙摆骨权重 > 0.5）在大腿肉（`thigh_l` + `thigh_r` 权重 > 0.3 的面）里面、其中深于 1 cm 的有多少、最深的一帧和深度，以及裙摆链偏离动画方向的最大角度（前、后按 bind 姿势的 Y 分）。`FLARE` 行是每组的最大和平均偏离角。用 Karin r3 的网格和 r4 参数、冲刺动画、默认 700 cm/s：`13.8`（深于 1 cm 的 `11.3`），最差 16 个顶点、5.95 cm，前 65.0°、后 56.4°（项目记录里 r3 参数是 52.9）。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/blender/build_pal.py` | Blender 内运行的构建入口：导入原版 OldCloth001（取 65 根基础骨）和源 VRM；新骨架用原版朝向、Karin 的位置（默认 ×1.30，`--scale`），每根 Karin 骨一个刚体变换把网格重摆上去；权重映射到 PalHuman 骨（Spine / Chest 按高度分给 `spine_01..03`）；物理链改名到游戏骨架的 NPC 配件链；烘焙 11 个面部变形；裙子加反向面；材质改名合并；导出贴图；VRM 碰撞体 → 胶囊，写 `physics.json`；不可见网格；写 `Karin_Body.fbx`、`Karin_Head.fbx`、`Hidden.fbx`、`report.json`、`build.blend` |
| `scripts/blender/palcommon.py` | 机器路径（环境变量）、启用 UEFormat、导入 `.uemodel` |
| `scripts/blender/kawaii_sim.py` | KawaiiPhysics 1.17.1 每帧步进的 Python 移植（速度、世界移动跟随、重力、刚度、胶囊碰撞、可选的 XPBD 环约束、角度限制、长度），用游戏动画（只取旋转的重定向）驱动 `build.blend`，量裙摆穿进大腿的程度；`export=` 写出 AnimBP 用的参数文件 |
| `scripts/physics_tune.json` | 7 个 Kawaii 组的动力学（阻尼、刚度、世界跟随、半径、角度限制、重力、沿链的曲线）和裙摆的显式胶囊（UE bind 姿势的组件空间）；Karin r4 的值 |
| `scripts/blender/probe_run_pose.py` | 用游戏动画把 `build.blend` 摆到左右屈髋最大的帧（或指定帧），渲染髋部五个视角；裙子骨不模拟 |
| `scripts/blender/render_preview.py` | 全身正、侧面（旁边放原版 OldCloth001 和 Head001）和每个面部变形的 Workbench 预览 |
| `scripts/blender/render_views.py` | 按参数给的相机位置、角度和正交宽度补拍视角 |
| `scripts/blender/render_keys.py` | 渲染源 VRM 脸上的单个形态键 |
| `scripts/gen_ue_config.py` | 写 `<run>/ue_config.json`（贴图、四个材质实例及其游戏父级、脸型和发型路径表、背部武器插槽）和 6 张 4×4 辅助贴图（平法线、黑遮罩、三种粗糙度的 MetallicRoughnessOcclusionSpecular、皮肤 SSS 颜色） |
| `scripts/ue/ue_import.py` | UE 编辑器 Python：导入身体（建占位骨架和物理资产）、贴图、占位母材质和父 MIC、自己的 MI；按槽名指定材质；挂物理资产和插槽；脸复制到所有女性脸型路径，不可见网格复制到所有发型路径 |
| `scripts/ue/ue_build_abp.py` | UE 编辑器 Python：建占位 `ALI_HumanCloth`，重建服装层动画蓝图 `ABP_F_OldCloth001_Implimentation`（InPose → 每组一个 KawaiiPhysics 节点 → Root），设根骨、`PhysicsSettings`、重力、曲线和胶囊（组件空间换到骨空间），编译并读回，写 `abp_graph.txt` |
| `tools/palx_run.ps1` | 对游戏 pak 运行 PalExport（usmap、Oodle 见上表） |
| `tools/run_py.ps1` | 用 commandlet 跑 UE Python，从日志里筛出 `[KARIN]`、错误和 Python 行 |
| `tools/cook_and_pack.ps1` | `-unversioned -iterate` cook；按白名单从 cooked 目录挑文件，分三个包；`repak pack --version V11 --mount-point ../../../`；`-Install` 复制到 `~mods` |
| `tools/verify_paks.ps1` | 用 PalExport 只读自己的 pak：列文件、`skel`、`json` dump |
| `tools/build_plugin.ps1` | 用 UnrealBuildTool 编译工程的编辑器目标（KawaiiPhysics 和 PalModTools） |
| `palexport/` | PalExport 源码（`Program.cs`、`PalExport.csproj`） |
| `ue/PalModTools/` | 编辑器插件源码（`unreal.PalGraphLib`，剑星项目 SBGraphLib 的 UE 5.1 移植）：按名字取图、列图和节点、加删节点、读引脚和设引脚默认值、读写嵌套属性（导出文本）、连线、重建节点、加成员变量、实现接口、加动画层、编译、导出图文本；读网格和骨架的参考姿势、换骨架、设插槽、列变形 |
| `ue/PalProj/` | 内容工程模板：`Pal.uproject`（PythonScriptPlugin、EditorScriptingUtilities、StructUtils、KawaiiPhysics、PalModTools，关掉 VR 插件）和 `Config/*.ini`（`bShareMaterialShaderCode=False`、不用 IoStore、不监视内容目录） |

脚本注释里的 `scripts/kawaii_sim.py`、`ue/ue_import.py` 等指项目原来的目录；本包里 Blender 脚本在 `scripts/blender/`，UE 脚本在 `scripts/ue/`，PowerShell 在 `tools/`。注释里的 `SB r12`、`SB r14`、`SB r15` 和 SB project 指剑星（Stellar Blade，完整仓库的 `games/stellar-blade/`，单游戏导出里没有）项目的轮次和结论。

## 输出与本机信息

- **中间结果：**
  - FBX 记有输出目录，`build.blend` 记有贴图的保存路径；
  - `kawaii_sim.py` 导出的参数文件在 `tune` 字段记有参数文件的绝对路径；
  - 日志、`player_list.txt` 和 PalExport 的 dump 记有本机和构建机路径。

  这些文件分享前要处理，不要收进本仓库。`report.json`、`physics.json`、`ue_config.json` 里没有本机路径。
- **发行物：** pak 里是 cook 后的资产，路径都是 `Pal/Content/…`；pak 里的资产没有逐个查本机路径。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时，要按新模型的骨名、网格、形态键、材质和碰撞体重写：

- `build_pal.py`：`--scale` 默认 1.30，`BODY_MESHES` / `HEAD_MESHES`（VRM 里的对象名，脸是叫 `Body` 的对象），`KMAP`（VRM 人形骨名 → PalHuman 骨），`BAKE_KEYS`，`FACE_MORPHS`（形态键配方），`SKEL_CHAINS`（Karin 的链头 → 游戏骨架的配件链），`MAT_RENAME`，`DRIVE`（VRM 碰撞体 → 驱动骨），各组的默认动力学和用哪些碰撞体，`CAP_MARGIN`；
- `scripts/physics_tune.json`：r4 的参数和裙摆胶囊（在 Karin 的 bind 姿势上量的）；
- `kawaii_sim.py`：穿模指标认的骨名（含 `skirt` 的组、`thigh_l` / `thigh_r`）、默认速度 700 cm/s、渲染相机；
- `gen_ue_config.py`：辅助贴图的数值（原版均值）、材质实例和贴图名、插槽偏移 ×0.85（Karin 躯干厚度）；
- `ue_import.py`：`/Game/Mods/KarinPal`、占位母材质的参数表；
- `cook_and_pack.ps1`：三个 pak 名和白名单；`verify_paks.ps1`：读回的包路径。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 资产路径：OldCloth001 网格、`SK_PalHuman_Skeleton`、`SK_Player_Female_PhysicsAsset`、`ALI_HumanCloth` 和层名 `ClothLayer`、`ABP_F_OldCloth001_Implimentation`，以及三个父材质（`MI_PalLit_HumanSkin`、`MI_Player_Hair001`、`MI_Player_Female_Outfit_OldCloth001_v01_M01`）和它们的参数名；
- 脸型和发型的数量（本 build 有 26 个女性脸型、37 个发型）：每次用新的资产列表重跑 `gen_ue_config.py`；
- `SK_PalHuman_Skeleton` 里的 NPC 配件链（`SKEL_CHAINS` 用到的骨名和父子关系）；
- `PalFacialComponent` 按名字驱动的 11 个形变名；
- 游戏里 KawaiiPhysics 的版本和属性布局；usmap 版本；pak 版本和压缩方式。

## 已验证与边界

- **实机。** r3 进游戏：加载、脸对齐、物理在跑，眨眼经用户确认；用户判手感偏硬（耳朵尤其），跑动时大腿根穿出裙片。r4（r3 网格 + 按离线模拟重调的参数）装进游戏能加载，手感待用户判断。其余表情，游泳、滑翔、战斗中的裙摆没有测。
- **便携版本身只做了离线验证（2026-10-13）：**
  - `kawaii_sim.py`：在项目 r3 构建（`build.blend`、`physics.json`）的副本上，用冲刺动画和本包的 `physics_tune.json` 带 `export=` 运行，导出文件除 `tune` 那一行外与项目的 `physics_r4.json` 逐字节相同；同一输入下原脚本和本包脚本的 `NODE`、`RESULT`、`FLARE` 行相同（冲刺和慢跑各一次），加 `--factory-startup` 也相同；
  - `build_pal.py`：用同一个源 VRM 和缓存，原脚本和本包脚本各构建一次：`physics.json`、`report.json` 和 5 张贴图逐字节相同，也与项目 r3 的相同；FBX 和 `build.blend` 的字节因路径不同而不同，在 Blender 里比较网格、权重、法线、UV、形态键、材质和骨架数据，三者相同；
  - `gen_ue_config.py`：用项目的资产列表重跑，`ue_config.json` 和 6 张辅助贴图与原脚本的输出逐字节相同，也与项目 r3 的相同；
  - PowerShell 工具：过了 PowerShell 解析器；缺环境变量时都在动手前报错；用假的 PalExport 和 repak 跑了 `palx_run.ps1`、`verify_paks.ps1`、`cook_and_pack.ps1 -SkipCook -Install`（参数转发、默认路径、白名单分包、安装）；
  - UE 一侧（`run_py.ps1`、`build_plugin.ps1`、真实 cook、`scripts/ue/*.py`）、插件（C++）和 PalExport（C#）没有重跑，只核对了改动；`render_preview.py`、`render_views.py`、`render_keys.py`、`probe_run_pose.py` 与原文件逐字节相同，没有重跑；
  - 详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中有帕鲁合成测试，不需要游戏、Blender 或 UE：`kawaii_sim.py` 的参数合并和曲线（从源码里单独编译这两个函数），`physics_tune.json` 的结构和取值、与 `build_pal.py` 的组名和 `ue_build_abp.py` 读的键对得上，`gen_ue_config.py` 的路径表和辅助贴图，PowerShell 工具的环境变量检查和白名单分包（要 pwsh 7 和 Windows，否则跳过），PROVENANCE 哈希和本包里没有本机路径。
- **测试没覆盖的部分：** Blender 脚本只做语法检查和上面两个函数；UE Python、真实的 UE / PalExport / repak 调用、C++ 插件和 PalExport 不在 Python 测试里。
- **便携改动：**
  - 去掉写死的本机路径，改为环境变量或参数（见上表）；
  - `kawaii_sim.py` 的默认参数文件改为本包的 `scripts/physics_tune.json`；
  - `gen_ue_config.py` 补上了 argparse，位置参数不变；
  - 换行统一成 LF。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md)。
- **没有收进本包：**
  - KawaiiPhysics 1.17.1 的源码（第三方，MIT，自己取）；
  - 一次性探针：`probe_frames.py`（打印原版和 Karin 骨架的骨朝向，用来定骨架合同），`ue_debug_mat.py`（查占位母材质和 MI 参数，UE 5.1 的 `set_material_instance_texture_parameter_value` 成功也返回 False，结论已写进 `ue_import.py` 的注释）；
  - 源模型、参考 mod、游戏数据、提取出的 JSON / uemodel / ueanim、usmap、Oodle DLL、生成的贴图、FBX、blend、pak 和发行包。
- **署名：** PalExport 建立在 FabianFG 的 CUE4Parse（NuGet 包）上，Blender 端读 `.uemodel` / `.ueanim` 用 h4lfheart 的 UEFormat，物理节点是 pafuhana1213 的 KawaiiPhysics，打包用 trumank 的 repak；本包都不含它们的代码，见 [工具来源](../../references/TOOL_SOURCES.md)。
