# 幻兽帕鲁（Palworld）

## 范围

这里整理 Steam《幻兽帕鲁》（App `1623730`，UE 5.1.1，单个 legacy pak）玩家角色替换的可复用合同，
来自 2026-10-13 的一项交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 女性玩家默认服装 `SK_Player_Female_Outfit_OldCloth001`（初期装备）r4 | 从 VRM 源模型完整构建身体（服装、头发、兽耳、尾巴，Karin 自己的比例）；服装层动画蓝图 `ABP_F_OldCloth001_Implimentation` 里 7 个 KawaiiPhysics 节点；所有女性脸型换成 Karin 的脸并带 11 个面部变形；所有玩家发型换成不可见网格 | 加载、比例、物理运行、眨眼为 `runtime-confirmed`（用户实机）；r3 的物理手感被用户判为「偏硬，耳朵尤其不柔软」，跑动时大腿根穿出裙片（`runtime-rejected`）；r4 按离线模拟重调后 `runtime-load-pass`，手感待用户反馈 |

快照只对 buildid `25246127`（游戏 v1.0.5.102999）有效。**资产路径、骨数、脸型和发型的数量、usmap 版本都是
`build-sensitive`**；骨名映射、胶囊、物理参数是 `case-derived`。

与其它 UE 目录的关系：剑星（本库 `games/stellar-blade/README.md`）同样把 KawaiiPhysics 链落到游戏骨架的配件链上，
本作的编辑器插件 PalModTools 就是剑星 SBGraphLib 的 UE 5.1 移植。区别：剑星的骨架用 Animation 平移重定向，只能在
AnimBP 里改比例；本作的人形骨架对 4075 根骨用 Skeleton 平移重定向，网格自己的 bind 姿势就决定比例，所以 Karin
直接用自己的比例。师父（本库 `games/sifu/README.md`）也用占位资产只 cook 自己的资产，但物理用 RigidBody。

本作的主要贡献：

- **不改玩家蓝图，替换服装层的实现蓝图。** 玩家 `ABP_Player` 有一个接口为 `ALI_HumanCloth` 的链接动画层 `ClothLayer`，
  默认服装在数据表里链接 `ABP_F_OldCloth001_Implimentation`。用同路径的新蓝图实现这个层，物理就跑在替换后的网格上。
- **KawaiiPhysics 1.17.1 的离线移植 `kawaii_sim.py`**：用游戏的冲刺、慢跑动画驱动 Python 版的 Kawaii 步进，量出裙摆
  顶点陷进大腿的数量和链在角度限制上停留的时间。手感「偏硬」和「大腿穿出」都在离线复现后才改参数。
- **Kawaii 的执行顺序决定调参方向**：角度限制在碰撞之后执行；跟随世界移动的滞后把链压在限制上，看起来就是「硬」。
- **表情直接用游戏 C++ 驱动的变形名**：`PalFacialComponent` 按名字驱动 11 个形变，把 Karin 的形态键配方烘成这些名字即可，
  不需要动画或蓝图。
- **只装 pak、不需要 UE4SS**：三个 `_P.pak` 放进 `~mods`，未加密、不需要 `.sig`。

## 核心方法

- 先用 CUE4Parse（项目的 PalExport）配 usmap 把玩家蓝图、服装数据表、目标网格、骨架、服装 AnimBP dump 成 JSON，
  再决定替换哪一层。游戏是 unversioned cook，没有 usmap 什么都读不出来。
- 身体网格 = 原版 OldCloth001 的 65 根基础骨 + 改名后落在游戏骨架配件链上的物理链骨；骨的朝向等于原版，位置用 Karin 的。
- UE 5.1 内容工程 `Pal`：骨架、物理资产、父材质、`ALI_HumanCloth` 都是游戏路径上的占位（不打包）；材质实例挂在游戏的
  材质实例下，只覆盖贴图参数，运行时用游戏的着色器。
- 无界面构建：编辑器 Python（`-run=pythonscript`）导入、生成 AnimBP，`-run=cook -unversioned`，repak 打 V11 pak。
- 物理参数的唯一来源是 `physics_tune.json`；改参数 → 离线模拟 → 导出解析后的参数文件 → 生成 AnimBP → cook → 实机。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的观察（眨眼、手感、穿模截图）和 agent 在远程测试机上的截图、Steam F12 连拍。物理是否在跑，看的是
跑动、跳跃时不可能由刚性挂接产生的姿态（双马尾水平后飘、跳起时上扬），而不是单张静止截图（见剑星的教训）。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：pak 与加载、玩家角色的组成、骨架与重定向、服装层、面部组件、材质、幻化
- [构建流水线](BUILD_PIPELINE.md)：提取 → Blender 构建 → UE 导入 → AnimBP → cook / pak → 读回 → 安装与发布
- [角色拟合](CHARACTER_FIT.md)：比例与重摆、权重、物理链改名、面部变形、双面裙、隐藏发型、材质
- [Kawaii 物理](KAWAII_PHYSICS.md)：节点与链、胶囊、1.17.1 的步进顺序、离线模拟、r3 → r4 的调参
- [开发工具](DEV_TOOLING.md)：PalExport、PalModTools 插件、命令行 UE、远程测试机
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理，以及被证伪的假设
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、实机闸门、发行包、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：r1 → r4 的每一轮
- [便携工具包](../../portable-kits/palworld/README.md)：Blender 构建与 Kawaii 模拟脚本、UE Python、编辑器插件源码、PalExport 源码、PowerShell 工具

## 公开边界

不含源模型、参考 mod、游戏资源、提取出的 JSON / uemodel / ueanim、usmap、发行 pak 或 KawaiiPhysics 源码。
便携包里的脚本是项目脚本去掉本机路径后的副本；Karin 专属的骨名映射、链表、胶囊和参数是案例值，换模型时按当前资源重新测量。
