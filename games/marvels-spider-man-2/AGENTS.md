# Agent 入口（漫威蜘蛛侠2）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态记在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对游戏 `toc` 的 SHA-1（本目录快照为 `318f4345f3a1`，启动器 v1.130.1.0）。build 变了：
   - 重建资产名索引（`sm2_index.py`）；
   - 用 `survey_targets.py` / `suit_models.py` 重新枚举目标模型和战衣链；
   - 用 `test_dyn_roundtrip.py` / `test_actor_roundtrip.py` 复核动力学段和 actor 编解码。
   本文给出的 exe 地址只对这个 build 有效。
2. 确认 ALERT 能导入（`dat1lib`，GPLv3，用户自取）。本库只用它读 toc 和算 CRC；安装器与 `.stage` 读写不依赖它。
3. 先看游戏目录里有没有 `toc.BAK` 和 `d\mods\`，有就说明装过别的 mod。
   - 本项目的安装器和 Overstrike 都以 `toc.BAK` 为基准，每次安装都会整体重来。
   - 混用两种安装方式，后装的会覆盖先装的。用户原来的 mod 要先问清楚。
4. 第一次进游戏前备份存档；测试时只读档。
5. 分清这一版改的是几何、材质、表情、物理参数还是挂接方式；一版只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **i30 的资产头是变长的**：`u32 magic | u8 ? | u8 pairs | u16 extra | pairs×8 | extra`。ALERT 按 36 B 切，那是 i29 的格式，
  在 i30 上会错（[技术合同](TECHNICAL_CONTRACTS.md) §1）。
- **删了 anim-vert 段必须清 `ModelBuilt` 的 0x10000000 位**，否则整件身体不显示（T1）。
- **材质图要和网格顶点格式匹配**：`*_sand` 材质图只给沙人化 NPC 的 fmt 5 网格用，用到 fmt 1 网格上，标题画面会崩溃（T4）。
  人物用 `required\materials\basic_normal_gloss(_subsurface)`。
- **只有 `u2 & 0x80` 的关节能带蒙皮权重**；新追加的 `0x01` 关节必须在 `ModelMirrorIds` 里有自映射项，否则这些关节会停在模型原点（T9）。
- **要替换全部战衣模型**：每套战衣各有身体模型，存档里装备的是哪套就显示哪套。只换默认战衣是看不出效果的（T4b）。
- **战衣模型里的动力学只跑 1 秒，靠数据改不了**：战衣部件由 SkinManager 创建，没有 owner actor，过不了每帧门控（[物理](PHYSICS.md) §3）。
  要持续模拟，必须把动力学放在有 owner 和 AnimController 的模型上。
- **一个 actor 里同类型的组件只认第一条**：多加的 HeroSuitAddition 会被丢掉（T18）。
- **改动力学模型的包围球要改 `ModelJointBspheres`**：运行时每帧用它重算包围球；改 `ModelBuilt` 的半径对门控无效（T13）。
- **物理链不能用约束类型 0（Simple）**：它不做锥限制，链会按重力垂到底（T15）。头发、耳朵、尾巴用 1（Cone）。
- **远程机上的 GUI 只能从用户会话启动**：SSH 在 session 0，从那里启动的游戏看不见，截图是黑的。
- **大文件经远程链路上传后先核对 SHA-256 再安装**：链路中途断过，不核对就可能装上半个包。
- **游戏在运行时不要安装**，也不要替用户关掉游戏。
- **不要声称实机通过**：回读检查、渲染预览、`test_dyn_model` 都只算 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用来收窄旧结论的适用范围，并写明 supersedes 关系。
例：「改 ModelBuilt 包围球半径能让 base 模型持续模拟」（T13）被证伪，换成了「运行时用 ModelJointBspheres 重算，
战衣部件没有 owner，过不了门控」。
