# Agent 入口（霍格沃茨之遗 Hogwarts Legacy）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对游戏版本（主菜单右下角，本目录快照为 `1613387`）和 `appmanifest_990080.acf` 的 `buildid`（`20773316`）。
   变了 → 先用 retoc + CUE4Parse 重新 dump 目标网格、`Biped_Skeleton`、目标材质实例和一个原版网格的 section，
   与本目录的格式结论比较（[技术合同](TECHNICAL_CONTRACTS.md) §2）。
2. 确认 UE **4.27** 能跑 Python commandlet，编辑器插件能编译，HLMeshProbe 能以 `GAME_HogwartsLegacy` 读回原版网格
   （[构建流水线](BUILD_PIPELINE.md) §1）。
3. 先看 `Phoenix\Content\Paks\~mods` 里装了什么。替换同一资产路径的 mod 会互相覆盖：一次只装一个，换装前把用户的包备份出来。
4. 首次进游戏前备份存档（`%LOCALAPPDATA%\Hogwarts Legacy\Saved\SaveGames\<id>`）。确认存档用的脸型 / 发型预设，
   替换目标随它定（[技术合同](TECHNICAL_CONTRACTS.md) §7）。
5. 分清这一版改的是拟合、材质、物理参数还是表情；一版只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **每个网格的骨必须都在它引用的骨架里。** 导出时所有部件共用一个骨架对象，头和空模型带上了 95 根游戏骨架没有的动态骨，
  游戏玩几分钟后在分层混合里崩溃（[排障手册](TROUBLESHOOTING.md) §1）。只有引用自带骨架（`SK_Karin_*_Skeleton`）的网格可以带它们；
  发行前对每个网格查名字表。
- **「模组崩溃」弹窗先看转储，不要先猜检测机制。** 崩溃报告器在装了 `~mods` 时一律建议卸载模组；
  `Saved\Crashes\<GUID>\` 里的 `CrashUserData.json`、`CrashContext.runtime-xml` 和 `.dmp` 才说明崩在哪里。
- **不新建材质实例。** HL 的 `UMaterialInterface` 尾部有 20 字节的唯一哈希；借用游戏的材质实例、替换它们的贴图。
  需要不影响别的部件时，按字节克隆到游戏里没人用的路径（[技术合同](TECHNICAL_CONTRACTS.md) §3）。
- **UE Python 读出来的结构体是副本。** `mesh.get_editor_property('materials')` 的元素改了不会写回；建新列表整体 set，
  烘焙后用 CUE4Parse 核对每个槽（全身灰色棋盘格就是槽为空）。
- **游戏自己的资产只做占位、不进包。** 骨架、物理资产、母材质、材质实例都按游戏路径建占位；组装时只收 `RiggedObjects/Characters/Human` 下
  自己替换的资产。占位被打进包会盖掉游戏原件（`Biped_Skeleton` 被盖掉会影响所有角色）。
- **重新导入前先删除资产。** UE 的 reimport 沿用资产里存的旧导入设置（曾因此导入 0 个形变）。
- **数据资产只做等长或带偏移修复的二进制修改。** 改了长度就要修导出表的 `SerialSize` 和 `BulkDataStartOffset`；
  改完用 CUE4Parse 读回。
- **物理调参只信数字。** AnimDynamics 的阻尼是 `(1-d)^dt`、作用在绝对空间；长链逐级累积滞后。先按 [物理](PHYSICS.md) §3 的模型算，
  再用 `feel_sim.py` 比较候选，最后进游戏。
- **远程测试机上的 GUI 只能从用户会话启动**；SSH 会话启动的游戏看不见、截图是黑的。
- **不要声称实机通过。** 预览、离线模型、读回检查都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系
（例：「旧 mod 全身发灰是因为超过 4 个骨影响」只是猜测，实测的灰色棋盘格原因是材质槽为空；
「崩溃弹窗是非官方 mod 检测」被转储证伪为骨架外的骨）。
