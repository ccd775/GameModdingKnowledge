# Karin Umbrella RS6 / RS67 / RS100 案例：完整 Unit 克隆、肩骨折叠与骨盆桥接

> 项目：`HD2/Umbrella_Replace_RS6RS67RS100`
>
> 目标：使用同一 Karin Umbrella 模型替换 RS6、RS67、RS100 的身体与头盔。
>
> 权威状态：v1 已被用户游戏内截图判定为 `runtime_rejected`；v2 是当前不可变几何/绑定基线；v3 Armor LUT splat 恢复版已 `packaged_and_offline_verified`，截至 2026-08-08 仍为 `runtime_validation_pending`。本案例没有部署 v3，也没有执行游戏自动化测试。

## v1 运行时拒绝：相同几何不等于相同运行时合同

v1 的离线资源集合、几何计数和贴图闭包均可解析，但用户在游戏中观察到：

- RS6 肩膀与大臂断开，双腿与胯骨断开。
- RS67、RS100 的身体、腿、尾巴等角色分件整体错位，表现为全方位比例/绑定分离。
- RS100 头盔巨大且悬空。

持久化证据：

- [RS6 肩/胯断开截图](../../../SOURCE_REFERENCES.md#local-only)
- [RS67 全身绑定分离截图](../../../SOURCE_REFERENCES.md#local-only)
- [RS100 头盔巨大悬空截图](../../../SOURCE_REFERENCES.md#local-only)
- [截图、故障三件套与根因哈希清单](../../../SOURCE_REFERENCES.md#local-only)

只读差分定位到 v1 的编译策略：它把同一角色几何分别写进各目标原生 Unit，同时保留 RS6、RS67、RS100 各自不同的 `TransformInfo`、`BoneInfo` 和 inverse bind。因而下面这个门禁是错误的：

```text
RawMesh payload equal across targets
=> runtime transform/bind equal
```

正确关系是：

```text
runtime result
  = RawMesh in mesh-local space
  + MeshInfo/TransformInfo
  + BoneInfo/local palette/inverse bind
  + external animation skeleton
```

其中任一项换了 lineage，几何字节相同也可能整体缩放、悬空或沿分件爆开。该反例把“多目标同几何时检查完整 Unit 合同”提升为 `project-proven`。

v1 还把源 `Shoulder` 投影到 clavicle、把 `UpperArm` 投影到 shoulder；其左右 shoulder endpoint closure 已经达到 `0` 与约 `5.96e-8 m`，仍被运行时截图否决。这证明 closure 只回答“选定的父子端点是否闭合”，不能证明源/目标肩语义数量、Torso/Arm 驱动、完整 Unit bind 或外部动画合同正确。

## 多目标替换：按角色编译一次，再克隆完整 Unit

v2 为七个逻辑角色各选一个完整载体：

- torso、left/right arm、hip、left/right leg 使用锁定的 DS42 完整 Unit。
- helmet 使用已验收的 RE2310 v5 head-only 完整 Unit。

每个角色只执行一次 AQ mesh compile：

```text
load complete carrier Unit
-> lock TransformInfo and core BoneInfo/inverse-bind signature
-> replace every positive render LOD RawMesh
-> save and reload carrier Unit
-> prove bind/header signature preserved
-> clone complete serialized Toc/GPU/Stream payload to every target FileID
```

克隆时只改 entry FileID；不是把刚生成的 RawMesh 再编进目标原生容器。最终同角色目标的完整 Unit payload 必须逐字节相同。

这是“目标外观和绑定应完全一致”时的通用方案，不代表所有项目都必须共享一个载体。若 Slim/Stocky 或槽位确实需要不同动画/调色板合同，应按 profile 使用不同的完整载体；不可采用的中间状态是“共享一份几何，却无证据地混用多个 target bind”。

本案例身体与头盔使用不同载体也说明：carrier policy 应按逻辑角色决定，不需要把全身强塞进一个 Unit lineage。具体载体 FileID 见[项目 SOP](../../../SOURCE_REFERENCES.md#local-only)，属于 `case-specific`。

## 良好肩膀的四层合同

肩膀不能简化为“把权重刷平”。本案例在 RE2310/DS42 方法上补足了“源双骨链折叠到目标单肩骨”的处理。

### 1. 轮廓与面归属先行

- 保留源 current shape mix 中的肩帽、肩胛、腋下和近端上臂轮廓。
- 先按源权重语义选出 shoulder/UpperArm 候选面，再把面心转换到 Ref 阈值所属的游戏空间分 Torso/Arm。
- 每个源面恰好归一个角色；缝边复制源顶点，不移动顶点“补肩峰”。
- 上背绳带、颈饰等附件保持其拓扑/语义所有权，不能被宽松的 arm envelope 吞入。

局部抬肩峰、外扩肩帽、缩放上臂只能暂时改变静态剪影，不能修复 bind、面归属或动态接缝。

### 2. 先比较源骨语义数与载体关节语义数

Umbrella 源骨架在一侧有 `Shoulder` 与 `UpperArm` 两组权重，而 DS42 载体用于该处的主要变形语义是一个 `l_shoulder/r_shoulder`。v2 因此将：

```text
Shoulder.L + UpperArm.L -> l_shoulder
Shoulder.R + UpperArm.R -> r_shoulder
```

这不是可直接复制到其他 donor 的固定骨名表。只有当目标完整载体的实际 palette、父子链和已验证参考都证明“两个源语义应由一个目标关节驱动”时才可折叠。若目标 Torso/Arm 没有该公共骨，应按实际 Unit/LOD palette 交集选 clavicle、chest 或独立 profile，不能强行照搬 `shoulder`。

### 3. 折叠后的肩变换锚在真实上臂段，并保留 donor roll

当 `Shoulder` 与 `UpperArm` 合并到一个游戏肩骨时，几何修正以源 `UpperArm` 为起点、`LowerArm` 为 child，而不是以较短的装饰/肩带 `Shoulder` 段作为实际肱骨长度：

```text
u = normalize(source LowerArm origin - source UpperArm origin)
v = normalize(target elbow origin - target shoulder origin)

R_base  = R_target_shoulder * C_source_to_game * inverse(R_source_upperarm)
R_close = shortest_arc(normalize(R_base * u), v)
L       = R_close * R_base * axial_scale_along(u)
t       = target_shoulder_origin - L * source_upperarm_origin
```

`R_base` 保留完整 DS42 肩 frame 的 roll；`R_close` 只增加闭合真实 parent-child 轴所需的最小 swing。这样既不丢 donor 已验证的肩袖方向，也不会因为源骨显示轴和真实 `UpperArm -> LowerArm` 链不一致而留下端点误差。

肩部与肘部不应无条件使用同一算法：本案例肩使用“donor 完整 frame + 最小闭合 swing”，肘和腿的宽几何则使用 parent-child shortest-arc，避免不镜像的 raw roll 让左右袖子反向扭转。

左右两侧使用同一个有符号 semantic basis；镜像由源骨架本身和完整三维门禁证明，不能再人工给右侧乘一个相反符号。

### 4. Torso/Arm 缝边必须同位置且同完整权重行

中立姿态共点只证明 `p_left(0) == p_right(0)`。若两侧权重不同，动作中仍会断开。固定源顶点对应后，应同时要求：

- 两侧 neutral position 在序列化精度下相同。
- 两侧完整语义权重行相同，而不只是 winner bone 相同。
- 权重语义存在于两侧完整载体的全部正 LOD palette。
- 在 shoulder/elbow 相对运动的差分姿势中，用固定对应集合计算 posed seam；不能在 posed 状态重新最近点配对。

Umbrella v2 左右肩段端点闭合误差分别约为 `2.98e-8 m` 和 `8.94e-8 m`，Torso/Arm 共享位置与权重误差均为 0。这些是 `case-specific` 离线数值，不是游戏内通过证据。

本模型含开放、多组件衣物肩口，因此 v2 的共享点集合不是单闭环：左、右固定对应点分别为 209、212，候选报告中的 `closed_matching_boundary_loops` 和 `boundary_edges_match_by_source_vertex` 均为 false。开放拓扑本身不应被错误判死，但边集合不一致意味着 v2 仍缺最终序列化 differential-pose seam 证据；必须保持 `runtime_validation_pending`，不能仅凭位置/权重误差为 0 宣称肩部已经运行时通过。

## 骨盆不要从 Torso 直接跨到 Leg

v1 的胯腿断开还暴露了角色分件图错误。v2 将下身所有权改为：

```text
torso -> hip -> left_leg/right_leg
```

并把 direct torso -> leg bypass 设为硬失败。共享顶点按接口分别统一：

- torso/hip 使用双方载体都支持的躯干语义。
- hip/leg 使用 hips 与对应侧 thigh 的受控混合。
- 左右胯中央共享点使用 hips。

本案例共统一 750 个骨盆共享源顶点，最大权重误差由 `1.0` 降为 `0.0`；torso/leg 直接共享点为 0。具体切分高度和精确骨名属于该模型/载体，通用合同是“接口图连续、双方 palette 可表达、位置与完整权重行一致、禁止跨层旁路”。

## 巨大悬空头盔优先查载体，不先缩模型

RS100 头盔巨大悬空与 RS67/RS100 全身分离同源：目标原生 Unit 的 mesh/bind container 与写入几何不兼容。v2 将完整头部刚性绑定到 `head`，只编译进 RE2310 v5 的 head-only 载体，再把完整 Unit 克隆到三个头盔目标。

遇到类似症状时，先比较最终 Unit 的 `MeshInfo transform`、`TransformInfo`、`BoneInfo`、inverse bind 和 head anchor；直接在 Blender 缩小/下移头盔可能只对一个目标暂时对齐，并把另两个目标或动画姿势进一步破坏。

## 同槽替换时的私有 ID 例外

v2 沿用 v1 的 1 个私有 Material 与 11 个私有 TextureMap ID，只因为它被打包为已诊断错误版 `patch_3` 的精确原位替换，且明确禁止两版共存。打包门禁要求：

1. live `patch_3` 三件套哈希精确等于被拒绝 v1。
2. 碰撞扫描排除这一个即将被替换的三件套。
3. 扫描其余全部已部署 patch 的 typed full ID、任意类型 full ID、high32 和目标 Unit ID。
4. ZIP 仍使用同一三成员名，部署策略为 replace，不是 coexist。

若旧版可能残留在其他 index、需要两版共存，或 live 槽位哈希已变化，就必须生成全新 namespace 并重新编译；不能把“同一 Mod 的更新”当成普遍可忽略 ID 冲突的理由。

该案例 v1 与 v2 的 `.stream` 哈希恰好相同，但 TOC/GPU 不同。版本身份必须绑定完整三件套，不能只看 patch index、修改时间或其中一个成员。

## v3 Splat 恢复：parent ABI、Piece.MaterialLut 与 UV 必须同时闭合

v2 的几何和绑定保持不变，但其私有材质仍使用 Advanced parent，且 33 个可见 Unit 的 UV1/UV2 全零。v3 按 Armor LUT splat recovery 流程完成三个互相独立的责任域：

1. 将私有 Material 迁移到原生 Armor LUT parent `0xf5ebd93181fdf00c`，完整保留 `11 textures / 25 variables` ABI 与 binding 顺序。
2. 从当前 armor-set 快照枚举 RS6/RS67/RS100 armor 与 helmet 的全部 Piece，为 10 个只归属于目标六个 kit 的 `Piece.MaterialLut` 增加 same-ID 中性覆盖。
3. 在 33 个可见 Unit、132 个 mesh、2,730,732 个被引用顶点上写入明确 UV ABI：UV0 保持 atlas，UV1 使用跨 Unit/LOD 连续的全局绑定姿态斜投影，UV2 逐字节复制 UV0。

可迁移结论：克隆正确 Armor LUT parent 仍不能证明 splat 生效，因为 Piece 会在生成时覆盖静态 MaterialLut；反过来，只覆盖运行时 LUT 而 UV1/UV2 全零也不能证明覆盖层有有效坐标。最终门禁必须同时闭合 Material ABI、Piece ownership、runtime LUT content、UV 语义和部署环境 provider。

v3 相对 v2 的差分被限制为 1 个私有 Material、11 个私有静态 TextureMap、10 个运行时 LUT TextureMap，以及 33 个可见 Unit 的 UV GPU 字节。71 个 Unit 的主 payload/stream、38 个 suppression Unit GPU 和其他资源均保持。基础级与全 mip 贴图面积分别为 8,980,461 与 9,177,695，均低于 4096 x 4096 上限。

当前已安装 v2 被 Mod Manager 重排到 `patch_2`，不再位于包名中的 `patch_3`；live `patch_3` 已属于另一个补丁。这再次证明 replacement lineage 必须用完整三件套哈希识别。v3 包只能先由 Mod Manager 禁用/卸载精确 v2 lineage 后安装，不能把包内 `patch_3` 手工覆盖到当前 live `patch_3`。

## 冻结载体优于静默跟随游戏更新

构建期间当前游戏基础 archive 已转为 DSAR，旧目标 archive 名也发生变化。v2 没有把解析失败的当前游戏文件临时当 donor，而是继续使用哈希锁定、已可解析的 DS42/RE2310 载体。

可迁移结论：游戏更新后若 parser、archive root 或目标身份变化，应先建立新格式/ABI 证据，再显式升级载体 lineage。不能因为“当前文件更新”而静默替换已经证明的 TransformInfo/BoneInfo 来源。

## 反面案例摘要

| 做法 | 运行时/工程后果 |
| --- | --- |
| 相同 RawMesh 分别编进不同 target-native Unit | 各目标保留不同 transform/bind，出现整体比例、分件和头盔错位 |
| 只比较顶点数、bounds 或 neutral | 无法发现外部骨架合同和动态 seam 不一致 |
| Shoulder 与 UpperArm 随意映到两个目标骨 | 可能制造双关节、错误段长或 Torso/Arm 不同驱动 |
| endpoint closure 为 0 就宣布肩部通过 | closure 不覆盖语义折叠、分件 seam、完整 Unit bind 或外部动画合同 |
| 折叠肩链后以 source Shoulder 小段为肱骨锚 | 实际 UpperArm -> LowerArm 端点无法闭合 |
| 肩部只做 shortest-arc 并丢弃 donor frame | 可能闭合链轴，但丢失已验证 roll 与肩袖方向 |
| neutral 缝边共点即验收 | 完整权重行不同会在举臂时分离 |
| Torso 直接切到左右 Leg | 胯部缺少连续 owner/palette 桥，容易形成环状裂缝 |
| 看到巨大头盔先手工缩放 | 掩盖 Unit container/bind 根因，只对单一目标或姿势偶然有效 |
| 复用旧私有 ID 却让旧版共存 | 加载顺序决定错误材质或贴图 provider |
| 游戏更新后无证据更换 donor archive | 将格式变化与绑定变化混入同一次修复，失去 provenance |

## 证据入口

- [项目长期 SOP](../../../SOURCE_REFERENCES.md#local-only)
- [v2 候选报告](../../../SOURCE_REFERENCES.md#local-only)
- [v2 编译与完整 Unit 克隆回读](../../../SOURCE_REFERENCES.md#local-only)
- [v2 替换式打包与部署碰撞扫描](../../../SOURCE_REFERENCES.md#local-only)
- [v2 离线发布包](../../../SOURCE_REFERENCES.md#local-only)
- [v3 运行时 LUT 归属合同](../../../SOURCE_REFERENCES.md#local-only)
- [v3 独立 AQ UV 回读](../../../SOURCE_REFERENCES.md#local-only)
- [v3 最终离线综合验收](../../../SOURCE_REFERENCES.md#local-only)
- [v3 替换式打包与部署碰撞扫描](../../../SOURCE_REFERENCES.md#local-only)
- [v3 离线发布包](../../../SOURCE_REFERENCES.md#local-only)

完整 FileID、载体 ID、三件套哈希、贴图预算和复建命令以项目 SOP 与机器报告为准。
