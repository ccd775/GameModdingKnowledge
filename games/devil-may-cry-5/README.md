# Devil May Cry 5（鬼泣5）

## 范围

这里整理 Steam《Devil May Cry 5》（App `601150`，RE Engine）角色替换的可复用合同，
来自 2026-10-01 的两项交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| KarinPT replace V v1.0 | 参照用户已有的「KarinPT 替换 Nero / Dante」两个 mod，把同一个 Karin_PicodraTech 身体网格改造成 V（`pl0200` / `pl0210`） | `runtime-confirmed`（仅标题画面：用户确认「看起来挺好的，V的脚基本也是贴在地面上的」） |
| KarinOriginal replace Nero / Dante / V v1.1 | 从 Karin_Original 源模型完整构建三个包；骨架、材质、目录结构以 PT 包为模板 | Nero / Dante：`runtime-confirmed`（用户实战报裙片穿模 → v1.1 修复后「看起来好了」）；V：v1.0 只做过标题画面自测，v1.1 的 V chain 没有在游戏里加载过 |

所有后缀号、骨数、偏移、缩放和参数都是 `build-sensitive` 或 `case-derived` 快照，只对
build `24901913` 有效。

与其它 RE Engine 目录的关系：Env_Emissive 材质、链物理、裙摆碰撞的**方法**与
[PRAGMATA](../pragmata/README.md)、[MHWs](../monster-hunter-wilds/README.md)、
[鬼武者](../onimusha-way-of-the-sword/README.md) 相通。但 DMC5 是 2019 年的引擎版本：物理是
`chain .21`（不是 chain2），网格 `.1808282334`、MDF `.10`、TEX `.11`，用 Fluffy 的 invalidate
方式加载散装文件，不需要 REFramework。**常量不能互相套用。** 本作的主要贡献：

- **以已有替换 mod 为骨架模板**：PT 身体网格的骨架 = 原版 Dante 339 骨 + 142 根 Karin 布料/头发骨。
  新模型沿用模板的 DMC5 骨架与 bind，只替换几何和物理骨。所有身体槽位用同一份 Karin 几何，
  各槽位网格只在骨架上不同（Hip 位置、Nero 魔人的骨架）。
- **Env_Emissive 的 albm alpha 控制自发光**：A = 0 时，背光的标题画面里角色整片发黑。
  这一点在标题画面用 A/B 实验确认过。
- **短裙物理**：PT 链里那套为大衣设计的胶囊和重力不适合短裙，要按网格表面重新拟合碰撞胶囊。
  Hip 的 bind 位置在 Nero、Dante、V 三套网格里不同，所以每个身体要单独生成一份 chain。

## 核心方法

- 先把用户已有的同类 mod **逐字段反推**成配方：骨架改了什么、fbxskel 改没改、材质用哪个 mmtr、
  隐藏件和签名放在哪，再用新源模型按配方复现。
- 骨架路线跟随参考 mod：PT 的 fbxskel 骨位置 = 网格 bind local，Hip 保留各角色原版位置，其余骨按
  Karin 比例。改造 V 时先用同一方法重做 Nero 的 fbxskel，确认和原 mod 一致后才用到 V 上。
- 几何放置靠拟合：先对 PT 网格做 ICP（手部 / 脸部），得到「身体缩放 + 头部缩放，按 Head 子树权重混合」
  这条变换，再把新源模型放进 PT 的同一空间。
- 打包时以 PT 包的完整文件树为底，只替换身体网格、身体 chain、MDF 贴图路径、UI 立绘和签名，
  其余文件原样保留：场景、隐藏头发用的空网格、头发槽 chain。
- 实机自测只到标题画面，战斗由用户测。标题画面是背光场景，最容易暴露材质的明暗问题。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed`。本项目的实机证据全部来自标题画面截图、用户截图和口头验收。
v1.1 的碰撞体、重力、回弹和角度限制**一起**被接受，文档只写「随 v1.1 一起被接受」，
不写「某个字段已被证明有效」。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：资源版本、槽位、PAK 与 Fluffy、MDF / TEX / fbxskel / 网格导出器
- [角色替换](CHARACTER_REPLACEMENT.md)：PT 模板、V 改造、Karin_Original 构建、贴图与材质、立绘与签名
- [chain 物理](CHAIN_PHYSICS.md)：chain .21 结构、链组映射、裙摆碰撞拟合
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、标题画面自测、Fluffy 安装与原地更新
- [排障手册](TROUBLESHOOTING.md)：症状导向的定位表与已被证伪的捷径
- [案例：Karin × DMC5](cases/KARIN_DMC5.md)：版本轨迹与每一轮反馈

## 公开边界

本目录只有文档，不含源模型、参考 mod、游戏资源、提取出的原生文件或发布包。构建脚本留在
项目目录 `DMC5/Work/`，这里只记录脚本职责、方法、结论和被拒绝的假设。
