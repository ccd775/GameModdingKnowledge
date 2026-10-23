# 技术合同

除标注外，均在 Ubisoft Connect 版（产品 5059）v1.5.6 上实测；数据 ID、索引号、列号都是这个版本的（`build-sensitive`）。

## 1. 版本与工具

- 游戏：`ACOdyssey.exe`（同目录还有 `ACOdyssey_plus.exe`），游戏文件日期 2026-07-22，forge v28。只装在测试机上。
- AnvilToolkit 1.3.6（第三方，用户自备）通过自写的 AcoHarness 无界面调用（[开发工具](DEV_TOOLING.md) §1）；奥德赛的文件列表 `Odyssey.gfl` 来自
  Kamzik123/AnvilToolkit-Resources。.NET 9 便携运行时（9.0.18）运行 harness；Blender 5.0.1；DirectXTex `texconv`；Python 3.12 / 3.14
  （numpy；录像分析另用 OpenCV）。
- AnvilToolkit 1.3.6 对奥德赛的已知缺口（`build-sensitive`，随工具版本）：
  - `DataStorage.SchemaFileNames` 里没有奥德赛：导出 XML 时报 NullReference。harness 补上 `ACOdyssey`（也补了 `ACOrigins`），dll 里本来就嵌着这两个 schema；
  - 读奥德赛贴图的顶层 mip 会弹 GUI 文件对话框，无界面时卡死：只能读内联 mip 的贴图，也只拿它们做模板；
  - `TextureMapType` 枚举里没有奥德赛的 Mask0（值 12）：按数字传；
  - Reflex3 读取器只认影 / 幻景的格式，读不了奥德赛的物理 blob（[物理](PHYSICS.md) §1）。

## 2. forge v28 布局（`build-sensitive`）

| 位置 | 内容 |
| --- | --- |
| 文件头 | `scimitar\0`（9 B）、u32 版本 = 28、u64 forge 头的偏移 |
| forge 头 | u32 条目数、u32、i64、i64、i32、u32 max、u32 表数、i64 第一张表的偏移 |
| 表 | u32 条目数、u32、i64 索引偏移、i64 下一张表（−1 结束）、u32 first、u32 last、i64 名字表偏移、i64 |
| 索引行（20 B） | i64 数据偏移、u64 数据文件 ID、i32 大小 |
| 名字行（0xC0 B） | +0 u32 大小、+4 u64 ID、+40 u32 时间戳、+44 名字 `char[128]`（NUL 结尾） |

- 2026-10-19 在 `DataPC` / `DataPC_patch_01` 上量出；名字最初按 +40 读是错的（`rejected`），+44 才对。
- **名字表里存着数据文件名**，所以不需要文件列表也能按名字找数据文件：`aco_forge.py index` 输出 TSV（forge、行号、ID、偏移、大小、名字），
  `aco_locate.py` 在这些 TSV 上按名字 / ID / 正则查找。`extract` 写 `<行号>_-_<名字>.data`；行号就是文件名前缀，换版本会变。
- 数据文件本身是 AnvilToolkit 的 `DataFile` 压缩容器（harness 把 Oodle 的位置指到 AnvilToolkit 的 `Libs`），用 `unpack-data` / `pack-data` 处理；`pack-data` 沿用原文件的元数据，
  打回后再解开内容相同（`offline-accepted`）。
- 本作的 `.prefetch` 文件可以用 harness 的 `prefetch-*` 读写；从 v2 起不需要改（§3）。

## 3. 覆盖顺序与「每一份副本」

- **主世界的覆盖顺序：`DataPC_patch_01` > `dlc_<n>\*.forge` > `DataPC_SharedGroup_00`**（`runtime-confirmed`，v1 / v2 对照；forge 名单 `build-sensitive`）。
  DLC forge 重新打包了大量角色文件：卡珊德拉的 VisualMaster、身体容器、头部表、头发表在 `dlc_43`、`dlc_58`（含其中的 `DataPC_ACD_Connection`）里都有副本。
