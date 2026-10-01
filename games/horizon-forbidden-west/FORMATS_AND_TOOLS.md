# 格式与工具

以下数值都是 build `14835813` 的快照（`build-sensitive`），除非另有说明。

## 资源定位

- **组记录。** `LocalCacheWinGame\package\streaming_graph.core` 里每个流式组对应一条 64 字节的 StreamingGroupData 记录，第一个字段是组 ID。
- **工具的「模型 ID」是组数组下标，不是组 ID。** h2 工具要的是这条记录在组数组里的下标，写成十六进制；它不是 Odradek 显示的组 ID。
  - Beta 的模型组 ID 是 8761，下标是 `0xB2C4`，命令里写 `b2c4`。
  - 面部骨架在工具里的 ID 是 `719`。
  - 换 build 后，扫描 `streaming_graph.core.org` 中的 64 字节记录，按组 ID 重新算下标。
- **mod 文件命名为 `NN_OFFSET`**，后缀为 `.core`、`_mesh.stream` 或 `_texture.stream`。
  - NN 是流图文件表的十六进制下标，OFFSET 是十六进制偏移。
  - 本案输出 33 个文件：1 个 `02_19A7C73A.core`（b2c4 所在的 core），7 个贴图 stream，25 个网格 stream。
- **同一组贴图的各级 mip 按级别交错存在 stream 里**（观察结果）。

## 导入导出工具 h2_pc_mi_091（id-daemon）

本案用的是 0.9.1 版，exe 的 SHA-256 是 `871331ef2b60bac0ef78b6ebacdb2a51d6fb4a0810c01e45b899b78536bd78f1`。配套教程是 Johnny Dazzling 写的 Tutorial Edition 4（2026-03-21）。来源见 [工具来源](../../references/TOOL_SOURCES.md)。

