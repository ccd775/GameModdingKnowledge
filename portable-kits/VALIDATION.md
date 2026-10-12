# 迁移验证记录

## 2026-10-12：浪人崛起（KT 引擎格式工具与腿部权重）

- **迁入内容：** 5 个 Python 文件，放在 `portable-kits/rise-of-the-ronin/scripts/`。来源是项目的 `tools/`、`original/tools/` 和 `repair/20261004/tools/`，按职责合并改写（每个来源各占 PROVENANCE 一行）：
  - `g1m_tool.py`：合并 `lib_g1m_sections.py`、`collapse_hidden_triangles.py`、`ko_hide_face.py`，以及 `ko_common.py` 的块读写；
  - `g1t_tool.py`：来自 `g1t_layout.py`，以及 `ko_fix_textures.py` 的常量块；
  - `ktdata.py`：来自 `build_current_g1t_usage_map.py`、`dump_ktid_slots.py`；
  - `leg_weights.py`：来自 `ko_leg_ref.py`、`ko_conform.py` 的 `leg_distributions`、`pico_legs.py`、`pico_legs_check.py`；
  - `shader_dump.py`：来自 `read_skin_shader.py`。
- **通用化改动：**
  - 去掉本机路径、模板路径和 Karin 专用的文件表，改为命令行参数；所有写文件的命令都拒绝覆盖。
  - G1M 解析不再依赖 gust_stuff 和 pyquaternion（只用标准库）。调色板骨号到骨架存储序号的映射改为显式处理：项目脚本按 gust 的命名间接用对了，但没有写明。
  - 腿部权重改为原地写入 G1M（只改混合字节、调色板、MM1G 和 FM1G 计数），不再经过 gust 导出 / 导入。原版参考也直接从 G1M 读出。
  - G1T 常量填充增加 R32_FLOAT / RGBA8；读回时能识别 BC1 / BC4 / BC5 / BC7（mode 6）/ 浮点的单一颜色。
  - 共用贴图审计（`ktdata.py usage`）把项目里的一次性扫描脚本做成了命令。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、scipy 1.18.0。输入是项目留下的 Picodra 20260916a 模板、三个原版腿部模型、10-04 发布的成品，以及原版 G1T。
  - **腿部参考：** 59097 个参考顶点，作为集合与项目的 `leg_ref.npz` 逐值相同。
  - **651 sub6：** 原地重做后，每个顶点的有效权重、调色板和追加的 12 个绑定都与发布的 20261004a 相同。回读得到静止姿态偏移 0.00198、弯脚踝时脚的平均位移 0 → 5.53。
  - **8DC sub7：** 有 2 个顶点相差一个 2^-11 量化步长，原因是骨架世界矩阵的浮点误差；调色板和 8 个绑定相同；静止姿态偏移 0.0065。
  - **贴图：** 5 张常量修复与发布包逐字节相同。对原版 `0x1E76FD2D` 写入 0.0，得到的正是上游 mod 的错误版本（只差 +0x3A / +0x3B）。85 张原版 G1T 全部能解析，其中 76 张是 tile 存储，抽查 3 张 tile 往返一致。
  - **G1H：** 能列出捏脸头 G1H 的 41 个嵌入模型；在 hidehead 包里，最大模型的 38 个子网格全部识别为已隐藏。
- **合成数据测试：** `RiseOfTheRoninTools` 共 5 项：
  - G1M 解析、隐藏（含 G1H 容器）、追加绑定；
  - G1T tile 往返、DDS 还原 tile、各格式常量填充与读回、比较与 mip；
  - 资源表的存储和两种 zlib 分块、两种 RDB 尾部、kidsobjdb、KTID、槽表与共用贴图审计；
  - shader 包拆分；
  - 腿部：从「膝下全绑膝骨」重分后，弯脚骨时脚会跟着动；缺失的骨被追加原生绑定；量化后权重之和为 1。
- **未验证：**
  - 便携版的 `ktdata.py` 没有在游戏数据上重跑：整理时游戏未安装。它沿用的解析逻辑在项目里用真实数据跑过。
  - 20261004a 的成品本身没有实机测试。
  - 从源模型构建的脚本没有迁入。

## 2026-10-12：新增龙之信条2便携包

- **迁入内容：** 32 个文件，放在 `portable-kits/dragons-dogma-2/`。
  - `scripts/` 下 7 个 Python：`devcmd.py`、`make_chain_spec.py`、`patch_mesh_header.py`、`build_karin_textures.py`、`make_original_lua.py`、`clsp_dump.py`、`clear_cet_flag.py`；
  - `scripts/blender/` 下 3 个 Blender 脚本：`build_karin_body.py`、`re_common.py`、`prepare_karin_original.py`；
  - `reframework/` 下 4 个 Lua：`karin_replacer.lua`、`karin_dev.lua`、`karin_probe_dump.lua`、`karin_pipeline_probe.lua`；
  - `devqueries/` 下 12 个 Lua 查询；
  - `dd2tool/` 下 DD2Tool 的 5 个 C# 源文件和 `DD2Tool.csproj`；
  - 来源是项目的 `Scripts/`、`Scripts/blender/`、`Scripts/reframework/`、`Scripts/devqueries/` 和 `Tools/src/DD2Tool/`。PROVENANCE 每个文件一行，记录原始和公开版的 SHA-256；
  - 新增 `requirements.txt`（numpy，只给贴图脚本用）。仓库检查允许的文件类型加上了 `.lua`、`.cs`、`.csproj`。
