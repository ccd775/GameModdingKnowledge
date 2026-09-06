# Karin Cloth04 Zoey v1.3 用户验收

## 证据等级

用户手工实机验收。该证据高于静态结构、StudioMDL、SourceIO、HLMV 和 CPU skin 离线门，但只覆盖用户实际验收的当前候选与本任务范围。

## 候选身份

- 项目：`L4d2/cloth04_replace_zoey`
- replacement：Zoey / `survivor_teenangst`
- 版本：v1.3
- VPK：`release/Karin_Cloth04_Zoey_v1.3.vpk`
- VPK bytes：`28,400,301`
- entries：`32`
- payload bytes：`28,398,881`
- SHA-256：`B5931A9C17C16AAA54DE838C0C7EBEB659214CE71DF242A67ACE9AD98BD719B4`
- manifest：`release/Karin_Cloth04_Zoey_v1.3.manifest.json`
- 离线 final gate：`reports/release/final-validation-ponytail-v15.json`，73/73

## 用户反馈

2026-08-18，用户在连续复测 v1.0-v1.3 后明确回复：“验收通过。”

因此可以把 **v1.3 当前候选在用户验收范围内** 标记为 `user-confirmed pass`。发布 manifest 中的 `pending_user_runtime_visual_test` 是打包时尚未收到反馈的历史状态，不回写篡改；本文件作为后续追加证据。

## 此前反馈链

1. v1.0：脸侧短发摆幅过大、手指爆开、普通 idle 双臂异常。
2. v1.1：脸侧短发收紧后，手指仍爆开；light 扶栏杆动作看似左右手互换。
3. v1.2：source-fit bind 修复手/指和假性左右互换，但倒地姿势暴露双马尾首端拉丝、整束头发远离头部。
4. v1.3：双马尾动态代表改为 VRM 首动态段，并重建 world/light procedural 合同；用户最终验收通过。

## v1.3 修复身份

- `HairBack_L/R_002` 不再使用远端 `Hair_tail_L/R_007`。
- 动态代表锁定为 `Hair_tail_L/R_001__2`，即 VRM `path_position=0` 且为静态锚的 direct child。
- world/light 使用同一编译后 procedural payload。
- root CPU skin 正面门通过，v1.2 负面对照失败。
- compiled physics 正面门 47/47，v1.2 负面对照失败 22 项。

具体项目数值见 [Karin Cloth04 -> Zoey 案例](../15-karin-cloth04-zoey-case-study.md)，通用方法见 [Source-Fit Bind、动画接入与 Procedural 回归排障](../18-source-fit-bind-procedural-regression.md)。

## 证据边界

“验收通过”不应被扩写为未记录的逐项矩阵。本条反馈没有单独列出：

- 每种枪械、双枪、近战、药品和投掷物的所有第一人称动作；
- 每张地图、所有 FOV/分辨率和全部极端动画；
- 所有材质在每种光照、bile、燃烧和 LOD 条件下的单项结果；
- 每根 jiggle 链的独立参数评分。

后续若出现新问题，必须记录新的候选 SHA、最小复现和证据，不得把本次通过当作未来版本的自动豁免。

## 可复用结论

- 用户截图可以推翻结构上“看起来正确”的 bind 或 procedural 假设。
- 同一审计器让已知坏候选失败，能证明门禁确实覆盖了运行时故障层。
- 发布时 pending、发布后用户确认应保存为两条时间有序证据，不修改旧报告伪造先验结论。
