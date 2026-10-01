# chain .21 物理：结构、链组映射、裙摆碰撞

格式是 `invariant`（DMC5 `chain .21`）；参数值是 `case-derived`。DMC5 用的是老式 chain，
不是 [鬼武者](../onimusha-way-of-the-sword/CHAIN2_PHYSICS.md) / [PRAGMATA](../pragmata/CHAIN2_PHYSICS.md)
的 chain2，字段名相近但文件不同。

## 1. 文件结构（RE Chain Editor 14.0 的 `file_re_chain` 可往返）

- 表头：各表计数，`calculateMode = 1`，`calculateStepTime = 2.0`。
- setting：按 `id` 引用。字段有重力、`damping`、`springForce`、`hardness`、`reduceSelfDistanceRate`、
  风参数，以及 `ChainCloth.cfil` 碰撞过滤器路径。
- 模型碰撞体：`jointNameHash` / `pairJointNameHash`（骨名的 murmur3 wide 哈希取低 32 位），端点为各自关节的
  局部偏移 `pos` / `pairPos`，`radius`，`chainCollisionShape = 2`（胶囊）。改了条数要同步表头的
  `chainModelCollisionCount`。
- group：一条链一个 group，用链尖名字（`terminateNodeName` + 哈希）解析，从链尖沿父骨往上取 `nodeCount` 个节点。
  节点字段有 `angleLimitDirection`（四元数）、`angleLimitRad`、`collisionRadius`、`collisionShape`
  （0 无，1 球，2 节点到子节点的胶囊）。
- link：两条链之间的横向约束（`distanceShrinkLimitCoef` / `distanceExpandLimitCoef`），用于裙片成环。

## 2. PT 链的约定（case-derived，沿用）

- 链骨和它们的父骨世界旋转都是单位阵，所以 `angleLimitDirection` 直接取「把 +X 转到静止线段方向」的
  世界空间四元数（最短弧）。Karin_Original 的链挂在单位旋转的 `KO_Base_*` 下，同样成立。
- setting：`0` 大衣 / 裙（重力 −20、`springForce 0.007`、`damping 0`），`5` 短发，`6` 长发 / 尾巴（`1` 在 Karin_Original 的链里没有被引用）。
- 12 个身体碰撞胶囊，都在骨轴上：Hip–Chest 0.08、Chest–Neck 0.071、Neck–Head 0.049、
  Waist–Thigh ×2 0.08、Thigh–Thigh 0.08、Thigh–Shin ×2 0.08、Neck–UpperArm ×2 0.036、UpperArm–Forearm ×2 0.057。
- 原版 V 大衣可作对照：重力 −9.8、`damping 0.1`、`springForce 0.001`；胶囊 0.11–0.12，带局部偏移
  （例如 Hip 上一条横向胶囊在 Hip 下方 8 cm）；大衣节点半径 0.025–0.055，角度限制约 0.79。

## 3. Karin_Original 的链组

group 和节点记录从同类 PT group 克隆，只改名字、节点数、方向和角度限制：

| 类别 | 源链 | 模板 PT group | setting | 角度限制 |
| --- | --- | --- | --- | --- |
| 双马尾 | `Hair_tail_L/R`（6 节） | `BR_HairCloth00_10` | 6 | `0.698 × k`，上限 4.189 |
| 尾巴 | `Tail`（6 节） | `TailCloth_05` | 6 | `0.524 × k`，上限 2.618 |
| 侧发 | `Hair_side_L/R`（3 节） | `Karin_R_HairCloth_02` | 5 | 0.524，之后 1.047；节点半径 0.02 |
| 耳朵 / 缎带 / 前发 | `Ear_*`、`Ribbon_L/R`、`Hair_front*` | `Karin_F_HairCloth00_01` | 5 | 0.524 |
| 小飘带 | 上衣缎带、鞋标签、手腕缎带、吊带缎带 | 同上 | 5 | 0.524；**碰撞关**（出生就嵌在胶囊里） |
| 裙子 | 16 条链 × 3 节（前 `Skirt_0`、后 `Skirt_8`、左右各 7） | `K_CoatCloth00_03` | 0 | 见 §4 |