- **没有迁入：**
  - `karin_replacer_original.lua`：由 `make_original_lua.py` 生成；
  - 驱动游戏窗口的脚本：`dd2_reload.py`、`dd2_reset_scripts.py`、`ui_find.py`、`ref_menu_find.py`、`fglock.py`、AHK 和 `.sh`。它们依赖本机的窗口布局、截图模板和前台锁；
  - `build_all.sh`：整理成 README 里的分步命令；
  - `probe_karin.py`、`probe_body_roundtrip.py`：一次性诊断；
  - 生成的规格 JSON（含绝对路径）、发行 PAK、RE-Engine-Lib 源码、游戏和模型数据。
- **便携改动**在 10 个文件：
  - `devcmd.py`：游戏目录原先写死，改为 `--game-dir` 或环境变量 `DD2_GAME_DIR`。没给目录、或目录下没有 `reframework/` 时报错，不创建文件；
  - `make_chain_spec.py`：
    - 原生链模板原先在项目的 `work/native`，改为 `--native-dir` 或 `DD2_NATIVE_DIR`，规格里仍写解析后的绝对路径；
    - 骨骼表原先按 profile 写死在项目的 `work/` 下，改为 `--inventory`；
    - 手写的参数解析改为 argparse，位置参数不变，`--profile=original` 的写法照样可用；
  - `build_karin_textures.py`：源图（PicodraTech 原先是绝对路径）、临时目录和清单、原生模板贴图、texconv、DD2Tool 原先都写死，改为 `--src`、`--work-dir`、`--manifest`、`--native-dir`、`--texconv`、`--dd2tool`（后三个也可用环境变量）；
  - `make_original_lua.py`：输入默认为本包的 `reframework/karin_replacer.lua`，输出改为必填的 `--out`，`--check` 改用 argparse。生成的文本没有变；
  - `clsp_dump.py`：改用 argparse，参数不变；
  - `clear_cet_flag.py`：加说明和 argparse，CRLF 改为 LF；
  - `blender/build_karin_body.py`：源 blend（PicodraTech 原先是绝对路径）和原生身体网格改为必填的 `--source-blend`、`--dd2-body`。这两个参数也会出现在 `build_report.json` 的 `args` 里；
  - `blender/re_common.py`：RE Mesh Editor 的插件目录原先写死为另一个项目的路径，改为可选的环境变量 `DD2_BLENDER_ADDONS`；
  - `blender/prepare_karin_original.py`：FBX 路径原先写死，改为 `--` 之后的第二个参数，SHA-256 检查不变；
  - `DD2Tool.csproj`：RE-Engine-Lib 位置提成属性 `ReeLibDir`，默认值仍是同级的 `../RE-Engine-Lib`；
  - 只把 CRLF 改为 LF：`MdfTools.cs`，以及 `audit_foreign_refs.lua`、`audit_joints.lua`、`container_joints.lua`、`native_refs.lua`、`skirt_rec.lua`。

  其余 16 个文件与原文件逐字节相同，包括 `patch_mesh_header.py`、4 个 `reframework/` 脚本和另外 4 个 C# 源文件。处理逻辑没有改。
- **等价性验证（离线）：**
  - **条件：**
    - build `25290080` 的原生文件；
    - Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；
    - Blender 4.5.12 LTS、RE Mesh Editor 0.66，插件经 `DD2_BLENDER_ADDONS` 加载；
    - texconv 2026.5.8.1；
    - DD2Tool 由本包源码编译：放在 RE-Engine-Lib（`bf0e5e5`）旁边，用 .NET SDK 10.0.401 编译通过，在 .NET 8 运行时上运行。
  - **DD2Tool：** 对同一个 mesh 的 `meshinfo` 输出，与项目里的 DD2Tool 相同，只有记录的输入路径不同。
  - **PicodraTech v1.3.0：** 依次运行本包的 Blender 脚本、DD2Tool `meshconv` / `meshreorder`、`patch_mesh_header.py`、`meshinfo`、贴图脚本、`mdfbuild`、`make_chain_spec.py` + `chainbuild`、`pack`：
    - `mdfbuild` 用的是项目的 MDF 规格，路径改到临时目录；
    - `.240423143` 和 `.260421070` 网格都与项目的构建相同，12 张贴图与项目缓存相同；
    - PAK 与发行包逐字节相同（`2E8E9EFE…`）。
  - **Original v1.0.1：** 从项目当时的 Blender 输出（`.240423143`）开始，走同样的流程：
    - 15 张贴图相同；
    - PAK 与发行包逐字节相同（`4FE56A2D…`）。
  - **Original 的 Blender 这一步：**
    - 用本包脚本重跑，网格与项目的相差约 11 字节（共 3.56 MB）；两次重跑之间也差这么多，固定 `PYTHONHASHSEED` 也一样；
    - 两次的 `build_report.json` 除路径外相同；
    - 这一步本身不是逐字节稳定的。这个差异对游戏有没有影响，没有测试；
    - PicodraTech 那一步重跑逐字节相同。
  - **Original 的源模型转换：** `prepare_karin_original.py` 用脚本里记了 SHA-256 的那个 FBX 重跑：`inventory.json` 和 5 张图片与项目的逐字节相同，blend 文件不同（Blender 文件里有路径等信息）。共享模型目录里现在那个 FBX 是 2026-10-02 为战神项目烘焙过膝盖的版本，脚本按 SHA-256 拒绝了它。
  - **链规格：**
    - `make_chain_spec.py` 的 PicodraTech F、child、Original O 三种输出，与项目原脚本逐字节相同；
    - F 和 O 也与两个发行版当时用的规格相同；
    - 用 README 里的 Blender 片段从源 blend 导出的骨骼表，得到的 F 规格也相同。
  - **Lua：**
    - 本包的 `karin_replacer.lua` 与 PicodraTech v1.3.0 发行脚本相同（`E6947AAD…`）；
    - `make_original_lua.py` 用它生成的脚本，与 Original v1.0.1 发行脚本逐字节相同（`3A2AD3FB…`）；
    - 对项目里的生成文件，`--check` 输出 `up to date`。
  - **`clsp_dump.py`：** 对原生 `body_female.clsp.3` 打印的内容和写出的 JSON，都与项目原脚本相同。
