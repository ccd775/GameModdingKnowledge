# Karin Nyako -> Hunter 角色替换案例

本文记录 `L4d2/nyako_replace_hunter` 从待机横向张臂、错误修正导致歪头，到最终
用户验收的完整闭环。这里的骨数、角度、误差、材质数和 VPK 身份都是项目实测值，
不能复制为其他角色或其他特感的默认参数。

## 1. 最终状态与证据等级

最终候选于 2026-08-18 收到用户明确反馈“验收通过”，因此其运行状态为
`user-confirmed pass`。追加证据见
[Karin Nyako -> Hunter 用户验收](evidence/karin-nyako-hunter-user-acceptance-2026-08-18.md)。

打包时的 `reports/package/package-validation.json` 和 compiled audit 仍保留
`runtime_game_test: not_run_by_design`。这是构建时的历史事实，不应在收到反馈后原地
改写；用户验收由独立 sidecar 追加。

最终候选身份：

| 项目 | 实测值 |
| --- | --- |
| VPK | `dist/Karin_Nyako_Hunter.vpk` |
| bytes | `37,525,555` |
| entries / payload bytes | `41` / `37,523,904` |
| SHA-256 | `54B4838F3770D4D49B9C7D6E51162B58C8389EFD056FD4CE1117AE49E17CB061` |
| 用户状态 | `user-confirmed pass` |

## 2. 四个独立运行时目标

本项目不是只替换一个 MDL，而是同时维护四个 companion family：

- `models/infected/hunter.{mdl,vvd,dx90.vtx,phy}`
- `models/infected/hunter_l4d1.{mdl,vvd,dx90.vtx,phy}`
- `models/v_models/weapons/v_claw_hunter.{mdl,vvd,dx90.vtx}`
- `models/v_models/weapons/v_claw_hunter_l4d1.{mdl,vvd,dx90.vtx}`

世界模型与第一人称 claw 是独立 bind 目标。本案世界模型采用 source-fit skeleton，
可见网格不做逐骨 rest rebake；两套 claw 则分别面向各自原生 41 骨 viewmodel rest
做 bind-space retarget。由此得到一条重要通用边界：**同一个 Mod 可以按 runtime
target 选择不同 bind 策略，但同一份几何不能同时重复应用 source-fit 和 target-fit。**

## 3. 参考包与原生目标分别拥有什么权威性

用户给出的动漫 Hunter 参考包是有用证据，但不是完整 canonical：

- 参考 world 为 105 骨，其中包含 53 根原生 core 与 52 根额外骨；有 32 条 jiggle、
  17 个 hitbox、5 个 attachment，但缺原生 `forward`，且没有 PHY。
- 参考 arms 为 40 骨，缺原生左右 Ulna/Wrist 四骨，并增加自定义 twist/Armature；
  不能直接当当前 claw ABI。
- 参考包材质存在闭包问题：VMT 引用名与实际 VTF 名不一致，并缺少完整感染者 burn
  proxy，因此不能直接复制为最终材质闭包。

当前游戏原生目标提供运行时 ABI：

- world 为 53 根 core、6 个 attachment、17 个 hitbox、Hunter animation include，
  以及 18-solid / 510-triangle physics source；
- 两套 claw 各为 41 骨，保留 Ulna/Wrist 接口；
- L4D2 与 L4D1 必须分别编译和审计，不能复制已编译 companion 后只改名。

最终采用的证据分工是：参考 `Body.smd` 只提供已成功动漫 Hunter 的 core world
rotation frame；Nyako 源提供关节 pivot、可见几何、权重和动态骨；原生当前版本提供
name/index/parent、attachment、hitbox、include、viewmodel ABI 与 physics 合同。

Nyako VRM 的 humanoid map 也不是 canonical：`leftEye` 实际指向 `Hair_tail_L`，
`rightEye` 指向 `Ahoge`。因此 VRM 只用于 spring/collider 语义和作者动态意图，眼/头/
身体映射仍由最终 Blend、父链、权重与空间位置确认。

## 4. 用户反馈链与两个独立根因

### 4.1 第一类错误：比例动画把 T Pose 侧轴位移叠进 idle

早期候选混用了源关节位置与 Hunter rotation，生成的 compiled `a_proportions` 又没有
严格等于 target bind 减原生 animation bind。Forearm 与 Hand 的比例 delta 含约
`+8` Source unit 离轴分量，运行时把横向张臂长期叠加到 idle。

旧候选关键误差：

- L Forearm 预期与实际 delta 的误差约 `8.94 su`；
- L Hand 误差约 `9.13 su`；
- 站立 idle 手腕相对锁骨只向下约 `-9.41..-2.42 deg`，因此视觉接近横张。

