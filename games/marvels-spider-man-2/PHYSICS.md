# 物理（AnimDynamics）

SM2 的次级物理是 AnimDynamics：粒子链加锥约束，**没有碰撞体**。布料走 Havok（`ModelHavokData` + `ModelClothMetaData`），体量大，本项目没碰。
本文的 exe 地址只对 v1.130.1.0 有效（`build-sensitive`），来自两轮逆向和实机对照。

## 1. `ModelAnimDynamicsDef`（段 `ADD1CBD3`）

ModelDef.AnimDynamics（`AnimDynamicsChainDef` 数组）编译后的形态。字段见 InsomniacTools 的 `i30.documentation.json`：
JointName / JointNameEnd / ConstraintType / Gravity / Mass(End) / Damping(End) / ConeAngleOuter(End) / ConeAngle±Y/±Z Scale / LengthElasticity。
最好的样本是 `prop_web_dangle`：19 个粒子的直链，参数全是默认值。其它样本：Black Cat 拉链、Great Hunter 肌肉、Venom 触手、背包挂件。

- 头 48 B：`u16 counts[8] = (粒子, 链节, 系绳总数, 弯曲(=链节), 0, 链, 链节, 0)` 加 `i32 offs[8]`。
  offs 相对头尾，表 k 用 offs[k+1]，-1 表示空表。每张表补齐到 16 B。
  每条链有 (链节 + 1) 个粒子，第一个粒子钉在动画上（invMass 0）。
- T0 粒子 12 B：绑定姿势的世界坐标 float3。
- T1 链节 64 B：`u16 a, b（全局粒子）, u16 关节, 子关节, u32 父关节, f32 invMass_a, invMass_b, 骨长, cos(锥角), sin(锥角),
  -sin·NegY, +sin·PosY, -sin·NegZ, +sin·PosZ, quat(xyzw)`。
  - 锥角沿链从 ConeAngleOuter 线性插值到 ConeAngleOuterEnd。
  - quat = 关节局部旋转 ⊗ 「把 +X 转到子关节局部方向」的旋转。
- T2 系绳 12 B：`u16 a(=链根粒子), b(=根+1,3,5…), f32 invMass_b, f32 最大距离 = 沿链长度 × 1.01`。每链 ceil(链节/2) 条。
  原版构建器有个怪癖：第 c 条链的第 t 个槽填的是「全模型系绳表」的第 t 项（`TETHER_COMPAT` 照原样复刻）。
- T3 弯曲 32 B：`u16 a, b, c, u16 根标志, f32 invMass_a, invMass_c, |pa-pc|, cos(∠abc), 0.8, 0.9`。
  每链第一项是根型：a = 根关节的父关节，标志 1。
- T5 链 108 B（27 个字）：
  - 前几个字：`(u16 约束类型, 首链节) (链节数, 系绳累计序号) (系绳数, 首链节) (弯曲数, 首粒子) (粒子数, 0) (0, 1)
    (首粒子, 根关节) (根关节父, 0)`；
  - 其后：根关节局部位置、系绳父(-1)、末关节信息、重力 f32×3、阻尼、链名字符串偏移。
  - **第 3、4 字是 `(链节数, 首粒子) (粒子数, 0)`**。写错时第 0 条链看不出问题，从第 1 条链起粒子错位，物理动 1 秒就卡成一团（T10）。
- T6 链节 40 B：`u16 a, b（链内）, u16 关节, 子关节, u32 父关节, f32×3 子关节局部方向, quat 关节局部旋转`。
- 默认值：质量 0.1（invMass 10）、阻尼 0.01、锥角 30° → 20°、重力 (0, -9.80665, 0)。
- `ModelBuilt` 首字要置 `0x20000000`。
- 动力学关节的约定：沿骨方向为局部 +X；带权重的 u2 = 0x81，链尾为 0x01（局部旋转为单位），并且要有 `ModelMirrorIds` 自映射项。
- 回归：`test_dyn_roundtrip.py` 从原版段读回参数，再用 `i30_dynamics.build` 生成并逐字比较。
  web_dangle、Black Cat、Great Hunter、Venom、Kraven、背包等原版模型 0 差异；少数模型有几个字不同（例如一个背包的系绳、一个 NPC 的 T6 四元数），属于原版构建器的个别差异，未深究。
  非规格化浮点必须逐位相等：以前把小整数对当浮点比，放过了 T5 的错误。
  `test_dyn_model.py` 独立核对 T5 的整数字段。

## 2. 约束类型与调参

