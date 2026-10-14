# 漫威蜘蛛侠2（Marvel's Spider-Man 2）便携包

先读 [游戏知识](../../games/marvels-spider-man-2/README.md) 和 [构建流程](../../games/marvels-spider-man-2/BUILD_PIPELINE.md)。toc、DAT1、`.model`、`.texture`、`.material`、`.actor` 和 `.stage` 的约定见 [技术合同](../../games/marvels-spider-man-2/TECHNICAL_CONTRACTS.md)；动力学链、距离门控和头部载体见 [物理](../../games/marvels-spider-man-2/PHYSICS.md)；拟合、裙子权重和头部比例见 [拟合与绑定](../../games/marvels-spider-man-2/CHARACTER_FIT.md)。

这是 Karin_Original 替换 Peter 和 Miles 的 Mod（v1、v2）实际使用的 Python 工具：i30 格式读写（toc / DAT1、`.model`、`.texture`、`.material`、`.actor`）、`.stage` 读写和不依赖 Overstrike 的安装器、名字索引与解包、VRM 拟合、批量构建、表情绑定、动力学链、头部载体，以及离线验收脚本。

- **游戏版本：** PC 版，启动器显示 v1.130.1.0；`toc` SHA-1 `318f4345f3a1`（SHA-256 `91bc0d4a…766b`）。资产 id、段布局和 actor 字段都随 build 变化，换版本前先重跑下面的离线检查。
- **Mod 安装：** 构建结果是 Overstrike 的 `.stage`（`format_version` 2，`game` MSM2）。可以用 Overstrike 装，也可以用本包的 `sm2_install.py`：第一次安装时备份 `toc.BAK`，之后每次都从 `toc.BAK` 重来；第 i 个包写成 `<游戏目录>\d\mods\mod<i>`，按命令行顺序后装的覆盖先装的；`uninstall` 用 `toc.BAK` 还原 `toc` 并删掉 `d\mods\mod*`。
- **ALERT（不随包）：** Tkachov/ALERT（GPLv3）的 `dat1lib` 负责读 toc 和算 CRC32 / CRC64。项目用的是提交 `bc90ed9b53fbcaa3b7acf94b36f00e77eab0dacb`。自己 `git clone https://github.com/Tkachov/ALERT` 后检出这个提交，用 `SM2_ALERT` 指向检出目录。脚本在用到时才导入 `dat1lib`，所以 `--help`、安装器、`.stage` 读写和 `.actor` 编解码不需要它；读游戏 toc、算新名字的哈希（追加关节、改材质路径、actor 新字符串）时需要。
- **Python：** 3.10 或更高。安装器（`sm2_install.py`、`sm2_stage.py`、`sm2_dat1.py`、`crc64_table.py`）、索引、查找、解包和 `.actor` 编解码只用标准库；拟合、构建和离线检查另需 numpy、Pillow、scipy、etcpak（`requirements.txt`，钉的 numpy 2.5.2 要 Python 3.12 或更高）。scipy 只在拟合（`sm2_karin_geo.py`）和 `sm2_pose_check.py` 里用，etcpak 只在压贴图（`sm2_assets.py`，经 `sm2_batch.py`）时用，都是用到时才导入。本次在 3.14.0、numpy 2.5.2、Pillow 12.3.0、scipy 1.18.0、etcpak 0.9.15 上测试。
- **工作目录放在仓库外：** `SM2_WORK` 和 `SM2_ALERT` 的默认值都在本包目录里（`scripts/` 的上一级），在仓库里运行时一定要设到仓库外，否则解出的游戏资产、拟合结果和 ALERT 源码会落进本包。
- **运行位置：** 以下命令都从交接包根目录执行，按 PowerShell 7（`pwsh`）写；脚本本身不限 Windows。

## 环境变量与参数

