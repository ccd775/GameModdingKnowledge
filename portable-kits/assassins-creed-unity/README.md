# 刺客信条：大革命（Assassin's Creed Unity）便携包

先读 [游戏知识](../../games/assassins-creed-unity/README.md) 和 [构建流水线](../../games/assassins-creed-unity/BUILD_PIPELINE.md)。forge、内嵌副本、
安装器、亚诺的数据 ID 与坐标系见 [技术合同](../../games/assassins-creed-unity/TECHNICAL_CONTRACTS.md)；附加骨架与碰撞见
[物理](../../games/assassins-creed-unity/PHYSICS.md)；发行包见 [验证与发布](../../games/assassins-creed-unity/VALIDATION_AND_RELEASE.md)。

这是 Karin_Original 整体替换亚诺（Arno）的 mod（v7，2026-10-24 用户实机接受）实际使用的工具：forge v27 索引 / 提取、内嵌副本扫描、
原地追加式安装器（按 forge 的版本、原版大小核对、xz payload、Steam 库自动定位）、BuildTable 的 XML 编辑、payload 构建器、附加骨架（BallJoint + 裙片碰撞）生成器、
发行包打包器、头部骨识别、GLB 坐标系旋转，Blender 的源模型规范化 / 拟合 / 表情 / 导出 / 对比渲染脚本，以及无界面驱动 AnvilToolkit 的 AcuHarness（C# 源码）。

- **游戏版本：** PC Steam 版（289650）build 21970519，游戏内 1.5.1，`ACU.exe`；forge v27。其它版本 / 平台（Ubisoft Connect 独立版）没有测过，
  数据文件的 ID、内嵌副本的分布和表的列号都可能变（`build-sensitive`）。
