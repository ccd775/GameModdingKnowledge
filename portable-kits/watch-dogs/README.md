# 看门狗便携包

先读 [游戏知识](../../games/watch-dogs/README.md) 和 [不用 ZModeler 生成 XBG](../../games/watch-dogs/XBG_WITHOUT_ZMODELER.md)。

本包附带 Karin 1.4、1.5、Karin_Original 0.1.2 实际使用的 XBG 写出器（不需要 ZModeler）、骨架修改、FAT v8 打包和不依赖 texconv 的贴图编码脚本，从 VRM 直接构建整个替换包的通用构建器，以及原有的 XBT 工具。

- **Python 版本**：XBT 工具、FAT 工具、`char01_paths.py` 和 `package_mod.py` 只需标准库，Python 3.10+。XBG 写出器、骨架工具、VRM 构建器和 `xbt_encode.py` 需要 numpy 和 Pillow；钉住的 numpy 2.5 需要 Python 3.12+（测试环境 Python 3.14.0）。
- **运行位置**：以下命令都从交接包根目录执行。
- **不随包提供**：游戏文件、模板 XBG 和底包、模型、ModManager 都由用户自备。

```powershell
python -m pip install -r requirements.txt -r portable-kits/watch-dogs/requirements.txt
$Kit = "portable-kits/watch-dogs/scripts"
```

## XBG：不用 ZModeler

```powershell
# 0. 从上一版运行包解出模板（char01.xbg 的条目名是 E886A8DB）
python -B $Kit/extract_fat8.py ../MyMod/Ref/old_mod.fat ../MyMod/Ref/old_mod

# 1. FBX（模型名含 LOD0 / LOD1）-> char01.xbg；写完自动回读，必须看到 READBACK PASS
python -B $Kit/build_xbg_from_fbx.py --fbx ../MyMod/Work/handoff.fbx --template-xbg ../MyMod/Ref/old_mod/E886A8DB.xbg `
  --output ../MyMod/Work/char01.xbg --report ../MyMod/Work/char01.build.json

# 2. 可选：按模型改骨架（只改位置；未列出的关节随父骨刚性移动；面部骨骼改了也无效）
python -B $Kit/xbg_skeleton_patch.py ../MyMod/Ref/old_mod/E886A8DB.xbg ../MyMod/Work/targets.json ../MyMod/Work/template_fitted.xbg
python -B $Kit/xbg_skeleton.py ../MyMod/Work/template_fitted.xbg --joint "L UpperArm"

# 3. 贴图：PNG -> donor XBT（尺寸、格式、mip 数与 donor 一致），不需要 texconv
python -B $Kit/xbt_encode.py ../MyMod/Work/coat_d.png ../MyMod/Ref/old_mod/<hash>.xbt ../MyMod/Work/<hash>.xbt

# 4. 替换条目重打 FAT/DAT（键可以是 8 位哈希或游戏路径）
python -B $Kit/repack_fat8.py ../MyMod/Ref/old_mod.fat ../MyMod/Output/my_mod.fat `
  graphics/characters/char/char01/char01.xbg=../MyMod/Work/char01.xbg
```

第 4 步的键也可以直接写哈希，例如 `E886A8DB=../MyMod/Work/char01.xbg`。游戏路径的哈希是小写反斜杠路径的 FNV-1 64 位值取低 32 位。

最后把 `my_mod.fat`、`my_mod.dat` 和 `modconfig.json` 放进 zip，用 ModManager 安装。`modconfig.json` 的写法沿用旧包，`packs` 填 FAT 文件名（不带扩展名），见 [部署与回滚](../../games/watch-dogs/DEPLOYMENT_WATCH_DOGS_KARIN.md)。换了 `friendlyId` 和 pack 名的新 mod 可以与旧版并存，但同一时间只能启用一个。

### 检查门

- `build_xbg_from_fbx.py` 输出 `READBACK PASS`：写出后重新解码，所有量化值与意图逐值相等。
- 调色板长度与模板不同时，写出器会重新计算矩阵表前的补零。用 `xbg_skeleton.py` 确认 `bind @ inv_bind` 的残差没有变大。模板自带约 0.04 的残差，来自原版面部和外套物理骨。
- 面数核对：每个 LOD 的面数应等于 FBX 三角化后的面数（报告 JSON 的 `faces`）。
- 实机：读档、外观、基础动作。

`targets.json` 的格式是 `{"关节名": [x, y, z]}`，坐标为 XBG 模型空间（米）：左为 −X，前为 +Y，上为 +Z。

## VRM：直接构建替换包