- 原版用法（16 个样本，`case-derived`）：
  - **0 Simple**：只给蛛丝、共生体触手（锥 10° → 5°，重力 +2 向上）、搭扣、链子这类绳和触手；
  - **1 Cone**：Great Hunter 肌肉（15–20°，保持静止形状、小幅抖动）和背包拉带（75° → 85°，质量 40，阻尼 0.5）；
  - **2 HalfCone**（某个 cone_scale 为 0）：拉链、项链、鹰翅、瓶子。
  - 原版阻尼 0.01–0.5。
- **Simple 不做锥限制，没有恢复力**：Karin 的链全用类型 0 时，全部按重力垂到底，耳朵塌在头顶（T15 `runtime-rejected`）。
  VRM 里这些 spring 的 gravityPower 全是 0，形状靠 stiffness 维持，SM2 没有对应参数，只能靠锥约束。
- 锥是「父关节帧里的静止方向」，链上每节都能偏一个锥角，所以整条链的最大弯曲是逐节累加的。
- 三轮实机调参：

  | 轮次 | 参数 | 反馈 |
  | --- | --- | --- |
  | T15 | 全部类型 0（Simple）；耳朵锥角 8°、重力 0 | 连续、柔软，但全部垂到底，耳朵塌在头顶 |
  | T16 | 类型 1，锥收小（耳 4 → 6°、双马尾 8 → 12°、尾巴 5 → 8°），重力 -0.3 ~ -2，阻尼 0.15–0.3 | 耳朵立住但几乎不动；其它部件「太弹」，在锥壁上反弹 |
  | T17 | 类型 1，锥放宽，阻尼 0.35–0.5，重力 -0.5 ~ -2.5 | 「整体效果可以」（`runtime-confirmed`） |

- T17 的终值（`sm2_karin_geo.DYN_SPRINGS`，`case-derived`）：

  | 链 | 锥角（根 → 尾） | 阻尼 | 重力 y |
  | --- | --- | --- | --- |
  | 双马尾 L/R | 10° → 14° | 0.4 | -2.5 |
  | 侧发 L/R | 10° → 14° | 0.45 | -2.0 |
  | 前发 ×3 | 8° → 10° | 0.5 | -1.5 |
  | 耳朵 L/R | 10° → 14° | 0.35 | -0.5 |
  | 丝带 L/R | 14° → 20° | 0.4 | -2.5 |
  | 尾巴 | 6° → 9° | 0.45 | -1.0 |

- 只改链参数时不用重新拟合：`sm2_dyn.load` 在构建时直接套用当前的 `DYN_SPRINGS`。

## 3. 每帧门控：为什么「只动 1 秒」

逆向 exe 的结论（2026-10-13，`build-sensitive`）：

- `AnimdynamicsJob` 每帧遍历全局 DynamicsInst 表，逐实例步进（`0x1428e2380`）。实例一旦「出界」，就做固定 1.0 s 的 blend-out，之后跳过。
  这就是实机上所有「约 1 秒后冻结」的来源。
- 出界条件（任一满足即出界）：
  - ModelInst 被隐藏（`+0x5c & 0x1e0`）；
  - 是子 ModelInst；
  - **ModelInst 没有 owner actor，或者 owner 没有 AnimControllerComponent**；
  - 超过 MaxUpdateDistance；
  - **相机距离 > 缩放 × 运行时包围球半径 × AnimDynamicsUpdateMultiplier**（默认 50）。
- **运行时包围球每帧由 `ModelJointBspheres` 重算**，`ModelBuilt` 的半径不参与。
- **`AnimControllerComponent.NeverCull = true` 时不计算相机距离**，距离门恒通过（`0x1428c6749` 处置位）。两个英雄 actor 都是 true。
- **SkinManager 创建的战衣部件没有 owner**：owner 只在 `Actor::CreateModelInst` 里写入，SkinManager 建部件不走这条路径。
  所以战衣模型里的动力学只能在部件重建（换战衣、关菜单、按 ESC）后跑 1 秒。**这是数据层面改不了的**（`rejected`：任何模型或 actor 字段都救不回来）。
- HeroSuitAddition 挂的子 actor 有自己的 owner 和 AnimController，所以能持续模拟。

## 4. 试过的挂接路线