- **合成数据测试：** `DragonsDogma2Tools` 4 项。
  - 链规格的四元数：`swing_from_x` 把 +X 精确转到 7 个方向（含 ±X），是单位四元数，没有绕 X 的扭转。`tilt_outward` 用的是合成的裙子骨架：4 个根围着一根偏离原点的竖轴，父骨坐标系都转过。检查每个节点的锥轴与静止方向的夹角正好是 0.25 rad，锥轴落在静止方向和外向量所在的平面里，并且朝外转；别的 setting 的组不变；
  - `patch_mesh_header.py`：只改偏移 22 的 2 个字节，`--flags` 有效，旧版本（240423143）报错且文件不变；
  - `clsp_dump.py`：MurmurHash3 的公开测试向量，`L_Breast` 的哈希与 DD2Tool（REE-Lib）打印的值相同，胶囊和球两种预设的解析，命令行写 JSON；
  - `devcmd.py`：没有游戏目录时报错；目录下没有 `reframework/` 时报错，也不创建目录；用假的游戏目录走一遍命令文件和结果文件。

  `--help` 测试覆盖 `scripts/` 下全部 7 个脚本；`build_karin_textures.py` 在缺 numpy 或 Pillow 时跳过。根测试共 46 项，全部通过。
- **未验证：**
  - 便携版没有装进游戏测试，实机结论来自项目用原脚本构建的发行包；
  - DD2Tool（C#）和 Lua 不在 Python 测试里，只用在上面的离线重建中；
  - `devcmd.py` 和 `karin_dev.lua` 没有连游戏测试；
  - 测试套件对 Blender 脚本只做语法检查；
  - 非 Windows 系统、其他 build、其他工具版本下的逐字节一致性；
  - 新模型的案例常量。

## 2026-10-06：看门狗物理（链、大衣布料、VRM 构建器的物理段）

- **迁入内容：** 3 个 Python 文件和 1 个配置样板，放在 `portable-kits/watch-dogs/`。
  - 来自项目的 `.work/physics/`：
    - `smu_format.py`（原名同）；
    - `xbg_physics.py`：合并自 `rig_physics.py`、`vanilla_skeleton.py`，以及 `build_coat_cloth_k15.py`、`build_k15_combined.py`、`build_ko_combined.py` 中的通用部分；
    - `vrm_physics.py`：来自 `build_ko_combined.py`。
  - `build_from_vrm.py` 新增可选的 `physics` 段和 `--colliders`。
  - `profiles/karin_original_1_0_0.json`：Karin_Original 1.0.0 的链、裙子布料和背面设置。
  - PROVENANCE 记录每个来源文件的原始 SHA-256；同一个公开文件合并了几个来源时，每个来源各占一行。
- **通用化改动：**
  - 保留的原版对象数原先写死为 16，改为"到大衣布料为止"；表的全局粒子分界原先写死为 161，改为按保留对象的节点数计算。对 Aiden 的模板，两种算法结果一致（16 和 161）。
  - 碰撞体：原先直接读 Nicky 的 char10.xbg。现在改为读 `xbg_physics.py export-colliders` 导出的 JSON，缺省时退回由骨架推出的胶囊。仓库不收录游戏数据。
  - 链、布料、背面的参数全部移到配置文件；项目里按模型写死的流程（蓝白 Karin 从源 BLEND 找回链权重）只写进文档，不迁入。
  - 没有 `physics` 段时，构建路径与此前完全相同。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0；输入为 Karin_Original 的 VRM，Karin 1.3.0 运行包作底包。
  - **有物理：** `profiles/karin_original_1_0_0.json` 配合从 char10.xbg 导出的碰撞体，输出 `READBACK PASS`，char01.xbg 与用户实机验收的 Karin_Original 1.0.0 逐字节相同（`609B07FC…`）。
  - **无物理：** `profiles/karin_original.json` 仍逐字节重建 0.1.2 的 char01.xbg（`CDE17BB0…`）。
  - **不给碰撞体文件：** 用骨架推出的胶囊，构建通过，各链静止时都在碰撞体外。