| 变量 | 读的脚本 | 含义 |
| --- | --- | --- |
| `SM2_GAME` | `sm2_common.py` 的 `load_toc()`，经它影响所有读游戏的命令；`sm2_index.py`（读 `dagstr`）；`sm2_batch.py`（读 toc 里的贴图 meta） | 游戏目录（含 `toc`、`dagstr`），只读。没有默认值，没设时报错 |
| `SM2_WORK` | `sm2_common.py`、`sm2_karin_geo.py`，经它们影响全部流水线脚本 | 工作目录：`native/`（解出的原版资产和 `asset_index.json`）、`reports/`（`suit_models.json`、`targets.json`、`masked_suits.json`）、`build_<target>/`、`build_sig/`、`build_sig_dyn/`、`build_face/`。默认是本包目录 |
| `SM2_ALERT` | `sm2_common.py`、`i30_actor.py`、`i30_joints.py`、`sm2_build_model.py` | ALERT 检出目录（下面有 `dat1lib/`）。默认 `<本包>/ext/ALERT`；找不到 `dat1lib` 时报错并给出仓库地址 |
| `SM2_VRM` | `sm2_karin_geo.py`（`--vrm` 的默认值）、`sm2_batch.py`、`sm2_face.py`、`sm2_pose_check.py` | 源 VRM。项目用的是 Karin_Original 的 `Karin(Clone).vrm`（SHA-256 `8f930404…2d87`），模型不随包提供。没设时报错 |

其他参数：`sm2_install.py --game <游戏目录>`（必填）；`sm2_batch.py --name` / `--author`（`.stage` 的 `info.json`，作者默认空）；`sm2_head_carrier.py --name` / `--description`（默认沿用 `--base` 包的）；`sm2_extract.py --out`（默认 `<SM2_WORK>/native`）。

## 构建流程

### 0. 准备

```powershell
python -m pip install -r requirements.txt -r portable-kits/marvels-spider-man-2/requirements.txt
$S = "portable-kits/marvels-spider-man-2/scripts"
$env:SM2_GAME  = "<游戏目录>"
$env:SM2_ALERT = "<ALERT 检出目录>"            # 提交 bc90ed9b53fbcaa3b7acf94b36f00e77eab0dacb
$env:SM2_WORK  = "../MyMod/Work"               # 仓库外
$env:SM2_VRM   = "<源模型>.vrm"
$W = $env:SM2_WORK
New-Item -ItemType Directory -Force "$W/native", "$W/reports", "$W/builds" | Out-Null

python -B $S/sm2_index.py                      # 一次：dagstr 里的名字 -> toc 资产表，写 <W>/native/asset_index.json
python -B $S/sm2_find.py "hero_spiderman_advanced" --ext .model     # 按正则查资产（路径用 /）
python -B $S/sm2_extract.py characters/hero/hero_spiderman_advanced/hero_spiderman_advanced.model   # 解到 <W>/native/
python -B $S/suit_models.py                    # 战衣链：奖励 loadout -> 物品 loadout -> 外观配置 -> .model，写 reports/suit_models.json
python -B $S/survey_targets.py                 # 目标模型、look、骨架签名，写 reports/targets.json（项目：108 个目标，7 种签名）
```

### 1. 单个目标的拟合与检查（可选）

```powershell
python -B $S/sm2_karin_geo.py --target peter   # 重摆 + TPS 拟合 + 权重 -> <W>/build_peter/karin_geo.npz；模型要先 sm2_extract 到 native/
python -B $S/sm2_preview.py --target peter     # 拟合结果与原版 LOD0 的正 / 侧对照图
python -B $S/sm2_build_model.py --target peter # 只写这一个 .model（不打包）
python -B $S/sm2_face.py --family peter --render                    # 脸绑到头模型的面部骨骼 + 合成表情对照图，<W>/build_face/peter/
python -B $S/sm2_pose_check.py "$W/build_sig_dyn/<签名>/karin_geo.npz" --png "$W/pose.png"   # 蹲 / 栖 / 坐 / 跨步时大腿穿出裙子的比例
```

改拟合参数（裙子权重、头部比例等）后 `sm2_batch.py` 要加 `--refit`，否则会复用 `build_sig*/` 里的旧拟合。链参数（`sm2_karin_geo.py` 的 `DYN_SPRINGS`）例外：`sm2_dyn.load()` 构建时直接套当前值，不用 `--refit`。

