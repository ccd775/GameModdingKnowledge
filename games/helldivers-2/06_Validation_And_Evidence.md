# 验证门禁与证据管理

> 核心结论：离线自洽、编译成功、ArchiveQT 往返、确定性打包和游戏运行正确是五个不同命题，必须分别证明。

## 证据层级

从弱到强：

1. 工具正常退出。
2. authoring 结构/静态检查通过。
3. Blender 内部姿态与差分检查通过。
4. 编译后 Unit 的语义/provenance 检查通过。
5. 最终 archive 的引用闭包和 roundtrip 通过。
6. 两次独立构建逐字节一致。
7. 绑定实际部署哈希的运行时矩阵通过。

后一级不会自动包含前一级，且运行时可以推翻所有离线推断。New_SR24 曾出现多次 52/52、176/176 离线通过后仍被截图否决，这不是例外，而是门禁设计必须面对的现实。

## 报告最低字段

每个机器报告至少包含：

```json
{
  "$schema": "project-stage/v1",
  "accepted": false,
  "status": "diagnostic|accepted|rejected|superseded",
  "created_at": "ISO-8601",
  "tool_versions": {},
  "inputs": [],
  "outputs": [],
  "scope": {
    "allowed_changes": [],
    "frozen_domains": []
  },
  "checks": {},
  "metrics": {},
  "known_limits": [],
  "evidence": []
}
```

`accepted` 应由所有硬门计算，不允许手工改成 true。失败后修改审计器，应输出 `r2` 新报告并保留 `r1`。

## 输入与 provenance

所有重要输入记录：

- resolve 后绝对路径。
- 文件大小和 SHA-256。
- 对目录型输入记录 manifest/文件列表摘要。
- 参考必须记录精确目录、authoring Blend、compiled triplet、原始角色身份及各自哈希；目录昵称和任务记忆不构成 provenance。
- 工具/脚本版本和 SHA-256。
- before/after 哈希，证明只读输入未改变。

上游报告不仅要 `accepted: true`，还要检查报告是否绑定当前输入哈希。路径相同但内容已变，不可继续。

## Authoring 静态门禁

### 场景卫生

- 目标对象存在且名称唯一。
- 无意外隐藏/禁用对象。
- object transform 符合合同。
- 无未声明 modifier、constraint、shape key 状态。
- 若保存中的非零 shape key 是权威外观，报告完整 `对象 -> key -> value`、烘焙顺序、current-mix 坐标误差，以及 topology/UV/weights/material-index/face-ownership 不变证明。
- 纹理来源存在且哈希匹配。

### 几何

- 顶点、三角形、indices、拓扑摘要。
- 非有限坐标/UV/权重为 0。
- 退化面已处理或有显式例外。
- bounds、中心、轴向和尺度合理。
- 与源几何的边长/局部体积在声明变换后保持。
- 修改域外顶点逐 float/位一致。

### 权重

- 无未加权点。
- 权重和误差在容差内。
- influence 数不超过目标限制。
- 局部 palette 全部可解析。
- 错侧骨、远距离手指骨和孤立微权重被审计。
- Slim/Stocky 和 LOD 副本的预期一致性得到证明。

### UV/材质

- 每个 loop 的 UV 数量和有限性。
- UV0/UV1/UV2 语义验证。
- 从当前 parent shader 记录 BaseData、动态 tiler、DecalSheet 各自消费的 Unit UV component；验证被绑定贴图的 sampler coordinate 实际可达，不只检查资源引用。
- material slot/section 数量不超过目标。
- 透明面和 opaque 面归类来自实际 alpha 数据。

## 姿态变形门禁

### 标准姿态集

推荐起点：

- neutral。
- arms up / shoulder abduction。
- left/right hand-to-head。
- crouch。
- asymmetric locomotion。
- 可组合装备接口姿态。
- 双手/单手 finger curl。

### 为什么需要差分姿势

若一批顶点权重从骨 A 改到骨 B，neutral 可能完全一致；只有 A 和 B 相对运动时才会暴露断层。因此每次迁移都要构造最大化 `A^-1 * B` 差异的姿势，并对目标连通片单独检查。

