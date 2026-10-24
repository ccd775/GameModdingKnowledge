# 技术合同

除标注外，均在 Steam 版（289650）build 21970519、游戏内 1.5.1 上实测；数据 ID、索引号、列号都是这个版本的（`build-sensitive`）。

## 1. 版本与工具

- 游戏：`ACU.exe`，Steam 289650，经 Ubisoft Connect 启动（要登录 Ubisoft 账号）。forge v27，63 个 forge（根目录 59 个，`dlc_10\`、`dlc_11\` 下 4 个），
  索引共 180 245 行。
- AnvilToolkit 1.3.6（第三方，用户自备）通过自写的 AcuHarness 无界面调用（[开发工具](DEV_TOOLING.md) §1）；文件列表 `Unity.gfl` 来自
  Kamzik123/AnvilToolkit-Resources。.NET 9 便携运行时（9.0.18）运行 harness；Blender 5.0.1；DirectXTex `texconv`；Python 3（项目用 3.14；便携包要求 3.10+；numpy、Pillow）。
- 与奥德赛（`games/assassins-creed-odyssey/TECHNICAL_CONTRACTS.md`）相比：AnvilToolkit 1.3.6 认得大革命的 schema（不用补
  `SchemaFileNames`）；表 XML 编译回去逐字节相同（不用修补空引用的填充字节）；读顶层 mip 的问题照旧，贴图模板只用内联 mip 的。

## 2. forge v27 布局（`build-sensitive`）

和奥德赛的 v28 相同（2026-10-24 在 `DataPC` / `DataPC_patch_01` 上量出）：

| 位置 | 内容 |
| --- | --- |
| 文件头 | `scimitar\0`（9 B）、u32 版本 = 27、u64 forge 头的偏移（1050） |
| forge 头 | u32 条目数、u32、i64、i64、i32、u32 max、u32 表数、i64 第一张表的偏移 |
| 表 | u32 条目数、u32、i64 索引偏移、i64 下一张表（−1 结束）、u32 first、u32 last、i64 名字表偏移、i64 |
| 索引行（20 B） | i64 数据偏移、u64 数据文件 ID、i32 大小 |
| 名字行（0xC0 B） | +0 u32 大小、+40 u32 时间戳、+44 名字 `char[128]` |

- 名字表里存着数据文件名：`acu_forge.py index` 输出 TSV（forge、行号、ID、偏移、大小、名字），按名字 / ID 直接 grep。`extract` 写
  `<行号>_-_<名字>.data`。DLC forge 在 TSV 里写成 `dlc_<n>\<名字>.forge`。
- 数据文件是 AnvilToolkit 的 `DataFile` 容器，用 harness 的 `unpack-data` / `pack-data` 处理；`pack-data` 沿用原文件的元数据。**同样的输入每次打出的容器字节
  都不同，解开后的对象逐字节相同**（2026-10-24 用便携包重建 v7：457 个数据文件的 14 585 个对象全部相同），所以比较构建结果要解包后比。

## 3. 内嵌副本与「每一个数据文件」

大革命把同一批对象（同样的对象 ID）嵌在多个数据文件里，这是本作和奥德赛最大的不同（`build-sensitive`，`runtime-confirmed`）：

- 玩家实体 `CN_P_Arno`（数据文件 `000000070CF6709B`）带着 EntityBuilder 和亚诺的全部 BuildTable；它在每个 world forge（巴黎、凡尔赛、序章、
  `RebirthRitual`、`TitleScreenFPP`、三个 `LGS_*` 时空裂隙、`dlc_11` 的 Saint-Denis）和它们的 patch 里各有一份，共 21 份，**21 份的大小各不相同**（按索引）。
- 界面数据 `DataAI_UIDataRoot`（`0000001842175574`，18 份）嵌着亚诺的整套外观表（Heads、Body_All、Body_Custom、Hoods、UpperBodies……）。
- 每个旧时代服装的数据文件（Altair、Ezio、Connor、Edward、Comet、Bellec、McFarlane、Fearless、UltimateArno、ThomasCarneillon）都嵌着 Heads、
  Hood_Position、亚诺的附加骨架表这些副本。
- **v1 只改了 `CN_P_Arno`**：Karin 的网格、蒙皮、贴图都对，但亚诺的整套装备（兜帽盖住脸、外套、披肩、腰带、裤子、靴子）和牙齿照样画出来
  （agent 本机截图，`runtime-rejected`）。**v2 把每一份都改了** → 只剩 Karin（`runtime-confirmed`）。引擎用的是先加载的那一份；
  具体哪一份起作用没有单独隔离（`hypothesis`），规则是全部都改（`invariant`，本作的原地替换方法）。
- 查法：`scan_objs.py <log> <IDHEX,…> <forge 名或子串>…` 调 harness 的 `scan-objs`，在内存里解压每个数据文件，列出自身 ID 是目标之一的对象；
  `objs_to_tsv.py` 汇成 `arno_tables.tsv`（forge、数据文件 ID、名字、对象 ID）。v1.5.1：**21 个 forge 里的 189 个数据文件（基础游戏 177 个、`dlc_11` 的 Saint-Denis 12 个）、669 个对象行**；
  `_assets` / `_gi` forge 里一个都没有。
- 玩家怎么选：EntitySelector → 世界里 PlayableSelector、菜单里 MenuSelector（模板 `CHR_UI_BaseEntity_Male`，来自 `DataAI_UIDataRoot`）→ `CN_P_Arno`
  或某个旧时代服装的 EntityBuilder（`reference-inferred`，从表结构读出）。
- 同一个 ID 在不同 forge 里是不同版本，所以表的修改**按副本各自构建**：`payload/forge/<forge>/<IDHEX>_<名字>.data`（forge 路径里的 `\` 写成 `__`）。
  没有可改内容的副本写进 `payload/skip.tsv`：v7 有 14 行，都是 `CN_P_LegacyAvatar_ThomasCarneillon` 在巴黎以外的 952 字节空壳（完整的那份只在巴黎）。

## 4. 原地追加安装器（`acu_install.py`）

奥德赛安装器的大革命副本（`games/assassins-creed-odyssey/TECHNICAL_CONTRACTS.md` §4），不解包、不重打 forge：

- payload：`<IDHEX>[_任意].data`（所有副本共用的通用文件）、`forge/<forge>/<IDHEX>[_任意].data`（某个 forge 的专用版本，优先于通用文件）、
  `skip.tsv`（`IDHEX<TAB>forge`，保持原版的副本）、`vanilla_sizes.tsv`（`forge<TAB>大小`，制作时的原版大小）。也可以直接给 `payload_<标签>.tar.xz`，
  安装器用 Python 的 `tarfile` 解到临时目录（Windows 自带的 `tar` 读不了 xz）。
- 安装：游戏在运行（`tasklist` 里有 `acu.exe`）或已有状态文件时拒绝；某个 ID 的某份副本既没有 payload 也不在 `skip.tsv` 里 → 列出来，什么都不写；
  有 `vanilla_sizes.tsv` 时，要动的每个 forge 大小必须和它一致（其它版本或已装了别的 mod 都会拒绝）；有 forge 专用版本却对不上任何索引行也拒绝。
  然后**先写状态**（`<游戏目录>\.karin_acu_state.json`：每个 forge 的原长、每个 ID 的索引行与名字行的位置和原字节），再把数据追加到末尾、改指索引行、
  改名字行的大小，fsync。
- 卸载：写回原行，把每个 forge 截断到原长，删状态文件。
- 找游戏：`--game`，或 `ACU_GAME_DIR`，或 Steam 库（注册表 `SteamPath` + `libraryfolders.vdf`，找含 `ACU.exe` 的 `steamapps\common\Assassin's Creed Unity`）。
- v7：33 个 ID、21 个 forge、471 个索引行，payload 232.7 MB（456 个按 forge 的版本 + 1 个通用的头部容器）。
- 证据：v1–v7 的每次安装都用它，游戏加载了追加的数据（`runtime-confirmed`）。每个发行包都在本机用包里的 `.cmd` 做过安装 → 状态 → 卸载往返：
  63 个 forge 全部回到原版大小（`offline-accepted`）；整文件逐字节还原只在合成 forge 上验证过（便携包核对）。

