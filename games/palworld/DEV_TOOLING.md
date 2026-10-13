# 开发工具

## 1. PalExport（CUE4Parse 命令行）

剑星 SbExport 的派生，C#，NuGet `CUE4Parse` / `CUE4Parse-Conversion` 1.2.2.202610，net10.0，`EGame.GAME_UE5_1`。

```text
PalExport <paks 目录> <usmap 或 -> <oo2core_9_win64.dll> <输出目录> <命令> [参数…]
  list <正则>            列包路径
  json <包>…             所有 export 的 JSON
  raw <包>…              原始 uasset / uexp / ubulk
  export <gltf|psk|其它> <包>…   导出网格、贴图、骨架、动画；gltf、psk 以外的值（项目写 ue 或 uemodel）都导出 UEFormat（.uemodel / .ueanim）
  skel <包>…             参考骨架、形变名、section 的精确 dump
  mappings <正则>        按名字列 usmap 里的结构（含属性）和枚举
```

- 包路径可以写 `/Game/...`，内部转成 `Pal/Content/...`。
- `PALX_EXTRA`（分号分隔的目录）额外挂载 pak 目录，例如同时读游戏和自己的 mod。
- 读自己的 pak 时把第一个参数指向 pak 所在目录（导出工具只读给定目录，不会自动加载 `~mods`）。
- 在 Git Bash 里直接运行时设 `MSYS_NO_PATHCONV=1`，否则 `/Game/...` 会被改写成 Windows 路径。
- `mappings` 用来对照游戏里的类型布局，例如确认 KawaiiPhysics 的版本（属性布局与 1.17.1 一致）、查 `EPalSkinType`。

## 2. PalModTools（UE 5.1 编辑器插件）

剑星 SBGraphLib 的 UE 5.1 移植（`UPalGraphLib`，BlueprintCallable，Python 里是 `unreal.PalGraphLib`）。依赖 UnrealEd、BlueprintGraph、
AnimGraph、AnimGraphRuntime、Kismet。

| 函数 | 用途 |
| --- | --- |
| `GetGraph` / `ListGraphs` / `GetNodes` / `AddNode` / `RemoveNode` / `GetPins` / `Connect` / `SetPinDefault` / `Reconstruct` | 动画图的增删改连 |
| `SetProperty` / `GetProperty` | 按 `Node.<字段>` 路径用导出文本读写节点属性（ImportText / ExportText） |
| `AddVariable`、`ImplementInterface`、`AddAnimLayerGraph`、`Compile`、`ExportGraph` | 蓝图结构：实现动画层接口、建层图、编译（返回含错误数的字符串） |
| `GetRefPose` / `GetSkeletonRefPose` | 网格 / 骨架的参考姿势（`名字|父|平移|四元数`） |
| `SetMeshSkeleton`、`SetMeshSocket`、`GetMorphTargets` | 网格的骨架、插槽、形变列表 |

坑：

- 给动画层接口加层图时，`FBlueprintEditorUtils::AddFunctionGraph` 触发断言；要用 `CreateNewGraph(UAnimationGraph, UAnimationGraphSchema)`
  + `AddDomainSpecificGraph`。
- `ImplementInterface` 用 `FBlueprintEditorUtils::ImplementNewInterface(BP, Interface->GetClassPathName())`（UE 5.1 的签名）。
- 插件用 UnrealBuildTool 编（`Development Win64 -TargetType=Editor`）；KawaiiPhysics 源码插件同时编。

## 3. 命令行跑 UE

- 编辑器 Python：`UnrealEditor-Cmd Pal.uproject -run=pythonscript -script="<脚本> <参数>" -unattended -nosplash -nop4 -abslog=<日志>`。
  脚本用 `[KARIN]` 前缀打日志，包装脚本只筛这些行和错误。路径一律用正斜杠。
- Cook：`-run=cook -targetplatform=Windows -unversioned -iterate`。
- UE 5.1 Python 的坑：
  - 导入选项要用 `set_editor_property`，直接给属性赋值会失败；
  - 第一次导入骨骼网格时新建的骨架不在 `imported_object_paths` 里，用 `list_assets` 在目标目录里找；
  - PNG 导入返回 None：给 `AssetImportTask` 显式设 `TextureFactory`；
  - `MaterialEditingLibrary.set_material_instance_texture_parameter_value` 成功时也返回 False，用 get 读回核对；
  - 重新导入网格前先删旧资产，否则旧的材质槽、骨留在网格里。

## 4. 远程测试机

- 命令和文件走 SSH / scp；桌面输入和截图走测试机交互会话里的 agent（SSH 会话在 session 0，从 SSH 启动的游戏不会出现在屏幕上）。
  游戏从桌面用 `steam://rungameid/1623730` 启动。
- 游戏里移动角色前先把游戏窗口切到前台，再按住移动键（模拟输入游戏能收到）。
- 表情、物理的证据用 Steam 截图键 F12 连拍（每 120 ms 一次），而不是单张截图；拍完删掉自己的截图和缩略图，不动用户的。
- 测试机重启后 Steam 可能报错、分辨率变低导致对话框按钮在屏幕外：结束 Steam 进程后重新启动。
- UE 用 Epic 启动器装在测试机上（需要用户在 UAC 上点同意）；启动器的下拉框在两批操作之间会自己关上，展开、悬停、点击要在同一批里做。
- 测试机可能被用户或别的会话占用：开始成批桌面操作前提醒用户别动鼠标键盘；收尾时关掉自己开的窗口。