### 指标

- 边长比：`posed_length / neutral_length`。
- p01/p99：观察整体分布，避免少数数值掩盖系统性拉伸。
- absolute min/max：抓单条极端边。
- seam pair distance：肩、颈、腰、髋等跨对象接口。
- bounds diagonal ratio、object diagonal ratio、中心漂移。
- 左右跨侧比例和错侧 winner bone。
- 连通片级 winner bone/骨质量分布。
- 候选相对冻结基线的 posed vertex delta。
- source segment 经 retarget 后到 target chain 的 signed axis cosine；禁止使用绝对值。
- parent segment 的 endpoint closure、末端继承接口的 linear/pivot 连续性。
- shoulder/elbow/hand 与 distal leg 的 full-3D mirror、target-local transverse 符号和 world fore/aft。

New_SR24 的通用姿态脚本使用过以下默认起点：权重和误差 `1e-4`、最大 4 influences、edge p01/p99 `0.35..3.0`、absolute `0.05..12.0`。这些数值必须通过源/donor 分布校准，不能原样宣布为所有模型的标准。

### 输出渲染

至少渲染正面、侧面或三分之四；尺寸和相机固定。渲染用于快速视觉比较，但不替代数值门禁，也不替代游戏。

## 局部专项门禁

### 肩部

- **Reference lock**：精确 Ref Blend/triplet/source identity 与输入哈希匹配；旧参考派生报告不得进入活动 lineage。
- **Silhouette**：与 source current mix/同角色 Ref 比较肩帽、肩胛、腋下和近端上臂；`local_shape_edits` 必须为空或有逐点授权。不能以“肩峰更明显”为理由接受圆肩/健硕肩。
- **Semantic cardinality**：声明 source Shoulder/UpperArm 与 final-lineage clavicle/shoulder 的一对一或 many-to-one 关系；映射必须由 Ref 与全部 carrier/target LOD palette 证明。
- **Natural projection before edits**：接口两侧先按各自 final lineage 独立投影，并在任何 post edit 前记录完整权重行误差。大误差是 palette/owner/projection 报警；after-override 的 0 不能覆盖它。自然权重已一致时要求无 blanket shoulder override、无人工固定过渡圈。
- **Partition**：先转到阈值所属空间再分面；每个源面恰好归属一次。从 neutral face ownership 冻结权威 seam 点/边集合。Ref 证明为单闭环时才强制闭环；开放/多组件衣物允许开链，但两侧必须覆盖声明集合、坐标与完整语义权重行一致。
- **Accessory tracer**：检查上背 neck-to-axilla 绳路没有跨过大臂；Torso 附件未被 arm-yoke 规则吞入。
- **Shoulder frame**：many-to-one 时以 source UpperArm -> LowerArm 实际段为锚；保留已证明 carrier roll，只附加闭合 target shoulder -> elbow 所需的最小 swing。
- **Signed bind axis**：source longitudinal axis 映到 target parent-child chain 的正方向；检查 target-local axial/transverse 分量，不能只看 radial RMS。endpoint closure 单独通过不构成肩部验收。
- **Bilateral motion**：shoulder/elbow/hand 做 full-3D mirror；左右 world fore/aft 同向。右臂前折、左臂后折是轴向合同失败，不是普通权重不平滑。
- **Elbow/wrist**：验证 shortest-arc segment closure、左右 roll 行为、LowerArm/Hand linear 与 wrist pivot 连续。
- **Pose matrix**：neutral、idle、salute、arm-up、左右 hand-to-head、asymmetric locomotion；正面、背面和两侧近景。
- **Serialized repeat**：从最终 Unit 的 TransformInfo/BoneInfo/weights 重跑，不能使用源 armature 或 builder 内存矩阵代替。
- **Dynamic seam**：固定 neutral 对应集合后施加 shoulder/elbow 差分姿态；不得在 posed 状态重新最近点配对。moving set 必须显式排除待证伪的替代骨，并报告实际 moving-weight coverage；同时测 seam gap 与肢体内部邻接 edge ratio。开放边界同样需要该门禁。

