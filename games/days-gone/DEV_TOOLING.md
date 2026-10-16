# 开发工具

脚本都在 [便携工具包](../../portable-kits/days-gone/README.md)；这里讲每个工具解决什么问题、有哪些坑。

## 1. DgExport（CUE4Parse 命令行）

- C# 写的 CUE4Parse 1.2.2 命令行：`DgExport <Paks 目录> <输出目录> list|json|raw|export|skel|anim|file …`。
  - `list <正则>`：列包内路径；`json` / `raw`：导出属性 JSON / 原始 uasset；`export`：网格转 `.uemodel` / glTF；
  - `skel`：骨名、父子、重定向模式、参考姿势，以及每个 LOD 的 `requiredBoneNames`；`file`：按路径原样取文件（如 `.lsd`）；
  - `anim`：CUE4Parse 解码的动画帧——**对面部动画没用**（per-track 压缩被解成常数轨道），面部动画取 `raw` 再用 `anim_pertrack.py`。
- 默认按游戏的 EGame 读；读原版 4.11 cook 出来的 mod 包时设 `DGX_GAME=GAME_UE4_11`。
- 在 Git Bash 里传 `/Game/...` 参数要设 `MSYS_NO_PATHCONV=1`，否则会被改写成 Windows 路径。
- 测试机上大批量导出时把结果打成 tar 再一次性取回；隧道在大流量下容易断。

## 2. Python 包工具（numpy）

| 工具 | 作用 |
| --- | --- |
| `upkg.py` / `uhdr.py` | 最小 uasset 读写：包头、名字表（带哈希）、导入 / 导出表、带标签属性解析、追加导出 / 导入、导出数据重排 |
| `paklist.py` / `pakextract.py` / `pakwrite.py` | pak v3 列表、解包、写包（在参考 mod 上验证过往返一致） |
| `refskel.py` | 从 cook 后的网格里按结构找到参考骨架（骨信息数组 + 变换数组），给出局部 / 组件矩阵和数组偏移 |
| `skel_retarget.py` | 改骨架包里骨的平移重定向模式（`face_*` → `AnimationRelative`） |
| `retarget_inplace.py` | 原地改名字表字符串、保持包头大小（带内联着色器图的 MI） |
| `skelmesh_normals.py` / `skelmesh_positions.py` | 在 cook 后网格的 GPU 蒙皮顶点缓冲里原地改法线 / 位置 |
| `anim_pertrack.py` | 解 `AKF_PerTrackCompression` 动画（Days Gone 的面部 / 口型动画） |
| `abp_springs.py` | 往烘焙后的动画蓝图里插 AnimDynamics 弹簧节点和 CopyBone 节点 |
| `blink_amp.py` / `lid_calib.py` | 眼睑放大骨的参考姿势补丁 / 眼睑关节标定 |
| `make_pak.py` / `patch_looks.py` | 组装 mod pak / 改 66 个 look |

## 3. Blender

- Blender 4.2，装 UEFormat 插件（`io_scene_ueformat`）才能导入 `.uemodel`（迪肯的头部网格和骨架）。
- Blender 自带的 Python 有 numpy，项目也用它跑上面的打包工具。
- 构建脚本按 `blender -b <build.blend> --python <脚本> -- <参数>` 运行，输出写绝对路径。

## 4. 远程测试机

- 用户的另一台 Windows 机器：装游戏、UE 4.11.2（用户授权安装）和 DgExport。命令和文件走 SSH；编辑器和游戏是 GUI，
  **只能从用户的桌面会话启动**（SSH 在 session 0，启动的窗口看不见、截图全黑），通过远程桌面的截图 + 点击 / 按键操作。
- **UE 4.11 编辑器只能用 GUI 导入 FBX**：对话框位置固定后，导入 → 覆盖确认 → 导入选项 → 保存 → 关闭可以写成固定的点击序列；
  每一步截图确认再继续。编辑器会顺带拉起 SteamVR，结束后关掉。
- **显示模式**：Bend 读 `%LOCALAPPDATA%\BendGame\Saved\Config\WindowsNoEditor\GameUserSettings.ini` 里自己的一行
  `VideoSettings=<W>x<H><f|w|wf> -device=0 -hdr=0 -refresh0=<Hz> -refresh1=1`（和 `LastUserConfirmedVideoSettings`），
  不是 `ResolutionSizeX` / `FullscreenMode`。用户云存档里的 `3840x2160f … -refresh0=144` 在远程桌面的虚拟显示器上设不上 →
  启动即 `SwapChain->ResizeTarget E_FAIL` 崩溃。测试期间改成 `1024x768w -refresh0=60`，改之前备份原文件，结束后问用户是否恢复。
  `set_resolution.ps1` 改桌面分辨率并列出可用模式；`watch_launch.ps1` 记录游戏进程的启动、窗口标题和退出码（排查秒退）。

## 5. 实机测试操作

- 启动：`steam://rungameid/1259420`，约 90 s 后进程稳定；标题画面按 Enter，主菜单默认高亮「繼續」，Enter 读档（约 60 s）。
- **失焦即暂停**：每次远程调用都会抢焦点、弹出暂停菜单。要在游戏里做的事（关菜单、转镜头、连拍）放在同一次调用里：
  切到游戏 → Esc → 动作 → 截图。
- **连拍**：同一次调用里连续截 20–40 张编号截图，取回后裁出脸 / 裙摆区域拼成联系表看；眨眼要镜头在正面时看。
- **照片模式**：暂停菜单「照片模式」。右键拖动绕角色转（范围有限，绕不到正脸时就退出照片模式——退出后游戏镜头保持照片模式的朝向，
  可以直接在游戏里看正脸）；E / Q 换页；「鏡頭」页的光圈调到 f/8 减少景深模糊；「角色」页「臉部表情」用右方向键切换表情。
  退出时按 Esc 会问「確定要離開照片模式嗎？」，Enter 确认。照片模式里 R 是「重設」镜头；**游戏里 R 是快速存档**。
- **退出**：暂停菜单点「離開並回到桌面」→ 截图确认是「離開並回到桌面 / 警告」对话框 → Enter。暂停菜单默认高亮「儲存遊戲」，不要在菜单上直接按 Enter。
- **崩溃**：会留下「回報問題」窗口，Steam 随后一直说游戏在运行 → 点「不要回報」关掉。编辑器开着时游戏约 2 秒后退出（退出码 0、没有 dump）。
- 用户可能同时在看、在玩：动手前截图看当前状态，不要关掉用户自己打开的窗口。
