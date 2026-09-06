# Left 4 Dead 2

## 范围与状态

本目录汇总 Source SMD/QC/VTA、StudioMDL、VTF/VMT、PHY、jigglebone、第一人称手臂、HUD、VPK 和运行时验收经验。Cloth04 -> Zoey、Karin Y -> Witch、Karin Nyako -> Hunter 和 SelfIllum/source-arms 案例已有用户运行确认；Charger、Francis、Smoker、Tank、Boomer、Spitter 等部分项目目前是静态通过或等待人工复测。

## 核心方法

- 先锁定目标 slot 的世界模型、light model、viewmodel、HUD、动画基准、PHY 和 include 合同，再审计参考 Mod 与源模型。
- 选择 source-fit 或 target-fit 绑定策略，不能同时叠加；每顶点最多使用目标允许的 influences，完整检查归一化、左右串骨和 seam 连续性。
- Source 动画基准、比例 corrective、局部 pose sequence 和 procedural bone 是独立责任域；Zoey/TeenAngst 只是已验证的特定 survivor 起点。
- 形态键、VTA、脚底和高跟鞋要先读取保存状态，再决定烘焙或删除；Basis 不自动等于作者想要的 rest。
- SMD 的 UV 交给 Blender Source Tools 写入，V 轴由 StudioMDL 处理；不要在导出前后重复翻转。
- 编译后从 MDL/VVD/VTX/PHY 回读骨架、sequence、companion checksum、VTX original-index coverage、材质和 physics；StudioMDL exit 0 不足以证明可用。
- VPK 采用隔离 compile sandbox、确定性 manifest、逐 payload hash 和可回滚的版本化 release 目录。HLMV 通过不等于游戏内通过。

## 阅读入口

- [详细索引](DETAILS_INDEX.md)
- [原则与证据等级](00-principles-and-evidence.md)
- [端到端 SOP](10-end-to-end-sop.md)
- [Source-fit、动画与 procedural 排障](18-source-fit-bind-procedural-regression.md)
- [案例与用户证据](evidence/)
- [模板](templates/)

## 公开边界

只分享方法、检查表和案例摘要。个人 VRM、参考 VPK、游戏原始模型、贴图、VPK 和私有发布包不在仓库内。

