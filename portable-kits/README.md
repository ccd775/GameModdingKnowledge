# Modding 便携工具包

无需注册 Skill。把整个仓库或导出的单游戏目录交给 agent，先读对应 README，按当前问题选择工具；构建、排障、暂停和复测可以反复进行。

| 游戏 | 实际附带脚本 | 命令与边界 |
| --- | --- | --- |
| MK1 | 图集拼合、hash/差异检查、PSK索引计划、比例/骨盆/颈部算子、三件套预检部署 | [使用](mortal-kombat-1/README.md) |
| 杀手 WOA | PRIM/GLB 校验、roundtrip 比较、六槽 TEXT/TEXD 重建 | [使用](hitman-world-of-assassination/README.md) |
| 看门狗 | 不用 ZModeler 的 XBG 写出器（FBX→char01.xbg、写后回读）、骨架关节移动、FAT v8 解包/重打包、PNG 直接编码 XBT；XBT/DDS 提取、注入、配对审计 | [使用](watch-dogs/README.md) |
| 黑旗记忆重置 | Forge v50 BMS 提取、LZ4 重建、显式资源替换 | [使用](assassins-creed-black-flag/README.md) |
| RE4R | KPKA v4 路径哈希、目录和 payload 提取 | [使用](resident-evil-4-remake/README.md) |
| L4D2 | VPK 提取/回读、VTA 缩放、StudioMDL 运行记录 | [使用](left-4-dead-2/README.md) |
| HD2 | 三件套解析、LUT 行折叠/注入、SDK UV 复制 | [使用](helldivers-2/README.md) |
| 西之绝境 | 贝塔替换构建器（VRM 拟合、遮挡剔除、分区权重、拼页、h2 ascii）、导入批处理、core 包围盒与 SkinInfo 补丁、姿势预览、游戏按键 | [使用](horizon-forbidden-west/README.md) |
| 对马岛 | 忠赖的铠甲角色替换完整构建器（VRM 拟合、剔除/减面、拼页、xmesh/xpps/SPS、PSARC）与离线校验渲染 | [使用](ghost-of-tsushima/README.md) |
| 战神：诸神黄昏 | 奎托斯 / 芙蕾雅替换构建器（原地写入网格、单组补丁 lodpack、GNF 贴图包）、逐顶点回读、屈膝模拟、骨架角色表、源模型形态键烘焙、Blender 拟合与减面 | [使用](god-of-war-ragnarok/README.md) |
| 浪人崛起 | KT 引擎 G1M / G1H 读取与原地隐藏、G1T tile 与常量填充、rdb / fdata / KTID 槽表与共用贴图审计、按原版分段重分腿部权重、shader 包拆分 | [使用](rise-of-the-ronin/README.md) |
| 龙之信条2 | Karin 玩家替换构建：Blender 拟合到原生女性骨架、DD2Tool 的 C# 源码（PAK 提取与打包、mesh / mdf2 / chain 读写）、链规格、贴图；REFramework 替换脚本、开发控制台与查询 | [使用](dragons-dogma-2/README.md) |
| 师父 | 女主默认服装替换构建：多 profile 的 Blender 构建（W 姿势重摆、面部、裙摆代理、骨链、躯干权重）、AO 与贴图、骨链调参；UE 4.26 编辑器 Python 与插件 SifuModTools 的 C++ 源码、SifuExport（CUE4Parse）的 C# 源码、cook / pak 与抓屏工具、发行打包 | [使用](sifu/README.md) |
| 幻兽帕鲁 | 女性玩家默认服装替换构建：从 VRM 构建身体、脸和隐藏发型（原版骨朝向 + Karin 比例、物理链落到游戏骨架的配件链、11 个面部形变）、KawaiiPhysics 1.17.1 离线模拟与参数导出、姿势探针与预览；UE 5.1 编辑器 Python 与插件 PalModTools 的 C++ 源码、PalExport（CUE4Parse）的 C# 源码、cook / 白名单分包 / repak 与读回工具 | [使用](palworld/README.md) |

[公共层](common/README.md) 提供项目初始化、哈希锁、断点、工具预检、确定性 ZIP 和 Blender 审计。

Python 3.10+；大多数脚本只用标准库，Forge 需 lz4，文档检查和导出需 markdown-it-py，对马岛构建器另需 `ghost-of-tsushima/requirements.txt`（numpy、scipy、etcpak、texture2ddecoder，需 Python 3.12+），西之绝境构建器另需 `horizon-forbidden-west/requirements.txt`（numpy、scipy，需 Python 3.12+），战神构建器另需 `god-of-war-ragnarok/requirements.txt`（numpy、scipy、etcpak、texture2ddecoder，需 Python 3.12+；贴图那一步要在 Windows 上调用游戏自带的 DLL），浪人崛起的腿部权重工具另需 `rise-of-the-ronin/requirements.txt`（numpy、scipy），其余浪人脚本只用标准库；龙之信条2的贴图脚本另需 `dragons-dogma-2/requirements.txt`（numpy，需 Python 3.12+）；龙之信条2的 DD2Tool 只随包提供 C# 源码，要自己取 RE-Engine-Lib 并用 .NET 10 SDK 编译，Lua 脚本由游戏里的 REFramework 运行；师父的贴图脚本另需 `sifu/requirements.txt`（numpy，需 Python 3.12+）和根目录的 Pillow，抓屏拼图只需 Pillow，Blender 脚本在 Blender 4.2 内运行，UE 脚本、编辑器插件（C++）和 SifuExport（C#，CUE4Parse，.NET 10 SDK 编译）只随包提供源码，要在装 UE 4.26.2 的 Windows 上运行，游戏 AES 密钥由用户自备；幻兽帕鲁的 `gen_ue_config.py` 另需 `palworld/requirements.txt`（numpy，需 Python 3.12+）和根目录的 Pillow，Blender 脚本在装了 UEFormat 插件的 Blender 4.2 内运行，UE 脚本、编辑器插件（C++）和 PalExport（C#，CUE4Parse，.NET 10 SDK 编译）只随包提供源码，要在装 UE 5.1.1 的 Windows 上运行，KawaiiPhysics 1.17.1 插件、repak、usmap 和 Oodle DLL 由用户自备。Windows 编译器在 Windows 中执行，Blender 审计在 Blender 内执行。仓库根命令：

```powershell
python -m pip install -r requirements.txt
python -B portable-kits/common/modkit.py init ../MyMod --game left-4-dead-2
python -B tests/test_portable_tools.py
python -B tools/check_repository.py
python -B tools/export_kit.py --game left-4-dead-2 --output ../L4D2-Portable
```

导出器带上该游戏文档、实际脚本、公共层和依赖说明，无需父仓库。不会带入私人模型或第三方二进制。

工具补齐格式步骤，不自动决定新角色的骨架、目标资源和外观。迁移来源见 [PROVENANCE.json](PROVENANCE.json)，实测边界见 [VALIDATION.md](VALIDATION.md)。
