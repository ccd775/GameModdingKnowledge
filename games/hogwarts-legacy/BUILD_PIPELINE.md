# 构建流水线

命令和参数见 [便携工具包](../../portable-kits/hogwarts-legacy/README.md)；这里写每一步做什么、为什么。

## 1. 工具与环境

| 工具 | 版本 | 用途 |
| --- | --- | --- |
| Blender | 4.0.2，后台运行 | `fit.py` 拟合与部件构建、`export_fbx.py` 导出、预览渲染 |
| Unreal Engine | 4.27.2（Epic 启动器版）+ PythonScriptPlugin + EditorScriptingUtilities | 占位工程 `Phoenix`：导入、材质槽、动画蓝图生成、cook |
| HLKTools 编辑器插件（C++） | 本项目源码；VS2022（MSVC 14.44）编译 | 从 JSON 生成「CopyPoseFromMesh → AnimDynamics」动画蓝图 |
| HLMeshProbe（C#，CUE4Parse） | CUE4Parse 提交 `2b8901c3ee9818558ad33e2496a58d50b82e99db` + 本项目补丁，.NET 10 | 读 HL / 4.27 包、更新后格式补丁与参考姿势写回、JSON / 形变 dump |
| retoc | 0.1.5 | IoStore ↔ legacy |
| Python | 3.12+（numpy） | 物理参数、数据资产补丁、材质实例克隆、离线调参 |

环境注意：

- UBT 在只装了 VS2022 的机器上报「Could not find NetFxSDK install dir」：在 `HKCU\SOFTWARE\Microsoft\Microsoft SDKs\NETFXSDK\4.8` 建
  `KitsInstallationFolder` 指向一个空目录即可编译，编完删掉。
- HLMeshProbe：`CUE4PARSE_SKIP_NATIVE=1 dotnet build -c Release`（跳过 CUE4Parse-Natives）；.NET 10 在不完全支持 CET 的 Windows 上崩溃，
  工程里加 `<CETCompat>false</CETCompat>`。
- 在 Git Bash 里调用时设 `MSYS_NO_PATHCONV=1`，否则 `/Game/...` 参数被改成 Git 安装目录下的路径。
- 原项目把工作目录 `subst` 成一个盘符，所有配置用该盘符的绝对路径；便携包改成相对路径和参数。

## 2. 提取与 dump

1. `retoc to-legacy` 按准确的资产名取：目标网格、`Biped_Skeleton`、女性网格（女性参考姿势）、目标材质实例、装备外观、角色部件数据资产、
   发型数据资产、动画蓝图、面部姿势资产、`DT_AvatarPresets`。
2. `HLMeshProbe json hl <目录> <过滤>` 出属性 JSON；`dump` 出几何 / 骨 / 权重 / 形变的紧凑 JSON；`probe` 看 section 布局；`mat` 看材质实例尾部哈希。
3. 由 dump 得到：游戏骨架 JSON（男 `Biped_Skeleton`，女为把女性网格参考姿势覆盖上去的版本）、参考网格（用于权重分配）、头部形变表。

## 3. Blender 拟合（`fit.py`）

输入：源模型 FBX、游戏骨架 JSON、参考网格 JSON、参数和部件表（`fit_<m|f>.json`）、形变映射（`face_map.json`）。
输出（工作目录）：`fit.blend`、`skel_ext.json`（游戏骨 + 动态骨的局部变换）、`dyn_chains.json`、各部件 FBX、`*_pos_ue.npy`、`fit_log.txt`。
细节见 [角色拟合](CHARACTER_FIT.md)。

## 4. 物理参数（`dyn_params.py`）

`dyn_chains.json` + `skel_ext.json` + `dyn.json`（按类别的目标手感）→ `dyn_nodes.json`（每个部件一组 AnimDynamics 节点设置）。
只改手感时从这一步开始（§10）。模型见 [物理](PHYSICS.md) §3。

## 5. 导出（`export_fbx.py`）

从 `fit.blend` 导出 `KarinBody`、`KarinHair`、`KarinHead`、`Empty`（髋部一个极小三角形）、`PhysProxy`、`Skeleton`（只有骨架的代理）。
骨架对象改名 `Armature`；FBX 用米、不做单位换算（UE 导入时换成厘米），`-Y` 向前、`Z` 向上，不加叶子骨。

**骨的取舍（v1.1 起）**：会变形到动态骨的网格（身体、头发）和 `Skeleton.fbx` 带全部骨；其余网格（头、空模型、`PhysProxy`）去掉游戏骨架里没有的骨。
它们引用游戏的 `Biped_Skeleton`，带着多余的骨会让游戏崩溃（[排障手册](TROUBLESHOOTING.md) §1）。导出日志每个网格一行 `EXPORTED <名字> all bones` 或
`game bones only, 95 removed`。

