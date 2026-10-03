# 迁移验证记录

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
