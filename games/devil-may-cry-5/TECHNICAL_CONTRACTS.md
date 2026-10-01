# 技术合同（DMC5，build 24901913）

文件版本号和字段布局是 `build-sensitive`；矩阵约定和工具行为是 `invariant`（对所用工具版本而言）。

## 1. 资源版本与工具

| 资源 | 后缀 | 读写方式 |
| --- | --- | --- |
| 网格 | `.mesh.1808282334` | RE Mesh Editor 0.44（Blender 4.0.2）；脚本里直接用插件模块 `file_re_mesh` 读 |
| 材质 | `.mdf2.10` | 自写最小改动编辑器（§5）；RE Mesh Editor 的 `file_re_mdf` 只用来读 |
| 贴图 | `.tex.11` | texconv → 插件模块 `DDSToTex`（版本 11）→ 改写头部 `0x1C`（§6） |
| 物理 | `.chain.21` | RE Chain Editor 14.0 的 `file_re_chain` 模块读写，往返无损 |
| 骨架 | `.fbxskel.3` | 自写：只改骨位置（§4） |
| 场景 | `.scn.19` | 本项目只比对，不修改 |

工具的坑：

- Blender 无界面模式（`-b`）下，RE Mesh Editor 调用 `wm.console_toggle()` 会触发
  `EXCEPTION_ACCESS_VIOLATION`。在工作副本里把这一调用改成 `pass`。
- `file_re_mdf` 读 v10 时，纹理条目大小要用 24（`version < 13` 时 `TEXTURE_ENTRY_SIZE = 24`）。
- Blender 4.0 重新导出会重算一部分自定义法线（PT 的 V 网格约 18%，主要是脸部的卡通法线）。
  原样转换的网格可以把源网格的法线 / 切线流（每顶点 8 字节）按顶点顺序搬回去，再断言一致。
- 导出参数：`preserveBoneMatrices=True`、`rotate90=True`、`exportAllLODs=False`、
  `autoSolveRepeatedUVs=True`、`preserveSharpEdges=False`、`useBlenderMaterialName=False`。

## 2. 矩阵与骨骼约定（invariant）

- RE 矩阵是行主序，平移在第 3 行；`world = local @ parentWorld`（行向量）。
- RE Mesh Editor 把 `reMeshWorldMatrix` / `reMeshLocalMatrix` / `reMeshInverseMatrix` 存在骨骼自定义属性里，
  `preserveBoneMatrices` 导出时直接用这些属性。新增骨骼要三者一起写，Blender 编辑骨矩阵为
  `ROT90 @ Matrix(world).transposed()`。
- chain 碰撞体的端点是「关节局部偏移」：`p_world = [pos, 1] @ world(joint)`。本项目涉及的
  Hip / Waist / Thigh / Shin 的 bind 旋转都是单位阵，局部偏移等于世界偏移。

## 3. 角色槽位（build-sensitive）

| 角色 | 身体网格槽位 | 只换 MDF 的变体 | 其它 |
| --- | --- | --- | --- |
| Nero | `pl0000_nero`、魔人 `pl0010_nero_majin` | 配色 `*_c00_*`、脏污 `pl0030` / `pl0031` | 头 `01_head`、头发 `03_hair` / `13_hairhood`、各义手槽 |
| Dante | `pl0100_dante`、魔人 `pl0110_dante_majin`、真魔人 `pl0120_dante_shinmajin` | 配色 `*_c00_*`、脏污 `pl0130` / `pl0131` | 帽子发型 `04_hair_fausthat` / `14_*`；魔人翅膀 `04_wingopen` / `05_wingclose` |
| V | `pl0200_v`、裸身 `pl0210_v_naked`（仅 M12 一段过场） | 配色 `pl0200_c00_v`、裂纹形态 `pl0230/0231/0232`（共用 `pl0200` 网格） | `01_head`、`03_hair`、`13_hair`、`11_head_event` |

PT 包还带着部分武器、过场 shader 和 `scene/players` 文件；Original 包原样继承这些文件，不做修改。

- 标题画面：Nero 在左、Dante 居中（背对镜头、持剑）、V 在右（持手杖）。三个人同屏，一次启动能看完三个身体。
- UI 立绘：脸部特写 `ui0040_01/02/03`（Nero / V / Dante），全身 `ui2100_10/12`、`20/22`、`30/32`。
  PT 包只换这几张，Original 包照做。
