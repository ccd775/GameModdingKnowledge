# Karin Y -> Witch 双目标替换案例

本文记录 `L4d2/Y_Replace_Witch` 从失败候选到用户验收候选的可复用结论。数字、哈希、骨数和阈值是本项目证据，不是新角色的默认参数。

## 1. 项目边界与来源

- 用户源 Blend：`L4d2/Shared/Models/Optimized/Karin_Y_BlenderSafe/Karin_Y_GeneralWorkflow.blend`；37 mesh、198,156 vertices、373,954 triangles、316 bones（270 deform）、376 shape-key blocks、8 个材质族。
- VRM：只作为动态意图和许可参考，不作为 Source skeleton、眼骨映射或可再分发许可。当前 VRM meta 为 `OnlyAuthor`、`Redistribution_Prohibited`、violent/commercial disallow。
- 目标是两个独立 runtime family：`models/infected/witch.{mdl,vvd,dx90.vtx,phy}` 与 `models/infected/witch_bride.{mdl,vvd,dx90.vtx,phy}`。
- 参考 VPK 只提供 ABI、材质和编译结果证据；它没有 QC/SMD/PHY 源，不能被当成可复现工程或最终可见资产来源。

普通 Witch 与 Bride 共享动画接口，但原生骨数、jiggle 数、附加 marker 和 physics 来源不同。两个目标必须分别生成 QC、分别编译、分别审计；“只复制普通模型再改文件名”不是安全做法。

## 2. 源模型审计得到的两个硬提醒

### 2.1 先烘焙当前有效 shape key

源 Blend 没有可直接复用的 Source action/constraint/driver；若直接清除 shape keys，会丢失当前默认体型。审计发现多个服装/身体 key 的默认值为 `0.75`，Hair 的 `Ahoge_big` 和 `Hair_tail_volume_up` 为 `1.0`。正确顺序是：在派生副本中烘焙当前非零值到 Basis，按需传播到仍保留的相对 key，随后才删除无用 key。

不要把全部隐藏或 `_OFF` key 导成 VTA：本源有大量极端位移，可能造成爆模。只导出目标游戏明确需要的 flex，并对 frame 0、最终拓扑和法线重新审计。

### 2.2 VRM 动态骨不是 Source `$jigglebone` 参数表

VRM spring group/collider 只能说明链顺序、首动态段、相对刚度/阻尼和碰撞意图。Source 没有同构的 collider solver，转换时必须使用保守的角度/长度/刚度限制，并把 anchor 与首动态段作为独立门。VRM 中损坏的 humanoid eye mapping 也不能直接信任；眼骨应从最终 Blend/目标 ABI 单独确认。

## 3. v0.1 -> v0.3 的反馈链

| 候选 | 结果 | 推翻/确认证据 |
| --- | --- | --- |
| v0.1 | `REJECTED_POSE_REGRESSION`；Bride 根位移异常，手臂姿态不可信 | HLMV/离线失败截图和旧包哈希 |
| v0.2 | `REJECTED_GAMEPLAY_ARM_RIG`；Bride 已接地，但游戏内双臂像四段折断 | 用户截图 `reports/visual/v0_2-gameplay-arm-regression.png`，SHA `41074F803973F0AD4426AC2AF69D2D68ADFD2EA026BD3DB8AD244FEE165F22D3` |
| v0.3 | `ACCEPTED_OFFLINE`，随后收到用户“验收通过” | [用户验收 sidecar](evidence/karin-y-witch-v0.3-user-acceptance-2026-08-18.md) |

v0.2 说明：旧的全局 triangle-edge 统计与 HLMV 固定抽帧都可以通过，而运行时仍然失败。实机/用户证据优先级高于“结构报告 accepted”；发布门必须增加关节运动学和对象/局部区域门。

## 4. 项目专用数值（不可复制）

下表用于识别本案例的候选与审计粒度，不是新的公共阈值或目标：

| 项目 | v0.3 项目实测 |
| --- | --- |
| 核心 bind | 53 个 ABI core；Karin pivot + 锁定 custom-bind rotation |
| 成品骨/动作/LOD0 | 126 bones / 85 sequences / 44,543 vertices each |
| physics | 两目标各 18 PHY solids，各自 companion family checksum 闭合 |
| 导出三角 | 47,276（源模型为 373,954） |
| pose audit | `Idle_Standing_Crying` 91 contiguous frames，schema v2，44/44 checks |
| HLMV | 每目标固定 5 个帧样本，另有 Ground + Origin Axis + Bones 诊断帧 |
| release | 27 entries，46,457,899 VPK bytes |

