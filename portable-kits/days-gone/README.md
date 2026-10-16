# 往日不再（Days Gone）便携包

先读 [游戏知识](../../games/days-gone/README.md) 和 [构建流程](../../games/days-gone/BUILD_PIPELINE.md)。pak、外观（look）、骨架、材质实例和动画蓝图的约定见 [技术合同](../../games/days-gone/TECHNICAL_CONTRACTS.md)；脸部关节、眨眼和口型见 [面部与口型](../../games/days-gone/FACE_AND_LIPSYNC.md)；头发、耳朵、尾巴和裙摆的 AnimDynamics 见 [物理](../../games/days-gone/PHYSICS.md)；DgExport、UE 4.11 和构建机上的工具见 [开发工具](../../games/days-gone/DEV_TOOLING.md)。

这是 Karin_Original（VRM）替换主角迪肯（Deacon）的 Mod（t31）实际使用的工具：Blender 构建脚本（身体、面部权重、眼睑骨、口型权重）、改写烘焙后资产的 Python 工具（参考骨架、根骨姿势、材质实例、外观、顶点缓冲、动画蓝图）和 pak v3 读写、C# 写的 DgExport（CUE4Parse 命令行）、案例配置，以及构建机上的 PowerShell 工具。

- **游戏版本：** Steam App 1259420，beta 分支 `days_gone_classic`（build 10034136）。引擎是 Bend 改过的 UE 4.11：游戏包是 FileVersionUE4 500、licensee 34（名字表带哈希），UE 4.11 原版 cook 的包（498、licensee 0）游戏也能读。主 pak `BendGame\Content\Paks\BendGame-WindowsNoEditor.pak`：pak v3、zlib，挂载点 `../../../BendGame/Content/`。
- **Mod 安装：** `zz_Karin_P.pak` 放进 `BendGame\Content\Paks\~mods\`，并把 `BendGame\Content\sfpaks\startuppackages.pak` 改名为 `disabled_startuppackages.pak`（与参考 mod 相同，只做一次）。Karin 的全部几何都在头部网格 `deacon_head_standard` 里：它是迪肯 66 个外观的主姿势部件（master part），这些外观的其余部件网格置空。
- **DgExport：**
  - 源码在 `dgexport/`，NuGet 依赖 CUE4Parse 和 CUE4Parse-Conversion `1.2.2.202610`，面向 net10.0（win-x64，`CETCompat=false`），要用 .NET 10 SDK 编译；请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包；
  - 调用：`DgExport <pak 目录> <输出目录> <命令> [参数…]`。命令：`list <正则>`、`json <包>…`、`raw <包>…`（原样保存包）、`export <uemodel|gltf|psk> <包>…`、`skel <包>…`（参考骨架、重定向模式、变形、材质槽和 LOD 段的 JSON）、`anim <包>…`、`file <路径>…`。包路径写 `BendGame/Content/…` 或 `/Game/…`；
  - 环境变量：`DGX_GAME`（CUE4Parse 的引擎版本，默认 `GAME_DaysGone`；读 UE 4.11 原版 cook 的 mod 包用 `GAME_UE4_11`）、`DGX_EXTRA`（`;` 分隔的额外挂载目录）。在 Git Bash 里调用要设 `MSYS_NO_PATHCONV=1`，否则 `/Game/…` 会被改写；
  - 局限：游戏的面部动画（FaceMoods、口型 viseme，`AKF_PerTrackCompression`）CUE4Parse 解成常量轨道，要用 `scripts/anim_pertrack.py` 解 `raw` 存下的包；游戏贴图是 Bend 自己的格式，CUE4Parse 解不出（Karin 的贴图走 UE 4.11 原版 cook）。
- **UE：** 4.11.2（Epic 启动器版）。内容工程必须叫 `BendGame`，cook 出来的路径才是 `BendGame/Content/…`；本包不带工程模板，在编辑器里新建空白工程即可。UE 4.11 没有编辑器 Python，导入在编辑器里手工做（第 3 步）。编辑器开着 `BendGame` 工程时游戏约 2 秒后退出，启动游戏前先关编辑器。
- **Blender：** 4.2.23 LTS，装 UEFormat 插件（h4lfheart/UEFormat 的 `io_scene_ueformat`，项目用的 manifest 版本 0.10.0）读 `.uemodel`：`build_body.py`、`face_rig.py`、`export_dummy_skeleton.py` 和带 `.uemodel` 参照的 `render_preview.py` 要用它。脚本按模块名启用插件，所以 `io_scene_ueformat` 文件夹要放在 Blender 的 `4.2\scripts\addons_core\`（项目这样做，`--factory-startup` 下也能启用）。VRM 用 Blender 自带的 glTF 导入器读，FBX 用自带的 `io_scene_fbx` 写。Blender 脚本用 Blender 自带的 Python 3.11 和 numpy。
- **Python：** 3.10 或更高。`scripts/` 下的包和 pak 工具（`paklist.py`、`pakextract.py`、`pakwrite.py`、`uhdr.py`、`upkg.py`、`retarget_imports.py`、`fix_root_pose.py`、`patch_looks.py`，以及不带 `--normals` 的 `make_pak.py`）只用标准库，其余要 numpy（`requirements.txt` 钉 numpy 2.5.2，要 Python 3.12 或更高）。本次在 Python 3.14.0 + numpy 2.5.2 和 Blender 4.2 自带的 Python 3.11.7 + numpy 1.24.3 上测试。
- **pak 字节与 zlib 有关：** 项目用 Blender 自带的 Python（zlib 1.2.13）跑 `make_pak.py`。Python 3.14 的 Windows 版用 zlib-ng，压出的 pak 字节不同，解开后的文件相同。要逐字节复现项目的 pak，就用 Blender 的 Python。
- **两台机器：** 项目在本机跑 Blender 和 Python 工具，在装游戏和 UE 4.11.2 的构建 / 测试机上跑 DgExport、编辑器导入、cook、安装和实机测试。两边的路径都用环境变量或参数给，也可以是同一台机器。
- **只在 Windows 上：** UE 4.11 编辑器、DgExport（win-x64）和 PowerShell 工具（按 PowerShell 7 `pwsh` 写）。`set_resolution.ps1`、`watch_launch.ps1` 要在游戏所在的用户桌面会话里运行。
- **运行位置：** 以下命令都从交接包根目录执行。

## 环境变量与参数

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `DG_CACHE` | `scripts/dgpaths.py`，经它影响 `make_pak.py`、`lid_calib.py`（或 `--cache`）和 Blender 的 `build_body.py`（没给 `--target` 时）、`face_rig.py`、`blink_rig.py`、`mouth_rig.py`、`viseme_sim.py` | 本机缓存根目录（第 0 步 DgExport 的输出复制过来），下面要有：`deacon_master_Skeleton.deacon_master_Skeleton.skel.json`（游戏骨架的 `skel` dump）；`anim/raw/animj/BendGame/Content/Animation/Deacon/…`（面部动画、口型和参考姿势的 raw 包）；`ue/BendGame/Content/Characters/Deacon/parts/head/deacon_head_standard.uemodel`；`raw/BendGame/Content/Characters/Deacon/parts/head/mi_deacon_head.uasset`、`mi_deacon_eyelash_hair.uasset`（`make_pak.py` 复制的游戏材质实例）；`looks/BendGame/Content/Characters/Deacon/looks/*.uasset`（66 个外观）。没设时脚本报错并说出变量名，不会退回到哪个本机路径 |
| `DG_MODELS_DIR` | `dgpaths.py`，经它影响 `build_body.py` | 源模型根目录，下面是 `Karin_Original/Karin(Clone).vrm` |
| `DG_WORK_ROOT` | `tools/*.ps1` | 构建机工作目录：`out\`（DgExport 输出、cook 日志、`watch.txt`）、`staging\`（待装的 pak）、`disabled_mods\`（换下来的 pak）、`tools\DgExport\`、`U411\BendGame\`（默认工程位置）。各脚本也接受 `-WorkRoot` |
| `DG_GAME_DIR` | `dgx_run.ps1`、`install_pak.ps1` | 游戏安装目录（含 `BendGame\Content\Paks`），或 `-GameDir` |
| `DG_UE_ROOT` | `cook.ps1`、`ue_editor.ps1` | UE 4.11 安装目录（含 `Engine\`），或 `-UERoot` |
| `DG_PROJECT` | 同上 | 内容工程目录（含 `BendGame.uproject`），或 `-Project`；默认 `<DG_WORK_ROOT>\U411\BendGame` |
| `DGX_GAME`、`DGX_EXTRA` | DgExport（`dgx_run.ps1` 原样传下去） | 见上文 |

其他参数：`dgx_run.ps1 -Exe`（默认 `<DG_WORK_ROOT>\tools\DgExport\DgExport.exe`），`install_pak.ps1 -Name`（默认 `zz_Karin_P`），`watch_launch.ps1 -OutDir`（默认 `<DG_WORK_ROOT>\out`），`set_resolution.ps1 [宽] [高] -ModesFile <文件>`，`lid_calib.py --skeleton / --anim / --ref / --joints / --out`，`build_body.py --target / --scale / --variant / --name / --prop / --head-drop`，`face_rig.py --check / --keep-joints`。缺少必需的变量时，各工具报错并说出变量名：Python 工具在写任何文件之前报错；Blender 脚本可能已经建好了空的输出目录。`cook.ps1` 把日志路径作为一个 `-abslog=<路径>` 参数交给 UE，工作目录和工程路径里不要有空格。

## 构建流程

按 t31 的做法写。每个 Blender 阶段读上一阶段的 `build.blend`，写出自己的 `build.blend`、`deacon_head_standard.fbx` 和报告；眨眼和口型阶段还要读上一阶段导进 UE、cook 出来的网格（Head 关节的朝向和脸部关节的位置以 cook 结果为准）。项目各轮的目录：t7（`build_body.py`）→ t11（`face_rig.py`）→ t29（`blink_rig.py`）→ t30（`mouth_rig.py`）→ t31（只改 `springs.json`，没有重新导入）。每步的原理和检查点见 [构建流程](../../games/days-gone/BUILD_PIPELINE.md)。

### 0. 一次性准备（构建机）

```powershell
$Kit = "portable-kits/days-gone"; $T = "$Kit/tools"
$env:DG_WORK_ROOT = "<构建机工作目录，无空格>"
$env:DG_GAME_DIR = "<Steam 库>\steamapps\common\Days Gone"
$env:DG_UE_ROOT = "<UE_4.11 安装目录>"
$R = $env:DG_WORK_ROOT
New-Item -ItemType Directory -Force "$R/tools", "$R/out", "$R/staging", "$R/disabled_mods", "$R/src" | Out-Null

# a) DgExport：复制到仓库外编译
Copy-Item -Recurse $Kit/dgexport "$R/src/DgExport"
dotnet build "$R/src/DgExport/DgExport.csproj" -c Release -o "$R/tools/DgExport"

# b) 参照数据：输出在 $R/out/<子目录>/ 下，保持包路径
$D = "BendGame/Content/Characters/Deacon"; $A = "BendGame/Content/Animation/Deacon"
pwsh -NoProfile -File $T/dgx_run.ps1 skel skel "$D/deacon_master_Skeleton"
pwsh -NoProfile -File $T/dgx_run.ps1 ue export uemodel "$D/parts/head/deacon_head_standard"
pwsh -NoProfile -File $T/dgx_run.ps1 raw raw "$D/deacon_master_Skeleton" "$D/parts/head/mi_deacon_head" "$D/parts/head/mi_deacon_eyelash_hair" "$A/Deacon_VimBlueprint"
$looks = pwsh -NoProfile -File $T/dgx_run.ps1 list list "^$D/looks/[^/]+\.uasset$"
pwsh -NoProfile -File $T/dgx_run.ps1 looks raw @looks
$anims = pwsh -NoProfile -File $T/dgx_run.ps1 list list "^$A/(facial/FaceMoods/|misc/dcn_ref_pose|vo/lipsync/dcn_visemes-)"
pwsh -NoProfile -File $T/dgx_run.ps1 animj raw @anims

# c) UE 4.11.2：在编辑器里新建空白工程 BendGame，放在 $R/U411/BendGame（或用 DG_PROJECT 指到别处）
```

把这些复制到本机的 `DG_CACHE`：`$R/out/skel/…/deacon_master_Skeleton.deacon_master_Skeleton.skel.json` 放在根目录；`$R/out/ue`、`$R/out/raw`、`$R/out/looks` 分别放成 `ue/`、`raw/`、`looks/`；`$R/out/animj` 放成 `anim/raw/animj/`。`raw` 里的 `Animation/Deacon/Deacon_VimBlueprint.uasset` 是第 5 步 `abp_springs.py` 的输入。

### 1–2. 本机：身体和脸

```powershell
python -m pip install -r requirements.txt -r portable-kits/days-gone/requirements.txt
$Kit = "portable-kits/days-gone"
$Blender = "<Blender 4.2.23 目录>\blender.exe"
$env:DG_CACHE = "<本机缓存目录>"
$env:DG_MODELS_DIR = "<源模型根目录>"
New-Item -ItemType Directory -Force ../MyMod/runs | Out-Null
$Runs = (Resolve-Path ../MyMod/runs).Path          # Blender 的输出目录用绝对路径

# 1. 身体：日志里有 BUILD_OK 才算成功。variant B 把 Karin 的次级链留成 KO_* 骨（物理要用）
& $Blender --background --factory-startup --python $Kit/scripts/blender/build_body.py -- "$Runs/body" --variant B *> "$Runs/body.log"
#    一次性：迪肯头部网格和骨架的 FBX，导进 UE 做 deacon_master 占位（DUMMY_OK）
& $Blender --background --factory-startup --python $Kit/scripts/blender/export_dummy_skeleton.py -- "$env:DG_CACHE\ue\BendGame\Content\Characters\Deacon\parts\head\deacon_head_standard.uemodel" "$Runs/dummy_deacon.fbx"
#    预览（可选）：正、侧、背面，可以把参照模型（.uemodel 或 .glb）放在旁边
& $Blender --background --factory-startup "$Runs/body/build.blend" --python $Kit/scripts/blender/render_preview.py -- "$Runs/body"

# 2. 脸：面部权重取自迪肯变形到 Karin 脸上的头部网格，face_* 关节移到 Karin 脸上（--keep-joints 则保留迪肯的位置）；
#    FACE_RIG_OK；--check 渲染张嘴测试
& $Blender -b "$Runs/body/build.blend" --python $Kit/scripts/blender/face_rig.py -- "$Runs/face" --check
#    给 make_pak.py 的两份数据：VRM 自定义法线（--normals），裙子下的皮肤内缩最多 2 cm（--positions）
& $Blender -b "$Runs/face/build.blend" --python $Kit/scripts/blender/dump_loop_normals.py -- "$Runs/face/loop_normals.npz"
& $Blender -b "$Runs/face/build.blend" --python $Kit/scripts/blender/skirt_body_shrink.py -- "$Runs/face/body_shrink.npz" 2.0
```

### 3. 构建机：导入和 cook（每个 Blender 阶段之后各做一次）

在编辑器里手工导入（`ue_editor.ps1` 打开工程）：

- 第一次：`dummy_deacon.fbx` 导入为 `/Game/Characters/Deacon/deacon_master`（同时生成 `deacon_master_Skeleton`）。
- `deacon_head_standard.fbx` 导入为 `/Game/Characters/Deacon/parts/head/deacon_head_standard`。导入器自己建一个 `deacon_head_standard_Skeleton`，`make_pak.py` 会把网格的骨架引用改到游戏的 `deacon_master_Skeleton`。法线按默认的“Compute Normals”导入，VRM 的自定义法线由 `make_pak.py --normals` 写回。以后各阶段用 Reimport 覆盖同一个资产（项目每次先把旧资产备份到 `$R\backup\<轮次>_assets`）。
- `build_body.py` 写出的 `textures/Karin_{Face,Alpha,Body,Hair,Costume}.png` 导入为 `/Game/Karin/Materials/Karin_*`。网格的材质槽顺序是 Face、Alpha、Body、Hair、Costume，`make_pak.py` 按这个顺序给游戏材质实例的副本。

```powershell
pwsh -NoProfile -File $T/ue_editor.ps1        # 导入或重新导入，保存，关闭编辑器
pwsh -NoProfile -File $T/cook.ps1 face        # 打印日志里的 "Success - …" / "Failure - …" 行
```

把 `<工程>\Saved\Cooked\WindowsNoEditor\BendGame\Content` 复制回本机这一阶段的 `cooked_all/`。

### 4. 本机：眼睑骨和口型

```powershell
$Mesh = "Characters/Deacon/parts/head/deacon_head_standard.uasset"
# 眨眼：每只眼 5 根只在网格里的眼睑骨 KB_Blink_*，各挂在一根放大骨 KB_Amp_* 下；写 blink_rig.json；BLINK_RIG_OK
& $Blender -b "$Runs/face/build.blend" --python $Kit/scripts/blender/blink_rig.py -- "$Runs/face/cooked_all/$Mesh" "$Runs/blink"     # 可加 --render
#   （导入 blink 的 FBX、cook，复制成 $Runs/blink/cooked_all，见第 3 步）
# 口型：每个 viseme 配 Karin 自己的口型键（configs/mouth_map_t30.json），解嘴部权重；--render 写 mouth_sheet.png
& $Blender -b "$Runs/blink/build.blend" --python $Kit/scripts/blender/mouth_rig.py -- "$Runs/blink/cooked_all/$Mesh" "$Runs/mouth" $Kit/configs/mouth_map_t30.json --render
#   （导入 mouth 的 FBX、cook，复制成 $Runs/mouth/cooked_all）
```

`viseme_sim.py`（按当前权重模拟迪肯的 viseme）和 `shape_sheet.py`（形态键联系表）是挑口型配方时用的检查脚本。

### 5. 本机：改写烘焙后的资产，打 pak

```powershell
$C = "$Runs/mouth/cooked_all"; $Py = "<Blender 4.2 目录>\4.2\python\bin\python.exe"   # 见上文：pak 字节与 zlib 有关
# 眼睑校准（一次；结果与 configs/lid_calib_t28.json 逐字节相同）
python -B $Kit/scripts/lid_calib.py --out "$Runs/lid_calib.json"
# 放大骨的烘焙静止姿势（旋转、缩放），改写 cooked_all 里的网格；先留一份 cook 原样的
Copy-Item "$C/$Mesh" "$Runs/mouth/cooked_raw.uasset"
python -B $Kit/scripts/blink_amp.py "$Runs/mouth/cooked_raw.uasset" "$C/$Mesh" "$Runs/blink/blink_rig.json" "$Runs/lid_calib.json" "$Runs/mouth/blink_amp.json"
# 游戏骨架：280 个 face_* 关节改成 AnimationRelative（表情叠在 Karin 的关节位置上）
python -B $Kit/scripts/skel_retarget.py "$env:DG_CACHE/raw/BendGame/Content/Characters/Deacon/deacon_master_Skeleton.uasset" "$Runs/deacon_master_Skeleton.uasset" "^face_=AnimationRelative"
# 动画蓝图：每根 KO_* 骨一个 AnimDynamics 弹簧节点，眼睑 10 个 CopyBone；结尾打印每个节点的 k、角度限制和平面
python -B $Kit/scripts/abp_springs.py "<raw 的 Deacon_VimBlueprint.uasset>" "$C/$Mesh" $Kit/configs/springs_t31.json "$Runs/Deacon_VimBlueprint.uasset" "$Runs/springs_report.json"
# pak：网格（骨架引用、根骨姿势、法线、位移）、贴图、5 个材质实例、66 个外观、骨架、动画蓝图；写 <pak>.report.json
& $Py -B $Kit/scripts/make_pak.py $C "$Runs/zz_Karin_P.pak" --stage "$Runs/stage" --normals "$Runs/face/loop_normals.npz" --positions "$Runs/face/body_shrink.npz" --skeleton "$Runs/deacon_master_Skeleton.uasset" --extra "Animation/Deacon/Deacon_VimBlueprint=$Runs/Deacon_VimBlueprint.uasset"
python -B $Kit/scripts/paklist.py "$Runs/zz_Karin_P.pak"        # 检查：挂载点、79 个条目
```

- `--extra` 的游戏路径不写开头的 `/Game/`（Git Bash 会改写它），脚本自己补上。
- 看 `<pak>.report.json`：`mesh_normals` 的 `unmatched` 应为 0，`sample_hit` 接近 1；`mesh_positions` 的 `moves_matched` 等于 `moves_total`；带内嵌 shader map 的材质实例 `size` 前后相同（这种材质实例的包头大小一变，游戏就崩，见技术合同）。
- 只调物理时（t31 就是这样）不用重跑 Blender 和导入：改 `springs` 配置，重跑 `abp_springs.py` 和 `make_pak.py`，用原来的 `cooked_all`。

### 6. 构建机：安装和实机

```powershell
# 第一次：与参考 mod 相同，停用 startuppackages.pak
Rename-Item "$env:DG_GAME_DIR\BendGame\Content\sfpaks\startuppackages.pak" disabled_startuppackages.pak
# 把 zz_Karin_P.pak 复制到 $R\staging\，两边各算一次 SHA-256；游戏和编辑器都关着时安装
pwsh -NoProfile -File $T/install_pak.ps1 <sha256>     # 打印 installed <前 12 位>；原来的 pak 移到 $R\disabled_mods\zz_Karin_P_prev.pak
# 用户桌面会话里：先设分辨率，再经 Steam 启动并记录进程（或直接从 Steam 启动）
pwsh -NoProfile -File $T/set_resolution.ps1 1920 1080
pwsh -NoProfile -File $T/watch_launch.ps1             # $R\out\watch.txt 和 watch1.png
```

游戏失去焦点时会暂停；启动就崩时先查显示设置和编辑器是否开着，见 [开发工具](../../games/days-gone/DEV_TOOLING.md)。

### `springs` 配置

`abp_springs.py` 的配置（`configs/springs_t31.json`，12 组、101 个节点：91 个弹簧 + 10 个 CopyBone）：

| 键 | 作用 |
| --- | --- |
| `template_node`、`plane_template_node`、`insert_before` | 动画蓝图里原有 AnimDynamics 节点属性名的后缀：新节点的标签从前者复制，平面限制的元素从第二个复制，新节点链接在第三个前面 |
| `groups[]` | `name`；`chains`（链根骨名，沿唯一的子骨走到叶子，每段一个节点）；`omega`（rad/s，可按段给列表，`k = I_pivot · omega²`）；`drag`（`damping = 1 − exp(−drag)`，不要超过约 13）；`limit`（每段的角度限制，度）；`width`、`thick`、`com`（盒子尺寸和质心位置）；`gravity`；`planes` |
| `planes[]` | `kind: radial`：`bone`、`center`（竖直轴的 x、y）、`margin`，可选 `max_z` / `min_z`；`kind: thigh`：`up`、`leg`（`#` 换成 Left / Right）、`radius`、`margin`、`min_off`、`from_segment`、`neighbors`（配合组的 `ring`、`ring_closed`） |
| `copies[]` | CopyBone 节点：`source`、`target`、`space`（`BCS_ParentBoneSpace`）、`translation` / `rotation` / `scale` |
| `drivers[]` | BoneDrivenController 节点：能加载但实机没有任何效果，不要用 |

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/blender/build_body.py` | Blender 内运行的身体构建：导入迪肯的 `.uemodel` 和 Karin 的 VRM，按段把 Karin 摆到迪肯的关节上（缩放默认 1.30），权重映射到迪肯的骨，variant B 保留次级链为 `KO_*` 骨；材质改名合并；写 FBX、`textures/`、`report.json`、`build.blend` |
| `scripts/blender/face_rig.py` | 面部：迪肯的头部网格移到 Karin 的 Head 上，经薄板样条按特征点变形到她脸上，Karin 的脸取最近面的权重；眼睛、口腔、眉线和睫毛单独处理；`face_*` 关节移到 Karin 脸上；删掉藏在皮肤后的 VRM 表情零件 |
| `scripts/blender/blink_rig.py` | 眼睑：按 VRM 的 `blink_L` / `blink_R` 形态键，每只眼加 5 根只做平移的眼睑骨和放大骨，权重按位移分量分配 |
| `scripts/blender/blink_sim.py` | 用迪肯的脸部动画（`anim_pertrack.py` 解码）在 `build.blend` 上模拟脸部关节蒙皮；`blink_rig.py`、`mouth_rig.py`、`viseme_sim.py` 共用 |
| `scripts/blender/mouth_rig.py` | 口型：每个迪肯 viseme 配 Karin 的口型键，逐顶点用非负最小二乘解脸部关节权重（和为 1、最多 4 个影响），再做邻域平滑 |
| `scripts/blender/viseme_sim.py`、`shape_sheet.py` | 检查：迪肯的 viseme 作用在当前权重上的效果；形态键联系表 |
| `scripts/blender/fbx_common.py` | 给 UE 4.11 导出 FBX（骨架对象名 `Armature`，去掉同名根骨） |
| `scripts/blender/dump_loop_normals.py` | 每个角的位置、UV、自定义法线和材质（UE 坐标），给 `make_pak.py --normals` |
| `scripts/blender/skirt_body_shrink.py` | 裙子盖住的身体皮肤沿法线内缩（默认最多 2 cm），给 `make_pak.py --positions` |
| `scripts/blender/export_dummy_skeleton.py` | 迪肯头部网格和骨架的 FBX，做 UE 里的 `deacon_master` 占位 |
| `scripts/blender/render_preview.py` | 正、侧、背面的 Workbench 预览，可并排参照模型 |
| `scripts/blender/fit_colliders.py` | 按 Karin 的身体拟合头、髋、大腿胶囊，给 `physchain.py` 的 `refit`（已放弃的 PhysX 路线，见下文） |
| `scripts/make_pak.py` | 打 pak：网格的骨架引用改到游戏骨架、根骨姿势、法线和位移补丁；贴图；游戏材质实例的副本（贴图引用改到 Karin，带 shader map 的原地改名字表）；66 个外观；`--skeleton`、`--extra`、`--phys` |
| `scripts/patch_looks.py` | 外观（`BendSkeletalMeshLook`）：主部件换成 Karin 的网格和材质实例，其余部件网格置空 |
| `scripts/retarget_imports.py`、`retarget_inplace.py` | 改包的导入路径：前者会让包头变长；后者原地改名字表、包头大小不变（带内嵌 shader map 的材质实例只能这样改） |
| `scripts/shader_skips.py` | 找内嵌 shader map 的 SkipOffset 记录（`make_pak.py` 用它判断材质实例有没有 shader map） |
| `scripts/fix_root_pose.py` | 根骨 `Armature` / `Align` 的局部姿势改成参考 mod 的布局（-90° X / 单位），组件空间姿势不变 |
| `scripts/skel_retarget.py` | 改游戏 Skeleton 里骨的平移重定向模式 |
| `scripts/blink_amp.py` | 写放大骨的烘焙静止姿势，让 CopyBone 把迪肯眼睑关节的位移放大成 Karin 的眨眼 |
| `scripts/abp_springs.py` | 改烘焙后的 `Deacon_VimBlueprint`：在类字段链头部插入新的 AnimDynamics / CopyBone 节点，旧的姿势链接全部 +M，写完重新解析核对 |
| `scripts/lid_calib.py` | 新写的：迪肯中性表情里眼睑关节睁眼 / 闭眼的偏移，给 `blink_amp.py` |
| `scripts/anim_pertrack.py` | 解 UE 4.11 `AKF_PerTrackCompression` 动画（迪肯的面部动画） |
| `scripts/refskel.py` | 从烘焙后的网格读参考骨架（局部和组件空间矩阵、在文件里的偏移） |
| `scripts/skelmesh_normals.py`、`skelmesh_positions.py` | 原地改烘焙网格 GPU 顶点缓冲的法线 / 位置（按位置匹配，文件大小不变） |
| `scripts/upkg.py` | UE 4.11 包（原版和 Bend 格式）读写：摘要、名字、导入、导出、带标签属性，追加名字 / 导入 / 导出后整体平移偏移 |
| `scripts/uhdr.py` | 打印包摘要和名字表；只认 FileVersionUE4 ≥ 504 的名字哈希，读游戏包（500 / licensee 34）会在名字表处出错，改用 `upkg.py dump` |
| `scripts/paklist.py`、`pakextract.py`、`pakwrite.py` | pak v3：列表、全部解出、从目录写（zlib 64 KiB 块，或 `--store`） |
| `scripts/physchain.py` | 往玩家物理资产加链刚体（已放弃的路线）；只因 `fit_colliders.py` 导入它的胶囊函数才收进来 |
| `scripts/dgpaths.py` | 新写的：`DG_CACHE` / `DG_MODELS_DIR` 下的路径，没设时报错 |
| `configs/springs_t31.json` | t31 的弹簧配置（项目 `runs/t31/springs.json`） |
| `configs/mouth_map_t30.json` | t30 的口型配方（`runs/t30/mouth_map.json`） |
| `configs/lid_calib_t28.json` | t28 的眼睑校准（`runs/t28/lid_calib.json`） |
| `dgexport/` | DgExport 源码（`Program.cs`、`DgExport.csproj`） |
| `tools/dgx_run.ps1` | 对游戏 pak 运行 DgExport |
| `tools/cook.ps1` | cook `BendGame` 工程（`-cookall -iterate`），打印成败行 |
| `tools/ue_editor.ps1` | 用编辑器打开 `BendGame` 工程 |
| `tools/install_pak.ps1` | 核对 SHA-256 后把暂存的 pak 装进 `~mods`，原来的移到 `disabled_mods`；游戏或编辑器在运行时拒绝 |
| `tools/set_resolution.ps1` | 设主显示器的桌面分辨率 |
| `tools/watch_launch.ps1` | 经 Steam 启动游戏，记录进程、退出码、窗口标题和一张截屏 |

脚本注释里的 `pytools/…` 指本包的 `scripts/`，`Scripts/…` 指 `scripts/blender/`（`make_pak.py`、`patch_looks.py` 在 `scripts/`）；`t20`、`t28b` 这类编号是项目的构建轮次。`build_body.py` 注释里的 `StellaBlade/…` 指剑星项目（完整仓库的 `games/stellar-blade/`，单游戏导出里没有）。

## 输出与本机信息

- **中间结果：**
  - `build_body.py` 的 `report.json` 在 `target` 记有 `.uemodel` 的绝对路径；
  - FBX 记有源 `.blend` 路径和创建时间，`build.blend` 记有贴图路径；`face_rig.py --check` 等渲染的 PNG 元数据里有 `.blend` 路径和时间；
  - `make_pak.py` 的 `<pak>.report.json` 在 `physics_asset`、`skeleton` 记有传入文件的路径；
  - DgExport 输出、cook 日志和 `watch.txt` 记有构建机路径。

  这些文件分享前要处理，不要收进本仓库。`blink_rig.json`、`face_rig.json`、`mouth_rig.json`、`lid_calib.json`、`springs_report.json`、`blink_amp.json` 里没有本机路径。
- **发行物：** pak 里是 cook 后的资产和改写过的游戏包，路径都是 `BendGame/Content/…`；pak 里的资产没有逐个查本机路径。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时，要按新模型的骨名、网格、形态键和材质重写：

- `build_body.py`：`K_MESHES`、`MAT_RENAME`（VRM 的网格和材质名）、缩放默认 1.30、骨的对应表和分段拟合；
- `face_rig.py`：特征点（眼、鼻尖、嘴、下巴）和区域划分；
- `blink_rig.py`：形态键名 `blink_L` / `blink_R`，`MAX_INF`、`MIN_COMP`、`S_MAX`；
- `mouth_rig.py` 和 `configs/mouth_map_t30.json`：viseme → Karin 口型键的配方、`gain`、各项权重；
- `configs/springs_t31.json`：12 组链的名字和参数；`configs/lid_calib_t28.json`：迪肯眼睑关节的校准；
- `make_pak.py`：`MIS`（5 个材质实例、各自复制的游戏材质实例和贴图替换）、`SKIN`（换成空白贴图的迪肯皮肤贴图）。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 资产路径：`/Game/Characters/Deacon/parts/head/deacon_head_standard`、`deacon_master_Skeleton`、`looks/` 下的 66 个外观、`mi_deacon_head`、`mi_deacon_eyelash_hair`、`Animation/Deacon/Deacon_VimBlueprint`；
- 动画蓝图里节点属性名的后缀（`springs` 配置的 `template_node`、`plane_template_node`、`insert_before`）和 `CopyBone` 节点；
- 迪肯的眼睑关节 `face_1544` / `face_1911`、口型 viseme 动画的名字；
- 游戏包的版本（500 / licensee 34）、pak 版本和压缩方式、`startuppackages.pak` 的处理。

## 已验证与边界

- **实机。** 项目用原脚本构建的各轮在构建机上进游戏：t5 Karin 出现、贴图正常；t10 表情（照相模式）经用户确认；t27 物理用户判定“都好了”；t29 眨眼（双眼完全闭合，按帧截图核对）；t30 口型，用户判定可以；t31（`sha256 87576aec…`）头发摆动收小，用户判定没问题。已知：照相模式里右侧双马尾的 AnimDynamics 链会拉成一大片，回到游戏后正常。项目记录里没有过场动画和战斗场景的检查。
- **便携版本身只做了离线验证（2026-10-16）：**
  - `make_pak.py` 用 Blender 自带的 Python 按 t31 的参数重跑，pak 与项目的 t31 pak 逐字节相同（`87576aec…`），暂存目录和报告也相同；用 Python 3.14 跑时暂存的 79 个文件仍逐字节相同，只有 zlib 压缩的字节不同；
  - `abp_springs.py`、`blink_amp.py`、`skel_retarget.py`、`lid_calib.py` 的输出与项目 t31 / t30 / t10 / t28 的文件逐字节相同；
  - Blender 脚本：`build_body.py`（variant B）的 `report.json` 和 5 张贴图与 t7 相同，`face_rig.py` 的 `face_rig.json` 与 t11 相同、渲染像素相同，`blink_rig.py` 的 `blink_rig.json` 与 t29 相同，`mouth_rig.py` 的 `mouth_rig.json` 和 `mouth_sheet.png` 与 t30 相同；FBX 只差创建时间和源路径，没有逐项比较；
  - `fit_colliders.py` 与现在的 `physchain.py` 一起运行时在头部胶囊处报错（`DEFAULT` 里已没有和 `head` 碰撞的链），原脚本也一样；它只服务于已放弃的 PhysX 路线；
  - UE 一侧（编辑器导入、cook）、DgExport（C#）和实机安装没有用本包重跑；PowerShell 工具只用假的 DgExport 和临时目录跑过；
  - 详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中有往日不再的合成测试，不需要游戏、Blender 或 UE：pak v3 写出、列表和解出的往返；合成 UE 包上的 `upkg.py` 读写、`refskel.py`、`retarget_imports.py`、`fix_root_pose.py`；`blink_amp.py` 的放大骨姿势；`skelmesh_normals.py` / `skelmesh_positions.py` 的顶点缓冲补丁；`abp_springs.py` 的四元数、弹簧常数、平面和 FName 编号；`anim_pertrack.py` 的轨道解码；`lid_calib.py` 和 `dgpaths.py`；PowerShell 工具的环境变量检查、DgExport 参数转发和 `install_pak.ps1`（要 pwsh 7 和 Windows，否则跳过）；PROVENANCE 哈希和本包里没有本机路径。`--help` 测试覆盖 `scripts/` 下全部脚本，没装 numpy 时跳过要 numpy 的那些。
- **测试没覆盖的部分：** Blender 脚本只做语法检查；`make_pak.py`、`patch_looks.py`、`abp_springs.py` 的整包改写、`retarget_inplace.py`、`skel_retarget.py` 要游戏包，只在上面的离线验证里跑过；`set_resolution.ps1`、`watch_launch.ps1`、`cook.ps1`、`ue_editor.ps1` 只检查了解析和缺变量时报错。
- **便携改动：**
  - 去掉写死的本机路径：`sys.path` 改成相对脚本自己的位置（Blender 脚本找上一级的 `scripts/`），缓存和源模型路径改为 `DG_CACHE` / `DG_MODELS_DIR`（新文件 `dgpaths.py`，没设时报错）；
  - 没有 argparse 的命令补上了 argparse，位置参数和选项不变（`--help` 不再需要环境变量）；
  - 构建机的 `cook.bat`、`ue411.bat`、`dgx_run.ps1`、`swap.ps1`、`setres.ps1`、`watchgame.ps1` 按 PowerShell 7 改写，路径改为 `DG_*` 环境变量或参数；`install_pak.ps1` 在没有暂存 pak 时先拒绝，`set_resolution.ps1` 的模式列表只在给了 `-ModesFile` 时写；
  - 每个迁入文件保留原来的换行（CRLF 的仍是 CRLF）。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md)。
- **没有收进本包：**
  - 已放弃的路线：`physchain_v1.py`（第一版链刚体）、`physasset_edit.py`；玩家网格上额外刚体的 PhysX 约束在游戏里不起作用（限位、锁定和驱动都没有可见效果，t12–t19）。`abp_dynamics.py`（把游戏原有的 3 个 AnimDynamics 节点改到 Karin 的链上，t20）已被 `abp_springs.py` 取代。`physchain.py` 只因 `fit_colliders.py` 导入它才收进来，`make_pak.py --phys` 是那条路线的入口；
  - 构建机的 `rungame.bat`（先 `setres.ps1 1920 1080` 再从 Steam 启动）和 `swap_karin.bat`（`swap.ps1` 的批处理版）：前者拆成第 6 步的两行命令，后者由 `install_pak.ps1` 代替；
  - 源模型、参考 mod、游戏数据、DgExport 的输出、cook 结果、生成的贴图、FBX、blend、npz、pak 和发行包。
- **署名：** DgExport 建立在 FabianFG 的 CUE4Parse（NuGet 包）上，Blender 端读 `.uemodel` 用 h4lfheart 的 UEFormat；本包不含它们的代码，见 [工具来源](../../references/TOOL_SOURCES.md)。
