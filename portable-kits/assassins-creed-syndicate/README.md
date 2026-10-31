# 刺客信条：枭雄（Assassin's Creed Syndicate）便携包

先读 [游戏知识](../../games/assassins-creed-syndicate/README.md) 和 [构建流水线](../../games/assassins-creed-syndicate/BUILD_PIPELINE.md)。双胞胎的可视图、
数据 ID 与内嵌副本见 [技术合同](../../games/assassins-creed-syndicate/TECHNICAL_CONTRACTS.md)；物理见 [物理](../../games/assassins-creed-syndicate/PHYSICS.md)；
安装器与发行包见 [验证与发布](../../games/assassins-creed-syndicate/VALIDATION_AND_RELEASE.md)。

这是 Karin_Original 同时替换雅各布和伊薇·弗莱（Jacob / Evie Frye）的 mod（v5，2026-10-30 用户实机接受）实际使用的工具：forge v27 索引 / 提取、
内嵌副本扫描、按内容比对的原地追加安装器（Steam / Ubisoft Connect / Epic 自动定位）、BuildTable 的 XML 编辑、两兄妹的 payload 构建器、
附加骨架（BallJoint + 裙片碰撞）生成器、自带嵌入式 Python 的发行包打包器、两兄妹网格的一键构建（拟合 → 表情 → 导出 → 导入 → 物理骨架）、
GLB 骨名还原与坐标系旋转，以及 Blender 的源模型规范化 / 拟合 / 表情 / 导出 / 测量 / 对比渲染脚本。

