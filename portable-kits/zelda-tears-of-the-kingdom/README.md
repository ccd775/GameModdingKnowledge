# 塞尔达传说：王国之泪 便携包

先读 [游戏知识](../../games/zelda-tears-of-the-kingdom/README.md) 和 [构建流水线](../../games/zelda-tears-of-the-kingdom/BUILD_PIPELINE.md)。文件格式和容器见 [技术合同](../../games/zelda-tears-of-the-kingdom/TECHNICAL_CONTRACTS.md)，头发和裙摆的物理见 [物理](../../games/zelda-tears-of-the-kingdom/PHYSICS.md)，表情和眨眼见 [面部](../../games/zelda-tears-of-the-kingdom/FACE.md)，存档工具和安装包见 [存档与发行](../../games/zelda-tears-of-the-kingdom/SAVE_AND_RELEASE.md)。

这是 Karin_Original 替换 Armor_1061 套装（v7c）实际用过的工具：

- Python 构建链：重定向、蒙皮、借用布料骨骼、面部拟合、贴图、图标和 RESTBL；
- Blender 导出与预览脚本；
- 三个 C# 工具的源码：TotkMdl（无界面驱动 Switch Toolbox 读写 BFRES）、NxExtract（LibHac 解包 XCI / NCA）、bphcl 探针（PhysicsTool.Core 读 Havok cloth）；
- 发行包的安装脚本和存档工具，以及打包脚本。

