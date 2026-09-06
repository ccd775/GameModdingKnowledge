# Karin Y -> Witch v0.3 用户验收

## 证据等级

用户明确反馈的本次候选验收证据。它高于本候选的静态报告、StudioMDL、SourceIO、HLMV 和 CPU skin 离线门，但只覆盖用户实际复测的范围；不能自动扩写为所有地图、武器、攻击、燃烧、ragdoll、jiggle 或 FOV 组合均已逐项验证。

## 候选身份

下列大小、条目和哈希是本项目实测的候选身份，不是其他 Mod 的发布模板。

- 项目：`L4d2/Y_Replace_Witch`
- 目标：`models/infected/witch.*` 与 `models/infected/witch_bride.*`
- 版本：`Karin_Y_Witch_Local_v0_3`
- VPK：`dist/Karin_Y_Witch_Local_v0_3.vpk`
- VPK bytes：`46,457,899`
- entries：`27`
- payload bytes：`46,456,754`
- SHA-256：`13C06C66BD0229E31A31503B0DDB7A200FAF4141FEBF507B8AF61702123058D0`
- 离线状态：`ACCEPTED_OFFLINE`

## 用户反馈

2026-08-18，用户在上一轮要求的候选复测后明确回复：**“验收通过。”**

因此，v0.3 在本次用户实际验收范围内升级为 `user-confirmed pass`。本文件是追加证据；不要修改打包时的 `runtime_game_test` 或旧 manifest 来伪造先验通过。

## 已确认的修复范围

- 普通 Witch 与 Bride 的手臂不再出现旧版截图中的“四段折断”轮廓。
- Bride 的悬空问题已修复。
- 两个目标仍分别覆盖原生 Witch runtime path，并保留各自的编译 companion/physics 合同。

## 证据边界

本条只确认用户实际验收的 v0.3 候选；它不代表未记录的完整运行时矩阵。若后续修改模型、材质、QC、PHY、VPK 或发布名，必须绑定新的候选 SHA，并重新建立静态、视觉和实机证据；本条不能成为未来版本的自动豁免。

## 许可边界

源 VRM 元数据记录 `OnlyAuthor`、`Redistribution_Prohibited`，并禁止 violent/commercial use。用户验收不改变许可条件。该 VPK 只能按本地研究/自用构建处理；公开上传、Workshop 发布或再分发前必须取得作者单独授权。
