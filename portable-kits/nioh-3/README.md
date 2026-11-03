# 仁王3（Nioh 3）便携包

先读 [游戏知识](../../games/nioh-3/README.md) 和 [构建流水线](../../games/nioh-3/BUILD_PIPELINE.md)。资源表注入、G1M、骨架、每材质计数和物理注册表的约定见 [技术合同](../../games/nioh-3/TECHNICAL_CONTRACTS.md)；贴图存储见 [G1T 格式](../../games/nioh-3/G1T_FORMAT.md) 和 [材质与贴图](../../games/nioh-3/MATERIALS_AND_TEXTURES.md)；骨链和碰撞体见 [物理](../../games/nioh-3/PHYSICS.md)；面部骨权重见 [表情](../../games/nioh-3/FACE.md)；崩溃和症状见 [排障手册](../../games/nioh-3/TROUBLESHOOTING.md)；离线 / 实机闸门和发行包见 [验证与发布](../../games/nioh-3/VALIDATION_AND_RELEASE.md)；版本轨迹见 [Karin_Original 案例](../../games/nioh-3/cases/KARIN_ORIGINAL.md)、[伊切尔案例](../../games/nioh-3/cases/ICHEL.md)、[Lenko 案例](../../games/nioh-3/cases/LENKO.md)。

这是替换仁王3 女性主角（忍者 / 武士两件上衣）的三个 Mod 实际使用的工具，三个角色共用一条构建链，各自只多一层前处理和参数：

- **Karin_Original**：FBX 经 Blender 导出（测试构建 build7–build24，发行包 build24）；
- **伊切尔**（尘白禁区，`scripts/n3ichel/`）：由 PMX 转换来的 FBX 经 Blender 导出，再按原 PMX 的材质拆成部位网格（ichel1）；
- **Lenko**（MMD `Lenko06.pmx`，`scripts/n3lenko/`）：不经 Blender，直接读 PMX（lenko1–lenko4）。

包里有：KT 引擎的格式库（`g1m_tool.py`、`g1t_tool.py`、`ktdata.py`，与浪人崛起便携包 `portable-kits/rise-of-the-ronin/` 的同名文件逐字节相同）、仁王3 的 G1T v0066 存储类型 3 编解码、NUNO type-4 骨链读取、`root.rdb` / `root.rdx` 注入安装器、资源定位和统计脚本、共用构建链 `scripts/n3build/`、伊切尔和 Lenko 的前处理 `scripts/n3ichel/`、`scripts/n3lenko/`、Blender 导出脚本、发行包用的安装器 `karin_install.py`（伊切尔、Lenko 的发行包用同一个安装器，只改了文件名和说明里的角色名）、改存档外观设置的换装器 `n3_miaomiao.py`（[存档与外观设置](../../games/nioh-3/SAVE_AND_APPEARANCE.md)），以及会话里写的离线检查 `scripts/checks/`。

- **游戏版本：** 仁王3 v2.0.0.2（PC）。资源在游戏目录的 `package\`（`root.rdb`、`root.rdx`、`0x<哈希>.fdata`）。
- **加载方式：** `n3inject.py` 改写 `root.rdb` / `root.rdx`：所有覆盖文件不压缩地放进新容器 `0x4b415249.fdata`（`KARI`），`root.rdx` 多一个容器槽，被覆盖的记录改指这个容器。第一次使用时把原表备份成 `root.rdb.original` / `root.rdx.original`。不用 DLL，不改 exe。
- **Blender：** 项目用 4.0.2，后台运行，`--factory-startup`。两个 Blender 脚本（`scripts/blender/ko_extract_source.py`、`scripts/n3build/blender_shapekeys.py`）用 Blender 自带的 Python 和 numpy，参数写在 `--` 之后。伊切尔的 FBX 也用这两个脚本导出；Lenko 不用 Blender。
- **texconv：** DirectXTex 的 `texconv.exe`，由用户自备。`n3_textures.py` 用 `<N3_BUILD>\toolchain\texconv.exe`；`find_variant.py`、`tex_stats.py` 用 `--texconv`（默认是脚本旁边的 `texconv.exe`）。
- **Python：** 定位脚本、`n3inject.py`、`karin_install.py` 和三个格式库只用标准库（安装器单独在 Python 3.8+ 上也能跑）。构建链、`n3_g1t.py`、`n3_g1t_resize.py`、`fpose.py`、`g1a.py`、`g2a.py`、`face_bones.py`、`n3_miaomiao.py` 和离线检查另需 numpy（`n3_miaomiao.py` 的图形界面用标准库 tkinter）；`n3_conform.py`、`n3_physics.py`、`n3_face.py` 另需 scipy；`g1m_render.py`、`g1m_subs.py`、`checks/swing.py`、`checks/facecheck.py` 另需 matplotlib；`n3_textures.py`、`find_variant.py`、`tex_stats.py` 另需根目录的 Pillow。
  `n3ichel/`、`n3lenko/` 下除 `pmx_read.py`（标准库；`geometry()` 要 numpy）以外都要 numpy；`ichel_source.py`、`ichel_conform.py`、`ichel_physics.py`、`lenko_conform.py`、`lenko_physics.py`、`lenko_source.py` 另需 scipy；`ichel_build.py`、`lenko_build.py`、`lenko_view.py` 另需 Pillow，`lenko_view.py` 还要 matplotlib。
  新增的检查都要 numpy；`layer_swing.py`、`face_sim.py`、`face_render.py`、`readback_blink.py`、`vanilla_blink.py` 另需 scipy，`face_render.py`、`readback_blink.py` 另需 Pillow。`requirements.txt` 钉的版本要 Python 3.12 或更高。本次在 3.14.0、numpy 2.5.2、scipy 1.18.0、matplotlib 3.11.2、Pillow 12.3.0 上测试。
- **只在 Windows 上：** `karin_install.py` 和 `n3_miaomiao.py` 写文件前用 `tasklist` 判断游戏是否在运行；texconv 只有 Windows 版。项目在 Windows 上构建，游戏在另一台测试机上。
- **运行位置：** 以下命令都从交接包根目录执行。所有命令都有 `--help`；不带参数的构建步骤（`n3_conform.py`、`n3_textures.py`、`ichel_conform.py`、`lenko_conform.py`、`lenko_coll.py`、`checks/coll_cover.py` 等不带参数的检查）的 `--help` 只打印说明，不会开始处理。

## 环境变量与参数

| 变量 / 参数 | 读的脚本 | 含义 |
| --- | --- | --- |
| `N3_BUILD` | `scripts/n3build/`、`n3ichel/`、`n3lenko/` 下的构建步骤（`pmx_read.py`、`lenko_pmx.py` 除外），`checks/` 下除 `diff24.py`、`radial_gap.py` 以外的检查 | 工作目录，布局见下一节。原项目默认用会话临时目录里的 `build\`；便携版没有默认值，用到路径时才检查，没设时报错并说出变量名（`--help` 不需要它） |
| `N3_VRM`（`--vrm`） | `n3_physics.py` 默认模式 | Karin 的 VRM 文件（带 `VRMC_springBone`，由 PhysBone 转换来的 39 条弹簧链）。原脚本写死了源模型目录里的 VRM。`--geometry` 模式不需要 |
| `N3_HEAD_SCALE` | `n3_conform.py`、`ichel_conform.py`、`lenko_conform.py` | 源模型整体缩放。`n3_conform.py` 默认 150（Blender 米 → 游戏厘米，并让头和游戏的头一样大）；另两个默认按颈高取（源模型的 Neck 落在游戏颈骨的高度） |
| `<模型目录>`（位置参数） | `ichel_source.py`、`lenko_source.py`、`checks/face_render.py`、`checks/readback_blink.py` | 源模型文件夹（PMX 和贴图）。`face_render.py` 按 `source/source.json` 里材质的 `texture_file` 相对它找贴图（原脚本写死了源模型目录），`readback_blink.py` 把它转给 `face_render.py` |
| `--texconv` | `find_variant.py`、`tex_stats.py` | texconv 可执行文件，默认是脚本旁边的 `texconv.exe`（原脚本只认这个位置） |
| `--data` | `karin_install.py` | 发行包的数据目录（`files\`、`collapse.txt`、`vanilla.json`、`package.json`；`staging\` 也建在这里），默认是脚本所在目录，即发行包的布局 |
| `--png` | `checks/swing.py`、`checks/facecheck.py` | 渲染图的输出路径，默认当前目录下的 `swing.png` / `facecheck.png`（原脚本写进会话临时目录的根） |

## 工作目录

```text
<N3_BUILD>/
  orig/                 原版文件副本（extract_many.py 取出，只读）：
                          0x5548953f.g1m 忍者上衣、0xed9b4309.g1m 武士上衣（写入目标）
                          0x4ba258df.g1m 女性基础身体（骨架和皮肤权重参考）、0xb24cac84.g1m 女性捏脸头（面部骨绑定核对）
                          0xd5d385f9.g1m 发型（头发骨链模板、head 碰撞组）、0xfed6b90c.g1m 腰腿（腰带垂饰模板）
                          0x6a0d18db.g1m 额饰（legs / skirt 碰撞组）
                          0x5583ad7d.bin / 0xedd65b47.bin 物理注册表，0x5c3826bd.bin / 0xf48ad487.bin 每材质计数（忍者 / 武士）
  source/               ko_extract_source.py：source.json、source.npz、textures/；blender_shapekeys.py：shapekeys.json、shapekeys.npz
  face/                 0xc76b3a43.g1fpose（女性面部姿势库）；facecheck.py 读的表情预设 0x<哈希>.g1frani
  tex/                  原版贴图模板：0x8b541440.g1t（COLOR）、0x7f1eb597.g1t（NORMAL）、0xe0739e0c.g1t（SHADING）、0x52244783.g1t（49 号槽）
  toolchain/texconv.exe
  conformed.npz, conform.json         n3_conform.py 写
  physics.json                        n3_physics.py 写
  face.json                           n3_face.py 写
  g1m/                                n3_build_g1m.py 写 <模型>.g1m、build_report[_samurai].json；n3_registry.py 写 <注册表>.bin、<计数>.bin
  atlas_uv.json                       n3_build_g1m.py 写（图集里各材质的区域）
  g1t/                                n3_textures.py 写（开始时先清空）
