# 战神：诸神黄昏便携包

先读 [游戏知识](../../games/god-of-war-ragnarok/README.md) 和 [构建流程](../../games/god-of-war-ragnarok/BUILD_PIPELINE.md)。

这是 Karin_Original 替换奎托斯（`r_heroa00.wad`）和同伴芙蕾雅（`r_freyavalkyrie00.wad`）时实际使用的脚本。

- **Python 版本：** 需要 Python 3.12 或更高，因为钉住的 numpy 2.5 和 scipy 1.18 不支持更早的版本。
- **游戏目录：** 用 `--game` 指定，或者设环境变量 `GOWR_GAME`。它是含 `exec\` 和 `libSceAgcTextureTool.dll` 的那个文件夹。脚本只读它，不写。
- **贴图只能在 Windows 上做：** 贴图包要调用游戏自带的 `libSceAgcTextureTool.dll`。DLL 在第一次用到时才加载，所以其他脚本在任何系统上都能导入。
- **Blender：** 拟合、减面和骨骼表要用 Blender，本项目用的是 5.0.1。这三个脚本放在 `scripts/blender/`。
- **运行位置：** 以下命令都从交接包根目录执行。

```powershell
python -m pip install -r requirements.txt -r portable-kits/god-of-war-ragnarok/requirements.txt
$Kit = "portable-kits/god-of-war-ragnarok/scripts"
$env:GOWR_GAME = "<Steam 库>\steamapps\common\God of War Ragnarok"
$Blender = "<Blender 5.0.1 目录>\blender.exe"
$Ref = "../MyMod/Ref"          # 源模型、自己备份的原版 wad、奎托斯底板 wad
$W = "../MyMod/Work"

# 0. 源模型修正（可选）：把 body_2 的形态键 kisekae_Knee 烘焙进 FBX 和 VRM，写成新文件
python -B $Kit/bake_knee.py $Ref/model.fbx $Ref/model.vrm $W/src/model.fbx $W/src/model.vrm

# 1. 贴图源和源模型骨骼表
python -B $Kit/extract_vrm_textures.py $W/src/model.vrm $W/tex_src
& $Blender --background --factory-startup --python $Kit/blender/dump_bones.py -- $W/src/model.fbx $W/karin_bones.json

# 2. 目标骨架的角色表
python -B $Kit/rigspec.py --character kratos --wad $Ref/r_heroa00.wad --out $W/rigspec_kratos.json
python -B $Kit/rigspec.py --character valk --wad $Ref/r_freyavalkyrie00.wad --out $W/rigspec_valk.json

# 3. Blender：摆到绑定姿势并烘焙，再减出远景 LOD（这里是奎托斯；芙蕾雅见下面的"案例常量"）
& $Blender --background --factory-startup --python $Kit/blender/fit_karin.py -- $W/src/model.fbx $W/rigspec_kratos.json $W/fit 1.6
& $Blender --background --factory-startup --python $Kit/blender/decimate_levels.py -- $W/fit/karin_fitted.blend $W/fit_lods 0.9 0.75 0.6 0.5 0.4 0.3 0.22 0.16 0.12 0.08 0.06 0.04 0.03 0.025 0.02 0.015

# 4. 网格：写 wad 和补丁 lodpack，再逐顶点回读
$K = "--base-wad", "$Ref/r_heroa00.wad", "--fit", "$W/fit", "--fit-lods", "$W/fit_lods", "--karin-bones", "$W/karin_bones.json", "--rigspec", "$W/rigspec_kratos.json"
python -B $Kit/build_kratos_final.py @K --out ../MyMod/Output/kratos
python -B $Kit/verify_build.py kratos ../MyMod/Output/kratos @K
$V = "--base-wad", "$Ref/r_freyavalkyrie00.wad", "--fit", "$W/fit_valk", "--fit-lods", "$W/fit_valk_lods", "--karin-bones", "$W/karin_bones.json", "--rigspec", "$W/rigspec_valk.json"
python -B $Kit/build_valk_final.py @V --out ../MyMod/Output/valk
python -B $Kit/verify_build.py valk ../MyMod/Output/valk @V
python -B $Kit/knee_sim.py ../MyMod/Output/valk --base-wad $Ref/r_freyavalkyrie00.wad

