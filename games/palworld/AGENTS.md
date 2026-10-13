# Agent 入口（幻兽帕鲁）

先读 [README](README.md)，再按当前问题进入对应文档。本目录只提供方法、合同和已被证伪的假设；
项目当前状态在项目目录的 `PROJECT_STATE.md`，脚本见 [便携工具包](../../portable-kits/palworld/README.md)。

## 接手一个新任务前

1. 核对 Steam appmanifest 的 `buildid`（本目录快照为 `25246127`，游戏 v1.0.5.102999）。build 变了就换对应版本的 usmap，
   重新导出 OldCloth001 网格、`SK_PalHuman_Skeleton`、`ABP_F_OldCloth001_Implimentation` 和服装数据表，复核骨名、
   配件链和服装层的拓扑；脸型、发型的数量也会随版本增加（本快照女性脸型 26 个、发型 37 个）。
2. 确认测试角色是女性、穿的是初期装备。身体替换只替换默认服装；穿了身体护甲就看不到 Karin，要用游戏自带的
   古典式化妆台把外观设成「初期装备」（[技术合同](TECHNICAL_CONTRACTS.md) §7）。
3. 列出 `Pal\Content\Paks\~mods` 里已有的包。用户自己的参考 mod（同样替换 OldCloth001 和脸型、发型）会和本 mod 冲突；
   不要擅自删除用户的包，移走前先问。
4. 远程测试机可能被用户或其他会话占用。启动游戏、移动角色前确认桌面空闲；不要关掉别人的程序。
5. 分清这一版改的是网格、物理参数还是材质。只改物理参数时跳过 Blender 和网格导入：改 `physics_tune.json` → 离线模拟导出
   → 生成 AnimBP → cook，十分钟内出包。

## 硬性规矩（本项目已付过学费或从剑星继承）

- **物理链只能用游戏骨架里已有的骨，父骨要一致。** Kawaii 按 USkeleton 建链；网格独有骨在编辑器里能动，进游戏不动。
  本作骨架有 4079 根骨，大部分是 NPC 的配件链，挑线性、且玩家动画里没有轨道的链来借用。
- **改物理参数先离线复现。** 用户说「硬」或「穿模」时，先用 `kawaii_sim.py` 在游戏的跑步动画上复现（链在限制上停留的比例、
  裙摆陷进大腿的顶点数），再改参数；只凭感觉改，r3 就把耳朵调成了几乎不动。
- **不要给贴腿的裙链加紧的角度限制。** Kawaii 1.17.1 在碰撞之后才执行角度限制，紧的限制会把被大腿推开的关节拉回大腿里。
- **骨的 bind 朝向必须等于原版。** 动画写的是绝对局部旋转；只有位置可以换成 Karin 的。
- **占位资产不能进包。** 骨架、物理资产、父材质、`ALI_HumanCloth` 是游戏路径上的占位，只给编辑器编译用；
  cook 后按白名单挑文件，打进包的只有网格、AnimBP 和 `/Game/Mods/KarinPal/`。
- **cook 和 AnimBP 生成都要检查成功标记。** cook 日志里要有 `Success - 0 error(s)`；AnimBP 编译结果要有 `errors=0`，
  并在日志里读回 `PhysicsSettings`、`Gravity`、曲线，确认新参数真的写进去了。
- **pak 读回再安装。** 用 PalExport 读自己的 pak，核对网格骨数、材质槽、AnimBP 的节点和参数；安装和发行都按 SHA256 核对。
- **不要用单张静止截图宣称物理或表情生效。** 物理看跑动、跳跃中的姿态；眨眼用连拍。

## 报告口径

结论归到 `invariant` / `build-sensitive` / `case-derived` / `hypothesis` / `rejected` 之一。
历史失败不删除；后来的证据只用于收窄旧结论的适用范围，并写明 supersedes 关系。
