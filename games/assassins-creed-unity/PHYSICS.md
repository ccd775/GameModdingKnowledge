# 物理

大革命的次级物理是**附加骨架**（add-on Skeleton）上的 `BallJointBoneModifier`：每个装备件（兜帽、腰带片、裙摆……）带一个小骨架，挂在角色的
附加骨架表里，运行时并进角色骨架。Karin 的物理是一个新的附加骨架 `Karin_Phys`。除标注外，数字都是 v7（2026-10-24 用户接受）的。

## 1. 宿主：嵌进每个附加骨架表所在的数据文件

- 玩家的附加骨架在表里列着：亚诺的是 `CN_P_ArnoAvatar_Skeleton`（`0x1453680995`，Body_All 列 7），每个旧时代服装有自己的 `*_Skeleton` 表。
  这些表同样内嵌在很多数据文件里（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- `Karin_Phys`（骨架 `0x4B41520F00` + `BallJointCommonData` +1 + `LiteRagdoll` +2）作为**新对象**追加进每个持有这类表的数据文件，表里一个反正会被去掉的
  布料附加骨架的单元格改指它（按顺序取第一个找到的：`Dress_Simple_HV_Col`、`Hood_3`、`Edward_Kenway_Hood`、Bellec 的 `Dress_DoubleSpine`）。
  v7 共 174 张表（v7 构建日志）：`CN_P_Arno` 21、`DataAI_UIDataRoot` 18、Altair / Ezio / Edward / Comet / Bellec / McFarlane / Fearless / UltimateArno 各 15、ThomasCarneillon 15。
  **康纳（Connor）的表里一个都没有** → 构建器打印 `WARN`，那身服装没有物理。
- 为什么不原地替换：`ACU_Unisex_Dress_Simple_HV_Col` 被约 30 个 NPC 数据文件共用；亚诺的头发骨架 `ACU_U_Arno_Hair`（`0x1C1F85E603`）在 Hood_Position
  列 9，反正会被去掉，又出现在 DLC 的 `SDN_Arno_*` 和派对服装 `CN_P_Arno_Party` 里。所以头发骨架只当模板（`SkeletonType` = CUSTOM 和非骨字段沿用，骨表重建）。
- 引用编译后只剩对象 ID（路径文本不进二进制），所以同一个编译好的 `Karin_Phys` 原样嵌进每个文件，每个文件里的引用都指向自己那份。

## 2. 骨架规则与 v3 闪退

**v3 在 Logo 处闪退**（用户的另一台电脑，3 个转储都是 `0xC0000005`，位置 `ACU.exe+0x95240` / `+0x95274`）。`ACU.exe` 的代码段在磁盘上加了壳，
转储里只有出错位置附近约 0x100 字节的代码；从这段代码和寄存器读出：循环沿附加骨架的骨走（`[bone+0x50]` = 父骨，u16 `[+0x88]` = Index，u32 `[+0x80]` = BoneID），
维护一个祖先栈，弹栈直到栈顶是父骨，再在目标骨架里找父骨的对应项（12 字节一项，u16 `+2` = 子树大小，靠跳过子树来遍历子骨）——栈被弹空了（大小 0 / 0xFFFF）。

把 `Karin_Phys` 和全部原版骨架逐项对照，找出三处不同，v4 一起改掉后游戏正常启动（用户实机，`runtime-confirmed`）：

1. **`ChildBoneCount` 是后代数**（子树大小 − 1），不是直接子骨数：`CN_P_Arno` 里全部 37 个骨架都这样；v3 的 121 根骨里有 50 根写的是直接子骨数
   （例如 Reference 写 2，应为 120）。上面的循环正是按这个数跳过子树，最可能是闪退原因（`hypothesis`：三处没有分开测）。
2. **`SkeletonKey` / `SkeletonHierarchyKey` 要用自己的**：v3 沿用了模板 `ACU_U_Arno_Hair` 的键，而头发骨架在同一批文件里照样被加载。原版只在骨层级完全相同时
   共用键（两条腰带、两双靴子、五个头部骨架）；键的算法不明，`Karin_Phys` 用（骨 ID、父骨序号）列表的 CRC32，并断言和模板不同。
3. **BallJoint 的 `LiteRagdoll` 留空**（`OrientationBone` 也和原版一样留空，v3 这一项没有问题）：v3 把 `LiteRagdoll` 指向 `LiteRagdoll_Player`（只嵌在 `CN_P_Arno` 里），原版 158 个 BallJoint 全部为空。