- **mod 安装：** 不解包 forge。`acu_install.py` 把每个替换数据文件追加到**所有**含该 ID 的 forge 末尾（根目录和 `dlc_<n>\`），改指 20 字节索引行和名字表的大小；
  卸载写回原行并截断。安装和卸载时游戏必须关闭。
- **AnvilToolkit：** 1.3.6（第三方，用户自备，不随包）。只通过 AcuHarness 无界面调用；它需要 AnvilToolkit 的 `Libs\`（含 Oodle）和
  `Unity.gfl`（Kamzik123/AnvilToolkit-Resources）。
- **.NET：** 编译 AcuHarness 用 .NET SDK（`dotnet` 在 PATH 上，Roslyn `csc.dll`）；运行用一个 .NET 9 运行时文件夹（项目用 9.0.18，
  含 `Microsoft.NETCore.App` 和 `Microsoft.WindowsDesktop.App`）。
- **Blender：** 5.0.1，后台模式。
- **texconv：** DirectXTex 的 `texconv.exe`，用户自备。
- **Python：** 3.10 或更高（`acu_install.py` 单独在 3.8+ 上跑，发行包就是这样用的）；`acu_phys_skel.py`、`head_bones.py`、`glb_rotate.py`、`glb_info.py` 要 numpy
  （`requirements.txt`），`build_mod.py` 要根目录 `requirements.txt` 里的 Pillow；其余只用标准库。

## 环境变量

| 变量 | 用在 | 内容 |
| --- | --- | --- |
| `ACU_GAME_DIR` | `acu_install.py`、`build_mod.py`、`scan_objs.py`、`make_release.py`（都可用 `--game`，`make_release.py` 除外） | 游戏目录（含 `ACU.exe`、`*.forge`、`dlc_<n>\`）；不设时从 Steam 库（注册表 `SteamPath` + `libraryfolders.vdf`）找 |
| `ACU_CACHE` | `build_mod.py`、`scan_objs.py` | 放 `index.tsv`（`acu_forge.py index` 的输出）和 `arno_tables.tsv`（`objs_to_tsv.py` 的输出）的目录 |
| `ACU_SCRATCH` | `build_mod.py`（可选） | 原版副本缓存和作业临时目录，默认 `%TEMP%\acu_work`；放在本仓库和同步盘之外 |
| `ACU_HARNESS` | `build_mod.py`、`scan_objs.py`、`acuharness/build.ps1`（输出到它所在的目录） | `AcuHarness.dll` 的路径 |
| `ACU_DOTNET` | `build_mod.py`、`scan_objs.py` | 运行 AcuHarness 的 `dotnet.exe`（.NET 9 运行时） |
| `ACU_TEXCONV` | `build_mod.py` | `texconv.exe` |
| `ACU_SRC_TEX` | `build_mod.py` | 源模型贴图目录：`Karin_Face.png`、`Karin_Body.png`、`Karin_Hair.png`、`Karin_Costume.png`（`prep_karin_original.py` 写出） |
| `ACU_TEMPLATES` | `build_mod.py` | 材质 / 贴图模板目录（布局见 §0 第 4 步） |
| `ACU_ATK_DIR`、`ACU_DOTNET_ROOT`、`ACU_ATK_LISTS` | `acuharness/build.ps1` | 解压的 AnvilToolkit 1.3.6、.NET 9 运行时文件夹、放 `Unity.gfl` 的目录；或 `-AtkDir` / `-DotnetRoot` / `-ListsDir` |
| `ACU_GAME` | AcuHarness（可选） | AnvilToolkit 的 `Game` 枚举名，默认 `Unity` |

缺少必需的变量时，脚本在写任何文件之前报错并说出变量名，不会退回到哪个本机路径。项目原脚本里写死的路径（游戏目录的默认值、同步盘上的工程目录、
共享的工具目录）都改成了这些变量（[VALIDATION.md](../VALIDATION.md)）。

## 构建流程

下面的命令从仓库根运行（PowerShell 7）。**游戏和模型派生的产物不要写进仓库**：先定一个仓库之外的工作目录 `$W`，所有输出都写成它下面的绝对路径
（Blender 的相对输出路径按 Blender 的当前目录解析）。

```powershell
$Kit = "portable-kits/assassins-creed-unity"
$W = "<仓库之外的工作目录>"            # 也不要放在同步盘里
$H = { & $env:ACU_DOTNET $env:ACU_HARNESS @args }
```

AcuHarness 只把带斜杠或以 `.` 开头的参数当作路径（转成绝对路径），不带斜杠的文件名按 harness 所在目录解析；`$W\…` 这样的绝对路径没有问题。

### 0. 一次性准备

1. 编译 AcuHarness：

   ```powershell
   $env:ACU_ATK_DIR = "<解压的 AnvilToolkit 1.3.6>"; $env:ACU_DOTNET_ROOT = "<.NET 9 运行时文件夹>"
   $env:ACU_ATK_LISTS = "<放 Unity.gfl 的目录>"; $env:ACU_HARNESS = "<输出目录>\AcuHarness.dll"
   pwsh -NoProfile -File $Kit/acuharness/build.ps1     # 末行打印 AcuHarness.dll 的路径
   $env:ACU_DOTNET = "$env:ACU_DOTNET_ROOT\dotnet.exe"
   ```

2. 全部 forge 的索引（纯 Python，几秒钟）：

   ```powershell
   $F = (Get-ChildItem "$env:ACU_GAME_DIR\*.forge", "$env:ACU_GAME_DIR\dlc_*\*.forge").FullName   # PowerShell 不替原生程序展开通配符
   python -B $Kit/scripts/acu_forge.py index @F > "$env:ACU_CACHE\index.tsv"
   ```

   v1.5.1：63 个 forge、180 245 行。PowerShell 7.4 起 `>` 原样写原生程序输出的字节；更早的版本会按控制台编码转码并写 CRLF，
   数据文件名都是 ASCII，读 TSV 的脚本按文本模式读（CRLF 自动归一），不受影响。

3. 内嵌副本清单（要 harness）：

   ```powershell
   $Ids = "145368098E,2DFA9960D6,145368099F,14536809A0,14536809A1,14536809A2,14536809A3,1EB36B1C7C,26A4C11760,10ED459755,1453680995"
   python -B $Kit/scripts/scan_objs.py "$W\objs.log" $Ids .forge
   python -B $Kit/scripts/objs_to_tsv.py "$env:ACU_CACHE\arno_tables.tsv" "$W\objs.log"
   ```

   ID 是 `build_mod.py` 的 `TABLE_DROPS` 和 `SKEL_TABLE`。forge 参数按「等于或包含」匹配索引的 forge 列，`.forge` 就是全部 63 个；也可以分几次扫
   （项目分成基础游戏和 `dlc_` 两个日志，`objs_to_tsv.py` 接受多个日志）。v1.5.1 的命中全在 21 个非 `_assets` / `_gi` 的 forge 里：189 个数据文件、669 个对象。

4. 模板（`ACU_TEMPLATES`，文件名要和 `build_mod.py` 里的一致）。`acu_forge.py extract <forge> <out> <IDHEX>…` 写 `<行号>_-_<名字>.data`；
   `& $H unpack-data <data> <dir>` 解包，`& $H export-xml <资源> <out.xml>` 导出 XML：

   | 模板文件 | 来源（v1.5.1 的 forge 行号） |
   | --- | --- |
   | `10001_-_1Handed_Sp2.Material.xml`、`12392_-_CN_W_1Handed_Sp2_Set.TextureSet.xml` | `DataPC.forge` 的 `Game Bootstrap Settings`（`0000000000000800`）里的对象 10001 / 12392，导出 XML |
   | `0_-_CN_U_FR_Arno_Head_LOD0_DiffuseMap.TextureMap`、`0_-_CN_U_FR_Arno_Head_LOD0_NormalMap.TextureMap` | `DataPC_SharedGroup_00.forge` 的 `000000126C7EB55D` / `000000126C7EB561`，解包后的对象 0（内联 mip，漫反射 sRGB / 法线线性） |
   | `0_-_CN_W_ULC_Arno_Sword1_0_SpecularMap.TextureMap` | `DataPC.forge` 的 `00000016E3F5EF5B`，解包后的对象 0 |

   物理骨架的模板 `ACU_U_Arno_Hair.Skeleton.xml` 和拟合用的骨架在 `CN_P_Arno`（`DataPC_ACU_Paris.forge` 的 `000000070CF6709B`）里：`& $H unpack-export <outroot> <CN_P_Arno.data>`
   写 `<outroot>\unpacked\<名字>\` 和 `<outroot>\xml\<名字>\`（头发骨架是第 184 个对象、头部骨架 `CN_U_Arno_Head_Rig` 第 66 个，同名对象按大小区分）。

### 1. 源模型（Blender）

```powershell
blender -b --factory-startup --python $Kit/scripts/blender/prep_karin_original.py -- "<Karin(Clone)_BlenderSafe.fbx>" "$W\src\karin_original_src.blend" "$W\src\src_tex"
$env:ACU_SRC_TEX = "$W\src\src_tex"
```

### 2. 拟合（Blender）

```powershell
& $H export-glb "$W\fit\arno_fit_skeleton.glb" <ACU_BaseSkeleton_Male> <亚诺头部 LOD0 .Mesh> <Upperbody_Arnaud_V2 LOD0> <Pants_Arnaud_V2 LOD0> `
    <ACU_Unisex_ArmsSimple> <ACU_Arnaud_Armpits> <ACU_Unisex_LegsRollbones> <ACU_Avatar_ForeArmTwist> <ACU_Male_ArmsFlat_Upper> `
    <ACU_Unisex_Dress_Simple_HV_Col> <CN_U_Arno_Head_Rig>
