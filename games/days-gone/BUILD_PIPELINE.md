# 构建流水线

确切命令、参数和环境变量见 [便携工具包](../../portable-kits/days-gone/README.md)；这里讲每一步做什么、产物是什么、为什么这样分。
项目在本机跑 Blender 和 Python，在装 UE 4.11.2 的测试机上跑 DgExport、编辑器导入、cook 和游戏。

## 0. 提取参照数据（DgExport，测试机）

| 资产 | 命令 | 用途 |
| --- | --- | --- |
| `Characters/Deacon/deacon_master_Skeleton` | `skel`（含每个 LOD 的 required bones） | 骨名、父子、重定向模式、参考姿势；Blender 和所有 Python 工具读这个 JSON |
| `Characters/Deacon/parts/head/deacon_head_standard` | `export uemodel` | Blender 里的迪肯头（面部权重来源）和身体骨位 |
| `Characters/Deacon/looks/*`（66 个） | `raw` | `patch_looks.py` 的输入 |
| `parts/head/mi_deacon_head`、`mi_deacon_eyelash_hair` | `raw` | Karin 材质实例的模板 |
| `Animation/Deacon/Deacon_VimBlueprint` | `raw` | `abp_springs.py` 的输入 |
| `facial/FaceMoods/*`、`misc/dcn_ref_pose`、`vo/lipsync/dcn_visemes-*` | `raw` | 面部模拟、眼睑标定、口型求解（用 `anim_pertrack.py` 解码） |
| `deacon_master_Skeleton`（原始包） | `raw` | `skel_retarget.py` 把 `face_*` 改成 `AnimationRelative` |

## 1. Blender 构建（本机，Blender 4.2 + UEFormat 导入插件）

按顺序，每一步读上一步的 `build.blend`，输出新的 `build.blend` 和 FBX：

1. `build_body.py`：Karin 的 VRM（BlenderSafe FBX）→ 迪肯骨架。`--prop karin`（默认）：骨段长度按 Karin 缩放后的比例重设、朝向和关节角保持迪肯的；`--scale` 1.30（默认），
   头不下移（`--head-drop 0`；1.40 / 5 cm 是 t0 试验 `--prop deacon` 时的值）。权重重映射到迪肯的骨，
   VRM spring 链保留为网格专用骨 `KO_*`（variant B），脸保留 237 个形状键（后面的面部步骤要用）。
   首次另跑 `export_dummy_skeleton.py`，给编辑器做一个只有迪肯骨架的占位 FBX。
2. `face_rig.py`：迪肯头部网格挪到 Karin 的 Head 上，用眼、鼻尖、嘴、下巴 + 远处锚点做薄板 RBF 变形，Karin 脸皮取变形后迪肯皮肤的权重；
   `face_*` 关节按同一变形挪到 Karin 脸上；删除藏在皮肤后面的 VRM 表情道具；`--check` 渲染张嘴测试图。
3. `blink_rig.py <上一版 cook 出的网格>`：每只眼 5 根 `KB_Blink_*` 眼睑骨（各挂在一根 `KB_Amp_*` 放大骨下），权重按 VRM `blink_L/R`
   形状键拟合；输出 `blink_rig.json`（骨、半轴、行程）。
4. `mouth_rig.py <上一版 cook 出的网格> <输出> <mouth_map.json>`：按口型求解下半张脸的权重（[面部](FACE_AND_LIPSYNC.md) §3）。
5. 辅助：`dump_loop_normals.py`（VRM 原法线 → npz，给 `--normals`）、`skirt_body_shrink.py`（裙下身体内收 → npz，给 `--positions`）、
   `fit_colliders.py`（AnimDynamics 平面限制的参考尺寸）、`render_preview.py` / `shape_sheet.py` / `viseme_sim.py`（预览与模拟）。

眼睑和口型脚本要读 cook 后网格的参考骨架拿 Karin 的关节位置；面部关节位置由 `face_rig.py` 决定，之后不变，所以用上一版 cook 的网格即可。

