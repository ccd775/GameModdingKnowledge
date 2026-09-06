# 替换槽位、动画基准与 Zoey/TeenAngst

本文回答一个容易被误解、但会直接决定角色体态的问题：动漫比例 survivor 替换 Mod
中所说的“使用 Zoey 动画”到底是什么。Hunter、Witch 等 non-survivor 不属于本文的
Zoey 默认范围，必须使用其目标槽位或已验证同槽位参考的动画合同。

结论先行：**输出到哪个幸存者槽位，和角色使用哪套动画基准，是两个独立决策。** Louis 模型完全可以继续覆盖 `survivor_manager.*`，同时使用 Zoey/TeenAngst 的动作族和 proportion corrective 基准。

## 1. 五个必须分开的合同

不要再用一个“目标角色”变量同时代表下面五件事：

| 合同 | 决定什么 | 典型来源 |
| --- | --- | --- |
| Output/replacement slot | VPK 覆盖路径、游戏身份、语音与选择逻辑 | 当前游戏实际生效的目标 survivor |
| Slot interface | arms/HUD 路径、attachments、hitboxes、physics、部分活动接口 | 当前目标槽位与成功同槽位 Mod |
| Character bind/rest skeleton | 角色静态骨长、头身比、肩宽、腿长、附件骨 | 同角色成熟 Mod和用户源模型 |
| Primary animation family | idle、walk、run、aim、武器、gesture、IK 的动作来源 | 锁定的动画 include/sequence 合同 |
| Proportion corrective baseline | autoplay proportion 中被减掉的 parent-local translation 基准 | 与主动画族匹配的一帧 native reference SMD |

地面修正还应作为第六个独立测量项记录。它只属于 proportion target 的 Pelvis local Z，不属于 Zoey 动画本身。

以 Louis 为例：

```text
output slot              = Louis / survivor_manager
slot interface           = Louis arms, HUD, attachments, hitboxes, physics
character rest skeleton  = 自定义动漫角色自己的 Source rest
primary animation family = Zoey / TeenAngst
corrective baseline      = native TeenAngst parent-local translations
ground correction        = 当前模型鞋底实测值
```

这不是混搭错误，而是角色替换的正常分层。

## 2. “使用 Zoey 动画”是什么

在本知识库的工作约定中，它至少同时包含两项：

1. **Zoey/TeenAngst 动作与序列族**

   `anim_teenangst.mdl` 和 `gestures_TeenAngst.mdl` 提供主要 locomotion、idle、aim、武器、gesture 与 IK 动作。具体项目可能还有 Producer、generic gestures 或 Biker gestures 等兼容 fallback；后续 include 的存在不自动改变主动画族，必须结合顺序、sequence 解析和 corrective 来源判断。

2. **与动作族匹配的 proportion corrective translation 基准**

   公共 ValveBiped 骨从原生 `TeenAngst.smd` 取 parent-local translations；corrective 和 target 都使用自定义角色的 local rotations。StudioMDL 在 frame 0 做 subtract，生成 translation-only autoplay delta，把 TeenAngst 动画的骨长基准适配到自定义角色自己的 rest proportions。

这两项必须一致。只换 include 不换 corrective，或只把 corrective 换成 TeenAngst 却继续使用另一套不兼容的主 sequence 合同，都是混合合同。

## 3. Zoey 不是什么

| 误解 | 正确解释 |
| --- | --- |
| 使用 Zoey 动画就必须替换 Zoey | 错。输出槽位仍可为 Louis、Rochelle 或其他幸存者。 |
| 要把 `$modelname` 改成 `survivor_teenangst.mdl` | 错。`$modelname` 由 replacement slot 决定。 |
| 把自定义角色骨架改成 Zoey 身材 | 错。自定义 bind/rest 应保持同角色成熟比例。 |
| 直接把 TeenAngst translations 写进最终 bind skeleton | 错。这会把角色拉向 Zoey 身材；translations 只作为 corrective 被 subtract。 |
| Zoey 会自动解决鞋底接地 | 错。ground correction 是最终鞋几何和动画基准之间的独立测量。 |
| Zoey 自动提供 Louis 的 hitbox、arms、HUD、attachments 或 PHY | 错。这些仍来自 output slot interface。 |
| 只要 QC 中出现 Biker/Producer include，主动画就不是 Zoey | 错。它们可能只是成功合同的 gesture/fallback。 |
| 动漫角色必须站成完全直膝 | 错。Zoey 的实际 idle 本身可以有自然屈膝与 foot IK。 |

## 4. 为什么动漫比例 survivor 默认使用 Zoey

本知识库把以下规则设为工作区强制默认策略：

> 对本知识库管理的动漫风格/动漫比例 survivor，如果没有另一套已由同类成熟 Mod、
> 编译后二进制和游戏实机共同证明的动画合同，必须使用 Zoey/TeenAngst 作为主动画和
> corrective 基准；不得根据 Louis/Rochelle 等输出槽位自动回退到 Manager/Biker/
> Producer rest。该规则不覆盖 infected 或其他 non-survivor runtime family。

它是本工作区由多个成功与失败案例得到的工程策略，不应伪装成 Source 引擎对全世界所有模型的绝对定律。如果一个新角色明确需要男性动作风格，或已有另一动画族的成熟同角色实机成功合同，可以例外，但必须把选择理由、reference 哈希、include/sequence 合同、编译结果和实机证据写入报告。

## 5. Proportion corrective 的准确作用

定义：

- `T(b)`：自定义角色 proportion target 的 parent-local transform。
- `C(b)`：动画基准 corrective 的 parent-local transform。
- `g`：独立测得的 Pelvis 地面修正。

