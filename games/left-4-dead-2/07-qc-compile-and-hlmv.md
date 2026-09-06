# QC、StudioMDL 编译与 HLMV 预览

## 1. QC 是接口声明，不是参考文件复制品

QC 应从“原生目标契约 + 自定义角色报告”生成。至少显式管理：

- `$modelname` 与 `$cdmaterials`；
- `$body` / `$model`、bodygroups、skin families、LOD；
- reference SMD、VTA、flexdesc/controller/rules、eyeball 和 mouth；
- surfaceprop、contents、illumposition；
- bbox、cbox、hitboxes；
- attachments；
- procedural/VRD 与 `$jigglebone`；
- physics collision；
- `$includemodel` 顺序；
- `$declaresequence` 原始顺序和重复行；
- proportion delta animation/sequence。

参考 Mod 的 QC 只能提供实现线索。输出槽位接口来自当前 L4D2 原生资源；角色几何和 rest skeleton 来自用户源与同角色参考；主动画、corrective 和 sequence 合同必须单独选择。不要从 `$modelname` 或 survivor 文件名推断动画族。

## 2. 比例校正序列

成熟的动漫角色替换应保留角色 rest proportions，并通过 proportion animation 把所选动画基准适配过来。下面只是语义示意，不是可跨项目复制的 flags 模板：

```qc
$animation "a_proportions_corrective_animation" "anims/avatar_native_reference.smd" {
    fps 30
}

$animation "a_proportions" "anims/avatar_proportion_target.smd" {
    fps 30
    subtract "a_proportions_corrective_animation" 0
}

$sequence "proportions" { "a_proportions" <flags-from-locked-contract> }
```

名称可变，但语义必须明确：reference 是**与主动画族匹配**、要被减掉的基准，target 是角色 bind/地面校正后的目标。检查编译后 sequence flags、帧数、骨数和平移/旋转 delta。项目特定 pelvis 偏移只能由测量产生。

`delta`/`predelta`、`post`、`hidden` 和 `autoplay` 的组合不是“动漫模型固定写法”。例如 Karin_PT/Rochelle 的成功合同编译 flags 为 `1052`，而 Riptide/Louis 的成功合同为 `12` 且不 hidden。两者都可使用 Zoey/TeenAngst 主动画，却不能互抄 flags。准确分层见 [替换槽位、动画基准与 Zoey/TeenAngst](15-animation-basis-slot-and-zoey.md)。

## 3. Sequence 与 Include 保真

- 不对 `$declaresequence` 自动去重。
- 同名重复可能是原生接口的有意结果；记录总行数、unique 数和重复明细。
- `$includemodel` 的顺序会影响虚拟动画和 gesture 解析，必须按已锁定的成功动画/sequence 合同保留。
- 编译后比较 local animation、local sequence、virtual sequence 和最终总数。
- 不要把 include MDL 的 sequence 名称 union 当作 `$declaresequence` 来源；声明表还承载顺序、槽位和有意重复。

Karin 的具体行数和 include 顺序见案例文档，不能作为所有 survivor 的通用常量。

### 多 target 的共用与独有合同

当一个项目要覆盖多个 runtime model path 时，先分别审计各自原生 QC、collision、physics、attachment/hitbox/IK 和 companion family；每个 `$modelname` 必须单独 StudioMDL 编译并在自己的 MDL/VVD/VTX/PHY 内检查 checksum。若这些 target 应显示同一自定义角色，则另建跨 target 合同，比较共享可见 bind/proportion 的 canonical reference、projected Pelvis、core/full projected reference 和 root delta。不能因为可见网格相同，就复制第一目标的 QC/PHY 或让第二目标沿用不同坐标系的 canonical。

## 4. 编译前门槛

在运行 StudioMDL 前确认：