这不是“Hunter idle 动画缺失”，也不是简单 L/R 交换。53 根原生 core 的名称、父级和
include ABI 都存在；错误发生在 bind/proportion 接口。

### 4.2 第二类错误：为迁就 native bind 而预扭整张可见网格

第一次修正把 53 根 core 强制换成 native Hunter rotation，再用逐 influence
bind-space LBS 对整张 world mesh 预变换。编译后的骨骼运动学因此看似更接近 Hunter，
但可见几何已经被另一套 rest frame 整体扭曲：

| 指标 | 被否决候选 |
| --- | ---: |
| 导出 corners | 146,196 |
| 位移超过 0.01 su | 98.03% |
| 平均 bind displacement | 11.7368 su |
| 最大 bind displacement | 73.0668 su |

用户截图显示头部歪斜、下巴前伸，而且手臂仍未达到预期。这个反例说明：**骨关节轨迹
接近正确，不等于带权网格最终可见姿势正确。** inverse bind 与预扭几何必须单独审计。

该错误 VPK 的 SHA-256 为
`D037200F2B357AF93C5A1CBD7BEC2B0574C9872EDF27F94559EBF39ED8564212`，保存在
`work/releases/rejected_native_bind_retarget_20260816/`，只能作为反例，不得部署。

## 5. 已验收的 world source-fit bind

最终 world 采用以下合同：

1. 保留 53 根 Hunter core 的 name/index/parent。
2. 每根 core 的 world rotation 精确取自成功动漫 Hunter
   `references/decompiled/reference_world/Body.smd`。
3. 每根有映射 core 的 world pivot 取经过统一 Source 尺度转换的 Nyako joint。
4. 由 `parent_world^-1 * desired_world` 重新计算 parent-local transform。
5. 源没有直接对应的 `Spine1/Spine2`，按成功参考脊柱累计段长比例插值，不使用任意
   `1/3`、`2/3`。本案比例近似 `9.662279e-7` 与 `1.0`，这是兼容参考的项目值，
   看起来反常也不能复制到新角色。
6. 32 根动态骨保留 Nyako source world pivot/rotation，再相对选定 target parent
   反算 local；不能把 source-local 矩阵直接接到已更换 frame 的 parent。
7. world 网格只做统一坐标/尺度变换与权重映射，不做逐骨 LBS rest rebake。
8. 为全部 85 根目标骨生成 `$definebone`，防止 StudioMDL 朝 animation baseline
   重组 custom rest。

项目门禁结果：53 根 core rotation 最大误差 `0 rad`，pivot 最大误差 `0 su`；
146,196 个 world corner 的 moved/mean/max displacement 全部为 `0`。编译后 85/85
骨名和 parent 与源一致，world rotation 最大 roundtrip 误差 `0 deg`，world position
最大误差 `0.000023 su`。

### 为什么不直接复制 Blender/VRM rotation

Blender 常用 bone Y 轴描述骨长方向，而 ValveBiped/Source 接口的轴约定不同。Nyako
raw Blender frame 与可工作的 Source frame 在 Head、UpperArm、Forearm 等处可相差
约 90 到 180 度。直接把 `bone.matrix_local` 当 Source world rotation 会造成 Head
roll、手臂轴翻转或 twist 错位。

通用做法是显式执行 DCC-to-Source basis conversion，或者像本案一样锁定同 slot、同
动画族且已被运行证明的 Source custom frame。后者仍必须作为新的 composite bind
candidate 验收，不能因为“来自成功参考”就跳过 pivot、local-axis、动画和几何门。

## 6. Hunter 本地动画源的职责不能混用

第二个关键修复是拆开本地序列资产的角色：

| 资产/序列 | 本案正确内容 |
| --- | --- |
| proportion target / `a_proportions` target | Nyako pivot + 成功参考 custom rotation |
| corrective / `reference.smd` | 原生 Hunter local translation + custom rotation |
| `CustomModel.smd` | 53 core 使用完整原生 Hunter pose；32 dynamic 使用 custom rest |
| `ragdoll.smd` | 53 core 使用完整原生 Hunter pose；32 dynamic 使用 custom rest |
| compiled `a_proportions` | target-native 的 translation-only delta；rotation identity |

失败候选把 `reference`、`CustomModel`、`ragdoll` 都写成同一套 projected/custom pose。
这样即使 bind 或比例 delta 的某些静态数值变好，默认/本地序列仍可能把 T Pose 职责
泄漏到运行姿势。

