# 技术合同

除标注外，均在 `witcher3.exe` 5.0.1048522（P4CL 13413172，DX12）上实测。

## 1. 版本与内容布局（`build-sensitive`）

- 次世代更新把内容合并进 `content\content0`：`content\content0\bundles\*.bundle` 加一个总的 `content\metadata.store`。
- bundle 头（v5，旧版 1.32 是 v3）：

  | 偏移 | 内容 |
  | --- | --- |
  | 0x00 | `POTATO70` |
  | 0x08 | u64 bundle 总长 |
  | 0x10 | u32 TOC 字节数（0x20 头之后） |
  | 0x14 | u16 版本 = 5 |
  | 0x16 | u32 TOC 字节数 + 0x20 |
  | 0x20 | TOC，每条 304 B：`name[256]`（latin-1，NUL 补齐，小写反斜杠路径）、`md5[16]`、u64 数据偏移、u32 原长、u32 压缩长、u32 CRC32（未压缩数据）、u8 压缩方式 |

  数据按 4096 对齐；压缩方式 0 无、1 zlib、2 snappy、3 doboz、4/5 lz4。游戏不校验 md5 字段（写出器照样填了）。旧版 v3 的条目是 320 B。
- `w3bundle.py`：`list [-v]`、`extract -p <通配> -o <目录>`（后面的 bundle 覆盖前面的，与游戏一致）、`pack`（v5，zlib 级别 9，压不小就存原样）。

## 2. 本地 mod 与 metadata.store v7（`build-sensitive`）

- 安装位置：`<游戏>\mods\<ModName>\content\blob0.bundle` + 同目录的 `metadata.store`。不需要脚本合并。
  `dx12user.settings`（文档目录）`[ContentManager/Mods] EnabledLocal=true` 是默认值。
- **只有 bundle、没有 metadata.store 的 mod 文件夹被整个忽略**（实测）。5.x 也不会替你生成。
- v7 布局（`w3metadata_write.py` 的写法，逆向自原版 store）：

  ```text
  03 56 54 4D | i32 version=7 | i32 maxSizeInBundle | i32 maxSizeInMemory
  VLQ 字符串表长度 + 字符串表
  VLQ n + FileInfo[n]   8 x u32: nameOff, 0, sizeInBundle, sizeInMemory, firstEntry, firstBuffer, numBuffers, compression
  VLQ n + FileEntry[n]  u64 offset, u32 sizeInBundle, u32 nextEntry, u32 fileId, u32 bundleId
  VLQ n + BundleInfo[n] u64 dataBlockSize, u32 dataBlockOffset, u32 nameOff, u32 firstEntry, u32 numEntries
  VLQ n + u32 bufferFileIds[n]
  VLQ n + DirInit[n]    i32 nameOff, i32 parentDir
  VLQ n + FileInit[n]   i32 fileId, i32 dirId, i32 nameOff        （非 buffer 文件）
  VLQ n + Hash[n]       u64 fnv1a64(小写路径), u64 fileId          （非 buffer 文件，按哈希排序）
  ```

  FileInfo / FileEntry / BundleInfo 的第 0 条是空记录。`<文件>.<N>.buffer` 算作所属文件的 buffer，不进目录和哈希表。VLQ：首字节
  0x80 负号、0x40 续位、低 6 位；后续字节 0x80 续位、低 7 位。
- 验证：用原版 bundle 重建原版 store（排除 `_censored` 文件，原版无删减 store 也不含它们），总长相同；FileInfo / FileEntry / Buffer / Hash 表
  逐字节一致；BundleInfo 只有 `buffers.bundle`（7.6 GB）一条不同：原版的 dataBlockSize 记 0，写出器记实际长度；目录表的顺序不同
  （字符串表同长但顺序不同，FileInit 的目录号随之不同）；头里两个 max 字段不同（`checks/regen_metadata_compare.py`，2026-10-23 复跑）。
  mod 用这份写出器的产物加载正常。

## 3. CR2W 与 WolvenKit 7

- 工具：WolvenKit 7 nightly `7.2.0-nightly.2026-10-14`（第一个支持 5.x CR2W 的 7.x 构建），只用它的 CLI 做 `--cr2w2json` /
  `--json2cr2w`。它的 `.exe.config` 要求 .NET Framework 4.8.1；只装了 4.8 的机器把 sku 改成 4.8 也能跑（`prepare.ps1` 这样做）。
