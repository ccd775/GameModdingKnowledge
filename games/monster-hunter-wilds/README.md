# Monster Hunter Wilds

## 范围

这里整理《怪物猎人：荒野》（Monster Hunter Wilds，RE Engine，Steam App `2246340`）
玩家装备外观替换的可复用合同，来自两个项目：

- **Karin_Original → 女性装备 `ch03_060_000`**：VRM 来源角色，使用社区 BoneSystem
  独立骨骼 + 表情映射 + chain2 物理，r1 → r6（2026-09-29 → 09-30），r6 用户验收。
- **旧 Karin mod 的 1.042 材质修复**（2026-08-05）：游戏更新后装备 MDF 合同变化的迁移。

所有具体后缀号、骨数、半径和参数都是 `build-sensitive` 或 `case-derived` 快照，只对
文中注明的 build 有效（主要为 exe `1.42.0.2` / build `24705561`）。

与 RE4R、Onimusha 目录的关系：同为 RE Engine，Mesh/MDF/TEX/chain2 的**方法**相通，但
本作的资源版本、装备部位结构、加载路线（REFramework + Fluffy）都不同，不能直接套用
其他作品的常量。本作独有的主要贡献：

- **REFramework 版本决定散装贴图能否加载**，而加载失败表现为「标题前永久黑屏」；
- **装备部位的引擎挂点骨**（武器挂点、投射器骨）是占位件不能删除的合同；
- 基于 **BoneSystem** 的独立骨骼 + 表情映射替换路线；
- 一套**只停在标题画面**的自动化自测夹具与负对照矩阵。

## 核心方法

- 先反查当前 build 的资源版本，再做任何写入；第三方文件名列表对 chain2 已过期。
- 骨架 = 原版 224 骨 fbxskel 的名字/顺序/父子不变，只换 rest；Mesh 可以额外携带
  脸部骨、链骨、挂点骨（仅 Mesh，不进 fbxskel），按名字绑定。
- 所有可见几何放在一个部位（本例 2 号胴甲），其余部位用占位件隐藏 —— 但占位件必须
  保留该部位的引擎挂点骨；投射器部位直接保留原版，由 BoneSystem 的 HideSlinger 隐藏。
- 材质从**当前 build** 的原版装备材质拷贝模板，只替换自己拥有的贴图槽与参数；
  NRRO 不要用引擎 NullNRRO（粗糙度 0.5，布料会有集中高光）。
- 碰撞体按「要推开布料的外表面」拟合，而不是按身体平均截面；再按静止间隙封顶。
- 黑屏时先做环境负对照（原版字节原样放回原版路径），再二分 mod 文件。

## 证据纪律

沿用本库的 `reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed` 五级。本作的特别教训：**r1–r5 连续五版离线
闸门全绿、实机全部黑屏**，根因在运行环境而不在任何 mod 文件；在环境被证明之前，任何
「修复」都只是在改一个与症状无关的变量。

## 阅读入口

- [技术合同](TECHNICAL_CONTRACTS.md)：资源版本、装备部位与挂点骨、骨架/BoneSystem、
  脸部、材质与 TEX/NRRO、chain2/clsp
- [加载与 REFramework](LOADING_AND_REFRAMEWORK.md)：散装 vs PAK、版本门槛、开机机理、Fluffy
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、自测夹具、负对照矩阵、发布纪律
- [排障手册](TROUBLESHOOTING.md)：症状定位表、已证伪的捷径、元错误
- [案例：Karin_Original 替换 ch03_060_000](cases/KARIN_ORIGINAL_CH03_060.md)
- [案例：1.042 更新后的 MDF 合同迁移](cases/KARIN_1042_MDF_MIGRATION.md)

## 公开边界

本目录只有文档。不含模型、纹理、参考 Mod、游戏 PAK、提取出的原生资源、BoneSystem
二进制或发布包；构建脚本留在项目目录内，这里只记录方法、结论和被拒绝的假设。