- **运行位置。** 教程是把工具解压到游戏的 `LocalCacheWinGame` 里运行。本项目改为在 [干净根目录](#干净根目录) 的 `LocalCacheWinGame` 里运行。工具要读 `package\streaming_graph.core.org`，没有这个文件就定位不到资源。
- **导出：** `h2_pc_mi_091.exe b2c4 <lod>`，LOD 取 0–7。
  - 每个 LOD 产出若干个 `b2c4_<n>.ascii`，一个文件里有多个子网格，子网格名形如 `b2c4_<网格号>_…`；
  - 另外产出 `b2c4_skel_24.ascii`（身体骨架）和 `b2c4_materials.txt`。
  - 面部骨架单独导出：`h2_pc_mi_091.exe 719 0` → `719_skel_0.ascii`。
- **导入网格：** `h2_pc_mi_091.exe b2c4 <lod> <骨架 ascii> <网格 ascii> <网格号> 0`。
  - 网格 ascii 的开头要带骨架；构建脚本会自动写上。
  - 每成功导入一个子网格，输出一行 `success!`。日志里还有 `Assets read success!`，所以计数时要按**整行**匹配。
- **导入贴图：** `h2_pc_mi_091.exe <组> 0 <dds> <贴图号>`。
  - 每替换一级 mip 输出一行 `Replacing mip …`；
  - 只替换**同尺寸**的 mip，所以槽位尺寸是固定的；
  - 组可以是 b2c4 以外的贴图组（本案用到了 `1036` 和 `5e9`）。
- **工作目录里的改动会累积。** 工具每次运行都会重新导出全部 ascii，并把改动叠加到工作目录下的 core 和 `NN_OFFSET` stream 上。因此每次批量导入都要从原版 core 重新开始：`make_mod.py` 每次运行先复制 `02_19A7C73A.core.pristine`，并删除旧的 stream。

## ascii 格式

这是 XNALara 风格的纯文本格式，单位为米。本节的格式规则是 `invariant`；每顶点权重槽数是 `build-sensitive`。

- **骨架段（可选）：**
  - 第一行是骨数；
  - 每根骨占 3 行：名字、父骨索引、`x y z qx qy qz qw`。
- **网格段：**
  - 先是网格数；
  - 每个网格依次是：名字、UV 层数 `nuv`、贴图数，再跟若干「贴图名 + UV 层索引」对；
  - 然后是顶点数。每个顶点占 `5 + nuv` 行：位置、法线、颜色（4 个整数）、`nuv` 行 UV、骨索引、权重；
  - 最后是面数和三角形行。
- **约定：**
  - 坐标：x 指向模型右侧，y 向前，z 向上；
  - 三角形顺时针，glTF 是逆时针，写入时要交换两个角；
  - UV 原点在左下角，所以写 `v = 1 - v_glTF`；
  - 数值只接受 `NaN`，不接受 Python 默认写出的 `nan`。
- **权重槽：**
  - 每顶点的权重槽数沿用模板子网格：215 的 sm1 是 8 个，260 的 sm0 是 4 个；
  - 用不满的槽填最后一个有效骨，权重写 0；
  - 颜色和 UV 层数也照抄模板子网格。

## Beta（b2c4）槽位

**网格：**

| 网格 | 原用途 | 本案写入 |
| --- | --- | --- |
| 215 sm1 | 上身皮肤材质，8 权重 | Karin 的上身、手臂和手、上衣、头发、兽耳 |
| 260 sm0 | 下身皮肤材质，4 权重 | 臀、腿、裙子、尾巴、长袜、鞋 |
| 625 / 109 / 419 / 206 / 243 / 380 / 529 / 50 | 面部皮肤 LOD0–7，绑定面部骨架 719 | Karin 的头（脸页），每个 LOD 写同一份 |
| 其余 LOD0 子网格（服装、头发 633、眼球、睫毛等） | — | 塌缩隐藏 |
| LOD1–7 中绑定 719 的面部网格 | — | 塌缩隐藏 |
| 身体 LOD1 及以上 | — | 保持原版：远处可能显示 Beta 的身体 |

这些网格绑定面部骨架 719（来自导出日志，LOD0–7）：625、514、160、109、644、537、419、267、240、206、193、117、82、611、243、643、165、522、380、157、529、50。

下身之所以只放腿、臀和下装，是因为 260 每顶点只有 4 个权重，手部需要更多；按 z 高度切分的早期做法会把手分到下身。

**贴图：**

| 组_编号 | 尺寸 / 格式 | 原用途 | 本案写入 |
| --- | --- | --- | --- |
| b2c4_240 | 2048 BC1 | 脸颜色（材质 set 19） | 脸页 |
| b2c4_1A | 2048 BC7 | 脸法线 | 平坦法线 `(128,128,255,128)` |
| b2c4_D1 / 45 / 98 | 1024 BC1 | 面部细节层（按材质推断） | 中性色 `(129,128,129)` |
| b2c4_246 / 1CD / E0 | 1024 BC6H_UF16 | 面部细节层法线（按材质推断） | 中性法线 `(127,127,255)` |
| 1036_2 | 2048 BC1 | 身体皮肤颜色 | 身体页 |
| 1036_1 | 2048 BC7 | 身体皮肤法线；B 通道近似光泽（原版皮肤中位数约 64，指甲更亮） | R=G=128，B 为按材质给的光泽，A=255 |
| 5e9_8 / 5e9_9 | 1024 BC1 | 皮肤遮罩 | 中性 `(126,0,74)` |

- **stream 位置：** 脸的颜色和法线在 `36_71EBC000`，皮肤的颜色和法线在 `28_03C02000`，两张遮罩在 `27_2D0C1000` 和 `27_2D00D000`。
- **服装颜色槽不用。** 上衣和裤子的颜色槽只有 512，太小，所以服装也画在身体页上。参照 mod 的服装颜色放在这些 512 槽里。
- **细节层置中性的原因**（`case-derived`）：不置中性的话，Beta 的面部细节会按新 UV 叠到 Karin 脸上。

## SkinInfo：CsNbtGen → VsNbt

- **问题：** 面部网格 625、109、514（sm0 和 sm1）、644（sm0 和 sm1）的 SkinInfo 部件类型是 `CsNbtGen`（7）。这类部件由 GPU compute pass 按 `VertexComputeNbtCount` 重算法线和切线。导入工具换了顶点缓冲，但不更新这个计数，于是计算越界，读档时卡死。
- **修法：** 把类型改成 `VsNbt`（5），计数设为 -1。参照 mod 的 core 对 625 和 109 做了同样的修改，这两个正是它换了几何的面部 LOD；514 和 644 它没有改。
- **定位：**
  - 在 core 里搜索原版的 (VertexCount, VertexComputeNbtCount) int32 对，结果必须唯一；
  - 类型字段在这对数之前 24 字节处，值必须是 7。
- **原版计数对：**

  | 网格 | (VertexCount, VertexComputeNbtCount) |
  | --- | --- |
  | 625 | (22895, 22816) |
  | 109 | (5871, 5775) |
  | 514 sm0 | (4626, 4459) |
  | 514 sm1 | (960, 866) |
  | 644 sm0 | (1776, 1710) |
  | 644 sm1 | (424, 370) |

- **适用范围：** 本案把这 6 个部件全部改了，包括塌缩隐藏的 514 和 644，没有逐个 A/B。按机理，真正必须改的是顶点数变了的网格（`hypothesis`）。

## 包围盒

导入工具保留原版的 LocalBounds，而 Karin 的耳朵、双马尾和尾巴超出了原版范围。

- `patch_bounds.py` 放大 4 个盒子：
  - 每个盒子按原版最小角的 3 个 float 查找，结果必须唯一；
  - 放大到包含对应的 Karin 子网格，再加 2 cm 余量；
  - 盒子的名字 `multi23`、`upper446`、`lower57`、`face87` 是本项目自己起的标签。
- **证据等级：** 这是预防性改动，没有做单独的 A/B 归因（`hypothesis`：不改的话，视锥剔除可能在镜头边缘提前剔掉超出部分）。

## HFW Mod Manager（KingJulz，0.9.8）

- **安装 mod：** 把 mod 文件平放在 `<游戏目录>\mods\<名字>\` 下，同目录放 `modinfo.json`，可选 `preview.png`。在管理器里可以把 zip 拖进 Mods 列表，也可以手动解压后点 Refresh。
- **Pack Mods：** 合并所有勾选的 mod，写入 `LocalCacheWinGame\package\mod\`（本机观察到 `package.52.00.core.stream` 每次打包都会更新），并改写 `streaming_graph.core`；原版保留为 `streaming_graph.core.org`。
- **Characters：** 在 Beta 上点 Activate，会在游戏根目录写入 `mod_NPC.ini`：

  ```ini
  [[CharacterOverride]]
  RootUUID = "8c75b85f-cd45-d547-8a94-5fecc14abeee"
  VariantUUID = "e13d2679-0d1c-724a-9dd4-eb6cb4610a13"
  ```

  点 Reset to Aloy 撤销。游戏如何读取这个文件，本项目没有调查。
- **冲突：** 两个替换 b2c4 的 mod 改的是同一批文件，必须只勾一个。
- **启动弹窗：** 管理器启动时弹出 `Failed to initialize offsets … HFW Gameplay Tweaks and Cheat Menu`，这是游戏目录里 Nukem 作弊菜单的 `winhttp.dll` 加载进了管理器进程。点确定即可，与 mod 无关。

## 干净根目录

Pack Mods 之后，游戏目录里的流图是改过的。在改过的目录上，Odradek 导出 cast 会失败，导入工具也会把 mod 内容当成原版。解决办法是另建一个根目录：

```
<干净根>\HorizonForbiddenWest.exe                       硬链接到游戏
<干净根>\LocalCacheWinGame\package\package.*.core      硬链接到游戏
<干净根>\LocalCacheWinGame\package\dlc, en              目录链接到游戏
<干净根>\LocalCacheWinGame\package\streaming_graph.core      硬链接到游戏的 streaming_graph.core.org
<干净根>\LocalCacheWinGame\package\streaming_graph.core.org  同上
<干净根>\LocalCacheWinGame\h2_pc_mi_091.exe             工具
<干净根>\LocalCacheWinGame\02_19A7C73A.core.pristine    第一次导出得到的原版 core，独立副本
```

- **只允许新文件落进这个目录。** 硬链接文件和游戏本体是同一份数据，任何程序都不能写它们。
- **工具输出不碰硬链接。** 导入工具写出的 core 和 stream 都是新文件；`make_mod.py` 写 core 时复制的是 `.pristine` 这份独立副本。
- **可以随时删掉。** 删除这个目录不影响游戏本体。

## Odradek（ShadelessFox）

本案使用 CI 构建 1.0-SNAPSHOT，用来查组 ID、材质、贴图编号，并导出 json 和 `model.cast` 供 Blender（Cast 插件）查看。

- 它只用于勘察，不参与构建；
- 要指向干净根目录才能正常导出。