python -B $Kit/scripts/glb_rotate.py "$W\fit\arno_fit_skeleton.glb" "$W\fit\arno_fit_naoeframe.glb" 90
blender -b --factory-startup --python $Kit/scripts/blender/fit_karin.py -- "$W\fit\arno_fit_naoeframe.glb" "$W\src\karin_original_src.blend" "$W\fit\fit.blend" `
    --scale auto --ground -0.004 --foot-scale 1.0 --foot-squash 0.8 --phys <链根,链根,…>
blender -b "$W\fit\fit.blend" --python $Kit/scripts/blender/render_compare.py -- "$W\review\fit"
```

`export-glb` 的资源参数都是解包出来的 `.Skeleton` / `.Mesh`（基础骨架和 `ArmsSimple` 在 `Game Bootstrap Settings` 里，上衣 / 裤子是巴黎 forge 里的同名数据文件，
其余附加骨架在 `CN_P_Arno` 里），写绝对路径。`--phys` 的 35 个链根见 [构建流水线](../../games/assassins-creed-unity/BUILD_PIPELINE.md) §3。

### 3. 表情（Blender）

```powershell
blender -b "$W\fit\fit.blend" --python $Kit/scripts/blender/face_rig.py -- "$W\src\karin_original_src.blend" "$W\fit\fit_face.blend" --report "$W\fit\face.json"
```

