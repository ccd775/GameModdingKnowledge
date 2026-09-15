# chain2 v17 次级物理

本作次级物理走 `.chain2.17`（由 `.pfb.18` 显式消费）。本文是本项目对该格式最完整的
可复用产出：格式本身是 `invariant`（对任何使用 chain2 v17 的 RE Engine 作品成立），
具体参数值是 `case-derived`。

## 1. 可行性：先查第二个实现，再下 BLOCKED

本项目一度把物理判为 `BLOCKED`，理由是「Blender 侧的 `RE-Chain-Editor` 只支持
`{4,9,12,13,14,15}`，且上游已归档为只读，不会再有 v17」。**该结论当天被推翻。**

错在只查了一个来源。另一个实现（RE-Engine-Lib 的 `Chain2File`）早就注明了 v17 的
header 分支，而真实情况是：

> **v17 与 v15 的唯一差异就是文件头，所有子结构完全兼容。**

`invariant` 教训：判「格式不支持」之前，至少把 **Blender 插件之外的第二个实现**
（C# / 独立库 / 其他游戏的移植）查一遍。归档的上游不等于没有实现。

## 2. v17 头部布局（confirmed，112 字节）

相对 v15：**删除** `collisionAttrOffset` 与 `extraDataOffset`（两者 `version < 17`
才有），**新增** `windSettingsOffset` 之后的 8 字节 null padding。因此偏移表是
6 个真实 uint64 + 1 个填充槽。

```text
0x00 version(u32)  magic(u32)='chn2'
0x08 errFlags(u32) masterSize(u32)
0x10 modelCollisionOffset  groupsOffset  linksOffset  freeLinksOffset
     settingsOffset  windSettingsOffset  padding            (7 x u64)
0x48 groupCount settingCount modelCollisionCount windSettingCount
     linkCount rotationOrder defaultSettingIdx calculateMode (8 x u8)
0x50 attributeFlags(u32)  paramFlags(u32)
0x58 calculateStepTime(f32)
0x5C modelCollisionSearch taperedCollideMethod freeLinkCount freeLinkJoint
     + HitFlags[8]                                          (12 x u8)
0x68 wildsUkn1(u16) highFpsCalculateMode(u16) wildsUkn3(u8) wildsUkn4(u8) pad(u16)
0x70 = 112 结束
```

不变量（4 个原生文件全部满足）：padding 槽恒为 `0`；`settingsOffset` 恒为 `112`；
`modelCollisionCount == 0` 时 `modelCollisionOffset == groupsOffset`。

记录大小：settings `184` B，collisions `80` B，groups `104` B，wind `184` B，
links `40` B，nodes `96` B。

**闸门做法**：用上述头部 + 插件原有的 v15 section 读写器，对每个原生文件逐 section
重新序列化并与原字节比对，要求**逐字节一致**再开工。本项目 4 个原生文件全 PASS。

### 一个会咬人的字段宽度

group 记录里的 `nodeCount` 在 group+12，必须按 **u8** 读；按 u32 读会拿到垃圾值。

节点记录（96 B）内本项目实际用到的字段偏移：

| 偏移 | 字段 |
| ---: | --- |
| `0` | `angleLimitDir`（4 x f32 四元数） |
| `16` | `angleLimitRad` |
| `32` | `collisionRadius` |
| `36` | `collisionFilterFlags` |
| `56` | `windCoef` |
| `72` | `gravityCoef` |
| `80` | `basePos` |

### 一个纯靠经验推偏移的教训

早期的 setting 偏移常量是凭经验推的，其中两个**错位一个槽**：

| 字段 | 曾用（错） | 正确 | 错误常量实际指向 |
| --- | ---: | ---: | --- |
| `friction` | `88` | **`84`** | `shockAbsorptionRate` |
| `hardness` | `128` | **`124`** | `windDelaySpeed` |

后果：连续三个版本「设 `friction = 0.05`」其实写进了 `shockAbsorptionRate`；另一个
被全字段 diff 标为可疑的 `hardness = 0.3` 其实是 `windDelaySpeed`，属误读。

`invariant` 修法：按结构体的**声明顺序**重新推导偏移，并要求推导结果**恰好消耗满**
记录长度（本例 184 字节）。对不上就说明中间漏了字段。

## 3. `angleLimitDir`：本项目最贵的一条语义

### 3.1 字段用途

