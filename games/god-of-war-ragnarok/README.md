# God of War Ragnarök（战神：诸神黄昏，PC）

## 范围

这里整理 PC 版角色替换的可复用合同。材料来自一个项目：用 Karin_Original（FBX 加 VRM，套头衫校服版）替换两个角色。

- **奎托斯**（`r_heroa00.wad`）：玩家角色。参照物是用户自己的 KarinPicodraTech_Kratos mod。本案以它的 wad 作为构建底板，但它替换过的流数据全部从原版 `root.lodpack` 重建，不复用它的几何。
- **芙蕾雅**（`r_freyavalkyrie00.wad`）：跟随奎托斯的同伴，也是各剧情关卡里的芙蕾雅。

证据边界是 Steam App `2322010`、build `18979360`（GoWR.exe SHA-256 `4d242ab5577379418196c692d3dff989f7223d3d7d01e8e0d2736cbc512c0eff`），快照时间 2026-10-02。

- 网格定义下标、网格组编号、流缓冲区哈希、骨骼编号、贴图名规则，都是该 build 的 `build-sensitive` 值；
- 缩放、部件分配、减面比例和贴图取值是 `case-derived`。

## 核心方法

- **原地写入。** 引擎按原版布局给每个网格定义预分配资源。Karin 只能写进原有的网格定义，顶点数和索引数都不能超过该定义在原缓冲区里的空间。缓冲区大小保持不变，模型太大就拆进同组的几个定义。
- **补丁包按哈希覆盖。** 改过的流缓冲区哈希加 1，写进补丁 `.lodpack`；wad 里的网格定义和头部流清单同步改成新哈希。贴图写进补丁 `.texpack`。两个包都由 `exec/boot-options.json` 的 `patch-lodpacks` / `patch-texpacks` 加载，不用解包原版资源。
- **不改骨架。** 在 Blender 里把 Karin 逐骨摆到目标角色的绑定姿势，烘焙进网格。蒙皮用 Karin 自己的权重，按人形骨角色映射到目标骨架上真正带蒙皮的骨骼。
- **隐藏其余网格。** 每个网格组至少保留一个非空网格。隐藏的定义画一个退化三角形，指向一块随补丁包发布的全零区域。
- **纯 Python 工具链。** wad、网格、补丁包的读写都是自写的；贴图的 PS5 tiling 调用游戏自带的 `libSceAgcTextureTool.dll`。不依赖社区的 GoW_rnrk_pc / img2gnf。

## 源模型修正（跨游戏）

2026-10-02 起，共享源模型 Karin_Original 的 FBX 和 VRM 已把 body_2 的形态键 `kisekae_Knee` 烘焙进基础网格，起因是多个游戏的 mod 都出现了膝盖皮肤穿出过膝袜。用这个源模型的其他项目要注意版本差异，见 [构建流程](BUILD_PIPELINE.md#0-源模型修正)。

## 证据纪律

沿用本库的五级证据（`reference-inferred` → `runtime-confirmed`）。本作的四条教训：

1. **先确认游戏真的加载哪个 wad。** 第一版芙蕾雅改的是 `r_freya00.wad`，游戏里毫无变化。游戏的资源依赖表里有 10 个资源依赖 `R_FreyaValkyrie00`，依赖 `R_Freya00` 的一个都没有。
2. **回读校验要逐顶点比对骨骼和权重。** 只检查「骨骼索引小于骨骼数」时，芙蕾雅头颈组的骨骼格式写错（u16 写成了 11 bit 打包）也能通过，到了游戏里整块网格绑错骨骼。
3. **只绑定原版网格真正带蒙皮的骨骼。** 芙蕾雅的骨架在同一关节上叠了不带蒙皮的 FK 控制骨。绑到控制骨上的裙子和尾巴，在游戏里整体翻到背后。
4. **卡死先二分。** 两条硬限制（容量、每组至少一个非空网格）和「隐藏要画退化三角形，不能只清零索引」，都是用一串最小构建在实机里二分出来的，从格式本身推不出来。

## 阅读入口

- [格式](FORMATS.md)：wad、MESH / MG 定义、顶点分量与骨骼权重布局、lodpack / texpack、boot-options、资源依赖表
- [构建流程](BUILD_PIPELINE.md)：源模型修正、骨架角色表、Blender 姿势拟合、远景 LOD、几何组装、槽位规划、原地写入、隐藏、贴图
- [验证与发布](VALIDATION_AND_RELEASE.md)：逐顶点回读、屈膝模拟、复现基线、实机测试方法、发布包
- [排障手册](TROUBLESHOOTING.md)：症状定位表、卡死二分记录、被否决的做法
- [案例：Karin_Original 替换奎托斯与芙蕾雅](cases/KARIN_ORIGINAL.md)

## 公开边界

本目录只有文档。以下内容都不在这里：

- 模型，以及从模型派生的拟合结果和骨骼表；
- 游戏 wad、补丁包，以及从游戏读出的骨架和贴图；
- 参照 mod 的资源；
- 发布包。

构建脚本放在 [战神5便携包](../../portable-kits/god-of-war-ragnarok/README.md)。贴图那一步要调用游戏自带的 DLL，只能在装了游戏的 Windows 上运行。
