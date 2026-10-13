# Kawaii 物理（KawaiiPhysics-SB 1.11）

最终构建：28 个 Kawaii 节点（16 片裙摆、尾巴、双马尾 ×2、侧发 ×2、头饰 ×2、前发 ×3、狐耳 ×2），全部挂在后处理
AnimBP 里 ControlRig 和 reprop 之后。用户验收的是整套参数，没有逐项归因。

## 1. 物理链必须落在游戏骨架的骨上（invariant，本作）

`FAnimNode_KawaiiPhysics::InitModifyBones` 遍历的是 `BoneContainer.GetSkeletonAsset()->GetReferenceSkeleton()`，即
**USkeleton 资源**的参考骨架，而不是网格的。后果：

- 网格独有的骨（不在 `CH_P_EVE_01_Skeleton` 里）永远不会被模拟，节点静默地什么也不做。
- 在编辑器里一切正常：导入时这些骨被并进了 dummy 骨架。所以编辑器预览不能证明运行时有物理。
- 骨架里有但网格里没有的子骨会被跳过；只有 `DummyBoneLength > 0` 时才会补一根虚拟末端骨。

做法：把 Karin 的 28 条链改名，落到游戏骨架已有的配件链上，父骨与骨架一致：

| Karin 链 | 游戏骨架链（父骨） |
| --- | --- |
| 裙 中前 / 中后 / 左右 A–G | `Ab_C_SkirtN_00..`、`Ab-Bc-SuiteA-01..`、`Ab_{L,R}_Skirt{A..G}_00..`（`Bip001-Pelvis`） |
| 尾巴 | `Ab_Tail00..06`（`Bip001-Pelvis`） |
| 双马尾 | `Ab-{L,R}-HeadTail01..07`（`Bip001-Head`） |
| 侧发 / 头饰 / 前发 | `Ab_Hair_Side_{l,R}_01..`、`Ab_Hair_K{L,R}01..`、`Ab_Hair_Fr{_L,,_R}_01..`（`Bip001-Head`） |
| 狐耳 | `Ab_Hair_F{L,R}01..03`（`Bip001-Head`） |

前提检查（每次换 build 都要重做）：链在骨架里是线性的、长度不短于 Karin 的链；这些骨在 EVE 动画里没有轨道
（idle、run 只有 Bip 和 Ab/Dm 辅助骨）；`BtoB_CtrlRig` 不驱动它们。Karin 的每条链以一根无权重的末端骨收尾，
所以 `DummyBoneLength` = 0。

定位过程见 [排障手册](TROUBLESHOOTING.md) 的「完全没有物理」。

## 2. 节点与预设

- Kawaii 把 RootBone 固定在动画姿态，模拟它的全部后代：**每个链头一个节点**。用一个组根骨挂多条链，会让各链头一起摆。
- RootBone 的位置固定，但**旋转会跟着子关节转**（父骨朝向模拟后的子关节）。挂在根骨上的顶点会绕根骨头部摆动。
  这一点决定了裙子从哪根骨开始模拟（§5）。
- 游戏默认值（126 个裙摆节点的统计）：stiffness 0.05、damping 0.1、world damping 位置/旋转 0.8、wind 0.3、
  裙摆半径 3、无角度限制，`BoneForwardAxis` = Y_Negative，`TargetFramerate` 60。

最终预设（`case-derived`）：

| 预设 | stiffness | damping | 半径 | 角度限制 | 碰撞 | 风 |
| --- | --- | --- | --- | --- | --- | --- |
| 裙摆 | 0.06 | 0.10 | 3.0 | 无 | 身体胶囊 | 0.3 |
| 尾巴 | 0.05 | 0.12 | 2.0 | 无 | 腿部胶囊 | 0.3 |
| 双马尾 | 0.04 | 0.12 | 3.0 | 无 | 身体胶囊 + 头部球 | 0.3 |
| 侧发 | 0.10 | 0.15 | 1.5 | 35° | 身体胶囊 + 头部球 | 0.2 |
| 头饰 | 0.10 | 0.15 | 1.0 | 35° | 头部球 | 0.2 |
| 前发 | 0.20 | 0.20 | 1.0 | 20° | 无 | 0.1 |
| 狐耳 | 0.18 | 0.15 | 1.0 | 22° | 无 | 0.15 |

