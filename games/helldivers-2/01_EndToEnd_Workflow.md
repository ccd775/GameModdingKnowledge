# 角色替换 Mod 端到端工作流

> 适用范围：完整角色或多装备槽角色替换。单一武器/小道具也可使用同一证据模型，但可缩小姿态与装备矩阵。
>
> 置信度：`project-proven`；whole-unit donor 行为为 `format-confirmed`（AQ Modified 2.4.3）。

## 总体原则

```text
证据采集 -> donor 合同复现 -> authoring -> 姿态门禁 -> 编译
       -> 序列化回读 -> 材质闭包 -> 合并 -> 确定性打包
       -> 明确授权后部署 -> 运行时验证 -> 接受或隔离
```

不要把模型处理、资源编译、材质修复和运行时判断混成一次不可解释的导出。每一阶段都应有输入哈希、输出哈希、机器报告和单一责任边界。

## Gate 0：基线、授权与环境

### 输入清单

- 用户源模型及所有外部贴图。
- 参考 Mod ZIP、manifest、所有 triplet。
- 可正常运行的 donor Mod 及其配套 authoring 源模型，若有。
- 当前游戏安装、版本、目标装备槽和替换对象。
- 用户对破坏性模型修改、游戏部署和启动验证的授权范围。

### 必做动作

1. 只读计算所有输入 SHA-256、大小、时间戳。
2. 锁定 Blender、AQ、SDK、FileDiver、DDS 工具的版本和哈希。
3. 创建项目目录和 `SOP.md`；从 [模板](templates/Project-SOP.template.md) 开始。
4. 枚举游戏 `data` 中目标 archive 的既有 patch index，但不写入。
5. 将状态设为 `inventoried`；未做的事情明确标为未做。

### 拒绝条件

- 参考 ZIP 有路径穿越、CRC 错误或不完整 triplet。
- 关键输入在审计过程中改变。
- 工具版本不明，或当前插件无法只读解析参考资源。
- 目标装备槽/FileID 仍靠猜测。

## Gate 1：参考、源模型和目标合同

### 参考 Mod 审计

先建立 reference identity lock：精确目录、authoring Blend、编译 triplet、原始角色身份、文件大小和 SHA-256 必须同时匹配。目录昵称、相似截图、旧任务记忆或另一个同名案例都不能作为参考。若用户纠正参考，旧参考产生的几何、阈值、报告和派生候选立即降为历史拒绝证据，不得继续影响活动构建。

建立以下映射表：

```text
manifest option
  -> archive id / patch triplet
  -> resource type and FileID
  -> equipment slot
  -> visible or suppression role
  -> Slim / Stocky / shared
  -> LOD and material sections
```

必须覆盖所有 manifest 选项。只编译可见身体而遗漏隐藏叠加槽，会让参考 Mod 的原几何重新覆盖或与新模型叠加。

### 源模型审计

至少记录：

- 每个 mesh 的顶点/面/三角形数、拓扑摘要、basis 摘要、shape key 数，以及保存中的全部非零 `对象 -> key -> value`。
- 骨架对象、骨数、实际承载权重的骨、最大 influences、未加权点。
- UV 层、材质槽、贴图、alpha 分布、色彩空间、打包图片。
- object matrix、parent inverse、modifier 和坐标系。
- 退化三角形、非有限数据、零面积 UV、重复材质。

若目标不承载 shape key，先在内存中预计算保存状态的 current mix，再只应用 shape-key mix。该步骤必须早于 split、法线、面遍历和 rest-to-bind；烘焙后证明坐标吻合且 topology、UV、weights、material index 与 face ownership 不变。不要通过 evaluated dependency graph 应用完整网格，以免活动 Armature Modifier 被二次烘焙。

### donor 证明

不要直接问“怎样把角色塞进 HD2 骨架”，先问“已运行 donor 的 authoring 输入怎样变成它的成品 Unit”。需要建立：

- authoring vertex/triangle 与编译后 RawMesh 的对应关系。
- 每个对象/material 的局部 palette 映射。
- mesh-local、armature、world 三个空间之间的矩阵关系。
- donor TransformInfo、BoneInfo、inverse bind、材质 section 的来源。
- 游戏装备槽实际使用的 Unit ID 与 archive 映射。

如果 donor 源与成品无法对应，最多把它当结构线索，不能当可写回模板。

## Gate 2：authoring 与模型处理