- 证据：v1 只改了 `DataPC_SharedGroup_00` 的副本 → VisualMaster 的修改被忽略（装备照常显示），身体容器里新加的材质也没被加载（Karin 网格和蒙皮正确，
  但整个是品红色）；DLC 里的身体容器副本只是 LODSelector 空壳。v2 改成写进每一份副本、材质放进 patch_01 的 LOD0 数据文件 → 贴图正确、装备消失。
  v2 的安装写进了 5 个 forge：根目录的 `DataPC_SharedGroup_00`、`DataPC_patch_01`，以及 `dlc_43`、`dlc_58` 下的 forge 和 `DataPC_ACD_Connection`。
- **规则（本作的原地替换方法，`invariant`）：一个数据 ID 的每一份副本都替换**；例外写进 `payload\skip.tsv`（`IDHEX<TAB>forge`）。v8 只有一项：
  `DataPC_SharedGroup_00` 里那份头发表是旧版本（还带着旧的 `ACD_CHF_PLA_Hair` 骨架），patch_01 的副本本来就压过它，保持原版
  （装进去会怎样没有测过，`hypothesis`）。
- **不需要改 `.prefetch`**：数据文件的根引用（LOD 网格、`ACD_Tex1` 模板）按需加载（v2 起，`runtime-confirmed`）。v1 曾替换游戏根目录的 `.prefetch`
  （安装器的 `payload\root\`），v2 去掉后没有影响。
- `aco_locate.py` 的「生效的那一份」是按名字排序的启发式：主 forge 的 patch（0）、其它主 forge（1）、DLC 的 patch（2）、DLC（3）；名字含 `_dlc`、`connection`、
  `throneroom` 的算 DLC。它把 `DataPC_SharedGroup_00` 排在 DLC 副本前面，和上面实测的覆盖顺序不一致：一个 ID 没有 `DataPC_patch_01` 副本时，
  它选出的那份可能不是主世界里生效的那份，覆盖顺序要紧时要按 forge 明确提取。DLC 区域加载自己的副本，Karin 在 DLC 区域是否正常没有测过。

## 4. 原地追加安装器（`aco_install.py`）

不解包、不重打 forge。项目记录里把它当作黑旗记忆重置（BFR）v2 的安装方式和社区工具 Forger 的同类做法（`reference-inferred`，没有逐项比对）。

- payload：`<IDHEX>[_任意].data`（打好的数据文件），可选 `skip.tsv`，可选 `root\*`（覆盖游戏根目录的同名文件）。
- 安装：
  1. 游戏在运行（`tasklist` 里有 `acodyssey`）或已有状态文件时拒绝；
  2. 遍历根目录的 `*.forge` 和 `dlc_*\*.forge`，对每个持有某 payload ID 的 forge（除去 `skip.tsv` 里的副本）记计划；有 ID 在哪都找不到时，
     什么都不写就停下；
  3. **先写状态** `<游戏目录>\.karin_aco_state.json`：来源目录、每个 forge 的原长、每个 ID 的索引行位置与原来的 20 字节、名字行位置与原来的 4 字节
     （写临时文件、fsync、原子替换），中断的安装也能卸载；`root\*` 先备份到 `<游戏目录>\.karin_aco_backup\` 并记下哈希；
  4. 把数据追加到 forge 末尾，索引行改成（新偏移、ID、新大小），名字行的 u32 大小改成新大小，fsync。每个 ID 打印写进了哪些 forge。
- 卸载：写回每个原索引行和名字行，把 forge 截断到原长；`root\*` 的备份核对哈希后还原；删掉状态文件。
- 证据：v1–v8 的每次安装都用它，游戏加载了追加的数据（`runtime-confirmed`）。发行包在测试机上的重新部署（2026-10-23）只在安装层面核对过：每一份副本都写了、
  `status` 的 `source` 指向包里的 payload（[验证与发布](VALIDATION_AND_RELEASE.md) §3）；游戏里的结论来自 build_v8 本身（payload 逐字节相同）。卸载后 forge 长度回到原值（agent 在测试机上核对 v1）；
  整个 forge 逐字节还原是按构造成立的，只在合成 forge 上逐字节验证过（2026-10-23，便携包核对），没有对测试机上的真实 forge 做整文件哈希。
- **游戏更新或文件校验会让状态失效**：装着 mod 时被更新 / 校验过，就不要再卸载（会把旧行写进新文件）；删掉状态文件，用 Ubisoft Connect 校验恢复原版。

## 5. 卡珊德拉的可视图与数据 ID（`build-sensitive`）

```text
ACD_CHF_PLA_Kassandra                          EntityBuilder 00000103E739C7D0
  模板实体 ACD_CHR_Playable_BaseEntity_Female   000001364A765740 → 骨架 ACD_Unisex_BaseSkeleton
  ACD_CHF_PLA_Kassandra_VisualMaster           00000103E739C903
    列 1 Body                                  00000103E739C908
         列 3 ACD_CHF_PLA_B01_A01_BodyKassandra LODSelector 容器 00000104280E464B（不流式加载）
              LOD0 00000104280E4653、LOD1 0000018482B71630  卡珊德拉专属，patch_01 里的独立数据文件
              LOD2–4 共用女性身体 0x141F5D46C36 / C3E / C46（不要替换）+ 附加骨架
    列 2 Outfit                                00000146D5F4AAFC  全部装备的 MASTER 表（含随头饰变化的发型）
    列 4 ACD_CHM_MER_ArmorItems_Selector
    列 6 Head                                  0000016424DFAD4B
         列 1–7 头 / 眼 / 眼影 / 汗 / 睫毛 / 眉 / 牙，列 8 眼球材质
         列 10 头发表 ACD_CHF_PLA_Kassandra_Hair  00000146D5F5EB4C
              列 3 ACD_CHF_PLA_Hair_NEW 骨架 00000194D13C465D（卡珊德拉专属）
              列 7 ACD_CHF_PLA_Kassandra_Hair_Offset 00000146D5F7B63B（辫子偏移）
              列 9 / 10 / 13 发型 LODSelector（GraphicVisualProperty：普通 0x141054A755C、兜帽、头盔）+ 行的 DynamicResources
         列 11 头部骨架（ACD_CHF_PLA_Kassandra_Head，见表情 §1）、列 12 HairTypes 标签、列 13 / 15 KinoRTCPSetter
         列 14 ACD_CHS_PLA_Head_Material（传奇服装的皮肤覆盖：Ethereal、Hades…）