对自定义角色与 TeenAngst 共通的接口骨：

```text
T.position(b) = custom_rest.position(b)
T.rotation(b) = custom_rest.rotation(b)

C.position(b) = teenangst_rest.position(b)
C.rotation(b) = custom_rest.rotation(b)

T.position(Pelvis).z += g
```

对角色独有附件骨：

```text
C(b) = T(b) = custom_rest(b)
```

StudioMDL 生成：

```text
D = subtract(T, C[frame 0])
```

运行时把 `D` 叠加到 TeenAngst 动画上。它修正的是动画的局部骨平移基准，不替换角色 bind skeleton。由于 `T.rotation == C.rotation`，编译后的 proportion rotation delta 应为 identity。

正确结果是：动作来自 Zoey，角色身材仍是自定义角色。

## 6. Sequence、include 与 flags 不能跨项目照抄

“使用 Zoey”不等于所有项目都复制同一份 QC。

- `$declaresequence` 是有序接口合同，不能从 include MDL 的 sequence 名称集合重新生成，也不能自动去重或排序。
- `$includemodel` 的路径、大小写和顺序按锁定成功合同保真。
- `reference`、`proportions` 的 flags、是否 hidden、`delta`/`predelta`/post 语义按该输出路径的成熟成功合同保真，并从编译后 MDL 复核。
- Karin_PT/Rochelle 案例的 `proportions` 编译 flags 为 `1052`；Riptide/Louis 成功路径合同为 `12`。这两组都可以以 Zoey 为主动画基准，却不能互相替换 flags 或 declaration 表。

因此，动画选择至少要记录两个来源：

```text
primary_animation_basis = Zoey / TeenAngst
sequence_contract_source = <已验证的当前输出路径合同>
```

## 7. 实施流程

1. 锁定 output slot 的世界、arms、HUD 路径。
2. 锁定角色 rest 证据并选择 bind 策略：target-fit mesh 才做逐骨 bind-space 重定向；source-fit skeleton 则把目标 pivot 贴合源网格并保持网格统一 similarity。
3. 明确 `primary_animation_basis = Zoey / TeenAngst`。
4. 哈希锁定 native TeenAngst animation MDL/ANI，并从 compiled rest 解码 corrective translation；反编译 reference SMD 作为交叉证据。
5. 从当前成功合同原样保留 ordered declarations、重复项、includes 和本地尾部 sequence 结构。
6. 生成一帧 corrective：TeenAngst common-bone translations + custom rotations。
7. 生成一帧 target：custom rest translations/rotations；只有 Pelvis 可加入已测 ground offset。
8. StudioMDL subtract 后，独立解析 MDL 验证 proportion rotation identity、translation 与报告一致。
9. 对 reference/rest pose 和真实 idle 分开量化。reference 用于检查腿链长度；idle 的自然屈膝属于动作表现。
10. 在游戏中复测站立、行走、奔跑、蹲伏、受伤、持枪和 foot IK。
11. 若存在 light 本地序列，分别记录 strict reference diagnostic 与 relative-to-bind motion hard gate。

## 8. 强制报告字段与门禁

构建报告至少包含：

```json
{
  "output_slot": "<survivor/path>",
  "slot_interface_source": "<report/hash>",
  "rest_skeleton_source": "<report/hash>",
  "primary_animation_basis": "Zoey / TeenAngst",
  "corrective_source": {"path": "<native animation MDL or proven SMD>", "sha256": "<hash>"},
  "sequence_contract_source": "<report/hash>",
  "ordered_includes": [],
  "declaresequence": {"total": 0, "unique": 0, "duplicates": {}},
  "ground_offset": {"owner": "proportion-target Pelvis local Z", "value": 0}
}
```

进入实机测试前必须通过：

- output slot 不能被动画选择偷偷改写。
- Zoey profile 的 corrective 必须来自已锁定 TeenAngst animation rest，而不是 Manager/Biker/Producer reference。
- target/corrective 节点表和父链一致，各只有一帧。
- common-bone translations 分别来自 custom rest 和 TeenAngst rest；角色独有骨在两帧相同。
- target/corrective rotations 相同；编译 proportion rotation delta 为 identity。
- ordered includes、declarations、unique 数、重复明细和尾部 sequence flags 与锁定合同一致。
- Calf/Foot/Toe 等 parent-local 链长没有因错误 corrective 被压短。
- ground offset 只有一个所有者；bind mesh/skeleton、Foot/Toe、attachments、physics、bbox 没有被顺手移动。
- target translation 逐轴等于 custom parent-local rest；禁止用 `normalize(native_axis) * target_length` 把姿势差混入比例差。
- light 的 bind-relative 动画覆盖完整；strict reference 因角色 bind 不同为 false 时只作诊断，不据此交换 L/R。

## 9. 常见反面案例

- 根据 Louis 槽位直接选择 `Manager.smd` corrective 和 Biker 主动画。
- 保留 TeenAngst include，却继续 subtract Manager corrective。
- 把 TeenAngst translations 写进最终 bind skeleton，导致角色被改造成 Zoey 比例。
- corrective 和 target rotations 不同，产生不需要的旋转 delta。
- 把 include 的 sequence 集合去重后重建 `$declaresequence`。
- 看到 idle 自然屈膝就继续调低 Pelvis，混淆动作 pose、腿链长度与鞋底接地。
- 为了落地直接移动鞋网格、Foot/Toe 或 bbox。

Riptide Louis 的定量反例见 [Karin Riptide 替换 Louis 案例](16-riptide-louis-case-study.md)。