## 2. UE 4.11.2 导入与 cook（测试机）

- 内容工程名必须是 `BendGame`（cook 出来的路径才是 `BendGame/Content/...`）。占位：`/Game/Characters/Deacon/deacon_master`（+ Skeleton，
  来自占位 FBX）；Karin 网格导入到 `/Game/Characters/Deacon/parts/head/deacon_head_standard`；贴图 `/Game/Karin/Materials/Karin_*`。
- 每次导入前把编辑器里的 `deacon_head_standard*.uasset` 备份到工作目录的 `backup\tNN_assets`。
- 导入流程（GUI）：内容浏览器「导入」→ 选 FBX →「覆盖已有资源」点「是」→ FBX 导入选项（不导动画、不导材质 / 贴图）点「导入」（约 75 s）
  →「保存所有」→「保存选中项」→ 关编辑器。法线选项在远程桌面上改不动，所以法线在 cook 之后补。
- 编辑器启动时会顺带拉起 SteamVR，结束后一起关掉。**编辑器开着时不要启动游戏**。
- cook：`UE4Editor-Cmd.exe <BendGame.uproject> -run=cook -targetplatform=WindowsNoEditor -cookall -iterate -unattended`
  （`tools/cook.ps1`），日志里找 `Success - 0 error(s)`。

## 3. cook 之后的补丁（本机，Python + numpy）

1. `blink_amp.py <cook 出的网格> <输出> blink_rig.json lid_calib.json`：改放大骨的参考旋转 / 缩放和眼睑骨的静止平移（所有序列化副本），
   并验证眼睑骨的组件空间静止位置没变。`lid_calib.json` 由 `lid_calib.py` 从迪肯的中性情绪动画算出（每个游戏 build 算一次）。
2. `abp_springs.py <游戏 Deacon_VimBlueprint> <网格> springs.json <输出>`：插入 CopyBone（眼睑）和 AnimDynamics（弹簧骨）节点，
   打印每个节点的骨、长度、刚度、限制和平面。只改物理参数时只重跑这一步和打包，不用进编辑器（t31）。
3. `skel_retarget.py`：游戏骨架包里的 `face_*` 改成 `AnimationRelative`（每个游戏 build 一次）。
4. `make_pak.py <cooked 内容根> <out.pak> --normals … --positions … --skeleton … --extra Animation/Deacon/Deacon_VimBlueprint=<文件>`：
   网格骨架导入改指游戏骨架、根骨姿势、材质实例（`retarget_inplace.py`）、66 个 look、法线 / 位置补丁、pak v3。报告里看
   `mesh_normals.unmatched = 0`、`mesh_positions.moves_matched`。在 Git Bash 里传 `--extra` 不要带开头的 `/Game/`（会被改写成路径）。

## 4. 安装与实机（测试机）

- 游戏和编辑器都关着时，`tools/install_pak.ps1` 校验 SHA-256 后放进 `~mods`，旧包挪到 `disabled_mods`。
- 从用户桌面会话启动游戏（`steam://rungameid/1259420`），标题按任意键 → 主菜单「繼續」读档。实机检查流程见 [验证与发布](VALIDATION_AND_RELEASE.md) §2。

## 5. 只改一部分时重跑哪些步

| 改动 | 重跑 |
| --- | --- |
| 弹簧参数（`springs.json`） | `abp_springs.py` → `make_pak.py` |
| 口型映射 / 求解参数 | `mouth_rig.py` → 导入 / cook → `blink_amp.py` → `make_pak.py`（动画蓝图可沿用） |
| 眼睑形状 | `blink_rig.py` → 导入 / cook → `blink_amp.py` → `abp_springs.py`（CopyBone 的源 / 目标没变时可沿用）→ `make_pak.py` |
| 只改材质 / 贴图引用 | `make_pak.py` |
