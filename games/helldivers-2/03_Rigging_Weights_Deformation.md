# 骨架、权重与变形合同

> 范围：Helldivers 2 角色替换中的坐标空间、骨架 rest、inverse bind、局部骨调色板、权重迁移、连通片、LOD、肩腹接口与手指动画。
>
> 结论来源：通用权重、finger 与资源格式经验保留自既有案例；肩部主方法来自 `Karin_Nyako_RE2310` RefBindAxis；跨 profile 开放肩缝由 DR03 补充；源 Shoulder/UpperArm 到目标单肩骨的折叠、按角色完整 Unit 克隆和骨盆桥接由 Umbrella v1 运行时反例与 v2 离线审计补充；自然 shoulder 权重优先、禁止 clavicle blanket override、差分姿态 moving-set 防假阳性与 DS42 owner clone 正向运行时证据来自 SSF FS37/SC15 v4。各项目当前状态仍以各自 SOP 为准。

## 事实等级

本文逐项使用以下标签，不能互换：

| 标签 | 含义 | 使用限制 |
| --- | --- | --- |
| `format-confirmed` | 由 AQ/HD2SDK 路径、序列化字段或独立二进制回读确认的格式行为 | 可作为当前工具版本的默认合同；升级工具或游戏后仍须复测 |
| `project-proven` | 在至少一个真实 HD2 Mod 中通过构建/审计，或由用户运行时截图证实的做法/失败模式 | 方法可迁移；模型尺寸、阈值和骨集合不可照抄 |
| `case-specific` | 特定角色、参考、槽位、候选的数字、索引、半径或 ID | 只能作为案例或新项目阈值的起点 |

## 1. 正确的心智模型

一个可用的蒙皮模型必须同时满足三个彼此独立的合同：

```text
几何合同：顶点究竟处于哪个 mesh-local 空间，是否仍保持源角色形体
绑定合同：TransformInfo / MeshInfo / BoneInfo / inverse bind 是否同源且自洽
权重合同：每个 Unit/LOD 的局部 palette、每点权重和跨分件边界是否连续
```

