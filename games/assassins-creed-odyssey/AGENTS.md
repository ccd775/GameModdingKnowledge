# Agent 入口（刺客信条：奥德赛）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对游戏版本：本目录快照是 Ubisoft Connect 版（产品 5059）v1.5.6，forge v28。`aco_forge.py index` 遇到别的 forge 版本会直接报错；
   版本变了 → 重建全部 forge 的索引，用 `aco_locate.py find` 重新确认每个数据 ID 的全部副本、生效的那一份和索引号，再改
   `build_mod.py` 顶部的常量（[技术合同](TECHNICAL_CONTRACTS.md) §2、§3、§5）。
2. 先跑 `aco_install.py status`：有状态文件说明 mod 装着。**游戏在装着 mod 时被更新或校验过，就不要再卸载**（会把旧索引行写回新文件）：
   删掉 `<游戏目录>\.karin_aco_state.json`，用 Ubisoft Connect 校验文件恢复原版，再重新安装。
3. 安装和卸载都要求游戏关闭（安装器会检查进程）。游戏和用户都在另一台测试机上：**结束游戏、部署之前先问**；多个会话共用测试机桌面时，
   按约定的锁文件协调，只删自己的锁。
4. 分清这一轮改的是模型 / 材质、物理还是表情；一轮只让一类改动进入实机反馈。表情的问题先在 Blender 里复现（`pose_preview.py`）。

## 硬性规矩（本项目已付过学费）

- **每一份副本都要替换**：主世界的覆盖顺序是 `DataPC_patch_01` > `dlc_<n>\*.forge` > `DataPC_SharedGroup_00`，DLC forge 里也有卡珊德拉的
  表和容器。v1 只改了 SharedGroup 那一份：VisualMaster 的修改被忽略（装备还在），容器里的材质也没加载（品红色）。
- **材质放进 patch_01 的 LOD0 数据文件**（和网格同一个数据文件）：DLC 里的身体容器副本只是 LODSelector 空壳，放在容器里的材质不会被加载。
- **不要动共用的女性身体 LOD2–4**：容器的 LODSelector 把 LOD2–4 指到 Karin 的 LOD1，卡珊德拉专属的 LOD0 / LOD1 原地顶替。
- **皮肤和服装模板吃编码贴图**（皮肤参数、染色区 / 布料 ID），不是反照率：Karin 用 `ACD_Tex1`（道具、玩家弓剑用的普通 PBR 模板）。
- **只用内联 mip 的贴图**做读取和模板：AnvilToolkit 读奥德赛的顶层 mip 会弹 GUI 文件对话框，无界面时卡死。
- **`compile-xml` 之后修补空引用的填充字节**（`build_mod.compile_fixed`）：奥德赛的写出器把它写成 0（原版 1）；表和骨架 XML 都会这样。
  打包前删掉 `compile-xml` 留下的 `.bak`。
- **AcoHarness 的文件参数要带斜杠**（`./x.glb`）：不带斜杠的名字按 harness 所在目录解析。
- **网格最多 255 根骨**（奥德赛的顶点格式 v4 没有宽索引），加上 KP 物理骨后 Karin_Original 的 LOD 是 152 根，Karin_PicodraTech 是 235 根。
- **物理参数表按键合并、前缀匹配**（`aco_phys_skel.params_for`）：宽行的 `"off": true`、`step`、`gf` 会漏进更具体的名字；换模型时看 `--report` 逐条链核对
  （[物理](PHYSICS.md) §2）。
- **比较两次构建要解包**：`.data` 容器每次构建的字节都不同，内部文件才可比。
- **坐标系**：影项目的拟合脚本按影的原始坐标系写，奥德赛的差绕竖轴 90°：拟合前 `glb_rotate.py +90`，导出的 LOD 导入前 `−90`
  （往返精确，[技术合同](TECHNICAL_CONTRACTS.md) §6）。
- **头发表**：去掉 9 / 10 / 13 列（普通 / 兜帽 / 头盔发型的 LODSelector）还要清空行的 `DynamicResources`，否则辫子还在后颈（v2）；
  SharedGroup 里那份头发表是旧版本，保持原版（`payload\skip.tsv`）。
- **虹膜挂在视线骨上**（`xE8AAD140` / `x8CA848A3`），不是眼窝骨：眼窝骨从来不转，v4 / v5 的虹膜是死的。
- **眼睑不要用长杠杆加预转**：杠杆把每一个绕非平行轴的小转动都放大，v6 的 1.44 m 杠杆把单眼扭转姿势放大成厘米级的睫毛错位（「上眼睑很奇怪」）。
  每根眼睑骨都和眯眼 / 睁大 / 视线跟随 / 扭转共用，增益只能取舍；先做左右眼不对称的诊断构建、从录像量角度，再定增益（[表情](FACE.md)）。
- **Blender 的 Workbench 预览需要 OpenGL 上下文**：SSH 会话里会崩，在交互桌面会话里跑（一次性的 `schtasks /IT` 计划任务可以）。
- **不要声称实机通过。** Blender 预览、姿势模拟、离线回读都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。例：

- 「眼睑骨在游戏里静止时闭合约 4–6°，是低头跟随造成的」（v5 推断）→ 收窄为：每根随眨眼转动的骨还被 13–15 个别的姿势带动，
  其中视线扫视（约每 2.5 秒一次）驱动的眼睑跟随让静止角一阵一阵地跳（v7 录像：保持、然后 1–2 帧内切换）。
- 「上眼睑褶骨在游戏里静止 ≈ 0°」（v7d，20° 增益下测得）→ 被 v7 取代：20° 增益藏住了 1–2° 的偏移，7° 增益下它们成了 15–30 % 的闭合。