`angleLimitDir` 是单位四元数，把 `+X` 旋转到该节点的**静止指向**（rest aim）；
`angleLimitRad` 是绕该轴的**锥形限制半角**。

### 3.2 参考系是**父骨坐标系**，不是骨骼自身坐标系

这条先判错过一次。换算公式（`loc` 行主序、行即坐标轴，故骨骼系→父骨系是右乘）：

```text
d_bone   = normalize(child.localT)           # 子骨 localT 本就在本骨坐标系中
d_parent = normalize(d_bone @ R_bone_local)  # 转到父骨坐标系
q        = q_from_to(+X, d_parent)
```

即它编码的是骨骼的**完整静止朝向**，包含骨骼自身的 local 旋转。终端节点保持单位
四元数。

### 3.3 为什么第一次的「证明」无法分辨

第一次用四条原生链精确验证（离散度 `0.00°`）——但那四条链的骨骼 local basis
**全是恒等的**。对恒等 basis 的骨骼，「骨骼自身系」与「父骨系」是同一个东西，那组
样本在原理上就不可能区分两种解释。

只有 local basis **非恒等**的链条才有分辨力（本作是 Capcom 的头发链）。在这些骨骼上
重新打分：骨骼自身系解释给出 `28.18°` 误差，父骨系给出 `0.00°`。

**部署后的实机症状也带签名**：错版的每个四元数都被沿链**上移了一节**（node 02 拿到
node 01 的真实指向，依此类推），根节点落到世界 `+Y` —— 表现为「尾巴朝天」。
链上整体错位一格就是参考系差一级的特征。

`invariant` 教训（本项目连续两次误判的共同模式）：**用无分辨力的样本确认假设**。
确立格式语义前先问一句 —— 这批样本能否证伪竞争假设？不能就换样本。之后的回归测试
必须用 basis 非恒等的链条。

### 3.4 两种骨骼约定共存，不必重建骨朝向

`angleLimitDir` 会**吸收**骨骼 local basis 的差异，所以同一个游戏里两种约定都能跑：

| 约定 | 代表 | 骨骼 local basis | 子骨偏移 | `angleLimitDir` |
| --- | --- | --- | --- | --- |
| 瞄准式 | 头发链 | 局部 X 指向子骨 | `(len,0,0)` | 接近单位四元数 |
| 单位式 | 身体链（腰带 / 袴 / 襷） | 恒等 | 任意方向 | 携带完整瞄准旋转 |

不变量是 `localBasis ⊗ angleLimitDir = 静止指向`。**结论：为了上物理去重建骨骼朝向
是不必要的**，Blender 导出的瞄准-Y 约定可以直接用，只要按实际 mesh 几何反算四元数。

### 3.5 沿用供体四元数 = 必然失败

修正前，本项目 10 条链的静止指向误差全部落在 `75°–152°`，而锥半角只有 `90°` 甚至
更小 —— **每个关节的静止目标都落在它自己的限制锥之外**。三个症状同时被解释：

- 求解器把每个关节顶在限制边界上 → 实机「太僵，几乎不动」
- 沿链等量的逐关节角误差在几何上画出圆弧 → 实机「整体卷曲」
- 这是**约束**不是力 → 任何 `gravity` / `springForce` / `damping` 都改不动它

前两版调参只动力的参数，因此以完全相同的方式失败。反过来说：**在求解器近乎静止时
仍然存在的形变，不可能是力的参数问题** —— 这条可以直接用来分诊。

修正后全部 `0.00000°`。

## 4. 调参纪律：从原生出发

本项目在这一条上返工了**三次**，是最贵的教训。

> **默认应当是「保留原生动力学，只改已证明必须改的」。跨链族搬运档位之前，必须逐
> 字段确认目标链族本来用什么值。**

三次返工的具体形态：

1. **把长链档位整包套到头发链上。** 头发的 `minDamping` 原生是阻尼**斜坡**的远端
   （根部 `0.25` → 发梢 `0.0013`，190 倍），而长链是**均匀阻尼**
   （`damping == minDamping`）。照抄长链把斜坡压平，整条发丝变得迟钝。
   `springMaxVelocity` 同理：原生头发是 `0`（不限速），套成 `0.10` 直接给归位速度加了
   上限 —— 这就是「归位太慢」的字面成因。