- **合成数据测试：** `WatchDogsPhysics` 3 项。
  - SMU 对象写出与解析的往返：不同起始偏移下矩阵都按文件偏移 16 字节对齐；名字哈希错误时报错；
  - 在合成模板上搭链：节点位置、父节点、+Y 朝向、逆绑定、保留对象逐字节不变、只有一个挂点时自由节点的挂点序号为 0、LOD 不变；`move()` 能移动和改挂节点；`export-colliders` 导出且拒绝覆盖；
  - VRM 端到端：合成的 jiggle、大衣布料、领子链和表。检查：
    - 保留和去掉的对象、表项分界；
    - 布料参数和大腿胶囊半径；
    - 改挂的粒子（仍固定的那个保持固定）；
    - 链的挂点和 flags、碰撞组（碰撞体文件和骨架推出两种来源）；
    - 裙子和头发的权重、背面副本。
- **未验证：**
  - 实机只有 Karin 1.6.0（FBX 路线，本包不含其流程）和 Karin_Original 1.0.0；
  - 骨架推出的胶囊、其他模型、带不同物理块的模板都没有实机测试；
  - 游戏的链做不到运动跟随，这是引擎限制，不是本包的缺陷。

## 2026-10-03：看门狗 VRM 构建器整理成通用版

- **迁入内容：** 8 个 Python 文件和 1 个配置样板，放在 `portable-kits/watch-dogs/`。
  - 来自项目的 `.work/karin_original/`，按职责改名：`vrm_model.py`（原名同）、`vrm_fit.py`（原 `karin_fit.py`）、`vrm_weights.py`（原 `weights_map.py`）、`vrm_assemble.py`（原 `assemble.py`）、`vrm_textures.py`（原 `build_textures.py`）、`build_from_vrm.py`（原 `build_karin_original.py`）、`package_mod.py`（原 `package_karin_original.py`）、`char01_paths.py`（原 `fat_paths.py`）；
  - `profiles/karin_original.json`：Karin_Original 0.1.2 的材质分槽和次级骨链规则，从原脚本里写死的常量整理而来；
  - PROVENANCE 记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **通用化改动：**
  - 模型相关的常量移到配置文件：VRM 材质到 4 个槽位的映射、高光类别、头发和裙子的链规则（`match`/`under`/`to` 或 `to_side`/`shares`/`side_width`）；
  - 链级原先取节点名的数字后缀，改为向上数到分叉节点或人形骨骼的步数。对 Karin_Original，两种算法在所有带权重的节点上结果一致；
  - 贴图：同一槽位多张 base color 时按配置顺序上下拼或拼成网格，加复制边缘的缝隙；睫毛槽裁到实际用到的 UV 区域；合成尺寸取底包 donor 的实际尺寸，原先写死为 Karin 1.3.0 的尺寸；
  - 拟合：根据左右大腿判断朝向，VRM 0.x（朝 −Z）先转 180°；VRM 0.x 的拇指改用 1.0 命名；可选人形骨骼和模板骨骼缺失时跳过对应步骤；
  - 权重：除 0.1.2 已有的眼骨外，下巴也并入 `Head`；模板里缺少的 char01 骨骼退回最近的已映射祖先；
  - 构建入口直接读底包 FAT/DAT，取出模板 XBG 和 donor XBT，不再依赖项目目录；新增 `build_report.json`；
  - 打包：底包、pack 名、friendlyId、版本、描述和 ZIP 时间戳都由参数给出；modconfig.json 保持 CRLF；输出目录非空时默认拒绝写入；
  - `repack_fat8.py` 拆出 `entry_hash` 和 `rebuild` 供打包调用，命令行行为不变。
- **没有迁入：** `twist_profile.py`（扭转骨比例已作为常量写进 `vrm_weights.py`）、`eye_check.py`、`preview_*.py`、`inspect_*.py`、`pose_test.py`：只服务于本项目的诊断。VRM、贴图、底包和产物都不收录。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0。输入为 Karin_Original 的 VRM（VRM 1.0）、`profiles/karin_original.json`、Karin 1.3.0 运行包作底包，modconfig 取自 0.1.2 包。
  - **结果：** `build_from_vrm.py --package` 输出 `READBACK PASS`。char01.xbg（`CDE17BB0…`）、15 个 XBT、FAT、DAT、modconfig.json 和 ZIP（`20D92DD7…`）都与用户实机认可的 Karin_Original 0.1.2 逐字节相同。
- **合成数据测试：** `WatchDogsVrmBuilder` 3 项。
  - 用合成 VRM 1.0 和合成底包端到端构建并打包：回读通过；缩放、躯干保留与四肢关节移动；前臂摆姿势方向；眼睛权重并入 `Head`、头发链分给 `Spine2`、裙摆按左右分给两侧大腿；两张外套贴图上下拼、睫毛裁剪；新包只改动预期条目；输出目录非空时拒绝写入；
  - VRM 0.x 的朝向判断和拇指改名：同一模型的 0.x 与 1.0 版本拟合结果一致；
  - 配置漏列材质时报错；三张贴图拼成 2×2 网格。
- **未验证：** 除 Karin_Original 外的任何模型都没有实机测试；VRM 0.x、缺失可选骨骼、多贴图拼图集只有合成数据测试。

## 2026-10-03：新增看门狗 XBG 写出器