狐耳最初用 0.30 / 12°，用户觉得几乎不动，改成上表的值。

模拟步骤（读源码确认）：速度 × (1 − damping) → 风 → 跟随组件移动/旋转的 (1 − world damping) → 重力 →
按 stiffness 拉回 `父骨模拟位置 + 姿态偏移`（`1 − (1 − S)^(帧率×dt)`）→ 球、胶囊、平面碰撞 → 角度限制 → 恢复骨长。

## 3. 身体碰撞胶囊

胶囊 = DrivingBone 的组件空间变换 × (OffsetLocation, OffsetRotation)，轴是局部 Z，从中心向两边各延伸 Length/2。
关节落在胶囊里时被推到「胶囊半径 + 关节半径」处。FRotator → 四元数用引擎的公式（Pitch、Yaw、Roll 的半角正余弦组合）。

- 起点：复制游戏 `CH_P_EVE_09_V02` 裙摆节点的胶囊（Spine/Spine1/Spine2、Pelvis、上臂/前臂、手、大腿、小腿），
  腿上的按 reprop 的 k 缩短。
- **不要原样照搬。** EVE 的胶囊按 EVE 的身体定：Pelvis 胶囊半径 14.9，Karin 静止的裙子关节陷进去最多 6.5 cm。
  Kawaii 每帧把这些关节往外推，在尾巴根高度形成一圈鼓包。
- 拟合规则（`ue_build_abp.py`）：对每个胶囊，取所有会和它碰撞的链的**被模拟关节**（不含固定的链头），
  在 bind 姿态下让每个关节离胶囊至少「关节半径 + 0.5 cm」；半径小于 2 cm 的胶囊丢弃。日志里记下由哪个关节决定。
- 最终（只模拟裙摆下摆时）：Pelvis 14.9 → 14.0，大腿 9.5 → 8.3，其余不变。

注意：胶囊只挡关节，挡不住关节之间的布（§5）。

## 4. 裙摆跟腿（权重 + BoneDrivenController）

Kawaii 沿径向把关节推出胶囊，抬起的大腿可能把一片裙子留在自己下面；SB 的 Kawaii 1.11 没有 BoneConstraints。
所以裙摆跟腿主要靠权重：

- 前面和侧面：髋关节 +2 cm 以下的顶点，从 `Bip001-?-Thigh` 分到一部分权重，到下摆最多 0.9（`0.9·h^1.2`）。
  角度因子 `(c + 0.5) / 0.5`（c = 相对髋关节的前向余弦，截断到 0–1）：从正前方到侧面全额跟随，到 120° 衰减为 0。
  最多 4 个影响骨。
- 后面：大腿屈曲时，后片如果跟着大腿，会被甩进腿下面。所以后片改挂网格独有的辅助骨 `KO_SkirtExt_L/R`：
  它们挂在 `Bip001-Spine`（大腿的父骨）下，位于髋关节，局部旋转为单位。AnimBP 里每侧两个 BoneDrivenController：
  源 = 大腿，先 RotationZ（外展）截断到 ±60，再 RotationX（后伸）截断到 [0, 120]。轴和符号从参考姿态推导并断言：
  Spine 的 X 是侧向轴，绕它 +30° 是屈髋，所以 Roll > 0 表示后伸。屈髋时辅助骨不动。
- 按皮肤补足：裙子贴近皮肤的地方，至少要和身下皮肤动得一样多。每个裙子顶点的跟随权重，提高到最近的被覆盖顶点
  （`body_2`、`underwear`、`knee-socks`）的大腿子树权重：间隙 4 cm 以内全额，到 9 cm 衰减为 0。
  前面和侧面补给大腿，后面补给辅助骨，总量封顶 0.9。裙子最后重映射。

## 5. 紧身段不进物理：髋关节以上用皮肤权重

最初每条裙链从腰带骨（`*_00`，z 98 → 91.7 cm）开始模拟。r13–r16 的四次失败：

