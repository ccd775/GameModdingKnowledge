# 看门狗便携包

先读 [游戏知识](../../games/watch-dogs/README.md) 和 [不用 ZModeler 生成 XBG](../../games/watch-dogs/XBG_WITHOUT_ZMODELER.md)。

本包附带：

- Karin 1.4、1.5、Karin_Original 0.1.2 实际使用的 XBG 写出器（不需要 ZModeler）、骨架修改、FAT v8 打包，以及不依赖 texconv 的贴图编码脚本；
- 从 VRM 直接构建整个替换包的通用构建器，含物理和面部表情；
- 给已有 XBG 加表情的 `xbg_face.py`；
- Windy City II 兼容用的私有头部处理；
- 原有的 XBT 工具。

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
- 固定规则：
  - 没有 `face` 段时，眼骨和下巴并入 `Head`（面部骨骼的位置由 dpdx 重置，见下文"面部表情"）；
  - 上臂、前臂按 Karin 1.3 实测比例分给扭转骨；
  - 手部权重向指根渐变到掌骨。

Karin City Noir 加的可选项（2026-10-07，部分实机，见 [char01 物理](../../games/watch-dogs/PHYSICS.md) §7）：

- 骨链悬挂：
  - `hang`：列出的关节及其子树在重摆姿势时保持 T-pose 的朝向，用于挂在上臂下、要竖直下垂的面板；
  - `hang_offset [外, 后]`（米）：这些子树整体外移、后移；
  - `hang_tilt`（度）：整体后倾（实测不采用）。
- `weight_remap`：`[{"part": 部件名前缀, "from": [VRM 关节], "to": VRM 关节}]`。在拟合之后把权重改挂，不改绑定形状，例如让夹克的手肘区不跟前臂走。
- 贴图：
  - `repack_slots`：把某槽位各材质在各 atlas 页上的 UV 岛逐个拷进一张画布，并改写顶点 UV。适合多个槽位共用 atlas 页的模型；
  - `repack_density {"部件名前缀": 倍数}`：重排时放大某些部件的像素密度；
  - `texture_size {"槽位": [宽, 高]}`：让漫反射比 donor 大，只改 DDS 头和低流的 0x19 字节，布局沿用 char01 已有的贴图。实机：头发 512→1024 后尾巴显示正常；同一版本里发带"镂空"的原因还没有确定；
  - `crop_slots`：只按 UV 包围盒裁剪（对散布的岛无效，保留备用）。

### 检查门

- 输出 `READBACK PASS`；`build_report.json` 的 `facing` 与模型的 VRM 版本一致（1.0 为 +Z，0.x 自动转 180°）。
- `layout_warnings` 为空，或已逐条确认。
- `--package` 时逐条回读新包，除替换的条目外全部逐字节保留。
- 实机：读档、脸和眼睛、基础动作、双手持枪、长头发和裙子在走路下蹲时的穿模。

## 物理：链与大衣布料

VRM 构建器的配置文件加 `physics` 段后，构建时会做三件事：

- 在闲置物理节点上搭链：头发、耳朵、发带、尾巴等；
- 把裙子或大衣挂到模板自带的大衣布料上；
- 给指定部件加背面。

格式、实测行为和被否定的做法见 [char01 物理](../../games/watch-dogs/PHYSICS.md)。

```powershell
# 可选：从游戏角色 XBG 导出碰撞体（例如 Nicky 的 char10.xbg 里的马尾和刘海胶囊）；仓库不收录游戏数据
python -B $Kit/xbg_physics.py export-colliders --xbg ../MyMod/Ref/char10.xbg --out ../MyMod/Work/colliders.json
# 构建：配置里有 physics 段即生效；--colliders 可选，缺省时用骨架推出的胶囊
python -B $Kit/build_from_vrm.py --vrm ../MyMod/Source/model.vrm --profile ../portable-kits/watch-dogs/profiles/karin_original_1_0_0.json `
  --base-fat ../MyMod/Ref/karin_replacer.fat --colliders ../MyMod/Work/colliders.json --out-dir ../MyMod/Work/build
