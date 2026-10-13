# 案例：另外四个 Karin 模型 → 女主默认服装（2026-10-13）

**用户需求**：「再做几个新的 mod」，用共享模型库里的四个源模型各做一个，替换同一个目标。源模型不随本库发布。

| profile | 源模型 | 服装与物理链 | pak（UE 资产目录） |
| --- | --- | --- | --- |
| `opt` | Karin_Original_PicodraTech（Original 体型 + PicodraTech 服装，.blend） | 双马尾、尾巴、侧发；外套下摆 9 片（`accessories_pelvis_01..04_l/r` + `_01`，铰在腰部）、耳机线 2 根（`cloth_pelvis_A_l/r`）、背后长飘带（`cloth_spine_03_A`） | `pakchunk99-KarinOriginalPicodraTech_P`（`Karin_OPT`） |
| `pt` | Karin_PicodraTech（新版体型 + PicodraTech，统一图集 .blend） | 同上；双马尾及膝 | `pakchunk99-KarinPicodraTech_P`（`Karin_PT`） |
| `umb` | Karin_Umbrella（新版体型 + 都市夹克、护目镜） | 双马尾、尾巴、侧发；两袖垂下的绳带（`upperarm_sleeve_01_l/r`，软驱动 0.6 Hz） | `pakchunk99-KarinUmbrella_P`（`Karin_UMB`） |
| `y` | Karin_Y（新版体型 + 和风服装，约 19.8 万顶点） | 双马尾、尾巴、侧发；右臂长袖（`lowerarm_sleeve_01_r`）、袖带（`_03_r`）、左后长摆（`cloth_spine_03_A`）、右侧两片腰摆（`cloth_pelvis_A_r/l`）、前后腰布（`accessories_pelvis_01/02`）、腰带垂饰（`accessories_pelvis_01_r/02_r`） | `pakchunk99-KarinY_P`（`Karin_Y`） |

## 1. 做法

- 把只适用于 Karin_Original 的脚本改成按 profile 构建（[构建流水线](../BUILD_PIPELINE.md) §8）：源模型归一化、按网格改名和丢弃、材质映射、
  透明面剔除、权重折叠规则、悬挂件回正、骨链规格、贴图都进 profile。
- 回归：`karin_original` profile 的构建与已发行 v6 逐字节一致（`cloth.json` 与 blend 网格数据），全部改完后又验证一次。
- 每个模型独立的 UE 资产目录，pak 之间不共享资产路径；`cook_pak.ps1 -AssetDir` 只收自己的目录。
- 所有模型缩放到同一头部关节高度（147.1 cm）。
- 图集模型的材质：每页一张 BaseColor + ComboMap，AO 按页烘焙（[材质与贴图](../MATERIALS_AND_TEXTURES.md) §4）。Karin_Y 的脸和皮肤共用一页，按网格分槽。

## 2. 离线发现并修掉的问题

- Karin_Y 的长袖与袖带、Umbrella 的袖绳在 T→A 重摆后转了 59°，甩进腿里 / 身后 → `hang` 回正。
- 关掉了「静止时与腿重叠」的碰撞后，外套下摆和长袖穿过腿 → 新式链保留腿部碰撞；袖子碰撞半径 ×0.12。
- PicodraTech 的 OuterB 下摆沿口袋绳走 → 显式路径 + 子树。
- Karin_Y 去掉了两把苦无（左手握的、嘴里叼的）：空手格斗动作和表情动画会让它们穿模。

## 3. 证据与限制

- `offline-accepted`：四个模型的静止 / 跑步 / 前踢预览；PicodraTech 和 Y 的眨眼、Ah、Oh；构建报告无未映射的组；
  烘焙后的 pak 读回，材质槽和后处理动画蓝图都指向各自目录。
- **没有进游戏**（当时测试机桌面被另一个会话占用；装一个就要先移出用户的 Karin_Original pak）。
- 外套下摆、长袖等都是单摆式骨链，不是布料：大动作时可能穿模，需要实测后再调（`T_*` 预设的刚度、`rscale`）。
- 以后可能：Y 的长摆和长袖改 NvCloth、真正的法线贴图。