新角色必须从自身 source、native target、成熟参考、已知坏候选和运行时视觉尺度重新计算所有门。

## 5. 四段手臂的真实根因

### 5.1 复合 bind basis 不相容

旧实现保留了 native Witch 的 global rotations，却把 Karin T-pose 的 joint positions 塞进同一骨架。名称、index、parent 和左右侧别都可能正确，但 parent-local translation 的方向已经不再沿目标骨轴：旧候选 Forearm/Hand 的约 `94%` translation 分量落在横向分量，肩到腕在 idle 中接近直线，原生屈肘运动被投影成多段折线。

正确做法不是盲目交换 L/R，也不是只把每根骨的 head 搬到源位置，而是选择一套有证据的 custom bind basis：保留目标 ABI 的 name/index/parent，使用同一 custom reference 提供核心 world rotation，使用 Karin 关节位置作为 pivot，然后重新计算 local transform。最终必须验证：

- 骨轴指向子关节，尤其 Clavicle -> UpperArm -> Forearm -> Hand；
- bind segment 的横向 translation/轴偏离在项目容差内；
- 全长动画中的 elbow bend delta 与原生动作一致；
- shoulder-hand reach ratio 与 upper-arm + forearm 长度合理；
- upper-arm/forearm 长度在 91 帧内没有额外漂移。

本项目锁定的 custom reference 是示例中已成功编译的 `witch/shenti.smd`，SHA `24EDF8643624FF1C8A49F673A17D4A13213D725C15D7A332EABC68BD0C42BDFB`。这个文件的身份只能作为本项目血缘证据；新项目必须选择并锁定自己的 reference。

同一类 composite bind 问题后来也在 Hunter 替换中出现，但错误修正又增加了整网格
LBS prepose，造成歪头与下巴前伸。跨案例对照见
[Karin Nyako -> Hunter](20-karin-nyako-hunter-case-study.md)；两者证明的是审计方法，
不是 Witch/Hunter 之间可直接复用 rotation、pivot 或阈值。

### 5.2 袖子被误当成上臂

旧候选把 35 个 `TY_Arm*`/`TY_ArmStrap*` 源组强制折到右 UpperArm。源语义和 VRM spring chain 表明它们属于右前臂外袖链；真实皮肤/手套已经随 Forearm 弯曲，外袖仍沿 UpperArm 下垂，于是画面出现一个额外的“假肘/假前臂”。

修复是让这些组按真实 source ancestor 回落到右 Forearm，并在减面时保护 Body arm band、Ty_Outer 肘带和局部肩部过渡。不要用整片袖子强灌 UpperArm，也不要用全局 smooth 抹平局部问题；先按对象、空间区域和源权重语义建立门。

## 6. Bride 悬空的根因与修复

Bride 的 rotated export canonical 只被部分采用：脚本取了 Bride 的 root position，却保留了另一套目标 rotation。这样生成的 `proportions` autoplay predelta 同时出现横移和抬高，编译后的 Bride root delta 比普通 Witch 多约 `+35.09` Source units 横移和 `+36.71` Source units 抬高。HLMV 中同一相机、同一 sequence 仍只剩脚在画面上方，因此不是取景误差。

修复是让普通 Witch 与 Bride 的可见几何共享同一个完整 canonical reference（position、rotation、projected Pelvis/core/full/root delta 都逐项比较），同时保留 Bride 自己的 source-local physics 和 model path。不要用 `$illumposition` 或移动 PHY 来“修”视觉原点；它们不是 autoplay root owner。

## 7. 关节运动学与表面蒙皮必须双门

本项目的 schema-v2 pose audit 覆盖 `Idle_Standing_Crying` 的 91 个连续帧，分别检查：

1. **运动学门**：左右 elbow bend delta、shoulder-hand reach ratio、upper-arm/forearm segment drift、bind reconstruction 和有限性；
2. **表面门**：全角色 arm、`Body_base`、Ty_Outer 肩/肘等对象/局部区域的 edge stretch 分位数、绝对边长和样本覆盖。