| 路线 | 做法 | 结果 |
| --- | --- | --- |
| 战衣自带（T10/T11） | 每个战衣模型带 48 个链关节和动力学段 | 换战衣 / 关菜单后约 1 秒有物理，然后冻结（`runtime-rejected`；§3 第 3 条） |
| base 模型（T12/T13） | 动力学放进英雄 actor 的 base 模型（只有 3 顶点占位网格），战衣只带同名关节；T13 把 base 的 ModelBuilt 半径改成 25 m | 只在按 ESC 时闪一下（`runtime-rejected`）；ModelBuilt 半径不参与门控 |
| 背包挂件（T15–T17，**v1**） | Miles 蜘蛛猫战衣原本就有 HeroSuitAddition，会挂 `prop_backpack_spidercat.actor`。把背包网格清空，链的三角形 + 链关节 + head / pelvis + 动力学放进这个挂件模型 | **持续模拟**（`runtime-confirmed`），但只覆盖这一套战衣 |
| 多条 HSA（T18） | 给 `hero_spiderman.actor` 追加 HSA，每个 loadout 一条 | 被丢掉，同类型组件只认第一条（`runtime-rejected`） |
| 头部载体（T19–T23，**v2**） | 带面罩战衣共用的头 actor `hma_hed_base.actor` / `test_i20_Head.model` | T19 / T20 冻结 → T21 加 NeverCull 和关节包围球后**持续** → T22 尾巴跟随 → T23 全部 91 套（`runtime-confirmed`） |

被否决的其它思路（不要再花试验）：
- `SuitLoadout` 写列表、通配或空串：只做一次 64 位精确比较（`0x140f29790`）。
- 给头 actor 加 IsHero / SimpleAnimated / animset（T20）：这些都不在门控条件里。
- 把 HSA 放到头 actor 上：头 actor 没有 SkinManager。
- vanity 物品的 ItemActor、webwings、道具 actor：要么不会被读取，要么只在滑翔时存在，要么没有模型和 AC。

## 5. 头部载体（v2 的做法）

`sm2_head_carrier.py --never-cull --joint-bsphere 1.0 --map-body --masked --blank-prop`：

1. **载体模型** `characters/test/test_i20Hero/test_i20_Head.model`（14 关节、一个 1 mm 四边形，其它东西都不用它）：
   - 追加 pelvis、spine、spine_helper1（按战衣骨架的父子关系挂在 a_body 下），再追加 48 个链关节；
   - 放入链三角形（[角色拟合](CHARACTER_FIT.md) §5）和 12 条链的动力学段；
   - 关节平移按「载体 head − 战衣 head」（头上的链）或「载体 a_body − 战衣 pelvis」（尾巴）整体平移；head / a_body 的 bind 旋转两边相同；
   - **`ModelJointBspheres` 的两个球半径放大到 1 m**：原来的 0.5 / 0.7 mm 对应约 4.5 cm 的更新距离，相机永远比这远（T19 / T20 冻结的原因）。
     有 NeverCull 后距离门恒通过，放大半径主要是为了渲染剔除：头出画时双马尾不被剪掉。
2. **头 actor** `actors/hma_hed_base/hma_hed_base.actor`：`AnimControllerComponent.NeverCull` 从 false 改为 true。只改 1 字节，长度不变。
3. **HeadManager 映射**：在 `hero_spiderman.actor`、`hero_milesmorales.actor`、`boss_symbiote_pete.actor` 的 `CustomJointMap` 里追加
   pelvis / spine / spine_helper1（[技术合同](TECHNICAL_CONTRACTS.md) §7）。不加的话尾巴跟着 a_body 走：下蹲 / 爬行时悬在站立时的胯部高度，
   尾根中段错位（T21）。
4. **去链**：`masked_suits.json` 列出的 91 个战衣身体去掉链三角形，否则会出现两套头发。
5. **蜘蛛猫背包**改为全部网格退化：不再带链，也不显示背包。

- 一个载体两族通用：Karin 的脸在两族 bind 下的世界位置几乎相同（z −0.0216 / −0.0219 m），实机 Miles 也没有偏移。
- 菜单 paperdoll（`ui_*_proxy`）也用这个头 actor，按名字自动匹配。v1 的背包挂件在菜单里能持续模拟（T15）；v2 在菜单里的表现没有单独确认。
- 已知副作用：
  - `hero_spiderman_invisible.actor` 也生成这个头 actor，用到它的场景可能出现悬空的头发（未遇到）；
  - antiock 的 nomask 剧情 loadout 的头是 Peter 的脸，那里没有链；
  - 共生体 Peter boss 也是 Karin 并带物理（已补映射）。

## 6. 未做 / 未知

- 便装（Peter 10、Miles 4）和 young 用各自的头 actor（例如 `hero_peterparker_head.actor`，其 AC 里没有 NeverCull 字段，要插入新字段）。
  可以照第 5 节的做法把链放进这些头模型，未做。
- 想根治共享头 actor 的副作用，就要给英雄单独做头 actor 和模型（新资产 id）。Peter 的头来自 `VanityHEDSpiderMan1.config`，还得改 config。
  新 id 能否加载未验证。
- 碰撞：AnimDynamics 没有碰撞体，头发和尾巴大动作时会穿过身体。