### 2. 发布构建链（v1 → v2）

```powershell
# 链的拟合：sm2_prop_test.py 和 sm2_head_carrier.py 读 <W>/build_sig_dyn/<签名>/karin_geo.npz。
# 先跑一次带 --dyn 的批量构建生成它们（项目里是 T11 的 --dyn --face），这一步的 .stage 本身不用。
python -B $S/sm2_batch.py --refit --dyn --face --out "$W/builds/dyn_fits.stage"

# v1 = 静态全量（T14：全部战衣 / 便装 + 绑好表情的头）+ 蜘蛛猫背包挂件物理（T17）
python -B $S/sm2_batch.py --refit --face --out "$W/builds/t14_karin_static.stage"
python -B $S/sm2_prop_test.py --base "$W/builds/t14_karin_static.stage" --out "$W/builds/v1.stage"

# v2 = v1 + 头部载体物理覆盖 91 套带面罩战衣（项目约 20 分钟）
python -B $S/sm2_head_carrier.py --base "$W/builds/v1.stage" --out "$W/builds/v2.stage" `
    --never-cull --joint-bsphere 1.0 --map-body --masked --blank-prop `
    --name "Karin Original (Peter & Miles, all suits) v2" --description "<说明>"

# 离线验收：三项都要 0 bad
python -B $S/test_dyn_model.py "$W/builds/v2.stage"
python -B $S/sm2_verify_stage.py "$W/builds/v2.stage" --sheet "$W/reports/v2_readback.png"
python -B $S/sm2_verify_face.py "$W/builds/v2.stage" --sheet "$W/reports/v2_faces.png"
```

- `--masked` 读 `<W>/reports/masked_suits.json`（`{"models": [<战衣模型路径>…]}`，项目里是 91 个：每个奖励 loadout 都用 `actors/hma_hed_base/hma_hed_base.actor` 当头 actor 的战衣身体）。这个列表是项目从全战衣 loadout 表整理出来的，本包没有生成它的脚本；也可以不用 `--masked`，改为每个战衣写一次 `--suit <模型路径>`。
- `sm2_prop_test.py` 和 `sm2_head_carrier.py` 都支持 `--delta <包>`：只写改动的资产，装在 `--base` 后面（mod1）做小步测试。
- `sm2_head_carrier.py` 的 `--cat-actor`（T20）、不带 `--never-cull` / `--map-body` 的组合（T19）是被否决的中间方案，留作复现。

### 3. 安装、状态、卸载

```powershell
python -B $S/sm2_install.py --game "<游戏目录>" install "$W/builds/v2.stage" [第二个包…] --report "$W/reports/install.json"
python -B $S/sm2_install.py --game "<游戏目录>" status      # toc SHA-1、归档数、mod 归档、toc.BAK 是否存在
python -B $S/sm2_install.py --game "<游戏目录>" uninstall   # toc <- toc.BAK，删 d\mods\mod*
```

发布前先在游戏目录外拷一份原版 `toc` 演练 install → status → uninstall：装 v2 后 toc SHA-1 是 `69ce1233d4fe`，卸载后回到 `318f4345f3a1`。发行包只需要这四个纯标准库脚本：`sm2_install.py`、`sm2_dat1.py`、`sm2_stage.py`、`crc64_table.py`。

### 4. 其他离线检查

```powershell
python -B $S/test_actor_roundtrip.py [--all]   # .actor 解码再编码要逐字节相同；--all 是索引里的全部 actor（项目 11,477 个，几分钟）
python -B $S/test_dyn_roundtrip.py [模型名…]    # 用 i30_dynamics 重建原版模型的 ModelAnimDynamicsDef，逐表比较；改 i30_dynamics 后必跑
python -B $S/survey_dyn2.py npc_blackcat.model # 动力学段逐表打印
```

`test_dyn_roundtrip.py` 在这个 build 上报 `total mismatching words 17`，全部来自 `npc_lidemon_antivenom_34x.model` 的 T6 表，原脚本同样如此；其余 15 个模型都是 0。

## 文件

