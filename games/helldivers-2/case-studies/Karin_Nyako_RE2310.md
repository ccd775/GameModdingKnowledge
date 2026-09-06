# Karin Nyako RE2310 案例：RefBindAxis 肩部、肢体与装备槽合同

> 项目：`HD2/Karin_Nyako_RE2310`
>
> 目标：使用 Nyako 完整替换 RE2310 套装，并保持同角色参考中的少女体型、肩胛轮廓、腋下位置和装饰走向。
>
> 权威状态：以 [项目 SOP](../../../SOURCE_REFERENCES.md#local-only) 为准。RefBindAxis v5 是当前不可变几何/绑定基线；活动发布已演进到 ArmorLUT Splat v7。v6 已 `runtime_rejected`，v7 已 `packaged_and_offline_verified`，截至 2026-08-08 仍为 `runtime_validation_pending`。

## 参考身份先于任何肩部算法

本案例只允许以下参考影响肩部几何、bind、权重、分件或门禁：

- [用户指定 Ref](../../../SOURCE_REFERENCES.md#local-only) 中的 `DS42 260501.blend` 与配套 `9ba626afa44a3aa3.patch_1*`。
- 该 Ref 的同角色源模型 `Shared/Models/Optimized/Karin_Riptide/`，仅用于证明同角色静止骨架和形体关系。
- Nyako 权威源 Blend 与其旁边 VRM；VRM 只提供动态骨骼/物理参考，不替代 HD2 bind 合同。

早期把目录昵称和错误工程当成参考，导致在错误肩形上反复调节。可复用结论是：参考必须锁定到精确路径、authoring Blend、编译 triplet、源角色身份和 SHA-256；“看起来像那个案例”或任务记忆不能作为 reference identity。其他项目、拒绝候选和历史探针不得向活动门禁回流。

## 肩部问题要拆成四层

### 1. 源轮廓

正确肩部凸起应来自同角色源几何中的肩帽、肩胛、腋下和近端上臂轮廓。局部抬肩峰、外扩肩帽或只缩上臂，会把少女体型做成圆肩、宽肩或健硕肩，并可能在分件边缘制造断面。

本案例最终没有局部肩部雕形；`local_shape_edits` 为空。先恢复正确参考、正确分件和正确 bind 后，源轮廓自然成立。

### 2. Torso/Arm 分件与腋下

分件顺序是：

1. 先按源权重语义找出肩/上臂候选面。
2. 把面心转换到游戏空间。
3. 在游戏空间应用由 Ref 测得的 torso envelope。
4. 复制边界顶点，不移动边界顶点；每个源面恰好归属一个角色。
5. 两侧边界必须闭环、坐标匹配、权重一致。

阈值属于哪个空间，就必须在哪个空间判断。在 source space 直接套 game-space 阈值会把腋下切线推向肘部。

上背从颈部绕到腋下的绳子是高价值示踪线：若它绕过大臂或从肩顶横穿，通常不是绳子本身的权重问题，而是腋下/近端上臂面被错误归入 Arm。`BodyRope`、`Choker`、`Fuda` 和 `neck_ribbon` 在本案例保持 Torso 所有权，不能套用 arm-yoke override。

### 3. Source rest 到 HD2 bind 的语义轴

只做全局 affine 会保留 VRChat T-pose 的局部顶点布局，却让它由 HD2/Ref 的另一套 bind pivot 驱动。必须在分件/导出前按每个 influence 把源 rest 几何烘焙到目标 bind。

本案例的 Blender/VRM 骨段纵轴是 local `+Y`，所选 Ref 的 HD2 `TransformInfo` 链轴是 local `+X`。肩部与手指使用显式语义基：

```text
C_y_to_x = [[ 0, 1, 0],
            [-1, 0, 0],
            [ 0, 0, 1]]

D_b = G_b * L_b * C_y_to_x * inverse(S_b)
p_bind = sum_b(weight_b * D_b * p_source_affine)
```

其中 `S_b` 是经全局 affine 后的源 rest frame，`G_b` 是 Ref/game bind frame，`L_b` 只沿语义链轴做经证明的长度配准。几何中的全局等比尺度必须保留，不能在构造骨 delta 时意外抵消。

左右两侧使用同一个 `C_y_to_x`；源骨架本身已经镜像，额外给一侧翻符号会再次破坏镜像。

直接使用 `R_target * transpose(R_source)` 是本案例已证伪的做法：它把 source `+Y` 映到 target `+Y`，不是 target 链轴 `+X`。目标左右 local `+Y` 在世界前后方向相反，因此运行时表现为右臂向前反折、左臂向后反折。

### 4. 肘部 roll 与腕部连续性

Ref 左右肘的完整 bone roll 并非严格镜像。宽袖让这种差异非常醒目，因此肘部不用 raw target roll，而使用父子关节轴的 shortest-arc swing，并沿源关节轴配准段长：

```text
u = normalize(source_child - source_parent)
v = normalize(target_child - target_parent)
Q = shortest_arc(u, v)
lambda = target_segment_length / source_segment_length
```

Hand 继承 LowerArm 的完整线性变换，再在目标 wrist 重新锚定。若 Hand 另建固定 frame，LowerArm/Hand 混合点会产生腕缝、剪切和手掌朝向差异。手指可以继续使用已证明的固定语义基转换。

存在非均匀轴向缩放时，法线必须对每个 influence 使用线性部分的 inverse transpose，再归一化；不能按位置矩阵直接变换法线。

## 为什么旧离线指标会假通过

到骨 pivot 的 radial RMS 只回答“点离枢轴多远”。绕同一 pivot 错转 90 度时半径不变，因此该指标可以全绿，而手臂仍向前/向后反折。它只能保留为体积/尺度诊断，不能作为方向验收。

肩部与上肢至少需要以下独立门禁：

- signed target-local chain-axis cosine，禁止取绝对值。
- 强权重质心位于目标纵轴正向和经参考校准的轴向区间。
- 左右 shoulder/elbow/hand 的完整三维镜像误差。
- target-local transverse 分量符号与 Ref 一致。
- 左右肩 world fore/aft 偏移同号且差值受限。
- shoulder-to-elbow、elbow-to-wrist endpoint closure。
- LowerArm/Hand 线性矩阵连续性与共享 wrist pivot 误差。
- Torso/Arm 固定 neutral 边界的闭环、坐标、权重与 posed seam。
- 待机、敬礼、左右 hand-to-head、arm-up 和 asymmetric locomotion。
- authoring 与编译后 AQ 回读各执行一次；不能复用 builder 内存对象充当独立证据。

## Case-Specific 数值

以下全部只属于 Karin Nyako RE2310 v5，不能复制为其他角色的默认常量：

| 指标 | v5 合同/结果 |
| --- | --- |
| Ref torso envelope | `abs(game_x) <= 0.2585172355 m` |
| Torso/Arm 边界 | 每侧 18 个坐标匹配点、单闭环、共享权重误差 `0.0` |
| shoulder axial scale | 左 `0.8718831891`；右 `0.8718787835` |
| shoulder 轴向角门 | `<=25 deg` |
| shoulder target-local X | `[0.10, 0.25] m` |
| shoulder/elbow/hand 镜像门 | `<=0.015 m` |
| world fore/aft 左右差 | `<=0.015 m` 且同号 |
| arm segment closure | `<=0.002 m` |
| 实测镜像误差 | shoulder `5.8854e-5 m`；elbow `0.0015135 m`；hand `7.7340e-5 m` |
| 实测 shoulder closure | 左 `8.6254e-7 m`；右 `0.0010266 m` |

## 其他被本案例证明的合同

### 保存中的 Shape Key 必须先烘焙

保存中的非零 shape key 是权威源外观的一部分。先冻结 `对象 -> key -> value`，预计算 current mix，再执行只作用于 shape key 的 `apply_mix`；烘焙必须早于法线、面遍历、角色分件和 bind retarget。不要直接应用 evaluated dependency graph 的完整网格，否则活动 Armature modifier 可能被二次应用。

v4 漏掉 `Body_base/Foot_HighHeel=1.0`，运行时脚趾穿出鞋子。该键影响 1,886 个顶点，最大源位移 `0.0305432 m`。v5 同时烘焙源 Blend 中六个非零保存状态，并证明拓扑、UV、权重、材质索引、面归属不变，坐标误差 `<=1e-7 m`，候选不再保留 shape key。

```text
Body_base  Breasts_small=0.75
Body_base  Foot_HighHeel=1.0
BodyRope   Breasts_small=0.75
Fuda       Breasts_small=0.75
Hair       Ahoge_big=1.0
Hair       Hair_tail_volume_up=1.0
```

### 腿脚也必须做完整 bind 转换

只转换上肢而让腿脚保留全局 affine，会让 thigh/knee/foot/ball 相对游戏 pivot 错位，走路和踏步时双脚交叉。v5 对 thigh、knee、foot 使用 parent-child shortest-arc swing + 轴向配准；ball 继承 foot 完整线性变换并在目标 pivot 重锚。腿链还需 signed axis、左右 palette、distal mirror、段闭合和 foot/ball 连续性门禁。

`case-specific` 轴向比例为 thigh 左/右 `0.895709061 / 0.895708435`、knee `0.847313560 / 0.847313697`、foot `0.912553382 / 0.912551077`；Ball 继承 Foot linear，不使用独立比例。这些数值只用于复核该冻结候选，不能移植。

### 隐藏原生盔甲要缩小可渲染几何

把原生盔甲材质换成透明/玻璃不等于隐藏。v3 的玻璃材质在游戏中显示为蓝色透明塑料叠层。v5 保留 Unit 元数据、骨架、LOD/MeshInfo、索引、section、原材质和 culling 合同，只把 12 个 suppression Unit 的正 LOD position stream 收缩到确定性微米占位；旧玻璃 material/texture 不进入实际资源闭包。

本案例使用 `1e-6 m` 占位，硬门为每轴 `<=2e-5 m`，覆盖 12 Unit 的 48 个 render LOD，并保留/单独验证 14 个 culling mesh。这些数量和阈值是 `case-specific`；可复用原则是修改可渲染几何，而不是依赖透明材质，并在最终 Unit 上回读每个正 LOD 与 culling body。

### 头部必须归实际消费者槽位

v3 把完整 Nyako 头部装入 armor/body role，同时把 RE2310 Helmet Unit 当 suppression，结果是穿盔甲时能看到头、独立头盔槽为空。v5 将头、脸、发、耳和头饰只放入可见 Helmet role，折叠到 `head` palette；Torso 不再重复持有头部。所有源面必须恰好由一个消费者角色拥有，可见集合与 suppression 集合必须互斥。该案例 Helmet target Unit 为 `12628959026638052995`，只属于该目标版本。

### 删除衣物必须按精确组件 provenance

“删除一件衣物”不授权删除邻近对象、同材质连通片或名字相似的附件。先冻结源对象/组件/面清单，再建立显式 delete set 与 preserve set；builder 报告每个源面的唯一归属和删除原因。

本案例的 `Top`、`Panty` 已从权威源 Blend 删除，因此候选中不得残留对应顶点；`Fuda` 必须保留，并随保存的 `Breasts_small=0.75` 一起烘焙。早期把删除范围扩大到 `Fuda`，以及角色分件遗漏头发、腹部或单侧腿，均说明不能以材质、空间邻近或模糊名称替代 source-face inventory。

### VRM 动态骨只提供物理参考

源 VRM 的动态骨、碰撞体和参数可用于建立 custom-bone/physics provenance，但不会因为模型已蒙皮就自动成为 HD2 运行时物理。若当前编译链没有明确写入并回读相应物理资源，只能标记为参考或 `known_limit`，不能宣称已完成动态效果。

## 拒绝链

| 阶段 | 运行时/审计结果 | 被证明的根因 |
| --- | --- | --- |
| 错误参考阶段 | 肩部反复变圆、变宽或出现断面 | reference identity 未锁定，在错误轮廓上迭代 |
| RefClean v1 | 手和手指绕远端枢轴拉成长条 | 只有全局 affine，没有 source-rest -> game-bind 烘焙 |
| RefBind v2 | 待机时右臂前折、左臂后折 | source `+Y` 错映到 target `+Y`，未映到链轴 `+X` |
| RefBindAxis v3 | 上肢方向改善；走路双脚重叠、原甲透明叠加、头盔槽为空 | 腿链未 retarget；玻璃材质抑制；头部角色归属错误 |
| RefBindAxis v4 | 上述三项离线修复，但脚趾穿鞋 | 未烘焙保存的 `Foot_HighHeel` shape key |
| RefBindAxis v5 | 全部当前离线门禁与确定性发布通过 | 尚未完成用户运行时验证，不能提升状态 |

## 证据入口

- [完整 SOP](../../../SOURCE_REFERENCES.md#local-only)
- [v5 retarget 实现](../../../SOURCE_REFERENCES.md#local-only)
- [v5 builder 与 shape-key bake](../../../SOURCE_REFERENCES.md#local-only)
- [v5 authoring 几何审计](../../../SOURCE_REFERENCES.md#local-only)
- [v5 编译后二进制审计](../../../SOURCE_REFERENCES.md#local-only)
- [v5 独立 AQ 验证](../../../SOURCE_REFERENCES.md#local-only)
- [v5 包复现报告](../../../SOURCE_REFERENCES.md#local-only)
- [v4 形态键拒绝记录](../../../SOURCE_REFERENCES.md#local-only)

完整哈希、运行时截图哈希、恢复/隔离路径和发布命令以项目 SOP 为准。
