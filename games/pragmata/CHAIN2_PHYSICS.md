# chain2 物理：从零加链、调参轨迹、碰撞与裙摆

格式与组件字段是 `invariant`（本作 chain2 `.15` / PFB `.18`）；参数值是 `case-derived`。
格式细节（节点记录、angleLimitDir 父骨系语义）与 [鬼武者 chain2](../onimusha-way-of-the-sword/CHAIN2_PHYSICS.md)
相同，这里只写本作不同或新增的部分。

## 1. 给没有物理的角色加 Chain2（invariant）

Hugh 的玩家 prefab 没有任何 Chain 组件，只能自己插：

1. 在身体 mesh 所在的 GameObject 上追加两个实例：`via.motion.ChainWind`（`WindAsset` 为空）和
   `via.motion.Chain2`。字段模板取同作已有 Chain2 的部件（本例 Diana `ch05000_parts_body_pa2010.pfb.18`）。
2. Chain2 字段：`ChainAsset` = 新 chain2 路径；`EnvWind` 指向刚插入的 ChainWind 实例；
   `EnabledCollision`；`UpdateTiming = 4`（见 §4）。把 chain2 路径加进 prefab 的资源表。
3. GO 上没有 `app.TimelineEventResetSimulationRegister` 的补一个（过场/传送时重置模拟）。
4. **所有**引用该 mesh 的 prefab 与 GO 都注入（Diana 是 7 个文件、9 个 GO）。
5. 插入后平移对象表索引（`parentId`、`GameObjectRefInfo`），见 [技术合同](TECHNICAL_CONTRACTS.md) §3。

链骨：全部新增 `KC_*` 骨，只存在于 mesh 骨表里（Diana 原生头发骨也是 mesh-only），追加在骨表末尾；
KC 骨带锚点骨的旋转，所以「父骨系 = 锚点骨系」，`angleLimitDirection` 直接由几何在锚点系里算出。

chain2 文件：表头从原生 `ch0900_00.chain2.15` 拷；setting 的标志位（`settingsAttrFlags`、`windDelayType`、
`groupDefaultAttr`）保留原生模板值，只替换动力学浮点；每条链一个 group，`terminateNodeNameHash` 指向链尖。

## 2. 链拓扑：从 VRM SpringBone 设计（case-derived 规则）

- 每条 spring = 一条链；每根骨只属于一条链。链尖骨缺失时按权重顶点估计（见 [角色替换](CHARACTER_REPLACEMENT.md) §3）。
- 嵌套最多一层：挂在另一条链中间节点上的子链（背部缎带挂在大衣中片）排在父组之后；
  更深的嵌套并入上一层末节。锚到静态 `Hip` 会与摆动的大衣脱开；冻结中片会撕开相邻片的共享接缝（均已否决）。
- **裙片 / 大衣整族统一锚点**（整族顶点合并投票，结果是 `Hip`），避免片与片之间剪切；其余链按根段顶点投票。
- VRChat 源：词干忽略 `L.` / `R.` 前缀；`VRCLeafTipBone_*` 当链尖；同词干重复列出的组并入主线；
  `SubLeg*` 下的 DynamicBone 碰撞辅助骨（`DBC_*`）、抓取机关骨跳过；关节全被移除的空 spring 跳过。
- 尾巴根部一圈顶点在源里位于根关节前方约 10 cm 却 100% 绑尾巴：沿链方向 10 cm 线性衰减到父骨。
- 姿态闸门：每根链骨各弯 30°，检查蒙皮拉伸（本项目链区最大 2.03×，另有来自源权重的小面）。

## 3. 参数档位来源

动力学浮点（29 个）按链族从**鬼武者**最终实机确认版拷贝（同一个 Karin 模型，尺度只差 1.07–1.13×）：
双马尾、耳机线、尾巴、头发/耳朵（gravityCoef 0.30）、呆毛、大衣/裙、缎带各一档。
然后按 §4 的实机反馈逐轮修正 —— **跨作搬来的「跟随感」调校不能直接用**。

## 4. 调参轨迹（runtime，按轮次）

