# 往日不再（Days Gone）

## 范围

这里整理 Steam《Days Gone》经典版（App `1259420`，beta 分支 `days_gone_classic`，build `10034136`，Bend 改过的 UE 4.11）
主角迪肯（Deacon）替换的可复用合同，来自 2026-10-15 → 10-16 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 迪肯 t31 | 从 VRM 构建、全部几何放进头部网格 `deacon_head_standard`（所有 66 个 look 的主姿势组件）；自带材质与贴图；头发 / 耳朵 / 狐尾 / 丝带 / 裙摆的次级物理（往游戏动画蓝图里插入的逐骨 AnimDynamics 弹簧节点）；表情（脸皮蒙到迪肯的 280 个 `face_*` 关节）；眨眼（放大骨 + CopyBone）；对话口型（按口型逐顶点解出的嘴部权重） | `runtime-confirmed`：物理、眨眼、口型、头发甩动幅度各自经用户实机反馈后确认（「这几项都好了」「眨眼相关的都正常了」「看起来感觉挺好的」「看起来可以了」） |

快照只对 build `10034136` 有效。**pak 格式、包版本号、骨数、动画蓝图节点数、关节名是 `build-sensitive`**；
放大倍数、弹簧参数、口型映射表是 `case-derived`。新版（Remastered）分支没有验证过。

与其它 UE 目录的关系：剑星、师父是 UE 4.26，次级物理放在网格自己的后处理动画蓝图里；本作是 UE 4.11 的 Bend 改版，
玩家网格没有后处理动画蓝图可挂，只能**改游戏自己的动画蓝图**（`Deacon_VimBlueprint`），而且是在**已烘焙的包里做图手术**，
没有编辑器里的源蓝图。

本作的主要贡献：

- **在已烘焙的 UE 4.11 动画蓝图里插节点**：理清 `AnimNodeProperties` 的正序 / 倒序两套索引，在类字段链头部插入新节点、
  把所有旧的 pose `LinkID`（包括数组里的）加 M，插了 101 个节点（91 个弹簧 + 10 个 CopyBone）仍能正常加载与播放；
- **逐骨 AnimDynamics 当弹簧骨**：单刚体节点 + 角度弹簧 + 角度限制 + 平面限制，替代在游戏里完全不起作用的 PhysX 额外刚体约束；
- **网格专用骨 + 改烘焙后的参考姿势**：给不在骨架里的骨（`KO_*` 物理骨、`KB_*` 眼睑骨）设旋转和缩放，配合 CopyBone 把
  迪肯 0.8 cm 的眼睑位移放大成动漫眼 3.9 cm 的闭眼；BoneDrivenController 在本作里完全无效；
- **按口型解嘴部权重**：迪肯的口型是 17 个叠加姿势，按它们和 Karin 自带 VRM 口型的对应关系逐顶点做非负最小二乘，
  让动漫嘴在脸内张开；
- **CUE4Parse 解不了的面部动画**：`AKF_PerTrackCompression` 的面部动画自己解码（`anim_pertrack.py`）。

## 核心方法

- 先用 CUE4Parse（DgExport）把玩家 pawn、look、骨架、头部网格、动画蓝图、面部动画 dump 出来，再决定方案。
- 只替换头部网格：Karin 的全部几何、材质槽都放在 `deacon_head_standard` 里；其余部件在 look 里指向不可见材质。
  骨架用游戏的 `deacon_master_Skeleton`（547 骨），网格可以多带骨（网格专用骨在游戏里能用）。
- UE 4.11.2 编辑器里建一个名为 `BendGame` 的内容工程，只负责导入 FBX 和 cook；材质实例、look、骨架引用都在 cook 之后
  用 Python 改二进制（游戏的材质实例带内联着色器图，不能挪动位置）。
- 每一类改动（几何、物理、眨眼、口型、物理参数）单独进实机反馈；面部改动先在 Blender 里用游戏动画数据模拟蒙皮。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的口头反馈，以及 agent 在测试机上的截图和连拍；文档逐项写明是哪一种。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：pak 与加载、目标资产与 look、骨架与重定向、网格专用骨、材质实例、动画压缩、动画蓝图图手术
- [构建流水线](BUILD_PIPELINE.md)：提取 → Blender 构建 → UE 4.11 导入与 cook → 烘焙后补丁 → 打包 → 安装
- [面部、眨眼与口型](FACE_AND_LIPSYNC.md)：面部关节蒙皮、眨眼放大骨、口型权重求解
- [物理](PHYSICS.md)：被否决的 PhysX 路线、逐骨 AnimDynamics 弹簧、平面限制、调参记录
- [开发工具](DEV_TOOLING.md)：DgExport、Python 工具、远程测试机、实机测试流程
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：t0 → t31 的每一轮
- [便携工具包](../../portable-kits/days-gone/README.md)：Python 包工具、Blender 构建脚本、DgExport 源码、PowerShell 工具

## 公开边界

不含源模型、游戏资源、提取出的 JSON / 动画、烘焙出的 uasset、发行 pak 或 UE 引擎源码。便携包里的脚本是项目脚本去掉本机路径后的副本，
Karin 专属的骨名、链表、关节编号和参数是案例值，换模型时要按当前资源重新测量。
