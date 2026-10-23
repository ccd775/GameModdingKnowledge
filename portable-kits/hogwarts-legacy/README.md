# 霍格沃茨之遗（Hogwarts Legacy）便携包

先读 [游戏知识](../../games/hogwarts-legacy/README.md) 和 [构建流程](../../games/hogwarts-legacy/BUILD_PIPELINE.md)。容器、更新后的网格格式、材质实例、骨架、数据资产的约定见 [技术合同](../../games/hogwarts-legacy/TECHNICAL_CONTRACTS.md)；AnimDynamics 语义和调参见 [物理](../../games/hogwarts-legacy/PHYSICS.md)；面部形变见 [表情](../../games/hogwarts-legacy/FACE.md)；崩溃和症状见 [排障手册](../../games/hogwarts-legacy/TROUBLESHOOTING.md)。

这是 Karin 替换黑魔法套装的 Mod（男女两版的测试构建 v1–v12，女巫版发行 v1.0 / v1.1）实际使用的工具：Blender 拟合与导出脚本、物理参数和离线检查、legacy 包的读写与补丁脚本（Python）、UE 4.27 编辑器 Python、编辑器插件 HLKTools 的 C++ 源码和占位工程、C# 写的 HLMeshProbe（打过补丁的 CUE4Parse），以及由项目的 `build.sh` 改写的分步构建驱动 `scripts/build_mod.py`。