| 版本 | 改动 | 结果 |
| --- | --- | --- |
| r13 | 原样复制 EVE 胶囊 | 第一个被模拟的关节（z≈91.7，尾巴根高度）陷在胶囊里，被推出去，形成一圈鼓包 |
| r14 | 胶囊按 §3 缩小 | 鼓包消失；跑动时腰带段绕腰线自由摆动，前后裙片和身体之间露出缝 |
| r15 | 链从第二根骨开始，腰带段跟骨盆刚性；下一段加 3 倍 stiffness 曲线 | 尾巴根两侧仍有皮肤穿出：髋关节摆进去时，「尾巴根 → 髋」这一段跟着倾进臀部 |
| r16 | 再给这一段加 8° 角度限制 | 更糟：弓步时后腿把关节推出去，角度限制又把它拉回大腿里，大片穿出 |

在 Blender 里复核（刚性裙子，从骨盆轴径向测量）：静止时尾巴根两侧（z 86–92）裙子离皮肤只有 1.0–1.5 cm，
z 82–84 处 2.1–2.9 cm，正后方 4–8 cm。刚性裙子在脊柱扭转 ±12°、侧倾 ±8°、前后弯 ±10°、屈髋 45–80°、后伸 25–30°
（带辅助骨）下都没有穿出，只有 40° 后伸加 15° 外展的弓步有 1 个顶点穿出 0.8 cm。所以问题出在物理，而不是权重。

最终做法（r17，用户：「这次好了」；思路是用户提出的）：

- `build_body.py` BAND：髋关节高度以上，裙子直接复制身下皮肤的权重（最近 6 个被覆盖顶点按距离倒数加权），
  从髋关节 −2 cm 到 +2 cm 线性过渡到原来的权重。结果：z 84–88 为 Pelvis 0.67 / Spine 0.31，z 88–92 为 Spine 0.65 / Pelvis 0.35。
- `ue_build_abp.py`：裙链从髋关节那根骨开始（`*_02` / `SuiteA-03`），只有下摆关节被模拟，绕髋关节摆动。
- 角度限制和曲线都去掉，胶囊按 §3 重新拟合。

结论（`case-derived`，方法可迁移）：贴身的布段不要交给只挡关节的碰撞，直接跟随皮肤；物理只放在布离开身体的地方。

## 6. 曲线与角度限制

- 游戏的 Kawaii 有 `DampingCurveData`、`StiffnessCurveData`、`RadiusCurveData`、`LimitAngleCurveData` 等
  `FRuntimeFloatCurve` 字段（SDK dump 核对过）。曲线值乘在基础值上，横轴 = 关节到根的累计骨长 / 链总长。
- 用导出文本设置：`(EditorCurveData=(Keys=((InterpMode=RCIM_Linear,Time=0,Value=3),(InterpMode=RCIM_Linear,Time=1,Value=1))))`。
  读回时引擎会省略默认值（`Time=0`、插值模式），并多出 `DefaultValue=…`：数关键帧要匹配 `[(,]Value=`，不能直接数 `Value=`。
- stiffness 乘上曲线后不能超过 1：公式里是 `(1 − S)` 的分数次幂。
- 角度限制是对「父关节 → 本关节」相对姿态方向的锥形限制，在碰撞**之后**执行，会撤销碰撞的推出。
  需要碰撞把布推开的链（腿边的裙摆）不要加角度限制。

## 7. 无界面编写 AnimBP

`ue_build_abp.py` 用项目插件 `SBGraphLib` 建图：

```text
LinkedInputPose → ControlRig(BtoB_CtrlRig, 4 个暴露输入) → ModifyBone × 14（reprop）
  → BoneDrivenController × 4（裙摆辅助骨）→ KawaiiPhysics × 28 → Output
```

- 属性用 `Node.<字段>` 路径加导出文本设置（如 `Node.PhysicsSettings`、`Node.CapsuleLimits`、`Node.StiffnessCurveData`）。
  空数组不能写 `()`，那会导入一个默认（原点）元素。
- 编译要求 0 错误；导出 `.t3d` 图和 JSON 报告（链、胶囊拟合、reprop、辅助骨）。
- 诊断开关 `diag`：在物理之后加两个 ×2 缩放的 ModifyBone，一个网格独有骨、一个骨架骨（见 [验证与发布](VALIDATION_AND_RELEASE.md) §3）。
