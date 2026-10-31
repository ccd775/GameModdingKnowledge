# 技术合同（DS2 PC 1.0.48.0）

数值除注明外都是 1.0.48.0 的 `build-sensitive` 值。坐标与西之绝境相同：x 向右、y 向前、z 向上，单位米。

## 1. 工具

| 工具 | 版本 / 来源 | 用途 |
| --- | --- | --- |
| `ds2_pc_mi_022.exe`（id-daemon） | 0.22，SHA-256 前缀 `bf28a9dc`；用户从 ReSHax 获取 | 按组导出 ascii 网格、骨架和 DDS；导入 ascii 网格（按 LOD、按网格下标）和 DDS（按贴图下标）。在干净根目录的 `LocalCacheWinGame` 里运行，写出 `NN_OFFSET.core` 和 `NN_OFFSET_mesh.stream` / `_texture.stream` |
| `Decima_pack_ds2.exe`（id-daemon） | 同一工具包，SHA-256 前缀 `b9fecd87` | 把 `pack\` 里的 `NN_OFFSET.*` 打成一个新包，并原地改写流图 |
| Odradek（ShadelessFox） | 1.0.49.0 的 DS2 构建 | 浏览资源；导出贴图（`odr.cmd -f dds -o <目录> <gid:idx> ...`）；它的 `types` / `extensions` JSON 是本项目 RTTI 读取器的类型表 |
| DirectXTex texconv | 2026.5.8.1 | PNG → BC1 / BC4 / BC7 |
| 本项目 Python（`ds2py`） | 见 [便携包](../../portable-kits/death-stranding-2/README.md) | 读流图和整组对象、核心补丁、链接表、构建、发行 |

HFW Mod Manager 不需要：打包器已经在 id-daemon 的工具包里。

## 2. 干净根目录

`setup_cleanroot.ps1` 建一个只给工具用的根目录（`%DS2_MODDING%\clean`）：

- `LocalCacheWinGame\package\` 里的包文件是游戏文件的**硬链接**，子目录是 junction；
- `streaming_graph.core` 是独立副本（打包器会原地写它），另有一个硬链接 `streaming_graph.core.org` 指向原版；
- `ds2_pc_mi_022.exe`、`Decima_pack_ds2.exe` 复制到 `LocalCacheWinGame`，`decima.ini` 写这个目录的路径。

**绝不原地写这里的任何包文件。** 游戏目录装了 mod 以后，导出、分析也都在这里做；本项目的 `Graph(<游戏目录>)` 在 `DS2_MODDING` 指向的工作区有 `clean\` 时自动改读它。

## 3. 流图 `streaming_graph.core`

文件 = 类型哈希（u64）+ 对象大小（u32）+ 一个 `StreamingGraphResource` 对象 + 4 个零字节。对象字段顺序和大小（1.0.48.0，文件 28 332 251 字节）：

| 字段 | 偏移 | 内容 |
| --- | --- | --- |
| ObjectUUID、IsPacked | 12、28 | 16 字节、1 字节 |
| TypeHashes | 29 | u32 个数 + 4762 × u64 |
| TypeTableData | 38 129 | u32 长度 + 字节：5 个 int32 的头（comp=0、stride=2、count、count、1），然后 count 个 u16，指向 TypeHashes |
| LinkTableID、LinkTableSize | 10 745 443 | u64（= 240，`streaming_links.stream` 在 Files 里的序号）、int32 |
| LocatorTable | 10 745 455 | 369 397 × u64 `Data`：**低 24 位文件序号，高 40 位偏移** |
| ArrayTable | 13 700 635 | 896 760 × u32 |
| SpanTable | 17 287 679 | 79 317 × 12 字节：`FileIndexAndIsPatch`（u32，最高位是 patch 标志）、`Length`（int32）、`Offset`（int32） |
| Groups | 18 239 487 | 79 317 × 68 字节：GroupID、NumObjects（int32），**GroupSize（int64）**，SubGroupStart / Count、RootStart / Count、SpanStart / Count、TypeStart / Count、LinkStart / LinkSize、LocatorStart / Count（u32），ObjectUUIDs（u32 个数 + 16 字节 × 个数，1.0.48.0 全为空） |
| SubGroups | 23 633 047 | 553 802 × u32，**存的是组号** |
| RootUUIDs、RootIndices | 25 848 259、26 656 471 | 50 513 × 16 字节、50 513 × u32 |
| Files | 26 858 527 | 241 个字符串：u32 长度 + **CRC32C（初值 0，不做终异或）** + UTF-8，如 `cache:package/package.18.00.core.stream` |
| PackFileOffsets | 26 871 327 | 每个文件一个 int32 数组，全为空 |
| PackFileLengths | 26 872 295 | 每个文件一个 int32 数组：所有 `.core.stream` 是 `[4]`，`.core` 和链接表是 `[]`（不是文件长度） |
| ObjectLocators 等 | 26 874 087 | 之后的字段与本项目无关 |

- 每个组的对象数据由它的 span 拼成；每个带 stream 的 `StreamingDataSource`（`Channel != 0xFF` 且 `Length > 0`）按顺序消耗该组的下一个 locator。
- 包文件是 DSAR 归档：逻辑偏移经块表映射到 LZ4 压缩块。
- **打包器的改动只在 SpanTable 和 LocatorTable**：被换的组的 span 改指新包（文件序号 0x80），被换的 stream 的 locator 改指新偏移，Groups 不变（v34：10 个 span、174 个 locator，共 918 字节）。
- 文件序号 0x80 是 `package.18.00.core.stream`，原版是 573 893 812 字节的拉美葡语语言包。开发时直接覆盖它；发行安装器改为在 Files 末尾**追加**一个新文件，见 [验证与发布](VALIDATION_AND_RELEASE.md#发行包)。

## 4. 链接表 `streaming_links.stream`

每个组的指针记录从它的 `LinkStart` 开始，共 `LinkSize` 字节，按对象反序列化时遇到指针的顺序排列。

- 记录 = 一个首字节加若干续字节。首字节：bit 7 = 还有续字节，**bit 6 = 带组字段**，低 6 位是数值；续字节每个 7 位，高位在前。
  - 不带组：只有对象下标，指向本组；
  - 带组：先是组字段，再是对象下标。`Ref` 的组字段是本组子组表里的**序号**，`StreamingRef` 的组字段直接是**组号**。
- 2 字节的本地记录最多装 13 位（下标 < 8192）。
- `relink.py` 在原位改写记录。目标短于原记录时，在前面补数值为 0 的续字节，长度保持不变。

实用规则：

- `Ref` 只能指向本组或它的子组。PrivateRoom 头发模型的部件（67695 / 67696）指不到 `50121:82`，因为 50121 不是它们的子组。
- 外观表 `31123:279.VariantDefs[n].Variant` 是 `StreamingRef`，可以指任意组；尸袋（ModelType 8）的记录只有 3 字节，装不下 50107，没改。
- 装备靴部件 40254 / 37072（右）和 26207（左）的记录只有 2 字节，装不下 15523 / 8554，改为把它们 LodMesh 的 `RuntimeMeshes.Mesh#0..2` 指向鞋的网格。
- `@<gid>:<idx>` 形式的字段：改写对象里所有指向该目标的链接（一个材质在全部 technique 里的同一张贴图绑定）。