```

`extract_many.py` 按内容给扩展名（`.g1m`、`.g1t`、`.ktid`、`.kidsobjdb`，其余 `.bin`）。面部姿势库和表情预设取出来是 `.bin`，改名为 `.g1fpose` / `.g1frani`。

伊切尔和 Lenko 各用一个工作目录，布局相同：`orig/`、`tex/`、`face/`、`toolchain/` 从 Karin 的工作目录复制（替换的是同一批资源）；`source/` 由 `ichel_source.py` / `lenko_source.py` 写（Lenko 另有 `source_report.json`）；`atlas_uv.json` 由 `ichel_build.py textures` / `lenko_build.py textures` 写。伊切尔的 Blender 导出要放在 `source/` 以外的目录（下面的 `<FBX 导出目录>`，项目里是工作目录下的 `raw/`），因为 `ichel_source.py` 要从它读、往 `source/` 写。

## 构建流程

下面 0–8 是 Karin_Original 的流程。伊切尔、Lenko 的工作目录用同样的原版文件（第 0 步），自己做第 1–2 步的前处理和贴合 / 物理，表情、写 G1M、校验、注册表、贴图都调用同一批 `n3build/` 脚本，安装和换装与 Karin 相同；见后面的[伊切尔](#伊切尔由-pmx-转换的-fbx)和 [Lenko](#lenko直接读-pmx) 两节。

```powershell
$Kit = "portable-kits/nioh-3"; $S = "$Kit/scripts"; $B = "$S/n3build"; $C = "$S/checks"
$env:N3_BUILD = "<工作目录>"; $W = $env:N3_BUILD
$env:N3_VRM = "<Karin 的 VRM>"
$Pkg = "<游戏目录>\package"
$Blender = "<Blender 4.0.2>\blender.exe"
python -m pip install -r requirements.txt -r $Kit/requirements.txt
```

### 0. 定位与取原版

```powershell
python -B $S/etw_reads.py reads.csv $Pkg reads.json [--patched]          # ETW 文件读取（tracerpt CSV）→ 每个阶段读了哪些资源
python -B $S/phase_only.py reads.json g1t 03_level 01_menu 1000          # 只在某个阶段读到的贴图；phase_diff.py 求交集
python -B $S/model_refs.py $Pkg 0x5548953f                               # 模型在 CharacterEditor 里的条目和链接的资源
python -B $S/extract_many.py $Pkg "$W/orig" 0x5548953f 0xed9b4309 0x4ba258df 0xb24cac84 0xd5d385f9 0xfed6b90c 0x6a0d18db `
    0x5583ad7d 0xedd65b47 0x5c3826bd 0xf48ad487
python -B $S/extract_many.py $Pkg "$W/tex" 0x8b541440 0x7f1eb597 0xe0739e0c 0x52244783
```

阶段标记、`logman` / `tracerpt` 的命令见 [构建流水线](../../games/nioh-3/BUILD_PIPELINE.md) §1。装过 mod 的游戏也能取原版：`extract_many.py` 和定位脚本有 `root.rdb.original` 时从它读。

### 1. 源模型（Blender）

```powershell
& $Blender --factory-startup --background --python $S/blender/ko_extract_source.py -- "<Karin.fbx>" "$W/source"
& $Blender --factory-startup --background --python $B/blender_shapekeys.py -- "<Karin.fbx>" "$W/source"
```

- `ko_extract_source.py`（浪人崛起项目的构建第 1 步）：FBX → `source.npz`（每个网格的顶点、逐 loop 法线 / UV / 三角形 / 材质号、权重）、`source.json`（骨骼的头尾和矩阵、网格、材质与贴图节点、已应用的形态键）、`textures/`（打包在 FBX 里的贴图原样写出）。保留预制体的形态键组合，不摆姿势、不缩放，Blender 世界坐标（Z 向上，米）。
- `blender_shapekeys.py`：每个网格的每个形态键相对 Basis 的世界空间位移 → `shapekeys.npz` / `shapekeys.json`（名字、动了的顶点数、最大位移），与预制体当前的组合无关。`n3_common.load_source` 和 `n3_face.py` 从 `source/` 读它们。

### 2. 贴合、物理、表情

```powershell
python -B $B/n3_conform.py            # → conformed.npz、conform.json；跨侧检查不过就停
python -B $B/n3_physics.py            # → physics.json（Karin 自己的弹簧链；--geometry [--skirt] 是早期按几何推的链）
python -B $B/n3_face.py               # → face.json（--extended 另加 27/28、39/40、59/60、160；--vanilla-lids 见下）
```

