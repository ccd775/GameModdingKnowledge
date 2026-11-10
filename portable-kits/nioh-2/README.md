# 仁王2（Nioh 2）便携包

先读 [游戏知识](../../games/nioh-2/README.md)、[Agent 入口](../../games/nioh-2/AGENTS.md) 和 [构建流水线](../../games/nioh-2/BUILD_PIPELINE.md)。被否定的归档改写路线、Mod Enabler 的挂钩、蒙皮常量缓冲、宿主绘制与合并调色板、影子和隐藏见 [技术合同](../../games/nioh-2/TECHNICAL_CONTRACTS.md)；弹簧链、碰撞体和离线测试台见 [物理](../../games/nioh-2/PHYSICS.md)；面部权重迁移和形态键眨眼见 [表情](../../games/nioh-2/FACE.md)；存档加解密和换装器见 [存档与外观](../../games/nioh-2/SAVE_AND_APPEARANCE.md)；症状和处理见 [排障手册](../../games/nioh-2/TROUBLESHOOTING.md)；离线 / 实机闸门、发行包和游戏版本见 [验证与发布](../../games/nioh-2/VALIDATION_AND_RELEASE.md)；版本轨迹见 [Karin_Original 案例](../../games/nioh-2/cases/KARIN_ORIGINAL.md)。

这是 KarinN2（用 Karin_Original 替换仁王2 女性主角，build1–build5，发行包 build5）实际使用的工具。和仁王3 不同，这里**不改游戏文件**：Mod 是一个 3DMigoto 的 Mod 文件夹，挂钩角色着色器，按 IB 哈希跳过原版角色的全部绘制，再借两次原版绘制画 Karin——右手护手（IB `0814c08f`）画身体、衣服、头发、狐耳、尾巴、裙子（两个合并的 85 骨调色板），原版脸（IB `834bff26`）画脸（脸自己的 128 条目调色板）。

包里有：

- **构建链**：帧分析解析 `fa_parse.py` / `fa_mesh.py`，跨绘制认骨 `bones.py`，关节求解 `n2_skel.py`，贴合 `n2_conform.py`，生成整个 Mod 的 `n2_build.py`（网格、贴图、`karin.ini` 和 7 个计算着色器：合并调色板 `merge_a` / `merge_s1` / `merge_s2`、弹簧链 `sim_a`、形态键眨眼 `blink_b`、帧戳 `tick` / `stamp`），以及用 Mod Enabler 自带编译器做编译检查的 `c46.py`；
- **离线检查**：蒙皮叠图 `check_skin.py`，双马尾 / 尾巴和狐耳的调参测试 `checks/`，裙子和链物理的测试台 `simcheck/`（`sim_a.hlsl` 的 Python 移植，带合成的跑 / 停 / 转身 / 侧闪动画）；
- **归档工具**：K300 归档读取 `n2lnk.py`、KT 包解析 `ktpack.py`、完整性扫描 `n2verify.py`、G1M 顶点缓冲指纹 `g1m_index.py`、按指纹 / 顶点位置找绘制对应模型的 `fa_match.py` / `findmodel.py`，以及 KT 引擎的 G1M 读取库 `g1m_tool.py`（与浪人崛起、仁王3 便携包的同名文件逐字节相同）。这是**被否定的路线**留下的工具：玩家装备模型在归档里没有找到（[技术合同](../../games/nioh-2/TECHNICAL_CONTRACTS.md) §1），收进来是为了能复查这个结论，构建不用它们；
- **换装器** `n2_miaomiao.py` 和护甲名称表 `n2_armor.py`：把存档里五件护甲的外观改成 Mod 要求的隼套装（[存档与外观](../../games/nioh-2/SAVE_AND_APPEARANCE.md)）。

