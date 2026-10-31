# Agent 入口（刺客信条：枭雄）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的状态文件里，不在这里；本目录只提供方法、合同和已被证伪的假设。
工具链与大革命（完整仓库里的 `games/assassins-creed-unity/AGENTS.md`）同源，那边的规矩（附加骨架三条、只经 CommonData 的碰撞、武器模板材质、≤ 255 骨、harness 路径参数要带斜杠）
在这里全部适用；下面只写枭雄自己的差异和本项目付过学费的地方。

## 接手一个新任务前

1. 核对游戏：本目录快照是一份 `ACS.exe` 链接时间 2016-08-16 的 PC 副本（forge v27、40 个 forge）。换了副本 → 重建索引（`acs_forge.py index`），
   重新扫描内嵌副本（`scan_objs.py` → `objs_to_tsv.py`），再核对 `build_mod.py` 顶部的 `CHARS` / `TABLES` / `PHYS_HOSTS`（[技术合同](TECHNICAL_CONTRACTS.md) §3–§4）。
2. 先跑 `acs_install.py status`：有状态文件说明 mod 装着。**游戏在装着 mod 时被更新或校验过，就不要再卸载**：删掉 `<游戏目录>\.karin_acs_state.json`，
   用商店的「验证文件」恢复原版，再重新安装。
3. 装着 mod 时 forge 里的索引行指向追加的数据：要提取原版副本，用构建缓存（`ACS_SCRATCH\vanilla`）或先卸载；`make_release.py` 读原版指纹时会经状态文件找回原位置。
4. 安装和卸载要求游戏关闭（检查 `ACS.exe` 进程）。用户在控制台前时不要启动或操作游戏；能否在本机实机测试按当次授权。
5. 分清这一轮改的是模型 / 材质、物理还是表情；物理一轮只动一组链。

## 硬性规矩

- **两兄妹、每一份副本**：双胞胎的表嵌在玩家实体（`ACVI_CHR_P_*`）、独特 NPC（`ACVI_CHR_U_*`、`*_HID`）、菜单（`ACVI_DataAI_UIDataRoot_*`）、任务数据块、
  搏击俱乐部 / 礼服变体和莉迪亚·弗莱的文件里，每个 world forge 和 `dlc_20` / `dlc_21` 的 patch forge 各带一个版本。payload 按 forge 分版本，`skip.tsv`
  记下没有目标表的副本（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **莉迪亚·弗莱会一起变**：她的头部表用伊薇的头部 LODSelector；所以她的表也去掉可视列、挂物理（不这样做的话按推断会是 Karin 的整个模型叠在莉迪亚的原版身体上，没有实测过）。
- **不碰开膛手杰克的老年雅各布**（`ACVI_DLC_CHR_P_Jacob40`，158 MB）：它只嵌了雅各布的护腕表，老年雅各布本人不是 Karin，项目把它留作原版。
- **骨名靠 CRC32**：探针 GLB 先过 `glb_names.py`，否则拟合脚本找不到 `Hips` / `Head`；面部骨以节点 `extras.Name` 的 ID 为准，别信工具起的别名。
- **枭雄骨架的两个额外字段**：每根骨都有 `MirroringTag`（空）和 `EnablePoseDrivenWrinkles`（False），生成的附加骨架也要写；原版 `ChildBoneCount` 同样是后代数
  （18 个服装骨架 486 / 486 根骨核对过）。
- **裙片碰撞用 `GlobalGravity`**：枭雄 241 个原版 BallJoint 没有一个用 `GlobalOwnGravity`（大革命的裙片用它），带 CommonData 的关节用 GlobalGravity /
  LocalOwnGravity / LocalGravity。
- **不要用 `LocalOwnGravity` 做「回弹」**（`rejected`）：它的重力不在骨自己的坐标系里，v2 的两只耳朵朝同一侧歪、双马尾持续抖动（[物理](PHYSICS.md) §3）。
- **双马尾只模拟隔节**：相邻链节都挂 BallJoint 会高频抖（v2、v4 两次复现）；链感靠按节递增的锥角和递减的摩擦（[物理](PHYSICS.md) §4）。
- **源模型的形态键别全信**：`kisekae_Knee` = 1 但不移动顶点；拟合时用 `--hide-band` 收紧袜子下的皮肤（[构建流水线](BUILD_PIPELINE.md) §3）。
- **构建输出到最后才出现**：`build_mod.py` 的 stdout 在管道里是块缓冲，12 分钟里看不到进度，末行 `BUILD_OK` 才算完成。
- **重的中间产物不要放进同步盘**，`ACS_SCRATCH` 指向本地目录；写完同步盘里的文件后检查同步客户端有没有生成冲突副本。
- **不要声称实机通过。** 离线回读、往返安装、Blender 渲染都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。历史失败不删除，后来的证据只收窄旧结论并写明 supersedes 关系。例：

- 「`LocalOwnGravity` 的 OwnGravity 沿骨自己的 +X，能当弹簧用」（v2，参考原版 Outfit11 饰物推断）→ `rejected`（v3）：两只耳朵的 OwnGravity 各沿自己的 X，
  实机却朝同一侧歪，说明引擎在某个共享坐标系里施加它（角色或世界 X，没有进一步确定）。
- 「双马尾抖动是 `LocalOwnGravity` 引起的」→ 收窄（v4）：改回 GlobalGravity 后，五节都模拟仍然抖；抖动跟着「相邻链节都模拟」走。