- source lock 通过；
- 所有 SMD/VTA/QCI/QC 路径存在且位于项目内；
- SMD 骨、权重、材质和 bounds 审计通过；
- output slot、primary animation basis、corrective source/hash、rest skeleton、sequence contract 和 ground owner 已分别记录；
- VTA frame 0 与 SMD 匹配；
- 材质闭包已生成到隔离 game root；
- physics 与视觉骨命名关系已审计；
- 输出目录没有来自不同候选的 MDL companion 残留；
- QC `$modelname` 对正式构建或 preview alias 是明确的。

## 5. StudioMDL 调用

用目标 L4D2 安装中的 `studiomdl.exe`，并显式指定隔离游戏根：

```powershell
& $StudioMdlPath -game $CompileSandbox $QcPath
```

推荐用 wrapper 脚本额外完成：

- 验证工具哈希；
- 捕获 stdout、stderr、exit code、开始/结束时间；
- 记录完整命令和 cwd；
- 解析 warning/error；
- 枚举本轮生成文件并计算 SHA-256；
- 拒绝把旧输出误认为本轮产物。

所有 warning 先视为失败，再按证据分类。不要仅凭 exit code 0 放行。

## 6. 编译后结构审计

至少检查：

- MDL 版本符合 L4D2 目标；
- MDL/VVD/VTX/PHY checksum 互相一致；
- `$modelname`、surfaceprop、contents、flags；
- 骨数、名称、父级、flags、procedural 类型；
- bind pose 骨端点与预期 skeleton 的误差；
- 最大顶点权重数；
- bodyparts、models、mesh、材质名、skin families、LOD；
- 编译后 VVD LOD0 总顶点不超过项目预算；公共工程目标为 `<=60,000`，拒绝 `>=65,535`；
- 逐 bodypart/model/mesh/strip-group 验证 VTX `original_mesh_vertex_index` 的 mesh-local、model-local 和 VVD global 范围，并要求每个 model 顶点覆盖完整；
- attachments、hitboxes、bbox/cbox；
- flex controllers/rules 和眼球接口；
- local/virtual animation 与 sequence；
- include model 路径与顺序；
- physics solid/convex、骨引用与 checksum。
- 设计为共享的 world/light 几何使用规范化 VVD/VTX/权重/VTX mapping 合同比较；不要要求含不同 sequence/PHY 的 MDL 原始哈希相同。
- world/light 共享 procedural 时，逐字段比较 compiled flags、length、mass、pitch/yaw/along stiffness+damping 和 angle，而不只比较 JiggleRule 数量。

可用 SourceIO 做独立解析，避免验证器与构建器共享同一错误假设。但“SourceIO 能导入/统计”不是 raw binary ABI 门：骨序/父级/rest/flags、procedural payload、sequence、VVD influence、VTX original ID 和 checksum/PHY 仍需专用二进制验证器读取。

StudioMDL return 0、无 warning、companion checksum 一致和最大三权重都不能代替 VTX 映射门禁。Riptide 的 153,854-vertex 世界模型满足这些表面条件，却因坏 VTX 在 `studiorender.dll` 确定性加载崩溃；修复候选为 59,248 vertices 且映射完整。详见 [Riptide Louis 案例](16-riptide-louis-case-study.md)。

## 7. 唯一 Preview Alias

世界模型最终路径通常与原版相同。HLMV 通过虚拟文件系统打开同名模型时，可能加载更新/DLC/base 中的原版而不是沙盒构建。

建立第二份 preview QC：

- 除 `$modelname` 外与正式 QC 字节级一致或由同一生成器生成；
- 使用不会与游戏资源冲突的唯一相对路径；
- 在报告中比较两份 QC 的规范化差异，只允许 modelname；
- 编译到隔离 game root；
- HLMV 打开唯一 alias。

HLMV 窗口标题、路径或“看起来像角色”都不单独证明血缘。再用 MDL/VVD/VTX 哈希与正式输入对应。

preview 只属于检查环境：正式/preview QC 的规范化差异必须只有唯一 `$modelname`，且 preview companion、compile-only animation sidecar、DX80/SW VTX、QC/SMD 和参考资产都必须被 release allowlist 拒绝。

