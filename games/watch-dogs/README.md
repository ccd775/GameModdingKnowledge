# Watch Dogs (2014)

## 项目结果

Karin v1.3.0 替换 Aiden 默认“私法制裁者”服装。商店服装、DLC、囚服、开场和剧情强制模型不在范围内。Blender -> FBX -> ZModeler Compound -> XBG -> XBT/FAT/DAT -> ModManager 的生产链已冻结，用户于 2026-08-05 实机接受。

## 最重要的工程合同

- XBG 必须是干净的双 LOD Compound：根层只保留 `char01.skel` 和 `char01.mesh`，state 只保留 `L0/L1`；不要把 replacement 拖入仍含 donor geometry 的旧 Compound。
- FBX 导入固定为 axes/geometry `1.000`、Blender axis system；不要在 ZModeler 再乘 `0.01`。
- 导出后同时做 GPU buffer audit 和全新进程回读；日志无 error 或预览可见都不能替代这两个门。
- XBT 低/高 streamed pair 必须保留 donor header，分别注入匹配尺寸和 mip 链的 DDS；结构测试通过仍需要实机渲染检查。
- diffuse、emission、glow mask 分开处理；最终运行包只带声明的 XBG、XBT、私有材质和兼容数据库资源。
- 发布采用版本化目录和冻结哈希；运行时失败回滚到上一冻结包，不覆盖原版游戏数据或其他 Mod。

## 结果与限制

v1.3.0 的双 LOD、GPU buffer、fresh-process、ModManager payload 和基础动作门通过。双马尾孔位、脖套动态和手部权重得到修复；少数持枪/插兜动作仍有轻微手指变形，属于已接受限制。

## 文档

- [端到端生产 SOP](SOP_WATCH_DOGS_CHARACTER_REPLACEMENT.md)
- [ZModeler 操作清单](ZMODELER_OPERATOR_CHECKLIST.md)
- [XBT 贴图管线](XBT_TEXTURE_PIPELINE.md)
- [部署与回滚](DEPLOYMENT_WATCH_DOGS_KARIN.md)
- [完整管线索引](PIPELINE_DETAILS.md)

