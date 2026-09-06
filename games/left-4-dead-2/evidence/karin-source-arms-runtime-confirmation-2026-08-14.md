# Karin source-derived 第一人称手臂运行确认（2026-08-14）

## 证据等级

用户手工实机反馈。它高于静态、StudioMDL、SourceIO、HLMV 和 VPK 离线验证，但只覆盖用户明确确认的范围。

## 候选

- 文件：`Karin_PT_L4D2/release/KarinPT_Rochelle_SourceArms.vpk`
- bytes：`44,031,174`
- SHA-256：`D59B4B001AC2B63BF1E61A0E136BC8E6E9326DAE5AC99B8A30CE05FD270AA0CA`
- VPK entries：`33`
- first-person visible geometry：用户 `Karin_PT_Unified_Atlas.blend` 经已验收 world SMD、源 polygon manifest、保形 view-space placement 和权重转移/平滑生成。

## 先前现象

同一 payload 使用 66 字符长文件名时，游戏中显示原版 Rochelle。离线验证同时证明：

- VPK 33/33 payload 与 accepted loose tree 逐字节一致；
- world MDL/VVD/VTX/PHY 与先前已生效的 SelfIllum 候选完全一致；
- 当时未发现另一个已启用 VPK 提供相同 `survivor_producer` 路径；
- 两次地图测试都发生在游戏最终把 SourceArms 条目写为 enabled 之前。

## 修复动作

没有重编任何 payload。游戏关闭时执行组合挂载修复：

1. 使用唯一短 ASCII 名 `KarinPT_Rochelle_SourceArms.vpk`；
2. 移走旧长名副本；
3. 保持 VPK SHA-256 不变；
4. 在 `addonlist.txt` 中只启用一次并置于前面；
5. 完整重新启动游戏。

结构化修复记录：`Karin_PT_L4D2/reports/runtime/source-arms-short-name-mount-repair.json`。

## 用户确认

2026-08-14，用户在上述修复后的复测中回复“好了”。结合紧邻的故障与修复上下文，这确认：

- 短名 SourceArms 候选已进入游戏运行时；
- Karin 替换 Rochelle 的目标路径已经生效，不再回退到原版 Rochelle；
- 当前交付 VPK 的 source-derived 第一人称手臂候选可以继续作为正式候选，而不需要回退到参考 Mod 二进制 arms。

## 不能扩大解释的范围

本条反馈没有逐项列出每种武器、换弹、推击、药品、投掷物、倒地动作、FOV 或肩口极限姿态。因此知识库不得据此声称“全部第一人称动画与穿插测试通过”。这些仍应在后续 runtime matrix 中分别记录。

本次同时改变了文件名、旧副本、enabled 状态、优先级和重启时序，又没有故障会话的 `show_addon_load_order` 输出。因此可以确认“组合挂载修复有效”，但不能把 66 字符文件名单独宣布为唯一根因。短 ASCII stem 仍应作为保守发布合同。

## 关联证据

- `Karin_PT_L4D2/release/KarinPT_Rochelle_SourceArms.manifest.json`
- `Karin_PT_L4D2/reports/release/vpk-validation-source-arms-short-name.json`
- `Karin_PT_L4D2/reports/release/loose-tree-zoey-bile-selfillum-source-arms-smooth-final.json`
- `Karin_PT_L4D2/reports/runtime/source-arms-short-name-mount-repair.json`
- `Karin_PT_L4D2/reports/arms_hud/source-first-person-arms-world-smd-extract.json`
- `Karin_PT_L4D2/reports/arms_hud/source-first-person-arms-similarity-reference-weight-smoothing-unpruned24.json`
- `Karin_PT_L4D2/reports/compile/source-first-person-arms-similarity-reference-weights-smooth-final-studiomdl.json`

