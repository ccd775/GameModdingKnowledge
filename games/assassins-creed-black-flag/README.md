# 刺客信条：黑旗记忆重置

这是完整 Karin 角色替换及其后续修复的知识记录，不是停留在早期“缺少目标游戏”的研究计划。最后一次修复是 AY / Karin Playable 1.6.1，目标 BuildID 24833802。

2026-09-05 的部署报告证明：恢复共享 NPC 头部数据、仅关闭 Karin outfit 内原生口腔的 Active Bool，保留眼睛、骨骼、权重和纹理；独立解码 873 项检查通过。用户在 2026-09-06 本知识库整理会话确认最后修复实机没有问题。结论范围沿用用户确认，不补写未报告的全动作/地图测试。

## 可复用知识

- Forge v50 的两种 BMS framing、field-4 raw LZ4、资源 envelope、TOC 顺序和非类型化区块保真。
- 从当前 Skeleton CRC 对应 MeshBone 表更新 inverse bind，区分原生骨与模板保留槽。
- glTF 与 BFR 三角绕序差异；材质变黑不一定是纹理问题。
- 单 primitive 与多 primitive 的实际运行差异；离线 base-vertex 假设曾导致头发/衣物拉伸。
- 形态键、atlas、法线和材质探针、脚底接触、头颈与服装局部变形。
- 玩家局部可见性从 outfit 实例 override 定位；全局清空共享头部表曾使 NPC 头部消失，且不能关闭玩家的原生口腔。
- 游戏更新后重新锁定 boot/patch/EXE；保留精确回滚，不能绕过旧安装器的版本检查。

## 文档与工具

- [便携脚本和命令](../../portable-kits/assassins-creed-black-flag/README.md)
- [真实工具角色](TOOLCHAIN.md)
- [格式研究快照](FORMAT_RESEARCH.md)
- [完整制作与修复历史](PROJECT_HISTORY.md)

历史文档包含被后来章节覆盖的“pending”“未取得游戏”等状态。阅读时从末段 Stage 26 往前定位当前结论；9 月 6 日的用户确认补充了当时尚未记录的实机状态。

便携脚本覆盖 Forge 提取/重建，不是通用模型转换器；新角色仍要根据文档中的 Mesh/rig 合同制作派生 authoring 和项目脚本。
