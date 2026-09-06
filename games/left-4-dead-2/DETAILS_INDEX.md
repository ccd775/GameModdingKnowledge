# Left 4 Dead 2 角色替换 Mod 公共知识库

本目录汇总在完整角色替换项目中验证过的技巧、工具、流程、排障记录和验收方法。它不是某个角色的构建产物，也不应保存受版权限制的参考 Mod 内容；这里只保存可复用知识、项目案例数据和证据链接。

整理状态：2026-08-18 已纳入 Cloth04 Zoey v1.0-v1.3、Karin Y -> Witch v0.1-v0.3
与 Karin Nyako -> Hunter 的完整反馈闭环。新增内容覆盖 source-fit world 的零逐骨
网格预扭门、Source custom rotation + avatar pivot、Hunter 本地 pose sequence 职责、
真实 ANI 手腕/Head 探针、全骨 `$definebone` roundtrip，以及 survivor/non-survivor
动画默认边界。Cloth04 v1.3、Witch v0.3 与 Nyako Hunter 当前 SHA 均已收到用户
验收通过，但结论只限各自实际验收范围，不虚构逐武器/FOV/地图矩阵。Karin
SelfIllum 与短名 SourceArms 也已有对应用户证据；Riptide v1.3 仍等待实机复测。

## 快速入口

第一次接手项目：

1. [原则与证据等级](00-principles-and-evidence.md)
2. [端到端 SOP](10-end-to-end-sop.md)
3. [工具链与工作区](01-toolchain-and-workspace.md)
4. [参考模型与源文件审计](02-reference-and-source-audit.md)

按问题阅读：

| 问题 | 文档 |
| --- | --- |
| 骨架映射、权重、角色比例异常 | [骨架、绑定与角色比例](03-rigging-retargeting-and-proportions.md) |
| 爆指、假性左右互换、source-fit、发根拉丝与正负回归 | [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md) |
| “Zoey 动画”到底做什么、为什么 Louis 也能用 | [槽位、动画基准与 Zoey/TeenAngst](15-animation-basis-slot-and-zoey.md) |
| 高跟鞋、形态键、表情、VTA | [形态键、表情与几何处理](04-shape-keys-flexes-and-geometry.md) |
| 头发、耳朵、尾巴、裙摆、ragdoll | [附件、procedural 骨与物理](05-physics-and-procedural-bones.md) |
| VTF、Boomer bile、夜光、透明 | [材质、贴图与 L4D2 Shader](06_materials_vtf_boomer_glow.md) |
| QC、StudioMDL、HLMV | [QC、编译与模型预览](07-qc-compile-and-hlmv.md) |
| 手臂、HUD、VPK、安装与回滚 | [第一人称手臂、HUD、打包与发布](08-arms-hud-packaging-release.md) |
| 从用户 Blend 制作第一人称手模 | [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md) |
| 已看到异常，需要快速定位 | [排障手册](09-debugging-playbook.md) |
| 新项目从零开始 | [端到端 SOP](10-end-to-end-sop.md) |
| 查 Karin PT 项目实测值和失败史 | [Karin PT 案例](11-karin-case-study.md) |
| 查 Cloth04 Zoey 爆指、light idle 与双马尾修复史 | [Karin Cloth04 Zoey 案例](15-karin-cloth04-zoey-case-study.md) |
| 查 Louis 加载崩溃、偏矮屈膝与透明反例 | [Riptide Louis 案例](16-riptide-louis-case-study.md) |
| 查 Witch/Bride 双目标、四段手臂、Bride 悬空与双变体编译 | [Karin Y -> Witch 案例](19-karin-y-witch-case-study.md) |
| 查 Hunter 待机张臂、歪头、no-LBS source-fit 与本地序列职责 | [Karin Nyako -> Hunter 案例](20-karin-nyako-hunter-case-study.md) |
| 查可复用脚本及其职责 | [自动化脚本目录](12-automation-script-catalog.md) |
| 查外部与本地证据来源 | [证据来源与延伸阅读](13-sources-and-further-reading.md) |
| 直接开始一轮可追溯构建 | [PowerShell 命令配方](14-command-recipes.md) |

## 模板

- [项目检查表](templates/project-checklist.md)
- [接续状态模板](templates/project-state-template.md)
- [实机反馈模板](templates/runtime-test-report-template.md)
- [候选清单模板](templates/release-manifest-template.json)

## 运行证据

- [Karin SelfIllum 修复用户实机确认（2026-08-08）](evidence/karin-selfillum-user-confirmation-2026-08-08.md)
- [Karin source-derived 第一人称手臂运行确认（2026-08-14）](evidence/karin-source-arms-runtime-confirmation-2026-08-14.md)
- [Karin Cloth04 Zoey v1.3 用户验收（2026-08-18）](evidence/karin-cloth04-zoey-v1.3-user-acceptance-2026-08-18.md)
- [Karin Y -> Witch v0.3 用户验收（2026-08-18）](evidence/karin-y-witch-v0.3-user-acceptance-2026-08-18.md)
- [Karin Nyako -> Hunter 用户验收（2026-08-18）](evidence/karin-nyako-hunter-user-acceptance-2026-08-18.md)
- [Riptide Louis 崩溃、体态与透明反馈及离线修复状态](16-riptide-louis-case-study.md)

## 使用规则

- 先确认结论标签：**通用规则**、**项目实测值**或**待实机验证假设**。
- 新项目不得复制 Karin 的骨数、pelvis 位移、材质数或 VPK entry 数；必须重新审计和计算。
- 修复必须发生在 source-of-truth 中，随后重建派生产物。不要直接改最终 VPK 里的文件并失去血缘。
- 静态验证、HLMV 预览和 L4D2 实机是三个独立门槛。
- 实机截图或录像发现的问题优先级高于静态推断。
- 更新知识库时，记录失败方案为什么失败，不只记录最后命令。

## 推荐项目文档最小集

每个新 Mod 项目至少维护：

```text
PROJECT_STATE.md
source-lock.json
reports/source-audit.json
reports/native-target-contract.json
reports/rig-map.json
reports/bind-strategy-and-pivot-contract.json
reports/composite-bind-basis-contract.json
reports/geometry-bind-displacement-contract.json
reports/animation-contract.json
reports/local-pose-sequence-contract.json
reports/cross-variant-root-contract.json
reports/pose-deformation.json
reports/light-bind-relative-animation.json
reports/procedural-world-light-parity.json
reports/known-bad-negative-controls.json
reports/material-contract.json
reports/compiled-model-contract.json
reports/world-vertex-mapping.json
reports/source-arm-selection-contract.json
reports/source-arm-view-placement-and-weight-continuity.json
reports/compiled-view-arms-contract.json
reports/hlmv-arms-screenshot-manifest.json
reports/hlmv-sequence-frame-control-manifest.json
reports/release/candidate-manifest.json
reports/runtime/
```

文件名可以变化，但职责不能缺失。

## 维护原则

当新项目得到可复用结论时：

1. 将一般规律写入相应专项文档。
2. 将角色特定数字写入单独案例，而不是正文规则。
3. 给出证据路径、公开官方来源或最小复现。
4. 若旧结论被实机推翻，保留旧方案并标记 rejected，说明推翻证据。
5. 更新本索引和相关检查表。