通用方法与案例阈值见 [Karin Nyako RE2310 案例](case-studies/Karin_Nyako_RE2310.md)、[DR03 跨 profile 肩缝案例](case-studies/Karin_DR03_CM10_EX00.md)、[Umbrella 肩骨折叠案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)和 [SSF 自然肩缝案例](case-studies/Karin_SSF_FS37_SC15.md)。

### 腹部/腰髋

- 分别驱动 chest、spine1、spine2、hips 的相对运动。
- 对环状壳、内衬、腰带、短裤、身体皮肤按连通片检查。
- 前后视角都要测；背部断层可能被尾巴/长发遮挡。
- `面存在` 不等于动画下连续。
- 声明相邻 ownership 图。若设计为 `torso -> hip -> leg`，则 torso/hip、hip/left leg、hip/right leg 分别冻结 seam；任何 direct torso/leg bypass 都硬失败。
- 每条接口的共享语义必须来自双方 final-lineage palette，位置与完整权重行相同；具体使用 spine、hips 或 thigh 由当前 carrier 推导。

### 手指

- 左右各 15 根语义骨（项目/骨架可能不同，需实际枚举）。
- 每根骨在 prepared/external pose 中有非零运动。
- 过渡环权重局部、枢轴距离合理。
- 单手 curl、双手 curl、抬臂 + curl 交叉姿态。
- p99 与 absolute edge ratio；检查附件误带 finger weight。

### 头盔接口

- 编译后 Torso 顶点最高点、neck bridge、head anchor。
- 原版头盔与其他自定义头部。
- 不能通过拉长可见脖子来弥补整体 body/head interface 偏低。
- 同一 head package 覆盖多个目标时，比较完整 Helmet Unit 的 MeshInfo/TransformInfo/BoneInfo/inverse bind；刚性 `head=1.0` 本身不能排除巨大悬空或缩放错误。

### 腿脚与保存形态

- `thigh -> knee -> foot -> ball` 每段 signed chain-axis、endpoint closure、左右 palette 与 full-3D mirror。
- Foot/Ball 的 linear 和共享 pivot 连续；仅 neutral/bounds 正常不足以排除走路时双脚交叉。
- 报告保存 shape-key mix 已在法线、分件和 retarget 前烘焙；鞋面近景确认脚趾不越过鞋底/鞋帮轮廓。

## 编译后 Unit 门禁

最终序列化数据重新解析并检查：

- Unit 集合、类型、版本和 FileID。
- LOD/RawMesh 数量、stride、vertices/indices。
- TransformInfo、BoneInfo、MeshInfo transform、inverse bind provenance。
- local palette 和权重行。
- material sections、draw start/count。
- GPU/stream offset/size/bounds。
- 修改目标与冻结目标的精确差分。
- 可见角色与 suppression target 集合互斥；每个源面/头部对象恰好由实际消费者槽位拥有一次。
- 每个正 render LOD 的可见/微型几何 bounds；culling LOD 独立冻结。
- suppression 正 draw 不使用透明/玻璃材质作为隐藏证据；若使用微型占位，位置流必须与原生可见几何不同且低于项目校准门限。
- Helmet role 非空、palette 与目标槽兼容；Torso 不重复持有完整 head package。
- 可见角色每个正 LOD 非空并使用其正式材质；远 LOD 不得回退到 suppression glass 或原生叠加几何。
- carrier-clone 路线中，每逻辑角色 compile count 必须为 1；记录 carrier ID/输入 triplet 哈希、clone target 集合，并证明同角色目标完整 payload 逐字节相同。
- 编译前后锁定 carrier `TransformInfo` 与核心 bone-bind（NumBones、RealIndices、inverse bind）；AQ 因材质 section 产生的 remap 重建只能落入显式允许列表。

不要只比较 loader-normalized ShortID 与源字段的原始字节；先理解 AQ 会规范化哪些字段。错误的序列化假设应修正审计器，而不是修改正确候选来迎合错误门禁。

