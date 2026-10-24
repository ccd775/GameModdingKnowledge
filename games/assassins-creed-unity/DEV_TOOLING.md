# 开发工具

## 1. AnvilToolkit 与 AcuHarness

- AnvilToolkit 1.3.6（第三方，用户自备）是 GUI 程序；项目只用它的 `AnvilToolkit.dll`，经自写的 AcuHarness（C#，便携包 `acuharness/`）无界面调用。
  harness 用 .NET SDK 的 Roslyn 编译（`build.ps1`），在 .NET 9 便携运行时上跑；运行目录里要有 AnvilToolkit 的 `Libs\`（含 Oodle）和 `Lists\Unity.gfl`。
- AcuHarness 是奥德赛 AcoHarness 的分支（`games/assassins-creed-odyssey/DEV_TOOLING.md`），游戏枚举默认 `Unity`（环境变量 `ACU_GAME`），新增：
  - `import-glb` 的 Unity / Syndicate 分支：顶点格式 v2、两个颜色、切线 + 副法线、> 255 骨拒绝（[技术合同](TECHNICAL_CONTRACTS.md) §7）；
  - `batch <commands.tsv>`：一行一条命令（制表符分隔、绝对路径），在一个进程里跑完，每条后打印 `BATCH <n> rc=<rc>`。启动加名字表预加载每次 1–2 s，
    一个数据文件的作业从约 40 s 降到 2–4 s；
  - `scan-objs <forge> <list.tsv> <IDHEX,…>`：按索引行（偏移、大小、标签）在内存里解压每个数据文件，打印自身 ID 是目标之一的对象（`OBJ` 行），
    读不了的数据文件打印 `ERR`。这是找内嵌副本的唯一手段（[技术合同](TECHNICAL_CONTRACTS.md) §3）；
  - `games`（列出 AnvilToolkit 的游戏枚举和 schema 名）、`mesh-info` / `import-glb` 多打印顶点格式、步长和包围盒。
- 不带斜杠、不以 `.` 开头的文件参数按 harness 所在目录解析：写 `./x.glb` 或绝对路径。
- 判断格式细节时，用 ilspycmd 反编译 `AnvilToolkit.dll` 读源码（例如 Unity 的网格导入选项、骨架和 BallJoint 的字段）。反编译结果不随本库发布。

## 2. 构建性能

- **同步盘**：项目目录在同步盘里时，解包出来的每个文件都被同步客户端处理，一个数据文件从约 2 s 变成约 30 s。原版副本缓存和作业临时目录放进
  `ACU_SCRATCH`（本地、不同步的目录；默认 `%TEMP%\acu_work`）。
- 原版副本缓存在 `ACU_SCRATCH\vanilla\<forge>\<IDHEX>\`（`.xml_ok` 标记导出完成）；大的旧时代服装文件全量导出 XML 要约 40 s，所以只导出 BuildTable。
- 470 个表作业 6 个并行，约 15 分钟；大部分时间花在第一次提取没缓存的副本上。

## 3. Blender

- Blender 5.0.1 后台模式（`-b --factory-startup --python … -- …`）。脚本参数全写绝对路径：相对路径按 Blender 的当前目录解析（从别的目录启动时落到 C 盘根）。
- `render_compare.py`：Workbench 平涂，正面 / 侧面各渲 Karin、亚诺、叠加三张；拟合后先看这个再导出。

## 4. 崩溃分析（v3 在 Logo 处闪退）

- 用户发来的崩溃报告里有 3 个小型转储，全部是 `0xC0000005`，位置 `ACU.exe+0x95240` / `+0x95274`。
- `ACU.exe` 的 `.text` 在磁盘上是加壳的：静态反汇编不可行（`pefile` 读不到异常目录，`.pdata` 为空）；转储里只有出错位置附近约 0x100 字节的代码。
  用 Python 的 `minidump` 读内存段、`capstone` 反汇编这一小段，再结合寄存器和栈上的指针，推出这段循环在做什么（附加骨架合并时的祖先栈，[物理](PHYSICS.md) §2）。
- 推出数据结构的意义后，**把自己生成的数据和全部原版逐项对照**（每个骨架的 `ChildBoneCount`、键、BallJoint 的引用），找出违反的规则。三处不同一起修，
  下一版正常启动。
- 小坑：分析脚本不要叫 `dis.py`：它会遮住标准库的 `dis`，依赖它的模块导入时出错。

## 5. 本机实机测试

v1 / v2 在本机测试；之后用户要求改为交付发行包、由用户在另一台电脑上测试（[验证与发布](VALIDATION_AND_RELEASE.md) §2）。本机流程留作参考：

- Steam 版经 Ubisoft Connect 启动，**要登录 Ubisoft 账号**。agent 不代填凭据：出现登录框就停下，请用户自己登录（v5 那次的本机测试因此没有进行）。
- 窗口化：`<文档>\Assassin's Creed Unity\ACU.ini` 里的 `WindowMode`（推断 0 = 窗口、2 = 全屏，来自枭雄的同名设置，因为上面的登录问题没能在游戏里核对，
  `hypothesis`）和分辨率。改之前备份原文件；**按字节改**（Git Bash 的 `sed` 会把 CRLF 换掉）。
- 启动：`steam://rungameid/289650`，约 85 s 后出现 `ACU.exe`。片头：按住回车约 200 ms，两次（瞬间按键会被游戏丢掉，游戏每帧轮询按键）。
  菜单每按住约 60 ms 走一格。看装备的特写：Esc → 角色自訂（第 2 项）→ 裝備欄 → 裝備（繁体中文界面）。v2 那次键盘和鼠标都没能移动暂停菜单的选择，没查明原因。
- 截图和按键用本机的窗口桥（pywinauto + mss + AutoHotkey v2，带共享的前台锁）；这些辅助脚本绑定本机路径，**不随便携包**。
- 结束：`taskkill /IM ACU.exe /F`（测试存档，可随意处理）；释放前台锁。