其它字段（`invariant`，按原版）：骨按深度优先排、`Index` = 位置；BoneID = 骨名的 CRC32（和 AnvilToolkit 写网格骨一样）；`GlobalPosition / Rotation` 相对附加骨架的根，
`LocalPosition / Rotation` 相对父骨（核对过：GLB 导出里 `Spine2⁻¹ · Head` 等于原版头发附加骨架里 Head 的 Global 值）；根是单位变换的 `Reference`，
骨表 = Reference + KP 骨父骨的全部祖先（变换取自 GLB）+ KP 骨；`MirrorBone` 指自己；`SolvingPriority` 沿物理链 1、2、…，身体骨 0。

检查（每次改骨架都做）：原版骨架（头发、`Dress_Simple_HV_Col`、`Hood_3`、`Big_Dress`、头部骨架）重新编译逐字节相同；网格的每根骨都能在某个加载的骨架里找到
（53 根基础骨、6 根头部骨架骨、100 根 `Karin_Phys` 骨）；`Karin_Phys` 的 `ChildBoneCount` / `Index` / 键 / 空引用按上面三条核对。

## 3. BallJoint 的行为

字段（取自原版头发 / 腰带）：`ConstraintAngleType` = Cone、`ConstraintAngle`（锥的半角，度）、`ConstraintScaleY / Z`（椭圆锥，Karin 用 1）、`Mass`、
`CollisionRadius`、`MechanicalFriction`、`AirFriction`、`WindScale`（0）、`GravityMode`（0 = GlobalGravity、2 = GlobalOwnGravity）、`OwnGravity`、
`LocalYawOft` / `LocalPitchOft` / `LocalRollOft`、`CommonData`、`OrientationBone`、`LiteRagdoll`。

- **没有弹簧**（从 v4 的现象推断的工作模型，`hypothesis`；v5–v7 按这个模型调参，结果都和预期一致）：重力把每节模拟的链拉到锥面边缘，不会回到静止姿势。锥中心放在静止姿势上时，一条链垂下约「锥角 × 模拟节数」：
  v4 的尾巴 3 × 20°、双马尾 3 × 25°、裙片 2 × 12°，双马尾和尾巴直垂、裙片压进大腿。
- 原版：锥角多是 10 / 15 / 20°，用在本来就下垂的短件上；158 个 BallJoint 里 116 个带 yaw / pitch 偏移，常见 |pitch| = 锥角（静止姿势在锥边 = 单侧摆动）。
- `step`：每隔几节模拟一节，中间的跟着刚性走（尾巴和双马尾 `step` 2：3 节模拟）。

## 4. 偏移约定与重力补偿

- **约定**（`reference-inferred`，从原版统计；`runtime-confirmed` 于 v6 的摆动）：按骨自己的局部坐标系，`LocalPitchOft` 绕局部 Z 转（正值把 X 轴转向 +Y），
  `LocalYawOft` 绕局部 Y 转（正值把 X 轴转向 −Z）。照这样解释，原版 `CN_P_Arno` 里 116 个带偏移的关节有 93 个是朝离开身体的方向摆、7 个朝内；
  其它轴向 / 符号 / 父骨坐标系的组合都在随机水平。v5 时的结论「偏移方向和任何坐标系测试都对不上」被这个统计取代。
- **重力补偿**（`acu_phys_skel.rest_offsets`）：把每节的锥中心逆着下垂方向偏一个锥角，重力正好把静止姿势（= 源模型的形状）托在锥边，链能向上 / 向外摆到两倍锥角。
  1. t = 骨到子骨（多个子骨取平均）的方向；t 与竖直向上的点积 > 0.7（朝上的件，比如耳朵）→ 不偏；
  2. 目标方向 m = 「向上」在垂直于 t 的平面上的分量；|m| < 0.3（几乎竖直下垂的件）→ 改用从它所挂的身体骨朝外的水平方向（原版裙片的做法）；
  3. 换到骨的局部坐标；子骨不在局部 X 方向上（`tl[0] < 0.7`，比如手上丝带的分叉根）→ 不偏（v6 第一次生成时这里的最小二乘退化，yaw 算出约 3300°）；
  4. 最小二乘解出让尖端朝 m 移动的 (pitch, yaw)，再缩放到正好一个锥角。

## 5. 参数与各版评价

| 版本 | 改动 | 用户评价 | 证据 |
| --- | --- | --- | --- |
| v3 | 第一版物理骨架 | Logo 处闪退 | `runtime-rejected`（§2） |
| v4 | 修好骨架规则；锥中心在静止姿势上：尾巴 20°、双马尾 25°、裙片 12° | 「双马尾、尾巴、裙子等都始终受重力影响……源模型尾巴和双马尾会维持本身形状……下落的裙片也穿入了大腿和臀部」 | `runtime-rejected` |
| v5 | 小锥角：尾巴 / 双马尾 4°、裙片 3°、侧发 / 耳 / 脸颊 5°、丝带 / 鞋标 10°（最大下垂约 12°） | 「尾巴和双马尾是保持原形的了，不过整体的物理效果幅度都可以再大一些、柔软一些。跑动时大腿还是会穿出裙片」 | 保形 `runtime-confirmed`；幅度、裙片 `runtime-rejected` |
| v6 | 重力补偿偏移（§4）；尾巴 / 双马尾 12°、裙片 10°、丝带 15°、鞋标 12°、侧发 5°（它朝里挂，往脸的方向摆）；摩擦降低；裙片碰撞：每条大腿一个胶囊 | 「物理效果整体尚可。但是现在跑动时，大腿还是会穿出裙子」 | 摆动 `runtime-confirmed`；碰撞 `runtime-rejected` |
| v7 | 每条大腿两个胶囊（§6），裙片 14° | 「v7 可以了」 | `runtime-confirmed`（2026-10-24） |

