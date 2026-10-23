# 巫师3 次世代版（The Witcher 3 Remastered）便携包

先读 [游戏知识](../../games/the-witcher-3/README.md) 和 [构建流水线](../../games/the-witcher-3/BUILD_PIPELINE.md)。bundle、metadata.store、CR2W 与物品模板的约定见
[技术合同](../../games/the-witcher-3/TECHNICAL_CONTRACTS.md)；比例与肩部见 [角色拟合](../../games/the-witcher-3/CHARACTER_FIT.md)；dyng 见
[物理](../../games/the-witcher-3/PHYSICS.md)；表情见 [表情](../../games/the-witcher-3/FACE.md)。

这是 Karin_Original 替换杰洛特的 mod（v0.4.3 用户确认，v0.4.4 待实测）实际使用的工具：v5 bundle 与 v7 metadata.store 读写、WolvenKit 骨名修复、
物品模板 / dyng / w3fac 生成器、Blender 构建脚本（拟合、贴图、dyng 规格、表情求解、导出）、离线检查脚本，以及准备与构建的 PowerShell 流水线。

- **游戏版本：** PC 次世代版 `witcher3.exe` 5.0.1048522（菜单 v5.01，DX12），内容在 `content\content0`，bundle 头 v5，`content\metadata.store` v7。
- **mod 安装：** `<游戏>\mods\modKarinReplacer\content\blob0.bundle` + 同目录的 `metadata.store`。不需要脚本合并。
- **Blender：** 5.0，装 Witcher3-Blender-Tools v1.1.0（dingdio，`witcher3_tools.zip`）作为扩展（模块名 `bl_ext.user_default.witcher3_tools`，
  别的装法用 `W3_ADDON_MODULE` 指定）。脚本用 Blender 自带的 Python 和 numpy；xbm 写出调用 texconv（WIC），所以只在 Windows 上测过。
- **WolvenKit：** 7 nightly `7.2.0-nightly.2026-10-14`，只用 CLI。`prepare.ps1` 把解压后的文件夹复制到工作目录，并把 `.exe.config` 的 .NET sku 改成 4.8。
- **Python：** 3.10 或更高；`scripts/` 下除 `karin_face.py` 和 `checks/rule_check.py`（numpy）外只用标准库。
- **PowerShell：** 7（`pwsh`）。

## 环境变量

