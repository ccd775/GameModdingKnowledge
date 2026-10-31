# 技术合同

数据 ID、列号、骨 ID 都是构建机那份副本的快照值（`build-sensitive`）；换副本先重建索引和副本清单，再核对。

## 1. 版本与工具

| 项 | 值 |
| --- | --- |
| 游戏 | PC，`ACS.exe` 链接时间 2016-08-16（文件日期 2016-10-19），非商店版副本，项目里标为「v1.51」（未核实；公开的 PC 补丁记录到 1.4）；40 个 forge（根目录 + `dlc_11..14` 服装包、`dlc_20` / `dlc_21` 的 world patch 与开膛手杰克），357 161 个索引行 |
| forge | v27，布局与大革命相同（完整仓库里的 `games/assassins-creed-unity/TECHNICAL_CONTRACTS.md` §2）；`acs_forge.py` 的文档字符串写了字段 |
| 工具 | AnvilToolkit 1.3.6 经 AcuHarness（大革命包的源码，`ACU_GAME=Syndicate`，`Syndicate.gfl`）；.NET 9.0.18；Blender 5.0.1；texconv |
| 源模型 | Karin_Original 的 Unity FBX（与大革命同一个文件，`prep_karin_original.py` 规范化） |

## 2. forge 与安装（`invariant`）