## 8. HLMV 检查矩阵

| 视图/状态 | 重点 |
| --- | --- |
| bind front/side/back | 比例、头肩、四肢、鞋、材质、bounds |
| idle | 地面、呼吸造成的拉伸、附件根部 |
| walk/run | 步幅、脚滑/陷地、肩胯、衣摆 |
| crouch/injured | 极端弯曲、穿模、hitbox |
| flex controllers | 眼睑、嘴、极端组合、VTA 爆点 |
| physics overlay | hull 对齐、骨跟随、单位 |
| LOD | 切换时轮廓、材质和附件是否跳变 |

保存两类图：

1. 原始截图，含完整 HLMV 标题、模型名和 sequence。
2. 用于快速审核的 contact sheet，注明源截图文件名。

对长序列，不要只截 bind 或任选一帧。按当前项目定义的归一化进度覆盖开头、中间、结尾和已知高风险姿势；每个 runtime variant 单独执行同一矩阵。所有基础帧都记录 sequence、frame 和 Ground 状态，至少一个诊断帧额外记录 Ground + Origin Axis + Bones。多 HLMV 窗口/自动化场景必须验证目标窗口身份，并在操作后回读 sequence 和 frame 控件，而不是依据截图文件名假定成功。

固定帧值和 HWND/PID 都是项目实现细节，不能跨项目复制；可复用的是“明确序列、覆盖进度、控件 read-back、原始截图血缘”的方法。HLMV pass 仍是离线证据，实机截图可推翻它。

## 9. HLMV 不能证明的内容

- Boomer bile 的真实 `IT` proxy 行为；
- 所有地图光照下的 SelfIllum/透明表现；
- 第一人称所有武器和特殊动作；
- 联机、服务器一致性和 addon 冲突；
- 完整 ragdoll/受击行为；
- 游戏内 LOD、血迹、燃烧、倒地等组合状态。

这些必须进入实机检查表。

HLMV 自身也可能不可用。若锁定参考/控制组和候选在同一 `studiorender.dll` 位置共同崩溃，记录工具版本、异常码和控制组结果，将状态标为 `unavailable_with_control_failure`。此时可用 compiled MDL 解码、CPU skin、骨段/pivot/边形变门和非空离线渲染替代发布前视觉门，但不能把替代结果写成 HLMV pass 或游戏实测。

## 10. 常见警告分类

| 类型 | 风险 | 处理 |
| --- | --- | --- |
| missing bone/material/animation | 高 | 阻止编译候选，修 source/QC |
| too many bone influences | 高 | 裁到三影响、归一化并报告损失 |
| zero-area/degenerate geometry | 中到高 | 定位面并修拓扑；不得直接忽略大量警告 |
| unused bone pruned | 高，若为附件/helper | 与预期骨清单比对；恢复权重/规则或证明应删除 |
| collision/solid warning | 高 | 检查 PHY 输入、骨和 checksum |
| material not found | 高 | 修复 `$cdmaterials` 和闭包 |

项目可以维护 allowlist，但每条必须含准确 warning 文本、适用工具哈希、解释和证明报告。

## 11. 编译退出门槛

- StudioMDL exit 0 且 warning 全部被分类；
- companion checksum、版本和路径正确；
- compiled VVD 顶点预算与逐 mesh VTX -> MDL -> VVD 映射通过，零越界、零缺失；
- 编译后接口契约与原生目标闭合；
- 主动画、corrective、sequence 和 rest skeleton 的独立合同与报告闭合；
- 自定义骨/比例/flex/physics 与源审计闭合；
- 唯一 alias HLMV 矩阵通过；或按控制组共同失败规则记录 unavailable，并通过独立 compiled decode/CPU skin/非空渲染替代门；
- 仍需游戏实测的项目已列入候选 manifest，而不是被写成“已通过”。
