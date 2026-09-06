# 自动化脚本目录

本目录说明 Karin PT、Cloth04 Zoey 等项目中形成的自动化职责，便于后续项目复用设计。源脚本主要位于 `L4d2/Karin_PT_L4D2/src/scripts/` 和各项目 `src/scripts/`。它们包含角色路径和契约时，不应直接复制参数；先运行 `python <script> --help`、阅读实现，并检查是否硬编码骨数、对象名、材质 atlas、survivor、include 或 declaration 表。第一人称脚本的阶段关系、接受/否决分支见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)；source-fit/procedural 回归见 [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md)。

Riptide 项目证明“职责可复用”不等于“脚本可原样调用”。Karin_PT 的 proportion、world QC、jiggle、flex、atlas、arms/HUD 和 release 脚本包含角色/槽位常量；新项目应参数化算法或编写项目脚本，并把输入合同写进报告。

## 1. 输入与来源审计

| 脚本 | 职责 |
| --- | --- |
| `verify_source_lock.py` | 验证输入与工具哈希锁 |
| `audit_blend_source.py` | 只读审计 Blend 场景、骨架、网格、材质和形态键 |
| `audit_source_vrm.py` | 审计 VRM humanoid、spring、collider 与源信息 |
| `audit_shape_key_deltas.py` | 计算每个 mesh/key 的非零 delta 与位移 |
| `extract_vpk_entries.py` | 从参考/原生 VPK 精确提取指定 entry |
| `audit_sourceio_model.py` | 用 SourceIO 独立检查 Source 模型 |
| `build_binary_lineage_probe.py` | 比较模型二进制来源，防止误用原版或参考模型 |

## 2. 骨架与模型构建

| 脚本 | 职责 |
| --- | --- |
| `build_rig_candidate_map.py` | 生成显式 source-to-target 骨映射及证据 |
| `cloth04_replace_zoey/src/scripts/build_rig_map.py` | Cloth04 项目实例：显式多对一 mapping，并对 collapsed spring 的 path-0 direct-child 代表设置硬门；算法可复用，骨名/数量不可复制 |
| `build_retargeted_world_blend.py` | 在派生 Blend 中构建最终骨架、单位、权重和常驻 shape |
| `generate_sourcefit_target.py` | source-fit 实例：保留目标 ABI/接口方向，把有源代表的 pivot 放到源 bone head，并输出逐骨 lineage/pivot 误差 |
| `build_sourcefit_blend_prototype.py` | 构建 no-LBS source-fit 派生 Blend；网格只做统一 similarity、权重映射/top-3，报告全 edge/bounds/centroid 合同 |
| `nyako_replace_hunter/src/scripts/build_retargeted_models.py` | Hunter 项目实例：53 core 使用锁定动漫 Hunter Source world rotation、Nyako pivot，动态骨保留 source world transform；world 量化 no-LBS residual，L4D2/L4D1 claw 则各自 target-fit。算法可参考，骨数、Spine 比例、对象和目标路径不可复制 |
| `audit_bind_geometry_contract.py` | 比较 target-fit 与 source-fit 候选的拓扑保形、pivot、side sign 和 lineage；已知坏候选作为负面对照 |
| `compare_sourceio_skeletons.py` | 比较两个编译/导入 skeleton 的名称、父级和 rest transforms |
| `export_world_smd.py` | 从冻结 Blend 导出 world SMD/VTA 及报告 |
| `generate_proportion_smd.py` | 从角色 bind 与**已选动画基准**生成 proportion corrective/target SMD；参数名中的 `zoey-reference` 表示动画 corrective 输入，不表示 output slot |
| `generate_jigglebone_include.py` | 从最终 rig map 生成经验证的 `$jigglebone` QCI |
| `generate_flex_include.py` | 生成 flexdesc/controller/rule include |
| `rescale_vta.py` | 结构化缩放 VTA position，并保留其他字段 |
| `audit_face_flex_export.py` | 审计 VTA frame、名称、拓扑与 bounds |
| `audit_export_packed_materials.py` | 检查导出 mesh 的材质槽/packed material 数据 |
| `audit_first_person_arm_components.py` | 盘点 Blend 中完整 edge-connected 部件、bounds、材质和臂骨影响，辅助建立源选面规则；项目脚本含 Karin 假设，不能原样泛化 |
| `build_source_arm_selection_manifest.py` | 在不可变源 Blend 上按形态键、原骨权重和完整 edge 连通关系生成 polygon-index 手臂 manifest；锁源 SHA 与精确三角闭包 |
| `build_source_first_person_arms_blend.py` | 把源 manifest 应用到拓扑完全一致的派生 world Blend；复制当前 Basis、clear keys 后写回 mesh，再裁出三件手臂部件 |
| `export_source_first_person_arms_smd.py` | 从裁剪 Blend 导出 126 骨 world-bind 手臂 SMD；是可审计分支，不优先于已验收 world-SMD 抽取 |
| `extract_source_first_person_arms_from_world_smd.py` | 黄金抽取路径：按 manifest 从已验收 world SMD 精确复制 triangle blocks，并验证 Basis-bake 坐标、UV、权重和 header 合同 |
| `retarget_first_person_arms_smd.py` | 逐 influence `sum(w * B_view * inverse(B_world) * p)` 候选/诊断器，处理 VRD 后备折叠、top-3 与归一化；必须附 triangle-edge stretch 门，Karin 最终因残余 helper 不连续未采用此几何路径 |
| `align_first_person_arms_similarity.py` | 早期/分侧 similarity 试验；正式路径由硬验全 edge 比率的 rigid-alignment 构建器取代，保留作诊断 |
| `transfer_reference_arm_weights.py` | Karin 最终 bone-fit 候选的同角色 nearest unique rest-position 权重来源：参考 corners 按五位坐标去重并平均，再逐源 corner 找最近点；只改权重，位置、法线、UV、拓扑和材质必须零变化 |
| `transfer_reference_arm_surface_weights.py` | 最近参考三角面/barycentric 转移与平滑实验分支；除非报告优于锁定候选，不得仅因算法看似更平滑就替换正式输入 |
| `audit_first_person_arms_surface_candidate.py` | 审计 source/geometry/candidate 的几何零变化、参考距离、左右泄漏、权重和、edge 与 triangle-corner 连续性 |

