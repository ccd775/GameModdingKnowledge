# 开发工具

## 1. AnvilToolkit 1.3.6 与 AcoHarness

- AnvilToolkit 是 GUI 程序；AcoHarness（便携包 `acoharness/Program.cs`）直接引用 `AnvilToolkit.dll` 无界面调用它。它从影项目的 harness 分出来，
  游戏由环境变量 `ACO_GAME` 选（默认 `Odyssey`），命令按需增加（命令表见 [便携包](../../portable-kits/assassins-creed-odyssey/README.md)）。
- 启动时它做 GUI 会做的初始化：设当前游戏、补上奥德赛 / 起源的 schema 名、建 `ScimitarClassReader`、DirectXTex 和 Oodle 的位置、临时目录，
  然后等 AnvilToolkit 在后台线程里加载完名字表（每 250 ms 看一次条目数，不再变化就继续）。参数里带斜杠或以 `.` 开头的才当作路径转成绝对路径，
  **不带斜杠的文件名按 harness 所在目录解析**（v1 时 `import-glb karin_lod0_ody.glb …` 因此找不到文件）。
- 构建：AnvilToolkit 是 WPF 程序，所以对 .NET 9 的 `Microsoft.NETCore.App` 和 `Microsoft.WindowsDesktop.App` 两套引用程序集编译，
  用 .NET SDK 自带的 Roslyn `csc.dll`；输出旁边放 AnvilToolkit、它的 `Libs\`（含 Oodle、DirectXTex）、`Lists\Odyssey.gfl` 和一个声明两套框架的
  `runtimeconfig.json`，用便携运行时的 `dotnet.exe` 运行。
- 查 AnvilToolkit 的 API 时用 ilspycmd 反编译（`TextureMap`、`Reference` 的读写、`TextureMapType` 枚举、Reflex3 类）。ilspycmd 的启动器崩溃时，
  直接用 `dotnet` 运行它的 dll。
- 已知缺口见 [技术合同](TECHNICAL_CONTRACTS.md) §1。`tex-info` / `tex-export` 碰到带顶层 mip 的贴图会挂起（等 GUI 文件对话框），要手动结束进程。

## 2. 索引缓存与查找

- `aco_forge.py` 只用标准库，直接在测试机上给全部 forge 建索引，只把两个 TSV 拷回构建机；以后查找都在本地做，
  不用每次都碰游戏目录。测试机的控制台是 GBK，脚本把 stdout 改成 UTF-8，名字里的非 ASCII 字符才不会出错。
- `aco_locate.py find` 支持名字、16 位十六进制 ID、`/正则/`；在 Git Bash 里传 `/正则/` 要设 `MSYS_NO_PATHCONV=1`，否则会被当成路径改写。
- `aco_gfl.py` 把 AnvilToolkit 的 `Odyssey.gfl` 导成 TSV（id、类哈希、forge、数据文件、名字），可以按类找对象。类哈希 = 类名的 CRC32：

  | 类 | 哈希 |
  | --- | --- |
  | MaterialTemplate | `BCFB3C7A` |
  | Material | `85C817C3` |
  | TextureMap | `A2B7E917` |
  | TextureSet | `D70E6670` |
  | Mesh | `415D9568` |
  | Skeleton | `24AECB7C` |
  | BuildTable | `22ECBE63` |
  | LODSelector | `51DC6B80` |

  `aco_gfl.py` 读 GFL 用的是影项目 `acsh_forge.read_gfl`（GFL 容器 + AnvilToolkit `Libs` 里的 Oodle v7），不在本库。
- `AcoHarness scan-refs` 在一批数据文件里找引用某个 ID 的对象（例如找谁引用了一个材质模板）。

## 3. Blender

- Blender 5.0.1，后台模式；拟合脚本用 `--factory-startup`。输出路径一律给绝对路径（相对路径按 Blender 的当前目录解析，项目里有一次渲染写到了盘符根目录）。
- 拟合骨架对象名沿用影的 `NaoeRig`；拟合 GLB 里的卡珊德拉网格改名为 `NaoeHeadRef*` 并隐藏，导出时删掉。
- `pose_preview.py` 用 Workbench 渲染，**需要 OpenGL 上下文**：从 SSH 会话直接跑会崩。在交互桌面会话里跑，例如建一个一次性的计划任务
  （`schtasks /Create … /IT`，立即运行，跑完删掉）。
- 拼对照表（多张渲染按网格拼成一张图）用 Pillow 的小脚本，不在本库。

## 4. 测试机流程（项目里的做法）

- 游戏只装在另一台 PC 上，通过 SSH 连接；需要桌面的操作（按键、鼠标、截图）由在交互会话里运行的计划任务执行。链路带宽有限：截图缩成小 JPEG，
  大文件分块（约 1 MB）传，长任务脱离会话运行并写日志（SSH 断开会结束会话里的进程）。用户开着远程桌面观看时链路更不稳定。
- 多个 agent 会话共用测试机桌面时，用一个记着占用者和时间的锁文件协调：开始前确认没有别人在用、只删自己的锁。
- 启动：「运行」里输入 `uplay://launch/5059/0`，约 50 秒到警告画面；警告和片头用空格 / Esc 跳过；主菜单「继续」读最近的存档，约 60 秒。
- **agent 每次远程调用都会抢走前台，游戏失去焦点就会打开暂停菜单**：每一批操作先把焦点切回游戏、再操作、在同一批里截图。镜头：相对移动鼠标，转到侧面 / 背面。
- 关闭：SSH 上 `taskkill /im ACOdyssey.exe /f`（存档是测试存档）。安装 / 卸载都要先确认游戏已退出。
- 分工：身体、装备、辫子这类静态外观由 agent 截图看；物理手感和表情由用户在游戏里看、截图或录屏 —— 眼睑这种几帧内的变化，单张截图看不出规律。

## 5. 录像逐帧分析

- 请用户录 10–20 秒正面脸部特写（例如 Game Bar 录屏），放到测试机上能取到的位置。
- 用 Python + imageio-ffmpeg 抽帧，OpenCV 按固定窗口裁出每只眼，按帧号拼成对照表；逐帧读每只眼的闭合比例，找眨眼峰值和「保持 → 切换」的节奏。
- 配合不对称的诊断构建（一只眼一个候选骨、已知的线性增益），闭合比例可以直接换算成骨在游戏里的转角（[表情](FACE.md) §7）。
- 录像、帧和对照表都是用户的私有素材，不进本库。