### 先冻结不变量

每个候选必须声明：

- 可以改变的对象、顶点、权重行、骨、材质 ID、纹理或 draw。
- 必须逐位不变的几何、UV、拓扑、材质、rest、非目标 Unit。
- 本次候选要回答的唯一问题。

例如“修肩缝”不授权调整头部高度、腹部权重、腿部几何或材质。

### 几何处理

- 默认保留源角色比例。
- 可接受一个有证据的全局刚性/等比变换，以及由源关节语义到目标 bind 的逐 influence rest pose 转换。
- 禁止按 HD2 原版骨长逐段缩放手臂、腹部、大腿或脚。
- object matrix 应应用到顶点并归一为 identity；确认写入的是 donor mesh-local 坐标。
- 对需要拆分的材质/装备槽保持 topology、UV 和顶点语义可追溯。
- 删除衣物使用精确对象/连通片/源面 manifest，同时声明 preserve set；禁止按共享材质、空间邻近或模糊名称扩大删除范围。
- 目标不支持 morph 时，将确认的外观烘入 Basis，再冻结几何摘要。

### 骨架与权重

- 使用 donor Unit 的局部 palette，不以全局骨名顺序猜测。
- 每顶点 influences 不超过目标限制，New_SR24/O44 已证实为 4。
- 权重归一，无未绑定点，无明显错侧骨。
- 连续身体表面与离散附件分开处理；附件不能被最近表面迁移随意吞入肩/胯骨。
- 修改 rest 必须重算对应 Unit 的 inverse bind，并证明 neutral identity 和外部驱动语义。
- 显式证明源骨段纵轴与目标 `TransformInfo` 链轴的有符号对应。若二者不同，先构造 semantic basis 或 parent-child shortest-arc；不能直接把两个骨矩阵相乘并假定 bone roll 同义。
- 对肩、肘、腕和腿脚逐段检查 endpoint closure；Hand/Foot 等混合接口应继承父段线性变换并在目标 pivot 重锚，除非有更强的语义 frame 证据。
- 肩部另行声明 source/target 语义骨基数。many-to-one 时所有 Shoulder/UpperArm 权重投影到同一目标语义，以真实 UpperArm 链为锚；endpoint closure 单项不能替代 seam、完整 Unit bind 和差分姿态。
- 从 face ownership 冻结肩、腰髋的权威 seam 点/边集合；闭环或开放拓扑以源/Ref 为准，两侧位置与完整语义权重行必须一致。
- 在任何 seam 权重编辑前，分别通过预定 final lineage 投影两侧源权重并锁定自然误差。自然权重已一致时禁止 blanket override 和固定过渡圈；自然误差很大时先修 owner/palette/projection。每个接口独立声明 post edit，不能使用全身开关。

### UV 与材质准备

- UV0、UV1、UV2 各自验证语义，不用“复制三份 UV”替代。
- 材质槽数量和 section 数不得超过目标 LOD 合同。
- 真正需要镂空才使用 AlphaClip；实际 alpha 接近 1 的浅透明可按 opaque 处理。
- 本地材质和纹理在编译前规划私有 ID namespace。
- 若项目限制所有贴图合计面积，按包内每个不同私有 TextureMap FileID 累加 base-level `width * height`；语义小计不能各自获得一份总预算。

### Gate 2 输出

- 冻结 authoring `.blend`。
- 机器可读 build report 和输入/输出 SHA-256。
- neutral/front/side/three-quarter 渲染。
- 多姿态 edge/seam/component 报告。
- 明确的候选 delta 及非目标逐位一致证明。

## Gate 3：编译、合并与离线验证

### 可见 Unit 编译

1. 预检 authoring 属性、palette、材质 section 和 donor/target ID。
2. 按 whole-unit donor 合同编译所有可见 Unit。
3. 立即用独立路径回读序列化 Unit。
4. 检查每个 LOD 的 geometry、weights、BoneInfo、inverse bind、draw ranges。

若多个目标应共享完全相同的绑定，按逻辑角色选择一个完整 carrier：每角色只编译一次，再仅改 FileID 克隆完整 Unit。锁定 `TransformInfo`、BoneInfo/MeshInfo/inverse-bind 同源性、culling 与核心 bone-bind，并要求同角色目标完整 payload 逐字节相同。每个 LOD 使用 owner RawMesh 自己的实际索引，不硬编码常见槽位。不得把同一 RawMesh 无证据地注入多个 target-native bind。

