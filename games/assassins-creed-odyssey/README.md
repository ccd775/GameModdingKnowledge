# 刺客信条：奥德赛（Assassin's Creed Odyssey）

## 范围

这里整理 PC 版《刺客信条：奥德赛》（Ubisoft Connect 产品 5059，v1.5.6，`ACOdyssey.exe`，AnvilNext 2.0，forge v28）里女主角
卡珊德拉（Kassandra）整体替换的可复用合同，来自 2026-10-19 → 10-23 的一个交付：

| 交付 | 内容 | 最高证据级 |
| --- | --- | --- |
| Karin_Original → 卡珊德拉 v8 | 不论穿什么装备都是 Karin：VisualMaster 去掉装备列，头部表去掉脸 / 眼 / 睫毛等，头发表去掉发型和辫子；Karin 的 LOD0 / LOD1 原地顶替卡珊德拉专属的身体 LOD，带 4 个新的 `ACD_Tex1` 材质；次级物理（双马尾、侧发、脸颊发、丝带、裙片、耳、尾巴）放进重建的头发物理骨架 `ACD_CHF_PLA_Hair_NEW`（KP 骨 + Reflex3 物理记录）；下颌、上眼睑、虹膜用「绑定偏移杠杆」蒙到卡珊德拉的头部骨架上；原地追加安装到每一份副本 | 模型与材质（v3 起）：`runtime-confirmed`（用户：「比例什么的都可以了」）；双马尾 / 脸颊头发物理（v4）：`runtime-confirmed`；v8 的眼睑（常态睁开、稳定）：`runtime-confirmed`（用户 2026-10-23：「看起来可以了」）；v6 的尾巴 / 耳朵软化：`runtime-load-pass`，用户没有单独评价；对话 / 过场表情、DLC 区域：未测 |

快照只对 v1.5.6 有效。**forge 的版本与布局、覆盖顺序里的 forge 名单、数据文件 ID 与 forge 索引号、表的列号、头部骨架的骨 ID 与姿势 ID
是 `build-sensitive`**；拟合比例、眼睑的骨与增益、杠杆长度、物理参数是 `case-derived`（Karin_Original）。

本作的主要贡献：

- **不论装备的整角色替换**：卡珊德拉的 VisualMaster 有一列（Outfit）装着全部装备的 MASTER 表，连随头饰变化的发型都在里面；去掉这一列，
  任何装备下都只剩身体和头。身体 LOD0 / LOD1 是卡珊德拉专属的独立数据文件，可以原地顶替；LOD2–4 是共用的女性身体，不能动。
- **每一份副本都要替换**：DLC forge（`dlc_43`、`dlc_58` 和其中的 `DataPC_ACD_Connection`）重新打包了卡珊德拉的表和容器，在主世界里压过
  `DataPC_SharedGroup_00`。v1 只改了 SharedGroup 那一份：装备还在、Karin 是品红色。
- **不重打 forge 的原地安装**：把新数据文件追加到每个持有该 ID 的 forge 末尾，改指 20 字节索引行和名字表里的大小；卸载写回原行并截断。
- **无界面驱动 AnvilToolkit 1.3.6**（AcoHarness）：补上它漏掉的奥德赛 schema、只用内联 mip 的贴图做模板、修复 XML 编译时空引用的填充字节。
- **奥德赛的 Reflex3 物理**比影 / 幻景的旧：骨架里的 `Reflex3Constraints.BinaryData` 是 `f32 3.1` + `[u8 类型][正文]` 记录；
  type 21 是 377 字节的 Physics 约束。直接写这个 blob，把 Karin 的物理链挂进卡珊德拉专属的头发骨架。
- **眼睑的增益取舍**：游戏里每一根会随眨眼转动的眼睑骨，同时还被眯眼、睁大、视线跟随、单眼扭转等 13–15 个姿势带动；
  只靠蒙皮时「常态睁开」和「完全眨眼」不能兼得。眼睑前后六轮（v4、v5、v6、v7d、v7、v8），用不对称的诊断构建和用户录像逐帧量出眼睑骨的实际角度，
  证伪了多骨抵消，最后选了低增益、稳定睁眼（[表情](FACE.md)）。