以上资产名和 101 帧是 Hunter 本案合同，不是所有特感的固定模板。通用规则是：从
当前原生模型、同目标成功样本和 compiled sequence 反证每个本地序列的职责，并在最终
MDL 中逐序列比较 position/rotation source。

## 7. 编译后的比例门与动作门

### 7.1 不要用“Y/Z 必须为零”代替真实合同

本案最终 L Forearm local position 约为
`(10.515105, 0.020254, -0.010722)`，L Hand 约为
`(9.721514, -0.192526, 0.024775)`。这些小离轴值来自已验证 Source frame，并非错误。

真正应检查的是每根公共骨：

```text
compiled_proportion_translation(b)
  ~= compiled_target_bind_local_position(b)
   - native_animation_bind_local_position(b)
compiled_proportion_rotation(b) ~= identity
```

最终两套 world 均覆盖 53/53 core 和 101 帧；translation 最大误差
`0.003148004 su`，低于项目门 `0.05 su`；rotation identity 最大误差 `0`，项目门为
`1e-4 rad`。

`CustomModel`、`ragdoll`、`reference` 还分别审计 52 根非 root core。root 因
StudioMDL animation basis 被明确排除，不能无说明地跳过。项目门为 position
`0.02 su`、rotation `0.01 rad`，三组均通过。

### 7.2 合成外部 ANI 才能直接观察 idle 运动学

HLMV 未取得有效姿势视图时，本项目把 `anim_hunter.ani` 的真实 idle frame、候选
compiled bind 和 `a_proportions` 合成，比较手腕相对锁骨向量与 Head quaternion：

| 探针 | 最终候选 | 被否决/旧坏候选 |
| --- | --- | --- |
| `Idle_Standing_01` 左手下倾 | `-39.94..-35.96 deg` | 约 `-9.41..-5.29 deg` |
| `Idle_Standing_01` 右手下倾 | `-38.35..-33.45 deg` | 约 `-7.54..-2.42 deg` |
| `Idle_Crouching_01` frame 0 左/右 | `-63.01 / -55.38 deg` | `-28.96 / -22.99 deg` |
| idle Head 与成功参考最大旋转差 | 约 `0.000002 deg` | 不适用 |

这些角度只能作为本案正负对照。通用门应从 compatible known-good、known-bad 与当前
动画采样重新校准；关键是它检查真实关节运动学，而不是只看静态 SMD 或全局 edge
分位数。

## 8. Attachment、hitbox、physics 与双 world 变体

source-fit 改变 pivot 后，不能默认 attachment/hitbox 正确，也不能为了保留 stock world
坐标把它们反向拉离角色。应分别审计 local interface 与最终几何关系。

本案结果：

- 6/6 attachment 保留；相对 native 的 local matrix 最大误差 `0.0000114`；
- `forward` 距可见面部最近表面 `0.139 su`；手、脚、blur 挂点也靠近对应几何；
- 17/17 hitbox 的 bone、hitgroup、local min/max 与原生和成功参考逐项一致；
- body+face 顶点的 hitbox union 覆盖率 `89.44%`，外部距离 P99 `0.862 su`、
  最大 `1.949 su`；头发、尾巴和服饰不计入身体 hitbox 覆盖门。

L4D2/L4D1 world 使用同一 custom bind，但分别从各自 modelname 同轮编译 MDL/VVD/
VTX/PHY。两份 physics 源可相同，已编译 PHY 仍不能复制，因为 companion checksum
分别属于各自 world family。本案 world checksum 为 `9CF0FEF5` 与 `93D750B9`。

## 9. 第一人称 claw 的独立策略

参考 Mod 的 40 骨 arms 不是 canonical viewmodel ABI。本案从当前原生 L4D2/L4D1
各自 41 骨 reference 建立目标，保留 `L/R_Ulna` 与 `L/R_Wrist`，再把选定的 Nyako
手臂几何分别做 bind-space retarget：

- 每套源 arms 为 8,907 triangles；
- 每套 compiled LOD0 为 5,731 vertices；
- 两套均无 PHY；
- checksum 分别为 `0BE9BE3D` 与 `2D44462F`。

这再次说明“world source-fit 不做 LBS”不能扩写为“整个 Mod 的所有模型都禁止
bind-space retarget”。策略属于具体 runtime target 与具体几何，必须分开选择和验收。

## 10. HLMV 路径陷阱与替代证据

首次 HLMV 尝试使用相对 model path，工具按启动 cwd 而不是预期 compile sandbox 解析，
显示了错误路径下的红色 `ERROR`。后续 HLMV 进程不稳定，最终没有取得可用的当前模型
姿势视图。

