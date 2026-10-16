# 工具获取与固定版本

历史版本是项目曾使用的快照，不是永远推荐的最新版。下载后记录 URL、版本、可执行文件或插件树的 SHA-256；先对当前游戏原生资源做 roundtrip，再判断兼容性。便携包不替用户下载或执行不明二进制。

| 工具 | 作者/维护者入口 | 在本工作区的用法 |
| --- | --- | --- |
| Blender | [官方历史版本](https://download.blender.org/release/) | 4.2.23 与 4.5.12 曾用于不同项目，DMC5 用 4.0.2，战神5 用 5.0.1，师父用 4.2.23（后台一律 `--factory-startup`），幻兽帕鲁用 4.2.23 + UEFormat 插件（读 `.uemodel` / `.ueanim`）；匹配源文件与插件 |
| RPKG Tool | [Glacier 工具页](https://glaciermodding.org/rpkg/) | CLI/GUI 2.34.0，导出 GLB/TGA 后重建并回读 |
| SMF / GlacierKit | [维护者的 suit modding 指南](https://glaciermodding.org/docs/modding/hitman/guides/suitmodding/) | SMF 2.33.40、GlacierKit 1.12.15 为历史锁；使用当前实体补丁 |
| ZModeler | [作者官网](https://www.zmodeler3.com/) | 3.3.1.1244；XBG filter、Skeleton Bind、L0/L1 Compound，需用户自己的授权。Watch Dogs 自 2026-10-03 起可不用（纯 Python XBG 写出器），仅作对照 |
| RE Mesh/Chain 工具 | [NSACloud](https://github.com/NSACloud) / [Chain 项目](https://github.com/NSACloud/RE-Chain-Editor) | Mesh 0.66、Chain 14.0；在 Blender 插件设置中安装并测试当前文件格式。DMC5 用 Mesh 0.44（无界面模式需屏蔽 `console_toggle`，MDF v10 只读不写），Chain 14.0 的 `file_re_chain` 可往返 chain .21。龙之信条2 用 Mesh 0.66 + Blender 4.5.12：0.66 只认旧版 mesh `.240423143`，进出都经 DD2Tool `meshconv` 转换 |
| REFramework | [nightly 发布](https://github.com/praydog/REFramework-nightly/releases) | RE Engine 游戏的加载器；MHWs exe 1.42.0.2 上 nightly 01212 无法加载散装贴图，01424 可以。每次游戏更新后重新确认，记录日志中的 commit。RE9 用它的 Lua autorun 写只读探针，读 Chain2 组件、关节坐标与枚举值 |
| BoneSystem（MHWs） | [作者发布帖（南风焓）](https://www.caimogu.cc/post/1937594.htm) | 26.1.13.1；REFramework 插件，独立骨骼与表情映射，配置见 MHWs 技术合同 |
| Fluffy Mod Manager | [作者官网](https://www.fluffyquack.com/) | MHWs、DMC5、RE9 的 mod 安装/回退（DMC5 为 invalidate 方式）；以其 `installed.ini` 为游戏目录的权威记录 |
| REE.PAK.Tool 路径表 | [Ekey](https://github.com/Ekey/REE.PAK.Tool) | `Projects/*_STM_Release.list`：RE Engine 游戏的文件路径表，用于按表提取与枚举部件/mdf2 变体（PRAGMATA、RE9）；游戏更新后重新下载。龙之信条2 用 `DD2_STM_Release.list`（2025-03-15），经 DD2Tool `resolve` 改写成当前 build 的版本号后再提取 |
| REasy | [seifhassine/REasy](https://github.com/seifhassine/REasy) | `resources/data/dumps/` 下的 RSZ 类型库：PRAGMATA 用 `rszpragmata.json`，RE9 用 `rszre9.json`（2026-10-01 取自 main）；先对原生 prefab 做逐字节往返再用 |
| gust_stuff | [eArmada8](https://github.com/eArmada8/gust_stuff) | v1.3.13：KT 引擎 G1M 导出 / 导入（fmt/ib/vb/vgmap + `mesh_metadata.json`）；真三国无双 起源先验证往返逐字节一致，再作为网格写回通道。浪人崛起便携包的 G1M 解析按它的 `parseG1MS` / `parseG1MG` 字段布局独立实现；导出会丢弃未被索引引用的顶点 |
| ROTR Mod Loader（RONPATCHER） | [Nexus Mods：Rise of the Ronin 第 9 号 mod](https://www.nexusmods.com/riseoftheronin/mods/9) | 1.0（2025-03 的文件）：`dinput8.dll` 代理；`RONPATCHER/root` 下按哈希命名的散装文件覆盖资源；mod 包不附带其 ini / Patches / system；同包附带的 g1ttools 与 qrdbtool 是独立工具 |
| RDBExplorer | [MrIkso](https://github.com/MrIkso/RDBExplorer)（MIT，commit `22e72d8`） | 面向仁王 3 的 rdb / fdata 浏览器；浪人崛起便携包的 G1T 64 KB tile 布局按它的 G1TParser 核实 |
| Project-G1M | [Joschuka](https://github.com/Joschuka/Project-G1M)（[浪人贴图格式 issue #42](https://github.com/Joschuka/Project-G1M/issues/42)） | 浪人崛起 G1T tile 存储的社区讨论；本项目未直接使用其插件 |
| dxc（Windows SDK） | [微软 Windows SDK](https://developer.microsoft.com/windows/downloads/windows-sdk/) | 10.0.26100.0 的 `dxc.exe -dumpbin` 反汇编浪人崛起的 DXIL 蒙皮着色器（`shader_dump.py --dxc`） |
| RenderDoc | [官方](https://renderdoc.org/) | 1.46：在浪人崛起上抓不到帧（设备经 NVIDIA Streamline 创建），已放弃；只作记录 |
| DWO Mod Loader（DWOPATCHER） | 作者 vagonumero13（Nexus Mods 的 DYNASTY WARRIORS: ORIGINS 页面） | `dinput8.dll` 代理；`DWOPATCHER/root` 下按哈希命名的散装文件覆盖资源；mod 包不附带其 ini / Patches，启动日志 `patcher_log.txt` 可确认加载 |
| Crowbar | [作者项目](https://github.com/ZeqMacaw/Crowbar) | 0.74，Source 伴随文件反编译 |
| Source 工具 | [Valve Source SDK](https://github.com/ValveSoftware/source-sdk-2013) | StudioMDL/VTEX/VPK/HLMV 使用目标 L4D2 安装提供的版本，不以 SDK2013 编译器替代 |
| HD2SDK CE | [维护者项目](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition) | 获取插件后固定 commit；不同 AQ 分支需单独作 Unit 往返测试 |
| FileDiver | [维护者项目](https://github.com/Obsoletes/filediver) | archive/FileID 提取；使用下载包自身 help 确认参数 |
| DirectXTex | [微软项目](https://github.com/microsoft/DirectXTex) | texconv 固定 SHA，进行 DDS 转换及解码检查。龙之信条2 贴图用 texconv 2026.5.8.1（SHA-256 `dcfdec10244e02cf5037fba089c55fb7e1326b1c8181742d77d15fa5cb5eef06`） |
| Ghost of Tsushima Toolkit for Blender | [Dave349234（Nexus）](https://www.nexusmods.com/profile/Dave349234) / [GitHub（coolab342 仓库，README 链接 Dave349234 的 Ko-fi 与 Nexus 主页）](https://github.com/coolab342/Ghost-of-Tsushima-Toolkit-for-Blender) | 对马岛 xmesh / xpps / texmeshman 格式参考（MIT，要求署名）；本工作区的纯 Python 构建器按它核实字段后独立实现 |
| GoT SPS Noesis 插件 | [SilverEzredes](https://github.com/SilverEzredes/fmt_GoT_SPS-Noesis-Plugin) | 对马岛 SPS（XTBS）贴图格式参考（本项目未直接使用） |
| h2_pc_mi_091（HFW Export-Import Tool） | [id-daemon（Nexus）](https://www.nexusmods.com/horizonforbiddenwest/mods/1744) | 西之绝境 0.9.1：按流图组下标导出 / 导入 ascii 网格与 DDS 贴图；同页有 Johnny Dazzling 写的 Tutorial Edition 4（2026-03-21） |
| HFW Mod Manager | [KingJulz（Nexus）](https://www.nexusmods.com/horizonforbiddenwest/mods/137) | 西之绝境 0.9.8：Pack Mods 与 Characters 角色切换（写 `mod_NPC.ini`）；mod 文件夹放 `modinfo.json` |
| Odradek | [ShadelessFox](https://github.com/ShadelessFox/odradek) | Decima 资源查看与 json / cast 导出，CI 构建 1.0-SNAPSHOT；西之绝境只用于勘察，需指向原版流图 |
| GOWTool | [kainotoa](https://github.com/kainotoa/GOWTool)（`gowr-pc` 分支，commit `ef484028`，2024-11-01） | 战神5 wad 条目偏移解析与 MESH 布局的参考：便携包的 `wad.py` 移植了它的 `src/Wad.cpp` 偏移解析，`mesh.py` 按 `src/Formats.cpp` 读字段。该仓库未附许可证文件 |
| libSceAgcTextureTool.dll | 游戏自带（战神：诸神黄昏 PC 安装目录） | 战神5 贴图的 PS5 tiling / detiling，脚本通过 ctypes 调用；不随包分发 |
| RE-Engine-Lib（REE-Lib） | [kagenocookie/RE-Engine-Lib](https://github.com/kagenocookie/RE-Engine-Lib)（MIT） | 龙之信条2 DD2Tool 的读写核心，commit `bf0e5e5222700716516797613a54b9b61fedfc35`（2026-09-19），未修改。它支持 TU3.2 起的 PAK（feature 0x40 remap 表）、mesh `.260421070`（DD2_V3）和 tex `.251211553`。便携包只带 DD2Tool 的 C# 源码，REE-Lib 要自己取 |
| REFramework nightly（龙之信条2） | [nightly 发布](https://github.com/praydog/REFramework-nightly/releases) / [pak_mods 注入（PR #1830）](https://github.com/praydog/REFramework/pull/1830) | 01421 起才注入 `<游戏>/pak_mods/*.pak`。build 25290080 上用 01424：revision `d1461375aee4ec3f313170f8eaad12064eb542d9`，`REFramework.zip` SHA-256 `f035f1da6c9b199ef8348256abfd6bacef4a903485f75d9ab73be5249ae2b14c`，装进游戏的只有其中的 `dinput8.dll`（`14f4d6fd65218f850f39781fb53fb07ba28da6601c1954529098b91608e6ae88`）。退出游戏时可能崩溃或卡住（上游已知） |
| .NET SDK 10 | [微软下载页](https://dotnet.microsoft.com/download/dotnet/10.0) | 10.0.401，用来编译龙之信条2的 DD2Tool（REE-Lib 用到 C# 14）；DD2Tool 面向 net8.0，运行用 .NET 8 运行时。Windows 10 19044 未装 CET 修复时，对私有 SDK 副本运行便携包的 `clear_cet_flag.py` |
| CUE4Parse | [FabianFG/CUE4Parse](https://github.com/FabianFG/CUE4Parse)（NuGet `CUE4Parse` / `CUE4Parse-Conversion`） | 师父的 SifuExport 以 1.2.2.202610 编译（.NET 10）：`GAME_UE4_26`、AES 索引解密、JSON / glTF / 骨架 / 动画帧导出，以及烘焙后 mod pak 的引用读回；游戏 AES 密钥由用户自备。幻兽帕鲁的 PalExport 用同一版本（`GAME_UE5_1`；unversioned 包要配 usmap，读 pak 要 Oodle 的 `oo2core_9_win64.dll`）：列文件、JSON、`.uemodel` / `.ueanim` 导出、参考骨架和变形 dump、usmap 结构查询，以及 mod pak 读回。往日不再的 DgExport 也用这一版本（默认 `GAME_DaysGone`，读 UE 4.11 原版 cook 的 mod 包用 `GAME_UE4_11`）：列文件、JSON、原样存包、`.uemodel` 导出和骨架 dump；游戏的逐轨压缩面部动画它解成常量轨道，便携包另用 `anim_pertrack.py` 解码 |
| Unreal Engine 4.11.2 | [Epic Games Launcher](https://www.unrealengine.com/) | 往日不再（Bend 改过的 UE 4.11）的内容工程（必须名为 `BendGame`）：编辑器里手工导入 FBX 和贴图（4.11 没有编辑器 Python），`UE4Editor-Cmd -run=cook -cookall -iterate` 出原版 4.11 格式的包，游戏可以直接读；编辑器开着该工程时游戏会自行退出 |
| Unreal Engine 4.26.2 | [Epic Games Launcher](https://www.unrealengine.com/) | 师父的内容工程（名为 `Sifu`）、Python 插件、cook 与 UnrealPak；编辑器插件 SifuModTools 用 `RunUAT BuildPlugin` 编译（Windows 上需 Visual Studio 2019/2022 的 C++ 生成工具，本项目 UBT 选用 MSVC 14.44）。插件的 backstop 与加速度驱动结论来自 4.26 引擎源码 |
| Unreal Engine 5.1.1 | [Epic Games Launcher](https://www.unrealengine.com/) | 幻兽帕鲁的内容工程（名为 `Pal`，CL 23901901）、Python 插件、`-unversioned` cook；编辑器插件 PalModTools 和 KawaiiPhysics 由 UnrealBuildTool 随工程编译（`-Compiler=VisualStudio2019`，需 Visual Studio 的 C++ 生成工具） |
| KawaiiPhysics | [pafuhana1213/KawaiiPhysics](https://github.com/pafuhana1213/KawaiiPhysics)（MIT） | 幻兽帕鲁用 1.17.1（`VersionName`）：游戏内置的 KawaiiPhysics 与它属性布局相同，只装进 UE 5.1 工程的 `Plugins\KawaiiPhysics\` 用来编写服装层动画蓝图，不进 pak；便携包不含其源码，`kawaii_sim.py` 是按它 1.17.1 每帧步进写的 Python 移植。剑星用的是游戏方修改的 KawaiiPhysics-SB 1.11 |
| UEFormat | [h4lfheart/UEFormat](https://github.com/h4lfheart/UEFormat) | Blender 插件 `io_scene_ueformat`（manifest 0.10.0，需 Blender 自带的 `zstandard`）：幻兽帕鲁的 Blender 脚本按模块名启用它，读 CUE4Parse 导出的 `.uemodel` / `.ueanim`；放在 Blender 的 `scripts/addons_core/`，或用 `PAL_BLENDER_ADDONS` 指向其所在目录。往日不再用同一版本，放在 `addons_core/`：`build_body.py`、`face_rig.py`、`export_dummy_skeleton.py` 导入迪肯头部的 `.uemodel` |
| repak | [trumank/repak](https://github.com/trumank/repak/releases) | v0.2.3 CLI（`repak_cli-x86_64-pc-windows-msvc.zip` SHA-256 `6720d602144d75df477a99d5bedb6ea780997546afc335901d4937cafeaa73fa`，与发布页的校验文件一致；`repak.exe` `fcd538e5994b9bb833622d425ae346f4e0692f02d4b0025114a559f9b6286022`）：幻兽帕鲁 mod 用 `pack --version V11 --mount-point ../../../` 打 legacy pak |
| 幻兽帕鲁 usmap | [PalworldModding/UsefulFiles](https://github.com/PalworldModding/UsefulFiles)（Mappings） | `Mappings_1.0.5.usmap`（master 分支，2026-09-20 取，SHA-256 `e919d45fa8eebc38e6f864ba9594706ce84a531f6970a2b2dd8dfa453d0705d9`），对应 buildid 25246127；游戏是 unversioned cook，没有它 CUE4Parse 读不出属性。游戏更新后换对应版本 |
| ALERT（dat1lib） | [Tkachov/ALERT](https://github.com/Tkachov/ALERT)（GPLv3） | 漫威蜘蛛侠2 用 commit `bc90ed9b53fbcaa3b7acf94b36f00e77eab0dacb`（2024-06-05）：读 toc、DSAR 解压、crc32 / crc64。注意它按 i29 的 36 B 切资产头，i30 的头是变长的，本库脚本自己解析。便携包不带 ALERT，用 `SM2_ALERT` 指向自取的副本 |
| Overstrike | [Tkachov/Overstrike](https://github.com/Tkachov/Overstrike) | 漫威蜘蛛侠2 的 `.stage` 格式与安装逻辑（MetaInstaller_I29 + StageInstaller_I29_V2）的参照；便携包的 `sm2_install.py` 是按其行为重写的纯标准库安装器，未复制其代码。用户也可以直接用 Overstrike 安装发行的 `.stage` |
| UnPSARC | [rm-NoobInCoding](https://github.com/rm-NoobInCoding/UnPSARC/releases) | 对马岛 DSAR / PSARC 解包参考（本项目未直接使用；mod 包用自写的不压缩 PSARC 写入器） |

黑旗使用的 AnvilToolkit 1.3.6 与 Forge Injector 只是格式比较来源；实测表明它们不是此项目 BFR 的最终编译器。最终 field-4 Forge 实现已在便携包中提供。Oodle 是按需外部依赖，必须由用户合法取得原 DLL，保持脚本中的 SHA 验证。

AQ Modified 的具体分发源、NexusTools 与 Blender Source Tools 的当前版本需要接手环境自行从原作者发布入口确认。此处没有编造一个“通用下载地址”或把 SDK CE 当成任意 AQ 分支的等价替代。可先进行不依赖这些工具的解析/源审计，再继续编译阶段。