全局 edge p99 不能替代关节运动学；局部坏三角也可能被整模统计淹没。Witch v0.3 的实际结果（只作为案例校准）是 44/44 checks、combined arm `p99/p99.9/max = 1.464187/1.772516/2.341558`，左右 elbow bend delta 最大误差分别约 `0.013069 deg` 与 `0.000944 deg`。这些数值不能复制为其他模型阈值，应由原生控制组、已知坏候选和可见尺度重新校准。

## 8. 双变体编译、物理和二进制审计

最终 v0.3 两个模型均为 126 bones、85 sequences、44,543 compiled LOD0 vertices、18 PHY solids；正式 Witch/Bride checksum 分别为 `E4E9F10A` 与 `76362149`。这些是候选身份，不是通用目标。

必须保留的流程：

- 两个 `$modelname` 各自独立编译，不共享陈旧 MDL/VVD/VTX/PHY；
- 每个目标的 MDL/VVD/VTX/PHY checksum、骨、sequence、attachment、hitbox、IK、include 和 physics 分别审计；
- `anim_witch.mdl/.ani` 仅进入 compile sandbox，不能进入发布包；
- preview QC 只允许与正式 QC 有明确的唯一 modelname 差异；
- VTX 做逐 bodypart/model/mesh/strip-group 的 original-index mapping 审计，StudioMDL exit 0 不能代替它；
- PHY 让 StudioMDL 按最终同名骨转换，不要先手工预变换后再让编译器转换一次；每个目标必须从同一轮编译携带自己的 PHY。

参考包没有 PHY 不代表新模型可以省略 PHY；若没有独立物理证据，必须明确记录依赖原生行为的决定，而不是默认为安全。

## 9. HLMV 的可重复矩阵与路径陷阱

HLMV 预览必须使用唯一 alias 和**绝对 preview MDL 路径**。相对模型参数会按 HLMV 启动 cwd 解析，即使 `-game` 指向 compile sandbox，也可能打开空白或原版。

本项目对两个变体都固定检查 `Idle_Standing_Crying` 的帧 `0, 22, 45, 68, 90`，每帧 Ground 开启；frame 45 额外打开 Ground + Origin Axis + Bones。多窗口环境下必须锁定准确 HWND，并回读 sequence/frame 控件，避免把另一模型窗口的状态当成当前候选。

HLMV 通过只表示离线视觉门通过，不表示游戏实测；反之，用户游戏截图可以推翻 HLMV 和旧数值门。发布报告必须保留两者的时间顺序。

## 10. 发布闭包与证据

v0.3 VPK 为 27 entries、46,457,899 bytes、SHA `13C06C66BD0229E31A31503B0DDB7A200FAF4141FEBF507B8AF61702123058D0`；loose tree 与 VPK 逐条 bytes/CRC/SHA 相等，preview、参考源、QC/SMD 和 `anim_witch` sidecar 均不在 payload。

每轮候选应保存：source lock、model-build/rig-map、pose audit、compiled binary audit、HLMV screenshot manifest、package validation、失败候选和用户追加验收。用户反馈应绑定候选 SHA、日期、原话/摘要、范围和未覆盖项，不能把“验收通过”扩写成未测试的全矩阵。

本项目的 v0.2 反面当前有用户游戏截图和项目 SOP 历史，但没有独立锁定的 schema-v2 machine-readable negative report。因此它是有效的运行时反例，却不能被写成“现有审计器已可复跑地拒绝 v0.2”。未来若补建负控，必须同时归档输入 hash、审计 schema 和预期失败 check ID。

## 11. 可迁移的反面案例

1. ABI/name/index/parent 全对，不代表 rotation basis 与 source pivot 组合正确。
2. 全局 edge stretch 通过，不代表 elbow、reach 或服装局部跟随正确。
3. 把外袖辅助骨按名称或位置硬挂 UpperArm，会制造假肢段；要按源父链和动态语义处理。
4. 只修 Bride 的 `$illumposition` 或 PHY，不能修 autoplay root delta。
5. 参考 VPK 能加载，不代表它提供可复现 QC/SMD/PHY，也不代表其 license 允许再分发。
6. HLMV 窗口标题、相对路径和单帧截图都不是 payload lineage 或完整动作合同。
