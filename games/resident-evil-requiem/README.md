# 生化危机 安魂曲（RESIDENT EVIL requiem / BIOHAZARD requiem）

## 范围

这里整理 Steam《RESIDENT EVIL requiem》（App `3764200`，RE Engine）角色替换与次级物理的可复用合同，
来自 2026-10-01 → 10-02 的工作：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| 用户自制「Leon Karin」（KarinPicodraTech → 里昂） | 配方来源：逐字段反推后复现 | 用户自用、实机可用 |
| Karin_Original → 里昂（Leon，`ch0100`）v1.2.0 | 从 VRM 源模型完整构建：网格、refskel、材质、贴图、屏蔽件、chain2、prefab 注入 | `runtime-load-pass`（「奖励内容 → 游戏模型」展柜；裙摆碰撞由运行时探针确认生效） |
| Karin_Original → 格蕾丝（Grace，`ch0200`）v1.2.0 | 同上 | `runtime-load-pass`（展柜；展柜里她的身体物理被游戏关闭，见 [物理](CHAIN2_PHYSICS.md) §6） |
| 「Leon Karin」哑光修复 | 5 个粗糙度为 0 的材质改指平法线、粗糙度 1 的 NRMR | `offline-accepted`（同一修法在 v1.1 上实机看到哑光） |

**实际游玩（走跑、战斗、过场、第一人称、死亡切割套件）都未测试**；用户尚未对 v1.2.0 给出验收。
所有后缀号、偏移、骨数、缩放和参数都是 `build-sensitive` 或 `case-derived` 快照，只对 build `23634047` 有效。

与其它 RE Engine 目录的关系：本作与 [PRAGMATA](../pragmata/README.md) 最近 —— chain2 同为 `.15`、prefab 同为
`.pfb.18`（RSZ v16）、refskel 同为 `.8`，PRAGMATA 的 PFB 读写器、refskel 路线和裙摆碰撞做法几乎原样可用；
但 mesh 版本、权重布局、部件号体系和 prefab 组织不同，**常量不能互相套用**。本作新增的主要结论：

- **`via.motion.Chain2.CollisionTarget` 决定 chain2 自带碰撞体是否生效**：Self 0 / Extern 1 / All 2（运行时枚举）。
  原生角色 prefab 全是 Extern = 只碰角色 `.clsp`，chain2 里拟合的大腿胶囊被完全忽略。
- **引擎 `NullNormal.tex` 的 alpha（= 粗糙度）是 0**：NRMR 槽留空的材质会像乳胶一样反光。
- **一个部件号有很多变体与套件**：身体有 12–13 个变体（8–9 个显示完整身体）、每个变体有多份 mdf2，默认套件用的身体变体原生不带 Chain2；
  只改「默认那一份」会在别的场景里掉回原模型或丢物理。
- **展柜（奖励内容 → 游戏模型）会对喂了专用动画的部件关闭 Chain2**：它能看外观，不能单独证明物理。

## 核心方法

- 先把用户手上实机可用的 mod **逐字段反推成配方**（哪些部件号换了、屏蔽件长什么样、refskel 改了哪些关节、
  材质用哪个 mmtr、chain2 放在哪个槽、clsp 怎么处理），再用自己的源模型按配方复现。
  偏离配方的地方要单独写理由（本项目：缩放按肩高、clsp 不改、多屏蔽了一个腰带部件）。
- 覆盖面靠**全量扫描**而不是猜：路径表列出每个部件号的全部变体与 mdf2 变体；prefab 扫描列出每个 prefab 用的
  mesh / mdf / chain2 / clsp；montage 数据列出每个套件（prefab 后缀集合）用哪些变体。
- 物理问题先用 REFramework Lua 探针读运行时状态（Chain2 列表、关节世界坐标、枚举值），再改文件；
  展柜截图看起来对，不等于碰撞生效。
- 一版只让一类改动进入实机反馈；改动未单独归因时照实写。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` /
`runtime-confirmed`。本项目的实机证据来自 agent 自己在展柜里的截图与 REFramework 探针数值，
**不是用户验收**；凡是只在展柜里看过的结论都标 `runtime-load-pass`。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：资源版本、部件号与变体、套件与展柜、PFB/RSZ、mesh/MDF/TEX 写法、运行时探针
- [角色替换](CHARACTER_REPLACEMENT.md)：参考 mod 配方、覆盖范围、refskel 路线、材质与粗糙度、屏蔽件
- [chain2 物理](CHAIN2_PHYSICS.md)：chain2 槽位、prefab 注入、CollisionTarget、碰撞体与裙摆、展柜里的物理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门清单、打包、Fluffy 安装、展柜自测自动化
- [排障手册](TROUBLESHOOTING.md)：症状导向的定位表与已被证伪的捷径
- [案例：Karin → 里昂 / 格蕾丝](cases/KARIN_LEON_GRACE.md)：版本轨迹、每一轮发现、未解决项

## 公开边界

本目录只有文档。不含源模型、参考 mod、游戏资源、提取出的原生文件或发布包；构建脚本留在项目目录内，
这里只记录脚本职责、方法、结论和被拒绝的假设。