- **迁入内容：** 11 个 Python 文件，放在 `portable-kits/watch-dogs/scripts/`。
  - 写出器，来自项目的 `.work/xbg_writer/`：`xbg_model.py`、`xbg_codec.py`、`fbx_reader.py`、`fbx_mesh.py`、`fbx_to_xbg.py`，入口是 `build_xbg_from_fbx.py`；
  - FAT v8，同一来源：`extract_fat8.py`、`repack_fat8.py`；
  - 骨架：`xbg_skeleton.py` 来自 `.work/karin_v14/skeleton.py`，`xbg_skeleton_patch.py` 来自 `.work/karin_original/skeleton_patch.py`；
  - 贴图：`xbt_encode.py`，来自 `.work/karin_original/`；
  - PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **没有迁入：**
  - `make_test_package.py`、`fat_paths.py`、`package_karin_original.py`：写死了本项目的发布目录和条目清单。打包改用 `repack_fat8.py` 和使用说明里的步骤；
  - Karin_Original 的 VRM 构建脚本（`vrm_model.py`、`karin_fit.py`、`weights_map.py`、`assemble.py`、`build_karin_original.py`、`build_textures.py`）：与该模型的材质名、部件名绑定；
  - 格式反推和对照工具（`roundtrip_test.py`、`compare_xbg_*.py`、`fit_*.py`），以及 1.4、1.5 的修复脚本：只服务于本项目的旧 FBX；
  - 模板 XBG、样本、FBX 和贴图：它们来自游戏或模型。
- **便携改动**在 6 个文件：
  - `build_xbg_from_fbx.py`：新增 `--force`，默认拒绝覆盖已有的输出和报告；
  - `extract_fat8.py`、`repack_fat8.py`：
    - 改用 argparse。原来直接读 `sys.argv`，运行 `--help` 会出错；
    - 默认拒绝覆盖已有输出；
    - `repack_fat8.py` 新增 `path_hash`，替换键可以直接写游戏路径；
  - `xbg_skeleton.py`：
    - 改名，原名 `skeleton.py` 太泛；
    - 从同目录导入 `xbg_model`；
    - 命令行改为 argparse 的通用残差检查，去掉了 Karin 专用的关节打印；
  - `xbg_skeleton_patch.py`：
    - 改名；
    - 新增 `rigid_world`，未列出的关节随父骨刚性移动；
    - 新增带写后验证的命令行；
    - 文档字符串里的逆绑定数量更正为 382；
  - `xbt_encode.py`：
    - 改为从同目录导入本包的 `xbt_tool.py`；
    - 新增 argparse 命令行，默认拒绝覆盖；
    - PSNR 改为输出普通浮点数。

  其余 5 个文件与原文件逐字节相同，编解码和转换逻辑都没有改。
- **等价性验证：**
  - **条件：** Python 3.14.0、numpy 2.5.2、Pillow 12.3.0。全部用本包的脚本运行，输入是项目已有的文件。
  - **写出器：** 输入为 v1.3 的 FBX 交接文件和 1.3.0 模板。`build_xbg_from_fbx.py` 输出 `READBACK PASS`，结果与项目写出器先前的输出逐字节相同（`4502953c…`）。
  - **骨架：** 在 1.3.0 模板上把两侧上臂沿锁骨方向内移 4 cm。`xbg_skeleton_patch.py` 移动了 82 个节点，上臂间距从 0.3726 m 变为 0.2931 m，与实机认可的 1.5 一致，残差没有变大。
  - **贴图：** `xbt_encode.py` 生成的头发和睫毛 XBT，与 Karin_Original 0.1.2 包内的文件逐字节相同。
  - **FAT：** 不替换任何条目时，`repack_fat8.py` 重打 1.3.0 包，FAT 和 DAT 都与原文件逐字节相同；`extract_fat8.py` 解出 22 个条目。
  - **合成测试：** `tests/test_portable_tools.py` 新增 5 项（`test_wd_*`）。把对齐测试换回旧的"照抄补零"写法时，4 个子用例全部失败；用修复后的写法全部通过。

## 2026-10-02：新增战神：诸神黄昏构建器

- **迁入内容：** 29 个 Python 文件。
  - `scripts/` 下 26 个：两个角色的构建入口、回读校验、屈膝模拟、两个贴图包入口、骨架角色表、VRM 贴图导出、源模型形态键烘焙，以及 17 个模块；
  - `scripts/blender/` 下 3 个 Blender 脚本。放在子目录里，是为了不让 `--help` 检查去跑它们；
  - 来源是项目工具目录 `Tools_GoWR` 的 `gowr/`、`source_fix/`、`blender/`。`knee_sim.py` 来自 agent 会话的临时目录，项目目录里没有它。`gamedir.py` 是新写的；
  - PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **没有迁入：**
  - `build_freya_final.py`：它改的是 `r_freya00.wad`，游戏不加载这个文件，是被否决的路线；
  - `lodpack.py`：没有脚本引用它；
  - `launch_test.sh`：仓库不收 `.sh` 文件；
  - `data/` 里的角色表、骨骼表、贴图计划和原版 boot-options，`work/` 里的拟合结果和原版 wad。它们来自游戏或模型。