头部骨的映射在 `face_rig.py` 的 `GAME_BONES`；换版本时先用 `head_bones.py <亚诺头部 GLB> <网格名>` 从原版权重核对（[表情](../../games/assassins-creed-unity/FACE.md)）。

### 4. 导出与导入网格

```powershell
blender -b "$W\fit\fit_face.blend" --python $Kit/scripts/blender/export_karin_lods.py -- "$W\mesh" --ratios 1,0.5,0.25,0.12 --profile acu_weapon --keep-full Body
$Lods = @{0 = "000000126C7EB58B"; 1 = "000000313DB95D1D"; 2 = "000000313DB95D2E"; 3 = "000000313DB95D33"}
foreach ($i in 0..3) {
    python -B $Kit/scripts/glb_rotate.py "$W\mesh\karin_lod$i.glb" "$W\mesh\karin_lod${i}_acu.glb" -90
    & $H import-glb "$W\mesh\karin_lod${i}_acu.glb" 0 "$W\mesh\karin_lod$i.Mesh" $Lods[$i]
}
python -B $Kit/scripts/glb_info.py "$W\mesh\karin_lod0_acu.glb"     # skin joints ≤ 255
```

### 5. 物理骨架与 payload

```powershell
python -B $Kit/scripts/acu_phys_skel.py <ACU_U_Arno_Hair.Skeleton.xml> "$W\mesh\karin_lod0_acu.glb" "$W\mesh\karin_phys.Skeleton.xml" `
    --id 323218444032 --report "$W\mesh\phys_report.json"