| 文件 | 职责 |
| --- | --- |
| `scripts/sm2_common.py` | 路径与环境变量、按需导入 ALERT、读 toc、名字索引、i30 变长资产头修正（ALERT 的 `get_asset_entry_by_index` 按 i29 的 36 字节头算） |
| `scripts/sm2_dat1.py` | DAT1 容器读写，与 Overstrike `DAT1.cs` 的保存方式逐字节一致；模型用 `MODEL_ALIGN`（5 个段 64 字节对齐） |
| `scripts/crc64_table.py` | 资产 id 用的 CRC64 表（取自 ALERT `dat1lib/crc64.py`，即反射的 CRC-64/ECMA-182） |
| `scripts/sm2_stage.py` | Overstrike `.stage`（v2）读写：`info.json` + `<span>/<资产 id>`，STG 包装（资产头、贴图 meta）；按路径算资产 id |
| `scripts/sm2_install.py` | 无界面安装器，复刻 Overstrike 的 MetaInstaller_I29 + StageInstaller_I29_V2：`install` / `status` / `uninstall` |
| `scripts/i30_model.py` | `.model` 解析：段、网格记录、顶点 / 法线 / UV / 索引 / 蒙皮解码、关节、绑定姿势、材质、Look |
| `scripts/i30_build.py` | 删段、重定位绝对字符串偏移（ModelMaterial、ModelLookBuilt）、刷新 toc 资产头 |
| `scripts/i30_writer.py` | fmt 1 网格块编码（顶点、法线、索引、蒙皮批）与 ModelSubset / GeomData 记录 |
| `scripts/i30_texture.py` | `.texture` 解析（TextureBuilt 头、SD / HD mip、72 字节 toc meta） |
| `scripts/i30_joints.py` | 给 `.model` 追加关节：绑定 / 逆绑定姿势、Lookup、层级、叶表、ModelMirrorIds |
| `scripts/i30_dynamics.py` | 写 ModelAnimDynamicsDef（AnimDynamics 链），对 6 个原版模型逐字复现 |
| `scripts/i30_actor.py` | `.actor` 编解码（组件表、序列化对象、内联字符串、引用表）；对游戏全部 11,477 个 actor 逐字节往返 |
| `scripts/i30_actor_edit.py` | actor 编辑：加组件、改字段和模型路径、重解码校验 |
| `scripts/bcdec.py` | numpy 写的 BC1 / BC4 / BC5 解码（只用于查看） |
| `scripts/sm2_index.py` / `sm2_find.py` / `sm2_extract.py` | 建名字索引 / 按正则查资产 / 解包到 `native/` |
| `scripts/suit_models.py` / `survey_targets.py` | 战衣链枚举 / 目标模型、look 和骨架签名 |
| `scripts/sm2_karin_geo.py` | Karin 重摆到英雄 A 姿势、TPS 拟合、权重映射、裙子权重（`skirt_transfer`）、`--dyn` 时把弹簧链留作独立关节（`DYN_SPRINGS`） |
| `scripts/sm2_fit.py` / `vrm.py` / `render.py` | 拟合器、VRM 读取、软件渲染。三个都来自本库的对马岛便携包（`portable-kits/ghost-of-tsushima/scripts/`）：`vrm.py`、`render.py` 与那边逐字节相同，`sm2_fit.py` 是 `fit.py` 加了 `set_mapping()` |
| `scripts/sm2_preview.py` | 拟合结果与原版 LOD0 对照图 |
| `scripts/sm2_build_model.py` | 把 Karin 部件写进战衣模型（body look 全部 LOD 共用一块几何、其余槽退化、删 Ziva / strands / morph）或清空模型 |
| `scripts/sm2_assets.py` | 从原版模板生成新贴图（BC1 / BC5 / BC7，SD / HD 分 span）和材质 |
| `scripts/sm2_batch.py` | 现行构建器：每种骨架签名拟合一次，合并网格、2×2 图集、一个材质，按关节名重映射到全部战衣 / 便装模型；`--face`、`--dyn`、`--dyn-base` |
| `scripts/sm2_dyn.py` | 把 `--dyn` 拟合的链接到目标模型：追加关节、写动力学段、包围球半径 |
| `scripts/sm2_face.py` | 表情：Karin 的脸按区域迁移到不戴面罩的头模型的面部骨骼，活动度取自 Karin 自己的 blendshape |
| `scripts/sm2_prop_test.py` | T15–T17：链上的三角形和动力学放进蜘蛛猫背包挂件（v1）；`chain_fit` / `strip_body` / `write_with` 也被 v2 复用 |
| `scripts/sm2_head_carrier.py` | v2：链放进带面罩战衣共用的头 actor 模型，打开 NeverCull、放大关节球、HeadManager 补胯部映射、批量去链、清空猫背包 |
| `scripts/sm2_verify_stage.py` | 离线回读 `.stage` 里每个 `.model`：权重和、0x80 变形位、顶点到主关节的距离、LOD 共用一块 |
| `scripts/sm2_verify_face.py` | `--face` 包：面罩脸与头模型脸逐顶点对齐、权重 |
| `scripts/test_dyn_model.py` | `--dyn` 包：绑定 / 逆绑定、Lookup、层级、镜像、动力学段读回重建、模拟关节都带权 |
| `scripts/test_dyn_roundtrip.py` / `survey_dyn2.py` | 原版动力学段重建对比 / 逐表打印（前者导入后者的 `get`） |
| `scripts/test_actor_roundtrip.py` | 原版 `.actor` 解码再编码，要求逐字节相同 |
| `scripts/sm2_pose_check.py` | 拟合的离线姿势检查与带贴图渲染 |

