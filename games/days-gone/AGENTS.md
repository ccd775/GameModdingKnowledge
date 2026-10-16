# Agent 入口（往日不再 Days Gone）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对 Steam 分支和 build：本目录快照是 `days_gone_classic`、build `10034136`。分支或 build 变了 → 先用 DgExport 重新 dump
   `deacon_master_Skeleton`、`deacon_head_standard`、`Deacon_VimBlueprint` 和 look，与上一次比较骨数、节点数、包版本
   （[技术合同](TECHNICAL_CONTRACTS.md) §1、§3、§8）。
2. 看 `BendGame\Content\Paks\~mods` 和 `%LOCALAPPDATA%\BendGame\Saved\Paks` 里装了什么，`sfpaks\startuppackages.pak`
   是否已改名。替换迪肯的 mod 互相覆盖：一次只装一个，把用户原来的包移到备份目录再测。
3. 确认 UE **4.11.2** 和内容工程 `BendGame` 能打开；**编辑器开着时游戏会在约 2 秒后退出**，测试前关编辑器。
4. 分清这一版改的是几何、物理、眨眼、口型还是物理参数；一版只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **绝不在游戏里存档。** 测试只读档（主菜单「繼續」）。**R 是快速存档键**；暂停菜单里「儲存遊戲」常是默认高亮，
  在暂停菜单上不要按 Enter。离开游戏用「離開並回到桌面」，先截图确认弹出的是「離開並回到桌面 / 警告」再确认。
- **游戏失焦就暂停。** 每次远程动作都会抢焦点：把「切到游戏、Esc、动作、截图」放在同一次远程调用里。
- **动画蓝图插节点只能插在类字段链头部**，并把每个旧 pose `LinkID`（包括数组里的）加上新节点数 M。插在尾部 → 加载时
  栈溢出崩溃；漏掉数组里的链接 → 几秒后变 A-pose（[技术合同](TECHNICAL_CONTRACTS.md) §8）。
- **游戏的材质实例带内联着色器图，导出数据不能挪位置。** 改引用只能原地改名字表里的字符串（`retarget_inplace.py`）；
  文件头变长就会 `Invalid BufferCount=0` 崩溃。
- **PhysX 约束对玩家网格上的额外刚体无效**（限制、锁定、驱动都没效果），次级物理走 AnimDynamics；
  **BoneDrivenController 节点完全无效**，驱动骨用克隆的 CopyBone。
- **面部动画别信 CUE4Parse 的解码**（per-track 压缩的轨道全被解成常数），用 `anim_pertrack.py`。
- **列「Head 下面的骨」时要过滤**：`Head` 同时是 `KO_*` 头发物理骨的父骨，面部求解只能用 `face_*`、`Jaw`、
  `lowerPalette_jnt`、`tongue*`；否则头发顶点被改成「Head + 头发骨」的混合权重，物理一摆就被拉扯。
- **显示模式看 Bend 自己的 `VideoSettings=` 行**，不是 `FullscreenMode`；测试机的虚拟显示器设 4K 独占会 `ResizeTarget E_FAIL` 崩溃
  （[开发工具](DEV_TOOLING.md) §4）。改之前备份 `GameUserSettings.ini`。
- **远程机上的 GUI（编辑器、游戏）只能从用户会话启动**，SSH 会话里启动的看不见。
- **不要声称实机通过。** Blender 模拟、离线读回都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系
（例：「眨眼没生效是放大倍数不够」被证伪为「BoneDrivenController 节点在游戏里根本不执行」）。