- 链组按**链尖节点名**解析。网格里没有这些骨时，链组不生效。V 自带的头发 chain 引用的骨在空网格里
  不存在，所以保留原样也不会动。

## 4. fbxskel（case-derived：跟随 PT mod）

两个 PT mod 的 fbxskel 骨位置都等于各自身体网格的 bind local（复核：Nero 71 根共有骨、Dante 64 根，
差值为 0），旋转不变。相对原版，Nero 改了 67 / 77 根，Dante 改了 49 / 64 根。**Hip 保留各角色原版位置**
（Nero `(0, 1.068, 0)`，Dante `(0, 1.11, 0.03)`），其余骨按 Karin 比例。

V 照做：Hip 放在 V 原版的 `(0, 1.08, 0)`，Hip 的子骨在世界空间补偿回原位，再按网格 local 写 fbxskel。
骨记录从 `boneOff + i * 0x40` 开始，位置在 `+0x10`（3 × float），写入网格 `localMatrix` 的第 3 行。
只在 fbxskel 里存在的骨保留原值，父子关系不一致时报警。先用这个方法重做 Nero 的 fbxskel，确认和原 mod
一致，再用到 V 上（改了 66 个位置）。

推论：同一套 Karin 比例的网格，Hip bind 随目标角色不同。挂在 Hip 上的东西（chain 碰撞体偏移等）
要按身体分别计算。

## 5. MDF v10（invariant 布局）

- 头 16 字节；材质条目 64 字节（`nameOff, hash, propBlockSize, propCount, texCount, shader, flags,
  propHdrOff, texHdrOff, propDataOff, mmtrOff`）；纹理条目 24；属性条目 24。字符串是 UTF-16 加双零结尾。
- flags 在材质条目 `+28`，bit0 = 双面。
- 最小改动编辑：原字节一律不动；新字符串（2 字节对齐）和克隆出来的属性块（16 字节对齐）追加到文件末尾，
  用绝对偏移引用。插入材质条目时，所有绝对偏移整体平移 `64 × k`，每个克隆条目拿到私有的纹理头 / 属性头 /
  属性数据。改名要同时写 `hash_wide`。
- 材质名必须覆盖目标角色原有的全部材质名。网格里用零面积的占位子网格保留这些名字（例如 V 的
  `m_handaccessories / m_pendant / m_bone / m_handR / m_chain`）。

## 6. TEX .11（build-sensitive 头字段）

texconv 编码 → `DDSToTex(…, 11)` → 按同类贴图改写 `0x1C` 处的 u32：

| 用途 | 格式 | `0x1C` |
| --- | --- | --- |
| albm（颜色） | BC7_UNORM_SRGB（fmt 99） | `0x480` |
| atos | BC7_UNORM（fmt 98） | `0x400` |
| NRMR | BC7_UNORM（fmt 98） | `0x500` |
| UI 立绘 1024² | BC7_UNORM_SRGB | `0x700` |

`0x1C` 的语义没有逆向，按原生或 PT 同类贴图照抄。PT 包里 NRMR 是 sRGB（fmt 99），属于错误，不要照抄。

## 7. PAK 与 Fluffy（build-sensitive）

- 用 `ree-pak-cli` 配 `DMC5_STM_Release.list` 解包；基础包加 `patch_001..008` 按优先级合并。
- Fluffy 的 `installtype=invalidate` 会把被替换文件在 PAK 目录里的哈希清零，原文件仍在 PAK 里。
  需要原版文件时，按偏移读出哈希为 `00000000` 的条目（压缩类型 0 原样、1 raw deflate、2 zstd）。
- Fluffy 包格式：zip 顶层是 mod 名文件夹，里面有 `modinfo.ini`、截图和 `natives/`。
  游戏目录的权威记录是 `Games/DMC5/installed.ini`。
- 用户的 PT 包还有一个惯例：作者签名藏在头部 MDF `m_teeth` 的 NormalRoughnessMap 槽里，指向
  `*_sign_albm.tex`。新包保留这个签名，只重绘标题行。
