# 开发工具与实机操作

脚本与源码在 [便携包](../../portable-kits/dragons-dogma-2/README.md)。

## 1. DD2Tool（REE-Lib 上的最小 CLI）

C# 源码约 900 行，依赖 kagenocookie/RE-Engine-Lib（commit `bf0e5e5`，2026-09-19，未修改）。REE-Lib 需要 C# 14 → .NET 10 SDK。

| 命令 | 作用 |
| --- | --- |
| `toc <pak> <out.tsv>` | 列出 PAK 条目（路径哈希、偏移、大小、压缩、加密）；remap 表另写 `<out>.remaps.tsv` |
| `resolve <pak> <old.list> <out.list> [ext=ver,...]` | 把旧路径表按新版本后缀改写，只保留 PAK 里存在的路径 |
| `extract <pak> <list> <regex> <outdir>` | 按路径表 + 正则提取 |
| `pack <out.pak> <staging>` | 把 `natives/...` 目录打成 KPKA |
| `meshinfo <mesh> <out.json>` | 骨表（名字、父、local / global 矩阵）、材质、组、LOD |
| `meshconv <in> <out> "DD2"` / `"DD2 (old v2)"` | 在 `260421070` 与 RE Mesh Editor 能读的 `240423143` 之间转换 |
| `meshreorder <in> <ref> <out>` | 按参照网格恢复骨序（参照里有的骨排在前面、同序） |
| `meshdiag` | 网格诊断 |
| `tex2dds <tex> <dds>` / `dds2tex <template.tex> <dds> <out>` | TEX ↔ DDS（写 TEX 时借模板头部） |
| `mdfinfo` / `mdfrt` / `mdfbuild <spec>` | MDF dump / 往返 / 按 spec 生成 |
| `chaininfo` / `chainrt` / `chainbuild <spec>` | chain dump（反射全部字段）/ 往返 / 按 spec 生成（[chain 物理](CHAIN_PHYSICS.md) §1） |
| `rszdump <rsz 资源目录> <pfb/user> <out> [depth]` | 需要与当前 build 匹配的 RSZ 模板（TU3.2 后官方模板过期） |

### Win10 上 .NET 10 的 CET 坑

未装 CET 内核修复的 Windows 10 19044 上，.NET 10 SDK 的 `csc.exe` / `VBCSCompiler.exe` / `MSBuild.exe` 等 apphost 带 `CETCOMPAT`
标记，启动即报 `Your Windows doesn't fully support CET`。处理：用**便携副本**的 SDK，只对副本里的 exe 清除 PE 调试目录中
`IMAGE_DEBUG_TYPE_EX_DLLCHARACTERISTICS` 的 bit0（`clear_cet_flag.py`，原文件备份为 `*.cet.bak`）。不要改系统级 dotnet。

## 2. 开发控制台（REFramework）

- `karin_dev.lua`（只在开发时装，不随 Mod 发行）每 15 帧轮询 `reframework/data/karin_dev/cmd.json` = `{"id", "lua"}`，
  对新 id 在游戏线程上 `load` + `pcall` 执行一次，把返回值写到 `result.json`。返回值必须可 JSON 序列化。
- 帮助函数表 `K`：`K.player()`（`app.CharacterManager:get_ManualPlayer()` 与其 GameObject）、`K.comp(go, type)`、`K.child` /
  `K.children`、`K.tname`、`K.str`、`K.mesh_res` / `K.mdf_res`（建资源并取 holder）。
- 客户端 `devcmd.py <file.lua | -e "code">`：原子写入 cmd.json（先写 `.tmp` 再 replace），按 id 等结果。
- 这是本项目最省时间的工具：不重启游戏就能读对象、试 setter、装临时 hook、录数据。

## 3. 查询脚本（devqueries）

