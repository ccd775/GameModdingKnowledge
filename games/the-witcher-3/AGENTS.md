# Agent 入口（巫师3 次世代版）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对游戏版本：本目录快照是 `witcher3.exe` 5.0.1048522（菜单 v5.01）、内容合并在 `content\content0`、bundle 头 v5、
   `content\metadata.store` v7。版本变了 → 先用 `w3bundle.py list` 和 `w3metadata.py` 看 bundle 头与 store 版本，
   再用 `checks/regen_metadata_compare.py` 确认写出器仍能重建原版 store（[技术合同](TECHNICAL_CONTRACTS.md) §1、§2）。
2. 看游戏目录 `mods\` 下装了什么。其它改杰洛特外观（身体、头、发型）的 mod 会覆盖同一批物品模板，一次只测一个。
   确认 `文档\The Witcher 3\dx12user.settings` 里 `[ContentManager/Mods] EnabledLocal=true`（默认如此）。
3. 用户也在同一台机器上玩：**部署会杀掉正在运行的游戏，部署前先问**。用户的存档会改变「读取游戏」列表的顺序，
   自动化测试前先看存档目录。
4. 分清这一轮改的是比例 / 拟合、物理还是表情；一轮只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **mod 文件夹里没有自己的 `metadata.store`，游戏整个忽略它**（只放 `blob0.bundle` 时毫无反应）。每次打包后重新生成
  （`w3metadata_write.py`）。
- **WolvenKit 7 写出的 dyng / w3fac 必须过 `fix_cr2w_skeleton_names.py`**：它把 `SSkeletonBone.name` 写成 `StringAnsi`，
  游戏里 dangle 组件和蒙在它骨架上的网格整个隐形；它读文件时还会丢掉这个字段，所以原版文件经 WolvenKit 往返一次也会坏
  （[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **dangle 组件放在发型（coif）物品里**，不要放在头部或身体物品里：发型物品总是挂着，原版就用它承载 dangle。
- **物品模板只做最小修改**：在原版模板 JSON 上改路径和参数。自己从零拼组件、改组件名的版本在游戏里整个隐形过。
- **dyng 约束的 wind 和 gravity 要显式设 0**：原版发型 wind 3.0 会把长链一直吹向一侧；源模型的 spring 没有重力。
- **每个模拟节点都直接挂在动画锚点上**（头、骨盆、躯干、手），不要挂在上一节模拟节点上：刚度目标 = dyng 父节点 × 局部变换，
  模拟的父节点会拖走子节点的目标，链停下来时外翻或扭曲（[物理](PHYSICS.md) §3）。
- **look-at 节点的绑定朝向按游戏规则建**：X 指向目标，Z 尽量保持 dyng 父节点的 Z（保号）。别的滚转在静止时就是转过的
  （双马尾发卷外翻约 175°）。
- **保形的链都加刚性形状链接**（隔一节、隔两节，长度 = 绑定距离），不要只修用户点名的那一条：只修尾巴那一轮，
  双马尾和侧发又扭了一轮。
- **离线物理检查要带上 look-at 的传递**：被钉住的段会转向漂移的模拟节点。不模拟这一点时裙子穿模复现不出来。
- **正面 / 背面截图会藏住问题**：判断形状要看侧面和用户的视角，并和目标姿势的渲染（`checks/blender/idle_view.py`）对比，
  不要凭记忆判断「这就是模型原来的样子」。
- **玩家表情只在过场和对话里明显运行**：测眨眼和口型用新游戏开场过场（维吉玛浴室），不要在自由活动的待机里等。
- **不要声称实机通过。** Blender 渲染、离线射线检查都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系
（例：「尾巴停下后折叠是刚度不够」被证伪为「重力 0 时上限内几乎没有恢复力，靠刚性形状链接和小上限保形」）。