- **游戏版本：** Steam App 990080，游戏版本 `1613387`（buildid `20773316`），2025-01-30「数据序列化 + 光追」更新之后。WB 改过的 UE 4.27（工程名 `Phoenix`），资源是 IoStore（`Phoenix\Content\Paks\*.pak/.utoc/.ucas`）。Mod 是同名三件套 `zzz_KarinDarkArts_<MF|F>_P.pak/.ucas/.utoc`，在游戏关闭时放进 `Phoenix\Content\Paks\~mods\`（没有就新建）。
- **retoc：** 0.1.5，由用户自备。`to-legacy --version UE4_27 [--no-shaders] --filter <准确的资产名> <Paks 目录> <输出>` 取原版资产；`build_mod.py pack` 调 `to-zen --version UE4_27` 和 `verify`。
- **UE：** 4.27.2（Epic 启动器版）+ PythonScriptPlugin + EditorScriptingUtilities。占位工程在 `ue/Phoenix/`（`Phoenix.uproject`、`Config/*.ini`：不用 IoStore、不共享材质着色器代码），插件源码在 `ue/HLKTools/`。编插件要 VS2022（项目用 MSVC 14.44）；UBT 报「Could not find NetFxSDK install dir」时见 [构建流程](../../games/hogwarts-legacy/BUILD_PIPELINE.md) §1。
- **Blender：** 项目用 4.0.2，后台运行；拟合加 `--factory-startup`，导出不加（与 `build.sh` 相同）。`fit.py` 对 4.1 之前和之后的自定义法线 API 都有分支，只有 4.0.2 的那条跑过。Blender 脚本用 Blender 自带的 Python 和 numpy。
- **HLMeshProbe：**
  - 源码在 `hlmeshprobe/`：`HLMeshProbe/`（`Program.cs`、`HLMeshProbe.csproj`）、`CUE4Parse/HLProbe.cs`、`cue4parse_probe.patch.txt`（`git apply` 用的补丁，只是改了扩展名）、`CUE4PARSE_BASE_COMMIT.txt`；
  - 编法：CUE4Parse（FabianFG）检出到 `2b8901c3ee9818558ad33e2496a58d50b82e99db`，打补丁，`HLProbe.cs` 放进 CUE4Parse 工程目录（打过补丁的 CUE4Parse 文件引用 `CUE4Parse.HLProbe`，所以它属于 CUE4Parse，**不能**和 `Program.cs` 放在一起，否则会编出两份同名类型、补丁记下的位置读不到）；`HLMeshProbe/` 放在克隆的根目录，与 `CUE4Parse/`、`CUE4Parse-Conversion/` 同级（工程按相对路径引用它们，自身不写目标框架；原项目的输出在 `bin/Release/net10.0/`）；
  - 用 .NET 10 SDK 编译，设 `CUE4PARSE_SKIP_NATIVE=1`（跳过 CUE4Parse-Natives）；工程里 `CETCompat=false`（.NET 10 在不完全支持 CET 的 Windows 上会崩）；
  - 命令：`probe <ue427|hl> <目录> [过滤]`（section 布局）、`patch <输入目录> <输出目录> [skel_ext.json]`（更新后格式补丁 + 参考姿势写回 + 按 HL 规则读回校验，校验失败时退出码 1）、`mat <ue427|hl> <目录> [过滤]`（材质实例尾部哈希）、`dump <hl|ue427> <目录> <输出目录> [过滤]`（LOD0 几何、蒙皮、参考骨架、形变 → JSON）、`json <ue427|hl> <目录> [过滤]`（属性 JSON）；
  - 请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包。
- **Python：** `build_mod.py` 和包补丁脚本只用标准库，3.10 或更高。`dyn_params.py`、`feel_sim.py`、`swing_check.py`、`hlskel.py` 另需 numpy，`make_tex.py` 另需 numpy 和 Pillow；`requirements.txt` 钉的 numpy 2.5.2 要 Python 3.12 或更高。本次在 3.12.10、numpy 2.5.2、Pillow 12.3.0 上测试。
- **只在 Windows 上：** UE 4.27 编辑器、cook 和插件编译。原项目在 Windows 上编译运行 HLMeshProbe 和 retoc；别的系统没有试过。
- **运行位置：** 以下命令都从交接包根目录执行。

## 环境变量与参数

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `HL_WORK` | `build_mod.py`（`--work`）；`scripts/ue/*.py` 的后备 | 工作目录，布局见下一节。原项目把工作目录 `subst` 成一个盘符，路径都写死在脚本和配置里 |
| `HL_BLENDER` | `build_mod.py`（`--blender`），`fit`、`export` | Blender 可执行文件 |
| `HL_UE_CMD` | `build_mod.py`（`--ue-cmd`），`import`、`cook` | `<UE_4.27>\Engine\Binaries\Win64\UE4Editor-Cmd.exe` |
| `HL_PROJECT` | `build_mod.py`（`--project`），`import`、`cook`、`assemble` | 内容工程目录（含 `Phoenix.uproject`）；cook 输出在它的 `Saved\Cooked\WindowsNoEditor\Phoenix\Content` |
| `HL_PROBE` | `build_mod.py`（`--probe`），`assemble` | HLMeshProbe 可执行文件 |
| `HL_RETOC` | `build_mod.py`（`--retoc`），`pack` | retoc 可执行文件 |
| `HL_GENDERS` | `build_mod.py`（`--genders`） | `"m f"`（默认）或 `"f"`（女巫版发行）；顺序决定包名里的 `MF` / `F`。原脚本的 `GENDERS` |
| `HL_TEXTURES` | `build_mod.py`（`--textures`） | `1` 时 `import` 也导入贴图。原脚本的 `TEXTURES=1` |
| `HL_UE_BUILD` | `scripts/ue/ue_import.py` | 这次导入用的 `ue_build.json`；`build_mod.py import` 把它设成 `<HL_WORK>\ue_build.json`。没设时用 `<HL_WORK>\ue_build.json` |
| `HL_UE_BUILD_CONFIGS` | `scripts/ue/ue_fixmat.py` | 要重新挂材质的配置，多个用 `;`（Windows）分隔；没设时用 `<HL_WORK>` 下的 `ue_build_m.json` 和 `ue_build_f.json` |
| `CUE4PARSE_SKIP_NATIVE` | HLMeshProbe 的编译 | `build_mod.py` 给所有子进程设为 `1`（与 `build.sh` 相同） |

`build_mod.py` 先检查本次各阶段要用的设置、工具、手工准备的输入和配置里没换掉的占位符，缺什么一次列出来再退出（退出码 1），不会跑到一半才失败。`--dry-run` 只打印命令和文件步骤。

## 工作目录

```text
<HL_WORK>/
  fit_m.json, fit_f.json            configs/ 的例子，换掉 <HL_WORK> 和 <KARIN_FBX>
  ue_build_m.json, ue_build_f.json  同上
  dyn.json, face_map.json           configs/ 原样复制
  dumpm/, dumpf/                    游戏骨架和参考网格的 JSON（HLMeshProbe dump，见第 0 步）
  tex_m/                            make_tex.py 的输出（两份 ue_build 的 tex_dir 都指向它）
  dami/                             原版 legacy 包（.uasset + .uexp）：DA_HUM_<M|F>_Upp_DarkArtsDeluxe01_Master，
                                    MI_HUM_M_{Upp,Low,Mask,Hat}_DarkArtsDeluxe01、MI_HUM_M_Acc_DarkArtsDeluxe01U
  hairda_out/                       hair_override_patch.py 改过的发型数据资产（女 2 个、男 1 个）
  ga_out2/                          ga_slot_patch.py 改过的 DA_GA_Outfit_072_<M|F>
  fit_<g>/                          fit / params / export 的输出
  ue_build.json, cook.log           import / cook 写
  mod_<g>/legacy, mod_<g>/legacy_hl assemble 写
  mod_mf/legacy_hl, mod_mf/out/, mod_mf/KarinDarkArts.tar.xz   pack 写
```

## 构建流程

原项目用 `build.sh <阶段…>`（bash，阶段按给出的顺序执行）；本包的 `scripts/build_mod.py` 是它的 Python 版，阶段、顺序、命令和输出筛选相同，路径改由参数或环境变量给。

### 0. 一次性准备

```powershell
$Kit = "portable-kits/hogwarts-legacy"; $S = "$Kit/scripts"
$env:HL_WORK = "<工作目录>"; $W = $env:HL_WORK
$env:HL_BLENDER = "<Blender 4.0>\blender.exe"
$env:HL_UE_CMD = "<UE_4.27>\Engine\Binaries\Win64\UE4Editor-Cmd.exe"
$env:HL_PROJECT = "<内容工程目录>"            # 下面 c) 建
$env:HL_PROBE = "<CUE4Parse 克隆>\HLMeshProbe\bin\Release\net10.0\HLMeshProbe.exe"
$env:HL_RETOC = "<retoc 0.1.5>\retoc.exe"
$Paks = "<Steam 库>\steamapps\common\Hogwarts Legacy\Phoenix\Content\Paks"

# a) HLMeshProbe（仓库外）
git clone https://github.com/FabianFG/CUE4Parse "<CUE4Parse 克隆>"; git -C "<CUE4Parse 克隆>" checkout 2b8901c3ee9818558ad33e2496a58d50b82e99db
git -C "<CUE4Parse 克隆>" apply (Resolve-Path $Kit/hlmeshprobe/cue4parse_probe.patch.txt)
Copy-Item $Kit/hlmeshprobe/CUE4Parse/HLProbe.cs "<CUE4Parse 克隆>/CUE4Parse/"
Copy-Item -Recurse $Kit/hlmeshprobe/HLMeshProbe "<CUE4Parse 克隆>/HLMeshProbe"
$env:CUE4PARSE_SKIP_NATIVE = "1"; dotnet build "<CUE4Parse 克隆>/HLMeshProbe/HLMeshProbe.csproj" -c Release

# b) 内容工程：占位工程 + 插件源码，插件随工程用 UBT 编译（原项目用的命令）
Copy-Item -Recurse $Kit/ue/Phoenix $env:HL_PROJECT
Copy-Item -Recurse $Kit/ue/HLKTools "$env:HL_PROJECT\Plugins\HLKTools"
& "<UE_4.27>\Engine\Build\BatchFiles\Build.bat" -TargetType=Editor Win64 Development "-Project=$env:HL_PROJECT\Phoenix.uproject" -WaitMutex -NoHotReloadFromIDE

# c) 只装了 VS2022 时 UBT 报找不到 NetFxSDK：在 HKCU\SOFTWARE\Microsoft\Microsoft SDKs\NETFXSDK\4.8 建 KitsInstallationFolder 指向一个空目录，编完删除
```

d) 原版资产：`retoc to-legacy`（`--filter` 写准确的资产名）把下面这些取成 legacy 包：`Biped_Skeleton`；男女黑魔法套装的上衣、配件、裤子网格（`SK_HUM_<M|F>_{Upp,Acc,Low}_DarkArtsDeluxe01_Master`）和袜子 / 鞋网格（参考权重用）；`dami/` 里的两个上衣数据资产和 5 个男版材质实例；三个发型数据资产（`DA_HUM_F_Hair_StuHair13_Loose_LowBun_Master`、`DA_HUM_F_Hair_StuHair18_PrincessLong_Bangs1`、`DA_HUM_M_Hair_StuHair03_ShavedBob`）；装备外观 `DA_GA_Outfit_072_<M|F>`。完整清单和选择理由见 [构建流程](../../games/hogwarts-legacy/BUILD_PIPELINE.md) §2。

```powershell
& $env:HL_RETOC to-legacy --version UE4_27 --filter DA_GA_Outfit_072_F $Paks "$W/legacy_src"   # 每个资产一次
```

e) dump 和手工输入：

```powershell
# 骨架和参考网格 → dumpm/、dumpf/：<名字>.json（bones、pos、bi、bw、idx、sections…），有形变时另写 <名字>_morphs.json
& $env:HL_PROBE dump hl "<legacy 目录>" "$W/dumpm" SK_HUM_M_
& $env:HL_PROBE dump hl "<legacy 目录>" "$W/dumpm" Biped_Skeleton
# 女性骨架 dumpf/F_Skeleton.json：Biped_Skeleton 的骨，参考姿势按骨名换成女性网格的（技术合同 §2）。做这一步的一次性脚本不在原工具目录里，没有收进本包

# 发型：每个 MeshOverrides[].Mesh 改指 DefaultMesh（兜帽 / 帽子下也显示替换的头发）
python -B $S/hair_override_patch.py "<legacy>/…/DA_HUM_F_Hair_StuHair13_Loose_LowBun_Master.uasset" "$W/hairda_out/DA_HUM_F_Hair_StuHair13_Loose_LowBun_Master.uasset"
# 装备外观：OutfitItems 的序列化顺序是 Upper、Lower、Socks、Shoes（序号从 0 开始），原项目把 Lower 的引用写进 Socks 和 Shoes。
# 游戏更新后先不给目标序号运行一次（只打印 CharacterPiece 引用、原样复制）核对顺序
python -B $S/ga_slot_patch.py "<legacy>/…/DA_GA_Outfit_072_F.uasset" "$W/ga_out2/DA_GA_Outfit_072_F.uasset" 1 2 3

# 配置：换掉占位符
$fbx = "<源模型 FBX>" -replace '\\', '/'; $w = $W -replace '\\', '/'
foreach ($n in 'fit_m', 'fit_f', 'ue_build_m', 'ue_build_f', 'dyn', 'face_map') {
  (Get-Content -Raw "$Kit/configs/$n.json").Replace('<HL_WORK>', $w).Replace('<KARIN_FBX>', $fbx) |
    Set-Content -NoNewline -Encoding utf8NoBOM "$W/$n.json" }

# 贴图：源 FBX 里的图 → make_tex.py → tex_m/（D、平法线、MRO 常量图）
& $env:HL_BLENDER -b --python $S/blender/extract_tex.py -- "<源模型 FBX>" "$W/ktex"
python -B $S/make_tex.py "$W/ktex" "$W/tex_m"
```

`make_tex.py` 读的文件名（`UnityTexture_*_Karin_*.png`）写在脚本里，是 Karin_Original 的贴图名；`extract_tex.py` 解出的名字对不上时先改名。

### 1. 构建

```powershell
python -m pip install -r requirements.txt -r portable-kits/hogwarts-legacy/requirements.txt
python -B $S/build_mod.py --textures fit params export import cook assemble pack          # 男女两版（MF）
python -B $S/build_mod.py --genders f --textures fit params export import cook assemble pack   # 女巫版（F）
python -B $S/build_mod.py --genders f --dry-run pack                                     # 只看命令
```

| 阶段 | 做什么 | 输入 → 输出 |
| --- | --- | --- |
| `fit` | `blender -b --factory-startup --python scripts/blender/fit.py -- fit_<g>.json`，只显示 `dynamic bones`、`part `、`head morphs`、`normals carried`、`missing key`、`Traceback`、`Error` 行（截到 200 字） | 源 FBX、`dump*/`、`face_map.json` → `fit_<g>/`：`fit.blend`、`skel_ext.json`、`dyn_chains.json`、各部件 FBX、`*_pos_ue.npy`、`fit_log.txt` |
| `params` | `dyn_params.py fit_<g> dyn.json fit_<g>/dyn_nodes.json`，显示最后一行 | → `fit_<g>/dyn_nodes.json`（每个部件一组 AnimDynamics 节点） |
| `export` | `blender -b fit_<g>/fit.blend --python scripts/blender/export_fbx.py -- fit_<g> fit_<g>.json`，显示 `EXPORTED` 和 `Error` 行 | → `fit_<g>/` 下 `KarinBody`、`KarinHair`、`KarinHead`、`Empty`、`PhysProxy`、`Skeleton` 的 FBX；带动态骨的网格和 `Skeleton.fbx` 带全部骨，其余只带游戏骨架的骨 |
| `import` | 由 `ue_build_<g>.json` 写 `ue_build.json`（没给 `--textures` 时清空 `textures`），在工程目录里跑 `UE4Editor-Cmd Phoenix.uproject -run=pythonscript -script="scripts/ue/ue_import.py"`；显示 `[HLK] ALL/IMPORT/abp/karin/morphs`、`LogHLK: Error/Warning`、`Error:` 行 | → 工程里的占位、网格、Karin 骨架、动画蓝图（插件生成） |
| `cook` | `UE4Editor-Cmd Phoenix.uproject -run=cook -targetplatform=WindowsNoEditor -CookAll`，日志写 `cook.log`，打印 `cook rc=… errors=…`（`Error:` 行数，必须为 0） | → `Saved\Cooked\WindowsNoEditor\Phoenix\Content` |
| `assemble` | 每个性别：清空 `mod_<g>/legacy*`；复制 cook 输出里 `RiggedObjects/Characters/Human` 下的文件（女：路径含 `_F/`、`/AVA_YF_`、`/Hair_F/`；男：其余；都跳过 `Materials/`）；复制 `ga_out2/DA_GA_Outfit_072_<G>.*`；`HLMeshProbe patch legacy legacy_hl fit_<g>/skel_ext.json`（显示 `verify`、`WARN`、`FAIL` 行的计数，前 5 种）；`da_animclass.py` 给上衣数据资产注入 `ABP_Karin_<G>_Body`；女：两个发型数据资产注入 `ABP_Karin_F_Hair`，再用 `mi_clone.py` 把 5 个男版材质实例克隆到 `_F` 路径；男：`StuHair03` 发型注入 `ABP_Karin_M_Hair`；打印 `<g> files: <.uasset 数>` | `dami/`、`hairda_out/`、`ga_out2/` → `mod_<g>/legacy_hl` |
| `pack` | 合并各性别的 `legacy_hl` 到 `mod_mf/legacy_hl`；在工作目录里 `retoc to-zen --version UE4_27 mod_mf/legacy_hl mod_mf/out/zzz_KarinDarkArts_<MF\|F>_P.utoc`、`retoc verify`；三个文件打成 `KarinDarkArts.tar.xz`，打印大小和 SHA-256 前 16 位 | → `mod_mf/out/zzz_KarinDarkArts_<MF\|F>_P.pak/.ucas/.utoc` |

与 `build.sh` 不同的地方：任何工具退出码非 0 都会停下（`build.sh` 在 `set -e` 下但没开 `pipefail`，HLMeshProbe 校验失败的退出码被后面的 `grep | sort | uniq | head` 吞掉）；`tar | xz -9 -T0` 换成 Python 的 `tarfile` + `lzma`（预设 9，同样三个成员、同样顺序，字节不同）；Python 子脚本加 `-B` 运行；UE 和 Blender 脚本在本包里原地运行，不再复制到工作目录。

### 2. 安装

游戏关闭时把 `mod_mf/out/` 里的三个文件复制进 `Phoenix\Content\Paks\~mods\`，原来的同名包先备份。只装一个版本（`_MF_P` 和 `_F_P` 不要同时放）。角色创建的要求（脸型第 1 / 14 个、发型第 8 / 17 个）见 [游戏知识](../../games/hogwarts-legacy/README.md) 和 [技术合同](../../games/hogwarts-legacy/TECHNICAL_CONTRACTS.md) §7。

### 3. 快速路线

```powershell
python -B $S/build_mod.py params import cook assemble pack      # 只改物理手感（dyn.json）
python -B $S/build_mod.py export import cook assemble pack      # 只改导出（比如骨的取舍）
# 只改材质分配：重新挂宿主材质实例，不重新导入；之后 cook assemble pack
& $env:HL_UE_CMD "$env:HL_PROJECT\Phoenix.uproject" -run=pythonscript "-script=$((Resolve-Path $S/ue/ue_fixmat.py).Path)" -unattended -nop4 -nosplash -NoSound -stdout -FullStdOutLogOutput
```

手工调 UE 时 `-script=` 的路径不能带空格（UE 只读到空格为止），有空格就先把脚本复制到不带空格的目录；`build_mod.py` 自己调 UE 时会把路径放进引号。

## 离线检查

```powershell
python -B $S/feel_sim.py "$W/fit_f/dyn_nodes.json" KarinHair Hair_tail_L   # 一条链的平面小角度模型：起跑峰值、跑动拖尾、急停后峰值 / 过零次数 / 回到 3° 内的时间
python -B $S/swing_check.py "$W/fit_f"                                     # 大腿前后摆 +55 / +70 / −30°：裙摆节点按外侧碰撞球外摆后，链折线进大腿胶囊的采样数
python -B $S/uasset.py "<包>.uasset" ["<回写>.uasset"]                       # 摘要、import / export / 预加载依赖；给第二个路径时写回并逐字节比较
python -B $S/texdump.py "<贴图>.uasset" [起] [止]; python -B $S/texwalk.py "<贴图>.uexp" <PF_ 名字偏移> <头大小>
& $env:HL_BLENDER -b "$W/fit_f/fit.blend" --python $S/blender/preview.py -- "$W/prev/f" "<dump 的原版网格>.json" …   # 正面 / 侧面 / 摆姿势，原版网格放在右边
& $env:HL_BLENDER -b "$W/fit_f/fit.blend" --python $S/blender/clav_test.py -- "$W/prev/clav.png"                    # 锁骨下压 12° 的颈肩特写
& $env:HL_BLENDER -b "$W/fit_f/fit.blend" --python $S/blender/cmp_upper.py -- "$W/prev/upper.png" KarinHead         # 按脸高取景的上半身正面；加第三个参数（FBX）时渲染源模型
& $env:HL_BLENDER -b --python $S/blender/sk_stats.py -- "<源模型 FBX>" "blink,mayu"   # Body 的形状键：顶点数、最大位移、加权中心、x 范围；空串列出全部
& $env:HL_BLENDER -b --python $S/blender/sk_dir.py -- "<源模型 FBX>" "LookLeft,LookUp"  # 左右两半的平均位移方向
```

`swing_check.py` 的大腿半径 `THR = 8.3` cm 是在 Karin 拟合结果上量的，`feel_sim.py` 的输入是固定的起跑 / 急停曲线（600 cm/s）。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/build_mod.py` | 分步构建驱动（`build.sh` 的 Python 版）：`fit`、`params`、`export`、`import`、`cook`、`assemble`、`pack`；先检查设置和输入，`--dry-run` 只打印 |
| `scripts/dyn_params.py` | `dyn_chains.json` + `skel_ext.json` + `dyn.json` → 每个部件的 AnimDynamics 单骨节点：集中杆模型（每个节点代表余下的整段，长 R、质心在 `com_frac`·R）按「1 g 侧向加速度下的总弯曲」定弹簧、按频率定惯量（盒子截面）、按阻尼比定阻尼；限位（外摆不对称）、碰撞体最近点上的外侧球（半径不超过静止距离）；`sim_every` 隔骨模拟 |
| `scripts/feel_sim.py` | 一条链的平面小角度时域模型，比较参数方案的手感 |
| `scripts/swing_check.py` | 裙摆与摆动大腿的运动学间隙检查 |
| `scripts/uasset.py` | UE 4.27 cooked legacy 包（无版本摘要、带标签属性）的读写：名字 / import / export / 预加载依赖可增改，写出时重算所有头部偏移、`SerialOffset` 和 `BulkDataStartOffset` |
| `scripts/da_animclass.py` | 给角色部件数据资产加 `AnimClass`：三个 import（包、`AnimBlueprintGeneratedClass`、CDO）、`ObjectProperty`、把 CDO 加进该导出的 SerializationBeforeCreate 预加载依赖 |
| `scripts/ga_slot_patch.py` | 装备外观 `OutfitItems`：把一项的 `CharacterPiece` 引用复制到别的项（等长） |
| `scripts/ga_edit.py` | 从 `OutfitItems` 删项并修正标签大小、`SerialSize`、`BulkDataStartOffset`。删掉 Socks / Shoes 会让游戏露出存档肤色的光腿，已改用 `ga_slot_patch.py`；留着是因为它是改长度的参考实现 |
| `scripts/hair_override_patch.py` | 发型数据资产：每个 `MeshOverrides[].Mesh` 指回 `DefaultMesh`（等长） |
| `scripts/mi_clone.py` | 按字节克隆游戏的材质实例到新路径（等长替换整个包里的字符串，尾部哈希和着色器图不动） |
| `scripts/make_tex.py` | 宿主贴图：四张不透明 D、带透明的图集 D、平法线、每种材质一张 MRO 常量图 |
| `scripts/texdump.py`、`scripts/texwalk.py` | 查 cooked 贴图包：名字表、`PF_` 名字位置、十六进制；按 4.27 布局走 `FTexturePlatformData` |
| `scripts/hlskel.py` | 读骨架 JSON 并算全局矩阵的小函数库（`load(文件)` → 数据、骨、全局矩阵、名字索引），交互分析用 |
| `scripts/blender/fit.py` | 拟合：用 Karin 自己的骨架摆进 HL 的 A 姿势、TPS（躯干从腿根到颈、手脚刚性、头部大球刚性、肩宽 / 颈 / 头高偏移）、法线随变形、95 根动态骨（裙、尾、双马尾、侧发、刘海、耳、丝带）作为真实骨、按原版网格的权重分配、按 `face_map.json` 做 HL 同名形变；写 `fit.blend`、`skel_ext.json`、`dyn_chains.json`、部件 FBX |
| `scripts/blender/export_fbx.py` | 导出部件 FBX：骨架改名 `Armature`；`Empty`（髋部极小三角形）、`PhysProxy`、`Skeleton` 代理；不用动态骨的网格去掉游戏骨架里没有的骨（v1.1 的崩溃修复） |
| `scripts/blender/preview.py`、`cmp_upper.py`、`clav_test.py` | 渲染检查（见上） |
| `scripts/blender/extract_tex.py` | 从 FBX 里取出贴图存成 PNG |
| `scripts/blender/sk_stats.py`、`sk_dir.py` | 源模型形状键的统计，写 `face_map.json` 时用 |
| `scripts/ue/ue_import.py` | UE 编辑器 Python：占位骨架 / 物理资产 / `MM_Prop` / 宿主材质实例，导入贴图，导入 Karin 骨架和网格（先删再导入），挂材质槽，生成动画蓝图 |
| `scripts/ue/ue_fixmat.py` | 只重新挂材质槽，不重新导入 |
| `configs/` | 案例配置：`fit_<m\|f>.json`（拟合参数、部件表、源 FBX、dump 路径）、`ue_build_<m\|f>.json`（宿主材质实例、贴图、网格目标路径、Karin 骨架、动画蓝图）、`dyn.json`（每类链的手感目标）、`face_map.json`（HL 形变 ← Karin 形状键） |
| `ue/Phoenix/` | 占位工程：`Phoenix.uproject`（PythonScriptPlugin、EditorScriptingUtilities、HLKTools）、`Config/DefaultEngine.ini`、`Config/DefaultGame.ini` |
| `ue/HLKTools/` | 编辑器插件：`UHLKToolsLibrary::CreateDynamicsAnimBlueprint(路径, 骨架, CopyPose JSON, 节点 JSON)` |
| `hlmeshprobe/` | HLMeshProbe 源码、CUE4Parse 补丁、基准提交 |

