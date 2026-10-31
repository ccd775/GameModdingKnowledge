# 仁王3（Nioh 3）便携包

先读 [游戏知识](../../games/nioh-3/README.md) 和 [构建流水线](../../games/nioh-3/BUILD_PIPELINE.md)。资源表注入、G1M、骨架、每材质计数和物理注册表的约定见 [技术合同](../../games/nioh-3/TECHNICAL_CONTRACTS.md)；贴图存储见 [G1T 格式](../../games/nioh-3/G1T_FORMAT.md) 和 [材质与贴图](../../games/nioh-3/MATERIALS_AND_TEXTURES.md)；骨链和碰撞体见 [物理](../../games/nioh-3/PHYSICS.md)；面部骨权重见 [表情](../../games/nioh-3/FACE.md)；崩溃和症状见 [排障手册](../../games/nioh-3/TROUBLESHOOTING.md)；离线 / 实机闸门和发行包见 [验证与发布](../../games/nioh-3/VALIDATION_AND_RELEASE.md)；版本轨迹见 [Karin_Original 案例](../../games/nioh-3/cases/KARIN_ORIGINAL.md)。

这是 Karin_Original 替换仁王3 女性主角的 Mod（测试构建 build7–build24，发行包 build24）实际使用的工具：KT 引擎的格式库（`g1m_tool.py`、`g1t_tool.py`、`ktdata.py`，与浪人崛起便携包 `portable-kits/rise-of-the-ronin/` 的同名文件逐字节相同）、仁王3 的 G1T v0066 存储类型 3 编解码、NUNO type-4 骨链读取、`root.rdb` / `root.rdx` 注入安装器、资源定位和统计脚本、构建链 `scripts/n3build/`、Blender 导出脚本、发行包用的安装器 `karin_install.py`，以及会话里写的离线检查 `scripts/checks/`。

- **游戏版本：** 仁王3 v2.0.0.2（PC）。资源在游戏目录的 `package\`（`root.rdb`、`root.rdx`、`0x<哈希>.fdata`）。
- **加载方式：** `n3inject.py` 改写 `root.rdb` / `root.rdx`：所有覆盖文件不压缩地放进新容器 `0x4b415249.fdata`（`KARI`），`root.rdx` 多一个容器槽，被覆盖的记录改指这个容器。第一次使用时把原表备份成 `root.rdb.original` / `root.rdx.original`。不用 DLL，不改 exe。
- **Blender：** 项目用 4.0.2，后台运行，`--factory-startup`。两个 Blender 脚本（`scripts/blender/ko_extract_source.py`、`scripts/n3build/blender_shapekeys.py`）用 Blender 自带的 Python 和 numpy，参数写在 `--` 之后。
- **texconv：** DirectXTex 的 `texconv.exe`，由用户自备。`n3_textures.py` 用 `<N3_BUILD>\toolchain\texconv.exe`；`find_variant.py`、`tex_stats.py` 用 `--texconv`（默认是脚本旁边的 `texconv.exe`）。
- **Python：** 定位脚本、`n3inject.py`、`karin_install.py` 和三个格式库只用标准库（安装器单独在 Python 3.8+ 上也能跑）。构建链、`n3_g1t.py`、`n3_g1t_resize.py`、`fpose.py`、`g1a.py`、`g2a.py`、`face_bones.py` 和离线检查另需 numpy；`n3_conform.py`、`n3_physics.py`、`n3_face.py` 另需 scipy；`g1m_render.py`、`g1m_subs.py`、`checks/swing.py`、`checks/facecheck.py` 另需 matplotlib；`n3_textures.py`、`find_variant.py`、`tex_stats.py` 另需根目录的 Pillow。`requirements.txt` 钉的版本要 Python 3.12 或更高。本次在 3.14.0、numpy 2.5.2、scipy 1.18.0、matplotlib 3.11.2、Pillow 12.3.0 上测试。
- **只在 Windows 上：** `karin_install.py` 用 `tasklist` 判断游戏是否在运行；texconv 只有 Windows 版。项目在 Windows 上构建，游戏在另一台测试机上。
- **运行位置：** 以下命令都从交接包根目录执行。所有命令都有 `--help`；不带参数的构建步骤（`n3_conform.py`、`n3_textures.py`、`checks/coll_cover.py`）的 `--help` 只打印说明，不会开始处理。

## 环境变量与参数

| 变量 / 参数 | 读的脚本 | 含义 |
| --- | --- | --- |
| `N3_BUILD` | `scripts/n3build/` 下全部构建步骤，`checks/` 下除 `diff24.py` 以外的检查 | 工作目录，布局见下一节。原项目默认用会话临时目录里的 `build\`；便携版没有默认值，用到路径时才检查，没设时报错并说出变量名（`--help` 不需要它） |
| `N3_VRM`（`--vrm`） | `n3_physics.py` 默认模式 | Karin 的 VRM 文件（带 `VRMC_springBone`，由 PhysBone 转换来的 39 条弹簧链）。原脚本写死了源模型目录里的 VRM。`--geometry` 模式不需要 |
| `N3_HEAD_SCALE` | `n3_conform.py` | 源模型整体缩放，默认 150（Blender 米 → 游戏厘米，并让头和游戏的头一样大） |
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

## 构建流程

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
python -B $B/n3_face.py               # → face.json（--extended 另加 27/28、39/40、59/60、160）
```