- `n3_conform.py`：源模型按 `N3_HEAD_SCALE` 缩放并平移到 Karin 的 Neck 落在游戏骨 11 上；头颈刚性，其余人形骨各拟合一个仿射（骨段方向和长度，保持截面），按 Karin 的权重线性混合。权重：Karin 的骨映射到游戏骨（躯干按高度分到脊椎）；贴身网格从原版身体 `0x4ba258df` 最近点迁移（远了淡出，手指保留映射权重，袖子不用手和手指骨）；头、头发、耳朵 → 12，尾巴 → 2，裙子越往下摆越跟最近的腿部皮肤。左右两侧的顶点不能拿另一侧手臂链的权重（按骨架判断）。
- `n3_physics.py`：VRM 的每条弹簧链成为一条 type-4 链，点 = 骨骼头加末端，用该骨骼自己的顶点做「源 → 贴合后」的拟合映射到游戏空间；第 i 个关节取第 i 根骨的源权重，其余权重按贴合后的游戏骨等比保留。`RIG` 定每类链的模板和碰撞组，`RIG_ANCHOR` 定挂接骨，脸颊两条跳过。
- `n3_face.py`：脸（Body 网格）蒙到玩家面部骨上，让游戏的面部姿势按 Karin 自己的形态键动：每个映射姿势取 6 根平移最大、旋转不超过 0.25 rad、在基础身体 / 女性头 / 两件上衣里绑定姿势相同的驱动骨，逐顶点非负岭回归；面部骨权重可以大于 1，头骨吃负的剩余，量化到同一个 f16 网格使总和精确为 1。`--vanilla-lids`（Lenko 的 lenko3 起；不加时结果与以前相同）另拟合 27/28、39/40 两组闭眼姿势：目标是 `blink_L` / `blink_R` 乘以它们在原版女性头 `0xb24cac84` 上相对 41/42 的闭合比例（0.82 / 0.85，`checks/vanilla_blink.py` 量的），优先级 1 / 2（`VANILLA_LIDS`、`VANILLA_LIDS_PRIORITY`），这样游戏用哪组姿势眨眼，这张脸都闭到原版脸闭到的程度。

### 3. 写 G1M 并读回

```powershell
python -B $B/n3_build_g1m.py ninja   --physics --collide --face
python -B $B/n3_build_g1m.py samurai --physics --collide --face
python -B $B/n3_validate_g1m.py "$W/g1m/0x5548953f.g1m" "$W/orig/0x5548953f.g1m" --layout-changed --physics
python -B $B/n3_validate_g1m.py "$W/g1m/0xed9b4309.g1m" "$W/orig/0xed9b4309.g1m" --layout-changed --physics
```

- `n3_build_g1m.py [ninja|samurai] [--physics [--collide] [--face]]`：Karin 的主体写进上衣的 rest 子网格；其余原版子网格保留缓冲、材质和 MESH_LOD 组，三角形塌缩；手臂、裙子 / 脸、每个 type-4 条目一个网格插在最后一个材质 0 子网格之后（各自的顶点缓冲、属性集、调色板、索引缓冲、子网格，MESH_LOD 类型 2 组 NUN id 0x2710 + k）。调色板超过 85 改 u16 骨索引（上限 128，再多就把权重最小的骨合并到保留的祖先，物理关节和面部骨不合并）；每个调色板条目用原生逆绑定（没有就追加到 MM1G）；FM1G 的计数和 GM1G 包围盒随之更新。`--physics` 用 `n3_g1m_physics.py` 写 SM1G 关节、ONUN type-4 子块和 FM1G 统计；`--collide` 追加各链的 LLOC 碰撞组（否则都用模型的第 0 组）；`--face` 把 `face.json` 的权重写给脸并放进裙子的子网格。输出 `g1m/<模型>.g1m`、`build_report[_samurai].json`、`atlas_uv.json`。
  `n3_g1m_physics.py` 的 `COLLISION_SETS` 条目是（原版模型，LLOC 条目号，追加的椭球[，`resize`]）：`resize` 是 `lloc_entry_bytes` 的参数，按图元号改原版椭球的半轴和中心（旋转不变）；`TEMPLATE_BLOCKS` 放 `orig/` 里没有的原版模型的 type-4 参数块（168 字节），按模板名直接用。两者都是 Lenko 加的；`TEMPLATE_BLOCKS` 默认为空、不给 `resize` 时，Karin / 伊切尔的输出不变。
- `n3_validate_g1m.py <built> <template> [--layout-changed] [--physics]`：用 `g1m_tool.py` 独立读回：文件大小字段、每个子网格的索引范围、调色板大小（u8 85 / u16 128）、调色板条目是原生绑定、权重和为 1、骨索引是 3 的倍数且在调色板内、FM1G 计数；预期之外的节和块必须逐字节不变。打印 `PASS` / `FAIL`，失败时退出码 1。

### 4. 贴图

```powershell
python -B $B/n3_textures.py                    # → g1t/：4096 BC7 图集 + 三张常量贴图 + 读回比较
python -B $S/n3_g1t.py info "$W/tex/0x7f1eb597.g1t"
python -B $S/n3_g1t.py constant "$W/tex/0x7f1eb597.g1t" --rgba 128,128,255,255 --output flat.g1t
python -B $S/n3_g1t.py dds <file>.g1t --output view.dds [--mip 0] [--layer 0]
python -B $S/n3_g1t.py encode <模板>.g1t <同格式同尺寸>.dds --output new.g1t
python -B $S/n3_g1t_resize.py <模板>.g1t <新尺寸>.dds --output new.g1t
```

- `n3_textures.py`：忍者上衣贴图组 0 的四个槽：COLOR `0x8b541440` 换成 4096 BC7 图集（服装、头发 / 脸、身体皮肤 2×2，UV 覆盖之外用 push-pull 填充），NORMAL 平坦 (128,128,255)、SHADING 原版均值 (10,10,10,160)、49 号槽 (0,0)；texconv 压缩后用 `n3_g1t.py dds` 读回和 PNG 比较，平均差写进 `report.json`。
- `n3_g1t.py`：G1T v0066、存储类型 3（64 KB tile 逐块 zlib + 线性 mip 尾）：`info`、`dds`（解成线性 DX10 DDS）、`encode`（模板 + 同格式同尺寸同 mip / 层数的 DDS，重新分 tile、重新压缩）、`constant`（每个 mip、每层一个颜色；BC1 / BC4 / BC5 / BC7 / 未压缩 / 浮点）。只改块数据、块表和文件大小，写完重新解析比对，从不覆盖已有文件。格式说明见 [G1T 格式](../../games/nioh-3/G1T_FORMAT.md)（项目原来的 `tools/N3_G1T_FORMAT.md`，`n3_g1t.py` 的说明里仍写着旧位置）。
- `n3_g1t_resize.py`：以单贴图平面 G1T 为头模板，按新尺寸重建 tile / 尾布局（BC 的 mip 到 4×4 为止），读回逐 mip 比对后写出。图集从 2048 模板放大到 4096 就用它。

### 5. 注册表、计数、贴图表、塌缩

```powershell
python -B $B/n3_registry.py ninja                 # → g1m/0x5583ad7d.bin（物理注册表）、g1m/0x5c3826bd.bin（每材质计数）
python -B $B/n3_registry.py samurai               # → g1m/0xedd65b47.bin、g1m/0xf48ad487.bin；[--g1m <模型>] [--no-counts]
python -B $S/collapse_set.py <输出目录> 0x4ba258df 0xb24cac84 0x7c857e61 … --from "$W/orig" <其他目录>
python -B $S/ktid_repoint.py $Pkg <KTID> <输出文件>.ktid 0=<G1T 哈希> 1=<G1T 哈希> …
python -B $S/ktid_setref.py $Pkg <KTID> <输出文件>.ktid <槽>=<对象哈希> …
```

- `n3_registry.py`：在原版物理注册表（类型 0xB340861A）末尾登记构建好的模型的 type-4 条目（按 ONUN 顺序的 (x, id)，x = 同材质条目里的序号，材质来自条目的 MESH_LOD 类型 2 组）；每材质计数（类型 0x56EFE45C）的每条记录改成模型实际的子网格数和顶点缓冲数。原版注册表已有 type-4 条目、某个材质没有子网格时拒绝。
- `collapse_set.py`：从第一个有 `<哈希>.g1m` 的目录取原版，用 `g1m_tool.py hide --all` 把所有三角形压成零面积写进输出目录（输出目录里已有的同名文件会先删掉，与原脚本相同）。
- `ktid_repoint.py`：KTID 槽改指别的 CharacterEditor 对象，按对象的贴图哈希查找（目标贴图必须已是某个对象的第一个值）；`ktid_setref.py`：直接写（槽 → 对象）。两者都从 `root.rdb.original` 读原版表，输出文件已存在时拒绝。

### 6. 安装（测试机）