## 6. UE 导入（`ue_import.py`，Python commandlet）

按 `ue_build_<m|f>.json`：

1. 占位：`Biped_Skeleton`（第一次从 `Skeleton.fbx` 导入后改名）、`Biped_PhysicsAsset` / `SK_Biped_Physics_Shadows`（复制引擎教程里的物理资产即可）、
   `MM_Prop` 母材质和各宿主材质实例。都在游戏路径上，**不进包**。
2. 贴图（可选，`TEXTURES=1`）：D → BC7 + sRGB，N → 法线贴图，MRO → Masks 线性；LOD 组用角色组。
3. Karin 骨架：删掉旧的 Karin 目录和绑在它上面的网格，从 `Skeleton.fbx` 导入后改名为 `SK_Karin_<G>_Skeleton`。
4. 网格：每个目标路径**先删除再导入**（reimport 会沿用旧的导入设置）；身体 / 头发绑 Karin 骨架，头和空模型绑占位 `Biped_Skeleton`；
   头部打开形变导入。材质槽按名字指向宿主材质实例（新建列表整体写回，结构体副本问题）；头部挂物理资产；包围盒各向外扩 20。
   其余路径（`_Master_A/_B`、另一个脸型 / 发型预设）由第一个复制。
5. 动画蓝图：`unreal.HLKToolsLibrary.create_dynamics_anim_blueprint(路径, Karin骨架, CopyPose JSON, 节点 JSON)`，
   生成 `CopyPoseFromMesh（bUseAttachedParent、bCopyCurves）→ 局部转组件空间 → N 个 AnimDynamics → 组件转局部空间 → 输出`，编译保存。
   插件里 `UAnimGraphNode_AnimDynamics` 没有导出：按类名 `FindObject` 后用通用的 `NewNodeOfClass` 建节点，`Node` 结构体用反射 + JSON 填。

## 7. cook

`UE4Editor-Cmd <工程> -run=cook -targetplatform=WindowsNoEditor -CookAll`；日志里 `Error:` 计数必须为 0。

## 8. 组装（legacy 树）

1. 从 cook 输出复制 `RiggedObjects/Characters/Human` 下的文件，按性别过滤（女：路径含 `_F/`、`/AVA_YF_`、`/Hair_F/`），不复制占位材质实例。
2. 复制改好的装备外观 `DA_GA_Outfit_072_<G>`（袜子 / 鞋指向空裤子部件）。
3. `HLMeshProbe patch <legacy> <legacy_hl> skel_ext.json`：每个网格插入 section 字段、按骨名写回参考姿势，再按 HL 规则读回校验（`verify ok (N meshes)`）。
4. `da_animclass.py`：给上衣和发型的部件数据资产注入动画类（[技术合同](TECHNICAL_CONTRACTS.md) §6）；发型数据资产事先由 `hair_override_patch.py` 改过覆盖网格。
5. 只做女性版时：`mi_clone.py` 把男版材质实例克隆到 `_F` 路径（[技术合同](TECHNICAL_CONTRACTS.md) §3）。

## 9. 打包与安装

`retoc to-zen --version UE4_27 <legacy_hl> zzz_KarinDarkArts_<MF|F>_P.utoc` → `retoc verify` → 三件套。游戏关闭时复制进 `~mods`，原来的包先备份；
发行包结构见 [验证与发布](VALIDATION_AND_RELEASE.md) §3。

## 10. 快速路线

- 只改物理手感：`params → import → cook → assemble → pack`，不重跑 Blender（cook 是增量的，一轮约 1 分钟）。
- 只改材质分配：`ue_fixmat.py` 重新挂槽，不重新导入。
- 只改导出（如骨的取舍）：`export → import → cook → assemble → pack`（v1.1 实测 54 秒）。

## 11. 远程测试机

原项目在另一台机器上跑游戏：命令和文件走 SSH，界面操作走用户会话里的计划任务。经验：

- 端口映射的带宽很小，单次传输超过约 2–3 MB 会卡住隧道；包先 xz（ucas 约压到 1/5），用限速的单连接流式上传，传完核对 SHA-256。
- 从 SSH 启动的游戏在 session 0，看不见；启动游戏走桌面输入（`steam://rungameid/990080`）。
- 隐藏的 PowerShell 会抢前台，游戏收不到模拟输入；在同一进程里 `AttachThreadInput + SetForegroundWindow` 再 `SendInput`，HL 的菜单接受绝对坐标点击和按键。
- 截图在远端缩成 JPEG 再取回；用户可能同时在看画面，镜头自己动了就停止输入。