## 5. RTTI 读取

`ds2rtti.py` 按 Odradek 的 `types_1048.json` / `extensions_1048.json` 通用地读对象，带额外二进制数据的类型由回调处理：

- `VertexArrayResource`、`IndexArrayResource`、`DataBufferResource`、`Texture`、`TextureList`、`ZivaRTResource`、`ShaderResource`、`LocalizedTextResource`；
- `PhysicsShapeResource` / `PhysicsRagdollResource`（`jolt.py`，移植自 Odradek）；
- `FacialRigSettingWithLODResource`（`riglogic.py`，大端 RigLogic 状态）；
- `UITexture`（本项目补的）：1 字节、小 / 大贴图的序列化长度（2 × int32），然后每张有长度的贴图一份 texture info。按长度断言，场景组 6744 的 653 个对象全部读通。

`group.py` 读整组对象时记下每个字段的字节位置（`__pos__`），核心补丁按位置原地写。骨架资源的 BindPose 是空的，绑定姿势由各网格的逆绑定矩阵求（`prep_ref.py` 的 `ref.json`）。

## 6. 导入工具不更新的字段

`ds2_pc_mi_022` 只更新 VertexArray / IndexArray 的计数和 `Primitive.EndIndex`。以下由 `patch_core.py` 按原版核心（`.core.pristine`）补：

| 字段 | 不补的后果 / 规则 |
| --- | --- |
| `RegularSkinnedMeshResource.StreamingDataSource.Length` | 网格变大时游戏读不全 |
| `PrimitiveSkinInfo.VertexCount` | 计数变了的 CsNbt* / CsNrm* 改成 VsNbt，`VertexComputeNbtCount = -1`（西之绝境的同一个坑） |
| 图元包围盒、`MeshHierarchyInfo.LocalBounds` | 被剔除 |
| `SkinnedMeshBoneBoundingBoxes`（网格和部件的） | 约定（以 `50108:514` 零误差验证）：以该骨为最大权重骨的顶点，在该骨局部空间（逆绑定矩阵）里的包围盒；Vec3 的 W：图元盒 W=Z，骨盒 W=1。根级粒子没有带盒的祖先时，共用第一个带盒关节的盒子 |

另外 `patch_core.py` 还做：部件隐藏标志（`hide_parts`）、逐网格逆绑定矩阵（`ibm`、`ibm_post`）、投影开关（`no_cast_shadow`，DrawFlags 低 2 位）、单字段补丁（`fields`，按字段路径写值或乘系数）、材质变量改名（`rename_vars`）。

## 7. 组与对象（1.0.48.0）