## 3. Physics

| 脚本 | 职责 |
| --- | --- |
| `prepare_physics_smd.py` | 从原生 physics 输入保留实际 hull 骨及必要祖先 |
| `audit_physics_smd_binding.py` | 验证 physics SMD 骨、绑定、顶点和转换假设 |
| `generate_world_physics_contract.py` | 从最终 target/rig-map 生成 definebone/jiggle QCI；支持角色专用有界 profile 并锁参数来源 |
| `audit_ponytail_root_skinning.py` | collapsed spring 根部 CPU skin：验证 path-0 代表、segment、seam 边、根区位移，并运行已知坏候选负门 |
| `audit_compiled_ponytail_physics.py` | 解码 world/light compiled procedural payload，逐字段验证父链、flags、length、mass、三向 stiffness/damping、angle 与 parity |

## 4. 材质与 HUD

| 脚本 | 职责 |
| --- | --- |
| `build_l4d2_atlas_materials.py` | 处理 base/normal/emission、调用 VTEX、生成 bile patch VMT/VTF |
| `validate_l4d2_material_outputs.py` | 验证 VMT/VTF 闭包、shader 契约、flags、mip、方向和 mask |
| `build_rochelle_arms_hud.py` | legacy：旧参考 arms token/VVD/VTX/材质搬运与 HUD 组装工具。arms 分支已否决；只允许将显式 HUD 子流程作为历史实现参考 |
| `render_vtf_hud_previews.py` | 解码 HUD VTF，生成含 alpha 的预览 |
| `compare_arms_audits.py` | 比较原生与候选 viewmodel 接口 |

材质构建器是 source-of-truth。不要直接修 `work/compile_sandbox/materials/` 下派生 VMT，然后忘记回写生成器。

`build_rochelle_arms_hud.py` 中的 `mechanic -> producer` 定长 token 替换和参考 VVD/VTX/14 件材质搬运，是 Karin 早期实现。该方案已被用户否决并废弃，只能用于审计旧候选或复现失败血缘，不能进入新的构建流程。HUD 图仍可由独立、显式输入处理，不应借此复活旧 arms payload。

## 5. QC、编译与预览