```

`physics` 段（完整字段见 `vrm_physics.py` 文件头）：

- `chains`：每条链写明起始关节、挂点骨骼（`Head`、`Pelvis` 等）、碰撞组，以及重力、阻尼、拉力、半径、节点池。可选：
  - `drop_end`：去掉无权重的末端关节；
  - `pin_parent`：把起始关节的父关节作为固定根。只有一节的链靠它才能摆动。
- `cloth`：
  - `joints`：裙子关节前缀；
  - `gravity`、`damping_scale`：布料参数；
  - `k`、`sigma`：每个顶点混合几个粒子，以及衰减；
  - `thigh_radius`：可选，加大大腿胶囊半径；
  - `hang_from_pelvis`：短裙必开，把整块布料挂到胯部。
  - 披肩用的选项（Karin City Noir）：
    - `roots`：显式列出链根；
    - `remap_z [[z0, z1], [z0', z1']]`：把粒子格按高度线性映射；
    - `anchor_bone`：所有粒子改挂这根骨；
    - `capsule_radius {骨骼: 半径}`：改布料的胶囊半径（`thigh_radius` 是它的特例）；
    - `clear_capsules [骨骼]`：把静止时落在这些胶囊里的粒子推出去。
- `colliders`：碰撞组。每项可以是：
  - `{"from": 导出对象名, "mirror": [骨骼], "fallback": "body"|"face"}`；
  - `{"legs": true}`（模板布料的大腿、骨盆、小腿胶囊）；
  - `{"derived": ...}`（由骨架推出的胶囊）；
  - `{"arm": "L"|"R", "radius": r}`（上臂、前臂胶囊）。
- `double_sided`：要加背面的 VRM 部件名，例如 `skirt/0`。

检查门：

- 输出 `READBACK PASS`。
- `build_report.json` 的 `physics` 中，保留对象数、去掉的表项、`global_cut`、改挂的粒子数与预期一致。
- 每条链的 `clearance_cm` 为正，即静止时不在碰撞体里。
- 实机检查：
  - 跑动、急停、转身、蹲下、上坡；
  - 各部件是否抽搐，尾巴和裙子是否黏在一起；
  - 下蹲时是否露出大腿。

## 面部表情：眨眼、视线、张嘴

原理、格式和实测见 [面部表情](../../games/watch-dogs/FACE.md)。

- 需要原版 `char01_facial_definition.dpdx`（FAT 哈希 `28E502D9`），从游戏的 `windy_city.fat` 解出，XMemCompress 压缩，仓库不收录。
- 构建器写出改好的副本，打包时作为**新条目**加进包里。底包里原本没有这个条目。

```powershell
# VRM 构建：配置文件加 face 段（样板 profiles/karin_original_face.json），并给出原版 dpdx
python -B $Kit/build_from_vrm.py --vrm ../MyMod/Source/model.vrm --profile ../MyMod/Work/profile_face.json `
  --base-fat ../MyMod/Ref/old_mod.fat --colliders ../MyMod/Work/colliders.json `
  --facial-definition ../MyMod/Ref/char01_facial_definition.dpdx --out-dir ../MyMod/Work/build --package ...

# 已有的 char01.xbg（不是本构建器做的），脸和某个 VRM 的脸是同一个网格（样板 profiles/karin_pt_face.json）
python -B $Kit/xbg_face.py --xbg ../MyMod/Ref/old_char01.xbg --vrm ../MyMod/Source/model.vrm `
  --profile ../MyMod/Work/xbg_face.json --facial-definition ../MyMod/Ref/char01_facial_definition.dpdx --out-dir ../MyMod/Work/face

# 离线检查：每个控制在权重 1 时移动多少顶点、最多几毫米；静止位移必须为 0
python -B $Kit/face_preview.py ../MyMod/Work/build --controls 32 36 55 42 50
python -B $Kit/dpdx_format.py ../MyMod/Work/build/char01_facial_definition.dpdx --xbg ../MyMod/Work/build/char01.xbg
```

`face` 段：

- `blink`：`L` / `R` 指定左右眨眼的形态键，或用 `key` 指定一个、按左右拆开。另有：
  - `gain`：放大目标；
  - `follow_scale`：上眼睑跟随向下看等控制的比例，默认 0.5。
- `jaw`：`key`（张嘴键）、`gain`。
- `gaze`：`keys`（Look 键）、`gain`：在拟合出的眼骨份额上再乘的倍数，Karin 用 2.0。

三项都可省略。`xbg_face.py` 的配置另需：
- `xbg_face_material`：XBG 里脸的材质序号；
- `vrm_face_materials`：VRM 里脸的材质名；
- 可选 `eye_nodes {"L": 节点名, "R": 节点名}`。

`xbg_face.py` 用相似变换把 VRM 的脸对到 XBG 的脸上，再带过形态键。只挪眼骨和下巴，每个顶点相同的 LOD 都重写脸的权重，其余逐值不变。

检查门：