## 核心方法

- 先用自写的 `aco_forge.py` 给全部 forge 建索引（forge 名字表里存着数据文件名，不需要文件列表就能按名字找），用 `aco_locate.py` 找出
  每个数据文件的全部副本和主世界里生效的那一份，再提取、解包成 schema XML。
- 源模型是 Karin_Original 规范化后的 blend（与本库未收录的刺客信条：影项目共用）。拟合、表情、导出脚本都是影项目脚本的奥德赛副本：
  奥德赛的原始坐标系和影的不同，拟合前把卡珊德拉的骨架 GLB 绕竖轴转 +90°，导出的 Karin LOD 再转 −90°（精确往返）。
- 网格经 AcoHarness 的 `import-glb` 写成奥德赛的顶点格式 v4；材质、纹理组、贴图从原版 XML / 贴图模板生成，放进 LOD0 的数据文件；
  表用 XML 改列再编译，编译后修补空引用的填充字节。
- 每轮只让一类改动进入实机反馈（模型与材质、物理、表情分开）。表情问题先在 Blender 里用头部骨架的原版姿势复现（`pose_preview.py`），
  看不清时做诊断构建，从用户录像里逐帧测量，再改参数。

## 证据纪律

沿用本库五级：`reference-inferred` / `offline-accepted` / `runtime-load-pass` / `runtime-rejected` / `runtime-confirmed`。
游戏只装在另一台测试机上；实机证据来自用户的观察、截图和录像，以及 agent 在测试机上的截图，文档逐项写明是哪一种。
结论再按 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 分类。未测场景见 [验证与发布](VALIDATION_AND_RELEASE.md) §4。

## 阅读入口

- [Agent 入口](AGENTS.md)：接手前核对项与硬性规矩
- [技术合同](TECHNICAL_CONTRACTS.md)：forge v28 布局、覆盖顺序与「每一份副本」、原地追加安装器、卡珊德拉的可视图与数据 ID、坐标系、网格导入、`ACD_Tex1` 材质、表与 XML 编译
- [构建流水线](BUILD_PIPELINE.md)：索引 → 提取 → 拟合 → 物理骨 → 表情 → 导出与导入 → 物理骨架 → payload → 安装，含拟合细节
- [物理](PHYSICS.md)：Reflex3 type 21 记录、`Hair_NEW` 物理骨架重建、KP 骨朝向、各版参数与用户评价、裙片
- [表情](FACE.md)：头部骨架、绑定偏移杠杆模型、虹膜与下颌、眼睑 v4 → v8、诊断构建与录像分析、多骨抵消、最终的增益取舍
- [开发工具](DEV_TOOLING.md)：AnvilToolkit 与 AcoHarness、索引缓存、Blender 预览、测试机流程、录像逐帧分析
- [排障手册](TROUBLESHOOTING.md)：症状 → 原因 → 处理
- [验证与发布](VALIDATION_AND_RELEASE.md)：闸门、可重新部署的包结构与它的实测重新部署、未测场景
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)：v1 → v8 的每一轮与证据级
- [便携工具包](../../portable-kits/assassins-creed-odyssey/README.md)：forge / 安装 / 表 / 物理骨架 / 姿势模拟脚本、Blender 脚本、AcoHarness 源码

## 公开边界

不含源模型、游戏资源、提取出的数据文件 / XML、构建出的网格 / 贴图 / payload、发行 zip、录像或截图，也不含 AnvilToolkit、.NET、texconv、
`Odyssey.gfl` 或影项目的脚本。便携包里的脚本是项目脚本去掉本机路径后的副本；卡珊德拉的数据 ID、列号、骨 ID、姿势 ID 以及 Karin 的
增益、杠杆、物理参数是快照 / 案例值，换版本或换模型时要按当前资源重新测量。