- `n3_conform.py`：源模型按 `N3_HEAD_SCALE` 缩放并平移到 Karin 的 Neck 落在游戏骨 11 上；头颈刚性，其余人形骨各拟合一个仿射（骨段方向和长度，保持截面），按 Karin 的权重线性混合。权重：Karin 的骨映射到游戏骨（躯干按高度分到脊椎）；贴身网格从原版身体 `0x4ba258df` 最近点迁移（远了淡出，手指保留映射权重，袖子不用手和手指骨）；头、头发、耳朵 → 12，尾巴 → 2，裙子越往下摆越跟最近的腿部皮肤。左右两侧的顶点不能拿另一侧手臂链的权重（按骨架判断）。
- `n3_physics.py`：VRM 的每条弹簧链成为一条 type-4 链，点 = 骨骼头加末端，用该骨骼自己的顶点做「源 → 贴合后」的拟合映射到游戏空间；第 i 个关节取第 i 根骨的源权重，其余权重按贴合后的游戏骨等比保留。`RIG` 定每类链的模板和碰撞组，`RIG_ANCHOR` 定挂接骨，脸颊两条跳过。
- `n3_face.py`：脸（Body 网格）蒙到玩家面部骨上，让游戏的面部姿势按 Karin 自己的形态键动：每个映射姿势取 6 根平移最大、旋转不超过 0.25 rad、在基础身体 / 女性头 / 两件上衣里绑定姿势相同的驱动骨，逐顶点非负岭回归；面部骨权重可以大于 1，头骨吃负的剩余，量化到同一个 f16 网格使总和精确为 1。

### 3. 写 G1M 并读回

```powershell
python -B $B/n3_build_g1m.py ninja   --physics --collide --face
python -B $B/n3_build_g1m.py samurai --physics --collide --face
python -B $B/n3_validate_g1m.py "$W/g1m/0x5548953f.g1m" "$W/orig/0x5548953f.g1m" --layout-changed --physics
python -B $B/n3_validate_g1m.py "$W/g1m/0xed9b4309.g1m" "$W/orig/0xed9b4309.g1m" --layout-changed --physics
```