- **游戏版本：** 仁王2 Complete Edition PC **1.25**（2021-02-05 首发版）。Steam 版会更新到 1.27 / 1.28.x，没有测过；着色器或模型的哈希变了，Mod 就不生效（显示原版角色），见 [验证与发布](../../games/nioh-2/VALIDATION_AND_RELEASE.md) §4。
- **加载方式：** Nioh 2 Mod Enabler 1.1（内含 3DMigoto 1.3.16：`d3d11.dll`、`d3dcompiler_46.dll`、`d3dx.ini`、`Mods\`）。把构建出的 `KarinN2\` 整个放进 `<游戏目录>\Mods\`，游戏里 `F10` 重载。不改 exe、不改归档。Mod 用到 Mod Enabler 的 `CommandListN2General` / `CommandListN2Shadows`。
- **源模型：** `source/` 是 Karin_Original 的 FBX 在 Blender 4.0.2 里导出的结果，和仁王3 项目是同一个 FBX，导出脚本见仁王3 便携包的 `scripts/blender/ko_extract_source.py` 和 `scripts/n3build/blender_shapekeys.py`（本包不重复收录）。
- **texconv：** DirectXTex 的 `texconv.exe`，由用户自备。`n2_build.py` 按 `--texconv` → `N2_TEXCONV` → `<工作目录>\texconv\texconv.exe` 的顺序找（原脚本认的是 `TEXCONV` 变量和构建包里的 `texconv\`）。
- **d3dcompiler_46.dll：** 编译检查用 Mod Enabler 里的那一个（3DMigoto 运行时用它编译 Mod 的着色器，比 fxc 严）。用户自备，本包不带。
- **Python：** `n2lnk.py`、`ktpack.py`、`n2verify.py`、`g1m_index.py`、`fa_match.py`、`fa_parse.py`、`g1m_tool.py`、`c46.py`、`n2_armor.py` 只用标准库；`fa_mesh.py`、`fa_list.py`、`bones.py`、`gamemesh.py`、`findmodel.py`、`n2_skel.py`、`checks/`、`n2_miaomiao.py` 要 numpy（换装器的图形界面用标准库 tkinter）；`n2_conform.py`、`n2_build.py`、`simcheck/` 另需 scipy；`n2_build.py` 另需根目录的 Pillow；`check_skin.py` 另需 matplotlib。`requirements.txt` 钉的版本要 Python 3.12 或更高。本次在 3.14.0、numpy 2.5.2、scipy 1.18.0、matplotlib 3.11.2、Pillow 12.3.0 上测试。
- **只在 Windows 上：** `c46.py` 用 ctypes 加载 DLL；texconv 只有 Windows 版；`n2_miaomiao.py` 写文件前用 `tasklist` 判断游戏是否在运行。项目在本机构建，游戏在另一台测试机上；帧分析在测试机上抓。
- **运行位置：** 以下命令都从交接包根目录执行。所有命令都有 `--help`，只打印说明、不需要任何环境变量、不会开始处理。`fa_mesh.py`、`gamemesh.py`、`ktpack.py`、`n2_armor.py` 和 `simcheck/` 里的 `common.py`、`simpy.py`、`test2.py` 是库，没有命令行。

## 环境变量与参数

| 变量 / 参数 | 读的脚本 | 含义 |
| --- | --- | --- |
| `<工作目录>`（位置参数） | `n2_build.py` | 构建输入目录，布局见下一节（原脚本就是这样传的，项目里是构建包 `_build\` 本身） |
| `N2_BUILD` | `check_skin.py`、`checks/simtest.py`、`checks/eartest.py`、`simcheck/` 的全部命令 | 同一个工作目录。原脚本按当前目录（`simtest.py`、`eartest.py`、`check_skin.py` 要从构建包根目录运行）或脚本位置（`simcheck/common.py` 切到 `tools\` 的上一级）找；便携版没有默认值，开始读数据前检查，没设时报错并说出变量名 |
| `N2_TEXCONV`（`--texconv`） | `n2_build.py` | texconv 可执行文件，默认 `<工作目录>\texconv\texconv.exe` |
| `N2_HEAD_SCALE` | `n2_conform.py` | 源模型整体缩放，默认 150（Blender 米 → 游戏厘米，并让头和游戏的头一样大）。原脚本就有这个变量 |
| `N2_GAME_DIR`（`--game-dir`） | `findmodel.py` | 游戏目录（里面有 `archive\`）。原脚本写死了本机的游戏目录；只在要从归档读条目（缓存里没有）时检查 |
| `--cache` | `findmodel.py` | 解压出的归档条目的缓存目录，下次运行直接读。原脚本写死了本机的缓存目录、总是缓存；便携版不给就不缓存（结果相同） |
| `[mod 目录]`、`--png` | `check_skin.py` | 构建出的 Mod 文件夹（读 `meshes\`）和输出图，默认 `<N2_BUILD>\out\KarinN2`、`<N2_BUILD>\build1\skin_check.png`（原脚本只认这两个位置） |
| `<游戏目录>` / `<archive 目录>`（位置参数） | `n2verify.py` / `n2lnk.py`、`g1m_index.py` | 原脚本就是这样传的 |

## 工作目录

```text
<工作目录>/                       n2_build.py 的第一个参数；N2_BUILD 指向同一个目录
  fa3/FrameAnalysis-2026-11-07-205515/   3DMigoto 帧分析（装备界面，隼套装外观，长马尾）；目录名写死在 n2_build.FA 和 check_skin.py 里
  fa3/fa3.json                    fa_parse.py --json 写
  data/bones3.json                bones.py 写：全局骨号 g<n> 的矩阵，每次绘制的调色板条目 → 全局骨号
  data/joints.json                n2_skel.py 写：50 个关节和骨号标签
  source/                         源模型导出：source.json、source.npz、shapekeys.json / .npz、textures/（n2_build.py 按文件名取身体、衣服、头发、脸 4 张颜色贴图）
  build1/conformed.npz, conform.json   n2_conform.py 写（conform.json 里有 Karin 关节在游戏空间的位置，离线物理测试也读它）
  build1/build_report.json        n2_build.py 写（副产物：部件顶点数、两个调色板的来源、宿主统计、脸的拟合残差、模拟链）
  texview/                        n2_build.py 写：脸那次绘制的 PS 槽 1 / 7 贴图转成的 PNG（取均值做常量贴图）
  texconv/texconv.exe             默认的 texconv
  asm/                            游戏着色器的反汇编（确认 cb0 布局用；脚本不读）
  out/KarinN2/                    check_skin.py 默认读的构建结果（输出目录随意）