# 5. 贴图包
python -B $Kit/build_textures.py --wad $Ref/r_heroa00.wad --tex-src $W/tex_src --out ../MyMod/Output/kratos/KarinOriginal.texpack
python -B $Kit/build_valk_textures.py --wad $Ref/r_freyavalkyrie00.wad --tex-src $W/tex_src --out ../MyMod/Output/valk/KarinOriginalFreya.texpack
```

`verify_build.py` 最后一行要是 `BAD 0`。安装方法（`exec\patch\`、`exec\boot-options.json` 的 `patch-lodpacks` / `patch-texpacks`）见 [验证与发布](../../games/god-of-war-ragnarok/VALIDATION_AND_RELEASE.md)。

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `build_kratos_final.py` | 奎托斯入口。Karin 写进网格组 230 的两个定义（各 LOD），其余全部隐藏；写出 `r_heroa00.wad`、`KarinOriginal.lodpack`（含 `.toc`）和 `mesh_report.json` |
| `build_valk_final.py` | 芙蕾雅入口。Karin 写进始终显示的皮肤组 36 / 14 / 13 和主发型组 27，其余全部隐藏；零块放在定义 280 的顶点区尾部 |
| `verify_build.py` | 逐顶点回读：位置、骨骼、权重、三角形；隐藏用的零块全零且不与任何槽位重叠；芙蕾雅还要求只用原版带蒙皮的骨骼。最后打印 `BAD <数量>` |
| `knee_sim.py` | 芙蕾雅专用。从构建结果解出皮肤和鞋袜网格，按原版骨架弯曲膝盖（0 到 90 度），统计穿出袜面的皮肤顶点 |
| `build_textures.py` | 奎托斯贴图包：拼 4096 图集，按贴图名决定每张贴图用图集还是纯色，压缩、tiling 后写 `.texpack`、`.toc` 和 `.plan.json` |
| `build_valk_textures.py` | 芙蕾雅贴图包：只替换 `freyavalkyrie00_` / `freya00_` 开头的贴图，规则沿用 `build_textures.py` |
| `rigspec.py` | 从 wad 里的骨架算出目标角色的人形骨角色表和绑定关节；左侧骨按 X 镜像查找，并列时可手工指定 |
| `extract_vrm_textures.py` | 把 VRM 里嵌入的图片导出为 PNG |
| `bake_knee.py` | 源模型修正：把 body_2 的形态键烘焙进 FBX 和 VRM 的基础网格，再把该形态键清零 |
| `gamedir.py` | 游戏目录的唯一设置处：`set_game()`、`game_root()`、`wad_dir()`；没设置时给出明确的报错 |
| `wad.py` | WAD（WTOC v2，可为 LZ4）读取；直接运行时列出全部条目并检查范围 |
| `mesh.py` / `mg.py` / `rig.py` | MESH 定义、MG 网格组、骨架的解析 |
| `decode.py` / `encode.py` | 顶点分量的解码和编码，含三种骨骼权重布局；容量计算和原地写入 |
| `geometry.py` | 把拟合结果组装成游戏坐标下的一套顶点和三角形，按骨骼角色映射权重，裙子混合大腿权重 |
| `charbuild.py` | 按容量为每个槽位挑选各部件的减面档位；放不下的副槽把部件交给主槽 |
| `build_inplace.py` | 原地写入：不改缓冲区大小，改过的缓冲区哈希加 1，隐藏定义指向零块；写单组多成员 lodpack |
| `build_mesh.py` | `root_buffer()` 从原版 `root.lodpack` 取缓冲区；`write_lodpack_single_group()` 写补丁 lodpack |
| `packs.py` | lodpack / texpack 的 `.toc` 读取 |
| `textures.py` / `gnf.py` / `agctex.py` | GNF 贴图条目和 texpack 的写入；BCn 编解码；通过游戏 DLL 做 tiling |
| `fbxbin.py` / `gltf_util.py` | 二进制 FBX（原样写回逐字节相同）和 GLB 的读写，供 `bake_knee.py` 使用 |
| `blender/fit_karin.py` | Blender 内运行：逐骨摆到目标绑定姿势，烘焙进网格，导出 npz 和 `summary.json`，另存 `karin_fitted.blend` |
| `blender/decimate_levels.py` | Blender 内运行：按给定比例减面，每档导出一个 `r<比例>` 目录 |
| `blender/dump_bones.py` | Blender 内运行：导出源模型的骨骼层级（`karin_bones.json`） |

## 输入与输出

- **游戏目录**（`--game` 或 `GOWR_GAME`）：
  - 网格那一步读 `exec\wad\pc_le\root.lodpack` 和它的 `.toc`；
  - 贴图那一步还读同目录的 `root.texpack`、其他 `*.texpack`（含各自的 `.toc`）和游戏根目录的 `libSceAgcTextureTool.dll`；
  - 不写游戏目录。
- **底板 wad**（`--base-wad` / `--wad`）：
  - **芙蕾雅用原版 `r_freyavalkyrie00.wad`。** 安装 mod 会覆盖游戏里的那份，所以要自己先备份一份原版，构建时用备份。LZ4 压缩的原版文件可以直接用；
  - **奎托斯在本案用的是用户自己早先的 mod（KarinPicodraTech_Kratos）的 `r_heroa00.wad`。** 它替换过的流数据全部从原版 `root.lodpack` 重建。`LOD0_HASH` 和 `PASSTHROUGH` 是按这份底板写的；用原版 `r_heroa00.wad` 做底板没有测试过；
  - `verify_build.py` 和 `knee_sim.py` 要用构建时的同一份底板。
- **源模型**：FBX 和 VRM 都不随包提供。`bake_knee.py` 只写到新文件，不改源文件。
- **中间结果**：
  - `tex_src/` 里的 PNG；
  - `karin_bones.json`；
  - `rigspec_*.json`；
  - Blender 的拟合目录（每个网格一个 npz，加 `summary.json` 和 `karin_fitted.blend`）。

  这些都来自模型或游戏，不随包提供。
- **输出：**
  - 网格：`r_heroa00.wad` / `r_freyavalkyrie00.wad`、`KarinOriginal(Freya).lodpack`、`.lodpack.toc`、`mesh_report.json`；
  - 贴图：`.texpack`、`.texpack.toc`、`.texpack.plan.json`；
  - 这些 JSON 里没有本机路径。`karin_fitted.blend` 是 Blender 文件，可能记有源文件路径，分享前要注意。

## 案例常量

以下是 Karin_Original 专用的值，不是通用配置：

- `build_kratos_final.py`：部件分配 `GROUP_PARTS`；
- `build_valk_final.py`：部件分配 `GROUP_PARTS`，零块宿主 `HOST`；
- `geometry.py`：材质到图集象限的 `ATLAS`，丢弃的材质 `DROP_MATERIALS`（`Karin_Alpha`），裙子混合比例 `skirt_leg_blend`；
- `build_textures.py` 的 `make_atlas()`：4 个材质名；
- `knee_sim.py` 顶部：`SHIN_BONES`、`SKIN_SLOT`、`SOCK_SLOTS`、`KNEE_HEIGHT`；
- `bake_knee.py`：网格名 `body_2`，默认形态键 `kisekae_Knee`；
- Blender 缩放：奎托斯 1.6，芙蕾雅 1.53；
- 芙蕾雅的减面比例：`0.9 0.8 0.7 0.6 0.5 0.4 0.3 0.22 0.16 0.12 0.08 0.06 0.04 0.03 0.02`，输出到 `fit_valk_lods`。

换模型时，这些值要按新模型的网格名、材质名和体型重写。

以下是 build `18979360` 的游戏布局（`build-sensitive`），游戏更新后要重新核对：

- `build_kratos_final.py`：`LOD0_HASH`、`PASSTHROUGH`；
- `build_valk_final.py`：网格组编号和 `HOST`；
- `rigspec.py` 的 `SPECS`：两个角色的骨骼编号；
- `build_textures.py` 的贴图名规则（`BODY_RE`、`DIFFUSE`、`EFFECT_RE` 等），`build_valk_textures.py` 的 `VALK_SELECT`；
- `build_mesh.py` 的 `PAD_JOINT`。

`build_mesh.py` 里的 `build()` 和 `write_lodpack()` 是早期写法，已被 `build_inplace.py` 取代：
- `build()` 重新排布整个缓冲区，不检查原容量；
- `write_lodpack()` 一个缓冲区一组，照它写出的补丁包在实机里崩溃。

现在只用这个文件里的 `root_buffer()` 和 `write_lodpack_single_group()`。

## 已验证与边界

- **可复现。** 满足以下条件时，用本包脚本重建，结果与已发布的 mod 文件**逐字节相同**：
  - 同一 build、同一组拟合结果、同一份骨骼表和角色表、同一组贴图源 PNG；
  - 同样的底板：奎托斯用 KarinPicodraTech_Kratos 的 wad，芙蕾雅用原版 wad；
  - Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.3.0、lz4 4.4.5、etcpak 0.9.15、texture2ddecoder 1.0.6。

  结果：两个角色的 wad、lodpack、`.lodpack.toc`、texpack、`.texpack.toc` 共 10 个文件相同；`mesh_report.json` 和贴图 `.plan.json` 也与项目记录相同。详见 [验证记录](../VALIDATION.md)。
- **离线检查。** 两个角色的 `verify_build.py` 都是 `BAD 0`。芙蕾雅的 `knee_sim.py` 在 0、30、60、90 度时，膝盖区都没有皮肤穿出袜面。
- **其他复现。** `rigspec.py` 重新生成的两个角色表与项目使用的逐字节相同。`bake_knee.py` 从原件烘焙出的 FBX 和 VRM，与项目当时烘焙的文件逐字节相同。
- **便携改动。** 去掉了写死的游戏目录、底板 wad 和工作目录，入口脚本改用 argparse，贴图 DLL 改为第一次用到时才加载。处理逻辑没有变；改动后重跑，结果仍然逐字节相同。哪些文件改了，见 [验证记录](../VALIDATION.md)。
- **只做一件事。** 这套脚本只处理奎托斯和同伴芙蕾雅这两个 wad。它不是安装器，不改游戏目录，也不处理 mod 之间的冲突。`r_freya00.wad` 游戏不会加载，本包不提供它的构建脚本。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中 7 项战神合成测试不需要游戏或模型：
  - 三种骨骼权重布局的编码、解码往返，包括 8 个 u16 骨骼槽的那一种；
  - 单组多成员 lodpack 的写入和 `.toc` 回读；
  - 槽位规划：档位挑选、副槽放不下时交给主槽、主槽放不下时按优先级丢部件；
  - 二进制 FBX 原样写回，以及改动压缩数组后的重写和尾部填充；
  - VRM 的形态键烘焙：基础网格移动、形态键清零、包围盒更新；
  - 骨架镜像：同一关节叠两根骨时的选择，以及 `left_override`；
  - 游戏目录没设置时报错，导入贴图模块不需要游戏。

  没装本包的额外依赖时，这些测试会跳过，并提示安装命令。
- **署名。** WAD 条目偏移的计算移植自 GOWTool（gowr-pc 分支），MESH / MG 布局也参考了它，见 [工具来源](../../references/TOOL_SOURCES.md)。
