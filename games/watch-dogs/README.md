# Watch Dogs (2014)

## 项目结果

Karin v1.3.0 替换 Aiden 默认“私法制裁者”服装。商店服装、DLC、囚服、开场和剧情强制模型不在范围内。Blender -> FBX -> ZModeler Compound -> XBG -> XBT/FAT/DAT -> ModManager 的生产链已冻结，用户于 2026-08-05 实机接受。

**2026-10-03 更新：不再需要 ZModeler。** 项目自写的纯 Python 写出器直接生成 `char01.xbg`。用它生成的 1.4（手指与脚跟修复）、1.5（缩短锁骨的骨架修改）和 Karin_Original 0.1.2（从 VRM 直接构建，骨架贴合模型）都经用户实机认可。格式、合同和范围见 [不用 ZModeler 生成 XBG](XBG_WITHOUT_ZMODELER.md)，脚本在 [便携包](../../portable-kits/watch-dogs/README.md)。

## 最重要的工程合同

- **无 ZModeler 路线**：以已被游戏接受的 char01.xbg 为模板，保留材质表、骨架和物理块，只重写调色板、LOD 表和 GPU 缓冲区。
- **矩阵表对齐**：节点表后的逆绑定矩阵表必须从文件绝对偏移的 16 字节边界开始。调色板长度变化时必须重新计算补零，否则读档到一半崩溃。
- **骨架**：身体骨骼的绑定位置游戏会采用，所以新模型应让骨架贴合模型；面部骨骼（`Facial_Hook` 下）的位置由面部动画重置为 Aiden 的，脸部顶点只蒙皮到 `Head`。
- **ZModeler 路线**（历史/对照）：XBG 必须是干净的双 LOD Compound，根层只保留 `char01.skel` 和 `char01.mesh`，state 只保留 `L0/L1`；FBX 导入固定为 axes/geometry `1.000`、Blender axis system。
- **回读与审计**：导出后同时做 GPU buffer audit 和回读（写出器逐值回读，ZModeler 路线用全新进程回读）；日志无 error 或预览可见都不能替代这两道检查。
- **XBT**：低/高两档 streamed 贴图必须保留 donor header，分别注入尺寸和 mip 链与之匹配的 DDS；不用 texconv 时可用 Pillow 按 mip 级逐级做 DXT 编码。
- **打包**：diffuse、emission、glow mask 分开处理；最终运行包只带声明的 XBG、XBT、私有材质和兼容数据库资源。
- **发布与回滚**：采用版本化目录和冻结哈希；运行时失败回滚到上一个冻结包，不覆盖原版游戏数据或其他 Mod。

## 结果与限制

v1.3.0 的双 LOD、GPU buffer、fresh-process、ModManager payload 和基础动作检查都已通过。双马尾孔位、脖套动态和手部权重得到修复；少数持枪/插兜动作仍有轻微手指变形，属于 1.3.0 的已接受限制。

- **1.4** 修复了手指和脚跟的支点偏移。
- **1.5** 收窄了肩宽；肩到上臂的过渡还略不自然。
- **Karin_Original 0.1.2** 只确认了读档、脸部和眼睛。以下尚未单独确认：脚是否悬空或陷地、双手持枪（肩比 Aiden 窄）、尾巴和裙子是否穿模。它没有面部表情和次级物理。

## 文档

- [不用 ZModeler 生成 XBG](XBG_WITHOUT_ZMODELER.md)
- [端到端生产 SOP](SOP_WATCH_DOGS_CHARACTER_REPLACEMENT.md)
- [ZModeler 操作清单](ZMODELER_OPERATOR_CHECKLIST.md)（历史路线）
- [XBT 贴图管线](XBT_TEXTURE_PIPELINE.md)
- [部署与回滚](DEPLOYMENT_WATCH_DOGS_KARIN.md)
- [完整管线索引](PIPELINE_DETAILS.md)
