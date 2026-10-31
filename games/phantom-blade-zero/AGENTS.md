# Agent 入口（影之刃零 Phantom Blade Zero）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对 `appmanifest_4115450.acf` 的 `buildid`（本目录快照为 `26266538`）。build 变了 → 先重新 dump 身体、头、外观数据表、
   `BP_Renewal_Hun` 和骨架，与上一 build 比较（[技术合同](TECHNICAL_CONTRACTS.md) §8）；usmap 也要重新生成（[开发工具](DEV_TOOLING.md) §2）。
2. 确认 UE **5.7** 编辑器（Epic 启动器版）和插件 PBZModTools 能编译（VS 2022 C++ 生成工具，项目用 MSVC 14.44）。
   内容工程名必须是 `ProjectPBZ`，且带一个空的 `HuaShira` 插件，否则 cook 出的路径对不上 `ProjectPBZ/Plugins/HuaShira/Content/`。
3. 先看 `ProjectPBZ\Content\Paks\~mods` 里装了什么。两个 Karin 包（`z_KarinPBZ_P`、`z_KarinPT_P`）替换同样的资产：一次只装一个。
4. 游戏由用户启动和游玩。**不要启动、结束或切到前台游戏进程**；只在游戏关闭时往 `~mods` 里装文件（安装脚本会拒绝在游戏运行时安装）。
5. 分清这一版改的是几何、材质、布料还是表情；一版只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **替换身体时保留原版身体的每一根骨。** 身体网格就是游戏里的领导者（`CharacterMesh0`）；原版 `Hun_Body_Simple` 有 264 根骨，
  其中 `weapon_l_child`、`weapon_r_child`、`ik_weapon_l_child`、`ik_weapon_r_child` 不在隐形网格 `Hun_Invs` 里。只按 `Hun_Invs`
  取骨，醉剑就丢了剑的模型和攻击判定（醉态攻击动画驱动 `weapon_r_child`）。导出后逐骨比较原版身体和新身体的骨名（[技术合同](TECHNICAL_CONTRACTS.md) §4）。
- **cook 要带版本号。** 游戏的引擎是改过的 5.7.4；无版本号（unversioned）的包一加载就崩。
- **只打自己的资产。** 骨架、物理资产、后处理动画蓝图、母材质按游戏路径建占位，cook 出来但不进容器；`mkcontainer.ps1` 的清单之外
  只收 `Mods/KarinPBZ/` 目录。占位进了容器会盖掉游戏原件。
- **隐藏部件用「错类型」的占位。** 一个三角形的骨骼网格存在游戏资产名下：游戏按 ChaosClothAsset / GroomAsset 加载时类型不符，
  组件拿不到资产，就不显示，不会崩。
- **材质只改分层材质的第 0 层**（关联类型 layer、索引 0）。改第 1 层网格不可见；改全局参数整件发白。贴图要做成虚拟纹理，
  否则材质实例退回白色。
- **UE Python 无界面跑之前先等资产注册表扫完**（`search_all_assets(True)`）。否则 `does_asset_exist` 返回假，旧资产没删，新导入并进旧网格，
  材质槽混进上一版的名字。
- **布料：一个布料资产每个 LOD 只能绑一个 section。** 需要一起动的部件（尾巴和系在上面的蝴蝶结）必须放进同一个材质槽，
  贴图就要合成一张。布料段里焊接后出现的退化三角会让整段建不出来（[物理](PHYSICS.md) §5）。
- **不要相信容器大小。** 内容变了 `.ucas` 字节数也可能完全不变；用哈希和读回判断。
- **PowerShell 变量名不分大小写。** `$l` 和 `$L` 是同一个变量；脚本里的循环变量和参数不要只差大小写。
- **不要声称实机通过。** 构建、读回、装进 `~mods` 都只是 `offline-accepted`；实机结论只来自用户。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系
（例：「领导者是隐形网格 `Hun_Invs`」被证伪为「游戏里身体网格装在 `CharacterMesh0` 上，它就是领导者」）。
