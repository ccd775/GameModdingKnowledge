# chain2 物理：槽位、注入、CollisionTarget 与裙摆

格式（chain2 `.15`、PFB `.18`）与 PRAGMATA 相同，节点记录、碰撞体记录、胶囊节点的细节见
[PRAGMATA 物理](../pragmata/CHAIN2_PHYSICS.md)；这里只写本作不同或新增的部分。参数值是 `case-derived`。

## 1. 写进原生已加载的槽位

原生 prefab 已经加载 chain2 的部件，直接用 Karin 的 chain2 覆盖同路径文件，prefab 不用改路径：

| 角色 | 头发 chain2 | 身体 chain2 |
| --- | --- | --- |
| 里昂 | `20_00` | `40_00`、`40_01` |
| 格蕾丝 | `20_00`、`20_02`、`20_03` | `40_01`、`40_02`、`40_03`、`40_04` |

内容（两个角色相同）：头发 chain2 11 组 / 41 节点（双马尾 2、侧发/前发/发饰 7、猫耳 2）；身体 chain2 26 组 /
89 节点（裙片 16、缎带 9、尾巴 1），16 条 link（裙片首尾相接一圈），32 个胶囊节点。

## 2. 给没有 Chain2 的身体 prefab 注入（invariant 做法）

- 全量扫描后，里昂 22 个、格蕾丝 21 个显示完整身体的 prefab **原生没有 Chain2**（清单见
  [技术合同](TECHNICAL_CONTRACTS.md) §2）。其中包括基础 montage 的 `40_70`：v1.0 在展柜里只有头发会动，裙子和尾巴是静止的。
- 注入：从**同一角色**带 Chain2 的原生身体 prefab 复制 `via.motion.ChainWind` + `via.motion.Chain2`（+ 缺的话
  `app.ActorChain2`），`ChainAsset` 指向 Karin 身体 chain2（里昂 `40_00`、格蕾丝 `40_01`），`EnvWind` 指向新插入的
  ChainWind，`CollisionTarget = 0`（见 §3）。插入后平移对象表索引。
- 验证器：每个显示被替换身体的 prefab 恰有一个 Chain2，且加载 Karin 的 chain2；未改动的 prefab 读写逐字节往返。

## 3. CollisionTarget：chain2 自带碰撞体为什么不生效（runtime 证据）

**症状（v1.1，展柜 + 探针）**：chain2 里按网格拟合了大腿/骨盆胶囊，静止间隙闸门也全部通过，但运行时探针读到
裙片节点陷在大腿胶囊里约 6 cm，双马尾穿进躯干。

**排除过的方向**：

- chain2 表头 `wilds_unkn0` 改成原生值（身体件 3、头发 20；参考 mod 是编辑器默认 0），第一个 setting 加 `Default`
  标志（`settingsAttrFlags` bit0）—— 单改这些无效（`rejected` 为成因；仍按原生值写）。
- 在 `Hip` 上放测试碰撞体 —— 节点完全不受影响，说明问题不在碰撞体尺寸或位置。

**原因**：REFramework 读出的运行时枚举 `via.motion.Chain2.CollisionTarget` = **Self 0 / Extern 1 / All 2**。
原生角色 prefab 的 Chain2 全部是 **1（Extern）**：只和角色 `.clsp` 碰撞，chain2 文件里的模型碰撞体被忽略。
参考 mod 把所有 clsp 换成大腿胶囊，正是在这个限制下让裙子有碰撞。

**修法（v1.2）**：所有加载 Karin chain2 的 Chain2 组件（原生槽位 + 注入的）设为 **0（Self）**：里昂 95 个、
格蕾丝 53 个组件。clsp 保持原生。修后探针：里昂展柜里裙片节点全部在碰撞体外，双马尾停在躯干碰撞体表面。
证据级 `runtime-load-pass`（展柜 + 探针数值，用户未在实际游玩里确认）。