```powershell
python -B $S/n3inject.py install $Pkg <覆盖文件目录> [--fdata 0x4b415249]
python -B $S/n3inject.py verify  $Pkg <覆盖文件目录>
python -B $S/n3inject.py restore $Pkg
```

覆盖文件目录里只认 `0x<8 位哈希>.<扩展名>`。每次安装都从 `.original` 备份重新生成；新记录保留原记录的类型、entry type 和参数块，新容器里的条目保留原条目的参数块。`n3inject.json` 记下写出的 `root.rdb` / `root.rdx` 的哈希：游戏后来换掉了它们（更新、校验文件），安装改为备份游戏当前的文件，卸载也不再把过期的备份写回去。`verify` 通过 `root.rdb` 解出每个覆盖逐字节比较，并列出意外变化的记录；本案例的输出是 `records changed: 33 (unexpected: 0)`。游戏必须关闭。

### 7. 发行包安装器

```powershell
python $S/karin_install.py install   "<游戏目录>" --data "<发行包目录>"     # 发行包里：python karin_install.py install "<游戏目录>"
python $S/karin_install.py verify    "<游戏目录>" --data "<发行包目录>"
python $S/karin_install.py uninstall "<游戏目录>" --data "<发行包目录>"
```

`karin_install.py`：把 `files\`（两件上衣、注册表、计数、贴图、贴图表）和 `collapse.txt` 列的 13 个原版模型（从玩家自己的游戏数据读出后塌缩，包里不带原版副本）放进 `staging\`；要替换的每个原版资源必须与 `vanilla.json`（v2.0.0.2 原版的 sha256）一致，暂存的每个文件必须与 `package.json` 一致，然后调用 `n3inject.py install`。版本不符时在暂存之前停下（这时已经做了 `.original` 首次备份，内容与当前文件相同）。`configs/collapse.txt`、`configs/vanilla.json` 是本案例的这两份清单（只有资源哈希和 sha256）；`package.json` 和 `files\` 是构建产物，不在本包里。发行包布局（安装器旁边是 `tools\`、`files\`）不需要 `--data`，行为与原脚本相同。

### 8. 存档外观（换装器）

```powershell
$Save = "$env:LOCALAPPDATA\KoeiTecmo\NIOH3\Savedata\<SteamID64>\SAVEDATA00\SAVEDATA.BIN"
python -B $S/n3_miaomiao.py                                   # 图形界面：扫描默认存档目录，选中后改外观 / 改回 / 从备份恢复
python -B $S/n3_miaomiao.py inspect $Save                     # 账号、等级、保存时间，两种流派五个部位的外观
python -B $S/n3_miaomiao.py apply $Save --out new.bin         # 写到另一个文件；--in-place 直接改（先备份到旁边的 MiaomiaoBackups\）
python -B $S/n3_miaomiao.py clear $Save --in-place            # 五个部位改回「显示身上的装备」
python -B $S/n3_miaomiao.py restore $Save <MiaomiaoBackups\…json>
```

`n3_miaomiao.py`：解密 `SAVEDATA.BIN`（《仁王》1 代的自定义 S 盒 AES-128-CTR，存档体子密钥在解密后的头 0x49 起），核对头、校验和和外观设置记录 `0xCE1DB6CF` 的结构，
把武士、忍者两条里下标 32–36（头、胸、手、腰、腿）写成 `KARIN_TARGETS`，重算校验和，只把改动字节的差量异或进原密文。写出前重新解密复查；改动超出这些字节就拒绝。
`--in-place` / 图形界面：游戏在运行就拒绝；先写备份和 JSON 记录（前后 sha256），用同目录临时文件替换；`restore` 核对当前存档仍是那次修改的结果，否则拒绝。
格式、实机证据和已否定的做法见 [存档与外观设置](../../games/nioh-3/SAVE_AND_APPEARANCE.md)。项目里用 PyInstaller 打成单文件 EXE 发给玩家（构建脚本不在本包里）。

## 伊切尔（由 PMX 转换的 FBX）

源是尘白禁区伊切尔的 MMD 模型转成的 FBX（`尘白.fbx`），同目录有原 PMX 和贴图 PNG。FBX 只有一个网格，24 个 PMX 材质按贴图并成了 7 个，姿势改成了 T 字，没有尾巴网格。案例、实机结果见 [伊切尔案例](../../games/nioh-3/cases/ICHEL.md)。

```powershell
$env:N3_BUILD = "<伊切尔的工作目录>"; $W = $env:N3_BUILD; $I = "$S/n3ichel"
$Raw = "<FBX 导出目录>"; $Model = "<PMX 和贴图所在目录>"
& $Blender --factory-startup --background --python $S/blender/ko_extract_source.py -- "<尘白.fbx>" $Raw
& $Blender --factory-startup --background --python $B/blender_shapekeys.py -- "<尘白.fbx>" $Raw
python -B $I/ichel_source.py $Raw $Model            # → source/：13 个部位网格、改名的人形骨、拆左右的表情键
python -B $I/ichel_conform.py                       # → conformed.npz、conform.json
python -B $I/ichel_physics.py "<伊切尔的 PMX>"        # → physics.json
python -B $B/n3_face.py                             # → face.json
python -B $I/ichel_build.py textures                # → atlas_uv.json、g1t/
python -B $I/ichel_build.py g1m ninja               # 默认 --physics --collide --face；samurai 同样
python -B $I/ichel_build.py registry ninja          # samurai 同样
python -B $B/n3_validate_g1m.py "$W/g1m/0x5548953f.g1m" "$W/orig/0x5548953f.g1m" --layout-changed --physics   # 武士同样
python -B $C/swing.py "$W/g1m/0x5548953f.g1m" 30 --png swing.png; python -B $C/facecheck.py 0x5548953f <脸的子网格>
```

- `ichel_source.py <FBX 导出目录> <模型目录>`：每个 FBX 三角形在同一张贴图内按 UV 中心（位置只作弱的平局判据，FBX 改成了 T 字姿势，只有躯干对得上）对回原 PMX 的三角形，按 PMX 材质拆成 `MESHES`：脸（仍叫 `Body`，`n3_face.py` 认这个名字）、头发、皮肤、衣服、颈饰、两种袖子、裙子、内裤、腿环、靴子、兽耳、头饰。半透明叠加层（`眼睛1`、`表情`）和碰撞代理 `Cylinder` 不放。人形骨改成 `n3_conform` 认的名字，补指尖骨（`<手指>Distal_end`）；胸口饰件 u 在 (1, 1.23] 的整三角形减 1，其余越界角夹到 [0, 1]。表情键：脸的 MMD 表情，加上按 x 正负拆左右、按 `n3_face.py` 的键名命名的 `blink_L/R`、`mayu_up_L/R`、`mayu_down_L/R`、`kuchi_A`、`kuchi_smile_1_L/R`。
- `ichel_conform.py`：`n3_conform.py` 的改写，区别是网格名、缩放（默认让她的 Neck 落在游戏颈骨的高度，约 100：模型是真人比例的米）和没有尾巴。仿射把 T 字的手臂转成游戏的 A 字；物理骨先归到最近的人形祖先，链权重由 `ichel_physics.py` 给。裙子没有骨，按 Karin 的做法越往下摆越跟腿，下摆外推一点。
- `ichel_physics.py <pmx>`：PMX 里刚体模式 1 / 2 的骨骼族（`FAMILIES`：后发、侧后发、前侧发、胸前发束、呆毛、小辫、兽耳、泡泡袖、裙侧丝带、背后蝴蝶结）各成链，点 = 骨骼头加一段延长的尖端，用该骨顶点的拟合映射到游戏空间（`n3_physics.point_fit`）；模板、挂接骨、碰撞组见脚本的说明。尾巴骨和胸部骨不用。
- `ichel_build.py textures | g1m <ninja|samurai> [flags] | registry <ninja|samurai>`：换上她的图集布局（`ATLAS`）后调用共用的 `n3_textures.py`、`n3_build_g1m.py`（`DROP` 为空）、`n3_registry.py`，其余与 Karin 相同。
- `pmx_read.py <file.pmx> [out.json]`：最小的 PMX 2.0 / 2.1 读取（头、材质、骨骼、表情名、刚体、关节；`geometry()` 给位置、UV、面和每面材质），`ichel_source.py`、`ichel_physics.py`、`lenko_*` 都用它。

## Lenko（直接读 PMX）

源是 MMD 模型 `Lenko06.pmx`（Kinsama）和 `tex/` 下的 10 张颜色贴图，不经 Blender。用户的要求和每一版的取舍见 [Lenko 案例](../../games/nioh-3/cases/LENKO.md)。

```powershell
$env:N3_BUILD = "<Lenko 的工作目录>"; $W = $env:N3_BUILD; $L = "$S/n3lenko"
$Model = "<模型目录>"                                 # Lenko06.pmx 和 tex/
python -B $L/lenko_source.py $Model                 # → source/（source.json / .npz、shapekeys.json / .npz、source_report.json）
python -B $L/lenko_conform.py                       # → conformed.npz、conform.json
python -B $L/lenko_physics.py "<Lenko06.pmx>"       # → physics.json
python -B $L/lenko_coll.py                          # 链点变了才需要：打印碰撞组常量，抄进 lenko_build.py
python -B $B/n3_face.py --vanilla-lids              # → face.json
python -B $L/lenko_build.py textures                # → atlas_uv.json、g1t/
python -B $L/lenko_build.py g1m ninja               # 默认 --physics --collide --face；samurai 同样
python -B $L/lenko_build.py registry ninja          # samurai 同样
python -B $B/n3_validate_g1m.py "$W/g1m/0x5548953f.g1m" "$W/orig/0x5548953f.g1m" --layout-changed --physics   # 武士同样
python -B $C/swing.py "$W/g1m/0x5548953f.g1m" 30 --png swing.png; python -B $C/blinkgap.py "$W/face.json"
python -B $L/lenko_view.py view.png [--conformed] [--ylim 80 120] [--hide hair,Body]   # 正 / 侧 / 背三视图
python -B $L/lenko_pmx.py "<Lenko06.pmx>"            # 读一遍：顶点、面、权重和的范围、表情数
```

外套、短裙和眨眼的检查（`layer_swing.py`、`coat_skirt_gap.py`、`radial_gap.py`、`face_render.py`、`readback_blink.py`、`vanilla_blink.py`）见[离线检查](#离线检查)。

- `lenko_pmx.py`：完整的 PMX 2.0 读取：几何、蒙皮权重、每面材质、顶点表情的位移，加上 `pmx_read.parse` 的元数据。
- `lenko_source.py <模型目录>`：PMX → 构建读的源格式。坐标 (x, y, z)_Blender = (x, z, y)_PMX 是镜像，所以三角形顶点顺序反过来；v 翻转；单位保持 MMD 单位，贴合按颈高缩放。外套版（PMX 默认），`Lenko_coat_Pig_l` 不放。
  - 外套缩短（`shorten_coat`）：腰带下沿 `Y_BELT` 以下、手臂权重 < 0.5 的外套顶点 y' = `Y_BELT` − k (`Y_BELT` − y)，外套物理骨同样处理；k 取「每个 15° 扇区外套下摆至少比裙摆低 `HEM_COVER`」的最小值（最大 1），偏离中位数超过 `HEM_OUTLIER` 的裙摆扇区不算。两只口袋小猪绕自己的中心按 k 缩小。
  - 网格按材质和三角形的主导骨族拆成 `MESH_ORDER` 的 12 个；腰带上那条长丝带按连通块整块分到 `ribbon`。
  - 骨：人形骨改名（腿部皮肤刷在 D 骨上，D 骨用腿的名字，FK 腿骨的权重并过去），补指尖骨，胸部物理骨 `Chest*` 改叫 `Bust*`。
  - 表情键：Body 上的每个顶点表情，加上拆左右的键；`blink_L/R` 来自 `bone_blink` 处理过的まばたき：游戏的眨眼姿势抬不动下眼睑，于是把闭合线按下缘的抬升量往下移（`CLOSE_*`）。
- `lenko_conform.py`：用 `ichel_conform` 的函数。网格分工：头上的、身体权重迁移的（skin、clothes、legwear、belt）、保留自身权重的（skirt、ribbon、tie、coat）；皮肤和衣服用手的规则（手套跟手），外套用袖子的规则；裙摆向腿过渡用 legwear，外推 `SKIRT_PUSH`。`drape_coat_back`：外套背面腰带以下按（方位 2°，高 0.5 cm）的格子往里收，直到最内层离短裙 / 丝带 `DRAPE_GAP`，不小于腰带处外套的半径，方位 100°–130° 渐入（`BACK_AZ`），纵向 `DRAPE_RAMP` 内渐入；袖子和口袋小猪不动。
- `lenko_physics.py <pmx>`：动态刚体骨从根沿唯一的动态子骨成链（`KINDS`：头发、长发、头顶饰物、裙子、领带、胸部）。超过 `LONG_HAIR` 的头发链细分到每节 ≤ `SEG_MAX`，用 `longhair` 模板；胸部链只带作者权重的 `BUST_SHARE`。外套骨不用：腰带以下的外套顶点取最近短裙表面点的权重（`coat_follows_skirt`），两层一起摆。
- `lenko_coll.py`：把借来的原版碰撞组按她的身体重拟合（绑定姿势）：保留原版图元的骨和旋转，只改中心和半轴；固定种子的随机搜索，约束是该组所有链的非根点都在外 `CLEAR`；短裙组再加两个臀部椭球。打印 `lenko_build.py` 的常量（`LENKO_*_RESIZE`、`LENKO_BUTT`），要 40 秒左右。
- `lenko_build.py textures | g1m <ninja|samurai> [flags] | registry <ninja|samurai>`：她的图集布局（`REGIONS`，按贴图文件分区，共用贴图的材质合并覆盖再 push-pull），往 `n3_g1m_physics.COLLISION_SETS` 登记 `lenko_skirt` / `lenko_tie` / `lenko_hair`（带 `resize`），往 `TEMPLATE_BLOCKS` 放 `longhair` 参数块（原版 50 cm 长发 `0x6da3fe6e` type-4 条目 0，不在 `orig/` 里），然后调用共用的步骤。
- `lenko_view.py <out.png> [--conformed] [--ylim lo hi] [--hide mesh,…]`：源模型（`source/`）或 `conformed.npz` 的贴图平涂三视图，每个三角形取 UV 中心处的颜色。

## 定位与统计

```powershell
python -B $S/census.py $Pkg                                  # root.rdb 按类型计数、外部资源、模型总大小
python -B $S/missing.py $Pkg                                 # rdx 里有、目录里没有的容器，以及其中的资源类型
python -B $S/ktid_find.py $Pkg 0x8b541440                    # 引用这些贴图的所有 KTID（经 CharacterEditor 对象），连同完整槽表
python -B $S/alias_ktid.py $Pkg 0xd956e4a2 --ktid <KTID> … --tex <G1T> …   # TextureAlias 对象里的 KTID（染色变体）
python -B $S/alias_entry.py $Pkg <对象库哈希> <值> …           # 含这些值的 kidsobjdb 条目和引用它们的条目
python -B $S/raw_ref.py $Pkg all|<类型,…> <哈希> …            # 哪些资源原样包含这个 4 字节值
python -B $S/slot_defaults.py $Pkg [槽类型 …]                 # 每种材质槽最常用的小号默认贴图及指向它的对象
python -B $S/rec_params.py $Pkg <哈希> …                      # root.rdb 记录和 fdata 条目的参数块
python -B $S/find_variant.py reads.json <阶段> $Pkg <参考>.g1t <工作目录> --texconv <texconv.exe>   # 同格式同尺寸、alpha 图案最像的贴图（染色变体）
python -B $S/dump_names.py $Pkg names.txt [类型]              # NameDatabaseFile 里的可打印字符串
python -B $S/g1m_summary.py "<目录>/*.g1m"; python -B $S/g1m_subs.py <file>.g1m; python -B $S/g1m_render.py out.png <file>.g1m …
python -B $S/face_bones.py <file>.g1m [最小骨号]              # 每根骨的权重质量和加权质心
python -B $S/nuno4.py <file>.g1m [--dump]                     # ONUN（NUNO 0036）子块，type-4 条目逐字段
python -B $S/fpose.py <file>.g1fpose --pose 41; python -B $S/fpose.py <file>.g1frani
python -B $S/g1a.py <file>.g1a|<哈希> [--package $Pkg] [--bones 0-30] [--frames]; python -B $S/g2a.py …   # 动画曲线的值域
python -B $S/tex_stats.py <工作目录> <file>.g1t … --texconv <texconv.exe>   # mip 0 每个通道的均值 / 标准差 / 范围
python -B $S/peinfo.py Nioh3.exe; python -B $S/patscan.py Nioh3.exe "E8 ? ? ? ? 85 C0"   # PE 节和导入表；按特征码找偏移（只读文件）
```

## 离线检查

```powershell
python -B $C/swing.py "$W/g1m/0x5548953f.g1m" 30 --png swing.png     # 绑定姿势漂移；每条链绕根转动时只有它自己的顶点在动；侧视 / 正视图
python -B $C/facecheck.py 0x5548953f 25 [0x7c836955] --png face.png   # 脸所在子网格按面部姿势蒙皮，各姿势的最大位移和渲染
python -B $C/blinkgap.py "$W/face.json"                               # 满眨眼 / 张嘴时拟合位移沿目标方向的比例、垂直误差、缝
python -B $C/fit_butt3.py 2 0.3 102                                   # 在胯骨上拟合一对镜像椭球（build24 的 KARIN_HIPS）
python -B $C/coll_cover.py                                            # legs 碰撞组对 Karin 和原版身体臀部的覆盖
python -B $C/lloc_dump.py 0x6a0d18db 0xd5d385f9                       # 原版模型的 LLOC 碰撞体，28 个字逐个
python -B $C/diff24.py <旧>.g1m <新>.g1m                              # 两个构建之间变了哪些块和 FM1G 字，新碰撞组的世界坐标
```

`swing.py` 的链表从 `<N3_BUILD>\g1m\build_report[_samurai].json` 读（文件名含 `5548953f` 时用忍者的）。`facecheck.py` 的模型从 `<N3_BUILD>\g1m\` 读，第二个参数是脸所在的子网格（build24：忍者 25、武士 27，见 `build_report[_samurai].json` 的 `skirt`）。`fit_butt3.py` 的网格搜索要几分钟。

Lenko 的外套 / 短裙和眨眼用的检查（lenko1–lenko4）：

```powershell
python -B $C/coat_skirt_gap.py                                         # 静止时每个（方位, 高度）格里短裙最外的半径和外套最内的半径
python -B $C/radial_gap.py "$W/conformed.npz" [<另一个>.npz …]          # 背后（|方位| ≥ 100°、y < 108）外套顶点离附近短裙 / 丝带的径向间隙分布
python -B $C/layer_swing.py                                            # 裙链绕根转动（整体甩、抬腿、后推、独立乱甩）时外套是否穿到短裙里
python -B $C/face_sim.py                                               # 按 face.json 摆游戏面部姿势：眼睑沿 blink 目标的行程、眉毛位移
python -B $C/face_render.py face.png "<模型目录>"                       # 脸的贴图渲染：静止、41+42、MMD 目标、27+28、39+40
python -B $C/readback_blink.py rb.png "$W/g1m/0x5548953f.g1m" "<模型目录>"   # 从成品 g1m 解出脸的权重再模拟眨眼，与 face.json 比较
python -B $C/vanilla_blink.py                                          # 原版女性头在各姿势、各表情动画眨眼帧下的上眼睑闭合比例
```

- `coat_skirt_gap.py`、`layer_swing.py`、`radial_gap.py` 读贴合后的 `skirt`、`coat`（`radial_gap.py` 还有 `ribbon`）网格，是 Lenko 的网格名；`layer_swing.py` 的链权重从 `physics.json` 读，`Skirt` 开头的链才转。`layer_swing.py` 的两个可选参数 `[trials] [max deg]` 原脚本读了但没用，场景是固定的。
- `layer_swing.py` 判穿过的办法：带链权重、|x| < 24 的外套顶点里，静止时在最近短裙采样点外 0.3 cm 以上、离它不到 4 cm 的那些，转动后沿该点法线的有向距离变成负的就算穿过；最后几行是后推 30° 时穿过的点和它们的权重来源（原脚本的调试输出）。
- `face_sim.py` 是 `face_render.py`、`readback_blink.py` 的公共部分，被导入时也打印它的表。`readback_blink.py` 导入 `face_render.py` 时，后者先把自己的 5 栏图写进同一个输出文件，再被 2 栏图（face.json 模拟 | g1m 读回）覆盖，与原脚本相同。
- `vanilla_blink.py` 读 `orig/0xb24cac84.g1m` 和 `face/` 下的姿势库、`*.g1frani`：本机的输出是 27/28 → 0.82、39/40 → 0.85（相对 41/42），即 `n3_face.py --vanilla-lids` 用的比例；待机脸 `0x5ca044ef` 的眨眼帧在原版脸上闭到 1.02。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/g1m_tool.py`、`g1t_tool.py`、`ktdata.py` | KT 引擎格式库，与浪人崛起便携包相同：G1M / G1H 读取、原地隐藏子网格、原生绑定检查；G1T 头、DX12 64 KB tile 与线性互转、常量填充（浪人崛起的存储类型 0 / 1，仁王3 的存储类型 3 用 `n3_g1t.py`）；`root.rdb` / `root.rdx` / fdata 提取、kidsobjdb、KTID 槽表 |
| `scripts/n3_g1t.py`、`n3_g1t_resize.py` | 仁王3 G1T v0066 存储类型 3 的解码、编码、常量填充；换尺寸重建 |
| `scripts/n3inject.py` | 资源表注入的安装 / 校验 / 还原（见上） |
| `scripts/karin_install.py` | 发行包安装器：原版 sha256 核对、从玩家数据生成塌缩模型、暂存核对、调用 `n3inject.py` |
| `scripts/n3_miaomiao.py` | 换装器：存档加解密、校验和、外观设置记录的读写，图形界面和命令行，备份 / 回滚 |
| `scripts/nuno4.py` | ONUN 读取，type-4 条目的完整布局（`n3_g1m_physics.py`、`n3_registry.py` 用它） |
| `scripts/fpose.py` | g1fpose（面部姿势库）和 g1frani（姿势权重动画）读取（`n3_face.py` 用它） |
| `scripts/g1a.py`、`g2a.py` | G1A（版本 0042）/ G2A（版本 0040）动画读取，Joschuka 的 Project-G1M 的移植 |
| `scripts/collapse_set.py`、`ktid_setref.py`、`ktid_repoint.py` | 塌缩一组模型；改 KTID 槽 |
| `scripts/etw_reads.py`、`phase_diff.py`、`phase_only.py`、`find_variant.py` | 按阶段统计游戏读了哪些资源；找染色变体 |
| `scripts/ktid_find.py`、`alias_entry.py`、`alias_ktid.py`、`raw_ref.py`、`slot_defaults.py`、`model_refs.py` | KTID / kidsobjdb / TextureAlias 的反查 |
| `scripts/extract_many.py`、`census.py`、`missing.py`、`dump_names.py`、`rec_params.py` | 取原版、统计 `root.rdb`、看参数块 |
| `scripts/face_bones.py`、`g1m_summary.py`、`g1m_subs.py`、`g1m_render.py`、`tex_stats.py` | 模型和贴图的报表与快速渲染 |
| `scripts/peinfo.py`、`patscan.py` | 只读的 PE 检查（节、导入表、特征码偏移），分析崩溃地址时用 |
| `scripts/blender/ko_extract_source.py` | Blender：FBX → `source.json` / `source.npz` / 贴图（构建第 1 步，浪人崛起项目的脚本） |
| `scripts/n3build/blender_shapekeys.py` | Blender：形态键位移 → `shapekeys.npz` / `shapekeys.json` |
| `scripts/n3build/n3_common.py` | 构建公共层：`N3_BUILD`、读原版模型和源模型（含 `EXTRA_SHAPE_KEYS` 按高度遮罩的形态键）、骨架、坐标轴转换、权重量化 |
| `scripts/n3build/n3_conform.py`、`n3_physics.py`、`n3_face.py` | 贴合与权重、骨链与链权重、面部骨权重 |
| `scripts/n3build/n3_build_g1m.py`、`n3_g1m_physics.py` | 写 G1M；SM1G 关节、ONUN type-4（`TEMPLATE_BLOCKS` 补 `orig/` 里没有的模板）、LLOC 碰撞组（含 `KARIN_HIPS` 臀部椭球，`resize` 重拟合原版椭球）、FM1G 统计 |
| `scripts/n3build/n3_validate_g1m.py` | 构建结果的独立读回校验 |
| `scripts/n3build/n3_registry.py`、`n3_textures.py` | 物理注册表与每材质计数；图集与常量贴图 |
| `scripts/n3ichel/ichel_source.py`、`ichel_conform.py`、`ichel_physics.py`、`ichel_build.py` | 伊切尔：FBX 导出按原 PMX 拆网格 → 源格式；贴合；PMX 刚体骨链；她的图集布局下的共用构建步骤 |
| `scripts/n3ichel/pmx_read.py` | PMX 2.0 / 2.1 的元数据和几何读取（伊切尔、Lenko 共用） |
| `scripts/n3lenko/lenko_pmx.py`、`lenko_source.py` | Lenko：完整的 PMX 读取；PMX → 源格式（外套缩短、网格拆分、骨改名、表情键与眨眼闭合线） |
| `scripts/n3lenko/lenko_conform.py`、`lenko_physics.py`、`lenko_coll.py` | 贴合（含背面外套贴向短裙）；骨链（长发细分、胸部、外套跟随短裙）；碰撞组重拟合 |
| `scripts/n3lenko/lenko_build.py`、`lenko_view.py` | 图集布局、碰撞组和 `longhair` 模板登记后的共用构建步骤；源模型 / 贴合结果的三视图 |
| `scripts/checks/*.py` | 离线检查（见上） |
| `configs/collapse.txt`、`configs/vanilla.json` | 本案例的塌缩清单和 33 个被替换资源的 v2.0.0.2 原版 sha256 |

