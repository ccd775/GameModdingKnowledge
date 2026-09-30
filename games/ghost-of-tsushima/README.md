# Ghost of Tsushima DIRECTOR'S CUT（对马岛之魂 导演剪辑版，PC）

## 范围

这里整理 PC 版主角替换的可复用合同。材料来自两个项目，都是用 Karin 的 VRM 模型替换仁（Jin）的「忠赖的铠甲」（`hero_kamakura_armor`）：

- Karin_Original：套头衫校服版，四版。
- Karin PicodraTech：露肩外套版，四个构建。

证据边界是 Steam App `2215430`、build `23879181`（2026-09 快照）。文中的偏移、骨骼索引、部件哈希和槽位容量都是该 build 的 `build-sensitive` 值；阈值和参数是 `case-derived`。

## 核心方法

- **不新增资源。** 模型写进 `hero_kamakura_armor_all_ranks.xmesh` 的 8 个 LOD0 部件原有缓冲，顶点数和索引数都不变。其余部件，以及 Jin 的身体、头、头发等 38 个网格，用 `hero.xpps` 的位置量化缩小到不可见。
- **Mod 包是普通 PSARC，放进 `cache_pc\psarc\`。** 文件数据必须不压缩，压缩后过厂商 logo 就黑屏卡死。
- **不改骨架。** Karin 按 VRM 人形骨骼拟合到 Jin 的 655 骨绑定骨架，用 TPS 空间变形、皮肤半径控制环和头部刚性映射完成。权重映射到 Jin 的主骨、扭转骨和脊柱链。
- **肩部是本作的核心难点。** Jin 的上臂转轴在 Karin 肩关节外侧约 8 cm。只要在 T-pose 下拟合，手臂一下垂，根部就会翻起来。露肩服装必须按下垂姿势反解绑定位置，见 [拟合与绑定](FITTING.md#肩部转轴不匹配本作最重要的一条)。
- **容量有限。** 8 个部件共 46.5k 顶点、5 张贴图页。模型装不下时依次做：
  1. 遮挡剔除；
  2. 把手拆出来；
  3. 只对布料、鞋和躯干皮肤做 QEM 减面；
  4. 按 UV 岛重新拼贴图页。
- **一套工具服务多个模型。** 每个模型一个 profile。改工具后，旧 profile 的输出必须逐字节不变，这就是回归闸门。

## 证据纪律

沿用本库的五级证据（`reference-inferred` → `runtime-confirmed`）。本作的两条特别教训：

1. **第二、三个构建在实机里暴露的肩部缺陷，离线下垂姿势渲染里其实都有。** 第二个的尖角看到了但被低估；第三个是因为只看了皮肤的数值指标，没有看手臂根部的全部网格（袖套边、外套领口）。审查时要把相关网格从正、侧、背三个方向都看一遍。
2. **要和源模型按同比例对比，不能只和上一版对比。** 腿套相对鞋子的比例失调，只和上一版比是看不出来的。

## 阅读入口

- [格式与交付合同](FORMATS.md)：归档、hero.xpps、xmesh、SPS 贴图、槽位、骨骼索引
- [拟合与绑定](FITTING.md)：VRM 读入、TPS 拟合、肩部转轴、脚和着地、权重映射
- [容量、剔除与贴图页](CAPACITY_AND_TEXTURES.md)：遮挡剔除、QEM 减面、UV 岛拼页
- [验证与发布](VALIDATION_AND_RELEASE.md)：离线闸门、姿势渲染、回归、发布
- [排障手册](TROUBLESHOOTING.md)：症状定位表、被证伪的捷径
- [案例：Karin_Original](cases/KARIN_ORIGINAL.md)
- [案例：Karin PicodraTech](cases/KARIN_PICODRATECH.md)

## 公开边界

本目录只有文档。以下内容都不在这里：

- 模型（PicodraTech 的 VRM 许可禁止再分发；本库按惯例不放任何模型）；
- 贴图、游戏归档和提取出的原生资源；
- 发布包。

构建工具是纯 Python（`build_karin.py`、`fit.py`、`vrm.py`、`atlas.py`、`decimate.py`、`gotfmt.py`、`gotarc.py`、`verify.py`、`render.py`），留在项目目录 `Karin_Original_GoT/tools/`。这里只记录方法、数值快照和被否决的假设。

格式知识部分参考了 Dave349234 的 "Ghost of Tsushima Toolkit for Blender"（MIT，要求署名），并在本 build 上重新核实过。来源见 [工具来源](../../references/TOOL_SOURCES.md)。