2. **力平衡被拉爆。** 把重力降到 `-0.98` 又把节点 `gravityCoef` 压到 `0.40`
   （合计 `25×` 削弱），同时把 `springForce` 提到 `8.5×`，净效果是 **`214×` 偏向弹簧**：
   几乎没有力驱动链条，强弹簧把它钉在静止姿态上。用户反馈的「软绵绵」和「很硬」其实
   是同一件事的两个阶段 —— 链条越来越接近静止，最后**完全停止仿真**。
   诊断量：**有效重力 = `gravity.y × 节点 gravityCoef`**，与 `springForce` 一起算
   力平衡偏移倍数，和原生对照。
   全程唯一正常的那条链，恰恰是「只关了风、其余全保留原生」的那条 —— 它是现成的
   对照组。
3. **第三次是同源的**：先诊断一条链的原生取值，再决定改不改。

### 分诊用的字段责任表（case-derived，但归因方式可复用）

| 症状 | 主控项 |
| --- | --- |
| 静止形态 / 垂坠程度 | `gravity` 与 `springForce` 之**比**；逐节点 `gravityCoef` |
| 站立不动时持续轻微抽动 | **环境风**：`windEffectCoef` / `envWindEffectCoef` / 节点 `windCoef` |
| 「整根刚体绕根部转」、没有段落感 | 阻尼**梯度**：`damping → minDamping` 的比值、`dampingPow` |
| 归位太慢 | `springMaxVelocity`（速度钳位）、`springForce` |
| 弹来弹去、停不下来 | `minDamping` 抬一档、`shockAbsorptionRate` |
| 「不跟随、发硬」 | 根部 `collisionRadius`（被碰撞体夹住）、`reduceDistance` |

### 风是个容易漏的驱动源

某版的静止抖动查到最后是**场景风**：本 Mod 的链沿用了供体腰带的
`windEffectCoef = 0.35`，而与本链尺度最接近的原生长链把风**完全关掉**。

风能解释全部现象：环境风是持续、随时间变化的力，角色站着不动它也不停（静止抖动）；
高频低幅（「快速轻微抽动」）；与弹簧刚度无关（软化 2.5 倍无效）；链越软对同一外力
响应越大（「更软了但还在抖」）；在 `0.06 m` 的供体腰带上看不出来，在 `1.03 m` 的链上
被放大 5 倍以上。

注意 `envWindEffectCoef` 耦合的是**场景风**，不是 chain2 内定义的风 —— 文件的
`windSettingCount = 0` **不代表**没有风。

### 终端节点也在被仿真

一次 `VERIFY FAIL` 的成因：脚本的终端分支只设了 `collisionRadius` / `gravityCoef`，
`windCoef` 还留着 `1.00`。

> 终端节点虽然没有出向段（`angleLimitDir` 保持单位四元数），但它**仍然是被仿真的
> 节点**。除「瞄准类」字段（`angleLimitRad` 等）外，所有节点字段都应当施加于它。

## 5. 结构约束与能力边界

- **多条链共用一个 setting 是常态。** 本作 `ch001_00_20` 的 8 条头发链（group 0–7）
  全部共用 setting 1。若编辑器是定宽原地覆写，逐链差异就只能走**节点级**字段
  （`gravityCoef` / `angleLimitRad` / `windCoef` / `collisionRadius`）；好在静止形态由
  `gravity/springForce` 之比决定，而 `gravityCoef` 恰好是节点级的，垂坠度仍可逐链调，
  只是振荡频率特性全局共享。需要真正独立时才做 `add_setting` + `set_group_setting`。
- **分辨率不是参数问题。** 「整条一起动、没有段落感」在阻尼梯度之外还有一个上游成因：
  节点太少。解法是构建器合成链骨 + `grow_group` 给 chain2 扩容，并**随段数重标定弹簧**。
- **合成链的第一根骨要有私有根。** 常见的链骨合成实现走 `zip(target, target[1:])`，
  因此 `target[0]` 必须已存在。让多条链共用一个闲置 helper 会让多个 group 写同一个
  `node[0]`；原生的每条裙摆链都有自己的 `_HJ_00`，**从不共用**。正确做法是给每条链在
  指定原生骨下合成一个私有根（形状与头发链一致：`FL03_chain_00` 的父级就是原生
  `Head`，而 `Head` 不属于该 group）。
