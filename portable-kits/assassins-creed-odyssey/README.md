# 刺客信条：奥德赛（Assassin's Creed Odyssey）便携包

先读 [游戏知识](../../games/assassins-creed-odyssey/README.md) 和 [构建流水线](../../games/assassins-creed-odyssey/BUILD_PIPELINE.md)。forge、覆盖顺序、
安装器、卡珊德拉的数据 ID 与坐标系见 [技术合同](../../games/assassins-creed-odyssey/TECHNICAL_CONTRACTS.md)；物理骨架见
[物理](../../games/assassins-creed-odyssey/PHYSICS.md)；眼睑与下颌见 [表情](../../games/assassins-creed-odyssey/FACE.md)。

这是 Karin_Original 整体替换卡珊德拉（Kassandra）的 mod（v8，2026-10-23 用户实机接受）实际使用的工具：forge v28 索引 / 提取、
原地追加式安装器（每一份副本、逐字节卸载）、BuildTable / LODSelector 的 XML 编辑、payload 构建器、Reflex3 物理骨架生成器、
头部骨架姿势模拟、GLB 坐标系旋转，Blender 拟合 / 表情 / 导出 / 预览脚本，以及无界面驱动 AnvilToolkit 的 AcoHarness（C# 源码）。

- **游戏版本：** PC Ubisoft Connect 版（产品 5059）v1.5.6，`ACOdyssey.exe`；forge v28。其它版本 / 平台没有测过，数据文件的 ID、索引号和
  布局都可能变（`build-sensitive`）。