**跨作对照**：PRAGMATA 插入的 Chain2（从原生部件复制）和带 chain2 内置大腿胶囊的原生 ch09000，`CollisionTarget`
都是 0，所以那边的模型碰撞体能生效。新的 RE Engine 项目里，先读模板组件的这个字段，再决定碰撞体放在 chain2 还是 clsp。
`All (2)`（同时碰 clsp 与自带碰撞体）本项目未测试；里昂/格蕾丝的原生 clsp 是按他们自己的体型做的，不适合 Karin。

## 4. chain2 内容

- 模板 = 参考 mod 的 chain2（表头、setting、风、group、节点记录）。每个链族取参考 mod 中对应的一组：setting 和
  沿链重采样的节点角度限制。

  | 链族 | 参考组（链尖） | 备注 |
  | --- | --- | --- |
  | 双马尾 | 头发 `Hair_Tail_L_end` | |
  | 侧发 / 前发 / 发饰 | 头发 `Hair_Side_L_end` | |
  | 猫耳 | 头发 `Hair_Front_end` | `gravityCoef 0.30`（鬼武者 / PRAGMATA 的长耳朵值） |
  | 尾巴 | 头发 `Tail_end` | 半径 8 → 30 mm |
  | 裙片 | 身体 `OuterA_L_end` | 半径 5 / 15 / 25 / 30 mm，中间节点 `collisionShape = 2` |
  | 缎带 | 身体 `Pocket_String_L_end` | |

- group `attrFlags = 0x840B`（RootRotation | AngleLimit | CollisionDefault | WindDefault | EnableEnvWind）。
- `angleLimitDirection` = 把 +X 转到子节点方向的四元数，在父（锚点）骨坐标系里表示；与参考 mod 的数值对过。
- link：相邻裙片两两相连成一圈（16 条）。记录从参考 mod 外套片之间的 link 复制，`nodeOffset = 0`，`nodeCount`
  保留参考值（曾把 nodeCount 清零，已撤回）。本作的参考 mod 实机带 link，这是 link 在 chain2 `.15` 上可用的先例
  （PRAGMATA 当时没有）。

## 5. 碰撞体拟合（做法同 PRAGMATA，值为里昂）

| chain2 | 碰撞体（shape 2，`endRadius = radius`） |
| --- | --- |
| 身体 | 每条大腿两段（r 0.0899 / 0.0692）、小腿一段（r 0.0654）、骨盆两根横杆（裆部 r 0.0748、髋臼 r 0.105） |
| 头发 | 大腿与骨盆同上，另加 `Spine_1` / `Spine_2` 两根躯干横杆（r 0.0831 / 0.0907），给双马尾用 |

静止间隙闸门：每个模拟节点（含胶囊段）在所有碰撞体外 ≥ 2 mm。裙片最小间隙正好卡在 2 mm（由闸门收缩得到），
头发最小 7.7 cm。

## 6. 展柜里能看到什么物理

- 里昂：身体 Chain2 开着（展柜只关他的外套 `45`，本来就被屏蔽），可以看到裙摆和双马尾的碰撞。
- 格蕾丝：展柜给 `40` 喂专用动画并关闭其 Chain2 → 身体链（裙、缎带、尾巴）不动，只有头发会动。这是游戏行为。
- 要看格蕾丝的身体物理，只能进实际游玩（本项目未做）。

## 7. 其它

- 格蕾丝 `40_02`（prefab 后缀 `103`）原生带 GpuCloth，它模拟的是原生衣服的顶点，在 Karin 的身体上没有有效对象，
  已关闭（`case-derived`）。
- 头发部件的 strands（`21`）未处理。

## 8. 被否决或未做的方向

- 只改 chain2 表头 / Default 标志让碰撞生效。`rejected`
- 照参考 mod 用大腿胶囊替换角色 clsp。未采用：改 CollisionTarget 只影响加载 Karin chain2 的组件，不动角色级碰撞形状；
  两种做法没有在实机里比较过。
- `CollisionTarget = 2 (All)`。未测试。
- 实际游玩中的跟随感、抖动、过场重置。未测试。
