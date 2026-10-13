# 师父（Sifu）便携包

先读 [游戏知识](../../games/sifu/README.md) 和 [构建流程](../../games/sifu/BUILD_PIPELINE.md)。pak、骨架、材质槽、物理资产的约定见 [技术合同](../../games/sifu/TECHNICAL_CONTRACTS.md)；骨链和裙摆见 [物理](../../games/sifu/PHYSICS.md)；SifuExport、编辑器插件和命令行 UE 见 [开发工具](../../games/sifu/DEV_TOOLING.md)。

这是五个 Karin 替换女主默认服装 `SK_W_MainChar_01` 的 Mod（Karin Original v6，以及 OPT、PT、Umbrella、Y 四个变体 v1）实际使用的工具：Blender 构建脚本、贴图和发行用的 Python 脚本、UE 4.26 编辑器 Python、编辑器插件 SifuModTools 的 C++ 源码、C# 写的 SifuExport（CUE4Parse 命令行）和 PowerShell 工具。

- **游戏版本：** Steam App 2138710，buildid `18739835`，游戏内版本 `v_1.29_6.775`。资源只有一个 `Sifu\Content\Paks\pakchunk0-WindowsNoEditor.pak`（pak v11，索引 AES 加密）。Mod pak 放进 `Sifu\Content\Paks\~mods\`，`.sig` 直接复制游戏自己的。
- **AES 密钥：** 本包不含密钥，也不要把它写进脚本或提交。`tools/sfx_run.ps1` 从环境变量 `SIFU_AES`（或 `-Aes`）读，直接运行 SifuExport 时也读 `SIFU_AES`。找法：在 `Sifu-Win64-Shipping.exe` 里搜立即数逐段写栈的指令序列（编进 exe 的密钥被拆成一串立即数写到栈上），拼出候选后去解密 pak 索引，开头能读出挂载点 `../../../` 就是对的，见技术合同 §1。读自己的 mod pak 不需要密钥。
- **SifuExport：**
  - 源码在 `sifuexport/`，NuGet 依赖 CUE4Parse 和 CUE4Parse-Conversion `1.2.2.202610`，面向 net10.0（win-x64，`CETCompat=false`），要用 .NET 10 SDK 编译；
  - 请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包；
  - 命令：`list <正则>`、`json <包>…`、`raw <包>…`、`export <uemodel|gltf|psk> <包>…`、`skel <包>…`、`anim <包> <帧号>…`、`file <路径>…`、`grep <正则> <字符串>…`。`anim` 的帧号必须小于 `numFrames`；
  - 环境变量：`SIFU_AES`，`SIFU_GAME`（默认 `GAME_UE4_26`），可选 `SIFU_USMAP`、`SIFU_OODLE`。
- **UE：** 4.26.2（Epic 启动器版）。编插件要 Visual Studio 构建工具（项目装的是 VS2019 Build Tools，UBT 实际选用了 VS2022 MSVC 14.44）。内容工程模板在 `ue/SifuProj/`（`Sifu.uproject` 和 `Config/`），插件源码在 `ue/SifuModTools/`。
- **Blender：** 4.2.23 LTS，用 `-b --factory-startup` 运行；不加 `--factory-startup` 时会加载用户装的第三方插件。Blender 脚本用 Blender 自带的 Python 3.11 和 numpy。
- **Python：** 3.10 或更高。`dyn_tuning.py` 和 `package_release.py` 只用标准库；`make_textures.py` 另需 numpy 和 Pillow，`frames_to_gif.py` 另需 Pillow。`requirements.txt` 钉的 numpy 2.5.2 要 Python 3.12 或更高；本次在 3.14.0、numpy 2.5.2、Pillow 12.3.0 上测试。
- **两台机器：** 项目在本机跑 Blender 和贴图，在装 UE 的构建机上跑 SifuExport 提取、UE 导入、cook 和打包。两边的路径都用环境变量或参数给，也可以是同一台机器。
- **只在 Windows 上：** UE 4.26 编辑器、UnrealPak、SifuExport（win-x64）和 PowerShell 工具。PowerShell 命令按 PowerShell 7（`pwsh`）写。
- **运行位置：** 以下命令都从交接包根目录执行。

## 环境变量与参数

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `SIFU_MODELS_DIR` | `scripts/blender/profiles.py`，经它影响 Blender 构建、`bake_ao.py`、`preview_model.py`、`make_textures.py` | 源模型根目录，下面是 `Karin_Original/`、`Karin_Original_PicodraTech/`、`Karin_PicodraTech/`、`Karin_Umbrella/`、`Karin_Y_BlenderSafe/`。没设时路径里是 `<SIFU_MODELS_DIR>`，载入会报找不到文件 |
| `SIFU_BASE_SKEL` | `scripts/blender/sifu_common.py` 的 `skel_parents()` | `Base_skeleton` 的 skel JSON。也可以写在 build_cfg 的 `base_skel`，后者优先；两个都没有时报错 |
| `SIFU_WORK_ROOT` | `tools/*.ps1` | 构建机工作目录：`work\`（上传的构建、`py_args.json`）、`logs\`、`out\`、`cache\`（SifuExport 输出）、`cap\`（抓屏）、`tools\SifuExport\`、`pluginsrc\`、`build\`。各脚本也接受 `-WorkRoot` |
| `SIFU_UE_ROOT` | `ue_run.ps1`、`cook_pak.ps1`、`build_plugin.ps1` | UE 4.26 安装目录（含 `Engine\`），或 `-UERoot` |
| `SIFU_PROJECT` | 同上 | 内容工程目录（含 `Sifu.uproject`），或 `-Project`；默认 `<SIFU_WORK_ROOT>\SifuProj` |
| `SIFU_GAME_DIR` | `sfx_run.ps1`、`cook_pak.ps1`、`package_release.py` | 游戏安装目录（含 `Sifu\Content\Paks`），或 `-GameDir` / `--game-dir`。`package_release.py` 只把它当安装说明里的示例路径 |
| `SIFU_AES` | `sfx_run.ps1`（或 `-Aes`）、SifuExport | 游戏 pak 的 AES 密钥（`0x…`） |
| `SIFU_PY_ARGS` | `scripts/ue/*.py` | 由 `ue_run.ps1` 设置：`<SIFU_WORK_ROOT>\work\py_args.json` 的路径，里面是传给 UE Python 的参数列表 |

其他参数：`sfx_run.ps1 -Exe`（默认 `<SIFU_WORK_ROOT>\tools\SifuExport\SifuExport.exe`），`build_plugin.ps1 -Plugin`（默认 `<SIFU_WORK_ROOT>\pluginsrc\SifuModTools\SifuModTools.uplugin`）和 `-Package`（默认 `<SIFU_WORK_ROOT>\build\SifuModTools`），`burst.ps1 -Dir`（默认 `<SIFU_WORK_ROOT>\cap`），`make_textures.py --flat-dir`，`package_release.py --out-root` / `--release-dir` / `--game-dir`。

## 构建流程

项目用 `build_model.sh`（本机：Blender 构建、预览、AO、贴图）和 `ship_model.sh`（上传、UE 构建、cook、取回、读回检查）两个驱动脚本；本包把它们拆成下面的分步命令。以变体 `y` 为例，profile 见后面的表。

### 0. 一次性准备

构建机上：

```powershell
$Kit = "portable-kits/sifu"; $T = "$Kit/tools"
$env:SIFU_WORK_ROOT = "<构建机工作目录>"
$env:SIFU_UE_ROOT = "<UE_4.26 安装目录>"
$env:SIFU_GAME_DIR = "<Steam 库>\steamapps\common\Sifu"
$env:SIFU_AES = "<游戏 pak 密钥 0x…>"
$R = $env:SIFU_WORK_ROOT
New-Item -ItemType Directory -Force "$R/work", "$R/scripts", "$R/src" | Out-Null

# a) SifuExport：复制到仓库外编译
Copy-Item -Recurse $Kit/sifuexport "$R/src/SifuExport"
dotnet build "$R/src/SifuExport/SifuExport.csproj" -c Release -o "$R/tools/SifuExport"

# b) 参照数据（输出在 $R/cache/<子目录>/ 下，保持包路径）
pwsh -NoProfile -File $T/sfx_run.ps1 base skel Sifu/Content/Characters/MainChar/W/Meshes/SK_W_MainChar_01 Sifu/Content/Characters/Skeleton/Base_skeleton
pwsh -NoProfile -File $T/sfx_run.ps1 gltf export gltf Sifu/Content/Characters/MainChar/W/Meshes/SK_W_MainChar_01
pwsh -NoProfile -File $T/sfx_run.ps1 face json Sifu/Content/Animations/01_FacialPoseAsset/MC_woman_facial_PoseAsset
pwsh -NoProfile -File $T/sfx_run.ps1 base list "MC_man_barehands_V3_north|MainChar_Attack_Special_FrontKick"   # 查动画的完整包路径
pwsh -NoProfile -File $T/sfx_run.ps1 anim anim "<跑步动画包>" 0 2 4 6 8 10 12 14 16

# c) UE 内容工程和插件
Copy-Item -Recurse $Kit/ue/SifuProj "$R/SifuProj"
New-Item -ItemType Directory -Force "$R/SifuProj/Plugins" | Out-Null
Copy-Item -Recurse $Kit/ue/SifuModTools "$R/pluginsrc/SifuModTools"
pwsh -NoProfile -File $T/build_plugin.ps1                   # 成功时打印 PLUGIN_OK，插件装进 SifuProj/Plugins
Copy-Item $Kit/scripts/ue/*.py "$R/scripts/"
pwsh -NoProfile -File $T/ue_run.ps1 "$R/scripts/scripts_smoke.py" "$R/work/smoke.json"   # 可选：确认插件函数可用
```

把 `$R/cache` 里的 W 骨架 JSON、W glTF、`Base_skeleton` JSON、面部姿势 JSON 和动画 JSON 复制到本机。编辑器里的 `Base_skeleton` 要按游戏参考姿势重建一次：本机生成参考 FBX（`$Blender`、`$W` 见下一节），复制到构建机后导入：

```powershell
& $Blender -b --factory-startup --python $Kit/scripts/blender/make_skeleton_fbx.py -- "<Base_skeleton.Base_skeleton.skel.json>" "$W/SK_BaseSkeletonRef.fbx"
# 构建机：
pwsh -NoProfile -File $T/ue_run.ps1 "$R/scripts/ue_import_skeleton.py" "$R/work/SK_BaseSkeletonRef.fbx" "$R/work/skel_import.json"
```

### 1–5. 本机：Blender 构建、预览、AO、贴图（代替 `build_model.sh`）

```powershell
python -m pip install -r requirements.txt -r portable-kits/sifu/requirements.txt
$Kit = "portable-kits/sifu"
$Blender = "<Blender 4.2.23 目录>\blender.exe"
$env:SIFU_MODELS_DIR = "<源模型根目录>"
$W = "../MyMod/Work"; $P = "y"
New-Item -ItemType Directory -Force "$W/$P" | Out-Null
$Wp = (Resolve-Path "$W/$P").Path                            # Blender 的输出路径要用绝对路径

# 1. build_cfg.json（每个 profile 一份）
@{ w_skel = "<…>/SK_W_MainChar_01.SK_W_MainChar_01.skel.json"; w_glb = "<…>/SK_W_MainChar_01.glb"
   pose_asset = "<…>/MC_woman_facial_PoseAsset.json"; base_skel = "<…>/Base_skeleton.Base_skeleton.skel.json"
   scale = 1.4; w_face_width_cm = 16.95; face_rig = $true; profile = $P
   out_blend = "$Wp/karin_sifu.blend"; out_fbx = "$Wp/SK_W_MainChar_01.fbx"
   out_report = "$Wp/build_report.json"; out_cloth = "$Wp/cloth.json" } |
  ConvertTo-Json | Set-Content -Encoding utf8NoBOM "$Wp/build_cfg.json"

# 2. 构建：日志里有 BUILD_DONE 才算成功
& $Blender -b --factory-startup --python $Kit/scripts/blender/build_karin.py -- "$Wp/build_cfg.json" *> "$Wp/build.log"
Select-String -Quiet BUILD_DONE "$Wp/build.log"

# 3. 预览（可选）：静止、跑步动画第 3 个解码帧、前踢第 6 个解码帧，带贴图；日志里有 PREVIEW_DONE
& $Blender -b --factory-startup "$Wp/karin_sifu.blend" --python $Kit/scripts/blender/preview_model.py -- $P "$Wp/preview.png" "<跑步>.anim.json" 3 "<前踢>.anim.json" 6

# 4. AO：有 slots 的 profile 每个图集页一张 ao/AO_<页>.png；日志里有 BAKE_DONE
& $Blender -b --factory-startup "$Wp/karin_sifu.blend" --python $Kit/scripts/blender/bake_ao.py -- "$Wp/ao" 1024 $P *> "$Wp/bake.log"

# 5. 贴图和 ue_build.json；第三个参数是构建机上接收这些文件的目录
python -B $Kit/scripts/make_textures.py $P $Wp "<构建机工作目录>/work/$P"
```

- `karin_original` 不写 `profile`（或写 `karin_original`），可以另给 `karin_vrm` 指定 VRM。它的 `bake_ao.py` 不走图集页模式，直接写出 `T_Karin_<槽>_S.png`；BaseColor 是 VRM 内嵌贴图原样，`ue_build.json` 是手写的（格式与 `make_textures.py` 的输出相同）。`make_textures.py` 只处理带 `slots` 的变体。
- `make_textures.py` 默认生成 `T_Karin_Flat_N.png`（64×64，RGB 128/128/255）和 `T_Karin_Black.png`（16×16 黑），字节与项目里的文件相同；`--flat-dir` 改为从现成文件复制。

### 6–9. 构建机：UE 导入、cook、取回和检查（代替 `ship_model.sh`）

```powershell
# 6. 上传：$Wp 下的 SK_W_MainChar_01.fbx、cloth.json、ue_build.json 放到 $R/work/<P>/，tex/*.png 放到 $R/work/<P>/tex/（先清掉旧 PNG）
# 7. 导入网格、材质、布料、骨链；看 $R/work/<P>/ue_build_out.json 的 log（commandlet 日志里看不到 Python 的输出）
pwsh -NoProfile -File $T/ue_run.ps1 "$R/scripts/ue_build_mesh.py" "$R/work/$P/ue_build.json"

# 8. cook 和打包；PakName / AssetDir 取 profile 的 pak / asset_dir
python -B -c "import sys; sys.path.insert(0, '$Kit/scripts/blender'); import profiles; p = profiles.activate('$P'); print(p['pak'], p['asset_dir'])"
pwsh -NoProfile -File $T/cook_pak.ps1 pakchunk99-KarinY_P -AssetDir Karin_Y
```

把 `$R/out/<pak>.pak` 和 `.sig` 取回本机的 `$Out/<P>/`，两边各算一次 MD5 核对。然后只挂载这个目录读回（不给 AES）：

```powershell
# 9. 读回检查：每个材质槽和 PostProcessAnimBlueprint 都要指向 /<asset_dir>/ 下
$Out = "../MyMod/Out"
Remove-Item Env:SIFU_AES -ErrorAction Ignore; $env:SIFU_GAME = "GAME_UE4_26"
& "<SifuExport.exe>" "$Out/$P" "$W/pakcheck" json Sifu/Content/Characters/MainChar/W/Meshes/SK_W_MainChar_01
@'
import re, sys
s = open(sys.argv[1], encoding="utf-8").read()
mats = re.findall(r'"MaterialSlotName":\s*"([^"]+)",\s*"Material":\s*\{[^}]*"ObjectPath":\s*"([^"]+)"', s)
pp = re.search(r'"PostProcessAnimBlueprint":\s*\{[^}]*"ObjectPath":\s*"([^"]+)"', s)
d = "/" + sys.argv[2] + "/"
ok = mats and all(d in p for _, p in mats) and pp and d in pp.group(1)
print("PAK CHECK", "OK" if ok else "FAIL", [m for m, _ in mats], pp.group(1) if pp else None)
'@ | Set-Content -Encoding utf8NoBOM "$W/pakcheck.py"
python -B "$W/pakcheck.py" (Get-ChildItem -Recurse "$W/pakcheck" -Filter SK_W_MainChar_01.json | Select-Object -First 1).FullName Karin_Y
```

### 10. 发行

```powershell
python -B $Kit/scripts/package_release.py $P 1 2026-10-13 --out-root $Out --release-dir ../MyMod/Release --game-dir "<安装说明里举例的游戏目录>"
```

写出 `<release-dir>/<pak>/`（pak、sig、`安装说明.txt`）和 `<release-dir>/<pak>_v<版本>.zip`，说明里有替换范围、互斥的同类 mod 和 MD5。只支持四个变体（`INFO` 里没有 `karin_original`）。安装：把 pak 和 sig 一起放进游戏的 `Sifu\Content\Paks\~mods\`，五个 Karin pak 一次只装一个。

### 只调物理

```powershell
python -B $Kit/scripts/dyn_tuning.py "$Wp/cloth.json"   # 就地重算骨链参数，不用重跑 Blender；打印每节的 I_sub/I_com、S、D
```

上传新的 `cloth.json`，把 `ue_build.json` 复制一份并加上 `"physics_only": true`，再跑 `ue_build_mesh.py`：它只重建 `PA_Karin_Dynamics` 和后处理动画蓝图。然后照常 cook。UE 工程里同时只有一个 `SK_W_MainChar_01`，换模型 cook 之前要先用那个模型的 `ue_build.json` 重新导入。

### 离线检查和实机抓屏

```powershell
& $Blender -b "$Wp/karin_sifu.blend" --python $Kit/scripts/blender/pose_preview.py -- "<动画>.anim.json" "$W/pose" 0 3 6
& $Blender -b "$Wp/karin_sifu.blend" --python $Kit/scripts/blender/preview_face.py -- "<MC_woman_facial_PoseAsset.json>" "$W/face" "Facial Blink"
& $Blender -b "$Wp/karin_sifu.blend" --python $Kit/scripts/blender/skirt_sim.py -- "$W/skirt.json" "$Wp/cloth.json" '{}' "<跑步>.anim.json" "<踢腿>.anim.json"
```

`skirt_sim.py` 只适用于有裙摆代理（`Proxy_Skirt`）的 `karin_original`。实机抓屏在游戏所在的用户桌面会话里进行：

```powershell
# Win+R 启动，隐藏运行；抓图目录用 -Dir 指定（默认 <SIFU_WORK_ROOT>\cap）
pwsh -NoProfile -WindowStyle Hidden -File "<路径>\burst.ps1" -Dir "<抓图目录>"
Set-Content "<抓图目录>\go.txt" "45 66 run 0.5"            # 45 帧，间隔 66 ms，标签 run，缩放 0.5；写 quit 停止
python -B $Kit/scripts/frames_to_gif.py "<抓图目录>" run "$W/run"          # 可加裁剪框 x0 y0 x1 y1 和联系表列数
```

用完删掉抓图目录。游戏要先点一下窗口才收键盘输入。

### profile

| profile | 源模型（`SIFU_MODELS_DIR` 下） | pak | `asset_dir` | 发行 |
| --- | --- | --- | --- | --- |
| `karin_original` | `Karin_Original/Karin(Clone).vrm` | `pakchunk99-KarinOriginal_P` | `Karin` | v6 |
| `opt` | `Karin_Original_PicodraTech/Karin_Original_PicodraTech_Optimized.blend` | `pakchunk99-KarinOriginalPicodraTech_P` | `Karin_OPT` | v1 |
| `pt` | `Karin_PicodraTech/Karin_PT_Unified_Atlas.blend` | `pakchunk99-KarinPicodraTech_P` | `Karin_PT` | v1 |
| `umb` | `Karin_Umbrella/Karin_Umbrella_Unified_Atlas.blend` | `pakchunk99-KarinUmbrella_P` | `Karin_UMB` | v1 |
| `y` | `Karin_Y_BlenderSafe/Karin_Y_GeneralWorkflow.blend` | `pakchunk99-KarinY_P` | `Karin_Y` | v1 |

字段含义和新模型的加法见构建流程 §8。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/blender/build_karin.py` | Blender 内运行的构建入口：按 profile 载入源模型，用自己的蒙皮摆进 W 的 A 姿势并应用，放 Sifu 关节，改权重，调用各阶段，写 FBX（骨架对象名 `Armature`）、`cloth.json`、`build_report.json`、`karin_sifu.blend` |
| `scripts/blender/source_prep.py` | 把任意 profile 源（.vrm / .glb / .fbx / .blend）整理成 Karin_Original VRM 导入后的状态：米制、单位对象变换、VRM 人形骨名、角色网格名、profile 材质槽、烘焙的形状键组合，剔除图集里全透明的面 |
| `scripts/blender/profiles.py` | 每个模型一个 profile（案例数据），不依赖 bpy；`make_textures.py`、`package_release.py` 也读它 |
| `scripts/blender/sifu_common.py` | UE 与 Blender 坐标换算、骨架 JSON 读取、建骨架、FBX 导出设置 |
| `scripts/blender/face_stage.py` | 面部：W 面部骨按 TPS 放到 Karin 脸上，迁移面部权重，按游戏的眨眼姿势拟合眼睑枢轴，按口型键拟合嘴 |
| `scripts/blender/cloth_stage.py` | 模拟件分槽、裙摆代理网格（NvCloth）、碰撞胶囊、复制 W 顶点色 |
| `scripts/blender/dyn_stage.py` | 骨链：在 `Base_skeleton` 备用骨上搭链、改权重，写 `PA_Karin_Dynamics` 和 RigidBody 节点的 JSON |
| `scripts/blender/torso_weights.py` | 把 W 的骨盆 / 脊椎权重分布按高度和扇区套到皮肤、上衣和裙腰上 |
| `scripts/blender/bake_ao.py` | 从构建结果烘焙 AO：有 `slots` 时每个图集页一张 `AO_<页>.png`，否则直接写 `T_Karin_<槽>_S.png` |
| `scripts/blender/preview_model.py` | 带贴图的全身联系表（静止和给定动画帧，多角度） |
| `scripts/blender/pose_preview.py` | 把构建结果摆进 SifuExport 解出的动画姿势渲染（正、侧、3/4、腰部前后） |
| `scripts/blender/preview_face.py` | 按游戏面部姿势资产渲染表情（眨眼、口型等） |
| `scripts/blender/skirt_sim.py` | 裙摆代理的时间步进替身（PBD），在游戏动画里比较参数方案 |
| `scripts/blender/make_skeleton_fbx.py` | 由 `Base_skeleton` JSON 生成参考 FBX（每骨一个小四面体），供编辑器重建 `Base_skeleton` |
| `scripts/dyn_tuning.py` | 骨链参数：质量、阻尼、限位、按 `S = w² · I_sub / I_com` 定的驱动、碰撞过滤和 RigidBody 节点设置；`dyn_stage.py` 调用，也能就地改 `cloth.json` |
| `scripts/make_textures.py` | 每个槽一张 2048 BaseColor（`_C` / `_CS`）和一张 ComboMap（`_S_<kind>`：R 粗糙度、G 金属 0、B AO、A 230 / 255），外加平法线和黑遮罩；写 `ue_build.json` |
| `scripts/package_release.py` | 发行文件夹和 zip，安装说明含 MD5 |
| `scripts/frames_to_gif.py` | 把 `burst.ps1` 的抓图拼成 GIF 和带时间标注的联系表 |
| `scripts/ue/ue_build_mesh.py` | UE 编辑器 Python：建占位母材质和物理资产，导入贴图建 MIC，以 `Base_skeleton` 导入 FBX，整体写回材质列表并断言，建布料和骨链，写 `ue_build_out.json` |
| `scripts/ue/ue_import_skeleton.py` | 导入参考 FBX，把骨架资产命名为 `/Game/Characters/Skeleton/Base_skeleton`，导出导入后的参考骨架 |
| `scripts/ue/verify_mesh.py` | 导出 `SK_W_MainChar_01` 的 LOD0 section 摘要 |
| `scripts/ue/scripts_smoke.py` | 输出引擎版本和 SifuModToolsLibrary 的函数列表，检查插件是否加载 |
| `tools/sfx_run.ps1` | 对游戏 pak 运行 SifuExport（密钥来自 `SIFU_AES`） |
| `tools/ue_run.ps1` | 用 commandlet 跑 UE Python；参数经 `py_args.json` 传，日志在 `logs\` |
| `tools/cook_pak.ps1` | cook 工程，只挑 `SK_W_MainChar_01.*` 和 `W/<AssetDir>/` 下的资产打 pak，复制游戏的 `.sig` |
| `tools/build_plugin.ps1` | 用 UAT 编插件并装进工程 |
| `tools/burst.ps1` | 用户桌面会话里的抓屏守护进程，由 `go.txt` 触发 |
| `sifuexport/` | SifuExport 源码（`Program.cs`、`SifuExport.csproj`） |
| `ue/SifuModTools/` | 编辑器插件源码：`CreateClothProxy`（带 backstop）、`CreateClothFromSection`、`RemoveAllClothing`、`BuildPhysicsAsset`（含 tapered 胶囊）、`CreatePhysicsAsset`、`SetupRigidBodyPostProcess`、`DumpRefSkeleton`、`DumpSections`、`SetPostProcessAnimBlueprint` |
| `ue/SifuProj/` | 内容工程模板：`Sifu.uproject`（PythonScriptPlugin、EditorScriptingUtilities、SifuModTools）和 `Config/*.ini`（`bShareMaterialShaderCode=False`、不用 IoStore） |

脚本注释里的 `PROJECT_STATE.md` 指项目的私有日志，对应本库的 [技术合同](../../games/sifu/TECHNICAL_CONTRACTS.md) 和 [构建流程](../../games/sifu/BUILD_PIPELINE.md)。`build_karin.py` 注释提到的 `analyze_weights.py` 是测 W 扭转骨权重分布的一次性脚本，没有迁入，测得的值写在 `TWIST` 里。

## 输出与本机信息

- **中间结果：**
  - `build_report.json` 的 `config`（build_cfg 原样）和 `source_prep.src` 记有本机路径；
  - FBX 的 SceneInfo 记有源 `.blend` 路径；Original 的 FBX 里贴图和视频节点也记有输出目录；
  - `karin_sifu.blend` 是 Blender 文件，记有路径；
  - `ue_build.json`、`py_args.json`、`ue_build_out.json` 记有构建机路径。

  这些文件分享前要处理，不要收进本仓库。
- **发行物：** 用 SifuExport 读回的烘焙网格 JSON 里没有本机路径，pak 里的其他资产没有逐个查。`安装说明.txt` 里的示例游戏目录来自 `--game-dir`（默认 `SIFU_GAME_DIR`，都没给时是占位文字）。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时，要按新模型的骨名、网格、材质和图集重写：

- `profiles.py`：五个 profile（源文件、pak、`asset_dir`、网格和材质映射、图集页、骨链规格）和 `T_*` 调参预设；
- `build_karin.py`：build_cfg 的 `scale`（1.4）、`w_face_width_cm`（16.95）默认值，`TWIST` 扭转骨分布；
- `face_stage.py`：Karin 的形状键名 `SHAPE_KEYS`、`POSE_TARGETS`、`BLINK_GAIN`、`EYE_WEIGHT`；
- `cloth_stage.py`：`CHAINS`、`SKIRT`（裙摆代理 11 × 32、最大距离 16 cm）、`SKIRT_CFG`、`SKIRT_COLLIDERS`；`dyn_stage.py` 的 `CHAINS`（Original 的骨链）；
- `torso_weights.py`：`TARGETS`、`SKIRT_BAND`、`SKIRT_BAND_FRONT`、`SKIRT_BAND_ANG`；
- `dyn_tuning.py`：`CHAINS`（Original 的链参数）和 `NODE`（RigidBody 节点设置）；
- `make_textures.py`：`KIND`（粗糙度、ComboMap alpha、AO 强度、父材质）和材质参数；
- `package_release.py`：`INFO`、`FAMILY` 和安装说明的文字。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 资产路径：`/Game/Characters/MainChar/W/Meshes/SK_W_MainChar_01`、`/Game/Characters/Skeleton/Base_skeleton`，以及 `ue_build_mesh.py` 的 `MASTERS`、`PARENT_MI`、`PLACEHOLDER_PA`（母材质、W 材质实例、两个物理资产的路径和参数名）；
- 槽位：W 的第 2、3 套服装覆盖槽 11–16 和 18，可见槽只能在 0–10（`build_karin.py` 超过 11 个材质时报错）；
- `Base_skeleton` 的骨序：RigidBody 节点按骨架骨号存，骨链只能用骨架里已有的备用骨；
- pak 版本、加密方式和 `.sig` 校验方式；游戏更新后密钥可能变。

## 已验证与边界

- **实机。** Karin Original v6 由用户在游戏里确认（「基本好了」）。四个变体 v1 只做了离线检查（预览联系表、面部姿势、pak 引用），没有进游戏。
- **便携版本身只做了离线验证（2026-10-13）：**
  - Blender 构建：`karin_original` 和 `y` 用本包脚本重跑，`cloth.json` 与项目的逐字节相同（Original 与 v6 相同）；`build_report.json` 除 4 个输出路径外相同；FBX 解码后数据相同，只差创建时间、源文件路径和 Blender 每次随机的对象 ID；`.blend` 的网格、权重、UV、顶点色、骨架数据相同；
  - `y` 的 AO、13 张贴图和 `ue_build.json` 与项目逐字节相同；
  - `package_release.py` 对项目的 `y` pak 重做，发行文件夹三个文件和 zip 内三个成员与发行包逐字节相同，zip 本身只差说明文件的时间戳；
  - UE 一侧（`ue_run.ps1`、`cook_pak.ps1`、`build_plugin.ps1`、`sfx_run.ps1`、`burst.ps1`、`scripts/ue/*.py`、插件、SifuExport）没有重跑，只核对了改动；
  - 详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中有 Sifu 合成测试，不需要游戏、Blender 或 UE：`dyn_tuning.py` 的驱动公式、碰撞过滤和就地改写，`make_textures.py` 的贴图通道和 `ue_build.json`，`package_release.py` 的发行文件夹和 zip，`frames_to_gif.py` 的 GIF 和联系表。`--help` 测试覆盖 `scripts/` 下全部 4 个脚本；`make_textures.py` 和 `frames_to_gif.py` 在没装 numpy 或 Pillow 时跳过。
- **测试没覆盖的部分：** Blender 脚本只做语法检查；UE Python、PowerShell、C++ 插件和 SifuExport 不在 Python 测试里。
- **便携改动：**
  - 去掉写死的本机路径，改为环境变量或参数（见上表）；
  - `sfx_run.ps1` 里的密钥删掉，改从 `SIFU_AES` / `-Aes` 读；
  - 没有 argparse 的 Python 命令补上了 argparse；
  - 换行统一成 LF。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md)。
- **没有收进本包：**
  - 一次性探针：`analyze_weights.py`、`face_probe.py`、`inspect_sources.py`、`measure_w_head.py`、`pdbgrep*.py`、构建目录里的检查脚本（`fbxcheck.py`、`normcheck.py`、`uvcheck.py`、`vcol.py`、`tagwalk.py`）；
  - `patch_rigidbody.py`：给插件源码追加 `SetupRigidBodyPostProcess` 的一次性脚本，改动已经在随包的插件源码里；
  - 早期快速预览 `preview.py`、`preview_proxies.py`：已被 `preview_model.py`、`pose_preview.py` 取代；
  - `build_model.sh`、`ship_model.sh`：拆成上面的分步命令；它们依赖本机目录和 ssh 别名；
  - 游戏 AES 密钥、源模型、游戏数据、提取出的 JSON / glTF / 动画、生成的贴图、FBX、blend、pak 和发行包；Original 手写的 `ue_build.json`（含绝对路径）。
- **署名：** SifuExport 建立在 FabianFG 的 CUE4Parse（NuGet 包）上，本包不含它的源码，见 [工具来源](../../references/TOOL_SOURCES.md)。
