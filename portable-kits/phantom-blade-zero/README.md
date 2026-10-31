# 影之刃零（Phantom Blade Zero）便携包

先读 [游戏知识](../../games/phantom-blade-zero/README.md) 和 [构建流水线](../../games/phantom-blade-zero/BUILD_PIPELINE.md)。容器、骨架、领导者网格与武器骨的约定见
[技术合同](../../games/phantom-blade-zero/TECHNICAL_CONTRACTS.md)；布料见 [物理](../../games/phantom-blade-zero/PHYSICS.md)；表情和眨眼见 [面部](../../games/phantom-blade-zero/FACE.md)；
PbzExport、objscan、usmap 和插件见 [开发工具](../../games/phantom-blade-zero/DEV_TOOLING.md)。

这是 Karin_Original（v3）和 Karin_PicodraTech（v1）替换主角「魂」实际使用的工具：两个 Blender 构建器、UE 5.7 编辑器 Python（原版和 PicodraTech 分支）、
编辑器插件 PBZModTools 的 C++ 源码、内容工程模板、C# 写的 PbzExport（CUE4Parse 命令行）和 objscan（GUObjectArray 扫描器）、usmap 修正脚本、
PowerShell 流水线和发行包的安装脚本。

- **游戏版本：** Steam App 4115450，buildid `26266538`，引擎 `5.7.4-301524+42ecbfa37f78`。资源是 IoStore（`ProjectPBZ-Windows` + `_s1` … `_s65`，索引加密，Oodle）。
  mod 是 `ProjectPBZ\Content\Paks\~mods\z_<名>_P.{utoc,ucas,pak}`，不需要 `.sig`。
- **AES 密钥、usmap、Oodle DLL：** 本包都不含。密钥从环境变量 `PBZX_AES` 读（`pbzx_run.ps1` 也会读 `<工作根>\tools\aes.txt`）；usmap 按 [开发工具](../../games/phantom-blade-zero/DEV_TOOLING.md) §2
  自己导出再用 `usmap_fix.py` 修正；Oodle DLL（`oo2core_9_win64.dll`）用户自备。读自己的 mod 容器不需要密钥。
- **PbzExport / objscan：** 源码在 `pbzexport/`、`objscan/`，面向 net10.0（win-x64），要用 .NET 10 SDK 编译；PbzExport 的 NuGet 依赖是 CUE4Parse 和 CUE4Parse-Conversion
  `1.2.2.202610`。请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包。
- **UE：** 5.7（Epic 启动器版）。编插件要 Visual Studio C++ 生成工具（项目用 VS 2022 BuildTools、MSVC 14.44）。
- **Blender：** 构建器在 Blender 4.2 内运行（`--background --factory-startup`），需要 UEFormat 插件（`io_scene_ueformat`，读 `.uemodel`）和自带的 glTF / FBX 插件。
- **Python：** `usmap_fix.py` 要 Python 3.10+，压缩的输入另需 `zstandard`（`requirements.txt`）。UE 脚本在 UE 自带的 Python 里运行。
- **只在 Windows 上：** UE、UnrealPak、PbzExport、objscan 和 PowerShell 工具。PowerShell 脚本按 PowerShell 7（`pwsh`）写；`release/install.ps1` 也支持 Windows PowerShell 5.1。