- 头：160 B。偏移 24 / 28 是文件长与 buffer 长；偏移 32 是头 CRC = 头 160 B 的 crc32（计算时该字段填 `0xDEADBEEF`）；偏移 40 起
  10 张表各 12 B（偏移、数量、表的 crc32）。名字表每条 `u32 字符串偏移 + u32 FNV-1a32(含结尾 0 的字符串)`。导出表每条 24 B：
  `u16 类名、u16 标志、u32 父、u32 数据长、u32 数据偏移、u32 模板、u32 数据 crc32`。
- 字符串属性的原版编码：`<0x80 | 长度>` + 字符（VLQ 长度，0x80 表示单字节字符，无结尾 0）；类型名 `String`。
- **WolvenKit 7 的骨名陷阱（`invariant`，本项目二分定位）**：`SSkeletonBone` / `SSkeletonTrack` 的 `name`（String）
  它读的时候直接丢掉，写的时候写成 `StringAnsi`（`<长度+1> 字符 00`）。带这种骨架的 dyng 让 dangle 组件和所有蒙在它上面的网格隐形
  ——原版 dyng 经 WolvenKit 往返一次就能复现。处理：生成 JSON 时给每根骨补上 `name`，转回 CR2W 后跑
  `fix_cr2w_skeleton_names.py`：把名字表里的 `StringAnsi` 原地改成 `String`、把每个 name 改成原版编码，重算导出表大小 / 偏移 / crc、
  各表 crc、文件长和头 CRC。w3fac 的两个骨架（骨骼和浮点轨道）同样处理。
- 物品模板（w2ent）里有一份 `flatCompiledData`（嵌套的整份 CR2W）：改组件时外层和嵌套的都要改（各生成器都递归处理）。

## 4. 玩家实体与物品模板

- 杰洛特的玩家实体没有身体网格。躯干、腿、手套、靴子、头、发型都是物品，按 `equip_template` 名解析到
  `items\bodyparts\geralt_items\<类别>\*.w2ent`（DLC 的在 `dlc\*\data\items\bodyparts\geralt_items\...`）。本版共 817 个模板：
  trunk 398、gloves 124、legs 117、heads 79、shoes 66、coif 33，另有 scabbards（不动）。
- 覆盖方式（不改脚本，不改 XML）——`build_mod.py stage` 按 bundle 清单把每个路径写成下面三种之一：

  | 类别 | 写入 | 来源 |
  | --- | --- | --- |
  | trunk / legs / gloves / shoes | 空 `CItemEntity`（没有组件） | `trunk\bare\t_01_mg__body.w2ent` 去掉 `CMeshComponent`（`make_empty_item_template.py`） |
  | coif（发型，全部 33 个） | Karin 本体 + dyng | `coif\c_01_mg__witcher.w2ent` 最小修改（`make_dangle_item_template.py`） |
  | heads（全部 79 个） | Karin 的脸 + 表情 | `heads\h_01_mg__geralt.w2ent` 最小修改（`make_head_item_template.py`） |

- 原版发型物品 = `CItemEntity` + `CAnimDangleComponent 'c_02_mg__half_tail'` + `CAnimDangleConstraint_Dyng` + `CMeshComponent 'c_02_mg__hair_tie'`
  + 5 个 `CFurComponent`（HairWorks），都经 `CMeshSkinningAttachment` 蒙在 dangle 上。补丁：dyng 路径、发绳网格换成整个 Karin 网格（并改包围盒）、
  删掉 5 个毛发组件和它们的附着、约束 wind 3.0 → 0、按类属性顺序插入 gravity = 0（dampening 不设，与原版一致）。组件名和其余参数保持原版。
- **为什么放在发型里**：发型物品总是挂着，原版用它承载 dangle（`runtime-confirmed`）。早期把 dangle 物品放在头部槽位的一次测试没有显示，
  但那次同时有骨名问题，结论不干净（`hypothesis`）。
- 原版头部物品 = `CMimicComponent 'head'` + 蒙皮头网格 + 眼睛网格 + 法线混合（皱纹）组件 + 湿身组件。补丁：`mimicFace` → Karin 的 w3fac，
  头网格 → Karin 的脸，眼睛 → 0.1 mm 存根网格，删掉法线混合组件、它的附着和材质实例（Karin 的 `pbr_std` 脸没有皱纹贴图）。
- 玩家实体自己带一个颈部过渡网格 `characters\models\geralt\head\model\h_mg__neck_transition.w2mesh`，换成同路径的 0.1 mm 存根
  （`make_stub_mesh.py`，一个蒙在 neck 上的三角形）。
- 剑鞘挂在杰洛特背部的槽位上，没有改，会穿过双马尾；要改得动玩家实体或剑鞘模板。

