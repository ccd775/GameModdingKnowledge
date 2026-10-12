# 龙之信条2便携包

先读 [游戏知识](../../games/dragons-dogma-2/README.md) 和 [构建流程](../../games/dragons-dogma-2/BUILD_PIPELINE.md)。替换脚本怎样把 Karin 交给游戏自己的身体构建，见 [运行时注入](../../games/dragons-dogma-2/RUNTIME_INJECTION.md)；链参数见 [链物理](../../games/dragons-dogma-2/CHAIN_PHYSICS.md)；开发控制台见 [开发工具](../../games/dragons-dogma-2/DEV_TOOLING.md)。

这是两个玩家替换 Mod（Karin PicodraTech v1.3.0、Karin Original v1.0.1）实际使用的工具：Blender 构建脚本、C# 写的 DD2Tool、Python 辅助脚本、REFramework Lua（替换脚本、开发控制台、探针）和开发查询。

- **游戏版本：** Steam App 2054970，build `25290080`（2026-10 更新 + DLC「Dark Arisen」）。格式：mesh `.260421070`、tex `.251211553`、mdf2 `.51`、chain `.55`、pfb `.18`。
- **REFramework nightly 01421 或更新：** 从 01421 起，它会把 `<游戏>/pak_mods/*.pak` 注入游戏；本项目用 01424。这个 build 默认不加载 patch pak，REFramework 的 LooseFileLoader 也不起作用，所以发行物是 `pak_mods/` 下的 PAK 加 `reframework/autorun/` 下的 Lua。
- **DD2Tool：**
  - 源码在 `dd2tool/`，依赖 [RE-Engine-Lib](https://github.com/kagenocookie/RE-Engine-Lib) 的 commit `bf0e5e5222700716516797613a54b9b61fedfc35`；
  - 编译用 .NET 10 SDK 10.0.401，因为 RE-Engine-Lib 用到 C# 14；程序本身面向 net8.0，运行要 .NET 8 运行时；
  - `DD2Tool.csproj` 默认在同级目录 `../RE-Engine-Lib` 找 RE-Engine-Lib，可用 `-p:ReeLibDir=<路径>` 改。请复制到仓库外再编译，否则 `obj/`、`bin/` 会落进本包；
  - 在没打 CET 内核补丁的 Windows 10 19044 上，.NET 10 SDK 的 `csc.exe`、`VBCSCompiler.exe`、`MSBuild.exe` 等启动即报 `Your Windows doesn't fully support CET`。这时只对自己的 SDK 副本运行 `scripts/clear_cet_flag.py <exe> ...`（原文件留作 `.cet.bak`），不要改系统里的 dotnet。
- **Blender：** 4.5.12 LTS 加 RE Mesh Editor 0.66。插件可以装进 Blender，也可以把环境变量 `DD2_BLENDER_ADDONS` 设为含 `re_mesh_editor` 的文件夹。RE Mesh Editor 不认识 `.260421070`，所以要先用 `DD2Tool meshconv` 转成 `.240423143`，导出后再转回来。
- **texconv：** DirectXTex 的 texconv，贴图那一步用，本项目用 2026.5.8.1。
- **Python：** 3.10 或更高。除贴图脚本外只用标准库；贴图脚本另需 numpy 2.5 和 Pillow，要 Python 3.12 或更高（`requirements.txt` 钉的 numpy 版本不支持更老的 Python）。
- **只在 Windows 上：** DD2Tool 和 texconv 都是 Windows 程序。提取出的文件名大小写混用，依赖 Windows 文件系统不区分大小写。
- **运行位置：** 以下命令都从交接包根目录执行。

## 构建流程

下面以 PicodraTech 为例，Original 的取值见后面的"两个 profile"表。

```powershell
python -m pip install -r requirements.txt -r portable-kits/dragons-dogma-2/requirements.txt
$Kit = "portable-kits/dragons-dogma-2"
$Game = "<Steam 库>\steamapps\common\Dragons Dogma 2"
$Blender = "<Blender 4.5.12 目录>\blender.exe"
$TexConv = "<DirectXTex 目录>\texconv.exe"
$env:DD2_BLENDER_ADDONS = "<含 re_mesh_editor 的文件夹>"   # 插件已装进 Blender 时省略
$W = "../MyMod/Work"
New-Item -ItemType Directory -Force $W | Out-Null
$env:DD2_NATIVE_DIR = "$W/native"                            # make_chain_spec.py / build_karin_textures.py 读这里

# 1. 编译 DD2Tool（仓库外，与 RE-Engine-Lib 并排）
git clone https://github.com/kagenocookie/RE-Engine-Lib ../MyMod/Tools/RE-Engine-Lib
git -C ../MyMod/Tools/RE-Engine-Lib checkout bf0e5e5222700716516797613a54b9b61fedfc35
Copy-Item -Recurse $Kit/dd2tool ../MyMod/Tools/DD2Tool
dotnet build ../MyMod/Tools/DD2Tool/DD2Tool.csproj -c Release -o ../MyMod/Tools/bin/DD2Tool
$T = "../MyMod/Tools/bin/DD2Tool/DD2Tool.exe"

# 2. 从 re_chunk_000.pak 取出要用的 9 个原生文件；旧路径表用 Ekey/REE.PAK.Tool 的 DD2_STM_Release.list
& $T resolve "$Game/re_chunk_000.pak" "<DD2_STM_Release.list 的路径>" $W/dd2_resolved.list
$Want = '^natives/stm/(appsystem/charaedit/ch000/material/runtime/body_runtime_human\.mdf2|character/_kit/(body/body_000_f/body_000_f\.mesh|body/body_001_f/body_001_f\.mdf2|body/_common/secondary/(body_chain\.chain|body_female\.clsp)|hair/hair_0[01]1/hair_0[01]1\.chain|_equipment/mantle/523/mantle_523_f\.chain|_equipment/pants/002/wl_002_0_0_albd\.tex))'
& $T extract "$Game/re_chunk_000.pak" $W/dd2_resolved.list $Want $W/native
$Ref = "$W/native/natives/stm/character/_kit/body/body_000_f/body_000_f.mesh.260421070"
New-Item -ItemType Directory -Force $W/conv | Out-Null
& $T meshconv $Ref $W/conv/body_000_f.mesh.240423143 "DD2 (old v2)"

# 3. profile 变量（PicodraTech）
$Profile = "picodra"; $Name = "karin_body"; $NatDir = "Character/_karin"; $Variant = "F"; $Pak = "KarinPicodraTech.pak"
$SrcBlend = "<模型目录>/Karin_PT_Unified_Atlas.blend"; $TexSrc = "<模型目录>/textures"; $Inv = "$W/inventory.json"
$B = "$W/build"; $Stage = "$W/stage"; $Nat = "$Stage/natives/STM/$NatDir"
New-Item -ItemType Directory -Force $B, "$Nat/tex" | Out-Null   # $Stage 里只能有这一个 profile 的文件

# 4. Blender：拟合到 DD2 女性骨架，导出 .240423143 和 build_report.json
& $Blender -b --factory-startup --python $Kit/scripts/blender/build_karin_body.py -- $B --source-blend $SrcBlend --dd2-body $W/conv/body_000_f.mesh.240423143 --materials karin --profile $Profile

# 5. 网格：转回 .260421070，前 192 根骨按原生顺序，flags 改为 4099，再导出 meshinfo
& $T meshconv "$B/$Name.mesh.240423143" "$B/raw.mesh.260421070" "DD2"
& $T meshreorder "$B/raw.mesh.260421070" $Ref "$B/$Name.mesh.260421070"
python -B $Kit/scripts/patch_mesh_header.py "$B/$Name.mesh.260421070"
& $T meshinfo "$B/$Name.mesh.260421070" "$B/$Name.meshinfo.json"
Copy-Item "$B/$Name.mesh.260421070" $Nat/

# 6. 贴图
python -B $Kit/scripts/build_karin_textures.py "$Stage/natives/STM" --profile $Profile --src $TexSrc --work-dir $B --texconv $TexConv --dd2tool $T

# 7. 材质：按下面"MDF 规格"写好 $W/mdf.json
& $T mdfbuild $W/mdf.json

# 8. 链
python -B $Kit/scripts/make_chain_spec.py "$B/build_report.json" $W/chain.json "$Nat/$Name.chain.55" $Variant --profile $Profile --inventory $Inv
& $T chainbuild $W/chain.json

# 9. 打包
& $T pack "$W/$Pak" $Stage
```

`pack` 会逐个列出文件，全部是 `OK` 才算写全。安装：

- **PicodraTech：**
  - 把 `$W/KarinPicodraTech.pak` 放进 `<游戏>/pak_mods/`；
  - 把 `reframework/karin_replacer.lua` 放进 `<游戏>/reframework/autorun/`。
- **Original：**
  - 先运行 `python -B $Kit/scripts/make_original_lua.py --out $W/karin_replacer_original.lua` 生成脚本；
  - 把它和 `KarinOriginal.pak` 按上面的位置安装。
- **两个只能装一个：** Original 的脚本见到 PicodraTech 的脚本时不工作。

### 两个 profile

| 项 | PicodraTech | Original |
| --- | --- | --- |
| `$Profile` / `$Name` | `picodra` / `karin_body` | `original` / `karin_original_body` |
| `$NatDir`（游戏内路径） | `Character/_karin` | `Character/_karin_original` |
| 源 blend | 模型自带的 `Karin_PT_Unified_Atlas.blend` | `prepare_karin_original.py` 生成的 `karin_original_src.blend` |
| 贴图源 | 模型的 `textures/`（4 张 4096 图集，脚本里写了文件名） | `prepare_karin_original.py` 生成的 `images/` |
| 骨骼表 `$Inv` | 用下面的 Blender 片段导出 | `prepare_karin_original.py` 生成的 `inventory.json` |
| 链参数 `$Variant` | `F` | `O` |
| PAK | `KarinPicodraTech.pak` | `KarinOriginal.pak` |
| Lua | `reframework/karin_replacer.lua` | `make_original_lua.py` 生成 |

Original 的源模型要先转换。这一步只接受脚本里记了 SHA-256 的那个 FBX。之后又改过的副本会被拒绝，例如为别的项目烘焙过膝盖形态键的版本：

```powershell
& $Blender -b --factory-startup --python $Kit/scripts/blender/prepare_karin_original.py -- $W/original "<模型目录>/Karin(Clone)_BlenderSafe.fbx"
# 之后：$SrcBlend = "$W/original/karin_original_src.blend"; $TexSrc = "$W/original/images"; $Inv = "$W/original/inventory.json"
```

PicodraTech 的骨骼表用 Blender 从源 blend 导出。`make_chain_spec.py` 只读 `armatures[0].bones` 里的 `name` 和 `parent`，骨骼顺序不影响结果：

```powershell
@'
import bpy, json, sys
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
bones = [{"name": b.name, "parent": b.parent.name if b.parent else None} for b in arm.data.bones]
json.dump({"armatures": [{"name": arm.name, "bones": bones}]}, open(sys.argv[-1], "w", encoding="utf-8"), indent=1)
'@ | Set-Content -Encoding utf8 $W/dump_inventory.py
& $Blender -b --factory-startup $SrcBlend --python $W/dump_inventory.py -- $Inv
```

### MDF 规格

`mdfbuild` 读一个 JSON。它以原生 `body_001_f.mdf2.51` 的 `nail_mat` 为模板（母版 `Character_Default.mmtr`）复制出 Karin 的材质，再从运行时皮肤 `body_runtime_human.mdf2.51` 原样复制 4 个材质。网格里有 4 个用这些名字的隐藏桩子网格，皮肤烘焙器按名字找它们。相对路径按当前目录解析：

```json
{
 "template": "<native>/natives/stm/character/_kit/body/body_001_f/body_001_f.mdf2.51",
 "templateMaterial": "nail_mat",
 "output": "<stage>/natives/STM/Character/_karin/karin_body.mdf2.51",
 "materials": [
  {"name": "karin_skin_mat", "alphaTest": false, "twoSided": false,
   "textures": {"BaseDielectricMap": "Character/_karin/tex/karin_skin_ALBD.tex",
                "NormalRoughnessMap": "Character/_karin/tex/karin_skin_NRMR.tex",
                "AlphaTranslucentOcclusionCavityMap": "Character/_karin/tex/karin_skin_ATOC.tex"},
   "params": {"AlphaTestRef": [0.5]}}
 ],
 "copyMaterials": [{"file": "<native>/natives/stm/appsystem/charaedit/ch000/material/runtime/body_runtime_human.mdf2.51",
                    "names": ["body_mat", "hand_mat", "nail_mat", "vfx_mat"]}]
}
```

两个 Mod 的材质按以下顺序写。贴图组 `<组>` 对应 `<NatDir>/tex/<组>_ALBD.tex`、`_NRMR.tex`、`_ATOC.tex`，`AlphaTestRef` 都是 0.5：

| 材质 | alphaTest / twoSided | PicodraTech 贴图组 | Original 贴图组 |
| --- | --- | --- | --- |
| `karin_skin_mat` | 否 / 否 | `karin_skin` | `karin_skin` |
| `karin_face_mat` | PicodraTech 是 / 否；Original 否 / 否 | `karin_skin` | `karin_face` |
| `karin_eyealpha_mat` | 是 / 是 | `karin_skin` | `karin_eyealpha` |
| `karin_hair_mat` | 是 / 是 | `karin_hair` | `karin_hair` |
| `karin_hairalpha_mat` | 是 / 是 | `karin_hair` | `karin_hair` |
| `karin_clotha_mat` | 是 / 是 | `karin_clotha` | 无 |
| `karin_clothb_mat` | 是 / 是 | `karin_clothb` | 无 |
| `karin_costume_mat` | 是 / 是 | 无 | `karin_costume` |

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/blender/build_karin_body.py` | Blender 内运行。统一缩放到 DD2 女性 Hip 高度，四肢摆到 DD2 静止方向并烘焙；输出完整的 192 骨 DD2 女性骨架（Karin 比例）加 `K_*` 次级骨，按骨名改权重，生成表情骨 `KF_*` 和 4 个兼容桩子网格；加权骨超过 256 根时报错。写出 `<name>.mesh.240423143`、`build_report.json`、`<name>_build.blend` |
| `scripts/blender/prepare_karin_original.py` | Original 专用。把 FBX（Unity VRM 导出：厘米、Y 向上）转成构建脚本要求的约定（单位、朝向、人形骨名），写出 blend；内嵌贴图按原字节导出；写骨骼表 `inventory.json` |
| `scripts/blender/re_common.py` | 启用 RE Mesh Editor，导入、导出 RE mesh |
| `scripts/patch_mesh_header.py` | 把 `.260421070` 头部偏移 22 的内容 flags 改成 4099（IsSkinning、HasJoint、UseRTVertexAnimation，与 `tops_001_bd_f` 相同）；只认内部版本 251205828 |
| `scripts/build_karin_textures.py` | 每个图集出三张图：`_ALBD`（BC7 sRGB）；`_NRMR`（BC7，RG 为转成 OpenGL 约定的法线 XY，B 为法线 Z，A 为粗糙度）；`_ATOC`（BC1，R 为 alpha，G、B 为 1）。透明区的颜色向外扩，避免 mip 黑边；texconv 压缩后由 `DD2Tool dds2tex` 套原生 tex 的头部 |
| `scripts/make_chain_spec.py` | 生成 `chainbuild` 规格。以原生 `body_chain.chain.55` 为底（保留胸部、腰挂点），追加 Karin 的链组。每个节点的 `angleLimitDirection` 是从 +X 转到该节点静止方向的摆动四元数；Original 的裙子锥轴从静止方向向外（离开裙根中心竖轴）倾 0.25 rad。参数集：A 到 F 为 PicodraTech 的几轮试验（发行用 F），O 为 Original |
| `scripts/make_original_lua.py` | 由 `karin_replacer.lua` 生成 Original 的脚本：改名字、版本、资源路径、配置文件和全局名，设 `CHAIN_REST_POSE = true`，PicodraTech 的脚本在时不工作。`--check` 检查已有文件是否最新 |
| `scripts/clsp_dump.py` | 读 `.clsp.3` 碰撞体预设（形状、关节、flags、几何）；关节名哈希用 meshinfo 反查 |
| `scripts/devcmd.py` | 开发控制台客户端，见下 |
| `scripts/clear_cet_flag.py` | 清 .NET SDK apphost 的 CET 兼容位，见上 |
| `dd2tool/` | DD2Tool 源码，不带参数运行时列出主要命令。全部命令：`toc`、`resolve`、`extract`、`pack`、`meshinfo`、`meshconv`、`meshreorder`、`meshdiag`、`tex2dds`、`dds2tex`、`mdfinfo`、`mdfrt`、`mdfbuild`、`chaininfo`、`chainrt`、`chainbuild`、`rszdump`。`rszdump` 依赖的 RSZ 模板对当前 build 已过期 |
| `reframework/karin_replacer.lua` | PicodraTech v1.3.0 的发行脚本，与发行包里的文件逐字节相同 |
| `reframework/karin_dev.lua` | 开发控制台的游戏端，只用于开发，不要发行 |
| `reframework/karin_probe_dump.lua` | 只读探针：把玩家的 GameObject、组件、网格层级写到 `reframework/data/karin_probe/player_dump_<n>.json` |
| `reframework/karin_pipeline_probe.lua` | 开发探针：记录游戏的换身体回调、皮肤烘焙返回值和 `build` 参数 |
| `devqueries/*.lua` | 发给开发控制台的查询，见下 |

## 开发控制台

```powershell
Copy-Item $Kit/reframework/karin_dev.lua "$Game/reframework/autorun/"
$env:DD2_GAME_DIR = $Game                                   # 或者每次加 --game-dir
python -B $Kit/scripts/devcmd.py -e "return K.player() ~= nil"
python -B $Kit/scripts/devcmd.py $Kit/devqueries/player_state.lua --timeout 30
```

- **工作方式：**
  - `devcmd.py` 写 `<游戏>/reframework/data/karin_dev/cmd.json`（`{"id", "lua"}`）；
  - `karin_dev.lua` 每 15 帧检查一次，在游戏线程里把每个新 id 执行一遍，写回 `result.json`（`{"id", "result"}` 或 `{"id", "error"}`）；
  - `devcmd.py` 打印结果 JSON。退出码：0 成功，1 Lua 报错，2 超时（默认 20 秒）、参数错误或找不到 Lua 文件，3 游戏目录无效。
- **游戏目录：** 没给 `--game-dir`、也没设 `DD2_GAME_DIR`，或者目录下没有 `reframework/` 时，直接报错，不创建任何文件。
- **查询代码：**
  - 查询代码在全局环境里运行，返回值要能转成 JSON；
  - 可用辅助表 `K`：`K.player()`、`K.comp(go, 类型名)`、`K.child(go, 名字)`、`K.children(go)`、`K.tname(o)`、`K.str(v)`、`K.mesh_res(路径)`、`K.mdf_res(路径)`；
  - 前一次设的全局变量下一次还在，可以先用 `-e` 设参数，再发查询文件。
- **浮点参数：** 传给浮点参数要写 `1.0`，不能写 `1`。Lua 整数会按整数位传进去，读回来接近 0。

| 查询 | 内容 |
| --- | --- |
| `player_state.lua` | 玩家当前的 mesh / mdf / chain 路径、隐藏掩码、原头部是否显示、`KarinReplacer.status()`（Original 的全局名是 `KarinOriginalReplacer`，要相应改） |
| `ubt_lists.lua` | `UpperBodyTransformer` 各列表的长度，加 `KarinReplacer.status()` |
| `mockup_state.lua` | 菜单模型（装备界面、头像）的状态 |
| `audit_joints.lua` | 角色各缓存里的 joint：本角色、失效、他人的各有多少。先设 `KARIN_AUDIT_TARGET = "mockup"` 可改查菜单模型 |
| `audit_foreign_refs.lua` | 子物体和场景里其他角色有没有引用玩家的 joint，以及其中失效的数量 |
| `audit_scene_refs.lua` | 全场景所有 `via.Behavior` 对玩家 joint 的引用。很慢，会卡住游戏几秒 |
| `container_joints.lua` | 脚本对象容器（`List<app.X>` / `app.X[]`）里缓存的玩家 joint |
| `native_refs.lua` | 玩家脚本缓存了哪些 `via.*` 原生对象（不含组件和 joint） |
| `chain_probe.lua` | 每个链关节的世界位置，以及链让它离开静止旋转多少度 |
| `chain_live.lua` | 运行时改链组倍率。先设全局 `SET = {[设置 id] = {grav=, damp=, elastic=, motion=, angle=}}`，返回各组根到尖的落差 |
| `skirt_rec.lua` / `skirt_get.lua` | 每帧记录裙子节点和大腿骨在 Hip 静止系里的位置（毫米），共 `NFRAMES` 帧（默认 480）；`skirt_get.lua` 把记录写到 `reframework/data/karin_dev/skirt_rec.json` |

审计类查询（`audit_*`、`container_joints`、`native_refs`）是 v1.1 运行时换身体时期用来查 joint 缓存的工具。

## 脚本注释里的「SOP」

部分脚本注释（如 `karin_replacer.lua`，为保持与发行版逐字节一致未改）引用了项目私有日志的章节号，对应关系：
SOP 5.2 → [技术合同](../../games/dragons-dogma-2/TECHNICAL_CONTRACTS.md) §4–5；SOP 6.0 → [运行时注入](../../games/dragons-dogma-2/RUNTIME_INJECTION.md) §2–3、§5–6；
SOP 6.1 / 6.3 → 运行时注入 §4 与 [排障手册](../../games/dragons-dogma-2/TROUBLESHOOTING.md)；SOP 6.4 → [表情](../../games/dragons-dogma-2/FACIAL_EXPRESSIONS.md)；
SOP 6（构建方法）→ [构建流程](../../games/dragons-dogma-2/BUILD_PIPELINE.md)；SOP 6.5 → [链物理](../../games/dragons-dogma-2/CHAIN_PHYSICS.md) 与构建流程 §8（第二个 profile）。

## 输出与本机信息

- **中间结果：**
  - `build_report.json` 的 `args` 和 `karin_blend` 记有本机路径；
  - `prepare_report.json` 的 `source` 也记有本机路径；
  - `<name>_build.blend` 是 Blender 文件，也可能记有源文件路径；
  - `make_chain_spec.py` 写出的规格里是原生文件的绝对路径。

  这些文件分享前要处理，不要收进本仓库。
- **发行物：** PAK 和 Lua 里没有本机路径。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时，要按新模型的骨名、材质名和体型重写：

- `build_karin_body.py`：`PROFILES`（资源路径、输出名）、`MATERIALS`（源材质到 DD2 材质和可见组）、`FACE`（表情通道和形态键名、弱骨合并阈值）；
- `prepare_karin_original.py`：`SRC_SHA256`、`RENAME`、`IMAGES`，以及 Hips 高度 0.7494 的检查；
- `make_chain_spec.py`：`ROOTS`、`ROOTS_ORIGINAL`、`TIPS`、`VRM`、`PROFILES`（裙子只碰大腿、外倾 0.25 rad），以及 `apply_variant()` 里 F 和 O 的参数表；
- `build_karin_textures.py`：`PROFILES` 里的图集文件名、粗糙度和法线 G 翻转；
- `make_original_lua.py`：`VERSION` 和 `SUBS`；
- `karin_replacer.lua`：资源路径、`FACE_*` 表情幅度、`CHAIN_REST_POSE`。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 文件版本：`patch_mesh_header.py` 的内部版本 251205828 和 flags 4099；DD2Tool `Program.cs` 的 `KnownNew`；
- 原生模板路径：`make_chain_spec.py` 的 4 个链模板，`build_karin_textures.py` 的 `TEMPLATE_REL`，MDF 的模板和贴图槽名；
- `karin_replacer.lua` 用到的 hook、字段和枚举名。网格 / 材质两个 hook、烘焙与体型 hook、用到的字段与枚举任一缺失时，脚本不递出 Karin 并在日志里列出缺哪项；chain 与隐藏掩码 hook 缺失时只是少了那一项功能。

## 已验证与边界

- **实机。** 用这些工具构建的 Mod 在 build `25290080` 上实机测过：Original v1.0.1 经用户在本机（无 DLC）确认；PicodraTech v1.3.0 由 agent 在装有 DLC 的测试机上自测（用户本机用到 v1.2.0）：
  - REFramework 01424；
  - 只替换女性人类，男性和兽人保持原样；
  - 没测过的场景：过场动画、攀爬大型魔物、梯子、布娃娃 / 死亡、角色编辑。
- **便携版本身只做了离线验证（2026-10-12）：**
  - PicodraTech：用本包的 Blender 脚本、本包源码编译的 DD2Tool 和本包的 Python 脚本重建，PAK 与发行包逐字节相同。MDF 那一步用的是项目当时的 spec（只改了路径）；按本页 MDF 表手写的 spec 没有做逐字节比对；
  - Original：从项目当时的 Blender 输出往后用本包工具重建，PAK 与 v1.0.1 发行包逐字节相同；
  - Original 的 Blender 这一步重跑结果不稳定：每次与项目的网格相差约 11 字节（共 3.56 MB），两次重跑之间也相差这么多，固定 `PYTHONHASHSEED` 也一样。这个差异对游戏有没有影响，没有测试；
  - 详见 [验证记录](../VALIDATION.md)。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中有 4 项龙之信条2合成测试，不需要游戏、Blender 或 .NET：
  - 链规格的四元数：`swing_from_x` 把 +X 转到给定方向；`tilt_outward` 让每个节点的锥轴离静止方向正好是给定角度，并转向远离裙根中心竖轴的一侧；
  - `patch_mesh_header.py` 只改 2 个字节，拒绝其他版本；
  - `clsp_dump.py` 的 MurmurHash3 和预设解析；
  - `devcmd.py`：用假的游戏目录走一遍命令和结果文件；缺游戏目录时报错。

  `--help` 测试覆盖 `scripts/` 下全部 Python 脚本；`build_karin_textures.py` 在没装 numpy 或 Pillow 时跳过。
- **测试没覆盖的部分：**
  - DD2Tool（C#）和 Lua 脚本不在 Python 测试里，只在上面的离线重建和项目的实机测试里用过；
  - Blender 脚本只做语法检查。
- **便携改动：**
  - 去掉了写死的本机路径，改为命令行参数或环境变量（`DD2_GAME_DIR`、`DD2_NATIVE_DIR`、`DD2_BLENDER_ADDONS`、`TEXCONV`、`DD2TOOL`）；
  - 没有 argparse 的脚本补上了 argparse；
  - `DD2Tool.csproj` 的 RE-Engine-Lib 位置可以用参数改；
  - 换行统一成 LF。

  处理逻辑没有变。哪些文件改了，见 [验证记录](../VALIDATION.md)。
- **署名：** DD2Tool 建立在 kagenocookie 的 RE-Engine-Lib（MIT）上，本包不含它的源码，见 [工具来源](../../references/TOOL_SOURCES.md)。
