# 工具获取与固定版本

历史版本是项目曾使用的快照，不是永远推荐的最新版。下载后记录 URL、版本、可执行文件或插件树的 SHA-256；先对当前游戏原生资源做 roundtrip，再判断兼容性。便携包不替用户下载或执行不明二进制。

| 工具 | 作者/维护者入口 | 在本工作区的用法 |
| --- | --- | --- |
| Blender | [官方历史版本](https://download.blender.org/release/) | 4.2.23 与 4.5.12 曾用于不同项目；匹配源文件与插件 |
| RPKG Tool | [Glacier 工具页](https://glaciermodding.org/rpkg/) | CLI/GUI 2.34.0，导出 GLB/TGA 后重建并回读 |
| SMF / GlacierKit | [维护者的 suit modding 指南](https://glaciermodding.org/docs/modding/hitman/guides/suitmodding/) | SMF 2.33.40、GlacierKit 1.12.15 为历史锁；使用当前实体补丁 |
| ZModeler | [作者官网](https://www.zmodeler3.com/) | 3.3.1.1244；XBG filter、Skeleton Bind、L0/L1 Compound，需用户自己的授权 |
| RE Mesh/Chain 工具 | [NSACloud](https://github.com/NSACloud) / [Chain 项目](https://github.com/NSACloud/RE-Chain-Editor) | Mesh 0.66、Chain 14.0；在 Blender 插件设置中安装并测试当前文件格式 |
| Crowbar | [作者项目](https://github.com/ZeqMacaw/Crowbar) | 0.74，Source 伴随文件反编译 |
| Source 工具 | [Valve Source SDK](https://github.com/ValveSoftware/source-sdk-2013) | StudioMDL/VTEX/VPK/HLMV 使用目标 L4D2 安装提供的版本，不以 SDK2013 编译器替代 |
| HD2SDK CE | [维护者项目](https://github.com/Boxofbiscuits97/HD2SDK-CommunityEdition) | 获取插件后固定 commit；不同 AQ 分支需单独作 Unit 往返测试 |
| FileDiver | [维护者项目](https://github.com/Obsoletes/filediver) | archive/FileID 提取；使用下载包自身 help 确认参数 |
| DirectXTex | [微软项目](https://github.com/microsoft/DirectXTex) | texconv 固定 SHA，进行 DDS 转换及解码检查 |

黑旗使用的 AnvilToolkit 1.3.6 与 Forge Injector 只是格式比较来源；实测表明它们不是此项目 BFR 的最终编译器。最终 field-4 Forge 实现已在便携包中提供。Oodle 是按需外部依赖，必须由用户合法取得原 DLL，保持脚本中的 SHA 验证。

AQ Modified 的具体分发源、NexusTools 与 Blender Source Tools 的当前版本需要接手环境自行从原作者发布入口确认。此处没有编造一个“通用下载地址”或把 SDK CE 当成任意 AQ 分支的等价替代。可先进行不依赖这些工具的解析/源审计，再继续编译阶段。
