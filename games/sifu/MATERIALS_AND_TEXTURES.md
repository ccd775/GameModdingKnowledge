# 材质与贴图

## 1. 父级用 W 的材质实例

- 替换模型的每个槽是一个 MIC，父级是 W 默认服装的材质实例（不是母材质）：
  脸 → `MI_MainChar_W_Head_Dyn`，皮肤 → `MI_MainChar_W_20_Body`，衣服 / 头发 → `MI_MainChar_W_BasicOutfit`（Cloth_Dyn 母材质，带 `bUsedWithClothing`，NvCloth 段也能用）。
- 这样继承了 W 的静态开关（如 IsMainChar、ClothAging 关），游戏里走的就是 W 已经编译好的着色器排列；MIC 本身不带静态参数覆盖，
  pak 里没有着色器。
- 编辑器里这三个材质实例和母材质只是游戏路径上的**占位**（参数名对上即可），cook 后按路径引用游戏原件，不进 pak。
- 旧的社区 mod 用 `M_CharaMaster_Cloth` 一个母材质配两个材质、4096 图集；本项目不用这种做法。

## 2. 覆盖的参数

| 参数 | 值 |
| --- | --- |
| `BaseColor` | 源贴图（或图集页）缩到 2048。alpha：脸 / 皮肤 255，衣服 / 头发 0（同 W） |
| `ComboMap` | R 粗糙度、G 金属度、B 烘焙 AO、A 遮罩（见 §3） |
| `Normal` | 平法线 `T_Karin_Flat_N`（RGB 128,128,255）；源模型没有可用的切线空间法线 |
| `Color_Old` | = BaseColor（中和变老） |
| `Aging_Mask` | 全黑 `T_Karin_Black` |
| `Aging_Normal_A` / `Aging_Normal_B` | 平法线 |
| `SSS_Color` | 脸 (0.198, 0.0247, 0.0247)，皮肤 (0.114, 0.0009, 0.0044) |
| `Hair_Dark` / `Hair_Light`（脸） | 黑 / 白 |
| `Camera Dist Falloff` | 70 |

游戏里主角会随死亡次数变老，变老是材质参数（`Color_Old`、`Aging_Mask`、`Aging_Normal_*`）做的；替换模型把它们中和掉，不跟着变老。

## 3. ComboMap 常量

| 类别 | R 粗糙度 | G | B AO 强度 | A |
| --- | --- | --- | --- | --- |
| 脸 | 140 | 0 | 0.6 | 230 |
| 皮肤 | 150 | 0 | 0.8 | 230 |
| 头发 | 115 | 0 | 0.9 | 255 |
| 衣服 | 205 | 0 | 1.0 | 255 |

B 通道 = 1 − 强度 × (1 − AO)，再取 0.8 次方。A 的含义按 W 的贴图取值（皮肤 230、衣服 255），未单独验证每个值的作用。

## 4. AO 与图集

- 源模型（VRChat 着色器）的 ORM 图是常数（AO 1、粗糙度 1、金属 0），发射图是白色发光遮罩，都不能用。
  AO 从构建后的网格在 Blender 里烘焙（`bake_ao.py`）：Karin_Original 按槽烘，图集模型按图集页烘（`AO_<page>.png`，线性灰度）。
  烘焙时给没有节点的占位材质打开 `use_nodes`，否则 bake 报 `'NoneType' object has no attribute 'nodes'`。
- 图集模型的每个槽对应一页图集；同一页被脸和皮肤共用时（Karin_Y），用 `mesh_materials` 按网格把同一个源材质分到不同槽。

## 5. 顶点色

W 的顶点色是材质遮罩。构建时按部位类别（脸、皮肤、头发、衣服）从 W 网格复制到替换模型上；NvCloth 代理的顶点色另作他用
（R 最大距离、G / B backstop，见 [物理](PHYSICS.md) §4），代理段在 UE 里构建布料后删除。

## 6. 证据

- 「测试 1–4 整个人发暗、看不出贴图」的原因是所有槽的材质都是 `null`（UE Python 结构体副本，[排障手册](TROUBLESHOOTING.md) §1）；
  修复后用 A/B 构建（游戏贴图对照红色双马尾）在实机确认贴图生效，最终构建的白发、黑丝带、红色点缀、服装刺绣在实机可见。
- 修复后的第一次实机（测试 5）仍偏暗，之后没有复现，原因未查明。
- 正面强光下的整体亮度、真正的法线贴图都还没做。