## 输出与本机信息

- **中间结果：** `source/`、`conformed.npz`、`physics.json`、`face.json` 来自源模型；`orig/`、`tex/`、`face/` 是游戏数据；`g1m/`、`g1t/` 是构建产物。这些都不要收进本仓库。`build_report*.json` 里有模板和输出的 sha256，没有本机路径；`n3_build_g1m.py` 的输出行打印输出文件的完整路径。
- **发行物：** 发行包只带 20 个自制文件和安装器，13 个塌缩模型由安装器从玩家的数据生成。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时要按新模型重写：

- `n3_common.py`：`CHEST`、`BODY`、`EXTRA_SHAPE_KEYS`（Karin 的形态键名和高度）；
- `n3_conform.py`：网格名（`HEAD_MESHES`、`TRANSFER_MESHES`、`skirt`、`tail`、`pullover`、`body_2`）、`TRANSFER_DIST`、`SKIRT_FMAX` / `SKIRT_PUSH`、`N3_HEAD_SCALE` 默认 150；
- `n3_physics.py`：`RIG`（Karin 的弹簧链前缀 → 模板和碰撞组）、`RIG_ANCHOR`，`--geometry` 的 `CHAINS`、`TWIN_MIN_Y`；
- `n3_face.py`：`POSES` / `EXTRA`（游戏姿势 → Karin 的形态键名和量）、`DRIVERS`、`MAX_ROT`、`RIDGE`；
- `n3_build_g1m.py`：`ATLAS`（Karin 的材质名 → 图集区域）、`DROP`、`ARM_ROOTS`；`n3_g1m_physics.py` 的 `KARIN_HIPS`（`checks/fit_butt3.py` 在 Karin 身上拟合的）；
- `n3_textures.py` 的常量值，`configs/collapse.txt`、`configs/vanilla.json`；`checks/coll_cover.py`、`fit_butt3.py` 的高度范围；
- `n3_miaomiao.py` 的 `KARIN_TARGETS`（测试存档的外观设置，换了 Mod 的目标模型就要换成对应装备的 ID）。