```

`n2_build.py` 会改写 `build1/build_report.json` 和 `texview/`，其余输入只读。核对等价性时请在工作目录的副本上跑。

## 构建流程

```powershell
$Kit = "portable-kits/nioh-2"; $S = "$Kit/scripts"
$env:N2_BUILD = "<工作目录>"; $W = $env:N2_BUILD
$FA = "$W/fa3/FrameAnalysis-2026-11-07-205515"
python -m pip install -r requirements.txt -r $Kit/requirements.txt
```

### 1. 帧分析 → 全局骨号 → 关节

```powershell
python -B $S/fa_parse.py $FA --json "$W/fa3/fa3.json"          # 每次绘制：VS / PS、vb / ib 哈希、布局、顶点 / 索引数、绑定的 PS 贴图
python -B $S/fa_list.py $FA "$W/fa3/fa3.json"                  # 蒙皮绘制一览：每对 (vb0, ib) 的顶点数、包围盒、最大骨号、出现在哪些绘制
python -B $S/bones.py $FA "$W/fa3/fa3.json" "$W/data/bones3.json" 21 19 15 29 16 31 17 32 22 24 23 25 42 47 43 45 44 46 38 39 40 41 35 36 48 49 50 51 52 56 59 60
python -B $S/n2_skel.py "$W/data/bones3.json" "$W/data/joints.json"
```

**绘制号的顺序不能改。** `bones.py` 按第一次出现的顺序给全局骨号编号（绘制按参数顺序、条目按升序），`n2_skel.LABEL`、`n2_conform.G` / `FINGER_G`、`n2_build.py` 和 `simcheck/common.LEG` 里的骨号都是按上面这个顺序（胸 21、袴 19、左胫甲 15 …，即项目 `bones3.json` 的顺序）得到的。按升序传同样 32 次绘制，矩阵相同、骨号全变，关节最多偏 1 米。

- 帧分析在测试机上抓：女性主角、长马尾、五件护甲外观是隼套装，站在装备界面，`d3dx.ini` 开 `hunting`、带 vb / ib / cb / 贴图转储，按 `F8`（[构建流水线](../../games/nioh-2/BUILD_PIPELINE.md) §1）。
- `bones.py`：蒙皮 VS 的 `vs-cb0` = 5 行头 + 每个调色板条目 3 行（3×4 行主序矩阵），BLENDINDICES 是条目号 × 3。各绘制的条目按矩阵相等（2e-3）归并成全局骨号，记下每个条目的加权中心和权重质量。上面的 32 次绘制是 `bones3.json` 用的那一组（护甲、皮肤、脸、头发等），得到 125 个全局骨号。
- `n2_skel.py`：全局骨号的标签（`LABEL`）是按加权中心手工标的；关节 = 父子两根骨的矩阵把同一点映到同一位置的那个点（最小二乘，向种子点正则化 0.05），右侧用镜像的骨号和种子。
- `fa_mesh.load_draw()`、`gamemesh.load()` 是库：按布局把一次绘制的 vb / ib 解成 numpy 数组；带上每个顶点的全局骨号。

### 2. 贴合

```powershell
python -B $S/n2_conform.py "$W/source" "$W/data/joints.json" "$W/build1"      # → conformed.npz、conform.json
```

`n2_conform.py`：源模型按 `N2_HEAD_SCALE` 缩放、平移到 Karin 的 Neck 落在游戏颈关节上；头颈刚性，其余人形骨各拟合一个仿射（骨段方向和长度，截面保持），按 Karin 的权重线性混合。权重写成记号：`g<n>` 全局骨号；头发、狐耳先全给头 `g8`，尾巴给骨盆 `g0`，构建器再改成模拟骨。方法和仁王3 的 `n3_conform.py` 相同，关节换成从仁王2 蒙皮矩阵解出的。

### 3. 生成 Mod

```powershell
python -B $S/n2_build.py $W "<输出目录>\KarinN2" [--texconv "<texconv.exe>"]
```

`n2_build.py`：读帧分析、`bones3.json`、`joints.json`、`source/` 和贴合结果，写出整个 Mod 文件夹（26 个文件，发行包另加手写的 `README.md`）：

- `meshes/`：宿主 A 的 `karinA.vb`（30274 顶点、48 字节）和 4 个 IB（身体、衣服用调色板 A；`hair_b`、`costume_b` 用调色板 B），脸的 `karinB.vb0` / `vb1` / `karinB_face.ib`、`karinB_blink.buf`（每顶点闭眼形态键位移）；
- `textures/`：4 张 `BC7_UNORM_SRGB` 2048 颜色贴图（先在线性空间乘 `ALBEDO_SCALE`）和 5 张 4×4 常量贴图（`refrough_b`、`artior_b` 取原版脸贴图的均值，要 `texview/`）；
- 计算着色器 `merge_a.hlsl`、`merge_s1.hlsl`、`merge_s2.hlsl`、`sim_a.hlsl`、`blink_b.hlsl`、`tick.hlsl`、`stamp.hlsl`，链参数、碰撞体、调色板映射直接写成常量；
- `karin.ini`：着色器挂钩（`PS_HASHES`、`VS_HASHES`、`SHADOW_VS`）、隐藏（`HIDE_IBS`）、资源、自定义着色器、两个宿主的覆盖段。

断言：每个调色板 ≤ 85 根骨、每个记号都有源绘制、宿主 A 顶点数 < 65536。标准输出是 `build_report.json` 去掉调色板的部分。

### 4. 编译检查

```powershell
python -B $S/c46.py "<Mod Enabler 的 d3dcompiler_46.dll>" (Get-ChildItem "<输出目录>\KarinN2\*.hlsl")
```

`c46.py`：ctypes 调 DLL 的 `D3DCompile`（`cs_5_0`、入口 `main`），每个文件打印 `OK` / `FAIL 0x…` 和编译器消息，全部通过才退出码 0。`RWBuffer<float4>` 这类多分量类型 UAV 的读取会报 X3676，fxc 10 不报。build5 的 7 个着色器全部 `OK`，`merge_a.hlsl` 有一条 X4000 警告（`src` 可能未初始化）。

### 5. 部署

整个 `KarinN2\` 放进 `<游戏目录>\Mods\`（替换旧版本时先删旧文件夹；改过着色器要删 3DMigoto 生成的编译缓存）。开着游戏时 `F10` 重载。实机闸门见 [验证与发布](../../games/nioh-2/VALIDATION_AND_RELEASE.md) §2。

## 离线检查

```powershell
python -B $S/check_skin.py ["<输出目录>\KarinN2"] [--png skin.png]   # 帧里的真实矩阵蒙皮 Karin（按 merge_a.hlsl 拼调色板），叠在原版角色上
python -B $S/checks/simtest.py                                   # 双马尾、狐尾、狐耳的几组参数：跑步 + 180° 转身、300 cm 侧闪时末端的摆角
python -B $S/checks/eartest.py                                   # 狐耳（两节）：减速的跑停、120° 转身、30 cm 前冲时的摆角、回弹次数、3 s 后的残余
python -B $S/simcheck/rest_check.py                              # 裙子静止：各合成姿势下 build4 的一步模拟 vs build3 的权重场，皮肤穿出裙子的顶点
python -B $S/simcheck/anim5.py                                   # sim_a.hlsl 的 Python 移植 + 70/30° 步幅的减速跑、停步、转身 / 侧闪：每组链的最大摆角、穿出帧
python -B $S/simcheck/tailtune.py                                # 狐尾（链 TA）：跑 / 停 / 转身时尖端摆角、扎进大腿胶囊的深度、静止下垂
python -B $S/simcheck/anim.py; python -B $S/simcheck/anim2.py    # 对称步态（45° / 65°）的同一套检查，比真实跑步更狠
python -B $S/simcheck/v3.py                                      # 裙子权重场（build3 的 blend）的几组参数；xfer / harm / adapt / v2 是更早的权重方案
```

- 这些检查都只读工作目录、只打印（`check_skin.py` 另写一张图），读 `build1/conform.json`、`build1/conformed.npz`、`source/`、`data/joints.json`；`simcheck/` 还导入 `scripts/n2_build.py`，用它的链表、碰撞体、权重函数和 `sim_layout`。
- **`check_skin.py` 跑不了 build5 的输出**（原脚本和便携版一样，`IndexError: index 62 is out of bounds for axis 0 with size 60`）：它只按 `build_report.json` 的 `palette_A`（60 根）拼调色板，而 `karinA.vb` 里头发、耳朵、尾巴、裙子（`PAL_B_MESHES`）的顶点用的是调色板 B（66 根，骨号到 65；调色板 B 是加物理时才有的）。便携版没有改它的逻辑；要用它先补上调色板 B（`karinA_hair_b.ib` / `karinA_costume_b.ib` 画的顶点按 `palette_B` 蒙皮）。
- `simcheck/` 的导入链：`common.py`（读数据、切到 `N2_BUILD`）→ `test2.py` → `xfer.py` → `harm.py` → `adapt.py` → `v2.py` → `v3.py` → `simpy.py`（`sim_a.hlsl` 的移植）→ `anim.py` → `anim2.py` → `anim5.py`；`rest_check.py`、`tailtune.py` 从 `simpy.py` / `anim.py` 起。每个命令都是在导入前先解析参数。`simcheck/README.md` 是项目原来的说明。
- `simpy.py` 要和 `n2_build.write_sim_shader` 手动保持一致；改了着色器的物理就要改它。
- 离线测试的动作要比游戏更狠，每条链都要有自己的数字（[物理](../../games/nioh-2/PHYSICS.md) §4–5）。

## 归档与帧分析的定位工具

```powershell
$Arc = "<游戏目录>\archive"
python -B $S/n2lnk.py index $Arc index.jsonl                         # 每个 archive_XX.lnk 的每个条目一行：偏移、大小、压缩、前 8 字节
python -B $S/n2lnk.py extract $Arc 3 1234 out.bin                     # 解出一个条目；many $Arc list.txt <目录>（每行 "归档 条目 [名字]"）；locate $Arc 3 0x1a2b3c
python -B $S/n2verify.py "<游戏目录>" verify.txt                       # 每个压缩块能解开、每个条目解出声明的大小；未压缩数据里整页为零的标出来
python -B $S/g1m_index.py $Arc index.jsonl g1m_vb.jsonl [--from N] [--zip-only]   # MDLTEXPK / G1M_PACK / G1M 里每个顶点缓冲的指纹（前 96 字节、中间 96 字节的 sha1）
python -B $S/fa_match.py $FA "$W/fa3/fa3.json" g1m_vb.jsonl [draw …]  # 帧里的顶点缓冲按指纹对归档
python -B $S/findmodel.py $FA "$W/fa3/fa3.json" g1m_vb.jsonl hits.json 31 39 --game-dir "<游戏目录>" [--cache <目录>]   # 按顶点数找候选，解出位置比较（误差 < 1e-3）
```

- `n2lnk.py`：K300 归档（`archive\archive_XX.lnk`）：0x20 字节头（`K300`、条目数、文件大小、对齐 0x800），每个条目 (偏移, 大小, 存储大小, 压缩标志)；压缩条目是 16 KB 一块，u32（压缩大小 | 0x8000 → zlib；否则原样）+ 数据，每块补齐到 16 字节。只读。`locate` 返回第一个 [偏移, 偏移 + max(存储大小, 大小)) 含该偏移的条目（与原脚本相同，压缩条目的区间会盖到后面的条目）。
- `ktpack.py`：KT 通用包（`MDLTEXPK` = G1M_PACK + `EXARG000` 贴图包、`G1M_PACK`、`EXARG000`）：头 0x30 字节，偏移表、大小表、附加包，偏移相对包头。
- `n2verify.py`：为排查那次悄悄把文件页清零的磁盘 I/O 故障写的（「整页为零」就是当时看到的损坏特征，[排障手册](../../games/nioh-2/TROUBLESHOOTING.md) §4）。`g1m_index.py` 以追加方式写输出，`--from` 用来续跑；`--zip-only` 由 `main()` 从命令行读（与原脚本相同）。
- 结论：按顶点数和指纹都没有在 20 个归档里找到玩家装备的 G1M（`rejected`），所以走 3DMigoto 绘制时替换。

## 存档外观（换装器）

```powershell
$Save = "$([Environment]::GetFolderPath('MyDocuments'))\KoeiTecmo\NIOH2\Savedata\<账号 ID>\SAVEDATA00\SAVEDATA.BIN"
python -B $S/n2_miaomiao.py                                   # 图形界面：扫描「文档」下的存档目录，选中后改外观 / 取消外观变更 / 从备份恢复
python -B $S/n2_miaomiao.py inspect $Save                     # 账号、等级、保存时间，五个护甲部位穿的装备和当前外观
python -B $S/n2_miaomiao.py apply $Save --out new.bin         # 写到另一个文件；--in-place 直接改（先备份到旁边的 MiaomiaoBackups\）
python -B $S/n2_miaomiao.py clear $Save --in-place            # 五个部位的外观改回各自装备本来的样子
python -B $S/n2_miaomiao.py restore $Save <MiaomiaoBackups\…json>
```

`n2_miaomiao.py`：解密 `SAVEDATA.BIN`（0x296F28 字节；《仁王》1 代的自定义 S 盒 AES-128-CTR，文件头 0x148 字节用固定密钥、解密后以 `NIOHUSR` 开头，存档体子密钥在解密后的头 0x40 起），按固定布局读装备表（0x1CC510，11 个格号）和装备区（0xED508 起 700 格 × 0x90 字节，+0 物品 ID、+2 外观 ID，大端），
把头、胴、手、腰、脚五件护甲的外观 ID 写成 `KARIN_TARGETS`（隼套装），并把 4 个完整性检查标志清零（与社区存档编辑器相同；游戏下次存档时会恢复）。只把改动字节的差量异或进原密文，改动超出这些字节就拒绝；写出前重新解密复查。
部位没穿护甲、物品和部位对不上、标志位置的值不是 0 / 1、物品大多不认识时拒绝。`--in-place` / 图形界面：游戏在运行就拒绝；先写备份和 JSON 记录（前后 sha256），用同目录临时文件替换；`restore` 核对当前存档仍是那次修改的结果，否则拒绝。
`n2_armor.py` 是护甲 ID → (部位, 英文名) 表。格式、实机证据和已否定的做法见 [存档与外观](../../games/nioh-2/SAVE_AND_APPEARANCE.md)。项目里用 PyInstaller 打成单文件 EXE 发给玩家（构建脚本不在本包里）。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/n2_build.py` | 构建器：网格、权重（裙子权重场、模拟骨、脸）、贴图、全部计算着色器、`karin.ini`、`build1/build_report.json` |
| `scripts/n2_conform.py` | 源模型贴合到帧分析解出的骨架，权重记号 |
| `scripts/fa_parse.py`、`fa_mesh.py`、`fa_list.py` | 3DMigoto 帧分析：文件名和日志 → 每次绘制的记录；vb / ib → numpy；蒙皮绘制一览 |
| `scripts/bones.py`、`gamemesh.py`、`n2_skel.py` | `vs-cb0` 调色板 → 全局骨号；原版绘制带全局骨号的网格；关节求解与骨号标签 |
| `scripts/c46.py` | 用 `d3dcompiler_46.dll` 编译计算着色器（`cs_5_0`） |
| `scripts/check_skin.py` | 蒙皮叠图检查 |
| `scripts/checks/simtest.py`、`eartest.py` | 双马尾 / 尾巴 / 狐耳的弹簧链调参测试 |
| `scripts/simcheck/*.py`、`README.md` | 裙子权重场和链物理的测试台（`sim_a.hlsl` 的 Python 移植、合成姿势和动画） |
| `scripts/n2lnk.py`、`ktpack.py`、`n2verify.py` | K300 归档读取、KT 包解析、归档完整性扫描 |
| `scripts/g1m_tool.py` | KT 引擎 G1M 读取库，与浪人崛起、仁王3 便携包相同 |
| `scripts/g1m_index.py`、`fa_match.py`、`findmodel.py` | 归档里 G1M 顶点缓冲的指纹；帧里的绘制对归档模型（被否定的路线） |
| `scripts/n2_miaomiao.py`、`n2_armor.py` | 换装器：存档加解密、装备表和外观字段、图形界面和命令行、备份 / 回滚；护甲 ID 表 |