人形 VRM（1.0 或 0.x）一步生成 char01.xbg、全部 XBT 和 ModManager 包，不经过 Blender、FBX 和 texconv。需要一个现成的 char01 替换包作底包：它的 char01.xbg 必须是 ZModeler 布局（写出器的模板），它的 XBT 是贴图 donor，它引用的私有材质也随之保留。

```powershell
# 0. 看底包里有哪些 char01 条目（列出全部游戏路径和哈希）
python -B $Kit/char01_paths.py

# 1. 只合成贴图和 UV 布局，先检查材质分组（可选）
python -B $Kit/vrm_textures.py ../MyMod/Ref/model.vrm ../MyMod/Work/profile.json ../MyMod/Work/textures

# 2. 构建；--package 时同时写出 FAT/DAT、modconfig.json 和 ZIP
python -B $Kit/build_from_vrm.py --vrm ../MyMod/Ref/model.vrm --profile ../MyMod/Work/profile.json `
  --base-fat ../MyMod/Ref/old_mod.fat --out-dir ../MyMod/Output/build `
  --package --pack my_mod --friendly-id my_mod --name "My Mod" --version 0.1.0

# 3. 只换条目重新打包已有的 XBG/XBT（不重建模型）
python -B $Kit/package_mod.py --base-fat ../MyMod/Ref/old_mod.fat --out-dir ../MyMod/Output/pkg `
  --pack my_mod --friendly-id my_mod --name "My Mod" --version 0.1.1 `
  --replace graphics/characters/char/char01/char01.xbg=../MyMod/Work/char01.xbg
```

构建步骤：从底包取出模板 XBG 和 donor XBT；按配置合成 4 个槽位的贴图并重排 UV；整体缩放到模板腿长，用双四元数蒙皮摆成模板绑定姿势；把 char01 的身体关节移到模型的关节位置（Pelvis 到 Spine2 保留模板位置）；映射权重；写 XBG（LOD1 复用 LOD0）并回读；把贴图编码进对应的 low/high 流 donor。`OUT/build_report.json` 记录输入哈希、缩放、朝向、骨架改动、各部件的槽位和回读结果。输出目录非空时拒绝写入，`--force` 覆盖。

### 配置文件（profile）

`profiles/karin_original.json` 是 Karin_Original 0.1.2 实际使用的配置，可作样板。

```json
{
  "materials": {
    "<VRM 材质名>": {"slot": "head | coat | hair | lashes", "spec": "skin | cloth | hair"}
  },
  "chains": [
    {"match": "<节点名正则>", "under": "<人形骨骼>", "to": "<char01 骨骼>", "shares": [0.0, 0.15, 0.35]},
    {"match": "<节点名正则>", "under": "<人形骨骼>", "to_side": ["L Thigh", "R Thigh"],
     "shares": [0.15, 0.35], "side_width": 0.02}
  ],
  "replace_head_maps": false
}
```

- `materials`：网格用到的每个材质都要列出，否则报错。同一槽位内按 base color 贴图分组：一张原样使用；两张上下拼；三张以上拼成网格，每格四周复制边缘作缝隙。`lashes` 槽只放一张贴图，裁到几何体实际用到的 UV 区域。`spec` 决定外套和头发的高光常量（省略时按槽位取默认）。
- `chains`：非人形骨骼默认把权重并给最近的人形祖先。匹配的规则按链级把 `shares[级]` 比例的权重移给 `to`，或按顶点 X 分给左右两根骨骼（`to_side`；中线处各半，`side_width` 是过渡宽度，单位米，默认 0.02）。规则必须且只能有 `to` 和 `to_side` 之一。链级是向上数到分叉节点或人形骨骼的步数；超出列表时沿用最后一个值。
- `replace_head_maps`：默认保留底包头部的法线和高光，只换头部颜色贴图。
- 固定规则：眼骨和下巴并入 `Head`（面部骨骼位置会被动画重置）；上臂、前臂按 Karin 1.3 实测比例分给扭转骨；手部权重向指根渐变到掌骨。

### 检查门

- 输出 `READBACK PASS`；`build_report.json` 的 `facing` 与模型的 VRM 版本一致（1.0 为 +Z，0.x 自动转 180°）。
- `layout_warnings` 为空，或已逐条确认。
- `--package` 时逐条回读新包，除替换的条目外全部逐字节保留。
- 实机：读档、脸和眼睛、基础动作、双手持枪、长头发和裙子在走路下蹲时的穿模。

## XBT：原有工具

