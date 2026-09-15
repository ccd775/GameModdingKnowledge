# 技术合同（Onimusha: Way of the Sword）

> 类别标注：`invariant` = 与 build 无关的工程规则；其余为 `build-sensitive` 快照。
> 快照绑定：Steam 正式版 App `2638890` / build `24769601`；历史 Demo App `3974650` /
> build `23977550`。新 build 必须重新提取与复验。

## 1. 资源版本（build-sensitive）

| 资源 | Demo `23977550` | 正式版 `24769601` |
| --- | --- | --- |
| Mesh 扩展名 | `.mesh.251215606` | `.mesh.260209350` |
| Mesh **内部**版本 | `250203152` | `250203152`（未变） |
| GPU Cloth | `.gpuc.251215760` | `.gpuc.260209505` |
| TEX | `.tex.251111100` | 未变 |
| MDF | `.mdf2.51` | 未变 |
| Chain2 | `.chain2.17`（PFB `.18` 显式消费） | 未变 |
| FBXSKEL | `.fbxskel.7` | 未变 |
| 官方 PAK | KPKA `4.2` feature `0x28` | 未变 |
| Mod PAK | KPKA `4.2` feature `0x00` | 未变 |

`invariant` 方法：Mesh/GPUC 的新后缀号不必靠猜，可由 PAK TOC 的 murmur3
`(lower, upper)` 对**反推**得到；先用已知量（`mdf2 -> [50, 51]`、`fbxskel -> [7]`）
自检反推器再上未知项。

跨 build 迁移的实测结论：Demo → 正式版三个可见槽的消费者骨架**逐位相同**（骨数、
骨名、`parentIndex` / `nextSiblingIndex` / `childIndex`、`boneRemapList` 与
local/inverse/world 三套矩阵全同），已冻结的 Mesh **只改扩展名**即可回读通过
（`RENAME-ONLY RETARGET: PASS`）。MDF51 donor 与 TEX 也逐字节相同。

## 2. 工具适配层（build-sensitive，但踩坑模式是 invariant）

- RE Mesh Editor `0.66` 不认识 `251215606` / `260209350`，会**错误近似到相邻世代**
  （本例为 RE9）。必须在导入/导出前安装显式映射
  `251215606 -> MHS3 remap -> internal 250203152`，并把该扩展名加入**六权重**压缩
  集合。`00/10` 槽可能带第二组 ExtraWeight 缓冲，按八权重处理会错。
  `invariant`：**插件的「版本近似」是静默的**，新后缀号必须显式声明，否则得到的是
  结构上自洽但语义错误的读写。
- MDF51 在本作**不是** 108 字节材质头，实包是 **104 字节**：在 MDF50 的
  `propertyCount` 之后插入一个 uint32 MMTR lookup。不得让旧 `file_re_mdf.py` 直接
  写 `.51`，必须走专用转换器。
- TEX `251111100` 不是 GDeflate：ALBD = `BC7 sRGB / [0,0]`，NRRO = `BC7 linear /
  [128,6]`，ALP = `BC4 / [0,0]`。

## 3. 角色槽位图（build-sensitive）

正式版 `ch001_00` 有 `00, 01, 02, 10, 20, 60, 70..75`（Demo 只有 `00/01/10/20/60`），
另有独立的 `ch001_01`，仅 `00` 槽。

| 模型 | 骨数 | 材质数 | 说明 |
| --- | ---: | ---: | --- |
| `ch001_00_00` | 317 | 14 | 服装 A，含 `Doufuku*` 布料链 |
| `ch001_00_10` | 423 | — | 脸 |
| `ch001_00_20` | 134 | — | 头发 / 头部附件 |
| `ch001_01_00` | 269 | 13 | 服装 B，含 `tasuki` / `Sode` / `HakamaYure` 链 |
| `ch001_00_02` | 26 | — | 小配件 |

`ch001_01` 没有自己的 `fbxskel`，复用 `ch001_00_90`。