## 输出与本机信息

- **中间结果：** `fa3/` 是游戏的帧分析（几百 MB，含游戏的网格和贴图）；`source/`、`build1/` 来自源模型；`data/` 由帧分析算出；`out/` 是构建产物。这些都不要收进本仓库。`build_report.json` 和标准输出里没有本机路径；`c46.py` 的编译器消息里有着色器文件的完整路径。
- **发行物：** 一个 `KarinN2\` 文件夹（26 个构建出的文件 + 手写的 `README.md`），不含游戏文件；换装器另发 ZIP（EXE、README、第三方许可、源码），不含任何存档。

## 案例常量

以下是 Karin 和这次帧分析专用的值，不是通用配置：

- `n2_build.py`：`SOURCES` / `HOST_A` / `HOST_B`（帧分析里的绘制号）、`ALBEDO_SCALE`、`SKIRT_*`（裙子权重场：`SKIRT_SRC`、`SKIRT_TOKENS`、`SKIRT_THIGH`、`SKIRT_LR_CM` 等）、`SIM_CHAINS`、`SIDE_HAIR_*`、`SKIRT_SIM_*`、`SKIRT_CHAINS`、`SIM_DEFAULT`、`SIM_COLLIDERS`、`SIM_LIMITS`、`PAL_B_MESHES`、`UPPER_LID`、`LID_MODE`、`LID_REF`、`LID_FULL_CM`、`LID_DEAD_CM`，以及贴图文件名；
- `n2_conform.py`：`N2_HEAD_SCALE` 默认 150、`SPINE_YS`、`FORE_T`、`THIGH_T`、`HEAD_MESHES`、`SKIRT_PUSH`；
- `n2_skel.py` 的 `LABEL`、`JOINTS_L` 的种子点和 `MIRROR`（fa3 这次帧分析的全局骨号，换一次帧分析骨号就会变）；`n2_conform.py` 的 `G`、`FINGER_G` 同样；
- `checks/`、`simcheck/` 的参数组、姿势、动作和高度范围（`common.py` 的 `LEG`、`AX`）；`check_skin.py` 的 `SRC`（护甲 → 绘制号）；
- `n2_miaomiao.py` 的 `KARIN_TARGETS`（Mod 做模型时测试存档里的隼套装外观 ID，换了 Mod 的目标外观就要换）。

以下随游戏版本变化（`build-sensitive`），游戏更新后要重新核对：

- 着色器哈希：`PS_HASHES`（11 个角色 PS）、`VS_HASHES`（布料 VS `24f9a3d0`）、`SHADOW_VS`、`FACE_VS`，蒙皮 VS `73278b6e` 的 cb0 布局（`SHADOW_LAYOUT`、`bones.HDR`）；
- IB 哈希：`HIDE_IBS`、`SOURCES`、`HOST_A`（`0814c08f`）、`HOST_B`（`834bff26`）；
- 帧分析目录名 `FA`（`fa3/FrameAnalysis-2026-11-07-205515`）只是本次抓帧的名字；
- `n2lnk.py` 的 K300 布局是在 Complete Edition 2021-02-05 版上量的；存档格式（`n2_miaomiao.py` 的偏移）与面向当前 Steam 版的社区编辑器相同（`reference-inferred`）。

## 已验证与边界

- **实机。** 结论来自项目用原脚本构建的 build1–build5（[验证与发布](../../games/nioh-2/VALIDATION_AND_RELEASE.md)、[Karin_Original 案例](../../games/nioh-2/cases/KARIN_ORIGINAL.md)）：build1d 由 agent 在装备界面和关卡里自测（`runtime-load-pass`）；build2b 的眨眼由用户确认；build4（鬓发、裙摆物理）、build5（调软的狐尾、隐藏裆前布条）只做了离线测试，用户在游戏里看过 build5。换装器在测试机上实测（agent，`runtime-load-pass`，2026-11-10）：取消外观变更后小腿显示原版护胫，改回后 Karin 恢复，游戏自动存档后完整性标志恢复为 1。
- **便携版本身只做了离线核对（2026-11-10）：** 在本机把项目构建包复制两份，原脚本在一份上、便携脚本在另一份上运行（`N2_BUILD` 指向副本）：
  - 从帧分析起的整条链：`fa_parse.py` → `bones.py`（上面的绘制顺序）→ `n2_skel.py` → `n2_conform.py` 两边的退出码、标准输出和写出的文件相同，并与项目里现有的 `fa3/fa3.json`、`data/bones3.json`、`data/joints.json`、`build1/conform.json` 逐字节相同、`build1/conformed.npz` 按数组相同；`fa_list.py` 的输出相同；
  - `n2_build.py` 写出的 26 个文件与发行包 build5 `release\KarinN2\` 逐字节相同（`README.md` 是手写的，不比较），`build1/build_report.json` 与项目里的现有文件、标准输出与原脚本都相同；
  - 生成的 7 个着色器用 `c46.py` + Mod Enabler 的 `d3dcompiler_46.dll` 全部编译通过，输出与原 `c46.py` 相同；
  - `simcheck/tailtune.py`、`rest_check.py`、`anim5.py`、`checks/simtest.py`、`eartest.py` 的退出码、标准输出和标准错误与原脚本相同；`check_skin.py` 两边都在同一处报 `IndexError`（见[离线检查](#离线检查)）。
  
  游戏、3DMigoto、测试机和帧分析都没有重跑。详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。`Nioh2Tools` 不需要游戏、帧分析、源模型或 texconv：合成的 K300 归档（存储、zlib 块、原样块）上 `n2lnk.py` 的 `index` / `extract` / `many` / `locate`，`ktpack.py` 的 MDLTEXPK / G1M_PACK / EXARG000，`g1m_index.py`（含 `--zip-only`），`n2verify.py`（零页标记、松散文件、坏块）；合成的 3DMigoto 帧分析上 `fa_parse.py`、`fa_mesh.load_draw`、`fa_list.py`、`fa_match.py`、`findmodel.py`（`N2_GAME_DIR` 缺失时的报错、`--cache` 之后不需要游戏目录）、`bones.py`、`gamemesh.load`、`n2_skel.py`（父子矩阵求关节）；`n2_build.py` 的 texconv 默认路径、`pack_weights`、`dds_const`；换装器的合成存档（固定头密钥流、加解密往返、`apply` / `clear` 只改五个外观字段和 4 个标志、各种拒绝、命令行 `--out`、`BACKUP.BIN` 被拒、Windows 上 `--in-place` 的备份与 `restore`）；`checks/`、`simcheck/` 的 `--help` 和缺 `N2_BUILD` 时的报错；PROVENANCE 与可移植性。没装 numpy / scipy 时要它们的项跳过；`--in-place` 那部分只在 Windows 上跑。
- **测试没覆盖的部分：** `n2_conform.py`、`n2_build.py` 的完整构建和离线检查只在本机真实数据上和原脚本比较过，测试里没有合成数据；`check_skin.py` 只测了缺 `N2_BUILD` 时的报错；`c46.py` 只测了 `--help`（DLL 不在本库里）；换装器的图形界面没有测；非 Windows 系统；1.25 以外的游戏版本。
- **便携改动：**
  - 写死的路径：`findmodel.py` 的游戏归档目录和缓存目录 → `--game-dir` / `N2_GAME_DIR`、`--cache`；`check_skin.py` 原来从构建包根目录用相对路径读 `fa3/`、`build1/`、`out/KarinN2/`、写 `build1/skin_check.png`，现在切到 `N2_BUILD`，Mod 目录和输出图可以用参数给；`simtest.py`、`eartest.py` 的 `build1/conform.json` → `N2_BUILD`；`simcheck/common.py` 原来切到 `tools\` 的上一级并从那里导入 `n2_build.py`，现在切到 `N2_BUILD`、从 `scripts/` 导入；`n2_build.py` 的 texconv 原来是 `TEXCONV` 变量或构建包里的 `texconv\`，现在是 `--texconv` / `N2_TEXCONV` / `<工作目录>\texconv\texconv.exe`（解析放在 `main()` 里，被 `simcheck/` 导入时不需要它）；
  - `fa_list.py`、`check_skin.py`、`simtest.py` 往 `sys.path` 里插的相对当前目录的 `tools` → 相对 `__file__` 的脚本目录；
  - 没有 argparse 的命令补上 argparse，位置参数和选项不变：`n2lnk.py`（子命令）、`n2verify.py`、`g1m_index.py`、`findmodel.py`、`fa_match.py`、`fa_parse.py`、`fa_list.py`、`bones.py`、`n2_skel.py`、`check_skin.py`、`n2_conform.py`、`n2_build.py`、`c46.py`、`checks/` 的 2 个、`simcheck/` 的 10 个。原来 `--help` 会被当成路径（`n2_build.py`、`n2_conform.py` 直接报错，`simcheck/` 和 `simtest.py`、`eartest.py` 直接开始跑）；`c46.py` 在解析之后才加载 DLL，`fa_list.py`、`check_skin.py`、`checks/` 在解析之后才导入 numpy / matplotlib，`simcheck/` 的命令只在直接运行时解析、而且在导入数据链之前。细节上的差别：`n2lnk.py` 不带参数时报用法错误（原来打印说明、退出码 1），未知子命令是用法错误（原来是 KeyError）；`findmodel.py`、`bones.py` 至少要一个绘制号（用法行本来就这么写）；没有说明的命令（`fa_list.py`、`checks/` 的 2 个、`simcheck/` 除 `tailtune.py` 以外的 9 个）加了一段说明，`n2_build.py`、`check_skin.py` 的说明里补了用法行；`simcheck/README.md` 改了「切到哪个目录」那一句；
  - 每个文件保留原来的换行：`n2lnk.py`、`n2_build.py`、`simcheck/` 的 `anim.py`、`anim2.py`、`common.py`、`simpy.py`、`README.md` 是 CRLF，其余 LF。

  `g1m_tool.py`、`ktpack.py`、`fa_mesh.py`、`gamemesh.py`、`n2_miaomiao.py`、`n2_armor.py`、`simcheck/simpy.py`、`simcheck/test2.py` 与原文件逐字节相同。处理逻辑、常量和输出没有变。哪些文件改了，见 [验证记录](../VALIDATION.md) 和 [PROVENANCE.json](../PROVENANCE.json)。
- **没有收进本包：** 构建包 `tools\` 里的一次性探针 `cmpvb.py`、`mwheads.py`、`mwheads2.py`、`survey.py`、`findcount.py`、`lidscan.py`（写死了本机的缓存和索引路径，只为当时的单个问题服务）和 `run_*.cmd`；换装器的 `build.cmd`、`requirements-build.txt`、项目自带的 `test_tool.py`（同样的合成存档测试写进了 `tests/test_portable_tools.py` 的 `Nioh2Tools`）、`LICENSE.txt`、`THIRD_PARTY_NOTICES.txt`、EXE 和 ZIP；`BUILD.md`（内容并进了本页和 [构建流水线](../../games/nioh-2/BUILD_PIPELINE.md)）；构建包里的 `source/`、`build1/`、`data/`、`fa3/`、`asm/`、`texconv/`、`texview/`，发行包，测试机脚本，任何存档。
- **署名：** 存档加密的自定义 S 盒和密钥块来自 pawREP 的 Nioh Savedata Decryption Tool（MIT）；`n2_armor.py` 的护甲 ID 表取自 alfizari/Nioh-2-Save-Editor 的 `items.json`（Apache-2.0），存档偏移也与该编辑器一致。两个文件保留了原来的 SPDX 行和出处注释（`n2_armor.py` 说明里提到的 `THIRD_PARTY_NOTICES.txt` 是换装器发行 ZIP 里的许可全文，没有收进本包）。3DMigoto 和 Nioh 2 Mod Enabler 由用户自备，本包不带它们的代码。
