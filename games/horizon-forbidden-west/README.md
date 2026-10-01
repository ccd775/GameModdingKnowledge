# Horizon Forbidden West（地平线：西之绝境，PC）

## 范围

这里整理 PC 版主角替换的可复用合同。材料来自一个项目：用 Karin_Original（VRM，套头衫校服版）替换贝塔（Beta）。

- 玩家用 HFW Mod Manager 的角色切换来扮演她：Characters → Beta → Activate。
- 游戏里埃洛伊和贝塔外观相同，所以替换贝塔就等于替换主角。
- 参照物是用户已有的「Karin Final 006」，它的 modinfo 作者为 Johnny Dazzling，是 Karin PicodraTech 的移植，有 4 个服装变体。它用来对照槽位和修复手法；本库不复制它的任何资源。

证据边界是 Steam App `2420110`、build `14835813`（游戏内版本 1.5.80.0），快照时间 2026-10。

- 组下标、网格/贴图编号、SkinInfo 的原版计数、包围盒数值，都是该 build 的 `build-sensitive` 值；
- 缩放、权重分区、遮盖距离和光泽值是 `case-derived`。

## 核心方法

- **只覆盖 Beta 的模型组，不新增资源。** 模型组在流图里的下标是 `0xB2C4`。用 id-daemon 的导入工具 `h2_pc_mi_091` 写入，产出一个 core 文件和若干 stream 文件，交给 Mod Manager 的 Pack Mods 打包。
- **Karin 放进 3 个原有子网格：**
  - 上身：网格 215 的 sm1；
  - 下身：网格 260 的 sm0；
  - 脸：面部皮肤网格，LOD0–7 各一个。

  这三处顶点数随模型变化。其余子网格保留原版的顶点数和索引数，所有顶点塌缩到同一点。
- **不改骨架。** 用 TPS 把 Karin 拟合到 Beta 的绑定骨架（整体 1.3 倍，头部刚性）。权重按身体分区从 Beta 原版顶点继承，PBD 骨不参与。
- **两张 2048 颜色页：**
  - 脸页：b2c4 的 `240`；
  - 身体页：皮肤贴图组 1036 的 `2`。

  头发不能放在脸页上（见下文）。
- **两个必做的 core 补丁：**
  - 面部网格的 SkinInfo 从 `CsNbtGen` 改成 `VsNbt`，否则读档卡死；
  - 包围盒放大到能装下 Karin。

## 证据纪律

沿用本库的五级证据（`reference-inferred` → `runtime-confirmed`）。本作的三条教训：

1. **读档卡死不一定是内容错误。** 这次的根因是 GPU 端按原版顶点数预存的计数（`VertexComputeNbtCount`）。导入工具只换缓冲，不更新这个计数。先把参照 mod 的 core 和原版逐字段对比，就能找到它已经做过的同一个修复。
2. **着色问题只在实机暴露。** 头发放在脸页上时，离线渲染完全正常。到了游戏里，面部着色器的次表面散射把阴影里的头发染成棕红色。材质归属要按着色器选，不能按贴图页的空位选。
3. **自动化实测要先确认输入真的进了游戏。** 游戏会丢掉很短的按键，必须用扫描码按住约 120 ms。同一台机器上还有其他会话在跑游戏，抢前台前要先协调。

## 阅读入口

- [格式与工具](FORMATS_AND_TOOLS.md)：流图组下标、导入工具、ascii 格式、网格和贴图槽、SkinInfo、包围盒、Mod Manager
- [构建流程](BUILD_PIPELINE.md)：VRM 读入、遮挡剔除、TPS 拟合、权重继承、拼页、子网格组装、LOD 策略
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、复现基线、实机测试方法、发布包
- [排障手册](TROUBLESHOOTING.md)：症状定位表、被证伪的捷径
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)

## 公开边界

本目录只有文档。以下内容都不在这里：

- 模型：本库按惯例不放任何模型；
- 贴图、游戏归档、导出的原生网格和骨架；
- 参照 mod 的资源；
- 发布包。

构建脚本是纯 Python，放在 [西之绝境便携包](../../portable-kits/horizon-forbidden-west/README.md)。导入那一步依赖 id-daemon 的 `h2_pc_mi_091.exe`，要由用户自己从作者的 Nexus 页面获取，见 [工具来源](../../references/TOOL_SOURCES.md)。