## 材质与纹理门禁

- DDS 格式、尺寸、mip、sRGB 标志。
- 按 BaseColor、Normal/NAR、Data/Control、Emission、Material LUT 等语义分别累加 base-level `width * height`，与项目预算比较。
- 解码后的平均/分位 luma 和关键 ROI。
- alpha min/max/直方图与裁切阈值。
- 对逻辑不透明 BC7，解码后的 alpha min/max 必须满足项目不透明硬门；不能只检查源 PNG。
- normal/NAR 的中性值与通道语义。
- emission color、strength 和遮罩乘积。
- child/parent/material/texture 引用闭包。
- full 64-bit、高 32 位/ShortID 冲突。
- model 实际引用次数和未引用资源。
- Armor LUT 路线分别记录 parent/child ABI、IdMasksArray + static LUT、Unit UV component 和 runtime `Piece.MaterialLut` coverage map。
- runtime LUT same-ID 覆盖必须绑定当前 armor-set 快照、全局引用计数、原生目标 DDS 与完整反提取哈希。
- Advanced -> Armor LUT 后增加 clean-color 门禁：作者 atlas 的空间图案必须出现。若只有统一灰/银/金属响应，即使 LUT 可达、SDK roundtrip 通过，也应拒绝并检查 DecalSheet UV ABI。

DDS 元数据正确不代表像素正确；必须解码回 PNG/数组进行比较。

## Archive 与最终集成门禁

最终报告至少验证：

- 精确资源计数和类型集合。
- 每个资源 payload 对应指定上游。
- 无重复 ID、无区间重叠、offset/size 有效。
- 所有模型材质引用闭合。
- 私有 namespace 与 donor/当前安装资源隔离。
- 特殊 draw 合同逐 LOD 正确。
- AQ 可解析；整档 roundtrip 达到声明的身份标准。
- 输入和上游报告未改变。

对混合工具环境，区分“插件 UI 注册 ABI”和“资源序列化 ABI”。如果 Blender 当前注册的 AQ PropertyGroup 早于冻结 HD2SDK，`entry.Save()` 可能因缺少场景属性失败。此时不得伪造 UI 属性或把环境错误算作候选失败；可在冻结 SDK 上使用底层 `StingrayMaterial.Serialize` 做 main payload 直接往返，Texture 继续 `Load/Save`，Unit `Load` only，最后仍要求整个 StreamToc 三件套逐字节回写一致。报告必须明确采用的验证模式。

## 可复现性门禁

至少验证：

- 两个独立 final triplet（若构建可重跑）逐字节一致。
- 两个独立 ZIP 逐字节一致。
- package report 的 source/member contract 完全一致。
- 固定成员顺序、时间戳、mode、stored compression。
- 两次构建都没有写 game data，也没有启动游戏。

## 运行时证据

### 截图记录

每次反馈保留：

- 原始图片，不重编码。
- SHA-256。
- 已部署 triplet 的三个 SHA-256 和 patch index。
- 游戏版本、体型、装备组合、姿势、镜头。
- 用户观察和 Agent 的根因假设分开写。

### 结果解释

- 静态通过 + 运行时失败：候选失败，说明门禁缺失，而不是用户截图“例外”。
- 截图显示多个症状时，按最小责任域分解，不一次改全身。
- 同一截图无法区分材质/几何时，优先设计能排除某一假设的离线或下一张截图。
- 用户明确“验收通过”可以作为手动运行时接受证据，但必须锁定候选/package 身份与接受范围，并分开记录 Agent 未观察的部署过程、用户未提供的测试矩阵和未执行的自动化测试。该状态不能自动传给下一候选。

## 失败与隔离

失败资产应：

- 从 `Output/` 移出。
- 移到含原因的 `Work/candidates/...rejected_do_not_use/`。
- 保留原文件名、哈希、失败报告和截图关联。
- 在 SOP 和案例时间线标明 superseded 链。

不要删除失败记录。New_SR24 的多次 regression 正是依靠旧候选的逐位比较定位到错误的三行附件权重。
