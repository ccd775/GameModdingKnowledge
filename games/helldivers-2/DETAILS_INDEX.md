# Helldivers 2 角色替换 Mod 公共知识库

> 公开副本说明：下文是原知识库快照。原项目报告没有分发；tools/validate_knowledge_base.ps1 现在检查公开文件与链接，不能重新证明原私有输入 SHA。新任务的实际调用从 portable-kits/helldivers-2/README.md 开始。

> 范围：使用 Blender、AQ Modified / ArchiveQT、HD2SDK Community Edition、FileDiver 和自定义审计脚本制作 Helldivers 2 角色模型替换 Mod。
>
> 状态：`project-proven`。肩部主案例来自 `HD2/Karin_Nyako_RE2310`；活动 supporting cases 来自 `HD2/DR03_Replace_Cm10EX00`、`HD2/Umbrella_Replace_RS6RS67RS100` 与 `HD2/SSF_Replace_FS37SC15`；另保留一个仅含资源、材质、UV 与发布经验的历史案例摘要。
>
> 肩部轮廓、腋下分件、上肢 rest-to-bind、形态键、原生盔甲抑制与头盔槽位方法以 RE2310 RefBindAxis 案例为主要来源；跨体型 palette 交集、开放衣物肩缝、AQ 顶点拆分和已安装材质闭包碰撞以 DR03 CM-10/EX-00 案例补充；源 Shoulder/UpperArm 到目标单肩骨的语义折叠、DS42 roll + 最小闭链 swing、多目标完整 Unit 克隆与骨盆桥接以 Umbrella 案例补充；自然 shoulder seam 权重优先、禁止用 clavicle blanket override 掩盖 lineage、差分姿态 moving-set 防假阳性和 DS42 owner clone 正向运行时证据以 SSF FS37/SC15 v4 补充。除明确标为“游戏/格式事实”的条目外，不应把单一项目数值或骨名推广为固定常量。
>
> 最后核验：2026-08-09。Karin SSF FS37/SC15 v4 已获用户手动运行时验收；Karin Nyako 与 Karin Umbrella 的活动发布状态仍以各自 SOP 为准；DR03 v3 肩缝证据已离线完成并被后续活动发布继承。Umbrella v1 与 SSF v3 的运行时拒绝、SSF v4 的运行时接受共同证明：同一 RawMesh、错误 target-native bind 或 post-override 相等均不能替代完整 final-lineage 证明。

## 先读什么

新任务的 Agent 应按以下顺序阅读：

1. [QUICKSTART.md](QUICKSTART.md)：从零开始的最短执行清单。
2. [01_EndToEnd_Workflow.md](01_EndToEnd_Workflow.md)：Gate 0-4 完整流程。
3. [02_HD2_Resource_Contracts.md](02_HD2_Resource_Contracts.md)：Unit、triplet、donor swap、坐标空间和装备槽合同。
4. [03_Rigging_Weights_Deformation.md](03_Rigging_Weights_Deformation.md)：骨架、rest/inverse bind、权重和姿态变形。
5. [04_Materials_Textures_Namespace.md](04_Materials_Textures_Namespace.md)：UV、DDS、透明、发光、材质与私有资源 ID。
6. [05_Compilation_Merge_Package_Deploy.md](05_Compilation_Merge_Package_Deploy.md)：编译、合并、确定性打包、部署和回滚。
7. [06_Validation_And_Evidence.md](06_Validation_And_Evidence.md)：静态、姿态、序列化、运行时及可复现性门禁。
8. [07_Troubleshooting_Playbook.md](07_Troubleshooting_Playbook.md)：按症状定位根因。
9. [08_Tools_And_Scripts.md](08_Tools_And_Scripts.md)：工具版本、运行约束和已验证脚本目录。
10. [case-studies/Karin_Nyako_RE2310.md](case-studies/Karin_Nyako_RE2310.md)：肩部/腋下、骨轴、腿脚、形态键、抑制与槽位的 RefBindAxis 失败链。
11. [case-studies/Karin_DR03_CM10_EX00.md](case-studies/Karin_DR03_CM10_EX00.md)：共享 Unit、材质闭包冲突、跨体型 palette 与动态肩缝失败链。
12. [case-studies/Karin_Umbrella_RS6_RS67_RS100.md](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)：完整 Unit 克隆、源双肩骨折叠、骨盆桥接和精确替换失败链。
13. [case-studies/Karin_SSF_FS37_SC15.md](case-studies/Karin_SSF_FS37_SC15.md)：自然肩缝权重、错误 clavicle 覆写/人工过渡圈、DS42 owner clone、髋腿例外、头发法线与严格贴图预算的运行时接受失败链。
14. [case-studies/New_SR24.md](case-studies/New_SR24.md)：资源、材质、UV 与发布经验。
15. [09_Agent_Handoff_Checklist.md](09_Agent_Handoff_Checklist.md)：长线任务交接合同。

模板位于 [templates](templates/)。任何新项目都应先复制模板到自己的项目目录，再填写项目常量；不要在公共知识库里写新的项目状态。

机器可读的知识库范围、源 SOP 哈希和验证状态见 [KNOWLEDGE_BASE.json](KNOWLEDGE_BASE.json)。