v7 的 `DEFAULT_PARAMS`（按 KP 骨名的正则，第一个匹配生效；`case-derived`）：

| 链 | 锥角 | CollisionRadius | 机械摩擦 | 空气摩擦 | 其它 |
| --- | --- | --- | --- | --- | --- |
| `KP_Hair_tail`（双马尾） | 12° | 0.04 | 1.5 | 1 | step 2 |
| `KP_Hair_side` | 5° | 0.03 | 2 | 1.5 | |
| `KP_Hair_front` | 5° | 0.02 | 3 | 2 | |
| `KP_Cheek` | 6° | 0.02 | 2 | 1.5 | |
| `KP_Ribbon` | 15° | 0.02 | 1.5 | 1 | |
| `KP_Shoes_tag` | 12° | 0.01 | 2 | 1 | |
| `KP_Skirt` | 14° | 0.02 | 2 | 1 | 与大腿碰撞 |
| `KP_Ear` | 5° | 0.02 | 3 | 2 | 朝上，不偏 |
| `KP_Tail` | 12° | 0.05 | 1.5 | 1 | step 2 |
| 其它 | 6° | 0.02 | 2 | 1.5 | |

质量都是 1，`WindScale` 0。耳朵、侧发、前发、丝带、鞋标的效果用户没有单独评价。

## 6. 裙片与大腿的碰撞

- 原版唯一会碰撞的 BallJoint 是亚诺的腰带片 `ACU_Belt_A_Arnaud`：`CommonData` → `BallJointCommonData`（`LiteRagDoll` 引用、`Gravity`、`LastBoneLength`）→
  `LiteRagdoll`（`Capsules`：`BoneID`、`Height`、`Radius`、`LocalMatrix`（行主序，平移在最后一行）、`GroupFlags`），关节的 `GravityMode` = `GlobalOwnGravity`（2）。
  Karin 的裙片照搬这条路；`LastBoneLength` 取最末一节裙片的平均长度。
- 胶囊坐标系 = 大腿骨（X 指向膝盖，和原版玩家 / 腰带的胶囊一样）。原版玩家的大腿胶囊：中心 0.25、Height 0.165、半径 0.085。
- Karin 的大腿（`karin_lod0_acu.glb`，UpLeg 坐标系，长 0.437 m）：皮肤半径在 x 0.05–0.25 处约 0.10 m、0.25–0.35 处 0.08、近膝盖 0.066，轴线偏 Y 约 −0.008；
  裙摆的点在髋关节高度（x ≈ 0.02），离大腿轴 0.157–0.20 m，中段的点在 x −0.1。
- v6：每条大腿一个胶囊（中心 0.22、Height 0.2、半径 0.10 = 裸皮），跑动时大腿还是穿出裙子。
- v7：每条大腿两个胶囊 (x, Height, 半径) = (0.12, 0.1, 0.13)、(0.32, 0.1, 0.11)，比皮肤多约 3 cm 给骨点之间的布；不管 `Height` 是整段还是半段长度，都覆盖
  0.02–0.45；静止时仍不碰（0.13 + CollisionRadius 0.02 < 0.157，每个裙片点留 7–16 mm）→ 跑动不再穿出（用户）。`Height` 到底是整长还是半长没有确定（`hypothesis`）。
- 准备过诊断构建 v7x（胶囊半径 ×2：碰撞若起作用，静止时裙子会明显撑开），v7 已通过，没有用到。
- **被否定的做法**：把裙片蒙到大腿上（`rejected`）——裙摆挂在髋关节高度，大腿转动只会把蒙上的裙摆往上、往后带，不会往前推开。

## 7. 没覆盖的

- 康纳的旧时代服装没有物理（§1）；DLC「亡者之王」的 `SDN_Arno_*` 表、派对服装 `CN_P_Arno_Party` 没有处理。
- 风（`WindScale` 0）、裙片和臀部 / 手臂的碰撞、`ConstraintScaleY / Z` 的椭圆锥都没试过。
- 过场、攀爬、跳跃时的物理没有专门看过。