伊切尔、Lenko 的值同样只对各自的模型有效：

- `ichel_source.py`：`PMX`（文件名）、`MESHES`、`LEFT_OUT`、`FBX_TEXTURE`、`PMX_TEX_INDEX`、骨名映射、`SIDE_RAMP`；`ichel_conform.py`：网格名、`TRANSFER_DIST`、`SKIRT_FMAX` / `SKIRT_PUSH`；`ichel_physics.py`：`FAMILIES`、`ANCHOR`；`ichel_build.py`：`ATLAS`；
- `lenko_source.py`：`PMX`、`Y_BELT`、`HEM_COVER`、`HEM_OUTLIER`、`SIDE_RAMP`、`CLOSE_*`、`DROP_MATERIALS`、`FIXED`、`MESH_ORDER`、`LONG_RIBBON`；`lenko_conform.py`：网格分工、`SKIRT_PUSH`、`DRAPE_GAP`、`BACK_AZ`、`DRAPE_RAMP`、`CELL`；
- `lenko_physics.py`：`KINDS`、`LONG_HAIR`、`SEG_MAX`、`BUST_SHARE`、`COAT_RAMP`、`COAT_KEEP`、`CROSS_MAX`；`lenko_coll.py`：`SETS` 的搜索范围、`MARGIN`、`BUTT_*`；`lenko_build.py`：`REGIONS`、`LENKO_*` 碰撞常量；
- `n3_face.py` 的 `VANILLA_LIDS` / `VANILLA_LIDS_PRIORITY`（比例本身是原版头量出来的，优先级是在 Lenko 上试出来的）；`checks/layer_swing.py`、`coat_skirt_gap.py`、`radial_gap.py` 的网格名、轴心和高度 / 方位范围（`layer_swing.py` 的轴心 z = −1.48 是写死的）。

