# PROJECT_STATE

## 当前目标

一句话说明目标 survivor、角色源模型和当前阶段。

## 权威输入

| 类型 | 路径 | SHA-256 | 用途 |
| --- | --- | --- | --- |
| Blend | `<path>` | `<hash>` | 几何/骨架/形态键 |
| VRM | `<path>` | `<hash>` | spring/collider 意图 |
| 原生目标 | `<path/report>` | `<hash>` | 游戏接口 |
| 参考 Mod | `<path>` | `<hash>` | `<specific purpose>` |

## 固定工具

| 工具 | 版本 | SHA-256 | 路径 |
| --- | --- | --- | --- |
| Blender | `<version>` | `<hash>` | `<path>` |
| StudioMDL | `<version>` | `<hash>` | `<path>` |
| VTEX | `<version>` | `<hash>` | `<path>` |
| VPK | `<version>` | `<hash>` | `<path>` |

## 角色与动画合同

| 合同 | 当前选择 | 来源/报告 | SHA-256 或有序摘要 |
| --- | --- | --- | --- |
| Output/replacement slot | `<survivor/path>` | `<native audit>` | `<hash>` |
| Slot interface | `<arms/HUD/attachment/hitbox/physics>` | `<report>` | `<hash>` |
| Character rest skeleton | `<custom reference>` | `<report>` | `<hash>` |
| Bind strategy | `<target-fit mesh | source-fit skeleton>` | `<pivot/edge report>` | `<hash>` |
| Composite bind basis | `<core rotation + pivot + parent contract>` | `<report>` | `<source hashes/axis gates>` |
| Geometry bind displacement | `<source-fit residual or target-fit transform>` | `<per-corner report>` | `<moved/mean/max>` |
| Primary animation family | `<Zoey/TeenAngst or proven exception>` | `<report>` | `<ordered includes>` |
| Corrective baseline | `<reference SMD>` | `<report>` | `<hash>` |
| Local pose sequence roles | `<reference/CustomModel/ragdoll or target equivalents>` | `<compiled report>` | `<frame/position/rotation owners>` |
| Light motion contract | `<strict diagnostic + relative hard gate>` | `<report>` | `<coverage>` |
| Procedural contract | `<world/light parity + collapsed-chain roots>` | `<report>` | `<hash>` |
| Sequence contract | `<successful contract>` | `<report>` | `<total/unique/duplicates/flags>` |
| Ground correction | `<value and unit>` | `<measurement report>` | `owner=proportion-target Pelvis local Z` |
| Multi-variant root parity | `<canonical/Pelvis/core/full/root equality or n/a>` | `<report>` | `<per-target source/hash>` |

## 当前候选

- Candidate ID: `<id>`
- Status: `working | current | superseded | rejected`
- VPK: `<path>`
- SHA-256: `<hash>`
- Manifest: `<path>`
- Static gate: `pass | fail | pending`
- Compiled VVD/VTX mapping gate: `pass | fail | pending`
- HLMV gate: `pass | fail | pending`
- Runtime gate: `pass | fail | pending-user-test`
- Runtime evidence sidecar: `<path/hash or none>`
- Known-bad negative control: `<candidate hash/report/expected failed check IDs>`
- Reused components: `<component/prior candidate/current hash attestation>`

## 已通过

- `<evidence-backed item>`

## 当前失败/阻塞

- 现象：`<symptom>`
- 证据：`<screenshot/report/log>`
- 已确认根因：`<root cause or unknown>`
- 受影响 source-of-truth：`<file>`

## 未验证假设

- `<assumption and required evidence>`

## 下一步唯一动作

```powershell
<exact next command>
```

预期输入：`<paths/hashes>`

预期产物：`<paths>`

成功门槛：`<machine-checkable conditions>`

## 不要做

- 不要编辑原始输入。
- 不要从目录中所有 VPK 猜当前候选。
- 不要跳过失败的上游 gate。
- 不要把项目实测参数当成通用值。
- 不要原地改写历史 manifest 来补录发布后的用户反馈。

## 最近变更

| 时间 | 变更 | 候选 | 结果 |
| --- | --- | --- | --- |
| `<timestamp>` | `<change>` | `<id>` | `<result>` |
