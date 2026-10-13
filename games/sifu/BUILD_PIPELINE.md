# 构建流水线

源模型 → Blender（本地）→ 贴图 → UE 4.26 内容工程（可以在另一台装 UE 的机器上）→ cook / pak → CUE4Parse 读回。
全部脚本化、可重跑；分步命令、环境变量（`SIFU_MODELS_DIR`、`SIFU_BASE_SKEL`、`SIFU_WORK_ROOT`、`SIFU_UE_ROOT`、`SIFU_GAME_DIR`、`SIFU_AES` 等）见 [便携工具包](../../portable-kits/sifu/README.md)。

## 0. 提取参照（一次）

用 SifuExport（CUE4Parse，[开发工具](DEV_TOOLING.md) §1）从游戏 pak 取：

| 产物 | 命令 | 用途 |
| --- | --- | --- |
| W 网格骨架 JSON（参考姿势、骨序、section） | `skel Sifu/Content/Characters/MainChar/W/Meshes/SK_W_MainChar_01` | 构建的目标骨架（`w_skel`） |
| `Base_skeleton` JSON | `skel Sifu/Content/Characters/Skeleton/Base_skeleton` | 备用骨的父子关系与参考姿势（`base_skel`）；编辑器骨架重建 |
| W 网格 glTF | `export gltf <同上>` | 权重分布、面部权重、顶点色、头宽（`w_glb`） |
| 面部姿势资产 JSON | `json .../MC_woman_facial_PoseAsset` | 眨眼 / 口型拟合（`pose_asset`） |
| 动画姿势 | `anim <动画包> <帧号…>` | 离线姿势预览与裙摆替身（帧号必须小于 numFrames，否则抛异常） |
| 材质实例、动画蓝图、物理资产 JSON | `json <包>` | 参数名、静态开关、`PA_W_MainChar` 的形状 |

## 1. Blender 构建（`build_karin.py`）

`blender -b --factory-startup --python build_karin.py -- <build_cfg.json>`。build_cfg 的键：`w_skel`、`w_glb`、`pose_asset`、
`scale`（1.4）、`w_face_width_cm`（16.95）、`face_rig`、`profile`、`base_skel`、输出 `out_blend` / `out_fbx` / `out_cloth` /
`out_report`；Karin_Original 另有 `karin_vrm`。阶段：

1. **载入与归一化**（`source_prep.load`）：按 profile 载入源模型（VRM / FBX / .blend 对象），烘焙形状键组合，应用对象变换，
   骨名改成 VRM 标准名，网格按角色改名（脸 `Body`、皮肤 `body_2`），材质映射到 profile 的槽，删去在图集里完全透明的面。
2. **重摆姿势**：Karin 用自己的蒙皮摆进 W 的 A 姿势（逐链对齐骨方向，手掌按 W 转），悬挂件回正，再把姿势应用成静止姿势。
3. **关节放置**：人形骨取 Karin 的关节（统一缩放），骨盆、脊椎分段、锁骨、`neck_02`、扭转骨按 W 的相对位置放。
4. **面部**（`face_stage`）：W 面部骨按 TPS 变形放到 Karin 脸上，迁移面部权重，拟合眨眼枢轴和嘴（[角色拟合](CHARACTER_FIT.md) §4）。
5. **权重**：人形权重映射到 Sifu 变形骨，四肢按 W 的帽函数分到扭转骨（主骨不带权重），胸 / 颈拆分；
   非人形骨按前缀或最近的人形祖先折叠。
6. **布料与碰撞**（`cloth_stage`）：模拟件分到自己的槽，生成裙摆代理网格，拟合碰撞胶囊，复制 W 顶点色。
7. **骨链**（`dyn_stage` + `dyn_tuning`）：在备用骨上搭链、改权重、生成 `PA_Karin_Dynamics` 与 RigidBody 节点的 JSON（[物理](PHYSICS.md)）。
8. **躯干权重**（`torso_weights`）：把 W 的骨盆 / 脊椎权重分布按高度和扇区套到皮肤、上衣、内衣和裙腰上。
9. 输出 FBX（骨架对象名 `Armature`）、`cloth.json`（布料、碰撞、骨链）、`build_report.json`、`.blend`。

`build_report.json` 要看：未映射的顶点组（应为空）、每条链的顶点数与关节位置（cm）、槽数（≤ 11）、面部拟合误差。

## 2. 离线检查

- `preview_model.py`：带贴图的全身联系表（静止 + 跑步第 3 帧 + 前踢第 6 帧，多角度）。
- `pose_preview.py`：把构建结果摆进解出来的游戏动画姿势（正 / 侧 / 3/4，腰部前后特写）。
- `preview_face.py`：面部姿势（眨眼、口型、疼痛 / 发力）。
- `skirt_sim.py`：裙摆的时间步进替身（[物理](PHYSICS.md) §4）。

## 3. 贴图

- `bake_ao.py`：从构建结果按图集页（或按槽）烘焙 AO。
- `make_textures.py <profile> <work_dir> <远端 work_dir>`：每个槽一张 2048 BaseColor（`_C` / `_CS`）和一张 ComboMap（`_S_<kind>`），
  外加平法线 `T_Karin_Flat_N` 和全黑 `T_Karin_Black`；写出 UE 端要用的 `ue_build.json`（贴图、材质、父级、`asset_dir`）。
  通道定义见 [材质与贴图](MATERIALS_AND_TEXTURES.md)。

