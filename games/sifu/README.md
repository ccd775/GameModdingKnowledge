# 师父（Sifu）

## 范围

这里整理 Steam《Sifu》（App `2138710`，Sloclap 改过的 UE 4.26）女主默认服装替换的可复用合同，
来自 2026-10-12 → 10-13 的两个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original v6 | 从 VRM 完整构建的女主网格（W 骨架 + 13 根 Base_skeleton 备用骨）、贴图与 MIC、表情（游戏面部姿势资产驱动）、眼球、NvCloth 裙摆、骨链物理（后处理动画蓝图里的 RigidBody 节点） | `runtime-confirmed`（用户本机实机：「基本好了」）；裙摆按用户反馈改了五轮 |
| 另外四个 Karin 模型 v1 | 同一套脚本改成按模型配置（profile）：Karin_Original_PicodraTech、Karin_PicodraTech、Karin_Umbrella、Karin_Y；每个模型自己的资产目录与物理链 | `offline-accepted`（预览、烘焙后 pak 的引用检查）；未进游戏 |

快照只对 build `18739835`（游戏内版本 `v_1.29_6.775`）有效。**pak 格式、资产路径、槽位号、骨数是 `build-sensitive`**；
骨链参数、裙摆半径等是 `case-derived`。

与其它 UE 目录的关系：剑星（本库 `games/stellar-blade/README.md`）同为 UE 4.26，也在后处理动画蓝图里做次级物理（KawaiiPhysics），
也只能用游戏骨架里已有的骨；但它走 IoStore，骨架用 Animation 平移重定向，网格改不了比例。本作没有 IoStore，骨架的
OrientAndScale / AnimationRelative 重定向允许网格用自己的比例（[技术合同](TECHNICAL_CONTRACTS.md) §4），物理用引擎自带的 RigidBody 节点。

本作的主要贡献：

- **只装 UE 编辑器就能做的完整替换**：内容工程起名 `Sifu`，在游戏路径上放占位资产（母材质、物理资产、骨架），
  只把自己的资产 cook 进 pak；材质实例挂在 W 原版材质实例下，直接继承游戏的静态开关组合；
- **把次级物理挂在网格自己的后处理动画蓝图上**：RigidBody 节点 + 专用物理资产，用骨架里本来就有的备用骨当宿主，
  不用改游戏的动画蓝图；
- **PhysX 加速度驱动的定量调参**：从源模型 VRM spring 的参数反推驱动刚度与阻尼，解决了「像钟摆一样晃」；
- **UE 4.26 NvCloth 裙摆**：代理网格、锥形胶囊、backstop（插件里补上的）、求解频率；以及一个离线的时间步进替身
  （`skirt_sim.py`）用游戏动画逐帧检查穿模；
- 同一套脚本**按 profile 构建多个源模型**：源模型归一化、骨名统一、悬挂件回正、在备用骨上自动搭链。

## 核心方法

- 先用 CUE4Parse 把目标网格、骨架、材质、动画蓝图、面部姿势资产 dump 成 JSON / glTF，再决定方案。
- 替换女主默认服装网格 `SK_W_MainChar_01`，不改骨架和动画：位置用 Karin 的比例（×1.4），旋转逐骨等于 W 的参考姿势，
  靠游戏骨架的重定向设置把动画搬过来。
- 权重跟 W 的分布走（四肢只上扭转骨、躯干按 W 的脊椎分布），脸用 W 的面部权重经 TPS 变形迁移，再拟合眼睑和嘴。
- 每一类改动（几何、权重、材质、布料、骨链）单独进实机反馈；裙摆的每一轮都先用离线动画替身复现用户看到的问题。
- 烘焙后的 pak 用 CUE4Parse 读回，核对材质槽和后处理蓝图真的指向自己的资产（曾经因为 UE Python 的结构体副本，
  所有槽都是 `null`，游戏里整个人发暗）。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的口头反馈，以及 agent 在测试机上的截图和连拍录屏；文档逐项写明是哪一种。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：pak 与加载、目标资产与使用者、骨架与重定向、材质槽、面部与眼球、物理资产引用
- [构建流水线](BUILD_PIPELINE.md)：提取 → Blender 构建 → 贴图 → UE 内容工程 → cook / pak → 读回检查；profile 与多模型
- [角色拟合](CHARACTER_FIT.md)：重摆姿势、关节位置、权重、躯干分布、表情、眼球
- [材质与贴图](MATERIALS_AND_TEXTURES.md)：W 材质实例做父级、ComboMap 通道、变老参数中和、AO 烘焙、顶点色
- [物理](PHYSICS.md)：RigidBody 后处理骨链、驱动数学、NvCloth 裙摆、backstop、离线替身、多模型的链规格
- [开发工具](DEV_TOOLING.md)：SifuExport（CUE4Parse）、编辑器插件 SifuModTools、命令行跑 UE Python、远程构建机、实机连拍
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、证据分层、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：v1 → v6 的每一轮反馈
- [案例：另外四个 Karin 模型](cases/KARIN_VARIANTS.md)：profile 化与四个 v1
- [便携工具包](../../portable-kits/sifu/README.md)：Blender 构建脚本、UE Python、编辑器插件源码、SifuExport 源码、PowerShell 工具

## 公开边界

不含源模型、游戏资源、提取出的 JSON / glTF、发行 pak、游戏 AES 密钥或 UE 引擎源码。便携包里的脚本是项目脚本去掉本机路径后的副本，
Karin 专属的骨名、链表和参数是案例值，换模型时要按当前资源重新测量。