| 脚本 | 用途 |
| --- | --- |
| `player_state.lua` / `mockup_state.lua` | 玩家 / 菜单模型（`app.GUIMenuMockupList`）的网格与材质资源路径等状态 |
| `audit_joints.lua` | 遍历一个角色的缓存（字段、joint 列表 / 数组、`List<app.X>` / `app.X[]` 里含结构体）：own / dangling / foreign joint 计数；验收要求 dangling = 0 |
| `audit_foreign_refs.lua` | 子物体与场景里其他角色（约 1.2 s）对玩家 joint 的引用及失效数 |
| `audit_scene_refs.lua` | 全场景每个 `via.Behavior` 按同样规则遍历（慢，会卡游戏数秒） |
| `container_joints.lua` / `native_refs.lua` / `ubt_lists.lua` | 容器里的 joint 缓存、脚本缓存的原生 `via.*` 对象类型、UpperBodyTransformer 列表长度 |
| `chain_probe.lua` | 每个 joint 的世界位置，以及 chain 把它从 base（静止）旋转转开了多少 |
| `chain_live.lua` | **在线调物理**：按 setting id 设组倍率 `set_GravityRate / set_DampingRate / set_ElasticRate / set_MotionForceCoef / set_AngleLimitCoef`，返回链尖下垂 |
| `skirt_rec.lua` + `skirt_get.lua` | **逐帧录制**：BeginRendering 前把裙节点和大腿骨换到 Hip 静止系（毫米整数）存进表，`NFRAMES` 帧后停；get 写 `karin_dev/skirt_rec.json` |

- **Lua 给 float 参数传 `1.0`，不要传 `1`**：整数会被当作整数位传入 float 参数，读回约 0（一次「全部倍率 = 1」的基线因此作废）。
- 录制配合按键脚本：开始录制 → 按住 W 走 N 秒 → 取数据 → Python 计算节点到身体表面的深度。读档后头一两秒游戏不认输入，先试按一次确认角色在动。
- 坐标系：点 `p` 的身体系坐标 = `conj(qHip)·(p − hipPos)`，Hip 局部 X = 上、Y = 角色右、Z = 前。

## 4. 反汇编托管方法

`DD2.exe` 磁盘上的 `.text` 未加密：`pefile` + `capstone` 按 image base `0x140000000` 反汇编。崩溃日志里的 `DD2.exe + 0x…` 就是 RVA；
REFramework 的 `method:get_function()` 给出方法地址。托管方法第一个参数是 VM 上下文，`rdx` = this；字段偏移用
`field:get_offset_from_base()` 对照（注意泛型基类的 −8 偏差，见 [运行时注入](RUNTIME_INJECTION.md) §7），枚举值用静态字段 `get_data(nil)`。
皮肤烘焙状态机就是这样拆出来的。hook 前看相邻方法地址间距：间距 0x20 的极小 / 折叠函数不要 hook。

## 5. 驱动游戏（自动化）

- 游戏忽略瞬时按键 / 点击：用 AutoHotkey 按住式（按下—保持数十毫秒—抬起）。窗口在后台时不渲染，截图是旧帧，每批动作前先激活窗口。
- **菜单逐步截图核对**：菜单记住上次焦点；每次按确认（F）前用模板匹配 / 亮度核对高亮项，不符就右键退出。盲按键序列曾误触
  「中途保存并继续游戏」覆盖了一次中途存档。
- 游戏内重读档（不写存档）：暂停 → System → Save →「放弃保存直接回到标题界面」→ 是 → 标题「继续」。
- 标题画面：关 REFramework 菜单（Insert）→ Enter → 首项高亮后 F。
- 结束进程：`DD2.exe` 和 `CrashReport.exe` 一起杀，并循环确认进程消失（taskkill 后要几秒才退）。
- 压力脚本：对话手势、走动、跳跃、攻击、蹲、暂停菜单、装备界面，每轮查进程与日志 `Exception occurred|hook error`。
- 与同机其它游戏自动化会话共用一个「前台锁」文件，拿到锁才动前台窗口，用完释放。
- Python 里用 `subprocess` 调 Git Bash 时用 `shutil.which("bash")`；裸 `bash` 会命中 `System32\bash.exe`（WSL）。

## 6. 第二台测试机

DLC 只装在另一台机器上时，用 SSH（命令、文件）+ 用户会话里的计划任务（桌面输入与截图）远程测试：

- SSH 会话在 session 0，看不到桌面，从 SSH 启动的游戏不会出现在用户屏幕上 → 游戏要经桌面动作启动。
- 远端放 DD2Tool + 便携 .NET 运行时、同一个开发控制台客户端、按 Mod 暂存目录，以及「游戏未运行时安装其一、先删另一个 Mod 的文件、打印哈希」的安装脚本。
- 看脸用暂停菜单 Photo（拍照模式）。远端存档同样先备份、只读档。
- 不留临时文件；关掉自己打开的窗口；批量操作前请用户别动那台机器的键鼠。