相邻裙链之间加 link，围成一个环，记录克隆自 PT 大衣的 link。合计 37 组、130 个节点、16 条 link。
闸门：每个带碰撞的节点及其节点胶囊在静止姿势下不进入任何身体胶囊（沿线段取 9 个采样点）。

## 4. 裙摆穿模：v1.0 → v1.1

**症状**（用户实战截图，v1.0）：站立和跑动时，大腿和臀部从裙子后面露出来。标题画面看不出这个问题：
Dante 是背面，但尾巴挡住了。

**诊断**（离线测量，Nero 网格）：

- 静止时裙子离身体只有 4–8 cm，后腰顶部只有 1–2 cm。
- 大腿表面离骨轴约 0.115，PT 胶囊只有 0.08。臀部完全没有被覆盖（Waist–Thigh 胶囊在骨轴上）。
- 判据是「顶点到最近胶囊的距离 − 胶囊半径 ≤ 节点半径 0.03 − 余量 1.5 cm」。按这个判据，
  臀部和大腿顶点有 54% 落在碰撞范围之外，臀部最多差 6 cm。
- setting 0 的重力 −20、回弹 0.007：裙子会一直下坠，直到碰到这些细胶囊。

**拟合方法**（`ko_skirtfit`，离线）：

- 身体点：不属于裙子、主权重在 Hip / Waist / Thigh 上、高度 0.80–1.20 的顶点。
- 约束一：所有身体点满足上面的判据。
- 约束二：所有带碰撞的静止节点（含节点胶囊）不进入身体胶囊。
- 对骨盆胶囊的位置、半宽、半径，以及大腿 / 裆部胶囊的半径和偏移做网格搜索，两个约束一起比较。

**v1.1 取值**：

| 项 | 值 |
| --- | --- |
| 新增骨盆 / 臀部胶囊 | 两端都挂 Hip，世界端点 `(±0.05, 1.09, 0)`，半径 0.11。局部偏移按身体算：Nero `y +0.022`，V `+0.01`，Dante `y −0.02, z −0.03` |
| Waist–Thigh ×2、Thigh–Thigh、Thigh–Shin ×2 | 半径 0.08 → 0.10，大腿端点 `z −0.01` |
| 裙 setting 0 | 重力 −20 → −9.8，`damping` 0 → 0.1，`springForce` 0.007 → 0.025 |
| 裙节点角度限制 | 0.698 / 1.047 / 1.396 → 0.20 / 0.60 / 0.80 / 0.80（腰口一段基本不动） |
| 裙节点半径 | 0.03 全段 → 根 0（形状 0）/ 0.01 / 0.03 / 0.03 |
| 尾巴根节点 | 碰撞关：固定的根段本来就从臀部里长出来，新骨盆胶囊会让它静止时陷入 4.5 cm |

结果：所有臀部和大腿顶点都在碰撞范围内，余量至少 0.7 cm（45 个后腰顶部顶点在 0.7–1.5 cm 之间），
静止穿透为 0。

被放弃的候选：骨盆胶囊放在 `(±0.07, 1.098, −0.01)` 可以做到 1.5 cm 余量全覆盖，但静止时会把后侧裙片顶起
1.7 cm，改变外形。取余量小一点、不顶起裙子的版本。

**证据**：v1.1 实战后用户确认「看起来好了」。碰撞体、setting、角度限制和节点半径是一起被接受的，**没有逐项归因**。

**每个身体一份 chain**：骨盆胶囊挂在 Hip 上，而 Hip 的 bind 在 Nero `(0,1.068,0)`、V `(0,1.08,0)`、
Dante `(0,1.11,0.03)` 各不相同。打包时按身体名对号入座（`pl0000/0010/0100/0110/0120/0200.chain.21`）。
大腿、腰的位置三者相同，偏移可以共用。

如果大步动作时仍有穿模，先加粗大腿胶囊或提高回弹；如果裙子显得太硬，先降回弹。每次只动一类参数。