| 内容 | 组 / 对象 | 工具键 |
| --- | --- | --- |
| Porter 外观 | `DSPlayerBodyVariant` 50107:0 → `ArtPartsDataResource` 50108:0（主模型 50108:548，覆盖模型 50108:20 → 50111:7 外骨骼、50108:23 → 50119 头发；面部 50108:21 → 50108:59） | `7e9d` = 50108 |
| 身体网格 LOD0–2 | 50108:144 / 73 / 392（prim 0 身体材质、prim 1 手套材质） | |
| Porter 靴子 | 右 218 / 364 / 90，左 453 / 614 / 194；赤脚部件 50108:57（右）/ 35（左） | |
| 外套（长外套，裙子和尾巴的槽） | 50110:234 / 124 / 73，部件 50110:7，骨架同身体（50118） | 外套材质贴图套 50110:9 |
| Porter 专用组 | 50108、50109、50110、50113、50116 | |
| 共享头部组 | 67633、67636、67685、67648（所有外观共用，不能塌缩） | |
| 身体骨架 | 50118（379 骨，含 146 `Cloth_PBD`、6 `Belt_PBD`、3 `Strand_PBD`） | `47CC` |
| 头发模型 | `ArtPartsModelResource` 50119:0：根部件 50120:0 + 50121 的 14 个部件 + 50120 的 18 个部件；骨架 67712、表示骨架 67700；PBD 体 67699:2（34 条 × 8 点） | 50121 = `1a0d`，67700 = `1A0C` |
| 头发槽 | LodMesh 50121:82（LOD0–3 = 85 / 38 / 27 / 56） | |
| 头发贴图 | 图集 67704（`sam_hair_def_v00`）、涂装遮罩 67706、绒毛层 67705；淋浴变体图集 31301 | 67704 = `A60`，67706 = `AA4` |
| 脸皮 | LodMesh 50120:1：LOD0 253 / LOD1 81（带 ZivaRT，计数绑死）、**LOD2 186**、LOD3 229、LOD4 45；部件 50108:43 | |
| 面部 | 骨架 67711（341 骨；67692 = 前 299 个）；面部模型 50108:59；RigLogic `FacialRigSettingWithLODResource` 34853:315；眨眼设置 `BlinkSettingResource` 74336:1；脸部贴图组 67673 | 67711 = `19FF`，67673 = `F9A` |
| 玩家组 | 31123（单个约 130 MB 的核心）：外观表 279、`DSPlayerModelControlComponentResource` 201（HairApv 199 等）、涂装组件 131、装备磨损 5046、装备靴 | `B6B` |
| 装备靴 | `ShoesEntityResource` 31123:14101 → `ArtPartsModelResource` 31123:9366（50 个部件，表示骨架 31123:301）；ItemId 11–18 每种 6 个部件；鞋面 LodMesh 15523（左）/ 8554（右） | |
| 靴子贴图变体集 | 31225（只被 31123 和 4167 用） | `A15` |
| 场景替身头发 | 12706（`DSPlayerTakeOverState` 替身，16 个头发部件，骨架 12715）；6744（私人房间场景的头发演员，模型 6744:433） | 12706 = `2deb`，6744 = `7e9e` |

### 外观表

`DSPlayerStreamingControlComponentResource 31123:279.VariantDefs[ModelType]`：0 Suit 39983、1 Porter 50107、2 PrivateRoom 40436、3 SkeletonOnly 65631、4 Suit2 58940、5 Naked2 43771、6 Jacket 67631、7 Naked 34852、8 DeadbodyBag 5494。项目把 0 / 2 / 4 / 5 / 6 / 7 改指 50107:0。

用户确认过的玩法范围：私人房间里只能换 11 套 Suit（同一模型的迷彩 / 配色变体）和帽子 / 眼镜 / 面罩；开场的 Porter、家居服、裸身、夹克、尸袋这些剧情外观玩家选不了。

## 8. stream-only 规则

往 31123（以及只想塌缩的大组）写网格时，不改核心：

1. 网格的顶点数、三角形数补齐到原网格（Karin 的鞋每侧 2642 顶点 / 2802 三角形，补退化顶点和三角形到鞋面各级的计数）；塌缩本来就保持计数。
2. 工具导入后会重写这个组的核心。`make_mod_ds2.ps1` 要求它和 `.core.pristine` **逐字节相同**，然后删掉，只打包 mesh stream。
3. 31123（装备靴、玩家组里的 4 套头发）、12706、6744 都这样处理；v21 起包只多了几 MB，而 v25 把 31123 核心打进去时是 295 MB。

## 9. 运行时组件（31123 普查，只读）

会改变外观的玩家组件：涂装（`DSPlayerMeshPaintComponentResource` + 20 个 `DynamicMeshPaintComponentResource`）、湿身（`WaterEffectComponentResource` × 4）、时间雨腐蚀（`DSCorrosionControlComponentResource`）、装备磨损（`DSEquipmentShaderControlResource`）、冻伤、兜帽（`DSPlayerHoodControlEventResource` / `DSPlayerHoodBalloonComponentResource`）、帽子 / 眼镜 / 手套 / 枪套 / 背包带 / 备用靴挂件、显隐（`DSMultiVisibilityRequestsControlComponentResource` × 18、`DSMeshAlphaComponentResource` × 24、`DSPlayerHideEquipmentEventResource`）。哪些真正影响了 Karin，见 [材质与磨损](MATERIALS_AND_WEAR.md)。
