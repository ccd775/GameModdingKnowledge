# 刺客信条：枭雄（Assassin's Creed Syndicate）

## 范围

这里整理 PC 版《刺客信条：枭雄》（`ACS.exe`，AnvilNext 2.0，forge v27）里两位主角雅各布 / 伊薇·弗莱（Jacob / Evie Frye）整体替换的可复用合同，
来自 2026-10-26 至 2026-10-30 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 雅各布 + 伊薇 v5 | 不论穿什么装备两兄妹都是 Karin：双胞胎（和用伊薇头部的莉迪亚·弗莱）的装备、头发、外套、护腕、项链表去掉全部可视列，只留头部 LODSelector；Karin 的 LOD0–3 原地顶替两人的头部 LOD 网格（同 ID），每人 4 个新的 `CN_Weapon_NoAlphaTest` 材质和贴图放进同一个数据文件；**同一批表对象和头部 LOD 内嵌在 38 个数据文件里，分布在 18 个 forge、共 318 份副本**（玩家实体、独特 NPC、藏身处、菜单、任务数据块、DLC 服装包、一战记忆），每一份按自己的版本改；次级物理是新的附加骨架 `Karin_Phys_<twin>`（121 骨、55 个 BallJoint），挂在头部表的头发附加骨架单元格上；裙片经 `BallJointCommonData → LiteRagdoll` 与大腿胶囊碰撞；下颌、眼睑、眼球蒙到各自的头部骨架；原地追加安装（290 个索引行），可重新部署的包自带嵌入式 Python，按内容比对、不锁版本 | 两兄妹替换、物理与表情可用：`runtime-confirmed`（用户 2026-10-27：「两个角色都被正确替换了，有物理有表情」）；v5 物理手感、膝盖与裙片法线修复：`runtime-confirmed`（用户 2026-10-30：「看起来可以」）；预渲染过场、开膛手杰克 DLC 的老年雅各布 / 伊薇：未处理；对话 / 过场里的表情、Steam / Ubisoft Connect / Epic 版：未测 |

快照来自构建机上的一份非商店版副本（`ACS.exe` 链接时间 2016-08-16，40 个 forge，357 161 个索引行），项目里标为「v1.51」，这个编号对 PC 版没有核实。
**数据文件 ID、内嵌副本的分布、表的列号、头部骨架的骨 ID** 是 `build-sensitive`；拟合比例、膝盖隐藏带、物理参数、碰撞胶囊、表情角度是 `case-derived`（Karin_Original）。

本作的主要贡献（相对大革命，完整仓库里的 `games/assassins-creed-unity/`）：

- **两个主角、一个拟合**：`ACVI_CHR_SHR_Male` 和 `_Female` 的关节位置完全相同（髋 0.96、头 1.6654，实体缩放 1），一次身体拟合（比例 1.6541）两人共用；
  表情按各自的头部骨架（[技术合同](TECHNICAL_CONTRACTS.md) §4）。
- **没有名字的骨**：枭雄的骨架不带骨名，导出的 GLB 节点名是数字 ID = 骨名的 CRC32；工具给少数面部骨起的别名的 CRC32 不是 ID（`JAW` = `Fx_Jaw`）。
  `glb_names.py` 按 CRC32 还原名字（[技术合同](TECHNICAL_CONTRACTS.md) §5）。
- **物理宿主换成头部表的头发单元格**：头发网格反正去掉了，`Karin_Phys_<twin>` 占用头部表第 14 列（头发附加骨架），嵌进 64 份头部表所在的文件（[物理](PHYSICS.md) §1）。
- **没有弹簧的 BallJoint 的手感调法**：v2 改用 `LocalOwnGravity` 被实机证伪（两只耳朵朝同一侧歪、双马尾持续高频抖动）；连续相邻的链节一起模拟会抖，
  隔节模拟（0 / 2 / 4）加按节递增的锥角与摩擦才既有链感又不抖（[物理](PHYSICS.md) §3–§4）。
- **源模型的两个坑**：形态键 `kisekae_Knee` 设为 1 却不移动任何顶点，膝盖皮肤从过膝袜里穿出；百褶裙的手调卡通法线让裙片出现污渍状阴影
  （[构建流水线](BUILD_PIPELINE.md) §3–§4）。
- **不锁版本的安装器**：不再要求 forge 大小一致，按 ID 找到每份副本、和制作时的原版逐份比对内容（大小 + SHA-1），缺的 DLC forge 跳过，不同的照样替换并列出；
  发行包自带官方嵌入式 Python，`.cmd` 是 ASCII 批处理，不依赖 PowerShell（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。

## 核心方法

- 工具链从大革命分出：forge v27、安装器、表编辑、Blender 拟合 / 表情 / 导出脚本、附加骨架生成器都是大革命副本的小改；AcuHarness 原样复用（`ACU_GAME=Syndicate`）。
- 先找全副本再改：`acs_forge.py index` 建全部 forge 的索引，`scan_objs.py` → `objs_to_tsv.py` 列出每个持有目标表或头部 LOD 的数据文件；`build_mod.py`
  对每一份从它自己的原版提取、改列、编译（原版先重新编译，必须逐字节相同）、打包。
- `make_meshes.py` 一次做完两兄妹：拟合 → 表情 → 导出 LOD → 旋转 → 导入（原版头部 LOD 的 ID）→ 物理骨架。
- 每轮只让一类改动进入实机反馈：stage 1 模型与材质，stage 2 物理与表情，v2–v5 只调物理（v3 同时修膝盖和裙片法线，因为都由用户的同一轮截图提出）。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
stage 1 / stage 2 由 agent 在构建机上实机截图（标题画面、读入一个转换来的存档后在伦敦街头）；之后由用户在同一台机器上实机试玩并给截图和评价，文档逐项写明是哪一种。
结论再按 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 分类。未测场景见 [验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：版本与工具、forge 与内嵌副本、双胞胎的可视图与数据 ID、骨架与骨名、材质、表编译、安装器
- [构建流水线](BUILD_PIPELINE.md)：索引 → 副本扫描 → 探针 GLB → 拟合（膝盖隐藏带）→ 表情 → 导出（裙片法线）与导入 → 物理骨架 → payload → 安装 → 发行包
- [物理](PHYSICS.md)：宿主、枭雄与大革命的骨架差异、v1–v5 的参数与用户评价、`LocalOwnGravity` 的反证、偏移约定的复核、裙片碰撞
- [表情](FACE.md)：两兄妹的头部骨、杠杆参数、未经评价的部分
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理，以及工具链的坑
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、按内容比对的安装器、自带 Python 的包、往返测试、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：stage 1 → v5 的每一轮与证据级
- [便携工具包](../../portable-kits/assassins-creed-syndicate/README.md)：forge / 副本扫描 / 安装 / 表 / 网格 / 物理骨架 / 发行脚本、Blender 脚本

## 公开边界

不含源模型、游戏资源、提取出的数据文件 / XML、索引与副本清单、构建出的网格 / 贴图 / payload、发行 zip、存档或截图，也不含 AnvilToolkit、.NET、texconv、
`Syndicate.gfl`、嵌入式 Python。便携包里的脚本是项目脚本去掉本机路径后的副本；本机实机测试用的截图 / 按键脚本和存档转换脚本不随包。双胞胎的数据 ID、列号、
骨 ID 以及 Karin 的物理参数、胶囊尺寸、表情角度是快照 / 案例值，换版本或换模型时要按当前资源重新测量。