## 5. 亚诺的可视图与数据 ID（`build-sensitive`）

```text
CN_P_Arno（EntityBuilder，数据文件 000000070CF6709B）
  模板 CHR_Playable_BaseEntity_Male → 骨架 ACU_BaseSkeleton_Male（DataPC 的 "Game Bootstrap Settings"）
  CN_P_ArnoAvatar_VisualMaster：列 4 Heads、列 6 Body_All、列 7 CHR_Animation_Male_Expression_Pack
    Heads（0x26A4C11760）：列 14 头部骨架 CN_U_Arno_Head_Rig、15 头部 LODSelector、16 眼 / 牙、20 湿润、21 睫毛、33 伤疤
    Body_All（0x145368098E）：列 7 CN_P_ArnoAvatar_Skeleton（附加骨架表 0x1453680995）、列 8 Body_Custom
      Body_Custom（0x2DFA9960D6）：1 Hoods、2 UpperBodies、3 Belts、4 Pants、5 ThrowBlade、6 ColorSets、8 Hood_Position（亚诺的头发）
单独的数据文件：
  CN_U_FR_Arno_Head（000000313DB95D16，15 份、3 种大小）：LODSelector + LOD0–3 网格 + 皮肤材质 CN_Skin_Wrinkle
    LOD0 000000126C7EB58B、LOD1 000000313DB95D1D、LOD2 000000313DB95D2E、LOD3 000000313DB95D33
  Arno_Head（00000010ED459755，15 份）：Arno_Head BuildTable（眼 / 牙、睫毛、湿润的 LODSelector + 头部骨架）
```

