# 案例：Karin_PicodraTech（2026-10-30 → 10-31）

源模型 `Karin_PT_Unified_Atlas.blend`（本库奥德赛的 PicodraTech 案例用的也是它）：10 个按材质合并的网格、一副 237 骨的骨架
（VRM 0 风格的骨名 `UpperLeg.L`、`Eye.L` …）、4 × 4096 图集。同一个 VRM（0.x）导入后是 457 根合并骨的乱骨架，不用。

做法（`build_pt.py`，`build_pbz.py` 的分支）：

- `bpy.data.libraries.load` 追加骨架和按角色选出的网格，按角色改名（头发、两套服装、皮肤、脸 …，丢掉 `Karin_Alpha`）；
  骨名映射到 Karin_Original 的 VRM 1 骨名（`BONE_RENAME`，顶点组一起改），所以关节拟合、面部形变、两张脸、隐藏三角和导出都是共用代码。
- 打开并烘焙的形状键：Hair_tail_volume_up、Ahoge_big、Foot_OFF、Toe_OFF；脸的 238 个形状键与 Karin_Original 同名。
- 比例 1.37（1.30 × 眼高比）。7 段布料（[物理](../PHYSICS.md) §2），合成的尾巴贴图（同一节 §5），`materials.json` 驱动 UE 脚本的分支。
- 范围默认与 Karin_Original 相同（成年两套服装、序章少年魂、物理与表情），独立的包 `z_KarinPT_P`；两套包一次只能装一个。这些是 agent 定的默认值，用户没有另外指定。

过程中修的问题：少年导入没有等资产注册表扫完，旧身体没删，导入并进了 Karin_Original 的槽（加扫描和断言）；UE 拒绝双马尾布料（4 个退化三角，加 `drop_degenerate`）；
尾巴合成图第一次缩成半分辨率（改成按 UV 岛装箱）；渲染检查脚本按节点名找 Principled BSDF 失败（节点名是本地化的，改按类型找）。

状态：第一版（10-30）和醉剑修复版（10-31）都构建、读回过（每个身体 7 个布料资产、头 78 / 睫毛片 77 / 少年头 77 个形变、眨眼自测通过），装进过游戏；
用户没有反馈（`offline-accepted`）。法线图集还没用，服装不加自发光。
