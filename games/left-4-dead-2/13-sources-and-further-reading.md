# 证据来源与延伸阅读

本页说明知识库结论的来源边界。外部资料用于解释机制或提供社区实践；本机当前 L4D2 资源、项目静态报告和用户实机反馈仍是本项目的最终证据。

## 1. 官方/第一方技术来源

- [Valve Source SDK 2013](https://github.com/ValveSoftware/source-sdk-2013)：公开的 Source 1 代码，用于理解 studio model 结构、VertexLitGeneric 和附加 shader pass 的实现概念。
- [VertexLitGeneric DX9 helper](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/materialsystem/stdshaders/vertexlitgeneric_dx9_helper.cpp)：用于确认主 pass 中 detail/self-illum 相关 combo、sampler 与处理顺序。
- [Emissive Scroll Blended pixel shader](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/materialsystem/stdshaders/emissive_scroll_blended_pass_ps2x.fxc)：用于确认 EmissiveBlend 是独立加法 pass，以及 base/emissive/flow 的采样职责。
- [Studio model public header](https://github.com/ValveSoftware/source-sdk-2013/blob/master/src/public/studio.h)：用于理解 MDL 中骨、动画、sequence、attachment、hitbox 等结构。
- [Alien Swarm `vaddons.cpp` 固定 addon 名缓冲示例](https://github.com/NicolasDe/AlienSwarm/blob/master/src/game/client/swarm/gameui/swarm/vaddons.cpp#L275-L282)：只用于说明相关 Source 分支存在文件名长度风险；它不是当前 L4D2 分支的完整源码，不能单独证明 Karin 长名是唯一根因。

注意：Source SDK 2013 不是 L4D2 的完整源码。它能说明共享的 Source 1 机制，但任何分支差异都必须由 L4D2 自带工具、当前游戏资源和实机测试确认。

## 2. 用户指定的社区资料

- [Boomer bile textures guide](https://steamcommunity.com/sharedfiles/filedetails/?id=2241927774)：用于了解角色材质接入 Boomer 污渍的社区工作流。

社区资料是有价值的实现证据，但不能替代当前游戏 VPK 内实际 `survivors_it_shared.vmt` 的内容。本文档中采用的 patch/include 结论已与本机原生文件交叉验证。

## 3. 本机原生资源

每个项目应重新按 `gameinfo.txt` 挂载顺序定位：

- `materials/models/survivors/survivors_it_shared.vmt`；
- 目标 survivor 的 MDL/VVD/VTX/PHY；
- 目标第一人称手臂；
- 目标 HUD VMT/VTF；
- 动画 include models；
- L4D2 自带 StudioMDL、VTEX、VPK 和 HLMV。

本机原生文件的解包副本应保存路径、来源 VPK entry 和 SHA-256。

## 4. Karin 项目本地证据

入口：

- `L4d2/Karin_PT_L4D2/docs/SOP.md`
- `L4d2/Karin_PT_L4D2/PROJECT_STATE.md`
- `L4d2/Karin_PT_L4D2/source-lock.json`

重点报告：

- `reports/source-toolchain-research.md`
- `reports/reference-native-qc-audit.md`
- `reports/rig/karin-to-rochelle-bone-map.md`
- `reports/compile/picodra-ellis-world-metadata-and-export-flow.md`
- `reports/arms_hud/ARMS_HUD_HANDOFF.md`：早期 handoff，包含现已否决的参考二进制 arms 快捷方案；只能作为失败血缘证据，不得作为当前构建入口。
- `work/arms_from_source/source_selection_contract.json`：源 polygon indices/totals；当前仍位于 `work/` 的归档技术债。
- `work/arms_from_source/arm_selection_subagent_audit.json`：逐对象 topology、edge hash 和 shape-key delta；应在未来合并提升到 `reports/`。
- `reports/arms_hud/source-first-person-arms-world-smd-extract.json`
- `reports/arms_hud/source-first-person-arms-similarity-bonefit.json`
- `reports/arms_hud/source-first-person-arms-similarity-bonefit-reference-weight-transfer.json`
- `reports/arms_hud/source-first-person-arms-similarity-reference-weight-smoothing-unpruned24.json`
- `reports/arms_hud/source-first-person-arms-qc-similarity-reference-weights-smooth-final.json`
- `reports/arms_hud/source-first-person-arms-similarity-reference-weights-smooth-final-sourceio-audit.json`
- `reports/compile/source-first-person-arms-similarity-reference-weights-smooth-final-studiomdl.json`
- `reports/ui/hlmv-source-arms-final-smooth-front.png` 与 `hlmv-source-arms-final-smooth-angle.png`：仅 front/angle 静态证据，完整视角矩阵尚未归档。
- `reports/release/loose-tree-zoey-bile-selfillum-source-arms-smooth-final.json`：包含旧参考哈希/token/namespace 负面门和 33-file closure。
- `reports/release/vpk-validation-source-arms-short-name.json`
- `reports/runtime/source-arms-short-name-mount-repair.json`
- `reports/release/zoey-proportion-lineage-audit.md`
- `reports/release/zoey-bile-selfillum-fix-lineage-audit.md`
- `reports/materials/material-output-validation-boomer-selfillum-final.json`
- `reports/runtime/`
- `L4d2/SharedKnowledge/evidence/karin-selfillum-user-confirmation-2026-08-08.md`
- `L4d2/SharedKnowledge/evidence/karin-source-arms-runtime-confirmation-2026-08-14.md`

关键 JSON 合同：

- `compiled-world-zoey-proportion-contract.json`
- `karin-proportion-zoey-ground.json`
- `retargeted-world-blend-zoey-proportion.json`
- `native-rochelle-physics-vs-karin-highheel-binding-audit.json`
- `rochelle-arms-compatibility.json`：旧参考与原生接口兼容性审计，只证明公共 viewmodel ABI 覆盖，不证明当前可见手模血缘。

后续 agent 引用项目结论时应链接到具体报告，而不是只说“之前已经验证”。

## 5. Karin Cloth04 替换 Zoey 项目证据

入口：

- `L4d2/cloth04_replace_zoey/docs/SOP.md`
- `L4d2/cloth04_replace_zoey/PROJECT_STATE.md`
- [Cloth04 Zoey 公共案例](15-karin-cloth04-zoey-case-study.md)
- [Source-fit/procedural 通用专题](18-source-fit-bind-procedural-regression.md)

source-fit bind、proportion 与 light：

- `reports/rig/rig-map-ponytail-v15.json`
- `reports/rig/target-sourcefit-ponytail-v15.json`
- `reports/build/bind-geometry-contract-sourcefit-ponytail-v15.json`
- `reports/compile/compiled-proportions-audit-sourcefit-ponytail-v15.json`
- `reports/compile/compiled-light-animation-equivalence-sourcefit-ponytail-v15.json`

双马尾正负回归：

- `reports/rig/ponytail-root-skinning-sourcefit-v15.json`
- `reports/rig/ponytail-root-skinning-sourcefit-v14.json`：已知坏 v1.2 负面对照。
- `reports/compile/compiled-ponytail-physics-sourcefit-v15.json`
- `reports/compile/compiled-ponytail-physics-v1.2-negative.json`

编译、发布与运行证据：

- `reports/compile/compiled-world-audit-sourcefit-ponytail-v15.json`
- `reports/compile/compiled-light-audit-sourcefit-ponytail-v15.json`
- `reports/release/release-vpk-validation-ponytail-v15.json`
- `reports/release/final-validation-ponytail-v15.json`
- [Cloth04 Zoey v1.3 用户验收](evidence/karin-cloth04-zoey-v1.3-user-acceptance-2026-08-18.md)

历史 release manifest 仍记录打包时的 pending 状态；2026-08-18 的用户确认作为 append-only sidecar 提升运行证据，不回写旧 manifest。v1.0-v1.2 保留为运行时反例，不能重新部署。

## 6. Riptide 替换 Louis 项目证据

入口：

- `L4d2/riptide_replace_louis/docs/SOP.md`
- `L4d2/riptide_replace_louis/PROJECT_STATE.md`
- [Riptide Louis 公共案例](16-riptide-louis-case-study.md)

加载崩溃和 compiled 顶点映射：

- `reports/diagnostics/tumtara-load-crash-isolation-20260812.md`
- `reports/diagnostics/world-vertex-mapping.json`：旧 153,854-vertex 失败候选。
- `reports/diagnostics/reference-world-vertex-mapping.json`：65,474-vertex 成功参考控制组。
- `reports/diagnostics/zoey-v1.3-world-vertex-mapping.json`：59,248-vertex 修复候选。
- `reports/build/compiled-model-audit-zoey-v1.3.json`

Zoey 动画、比例和接地：

- `reports/diagnostics/zoey-proportion-height-knee-fix-20260813.md`
- `reports/diagnostics/shoe-ground-fix-20260812.md`：保留鞋底/Pelvis 测量；其中早期“Louis 槽位决定动画基准”的解释已被后续证据否决。
- `reports/build/world-qc-assets-zoey-v1.3.json`
- `reports/build/studiomdl-world-zoey-v1.3.json`

透明材质和发布：

- `reports/materials/uv2-runtime-candidate-matrix.md`
- `reports/materials/uv2-translucency-v1.3.md`
- `reports/materials/uv2-alpha-mode-v1.3.png`
- `reports/release/final-validation-v1.3.json`
- `reports/release/vpk-validation-v1.3.json`

证据状态必须写准确：用户已实机确认旧超顶点包加载崩溃，以及 v1.2 的不透明、额外屈膝和偏矮；v1.3 的 world、动画、材质和 VPK 已通过离线门禁，但当前仍是 `pending user runtime visual retest`。不能把静态 alpha、HLMV 或编译成功升级成游戏实测通过。

## 7. 参考 Mod 的证据角色

- `L4d2/ref/ccd_unendingFlame/`：提供已使用 SelfIllum 与 survivor bile patch 的材质实践。
- Karin/Picodra 参考：提供同角色 rest skeleton、比例、附件链，以及第一人称 viewmodel ABI、idle/proportion 和 rest-space 权重样本指导。其 compiled arms 网格与 `ko_komado_pt` 材质闭包已被用户明确否决，不能进入最终可见资产。

参考包中的文件不得被当成最终交付来源。候选 VPK 必须通过二进制 lineage、loose tree payload 和 SHA-256 证明来自本项目构建。

## 8. 如何新增来源

新增链接或本地证据时记录：

- 标题与 URL/路径；
- 访问或提取日期；
- 来源类型：官方、原生本机、社区、源模型、静态报告、HLMV、实机；
- 它具体支持哪个结论；
- 是否存在版本/分支限制；
- 是否被更高等级证据推翻。

不要堆积未读链接。每个来源都应对应一条可验证结论。

## 9. Karin Y -> Witch 双目标项目证据

入口：

- `L4d2/Y_Replace_Witch/PROJECT_STATE.md`
- `L4d2/Y_Replace_Witch/docs/SOP.md`
- [Karin Y -> Witch 双目标案例](19-karin-y-witch-case-study.md)
- [Karin Y -> Witch v0.3 用户验收](evidence/karin-y-witch-v0.3-user-acceptance-2026-08-18.md)

bind、权重和局部拓扑：

- `reports/build/model-build.json`：custom bind rotation + Karin pivot、core 覆盖、axis、权重 lineage、局部 smoothing/decimation 门。
- `src/scripts/build_retargeted_models.py`：项目实现；可读算法，不可复制骨名、对象、区域或阈值。

双变体 canonical、root 与 physics：

- `reports/build/modelsrc-build.json`：ordinary/Bride 的 canonical、projected Pelvis/core/full/root-delta equality 与 physics source-local policy。
- `src/scripts/prepare_model_sources.py`：双 QC/QCI/SMD 和 collision/PHY 投影实现。

姿态、二进制和视觉：

- `reports/audit/pose-deformation.json`：schema v2，全帧 surface + articulation audit。
- `src/scripts/audit_pose_deformation.py`：predelta FK/CPU LBS 实现；阈值只属本项目。
- `reports/compiled/compiled-model-audit.json`：双 target companion、VTX deep mapping、PHY 和 checksum。
- `reports/visual/hlmv-visual-validation.md`：v0.3 固定帧 HLMV 矩阵，以及 v0.2 HLMV false-negative 的说明。
- `reports/visual/v0_2-gameplay-arm-regression.png`：保留的用户游戏内四段手臂反例，SHA-256 `41074F803973F0AD4426AC2AF69D2D68ADFD2EA026BD3DB8AD244FEE165F22D3`。

发布与许可：

- `reports/package/package-validation.json`：fresh loose tree 与 VPK 的 entry/CRC/bytes/SHA 闭包。
- `reports/contracts/source-license.md`：VRM 许可限制。

v0.3 VPK 的 SHA-256 为 `13C06C66BD0229E31A31503B0DDB7A200FAF4141FEBF507B8AF61702123058D0`；用户已在本次验收范围内确认通过。v0.2 仍是实机反例。当前项目没有独立锁定的 v0.2 schema-v2 negative JSON，不能声称已有可复跑的机读负控；后续若补建，必须同时归档输入 hash、schema 和预期失败 check ID。

## 10. Karin Nyako -> Hunter 项目证据

入口：

- `L4d2/nyako_replace_hunter/PROJECT_STATE.md`
- `L4d2/nyako_replace_hunter/docs/SOP.md`
- [Karin Nyako -> Hunter 案例](20-karin-nyako-hunter-case-study.md)
- [2026-08-18 用户验收](evidence/karin-nyako-hunter-user-acceptance-2026-08-18.md)

关键报告：

- `reports/source/source-vrm-audit.json`：VRM spring/collider 与损坏 humanoid eye mapping。
- `reports/build/model-build.json`：成功参考 Source rotation + Nyako pivot、32 dynamic、
  world no-LBS displacement 与两套 claw target-fit。
- `reports/build/modelsrc-build.json`：85 `$definebone`、Hunter 本地 pose sequence 职责、
  两套 world physics source。
- `reports/compiled/compiled-model-audit.json`：53 core/101 帧 proportion delta、rotation
  identity、local pose owner、四模型 companion 与 deep VTX mapping。
- `reports/idle-arm-head-sourcefit-fix-20260816.md`：横向张臂与整网格 prepose/歪头的
  正反诊断。
- `reports/materials/material-build.json`、`reports/uv/exported-uv-audit.json`、
  `reports/package/package-validation.json`：材质、UV 与 41-entry payload 闭包。

accepted VPK SHA-256 为
`54B4838F3770D4D49B9C7D6E51162B58C8389EFD056FD4CE1117AE49E17CB061`。
被否决 native-rotation/LBS 候选 SHA-256 为
`D037200F2B357AF93C5A1CBD7BEC2B0574C9872EDF27F94559EBF39ED8564212`。
后者是用户截图和归档支持的运行时反例，但没有独立锁定 schema 的 machine-negative
JSON，不能声称当前审计器已经拥有可重跑完整负控。