| 变量 | 用在 | 内容 |
| --- | --- | --- |
| `W3_GAME_DIR` | `prepare.ps1`、`pipeline.ps1`（Blender 阶段和 `-Deploy`）、Blender 脚本、`regen_metadata_compare.py` | 游戏目录（含 `bin\x64_dx12`、`content\content0\bundles`）；或 `-GameDir` |
| `W3_WORK` | 全部 | 工作目录，放在同步盘之外，`prepare.ps1` 填充：`uncook\`、`extract_items\`、`scratch\`（`all_bundles.tsv`、模板 JSON、日志、报告）、`build\`、`blend\`、`karin_src\textures\`、`tools\wk7\`；或 `-WorkRoot` |
| `W3_WOLVENKIT_DIR` | `prepare.ps1`（工作目录里还没有 `tools\wk7` 时） | 解压后的 WolvenKit 7 nightly 文件夹（含 `WolvenKit.CLI.exe`）；或 `-WolvenKitDir` |
| `W3_BLENDER` | `pipeline.ps1` | Blender 5.0 的 `blender.exe`；或 `-Blender` |
| `W3_SOURCE_FBX` | `karin_build.py` | 源模型 FBX（项目用的是 `Karin(Clone)_BlenderSafe.fbx`）；也可以在 JSON 参数里给 `karin_fbx` |
| `W3_ADDON_MODULE` | Blender 脚本（可选） | 插件的模块名，默认 `bl_ext.user_default.witcher3_tools` |

缺少必需的变量时，Python 工具报错并说出变量名（`scripts/w3paths.py`），不会退回到哪个本机路径；PowerShell 工具在做任何事之前报错。

## 构建流程

### 0. 一次性准备

```powershell
$Kit = "portable-kits/the-witcher-3"
$env:W3_GAME_DIR = "<游戏目录>"
$env:W3_WORK = "<工作目录，在同步盘之外>"
$env:W3_WOLVENKIT_DIR = "<解压后的 WolvenKit 7 nightly 文件夹>"
pwsh -NoProfile -File $Kit/tools/prepare.ps1          # 末行 prepared
```

### 1. 构建

```powershell
$env:W3_BLENDER = "<Blender 5.0 目录>\blender.exe"
$env:W3_SOURCE_FBX = "<源模型 FBX>"
pwsh -NoProfile -File $Kit/tools/pipeline.ps1          # 末尾打印 blob0.bundle / metadata.store 的长度和 SHA-256
#   -BuildArgs '{"stage":"all","tail_scale":0.75}'   改 karin_build.py 的 CFG（任何键）；{"physics":false} / {"face":false} 关掉物理 / 表情
#   -SkipBlender                                     只重做资源、模板和打包（改了 POSE_GAIN、风 / 重力 / 阻尼时）
#   -Wind 0 -Gravity 0 -Dampening -1 -Fur drop       dyng 约束参数（默认即 v0.4.4 的值；-Dampening < 0 不写）
#   -ModName modKarinReplacer                        mod 文件夹名
#   -Deploy                                          结束正在运行的游戏、复制到 <游戏>\mods\<ModName>\content、启动游戏
```

产物：`<W3_WORK>\build\mods\<ModName>\content\{blob0.bundle, metadata.store}`；Blender 日志 `scratch\build.log`，报告 `scratch\karin_build_report.json`，
可在 Blender 里打开的 `blend\karin_fit.blend`。`pipeline.ps1` 在任何一步失败时停下（Blender 日志里没有 `[karin_build] DONE` 也算失败）。

### 2. 离线检查

```powershell
$B = $env:W3_BLENDER; $Blend = "$env:W3_WORK\blend\karin_fit.blend"; $Spec = "$env:W3_WORK\build\karin_dyng_spec.json"
python -B $Kit/scripts/checks/rule_check.py $Spec                         # 每个 look-at 节点 errZrule 应为 0
& $B -b $Blend --python $Kit/scripts/checks/blender/idle_view.py -- $Spec <输出前缀>       # 目标形状：全身，右侧到背后 5 个角度，bind / idle
& $B -b $Blend --python $Kit/scripts/checks/blender/idle_head.py -- $Spec <输出前缀>       # 头部特写：正面、两侧、斜侧 6 个角度，bind / idle
& $B -b $Blend --python $Kit/scripts/checks/blender/skirt_walk_sink.py -- $Spec <输出前缀> `
    locomotion_walk_cycle_slow_forward,locomotion_walk_cycle_fast_forward,walk,locomotion_run_cycle_slow_forward,locomotion_sprint_cycle_forward 8
& $B -b $Blend --python $Kit/scripts/checks/blender/face_geom.py -- $Spec  # 头发离脸距离、头部碰撞中心
& $B --background --factory-startup --python $Kit/scripts/blender/karin_preview.py -- '{"out":"<目录>"}'
& $B --background --factory-startup --python $Kit/scripts/checks/blender/cmp_w2mesh.py -- `
    "$env:W3_WORK\uncook\characters\base_entities\man_base\man_base.w2rig" <参照 w2mesh> <新 w2mesh>
