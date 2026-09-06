# L4D2 实机测试记录

## 候选

- Candidate ID: `<id>`
- VPK path: `<path>`
- VPK bytes / entries / payload bytes: `<values>`
- VPK SHA-256: `<hash>`
- 游戏 build ID: `<id>`
- 测试时间：`<timestamp/timezone>`
- 测试者：`<name>`

## 环境

- 地图/章节：`<map>`
- survivor：`<target>`
- runtime variant：`<ordinary/bride/light/DLC or target path>`
- 其他启用 addon：`<list or none>`
- 图形设置/光照说明：`<details>`
- 第一/第三人称：`<view>`
- Runtime VPK filename：`<name.vpk>`
- Filename/stem characters and encoded bytes：`<counts>`
- `addonlist.txt` state/encoding：`<state/encoding>`
- 完整退出并重启：`yes/no`
- `show_addon_load_order`：`<file/output>`
- `show_addon_metadata`：`<file/output>`

## 验收范围

- Acceptance scope：`<明确测试过的版本、问题链、动作与场景>`
- Not claimed：`<没有逐项测试、不得由 pass 推断的内容>`
- Supersedes runtime evidence：`<previous evidence path or none>`
- Evidence mode：`user manual / automated harness / mixed`

## 测试矩阵

| 场景 | 结果 | 证据 | 备注 |
| --- | --- | --- | --- |
| 候选实际挂载 | `pass/fail` | `<console/visual>` | 与菜单复选框分开记录 |
| 世界模型替换 | `pass/fail` | `<file>` | 是否仍为原版 survivor |
| 地图载入/重复载入 | `pass/fail` | `<file/dump>` | 记录崩溃模块/offset |
| idle/walk/run/crouch/jump | `pass/fail` | `<file>` | |
| 肩/肘/腕或髋/膝/踝关节链 | `pass/fail` | `<file>` | 是否出现额外段、反向弯曲、袖子/服装滞后 |
| injured/incap/ragdoll | `pass/fail` | `<file>` | |
| 第一人称长枪 | `pass/fail` | `<file>` | idle/fire/reload/shove |
| 第一人称手枪/双枪 | `pass/fail` | `<file>` | idle/fire/reload/shove |
| 第一人称近战 | `pass/fail` | `<file>` | swing/shove |
| 医疗、药品、投掷物、携带物 | `pass/fail` | `<file>` | 各类 viewmodel |
| 腕口/掌心/手指/肩口 | `pass/fail` | `<file>` | 左右、极限动作、不同 FOV |
| 袖套/腕饰/武器穿插 | `pass/fail` | `<file>` | |
| 总体身高/头顶高度 | `pass/fail` | `<file>` | 与明确基线比较 |
| reference/rest 腿链 | `pass/fail` | `<file>` | 排除 corrective 链缩短 |
| idle/aim 自然屈膝 | `pass/fail` | `<file>` | 区分 authored pose 与额外屈膝 |
| 脚在鞋内 | `pass/fail` | `<file>` | 几何/shape key |
| 鞋底与地面接触 | `pass/fail` | `<file>` | bind/idle/walk/run/crouch 分开 |
| 多 variant root/接地一致性 | `pass/fail/not applicable` | `<file>` | 同一角色多个 target 不应只有一者悬空/偏移 |
| 表情/眼睛/嘴 | `pass/fail` | `<file>` | |
| 头发/耳朵/尾巴/衣摆 | `pass/fail` | `<file>` | |
| Boomer bile 全表面 | `pass/fail` | `<file>` | |
| 普通微光 | `pass/fail` | `<file>` | |
| 作者发光区域 | `pass/fail` | `<file>` | |
| 连续透明 | `pass/fail` | `<file>` | 帽檐/薄纱/衣摆及排序 |
| alpha-test 切边 | `pass/fail` | `<file>` | 发丝/硬边 |
| 血迹/燃烧/LOD | `pass/fail` | `<file>` | |

## 失败详情

- 现象：`<what is visible>`
- 最小复现：`<steps>`
- 期望：`<expected>`
- 实际：`<actual>`
- 首次出现时间/动作：`<details>`
- 原始截图/录像：`<absolute or project-relative paths>`

## 分析

- 直接证据：`<facts>`
- 初始假设：`<hypotheses>`
- 已排除：`<items and evidence>`
- 确认根因：`<cause or pending>`

## 后续

- 修改 source-of-truth：`<file>`
- 最小重建范围：`<stages>`
- 复测门槛：`<conditions>`

本报告应作为 append-only sidecar 保存。发布 manifest/final report 是打包时快照，不因后续 pass/fail 原地改写；由项目状态文件追加指向本报告及其哈希。
