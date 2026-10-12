# chain `.55` 物理：生成、方向、静止姿势、裙摆角度限制

格式是 `build-sensitive`（DD2 `chain .55`，老式 chain，不是 chain2）；参数值是 `case-derived`。
生成器 `make_chain_spec.py` + `DD2Tool chainbuild`，运行时工具见 [开发工具](DEV_TOOLING.md) §3。

## 1. 文件怎么来

- **底座 = 原生 `body_chain.chain.55`**（胸部抖动、腰钩、背挂点照常工作），Karin 的链组追加在后面。
- setting 从原生 chain 克隆再改字段：长发 / 头发 / 尾巴 / 耳朵用 `hair_011.chain` 的 setting，缎带 / 绳用 `hair_001.chain`，
  外套 / 裙用 `mantle_523_f.chain`。克隆时清掉 wind 引用（`windId = 0`）。
- group 从同类原生 group 克隆（头发类模板 `hair_011` group 1，布类模板 `mantle_523_f` group 0），只改：名字和链尖哈希
  （`MurMur3` 骨名哈希，链按链尖名解析，再沿父骨往上取 `nodeCount` 个节点）、节点数、每节点 `collisionRadius`（根→尖线性插值）、
  `angleLimitDirection`、可选的节点字段与 group 字段覆盖（如 `clspFlags1`）。清掉子组。
- `chainbuild` spec 结构：`{"base", "output", "settings": {key: {file, index, set}}, "groups": [{joints, setting, template, radius,
  node, group, aldir}]}`。写完立即回读核对 group / setting 数。
- 嵌套链（父骨本身也在模拟）保持刚性，不建组。

## 2. `angleLimitDirection`（invariant 级，由原生 `hair_000` 反推验证）

- 每个节点存一个**摆动四元数**：从 +X 转到「该节点静止方向」，在**父骨空间**表示；静止方向 = 本骨 local 旋转 × X
  （RE 行主序 local 矩阵的第 0 行）。生成器 `swing_from_x(d)`：最短弧、无绕 X 扭转。
- 设为单位四元数 = 把静止方向当成「沿父骨 X 轴」：头部子链会朝上飞。
- group 的 `angleLimitDirectionMode` = BasePose；`angleMode` 可选 LimitCone / LimitOval / LimitHinge，半径 `angleLimitRadius`（rad）。
- 前提：次级骨局部 +X 指向子骨（[构建流水线](BUILD_PIPELINE.md) §1）。

## 3. 重力、弹簧与静止姿势

- 重力在 **setting 的 `gravity` 向量**里（默认 (0,−10,0)），节点 `gravityCoef` 关不掉它；要零重力就把 setting 的向量置零。
- 初版参数取自 VRM `secondaryAnimation`（stiffness / gravityPower / dragForce 按组），再按实机反馈调。
- **静止形状要有人维持**：Motion 只驱动核心约 81 根骨，`K_*` 链骨没有逐帧回位 → 链没有静止形状，重力把尾巴拖垂、
  双马尾不动。第二个模型的脚本打开 `CHAIN_REST_POSE`：每帧在 UpdateScene 前把 `K_*` 骨的 LocalRotation 设回
  BaseLocalRotation（130–140 根，约 0.3–0.7 ms）。第一个模型的参数是在没有回位时调出来的，保持关闭。
- 第二个模型的最终档（变体 O，spring / gravity m/s² / damping）：双马尾 0.03 / 0 / 0.015，尾巴 0.05 / 0 / 0.015（零重力、弱弹簧低阻尼，
  摆得开），侧发 0.08 / 1.8 / 0.05，裙 0.08 / 2.0 / 0.2。
- `Cheek_*` 这类骨要先查它带的是什么：Original 的 `Cheek_L/R` 加权的是脸部皮肤（VRM 的脸颊抖动），加链会让脸皮乱动（审查发现后撤回）；
  脸颊两侧的头发是 `Hair_side_*`。

## 4. 碰撞