## 环境变量

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `PBZ_WORK` | `scripts/blender/build_pbz.py`、`build_pt.py` | 原版 dump 目录：`ue/Hun_Invs.uemodel`、`ue/Hun_Young_Skeleton.uemodel`、`ue/Hun_Hat_Skeleton.uemodel`；`c/Hun_Skin_Skeleton.Hun_Skin_Skeleton.skel.json`、`c/Hun_Body_Simple.Hun_Body_Simple.skel.json`；`g/Hun_Invs.Hun_Invs.skel.json`；`y/Hun_Young_Skeleton…`、`y/Hun_Young_Body…`。没设时报错退出，什么都不写 |
| `PBZ_SOURCE_VRM` | `build_pbz.py` | Karin_Original 的 VRM |
| `PBZ_SOURCE_BLEND` | `build_pt.py` | `Karin_PT_Unified_Atlas.blend`（旁边要有 `textures/`） |
| `PBZ_BLENDER_ADDONS` | 两个构建器 | 可选：UEFormat 没装进 Blender 时，含 `io_scene_ueformat` 的目录 |
| `PBZ_ROOT` | `tools/*.ps1` | UE 侧的工作根：`UE\ProjectPBZ`、`logs\`、`out\`、`out_test\`、`tools\`（`PbzExport\PbzExport.exe`、`Mappings.usmap`、`oo2core_9_win64.dll`、`aes.txt`）、`extract\`。也可用 `-Root`（`pbzx_run.ps1` 用 `-WorkRoot` / `PBZ_WORK_ROOT`） |
| `UE_ROOT` | `ue_run.ps1`、`cook.ps1`、`build_plugin.ps1`、`run_all.ps1`、`mkcontainer.ps1`、`mktest.ps1` | UE 5.7 安装目录（含 `Engine\`），或 `-UE` |
| `PBZ_GAME_DIR` | `pbzx_run.ps1`、`mktest.ps1` | 含 `ProjectPBZ` 的游戏目录，或 `-GameDir` |
| `PBZX_AES`、`PBZX_GAME`、`PBZX_EXTRA`、`PBZX_SCRIPT` | PbzExport | 密钥；引擎版本（默认 `GAME_UE5_7`）；先读的额外 pak 目录（读回 mod 用）；`1` 时把蓝图字节码读进 json |

## 构建流程

### 0. 一次性准备（构建机）

```powershell
$Kit = "portable-kits/phantom-blade-zero"; $T = "$Kit/tools"
$env:PBZ_ROOT = "<工作根>"; $env:UE_ROOT = "<UE_5.7 安装目录>"; $env:PBZ_GAME_DIR = "<Steam 库>\steamapps\common\PBZ"
$R = $env:PBZ_ROOT
# a) PbzExport / objscan：复制到仓库外编译
Copy-Item -Recurse $Kit/pbzexport "$R/src/PbzExport"; dotnet publish "$R/src/PbzExport/PbzExport.csproj" -c Release -o "$R/tools/PbzExport"
Copy-Item -Recurse $Kit/objscan "$R/src/objscan";     dotnet publish "$R/src/objscan/objscan.csproj" -c Release -o "$R/tools/objscan"
# b) usmap：游戏运行时用 objscan 找 GUObjectArray，打补丁的 Dumper-7 导出，再修正
python $Kit/scripts/usmap_fix.py "<Dumper-7 导出的 usmap>" "$R/tools/Mappings.usmap"
# c) 内容工程和插件
Copy-Item -Recurse $Kit/ue/ProjectPBZ "$R/UE/ProjectPBZ"
Copy-Item -Recurse $Kit/ue/PBZModTools "$R/UE/ProjectPBZ/Plugins/PBZModTools"
pwsh -NoProfile -File $T/build_plugin.ps1        # 日志 logs\ubt.txt，最后一行 UBTEXIT 0
```

### 1. 原版 dump

```powershell
$H = "ProjectPBZ/Plugins/HuaShira/Content/Characters/Hero"
pwsh -NoProfile -File $T/pbzx_run.ps1 c skel "$H/Hero_Hun/Hun_Skin_Skeleton" "$H/Hero_Hun/SkinParts/Hun_Body_Simple" "$H/Hero_Hun/SkinParts/Hun_Head_New"
pwsh -NoProfile -File $T/pbzx_run.ps1 g skel "$H/Hero_Hun/Hun_Invs"
pwsh -NoProfile -File $T/pbzx_run.ps1 y list "/Hun_Young_Skeleton\.uasset$"      # 少年魂骨架的包路径
$YS = "<上一行列出的包路径，去掉 .uasset>"
pwsh -NoProfile -File $T/pbzx_run.ps1 ue export uemodel "$H/Hero_Hun/Hun_Invs" "$H/Hero_Hun/Hats/Hun_Hat_Skeleton" $YS
pwsh -NoProfile -File $T/pbzx_run.ps1 y skel $YS "$H/Young_Hun/SkinParts/Hun_Young_Body"
```

输出在 `<工作根>\extract\<子目录>\` 下，保持包路径。把需要的文件按上表的布局整理到 `PBZ_WORK`（文件名就是 `<包名>.<包名>.skel.json` 和 `<包名>.uemodel`）。

### 2. Blender 构建

```powershell
$env:PBZ_WORK = "<原版 dump 目录>"; $env:PBZ_SOURCE_VRM = "<Karin(Clone).vrm>"
blender --background --factory-startup --python $Kit/scripts/blender/build_pbz.py -- "<run>" --scale 1.30 --variant adult
blender --background --factory-startup --python $Kit/scripts/blender/build_pbz.py -- "<run>" --scale 1.32 --variant young
# PicodraTech：
$env:PBZ_SOURCE_BLEND = "<Karin_PT_Unified_Atlas.blend>"
blender --background --factory-startup --python $Kit/scripts/blender/build_pt.py -- "<run>" --variant adult      # 默认 --scale 1.37
blender --background --factory-startup --python $Kit/scripts/blender/build_pt.py -- "<run>" --variant young
blender --background "<run>/build.blend" --python $Kit/scripts/blender/render_pt.py -- "<run>" "<输出前缀>"   # 可选：贴图与分段配色预览（少年版加参数 _Young）
```

日志最后一行 `BUILD_OK <run>`。核对 `report.json`：`missing_face_keys` 与 `slots_unmapped` 为空，`bones.body` = 264，`body_bones_added` 是四根 `*_child` 骨。

### 3. UE 全流程

```powershell
pwsh -NoProfile -File $T/run_all.ps1 -Run "<run>"                                   # Karin_Original → <工作根>\out\z_KarinPBZ_P.*
pwsh -NoProfile -File $T/run_all.ps1 -Run "<pt run>" -Mod pt -Root "<PicodraTech 的工作根>"  # → z_KarinPT_P.*
```

构建目录（`-Run`）的路径里不要有空格：UE 的 `-script="脚本 参数"` 按空格切参数（项目的 `.cmd` 也一样）。进度在 `logs\run_all.txt`（`ok <步>` / `FAIL <步>` / `DONE`），每一步的输出在 `logs\<步>.out.txt`。单独跑一步：`ue_run.ps1 <脚本> <日志名> [参数]`；单独打容器：
`mkcontainer.ps1 [-Mod pt] [-Exclude 'NameA+NameB']`（排除某些资产做二分）；只装几个包做测试：`mktest.ps1 -Pkgs "Characters\Hero\Hero_Hun\SkinParts\Hun_Body_Simple+Mods\KarinPBZ\*"`
（装成 `z_PBZTest_P`，会删掉 `~mods` 里的测试包和两套 Karin 包，别的 mod 不动；游戏运行时拒绝）。过场的 groom 占位只要做一次：`ue_run.ps1 scripts/ue/ue_grooms.py grooms`。

### 4. 读回与安装

```powershell
$env:PBZX_EXTRA = "$R\out"
pwsh -NoProfile -File $T/pbzx_run.ps1 rb skel "$H/Hero_Hun/SkinParts/Hun_Body_Simple" "$H/Hero_Hun_Climax/SkinParts/Hun_Body_Climax"
pwsh -NoProfile -File $T/pbzx_run.ps1 rb morphs "$H/Hero_Hun/SkinParts/Hun_Head_New"
```

发行包：按 [验证与发布](../../games/phantom-blade-zero/VALIDATION_AND_RELEASE.md) §3 的布局放 `release/install.ps1`、两个一行的 `.cmd`、README 和 `files\`（三个文件 + `SHA256SUMS.txt`）。
`install.ps1` 里的包名、buildid 是常量，换包时改 `$Names`、`$OtherNames`、`$BuildId`。

## 文件

| 文件 | 内容 |
| --- | --- |
| `scripts/blender/build_pbz.py` | Karin_Original 构建器（VRM → 领导者 / 身体 / 头 / 睫毛片 / 隐藏件 FBX、布料分段与 `cloth*.json`、面部形变、贴图、报告） |
| `scripts/blender/build_pt.py` | PicodraTech 分支（blend 源模型、骨名映射、七段布料、合成尾巴贴图、`materials*.json`） |
| `scripts/blender/render_pt.py` | `build.blend` 的贴图预览和分段配色预览 |
| `scripts/ue/*.py` | UE 5.7 步骤：`ue_import_pbz`、`ue_import_young`、`ue_fixmats`、`ue_brightness`、`ue_cloth`、`ue_blink`、`ue_morphdump`、`ue_grooms` |
| `scripts/ue/pt/*.py` | PicodraTech 分支：导入、少年导入（加了资产注册表扫描和旧槽断言）、材质、亮度、布料（任何一段失败就失败），都读 `materials.json` |
| `scripts/usmap_fix.py` | 去掉 Dumper-7 usmap 里的继承属性 |
| `tools/run_all.ps1`、`ue_run.ps1`、`cook.ps1`、`build_plugin.ps1` | 项目 `.cmd` 的 PowerShell 版 |
| `tools/mkcontainer.ps1`、`mktest.ps1`、`pbzx_run.ps1` | 容器、测试容器、PbzExport 包装 |
| `release/install.ps1` | 发行包的安装 / 卸载 / 检查 |
| `pbzexport/`、`objscan/` | C# 源码 |
| `ue/PBZModTools/`、`ue/ProjectPBZ/` | 编辑器插件源码、内容工程模板（含空插件 `HuaShira`） |

已知问题（保留原样）：`scripts/ue/ue_import_young.py`（Karin_Original 版）没有等资产注册表扫完，旧身体存在时可能把新导入并进旧网格；PicodraTech 分支已修，
重做 Karin_Original 的少年导入时可以直接用 `scripts/ue/pt/ue_import_young.py` 的写法。