## 输出与本机信息

- **中间结果：** `fit_log.txt`、`fit.blend`、FBX（SceneInfo 里有源路径）、`ue_build.json`、`cook.log` 记有本机路径；`dump*/` 和 `dami/` 是游戏数据。这些都不要收进本仓库。
- **发行物：** 三件套和 `KarinDarkArts.tar.xz` 里是 cook 出来的包，没有逐个查本机路径。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时要按新模型重写：

- `fit.py`：Karin 的骨名（`chain_targets`、`GROUPS`、`hl_group_for`）、动态骨前缀 `DYN_PREFIX` / `DYN_STATIC` / `HL_PARENT`、裙摆权重 `skirt_w`；
- `fit_<m|f>.json`：部件的对象名和材质 → 槽，比例参数（`g_perp`、`g_head`、`g_hand`、`g_foot`、`skirt_leg`、`head_offset`、`neck_offset`、`shoulder_offset`、`shoulder_in`），男女不同；
- `face_map.json`（Karin 形状键名，含日文）、`dyn.json`（四轮实机调出来的手感）；
- `make_tex.py` 的贴图文件名和粗糙度，`swing_check.py` 的 `THR`。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 资产路径：`ue_build_<m|f>.json` 的网格、材质实例、贴图路径，`build_mod.py` 的 `F_HAIR`、`M_HAIR`、`MI_CLONES` 和性别筛选规则，`ue_import.py` 的 `Biped_Skeleton`、`Biped_PhysicsAsset`、`MM_Prop`；
- 更新后的网格格式（每个 render section 多一个 uint32）和 HLMeshProbe 的补丁位置；材质实例尾部的 20 字节哈希；
- `Biped_Skeleton` 的骨（网格的每根骨都必须在它引用的骨架里）；
- retoc 版本和 IoStore 的 toc 版本。