## 4. UE 内容工程（`ue_build_mesh.py`）

工程：UE 4.26.2 空内容工程，名字 `Sifu`，插件 PythonScriptPlugin、EditorScriptingUtilities、SifuModTools；
`bShareMaterialShaderCode=False`、不用 IoStore。用命令行 commandlet 跑（`ue_run.ps1`，[开发工具](DEV_TOOLING.md) §3）：

1. 在游戏路径上建占位：W 三个材质实例与它们的母材质、`PA_W_MainChar`、`PA_M_MainChar_ShadowCapsules`（`Base_skeleton` 事先导入）。
2. 导入贴图，建 MIC（父级 = 对应的 W 材质实例），放进 `/Game/Characters/MainChar/W/<asset_dir>/`。
3. 以 `Base_skeleton` 导入 FBX 到 `W/Meshes/SK_W_MainChar_01`；**新建材质列表整体写回**并断言；
   PhysicsAsset / ShadowPhysicsAsset 指向游戏的两个物理资产。
4. 布料：`CreateClothProxy`（代理槽 → 渲染槽，顶点色给最大距离与 backstop），碰撞用 `PA_Karin_Cloth`。
5. 骨链：`BuildPhysicsAsset` 建 `PA_Karin_Dynamics`，`SetupRigidBodyPostProcess` 重建 `ABP_Karin_PostProcess` 的动画图并写入节点参数，
   `SetPostProcessAnimBlueprint` 挂到网格上。
6. 写 `ue_build_out.json`（每步的日志）。commandlet 日志里看不到 Python 的输出，以这个文件为准。

只调物理时：`python dyn_tuning.py cloth.json` 就地重算参数（不用重跑 Blender），上传后用 `physics_only: true` 的 build json，
只重建 `PA_Karin_Dynamics` 和动画蓝图。

## 5. cook 与 pak（`cook_pak.ps1 <PakName> [-AssetDir <目录>]`）

1. `UE4Editor-Cmd <工程> -run=cook -targetplatform=WindowsNoEditor`。
2. 从 `Saved/Cooked/WindowsNoEditor/Sifu/Content` 里只挑 `Characters/MainChar/W/Meshes/SK_W_MainChar_01.*` 和
   `Characters/MainChar/W/<AssetDir>/**`（占位全部排除），写响应文件，挂载路径 `../../../Sifu/Content/<相对路径>`。
3. `UnrealPak <pak> -create=<响应文件> -compress`，再把游戏的 `pakchunk0-WindowsNoEditor.sig` 复制成同名 `.sig`。

## 6. 读回检查

用 SifuExport 只挂载输出目录（不给 AES）读烘焙后的网格：每个 `MaterialSlotName` 的 `Material.ObjectPath` 都在
`/<asset_dir>/` 下，`PostProcessAnimBlueprint` 也在。另核对文件数和 pak MD5（本地与构建机两边）。

## 7. 发行

`package_release.py <profile> <version> <date>`：`<pak名>/`（pak、sig、安装说明.txt）和 `<pak名>_v<version>.zip`，
说明里写替换范围、互斥的同类 mod、MD5（[验证与发布](VALIDATION_AND_RELEASE.md) §3）。

## 8. profile（多个源模型）

`profiles.py` 每个模型一个字典，`activate(name)` 深拷贝成当前配置。`karin_original` 是参照 profile，保存的是 v6 发行时的常量，
重构后它的构建与 v6 逐字节一致（`cloth.json` 与 blend 网格数据）。字段：

| 字段 | 含义 |
| --- | --- |
| `name` / `src` / `pak` / `asset_dir` | 名字、源文件、pak 名、UE 资产目录（每个模型独立，pak 之间不共享资产路径） |
| `head_m` | 缩放目标：头部关节高度（m，取 Karin_Original 的 1.0508）；所有模型都缩放到同一头部关节高度（×140 = 147.1 cm） |
| `face_mesh` / `skin_mesh` / `thigh_meshes` / `alpha_mat` | 角色网格名、算大腿碰撞半径的网格、表情叠加层材质 |
| `mesh_renames` / `drop_meshes` / `mesh_materials` | 源网格改名、丢弃的网格（如道具）、按网格覆盖材质映射 |
| `slots` / `materials` / `tex_dir` / `tex_files` / `cull_alpha` | UE 槽名、源材质 → 槽、图集贴图、透明剔除阈值 |
| `fold_prefix` / `fold_ancestor` | 非人形骨的权重折叠规则 |
| `hang` | T→A 重摆后要回正的悬挂骨 |
| `torso_targets` / `torso_exclude` | 套用 W 躯干分布的网格 |
| `cloth_chains` / `skirt` | NvCloth 件（`"default"` = 模块常量；裙摆可选） |
| `dyn` | 骨链规格（[物理](PHYSICS.md) §3） |

加一个新模型：先盘点源模型（骨名、网格、材质、形状键、图集页），写 profile，构建，看 `build_report.json`
有没有未映射的组和不合理的链几何，再看预览。
