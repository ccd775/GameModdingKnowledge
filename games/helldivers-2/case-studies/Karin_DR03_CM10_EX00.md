# Karin DR03 CM-10/EX-00 案例：私有材质闭包与跨体型肩缝

> 项目：`HD2/DR03_Replace_Cm10EX00`
>
> 目标：使用 Karin DR03 Atlas 模型替换 CM-10 与 EX-00，并复用实际共享的游戏 Unit。
>
> 权威状态：以 [项目 SOP](../../../SOURCE_REFERENCES.md#local-only) 为准。v1 因运行时纯灰被拒绝；v2 已由运行时截图证明颜色恢复，但因动作中肩缝断开被拒绝；v3 肩缝候选已 `packaged_and_offline_verified`，后续因活动发布继续演进而转为 `superseded`，其肩部证据仍有效。当前活动发布状态必须读取项目 SOP，不能由本案例页推断。本案例未自动化测试 v3 游戏运行时。

## 先按 FileID 建消费者图，不按套装名称重复制作

CM-10、EX-00 和其他套装可复用同一组底层 Unit。替换是否需要“处理两次”应由目标 FileID 去重后的消费者图决定，而不是由军械库显示名决定：

1. 从装备定义追到每个 Slim/Stocky、Torso/Arm/Hips/Leg/Helmet Unit。
2. 按完整 FileID 去重，并记录每个 Unit 的全部消费者。
3. 一个 Unit override 会对所有消费者全局生效，不能按当前 armor kit 条件化。
4. 报告主要目标和连带影响；不要为了“只影响当前套装”复制一个已经共享的目标，也不要遗漏共享消费者的复测。

本案例的实际 blast radius 还包括共享 hips undergarment 的其他 armor kit。完整目标图见 [consumer scope 报告](../../../SOURCE_REFERENCES.md#local-only)。

## v1 纯灰：几何加载成功不代表材质闭包属于当前 Mod

v1 在游戏中模型、轮廓和蒙皮均已加载，但全身呈纯灰/高金属感。根因不是 atlas 像素、UV 或法线，而是更高优先级已安装 Mod 使用了相同的本地资源 ID：

- 1 个 child Material FileID 冲突。
- 11 个 TextureMap FileID 冲突。
- 当前 Unit 仍引用这些 ID，因此运行时解析到另一 Mod 的 Armor LUT 材质闭包。

这证明资源解析的责任链必须扩展到当前安装环境：

```text
target Unit
-> referenced child Material full 64-bit FileID
-> every referenced TextureMap full 64-bit FileID
-> highest-priority installed provider for each ID
```

只扫描候选自身、只看 Unit ID、只检查贴图文件存在，都会漏掉这种覆盖。更高优先级 patch 可以劫持整个材质闭包，即使可见 Unit 本身确实来自当前 Mod。

v2 使用稳定 Murmur64A 私有命名空间重写 child Material 和 11 个 TextureMap ID，保留 stock parent、binding、顺序和 payload。相对 v1，Unit GPU/stream、几何、权重和贴图像素均不变；用户随后确认颜色恢复。这是“先证明 ID 解析冲突，再做最小 namespace delta”的运行时接受证据。

## v2 肩缝：中立姿态共点仍可在动作中分离

用户截图显示左大臂肩口在动作中断开。只读诊断排除了缺面和局部肩型问题：Torso/Arm 的中立边界坐标吻合，但每一对重复边界顶点的完整权重行都不同。

- 左侧 73 个匹配顶点对、71 个唯一坐标。
- 右侧 170 个匹配顶点对、168 个唯一坐标。
- 最大权重误差为 `1.0`。
- Torso 侧被折叠到 `chest`，Arm 侧仍随 `l_shoulder/r_shoulder`。
- 确定性 45 度差分压力姿态最大分离 `0.147710803 m`。

中立位置只证明 `p_torso(0) == p_arm(0)`，不能证明两侧由同一变换驱动。固定中立对应集合后，应在让两组 winner bones 产生最大相对运动的姿态中计算 posed seam；不能在 posed 状态重新做最近点匹配。

诊断证据见 [v2 肩缝报告](../../../SOURCE_REFERENCES.md#local-only)。

## 从 RE2310/DS42 迁移方法，不迁移骨名

RE2310 仿照 DS42 的可迁移方法是：

1. 保持正确的面归属和源轮廓。
2. 复制边界坐标，不靠局部雕形遮缝。
3. 让 Torso/Arm 两侧的权重行一致。
4. 在部件内部以有限拓扑环平滑恢复原权重。

不可直接迁移的是“肩缝必须使用 shoulder 骨”。RE2310 的目标 Torso 具有 shoulder 骨；CM-10/EX-00 的各体型 palette 不同。共享缝骨必须从每个目标 Unit、每个 LOD 的实际 BoneInfo 交集推导：

```text
shared_palette(profile, side)
  = intersection(Torso profile LOD0..3, Arm profile/side LOD0..3)
```

本案例得到：

| 体型 | 缝边语义骨 | 原因 |
| --- | --- | --- |
| Slim | `l_clavicle/r_clavicle` | Slim Torso 与对应 Arm 的全部 LOD 都包含 clavicle |
| Stocky | `chest` | Stocky Torso 的全部 LOD 不含 clavicle/shoulder；与 Arm 的稳定公共骨为 chest |

若把所有体型压成一个全局 palette 交集，会不必要地把 Slim 也降级为 `chest`；若只按 Slim 选择 clavicle，Stocky 又无法序列化。正确做法是按 profile 分流受影响的 authoring role，并保持非目标域相同。

## v3：精确缝环与受控内侧过渡

v3 保持 v2 的面归属、顶点位置、UV、法线、材质、atlas 和整体轮廓，只修改上身蒙皮：

- `torso`、`left_arm`、`right_arm` 分为 Slim/Stocky authoring 变体。
- `helmet`、`hip`、`left_leg`、`right_leg` 保持共享。
- 所有坐标匹配的边界点在两侧都使用该 profile 的缝骨和精确 `1.0` 权重。
- Arm 内侧第一、第二拓扑环分别保留约 `1/3`、`2/3` 原权重，再恢复原 Arm 权重。
- 每点最多 4 influences，并在序列化精度下重新归一。

`1/3`、`2/3` 和两圈过渡是本模型的 case-specific 设计，不是固定公式。可复用合同是“精确公共驱动的缝边 + 有限、可审计的内部过渡 + 域外权重冻结”。

v3 有 10 个物理 Blender 对象，但每个体型仍只有 7 个逻辑角色，且分别恰好覆盖全部 109,144 个源面。报告必须同时区分：

- 物理对象数：为不同 profile 序列化而存在的重复载体。
- 每 profile 的逻辑角色/face coverage：判断漏面和重复面的真实合同。

用物理对象总数直接做 face coverage 会把必要的 profile 复制误判为重复几何。

## 边界不一定闭环，权威集合必须在坐标空间冻结

DR03 的部分衣物肩口本来就是开放组件，因此“边界必须是单闭环”不是通用硬门。通用门禁应是：

1. 从候选的 face ownership 和中立坐标建立权威 seam vertex/edge 集合。
2. 两侧对每个权威坐标都有匹配，且没有声明外的缺边。
3. 两侧完整语义权重行一致。
4. 固定这组对应，在差分姿态中验证分离距离。

本案例权威坐标边为左 70、右 169。AQ 会按 UV、法线、loop/section 语义拆分顶点，序列化后右 Torso 多出 1 条索引级内部边；它不在候选权威缝边中，Arm 也没有缺边。因而不能要求“候选与序列化 raw index boundary 集合完全相等”。应把 local indices 映射回坐标空间，验证全部权威边仍存在，再单独分类额外的 pseudo-boundary。

## 序列化读回必须恢复语义骨名

authoring 中的 `0_N` 和最终 RawMesh 的局部 bone index 不是跨 Unit 的全局骨号。v3 对 Slim/Stocky × 左/右 × LOD0-3 共 16 条肩缝执行独立回读：

1. 从实际目标 Unit 读取对应 LOD 的 BoneInfo。
2. 将每个正权重 local index 通过 `RealIndices` 还原到 TransformInfo/语义骨名。
3. 检查 Torso/Arm 两侧均解析为该 profile 的预期缝骨。
4. 比较完整权重行、坐标 seam edge 和压力姿态分离。

候选最大中立坐标误差为 `2.9802322387695312e-8 m`，45 度公共骨变换后的最大分离为 `5.960464477539063e-8 m`；16 条序列化肩缝权重误差均为 0。该结果是强离线证据，仍不能替代 v3 游戏内复测。

## 编译差分使用字段允许列表

“最终 patch 哈希变化”不能证明只修了肩缝。v3 以冻结 v2 为基线，按资源和字段分层比较：

- entry key 集合完全相同。
- 26 个 suppression Unit 逐字节相同。
- helmet、hips、双腿共 6 个未受影响 visible Unit 逐字节相同。
- 6 个上身 Unit 的 metadata、material table、position、normal、tangent、UV、color、indices 和 culling 数据相同。
- 上身变化只允许落在 bone indices/weights 等蒙皮字段。
- 私有 Material 与 11 个私有 TextureMap 逐字节相同。

这种“受影响字段允许列表 + 非目标资源逐字节冻结”应优先于只比较顶点数、bounds 或总资源数。

## 包编号不是已安装版本身份

发布包使用 `patch_7`，但 Mod Manager 曾把已安装 v2 重排为 `patch_0`。因此：

- patch index 是安装位置，不是版本身份。
- 停用、诊断和回滚都以三件套 SHA-256 识别。
- 打包时记录占用 index 快照；部署前必须重新读取，不能沿用旧快照。
- 同一目标 Unit 的 v2/v3 不得同时启用；更高优先级会覆盖较低版本并污染测试归因。
- 被拒绝发布物移出 `Output/`，但保留原文件名、哈希、报告和冻结编译基线。

## 反面案例摘要

| 做法 | 为什么失败 |
| --- | --- |
| 看到纯灰就重做 atlas/UV | 实际是更高优先级 Mod 劫持 Material/TextureMap ID |
| 只给 Unit 使用私有 ID | child Material 仍引用冲突 TextureMap，闭包并未私有化 |
| 中立边界共点即通过 | 不同骨驱动在动作中可产生厘米级裂缝 |
| 直接照搬参考案例的 shoulder 骨 | Stocky Torso palette 中根本没有该骨 |
| 为兼容 Stocky 把所有体型都绑 chest | 丢失 Slim 可用的 clavicle 语义；全局最小交集过度降级 |
| 强制所有肩口为单闭环 | 开放衣物组件会被误判；也不能发现同坐标不同权重 |
| 要求序列化 raw index boundary 完全相等 | AQ loop vertex split 会制造索引级 pseudo-boundary |
| 只凭 patch 编号判断已安装版本 | Mod Manager 可重排 index，可能删除或测试错误候选 |

## 证据入口

- [完整 SOP](../../../SOURCE_REFERENCES.md#local-only)
- [v3 candidate build 报告](../../../SOURCE_REFERENCES.md#local-only)
- [v3 candidate 独立读回](../../../SOURCE_REFERENCES.md#local-only)
- [v3 compile 与最小差异报告](../../../SOURCE_REFERENCES.md#local-only)
- [v3 serialized seam 报告](../../../SOURCE_REFERENCES.md#local-only)
- [已归档的 v3 离线发布包](../../../SOURCE_REFERENCES.md#local-only)

完整 FileID、候选/报告/三件套/ZIP 哈希、拒绝资产位置、复现命令和后续人工复测矩阵以项目 SOP 为准。