- 角色碰撞来自原生 `body_female.clsp`（胶囊按原生身体尺寸）。group 的 `clspFlags1` 决定和哪些胶囊碰。
- 原生髋 / 脊椎胶囊包在 Karin 裙根周围，把裙子整片撑开（「裙摆翘太高」）→ 裙组只碰大腿：`clspFlags1 = "V15, V16"`、`clspFlags2 = "0"`。
- 代价：腹部 / 裆部没有碰撞体，裙片向内翻时没东西挡（§5）。

## 5. 裙摆角度限制（v1.0.1，走路时裙片翻进身体）

**现象**：向前走时裙片全部穿进身体，露出腹部、内裤、大腿根（用户截图）。16 片裙（`K_Skirt_0/8/1..7_L/R`），每片 4 节点、长约 29 cm。

**测量**（`skirt_rec.lua` 逐帧记每片 3 个节点 + 左右大小腿骨，在 Hip 静止系中，毫米整数；再用 Python 算深度）：

- 模板 mantle_523 的 `LimitOval` 半径 1.309（75°）+ 无髋部碰撞 → 走动时前片向内翻最多 18 cm，40–60% 的帧在腹部 / 裆部里面。
- 现场用 `via.motion.ChainGroup` 的倍率 setter 做对照：阻尼降到 0.25×、`MotionForceCoef` 0、弹簧 3× **都无效**；只有角度限制有效。

**迭代**：

| 版本 | 角度限制 | 结果 |
| --- | --- | --- |
| v1.0.0 | 模板 LimitOval 1.309 | 前片翻进身体（`runtime-rejected`） |
| f4 | 对称 LimitCone 0.26 | 不再翻进身体；但向外也被限住，抬腿时大腿推不动裙摆，碰撞把裙片往两侧推，大腿从相邻两片之间穿出（片间表面点深入大腿 7.7 cm）；用户：「好了很多，只有一点点裙片最下端会露出来」 |
| **f5** | LimitCone 0.45，锥轴 = 静止方向**向外**（离开裙根中心竖轴）转 0.25 rad | 向内约 0.20 rad（11°）、向外约 0.70 rad（40°）；用户：「这次好了」（`runtime-confirmed`；f5 的逐帧数据未录） |

**外倾锥轴的算法**（`tilt_outward`）：取该 setting 所有链根在模型空间的水平中心 `(cx, cz)`；每条链的外向 `u = (root.x − cx, 0, root.z − cz)`；
对每个节点把 `u` 变到父骨空间，去掉沿静止方向 `d` 的分量得 `w`，锥轴 = `d·cos(a) + ŵ·sin(a)`，再 `swing_from_x`。
结果：每个节点的锥轴与静止方向夹角恰为 `a`（14.3°），且朝外。

**原生参考**：`pants_524/525_wl_f`（无碰撞的腰片）用 `LimitCone` 0.349 / 0.524；原生裙 / 腰布靠重力 + 多个 clsp 胶囊、无弹簧；
`mantle_523` 自己是 `LimitOval` 1.309 + `angleLimitDistance` 0.4 + `coefOfExternalForces` 0.71（披风可以大摆，裙子不行）。

**可迁移的结论**：没有碰撞体能挡的方向，用角度限制挡；限制要**非对称**——向身体内侧窄、向外宽，让肢体能把布推开而不是从片间穿出。
只有片间穿出、没有整体翻入时，再考虑节点胶囊——这是 PRAGMATA 的解法，见本库 `games/pragmata/CHAIN2_PHYSICS.md`。

## 6. 调参纪律

- 一次只动一组能归因的字段；同一版里多个改动一起被接受时，写「随 vX 一起被接受」。
- chain-only 修复版要证明相对上一版只有预期字段变化（f5 vs v1.0.0：只有 16 组 × 4 节点的 angleMode / angleLimitRadius / angleLimitDirection）。
- 加 profile 或改生成器后，另一个 profile 的 spec 必须逐字节不变。
