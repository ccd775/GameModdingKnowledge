# Onimusha: Way of the Sword

## 范围

这里整理《鬼武者：新生》（Onimusha: Way of the Sword，RE Engine）主角替换的可复用
合同，来自 Karin PicodraTech 替换宫本武藏 `ch001_00` 的长线项目（Demo v1.0 → 正式版
v1.11.0）。所有具体后缀号、骨数、偏移和参数都是 `build-sensitive` 或 `case-derived`
快照，只对文中注明的 build 有效。

与 RE4R 目录的关系：同为 RE Engine，Mesh/MDF/TEX/PAK 的**方法**相通，但本作的资源
版本号、MDF51 头部布局、chain2 版本和加载路线都不同，**不能直接套用 RE4R 的常量**。
本作独有的主要贡献是 **chain2 v17 次级物理的完整读写与调参方法**。

## 核心方法

- 先反推当前 build 的资源版本号（Mesh/GPUC 后缀由 PAK TOC 的 murmur3 对反推），
  再决定工具适配层，不要让旧插件按相近版本近似。
- 骨绑定**按名字**，不按索引：Mesh 加权骨只要在目标运行时骨架里同名存在且 rest 一致
  即可，骨序和骨数差异不影响。这条推翻了早期「必须复刻原生骨序」的硬约束。
- 比例策略是一次全局相似变换 + **局部**方向修复，不是全身逐骨 directional retarget；
  与原生动画/IK 冲突的区域（手臂、腿）采用原生 rest 闭包的 hybrid 方案。
- chain2 的静止指向必须从 mesh 几何逐节点反算，不能沿用供体四元数；`angleLimitDir`
  表达在**父骨坐标系**。
- 调物理参数前先逐字段 diff：**从原生出发、只改已证明必须改的**；跨链族搬运档位是本
  项目三次返工的共同原因。
- 生产构建器一旦冻结就不再改，能力扩展走**运行时注入的版本化 runner**；每个发行版
  有自己的打包器，旧打包器保持冻结以维持旧版可复现。

## 证据纪律

沿用本库的 `reference-inferred` / `offline-accepted` / `runtime-load-pass` /
`runtime-rejected` / `runtime-confirmed` 五级。本项目的特别教训：**离线闸门全绿与实机
通过是两件事**，v1.4–v1.6 都是离线全绿、实机拒绝。发行包内的运行时状态必须逐项分层
写明哪一项是实机确认、哪一项只是离线验证并随包发出。

## 阅读入口

- [技术合同](TECHNICAL_CONTRACTS.md)：资源版本、槽位、骨骼与网格导出合同
- [骨骼与几何](RIG_AND_GEOMETRY.md)：hybrid 闭包、方向重定向、末节指骨、地面接触
- [chain2 次级物理](CHAIN2_PHYSICS.md)：v17 格式、字段语义、调参方法
- [验证与发布](VALIDATION_AND_RELEASE.md)：加载路线、闸门、打包器血统、确定性
- [排障手册](TROUBLESHOOTING.md)：症状导向的定位表与已被证伪的捷径
- [案例：Karin PicodraTech 替换宫本武藏](cases/MUSASHI_KARIN_PICODRATECH.md)

## 公开边界

本目录只有文档。不含模型、纹理、参考 Mod、游戏 PAK、提取出的原生资源或发布包；
构建脚本留在项目目录内，这里只记录方法、结论和被拒绝的假设。