`build_mod.py` 的 `TABLE_DROPS`（每一行都去掉这些列）：

| 表 | 去掉的列 | 效果 |
| --- | --- | --- |
| Body_All | 8 | 去掉 Body_Custom |
| Body_Custom | 1–6、8 | 全部装备表 |
| Hoods | 2、3、4、10、11、12、14、16 | 兜帽（戴上 / 放下的网格、布料、骨架） |
| UpperBodies | 1、2、4、5、6、7、13、14 | 上衣 |
| Belts | 2、4、6、7、8、10 | 腰带 |
| Pants | 1、3 | 裤子（+ 靴子骨架） |
| ThrowBlade | 1、3、5、6 | 护腕 / 标志性武器的外观 |
| Hood_Position | 5、6、7、9、10、11 | 兜帽遮挡、亚诺的头发和头发骨架 |
| Heads | 16、20、21、33 | 眼 / 牙、湿润、睫毛、伤疤 |
| Arno_Head | 16、20、21、31、33 | 同上 + 囚犯胡子 |

- 旧时代服装：它们自己的 Body / Visuals / Softbody / 装备表只在自己的数据文件里（名字匹配 `LegacyAvatar|PrologueAssassin_(Body|Softbody|Skeleton)`），
  这些表的每个 GraphicObject / SoftBody / TextureSet 列都去掉。Connor、Edward、Comet 的头用 `Arno_Head`。旧时代服装在游戏里是否只剩 Karin，没有检查过。
- 头部容器只换 4 个 LOD 网格（同 ID），头部骨架（Heads 列 14）和 LODSelector（列 15）保留。去掉身体和全部装备后，整个角色就是头部容器里的 Karin。
- 新 ID 从 `0x4B41520000` 起（原版最大的数据文件 ID 是 `0x3F57BB287B`）：材质 +0x01..04（Face、Body、Hair、Costume）、纹理组 +0x11..、漫反射 +0x21..、
  平法线 +0x31..、共用的高光图 +0x41、纹理组的 Source 句柄 +0x51..、物理骨架 `Karin_Phys` +0xF00（`323218444032`）、它的 `BallJointCommonData` +0xF01、
  `LiteRagdoll` +0xF02、骨与修饰器的内联对象 +0x1000 起。

## 6. 坐标系与拟合