python -B $Kit/scripts/checks/regen_metadata_compare.py                  # 换游戏版本后：重建原版 store 并逐表比较
```

Blender 的输出路径用绝对路径（相对路径按 blend 文件所在目录解析）。

### 3. 发行

把 `content` 下的两个文件放进 `mods/modKarinReplacer/content/`，加 README（改动、测试状态、已知限制）、SHA256.txt 和安装说明，打成 zip
（结构与安装说明的要点见 [验证与发布](../../games/the-witcher-3/VALIDATION_AND_RELEASE.md) §3）。

## 脚本

| 脚本 | 用法 | 说明 |
| --- | --- | --- |
| `scripts/w3bundle.py` | `list <bundle或目录>… [-p 通配] [-v]`、`extract <bundle或目录>… -p <通配>… -o <目录> [--overwrite]`、`pack <目录> <out.bundle> [--compression 1]` | v5 bundle；读也支持 v3；lz4 / snappy 压缩的条目要装 `lz4` / `cramjam` |
| `scripts/w3metadata_write.py` | `<content 目录> [-o out]` | 给目录下全部 `.bundle` 写 v7 `metadata.store` |
| `scripts/w3metadata.py` | `<metadata.store>` | 打印 store 的各表（调试） |
| `scripts/build_mod.py` | `stage <staging> --empty <w2ent> [--head <w2ent>] [--coif <w2ent>] [--extra <目录>]… [--listing <tsv>]`；`pack <staging> <mod 目录>` | 按 bundle 清单铺满杰洛特的全部物品模板（剑鞘除外）并打包 |
| `scripts/fix_cr2w_skeleton_names.py` | `<in> [<out>]` | WolvenKit 写出的 `SSkeletonBone` / `SSkeletonTrack` 名字改回原版 String 编码，重算大小与 CRC |
| `scripts/make_empty_item_template.py` | `<t_01_mg__body.w2ent.json> <out.json>` | 空 `CItemEntity` |
| `scripts/make_mesh_item_template.py` | `<in.json> <out.json> <mesh depot> <组件名> minx miny minz maxx maxy maxz` | 单网格物品（无物理时的回退布局） |
| `scripts/make_dangle_item_template.py` | `<c_01_mg__witcher.w2ent.json> <out.json> <dyng> <mesh> <stub> [--fur stub\|drop] [--bbox …] [--wind w] [--gravity g] [--dampening d]` | 发型物品：dangle + Karin 网格 |
| `scripts/make_head_item_template.py` | `<h_01_mg__geralt.w2ent.json> <out.json> <w3fac> <face mesh> <stub> [--bbox …]` | 头部物品：Karin 的 mimic 脸 |
| `scripts/make_dyng.py` | `<dyng 规格> <c_02_mg__half_tail.w3dyng.json> <out.json>` | dyng 资源 JSON |
| `scripts/make_w3fac.py` | `<表情规格> <h_01_mg__geralt.w3fac.json> <out.json>` | w3fac JSON，按 `face_pose_map.POSE_GAIN` 缩放 |
| `scripts/face_pose_map.py` | 模块 | W3 表情姿势 → Karin 形状键、口型增益（案例值） |
| `scripts/karin_face.py` | 模块（numpy） | 平移蒙皮分解：k-means 出骨 + NNLS 权重 / 最小二乘平移交替 |
| `scripts/w3paths.py` | 模块 | 环境变量 → 路径（新写的文件） |
| `scripts/blender/karin_build.py` | `blender --background --factory-startup --python … -- '<JSON>'` | 拟合、贴图、dyng 规格、表情、导出；`DYNG_GROUPS`、`CFG` 是 Karin 的案例值 |
| `scripts/blender/make_stub_mesh.py` | `… -- '{"out":"<w2mesh>","bone":"neck"}'` | 0.1 mm 存根网格 |
| `scripts/blender/karin_preview.py` | `… -- '{"out":"<目录>"}'` | 导出网格重新导入、与杰洛特原版身体对照的预览 |
| `scripts/checks/…` | 见上文 §2 | 离线检查；`skirt_walk_sink.py`、`face_geom.py` 里的骨名 / 组名是 Karin 的 |
| `tools/prepare.ps1`、`tools/pipeline.ps1`、`tools/wk.ps1` | 见上文 | 准备、构建、WolvenKit CLI 包装（`-Mode cr2w2json\|json2cr2w`、`-Exe`） |

## 换一个模型时

- `karin_build.py` 的骨名映射（`HUMANOID_TO_W3`、`nearest_humanoid`）、`DYNG_GROUPS` 的链根名、贴图计划（材质名 → 贴图）、裙子 / 脸的网格名、
  `face_pose_map.POSE_MAP` 的形状键名都是 Karin 的，要按新模型改；比例参数要重新调（[角色拟合](../../games/the-witcher-3/CHARACTER_FIT.md) §6）。
- 物品模板生成器、bundle / store 工具、骨名修复、dyng / w3fac 写出与模型无关。

## 边界

本包已在 2026-10-23 从一个全新的工作目录跑通 `prepare.ps1` + `pipeline.ps1`（含 Blender、不部署），产物与 v0.4.4 的内容等价（[VALIDATION.md](../VALIDATION.md)）；
`-Deploy` 和游戏内测试没有用便携包重跑（项目里用原脚本跑过）。不带游戏资源、源模型、插件、WolvenKit 或 texconv。
