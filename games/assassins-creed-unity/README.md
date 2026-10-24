# 刺客信条：大革命（Assassin's Creed Unity）

## 范围

这里整理 PC Steam 版《刺客信条：大革命》（Steam 289650，build 21970519，游戏内版本 1.5.1，`ACU.exe`，AnvilNext 2.0，forge v27）里主角
亚诺（Arno）整体替换的可复用合同，来自 2026-10-24 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 亚诺 v7 | 不论穿什么装备都是 Karin：亚诺的装备表去掉全部可视列，头部表去掉眼 / 牙、湿润、睫毛、胡子、伤疤；Karin 的 LOD0–3 原地顶替亚诺头部容器 `CN_U_FR_Arno_Head` 里的四个 LOD 网格，带 4 个新的 `CN_Weapon_NoAlphaTest` 材质；**同一批表对象内嵌在 189 个数据文件里**（`CN_P_Arno`、`DataAI_UIDataRoot`、每个旧时代服装文件），每一份都按自己的版本改；次级物理（双马尾、侧发、前发、脸颊发、丝带、鞋标、裙片、耳、尾巴）是一个新的附加骨架 `Karin_Phys`（121 骨、55 个 BallJoint），嵌进每个玩家附加骨架表所在的数据文件；裙片经 `BallJointCommonData → LiteRagdoll` 与大腿胶囊碰撞；下颌、上眼睑、眼球用绑定偏移杠杆蒙到亚诺的头部骨架；原地追加安装到 21 个 forge 的 471 个索引行 | 模型与材质（v2）：`runtime-confirmed`（agent 在本机实机截图；用户另一台机器「v2 可以进入游戏」）；次级物理保形与摆动（v6）：`runtime-confirmed`（用户：「物理效果整体尚可」）；裙子与大腿碰撞（v7）：`runtime-confirmed`（用户 2026-10-24：「v7 可以了」）；表情：`runtime-load-pass`，用户没有单独评价；菜单 / 自定义界面的模型、旧时代服装、过场、DLC「亡者之王」自己的亚诺表、派对服装：未测或未处理 |

快照只对 Steam build 21970519 有效。**forge 布局、数据文件 ID、内嵌副本的分布、表的列号、头部骨架的骨 ID** 是 `build-sensitive`；拟合比例、
物理参数、碰撞胶囊、表情杠杆是 `case-derived`（Karin_Original）。

本作的主要贡献：

- **内嵌副本**：大革命把同一批表对象（同样的对象 ID）嵌在很多数据文件里 —— 玩家实体 `CN_P_Arno`、界面数据 `DataAI_UIDataRoot`、每个旧时代服装的文件。
  引擎用先加载的那一份；v1 只改了 `CN_P_Arno`：Karin 显示出来了，但装备和牙齿都没被隐藏。harness 的 `scan-objs` 在内存里解压每个数据文件、按对象 ID 找出全部副本，
  构建器按副本各自的版本逐个改（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **附加骨架的硬规则**：v3 在 Logo 处闪退（`ACU.exe+0x95240`）。从崩溃转储里的循环结构和全部原版骨架对照出三条：`ChildBoneCount` 是**后代数**而不是
  直接子骨数、骨架键必须是自己的、BallJoint 的 `LiteRagdoll` 留空（[物理](PHYSICS.md) §2）。
- **没有弹簧的 BallJoint**：重力把每节链拉到锥面边缘，链越长垂得越多。把锥中心逆着下垂方向偏一个锥角，重力就正好把静止姿势托在锥边，
  摆动范围是两倍锥角；偏移的轴向与符号从原版 116 个带偏移的关节里统计出来（[物理](PHYSICS.md) §4）。
- **只经 CommonData 的碰撞**：原版唯一会碰撞的关节（亚诺的腰带片）走 `CommonData → BallJointCommonData → LiteRagdoll`；照搬这条路给裙片挂大腿胶囊，
  第二轮（加长、加粗）解决了跑动时大腿穿出裙子（[物理](PHYSICS.md) §6）。
- **可重新部署的包**：payload 按 forge 分版本（同一个数据文件在各 forge 里是不同版本），打成 solid xz（232 MB → 44 MB），安装器从 Steam 库自动找游戏，
  并核对每个要动的 forge 和制作时的原版大小一致（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。

## 核心方法

- 工具链从刺客信条：奥德赛项目分出（`games/assassins-creed-odyssey/`）：forge v27 的布局和奥德赛 v28 相同，安装器、表编辑、Blender 拟合 / 表情 /
  导出脚本都是奥德赛副本的小改；AcuHarness 是 AcoHarness 的大革命分支（顶点格式 v2、`batch`、`scan-objs`）。
- 先找全副本再改：`acu_forge.py index` 建全部 forge 的索引，`scan_objs.py` → `objs_to_tsv.py` 列出每个持有亚诺表对象的数据文件；`build_mod.py` 对每一份
  从它自己的原版提取、改列、编译（原版先重新编译一遍，必须逐字节相同）、打包。
- 网格放进亚诺的头部容器（LOD0–3 换成 Karin，同 ID），材质和贴图也放在这个容器里；身体、装备全部去掉，所以整个角色只剩头部容器里的 Karin。
- 物理骨架从 Karin 的 LOD0 GLB 生成（`acu_phys_skel.py`），作为新对象嵌进每个附加骨架表所在的数据文件，并占用一个反正会被去掉的布料附加骨架的单元格。
- 每轮只让一类改动进入实机反馈：v2 模型与材质，v3 / v4 表情与物理骨架，v5–v7 只调物理。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
v1 / v2 由 agent 在本机实机测试（截图）；之后用户要求改为交付可重新部署的包，在另一台电脑上测试，实机证据来自用户的描述和截图，文档逐项写明是哪一种。
结论再按 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 分类。未测场景见 [验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：版本与工具、forge v27、内嵌副本与「每一个数据文件」、亚诺的可视图与数据 ID、坐标系、网格导入、材质、表编译、原地安装器
- [构建流水线](BUILD_PIPELINE.md)：索引 → 副本扫描 → 提取 → 拟合 → 表情 → 导出与导入 → 物理骨架 → payload → 安装 → 发行包
- [物理](PHYSICS.md)：附加骨架的宿主、v3 闪退与骨架规则、BallJoint 的行为、偏移约定与重力补偿、各版参数与用户评价、裙片碰撞
- [表情](FACE.md)：从原版权重认出头部骨架、骨映射、杠杆参数、未经评价的部分
- [开发工具](DEV_TOOLING.md)：AnvilToolkit 与 AcuHarness、同步盘的性能陷阱、崩溃转储分析、本机实机测试（窗口化、Ubisoft Connect 登录）
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、可重新部署包的结构与往返测试、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：v1 → v7 的每一轮与证据级
- [便携工具包](../../portable-kits/assassins-creed-unity/README.md)：forge / 副本扫描 / 安装 / 表 / 物理骨架 / 发行脚本、Blender 脚本、AcuHarness 源码

## 公开边界

不含源模型、游戏资源、提取出的数据文件 / XML、索引与副本清单、构建出的网格 / 贴图 / payload、发行 zip、崩溃转储或截图，也不含 AnvilToolkit、.NET、
texconv、`Unity.gfl`。便携包里的脚本是项目脚本去掉本机路径后的副本；亚诺的数据 ID、列号、骨 ID 以及 Karin 的物理参数、胶囊尺寸、表情杠杆是快照 /
案例值，换版本或换模型时要按当前资源重新测量。