## 已验证与边界

- **实机。** v12 的物理和表情由用户在游戏里认可（2026-10-19）。女巫版 v1.0 玩几分钟后崩溃（转储：按骨骼分层混合在 `Ear_L` 处访问冲突）；v1.1（`export_fbx.py` 给绑 `Biped_Skeleton` 的网格去掉 Karin 多出的骨）2026-10-23 重建（cook 0 错误、retoc verify 通过、绑 `Biped_Skeleton` 的网格里没有 `Ear_L`、头部仍有 56 个形变），用户玩了一阵没有闪退。这些都是项目用原脚本（`build.sh`）构建的。
- **便携版本身只做了离线核对（2026-10-23）：** Python 全部过语法检查；`scripts/` 下 14 个命令的 `--help`；下面的合成测试；Blender、UE、插件、HLMeshProbe 和 retoc 一侧只核对了改动，没有重跑。详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。`HogwartsLegacyTools` 不需要游戏、Blender、UE 或 retoc：`dyn_params.py` 在合成骨架和链上的节点（阻尼 < 1、弹簧、外摆不对称限位、`sim_every`、碰撞球不从体内开始），`feel_sim.py`、`swing_check.py` 的输出；合成 legacy 包上的 `uasset.py` 逐字节往返、`da_animclass.py`（import、属性、预加载依赖、偏移）、`ga_slot_patch.py`、`ga_edit.py`、`hair_override_patch.py`、`mi_clone.py` 及其拒绝路径；`build_mod.py` 的设置检查、`--dry-run`、用替身工具跑 `fit export import cook assemble pack` 和 `params`；PROVENANCE 与可移植性。没装 numpy 时物理那一项跳过。
- **测试没覆盖的部分：** Blender 脚本、UE Python、C++ 插件和 HLMeshProbe 只做语法检查或不在 Python 测试里；`build_mod.py` 对真 Blender / UE / HLMeshProbe / retoc 的调用没有在本包里跑过；`fit.py` 的 Blender 4.1+ 法线分支没跑过；非 Windows 系统。
- **便携改动：**
  - `build.sh` 改写成 `build_mod.py`（`.sh` 不是本库允许的文件类型；工作盘符、`$TEMP` 下的 HLMeshProbe、Blender / UE / retoc 路径改为参数或环境变量）；
  - `ue_import.py`、`ue_fixmat.py` 的配置路径改从 `HL_UE_BUILD` / `HL_UE_BUILD_CONFIGS` / `HL_WORK` 取；
  - 没有 argparse 的命令补上了 argparse，位置参数不变；
  - `configs/` 里的绝对路径换成 `<HL_WORK>/…` 和 `<KARIN_FBX>`；
  - 换行统一成 LF；补丁文件改扩展名为 `.patch.txt`；`HLProbe.cs` 单独放到 `hlmeshprobe/CUE4Parse/`。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md) 和 [PROVENANCE.json](../PROVENANCE.json)。
- **没有收进本包：** 测试机远程辅助脚本（`tools/remote/*`）和虚拟手柄工具；会话里的一次性探针和实验脚本（`session_py/`、`session_bl/`）；女性骨架 JSON 的合成脚本；工作目录里的配置副本和日志；源模型、游戏数据、dump、cook 结果、FBX、blend、编好的插件和 HLMeshProbe、发行包。
- **署名：** HLMeshProbe 建立在 FabianFG 的 CUE4Parse 上（本包只带补丁，不含它的源码），打包用 retoc，见 [工具来源](../../references/TOOL_SOURCES.md)。