**适用范围**
- **游戏版本：** 王国之泪 1.2.0，title `0100F2C0115B6000`。mod 是 yuzu 系模拟器的 LayeredFS 文件夹 `user\load\0100F2C0115B6000\<名>\romfs\`。
- **本包不含：**
  - Switch Toolbox、PhysicsTool、LibHac 的二进制；
  - 密钥（`prod.keys`、title key）、游戏 romfs、源模型、构建产物。
- **基础模型：** 零售版 `.bfres.mc` 的顶点数据用任天堂的 mesh codec，Switch Toolbox（2026-10-31 版）读不了。`build_karin.py` 的基础模型要用 Switch Toolbox 能读的另存版本，项目用的是用户旧 mod `03_kalin` 里另存过的 1061 三件。见 [技术合同](../../games/zelda-tears-of-the-kingdom/TECHNICAL_CONTRACTS.md) §2。
- **平台：** TotkMdl 只能在 Windows 上运行（net48 + WinForms）。存档工具和安装器支持 Windows PowerShell 5.1 和 PowerShell 7。

## 环境变量与工作目录

| 变量 | 读它的脚本 | 含义 |
| --- | --- | --- |
| `TOTK_WORK` | `build_karin.py`、`tk.py`、`face_anim.py`、`make_textures.py`、`make_icons.py`、`package.py`、`txtg.py` | 工作目录，结构见下。`build_karin.py` 没设时报错退出，不写任何东西 |
| `TOTK_ST_DIR` | `tk.py`、`txtg.py` | 可选。放 `TotkMdl.exe` 的 Switch Toolbox 副本（要有 `tegra_swizzle_x64.dll`），默认 `$TOTK_WORK/tools/st_headless` |
| `PHYSICSTOOL_DIR` | `tools/bphcl_probe` | PhysicsTool-2.2.0-win-x64 目录 |
| MSBuild 属性 `SwitchToolboxDir` / `LibHacDll` / `PhysicsToolDir` | 三个 `.csproj` | 依赖 DLL 的位置，`dotnet build -p:<属性>=<路径>` |

`$TOTK_WORK` 下的结构：

| 路径 | 内容 |
| --- | --- |
| `src/karin_dump.npz`、`src/karin_shapekeys.npz` | `blender/blender_dump_karin.py`、`blender_dump_shapekeys.py` 的输出 |
| `src/tex/*.png` | `blender/extract_tex.py` 从 FBX 里导出的贴图，文件名见 `make_textures.py` 的 `ALB` |
| `ref/03_kalin/Model/Armor_1061.Armor_1061_{Head,RaulSkin_Upper,Lower}.bfres` | Switch Toolbox 能读的基础模型 |
| `romfs/` | 原版文件：`Pack/ZsDic.pack.zs`、`System/Resource/ResourceSizeTable.Product.120.rsizetable.zs`、`TexToGo/Link_RaulSkin_{Alb,Nrm,Spm}.txtg`、`UI/Tex/Icon/Armor_106?_*.bntx.zs`、`Pack/Actor/Armor_106?_*.pack.zs` |
| `romfs_st/` | 给 TotkMdl 当游戏目录用：`romfs/` 去掉 `TexToGo/`（Switch Toolbox 读某些原版 txtg 会抛异常，任何引用它们的模型都打不开） |
| `romfs_anim/Model/` | `Player_Animation.anim.bfres`（解压后的）和 `Player_Animation.Skeleton.bfres.mc` |
| `work/anim_skel.json` | `TotkMdl info romfs_anim/Model/Player_Animation.Skeleton.bfres.mc romfs_st work/anim_skel.json` |
| `work/build/` | 构建输出：`out/*.bfres.mc`、`tex/*.txtg`、`packs/`、`icons/`、`preview/icon_*.png`、报告 |

## 构建流程

### 0. 编译工具（Windows）

```powershell
$Kit = "portable-kits/zelda-tears-of-the-kingdom"; $W = "<仓库外的目录>"; $env:TOTK_WORK = "<工作目录>"
# 复制到仓库外编译，否则 obj/、bin/ 会落进本包
Copy-Item -Recurse $Kit/tools/TotkMdl "$W/src/TotkMdl"
dotnet build "$W/src/TotkMdl/TotkMdl.csproj" -c Release -p:SwitchToolboxDir="<Switch Toolbox 目录>" -o "$env:TOTK_WORK/tools/st_headless"
# st_headless 先放一份完整的 Switch Toolbox（TotkMdl 从自己旁边、Lib\、Lib\Plugins\ 加载它的 DLL）
Copy-Item -Recurse $Kit/tools/NxExtract "$W/src/NxExtract"
dotnet build "$W/src/NxExtract/NxExtract.csproj" -c Release -p:LibHacDll="<LibHac 0.19 nuget>/lib/net7.0/LibHac.dll" -o "<nx 目录>"
Copy-Item -Recurse $Kit/tools/bphcl_probe "$W/src/ptprobe"
dotnet build "$W/src/ptprobe/ptprobe.csproj" -c Release -p:PhysicsToolDir="<PhysicsTool-2.2.0-win-x64>"
```

PhysicsTool 和探针在本机（Windows 10 19044）直接启动 exe 会因 CET 兼容崩溃。改用 `dotnet` 宿主运行：`$env:DOTNET_EnableCETCompat=0; dotnet ptprobe.dll <x.bphcl>`。

### 1. 原版文件

`tools/NxExtract/nxx.ps1` 在 pwsh 7.4 里加载 LibHac 和 NxExtract.dll，把基础版 XCI 的程序 NCA 叠上更新 NCA 后列出或解出 romfs：

```powershell
pwsh -File $Kit/tools/NxExtract/nxx.ps1 -mode x -out <romfs> -pats "Model/Armor_1061*;Pack/Actor/Armor_106*;TexToGo/Link_RaulSkin_*" `
  -Work <含 nx\ 和 title_merged.keys 的目录> -Keys <含 prod.keys 的目录> -Base "<游戏.xci>|<程序 NCA 名>" -Patch <更新的程序 NCA>
```

yuzu 自带的「转储 RomFS」在 `Banc/` 里出错卡死，项目因此改用 NxExtract。

### 2. 源模型

```powershell
blender -b --factory-startup -P $Kit/scripts/blender/blender_dump_karin.py -- <Karin_Original.fbx> $env:TOTK_WORK/src/karin_dump.npz
blender -b --factory-startup -P $Kit/scripts/blender/blender_dump_shapekeys.py -- <Karin_Original.fbx> $env:TOTK_WORK/src/karin_shapekeys.npz Body
blender -b --factory-startup -P $Kit/scripts/blender/extract_tex.py -- <Karin_Original.fbx> $env:TOTK_WORK/src/tex
```

### 3. 模型、贴图、图标、打包

```powershell
python $Kit/scripts/build_karin.py              # -> work/build/out/*.bfres.mc 和 report.json
python $Kit/scripts/make_textures.py $env:TOTK_WORK/work/build/tex
python $Kit/scripts/make_icons.py $env:TOTK_WORK/romfs $env:TOTK_WORK/work/build/icons 1061 1062 1063 1064
python $Kit/scripts/package.py <mod 目录>/00_Karin_Original --vanilla $env:TOTK_WORK/romfs/System/Resource/ResourceSizeTable.Product.120.rsizetable.zs `
  --merge <其他启用的 mod 的 RESTBL> --extra $env:TOTK_WORK/work/build/packs $env:TOTK_WORK/work/build/icons
```

- `package.py` 会先删掉 `<mod 目录>/romfs` 再写。
- `work/build/packs/Pack/Actor/Armor_106?_Head.pack.zs`：头盔 pack，ArmorParam 的 `HideMaterialGroupNameList` 追加 `G_Face_Only`、`G_Head_All`。项目直接沿用 `03_kalin` 改好的四个文件。
- 图标 PNG（`work/build/preview/icon_*.png`）用 `pose_test.py` 摆姿势后，由 `blender/blender_preview.py --icon` 渲染。

### 4. 离线检查

- `TotkMdl export <out 模型> romfs_st <x.json>` 导出顶点和权重，再交给下面的脚本：
  - `pose_test.py`：线性蒙皮测试姿势（负权重不参与）；
  - `face_preview.py`：游戏面部动画帧，支持带符号的权重；
  - `swing_test.py`：按 bphcl 里的真实铰链轴转动借用的布料骨骼，报告耳尖位移和耳朵伸长。
- `blender/blender_preview.py` 渲染正、侧、背三视图，`blender/inv_karin.py` 列出 FBX / VRM 的物体和骨架。
- `tools/bphcl_probe` 列出每个 cloth 驱动哪些骨骼，以及驱动三角形的三个粒子（`F` = 固定）。

### 5. 发行包与存档工具

```powershell
python $Kit/scripts/assemble_package.py --mod <mod 目录>/00_Karin_Original --related <相关 mod.zip> --version v7c --out <新目录>
```

- `--related` 是用户自己装的 `load/01_Kalin_Base`、`load/02_Visuals_UltraCam` 和 `sdmc/UltraCam`，可以是 ZIP 或文件夹。
- 输出 Full / Lite 两个文件夹和 ZIP：
  - 安装包内容来自 `release/`：`README.md` 和 `tools/Install.ps1`、`tools/Give-KarinArmor.ps1`；
  - 两个 `.bat` 由脚本写出，因为本库不收 `.bat`。
- 存档工具单独用：`powershell -ExecutionPolicy Bypass -File release/tools/Give-KarinArmor.ps1 [-UserDir <user>] [-Slot N | -AllSlots] [-DryRun]`。

## 脚本一览

| 脚本 | 作用 |
| --- | --- |
| `build_karin.py` | 主构建：按段相似变换把 Karin 搬到 Link 的 T 姿势骨架，头部单独缩放和下沉，肩部压扁、腿部加粗，裙摆按方位角改到 24 根裙骨，借用布料骨骼（`APPENDAGES`），面部和眨眼拟合，材质改名避开染色动画，调用 TotkMdl `replace` |
| `retarget.py` | `similarity`（缩放 + 旋转 + 沿段拉伸 + 垂直方向的 `radial`）、`blend_transform`、权重限制 |
| `tk.py` | 调用 TotkMdl 并读取它的 JSON，计算世界绑定矩阵 |
| `face_anim.py`、`fska.py` | 自己实现的 FSKA v10 读取器，在 Head 空间里计算面部骨骼的蒙皮矩阵 |
| `face_rig.py` | 逐顶点 NNLS 把形态键拟合到面部骨骼上；`fit_blink` 用带符号、可大于 1 的眼皮权重拟合眨眼 |
| `mc.py`、`totkfs.py`、`byml7.py` | MCPK（无 magic 的 zstd）、ZsDic 字典 zstd、SARC、RESTBL、BYML v2–v7 |
| `txtg.py`、`make_textures.py`、`make_icons.py` | TexToGo 读写（ASTC / BC，按 mip 块线性重排），原版 Link 皮肤贴图作头模板；背包图标在原 BNTX 里原地替换 |
| `package.py` | 组装 mod 文件夹，合并 RESTBL（原版 + 其他 mod 的改动取大 + 本 mod 的条目） |
| `pose_test.py`、`face_preview.py`、`swing_test.py` | 离线姿势、面部动画和摆动检查 |
| `assemble_package.py` | Full / Lite 发行包（项目里 `assemble.sh` 的 Python 版） |
| `blender/*.py` | 导出 Karin 网格、骨架和形态键，导出贴图，查看物体清单，渲染预览 |
| `tools/TotkMdl` | `info` / `export` / `replace` / `anims`。`replace` 的编辑 JSON 支持：删形状、复制材质、换采样器贴图、重建平滑矩阵表（`smoothBones`）、新形状、改形状材质、材质改名（`renameMaterials`）、逐形状浮点权重格式（`weightFormat`） |
| `tools/NxExtract` | LibHac 叠加基础版和更新 NCA，按 glob 列出或解出 romfs |
| `tools/bphcl_probe` | PhysicsTool.Core 读 `.bphcl`：每个 cloth 的骨骼、驱动三角形、约束集 |
| `release/tools/Install.ps1` | 安装到 yuzu 系模拟器：同名 mod 和设置先备份，提示排序靠前的 mod，可选调用存档工具 |
| `release/tools/Give-KarinArmor.ps1` | 往最近的存档槽的防具包加 Armor_1061 三件：按哈希表定位数组、只用空格子、置「已获得」标记、先备份、模拟器运行时拒绝 |