## 5. 骨架与坐标（`invariant`）

- 骨架 `characters\base_entities\man_base\man_base.w2rig`，静止姿势不改：W3 动画带每根骨的平移，改骨长会被动画改回去。
- Witcher3-Blender-Tools 导入骨架时开着 rot90：**W3 世界矩阵 = Blender 骨的 `matrix_local @ Rz(90°)`**；新建的骨用
  `matrix = W3 @ Rz(−90°)`，导出器会补回来。头骨坐标系：X 朝上、Y 朝前、Z 朝角色左。W3 模型空间里角色的左边是 −x。
- 网格的骨索引是 u8：每个网格最多 256 根骨（Karin 身体网格 176 根）。蒙在 dangle 上的网格，导出骨架里去掉 `Root`、`Trajectory`、`Reference`、
  `IK_*`，保证网格的每根骨都在 dyng 骨架里。

## 6. 网格、材质与贴图

- 网格由插件的原生写出器写（`use_native_writer=True`，MikkTSpace 切线）：`isTwoSided`、`autohideDistance` 120。
- 材质：每个 Karin 材质一个本地 `pbr_std`（`engine\materials\graphs\pbr_std.w2mg`）：只给 Diffuse、`SpecularColor` 0.08、`RSpecBase` 0.6、
  `RSpecScale` 0；带透明的两个材质（`Karin_Alpha`、`Karin_Hair_Transparent`）用 `enableMask` + RGBA 漫反射。
- 贴图：2048² 未烘焙的 xbm（贴图组 `CharacterDiffuse` / `CharacterDiffuseWithAlpha`）直接打进 bundle，游戏能读。纯白的动漫漫反射在 W3 的角色光照下
  发亮，乘 0.82。插件的 xbm 写出器调用 texconv（WIC），Blender 后台模式要先 `CoInitializeEx`。
- **xbm 里写着源 PNG 的绝对路径（importFile）**：换一个工作目录，xbm 的字节和 bundle 哈希都会变，像素数据不变（[验证](VALIDATION_AND_RELEASE.md) §1）。

## 7. dyng（`CDyngResource`）格式

- 数组：`nodeNames`、`nodeParents`（名字）、`nodeMasses`、`nodeStifnesses`（原文拼写）、`nodeDistances`、`nodeTransforms`（相对父节点的局部矩阵）；
  `linkTypes`、`linkLengths`、`linkAs`、`linkBs`；`triangleAs`、`triangleBs`、`triangleCs`；`collisionParents`、`collisionRadiuses`、`collisionHeights`、
  `collisionTransforms`；内嵌 `CSkeleton`：`bones`（`name` + `nameAsCName`）、`parentIndices`、`rigdata`（位置、四元数、缩放）。
- 每个节点都有一条碰撞记录（半径 0、高 0.006、单位变换），跟原版头发一样；这个高度同时是让节点把 X 轴对准子节点的朝向半径。
- 约束 `CAnimDangleConstraint_Dyng` 的属性顺序：`dyng, animSet, drawlinks, drawcolls, drawlimits, dampening, gravity, speed, planeCollision,
  useOffsets, shake, wind, max_links_iterations`；原版物品只设 `wind` / `useOffsets`。
- 节点、链接、三角形的语义和取值见 [物理](PHYSICS.md) §1。`make_dyng.py` 以原版 `coif\model\c_02_mg__half_tail.w3dyng` 的 JSON 为模板，替换全部数组。

## 8. 表情（`CMimicFace`，`.w3fac`）

- 杰洛特的 `h_01_mg__geralt.w3fac`：`CMimicFace #0`（`mapping`、129 个 `mimicPoses`、法线混合区域、颈 / 头索引）、`CSkeleton #1`（面部骨架）、
  `CSkeleton #2`（148 条浮点轨道；轨道名就是表情姿势名，顺序与 `mimicPoses` 对应）。
- Karin 的版本（`make_w3fac.py`）：保留 6 根锚点骨（`torso3`、`l_shoulder`、`r_shoulder`、`neck`、`head`、`hroll`）和浮点轨道骨架；
  每根表情骨是一对 `placer_kf_NN`（头骨的子骨，静止偏移在头部空间、朝向同头骨）+ `kf_NN`（单位变换的子骨），共 6 + 2 × 100 = 206 根；
  `mapping` = 100 根 `kf_NN`；每个姿势对每根映射骨给一个只含 X / Y / Z 平移的 `EngineQsTransform`（全零就写空的，等于单位变换）。
- 脸部网格单独导出，骨架是锚点 + placer / kf 骨，`rotate_bones_90=True`。