- 大革命的原始坐标系和奥德赛相同（X 左、−Y 前、Z 上），所以沿用奥德赛的做法：拟合前把亚诺的骨架 GLB 绕竖轴转 +90°，导出的 Karin LOD 导入前转 −90°
  （`glb_rotate.py`，往返精确）。
- 骨名和奥德赛同一套；**没有 `Neck1`**（Neck → Head），`fit_karin.py` 的 Neck 权重拆分只在目标骨架有 `Neck1` 时才做。
- 拟合（躯干最小二乘）比例 1.6541，鞋底 −0.004，`--foot-squash 0.8`。
- `export-glb` 写出的顶点位置除以网格的 `Scale`（亚诺的角色网格是 2），反向绑定矩阵再乘回来，所以骨架变形后的静止形状已经是原尺寸
  （`render_compare.py --ref-scale 1`，2026-10-24 量过）。

## 7. 网格导入（AcuHarness `import-glb`，Unity 分支）

- 顶点格式 v2：`Pos3s_Col1s_Norm3ub_Col1ub_Tan4ub_Binorm4ub_Tex2s_Joint4`（或 `Joint8`）：两个颜色（Col1s 在 Pos.w、Col1ub 在 Norm.w）、切线 + 副法线、一套 UV。
  harness 给缺的 Color0 / Color1 填白，缺副法线时取 N×T。
- **最多 255 根骨**（v2 没有宽索引，超过就拒绝）。Karin 的 LOD 是 159 根：53 根基础骨、6 根头部骨架骨、100 根 KP 物理骨；纯数字的骨名按原始 ID 导入。
  每根网格骨都要在加载的某个骨架里（基础骨架、头部骨架、`Karin_Phys`）。
- 自动缩放：Karin 的网格 `Scale` = 3。

## 8. 材质（`CN_Weapon_NoAlphaTest`）

- 角色模板（`CN_Skin_Wrinkle`、`CN_Cloth_Tile_ColorMasked_AlphaTest`）吃染色遮罩、皮肤参数这类编码贴图，不是普通的反照率。
- Karin 用武器模板 `CN_Weapon_NoAlphaTest`（材质 `75838371526`，在 DataPC 的 "Game Bootstrap Settings"；XML 模板 `1Handed_Sp2.Material` /
  `CN_W_1Handed_Sp2_Set.TextureSet`）：`3:Layer0_Diffuse` = 反照率；`3:Layer0_Normal` = RG 法线、**A = 光泽度**（B 0）；`3:Layer0_SpecularReflectance`
  = RGB 高光颜色（sRGB）。改 `TwoSided` = True、`Category` = `RC_Character`，引用路径改到头部容器。
- 贴图都是内联 mip（没有顶层 mip）：漫反射 BC7 sRGB 2048²；每部分一张 64² 的平法线（A 通道放光泽度：Face 90、Body 90、Hair 120、Costume 70）；
  一张 64² 的灰色高光图（40）。`tex-import <模板> <dds> <out> --id <HEX>`，模板分别是亚诺头部的漫反射 / 法线贴图和亚诺佩剑的高光图。
  全部放进头部容器这个数据文件（`runtime-confirmed`，v2 贴图正确）。

## 9. 表的编辑与编译

- `bt_tool.py edit`：`--drop` 去掉每行的单元格，`--set` 改句柄 / 引用单元格的 ID 和路径。大革命的表 XML 用 `compile-xml` 编译回去和原版**逐字节相同**；
  `build_mod.py` 对每一份副本都先编译原版 XML 比对，不同就停（`offline-accepted`，每次构建都检查）。
- **引用编译后只剩对象 ID**：`Path` 文本不进二进制（同一份 XML 换个路径编译，字节相同）。所以一个编译好的对象可以原样嵌进很多数据文件，
  每个文件里的引用都指向它自己那份（物理骨架就是这样嵌的，[物理](PHYSICS.md) §1）。
- `compile-xml` 在被覆盖的文件旁留 `.bak`，打包前删掉。每个数据文件的全部 harness 命令（原版重编比对、编译改过的表、`pack-data`）放进一次 `batch`。