工具链从刺客信条：大革命的便携包（完整仓库里的 `portable-kits/assassins-creed-unity/`）分出。**AcuHarness** 的源码在本包的 `acuharness/`（`Program.cs` 与大革命包
和本项目用的逐字节相同，`build.ps1` 是大革命包的便携版），运行时设 `ACU_GAME=Syndicate`（`build_mod.py`、`scan_objs.py`、`make_meshes.py` 会自己设），`Lists\` 里放 `Syndicate.gfl`。

- **游戏版本：** 制作用的是一份非商店版的 PC 副本（`ACS.exe` 链接时间 2016-08-16，forge v27，40 个 forge，357 161 个索引行），
  项目里标为「v1.51」，这个编号对 PC 版没有核实（公开的 PC 补丁记录到 1.4，2016-03）。Steam / Ubisoft Connect / Epic 版没有测过。
  数据文件的 ID、内嵌副本的分布和表的列号可能随版本变（`build-sensitive`）；安装器按内容比对每一份副本，不锁版本（[验证与发布](../../games/assassins-creed-syndicate/VALIDATION_AND_RELEASE.md) §3）。
- **mod 安装：** 不解包 forge。`acs_install.py` 把每个替换数据文件追加到每个含该 ID 的 forge 末尾（根目录和 `dlc_<n>\`），改指 20 字节索引行和名字表的大小；
  卸载写回原行并截断。安装和卸载时游戏必须关闭。
- **AnvilToolkit：** 1.3.6（第三方，用户自备，不随包），只经 AcuHarness（本包 `acuharness/` 的 C# 源码）无界面调用；要 AnvilToolkit 的 `Libs\`（含 Oodle）和 `Syndicate.gfl`
  （Kamzik123/AnvilToolkit-Resources）。
- **.NET / Blender / texconv：** 编译 AcuHarness 用 .NET SDK，运行用 .NET 9 运行时（9.0.18）；Blender 5.0.1 后台模式；DirectXTex `texconv.exe`。
- **Python：** 3.10 或更高（`acs_install.py` 单独在 3.8+ 上跑）；`acs_phys_skel.py`、`head_bones.py`、`glb_rotate.py`、`glb_info.py` 要 numpy，
  `build_mod.py` / `make_meshes.py` 要根目录 `requirements.txt` 里的 Pillow；其余只用标准库。
- **发行包里的 Python：** `make_release.py` 把 python.org 的 Windows 嵌入式 Python（`python-x.y.z-embed-amd64.zip`，项目用 3.14.10）放进 zip 的 `python\`，
  `.cmd` 是纯 ASCII 批处理，用户电脑不需要装 Python，也不需要 PowerShell。

## 环境变量

| 变量 | 用在 | 内容 |
| --- | --- | --- |
| `ACS_GAME_DIR` | `acs_install.py`、`build_mod.py`、`scan_objs.py`、`make_release.py`（前三个也可用 `--game`） | 游戏目录（含 `ACS.exe`、`*.forge`、`dlc_<n>\`）；不设时从 Steam 库、Ubisoft Connect 注册表、已安装程序、Epic 清单里找，找到多个时让人选 |
| `ACS_CACHE` | `build_mod.py`、`scan_objs.py` | 放 `index.tsv`（`acs_forge.py index`）和 `twin_objs.tsv` / `twin_meshes.tsv`（`objs_to_tsv.py`；可选 `twin_objs2.tsv`）的目录 |
| `ACS_SCRATCH` | `build_mod.py`（可选） | 原版副本缓存和作业临时目录，默认 `%TEMP%\acs_work`；放在仓库和同步盘之外 |
| `ACS_HARNESS`、`ACS_DOTNET` | `build_mod.py`、`scan_objs.py`、`make_meshes.py` | `AcuHarness.dll`（大革命包 `acuharness/build.ps1` 编译）和运行它的 `dotnet.exe` |
| `ACS_TEXCONV` | `build_mod.py` | `texconv.exe` |
| `ACS_SRC_TEX` | `build_mod.py` | 源模型贴图目录：`Karin_Face.png`、`Karin_Body.png`、`Karin_Hair.png`、`Karin_Costume.png`（`prep_karin_original.py` 写出） |
| `ACS_TEMPLATES` | `build_mod.py`、`make_meshes.py` | 材质 / 贴图 / 头发骨架模板目录（§0 第 4 步） |
| `ACS_BLENDER`、`ACS_SRC_BLEND` | `make_meshes.py` | `blender.exe` 和 `prep_karin_original.py` 写出的源 blend |
| `ACS_PHYS_ROOTS` | `make_meshes.py`（或 `--phys-roots`） | 第 2 阶段的 35 个链根，逗号分隔（[构建流水线](../../games/assassins-creed-syndicate/BUILD_PIPELINE.md) §3） |
| `ACS_PYTHON_EMBED` | `make_release.py`（或 `--python`） | `python-x.y.z-embed-amd64.zip` |

缺少必需的变量时，脚本在写任何文件之前报错并说出变量名。项目原脚本里写死的路径（默认游戏目录、同步盘上的工程目录、共享工具目录）都改成了这些变量
（[VALIDATION.md](../VALIDATION.md)）。

## 构建流程

命令从仓库根运行（PowerShell 7）。产物写到仓库和同步盘之外的工作目录 `$W`，全部用绝对路径。

```powershell
$Kit = "portable-kits/assassins-creed-syndicate"
$W = "<仓库之外的工作目录>"
$H = { & $env:ACS_DOTNET $env:ACS_HARNESS @args }
$env:ACU_GAME = "Syndicate"
```

### 0. 一次性准备

1. 编译 AcuHarness（.NET SDK 编译，运行用 .NET 9 运行时）：

   ```powershell
   $env:ACU_ATK_DIR = "<解压的 AnvilToolkit 1.3.6>"; $env:ACU_DOTNET_ROOT = "<.NET 9 运行时文件夹>"
   $env:ACU_ATK_LISTS = "<放 Syndicate.gfl 的目录>"; $env:ACU_HARNESS = "<输出目录>\AcuHarness.dll"
   pwsh -NoProfile -File $Kit/acuharness/build.ps1     # 末行打印 AcuHarness.dll 的路径
   $env:ACS_HARNESS = $env:ACU_HARNESS; $env:ACS_DOTNET = "$env:ACU_DOTNET_ROOT\dotnet.exe"
   ```

   `build.ps1` 的注释里写的是 `Unity.gfl`：它只是把 `ACU_ATK_LISTS` 目录里的文件拷进 harness 的 `Lists\`，放 `Syndicate.gfl` 即可。
2. 全部 forge 的索引（纯 Python，几秒钟）：

   ```powershell
   $F = (Get-ChildItem "$env:ACS_GAME_DIR\*.forge", "$env:ACS_GAME_DIR\dlc_*\*.forge").FullName
   python -B $Kit/scripts/acs_forge.py index @F > "$env:ACS_CACHE\index.tsv"
   ```

3. 内嵌副本清单（要 harness；每个 forge 组约 20 分钟，伦敦 / London_20 / London_21 这几个大 forge 单独跑，可以 6 个并行；跳过 `_gi` / `_grid`）：

   ```powershell
   $Tables = "0FE84A8684,0FE84A864A,2FF072B654,2FF072B66E,5B2AF6EA66,5B2AF6EA67,47C93F09B4,483A8DECA4,14B2685216,6CF114F8C1,44F5C89FE1,44F5C89FE2,44F5C89FE3,60E697FF79,60E697FF81,58EAD0A853,4855906D31,5C8B4C3D6B,5DCB8CAD55,4479401BE8"
   $Lods = "27CCC692C6,38534E59BE,38534E59C3,38534E59C8,3E33A56077,5D2B51F63C,5D2B51F641,5D2B51F646"
   python -B $Kit/scripts/scan_objs.py "$W\objs_london.log" $Tables DataPC_ACVI_London.forge     # 其余 forge 组同理
   python -B $Kit/scripts/objs_to_tsv.py "$env:ACS_CACHE\twin_objs.tsv" (Get-ChildItem "$W\objs_*.log").FullName   # PowerShell 不替原生程序展开通配符
   python -B $Kit/scripts/scan_objs.py "$W\lods.log" $Lods .forge
   python -B $Kit/scripts/objs_to_tsv.py "$env:ACS_CACHE\twin_meshes.tsv" "$W\lods.log"
   ```

   ID 是 `build_mod.py` 的 `TABLES` 和 `CHARS[*]["lods"]`。

4. 模板（`ACS_TEMPLATES`，文件名要和脚本里的一致）。`acs_forge.py extract <forge> <out> <IDHEX>…` 写 `<行号>_-_<名字>.data`，`& $H unpack-data` 解包，
   `& $H export-xml` 导出 XML：

   | 模板文件 | 来源 |
   | --- | --- |
   | `9472_-_ACVI_Weapons_Kukri.Material.xml`、`12767_-_ACVI_Weapons_Kukri_Set.TextureSet.xml` | `DataPC.forge` 的 `Game Bootstrap Settings`（`0000000000000800`）里的对象 9472 / 12767（`CN_Weapon_NoAlphaTest`），导出 XML |
   | `0_-_ACVI_CHR_P_JacobFrye_Head_DiffuseMap.TextureMap`、`0_-_ACVI_CHR_P_JacobFrye_Head_NormalMap.TextureMap` | `DataPC_SharedGroup_00.forge` 的 `0000001D39EEE733` / `0000001D39EEE737`，解包后的对象 0（内联 mip） |
   | `0_-_ACVI_Weapons_Kukri_SpecularMap.TextureMap` | `DataPC.forge` 的 `0000002298E449CC`，解包后的对象 0 |
   | `ACVI_CHR_P_JacobFrye_Hair.Skeleton.xml` | 雅各布头部容器 `ACVI_CHR_P_JacobFrye_Head`（`0000000FE84A8684`，如 `DataPC_ACVI_London.forge`）里的头发附加骨架，导出 XML |

### 1. 源模型与探针 GLB

```powershell
blender -b --factory-startup --python $Kit/scripts/blender/prep_karin_original.py -- "<Karin(Clone)_BlenderSafe.fbx>" "$W\src\karin_original_src.blend" "$W\src\src_tex"
$env:ACS_SRC_BLEND = "$W\src\karin_original_src.blend"; $env:ACS_SRC_TEX = "$W\src\src_tex"
# 每个双胞胎：基础骨架 + 头部 LOD0 + 一件服装的身体 LOD0 + 它的附加骨架 + 头部骨架
& $H export-glb "$W\probe\jacob_probe.glb" <ACVI_CHR_SHR_Male.Skeleton> <雅各布头部 LOD0 .Mesh> <服装身体 LOD0 .Mesh> <服装附加 .Skeleton> <头部 .Skeleton>
python -B $Kit/scripts/glb_names.py "$W\probe\jacob_probe.glb" "$W\probe\jacob_named.glb" --dict "$W\bone_names.json"
python -B $Kit/scripts/glb_rotate.py "$W\probe\jacob_named.glb" "$W\mesh\probe\jacob_fitframe.glb" 90
blender -b --factory-startup --python $Kit/scripts/blender/measure_glb.py -- "$W\mesh\probe\jacob_fitframe.glb"   # 鞋底高度 → --ground
```

`ACVI_CHR_SHR_Male.Skeleton` 在 `DataPC.forge` 的 `DataItems`（`0000000100017E09`）里（对象 33），`ACVI_CHR_SHR_Female` 嵌在 `ACVI_DataAI_UIDataRoot_Evie`（对象 3）。
枭雄的骨没有名字（骨 ID = 名字的 CRC32），`glb_names.py` 用 CRC32 把骨名还原，并修正工具按别名命名的面部骨（`--dict` 的 JSON 会写回新认出的名字）。

### 2. 网格、表情与物理骨架（两兄妹一起）

```powershell
python -B $Kit/scripts/make_meshes.py "$W\mesh" --stage 2      # 末行 MESHES_OK；每个双胞胎约 2 分钟
```

逐个双胞胎执行：`fit_karin.py`（`--scale auto --ground 0.0 --foot-squash 0.8 --hide-band body_2:0.20:0.46:0.15`、`--phys` 链根）→ `face_rig.py` →
`export_karin_lods.py --profile acs_weapon --mat-base <base> --split-normals skirt:40` → `glb_rotate.py -90` → `import-glb`（原版头部 LOD ID）→
`acs_phys_skel.py`（`--id <base + 0xF00>`）。写 `$W\mesh\<twin>\karin_lod0..3.Mesh` 和 `Karin_Phys_<twin>.Skeleton.xml`（+ `.BallJointCommonData.xml` /
`.LiteRagdoll.xml`）。`--stage 1` 不带链根和表情；`--twins jacob`、`--no-face`、`--face-args "…"` 用于单独调试。

### 3. payload

```powershell
python -B $Kit/scripts/build_mod.py "$W\mesh" "$W\build" --phys "jacob=$W\mesh\jacob\Karin_Phys_jacob.Skeleton.xml" --phys "evie=$W\mesh\evie\Karin_Phys_evie.Skeleton.xml"
```

318 份数据文件副本、6 个并行约 12 分钟，payload 约 870 MB（290 个文件 + `skip.tsv`）；stdout 到结束才整块输出，末行 `BUILD_OK`。每一份原版表先重新编译，
和原版逐字节不同就停。

### 4. 安装 / 卸载（游戏关闭时）

```powershell
python -B $Kit/scripts/acs_install.py status
python -B $Kit/scripts/acs_install.py install "$W\build\payload"
python -B $Kit/scripts/acs_install.py uninstall
```

状态写在 `<游戏目录>\.karin_acs_state.json`，已有状态时拒绝安装。安装前检查写权限（Program Files 下要管理员）。

### 5. 发行包

```powershell
python -B $Kit/scripts/make_release.py "$W\release\Karin_ACS.zip" s2="$W\build\payload" --python "<python-3.x.y-embed-amd64.zip>"
```

每个 `标签=payload` 生成 `payload_<标签>.tar.xz`（附 `vanilla.tsv`：每份被替换副本在**这台机器**原版里的大小 + SHA-1，装着 mod 时经状态文件读原位置）
和 `install_<标签>.cmd`；另有 `uninstall.cmd`、`status.cmd`、`README.txt`、`acs_install.py` 和 `python\`。zip 含游戏数据和模型，不要放进公开仓库。

## 脚本

| 脚本 | 用法 | 说明 |
| --- | --- | --- |
| `scripts/acs_forge.py` | `index <forge>…`、`extract <forge> <out> <IDHEX>…` | forge v27 读取；纯标准库 |
| `scripts/scan_objs.py` | `<out.log> <IDHEX,…> <forge 或子串>… [--game]` | 调 harness 的 `scan-objs`，找嵌着这些对象的全部数据文件 |
| `scripts/objs_to_tsv.py` | `<out.tsv> <log>…` | 汇成 `twin_*.tsv`（forge、数据文件 ID、名字、对象 ID） |
| `scripts/acs_install.py` | `install <payload 目录 \| .tar.xz>`、`uninstall`、`status`，`[--game]` | 原地追加安装器；按 ID + 内容匹配副本、写权限预检、自动找游戏 |
| `scripts/bt_tool.py` | `show`、`edit … [--drop] [--set]… [--clear-dynres]`、`lodsel` | BuildTable / LODSelector 的 schema XML 编辑；`edit()` 还有 `add_missing`（补缺的单元格） |
| `scripts/build_mod.py` | `<mesh_root> <out_dir> [--phys twin=xml]… [--workers] [--tex-size] [--spec] [--gloss] [--game]` | 两兄妹的 payload；数据 ID、列号、材质 ID 是案例值 |
| `scripts/make_meshes.py` | `<out_root> [--stage 1\|2] [--twins] [--face-args] [--no-face] [--phys-roots]` | 两兄妹的网格与物理骨架一键构建 |
| `scripts/acs_phys_skel.py` | `<模板> <lod0 GLB> <out.Skeleton.xml> --id <ID> [--report] [--no-collide] [--capsule-scale]` | 附加骨架（`MirroringTag` / `EnablePoseDrivenWrinkles`、GlobalGravity 裙片碰撞、按链分节参数、`upright` 偏移） |
| `scripts/make_release.py` | `<out.zip> <标签>=<payload>… [--python <embed.zip>]` | 可重新部署的 zip（solid xz、`vanilla.tsv`、嵌入式 Python、ASCII `.cmd`） |
| `scripts/glb_names.py` | `<in.glb> <out.glb> [--dict <json>] [--ref <named.glb>]…` | 按 CRC32 还原骨名、修正别名 |
| `scripts/head_bones.py`、`glb_rotate.py`、`glb_info.py` | `<glb> <网格名> [--min]`、`<in> <out> <度>`、`<glb> [--joints]` | 认面部骨、绕竖轴旋转（+90 / -90 往返精确）、GLB 概览 |
| `acuharness/Program.cs`、`build.ps1` | 见 §0 第 1 步 | AcuHarness 源码与构建脚本（命令：`batch`、`scan-objs`、`unpack-data`、`export-xml-dir`、`compile-xml`、`pack-data`、`export-glb`、`import-glb`、`tex-import` 等） |
| `scripts/blender/*.py` | `blender -b … --python <脚本> -- …`（用法见各脚本文档字符串和 §1–§2） | `fit_karin.py` 加了 `--hide-band`，`export_karin_lods.py` 加了 `acs_weapon` 配置和 `--split-normals` |

## 换一个模型时

`build_mod.py` 的 `CHARS` / `TABLES` / `PHYS_HOSTS`、`export_karin_lods.py` 的 `acs_weapon` 材质映射、`face_rig.py` 的骨映射与角度、`acs_phys_skel.py` 的
`DEFAULT_PARAMS` 和 `THIGH_CAPSULES`、`make_meshes.py` 的 `FIT_ARGS`（膝盖隐藏带）都是 Karin_Original 对两兄妹的案例值。forge 读取、副本扫描、安装器、
`bt_tool.py`、`glb_names.py`、`glb_rotate.py`、发行打包与附加骨架规则与模型无关。

## 边界

便携副本的核对见 [VALIDATION.md](../VALIDATION.md)。实机结论来自项目用原脚本构建的 v1–v5。不带游戏资源、源模型、AnvilToolkit、.NET、texconv、
`Syndicate.gfl`、嵌入式 Python 或构建产物（`acuharness/` 只有源码）；本机实机测试用的截图 / 按键辅助脚本和存档转换脚本不随包。
