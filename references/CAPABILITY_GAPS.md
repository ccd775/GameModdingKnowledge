# 能力与边界

本仓库提供长线工作方法、实际格式工具与历史案例。它可以作为 agent 的制作资料，但没有在陌生机器上完成所有游戏新角色的端到端验收，因此不能称为“一键生成任意 Mod”。

| 游戏 | 已带实现 | 继续制作时需适配 |
| --- | --- | --- |
| MK1 | Atlas/索引检查、骨盆与颈部数学算子、三件套预检和备份部署 | 每角色骨架映射、定制UE导入/Cook、native多export/store/redirect写入、游戏复测 |
| Hitman | GLB/PRIM 验证、roundtrip、六槽 TEXT 重建 | 当前实体 QuickEntity、rig/atlas、RPKG/SMF |
| Watch Dogs | 不用 ZModeler 的 XBG 写出器（FBX→char01.xbg）、骨架关节移动、FAT v8 解包/重打包、XBT 解析/注入/配对、PNG 直接编码 XBT；通用 VRM 构建器：拟合与摆姿势、骨架贴合、权重映射、贴图拼图集、打包 ModManager ZIP；物理：在闲置节点上搭链、裙子或大衣挂到模板的大衣布料上、背面副本、导出游戏碰撞体 | 一个 ZModeler 布局的 char01 底包（模板 XBG 与贴图 donor）、新模型的 profile（材质分槽、次级骨链、物理段）、可选的游戏碰撞体导出文件、XBG GPU 面数审计、实机检查；表情未做；链只原地晃动，跑动时不会向后飘（引擎限制） |
| Black Flag | Forge v50 LZ4 提取/重建 | 当前 Mesh writer/target rig、纹理和角色局部资源合同 |
| RE4R | KPKA v4 哈希/目录/提取 | RE Mesh/Chain 工具、每角色映射和 PFB/RSZ |
| L4D2 | VPK 提取/校验、VTA 缩放、StudioMDL 记录器 | 源 SMD/QC、flex/procedural/physics、MDL 深审计 |
| HD2 | patch triplet、LUT、SDK UV 复制 | 当前 AQ/SDK、Unit carrier、权重和 Piece ownership |
| MHWs | 仅文档（合同、排障、自测方法），无便携脚本 | RE Mesh/Chain 工具、BoneSystem、当前 REFramework；每角色骨架/脸部映射、挂点骨与碰撞拟合 |
| Horizon Forbidden West | 构建器：VRM 拟合、遮挡剔除、分区权重继承、拼页、h2 ascii 写出；导入批处理（成功数核对）、core 包围盒与 SkinInfo 补丁、姿势预览 | id-daemon 的 h2_pc_mi_091 与 Mod Manager（用户自取）、新模型的案例常量（网格名、遮盖规则、光泽）、新 build 的槽位与原版计数复核、实机复测 |
| God of War Ragnarök | 完整构建器：wad / MESH / MG 读写、原地写入与槽位规划、退化三角形隐藏、补丁 lodpack / texpack、骨架角色表、Blender 姿势拟合与减面；逐顶点回读、屈膝模拟；源模型形态键烘焙（FBX / VRM） | 游戏自带的 `libSceAgcTextureTool.dll`（贴图，仅 Windows）、Blender；新角色的骨骼角色表与网格组选择、新 build 的定义下标与哈希复核；次级物理与表情未做；战斗与过场复测 |
| Ghost of Tsushima | 完整构建器：VRM 拟合与肩部反解、剔除/减面、UV 拼页、xmesh/xpps/SPS 写入、PSARC 打包；离线校验与渲染 | 新模型的 profile（网格→槽位、遮盖规则、参数）、新 build 的偏移与断言复核、实机复测 |
| DW Origins | 仅文档（合同、排障、读档自测流程），无便携脚本；构建脚本留在项目目录 | gust_stuff、DirectXTex；rdb/fdata/KTID 解析可用浪人便携包的 `ktdata.py`；新 build 的 KTID 槽表与原版权重分布重新统计；次级物理（NUNO / 链骨）未做；实际战斗复测 |
| Rise of the Ronin | G1M / G1H 读取与原地隐藏、占位面塌缩、原生绑定检查；G1T tile 互转、DDS 导出、原容器常量填充、mip 检查；rdb / fdata / KTID 提取与槽表、共用贴图审计；按原版分段重分腿部权重（含回读与离线姿势）；shader 包拆分 | 游戏数据（`fdata_package_dx12`）、gust_stuff 与 Blender（新几何）、texconv（新颜色图）；从源模型构建的贴合 / 分件 / 图集脚本未收录；物理与表情未做；室内绑腿未解决；实机复测 |
| Sifu | Blender 构建器（源模型归一化、W 骨架拟合、TPS 面部权重、W 躯干分布、NvCloth 代理与碰撞、备用骨上的骨链、按 profile 构建多个模型）、AO 与贴图、离线姿势预览与裙摆替身；UE 4.26 编辑器插件（NvCloth 代理 + backstop、物理资产、RigidBody 后处理蓝图）与 commandlet 构建脚本；cook / pak 与 CUE4Parse 读回；发行打包 | UE 4.26.2 与 C++ 生成工具、游戏 AES 密钥（自备）、CUE4Parse 编译；新模型的 profile（网格角色、材质分槽、悬挂件、链规格）；对话口型、过场、其它服装与分身敌人复测；真正的法线贴图 |
| Palworld | Blender 构建器（VRM → OldCloth001 骨架：原版朝向 + Karin 位置的重摆、权重映射、物理链改名到游戏骨架配件链、11 个面部形变、双面裙、隐藏发型、VRM 碰撞体 → 胶囊）、KawaiiPhysics 1.17.1 离线模拟与参数导出、姿势探针与预览；UE 5.1 编辑器插件 PalModTools（无界面编写 AnimBP）与导入 / AnimBP 脚本；cook、按白名单分包、repak 打包与 CUE4Parse 读回 | UE 5.1.1 与 C++ 生成工具、KawaiiPhysics 1.17.1 源码插件、与 build 对应的 usmap、Oodle DLL、CUE4Parse 编译（均自备）；新模型的链映射与配件链复核、胶囊与参数；r4 手感的实机判断；除眨眼外的表情、游泳 / 滑翔 / 战斗场景复测；头发色调 |
| Marvel's Spider-Man 2 | i30 toc / `.model`（网格、蒙皮、关节、Look 组、AnimDynamics 段）/ `.texture` / `.material` / `.actor` 的纯 Python 读写；VRM 重摆与 TPS 拟合、按骨架签名批量替换 108 个模型、面部骨骼表情、裙子权重迁移；动力学段写入与原版逐字回归；头部载体物理（NeverCull、关节包围球、HeadManager 映射、批量去链）；`.stage` 写入与纯标准库安装器；离线回读与姿势检查 | ALERT 的 `dat1lib`（GPLv3，自备）、游戏目录、源 VRM；换 build 后重建名字索引与目标 / loadout 表；便装与 young 的物理、眨眼（Morph2 未解）、切线、半透明材质；碰撞（AnimDynamics 无碰撞体）；拍照模式 / 过场 / boss 战复测 |
| Days Gone | 包工具：pak v3 读写、最小 uasset 读写、参考骨架定位、骨架重定向模式修改、带内联着色器图的 MI 原地改引用、GPU 顶点缓冲原地改法线 / 位置、per-track 压缩动画解码、烘焙动画蓝图插入 AnimDynamics / CopyBone 节点、眼睑放大骨补丁、look 批量改写、组装 pak；Blender 构建器（VRM → 迪肯骨架、TPS 面部权重与关节迁移、眼睑骨拟合、按口型求解嘴部权重、面部动画模拟与预览）；DgExport（CUE4Parse）源码；测试机 PowerShell 工具 | UE 4.11.2 编辑器（FBX 只能 GUI 导入）、UEFormat Blender 插件、CUE4Parse 编译、游戏本体；新模型的骨映射、弹簧参数与口型表；照片模式双马尾拉伸、过场 / 骑车 / 其它服装复测；Remastered 分支未验证 |
| The Witcher 3 Remastered | v5 bundle 读写、v7 metadata.store 写出与原版重建比较、WolvenKit 骨名修复（CR2W 表 / 头 CRC 重算）、空 / 单网格 / dangle / 头部物品模板生成、铺满全部杰洛特物品模板并打包；dyng 与 w3fac JSON 写出；Blender 构建器（逐骨拟合、待机姿势里的肩部拟合、权重重定向、裙子跟随大腿、dyng 规格含形状链接与碰撞代理、形状键 → 平移表情骨分解、w2mesh / xbm 导出）；离线检查（目标形状渲染、裙子射线穿模、look-at 滚转、头部碰撞中心、网格内容比较）；准备 / 构建 PowerShell 流水线 | Blender 5.0 + Witcher3-Blender-Tools、WolvenKit 7 nightly CLI、texconv（插件调用，Windows）、游戏本体；新模型的骨名映射、dyng 分组与碰撞代理、表情映射表、比例参数；v0.4.4 的实机确认；骑马 / HairWorks / 游戏内对话复测；剑鞘挂点 |
| RE9 Requiem | 仅文档（合同、排障、展柜自测与运行时探针方法），无便携脚本 | RE Mesh/Chain 工具、REasy RSZ 类型库、REFramework；每角色部件/变体覆盖、refskel 映射、chain2 拟合与 prefab 注入；实际游玩复测 |

完整清单见 [便携入口](../portable-kits/README.md)。带有 --help 的脚本也有明确格式限制，不能把旧角色合同当成所有模型的常量。

外部工具从 [维护者入口](TOOL_SOURCES.md) 获取并固定版本。GUI 工具按游戏操作清单运行，使用新截图/控件状态确认，不复用历史 PID、句柄或坐标。无需安装作者个人的 Computer Use skill；接手 agent 可以使用其自身可靠的 GUI 能力，或由用户完成明确步骤。

骨架映射、衣物物理和材质外观是按源模型决定的项目工作。参考 Mod 只提供已声明的 donor/接口作用，不打包其可见资产。构建失败可以回到前一阶段；用户实机反馈能够推翻离线推断。