- **mod 安装：** 不解包 forge。`aco_install.py` 把每个替换数据文件追加到**所有**含该 ID 的 forge 末尾（根目录和 `dlc_<n>\`），改指 20 字节索引行
  和名字表的大小；卸载写回原行并截断。安装和卸载时游戏必须关闭。
- **AnvilToolkit：** 1.3.6（第三方，用户自备，不随包）。只通过 AcoHarness 无界面调用；它需要 AnvilToolkit 的 `Libs\`（含 Oodle）和
  `Odyssey.gfl`（Kamzik123/AnvilToolkit-Resources）。
- **.NET：** 编译 AcoHarness 用 .NET SDK（`dotnet` 在 PATH 上，Roslyn `csc.dll`）；运行用一个 .NET 9 运行时文件夹（项目用 9.0.18，
  含 `Microsoft.NETCore.App` 和 `Microsoft.WindowsDesktop.App`）。
- **Blender：** 5.0.1，后台模式。`pose_preview.py` 用 Workbench 渲染，需要 OpenGL 上下文（SSH 会话里会崩，见下文 §2）。
- **texconv：** DirectXTex 的 `texconv.exe`，用户自备。
- **Python：** 3.10 或更高（`aco_install.py` 单独在 3.8+ 上跑）；`aco_phys_skel.py`、`aco_pose_sim.py`、`glb_rotate.py`、`glb_info.py` 要 numpy
  （`requirements.txt`），`build_mod.py`、`build_atlas.py` 要根目录 `requirements.txt` 里的 Pillow；其余只用标准库。

## 环境变量

| 变量 | 用在 | 内容 |
| --- | --- | --- |
| `ACO_GAME_DIR` | `aco_install.py`、`aco_locate.py extract` | 游戏目录（含 `ACOdyssey.exe`、`DataPC*.forge`、`dlc_<n>\`）；或 `--game` |
| `ACO_CACHE` | `aco_locate.py` | 放 `main_index.tsv` / `dlc_index.tsv`（`aco_forge.py index` 的输出）的目录；或 `--cache` |
| `ACO_WORK` | `build_mod.py`、`aco_phys_skel.py`、`aco_pose_sim.py` | 工作目录，放原版数据文件的提取 / 解包 / XML（布局见 §0.3）；放在本仓库和同步盘之外 |
| `ACO_HARNESS` | `build_mod.py`、`acoharness/build.ps1`（输出到它所在的目录） | `AcoHarness.dll` 的路径 |
| `ACO_DOTNET` | `build_mod.py` | 运行 AcoHarness 的 `dotnet.exe`（.NET 9 运行时） |
| `ACO_TEXCONV` | `build_mod.py`、`build_atlas.py` | `texconv.exe`；`build_atlas.py` 也可用 `--texconv` |
| `ACO_SRC_TEX` | `build_mod.py` | 源模型贴图目录：`Karin_Face.png`、`Karin_Body.png`、`Karin_Hair.png`、`Karin_Costume.png` |
| `ACO_HEAD_SKELETON_XML` | `aco_pose_sim.py`、`blender/pose_preview.py`（`pose_preview.py` 给了 `--head-xml` 时不需要） | 卡珊德拉头部骨架的 XML；不设时按 `ACO_WORK` 的布局找，两个都没有就报错 |
| `ACO_ATK_DIR`、`ACO_DOTNET_ROOT`、`ACO_ATK_LISTS` | `acoharness/build.ps1` | 解压的 AnvilToolkit 1.3.6、.NET 9 运行时文件夹、放 `Odyssey.gfl` 的目录；或 `-AtkDir` / `-DotnetRoot` / `-ListsDir` |
| `ACO_GFL`、`ACO_ACSH_SCRIPTS` | `aco_gfl.py` | `Odyssey.gfl`；放 `acsh_forge.py` 的目录（刺客信条：影项目的脚本，**不在本包**） |
| `ACO_GAME` | AcoHarness（可选） | AnvilToolkit 的 `Game` 枚举名，默认 `Odyssey` |

缺少必需的变量时，脚本在写任何文件之前报错并说出变量名，不会退回到哪个本机路径。项目原脚本里写死的路径（游戏目录的默认值、
同步盘上的工程目录、影项目的工具目录）都改成了这些变量（[VALIDATION.md](../VALIDATION.md)）。

## 构建流程

下面的命令从仓库根运行（PowerShell 7）。**游戏和模型派生的产物不要写进仓库**：先定一个仓库之外的工作目录 `$W`，所有输出都写成它下面的
绝对路径（Blender 的相对输出路径按 Blender 的当前目录解析，见 [开发工具](../../games/assassins-creed-odyssey/DEV_TOOLING.md) §3）。

```powershell
$Kit = "portable-kits/assassins-creed-odyssey"
$W = "<仓库之外的工作目录>"            # 也不要放在同步盘里；可以和 ACO_WORK 同级
$H = { & $env:ACO_DOTNET $env:ACO_HARNESS @args }
```

AcoHarness 只把带斜杠或以 `.` 开头的参数当作路径（转成绝对路径），**不带斜杠的文件名按 harness 所在目录解析**；`$W\…` 这样的绝对路径没有问题。

### 0. 一次性准备

1. 编译 AcoHarness：

   ```powershell
   $env:ACO_ATK_DIR = "<解压的 AnvilToolkit 1.3.6>"; $env:ACO_DOTNET_ROOT = "<.NET 9 运行时文件夹>"
   $env:ACO_ATK_LISTS = "<放 Odyssey.gfl 的目录>"; $env:ACO_HARNESS = "<输出目录>\AcoHarness.dll"
   pwsh -NoProfile -File $Kit/acoharness/build.ps1     # 末行打印 AcoHarness.dll 的路径
   $env:ACO_DOTNET = "$env:ACO_DOTNET_ROOT\dotnet.exe"
   ```

2. 全部 forge 的索引（在有游戏的机器上；纯 Python）：

   ```powershell
   python -B $Kit/scripts/aco_forge.py index "$env:ACO_GAME_DIR\DataPC.forge" "$env:ACO_GAME_DIR\DataPC_patch_01.forge" ... > "$env:ACO_CACHE\main_index.tsv"
   python -B $Kit/scripts/aco_forge.py index <dlc_*\*.forge 和 DataPC_*_dlc_patch_01.forge> > "$env:ACO_CACHE\dlc_index.tsv"
   python -B $Kit/scripts/aco_locate.py find ACD_CHF_PLA_Kassandra_VisualMaster 00000104280E464B "/BodyKassandra_LOD[01]$/"
   ```

   `find` 列出持有它的每个 forge，按**脚本的启发式**排序并给第一行标 `*`：主 forge 的 patch、其它主 forge、DLC 的 patch、DLC（按 forge 名判断）。
   这不完全是游戏的覆盖顺序：实测主世界里是 `DataPC_patch_01` > `dlc_<n>\*.forge` > `DataPC_SharedGroup_00`
   （[技术合同](../../games/assassins-creed-odyssey/TECHNICAL_CONTRACTS.md) §3），而定位器把 `DataPC_SharedGroup_00` 排在 DLC 副本前面。
   所以一个 ID 没有 `DataPC_patch_01` 副本时，带 `*` 的那行可能不是生效的那份（`aco_locate.py extract` 取的就是这一行）。覆盖顺序要紧时，
   看完 `find` 的全部行，用 `aco_forge.py extract <forge> …` 明确指定 forge。

3. 提取并解包 `build_mod.py` / `aco_phys_skel.py` 用到的原版数据文件。`aco_forge.py extract <forge> <out> <IDHEX>…` 写 `<索引号>_-_<名字>.data`；
   `& $H unpack-export <outroot> <data…>` 写 `<outroot>\unpacked\<名字>\` 和 `<outroot>\xml\<名字>\`。脚本期望的布局（索引号是 v1.5.6 的 forge 行号，
   换版本后要按实际改 `build_mod.py` 顶部的常量）：

   | `ACO_WORK` 下的路径 | 来源 forge | 数据文件 | 用途 |
   | --- | --- | --- | --- |
   | `x1\SharedGroup_00\6365_-_…_BodyKassandra.data`、`6518_-_…_Kassandra_VisualMaster.data` + `x1\sg\` | `DataPC_SharedGroup_00` | `00000104280E464B`、`00000103E739C903` | 容器（LODSelector）、VisualMaster |
   | `x1\patch_01\19901_…_LOD0`、`19900_…_LOD1`、`19505_…_Kassandra_Head`、`19506_…_Kassandra_Hair` + `x1\p1\` | `DataPC_patch_01` | `00000104280E4653`、`0000018482B71630`、`0000016424DFAD4B`、`00000146D5F5EB4C` | 独立 LOD0 / LOD1、头部表、头发表 |
   | `x2\patch_01\19511_-_ACD_CHF_PLA_Hair_NEW.data` + `x2\p1\` | `DataPC_patch_01` | `00000194D13C465D` | 物理骨架模板（`--skeleton`） |
   | `x2\p1\xml\19895_-_ACD_CHR_Playable_BaseEntity_Female\10_-_ACD_Unisex_BaseSkeleton.Skeleton.xml` | `DataPC_patch_01` | `ACD_CHR_Playable_BaseEntity_Female` | 基础骨架（`aco_phys_skel.py`） |
   | `x2\sg\unpacked\6369_-_ACD_CHF_PLA_Kassandra_Head\` | `DataPC_SharedGroup_00` | 同名的头部数据文件（带贴图） | 内联 mip 的贴图模板（漫反射 sRGB、法线线性） |
   | `x5\sg\xml\9245_-_ACD_CHW_PLA_01_BowAlexios\` | `DataPC_SharedGroup_00` | `ACD_CHW_PLA_01_BowAlexios` | `ACD_Tex1` 材质与纹理组的 XML 模板 |
   | `x1\p1\xml\18988_-_ACD_CHF_PLA_Kassandra_Head\0_-_ACD_CHF_PLA_Kassandra_Head.Skeleton.xml` | `DataPC_patch_01` | 同名的头部数据文件（带头部骨架） | `aco_pose_sim.py` 的头部骨架与 328 个姿势 |

   同名数据文件不止一个（头部表、头部网格 / 骨架、贴图各是一个），用 `aco_locate.py find <名字>` 看索引号和大小来区分。

### 1. 拟合（Blender）

```powershell
New-Item -ItemType Directory -Force "$W\fit" | Out-Null
& $H export-glb "$W\fit\kassandra_fit_skeleton.glb" <ACD_Unisex_BaseSkeleton> <身体 LOD0 .Mesh> <头 LOD0 .Mesh> <Male_BaseAddon> <Male_AverageAddon> <Female_Bottom> <Female_Boobs> <Kassandra_Head .Skeleton>
python -B $Kit/scripts/glb_rotate.py "$W\fit\kassandra_fit_skeleton.glb" "$W\fit\kassandra_fit_naoeframe.glb" 90
blender -b --factory-startup --python $Kit/scripts/blender/fit_karin.py -- "$W\fit\kassandra_fit_naoeframe.glb" <源模型.blend> "$W\fit\fit.blend" `
    --scale auto --ground -0.008 --foot-scale 1.0 --foot-squash 0.8 --phys <链根,链根,…>
```