| 脚本 | 职责 |
| --- | --- |
| `generate_world_qc.py` | 从审计报告和 include 生成正式/preview QC |
| `run_studiomdl.py` | 固定工具和 game root 调用 StudioMDL，捕获日志与产物 |
| `audit_compiled_world_contract.py` | 审计编译 MDL/VVD/VTX/PHY 与目标契约 |
| `Y_Replace_Witch/src/scripts/audit_compiled_models.py` / VTX mapping audit | Witch 双目标实例：逐 bodypart/model/mesh/strip-group 验证 compiled VVD 预算和 VTX -> MDL -> VVD 索引完整性；StudioMDL 成功不能替代 |
| `Y_Replace_Witch/src/scripts/build_retargeted_models.py` | Witch 项目实例：构建 source-fit/custom-bind target、权重 lineage、局部 topology protection 和 bind-basis 审计；算法职责可参考，骨名/对象/阈值不得原样调用 |
| `Y_Replace_Witch/src/scripts/prepare_model_sources.py` | Witch 项目实例：从双 target 契约生成 QC/QCI/SMD，保留每变体 collision/PHY 来源并比较共享 canonical/Pelvis/root 投影；路径和 native block 必须重新审计 |
| `nyako_replace_hunter/src/scripts/prepare_model_sources.py` | Hunter 项目实例：从最终 target 生成全 85 骨 `$definebone`，并拆分 corrective/reference、`CustomModel`、`ragdoll` 的 custom/native pose 职责。数量与序列名是项目值 |
| `audit_pose_deformation.py` | 从 Source predelta、FK 与 CPU LBS 评估完整动画的 surface edge 与关节运动学（bend delta、reach、segment drift、对象/局部区域）；必须有输入血缘、样本覆盖和已知坏候选策略 |
| `nyako_replace_hunter/src/scripts/audit_compiled_models.py` | Hunter 项目实例：深层 VTX + 53 core/101 帧 proportion target-native delta + rotation identity + 三条本地 pose sequence owner；root 排除有明示理由。帧数、骨数和阈值不可复制 |
| `render_blend_preview.py` | 在 Blender 中生成绑定/材质预览 |
| `build_hlmv_preview_sheet.py` | 将 HLMV 原始截图整理成 contact sheet |
| `hlmv_window_action.ahk` 或等价工具 | 对准确 HLMV 窗口和控件设置/回读 sequence、frame；避免多窗口焦点串控。不得固化其他项目的 HWND、PID 或屏幕坐标 |
| `audit_light_animation_equivalence.py` | 同时输出 strict reference diagnostic 与 relative-to-bind motion hard gate，覆盖 light 本地序列逐帧/逐骨 |
| `audit_light_idle_skinning.py` | 从 compiled light 动画执行 CPU LBS，检查 L/R、指骨段、pivot 半径、三角绝对边长与退化 |
| `build_visual_pose_validation.py` / `render_compiled_pose_evidence.py` | HLMV 不可用时生成 compiled-pose payload、离线姿态渲染和非空图像闭包；不能冒充游戏实测 |
| `generate_source_first_person_arms_qc.py` | 从成熟参考提取 55 definebone、49 bonemerge、idle/proportion ABI，但把 `$body`、材质路径和正式/唯一 preview `$modelname` 指向 source-derived 资产 |
| `build_view_arms_rigid_alignment_smd.py` | 对 source-derived geometry 应用全局 uniform similarity，并硬验所有 triangle-edge 比率一致；参数必须来自同角色 view rest/bone/surface 拟合，不能只猜 Z offset |
| `smooth_transferred_arm_weights.py` | 沿源 topology 邻接平滑同角色转移权重；默认最后才 top-3/归一化，用于消除 nearest-point 权重硬边，并报告参数与影响闭包 |

## 6. 组装、验证与发布

| 脚本 | 职责 |
| --- | --- |
| `assemble_release_tree.py` | 从显式 world/material/arms/HUD 输入组装新的 loose tree |
| `assemble_source_arms_release.py` | 组装 source-derived arms 候选；替换三件 companion、删除旧 14 件参考材质、锁定 33 文件闭包，并执行旧哈希/namespace/token 负面门 |
| `stage_release.py` | 把通过门槛的构建暂存为命名候选 |
| `validate_vpk_tree.py` | 逐 entry 读取 VPK payload，与 loose tree 比较 CRC/SHA/bytes |
| `validate_installer_roundtrip.py` | 在 fake game root 验证安装、备份、卸载和恢复 |
| `build_final_validation.py` | 汇总所有阶段报告，形成最终静态 gate |
| `build_release_manifest.py` | Cloth04 实例：汇总 source-fit、light relative、procedural 正负门、组件闭包和 VPK 身份；manifest 参数/骨数是项目专用 |
| `package_release.py` | 项目实例：重新哈希 compiled/pose 审计输入，按显式 allowlist 组装 loose tree，拒绝 preview/reference/compile-only source，最后逐 VPK entry 验 CRC/bytes/SHA |
| `repair_runtime_mount_name.ps1` | 游戏关闭时校验候选哈希，备份 GBK `addonlist.txt` 和旧 VPK，把同一 payload 安装为短 ASCII 名并置为第一启用项，输出可回滚报告 |

## 7. 脚本设计要求

后续新增脚本应遵守：