以下随游戏版本变化（`build-sensitive`），游戏更新后要重新核对：

- 资源哈希：两件上衣、注册表、计数、贴图、KTID、要塌缩的模型（`n3_build_g1m.TARGETS`、`n3_registry.REGISTRY`、`n3_textures.CONSTANTS`、`n3_common.CHEST` / `BODY`、`n3_face.SAME_BIND` / `POSE_LIB`、`n3_g1m_physics.TEMPLATES` / `COLLISION_SETS`）；
- `lenko_build.py` 的 `longhair` 参数块（原版 `0x6da3fe6e` 的 type-4 条目 0）和三个碰撞组的原版底（`0x6a0d18db` 条目 1、`0x5548953f` 条目 0、`0xd5d385f9` 条目 0）；`VANILLA_LIDS` 的 0.82 / 0.85 是在 v2.0.0.2 的原版女性头和姿势库上量的；
- 两件上衣的子网格布局（`TARGETS` 的 rest 子网格）、玩家骨号、面部骨号 400–737、type-4 / type-5 id 的命名空间、FM1G 的统计偏移、G1T v0066 的头字段；
- `vanilla.json`：v2.0.0.2 原版的 sha256，版本一变安装器就拒绝。

## 已验证与边界

- **实机。** 结论来自项目用原脚本构建的 build7–build24（[验证与发布](../../games/nioh-3/VALIDATION_AND_RELEASE.md)、[Karin_Original 案例](../../games/nioh-3/cases/KARIN_ORIGINAL.md)）：build21 关卡内物理由用户确认，build23 由用户确认；build24（臀部碰撞椭球）由发行包装进测试机，`verify` 33/33，实机效果待用户确认。伊切尔（ichel1 主菜单外观由用户确认，关卡内没测）和 Lenko（lenko1–lenko4 依次装进测试机，各版的实机反馈和修改）见 [伊切尔案例](../../games/nioh-3/cases/ICHEL.md)、[Lenko 案例](../../games/nioh-3/cases/LENKO.md)。
- **伊切尔 / Lenko 的便携副本（2026-11-03，离线）：** 原脚本和便携脚本各在项目构建目录的一份副本上跑完整条链，Lenko：`lenko_source` → `lenko_conform` → `lenko_physics` → `n3_face --vanilla-lids` → `lenko_build` textures / g1m ×2 / registry ×2 → `n3_validate_g1m` ×2；伊切尔：`ichel_source`（用项目里已有的 Blender 导出）→ `ichel_conform` → `ichel_physics` → `n3_face` → `ichel_build` 同样 5 步 → `n3_validate_g1m` ×2。两条链各 11 步的退出码、标准输出和工作目录的 104 个文件都相同（npz 按数组比较），重新写出的文件也与项目构建目录里 lenko4 / ichel1 的现有文件逐字节相同。`lenko_coll.py`、`lenko_view.py`、`lenko_pmx.py`、`pmx_read.py` 和 7 个新检查在 Lenko 的数据上各跑一次，标准输出和写出的 4 个文件（3 张图、1 个 json）相同。Blender、游戏和测试机都没有重跑。
- **便携版本身只做了离线核对（2026-11-01）：** 在本机用原脚本和便携脚本在同一份输入上运行、逐字节比较：构建链 10 步（贴合 → 物理 → 表情 → 两件上衣 → 校验 → 注册表 → 贴图）的 22 个输出相同，并与发行包 build24 的 10 个对应文件逐字节相同；构建链的其余参数 10 步相同；7 个离线检查 8 次运行的输出（含 3 张渲染图）相同；27 个定位 / 报表脚本 32 次运行的输出和 17 个写出的文件相同；`karin_install.py` 在发行包布局下「拒绝 → 安装 → 校验 → 卸载」四步与原件相同。Blender、游戏和测试机都没有重跑。详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。`Nioh3Tools` 不需要游戏、Blender、源模型或 texconv：合成的 `root.rdb` / `root.rdx` / fdata 上 `n3inject.py` 的安装 → 校验 → 还原（带空格的路径、参数块保留、过期备份的两条路径），`karin_install.py` 拒绝版本不符的原版并且不安装、从便携包和发行包两种布局安装 / 校验 / 卸载；合成 G1T v0066 存储类型 3 的解码、编码往返（逐字节）、常量填充和换尺寸；`n3_g1m_physics.lloc_entry_bytes` 追加椭球和 `new_lloc`；`n3_registry.py` 的注册表与计数；定位脚本、ETW 统计和阶段比较；`N3_BUILD` / `N3_VRM` 缺失时的报错；构建链（含 `n3ichel/`、`n3lenko/`）和检查的 `--help`；PROVENANCE 与可移植性。没装 numpy / scipy 时要它们的项跳过；`karin_install.py` 那项只在 Windows 上跑。
- **换装器（2026-11-02）：** 项目里同一份源码在测试机上实测（agent，`runtime-load-pass`）：游戏里把外观换掉 → `apply --in-place` → 重进关卡，角色模型恢复显示。
  `Nioh3Tools` 里有它的合成存档测试：已知的头密钥流、加解密往返、`apply` / `clear` 只改五个部位和校验和、结构异常拒绝、命令行 `--in-place` 的备份与 `restore`。
