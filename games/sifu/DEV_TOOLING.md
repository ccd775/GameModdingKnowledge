# 开发工具

源码和脚本在 [便携工具包](../../portable-kits/sifu/README.md)；这里说明它们解决什么问题、怎么用、有哪些坑。

## 1. SifuExport（CUE4Parse 命令行）

无界面的 C# 小工具（.NET 10，NuGet `CUE4Parse` / `CUE4Parse-Conversion` 1.2.2.202610），专为本作写：

```text
SifuExport <paksDir> <outDir> <command> [args...]
  环境变量：SIFU_AES=0x...（游戏 pak 需要；读自己的 mod pak 不需要）、SIFU_GAME=GAME_UE4_26、可选 SIFU_USMAP / SIFU_OODLE
  list <regex>              列出匹配的包路径
  json <pkg>...             导出包里所有 export 的 JSON
  export <fmt> <pkg>...     导出网格 / 贴图（uemodel | gltf | psk）
  skel <pkg>...             骨架网格或骨架的精确参考姿势 / 形变目标 / section
  anim <pkg> <帧号>...      解码动画，输出这些帧每根骨的父空间平移 / 旋转（未打关键帧的骨取参考姿势）
  raw <pkg>...              原始 uasset / uexp / ubulk
  file <路径>...            按 pak 内路径取原始文件
  grep <路径正则> <字符串>...  在匹配的 .uasset 里搜字节串（找谁引用了某个资产 / 名字）
```

- 包路径可以写 `/Game/...`（自动换成 `Sifu/Content/...`）。
- `anim` 的帧号必须小于 `numFrames`，否则抛异常。
- 读回自己的 mod pak：把 pak 单独放进一个目录，不给 AES，`json` 网格包，查 `MaterialSlotName` / `Material.ObjectPath` 和 `PostProcessAnimBlueprint`。

## 2. 编辑器插件 SifuModTools（UE 4.26 C++）

Python 够不到的编辑器操作都放在这个 `BlueprintFunctionLibrary` 里，Python 以 `unreal.SifuModToolsLibrary.*` 调用：

| 函数 | 作用 |
| --- | --- |
| `CreateClothFromSection` | 从某个 section 建 NvCloth 资产并绑定；顶点色 R → 最大距离，G → AnimDrive 遮罩；`ConfigJson` 写到 `UClothConfigNv` |
| `CreateClothProxy` | 代理流程：从代理槽的低模 section 建布料、删除该 section、以 mesh-to-mesh 绑定到渲染槽；`BackstopScale` > 0 时由 G / B 生成 backstop |
| `RemoveAllClothing` | 清除网格上的全部布料 |
| `CreatePhysicsAsset` / `BuildPhysicsAsset` | 建物理资产；按 JSON 填胶囊 / 锥形胶囊 / 球 / 盒（骨局部坐标、cm）、运动学标记与约束 |
| `SetupRigidBodyPostProcess` | 把（后处理）动画蓝图的 AnimGraph 重建为 InputPose → LocalToComponent → RigidBody → ComponentToLocal → Output，把 JSON 写进 `FAnimNode_RigidBody` 并编译 |
| `SetPostProcessAnimBlueprint` | 设置网格的后处理动画蓝图 |
| `DumpRefSkeleton` / `DumpSections` | 参考骨架、LOD0 section（材质索引、顶点、三角形、布料 GUID）的 JSON，用于核对 |

用 `RunUAT BuildPlugin` 编译（`build_plugin.ps1`），产物复制到工程的 `Plugins/`。本项目的构建机上 UBT 实际选的是 VS2022 MSVC 14.44。
写插件时直接读 UE 4.26 的引擎源码头文件（`ClothConfigNv.h`、`ClothingSimulationNv.cpp`、`AnimNode_RigidBody.h`、
`ConstraintDrives.cpp`、`PhysicsInterfacePhysX.cpp` 等）确认字段和行为；backstop 与加速度驱动的结论都来自源码。

## 3. 命令行跑 UE Python（`ue_run.ps1`）

```text
UE4Editor-Cmd <工程>/Sifu.uproject -run=pythonscript -script=<脚本> -unattended -nullrhi -nosplash -nop4
```

- 脚本参数通过一个 JSON 文件（参数列表）传，避免命令行引号问题；`ue_run.ps1` 负责写这个文件，再把日志过滤出错误和 `_DONE` 标记。
- commandlet 的日志文件里**没有** `LogPython` 的普通输出：脚本把结果写到自己的 JSON（`ue_build_out.json`），以它为准。
- 不需要开编辑器界面，可以在没人登录桌面时通过 SSH 跑。

## 4. 远程构建机与实机测试

本项目的游戏和 UE 装在另一台 Windows 机器上，本地只有 Blender 和脚本：

- 文件和命令走 SSH / scp（远端 OpenSSH Server，默认 shell 是 cmd，要 PowerShell 就 `pwsh -NoProfile -File ...`）。
- **SSH 会话在 session 0，看不到桌面**：从 SSH 启动的游戏不会出现在屏幕上，截图是黑的。启动游戏、截屏、按键要在用户的交互会话里执行
  （本项目用一个 `/IT` 计划任务在用户会话里跑输入 / 截图代理）。以管理员身份运行的窗口收不到普通权限任务的输入（UIPI）。
- 实机连拍（`burst.ps1`）：在用户会话里隐藏启动一个守护脚本，通过 SSH 往触发文件写「帧数 间隔ms 标签 缩放」开始连拍，
  `quit` 结束；`frames_to_gif.py` 把帧拼成 GIF 和带时间标注的联系表。键盘输入前要先点一下游戏窗口（代理启动时会抢焦点）。
  测完删除帧目录。
- 构建机的桌面可能被其它会话同时使用（别的游戏项目）：动桌面、开游戏前先协调，结束时关掉自己开的窗口。
- 远端大流量下载（BT）曾让 SSH 卡在密钥交换，重启远端后恢复。

## 5. 其它

- 游戏目录带 shipping PDB：按正则在 PDB 里搜类名和 `Z_Construct_UClass_*_Statics::NewProp_*`，可以快速知道某个类有哪些属性
  （本项目用来查角色材质 / 变老相关的类）。
- Blender 4.2.23 后台运行一律加 `--factory-startup`；输出写绝对路径（相对路径会落到当前目录，曾经写到磁盘根目录被拒绝）。
- Git Bash 里 Windows 的 Python `print` 带 `\r`：把输出读进 shell 变量前 `tr -d '\r'`（曾让 pak 检查把目录名比较失败）。
- heredoc 里的 Python 含 `'''` 或反斜杠路径时容易被 shell 截断或改写：补丁写成文件再执行。