```powershell
python -B $Kit/xbt_tool.py inspect ../MyMod/Ref/low.xbt
python -B $Kit/xbt_tool.py extract ../MyMod/Ref/low.xbt ../MyMod/Work/low.dds
python -B $Kit/xbt_tool.py inject ../MyMod/Ref/low.xbt ../MyMod/Work/replacement.dds ../MyMod/Work/new.xbt
python -B $Kit/audit_xbt_templates.py ../MyMod/Ref/textures ../MyMod/Work/xbt-audit
python -B $Kit/build_xbt_pair.py ../MyMod/Ref/source.png ../MyMod/Ref/low.xbt ../MyMod/Ref/low_high.xbt ../MyMod/Work/pair --texconv $Texconv --expected-texconv-sha256 $TexconvSHA256
```

注入保留 donor header，拒绝 DDS 尺寸、mip、格式不一致的输入，也拒绝覆盖已有输出；`--force` 只用于格式实验。pair builder 限定 XBT 123 + legacy DXT1/DXT5，low 为完整 mip，high 为单 mip。模板审计只在同一目录内配对，不递归猜测。

## 脚本

| 脚本 | 职责 |
| --- | --- |
| `build_xbg_from_fbx.py` | 入口：FBX 两个 LOD -> char01.xbg，写后逐值回读，拒绝覆盖已有输出 |
| `xbg_model.py` | XBG 结构读取（材质表、调色板、节点表、LOD 描述符、GPU 缓冲区） |
| `xbg_codec.py` | 顶点编解码与整文件写出；以模板保留材质表、骨架、矩阵表和物理块，并重新计算矩阵表的 16 字节对齐 |
| `fbx_reader.py`、`fbx_mesh.py` | 纯 Python 二进制 FBX 7.x 读取，按角点展开网格、UV、颜色、材质和蒙皮 |
| `fbx_to_xbg.py` | ZModeler 约定的转换：坐标 `(−x, −y, z)`、绕序反转、v 翻转、前 4 个权重量化、按材质名匹配模板槽位 |
| `xbg_skeleton.py` | 读取绑定姿势和逆绑定矩阵，做姿势和线性蒙皮；命令行检查残差 |
| `xbg_skeleton_patch.py` | 移动关节并同步更新节点局部平移与逆绑定矩阵；写后验证，失败时删除输出 |
| `xbt_encode.py` | PNG -> donor XBT，Pillow 逐级 DXT1/DXT5 编码，保留 donor 文件头 |
| `extract_fat8.py`、`repack_fat8.py` | 未压缩 FAT v8 / DAT 解包与重打包；条目 16 字节对齐，键可用游戏路径 |
| `build_from_vrm.py` | 入口：VRM + 配置 + 底包 -> char01.xbg、XBT、可选 ModManager 包；写 `build_report.json` |
| `vrm_model.py` | 最小 glTF/VRM 读取（节点、蒙皮、网格、材质、贴图）；VRM 0.x 拇指改用 1.0 命名 |
| `vrm_fit.py` | 朝向判断、按腿长缩放、双四元数摆姿势、计算 char01 关节的新位置 |
| `vrm_weights.py` | 人形骨骼权重映射、扭转骨比例、掌骨渐变、配置里的链规则 |
| `vrm_textures.py` | 按配置合成 4 个槽位的贴图和 UV 布局（`layout.json`） |
| `vrm_assemble.py` | 把摆好姿势的部件转成写出器输入（子网格按槽位合并） |
| `char01_paths.py` | char01 的 XBG/XBT 游戏路径、low/high 流和 FAT 哈希 |
| `package_mod.py` | 底包换条目、写 modconfig.json（CRLF）、固定时间戳的可复现 ZIP |
| `xbt_tool.py`、`audit_xbt_templates.py`、`build_xbt_pair.py` | 原有 XBT 解析、注入、模板审计和 texconv 配对构建 |

## 限制

- 只支持 char01 骨架和模板里的材质槽。每个顶点最多 4 个权重，每个子网格最多 65,535 个顶点，调色板最多 255 根骨骼；超出时直接报错，不会静默拆分。
- VRM 构建器只对 Karin_Original（VRM 1.0）做过逐字节核对：用样板配置重建的 XBG、15 个 XBT、FAT/DAT、modconfig 和 ZIP 与实机认可的 0.1.2 完全一致。VRM 0.x 和其他模型只有合成数据测试，未经实机。
- VRM 构建器不做表情、视线和次级物理：脸是刚性的，嘴和眼睛不会动；头发、裙子只随骨骼按比例摆动。
- 输出与 ZModeler 语义一致，但不逐字节一致。
- 测试只用合成数据：`python -B tests/test_portable_tools.py`。