- **Capcom 从不做嵌套链。** 审计全部 22 个原生 group 后确认：每个 group 的根都是没有
  任何其他 group 在模拟的骨。因此源模型里挂在「已被模拟的骨」下面的部件（本例
  `Back_Ribbon` / `Tail_Ribbon` / `Pocket_String`）没有现成先例，改锚到刚性骨又会让它
  脱离所依附的部件 —— 这是需要决策的分叉，不要猜。

## 6. 碰撞：不要用补碰撞体解决约束问题

一条挂了很久的「必须为长链补 Chest/Spine/UpperArm 等效碰撞覆盖」的前置条件被实测
**撤销**。四个原生 chain2 的 `modelCollisionCount`：

| 文件 | 组数 | 模型碰撞体 |
| --- | ---: | ---: |
| 身体 `ch001_00_00` | 22 | **0** |
| 头发 `ch001_00_20` | 10 | 2（均在 `Head`） |
| 斗篷 `ch001_00_01` | 22 | 8 |
| 斗篷变体 | 22 | 4 |

身体链一个碰撞体都没有 —— 和服、腰带、袖子全靠**角度限制 + 回拉项**约束。所以「与原生
等价的覆盖」对身体链而言就是 `0`。

chain2 内的 UTF-16 字符串只有碰撞**过滤器**（`Chain_Terrain.cfil` /
`CharacterDefault.cfil` / `Cloth_Character.cfil`），不是碰撞**几何**：节点自带
`collisionRadius` 胶囊，`collisionFilterFlags` + `.cfil` 决定它与哪些层相碰，角色本体
碰撞由引擎侧提供。

**穿模的正确手段是角度限制与回拉项，不是补碰撞体。**

## 7. 左右不对称：先证伪数据，再归因动画

这条走了两轮。

**第一轮（结论对但不是病因）**：把 8 条头发链的 `collisionRadius` 排开，发现供体侧
有一条链的前三个节点脱离了全文件默认的 `0.005 / 0.005 / 0.010`，是原作者为某一缕头发
手调的。源角色的头发本就不左右对称，而替换进来的角色是**严格镜像**的，所以这组差值
纯属**供体残留**，没有几何依据。清掉是对的。

注意取样：只看 node 0 会得到「0.005 对 0.006，四舍五入级别」的印象；node 1/2 的
`1.6×` / `1.8×` 才是实情。**取样不足以支撑结论**是这一轮的直接成因。

**第二轮（真正的结论）**：对齐之后左右仍然不同。做了穷尽比对 —— 96 字节节点记录的
20 个字段逐字段 diff、solver setting 是同一条记录、节点数与数组区间、骨骼 rest 镜像
残差 `< 1e-5`、蒙皮权重差 `< 0.5%`、碰撞体侧向分量全为 0、部署侧 SHA-256 无第二份文件
遮蔽。唯一的差异 `angleLimitDir` 解出来是正确镜像（两侧偏离 `+Y` 约 7 度、符号相反，
和为 180 度）。

> **病因是角色动画本身不对称**：持刀手、待机姿势、步态左右都不同，同一套参数在两侧
> 受到的激励不一样。这不是能在 chain2 里修的东西。
>
> 推论：不要再把左右差异当数据缺陷来查。可动作的信息在「两侧共有」的那一半反馈里
> （本例是「一整根在动」→ 阻尼梯度太平）。

## 8. 验证器该验什么

每次改完 chain2，离线验证器至少要覆盖：

- 逐节点**静止指向误差**（世界系口径），要求全部 `0.00000°`，并显式检查方向语义
  （例如尾巴必须 `down=True back=True`）与 `|q| = 1`。
- 风字段全零（若该版策略是关风）、`shockAbsorptionRate` 等易错字段回到预期值。
- **未申报却带权重的链**：维护一个 `TARGETED` 终端骨集合，新链的终端骨必须未加权
  （原生约定）。这道检查在本项目真的报过 FAIL 并拦住了错误。
- **结构闸门**：回读 v17 头，逐组累加 `nodeCount`，断言
  `group / setting / node / 字节数` 四元组，并校验每个组的节点数组不越界。自己**追加**
  生成的文件，纯哈希锁挡不住「写了一半但哈希被一起更新」，结构闸门才挡得住。
- **差量证明**：用字节级 diff 证明这一版**只改了**声明要改的那几个 float。本项目靠
  它顺带证明了一次「几何版本没有移动任何链骨的 rest」。

若某版改动是定宽原地覆写，`group/setting/node` 三元组**应当保持不变** —— 数量一旦
变化就是 bug，而不是新基线。
