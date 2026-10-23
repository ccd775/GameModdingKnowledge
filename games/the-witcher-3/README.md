# 巫师3：狂猎 次世代版（The Witcher 3: Wild Hunt — Remastered）

## 范围

这里整理 PC 版《巫师3》次世代更新（菜单显示 v5.01，`witcher3.exe` 5.0.1048522，P4CL 13413172，DX12）里
主角杰洛特（Geralt）替换的可复用合同，来自 2026-10-17 → 10-19 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 杰洛特 v0.4.3 / v0.4.4 | 从 FBX 构建：几何按杰洛特的 `man_base` 骨架逐骨拟合（骨架静止姿势不动）；所有身体部件物品换成空模板；发型（coif）物品承载整个 Karin 网格和一个 `CAnimDangleComponent`（dyng 次级物理：双马尾、侧发、刘海、耳尖、狐尾、裙摆、丝带）；头部物品换成 Karin 自己的 `CMimicFace`（从她的形状键解出的 100 根面部骨） | v0.4.3：`runtime-confirmed`（用户实机：「看起来好了」，双马尾 / 侧发停下后保持原形、跑动不穿脸）；v0.4.4（走动时髋侧不再穿出裙子）：`offline-accepted`，已部署，待用户实测 |

快照只对 5.0.1048522 有效。**bundle 头版本、metadata.store 版本、物品模板路径、`man_base` 骨数是 `build-sensitive`**；
拟合比例、dyng 分组参数、表情映射表是 `case-derived`。旧版（1.32，DX11 单独 exe）的 bundle v3 / metadata.store v6 没有验证过。

本作的主要贡献：

- **不用脚本、不用 XML 的整角色替换**：杰洛特的玩家实体本身没有身体网格，身体是按名字解析的物品模板。覆盖
  `items\bodyparts\geralt_items\**`（含 DLC 目录）下除剑鞘外的全部模板即可，任何服装、发型、胡子状态都绕不开；
- **5.x 本地 mod 的两件套**：`blob0.bundle`（v5）+ 自己生成的 `metadata.store`（v7）。缺了 metadata.store，游戏整个忽略这个 mod 文件夹；
- **WolvenKit 7 的骨名陷阱**：它把 `SSkeletonBone.name` 写成 `StringAnsi`，读的时候又直接丢掉这个字段。它写出的 dyng / w3fac 骨架让
  dangle 组件和蒙在上面的网格整个隐形，必须用 `fix_cr2w_skeleton_names.py` 改回原版编码；
- **dyng 的实际语义**（全部实机验证）：节点 `distance` 是离开动画位置的上限、链接类型 0 刚性 / 1 最小距离 / 2 最大距离、三角形 (a, b, −1) 是
  look-at 及其滚转规则、重力 0 时上限内几乎没有恢复力；由此得到「锚定父节点 + 刚性形状链接 + 小上限 + 碰撞代理」的保形做法；
- **从形状键解表情骨**：W3 的表情是 129 个纯平移姿势驱动的面部骨，把 Karin 的形状键拟合成平移蒙皮分解（k-means + NNLS 交替），
  过场和对话里的眨眼、口型、眉毛由游戏原有的表情动画驱动。

## 核心方法

- 先用自写的 `w3bundle.py` 列出全部 bundle 内容，提取 `man_base.w2rig`、杰洛特的物品模板、头部 w3fac、半马尾 dyng 和移动动画。
- Blender 5.0 + Witcher3-Blender-Tools（dingdio）插件读 w2rig / w2mesh / w2anims、写 w2mesh 和 xbm；WolvenKit 7 nightly
  只用来在 CR2W 与 JSON 之间转换（物品模板、dyng、w3fac 都是改 JSON 再转回去）。
- 骨架静止姿势不改：W3 的动画带每根骨的平移，所以骨长必须是杰洛特的。Karin 的几何按骨逐段仿射到 `man_base` 关节上；
  肩部在杰洛特的待机姿势里拟合后再解回绑定姿势。
- 每一轮只让一类改动进入实机反馈（比例、物理、表情分开），物理问题先在 Blender 里用游戏动画复现（目标姿势渲染、裙子射线穿模检查），
  再改参数。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
实机证据来自用户的反馈，以及 agent 在同一台机器上的截图和连拍；文档逐项写明是哪一种。未测场景见
[验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：bundle v5 与 metadata.store v7、CR2W 与 WolvenKit、玩家物品模板、骨架坐标、网格与材质、dyng 与 w3fac 格式
- [角色拟合](CHARACTER_FIT.md)：原生骨架路线、逐骨仿射、窄肩与待机姿势拟合、权重习惯、裙子跟随大腿
- [物理](PHYSICS.md)：dyng 语义、保形、骨架朝向与滚转规则、形状链接、碰撞代理、裙子、调参记录
- [表情](FACE.md)：形状键 → 129 个表情姿势、平移蒙皮分解、w3fac 写入、口型幅度
- [构建流水线](BUILD_PIPELINE.md)：prepare → Blender 构建 → 模板与资源生成 → 骨名修复 → 打包 → 部署
- [开发工具](DEV_TOOLING.md)：插件、WolvenKit、离线检查脚本、实机测试自动化
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：v0.1.0 → v0.4.4 的每一轮
- [便携工具包](../../portable-kits/the-witcher-3/README.md)：bundle / metadata.store 读写、模板与资源生成器、Blender 构建与检查脚本、PowerShell 流水线

## 公开边界

不含源模型、游戏资源、提取出的 JSON / 动画、构建出的 w2mesh / xbm / bundle、发行 zip 或第三方工具二进制。
便携包里的脚本是项目脚本去掉本机路径后的副本，Karin 专属的骨名、链表、分组参数和表情映射是案例值，换模型时要按当前资源重新测量。