脚本注释里的 `SOP/FORMAT_NOTES.md`、`SOP/PLAN_ALL_SUITS_PHYSICS.md`、`PROJECT_STATE` 和 `Work/…`、`../builds/…`、`../../Output/…` 指项目的私有文档和目录，对应本库的 [技术合同](../../games/marvels-spider-man-2/TECHNICAL_CONTRACTS.md)、[物理](../../games/marvels-spider-man-2/PHYSICS.md) 和上面的 `SM2_WORK` 布局。注释里的 actorfmt.py、head_carrier_build.py 是项目 workflow 的原型，没有迁入（已移植成 `i30_actor.py` 和 `sm2_head_carrier.py`）。

## 输出与本机信息

- `<W>/native/`、`reports/`、`build_*/` 是游戏资产和由游戏数据导出的中间结果，不要收进本仓库。`karin_geo.json` 记有源 VRM 的文件名。
- `.stage` 的 `info.json` 只有名字、作者和说明；作者默认空。

## 案例常量

以下是 Karin 专用的值，不是通用配置。换模型时，要按新模型的网格、材质和弹簧重写：

- `sm2_karin_geo.py`：`TARGETS`、`HUMAN2NAME`、`GROUPS`（Karin 材质 → 部件）、`DYN_SPRINGS`（12 条链的约束类型、锥角、重力、阻尼）、比例默认值（`--scale` / `--head-scale` 1.45、`--neck-drop` 3 cm）和裙子参数；
- `sm2_batch.py`：`ROOT`（`characters/hero/karin_original`）、`ATLAS` / `ATLAS_IMG`（VRM 贴图名）、`GLOSS`、`--name` 默认值；
- `sm2_face.py`：`FAMILIES`、`GAZE`、`LIDS` 和区域划分；`sm2_pose_check.py`：`TEX`、`LEG`；
- `sm2_prop_test.py`：`MOVE`、`PROP_RADIUS`；`sm2_head_carrier.py`：`T19_SUITS`、`BODY_JOINTS`。

以下随游戏 build 变化（`build-sensitive`），游戏更新后要重新核对：

- 资产路径和 id：`sm2_batch.py` 的 `BASES`、`HEADS`、`TPL_MAT`、`TPL_TEX`，`sm2_prop_test.py` 的 `SUIT`、`PROP`，`sm2_head_carrier.py` 的 `HEAD_MODEL`、`HEAD_ACTOR`、`HERO_ACTORS`、`CAT_ACTOR`；
- 段标签、段布局和对齐（`MODEL_ALIGN`）、i30 资产头、72 字节贴图 meta、toc 的八个段；
- actor 组件字段（HeadManager 映射、AnimController 的 NeverCull、HeroSuitAddition）和动力学门控。

