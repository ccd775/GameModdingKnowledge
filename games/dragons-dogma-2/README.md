# 龙之信条2（Dragon's Dogma 2）

## 范围

这里整理 Steam《Dragon's Dogma 2》（App `2054970`，RE Engine）玩家角色替换的可复用合同，
来自 2026-09-23 → 10-11 的两个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin PicodraTech v1.3.0 | 从源模型完整构建的身体网格（自带 Karin 比例骨架 + 182 根次级骨）、贴图、MDF、chain 物理、表情；REFramework Lua 在游戏**自己构建身体**时递入 | 用户本机实机用到 v1.2.0（其间发现的比例问题已修复）；v1.3.0（表情、2026-10 build + DLC）为 agent 在测试机实机自测：读档、装备预览、头像、物理、表情、拍照模式、对话手势、走跑跳攻蹲；表情幅度用户未单独确认 |
| Karin Original v1.0.1 | 同一代码库的第二个 profile；物理按用户反馈调过三轮，v1.0.1 修复走路时裙片翻进身体 | `runtime-confirmed`（用户本机：「这次好了」）；v1.0.0 的表情由 agent 在测试机自测 |

快照只对 build `25290080`（2026-10 更新 + DLC「Dark Arisen」）和 `24831693`（2026-09，社区称 TU3.2）有效，
两者格式版本相同。**任何后缀号、偏移、骨数、钩子名都是 `build-sensitive`**；参数值是 `case-derived`。

与其它 RE Engine 目录的关系：DD2 用的是老式 `.chain`（`.55`），不是 PRAGMATA（本库 `games/pragmata/README.md`） /
鬼武者（本库 `games/onimusha-way-of-the-sword/README.md`） 的 chain2；与 DMC5（本库 `games/devil-may-cry-5/CHAIN_PHYSICS.md`） 的 chain
字段相近但版本不同。本作的主要贡献：

- **TU3.2 之后的整包格式**（单个 65 GB `re_chunk_000.pak`、KPKA feature `0x40` remap 表、mesh `.260421070`），
  社区旧工具和旧教程全部失效时，怎样用 REE-Lib 自建一条最小工具链；
- **不改原生文件的玩家专属替换**：游戏用 kit 拼装人类，身体网格全同性别共用。替换只发生在游戏为玩家构建身体的那一刻，
  由 Lua 钩子把 Karin 的网格 / 材质 / chain 递进去，重绑、物理、IK 全部由游戏自己完成；
- 运行时换身体（`setMesh`）的**完整踩坑表**：joint 缓存、结构体容器副本、工作线程崩溃、皮肤烘焙状态机；
- **骨驱动表情**：把源模型形态键编码成平移骨，再从原生隐藏头部的面部骨实时驱动；
- 裙摆穿模的**逐帧录制 + 现场调参**定位法，以及「外倾圆锥」角度限制。

## 核心方法

- 先用只读探针把玩家对象层级、组件、材质、joint 表 dump 出来，再决定方案。玩家根 GameObject 的
  `via.render.Mesh` 就是身体，装备是子 GameObject，靠 `SharedSkeleton` 按名字共享根骨架。
- 选「运行时只改玩家」而不是「替换 `body_000_f.mesh`」：后者让所有同性别 NPC 都变成 Karin。
- 先尝试最直接的运行时 `setMesh`（v1.1），在它暴露出引擎侧残余崩溃后，反过来找游戏自己的换身体流水线（v1.2）：
  `PartSwapMeshHolder.swap` / `PartSwapMaterialHolder` / `setBodyChainAsset` 三个注入点。注入点之外唯一的障碍
  （皮肤烘焙）用反汇编拆状态机后改道。
- 物理调参只信**实测**：逐帧录制节点位置，在线用 `via.motion.ChainGroup` 的倍率 setter 做对照实验，确认哪个旋钮
  真正起作用后才改文件（裙摆问题里阻尼 / 弹簧 / 运动力都无效，只有角度限制有效）。
- 一版只让一类改动进入实机反馈；chain-only 的修复版要能证明「相对上一版只有这些字段变了」。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed`。实机证据来自用户截图与口头验收，以及 agent 在主开发机和
一台装有 DLC 的测试机上的冷启动、压力脚本和运行时探针；文档逐项写明是哪一种。未测场景见 [验证与发布](VALIDATION_AND_RELEASE.md) §5。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：PAK/资源版本、加载路线、角色资源结构、贴图通道、材质母版、版本更新的影响
- [构建流水线](BUILD_PIPELINE.md)：源模型 → 网格（骨架、权重、骨序、兼容桩）→ 贴图 → MDF → chain → PAK
- [运行时注入](RUNTIME_INJECTION.md)：构建时注入（现行）、皮肤烘焙状态机、体型编辑表、运行时换身体（已取代）的教训
- [chain 物理](CHAIN_PHYSICS.md)：`.chain.55` 生成、angleLimitDirection、链静止姿势、裙摆角度限制
- [表情](FACIAL_EXPRESSIONS.md)：形态键 → 平移骨编码、从原生面部骨驱动
- [开发工具](DEV_TOOLING.md)：DD2Tool、开发控制台与查询脚本、反汇编托管方法、游戏自动化与存档安全
- [排障手册](TROUBLESHOOTING.md)：崩溃栈 / 症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、发行包结构、证据分层、未测场景
- [案例：Karin PicodraTech / Original](cases/KARIN_PICODRATECH_ORIGINAL.md)：版本轨迹与每一轮反馈
- [便携工具包](../../portable-kits/dragons-dogma-2/README.md)：DD2Tool 源码、Lua 注入脚本、开发控制台、构建脚本

## 公开边界

不含源模型、游戏资源、提取出的原生文件、发行 PAK 或 REE-Lib 源码。便携包里的脚本是项目脚本去掉本机路径后的副本，
Karin 专属的骨名、链表和参数是案例值，换模型时要按当前资源重新测量。
