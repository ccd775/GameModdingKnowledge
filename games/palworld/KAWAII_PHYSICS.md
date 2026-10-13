# Kawaii 物理（游戏内 KawaiiPhysics ≈ 1.17.1）

最终构建 r4：服装层 AnimBP 里 7 个 Kawaii 节点（裙摆 16 条链、尾巴、双马尾、侧发 + 面颊发、前发、兽耳、丝带），参数来自
`physics_tune.json` 经离线模拟导出的文件。r3 的物理在游戏里运行（用户确认），但手感被判「偏硬，耳朵尤其不柔软」，跑动时
大腿根穿出裙片；r4 是针对这两点的重调，手感待用户反馈。

## 1. 物理链必须是游戏骨架里的骨（invariant，与剑星相同）

`FAnimNode_KawaiiPhysics::InitModifyBones` 遍历的是 USkeleton 资源的参考骨架，不是网格的。网格独有的骨在编辑器里能动
（占位骨架就是从这个网格建的），进游戏后游戏用自己的 `SK_PalHuman_Skeleton`，链根本不会被收集。所以 Karin 的每条链都改名
落到游戏骨架里已有的 NPC 配件链上，父骨一致（映射表见 [角色拟合](CHARACTER_FIT.md) §3）。剑星踩过这个坑，本作一开始就照做，
r3 第一次进游戏物理就在跑。

- 每个链头一个 RootBone；同组的其它链头放 `AdditionalRootBones`（一个节点管一组，r4 裙摆一个节点 16 条链）。
- RootBone 本身固定在动画姿态，模拟它的后代。裙链从第二根骨开始当根：腰带段跟骨盆刚性（剑星 r15 的教训）。
- `DummyBoneLength = 0`：Karin 的每条链都以一根末端骨收尾。
- `BoneForwardAxis = X_Positive`（构建时链骨的 X 轴沿骨方向）。
- `TeleportDistanceThreshold = 300`、`TeleportRotationThreshold = 10`。

## 2. 1.17.1 的单帧步进（读源码确认，离线模拟照此移植）

每个被模拟的关节，按顺序：

1. 速度 = (本帧位置 − 上帧位置) / 上一帧 dt，乘 (1 − Damping)；位置 += 速度 × dt。
2. 位置 += 组件的移动量 × (1 − WorldDampingLocation)；旋转同理用 WorldDampingRotation。
3. 位置 += ½ × 重力 × dt²（`Gravity` 为 cm/s²，节点上单独设）。
4. 按 Stiffness 拉回「父关节模拟位置 + 动画姿态里的父子偏移」，比例 1 − (1 − S)^(60 × dt)。
5. 球、胶囊、平面碰撞：把关节推到「碰撞体半径 + 关节 Radius」之外。
6. BoneConstraints（XPBD）——在碰撞**之后**（1.17.1 里 BeforeCollision 的选项没起作用）。
7. **角度限制**：相对动画姿态方向的锥形限制，也在碰撞之后；然后恢复骨长。
8. 写回：父骨只有一个子骨时，父骨旋转 = 从姿态方向转到模拟方向的最短旋转。

曲线（`StiffnessCurveData` / `DampingCurveData` / `LimitAngleCurveData` 等）的值乘在基础值上，横轴是关节到根的累计骨长 /
链总长。用导出文本设 `Node.StiffnessCurveData.EditorCurveData.Keys = ((Time=0,Value=1),(Time=1,Value=0.7))`。

两条推论决定了调参方向：

- **持续移动时的滞后**：跑步时每帧注入 (1 − WorldDampingLocation) × 每帧位移的滞后，Stiffness 每帧拉回一部分，稳态滞后约
  (1 − world_loc) × 每帧位移 / stiffness。world_loc 0.8、stiffness 0.1 时，700 cm/s 下这个量远大于链长能容纳的角度，
  链被一直压在角度限制上，摆不起来——看起来就是「硬」。
- **角度限制会撤销碰撞**：大腿把裙关节推出去，角度限制再把它按姿态方向拉回来，就拉进了大腿。贴腿的裙链限制要松，让碰撞赢。

## 3. 碰撞胶囊

- 胶囊 = DrivingBone 的组件空间变换 × (OffsetLocation, OffsetRotation)，轴为局部 Z，从中心向两边各 Length/2。
  `ue_build_abp.py` 从 bind 姿势的两个端点（组件空间）反算骨空间的偏移和旋转。
- 起点：VRM 的 spring 碰撞体（头、胸、上臂、髋、大腿）重摆后转成胶囊，半径缩到「bind 姿势下每个被模拟关节离胶囊至少
  关节半径 + 0.5 cm」，小于 2 cm 的丢掉（剑星 r14 的规则，防止静止关节被每帧推出、鼓包）。
- r3 的问题：缩完的大腿胶囊半径 8.0 cm，比大腿实际的肉（约 9.4 cm）细，跑动时大腿根从裙片之间穿出。
- r4（`physics_tune.json` 里显式写胶囊，覆盖派生值）：
  - 每条大腿两段，沿 VRM 大腿碰撞体的轴线：上段（髋下 z 82 → 76）半径 9.5，下段（z 73 → 52.5）半径 12.0；
  - 骨盆横向胶囊半径 9.75；
  - 裙关节 Radius 2.5 → 1.0：碰撞只需要挡住布，关节半径大会让静止的布被推开。
  - bind 姿势仍无碰撞（离线模拟 `bind=1` 下推动量约 1°）。