更新或交接后运行只读深度自检：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'HD2/SharedKnowledge/tools/validate_knowledge_base.ps1' -Deep -AsJson
```

检查器见 [`tools/validate_knowledge_base.ps1`](tools/validate_knowledge_base.ps1)，它不会修改项目或游戏目录。
当前活动案例（主案例与 supporting cases）的缺失链接、大小或哈希不匹配是 hard failure；manifest 中明确声明为 `metadata_only_in_this_checkout` 的历史证据缺失会作为 warning 保留，不会被静默忽略。

## 三层事实模型

每条结论应归入以下一层：

| 层级 | 含义 | 使用方式 |
| --- | --- | --- |
| `format-confirmed` | 已由工具源码、序列化结构或多个独立资源确认的 HD2/AQ 行为 | 可作为默认合同，但仍要绑定工具/游戏版本 |
| `project-proven` | 在至少一个真实 Mod 中通过构建、审计或运行时验证 | 可复用方法，不可直接复用项目数值 |
| `case-specific` | 特定模型、目标槽、FileID、draw range、patch index 或阈值 | 只放案例/SOP；新项目必须重新测量 |

例如：AQ whole-unit swap 会继承 donor entry 是 `format-confirmed`；RE2310 的肩部 game-space envelope、DR03 的 Slim clavicle/Stocky chest 骨名、SSF 的 171 点/owner FileID 和任何固定过渡圈比例都是 `case-specific`；“先审计自然 final-lineage 权重、再逐 seam 决定是否 post edit”是 `project-proven` 方法。

## 状态词必须精确

禁止用“完成”“通过”混淆不同阶段。建议只使用：

```text
inventoried
authoring_validated
compiled_and_offline_verified
packaged_and_offline_verified
deployed_without_launch
runtime_validation_pending
runtime_validated
rejected
superseded
quarantined_do_not_use
```

`offline_verified` 永远不等于 `runtime_validated`。用户截图或实际运行结果可以推翻全部离线门禁；被推翻的候选必须保留为拒绝证据，并从 `Output/` 隔离。

## 不可破坏原则

- `Ref/`、用户源 `.blend`、donor 成品和已接受发布包视为不可变输入。
- 所有输入、工具、脚本、候选、报告和发布包都记录 SHA-256。
- 中间物只写 `Work/`，最终交付只写 `Output/`，公共知识只写 `SharedKnowledge/`。
- 不覆盖已有候选、报告、ZIP 或游戏 patch index；新尝试使用新路径。
- 不把失败报告改写成成功报告；修正审计器后生成新版本报告。
- 部署授权、启动游戏授权、控制 Steam 授权是三件独立事项。
- 未经明确授权不得修改游戏 `data`，不得启动 Steam 或游戏。
- 部署时只复制精确三件套，不需要 Arsenal；回滚只删除哈希匹配的精确三件。

## 公共知识的更新规则

1. 新发现先写入项目 `SOP.md`，包含证据路径、哈希和状态。
2. 至少确认根因与适用范围后，再提升到公共知识库。
3. 公共条目必须说明哪些是通用合同、哪些只是案例数据。
4. 与旧结论冲突时不静默覆盖：记录旧结论为何失效，并链接新的证据。
5. 大型二进制、渲染图和临时审计结果留在项目 `Work/`；公共库只存文档、模板和轻量工具说明。

## 权威证据入口

- RE2310 项目完整 SOP：[`../Karin_Nyako_RE2310/SOP.md`](../../SOURCE_REFERENCES.md#local-only)
- RE2310 已验证脚本：[`../Karin_Nyako_RE2310/Work/scripts`](../../SOURCE_REFERENCES.md#local-only)
- RE2310 机器报告：[`../Karin_Nyako_RE2310/Work/reports`](../../SOURCE_REFERENCES.md#local-only)
- RE2310 审计与拒绝证据：[`../Karin_Nyako_RE2310/Work/audits`](../../SOURCE_REFERENCES.md#local-only)
- RE2310 最终离线发布物：[`../Karin_Nyako_RE2310/Output`](../../SOURCE_REFERENCES.md#local-only)
- DR03 项目完整 SOP：[`../DR03_Replace_Cm10EX00/SOP.md`](../../SOURCE_REFERENCES.md#local-only)
- DR03 v1/v2 运行时拒绝与 v3 离线证据：[`case-studies/Karin_DR03_CM10_EX00.md`](case-studies/Karin_DR03_CM10_EX00.md)
- DR03 v3 机器报告：[`../DR03_Replace_Cm10EX00/Work/reports`](../../SOURCE_REFERENCES.md#local-only)
- DR03 v3 最终离线发布物：[`../DR03_Replace_Cm10EX00/Output`](../../SOURCE_REFERENCES.md#local-only)
- Umbrella 项目完整 SOP：[`../Umbrella_Replace_RS6RS67RS100/SOP_zh-CN.md`](../../SOURCE_REFERENCES.md#local-only)
- Umbrella v1 运行时拒绝证据：[`../Umbrella_Replace_RS6RS67RS100/Work/evidence/runtime-20260808-v1-bind-rejection`](../../SOURCE_REFERENCES.md#local-only)
- Umbrella v2 机器报告：[`../Umbrella_Replace_RS6RS67RS100/Work/reports`](../../SOURCE_REFERENCES.md#local-only)
- Umbrella v2 最终离线发布物：[`../Umbrella_Replace_RS6RS67RS100/Output`](../../SOURCE_REFERENCES.md#local-only)
- SSF 项目完整 SOP：[`../SSF_Replace_FS37SC15/SOP.md`](../../SOURCE_REFERENCES.md#local-only)
- SSF v3 运行时拒绝、v4 离线门禁与用户运行时验收：[`case-studies/Karin_SSF_FS37_SC15.md`](case-studies/Karin_SSF_FS37_SC15.md)
- SSF v4 机器报告：[`../SSF_Replace_FS37SC15/Work/reports`](../../SOURCE_REFERENCES.md#local-only)
- SSF v4 运行时接受发布物：[`../SSF_Replace_FS37SC15/Output`](../../SOURCE_REFERENCES.md#local-only)
- 历史案例摘要：[`case-studies/New_SR24.md`](case-studies/New_SR24.md)。其外部二进制证据在本工作区可能未驻留，机器索引会将缺失链接报告为 warning。
