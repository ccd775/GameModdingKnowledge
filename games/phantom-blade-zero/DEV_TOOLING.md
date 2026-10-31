# 开发工具

## 1. PbzExport（CUE4Parse 命令行）

源码在便携包 `pbzexport/`（从幻兽帕鲁的 PalExport 派生；CUE4Parse / CUE4Parse-Conversion 1.2.2.202610，net10.0 win-x64）。

```text
PbzExport <paks 目录> <usmap 或 -> <Oodle DLL> <输出目录> <命令> [参数...]
  list <正则> | json <包>... | export uemodel|gltf|psk <包>... | skel <包>... | raw <包>... | morphs <包>...
环境变量：PBZX_AES（十六进制密钥）、PBZX_GAME（默认 GAME_UE5_7）、PBZX_EXTRA（额外的 pak 目录，; 分隔，先于游戏读，用来读回 mod 容器）、
PBZX_SCRIPT=1（把蓝图字节码读进 json）
```

`tools/pbzx_run.ps1` 包了一层：从工作根的 `tools\` 取 exe、usmap、Oodle DLL 和 AES 文本。`skel` 输出的 `.skel.json` 是 Blender 构建器的输入；
`morphs` 读 cook 后的 GPU 形变数据（每个形变的增量数、平均 / 最大位置与法线增量）。

## 2. 反射信息：objscan、Dumper-7 补丁、usmap_fix

- `objscan/`（C#）：`objscan <pid|exe 名>`。在主模块的可写节里找指针 P，使 P（固定数组）或 *P（第一块）里是连续下标的 FUObjectItem，且
  Object->(int32 @ k) == 下标。打印命中的地址、步长、Object 在 item 里的偏移、InternalIndex 在 UObject 里的偏移和周围的 dword（用来读 Num / Max）。
- Dumper-7 的补丁（源码不随包；在 Dumper-7 上改这三处）：按 objscan 的结果写死 FChunkedFixedUObjectArray 的布局（[技术合同](TECHNICAL_CONTRACTS.md) §3）、
  ini 放在 exe 旁边、跳过 `InitTextOffsets`（它调用 ProcessEvent 让游戏崩溃），先写 mappings 再做别的。注入方式：UE4SS 的 `dwmapi.dll` 代理加载
  `ue4ss\UE4SS.dll`（这里换成 Dumper-7 的构建）。用完把代理改名禁用（项目里是 `dwmapi.dll.off`）。
- `scripts/usmap_fix.py <in> <out> [--dump 正则]`：去掉每个结构体里的继承属性，重排下标，写未压缩的 usmap（版本不变）。输入是 zstd 压缩时需要 `zstandard`。

## 3. UE 5.7 内容工程与 PBZModTools

- 工程 `ue/ProjectPBZ`：`ProjectPBZ.uproject`、`Config/DefaultEngine.ini`、`DefaultGame.ini`，空插件 `Plugins/HuaShira`（只有 `.uplugin`，让资产路径是 `/HuaShira/...`）。
  把 `ue/PBZModTools` 复制到 `Plugins/PBZModTools`，用 `tools/build_plugin.ps1` 编译。
- 插件函数（`PBZModToolsLibrary.h`）：

| 函数 | 用途 |
| --- | --- |
| `CreatePhysicsAsset` / `BuildPhysicsAsset` | 从 JSON 建物理资产（布料碰撞体） |
| `SetMorphCurveMetaData` / `GetMorphTargetNames` / `DumpMorphTargets` / `CopyMorphTangents` | 形变的曲线元数据、名单、增量统计；`CopyMorphTangents` 的改动到不了 cook（GPU 形变从源重建） |
| `DumpRefSkeleton` / `DumpSections` | 参考骨架与 section 核对 |
| `SetPostProcessAnimBlueprint` / `SetMeshPhysicsAsset` | 网格的后处理动画蓝图与物理资产 |
| `ClearMaterialInstanceParameters` / `SetMaterial{Texture,Scalar,Vector}Parameter` / `DumpMaterialInstanceParameters` | 分层材质的按关联 / 索引覆盖 |
| `CreateClothFromSlot` | 从材质槽建布料：掩码（径向、锚点、backstop、`sim_slot` 外壳）、配置、绑定、法线替换 |
| `SetClothSolver` / `RemoveAllClothing` / `SetSectionCastShadow` | 求解器迭代与子步、清布料、段的投影 |
| `SetCurveSequence` | 写只有曲线的动画序列（眨眼、FaceShow） |
| `BuildCopyPoseOverlayAnimBP` / `TestCopyPoseAnim` | 重建 CopyPose 动画蓝图（叠加、槽、门控）并在编辑器世界里自测 |

- 无界面运行：`tools/ue_run.ps1 <脚本> <日志名> [参数]`（`UnrealEditor-Cmd -run=pythonscript -script="..."`）。脚本路径要用正斜杠：
  这个 commandlet 的 `-script=` 会吃掉 `\u` / `\U`。日志里出现 `LogExit: Exiting` 才算跑完；每个脚本最后写自己的完成标记。
- 无界面的编辑器在资产注册表扫描完之前就开始跑脚本：先 `search_all_assets(True)`。

## 4. 远程构建机与实机

- 项目里 Blender 构建在一台 Windows 机，UE、游戏在另一台（只能经第一台 SSH 过去）。脚本都是无界面的；通过 SSH 起的进程在 session 0，
  看不到桌面——需要在用户桌面会话里做的事（远程连接的重连）用一次性的交互式计划任务（`/IT`）做，用完删掉。
- 长任务（UE 全流程约 2.5 分钟）用 `Invoke-CimMethod Win32_Process Create` 脱离 SSH 会话启动，再轮询进度文件；SSH 断了任务也不停。
- 游戏由用户启动和游玩，agent 只在游戏关闭时安装文件；实机结论来自用户反馈。