`export-glb` 的资源参数是 `ACO_WORK` 下解包出来的 `.Skeleton` / `.Mesh` 文件，同样写绝对路径。

产物 `fit.blend`（骨架对象名沿用 `NaoeRig`）和 `fit_fit.json`（`phys` 表：每根 `KP_*` 骨的父骨、长度、方向）。`--phys` 的链根表在项目里来自
影项目的一个文本文件，不随包。项目接着用影项目的 `skirt_follow.py --max 0.95 --sigma 0.2` 让裙子跟随大腿，写出下一步用的 `fit_skirt.blend`；
这个脚本也不随包（[物理](../../games/assassins-creed-odyssey/PHYSICS.md) §5），没有它时直接把 `fit.blend` 交给下一步。

### 2. 表情（Blender）

```powershell
blender -b "$W\fit\fit_skirt.blend" --python $Kit/scripts/blender/face_rig.py -- <源模型.blend> "$W\fit\fit_face.blend" `
    --blink-angle 25 --jaw-angle 6 --lid-bone-L 0xB1A846F5 --lid-bone-R 0x86260864 --report "$W\fit\face.json"
```

v8 的参数（`case-derived`）。报告里每侧 `blink_<侧>` 的 `pivot` 与 `c` 之差是杠杆长度，`explained` 是能解释的眨眼形状键比例。

离线看效果用 `pose_preview.py`：它要卡珊德拉头部骨架的 XML，**用 `--head-xml` 给出**，或者设 `ACO_HEAD_SKELETON_XML` / `ACO_WORK`（三者都没有时报错）。
它在 Workbench 里平涂贴图渲染，**需要 OpenGL 上下文**：从 SSH 会话直接跑会崩，要在交互桌面会话里运行。一次性的计划任务（`/IT`）可以做到，
但**它不继承当前会话的环境变量**，所以命令里的路径全部写绝对路径，并显式传 `--head-xml`：

```powershell
$KitAbs = (Resolve-Path $Kit).Path
$Head = "$env:ACO_WORK\x1\p1\xml\18988_-_ACD_CHF_PLA_Kassandra_Head\0_-_ACD_CHF_PLA_Kassandra_Head.Skeleton.xml"
'{"rest": {}, "blink050": {"poses": [[3972761639, 0.5], [381990212, 0.5]]}, "twist": {"poses": [[4063973011, 0.5]]}}' | Set-Content "$W\states.json"
"`"<blender.exe>`" -b `"$W\fit\fit_face.blend`" --python `"$KitAbs\scripts\blender\pose_preview.py`" -- `"$W\preview`" `"$W\states.json`" --res 700 --head-xml `"$Head`" > `"$W\preview.log`" 2>&1" |
    Set-Content -Encoding oem "$W\preview.cmd"
schtasks /Create /TN aco_preview /TR "`"$W\preview.cmd`"" /SC ONCE /ST 00:00 /IT /F
schtasks /Run /TN aco_preview       # $W\preview.log 里出现 PREVIEW_OK 后：schtasks /Delete /TN aco_preview /F
```

在交互桌面里直接跑时，同一条 `blender … pose_preview.py -- "$W\preview" "$W\states.json" --res 700 --head-xml $Head` 即可。上面是写法示例；
便携包核对时 Blender 脚本没有重跑（[VALIDATION.md](../VALIDATION.md)），项目里是按同样的思路用一次性计划任务跑的。

### 3. 导出与导入网格

```powershell
blender -b "$W\fit\fit_face.blend" --python $Kit/scripts/blender/export_karin_lods.py -- "$W\mesh" --ratios 1,0.5 --profile aco_tex1 --keep-full Body
python -B $Kit/scripts/glb_rotate.py "$W\mesh\karin_lod0.glb" "$W\mesh\karin_lod0_ody.glb" -90
python -B $Kit/scripts/glb_rotate.py "$W\mesh\karin_lod1.glb" "$W\mesh\karin_lod1_ody.glb" -90
& $H import-glb "$W\mesh\karin_lod0_ody.glb" 0 "$W\mesh\karin_lod0.Mesh" 00000104280E4653
& $H import-glb "$W\mesh\karin_lod1_ody.glb" 0 "$W\mesh\karin_lod1.Mesh" 0000018482B71630
python -B $Kit/scripts/glb_info.py "$W\mesh\karin_lod0_ody.glb" --joints     # 骨数要 ≤ 255
```

### 4. 物理骨架与 payload

```powershell
New-Item -ItemType Directory -Force "$W\phys" | Out-Null
python -B $Kit/scripts/aco_phys_skel.py "$W\phys\Hair_NEW_karin.Skeleton.xml" --binds "$W\mesh\karin_lod0_ody.glb" --fit "$W\fit\fit_fit.json" --report "$W\phys\report.json"
python -B $Kit/scripts/build_mod.py "$W\mesh" "$W\build" --skeleton "$W\phys\Hair_NEW_karin.Skeleton.xml"     # 末行 BUILD_OK
```

`aco_phys_skel.py` 打印骨数（基础骨 + KP 骨）和物理记录数；`--params <json>` 追加 `[正则, {字段}]` 行覆盖 `DEFAULT_PARAMS`（v6 的值）。
`build_mod.py` 先删掉再重建输出目录，写 `$W\build\payload\`：7 个 `<IDHEX>_<名字>.data` 和 `skip.tsv`；`--tex-size`（默认 2048）、`--gloss`（默认 70）。

### 5. 安装 / 卸载（游戏关闭时）

```powershell
python -B $Kit/scripts/aco_install.py status                 # 有状态文件时先 uninstall
python -B $Kit/scripts/aco_install.py install "$W\build\payload"
python -B $Kit/scripts/aco_install.py uninstall
```

`install` 逐个 ID 打印它写进了哪些 forge；状态写在 `<游戏目录>\.karin_aco_state.json`，已有状态时拒绝安装。**更新或校验游戏文件前先卸载。**

### 6. 发行

可重新部署的包结构（`payload\`、`aco_install.py`、`_env.cmd` / `install.cmd` / `uninstall.cmd` / `status.cmd`、README、`BUILD_INFO.json`、
`MANIFEST.sha256`）和它的实测重新部署见 [验证与发布](../../games/assassins-creed-odyssey/VALIDATION_AND_RELEASE.md) §3。`.cmd` 包装脚本不在本包里
（仓库不收 `.cmd`），那一节写了它们的做法。

## 脚本

| 脚本 | 用法 | 说明 |
| --- | --- | --- |
| `scripts/aco_forge.py` | `index <forge>…`（TSV 到 stdout）、`extract <forge> <out> <IDHEX>…` | forge v28 读取；纯标准库，测试机上也能跑 |
| `scripts/aco_locate.py` | `[--cache] [--game] find <名字\|IDHEX\|/正则/>…`、`extract <out> <名字\|IDHEX>…` | 按索引找数据文件的全部副本；`*` 行和 `extract` 用脚本的启发式（patch > 其它主 forge > DLC），没有 patch_01 副本时可能与实测的覆盖顺序不符（§0 第 2 步） |
| `scripts/aco_install.py` | `install <payload>`、`uninstall`、`status`，`[--game]` | 原地追加安装器；`payload\skip.tsv`（`IDHEX<TAB>forge`）里的副本保持原版；`payload\root\*` 覆盖游戏根目录文件（先备份、按哈希还原） |
| `scripts/bt_tool.py` | `show <xml>`、`edit <in> <out> [--drop 列,…] [--set 列=ID[:路径]]… [--clear-dynres]`、`lodsel <in> <out> --lod I=ID[:路径]…` | BuildTable / LODSelector 的 schema XML 编辑 |
| `scripts/build_mod.py` | `<mesh_dir> <out_dir> [--tex-size] [--gloss] [--skeleton <xml>]` | 构建 payload；数据 ID、列号、材质 ID 是卡珊德拉 / Karin 的案例值 |
| `scripts/aco_phys_skel.py` | `<out.xml> --binds <glb\|mesh-bones 输出> --fit <fit json> [--params] [--report] [--template] [--base]` | 重建 `ACD_CHF_PLA_Hair_NEW`：Reference 起的父链 + KP 骨 + Reflex3 type 21 物理记录 |
| `scripts/aco_pose_sim.py` | 模块（numpy） | 把头部骨架的姿势组（绝对局部变换）作用到带蒙皮的 GLB 上（线性混合蒙皮，用 GLB 自己的绑定） |
| `scripts/glb_rotate.py` | `<in.glb> <out.glb> <度>` | 绕原始竖轴整体旋转（位置、法线、切线、IBM、根节点）；+90 / −90 往返精确 |
| `scripts/glb_info.py` | `<glb> [--joints]` | 网格、图元、材质、蒙皮关节与世界位置 |
| `scripts/aco_gfl.py` | `<out.tsv> [--gfl] [--acsh-scripts]` | 把 `Odyssey.gfl` 转成 TSV（id、类哈希、forge、数据文件、名字）；需要影项目的 `acsh_forge.read_gfl`（不在本包） |
| `scripts/build_atlas.py` | `<src_tex> <out> [--size 4096] [--texconv]` | 2×2 图集 + BC7 DDS（**被放弃的**皮肤材质路线，见技术合同 §8） |
| `scripts/blender/fit_karin.py` | `blender -b --factory-startup --python … -- <骨架 glb> <源 blend> <out.blend> […]` | 刚性躯干 + 四肢对关节的拟合，`--phys` 生成 +X 沿链的 KP 骨 |
| `scripts/blender/face_rig.py` | `blender -b <fit.blend> --python … -- <源 blend> <out.blend> […]` | 下颌、眼睑、虹膜的绑定偏移（杠杆）蒙皮 |
| `scripts/blender/export_karin_lods.py` | `blender -b <blend> --python … -- <out> --ratios … --profile aco_tex1 --keep-full Body` | 改材质名为目标 Material ID、合并、三角化、白顶点色、≤ 4 权重、裁骨、减面 LOD |
| `scripts/blender/pose_preview.py` | `blender -b <blend> --python … -- <out> <states.json> [--res] [--dist] [--head-xml <xml>]` | 头部姿势下的脸部渲染（Workbench，需 OpenGL）；头部骨架 XML 用 `--head-xml`，或 `ACO_HEAD_SKELETON_XML` / `ACO_WORK` |
| `scripts/blender/aco_pack_atlas.py` | `blender -b <blend> --python … -- <out.blend> <材质名> [--drop Karin_Alpha]` | 把 UV 收进 2×2 图集（被放弃的路线） |
| `acoharness/Program.cs`、`build.ps1` | 见下表 | AcoHarness 源码与构建脚本 |

### AcoHarness 命令

| 命令 | 作用 |
| --- | --- |
| `unpack-data <file.data> <outdir>`、`unpack-export <outroot> <data…>` | 解包数据文件；`unpack-export` 还导出 XML（跳过 Mesh / TextureMap 等二进制资源） |
| `export-xml <资源> <out.xml>…`、`export-xml-dir <dir> <outdir> [glob]`、`compile-xml <in.xml> <out>` | schema XML 往返；`compile-xml` 在被覆盖的文件旁留 `.bak` |
| `pack-data <目录> <原 .data\|-> <out.data>` | 打回数据文件（沿用原文件的元数据） |
| `export-glb <out.glb> <Mesh / Skeleton…>` | 导出 GLB（第一个骨架为主） |
| `import-glb <in.glb> <网格选择> <out.Mesh> <IDHEX> [--joints N] [--no-autoscale] [--offset x,y,z]` | 奥德赛分支：顶点格式 v4、白色 Color0、缺副法线时取 N×T、> 255 骨拒绝 |
| `mesh-info`、`mesh-bones`、`mesh-binds`、`reserialize`、`debug-mesh`、`debug-data` | 网格和骨的检查 |
| `tex-info`、`tex-export`、`tex-import <模板> <dds> <out> [--id HEX] [--maptype N]` | 贴图；只用内联 mip 的贴图（顶层 mip 会弹 GUI 文件对话框） |
| `prefetch-dump`、`prefetch-show`、`prefetch-find`、`prefetch-add`、`prefetch-edit`、`make-patch-meta` | prefetch 文件（v2 起不再需要改） |
| `scan-refs <forge> <list.tsv> <IDHEX,…> [classId]` | 在数据文件里找引用某 ID 的对象 |
| `reflex-xml`、`reflex-compile`、`pack-forge` | 继承自影项目的 harness；AnvilToolkit 的 Reflex3 读取器只认 Mirage 的格式，奥德赛的物理 blob 由 `aco_phys_skel.py` 直接写 |

环境变量：`ACO_GAME`（默认 `Odyssey`）、`ATK_DIR`（Oodle 所在的 `Libs` 的上级，默认 harness 目录）、`ATK_RUNTIME`（工作目录，`Lists\` 从这里读，
默认 harness 目录）、`ACSH_DEBUG=1`（打印第一次机会异常）；`--rawdir <dir>` 设置顶层 mip 的查找目录。

## 换一个模型时

- `build_mod.py` 的数据 ID、表的列号、索引号、`PARTS` 贴图名，`export_karin_lods.py` 的 `aco_tex1` 材质映射，`face_rig.py` 的眼睑骨 / 角度，
  `aco_phys_skel.py` 的 `DEFAULT_PARAMS`（按 `KP_*` 名字匹配）都是 Karin_Original 对卡珊德拉的案例值；换模型或换角色要重新测量。
- forge 读取、索引搜索、安装器、`bt_tool.py`、`glb_rotate.py`、Reflex3 记录写出、姿势模拟与模型无关。

## 边界

便携副本只在合成数据上做了离线核对（2026-10-23）：改动过的命令行脚本与项目原脚本输出逐字节相同（[VALIDATION.md](../VALIDATION.md)）。
`build_mod.py`、Blender 脚本和 AcoHarness 没有用本包重跑；实机结论来自项目用原脚本构建的 v1–v8。不带游戏资源、源模型、AnvilToolkit、
.NET、texconv、`Odyssey.gfl`、影项目的脚本或构建产物。