- 安装不解包 forge：替换数据文件追加到 forge 末尾，改指 20 字节索引行（偏移、ID、大小）和名字表行的大小字段；卸载写回原行并截断到安装前的长度。
- 同一个数据文件 ID 在多个 forge 里各有一行（各 world forge 和 patch forge 的版本不同），每一行都要换（[§3](#3-内嵌副本)）。
- 读 forge 前核对魔数 `scimitar\0` 和版本 27 / 28，其他版本拒绝。

## 3. 内嵌副本

同样的表对象（同一个对象 ID）嵌在很多数据文件里，引擎用先加载的那一份。构建机副本上，目标表和头部 LOD 出现在 **38 个数据文件 ID、18 个 forge、318 份副本**里：

| 类别 | 数据文件 |
| --- | --- |
| 玩家实体 | `ACVI_CHR_P_JacobFrye`（17 份）、`ACVI_CHR_P_EvieFrye`（16 份）、搏击俱乐部 / 礼服变体及其 `_Body`、`dlc_11..14` 服装包里的玩家文件 |
| 头部容器 | `ACVI_CHR_P_JacobFrye_Head`（14 份）、`ACVI_CHR_P_EvieFrye_Head`、`_Head_SpecialLOD`、`ACVI_CHR_P_LydiaFrye_Head`；`London_20` 里头部 LOD 是独立数据文件（`*_Head_LOD0..3`） |
| 其他 | 独特 NPC `ACVI_CHR_U_*Frye`、藏身处 `*_HID`、菜单 `ACVI_DataAI_UIDataRoot_Jacob / _Evie`、任务数据块（`DataBlock_*`、`Cell06561_DataBlock`）、莉迪亚·弗莱 `ACVI_CHR_P_LydiaFrye(_Body)` |

- 找法：`scan_objs.py`（harness `scan-objs`，在内存里解压每个数据文件、按对象 ID 命中）→ `objs_to_tsv.py`。每组 forge 约 20 分钟，跳过 `_gi` / `_grid`。
- payload 按 forge 分版本：`forge/<forge>/<IDHEX>_<名字>.data`；28 份搏击俱乐部 / 礼服副本里没有目标表，记进 `skip.tsv`（留原版）。
- 留原版：`ACVI_DLC_CHR_P_Jacob40`（开膛手杰克的老年雅各布，158 MB，只嵌了雅各布的护腕表）。

## 4. 双胞胎的可视图与数据 ID（`build-sensitive`）

```text
ACVI_CHR_P_JacobFrye (EntityBuilder)  模板 ACVI_CHR_Playable_BaseEntity_Jacob -> ACVI_CHR_SHR_Male.Skeleton
  VisualMaster: 7 Body, 5 Head
    Body (0x2FF072B662): 1 OutFits (0x0FE84A864A), 4 Bracers (0x2FF072B66E -> DartGun / RopeLauncher 子表), 11 CaneSword
      OutFits 每行: 10 身体网格, 27/28 外套, 35/38 兜帽, 41 刀鞘, 47 帽子, 29/50 布料, 49 ColorSets, 52 Belts (0x2FF072B654),
                    附加骨架 11 / 36 / 43 / 51 / 57, 56 FX
    Head (0x0FE84A8684): 1 头部 LODSelector, 2 头部骨架（面部绑定）, 6 睫毛, 10/16-21 头发, 12 眼 / 牙, 13 眼球材质,
                         14 头发附加骨架, 15 阴影眼
ACVI_CHR_P_EvieFrye  模板 ACVI_CHR_Playable_BaseEntity_Evie -> ACVI_CHR_SHR_Female.Skeleton
  VisualMaster: 1 Body (Outfits 0x44F5C89FE1 [55 Cloak 0x44F5C89FE2], Bracers 0x44F5C89FE3), 2 Head (0x14B2685216), 4 Necklace (0x58EAD0A853)
搏击俱乐部 / 礼服: 雅各布用自己的 Head 表 + 自己的身体表 (0x47C93F09B4 / 0x483A8DECA4);
  伊薇用 Head_SpecialLOD (0x6CF114F8C1，第 1 列直接是伊薇的 LOD0 网格) + 身体表 (0x5C8B4C3D6B / 0x4855906D31)
莉迪亚·弗莱 (一战): Head 0x5DCB8CAD55 = 伊薇的头部 LODSelector + 头部骨架 + 莉迪亚的头发; Body 0x4479401BE8; 用伊薇的 Bracers
头部 LOD 网格: 雅各布 27CCC692C6 / 38534E59BE / 38534E59C3 / 38534E59C8，伊薇 3E33A56077 / 5D2B51F63C / 5D2B51F641 / 5D2B51F646
```

- 改法（`build_mod.py` 的 `TABLES`）：20 张表里类型为 `GraphicObject` / `SoftBody` / `TextureSet` / `Material` / `FX` 的列全部去掉，只有头部表的第 1 列
  （LODSelector / 伊薇 SpecialLOD 的 LOD0）保留；骨架、子表、声音列保留（武器挂点和道具骨还要用）。外套表另去掉第 49 列 ColorSets（被去掉网格的换色）。
- 头部 LOD 的每一份都换成 Karin 的同 ID 网格；该数据文件同时加入这位双胞胎的 4 个材质、TextureSet、漫反射 / 平法线（A = 光泽度）/ 高光贴图。
- 新对象 ID：雅各布 `0xC04B410000+`、伊薇 `0xC04B450000+`（原版最大 ID `0x8CBB3C827F`）；偏移 MAT `+0x01`、SET `+0x11`、DIFF `+0x21`、NORM `+0x31`、
  SPEC `+0x41`、SRC `+0x51`、物理骨架 `+0xF00`（BallJointCommonData `+0xF01`、LiteRagdoll `+0xF02`，内联骨 / 修饰器 ID 从 `+0x1000`）。

## 5. 骨架与骨名

- `ACVI_CHR_SHR_Male` 与 `_Female` 的关节位置完全相同（髋 0.96、头 1.6654），实体缩放 1；一次拟合两人共用（`case-derived` 的比例 1.6541，与大革命的亚诺相同）。
- 骨架不带骨名：骨 ID = 名字的 CRC32（`zlib.crc32`，区分大小写；`Reference`、`Hips`、`Spine..Spine2`、`LeftUpLeg`、`LeftFootThumb1` 等核对过），命名沿用大革命
  （没有 `Neck1`）。`export-glb` 把骨写成数字 ID；`glb_names.py` 用已知名字的 CRC32 还原，`import-glb` 再按名字哈希回同样的 ID，往返安全。
- 工具给少数骨起的别名的 CRC32 不是 ID：伊薇的 `JAW` 是 `Fx_Jaw`（4253370951）、`EYE_LEFT` 是 `Fx_Eye_Left`（485040451）。真 ID 在节点的 `extras.Name`。
- 坐标系与大革命相同：拟合前 `glb_rotate.py +90`，导出的 LOD `-90` 再导入（大革命技术合同 §6）。
- 网格 ≤ 255 骨（顶点格式 v2）；stage 2 的 Karin LOD 是 175 根。

## 6. 材质（`CN_Weapon_NoAlphaTest`）

模板是 `ACVI_Weapons_Kukri`（`Game Bootstrap Settings` 里的对象 9472 / 12767）：每位双胞胎 4 个材质（脸、身体、头发、服装），`TwoSided` 改成 True；
漫反射 2048² BC7 sRGB，法线是 64² 的平法线、A 通道 = 光泽度（默认 90 / 90 / 120 / 70），一张共用的灰色高光图（默认 40）。漫反射 / 法线贴图模板是雅各布头部的
内联 mip 贴图（顶层 mip 的贴图会让工具弹文件对话框）。

## 7. 表的编辑与编译

- 每份原版表先 `compile-xml` 一遍，和原版逐字节相同才继续（全部 318 份通过）；改表用 `bt_tool.edit`，莉迪亚的头部行缺第 14 列，`add_missing` 补上单元格。
- 编译后引用只剩对象 ID：一个编译好的对象（材质、物理骨架）可以原样嵌进多个数据文件。

## 8. 安装器（`acs_install.py`）

- 游戏目录：`--game` → `ACS_GAME_DIR` → 自动找（Steam：`SteamPath` + `libraryfolders.vdf` + `appmanifest_368500.acf` 的 `installdir`；Ubisoft Connect：
  `HKLM\SOFTWARE\Ubisoft\Launcher\Installs\*\InstallDir`，32 / 64 位两个视图；已安装程序里名字含 Syndicate 的 `InstallLocation`；Epic 清单）。一个就用，
  多个列出编号让人选；`uninstall` / `status` 优先选有状态文件的那个。
- 匹配：每个 forge 里按 ID 找到 payload 涉及的副本，算内容指纹（大小 + SHA-1）和 `vanilla.tsv` 比：同 forge 的变体来源相同 → 用它；别的 forge 里有来源相同的变体
  → 用那份；只有同 forge 的变体但内容不同 → 照样替换并列出；有通用文件 → 用通用文件；都没有 → 留原版并列出；payload 里有、游戏里没有的 forge（没装的 DLC）→ 跳过并列出。
  一份都对不上，或 forge 不是 v27 / v28，才拒绝。
- 写之前检查写权限（Program Files 下的 Steam / Ubisoft 安装要管理员），失败时什么都不改；状态文件先于 forge 写入，中断的安装也能卸载。
