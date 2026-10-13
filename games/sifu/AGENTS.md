# Agent 入口（师父 Sifu）

先读 [README](README.md)，再按当前问题进入对应文档。项目当前状态在独立工程的 PROJECT_STATE 里，不在这里；
本目录只提供方法、合同和已被证伪的假设。

## 接手一个新任务前

1. 核对 `appmanifest_2138710.acf` 的 `buildid`（本目录快照为 `18739835`）。build 变了 → 先用 CUE4Parse 重新 dump
   目标网格、骨架、W 材质实例和面部姿势资产，与上一 build 比较（[技术合同](TECHNICAL_CONTRACTS.md) §7）。
2. 确认 UE **4.26.2** 和编辑器插件能编译（[开发工具](DEV_TOOLING.md) §2）。内容工程名必须是 `Sifu`，否则 cook 出的路径不在
   `Sifu/Content/` 下。
3. 先看 `Sifu\Content\Paks\~mods` 里装了什么。替换同一网格的 mod 会互相覆盖：一次只装一个，换装前把用户的包备份出来。
4. 首次进游戏前备份存档（`%LOCALAPPDATA%\Sifu\Saved\SaveGames`）。测试只读档。
5. 分清这一版改的是几何、权重、材质、布料还是骨链；一版只让一类改动进入实机反馈。

## 硬性规矩（本项目已付过学费）

- **UE Python 读出来的结构体是副本。** `mesh.get_editor_property("materials")` 的元素改了不会写回；要建新列表整体 set，
  再断言读回。烘焙后的 pak 用 CUE4Parse 核对每个槽的材质路径（[排障手册](TROUBLESHOOTING.md) §1）。
- **游戏自己的资产只做占位、不进 pak。** 母材质、W 材质实例、物理资产、骨架都按游戏路径建占位；`cook_pak.ps1` 只收
  目标网格和自己的资产目录。占位被打进 pak 会盖掉游戏原件。
- **材质槽 0–10 归自己，代理槽放 11。** W 的第 2、3 套服装按槽号覆盖 11–16 和 18。
- **骨架不动。** 网格只能用游戏骨架里已有的骨（W 的 268 根 + Base_skeleton 的备用骨）；旋转逐骨等于 W 参考姿势。
- **Blender 一律 `-b --factory-startup` 跑**，输出路径用绝对路径。不加 factory-startup 会加载用户装的第三方插件。
- **物理调参只信数字。** PhysX 的角阻尼几乎不管摆动（只作用在质心惯量上），驱动是加速度驱动；
  先按 [物理](PHYSICS.md) §2 的公式算，再进游戏看。
- **裙摆问题先离线复现。** 用 `SifuExport anim` 解出出问题的那一招，在 `skirt_sim.py` 里比较候选；
  只信 2 次和 6 次迭代都同意的结论。
- **悬挂件在 T→A 重摆后要回正。** 挂在手臂下的袖子、绳带会跟着手臂转 50° 以上，甩进腿里（`hang`，[角色拟合](CHARACTER_FIT.md) §1）。
- **远程机上的 GUI 只能从用户会话启动。** SSH 在 session 0，从那里启动的游戏看不见、截图是黑的
  （[开发工具](DEV_TOOLING.md) §4）。
- **不要声称实机通过。** 预览、离线替身、pak 引用检查都只是 `offline-accepted`。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系
（例：「测试 1–4 发暗是光照 / 材质参数问题」被证伪为「所有槽的材质都是 null」）。
