# 死亡搁浅 2 便携包

先读 [游戏知识](../../games/death-stranding-2/README.md) 和 [构建流程](../../games/death-stranding-2/BUILD_PIPELINE.md)。

这是 Karin_Original 替换山姆项目实际使用的脚本：Decima 流图 / 链接表 / 整组对象的读取器、核心补丁、链接表重指、构建器、塌缩、打包与安装，以及按组核对的发行安装器。

- **Python**：3.12+（numpy、scipy、Pillow、lz4），见 `requirements.txt`。
- **外部工具**（用户自己获取，见 [工具来源](../../references/TOOL_SOURCES.md)）：
  - id-daemon 的 `ds2_pc_mi_022.exe` 和 `Decima_pack_ds2.exe`（导入 / 导出、打包）；
  - Odradek 1.0.49.0 DS2 构建里的 `types_1048.json` 和 `extensions_1048.json`（RTTI 类型表，读流图和对象必需）；
  - DirectXTex 的 `texconv.exe`。
- **环境变量**（缺了脚本会先报出变量名，什么都不写）：

  | 变量 | 内容 |
  | --- | --- |
  | `DS2_GAME_DIR` | 游戏目录（有 `DS2.exe` 的那个） |
  | `DS2_MODDING` | 工作区：`clean\`（干净根目录）、`work\`（导出与构建）、`out\`（构建输出）、`backup\`（开发安装的备份）、`tools\`（`texconv.exe`、`ds2_modtool\`） |
  | `DS2_TYPES_DIR` | 放 Odradek 类型表的目录（默认：脚本所在目录） |
  | `DS2_VRM` | 源 VRM（`build_karin.ps1` 的 `-Vrm` 默认值） |

## 流程

```powershell
python -m pip install -r requirements.txt -r portable-kits/death-stranding-2/requirements.txt
$Kit = "portable-kits/death-stranding-2/scripts"
$env:DS2_GAME_DIR = "<游戏目录>"; $env:DS2_MODDING = "<工作区>"; $env:DS2_TYPES_DIR = "<Odradek 类型表目录>"

# 0. 干净根目录（硬链接游戏的包文件；先把 id-daemon 的两个 exe 放进 <工作区>\tools\ds2_modtool）
pwsh -File $Kit/setup_cleanroot.ps1

# 1. 导出要用的组（每个 LOD 一个子目录，核心存成 .core.pristine）；查组的工具键
python -B $Kit/group_keys.py 50108 50110 50121 50120 31123
pwsh -File $Kit/export_group.ps1 -Group 7e9d -Name porter -Lods 0,1,2
#    50110 → g50110、50121 → g50121（0–3）、50120 → g50120（2–4）、31123 → g31123、12706 → g12706、6744 → g6744 …

# 2. 参考数据、头发图集空格、（有表情版）面部绑定增量
python -B $Kit/prep_ref.py <工作区>/work/porter/ref.json
python -B $Kit/hair_used.py
python -B $Kit/face_motion.py <工作区>/work/porter/face_motion.json

# 3. 链接表（每个版本从原版重新生成；末尾 f = 有表情版）
python -B $Kit/make_links.py v13
python -B $Kit/make_links.py v13f

# 4. 构建：build_ds2 → DDS → 塌缩任务 → 导入、核心补丁、打包 → 拷贝链接表
pwsh -File $Kit/build_karin.ps1 -Name karin_v34 -Links streaming_links_v13.stream
pwsh -File $Kit/build_karin.ps1 -Name karin_v34f -Links streaming_links_v13f.stream -Face

# 5. 离线读回、开发安装（游戏关闭时）
python -B $Kit/verify_pack.py <工作区>/out/karin_v34 50108 144
pwsh -File $Kit/install.ps1 -Name karin_v34      # -Restore 还原