## 已验证与边界

- **实机：** v1、v2 由用户在游戏里确认（v1「整体效果可以」，v2 抽查两族多套带面罩战衣「看起来都挺好」）；两者都是用原脚本构建的。
- **便携版本身只做了离线验证（2026-10-14，同一 build、同一 VRM）：** 原脚本和本包脚本在同样的输入上逐项比较，详见 [验证记录](../VALIDATION.md)：
  - 安装器：把 v2 发行包装进原版 toc 的副本，装后 SHA-1 `69ce1233d4fe`、卸载后 `318f4345f3a1`，安装报告与原脚本逐字节相同；
  - `sm2_index.py`、`suit_models.py`、`survey_targets.py` 写出的 `asset_index.json`、`suit_models.json`、`targets.json` 与项目的逐字节相同；`test_actor_roundtrip.py`、`test_dyn_roundtrip.py`、`sm2_find.py`、`sm2_extract.py`，以及对 v2 发行包的 `test_dyn_model.py`、`sm2_verify_stage.py`、`sm2_verify_face.py`：输出与原脚本相同；
  - 构建只对一个目标模型（`hero_spiderman_advanced`）重跑：`sm2_batch.py`（不带参数、`--dyn`、`--dyn --face`）、`sm2_prop_test.py`、只去一套战衣链的 `sm2_head_carrier.py`，以及拟合、单模型写入、表情、姿势检查和预览，结果与原脚本逐字节相同（`.stage` 只差作者）；全量 v1 / v2 构建没有用本包重跑。
- **测试：** 运行 `python -B tests/test_portable_tools.py`。其中有 3 项蜘蛛侠2合成测试，不需要游戏、ALERT 或模型：`.stage` 写入读回、资产 id（与游戏 toc 里两套默认战衣的 id 一致）；安装器在合成 toc 上的 install → status → 两个包 → 重装 → uninstall；`.actor` 序列化对象和容器的编码 / 解码往返（不导入 `dat1lib`）。`--help` 测试覆盖 `scripts/` 下全部 38 个脚本；没装 numpy 或 Pillow 时，需要它们的脚本跳过。
- **便携改动：** 去掉写死的游戏目录和源 VRM 路径，改为 `SM2_GAME`、`SM2_VRM`；工作目录和 ALERT 位置可用 `SM2_WORK`、`SM2_ALERT` 改；`dat1lib`、scipy、etcpak 改为用到时才导入；没有参数解析、一运行就干活的脚本补了 argparse；`--author` 默认空；换行统一成 LF。处理逻辑没有变；逐文件的改动见 [验证记录](../VALIDATION.md)。
- **没有收进本包：**
  - `sm2_package.py`：旧打包器（T3–T4b，只换两套默认战衣，按部件分材质），已被 `sm2_batch.py` 取代；
  - `sm2_hsa_test.py`：T18 的多条 HeroSuitAddition 试验，路线已否决；
  - 其余一次性调查脚本：`survey_align.py`、`survey_dyn.py`、`survey_flags.py`、`survey_fmt1_graphs.py`、`survey_joint_order.py`、`survey_materials.py`、`survey_models.py`、`find_materials.py`、`tex_inspect.py`，以及源 VRM 审计 `vrm_audit.py`、`vrm_read.py`；
  - ALERT、Overstrike、InsomniacTools 的源码（项目放在 `Work/ext/`，都是第三方）；
  - 游戏数据、解出的资产、`asset_index.json`、`reports/` 下的 JSON（含 `masked_suits.json`）、拟合结果、`.stage`、发行包（含 `install.bat` / `uninstall.bat`）、源 VRM。
- **署名：** 读 toc 用 Tkachov 的 ALERT（GPLv3，本包不含其代码；`crc64_table.py` 的表取自它的 `crc64.py`）；`.stage` 格式和安装逻辑来自 Tkachov 的 Overstrike；段名来自 InsomniacTools。见 [工具来源](../../references/TOOL_SOURCES.md)。
