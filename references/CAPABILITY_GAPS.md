# 能力与边界

本仓库提供长线工作方法、实际格式工具与历史案例。它可以作为 agent 的制作资料，但没有在陌生机器上完成所有游戏新角色的端到端验收，因此不能称为“一键生成任意 Mod”。

| 游戏 | 已带实现 | 继续制作时需适配 |
| --- | --- | --- |
| MK1 | Atlas/索引检查、骨盆与颈部数学算子、三件套预检和备份部署 | 每角色骨架映射、定制UE导入/Cook、native多export/store/redirect写入、游戏复测 |
| Hitman | GLB/PRIM 验证、roundtrip、六槽 TEXT 重建 | 当前实体 QuickEntity、rig/atlas、RPKG/SMF |
| Watch Dogs | XBT 解析/注入/配对/PNG 转换 | 源模型 FBX、ZModeler Compound、XBG GPU 审计、FAT/DAT |
| Black Flag | Forge v50 LZ4 提取/重建 | 当前 Mesh writer/target rig、纹理和角色局部资源合同 |
| RE4R | KPKA v4 哈希/目录/提取 | RE Mesh/Chain 工具、每角色映射和 PFB/RSZ |
| L4D2 | VPK 提取/校验、VTA 缩放、StudioMDL 记录器 | 源 SMD/QC、flex/procedural/physics、MDL 深审计 |
| HD2 | patch triplet、LUT、SDK UV 复制 | 当前 AQ/SDK、Unit carrier、权重和 Piece ownership |

完整清单见 [便携入口](../portable-kits/README.md)。带有 --help 的脚本也有明确格式限制，不能把旧角色合同当成所有模型的常量。

外部工具从 [维护者入口](TOOL_SOURCES.md) 获取并固定版本。GUI 工具按游戏操作清单运行，使用新截图/控件状态确认，不复用历史 PID、句柄或坐标。无需安装作者个人的 Computer Use skill；接手 agent 可以使用其自身可靠的 GUI 能力，或由用户完成明确步骤。

骨架映射、衣物物理和材质外观是按源模型决定的项目工作。参考 Mod 只提供已声明的 donor/接口作用，不打包其可见资产。构建失败可以回到前一阶段；用户实机反馈能够推翻离线推断。