# 6. 发行：每个变体一个目录，再放 install.ps1 和三个 .bat（见下）
python -B $Kit/make_release.py <工作区>/out/karin_v34 <发行目录>/NoExpression "Karin v34 (no expression)"
python -B $Kit/make_release.py <工作区>/out/karin_v34f <发行目录>/Expression "Karin v34 (expression)"
```

构建要脱离 SSH 运行（`wmic process call create "cmd /c ..."`，把输出重定向到日志），否则 SSH 断线会杀掉构建。

发行目录里的三个 `.bat`（仓库不收 `.bat`）：

```bat
@echo off
rem 安装-无表情版.bat；安装-有表情版.bat 把 NoExpression 换成 Expression；卸载.bat 换成 -Uninstall
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Variant NoExpression
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" -Variant NoExpression -GameDir "%~1"
)
pause
```

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `ds2rtti.py` | Decima RTTI 读取器（移植自 Odradek）：DSAR / LZ4 归档、按类型表读对象、带额外数据的类型（顶点 / 索引 / 数据缓冲、贴图、ZivaRT、着色器、本地化文本、物理形状、面部绑定、`UITexture`） |
| `jolt.py` / `riglogic.py` | `PhysicsShapeResource` / `PhysicsRagdollResource` 与 `FacialRigSettingWithLODResource` 的额外数据 |
| `graph.py` | 流图：文件、组、span、locator、子组、类型表、链接记录解码与编码；`game_root()` / `clean_root()` 读环境变量。`python graph.py [游戏目录]` 打印概要 |
| `group.py` | 读整组对象（字段字节位置记在 `__pos__`）。`python group.py <gid>` |
| `ds2ascii.py` | id-daemon ascii 网格和骨架的读写 |
| `roundtrip.py` | `prep`：给网格 ascii 加骨架头；`compare`：逐对象比较两份组核心 |
| `relink.py` | 原位改写链接记录：`<out> <gid>:<idx> <字段> <目标> ...`；字段可用 `Field#n`、`@<gid>:<idx>` |
| `make_links.py` | 项目链接表的全部重指（v5–v13，`f` 后缀为有表情版），调用 `relink.py`；`--print` 只列参数 |
| `patch_core.py` | 补导入工具不更新的字段；部件隐藏、逆绑定矩阵（`ibm` / `ibm_post`）、投影开关、单字段补丁、材质变量改名 |
| `prep_ref.py` | 参考数据 `ref.json`：骨架、绑定世界矩阵、槽网格关节表、图元材质 |
| `build_ds2.py` | 构建器入口：VRM 读入、剔除、TPS 拟合、权重继承、借粒子（外套 / 背包带 / 头发）、头发图集、涂装 UV 角、表情拟合与眼睑杠杆、装备靴补齐、塌缩、写 ascii / `jobs.json` / 贴图页 |
| `fit_ds2.py` | VRM 人形骨到 Porter 骨架的对应与 TPS 拟合 |
| `atlas.py` / `vrm.py` | 按 UV 岛拼页（含空格适配）；VRM 1.0 / 0.x 读取 |
| `hair_used.py` | 头发图集里山姆头发卡片用到的格子（512 掩码） |
| `rigdec.py` / `face_motion.py` | RigLogic 关节矩阵解码；单控制量下的关节世界增量 |
| `make_dds.py` | 按原版槽位的尺寸和格式转 DDS，写 `textures.json` |
| `collapse_mesh.py` / `gen_collapse.py` | 塌缩单个 ascii；整组塌缩任务（`--only`、`--skel`、`--stream-only`） |
| `verify_pack.py` | 经打包后的流图和包读回组、解码网格位置 |
| `make_release.py` | 发行变体：包文件 + manifest（重定向、链接改动、原版指纹） |
| `scan_strings.py` / `who_uses.py` / `sharing.py` / `group_keys.py` / `texsets.py` / `preview.py` | 扫全部核心包找字节模式；哪些部件用到某组的网格；哪些外观经子组用到某组；工具键；材质的贴图集；三视图预览 |
| `setup_cleanroot.ps1` / `export_group.ps1` | 干净根目录；按组导出 |
| `build_karin.ps1` / `make_mod_ds2.ps1` / `pack.ps1` | 整条构建；导入、stream-only 核对、核心补丁；打包（每次从 `.org` 恢复流图） |
| `install.ps1` | 开发安装 / 还原（覆盖 `package.18.00`） |
| `release/install.ps1` | 发行安装器：按组核对、追加新包文件、可卸载（Windows PowerShell 5.1） |

## 输入与输出

- **导出**：`<工作区>\work\<名>\lod<N>\`（ascii、`export.log`），核心 `<工作区>\work\<名>\<NN_OFFSET>.core.pristine`；骨架 `<工作区>\work\skeletons\KEY_skel_<序号>.ascii`。这些都是游戏资源，不随包提供。
- **构建**：`<工作区>\work\karin\v1\`（`ascii\`、`jobs.json`、贴图页、`dds\`、`textures.json`、`fields.json`、`make.log`）；输出 `<工作区>\out\<名>\`（`package.18.00.core.stream`、`streaming_graph.core`、`streaming_links.stream`、`pack.log`）。
- `make_mod_ds2.ps1` 里各组 pristine 的文件名（`14_3BB15CCB` 等）是 1.0.48.0 的原版 span 位置，换版本要按导出重写。

## 边界

- 构建器的常量（槽位网格号、粒子行高、杠杆网格、`SHOWER_HAIR` 等）是这个模型和 1.0.48.0 的值。
- 没有收：远程桌面辅助脚本（截图、按键、窗口），`run_build.cmd`（脱离 SSH 运行构建），实验用的一次性分析脚本，任何游戏数据、模型、发行包。
- 和项目原件的对照见 [迁移验证记录](../VALIDATION.md)。