- **便携改动**在 12 个文件，另加新文件 `gamedir.py`：
  - 游戏目录只在 `gamedir.py` 一处设置：`--game` 或环境变量 `GOWR_GAME`，都没有时明确报错。`build_mesh.py`、`build_textures.py`、`agctex.py` 原来写死的路径改为调用它；
  - `agctex.py` 改为第一次用到时才加载 DLL，所以任何模块在任何系统上都能导入；
  - 入口脚本改用 argparse，底板 wad、拟合目录、骨骼表、角色表和输出都从参数传入。涉及 `build_kratos_final.py`、`build_valk_final.py`、`verify_build.py`、`knee_sim.py`、`build_textures.py`（新增 main，用奎托斯的默认规则）、`build_valk_textures.py`、`rigspec.py`、`extract_vrm_textures.py`、`bake_knee.py`、`wad.py`；
  - `verify_build.py` 不再从构建脚本导入 `BASE_WAD`，也不再切换到自己所在的目录；
  - `rigspec.py` 的骨骼表改成常量 `SPECS`，去掉了 `r_freya00` 那一份；
  - `knee_sim.py` 的骨骼号、槽位号和膝盖高度提成顶部常量，CRLF 换行改为 LF；
  - `wad.py` 直接运行时会先列出全部条目。

  其余 16 个文件与原文件逐字节相同，包括 3 个 Blender 脚本。处理逻辑没有改。
- **等价性验证：**
  - **条件：** build `18979360`；Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.3.0、lz4 4.4.5、etcpak 0.9.15、texture2ddecoder 1.0.6。全部用本包的脚本运行。输入是项目已有的拟合结果（来自已修正膝盖的源模型）、骨骼表、两个角色表，以及从 VRM 导出的贴图源 PNG。
  - **奎托斯：** 底板是 KarinPicodraTech_Kratos 的 wad。`r_heroa00.wad`（`c8b43fc4…`）、`KarinOriginal.lodpack`（`a483890f…`）及其 `.toc`、`KarinOriginal.texpack`（`b37d5ca5…`）及其 `.toc`，与已发布的 5 个文件逐字节相同。
  - **芙蕾雅：** 底板是原版 `r_freyavalkyrie00.wad`（LZ4）。`r_freyavalkyrie00.wad`（`f003da61…`）、`KarinOriginalFreya.lodpack`（`408cc758…`）及其 `.toc`、`KarinOriginalFreya.texpack`（`20d321c0…`）及其 `.toc`，与已发布的 5 个文件逐字节相同。
  - **报告：** 两个角色的 `mesh_report.json` 和贴图 `.plan.json`，也与项目里的记录逐字节相同。
  - **回读：** `verify_build.py` 两个角色都是 `BAD 0`（奎托斯 10 个槽位，芙蕾雅 19 个槽位，位置误差都是 0）。
  - **屈膝：** `knee_sim.py` 在 0、30、60、90 度时，`outside_knee` 都是 0。会话里的原脚本对同一份输出给出的结果逐行相同。
  - **角色表：** `rigspec.py` 重新生成的两个角色表，与项目使用的逐字节相同。奎托斯的骨架和项目当时一样，是从 KarinPicodraTech_Kratos 的 wad 读的。
  - **形态键烘焙：** `bake_knee.py` 从 `.orig` 原件烘焙出的 FBX（`18f00e1a…`）和 VRM（`8f930404…`），与项目当时在会话里烘焙的副本逐字节相同。
    - 这次比对发现，共享模型目录里的两个烘焙文件与之不同：各有一段 384 KiB（0x60000）、按 4 KiB 对齐的全零块，VRM 在 0xC0000，FBX 在 0xE0000，块以外逐字节相同。结果是那个 FBX 无法解析，那个 VRM 里脸部网格 `Body` 有 70 个形态键的数据变成了 0；
    - 这是复制进同步盘时发生的存储损坏，不是脚本差异。`.orig` 原件没有这种全零块；
    - 2026-10-02 当天已用会话里的烘焙副本替换，替换后两个文件的哈希与本包输出一致，FBX 能解析，VRM 脸部全零形态键的数量与原件相同（474 个里 218 个，原本就是空的）。复制进同步盘的文件要在复制后重新核对哈希。
  - **其他：** `scripts/` 下 26 个脚本都能用 `--help` 运行。