python -B $Kit/scripts/build_mod.py "$W\mesh" "$W\build" --phys "$W\mesh\karin_phys.Skeleton.xml"     # 末行 BUILD_OK
```

`acu_phys_skel.py` 打印骨数、BallJoint 数和骨架键，旁边写 `karin_phys.BallJointCommonData.xml` / `.LiteRagdoll.xml`；`--no-collide` 不写碰撞对象，
`--capsule-scale <f>` 放大胶囊半径（诊断）。`--id` 必须是 `build_mod.PHYS_ID`。`build_mod.py` 先删掉再重建输出目录，写 `$W\build\payload\`
（通用的头部容器、`forge\<forge>\` 下按 forge 的版本、`skip.tsv`）；`--tex-size`（默认 2048）、`--spec`（默认 40）、`--gloss`（默认 `90,90,120,70`）。
470 个作业约 15 分钟（6 个并行；第一次要提取全部副本）。

### 6. 安装 / 卸载（游戏关闭时）

```powershell
python -B $Kit/scripts/acu_install.py status                 # 有状态文件时先 uninstall
python -B $Kit/scripts/acu_install.py install "$W\build\payload"
python -B $Kit/scripts/acu_install.py uninstall
```

`install` 先为每个 ID 打印副本数，再逐行打印写进了哪个 forge；状态写在 `<游戏目录>\.karin_acu_state.json`，已有状态时拒绝安装。**更新或校验游戏文件前先卸载。**

### 7. 发行包

```powershell
python -B $Kit/scripts/make_release.py "$W\release\Karin_ACU_v7.zip" v7="$W\build\payload"
```

每个 `标签=payload` 生成 `payload_<标签>.tar.xz` 和 `install_<标签>.cmd`；另有 `uninstall.cmd`、`status.cmd`、`README.txt` 和 `acu_install.py`。`vanilla_sizes.tsv`
取自**这台机器**的原版游戏（装着 mod 时从状态里取原长）。`LABELS` 里是项目各版本的说明文字，新标签要自己加。发包前在有原版游戏的机器上用包里的
`.cmd` 跑一遍 安装 → 状态 → 卸载。zip 含游戏数据和模型，不要放进公开仓库。

## 脚本

| 脚本 | 用法 | 说明 |
| --- | --- | --- |
| `scripts/acu_forge.py` | `index <forge>…`（TSV 到 stdout）、`extract <forge> <out> <IDHEX>…` | forge v27 读取（也接受 v28）；纯标准库 |
| `scripts/scan_objs.py` | `<out.log> <IDHEX,…> <forge 或子串>… [--game]` | 调 harness 的 `scan-objs`，找嵌着这些对象的全部数据文件 |
| `scripts/objs_to_tsv.py` | `<out.tsv> <log>…` | 把 `scan_objs.py` 的日志汇成 `arno_tables.tsv`（forge、数据文件 ID、名字、对象 ID） |
| `scripts/acu_install.py` | `install <payload 目录 \| .tar.xz>`、`uninstall`、`status`，`[--game]` | 原地追加安装器；按 forge 的版本、`skip.tsv`、`vanilla_sizes.tsv` |
| `scripts/bt_tool.py` | `show <xml>`、`edit <in> <out> [--drop 列,…] [--set 列=ID[:路径]]… [--clear-dynres]`、`lodsel <in> <out> --lod I=ID[:路径]…` | BuildTable / LODSelector 的 schema XML 编辑（大革命不用空引用修补） |
| `scripts/build_mod.py` | `<mesh_dir> <out_dir> [--tex-size] [--spec] [--gloss] [--phys <xml>] [--game]` | 构建 payload；数据 ID、列号、材质 ID 是亚诺 / Karin 的案例值 |
| `scripts/acu_phys_skel.py` | `<模板.Skeleton.xml> <lod0 GLB> <out.Skeleton.xml> [--report] [--id] [--no-collide] [--capsule-scale]` | 附加骨架：Reference + 祖先骨 + KP 骨、BallJoint（重力补偿偏移）、裙片碰撞对象 |
| `scripts/make_release.py` | `<out.zip> <标签>=<payload>…` | 可重新部署的 zip（solid xz、`.cmd`、README、安装器、原版大小） |
| `scripts/head_bones.py` | `<glb> <网格名> [--min 0.3]` | 列出网格蒙到的每根骨和它的顶点重心，用来认没有名字的面部骨 |
| `scripts/glb_rotate.py` | `<in.glb> <out.glb> <度>` | 绕原始竖轴整体旋转；+90 / −90 往返精确 |
| `scripts/glb_info.py` | `<glb> [--joints]` | 网格、图元、材质、蒙皮关节 |
| `scripts/blender/prep_karin_original.py` | `blender -b --factory-startup --python … -- <fbx> <out.blend> <tex_dir>` | 把 Karin_Original 的 Unity FBX 规范化成源 blend + 贴图 |
| `scripts/blender/fit_karin.py` | `blender -b --factory-startup --python … -- <骨架 glb> <源 blend> <out.blend> […]` | 刚性躯干 + 四肢对关节的拟合，`--phys` 生成 +X 沿链的 KP 骨；没有 `Neck1` 时跳过颈部权重拆分 |
| `scripts/blender/face_rig.py` | `blender -b <fit.blend> --python … -- <源 blend> <out.blend> […]` | 下颌、眼睑、眼球的绑定偏移（杠杆）蒙皮；`GAME_BONES` = 大革命的头部骨 |
| `scripts/blender/export_karin_lods.py` | `blender -b <blend> --python … -- <out> --ratios … --profile acu_weapon --keep-full Body` | 改材质名为目标 Material ID、合并、三角化、白顶点色、≤ 4 权重、裁骨、减面 LOD |
| `scripts/blender/render_compare.py` | `blender -b <fit.blend> --python … -- <前缀> [--ref-scale 1]` | Karin / 亚诺 / 叠加的正面、侧面渲染 |
| `acuharness/Program.cs`、`build.ps1` | 见下表 | AcuHarness 源码与构建脚本 |

### AcuHarness 命令

| 命令 | 作用 |
| --- | --- |
| `batch <commands.tsv>` | 一行一条命令（制表符分隔、绝对路径），一个进程跑完，每条后打印 `BATCH <n> rc=<rc>` |
| `scan-objs <forge> <list.tsv> <IDHEX,…>` | 按索引行（偏移、大小、标签）在内存里解压数据文件，打印自身 ID 命中的对象（`OBJ`）和读不了的文件（`ERR`） |
| `unpack-data <file.data> <outdir>`、`unpack-export <outroot> <data…>` | 解包数据文件；`unpack-export` 还导出 XML |
| `export-xml <资源> <out.xml>…`、`export-xml-dir <dir> <outdir> [glob]`、`compile-xml <in.xml> <out>` | schema XML 往返；`compile-xml` 在被覆盖的文件旁留 `.bak` |
| `pack-data <目录> <原 .data\|-> <out.data>` | 打回数据文件（沿用原文件的元数据） |
| `export-glb <out.glb> <Mesh / Skeleton…>` | 导出 GLB（第一个骨架为主） |
| `import-glb <in.glb> <网格选择> <out.Mesh> <IDHEX> [--joints N] [--no-autoscale] [--offset x,y,z]` | Unity 分支：顶点格式 v2、白色 Color0 / Color1、缺副法线时取 N×T、> 255 骨拒绝 |
| `mesh-info`、`mesh-bones`、`mesh-binds`、`reserialize`、`debug-mesh`、`debug-data`、`games` | 网格、骨和工具的检查 |
| `tex-info`、`tex-export`、`tex-import <模板> <dds> <out> [--id HEX] [--maptype N]` | 贴图；只用内联 mip 的贴图（顶层 mip 会弹 GUI 文件对话框） |
| `scan-refs`、`prefetch-*`、`make-patch-meta`、`reflex-*`、`pack-forge` | 继承自奥德赛 / 影的 harness，大革命项目没有用到 |

环境变量：`ACU_GAME`（默认 `Unity`）、`ATK_DIR`（Oodle 所在的 `Libs` 的上级，默认 harness 目录）、`ATK_RUNTIME`（工作目录，`Lists\` 从这里读，默认 harness 目录）、
`ACSH_DEBUG=1`（打印第一次机会异常）。

## 换一个模型时

- `build_mod.py` 的数据 ID、列号、`PARTS` 贴图名，`export_karin_lods.py` 的 `acu_weapon` 材质映射，`face_rig.py` 的 `GAME_BONES` 和角度，`acu_phys_skel.py` 的
  `DEFAULT_PARAMS`（按 `KP_*` 名字匹配）和 `THIGH_CAPSULES` 都是 Karin_Original 对亚诺的案例值；换模型或换角色要重新测量（大腿胶囊要按新模型的大腿半径和裙摆位置算）。
- forge 读取、副本扫描、安装器、`bt_tool.py`、`glb_rotate.py`、发行打包、附加骨架的规则与模型无关。

## 边界

便携副本的核对（2026-10-24）：改动过的命令行脚本在合成数据和本机真实数据上与项目原脚本输出逐字节相同；用便携包重建 v7，数据文件里的全部对象与
发行的 v7 相同（[VALIDATION.md](../VALIDATION.md)）。Blender 脚本没有用本包重跑；实机结论来自项目用原脚本构建的 v1–v7。不带游戏资源、源模型、
AnvilToolkit、.NET、texconv、`Unity.gfl` 或构建产物；本机实机测试用的截图 / 按键辅助脚本（绑定本机路径）不随包。
