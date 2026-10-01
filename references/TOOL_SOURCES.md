# 工具获取与固定版本

历史版本是项目曾使用的快照，不是永远推荐的最新版。下载后记录 URL、版本、可执行文件或插件树的 SHA-256；先对当前游戏原生资源做 roundtrip，再判断兼容性。便携包不替用户下载或执行不明二进制。

| 工具 | 作者/维护者入口 | 在本工作区的用法 |
| --- | --- | --- |
| Blender | [官方历史版本](https://download.blender.org/release/) | 4.2.23 与 4.5.12 曾用于不同项目，DMC5 用 4.0.2；匹配源文件与插件 |
| RPKG Tool | [Glacier 工具页](https://glaciermodding.org/rpkg/) | CLI/GUI 2.34.0，导出 GLB/TGA 后重建并回读 |
| SMF / GlacierKit | [维护者的 suit modding 指南](https://glaciermodding.org/docs/modding/hitman/guides/suitmodding/) | SMF 2.33.40、GlacierKit 1.12.15 为历史锁；使用当前实体补丁 |
| ZModeler | [作者官网](https://www.zmodeler3.com/) | 3.3.1.1244；XBG filter、Skeleton Bind、L0/L1 Compound，需用户自己的授权 |
| RE Mesh/Chain 工具 | [NSACloud](https://github.com/NSACloud) / [Chain 项目](https://github.com/NSACloud/RE-Chain-Editor) | Mesh 0.66、Chain 14.0；在 Blender 插件设置中安装并测试当前文件格式。DMC5 用 Mesh 0.44（无界面模式需屏蔽 `console_toggle`，MDF v10 只读不写），Chain 14.0 的 `file_re_chain` 可往返 chain .21 |
| REFramework | [nightly 发布](https://github.com/praydog/REFramework-nightly/releases) | RE Engine 游戏的加载器；MHWs exe 1.42.0.2 上 nightly 01212 无法加载散装贴图，01424 可以。每次游戏更新后重新确认，记录日志中的 commit |
| BoneSystem（MHWs） | [作者发布帖（南风焓）](https://www.caimogu.cc/post/1937594.htm) | 26.1.13.1；REFramework 插件，独立骨骼与表情映射，配置见 MHWs 技术合同 |
| Fluffy Mod Manager | [作者官网](https://www.fluffyquack.com/) | MHWs、DMC5 的 mod 安装/回退（DMC5 为 invalidate 方式）；以其 `installed.ini` 为游戏目录的权威记录 |
| Crowbar | [作者项目](https://github.com/ZeqMacaw/Crowbar) | 0.74，Source 伴随文件反编译 |
| Source 工具 | [Valve Source SDK](https://github.com/ValveSoftware/source-sdk-2013) | StudioMDL/VTEX/VPK/HLMV 使用目标 L4D2 安装提供的版本，不以 SDK2013 编译器替代 |
| HD2SDK CE | [维护者项目](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition) | 获取插件后固定 commit；不同 AQ 分支需单独作 Unit 往返测试 |
| FileDiver | [维护者项目](https://github.com/Obsoletes/filediver) | archive/FileID 提取；使用下载包自身 help 确认参数 |
| DirectXTex | [微软项目](https://github.com/microsoft/DirectXTex) | texconv 固定 SHA，进行 DDS 转换及解码检查 |
| Ghost of Tsushima Toolkit for Blender | [Dave349234（Nexus）](https://www.nexusmods.com/profile/Dave349234) / [GitHub（coolab342 仓库，README 链接 Dave349234 的 Ko-fi 与 Nexus 主页）](https://github.com/coolab342/Ghost-of-Tsushima-Toolkit-for-Blender) | 对马岛 xmesh / xpps / texmeshman 格式参考（MIT，要求署名）；本工作区的纯 Python 构建器按它核实字段后独立实现 |
| GoT SPS Noesis 插件 | [SilverEzredes](https://github.com/SilverEzredes/fmt_GoT_SPS-Noesis-Plugin) | 对马岛 SPS（XTBS）贴图格式参考（本项目未直接使用） |
| UnPSARC | [rm-NoobInCoding](https://github.com/rm-NoobInCoding/UnPSARC/releases) | 对马岛 DSAR / PSARC 解包参考（本项目未直接使用；mod 包用自写的不压缩 PSARC 写入器） |

黑旗使用的 AnvilToolkit 1.3.6 与 Forge Injector 只是格式比较来源；实测表明它们不是此项目 BFR 的最终编译器。最终 field-4 Forge 实现已在便携包中提供。Oodle 是按需外部依赖，必须由用户合法取得原 DLL，保持脚本中的 SHA 验证。

AQ Modified 的具体分发源、NexusTools 与 Blender Source Tools 的当前版本需要接手环境自行从原作者发布入口确认。此处没有编造一个“通用下载地址”或把 SDK CE 当成任意 AQ 分支的等价替代。可先进行不依赖这些工具的解析/源审计，再继续编译阶段。
