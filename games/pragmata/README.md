# PRAGMATA

## 范围

这里整理 Steam《PRAGMATA》（App `3357650`，RE Engine）角色替换与次级物理的可复用合同，
来自 2026-09-28 → 09-30 的四个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Gamer JP「Karin Hugh v1.1」+ phys3 | 在别人已做好的替换 mod 上加 chain2 物理（Hugh 的 prefab 原本没有任何 Chain 组件） | `runtime-confirmed`（用户：phys3「挺好的」） |
| Gamer JP「Diana Minahoshi v1.0」+ phys3 | 同上，Diana | `runtime-confirmed`（同上） |
| Karin_Original → Hugh v0.3.0 | 从 VRM 源模型完整构建：网格、refskel、材质、贴图、屏蔽件、chain2、prefab 注入 | `runtime-confirmed`（用户验收 v0.3.0） |
| Karin_kipfel → Diana v0.3.0 | 从 FBX 源模型完整构建（原生 rest 路线） | `runtime-confirmed`（用户验收 v0.3.0） |

所有后缀号、偏移、骨数、缩放和参数都是 `build-sensitive` 或 `case-derived` 快照，只对
build `24543093`（2026-09-18 安装）有效。

与其它 RE Engine 目录的关系：Mesh/MDF/TEX/chain2 的**方法**与
[鬼武者](../onimusha-way-of-the-sword/README.md)、[RE4R](../resident-evil-4-remake/README.md) 相通，
但本作的资源版本、chain2 版本（`.15`，不是鬼武者的 `.17`）、prefab 结构和加载路线都不同，
**常量不能互相套用**。本作的主要贡献：

- **给没有物理的角色从零加 chain2**：PFB/RSZ 实例插入、Chain2 组件字段、UpdateTiming 的坑；
- **从别人的 mod 反推「已被实机证明可用」的构建配方**，再用自己的源模型复现；
- **裙摆防穿模的完整闭环**：chain2 内置模型碰撞体的拟合、静止间隙闸门、节点胶囊碰撞，以及
  不需要进游戏就能比较候选的步幅估计。

## 核心方法

- 先找一个已经能在实机跑的同类 mod，把它**逐字段反推**成配方（骨架动了哪些、refskel 改没改、
  材质用哪个 mmtr、屏蔽件长什么样），再用自己的源模型按配方复现。配方里每一条都有实机先例，
  出问题时归因范围小。
- 两种骨架路线：**refskel 路线**（改 mesh rest + `*.refskel.8` 到源模型比例，Hugh）和
  **原生 rest 路线**（骨架完全原生，逐骨把几何贴到原生关节，Diana）。选哪条跟随参考 mod。
- 物理：chain2 `.15` 可被 RE-Chain-Editor 逐字节往返；组件要自己插进 `.pfb.18`，并覆盖到
  **所有引用该身体 mesh 的 prefab**（全量扫描，不要猜）。
- 调参时一次只动一组能归因的字段，并记下每一轮的实机反馈（见 [物理](CHAIN2_PHYSICS.md) §4）。
- 裙摆穿模按「碰撞体有没有生效 → 碰撞体贴不贴身 → 节点之间的布有没有被挡」顺序查；本作的
  终解是 chain2 内置大腿/骨盆胶囊 + 裙片节点 `collisionShape = 2`（节点到子节点的胶囊）。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed`。本项目的实机证据全部来自用户截图与口头验收，
**没有逐项归因实验**：同一版里的多个改动被一起接受时，文档写「随 vX 一起被接受」，不写
「某字段已被证明有效」。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：资源版本、槽位、PFB/RSZ、工具适配层的坑
- [角色替换](CHARACTER_REPLACEMENT.md)：参考 mod 反推、两种骨架路线、源模型读取、形态键烘焙、材质、屏蔽件
- [chain2 物理](CHAIN2_PHYSICS.md)：从零加物理、调参轨迹、碰撞体与裙摆
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门清单、确定性、打包
- [排障手册](TROUBLESHOOTING.md)：症状导向的定位表与已被证伪的捷径
- [案例：Karin → Hugh / Diana](cases/KARIN_HUGH_DIANA.md)：版本轨迹与每一轮反馈

## 公开边界

本目录只有文档。不含源模型、参考 mod、游戏资源、提取出的原生文件或发布包；构建脚本留在
项目目录内，这里只记录脚本职责、方法、结论和被拒绝的假设。