- `format-confirmed` AQ whole-unit swap 会保留 donor entry 的 `TransformInfo`、`BoneInfo`、`MeshInfo transform`、inverse bind 与 section 结构，再把 FileID 改成目标 `Z_SwapID_N`。它不是“目标 Unit 保留原 bind，只换 RawMesh”。详见 [02_HD2_Resource_Contracts.md](02_HD2_Resource_Contracts.md) 和 [New_SR24 SOP 7.4](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 几何看起来正常、neutral skinning 为 identity、姿态渲染全绿，任何一项都不能单独证明游戏运行时正确。V10 的 11/11 Unit、52/52 集成和 9/9 局部门禁全部通过，仍被用户截图否决，因为测试驱动矩阵没有真正覆盖游戏的外部骨架合同。证据见 [V11 compiled external gate](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 若目标是保留自定义角色形象，默认应保留源文件确认的保存外观（Basis 或保存中的 current shape mix），只允许有证据的全局刚性/等比变换与 rest-to-bind；不能按 HD2 原版骨长逐段拉伸肩、腹、大腿和脚。

## 2. 坐标空间与几何 provenance

### 2.1 写入的一定是 donor mesh-local

- `format-confirmed` AQ 的 `GetMeshData` 直接序列化 `mesh.vertices[].co`，不会替你应用 Blender object matrix；运行时仍会应用 Unit 中的 `MeshInfo transform` 与 inverse bind。
- `project-proven` 把 world/armature-space 点直接写成 mesh-local，会使运行时再次施加 donor transform，表现为整体偏移、肢体错位或非均匀拉伸。
- `project-proven` authoring 输出应把 object transform 归一为 identity，并在报告中记录完整矩阵链，而不是只比较 bbox。

建议显式写出变换链：

```text
p_source_object
  -> source object/armature relation
  -> 已证明的全局 rigid/similarity transform（若需要）
  -> donor armature space
  -> inverse(donor mesh-to-armature)
  -> p_donor_mesh_local，写入 vertices[].co
```

若 `p_armature` 已在 donor armature 空间，而 `M_mesh` 是 donor mesh-to-armature：

```text
p_mesh_local = inverse(M_mesh) * p_armature
```

矩阵的行/列约定必须以当前 SDK 的转换函数为准，不能仅凭公式猜转置。

### 2.2 不要从导入骨的显示形状推断人体骨段

- `project-proven` Stingray 骨导入 Blender 后常显示为约 `0.05 m` 的编辑骨；bone roll 和 `matrix_local` 表示资源 transform 方向，不等于“骨头 head 指向下一关节”的人体方向。
- `project-proven` V1-V3 直接用目标 edit-bone roll 做 A-Pose/逐段拟合，造成长发上翻和四肢拉伸。应先从 donor 源模型与已编译 Unit 证明关节 frame，再决定是否需要 rest 转换。

### 2.3 几何 provenance 必须独立于 bind 验证

对保形项目，建议冻结一个源几何公式并逐顶点检查：

```text
p_candidate = declared_bind_retarget(s * R * (inverse(M_source_armature) * M_source_object * p_source_frozen) + t)
```

其中 `p_source_frozen` 是已证明的 Basis 或保存 current mix，`s/R/t` 必须是单一、可解释、有 donor 对应证据的全局相似变换；`declared_bind_retarget` 必须由有符号语义轴与目标 bind 证明。禁止不可追溯的区域缩放和“视觉修型”。

- `project-proven` 一致 rest 不会恢复已经被静态拟合破坏的几何；几何 provenance 与 bind 必须分别验收。
- `project-proven` V10 的独立几何审计逐 float32 分量证明普通顶点与 bridge 顶点都来自源 Basis 公式，最大位置残差为 0。证据见 [V10 source geometry preservation](../../SOURCE_REFERENCES.md#local-only)。
- `case-specific` V10 的 `s=1.7514482660417752`、平移和 Z 轴 180 度只属于 Karin/O44，不是 HD2 通用值。

## 3. Rest、层级与 inverse bind

### 3.1 LBS 基本关系

用齐次坐标表示线性混合蒙皮：

```text
p_pose = sum_i w_i * D_i * p_bind
D_i    = G_i_pose * inverse(G_i_rest)
sum_i w_i = 1
```

在 HD2 Unit 的 donor mesh-local 约定中，对某个骨语义 `i`：

```text
G_relative_i = inverse(G_mesh) * G_bone_i
inverse_bind_i = inverse(G_relative_i)
neutral_i = G_relative_i * inverse_bind_i ~= Identity
```

- `format-confirmed` `G_mesh` 来自该 LOD `MeshInfo.TransformIndex` 指向的 TransformInfo，`G_bone_i` 来自 BoneInfo `RealIndices` 对应的 TransformInfo。不能假定 mesh transform 恒为 root。
- `format-confirmed` 当前 Stingray/AQ 路径把矩阵以转置的 row-major 形式存储；通过 SDK 转成 Blender matrix 后，若直接编辑原始 16-float 数组，平移在索引 `12:15`。实现证据见 [V21 finger-only compiler](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 修改 global TransformMatrix 的 origin 后，还要由 `inverse(parent_global) @ child_global` 重算相应 local `Transforms[].pos`，并为每个 LOD 中受影响的 BoneInfo 行重算 inverse bind。
- `project-proven` neutral identity 应逐骨、逐 Unit、逐 LOD 检查，而不是只看最终网格“似乎没动”。

### 3.2 Neutral identity 是必要条件，不是充分条件

- `project-proven` 如果候选 rest 与候选 inverse bind 同时按同一个错误假设生成，`rest * inverse_bind ~= I` 仍会通过。
- `project-proven` V10 的 neutral 最大残差仅 `2.4587e-7 m`，跨 Unit origin/segment 差为 0，但真实运行仍严重扭曲。证据见 [V10 final Unit rest audit](../../SOURCE_REFERENCES.md#local-only) 与 [SOP 7.37](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 任何 bind 验收都必须再使用 donor/runtime-proven 外部 rig 施加姿势，并在最终编译 Unit 上回读验证。

### 3.3 不要逐骨拼接不连续 origin

若把骨 `i` 的 rest origin 改动记作 `delta_o_i`，多权重点在中立附近的静态错位可近似理解为：

```text
delta_p ~= sum_i w_i * delta_o_i
```

符号和旋转项取决于矩阵约定，但结论不变：相邻骨的 origin delta 不连续会在混合区形成剪切。

- `project-proven` 逐骨拼接不同 lineage 的 origin 会在多权重边界制造 `sum(weight * origin_delta)` 型静态剪切；应使用一套连续、可证明的 rest lineage。
- `project-proven` 修改 rest 时优先保持一个已证明的全局 lineage；若必须选择性改 rest，只改拓扑和 Unit 所有权明确隔离的语义，并把其他 TransformInfo/inverse-bind 行做字节级冻结。
- `project-proven` 若被移动的骨有不在修改范围内的后代，就无法同时保持该后代 global transform 精确不变。编译器应传播改动或直接拒绝。V21 明确检查“没有 non-finger descendant 挂在 finger 下”。

### 3.4 跨 Unit 一致性

- `project-proven` 同一可见关节语义若出现在多个相邻 Unit，其 origin、父层级和 basis 必须一致，或必须有专门的接口证明；混用不兼容的 rest lineage 会产生跨 Unit 拉伸。
- `project-proven` 选择性 prepared rest 只适合语义所有权封闭的 Unit；非目标骨行和所有相关后代必须冻结或显式传播。
- `case-specific` V16 使用 51-origin role-consistent 基线，V21 合同含 49 个 origin，其中只允许 30 个 finger origin 改写。这些计数不能推广到其他角色。

### 3.5 从源 rest 烘焙到目标 bind 的语义轴

`project-proven` 全局 affine 只能把整个人放进目标尺度/方向，不能消除源 VRChat T-pose 与 HD2/Ref bind pose 的逐骨 frame 差异。若顶点仍围绕源 rest pivot 排列，却由目标 inverse bind 驱动，肩臂、手指和腿脚会绕远端枢轴旋转。

先为每个源骨建立有符号的语义纵轴，再与目标父子关节链对应。Karin Nyako RE2310 中，源 Blender 骨段沿 local `+Y`，所选 Ref 的 HD2 `TransformInfo` 链沿 local `+X`，因此肩部/手指使用：

```text
C_y_to_x = [[ 0, 1, 0],
            [-1, 0, 0],
            [ 0, 0, 1]]

D_b = G_b * L_b * C_y_to_x * inverse(S_b)
p_bind = sum_b(weight_b * D_b * p_source_affine)
```

- `S_b`：经全局 affine 后的源 rest frame。
- `G_b`：Ref/game bind frame。
- `L_b`：只沿目标链轴的、由父子 pivot 距离推导的长度配准。
- `project-proven` 左右使用同一个 semantic basis；源骨架本身已镜像，不能再人为翻转一侧。
- `project-proven` 全局等比尺度保留在 `p_source_affine` 中，构造 rigid frame 时只去掉骨 frame scale，不能把角色尺度一并抵消。
- `project-proven` 非均匀 `L_b` 下，法线按每个 influence 的线性部分 inverse transpose 变换后再归一化。

肘、膝、踝等目标 raw bone roll 不一定左右镜像。对宽袖和连续肢体，优先使用父子轴 shortest-arc：

```text
u = normalize(source_child - source_parent)
v = normalize(target_child - target_parent)
Q = shortest_arc(u, v)
lambda = length(target_segment) / length(source_segment)
```

Hand 继承 LowerArm 的完整线性变换后在目标 wrist 重锚；Ball/Toe 可按同一原则继承 Foot。独立重建末端 frame 会在混合权重点产生腕/踝剪切。实现与证据见 [RE2310 v5 retarget](../../SOURCE_REFERENCES.md#local-only) 和 [几何审计](../../SOURCE_REFERENCES.md#local-only)。

## 4. 局部骨调色板与 authoring 合同

- `format-confirmed` O44/AQ 路线使用 `LegacyWeightNames=True`，顶点组名是每个对象的局部 `0_N`，不是全局骨数组索引。
- `format-confirmed` 同一语义骨在不同 Unit、LOD 或 section 中可能对应不同 local index；必须从各自 BoneInfo/RealIndices 显式解析 semantic -> local palette 映射。
- `project-proven` O44 authoring 网格没有持久化 Armature Modifier。预览时可临时添加语义顶点组和 modifier，但保存/导出前必须恢复 authoring 合同并证明临时对象已清理。
- `project-proven` 每个导出 mesh 的 object transform 应为 identity；所有正权重组必须可解析；未知组不得有正权重。
- `project-proven` float64 内归一不代表 float32/打包权重仍合格。应在 authoring、序列化后各检查一次。
- `project-proven` 权重污染审计要先按严格 `weight > 0.0` 枚举，再按空间、组件和权重大小判断是否错误；不能用一个显示阈值把极小但会随大角度旋转放大的权重藏掉。
- `project-proven` 没有正权重不表示骨可以删除。root、twist、toe、ball 等 helper 仍可能参与 TransformInfo 层级、mesh transform 或动画传播，必须按 donor Unit 保留和验证。
- `case-specific` New_SR24/O44 的上限是每顶点 4 influences；新 donor 必须重新读取格式，不要把 4 当所有 HD2 资源的无条件常量。

每个对象至少报告：

```text
vertex_count / triangle_count / topology digest
local palette semantic map
unweighted_vertices
vertices_over_influence_limit
max(abs(sum(weights)-1))
wrong-side positive weights
raw float32 weight digest + normalized semantic digest
```

## 5. 权重处理策略

### 5.1 先按连通片和角色分类

- `project-proven` 连续皮肤/衣料、分离硬附件、袖口小片、腰带、短裤、鞋与飘带不能使用同一迁移策略。
- `project-proven` 最近三角形重心插值适合把 donor 权重迁移到拓扑连续、语义对应的表面；它会在靠得很近但不相连的附件上采到错误表面。
- `project-proven` 材质 ID 不是可靠的组件选择器。New_SR24 的 130 个相关连通片使用同一 Atlas 材质，必须结合对象 role、component ID、拓扑、bounds 和权重语义。证据见 [V13 component analysis](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 小型刚性附件应优先整片继承可信基线或使用明确的父骨语义，不能在片内按 donor 距离逐点混合。

推荐先生成连通片清单：

```text
object / LOD / component_id
vertices / faces / bounds / material set
winner-bone histogram / positive-bone set
changed-row count / implicated pose-edge count
```

### 5.2 赢家骨跳变是高价值报警器

对顶点 `v` 定义赢家骨：

```text
winner(v) = argmax_b weight(v,b)
```

- `project-proven` 若一个刚性小片的相邻顶点在语义上相距很远的骨之间跳变，动画时通常会被撕开。
- `project-proven` V7 最近表面迁移使短裤边最大比率达到 `19.2066`，右袖小片达到 `15.8453`；根因正是相邻点采到不同 donor 表面。最终做法是整片回退可信权重，只在连续边界做窄域过渡。

赢家骨相同也不等于连续，因此还要比较完整权重行和姿态边长。

### 5.3 保持局部语义质量，而不是全行扩散

当局部只允许一组骨重新分配时，可定义语义池 `P`：

```text
mass_P(v) = sum_(b in P) w(v,b)
q(v,b)    = w(v,b) / mass_P(v)
w_new(v,b) = mass_P(v) * q_new(v,b),  b in P
```

池外权重逐位保持。该方法只适用于“权重确为根因且修改域已证明”的局部问题，不能用来掩盖错误参考、错误分件或错误 rest frame。

### 5.4 肩部跨对象边界：按游戏空间分件，不修型

RE2310 案例证明，肩部外观必须先解决 Torso/Arm 面归属和腋下位置，再讨论权重：

1. 按源权重语义识别 shoulder/UpperArm 候选面。
2. 把面心转换到游戏空间后，应用从精确 Ref 测得的 torso envelope；不能在 source space 使用 game-space 阈值。
3. 每个源面恰好分到一个角色；零归属、多归属和未解析面全部硬失败。
4. 分件边界复制顶点而不移动几何。从 face ownership 与 neutral 坐标冻结权威 seam 点/边集合；其拓扑必须与源/Ref 声明一致。Ref 证明是单闭环时才强制单闭环；开放或多组件衣物允许开链，但两侧必须覆盖声明集合、坐标匹配并共享同一完整权重行。
5. `BodyRope`、`Choker`、`Fuda`、`neck_ribbon` 等 Torso 附件保持自身角色，不套用 arm-yoke 规则。
6. 上背 neck-to-axilla 绳路若跨到大臂，优先判定腋下/近端上臂分件错误，而不是先改绳子权重。

`project-proven` 局部抬肩峰、外扩肩帽或缩放近端上臂会产生圆肩、健硕肩和断面。Karin Nyako v5 的肩部轮廓来自源几何、正确分件和 bind 转换，报告中的 `local_shape_edits` 为空。

`case-specific` 该案例的 Ref envelope 为 `abs(game_x) <= 0.2585172355 m`，每侧 18 个坐标匹配边界点、单闭环、共享权重误差 `0.0`。这些值只记录在 [RE2310 案例](case-studies/Karin_Nyako_RE2310.md)，新角色必须重测。

### 5.5 源多级肩链折叠到目标单肩骨

`project-proven (offline only)` 源骨架可能用 `Shoulder -> UpperArm -> LowerArm` 表达肩带/锁骨与实际上臂，而目标完整 carrier 只提供一个主要 shoulder 变形关节。先比较语义基数与最终 Unit/LOD palette；若 Ref 明确证明两组源权重都应由一个目标关节驱动，才做 many-to-one：

```text
source Shoulder weights + source UpperArm weights
  -> one target shoulder semantic
```

折叠后的 retarget correction 以真实 `UpperArm -> LowerArm` 运动段为锚，不以较短的 source Shoulder 显示段当肱骨：

```text
u = normalize(p_source_lowerarm - p_source_upperarm)
v = normalize(p_target_elbow - p_target_shoulder)

R0     = ortho(G_target_shoulder) * C_semantic * inverse(ortho(S_source_upperarm))
Qclose = shortest_arc(normalize(R0 * u), v)
A      = I + (lambda - 1) * u * transpose(u)
L      = Qclose * R0 * A
t      = p_target_shoulder - L * p_source_upperarm
```

- `R0` 保留已证明 carrier shoulder frame 的 roll；`Qclose` 只附加闭合真实链轴所需的最小 swing。
- 左右使用同一有符号 semantic basis，不能额外翻转一侧。
- source Shoulder 与 UpperArm 折叠后必须共享同一 correction；只让其中一组闭链会留下未测的肩部权重域。
- shoulder 与 elbow 可使用不同 roll policy；宽袖 elbow 常需 parent-child shortest-arc，不能把 shoulder 算法机械套到整条手臂。
- 法线在非均匀/逐 influence 线性变换下使用 inverse transpose 后归一化。

Umbrella v1 的肩 endpoint closure 已接近 0，仍因错误的源骨语义拆分、缺失 seam 门禁和 target-native Unit bind 混用而在游戏中断开。closure 是必要门禁，不是“良好肩膀”的充分条件。算法、反例和数值见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

### 5.6 自然 seam 权重优先，post edit 必须逐接口证明

`project-proven (runtime accepted)` 分件产生重复边界点后，先在预定 final lineage 中对两侧独立投影源权重，再比较完整语义权重行：

```text
W_a_natural = project(source weights, final lineage of role A)
W_b_natural = project(source weights, final lineage of role B)
natural_error = distance(W_a_natural, W_b_natural)
```

- `natural_error=0` 且骨集合、分布与 Ref/source 一致时，保留自然权重。不得再把整个 seam 锁成 clavicle/chest/root，也不得为“平滑”添加固定两圈或固定比例。
- 大的 pre-override error 应触发 palette、owner Unit 和 projection map 复查；不能只报告 post-override error。
- 几何使用的 rest-to-bind correction 与最终运行时权重必须共享同一骨语义。按 `D_shoulder` 烘焙几何后再改绑 clavicle，neutral 可能闭合，差分动作仍会断。
- 每个 post-partition seam edit 都要列出目标接口、修改点、骨语义、理由和 before/after。肩、腰、髋腿分别决策，禁止全局开关。
- seam gap 只能抓两侧分离；还要检查 arm/leg 内邻接 edge ratio，防止错误过渡环把裂缝转移到肢体中段。

SSF v3 的 171 点肩缝在 clavicle 覆写后离线相同，但游戏中肩线错误且上臂中段断裂；v4 恢复自然 `chest + side shoulder` 权重并使用 DS42 owner clone 后获用户验收。完整失败链和 case-specific 数值见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

### 5.7 镜像必须比较完整三维语义

- `project-proven` 左右源骨架通常已经镜像；相同 semantic basis 应直接作用两侧，不再添加手工 side sign。
- `project-proven` 只比较 `abs(x)`、bounds 或 radial distance 会掩盖前后方向相反。应比较完整三维质心、target-local transverse 符号和 world fore/aft。
- `project-proven` 左右几何可以存在有证据的真实非对称，但必须由 Ref、拓扑或组件清单证明，不能把一侧错转解释成“模型不对称”。

## 6. 手指专项

### 6.1 两条已证伪路线

- `project-proven` 把所有 finger 权重合并到 `hand` 会消除扭曲，但手指完全不动；V4e 被用户明确否决。
- `project-proven` 保留 finger 权重、却让序列化 pivot 离关节过渡区约 `114 mm`，会把手指拉成折线/长条；V7 被用户运行时截图否决。诊断见 [V7 runtime contract diagnostic](../../SOURCE_REFERENCES.md#local-only)。

### 6.2 从父子权重交集估计几何关节

对 child finger bone `c` 和其父骨 `p`，可用父子权重交集作为关节支持：

```text
bridge_weight(v) = min(w(v,p), w(v,c))
origin(c) = sum_v bridge_weight(v) * world_position(v)
            / sum_v bridge_weight(v)
```

- `project-proven` 该方法把 pivot 定位到实际父子混合环，而不是指尖、包围盒中心或 O44 另一角色的关节。
- `project-proven` 上式的 `world_position` 必须先转换到 prepared-rest/TransformInfo origin 使用的同一冻结坐标空间；若 authoring object matrix 非 identity，不能直接把 Blender world 坐标写进序列化 origin。
- `project-proven` 每根骨必须有非空 bridge support；左右、各手指、每一级 LOD 的输入摘要和 centroid 应一致或在声明容差内。
- `project-proven` 修改 origin 后只重算对应 finger inverse bind；所有非 finger 行保持精确基线。
- `case-specific` V21 为左右各 5 指、每指 3 节，共 30 根 finger；其合同与公式见 [V21 finger bridge rest contract](../../SOURCE_REFERENCES.md#local-only)。

### 6.3 手指权重必须局部化，但不能用一个距离阈值粗暴截断

- `project-proven` 袖口、饰件上的微量 finger 权重会在大旋转下造成极长尖刺；应按 connected component、finger-majority support 和最近 pivot 距离定位。
- `project-proven` 初始 V5 曾把 finger 权重扩散到约 2000 个袖口/饰件顶点；清理远端支持后保留了全部 30 根可动骨。
- `project-proven` finger 专项通过后仍要对微型袖口附件跑非对称 locomotion；附件应保留自身 elbow/hand 语义，不能吸收微量远端 finger 权重。
- `case-specific` “距最近 finger pivot 超过 8 cm 清零”和 R2 的 3 点 guard 都只是 Karin 的诊断结果；新模型应先看组件、权重大小和目标动画，不得直接照搬。

### 6.4 手指门禁必须真的转动 finger bones

标准姿势若不旋转 finger bones，无法发现手指 bind 错误。手指专项至少检查：

- 30/30（或本模型全部）finger bones 有正权重点且在确定性 curl 中产生位移。
- identity pose 最大误差接近浮点噪声；重复 pose 输出确定一致。
- 每个 parent-child transition ring 非空，centroid 与序列化 pivot 对齐。
- finger-majority 顶点局部化，无远端袖口/头发/饰件污染。
- 每根手指和整体的 edge ratio min/P99/max/mean；不能只看平均值。
- 上肢抬举与双手 curl 同时施加，覆盖耦合回归。
- 编译后从 Unit 反序列化 TransformInfo、BoneInfo 和 weights 再运行同一测试。

finger pivot 的历史公式见 [V21 finger bridge rest contract](../../SOURCE_REFERENCES.md#local-only)。

## 7. 肩、腹与分件接口排障

### 7.1 肩膀断开或变圆

按以下责任层顺序判断，前一层未闭合前不要进入下一层：

1. **参考身份**：精确 Ref Blend、compiled triplet 和同角色源是否锁定；错误参考产生的阈值和几何必须隔离。
2. **源轮廓**：source current mix 中的肩帽、肩胛和腋下是否完整；不要用局部肩峰抬升重新雕形。
3. **语义基数**：source Shoulder/UpperArm 与 target clavicle/shoulder 是一对一、many-to-one 还是不同 profile；映射是否由最终 carrier palette/Ref 证明。
4. **自然权重**：两侧在任何 seam edit 前的 final-lineage projection 是否已经一致；pre-override error 是否被保留而不是被覆写后的 0 掩盖。
5. **分件**：neutral 是否已有切口；权威 seam 点/边集合是否符合声明的闭环或开放拓扑、两侧覆盖完整、共点且同完整权重行；上背绳是否仍走 neck-to-axilla。
6. **肩 frame**：若折叠到单肩骨，是否以 UpperArm 实际运动段为锚，保留 carrier roll 并仅做最小 closure swing。
7. **语义轴**：source bone longitudinal axis 是否有符号地映到 target chain axis；不能只比较 bone matrix 的相对旋转。
8. **肘腕连续性**：LowerArm 是否使用 parent-child shortest-arc，Hand 是否继承 LowerArm linear 并在 wrist 重锚。
9. **序列化/姿态**：完整 Unit bind lineage 是否一致；差分姿态是否排除待证伪的替代骨；待机/敬礼/hand-to-head 中 signed axis、左右镜像、fore/aft、segment closure、固定对应 posed seam 和邻接 edge ratio 是否同时通过。

典型症状映射：

| 症状 | 首查合同 |
| --- | --- |
| 肩膀圆、宽、健硕 | 错误参考、局部修型、腋下面被划入 Arm |
| 肩根有断面 | Torso/Arm face ownership、权威 seam 拓扑、共享完整权重行 |
| 链闭合近 0 但肩仍断 | source/target 语义基数、未覆盖的 Shoulder/UpperArm 权重域、target-native Unit bind 混用 |
| 肩线错误且大臂中段出现折带 | 几何 correction 与最终权重骨是否同语义；是否有 blanket seam override 或固定两圈过渡 |
| 绳子从肩顶跨过大臂 | game-space envelope 用错空间，腋下切线被推向肘部 |
| 右臂前折、左臂后折 | source `+Y` 错映到 target `+Y`，未映到链轴 `+X` |
| 左右宽袖反向扭转 | 直接继承不镜像的 target elbow roll |
| 腕口剪切、掌心方向错 | Hand 使用独立 frame，未继承 LowerArm linear |

完整轮廓/分件主方法见 [Karin Nyako RE2310 案例](case-studies/Karin_Nyako_RE2310.md)；开放跨 profile seam 见 [DR03 案例](case-studies/Karin_DR03_CM10_EX00.md)；源肩骨折叠与完整 Unit 反例见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)；自然肩权重、错误过渡圈与 owner-clone 运行时正向证据见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

### 7.2 腹部“黑带/断层”先分三类

| 现象 | 首要诊断 | 不要先做 |
| --- | --- | --- |
| 真正看到背景，边界随骨分离 | Torso/Hip 对应边界点、语义权重和 differential pose seam | 随手补一圈新面 |
| 黑色实体环仍遮挡身体 | 查断开 liner/accessory 连通片、UV 落点和材质 | 把它误判成缺贴图或 AO |
| 没有开口但腹部被拉长 | 查几何 provenance、rest lineage、spine/chest 权重过渡 | 缩放腹部去“对齐原版体型” |

- `project-proven` V17 把一个 328 点/480 三角面的环形壳从 `spine2` 改到 `chest`；标准 176/176 姿势因两骨相对运动不足而假阳性，游戏中暴露巨大黑带。后续语义迁移必须专门驱动“旧骨 vs 新骨”的差分姿势。证据见 [V17 runtime rejection](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` V18 精确回滚权重仍有黑带，因为深色 liner 本身会在分层后暴露；不是 UV、法线或缺面。证据见 [V18 black-band root cause](../../SOURCE_REFERENCES.md#local-only)。
- `project-proven` 最终策略是把可见分界移到隐藏区域、排除错误 liner，并让 Torso/Hip 边界共享已由 donor 证明的同一语义权重。V19 的 asymmetric seam 从对照 `0.1373919814 m` 降为 0，随后用户确认断层消失。证据见 [V19 dynamic seam audit](../../SOURCE_REFERENCES.md#local-only)。
- `case-specific` V19 的共享语义是 `spine1=1.0`，涉及 Torso 151 点、Hip 172 点；其他角色必须从 donor 和自身拓扑重新推导。

### 7.3 头颈高度问题不等于全身缩放

- `project-proven` 先查 bridge 面属于 Helmet 还是 Torso、Torso 顶高、head anchor 和动画遮盖量。桥放在 Helmet 中会在换原版/其他 Mod 头盔时消失。
- `project-proven` 局部抬高 Helmet/颈口会制造长脖子；V8 已证伪。
- `project-proven` 只有在最终编译 Unit 上测接口高度和多头盔组合，才能区分“缺桥”“槽位归属错误”“bind 高度错误”。

### 7.4 鞋尖卷曲与肢体折叠

- `project-proven` 先检查是否既合并了 Toe 权重到 Foot，又把 Toe 几何额外旋转了一次。V4c 的鞋尖上卷来自这类双重处理；删除几何 override 即恢复源轮廓。
- `project-proven` 腿脚大面积折叠或交叉通常优先怀疑 rest-to-bind 未覆盖完整 `thigh -> knee -> foot -> ball` 链，而不是脚模型本身。每段使用有符号 parent-child 轴、shortest-arc 和轴向段长配准；Ball/Toe 继承 Foot linear 并重锚。
- `project-proven` 静态脚趾穿出鞋面时先核对源 Blend 保存中的 shape key mix。烘焙必须早于法线、分件和 bind retarget，并证明 topology/UV/weights/face ownership 不变。
- `case-specific` Karin Nyako v4 漏掉 `Foot_HighHeel=1.0`，涉及 1,886 顶点和最大 `0.0305432 m` 源位移，因运行时露脚趾被拒绝。

## 8. 变形指标与诊断逻辑

### 8.1 姿态边长比

对 neutral 边 `e=(i,j)`：

```text
r_e = length(p_i_pose - p_j_pose) / length(p_i_neutral - p_j_neutral)
```

- `project-proven` 同时记录 min、P01、median、P99、max。P99 能看整体退化，max 能抓只影响 1-3 个附件点的尖刺；二者不能互相替代。
- `project-proven` 对短于 epsilon 的 neutral 边可跳过除法，但必须报告 ignored count；posed 非有限点和 collapsed edges 必须单独硬失败。
- `project-proven` 分别统计全对象、changed-domain incident edges、每个连通片和手指区域。全对象统计会稀释局部灾难。
- 实现需要同时输出全局与声明域的分位数、absolute outlier 和非有限点；不要让全模型统计稀释局部灾难。

### 8.2 跨分件 seam

先在 neutral 建立固定对应集合 `C`，姿态后计算：

```text
d_seam_max = max_((a,b) in C) length(p_a_pose - p_b_pose)
```

同时记录 mean/P95/P99/max 和最坏 class。不要在 posed 状态重新做最近点匹配，否则会把已经分开的点配到别的表面而掩盖裂缝。

### 8.3 Differential pose

- `project-proven` 如果从骨 A 改绑到骨 B，必须构造让 A/B 产生足够相对运动的姿势；只做日常 A-Pose、蹲伏或举臂可能完全覆盖不到。
- `project-proven` 对肩臂要覆盖 shoulder、elbow、hand 的相对运动，并加入待机、敬礼与左右 hand-to-head；对腹部语义迁移要让 chest、spine2 或目标 spine 明显相对运动。
- `project-proven` pose coverage 也要设下限，防止脚本因骨名未解析、modifier 未绑定或姿势未真正应用而“全都等于 1”并误通过。

### 8.4 Signed axis、镜像与段闭合

对源父子链向量 `u_source` 经 retarget 线性部分 `D_linear` 后，与目标链向量 `u_target` 比较：

```text
axis_cosine = dot(normalize(D_linear * u_source), normalize(u_target))
```

- `project-proven` 必须保留符号，不能使用 `abs(axis_cosine)`；180 度翻转会被绝对值掩盖。
- `project-proven` 检查父段变换后的 source child pivot 与 target child pivot 的 endpoint closure。
- `project-proven` shoulder/elbow/hand 质心做完整三维镜像；同时检查 target-local transverse 符号与 world fore/aft，不能只比左右 `abs(x)`。
- `project-proven` radial RMS 对绕 pivot 的旋转不敏感。错转 90 度时半径可以完全不变，因此 radial RMS 只能作为尺寸诊断，不能替代 signed direction。
- `project-proven` 编译后必须从最终 Unit 的 TransformInfo、BoneInfo 和权重重新计算；用源 armature pose 或 builder 内存矩阵会重演错误假设。

### 8.5 Bounds 只能做烟雾检查

- `project-proven` bbox diagonal、中心位移和总高度能抓整体爆炸，但抓不到肩缝、手指反曲、短裤嵌入或整圈 liner 分层。
- `project-proven` 任何“整体 bounds 正常”的结论都必须配合 edge、seam、component 和近景渲染。

## 9. LOD、Slim/Stocky 与序列化覆盖

- `project-proven` 修改必须覆盖所有可见 LOD 和所有目标体型 Unit。只修 LOD0 会在镜头拉远或装备切换时复发。
- `project-proven` 如果参考 Mod 的 LOD0-LOD3 是复制 LOD，仍要逐级验证；不能因为顶点数相同就假定 BoneInfo、section 或 palette 相同。
- `project-proven` 同一 authoring 点可能在 Slim/Stocky、左右槽和四级 LOD 中序列化为多行。报告应同时给出“语义点数”和“实际写入行数”。
- `project-proven` 编译后检查每级 LOD 的 `RealIndices`、inverse-bind 行、正权重 local index、section 起点/数量和 mesh transform。authoring 通过不能替代 serialized postflight。
- `project-proven` 非目标 Unit、非目标 LOD 和 hidden/suppression payload 应与冻结基线逐字节一致。

## 10. 已证伪路线

| 路线 | 为什么看似合理 | 实际失败 | 证据等级 |
| --- | --- | --- | --- |
| 按 HD2 edit-bone roll/骨长逐段拟合 | 容易与原版骨架“对齐” | 源角色比例被拉坏，发丝和四肢方向异常 | `project-proven`，V1-V3 |
| 把 armature/world 点直接写入 vertices.co | Blender 预览位置正确 | runtime 再施加 MeshInfo transform，发生二次偏移 | `format-confirmed` + `project-proven` |
| 只替换 RawMesh、以为目标 bind 会保留 | 目标 ID 没变 | AQ 实际转移 donor whole Unit；bind provenance 错误 | `format-confirmed` |
| 逐骨复制 O44 origin | donor 已运行，看似最可信 | 相邻 origin delta 不连续，多权重点静态剪切 | `project-proven`，V5 |
| 只验 neutral identity | 数值容易达到极小残差 | 错 rest 与错 inverse bind 可互相抵消 | `project-proven`，V6/V10 |
| 只用候选自己的 preview rig | 预览内部自洽 | 不代表游戏外部驱动空间 | `project-proven`，V10/V11 |
| 全模型 donor 权重迁移 | donor 动画已运行 | 连续身体局部改善，手臂、鞋和附件大量回归 | `project-proven`，V12-V15 |
| 最近表面逐点混合所有组件 | 实现简单、表面距离小 | 短裤/袖饰跨 donor 表面，赢家骨跳变 | `project-proven`，V7 |
| 所有 finger 合并到 hand | 手指不再爆炸 | 手指完全不动 | `project-proven`，V4e |
| finger 权重正确就不测 pivot | 30 骨都有非零权重 | pivot 离过渡环过远，手指变长条 | `project-proven`，V7 |
| 只用固定四姿势 | 已覆盖举臂/蹲伏/移动 | 未驱动目标骨对的相对运动，整圈壳分层漏检 | `project-proven`，V17 |
| 看到腹部黑带就补面/改贴图 | 视觉上像空洞 | 可能是深色 liner 或跨槽权重语义不一致 | `project-proven`，V17-V19 |
| 局部抬头/抬颈解决头盔间隙 | 接口高度数字变正常 | 角色出现超长脖子 | `project-proven`，V8 |
| 只改一个 LOD/一个体型 | 近景立刻改善 | 远景或 Slim/Stocky 切换回归 | `project-proven` |
| 用目录昵称/记忆选择肩部参考 | 名称看起来熟悉 | 在错误肩形上持续迭代，所有派生阈值失效 | `project-proven`，RE2310 错误参考阶段 |
| 局部抬肩峰或外扩肩帽 | 静态图上可见“肩峰” | 圆肩、健硕肩、断面，破坏源角色体型 | `project-proven`，RE2310 |
| 在 source space 使用 game-space envelope | 阈值数值本身来自 Ref | 腋下边界被推到近端上臂/肘方向，绳路跨大臂 | `project-proven`，RE2310 |
| `R_target * transpose(R_source)` 直接对齐骨矩阵 | 数学上像 rest delta | source `+Y` 映到 target `+Y` 而非链轴 `+X`，左右臂前后反折 | `project-proven`，RE2310 RefBind v2 |
| 直接继承完整 target elbow roll | target TransformInfo 最权威 | 左右 roll 不镜像，宽袖反向扭转 | `project-proven`，RE2310 |
| endpoint closure 接近 0 就宣布肩部通过 | 被测父子端点闭合 | 未覆盖源骨语义基数、seam 驱动与完整 Unit bind，游戏仍可断开 | `project-proven`，Umbrella v1 |
| 同一 RawMesh 分别编入不同 target-native Unit | 几何、顶点数和 bounds 相同 | 不同 TransformInfo/BoneInfo 造成肩、胯、全身和头盔错位 | `project-proven`，Umbrella v1 |
| Hand 使用独立 fixed frame | 掌骨本身能对齐 | LowerArm/Hand 混合区剪切，腕缝和掌心朝向错误 | `project-proven`，RE2310 |
| 只验 pivot radial RMS | 手/指半径与 Ref 接近 | 绕 pivot 错转 90 度仍可通过，漏掉有符号方向错误 | `project-proven`，RE2310 RefBind v2 |

## 11. 推荐执行流程

### 阶段 A：冻结证据

1. 锁定用户指定参考的精确目录、authoring Blend、编译 triplet、原始角色身份和 SHA-256；隔离所有旧参考派生物。
2. 证明 donor authoring 与已运行成品的顶点/三角、palette 和 Unit 字段对应。
3. 枚举所有目标 Unit、LOD、Slim/Stocky、section、MeshInfo transform 和 BoneInfo；若使用完整 carrier clone，同时冻结每角色 carrier 与 clone target 集合。
4. 建立全局语义名到每个对象 local `0_N` 的显式映射。

### 阶段 B：建立 authoring 基线

1. 冻结保存中的全部非零 shape key 值，预计算 current mix，再用 shape-key-only `apply_mix` 烘焙；证明 topology/UV/weights/face ownership 不变。
2. 先应用单一、已证明的全局坐标变换，再按源 rest -> 目标 bind 的语义轴逐 influence 烘焙；object matrix 归一为 identity。
3. 保留 topology/UV/material provenance；建立连通片 inventory。
4. 验证无未加权点、影响数上限、归一化、无错侧权重。
5. 冻结 geometry、weights、scene metadata 的 float32 digest。

### 阶段 C：设计最小变更

1. 从最近的已接受基线分叉，不在 rejected 候选上叠加未知变化。
2. 声明允许改变的对象、LOD、component、顶点、骨和权重池。
3. 声明必须逐位不变的所有其他字段。
4. 连续表面使用拓扑/重心迁移与窄域 harmonic 过渡；附件使用整片语义保护。
5. 若改 rest，列出所有受影响 TransformInfo、local transforms、descendants 和每 LOD inverse-bind 行。

### 阶段 D：authoring 与外部姿态门禁

1. 验 geometry/topology/UV/material/object property 冻结。
2. 验 changed set 恰好等于声明域，域外权重 bit-exact。
3. 跑 neutral、arm-up、crouch、asymmetric locomotion。
4. 再跑针对问题的 differential pose、seam、signed chain-axis、左右 full-3D mirror、world fore/aft 和 segment closure。
5. 用 runtime-proven donor rig，不用候选自身 rig 作为唯一证据。
6. 生成正面、侧面、三分之四和问题区域近景。

### 阶段 E：编译后二进制门禁

1. whole-unit 编译所有可见 Unit；采用 carrier clone 时每逻辑角色只编译一次，再克隆完整序列化 Unit。
2. 独立回读最终 Unit，不调用同一 builder 的内存对象作为证据。
3. 逐 Unit/LOD 验 TransformInfo、local hierarchy、MeshInfo、BoneInfo、inverse bind、palette 与权重；同角色 clone payload 的唯一哈希数必须为 1。
4. 在反序列化合同上重跑 neutral、external pose、seam、finger/component 专项。
5. 做两次隔离、串行编译并比较 triplet；AQ archive 操作不要并行竞争共享临时文件。

### 阶段 F：运行时

1. `compiled_and_offline_verified` 仍标记 `runtime_validation_pending`。
2. 经明确授权后，测试军械库/任务内、Slim/Stocky、近远 LOD、原版和自定义头盔、待机/奔跑/蹲伏/举臂/瞄准/手指动作。
3. 用户截图可以推翻所有离线门禁；被推翻候选移到 `quarantined_do_not_use`，保留报告供根因比较。

## 12. 验证清单

### 坐标与几何

- [ ] 写入点已明确为 donor mesh-local，不是 world/armature-space。
- [ ] object transform 为 identity；父级、modifier、临时预览对象无残留。
- [ ] 每个顶点可追溯到源保存的 current shape mix、声明的全局变换和 rest-to-bind，或声明的局部几何变更。
- [ ] shape-key mix 在分件/法线/retarget 前烘焙；无残留 key，且 topology/UV/weights/face ownership 未改变。
- [ ] 不存在未授权的逐骨/区域缩放、头颈偏移或二次 Toe 旋转。
- [ ] topology、UV、材质与非目标对象摘要符合冻结合同。

### Palette、权重与组件

- [ ] 每个 Unit/LOD/section 独立解析 local palette；没有全局 index 猜测。
- [ ] 未加权点为 0；正权重组全部可解析。
- [ ] 每点 influences 不超过当前 donor 合同；float32 权重和在容差内。
- [ ] 无错侧骨；finger 等高风险权重没有扩散到远端组件。
- [ ] 连续身体和离散附件分别处理；每个修改组件有 manifest。
- [ ] 变更域外 raw weight 行 bit-exact；池外质量与总 pool mass 守恒。
- [ ] 所有 LOD、Slim/Stocky 和重复对象均覆盖。

### Rest 与 inverse bind

- [ ] global TransformMatrix、local `Transforms[].pos` 和父层级相互一致。
- [ ] 每个受影响 LOD 的 inverse bind 都按自己的 mesh transform 重算。
- [ ] neutral identity 逐骨/逐 Unit/逐 LOD通过。
- [ ] 同语义跨 Unit origin/basis 一致，或有明确隔离与接口证明。
- [ ] 移动骨的 descendants 已传播或被硬门拒绝。
- [ ] source longitudinal axis 到 target chain axis 的 signed cosine 正确，未使用绝对值掩盖翻转。
- [ ] source/target 肩部语义骨基数已声明；若 many-to-one，所有被折叠源权重使用同一 target semantic 与 correction。
- [ ] 每段 source child pivot 经父段变换后闭合到 target child pivot。
- [ ] LowerArm/Hand 与 Foot/Ball 等混合接口的线性变换和共享 pivot 连续。
- [ ] donor/runtime-proven 外部驱动测试通过，而非只用候选自身 rig。

### 姿态与局部质量

- [ ] 标准四姿势实际产生了规定的 pose coverage。
- [ ] 针对改绑骨对执行 differential pose。
- [ ] edge ratio 同时报 min/P01/P99/max、collapsed 和 nonfinite。
- [ ] changed-domain、每连通片、Torso/Arm 权威 seam 集合、腹 seam、手指分别统计；闭环/开放拓扑与源/Ref 声明一致。
- [ ] 每条 seam 在 post edit 前的自然 final-lineage 权重误差已报告；所有 post edit 有逐接口理由，未用 after-override 相同掩盖 before-override 失败。
- [ ] 固定 neutral boundary class 后计算 posed seam，没有 posed 最近点重配。
- [ ] 差分姿态声明 moving/excluded bones，并报告实际 pose coverage；不会把错误替代骨与正确骨一起移动后产生假阳性。
- [ ] 肩部强权重质心的正向链轴、左右 full-3D mirror、target-local transverse 和 world fore/aft 通过。
- [ ] 上背 neck-to-axilla 装饰走向未跨到大臂；待机、敬礼、双侧 hand-to-head 均检查。
- [ ] 手指骨全部运动，transition ring 非空，pivot 对齐，curl 可重复。
- [ ] 正/背/侧/三分之四与局部近景均人工检查。

### 编译与状态

- [ ] 最终编译 Unit 独立回读后重复上述 bind/pose/LOD 检查。
- [ ] carrier clone 路线记录每角色 compile count、carrier ID/哈希、clone targets、payload identity、TransformInfo 与核心 bone-bind 前后签名。
- [ ] 非目标 Unit 和 suppression payload 与冻结基线一致。
- [ ] 两次隔离串行构建结果确定一致。
- [ ] 报告明确区分 authoring、compiled/offline 和 runtime 状态。
- [ ] 未做游戏验证时绝不写 `runtime_validated`。
- [ ] 用户手动验收只提升明确绑定的候选与范围；未观察的部署过程、未提供的姿态矩阵和未执行的自动化测试仍列为限制。

## 13. 案例阈值，只作起点

以下全部为 `case-specific`，新项目应依据单位尺度、拓扑密度、donor 对照和目标动画重新校准：

| 指标 | 案例使用值/结果 | 说明 |
| --- | --- | --- |
| 每点最大 influences | 4 | O44/New_SR24 donor 合同 |
| 通用权重和误差门 | `1e-4` | 标准 pose validator；局部修改常收紧到 `1e-6` |
| neutral bind 误差 | 约 `2e-6 m` 级硬门 | 只证明内部自洽 |
| 标准 edge P01/P99 | `>=0.35 / <=3.0` | 宽门，只做全身烟雾检查 |
| V21 finger edge | absolute `0.25..2.25`，P99 `<=1.5`，mean `0.95..1.05` | 专项 combined curl |
| V21 R2 finger P99 | `1.438009 / 1.277000` | 离线 cross-pose |
| RE2310 shoulder axis | 最大 `25 deg`；target-local X `[0.10,0.25] m` | RefBindAxis v5，仅该角色 |
| RE2310 arm mirror | shoulder/elbow/hand `<=0.015 m` | full-3D mirror，不是单轴绝对值 |
| RE2310 shoulder fore/aft | 左右同号且差 `<=0.015 m` | 防止一臂前折、一臂后折 |
| RE2310 arm closure | `<=0.002 m` | shoulder/elbow parent-child endpoint |
| RE2310 Torso/Arm boundary | 每侧 18 点、单闭环、共享权重误差 `0.0` | Ref game-space envelope 的案例结果 |
| RE2310 实测 arm mirror | shoulder `5.8854e-5 m`；elbow `0.0015135 m`；hand `7.7340e-5 m` | v5 authoring audit，非运行时接受 |
| Umbrella v2 shoulder closure | 左 `2.98e-8 m`；右 `8.94e-8 m` | UpperArm 锚、DS42 roll + minimal swing；仅离线 |
| Umbrella v2 neutral shoulder seam | 左 209、右 212 对；位置/权重误差 `0` | 开放多组件边界，尚缺 serialized differential-pose/runtime 验证 |

阈值制定原则是“相对已运行 donor 和已认可基线更好，并能拒绝已知失败样本”，不是追求所有值都接近 1。衣料、关节和夸张动画允许真实形变；真正危险的是非有限、塌边、局部尖刺、跨组件撕裂和错误语义。

## 14. 证据索引

| 主题 | 相对路径 | 结论 |
| --- | --- | --- |
| donor 完整 bind | [o44-donor-full-bind-contract.json](../../SOURCE_REFERENCES.md#local-only) | 外部 preview rig 与 donor Unit bind 基线 |
| C4/D7 骨架比较 | [c4-d7-rig-comparison-r1.json](../../SOURCE_REFERENCES.md#local-only) | 核心骨段同源，不需拟合原版体型 |
| rest/正权重审计 | [v16-rest-bind-contract-audit-r1.md](../../SOURCE_REFERENCES.md#local-only) | origin、helper、49 正权重骨与 top-4 状态 |
| 全模型迁移失败 | [v13-selective-component-weighting-analysis-r1.md](../../SOURCE_REFERENCES.md#local-only) | 必须按连通片混合策略 |
| 源几何 provenance | [karin-v10-source-geometry-preservation-r4.json](../../SOURCE_REFERENCES.md#local-only) | 几何与 bind 必须独立证明 |
| neutral 自洽边界 | [v10-final-unit-proportion-rest-audit-r2.json](../../SOURCE_REFERENCES.md#local-only) | 极小 neutral 残差仍非运行时充分条件 |
| 外部合同失败 | [v11 compiled external gate](../../SOURCE_REFERENCES.md#local-only) | 自身 preview rig 的假阳性 |
| 腹部语义失败 | [v17-runtime-rejection-and-v18-contract-r1.json](../../SOURCE_REFERENCES.md#local-only) | differential pose 与编译后组件审计必要 |
| 腹部最终 seam | [v19-authoring-delta-and-dynamic-seam-r2.json](../../SOURCE_REFERENCES.md#local-only) | 共享 spine1 bridge 消除动态裂缝 |
| finger pivot 公式 | [V21 finger rest contract](../../SOURCE_REFERENCES.md#local-only) | 父子权重交集质心 |
| RE2310 肩部完整方法 | [Karin Nyako RE2310 案例](case-studies/Karin_Nyako_RE2310.md) | 精确参考、game-space 分件、语义轴、肘腕连续性与拒绝链 |
| RE2310 retarget 实现 | [nyako_ref_bind_axis_retarget_v5.py](../../SOURCE_REFERENCES.md#local-only) | `+Y -> +X`、shortest-arc、末端继承与法线 inverse transpose |
| RE2310 authoring 审计 | [nyako-re2310-ref-bind-axis-v5.json](../../SOURCE_REFERENCES.md#local-only) | signed axis、mirror、fore/aft、closure、shape key 与槽位 |
| RE2310 compiled 审计 | [compiled-v5-final-a.json](../../SOURCE_REFERENCES.md#local-only) | 最终 Unit 回读后的同类门禁 |
| Umbrella v1/v2 失败链 | [Karin Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md) | endpoint closure 假充分、源双肩骨折叠、完整 Unit clone 与开放 seam 剩余风险 |

肩部版本历史、哈希和拒绝状态以 [Karin Nyako RE2310 SOP](../../SOURCE_REFERENCES.md#local-only) 为准。
