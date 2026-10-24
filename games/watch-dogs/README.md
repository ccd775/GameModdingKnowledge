# Watch Dogs (2014)

## 项目结果

Karin v1.3.0 替换 Aiden 默认“私法制裁者”服装。商店服装、DLC、囚服、开场和剧情强制模型不在范围内。Blender -> FBX -> ZModeler Compound -> XBG -> XBT/FAT/DAT -> ModManager 的生产链已冻结，用户于 2026-08-05 实机接受。

**2026-10-03 更新：不再需要 ZModeler。** 项目自写的纯 Python 写出器直接生成 `char01.xbg`。用它生成的 1.4（手指与脚跟修复）、1.5（缩短锁骨的骨架修改）和 Karin_Original 0.1.2（从 VRM 直接构建，骨架贴合模型）都经用户实机认可。格式、合同和范围见 [不用 ZModeler 生成 XBG](XBG_WITHOUT_ZMODELER.md)，脚本在 [便携包](../../portable-kits/watch-dogs/README.md)。便携包还带通用 VRM 构建器：VRM + 配置文件 + 已有的 char01 底包，一条命令生成 XBG、XBT 和 ModManager 包。

**2026-10-06 更新：物理和剧情模型。**

- Karin 1.6.0 和 Karin_Original 1.0.0 都经用户实机验收并发布。
- 剧情强制模型也换成了 Karin：开场、受伤带血、囚服、车祸。开场过场和车祸闪回是预渲染视频，换不了。
- 物理：
  - 双马尾、尾巴、耳朵、头发、发带用链，原地晃动；
  - 大衣或裙子挂在模板自带的大衣布料上，会随身体运动、被腿顶起。
- 格式、实测行为和限制见 [char01 物理](PHYSICS.md)。VRM 构建器的配置文件加 `physics` 段即可使用。

**2026-10-07 起：第三个替换 Karin City Noir（试验）。** 夹克用大衣布料改成的披肩，构建器新增几项配置（骨链悬挂、权重改挂、按槽位重排 UV 岛、加大漫反射贴图）。实机结果：
- 夹克能跟随身体运动；跑动摆臂时手肘会从披肩里穿出来；
- 重排 UV 后尾巴贴图正常。

发带"镂空"的问题还没有解决。见 [char01 物理](PHYSICS.md) §7 和便携包说明。

**2026-10-10：与 The Fall of Windy City II 兼容。** WC2 改写了 Aiden 的头部材质，Karin 的脸因此发黑。修法是给包换上私有头部材质和私有头部贴图，已在实机确认。见 [Windy City II 兼容](WINDY_CITY_2_COMPAT.md)。

**2026-10-24：面部表情。** 面部骨骼会被面部定义 `char01_facial_definition.dpdx` 重置。改写这份文件、作为新条目打进包以后，眨眼、视线、张嘴就能跟着游戏的面部动画动。
- 实机（Karin_Original 1.1.0-test）：游戏读取包里的 dpdx，嘴会动；但眨眼闭不严，眼珠几乎看不出在动。
- 修正版是 Karin_Original 1.1.1-test 和蓝白 Karin 1.7.0-test：眼睑改成平移，视线 ×2。离线验证通过，尚未实机。

见 [面部表情](FACE.md)。

## 最重要的工程合同

- **无 ZModeler 路线**：以已被游戏接受的 char01.xbg 为模板，保留材质表、骨架和物理块，只重写调色板、LOD 表和 GPU 缓冲区。
- **矩阵表对齐**：节点表后的逆绑定矩阵表必须从文件绝对偏移的 16 字节边界开始。调色板长度变化时必须重新计算补零，否则读档到一半崩溃。
- **骨架**：
  - 身体骨骼的绑定位置游戏会采用，所以新模型应让骨架贴合模型；
  - 面部骨骼（`Facial_Hook` 下）的局部变换由面部定义 `char01_facial_definition.dpdx` 重建。要挪面部骨骼，必须同时改 dpdx 里的静止平移，并把它作为新条目打进包；
  - 不做表情时，脸只蒙皮到 `Head`。
- **ZModeler 路线**（历史/对照）：XBG 必须是干净的双 LOD Compound，根层只保留 `char01.skel` 和 `char01.mesh`，state 只保留 `L0/L1`；FBX 导入固定为 axes/geometry `1.000`、Blender axis system。
- **回读与审计**：导出后同时做 GPU buffer audit 和回读（写出器逐值回读，ZModeler 路线用全新进程回读）；日志无 error 或预览可见都不能替代这两道检查。
- **XBT**：低/高两档 streamed 贴图必须保留 donor header，分别注入尺寸和 mip 链与之匹配的 DDS；不用 texconv 时可用 Pillow 按 mip 级逐级做 DXT 编码。
- **打包**：diffuse、emission、glow mask 分开处理；最终运行包只带声明的 XBG、XBT、私有材质和兼容数据库资源。头部要用私有材质和私有贴图，否则改写 Aiden 头部材质的 mod（WC2）会把脸弄黑。
- **物理块**：物理节点 flags 的高 16 位是挂点序号，越界的节点不会被模拟。链只跟随挂点骨骼的转动，没有"跑动时向后飘"。大衣布料的静止形状取自粒子的绑定位置，可以外推和改挂。短裙要整块挂到胯部上。
- **发布与回滚**：采用版本化目录和冻结哈希；运行时失败回滚到上一个冻结包，不覆盖原版游戏数据或其他 Mod。

## 结果与限制

v1.3.0 的双 LOD、GPU buffer、fresh-process、ModManager payload 和基础动作检查都已通过。双马尾孔位、脖套动态和手部权重得到修复；少数持枪/插兜动作仍有轻微手指变形，属于 1.3.0 的已接受限制。

- **1.4** 修复了手指和脚跟的支点偏移。
- **1.5** 收窄了肩宽；肩到上臂的过渡还略不自然。
- **Karin_Original 0.1.2** 只确认了读档、脸部和眼睛。以下尚未单独确认：脚是否悬空或陷地、双手持枪（肩比 Aiden 窄）、尾巴和裙子是否穿模。它没有面部表情和次级物理。

## 文档

- [不用 ZModeler 生成 XBG](XBG_WITHOUT_ZMODELER.md)
- [char01 物理](PHYSICS.md)
- [面部表情](FACE.md)
- [Windy City II 兼容](WINDY_CITY_2_COMPAT.md)
- [端到端生产 SOP](SOP_WATCH_DOGS_CHARACTER_REPLACEMENT.md)
- [ZModeler 操作清单](ZMODELER_OPERATOR_CHECKLIST.md)（历史路线）
- [XBT 贴图管线](XBT_TEXTURE_PIPELINE.md)
- [部署与回滚](DEPLOYMENT_WATCH_DOGS_KARIN.md)
- [完整管线索引](PIPELINE_DETAILS.md)