因此本案从未把 HLMV 记为 pass。离线阶段改用：compiled bind roundtrip、compiled
proportion/sequence 解码、真实 ANI 动作合成、关节向量、Head quaternion、几何
displacement 与 VTX mapping。用户最终实机验收提供了更高等级证据。

可迁移结论：HLMV 无有效结果既不是视觉通过，也不能自动证明模型失败。先锁定绝对
preview path 与控制组；若工具门 unavailable，则保留 unknown 状态和替代证据，最终
仍由游戏/用户运行门闭环。

## 11. 编译、材质与发布闭包

最终两套 world 各为 85 bones、93 sequences、33,816 LOD0 vertices、18-solid PHY；
两套 arms 各为 41 bones、5,731 LOD0 vertices。四组模型均通过 MDL/VVD/VTX checksum、
top-3 skinning与逐 bodypart/model/mesh/strip-group VTX mapping。

材质闭包为 18 VMT + 7 VTF：4 张 DXT5 ColorAlpha、3 张 DXT1 normal、12 mip；透明
只使用 alphatest，所有 VMT 自包含 Hunter burn proxy。最终 VPK 的 41 entries 由
14 model companions、18 VMT、7 VTF、2 addon metadata 组成，loose/VPK 的 path、
CRC、bytes、SHA-256 逐项一致。

所有数量都是本项目身份，不是新项目模板。真正通用的是显式 manifest、打包前重哈希
compiled/UV 报告、拒绝 QC/SMD/参考资产/compile-only sidecar 和逐 entry payload
闭包。

## 12. 可迁移的反面案例与注意事项

1. 动漫角色通常希望保留原始体型，但“只对齐头/关节位置”仍必须建立完整
   rotation+pivot+parent composite bind；只搬骨头 head 不足以定义可工作的轴。
2. raw Blender/VRM bone rotation 不是 ValveBiped rotation；没有 basis conversion 时
   宁可使用已锁定且同 slot 的 Source custom frame。
3. source-fit world 不应再做一次逐骨 target-fit LBS；几何 displacement 必须成为硬门。
4. 骨骼 idle 轨迹正确不代表网格没有被 inverse bind/prepose 扭坏；关节门与几何门要
   分开。
5. `reference`、`CustomModel`、`ragdoll` 的名字不能推断内容；必须从成功合同和编译
   结果验证职责。
6. 小的 child local Y/Z 分量不等于错误；审计 target-native delta 和代表动作，不要
   用“全部归零”破坏已验证 frame。
7. helper pivot 插值应继承已验证链的累计比例；不要随手平均。近零段长只要有证据也
   可能是接口设计的一部分。
8. 当前原生 ABI 优先于示例 Mod。示例漏 attachment、缺 PHY、少 viewmodel 骨或材质
   闭包错误时，只能选择性吸收其已证明部分。
9. 同一可见角色的 L4D2/L4D1 world 与 claw 仍是四个独立编译目标，不能靠重命名复制
   companion。
10. VRM spring/collider 是动态语义和相对意图证据，不是 Source 参数表。本案从 79 个
    spring group、15 个 collider group、36 个 collider 中选择 32 根动态骨并保守映射；
    这些数量和参数都不可复制。
11. 已知坏候选应连同 hash、报告和截图保留。用户截图推翻静态推断后，应给缺失的数据
    层补门，而不是改写旧报告成“从未通过”。

## 13. 证据路径

- 项目状态：`L4d2/nyako_replace_hunter/PROJECT_STATE.md`
- 构建 SOP：`L4d2/nyako_replace_hunter/docs/SOP.md`
- 失败诊断：`L4d2/nyako_replace_hunter/reports/idle-arm-head-sourcefit-fix-20260816.md`
- bind/geometry：`L4d2/nyako_replace_hunter/reports/build/model-build.json`
- QC/sequence/definebone：`L4d2/nyako_replace_hunter/reports/build/modelsrc-build.json`
- compiled 比例、序列与 VTX：`L4d2/nyako_replace_hunter/reports/compiled/compiled-model-audit.json`
- UV：`L4d2/nyako_replace_hunter/reports/uv/exported-uv-audit.json`
- 材质：`L4d2/nyako_replace_hunter/reports/materials/material-build.json`
- package：`L4d2/nyako_replace_hunter/reports/package/package-validation.json`
- 用户验收：[2026-08-18 验收 sidecar](evidence/karin-nyako-hunter-user-acceptance-2026-08-18.md)

这些项目报告中的 `accepted` 只代表各自静态/离线门；最终运行状态由追加用户证据
提供，二者应按时间顺序共同保留。
