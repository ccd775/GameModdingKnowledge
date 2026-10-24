# Agent 入口（刺客信条：大革命）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。工具链与奥德赛（`games/assassins-creed-odyssey/`，完整仓库里有）同源，那边的规矩多数也适用，差异在下面写明。

## 接手一个新任务前

1. 核对游戏版本：本目录快照是 Steam 版（289650）build 21970519，游戏内 1.5.1，forge v27。版本变了 → 重建全部 forge 的索引（`acu_forge.py index`），
   重新扫描内嵌副本（`scan_objs.py` → `objs_to_tsv.py`），再核对 `build_mod.py` 顶部的数据 ID 和列号（[技术合同](TECHNICAL_CONTRACTS.md) §3、§5）。
2. 先跑 `acu_install.py status`：有状态文件说明 mod 装着。**游戏在装着 mod 时被更新或校验过，就不要再卸载**（会把旧索引行写回新文件）：
   删掉 `<游戏目录>\.karin_acu_state.json`，用 Steam「验证游戏文件完整性」恢复原版，再重新安装。
3. 安装和卸载都要求游戏关闭（安装器检查 `ACU.exe` 进程）。用户在哪台机器上测试、能不能在本机启动游戏，按当次授权；本项目 v3 起由用户在另一台电脑上
   测试发行包。多个会话共用桌面时，按约定的锁文件协调，只删自己的锁。
4. 分清这一轮改的是模型 / 材质、物理还是表情；一轮只让一类改动进入实机反馈。物理骨架改动前先和原版骨架逐项对照（[物理](PHYSICS.md) §2）。

## 硬性规矩（本项目已付过学费）

- **同一个对象在很多数据文件里各有一份**：亚诺的表（Body_All、Body_Custom、各装备表、Heads、Hood_Position……）同时嵌在 `CN_P_Arno`、`DataAI_UIDataRoot`
  和每个旧时代服装的数据文件里，而且每个 world forge（巴黎、凡尔赛、序章、时空裂隙……）和它的 patch_02 / 03 都各带一个版本。先 `scan_objs.py` 找全，
  再每一份按它自己的原版改；v1 只改了 `CN_P_Arno`：Karin 显示出来了，但亚诺的装备和牙齿一件都没被隐藏（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **原版先重新编译一遍**：大革命的表 XML 编译回去和原版逐字节相同（不需要奥德赛的空引用填充修补），`build_mod.py` 对每一份都先验证这一点，不同就停。
- **附加骨架**：骨按深度优先排，`Index` = 位置，**`ChildBoneCount` = 后代数**（不是直接子骨数）；`SkeletonKey` / `SkeletonHierarchyKey` 用自己的（不要沿用
  模板的）；BallJoint 的 `LiteRagdoll` 和 `OrientationBone` 留空（原版全部为空）。v3 在后代数、键、`LiteRagdoll` 三处和原版不同，在 Logo 处闪退；三处一起改掉后正常启动，单独哪一处致命没有分开测，全部当规则遵守（[物理](PHYSICS.md) §2）。
- **不要原地替换共享的布料附加骨架**：`ACU_Unisex_Dress_Simple_HV_Col` 被约 30 个 NPC 文件共用。Karin 的物理骨架是新对象，只改玩家附加骨架表里的单元格。
- **BallJoint 没有弹簧**：锥中心放在静止姿势上，重力会把链一路拉到锥边（v4 双马尾、尾巴直垂，裙片压进大腿）。按原版约定逆着下垂方向偏一个锥角
  （[物理](PHYSICS.md) §4）。
- **碰撞只走 CommonData**：BallJoint 自己的 `LiteRagdoll` 引用在原版里全部为空（v3 把它指向 `LiteRagdoll_Player`，是 v3 和原版的三处差异之一）；裙片碰撞用
  `CommonData → BallJointCommonData → LiteRagdoll`，`GravityMode` = `GlobalOwnGravity`（2）。
- **材质用武器模板**：角色模板（`CN_Skin_Wrinkle`、`CN_Cloth_Tile_ColorMasked_AlphaTest`）吃染色遮罩 / 皮肤参数这类编码贴图；Karin 用
  `CN_Weapon_NoAlphaTest`（法线 A 通道 = 光泽度）。
- **网格最多 255 根骨**（顶点格式 v2 没有宽索引），Karin 的 LOD 是 159 根。
- **AcuHarness 的文件参数要带斜杠**（`./x.glb`）：不带斜杠的名字按 harness 所在目录解析。`batch` 里每行用绝对路径。
- **重的中间产物不要放进同步盘**：解包出来的每个文件都会被同步客户端处理，一个数据文件从约 2 s 变成约 30 s。`ACU_SCRATCH` 指向本地目录。
- **ACU.exe 的代码段在磁盘上是加壳的**：静态反汇编不可行，崩溃转储里只有 RIP 附近约 0x100 字节的代码。闪退时先把数据和全部原版对照（[开发工具](DEV_TOOLING.md) §4）。
- **Steam 版经 Ubisoft Connect 启动**：要登录 Ubisoft 账号。agent 不代填凭据，遇到登录框就停下交给用户。
- **不要声称实机通过。** 离线回读、骨架对照、往返安装都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。例：

- 「原版 BallJoint 的偏移方向和任何坐标系测试都对不上（镜像的一对互相矛盾），不能用」（v5 分析）→ 被 v6 取代：按骨的局部坐标系、
  `LocalPitchOft` 绕局部 Z、`LocalYawOft` 绕局部 Y 解释时，116 个带偏移的关节里 93 个朝外摆、7 个朝内，其它轴向 / 符号组合都在随机水平。
- 「把裙片蒙到大腿上就能跟着腿走」→ `rejected`：裙摆挂在髋关节高度，大腿转动只会把蒙上的裙摆往上、往后带，不会往前推开。