- `READBACK PASS`（`xbg_face.py` 自带回读）。
- dpdx 的静止平移与 XBG 一致：构建时自动检查，不一致直接失败。
- `build_report.json` 的 `face` 段：
  - `blink.*.relative_residual` 约 0.07，`edge_reach` 接近 1；
  - 每个 Look 键配到的控制和相关系数（不低于 0.5）；
  - `xbg_face.py` 还要看 `match` 的中位和最大误差，以及有没有未匹配的顶点。
- `face_preview.py`：静止位移 0，眨眼控制移动的毫米数与形态键相当。
- 实机：眨眼是否闭严、视线、张嘴，以及向下看时眼睑压得多不多。

## Windy City II：私有头部材质

The Fall of Windy City II 改写 Aiden 的头部材质，替换 mod 的脸会发黑。`private_head.py` 对已构建的包做后处理：

- 头部槽改用私有材质；
- 用三张单文件的私有头部贴图；
- 删掉 Aiden 的 6 个头部贴图条目。

见 [Windy City II 兼容](../../games/watch-dogs/WINDY_CITY_2_COMPAT.md)。

```powershell
# 原版头部材质 graphics\_materials\mkamelaquino-m-20130115113413.material.bin 从游戏里解出，仓库不收录
python -B $Kit/private_head.py ../MyMod/Output/my_mod.fat ../MyMod/Output/private `
  --vanilla-material ../MyMod/Ref/mkamelaquino-m-20130115113413.material.bin
```

在打包脚本里，也可以用 `package_mod.package(..., transform=lambda e: private_head.privatize(e, material))` 直接处理。

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
| `smu_format.py` | 物理块里 SMU 对象（链、jiggle；布料的头部和碰撞表）的读写，矩阵按文件偏移对齐 |
| `xbg_physics.py` | 在闲置节点上搭链、移动或改挂节点并重写逆绑定；定位大衣布料、碰撞胶囊和表；粒子外推、按角度和高度分配权重；碰撞组；`export-colliders` 命令 |
| `vrm_physics.py` | VRM 构建器的 `physics` 段：链、裙子或大衣挂到布料上、背面副本 |
| `dpdx_format.py` | 面部定义 `.dpdx` 读写（逐字节往返）、smallest-three 四元数、纯平移增量；命令行打印各表，并与 XBG 的静止姿势对比 |
| `vrm_face.py` | VRM 构建器的 `face` 段：眼骨定位，平移眼睑（每个顶点解非负份额），下巴枢轴搜索，视线份额；改写 dpdx 并校验 |
| `xbg_face.py` | 入口：给已有的 char01.xbg 加表情。VRM 脸相似变换对齐、带过形态键、只挪眼骨和下巴、重写各 LOD 的脸权重 |
| `face_preview.py` | 离线预览：在构建好的 XBG 和 dpdx 上施加控制并蒙皮，可写 OBJ |
| `private_head.py` | 私有头部材质和单文件私有头部贴图，删掉 Aiden 的头部贴图条目（Windy City II 兼容） |
| `xbt_tool.py`、`audit_xbt_templates.py`、`build_xbt_pair.py` | 原有 XBT 解析、注入、模板审计和 texconv 配对构建 |

## 限制

- 只支持 char01 骨架和模板里的材质槽。每个顶点最多 4 个权重，每个子网格最多 65,535 个顶点，调色板最多 255 根骨骼；超出时直接报错，不会静默拆分。
- VRM 构建器只对 Karin_Original（VRM 1.0）做过逐字节核对：用样板配置重建的 XBG、15 个 XBT、FAT/DAT、modconfig 和 ZIP 与实机认可的 0.1.2 完全一致。VRM 0.x 和其他模型只有合成数据测试，未经实机。
- 面部表情：
  - 只做了眨眼、视线、张嘴，上唇不动；
  - 实机只测过第一版（Karin_Original 1.1.0-test）：嘴会动，眨眼闭不严，眼珠几乎不动；
  - 现在的平移眼睑和视线 ×2（1.1.1-test、蓝白 Karin 1.7.0-test）只有离线验证；
  - 没有 `face` 段时，脸是刚性的。
- 没有 `physics` 段时，头发和裙子只随骨骼按比例摆动。
- 物理：
  - `profiles/karin_original_1_0_0.json` 配合从 char10.xbg 导出的碰撞体，重建的 char01.xbg 与实机验收的 Karin_Original 1.0.0 逐字节相同；
  - 游戏的链只会原地晃动，跑动时不会往后飘；
  - 不给碰撞体文件时，用骨架推出的胶囊代替，这种胶囊未经实机验证；
  - 只支持带 Aiden 原版物理块的模板。
- 输出与 ZModeler 语义一致，但不逐字节一致。
- 测试只用合成数据：`python -B tests/test_portable_tools.py`。