| 轮 | 改了什么 | 实机反馈 |
| --- | --- | --- |
| phys1 | 鬼武者档位原样 | 有物理，但双马尾/线缆、大衣、尾巴/缎带**移动中高频乱颤**；头部短部件正常 |
| phys2 | 只改 `reduceSelfDistanceRate`：长链 0.50、布料 0.70，关掉速度触发的第二档回拉 | 不再乱颤，但**没有运动跟随**（跑动时头发不甩到身后） |
| phys3 | 插入的 Chain2 `UpdateTiming` 3 → **4**；长链 reduceSelf 0.25、布料 0.45；所有档位去掉第二档 | 「挺好的」（接受） |

结论：

- 乱颤的更可能成因是 `UpdateTiming`：插入的组件从 Diana 身体**布料**部件复制了 3；全量扫描 73 个原生
  Chain/Chain2 组件，Diana 所有**头发**部件与 ch09000 都是 4，布料部件是 3。移动中的角色用 3，
  根部位移与模拟不同步。（phys3 同时改了 reduceSelf，未做单变量归因。）
- `reduceSelfDistanceRate` 是「跟随」旋钮：高 = 钉在静止位。phys2 为治抖把它调高，同时头发档自带
  「速度 > 3 m/s 以 0.86 回拉」的第二档，跑动时直接回到 rest。本作原生头发 0.30–0.68 且都没有第二档；
  原生长布料链 0.73 / 0.84。
- 先怀疑过的 `settingsAttrFlags` 被数据否定：抖的双马尾与鬼武者标志位一致。
- 若抖动再现：先确认是否「移动中高频」，是则 UpdateTiming 不是主因，再把长链 reduceSelf 往 0.35 调
  或加梢部阻尼（`minDamping`）。

## 5. 碰撞

### 5.1 两条碰撞来源与 group 标志（reference-inferred）

group `attrFlags` 位（名称来自 RE Chain Editor 的属性表）：

```text
   1 RootRotation      8 CollisionDefault    1024 WindDefault
   2 AngleLimit       16 CollisionSelf      32768 EnableEnvWind
   4 ScaleAnimation   32 CollisionModel     65536 CollisionCharacter
```

本作原生值：`0x840B`（ch0900，带 chain2 内置大腿胶囊）、`0x8423`、`0x185F3`、`0x2840B`。
本项目用 `0x840B` = CollisionDefault、**不含** CollisionCharacter：链条只碰 chain2 文件里的
模型碰撞体，不碰角色 `.clsp`。据此推断 v0.1 的 Diana 虽然 `EnabledCollision = 1`，但文件里
没有碰撞体，实际上什么也不碰（推断，未单独实验）。

补充（2026-10-02，来自 [生化危机 安魂曲](../resident-evil-requiem/CHAIN2_PHYSICS.md) §3）：chain2 自带碰撞体是否生效，还取决于 prefab 上 `via.motion.Chain2.CollisionTarget`（RE9 运行时枚举 Self 0 / Extern 1 / All 2；Extern 只碰 `.clsp`）。本项目插入的 Chain2（从原生部件复制）和原生 ch09000 读出来都是 0，与模型碰撞体生效一致；本作未单独读枚举。新项目复制模板组件时先核对这个字段。

角色 `.clsp` 不能直接复用：Hugh 的 clsp 有背包机械臂、颈后推进器和 0.2 m 胸腔胶囊，Karin 没有这些部件。

### 5.2 chain2 内置模型碰撞体（runtime-confirmed，随 v0.2/v0.3 一起被接受）

本作原生先例：ch0900 = `L_Thigh → L_Shin` 胶囊 r 0.05 ×2 + 横跨 `Hip` 的横杆（joint == pair，局部 x ±0.025，r 0.116），
shape 2；本地提取的 14 个原生 chain2.15 里**没有一个带 link**。

拟合配方（按构建出的网格，`invariant` 做法）：

- **大腿**：每条腿两段胶囊（`Thigh → Shin` 的 10–50% 与 50–92%），半径 = 该段内**由这条大腿主导（权重 ≥ 0.6）**
  的皮肤顶点到骨轴距离的 **p90**。胶囊起点离开髋关节，避免起点半球鼓进髋部、顶到裙根。
- **骨盆**：两根横跨 `Hip` 的横杆，高度 = 裆部（最低点往上 35%）与髋臼（Hip 关节高度）；
  「半长 + 半径」= 该高度带内侧向宽度 p98，半径 = min(前后厚度 / 2, 宽度)。