- `n3_build_g1m.py [ninja|samurai] [--physics [--collide] [--face]]`：Karin 的主体写进上衣的 rest 子网格；其余原版子网格保留缓冲、材质和 MESH_LOD 组，三角形塌缩；手臂、裙子 / 脸、每个 type-4 条目一个网格插在最后一个材质 0 子网格之后（各自的顶点缓冲、属性集、调色板、索引缓冲、子网格，MESH_LOD 类型 2 组 NUN id 0x2710 + k）。调色板超过 85 改 u16 骨索引（上限 128，再多就把权重最小的骨合并到保留的祖先，物理关节和面部骨不合并）；每个调色板条目用原生逆绑定（没有就追加到 MM1G）；FM1G 的计数和 GM1G 包围盒随之更新。`--physics` 用 `n3_g1m_physics.py` 写 SM1G 关节、ONUN type-4 子块和 FM1G 统计；`--collide` 追加各链的 LLOC 碰撞组（否则都用模型的第 0 组）；`--face` 把 `face.json` 的权重写给脸并放进裙子的子网格。输出 `g1m/<模型>.g1m`、`build_report[_samurai].json`、`atlas_uv.json`。
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

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/g1m_tool.py`、`g1t_tool.py`、`ktdata.py` | KT 引擎格式库，与浪人崛起便携包相同：G1M / G1H 读取、原地隐藏子网格、原生绑定检查；G1T 头、DX12 64 KB tile 与线性互转、常量填充（浪人崛起的存储类型 0 / 1，仁王3 的存储类型 3 用 `n3_g1t.py`）；`root.rdb` / `root.rdx` / fdata 提取、kidsobjdb、KTID 槽表 |
| `scripts/n3_g1t.py`、`n3_g1t_resize.py` | 仁王3 G1T v0066 存储类型 3 的解码、编码、常量填充；换尺寸重建 |
| `scripts/n3inject.py` | 资源表注入的安装 / 校验 / 还原（见上） |
| `scripts/karin_install.py` | 发行包安装器：原版 sha256 核对、从玩家数据生成塌缩模型、暂存核对、调用 `n3inject.py` |
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
| `scripts/n3build/n3_build_g1m.py`、`n3_g1m_physics.py` | 写 G1M；SM1G 关节、ONUN type-4、LLOC 碰撞组（含 `KARIN_HIPS` 臀部椭球）、FM1G 统计 |
| `scripts/n3build/n3_validate_g1m.py` | 构建结果的独立读回校验 |
| `scripts/n3build/n3_registry.py`、`n3_textures.py` | 物理注册表与每材质计数；图集与常量贴图 |
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
- `n3_textures.py` 的常量值，`configs/collapse.txt`、`configs/vanilla.json`；`checks/coll_cover.py`、`fit_butt3.py` 的高度范围。

以下随游戏版本变化（`build-sensitive`），游戏更新后要重新核对：

- 资源哈希：两件上衣、注册表、计数、贴图、KTID、要塌缩的模型（`n3_build_g1m.TARGETS`、`n3_registry.REGISTRY`、`n3_textures.CONSTANTS`、`n3_common.CHEST` / `BODY`、`n3_face.SAME_BIND` / `POSE_LIB`、`n3_g1m_physics.TEMPLATES` / `COLLISION_SETS`）；
- 两件上衣的子网格布局（`TARGETS` 的 rest 子网格）、玩家骨号、面部骨号 400–737、type-4 / type-5 id 的命名空间、FM1G 的统计偏移、G1T v0066 的头字段；
- `vanilla.json`：v2.0.0.2 原版的 sha256，版本一变安装器就拒绝。

## 已验证与边界

- **实机。** 结论来自项目用原脚本构建的 build7–build24（[验证与发布](../../games/nioh-3/VALIDATION_AND_RELEASE.md)、[Karin_Original 案例](../../games/nioh-3/cases/KARIN_ORIGINAL.md)）：build21 关卡内物理由用户确认，build23 由用户确认；build24（臀部碰撞椭球）由发行包装进测试机，`verify` 33/33，实机效果待用户确认。
- **便携版本身只做了离线核对（2026-11-01）：** 在本机用原脚本和便携脚本在同一份输入上运行、逐字节比较：构建链 10 步（贴合 → 物理 → 表情 → 两件上衣 → 校验 → 注册表 → 贴图）的 22 个输出相同，并与发行包 build24 的 10 个对应文件逐字节相同；构建链的其余参数 10 步相同；7 个离线检查 8 次运行的输出（含 3 张渲染图）相同；27 个定位 / 报表脚本 32 次运行的输出和 17 个写出的文件相同；`karin_install.py` 在发行包布局下「拒绝 → 安装 → 校验 → 卸载」四步与原件相同。Blender、游戏和测试机都没有重跑。详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。`Nioh3Tools` 不需要游戏、Blender、源模型或 texconv：合成的 `root.rdb` / `root.rdx` / fdata 上 `n3inject.py` 的安装 → 校验 → 还原（带空格的路径、参数块保留、过期备份的两条路径），`karin_install.py` 拒绝版本不符的原版并且不安装、从便携包和发行包两种布局安装 / 校验 / 卸载；合成 G1T v0066 存储类型 3 的解码、编码往返（逐字节）、常量填充和换尺寸；`n3_g1m_physics.lloc_entry_bytes` 追加椭球和 `new_lloc`；`n3_registry.py` 的注册表与计数；定位脚本、ETW 统计和阶段比较；`N3_BUILD` / `N3_VRM` 缺失时的报错；构建链和检查的 `--help`；PROVENANCE 与可移植性。没装 numpy / scipy 时要它们的项跳过；`karin_install.py` 那项只在 Windows 上跑。
- **测试没覆盖的部分：** 两个 Blender 脚本只做语法检查；`n3_conform.py`、`n3_physics.py` 默认模式、`n3_face.py`、`n3_build_g1m.py`、`n3_textures.py` 只在本机真实数据上和原脚本比较过，测试里没有合成数据；`g1a.py`、`g2a.py` 只测了 `--help`（本机没有动画文件）；非 Windows 系统；其他游戏版本。
- **便携改动：**
  - `n3_common.py` 的 `BUILD` 原来默认是会话临时目录，改为只认 `N3_BUILD`，用到路径时才检查（`BUILD` / `ORIG` 是延迟求值的路径对象）；`n3_physics.py` 写死的 VRM 路径改为 `N3_VRM` / `--vrm`；
  - 没有 argparse 的命令补上了 argparse，位置参数和选项不变；`find_variant.py`、`tex_stats.py` 加 `--texconv`，`swing.py`、`facecheck.py` 加 `--png`；
  - `karin_install.py` 的工具目录在发行包布局下是 `tools\`，否则是脚本所在目录；数据目录加 `--data`；
  - 离线检查里写死的项目和会话目录改为相对脚本的路径和 `N3_BUILD`；
  - 每个文件保留原来的换行（11 个 CRLF，其余 LF）。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md) 和 [PROVENANCE.json](../PROVENANCE.json)。
- **没有收进本包：** 测试机远程辅助脚本（`tools/remote/*.sh`）；浪人崛起项目的其他构建脚本（`tools/ko/ronin_original/` 下除 `ko_extract_source.py` 以外）；会话里的一次性脚本和文本转储；源模型、游戏数据、构建产物、发行包（`files\`、`package.json`、`.cmd`、zip）。
- **署名：** G1A / G2A 读取移植自 Joschuka 的 Project-G1M；G1T 存储类型 3 的参照解析器是 MrIkso 的 RDBExplorer；注入方式与 eArmada8 的 yumia_fdata_tools 相同（本包不带它们的代码）。