- **合成测试**新增 7 项：
  - 三种骨骼权重布局的编码、解码往返：(9,2,4)+(10,2,3)、(9,2,4)+(10,2,2)、(9,4,4)+(10,3,1)。第二种检查 8 个 u16 骨骼槽（用 7 个，第 8 个为 0），骨骼号大于 2047 也不丢；超出容量的影响数按 10 / 7 / 4 截断；
  - 单组多成员 lodpack 的写入，以及从 lodpack、`.toc`、LZ4 压缩的 `.toc` 回读；
  - 槽位规划：先取共同档位再按顺序升级，索引容量也算；副槽连最低档都放不下时，部件交给主槽；主槽放不下时从末尾丢部件；什么都放不下时报错；
  - 二进制 FBX：16 种长度下原样写回逐字节相同（覆盖"已对齐时填充 16 字节"）；改动 zlib 压缩的数组后重写，其他属性不变，尾部填充仍按 16 字节对齐；
  - VRM 形态键烘焙：`body_2` 的稀疏 `kisekae_Knee` 加到基础网格上，该形态键清零（索引保留），包围盒更新；另一个形态键和另一个网格不变；
  - 骨架镜像：同一关节上叠两根骨时按父骨选择，`left_override` 只替换指定的角色；
  - 游戏目录：没设置时报错；导入 `agctex.py` 不需要 DLL，第一次真正使用时才去找它。

  根测试共 31 项，全部通过。十个游戏的独立导出测试也全部通过，其中战神的测试在导出包里确实执行了，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/god-of-war-ragnarok/requirements.txt`：numpy 2.5.2、scipy 1.18.0、etcpak 0.9.15、texture2ddecoder 1.0.6（需要 Python 3.12+）。
  - Pillow 和 lz4 来自根 `requirements.txt`；
  - 贴图那一步要在 Windows 上调用游戏自带的 `libSceAgcTextureTool.dll`；
  - Blender 5.0.1 只用于拟合、减面和骨骼表。
- **未执行：**
  - Blender 的三步（骨骼表、拟合、减面）没有重跑，等价性验证用的是项目已有的拟合结果和骨骼表；
  - 用原版 `r_heroa00.wad` 做奎托斯底板；
  - 新模型的案例常量；其他 build；其他库版本下的逐字节一致性；
  - 在非 Windows 系统上跑网格步骤；
  - 本次没有部署或启动游戏，实机证据仍是此前 agent 的自测。

## 2026-10-02：新增西之绝境构建器

- **迁入内容：** 9 个 Python 文件，`build_hfw.py`、`make_mod.py`、`patch_bounds.py` 和 6 个模块或工具脚本。PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **便携改动**只在 4 个文件：`make_mod.py`、`patch_bounds.py`、`pose_preview.py`、`gamekey.py`。
  - 4 个文件的位置参数都改用 argparse，有了 `--help`，测试也就能统一检查各脚本的帮助输出；
  - `make_mod.py` 在缺少 h2 工具、`.pristine` core、texconv 或 `jobs.json` 时直接报错；
  - `gamekey.py` 在非 Windows 系统上也能导入。

  其余 5 个文件与原文件逐字节相同。其中 `vrm.py` 与对马岛便携包中的同名文件逐字节相同。
- **等价性验证：**
  - **条件：** build `14835813`；Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0；texconv 2024.6.5.1（SHA-256 `9450ba6c…`）；h2_pc_mi_091 0.9.1（SHA-256 `871331ef…`）；同一 VRM 和同一组 h2 导出。
  - **构建：** `build_hfw.py` 的 30 个输出与 v4 构建逐字节相同，包括 25 个 ascii、4 张页和 `jobs.json`。
  - **导入和补丁：** `make_mod.py` 和 `patch_bounds.py` 产出的 33 个 mod 文件，与 agent 实机测试过的 v4 逐字节相同。便携改动前后各跑了一次，两次都相同。
  - **其他：** `pose_preview.py` 产出 15 个 OBJ；`make_mod.py` 在工具目录缺失时以退出码 2 拒绝运行。
- **合成测试**新增 5 项：
  - ascii 读写往返：骨架、多 UV 层、8 个权重槽、LF 换行，且不写出 `nan`；
  - core 补丁：常量从脚本源码中读取，检查 4 个包围盒和 6 个 SkinInfo 部件；类型不是 7 时拒绝修改，文件保持不变；
  - 权重量化，以及射线锥遮挡判定（立方体内外各一个点，另测距离不足的情况）；
  - 掩码合并：两个包围盒重叠但足迹分离的岛分成两块，镜像的岛合成一块；
  - 姿势 FK：转轴不动，子骨跟随，蒙皮按权重混合。

  根测试共 24 项，全部通过。九个游戏的独立导出测试也全部通过，其中西之绝境的测试在导出包里确实执行了，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/horizon-forbidden-west/requirements.txt`：numpy 2.5.2、scipy 1.18.0（需要 Python 3.12+）。
  - Pillow 来自根 `requirements.txt`；
  - `gamekey.py` 另需 pywinauto，只在 Windows 上做实机测试时使用。
- **未执行：**
  - 新模型的案例常量；
  - 其他 build；
  - 其他库版本或 texconv 版本下的逐字节一致性。

  实机证据仍是 v4 的 agent 自测，用户尚未单独确认。

## 2026-10-01：新增对马岛构建器

- **迁入内容：** 9 个 Python 文件，`build_karin.py`、`verify.py` 和 7 个模块。PROVENANCE 分别记录每个文件的原始 SHA-256 和公开版 SHA-256。
- **便携改动**只在 `build_karin.py` 和 `verify.py` 两个文件：
  - 去掉写死的本机游戏目录和 VRM 路径，改为 `--game`（或 `GOT_GAME_DIR`）和必填的 `--vrm`；
  - texconv 改为可选的 `--texconv`，可用 `--expected-texconv-sha256` 校验；不提供时用 etcpak；
  - 两个文件的 CRLF 换行统一为 LF。

  其余 7 个文件与原文件逐字节相同。
- **等价性验证**（build `23879181`；环境为 Python 3.14.0、numpy 2.5.2、scipy 1.18.0、Pillow 12.2.0、etcpak 0.9.15）：用 PROVENANCE 里记录的便携脚本、同一 VRM 和 texconv 2025.10.28.1（SHA-256 `2cb5703c…`）重建两个 profile，输出与项目构建逐字节相同：
  - Original：md5 `a30f3ac17122e2ab1702bc74dffa2ec0`；
  - PicodraTech：md5 `bf0a6e15a6c7786dd48a91210e31fc82`。

  两个 profile 不带 texconv 的 etcpak 构建都通过 `verify.py`（PROBLEMS none，使用 76 根骨骼）。
- **合成测试**新增 6 项：
  - PSARC 数据原样存储且按 8192 对齐（用非零载荷检查）；
  - 权重和法线打包；
  - 减面时边界锁定、面朝向不翻；
  - 拼页像素与 UV 一致，缩小比例下也一致，透明标记不丢色；
  - 下垂姿势反解；
  - 5 种错误输入被拒绝：缺 VRM、缺游戏目录、只给哈希不给 texconv、texconv 路径不存在、哈希不符。

  根测试共 19 项，全部通过；八个游戏的独立导出测试通过，其中对马岛测试在导出包里确实执行，没有被跳过。
