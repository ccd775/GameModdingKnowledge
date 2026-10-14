# 漫威蜘蛛侠2（Marvel's Spider-Man 2 PC）

## 范围

这里整理 PC 版《Marvel's Spider-Man 2》（Insomniac 引擎 i30，启动器显示 **v1.130.1.0**）用 Karin_Original 替换 Peter 和 Miles 的可复用合同。
内容来自 2026-10-12 → 10-14 的一个项目：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| v1 | 全部 108 个战衣 / 便装模型 + 3 个不戴面罩的头模型换成 Karin（一个合并网格、2×2 图集、一个材质）；面部骨骼绑定的表情；裙子权重修正；头部比例 1.45。弹簧物理只在 Miles「杂货铺猫咪战衣」的背包挂件上 | `runtime-confirmed`（用户实机：「整体效果可以」） |
| v2 | v1 + 弹簧物理覆盖 Peter / Miles 全部 91 套带面罩战衣：双马尾、侧发、前发、耳朵、丝带、尾巴，挂在带面罩战衣共用的头 actor 上 | `runtime-confirmed`（用户抽查两族多套战衣：「看起来都挺好」） |

快照只对 toc SHA-1 `318f4345f3a1`（游戏 v1.130.1.0）有效。**资产 id、段布局、actor 组件字段、exe 地址都是 `build-sensitive`**；
链参数、头比例、模型列表是 `case-derived`。

本作的主要贡献：

- **纯 Python 的 i30 读写**：toc / DAT1、`.model`（网格、蒙皮、关节、Look、动力学段）、`.texture`、`.material`、`.actor`。
  `.actor` 编解码对游戏全部 11,477 个 actor 逐字节往返。另有一个不依赖 Overstrike 的 `.stage` 安装器。
- **一次拟合，覆盖全部战衣**：每种骨架签名只拟合一次，按关节名重映射到 108 个目标模型，所有 LOD 共用一块几何。
- **从零写 `ModelAnimDynamicsDef`**（AnimDynamics 链），对 6 个原版模型逐字复现。
- **找到「物理只动 1 秒」的根因**：逆向 exe 的每帧门控（[物理](PHYSICS.md) §3），据此把物理挂到带面罩战衣共用的头 actor 上：
  打开 NeverCull、放大关节包围球、在 HeadManager 映射里补上胯部关节。

## 核心方法

- 先用 ALERT 的 `dat1lib` 读 toc，再用游戏根目录的 `dagstr` 解出资产名（CRC64 → id）。之后 `.model` 等格式全部由自己的 Python 解析。
- 每套战衣都有自己的身体模型，存档装备的战衣决定显示哪个，所以要替换**全部** 108 个目标模型；不戴面罩的头是单独的头模型。
- Karin 只换网格、权重、材质，不动游戏骨架和动画；新关节只在需要动力学的地方追加。
- 战衣模型自己带的动力学在游戏里只能跑 1 秒，所以物理要放在**有自己 owner actor 和 AnimController 的模型**上：
  v1 用蜘蛛猫背包挂件，v2 用带面罩战衣共用的头 actor（头部载体）。
- 每一类改动（几何、材质、表情、物理参数、挂接方式）单独进实机反馈；每轮都先过离线回读检查。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户在测试机上的口头反馈和截图，以及 agent 的截图；文档逐项写明是哪一种。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：toc 与资产头、`.stage` 与安装、`.model` 各段、蒙皮编码、Look 组、贴图与材质、`.actor`、战衣链与 loadout、HeadManager
- [构建流水线](BUILD_PIPELINE.md)：索引与提取 → 按骨架签名拟合 → 批量构建 → 表情 → 物理载体 → 打包，以及各步的离线闸门
- [角色拟合](CHARACTER_FIT.md)：重摆姿势、TPS 拟合、权重迁移、裙子、头比例、面部骨骼绑定、Look 组覆盖
- [物理](PHYSICS.md)：AnimDynamics 段布局、约束类型与调参、每帧门控、试过的四条挂接路线、头部载体的做法
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、证据分层、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：T0 → T23 的每一轮
- [便携工具包](../../portable-kits/marvels-spider-man-2/README.md)：全部 Python 工具、安装器、离线检查

## 公开边界

不含源模型、游戏资源、提取出的资产、发行 `.stage`、ALERT（GPLv3，用户自取）或 Overstrike。便携包里的脚本是项目脚本去掉本机路径后的副本；
Karin 专属的链表、拟合参数和模型列表是案例值，换模型或游戏版本时要按当前资源重新测量。