**实机当前渲染的是 `ch001_01_00`（服装 B）。** 两套都必须替换才能覆盖全部场景 ——
本项目曾在一次发行里漏掉服装 B，只靠打包器的部署一致性闸门才拦下来。

替换策略：`00` 承载身体/服装/尾巴，`10` 承载脸，`20` 承载头发/头部附件，`01/60` 用
塌缩的屏蔽 Mesh（`01` 另配 4 字节 `GCLO` GPUC stub）。

## 4. 骨绑定合同（invariant，已推翻旧结论）

> 早期 SOP 写「三个可见槽必须使用各自原生消费者骨序」，并当作硬约束。**这条被过度
> 推广了。**

实机证据：把 `317` 骨的身体 Mesh **原样**（零重映射）部署到 `269` 骨、骨序完全不同
的 `ch001_01_00`，姿态、动作跟随、手臂腿脚全部正常。

真实约束是：

- **Mesh 加权的骨必须在运行时骨架里按名字存在，且 rest 矩阵一致。**
- 骨序、骨数、未加权骨的差异都不影响。

与早期反例不矛盾：往 slot 20 追加身体骨后不被动画，是因为那些骨在头发部件的关节集里
**根本不存在**，按名字也绑不上。

实用推论：为新槽位/新服装做替换时，只要加权骨集合在目标骨架里齐全，同一份 Mesh 可
直接复用，无需重建。

## 5. 比例与 rest 合同（case-derived，但决策模式是 invariant）

- 所有可见几何共用**一次**相似变换 `target Hip @ uniform_scale @ inverse(source Hips)`，
  缩放取 `target Hip Z / source Hips Z`，使源 `Z = 0` 保持游戏地面。donor 只提供运行时
  骨名、顺序、父级与轴向。
- 与原生动画/IK 冲突的区域改用 **hybrid 闭包**：手臂 132 骨 + 腿部 40 骨恢复为原生
  全局 rest（并集 172，其余 145 骨保持 source-proportion baseline），再对实际加权的
  46 骨（38 臂 + 8 腿）做局部 aim 方向修复。详见 [骨骼与几何](RIG_AND_GEOMETRY.md)。
- 面部 `Eye.L/R` 权重稳定映射到 `Head`，不使用原生眼球枢轴 —— 脸绑单骨的代价是没有
  表情和独立眼动，这是**已接受的**边界，不是缺陷。

## 6. 网格导出合同（invariant）

- 源 Shape Key（如隐藏脚面的 `Foot_OFF` / `Toe_OFF`）必须先烘焙再删除；隐藏面要按
  **锁定面积合同**精确删除（本例 3,888 个三角形），并保留共享的可见顶点。
- 导出前按实际半精度 UV、量化 normal/tangent、颜色 corner payload **拆点**。
- 单材质大网格先按最多 18,000 三角形预分块；最终每个 submesh 不超过 60,000 顶点，
  `has32BitIndexBuffer` 必须为 `0`。
- 法线用与位置相同的加权 affine delta 的 inverse-transpose 后归一化；位置验收通过后
  才拆成最终 export-corner topology，冻结可表示的 corner normal 并重算 tangent。
  分块不得改写 position/UV/color/weight/material/packed-normal 静态 payload。

## 7. 材质绕过（case-derived，双服装已实机确认）

本作的身体材质由 PFB 加载的 `*_mmi/mpi.user.3` 按 **Murmur3 名字哈希**命中并写参；
原生 Body 材质名会被强制覆盖成近黑。绕过方法是让所有非脸表面使用一个**原生消费者
从不命中**的材质名（本例 `ch001_00_20_hair_Mat`）。

验证方法（每个 build、每套服装都要重做）：对全部消费者 `user.3` 做名字与哈希扫描，
要求目标名 **0 命中**，同时确认原生名的命中数全部落在预期的 mmi 文件里。

残留风险（`hypothesis`，静态无法排除）：没有该 build 的 RSZ schema，无法证明消费者
不会按 **material index** 或整个 slot 写参。只能实机确认。