- 输入路径必须显式，不从整个目录猜“最新文件”；
- 默认拒绝覆盖输出；
- 只写项目/用户授权范围；
- 输出 JSON 报告，必要时附 Markdown/PNG；
- 报告包含工具版本、输入哈希、完整命令、时间和结果；
- source-lock 验证 required role 清单完整性，不仅验证已列项；跨项目借用的解析库、插件和正式 gate 脚本也要锁定；
- source-derived 选面报告必须包含源 Blend SHA、对象拓扑合同、规则参数、每对象 polygon indices 和三角/material totals；
- manifest 映射到派生 Blend 前必须比较顶点、边、polygon 顺序/topology hash，不允许静默坐标近邻回退；
- 删除 shape keys 前必须把当前 Basis 坐标烘回基础 mesh，并在报告中记录该操作；
- 第一人称参考资产必须分别声明 `abi_source` 与 `visible_geometry_source`，不得用 55 骨兼容推断网格血缘；
- 正式 arms gate 同时检查新 companion 正面哈希、旧参考 companion 负面哈希、允许材质名、禁止 token 和禁止 namespace；
- HLMV preview QC 除唯一 `$modelname` 外必须与正式 QC 输入同源，并保留多角度截图清单；
- 多 runtime target 的脚本分别生成/审计 companion family，同时把设计共享的 canonical/Pelvis/core/full/root 投影作为跨目标 equality gate；
- bind-basis 报告必须区分 name/index/parent、pivot、rotation 与坐标来源；若组合来源不同，额外输出 child local-axis 与代表动画运动学门；
- source-fit/no-LBS 报告以完成 global similarity 后的源几何为 baseline，逐 corner 量化
  额外 bind displacement；不能只写布尔声明，也不能把该零位移门套到另行选择
  target-fit 的 viewmodel；
- proportion frame count 由当前 sequence contract 决定，不硬编码“一帧”；静态重复帧
  必须逐帧覆盖且 transform 一致；
- 每条关键 local pose sequence 显式记录 frame count、position owner 和 rotation owner，
  不根据 `reference`/`CustomModel`/`ragdoll` 名字猜姿势；
- 从 target SMD 生成 `$definebone` 后，必须从 compiled MDL 做全骨 rest roundtrip；raw
  SMD rotation 到当前 QC 字段的换序为 `(Y,Z,X)` 并从 radians 转 degrees，但公式仍需
  用当前工具链/原生控制组交叉验证；
- 姿态回归器同时覆盖表面形变和关节运动学，按对象/局部区域输出样本与指标；全局 edge 统计不能替代；
- HLMV 自动化必须锁定目标窗口身份并回读 sequence/frame/Ground 等关键状态；保存的截图文件名不是控件状态证据；
- release 脚本将 preview alias、compile-only include sidecar、QC/SMD、DX80/SW 和参考资产作为 denylist，而不是依赖人工清理；
- 构建报告显式包含 `output_slot`、`slot_interface_source`、`rest_skeleton_source`、`primary_animation_basis`、`corrective_source + sha256`、`sequence_contract_source`、`ordered_includes` 和 `ground_offset_owner`；
- 禁止从 `$modelname`、survivor 文件名或输出目录自动推断动画基准/corrective；
- declaration 和 include 使用有序列表，记录 total、unique 与重复项，不自动去重或排序；
- 编译验证器读取最终 VVD/VTX 数据，执行 `<=60,000` 工程预算和逐 mesh mapping 完整覆盖；
- 验证集合应检查 `actual == expected`，不能只检查 expected 子集存在；
- 派生目录中的 extra/stale 文件应失败；
- 常量图片的方向检查可有明确豁免，非恒定图不可豁免；
- 重试必须有上限、间隔和最终错误；
- 出错时不删除可用于诊断的日志和中间产物。
- 回归器锁正候选和已知坏候选的输入哈希、schema 与预期失败 check ID；禁止空集合或恒通过。
- 复用上一候选组件时生成本轮 hash reuse attestation，不只引用历史报告路径。

## 8. 推荐调用顺序

```text
verify source lock
  -> audit Blend / VRM / native / references
  -> build rig map
  -> build retargeted derivative Blend
  -> compare target-fit and source-fit bind candidates with edge/pivot/seam gates
  -> export and audit SMD/VTA
  -> build source arm polygon manifest on immutable Blend
  -> verify manifest topology against accepted world derivative
  -> extract exact arm triangle blocks from accepted world SMDs
  -> fit one shape-preserving view-space transform and reject local edge stretch
  -> transfer ABI-only same-avatar view weights
  -> smooth full weights on source topology, then final top-3
  -> generate formal and unique-alias arms QC from ABI-only reference
  -> compile/audit source-derived arms + multi-angle HLMV gate
  -> lock output slot / animation basis / corrective / sequence contracts
  -> generate proportion / flex / jiggle / physics inputs
  -> run collapsed-chain CPU skin positive + known-bad negative controls
  -> build and validate materials
  -> generate QC
  -> run StudioMDL
  -> audit compiled contract + VVD budget + VTX mapping
  -> audit light bind-relative motion + world/light procedural field parity
  -> HLMV visual gate
  -> build HUD and assemble source-derived arms release closure
  -> assemble new loose tree
  -> build VPK
  -> validate VPK payloads
  -> validate installer roundtrip
  -> build final validation + candidate manifest
```

每个箭头都是门槛。上游报告失败时，不运行下游并把错误扩散到最终 VPK。