- **依赖：** 本包的额外依赖放在 `portable-kits/ghost-of-tsushima/requirements.txt`：numpy 2.5.2、scipy 1.18.0、etcpak 0.9.15、texture2ddecoder 1.0.6。
  - 这些版本需要 Python 3.12+。
  - 根 `requirements.txt` 不变，其他工具包仍支持 Python 3.10。
  - 没装这些依赖时，对马岛测试会跳过并提示安装命令。
  - 本机的 Pillow 是 12.2.0、markdown-it-py 是 4.2.0，与根文件里的 12.3.0 / 4.0.0 不同。
- **未执行：**
  - 新模型的 profile；
  - 本次没有新的实机部署；
  - VRM 读入只在两个项目模型上验证过；
  - 没有在其他库版本上核对逐字节一致性。

## 2026-09-15：新增 MK1 公开工具与第七游戏导出

- 迁入MK1流程、8份案例、当前状态、模板及11个源码/测试文件（6个工具、5个测试文件），没有游戏/模型payload或专用二进制。公开脚本只规范LF换行；原始和公开字节hash分别保存在PROVENANCE。
- 根组件测试13项通过，其中MK1入口执行18项合成测试及3个CLI帮助检查；Windows PowerShell合成部署测试通过，4项hash/路径拒绝生效，不操作真实游戏。
- 七个游戏的独立导出测试通过：目录含空格，使用导出包自己的代码和测试；MK1工具在导出包中实际执行，未选择游戏显式跳过。
- 公开边界、链接、JSON、Python语法和源码provenance检查通过。Python3.12，markdown-it-py4.0.0、lz4 4.4.5、Pillow12.3.0。
- 当前T1000 v8材质复发与Umbrella柯南武器候选未安装均单独说明；此次迁入没有重新Cook、部署或实测游戏，也没有更新旧v0.1.0 Release附件。

以下为六游戏首次迁入的历史记录。

整理日期：2026-09-06。状态：便携脚本组件测试，不是六款游戏新 Mod 的端到端验收。

测试环境：Python 3.12.10、lz4 4.4.5、markdown-it-py 4.0.0；requirements.txt 与实际测试版本一致。

## 实际迁入

19 个原项目 Python 文件；每项在 PROVENANCE.json 中记录源相对位置、原始大小与 SHA-256。保留的是作者在工作区编写的算法/包装器，未复制参考 Mod、模型、纹理、原游戏文件或第三方 DLL。

迁移改动包括：显式输入/输出路径；XBT/PAK 输出防覆盖；VTA 的原 126 骨/31 帧参数化；Forge 的 LZ4 独立于本机 Oodle 路径、field 8 才按需加载已固定 DLL；StudioMDL 新输出检查；RE4 table/payload bounds 检查。格式专属限制仍保留，不将其变成全格式支持声明。

新公共 modkit 提供 init、inventory、verify、doctor、checkpoint、package。旧 PowerShell helper 只保留兼容入口，不再复制到 common 子目录。

## 合成回归

运行 `python -B tests/test_portable_tools.py`：12 项测试通过，使用运行时创建的合成 fixture，没有读取游戏或私人模型。

- 新项目创建、追加断点、重复写入拒绝。
- 完整文件集合/hash 校验、额外文件拒绝、两份 ZIP 字节相等。
- 空输入、越界路径拒绝。
- XBT 提取/注入字节相等、DDS 格式不匹配与覆盖拒绝。
- PRIM/GLB 相同数据通过、顶点改变失败、损坏 GLB 失败。
- 合成 Forge 替换、重复构建相等、独立 extractor 回读；LZ4 不加载 Oodle。
- VTA 使用 1 骨/2 帧的非旧角色合同缩放，保留法线，重复输出拒绝。
- VPK payload CRC 正向/反向和路径隔离。
- KPKA DEFLATE 提取与表/负索引反例。
- HD2 三件套与错误范围检查；LUT header/行内容检查。
- 所有命令行脚本的 --help 启动检查。

未执行：RPKG 实际 TEXT 编译、StudioMDL 实际角色编译、用户 HD2SDK UV 编译、Oodle DLL 分支、六款游戏部署与新运行时测试。原项目的实机验收记录保留为历史证据。

另在 Blender 4.2.23 上创建并保存合成三角网格/UV/材质/shape-key 场景，实际运行迁入的源审计器并核对 JSON。命令使用 --python-exit-code 1，避免脚本异常被 Blender 默认退出码掩盖。合成 Blend 和报告在包外生成，不作为用户模型分发。

## 继续维护

`tests/test_export_portability.py` 另外执行一次覆盖六份导出目录的隔离测试：路径含空格，不使用父仓库代码，逐项检查实际脚本存在，并运行导出包自身的组件测试。未选择游戏的测试显式跳过，所选游戏和公共层通过；六份均通过本地链接、JSON、脚本 provenance 哈希与 Python 语法检查。

修改脚本后重新运行相关测试，更新迁移后的 hash，并检查 standalone 导出。新 build 导致格式失败时记录错误和精确输入身份，修正当前分支，不静默删除检查或复制旧角色常量。