- **测试没覆盖的部分：** 两个 Blender 脚本只做语法检查；换装器的图形界面只在项目里做过启动冒烟测试；`n3_conform.py`、`n3_physics.py` 默认模式、`n3_face.py`、`n3_build_g1m.py`、`n3_textures.py` 以及伊切尔 / Lenko 的步骤和新检查只在本机真实数据上和原脚本比较过，测试里没有合成数据（`n3_face.py --vanilla-lids`、`TEMPLATE_BLOCKS`、`lloc_entry_bytes` 的 `resize` 也一样）；`g1a.py`、`g2a.py` 只测了 `--help`（本机没有动画文件）；非 Windows 系统；其他游戏版本。
- **便携改动：**
  - `n3_common.py` 的 `BUILD` 原来默认是会话临时目录，改为只认 `N3_BUILD`，用到路径时才检查（`BUILD` / `ORIG` 是延迟求值的路径对象）；`n3_physics.py` 写死的 VRM 路径改为 `N3_VRM` / `--vrm`；
  - 没有 argparse 的命令补上了 argparse，位置参数和选项不变；`find_variant.py`、`tex_stats.py` 加 `--texconv`，`swing.py`、`facecheck.py` 加 `--png`；
  - `karin_install.py` 的工具目录在发行包布局下是 `tools\`，否则是脚本所在目录；数据目录加 `--data`；
  - 离线检查里写死的项目和会话目录改为相对脚本的路径和 `N3_BUILD`；
  - 伊切尔 / Lenko（2026-11-03）：
    - `n3ichel/`、`n3lenko/` 的 12 个命令和 7 个新检查补上 argparse，位置参数和选项不变。`ichel_build.py` / `lenko_build.py` 的步骤只接受 `g1m` / `registry` / `textures`，`g1m` / `registry` 缺目标时报用法错误（原来是 IndexError）；`radial_gap.py` 不给文件时报用法错误（原来什么也不做）。`n3_face.py` 新的 `--vanilla-lids` 也进了 argparse；
    - 两个 `*_build.py` 的 `textures` 步骤调用便携版 `n3_textures.py`（它有 argparse）之前把命令行清空；原版 `n3_textures.py` 不读命令行；
    - `ichel_conform.py` 原来没有 `sys.path` 条目（在项目里要用 `PYTHONPATH` 指向 `n3build`），加了相对脚本的 `n3build`；
    - `lenko_coll.py` 在模块级读原版身体之前解析参数；`face_sim.py` 只在直接运行时解析（`face_render.py`、`readback_blink.py` 导入它）；
    - 写死的路径：`face_render.py` 的源模型目录 → `<模型目录>` 参数；`readback_blink.py` 原来从会话目录导入 `face_render.py`，现在从脚本所在目录导入，多一个 `<模型目录>` 参数转给它；`face_sim.py`、`vanilla_blink.py` 的项目 `tools` 路径 → 相对脚本；`layer_swing.py`、`coat_skirt_gap.py`、`vanilla_blink.py` 的 `os.environ['N3_BUILD']` → `n3_common.BUILD`；
    - `layer_swing.py` 原件混用 CRLF 和 LF，便携版统一为 LF；
  - 每个文件保留原来的换行（15 个 CRLF，其余 LF）。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md) 和 [PROVENANCE.json](../PROVENANCE.json)。
- **没有收进本包：** 测试机远程辅助脚本（`tools/remote/*.sh`，以及伊切尔 / Lenko 会话里的上传、暂存、安装脚本）；浪人崛起项目的其他构建脚本（`tools/ko/ronin_original/` 下除 `ko_extract_source.py` 以外）；伊切尔 / Lenko 发行包的 `ichel_install.py` / `lenko_install.py`（与 `karin_install.py` 只差说明里的名字）和打包脚本；会话里的一次性脚本和文本转储（Lenko 会话里还有 `true_gap.py`、`cull_render.py` 等没有收）；源模型、游戏数据、构建产物、发行包（`files\`、`package.json`、`.cmd`、zip）。
- **署名：** G1A / G2A 读取移植自 Joschuka 的 Project-G1M；G1T 存储类型 3 的参照解析器是 MrIkso 的 RDBExplorer；注入方式与 eArmada8 的 yumia_fdata_tools 相同（本包不带它们的代码）。