- 试过但没用的：两腿之间的中心胶囊（离线模拟里零效果）；裙摆环形 BoneConstraints（Leather 等柔度在厘米尺度下几乎是刚性，
  环不能变宽，大腿抬起时穿模反而从 21 变成 131 个顶点）。

## 4. 离线模拟（`kawaii_sim.py`）

```text
blender --background <run>/build.blend --python kawaii_sim.py -- <run_dir> <anim.ueanim> <tag> [key=value ...]
  speed=700  fps=60  loops=3  groups=skirt,tail  tune=<physics_tune.json>  set.<组>.<键>=<JSON>
  render=1（渲染最坏帧）  bind=1（静止姿态）  nopen=1（不测穿模）  dbg=<组>  dumpbones=<子串>  export=<文件>
```

- 动画：游戏的 `.ueanim`（PalExport 导出），只取旋转，按游戏的 Skeleton 平移重定向套到 `build.blend` 的骨架上；组件以
  `speed` 沿前方匀速移动。没有转身，所以 world_rot 不参与。
- 物理：上面 §2 的步进（无风、无球和平面碰撞、无瞬移判定），固定 60 fps，跑 `loops` 个循环，量最后一个循环。
- 指标：
  - `RESULT`：裙子顶点（裙骨权重 > 0.5）落在大腿肉（大腿权重 > 0.3 的面）内侧的平均数、深于 1 cm 的平均数、最坏帧；
  - `FLARE`：每组关节偏离动画方向的最大、平均角度。平均值贴着角度限制 = 链一直被压在限制上（「硬」）。
- `export=` 写出合并后的参数（run 的 `physics.json` 几何 + `physics_tune.json` 动力学），`ue_build_abp.py` 只从这份文件生成 AnimBP，
  所以游戏里的参数就是被模拟过的那一份。
- 局限：不是游戏的逐帧结果；只用来比较候选、复现用户描述的现象。结论要在冲刺和慢跑两个动画上都成立才采纳。

## 5. r3 → r4 的参数

| 组 | r3（damping / stiffness / world_loc / 限制） | r4（damping / stiffness / world_loc / world_rot / 半径 / 限制 / 重力 Z / stiffness 曲线） |
| --- | --- | --- |
| 裙摆 | 0.25 / 0.12 / 0.8 / 40° | 0.15 / 0.10 / 0.95 / 0.7 / 1.0 / 65° / −60 / 1 → 0.7 |
| 尾巴 | 0.15 / 0.06 / 0.7 / 60° | 0.10 / 0.05 / 0.75 / 0.6 / 4 / 70° / −80 / 1 → 0.5 |
| 双马尾 | 0.12 / 0.08 / 0.75 / 50° | 0.08 / 0.05 / 0.80 / 0.65 / 3 / 55° / −100 / 1 → 0.5 |
| 侧发 | 0.30 / 0.15 / 0.8 / 35° | 0.15 / 0.08 / 0.85 / 0.7 / 1.5 / 40° / −40 / 1 → 0.6 |
| 前发 | 0.30 / 0.20 / 0.8 / 25° | 0.20 / 0.12 / 0.90 / 0.75 / 1.5 / 28° / 0 / 1 → 0.7 |
| 兽耳 | 0.30 / 0.30 / 0.8 / 20° | 0.10 / 0.12 / 0.985 / 0.6 / 1 / 40° / 0 / 1 → 0.6 |
| 丝带 | 0.30 / 0.15 / 0.8 / 45° | 0.12 / 0.07 / 0.80 / 0.7 / 1 / 50° / −60 / — |

离线结果（700 cm/s 冲刺）：裙子陷进大腿的顶点每帧 52.9 → 13.8（剩下的在裙子内侧，外面看不到）；慢跑 9.7 → 0.7。

方向（`case-derived`，方法可迁移）：

- 软 = 低 stiffness（0.05–0.12）+ 向末端递减的 stiffness 曲线 + 低 damping（0.08–0.15）。
- 裙摆、兽耳这类不该被跑步「吹」起来的，用高 world_loc（0.95 以上），避免稳态滞后把链压在限制上；它们的摆动来自
  身体自身的动作，而不是整体平移。
- 限制要松到让碰撞赢；兽耳 20° 的限制加 0.3 的 stiffness 几乎不动。

## 6. 无界面编写 AnimBP（`ue_build_abp.py`）

用项目插件 PalModTools 的 `PalGraphLib`（[开发工具](DEV_TOOLING.md) §2）：

```text
ClothLayer：InPose → KawaiiPhysics ×7 → Root
```

- 属性用 `Node.<字段>` 路径加导出文本设置：`Node.RootBone`、`Node.AdditionalRootBones[i].RootBone`、`Node.PhysicsSettings`
  （Damping、Stiffness、WorldDampingLocation、WorldDampingRotation、Radius、LimitAngle）、`Node.Gravity`、`Node.CapsuleLimits[i].*`、
  `Node.SphericalLimits[i].*`、曲线。
- 编译结果必须含 `errors=0`；随后在日志里读回 `PhysicsSettings`、`Gravity`、`StiffnessCurveData`，并导出 `abp_graph.txt`。
- 读回 pak 时再核对一次（PalExport `json`）。