```

另有 `ACD_CHS_PLA_AlexiosKassandra_Outfit_BuildTags_{Master,Body,Outfit,MetalLeather}`，没有改。

v8 的 payload（`build_mod.py`，字节数是 v8 的）：

| 数据文件 | 改动 | 字节 |
| --- | --- | --- |
| `00000103E739C903` VisualMaster | 去掉列 2（Outfit）：任何装备都不再显示（弓和箭袋不在这一列，仍然显示） | 682 |
| `00000104280E464B` BodyKassandra 容器 | LODSelector 的 LOD2–4 指到 Karin 的 LOD1；容器里的 LOD0 / LOD1 网格换成 Karin 的 | 815 495 |
| `00000104280E4653` LOD0 | Karin LOD0 + 4 个 `ACD_Tex1` 材质、纹理组、漫反射、共用平法线、Mask0（§8） | 4 890 287 |
| `0000018482B71630` LOD1 | Karin LOD1（材质解析到 LOD0 数据文件里的对象） | 305 434 |
| `0000016424DFAD4B` 头部表 | 去掉列 1–8 和 14；保留头部骨架、头发表、标签 | 1 485 |
| `00000146D5F5EB4C` 头发表 | 去掉列 9 / 10 / 13，清空行的 `DynamicResources`；保留发型骨架和辫子偏移；SharedGroup 的旧版不装 | 507 |
| `00000194D13C465D` `ACD_CHF_PLA_Hair_NEW` | Karin 的物理骨架（[物理](PHYSICS.md) §2） | 15 537 |

- 只去掉头发列时（v2）辫子还在后颈：辫子来自头发表，行的 `DynamicResources` 也会加载发型网格（`runtime-confirmed`，v2 → v3）。
- 新对象 ID（`case-derived`）：材质 `0x2A0CA5A0001`–`0004`（Face、Body、Hair、Costume；十进制 2889612918785–788，导出时用作材质名）、
  纹理组 `…11`–`14`、漫反射 `…21`–`24`、共用平法线 `…31`、Mask0 `…32`。动手前核对过 `0x2A0CA5A00xx` 这一段在 v1.5.6 的索引和文件列表里没人用。
- LODSelector 里 LOD1 的路径：`DataPC_patch_01\ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1\ACD_CHF_PLA_B01_A01_BodyKassandra_LOD1.Mesh`。

## 6. 坐标系（`build-sensitive`：游戏 v1.5.6 的数据、AnvilToolkit 1.3.6 的轴约定）

| 坐标系 | 轴 |
| --- | --- |
| 网格 / 原始 GLB（AnvilToolkit 不做轴转换） | X = 角色的左、−Y = 前、Z = 上，原点在地面 |
| 影的原始坐标系（影项目的拟合脚本按它写） | X = 前、Y = 左、Z = 上；影 = Rz(+90°) · 奥德赛 |
| Blender 里（glTF 导入做了 Y-up 转换） | 前 +X、上 −Y、左 +Z（拟合、表情脚本都按这个） |
| Reference 起的骨架（`ACD_Unisex_BaseSkeleton`、`Female_Boobs` 附加骨架） | X = 前、Y = 左、Z = 上，原点在 Hips；`RootBoneDefaultLocalPosition` (0, 0, 0.964) |
| 头部骨架 `ACD_CHF_PLA_Kassandra_Head`（Neck 起） | X = 上、+Y = 前、+Z = 左；绕 +Z 正转 = 前端向下 = 闭眼方向 |
| 原版物理链骨 | 局部 +X 沿链向下、+Y 前后（矢状）、+Z = X × Y（角色的右） |

- `glb_rotate.py`：整体绕原始竖轴旋转：蒙皮网格的位置 / 法线 / 切线 p → Q p，IBM → IBM Q⁻¹，根节点（蒙皮网格节点除外）L → Q L，重算 POSITION 的 min / max。
  拟合前把卡珊德拉的骨架 GLB 转 +90°，导出的 Karin LOD 转 −90°；往返精确，导入后 Karin 的绑定与原版骨的位置差在 0.1 mm 内、旋转差在 2e-4 内
  （`offline-accepted`）；v1 起实机蒙皮正确（`runtime-load-pass`，agent 截图）。
- 骨 ID = 骨名的 CRC32（网格骨、Reflex 记录都是）。头部骨在工具的名字表里没有名字，拟合骨架里用十进制 ID 当骨名。

## 7. 网格导入

- `AcoHarness import-glb <glb> 0 <out.Mesh> <IDHEX>`，奥德赛分支按 AnvilToolkit 给 Origins / Odyssey 的导入选项：顶点格式版本 4、没有宽索引；
  带蒙皮的 v4 格式只有 `Pos3s_Norm4ub_Col4ub_Tex2s_Joint{4,8}_8bit`（一组颜色、一组 UV，法线 + 切线 + 副法线符号打包）。harness 补白色 Color0、
  缺副法线时取 N × T、强制切线 / 副法线、**超过 255 根骨拒绝**、自动缩放（`Scale` = 包围盒绝对最大值向上取整），并修正零 / NaN 法线和切线
  （否则写到一半中断）。
- `export_karin_lods.py --profile aco_tex1`：材质改名为目标 Material ID（十进制）、合并成一个网格、三角化、白色顶点色、每顶点最多 4 个归一化权重、
  骨架裁到用到的骨和它们的祖先；LOD 比例 1、0.5；`--keep-full Body` 让 Karin 的脸（源模型里网格名叫 `Body`）在 LOD1 不减面并拷回自定义法线；
  `Karin_Alpha` 的面（眼泪、红晕等只靠表情形状键露出来的叠加层）删掉。
- 骨数：没有物理骨时 52 根、4 个图元（v2）；加上 KP 物理骨后 152 根（v4 起）。
- 游戏用网格自己的绑定矩阵蒙皮（影项目里验证过，奥德赛 v4 起虹膜和眼睑在静止时正常，`runtime-confirmed`），表情的绑定偏移依赖这一点（[表情](FACE.md) §2）。

## 8. 材质（`ACD_Tex1`）与贴图

- **角色模板吃编码贴图**（`rejected` 作为 Karin 的材质）：`ACD_CHS_SHR_Skin` 的漫反射是皮肤参数；`ACD_CHS_Fabric` / MetalNLeather 的漫反射 R 是颜色索引
  （见到 255 / 192 / 38）、G 是布料 ID。为此做过的 2×2 图集路线（所有面放进卡珊德拉头部皮肤材质 1426570796496，4096² BC7 约 22 MB；
  `aco_pack_atlas.py`、`build_atlas.py`、导出配置 `aco_atlas`）在查明这一点后放弃，没有进游戏。
- **`ACD_Tex1`**（`0000004077569BF5`，道具和玩家的弓剑用）是普通 PBR：`3:Layer0_Diffuse` 反照率 RGBA；`3:Layer0_Normal` RG 法线 + **B 金属度 + A 光泽度**；
  `3:Layer0_SpecularOcclusion` = Mask0（贴图类型 12），**B** = 高光遮蔽；`1:Layer0_ScaleU/V`。
- Karin 的 4 个材质（Face、Body、Hair、Costume；`Karin_Hair_Transparent` 与 Hair 共用一个材质）从不透明的弓 `ACD_CHW_PLA_01_BowAlexios` 的材质 /
  纹理组 XML 换 ID 生成（弓：材质 535855619145、纹理组 …945、漫反射 …950、法线 …954、Mask0 …958），`TwoSided` 设 True，纹理组路径改指 LOD0 数据文件。
- 贴图：漫反射 `texconv` BC7_UNORM_SRGB 2048²（`--tex-size`）；`tex-import <模板> <dds> <out> --id <HEX>`，模板是卡珊德拉头部数据文件里只有内联 mip 的贴图
  （漫反射 sRGB、法线线性），输出沿用模板的（空的）顶层 mip 列表 → 所有 mip 都内联。共用 64² 平法线 RGBA (128, 128, 0, 光泽 70)，金属度 0；
  64² Mask0 (255, 255, 255, 255)，`--maptype 12`。
- **材质、纹理组、贴图都放进 patch_01 的 LOD0 数据文件**（网格后面的对象 1…n），随网格一起加载；LOD1 的材质引用解析到这些对象（v2 起，`runtime-confirmed`）。
- 未做 / 未查：4K 贴图（现在 2048）；头发透明卡片的透明效果没有单独检查。

## 9. 表与 XML 编译

- BuildTable 的每行（`BuildRow`）由按列号命名的 `DynamicProperty` 单元组成（Handle / Reference / GraphicVisualProperty）。`bt_tool.py edit`：
  `--drop` 从每一行删掉这些列，`--set 列=ID[:路径]` 改引用，`--clear-dynres` 清空每行的 `DynamicResources`（随行加载的句柄）。
  `lodsel` 改 `LODDescriptor` 的 `Object` 引用。
- **空引用的填充字节**（`build-sensitive`，AnvilToolkit 1.3.6 的奥德赛写出器）：原版 XML 原样 `compile-xml` 回去，空引用指针类型（3）后面那个字节原版是 1、
  写出器写 0（VisualMaster 上 4 个字节，Hair_NEW 骨架 2 个）。在 XML 里补 `ReferenceType="1"`（`bt_tool.fix_null_refs`，现在仍然会补）不够（`rejected`）。
  `build_mod.compile_fixed`：再编译一遍原版 XML，找出「原版 1、重编 0、前一字节 3」的位置，用 `difflib` 的匹配块映射到改过的编译结果上补回 1；
  落在被删掉的单元里的字节没有对应位置（引用已经没了）。
- `compile-xml` 在它覆盖的文件旁留 `<文件>.bak`，打包前删掉（`build_mod.pack`）。
- `unpack-export` 不给二进制资源导出 XML（Mesh、TextureMap、CompiledMip、Animation、CompiledTextureMap、HairMesh、RawAsset、CompiledMesh）。

头部骨架、表情姿势和视线定义见 [表情](FACE.md) §1；Reflex3 物理记录见 [物理](PHYSICS.md) §1。
