# Karin SSF FS-37/SC-15 案例：自然肩缝权重与 DS42 owner Unit 克隆

> 项目：`HD2/SSF_Replace_FS37SC15`
>
> 目标：使用 Karin SSF 替换 FS-37 Ravager 与 SC-15 Drone Master，并利用两套装备实际共享的身体 Unit 只制作一次身体几何。
>
> 权威状态：以 [项目 SOP](../../../SOURCE_REFERENCES.md#local-only) 为准。v1-v3 均被用户游戏内反馈拒绝；v4 采用完整 RE2310/DS42 owner lineage 后，于 2026-08-09 获得用户明确“已验收通过”，在本轮修复范围内为 `runtime-validated`。该验收由用户手动完成，Codex 没有执行部署、启动游戏或自动化运行测试。

## 本案例新增的运行时结论

本案例把以下结论从离线推断提升为 `project-proven` 的用户运行时接受证据：

1. Torso/Arm 中立坐标相同、边界权重在覆写后相同，并不能证明肩部绑定正确。
2. 几何若按 `shoulder` rest-to-bind correction 烘焙，运行时权重却被改为 `clavicle`，neutral 仍可能看似闭合，动作中会出现肩线错误和大臂断层。
3. 当自然 donor projection 已使接口两侧完整权重行逐点相同时，任何 blanket shared-bone override 都是破坏，而不是修复。
4. 为掩盖错误接口而添加固定两圈权重渐变，会把第一条断缝转移成大臂中段的刚度折带。
5. 多目标共用外观时，正确复用单位是“每逻辑角色一个完整、已证明的 donor Unit lineage”，不是“同一 RawMesh 分别写入各 target-native Unit”。
6. “肩部不做 post edit”不能机械扩展为“所有 seam 都不做 post edit”；腰与髋腿边界必须按自身自然投影误差独立决定。

## 失败链

| 版本 | 运行时结果 | 主要根因 |
| --- | --- | --- |
| v1 | 肩部断开、右腿与胯断开、上半头发偏暗 | 分件 seam 与骨表不自洽；右腿缺少正确 thigh chain；误用源材质实际未绑定且 UV 岛内大面积为黑的 hair normal |
| v2 | 头发受光修复，肩部与右大腿仍错误 | 肩界硬锁 `chest`；右腿按所有目标 LOD 的全局骨表交集退化为 `r_knee`，破坏大腿体积 |
| v3 | 右腿改善，但肩线仍错误且大臂中段断裂 | 肩缝强制 `clavicle=1`，再人为添加两圈 clavicle 过渡；身体仍在 target-native Unit 中分别编译 |
| v4 | 用户明确验收通过 | 保留自然 `chest + side shoulder` 权重；身体在 DS42 owner Unit 中按角色编译一次并完整克隆；下半身 seam 例外单独保留 |

v3 拒绝截图与报告见 [运行时拒绝记录](../../../SOURCE_REFERENCES.md#local-only) 和 [原始截图副本](../../../SOURCE_REFERENCES.md#local-only)。v4 用户验收见 [验收记录](../../../SOURCE_REFERENCES.md#local-only)。

## v3 为什么会“离线全绿、游戏仍断”

### 1. donor palette 选择错误后，用覆写掩盖报警

v3 先按 FS37/SC15 target-native 容器求可用 palette。原生 slim torso 没有 `l/r_shoulder`，于是 torso 内同侧 shoulder 语义被压到 `l/r_clavicle`；arm 侧仍保留 shoulder。候选报告中的肩缝 `max_weight_error_before_override=1.0` 是 lineage 不兼容的强报警。

错误处理是把接口两侧 171 点全部改为 `{clavicle: 1.0}`，使“覆写后的两侧权重误差”变成 0。该门禁只证明两份错误数据相同，没有证明它们符合源权重、几何 correction 或游戏 bind。

可复用规则：

```text
project each side independently through the intended final lineage
-> audit natural semantic weight rows before edits
-> treat a large pre-override error as a contract failure
-> never let a post-edit equality check erase the pre-edit failure
```

### 2. 几何 correction 与运行时权重语义分裂

SSF 的正确 retarget 已按 RE2310 语义把源 Shoulder/UpperArm 映射到 `l/r_shoulder`，并用 shoulder correction `D_shoulder` 烘焙几何。v3 随后把导出权重改成 clavicle，因此运行时实际使用：

```text
authoring position: p_bind = sum(w_shoulder * D_shoulder * p_source + ...)
runtime motion:     p(t)   = M_clavicle(t) * B_clavicle^-1 * p_bind
```

而不是与 authoring 同源的 shoulder 驱动。neutral 中 inverse bind 可以让两者暂时重合；只要 clavicle 与 shoulder 产生相对运动，错误就暴露。

### 3. 两圈“平滑”制造第二条折带

v3 在 arm 侧人为建立：

```text
seam  = 1.0 clavicle
ring1 = 2/3 clavicle + 1/3 original
ring2 = 1/3 clavicle + 2/3 original
ring3 = nearly full shoulder
```

这些环延伸到上臂中段。它们没有恢复正确 lineage，只把 clavicle 与 shoulder 的相对运动摊到两圈狭窄拓扑中，正好形成用户截图里的中段刚度折线。RE2310 接受路线不存在这种固定两圈算法。

## v4 如何精确复刻 RE2310/DS42 方法

### 冻结 clean authoring contract

v4 使用 [donor clean authoring contract](../../../SOURCE_REFERENCES.md#local-only)，该文件与 RE2310 clean contract 逐字节一致。六个身体角色分别使用一个 DS42 owner Unit：

| 角色 | DS42 owner Unit |
| --- | ---: |
| torso | `10880137359014613513` |
| left_arm | `15903719632451550601` |
| right_arm | `9176561510485273701` |
| hip | `8442753292735712283` |
| left_leg | `4718048748851718690` |
| right_leg | `703515194587506105` |

这些 FileID 是 `case-specific`。可复用的是：owner、MeshInfo、BoneInfo、carrier object、canonical projection 和 reference palette 必须从同一冻结合同读取，不能凭当前常见值硬编码。

### 每角色编译一次，再克隆完整 Unit

身体角色的编译顺序是：

```text
load exact DS42 owner Unit
-> for each positive LOD, use that owner RawMesh's MeshInfoIndex and BoneInfoIndex
-> compile candidate role into the owner container
-> preserve and verify owner header, TransformInfo, BoneInfo, MeshInfo and culling
-> save and parse the owner entry
-> clone the complete serialized Unit to every FS37/SC15 target FileID
```

只改目标 FileID，不把 RawMesh 注入另一套 target-native bind。两个 helmet 是例外：它们是不同原生消费者，均使用刚性 `head` 几何并在各自 native helmet container 中编译。

编译报告共有 8 个 visible compile record，即 6 个身体 owner role 加 2 个头盔目标，而最终仍覆盖 12 个 visible Unit 与 17 个 suppression Unit。编译后要求同一身体 role 的两个目标完整 Unit payload 逐字节相同。证据见 [编译报告](../../../SOURCE_REFERENCES.md#local-only) 和 [palette/clone 审计](../../../SOURCE_REFERENCES.md#local-only)。

## 自然肩缝是答案，不需要人工雕权

SSF 源模型按 DS42 canonical projection 分区后，左右肩各有 171 个共享源点：

| 来源对象 | 每侧共享点 |
| --- | ---: |
| `Body_base` | 18 |
| `Jacket` | 54 |
| `Jacket_Bag` | 99 |
| 合计 | 171 |

自然结果为：

- 两侧完整语义权重行逐点误差 `0.0`。
- 权重骨严格为 `chest + l/r_shoulder`。
- shoulder 权重最小值约 `0.9475716`，最大值 `1.0`。
- clavicle 最大权重 `0.0`。
- `Body_base` 每侧仍是 18 点单闭环；多层衣物按真实拓扑允许多个闭合组件，不能强制整个肩口只有一环。
- 35 度 shoulder-only 差分姿态中，两侧固定对应 seam 最大间隙 `0.0`。
- arm 邻接边长比约为 `0.9415..1.0477`。

因此 v4 的硬门不是“把肩缝统一到某个共享骨”，而是：

```text
natural donor-projected seam rows are already identical
and contain only chest + side shoulder
and no post-partition shoulder weight edit exists
and no artificial transition ring exists
```

实现与证据见 [v4 builder](../../../SOURCE_REFERENCES.md#local-only) 和 [35 度肩部审计](../../../SOURCE_REFERENCES.md#local-only)。

## 差分姿态审计本身也可能写错

若测试脚本把所有 `l_` 或 `r_` 前缀骨一起旋转，旧 v3 的 clavicle 带也会和 shoulder 一起移动，从而产生假连续。肩部专项姿态必须声明实际 moving set：

- 移动 `side_shoulder` 及其下游语义。
- 明确排除 clavicle，除非测试目的就是 clavicle/shoulder 相对运动。
- 报告每个 seam 点的 moving weight coverage，防止骨名未解析后“全不动也通过”。
- 固定 neutral 对应集合，posed 后不重新最近点配对。
- 同时检查 seam gap 与邻接 edge ratio；前者抓分离，后者抓大臂内部刚度折带。

这是 v3 失败后新增的审计器设计经验。

## 肩部无后处理不等于全身无后处理

同一只读探针显示，DS42 自然投影下：

| seam | 共享点 | 自然不一致点 | 最大权重误差 |
| --- | ---: | ---: | ---: |
| torso/hip waist | 184 | 105 | `0.08841348` |
| left hip/leg | 41 | 1 | `0.00779468` |
| right hip/leg | 41 | 1 | `0.00870710` |

因此 v4 只取消 shoulder post edit，仍保留三条经当前 ownership 图证明的边界合同：

- waist -> `spine1`
- left hip-leg -> `l_thigh`
- right hip-leg -> `r_thigh`

右腿同时改用完整 DS42 right-leg owner palette，保留 `r_thigh -> r_knee -> r_foot -> r_ball` 链。v2 把所有目标 LOD 先求全局最小骨表交集，导致 `r_thigh` 消失并把大腿压到 `r_knee`；这是“大腿变粗、穿出裙摆”一类症状的反面案例。

通用决策应逐 seam 进行：先测自然投影误差，再决定是否需要 shared-bone contract。不能因为 shoulder 天然正确就删除腰腿合同，也不能因为腰腿需要覆写就推断 shoulder 也应覆写。

## 头发变暗：不要使用源材质未绑定的贴图

`Karin_Hair` 与 `Karin_Hair_Transparent` 的实际源材质只绑定 p4 底色，没有绑定磁盘旁边的 p4 normal。那张 normal 在头发 UV 岛内大面积为黑。v1 因文件名看似匹配而误用它，导致上半头发异常受光变暗。

修复是对 p4 cell 使用平坦切线法线 `(128,128,255)`，并在 atlas 报告中锁 `page4_hair_normal_is_flat=true`。可复用规则是：贴图 provenance 来自实际材质 node/binding 与 UV ROI，不来自邻近文件名；未绑定贴图不能自动视为权威输入。

## 私有资源和严格总贴图预算

v4 使用新的带版本 namespace，不复用 v1-v3 或其他已部署 Mod 的本地 Material/TextureMap ID。封包时扫描 10 个当前 live patch TOC、405 个资源键，12 个私有资源的同类型 full ID、任意类型 full ID 和 high32 碰撞均为 0。

最终 11 个不同私有 TextureMap 的 base-level 总面积为：

```text
4,718,641 / 16,777,216 pixels
```

其中两张主图为 `2048x1024`，禁用 IlluminateData 使用 `4x4` 黑图，其余 shader ABI 小贴图也全部计入。该尺寸与 ID 都是 `case-specific`；可复用的是每个版本建立新 namespace、扫描当前部署资源，并按最终包内不同私有 TextureMap FileID 汇总严格总面积。

## 应加入新项目的硬门

### Authoring

- 记录每个 seam 的自然 donor-projected 完整权重误差，且发生在任何 post edit 之前。
- 每个 post-partition seam edit 都列出 seam、理由、共享骨、修改点数和 before/after 误差。
- 肩部若自然权重已一致，要求 `no_post_partition_shoulder_weight_edits=true`。
- 报告边界对象来源、点数、边数、组件数与闭环/开放声明，不能只报告总点数。

### Compiled Unit

- 身体每个 LOD 的实际 palette 是冻结 donor reference palette 子集，并覆盖候选实际使用骨。
- Torso 全部 LOD 包含两侧 shoulder；Arm 全部 LOD 包含对应 side shoulder。
- 每逻辑角色的 owner metadata、culling 和核心 bind signature 编译前后保持。
- 同角色多目标完整 Unit payload 逐字节相同。
- 头盔等例外角色显式声明 native-container policy，不能被身体 clone 规则误吞。

### Pose 与运行时

- 差分姿态 moving set 明确排除待证伪的替代骨。
- seam gap、邻接 edge ratio 和 moving-weight coverage 同时通过。
- 运行时失败候选保留截图、哈希、根因和缺失门禁；不能因为新版本通过而删除。
- 用户手动验收可提升明确范围的状态，但必须单独记录未观察的部署过程、未提供的姿态矩阵和未执行的自动化测试。

## 证据入口

- [项目 SOP](../../../SOURCE_REFERENCES.md#local-only)
- [v4 用户运行时验收记录](../../../SOURCE_REFERENCES.md#local-only)
- [v3 运行时拒绝报告](../../../SOURCE_REFERENCES.md#local-only)
- [v3 拒绝截图](../../../SOURCE_REFERENCES.md#local-only)
- [v4 clean donor contract](../../../SOURCE_REFERENCES.md#local-only)
- [v4 candidate report](../../../SOURCE_REFERENCES.md#local-only)
- [v4 shoulder pose audit](../../../SOURCE_REFERENCES.md#local-only)
- [v4 compile report](../../../SOURCE_REFERENCES.md#local-only)
- [v4 compiled palette/clone audit](../../../SOURCE_REFERENCES.md#local-only)
- [v4 package report](../../../SOURCE_REFERENCES.md#local-only)

完整 FileID、命名空间、三件套哈希、重建命令和历史候选状态以项目 SOP 为准。