- 世界坐标算好，用关节世界矩阵的逆换到**关节局部**写入 `pos` / `pairPos`；记录从 ch0900 的第 3 条
  （joint == pair 的横杆）克隆，`chainCollisionShape = 2`，`collisionFilterFlags = -1`；表头 `chainModelCollisionCount` 同步。
- 覆盖率闸门：裙高范围内由大腿/髋主导的皮肤顶点，落在某个碰撞体内（+5 mm）的比例 > 90%
  （本项目 98.5% / 98.2%）。另一款 RE Engine 作品（怪物猎人荒野）的记录也指向同一结论：
  要把布推开的碰撞体按**外表面**拟合，均值/低分位半径会让跑动时大腿根穿出。

### 5.3 静止间隙闸门（invariant）

每个模拟节点（链根除外）在静止姿势下都必须在所有碰撞体外 ≥ 2 mm（含节点半径）；胶囊节点
（见 5.4）要求**整段**在外，半径取两端较大者。违例时先缩节点半径（不低于 3 mm），仍不够再缩碰撞体半径。
所有操作只让半径变小，所以单遍即可收敛。起始就在碰撞体里的节点会被一帧推飞，表现为抖动或炸开。

结果（本项目）：Hugh 碰撞体半径 大腿 0.0895 / 0.0689、骨盆 0.0749 / 0.1044，最小段间隙 2.0 mm；
Diana 0.0559 / 0.0545、0.0578 / 0.0703，最小段间隙 8.7 mm。

### 5.4 裙片节点配方与胶囊节点（runtime-confirmed，v0.3 被接受）

- 裙片 `angleLimitRad`：根 0.524、中间 1.047、末端 1.571；节点半径沿链向下摆递增 5 / 15 / 25 / 30 mm
  （鬼武者 v0.8/v0.9 的结论）；尾巴半径 8 → 30 mm 渐变。
- **节点 `collisionShape` 枚举**（RE Chain Editor）：0 None、1 Sphere、2 Capsule、3 StretchCapsule。
  1 只挡节点那一点，两节点之间的布（下摆段 7–9 cm）照样切进迈出去的大腿。
- 裙链的中间节点（非根、有子节点）设为 **2**：节点到子节点整段按胶囊碰撞。本作原生先例：
  ch7700 的 24 个节点用 2（含 `0x840B` 组）。链根保持原值，链尖保持 1。
- v0.2 → v0.3 只改了这一项（两个 chain2，其余逐字节相同），用户实机验收通过。

## 6. 离线步幅估计（offline 方法，不是求解器）

用于在进游戏前比较候选：`Hip` 固定，把一侧大腿转过 −30…60° 屈伸 × 0…30° 外展（28 个姿势）；
每条裙链从根到尖逐段做锥面搜索，找清开所有碰撞体所需的最小偏角（在上一段已旋转的坐标系里量，
受该节点 `angleLimitRad` 限制）；相邻裙链之间取直纹面当裙面；从髋竖轴向每个摆好姿势的腿/髋皮肤
顶点打水平射线，先碰到裙面就算「皮肤在裙外」。

| 候选（Diana） | 漏的姿势 | 最深 |
| --- | --- | --- |
| 无碰撞 | 13 / 28（从 30° 屈 + 10° 外展起） | — |
| v0.2：节点球 | 6 / 28（从 45° 屈 + 20° 外展起） | 85 mm |
| v0.3：中间节点胶囊 | 2 / 28（只剩 60° 屈 + 20–30° 外展） | 10 mm |

局限：贪心逐段求解、链与链独立、裙面是骨线的弦（腰部弦下垂会在静止时就报约 1 cm 的假阳性，
Hugh 有此基线）；只用于**相对比较**，结论要实机确认。

## 7. 被否决或未做的方向

- 裙根摆角 30° → 40°（极端姿势所需 32–35°）：模型里反而更差（根段侧摆拉开相邻裙片），保持 0.524。`rejected`
- 裙片之间的 chain2 link（鬼武者 v0.10 的做法）：本作原生 chain2 没有 link 先例，v15 的 link 布局未验证；
  v0.3 已被接受，未做。`hypothesis`（下一候选）
- 用角色原生 `.clsp` 给替换模型当碰撞。`rejected`
