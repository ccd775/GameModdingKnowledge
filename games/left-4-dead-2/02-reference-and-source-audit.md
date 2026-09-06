# 参考模型与源文件审计

## 1. 先建立输入锁

对以下文件记录绝对路径、大小、修改时间和 SHA-256：

- 用户提供的 `.blend`、`.vrm`、`.fbx` 与原贴图；
- 所有参考 `.vpk`、解包或反编译结果；
- 原生目标 survivor 的 MDL/VVD/VTX/PHY 和 VMT；
- 工具二进制与插件包。

工具锁不能只覆盖可执行文件。按 required role 清单记录 Blender、Blender Source Tools、SourceIO、Crowbar、StudioMDL、VTEX、VPK，以及参与正式 gate 的项目脚本/版本。`source-lock` 中“已列 14 项全部通过”不等于依赖清单完整；验证器还要检查 required roles 没有漏项，尤其是从其他项目目录借用的解析库或插件。

后续所有工作使用派生副本。每个会改变模型、贴图或编译结果的阶段前验证锁，正式发布前再验证一次；发现变化就停止并重新审计来源。final manifest 应链接本轮 source-lock verification 的路径与哈希。

工作区换盘符或迁移主机时，`path missing` 与 `hash changed` 要分开处理。只迁移确认属于同一工作区的路径字段，随后对每一项重新验证 bytes/SHA-256；工具仍在旧盘时不要全局替换盘符。迁移记录应进入 source-lock verification，不能通过删除失败项来“恢复通过”。

## 2. 审计参考 Mod 的真实身份

不要用文件名判断参考 Mod 替换的是谁。至少检查：

- VPK 内的目标模型路径；
- MDL 内部 `$modelname` 或等价元数据；
- 骨骼集合、include model、attachments、hitboxes；
- 材质和贴图路径；
- 是否只有材质而没有世界模型；
- MDL 版本能否被当前 Crowbar/SourceIO 正确解析。

曾遇到路径名写 Rochelle、内部遗留 Zoey 文本的模型；也遇到材质参考包被误当作完整世界模型。若身份不清，禁止复制 QC。

## 3. 原生目标契约

从当前挂载顺序下实际生效的目标 survivor 提取：

- 世界模型固定路径；
- 第一人称手臂固定路径；
- ValveBiped 公共骨骼与父子关系；
- attachments；
- hitboxes、bbox、cbox、surfaceprop；
- bodygroups、skin families、LOD；
- `$includemodel` 顺序；
- sequence 声明，包括重复项；
- flex controller、眼球和嘴部接口；
- 物理模型是否存在及其 checksum 关系。

输出机器可读审计报告。它定义“游戏接口”，不是要求把自定义角色拉伸成原版身体。

### 动画合同必须另行审计

原生输出槽位不是动漫角色动画基准的自动来源。另建 animation contract，至少记录：

- primary animation family 与选择证据；
- corrective animation rest 的路径、来源和 SHA-256；优先锁定 compiled native animation MDL/ANI，反编译 reference SMD 作为交叉证据；
- `$declaresequence` 的有序行、总数、unique 数和重复明细；
- `$includemodel` 的路径、大小写、顺序，以及哪些是 main、哪些是 fallback；
- `reference`/`proportions` 的本地 sequence 结构、flags 和 frame count；
- 自定义 rest skeleton 的独立来源；
- ground offset 的测量来源和唯一 owner。

文件名包含 Louis/Zoey/Rochelle，或 QC 同时出现 TeenAngst/Producer/Biker，都不能单独证明主动画源。必须结合 include 顺序、sequence 解析、corrective translation 来源和成功运行证据判断。

## 4. Blend 审计

审计脚本应只读打开 Blend，并输出：

- Blender 版本、场景和单位；
- armature 名、骨数、层级、约束、对象与 data 矩阵；
- mesh 名、顶点/面数量、材质槽、UV 层；
- 所有 vertex groups 和最大权重影响数；
- shape key 名、相对关系、实际 delta 顶点数与最大位移；
- 材质节点、base/normal/emission/alpha 连接关系；
- 缺失外部文件和 packed data 状态；
- bounds、最低点和关键身体标记。

仅看到 shape key 名称不够。相同名称可能出现在多个 mesh 上，但只有一个 mesh 有非零 delta。

## 5. VRM 审计

VRM 中的 spring bone 数据可用于理解作者意图，但不能直接等价为 Source `$jigglebone`。记录：

- spring group 和 joint 顺序；
- center 节点；
- stiffness、drag、gravity power/direction、hit radius；
- collider group、节点、offset 和 radius；
- humanoid bone 映射；
- meta 与 exporter 版本。

之后把这些数据转换为经过稳定性限制的 Source profile，并明确单位、时间步和重力方向的假设。

VRM humanoid 条目即使 schema 上 `valid`，也不证明语义正确。必须检查节点名、父链、
左右侧别、空间位置、是否属于 skin joint，以及眼/颌/手足等关键映射是否落在合理身体
区域。Nyako 源曾把 `leftEye` 指到 `Hair_tail_L`、`rightEye` 指到 `Ahoge`；若盲信
humanoid map，会把头发动态链误当面部控制。损坏映射只保留为审计证据，实际 rig map
应由最终 Blend、网格权重和目标 ABI 重新确认。

## 6. 贴图与材质审计

为每个 Blender material 建表：

| 字段 | 说明 |
| --- | --- |
| 材质名 | 最终 SMD/VMT 应使用稳定 ASCII 名 |
| Base Color | 源图、色彩空间、alpha 用途 |
| Normal | 源图、绿色通道方向、黑色无定义像素 |
| Emission | 是否真实连接、是颜色还是强度 mask |
| Alpha | translucent、alphatest 或未使用 |
| UV | 使用哪个 UV 层、是否需要重排 |
| 目标 VMT | 预期 shader 与参数族 |

不要因为多个材质共用 atlas 就给它们相同 emission。必须用实际 UV 三角形覆盖范围验证某个材质是否采样到发光区域。

## 7. 参考反编译的边界

- Crowbar 可用于受支持的 L4D2 v48/v49 模型，但某些社区模型版本可能无法完整反编译。
- 反编译失败不是许可去猜 QC。改用 SourceIO、二进制结构审计、VPK 内容、同角色其他版本和运行表现交叉验证。
- 参考 Mod 的二进制、QC、材质和纹理只能作为证据，不能覆盖用户源模型的角色形象。
- 对每个 compiled target 分别记录 `abi_source` 与 `visible_geometry_source`。第一人称参考 arms 即使能提供完整 nodes/QC/animation，也不能据此成为皮肤、袖子、UV、法线或材质的来源。
- 参考 companion 必须保存 SHA-256、材质 token 和 namespace，作为最终候选的负面门；接口兼容报告只能证明 ABI，不是视觉血缘报告。

## 8. 审计阶段退出门槛

进入修改前必须能回答：

- 目标 survivor 的世界模型、手臂和 HUD 路径是什么？
- 原始角色的权威几何、骨架、形态键和贴图分别来自哪里？
- 哪个参考负责接口，哪个参考负责比例/附件？
- 世界模型与第一人称手臂各自的 ABI、可见几何、选面、权重指导和材质来源是什么？
- output slot、slot interface、custom rest、primary animation、corrective baseline 和 sequence contract 分别来自哪里？
- 所有输入和工具是否被哈希锁定？
- source-lock 的 required role 清单是否完整，而不只是已列项全部通过？
- 单位、对象矩阵、shape key、发光和透明意图是否已被机器报告证明？
- 当前有哪些结论仍只是待实机验证假设？