### 完整覆盖

将可见 Unit 与经过冻结验证的 suppression/hidden Unit 合并，覆盖 manifest 图中的所有目标。要求：

- 可见 payload 与可见编译源一致。
- suppression payload 与冻结源一致。
- 非目标资源不变。
- GPU/stream 区间不重叠且边界有效。
- suppression 修改可渲染几何，而不是仅替换成透明/玻璃材质；正 LOD 和 culling LOD 分开回读。
- 头、身体和附件按实际消费者槽位恰好出现一次；可见集合与 suppression 集合互斥。

### 材质闭包

按顺序处理：

1. 基础 child materials 与 textures。
2. 头发/透明件或 opaque rewrite。
3. 面部独立材质。
4. 私有 namespace 迁移。
5. 最终模型中的 material ID rewrite。
6. emission、sRGB、alpha 和引用闭包验证。

每个阶段使用新候选路径；不要在同一个文件上原地反复改写。发布 patch index 由最终部署模式决定：默认新槽使用新 index；精确旧版替换可保留同 index，但必须绑定旧三件套哈希并禁止共存。

### 最终合并

- AQ/Blender 写 archive 的任务串行运行。
- Unit 做 load-only 语义验证；不要依赖 `Unit.Save()` 的字节身份。
- Material/TextureMap 可在适用时做 load-save。
- 最终 archive 做完整 triplet roundtrip、资源计数、引用闭包和 payload provenance。

## Gate 3.5：确定性发布

1. 最终 triplet 三份文件各自计算 SHA-256。
2. 生成恰好三个 stored 成员的 ZIP，固定顺序和时间戳。
3. 验证 CRC、大小、成员名和成员哈希。
4. 在隔离新路径重复打包。
5. 比较两个 ZIP 大小、SHA-256 和逐字节内容。
6. 将正式包和报告放入 `Output/`；失败/旧包移入 `Work/candidates/...do_not_use/`。

状态只能写 `packaged_and_offline_verified`。

## Gate 4：部署和运行时验证

### 授权检查

必须分别确认：

- 是否允许写游戏 `data`。
- 是否允许启动 Steam。
- 是否允许启动游戏并进行输入控制。

用户只说“打包”不等于允许部署；只说“部署”不等于允许启动。

### 安全部署

- 游戏进程未运行。
- 目标目录名称和父目录严格匹配预期安装。
- 先冻结互斥模式：新槽安装要求 patch index 未占用且高于现有最大值、三份目标均不存在；精确旧版替换要求 live 三件套逐份匹配已诊断 lineage、只从碰撞扫描排除该 triplet、旧新版不共存。
- 临时拷贝 fsync 后校验哈希，再原子改名。
- replacement 优先通过 Mod Manager 禁用/卸载旧版后安装；直接替换必须另有明确授权和可恢复旧三件套。
- 若中途失败，只回滚/删除本次创建且哈希匹配的精确文件。

### 运行时矩阵

至少观察：

| 维度 | 检查 |
| --- | --- |
| 场景 | 军械库、任务内 |
| 体型 | Slim、Stocky |
| 视角 | 正、背、侧、三分之四、近景 |
| LOD | 近、中、远；切换无跳变 |
| 动画 | 待机、跑动、蹲伏、举臂、瞄准、手指动作 |
| 接口 | 原版头盔、其他自定义头盔/装备 |
| 材质状态 | clean 及项目声明支持的 dirt/blood/gunk/acid |

每张截图记录时间、已部署 triplet 哈希、装备/体型、姿势和观察结论。

### 接受与拒绝

- 只有完整矩阵达到项目标准才写 `runtime_validated`。
- 用户截图发现问题时立即将当前包标记 `rejected`，不因离线报告全绿而争辩。
- 修复从最近接受的基线分叉；不要在被拒绝候选上继续叠加未知改动。

## 迭代纪律

一次迭代应包含：

```text
problem screenshot/hash
-> falsifiable root-cause hypothesis
-> smallest declared delta
-> authoring delta audit
-> standard + targeted pose gates
-> compiled postflight
-> material/integration closure
-> deterministic package
-> status update and recovery command
```

如果无法说明“这次到底改了哪几行权重、哪几个 material ID 或哪段 GPU payload”，说明改动范围仍过大，不应进入最终合并。
