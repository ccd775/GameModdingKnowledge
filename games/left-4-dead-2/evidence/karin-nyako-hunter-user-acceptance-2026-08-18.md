# Karin Nyako -> Hunter 用户验收（2026-08-18）

## 证据等级

用户手工实机验收。该证据高于本候选的静态结构、StudioMDL、HLMV 和离线动画合成
门，但只覆盖用户实际验收的当前候选与本任务范围。

## 候选身份

- 项目：`L4d2/nyako_replace_hunter`
- replacement：Hunter、Hunter L4D1 及两套 claw viewmodel
- VPK：`dist/Karin_Nyako_Hunter.vpk`
- VPK bytes：`37,525,555`
- entries：`41`
- payload bytes：`37,523,904`
- SHA-256：`54B4838F3770D4D49B9C7D6E51162B58C8389EFD056FD4CE1117AE49E17CB061`
- package report：`reports/package/package-validation.json`
- 打包时 runtime 字段：`not_run_by_design`

## 用户反馈

2026-08-18，用户对上述候选明确回复：**“验收通过。”**

因此，该 SHA 对应候选在用户实际验收范围内升级为 `user-confirmed pass`。打包报告
仍是构建时快照，不回写其 `runtime_game_test` 字段；本文件作为追加证据。

## 已确认的修复范围

- 先前阻止验收的 Hunter 待机横向张臂问题不再阻止当前候选通过。
- 被否决 native-bind/LBS 版本引入的歪头、下巴前伸回归不再阻止当前候选通过。
- 当前“成功动漫 Hunter core rotation + Nyako pivot + 原始 world 网格不预扭”的
  source-fit bind、动画职责拆分和编译闭包获得用户最终验收。

完整反馈链、离线正反对照和项目实测值见
[Karin Nyako -> Hunter 案例](../20-karin-nyako-hunter-case-study.md)。

## 证据边界

用户没有逐项列出地图、每个攻击/扑击动作、L4D1 变体、第一人称 claw、ragdoll、
燃烧、材质、每条 jiggle 链或 FOV 矩阵。因此不能把“验收通过”扩写为这些项目均已
分别测试。HLMV 此前没有取得有效的候选姿势视图，也不得追记为 HLMV pass。

后续若模型、骨架、动画、材质、QC、PHY 或 VPK 任一字节变化，必须生成新 SHA 并
重新建立离线与用户证据；本条不能成为未来版本的自动豁免。
