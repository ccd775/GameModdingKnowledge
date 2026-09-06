# 从角色源模型制作第一人称手臂

本文是 L4D2 角色替换 Mod 第一人称手臂的权威流程。目标不是“让一个现成手臂模型改名后能加载”，而是同时满足三件事：可见几何确实来自用户源模型、骨架/动画符合目标 viewmodel 接口、最终 VPK 能在游戏中被实际挂载。

本文把可迁移规则与 Karin 项目实测值分开。标有“项目实测”的骨数、三角数、阈值、缩放、哈希和文件数不得复制到其他角色。

## 1. 先拆开六种来源职责

第一人称手臂不是世界模型的简单裁剪版，也不是参考 Mod 的二进制改名版。每个候选都应显式记录以下来源：

| 字段 | 应负责的内容 | 不应被推断出的内容 |
| --- | --- | --- |
| `visible_geometry_source` | 皮肤、手指、袖子、腕饰、拓扑、UV、法线 | viewmodel 骨架接口 |
| `geometry_selection_source` | 哪些源三角面进入手臂及其 polygon manifest | 编译后的动画兼容性 |
| `viewmodel_abi_source` | 节点表、父级、rest、definebone、bonemerge、idle/proportion | 最终可见网格血缘 |
| `slot_interface_source` | 目标文件路径、目标 survivor 接口、companion 组合 | 角色比例和作者材质 |
| `weight_guidance_source` | 前臂扭转、手腕和手指在 view rest 中的权重分布 | 源模型位置、UV、材质 |
| `material_source` | 允许的材质 token、VMT/VTF namespace | 可用哪个参考网格 |

推荐职责分工：

- 用户提供的 Blend/VRM 是可见几何与材质意图的唯一源头。
- 已验收世界模型构建提供已经烘焙的 Basis、单位、world bind、法线、UV、权重和三角顺序。
- 同角色成熟手臂参考可以提供 viewmodel ABI、比例动画和 rest-space 权重样本指导，但不自动拥有可见网格。
- 当前游戏的原生目标手臂提供目标路径和分支兼容性控制组。

只有用户明确授权复用参考可见资产时，参考网格才可以成为 `visible_geometry_source`。骨数相同、能被 StudioMDL 编译或能在 HLMV 加载，都不能替代血缘证明。

## 2. 阶段 A：锁定输入与目标接口

开始建模前保存：

- 用户源 Blend/VRM/贴图的路径、大小和 SHA-256；
- 已验收 world Blend、world SMD 和导出报告的哈希；
- 目标原生 arms 的 MDL/VVD/VTX 及解编译接口；
- 参考 arms 的 MDL/VVD/VTX、QC、SMD 和材质闭包；
- L4D2 build、StudioMDL、HLMV、VPK 工具路径和哈希；
- 正式目标路径，例如 Rochelle 的 `models/weapons/arms/v_arms_producer_new.*`。

原始输入保持只读。每次选面、坐标转换、权重转移、QC 生成和编译都写到新目录，并输出 JSON 报告。不要从“最新文件”或修改时间猜当前输入。

退出门槛：来源职责已分开；源和参考均有哈希；目标三件 companion 路径已经从当前游戏资源验证。

## 3. 阶段 B：在不可变源模型上选择可见三角面

### 3.1 优先使用语义，不按包围盒粗裁

稳健的选面信号包括：

- 手臂隐藏/显示 shape key 的非零顶点并集；
- 原始角色骨组的 Shoulder、UpperArm、LowerArm、Hand 和五指权重；
- 按共享完整 mesh edge 计算的 face connected component；
- 源材质槽和明确的服装/腕饰对象；
- 侧向、最小高度和平均臂权重，只作为组件级复核条件。

不要只按 X/Y/Z 长方体裁剪。宽袖、腕环、飘带和衣服主体常在空间上重叠；坐标裁剪很容易漏掉袖套，或把胸腹、裙摆和装饰线带入第一人称。

连通关系必须以“共享完整边”定义。只共享一个顶点的部件在 Blender 数据中可能互相接触，但不应因此被合成一个面区域。

### 3.2 选面结果必须成为 polygon-index manifest

manifest 至少记录：

```text
source Blend path + SHA-256
object name
vertex/edge/polygon counts
topology hash or ordered polygon-vertex contract
selection rule and parameters
sorted unique polygon indices
triangle count and material token
component-level bounds/weight statistics
```

权重阈值只能在锁定的原始骨组上计算。世界模型重绑定后，即使拓扑没变，权重分布也可能改变；在派生 Blend 上重新跑相同阈值会得到不同区域。正确流程是先在不可变源上生成 polygon indices，再证明派生对象的顶点、边、polygon 顺序和 topology hash 完全一致，最后复用 indices。

拓扑合同不一致时立即停止并重建 manifest。不得退回坐标近邻去猜 polygon 对应关系。

### 3.3 肩口与脱离腕饰

裁掉胸腹后，肩根通常会留下开口。这不是自动失败：成熟 view arms 本来也常保留相机外的上臂 stub。应在 HLMV 和游戏极限动作中检查它是否可见；若可见，只扩一圈切边或封闭切环，不要把整个躯干主体并入 viewmodel。

脱离式腕环、管线或袖口部件要按独立 edge component 保留。不要用某次审计产生的 component 序号作为长期 ID；应保存首面、面数、bounds、权重和 topology 签名。

最终正权重闭包还应设置语义硬排除。Karin 的 `Outer*` 属于腰/裙摆，`Code*` 属于耳机线，`Pocket_String*` 与 `Back_Ribbon*` 也不是手模附件；任一出现在最终 arms 正权重闭包中即失败。源臂链除 fingers 外没有必须新增到 view ABI 的自定义附件骨，脱离腕环/管件仍由标准 arm 加少量 Chest/Spine 权重驱动。

### 3.4 Karin 项目实测闭包

锁定源 Blend SHA-256：

```text
43B1A8DBE7990B9AB6547369B93C6EFE30777B4E714B266370AE1CF64F545C41
```

逐对象拓扑证据：

| 对象 | vertices/edges/polygons | topology SHA-256 | edge SHA-256 |
| --- | --- | --- | --- |
| `Body.001` | `12794/36680/24044` | `ABBF6BBFD3BC7C6C8B0F2381F8A72458B78439978452638629E29D8F391FFCEE` | `B7D87719D4EF010419AE1959889933D0F3CDEC6B7AC9F8830A0847F9A5182F26` |
| `Body.003` | `11895/35102/23228` | `BA977CBCF976301A9A85783162B7605B11F683416459BA4891A65B7E325C786E` | `6143EE66DDA813CC7713B960B33A3133121526E39A7EA4ACB6ED77155ADB4597` |
| `Body.006` | `10950/31390/20464` | `FF88B369A4F3ABFAED59FDF47B8950C1EABB0E408824B63DFBC6AAE8583C2B1B` | `8EDE6A5C56687A3D192B98473B09D426E632A8C19B096AB99FA55B5C659028EE` |

shape key 名称本身不是语义证据。七个 OFF key 虽在三个对象上同名存在，只有 `Body.003` 有实际 delta：

| key | 非零顶点 | 最小正 delta |
| --- | ---: | ---: |
| `Shoulder_OFF` | 332 | `0.0155216691` |
| `UpperArm_OFF` | 160 | `0.0207138371` |
| `Elbow_OFF` | 222 | `0.0188647344` |
| `LowerArm_OFF` | 160 | `0.0162176419` |
| `Wrist_OFF` | 128 | `0.0112709343` |
| `Hand_OFF` | 906 | `0.0050209208` |
| `Finger_OFF` | 3,106 | `0.0001368093` |

这些计数从 epsilon `0` 到 `1e-5` 均稳定；`Body.001` 与 `Body.006` 的同名七 key 全部为零。后续项目必须逐对象计算实际 delta，不能见到 `Hand_OFF` 名称就直接选面。

| 可见部分 | 源语义选择 | 结果 |
| --- | --- | ---: |
| `Body.003` / `Body` | 七个手臂 OFF shape key 的非零顶点并集，三角面三个顶点都必须命中 | 9,636 tris |
| `Body.006` / `ClothA_Blue` | 四个经 edge component、空间和臂权重共同确认的组件 | 2,064 tris |
| `Body.001` 主袖 | 在主体组件中按 19 个对应侧源骨权重中位数选面，再取最大 edge-connected 区域 | 左右各 2,213 tris |
| `Body.001` 脱离腕饰 | 排除主体后按 edge component、侧向、高度和平均臂权重复核 | 左右各 958 tris |

最终为 `Body=9636`、`ClothA_Blue=2064`、`ClothB_Blue=6342`，合计 18,042 tris。精确阈值和 polygon indices 保存在 `Karin_PT_L4D2/work/arms_from_source/source_selection_contract.json`；逐对象 counts/topology hash 由 `work/arms_from_source/arm_selection_subagent_audit.json` 另行证明。当前两份报告共同构成合同，未来构建器应把 topology 直接写入主 manifest。这些数字只对该源哈希有效。

## 4. 阶段 C：保存当前 Basis，优先从已验收 world SMD 抽取

### 4.1 Blender 的 Basis 清除陷阱

复制 mesh 后直接删除 shape keys，可能丢失派生 Blend 当前 `Basis` 中已经写入的比例/姿态变换。安全顺序是：

```text
snapshot key_blocks["Basis"].data[].co
  -> clear/remove shape keys
  -> write snapshot back to mesh.vertices[].co
  -> update mesh
  -> delete unselected faces
```

Karin 的失败候选正是先 clear keys、未写回 Basis。它保留了派生骨架和权重，却导出了旧坐标；随后正确的 bind 公式也会把错误输入放大成缩臂、错位和长刺。

### 4.2 已验收 world SMD 是更稳定的黄金输入

若 world SMD 的导出报告证明：

- 已应用最终 Basis、单位和 world bind；
- mesh 已三角化；
- SMD triangle 顺序等于 Blender polygon 顺序；
- 材质、法线、UV 和权重已通过世界模型验收；

则可直接按 manifest 的 polygon index，从 world SMD 原样复制每个 triangle block。这样 position、normal、UV、material、weight ID/value 和 SMD header 都来自同一个已验收 source-of-truth，避免临时裁剪 Blend 引入新的隐式状态。

SMD corner 行首的 bone ID 是旧格式 fallback/父骨字段，不是 Blender vertex 或 polygon index。只有导出阶段保存的顺序合同能把 polygon manifest 映射到 SMD。Karin 当时的 world export report 没有直接保存 polygon-to-triangle hash；最终可信度来自抽取报告对全部 54,126 corners 的 position/material/parent/UV/weight 回归和 exact copied-block 断言。未来 exporter 应直接输出 mapping/hash。

Karin 黄金抽取输出：

| 材质 | 三角面 | SHA-256 |
| --- | ---: | --- |
| `Body` | 9,636 | `B2CE0DB3C3828510FD6135BC773F07EC92347EECE5339D50E71BC1336A2C02DF` |
| `ClothA_Blue` | 2,064 | `98CD1360FE5A6AC406BE0DE8BB8C0BB26919FBC17F6FC74A9DAE7C3C0BAC4D8A` |
| `ClothB_Blue` | 6,342 | `1690ADE291D5FCBDD54087C8B21E0114696695DFF49340E5416A939833832402` |

报告 `reports/arms_hud/source-first-person-arms-world-smd-extract.json` 证明 position 最大误差不超过 `7.51e-6` Source units，材质、UV、weight bone ID 和 weight value 零不一致。

退出门槛：三角闭包等于 manifest；Basis 已明确烘焙；黄金抽取与 world SMD 的 triangle raw blocks 可逐项证明一致。

## 5. 阶段 D：把 world 几何放入 view rest space

### 5.1 逐 influence bind conversion 是候选，不是免检真理

在线性蒙皮假设下，将 world 骨 `s` 的 bind 顶点转到 view 骨 `m(s)` 可写为：

```text
p_view = sum_s w_s * B_view[m(s)] * inverse(B_world[s]) * p_world
```

法线使用对应逆转置线性部分并重新单位化；映射到同一目标骨的权重先合并，再裁到引擎支持的最大影响数并归一化。

公式本身可以正确，但离散的骨映射仍可能不连续。相邻顶点若分别落到 `VRD`、`Forearm_driven`、`Driven_ulna` 和 `Hand` 的不同空间分支，会在腕口产生长刺或拉片。Karin 的失败演进为：未烘 Basis 的 legacy 候选有 202 tris / 268 edges 超过 10 倍、最大 `44.7794x`；烘好 Basis/改用黄金 world 输入后，逐 influence 路径仍有 17 tris / 28 edges 超过 10 倍、最大 `26.5340x`；最终 uniform similarity 才把局部非均匀 stretch 降为 0。因此 Basis 修复和 helper 连续性是两个独立门。

### 5.2 必须测量三角边长

对每条源三角边 `e=(i,j)` 计算：

```text
r_e = length(p'_i - p'_j) / length(p_i - p_j)
```

全局 uniform similarity 允许所有 `r_e` 等于同一个缩放值；局部比率出现大幅离群则说明拓扑被非均匀拉伸。至少报告 min、median、p99、max，以及 `>2x`、`>5x`、`>10x` 计数。视觉上“最大的竖刺消失”不代表这个门已通过。

### 5.3 保形 similarity + 同角色最近点权重转移

当存在同角色成熟 view arms，可将职责进一步拆开：

1. 对 source-derived positions/normals 应用一个全局 uniform similarity，使它进入参考 view rest space；
2. 源 topology、UV、material 和法线血缘保持不变；
3. 只从参考 rest-space 点样本复制 view 骨权重；
4. 沿源 topology 邻接平滑权重；
5. 平滑完成后一次性裁为最多三影响并归一化。

Karin 正式 `transfer_reference_arm_weights.py` 的精确算法是：把参考 SMD corners 的 position 四舍五入到五位小数后去重；同位置重复 corner 的权重先平均/归一化；再对每个源 corner 以欧氏距离选择最近参考位置，并复制该点权重。它没有求最近三角面、没有 barycentric 插值，也没有材质/侧别约束。现有生成报告把它简称为 `nearest rest-space surface sample`，该标签不精确，应以脚本实现和本文为准。

`transfer_reference_arm_surface_weights.py` 才是最近参考三角形/barycentric 的实验分支；它不是最终候选来源。不要因为“surface”听起来更成熟就静默替换算法，必须比较 reference distance、左右泄漏、same-position 和 triangle-corner 连续性后重新晋升候选。

不要每轮平滑后都 top-3。提前剪枝会不断丢掉弱影响，制造新的硬边。nearest-point 权重未经连续性检查也不能成为最终权重；逐点硬转移常会在同一三角形内部跳变。

Karin 最终项目实测：

- global scale `1.072`，offset `[0, 1.43, 0.14]` Source units；
- 54,126 个 triangle-edge samples 的比率范围为 `1.071999999999585..1.072000000000341`；
- local nonuniform stretch 为 0；
- 最近点权重沿拓扑平滑 24 轮，self-weight `2.0`，最后一次 top-3；
- final SMD SHA-256 `68267B6DC9DDDABA625F82EF7F3971716A3F3150C027F85B44941EF8B5276C28`；
- 38 个实际加权骨，最多三影响；
- 同坐标权重不一致 0，左右骨串泄漏 0，跨中线三角 0；
- triangle-corner weight L1：p99 `0.647931`、p999 `0.783932`、max `0.973791`、`>1.0` 为 0。

`serialized_zero_weight_links=256` 是六位文本序列化产生的极小影响清洁度记录；StudioMDL 编译后的最多三影响合同仍通过。新脚本应在写 SMD 前删除量化后为零的 link，但不要把此非阻断项误判成几何撕裂。

这些 placement 与 smoothing 参数只属于 Karin。当前 `source-first-person-arms-similarity-bonefit.json` 锁定了结果和参考距离（median `0.3442`、p90 `1.4114`、p99 `3.8680`、max `6.7367` Source units），但没有记录 `1.072/[0,1.43,0.14]` 的拟合目标、搜索过程、骨/表面锚点或 residual 接受阈值。这是复现链的已知缺口：未来 placement 报告必须保存拟合方法、输入锚点、objective、搜索边界和阈值。edge 保形只能证明没有撕裂，不能单独证明位置正确。

## 6. 阶段 E：绑定 viewmodel ABI 与动画

世界模型和第一人称手臂是两个独立编译目标。不要因为目标是 Rochelle 就直接把原生 Rochelle 66 骨 rest 强加给动漫角色手臂；这会把手掌、手指、锁骨和前臂比例压回原生体型。

从成熟参考继承 ABI 时，应逐项锁定：

- SMD `nodes` 的名称、索引、父级和 frame 0 rest；
- QC `$definebone` 行数、顺序和数值；
- `$bonemerge` 行数和顺序；
- viewmodel 真正使用的 forearm helper 与 `thumbroot`；
- `idle` 和 proportion 动画的 SMD、flags 与绝对/delta 语义；
- bbox、illumposition、surfaceprop、contents 和 cdmaterials；
- 正式 modelname 与唯一 preview alias。

Karin ABI 参考 SMD SHA-256 为 `C662E12C33B047CF9AAD1B24E235A1E8CBCA3A87A87065C6C2C50C38A24F6ED8`。关键 helper 身份如下，均以对应侧 `Forearm` 为 parent：

| side | `thumbroot` index | `Driven_ulna` index / local X | `Forearm_driven` index / local X |
| --- | ---: | --- | --- |
| L | 25 | `26 / 6.868280` | `27 / 3.358414` |
| R | 47 | `48 / 6.694323` | `49 / 3.201679` |

Karin 使用参考的 55 节点、55 行 definebone、49 行 bonemerge，并保留左右 `Forearm_driven`、`Driven_ulna` 和 `thumbroot`。最终 gate 要求节点索引/名称/父级/rest 与锁定参考一致，55 definebone 与 49 bonemerge 逐行一致；compiled sequence 只有 `idle` 与 `arml_proportions`，flags 分别为 `0` 与 `1289`。`arml_proportions` 是隐藏、实时、循环、autoplay 的绝对动画，不能套用世界模型的 delta proportion 配方。

world 的 `VRD_L/R` 不属于该 55 骨 ABI。优先通过同角色最近点权重转移和拓扑平滑恢复 forearm helper 分布；只有无法重做时，才使用项目有证据的折叠比例。Karin 后备比例为：

```text
VRD_L -> 0.410034 L_Forearm_driven + 0.589966 L_Driven_ulna
VRD_R -> 0.362251 R_Forearm_driven + 0.637749 R_Driven_ulna
```

它们不是通用常量。

退出门槛：可见 SMD 与参考 SMD 哈希不同；节点/rest/QC/sequence 接口按合同一致；world-only helper 不进入 view ABI；最多三影响且无缺失骨。

## 7. 阶段 F：材质血缘与负面门

第一人称材质应复用本项目 atlas 或进入本项目专有 namespace。禁止为了省事把参考手臂的 VMT/VTF 闭包一起打包。

Karin 正面允许：

```text
Body
ClothA_Blue
ClothB_Blue
models/survivors/karin_pt/
```

Karin 旧参考 arms 的三件二进制必须作为负面哈希：

| companion | 必须拒绝的 SHA-256 |
| --- | --- |
| MDL | `DFBAD4CE20FE13356375BC3034BAABB4574119D05CE6DBB5E759100FE5C892A1` |
| VVD | `4D7757362316C334A85F57E9E0E9A4A694C46C9A2183710F825C863ED74E9864` |
| DX90.VTX | `D4C0634282C57ACCB847F47AEB1915DFBE1C81E6018BC9FB9E3CDD73D9C5717F` |

同时拒绝：

- MDL 中的 `mechanic`、`ko_komado_pt`、`clotha_pink`、`clothb_pink`；
- release tree 中任何 `materials/ko_komado_pt/**`；
- 参考 Mod 的旧五材质 token；
- 与参考 VVD/VTX byte-identical 的 companion。

哈希门、字符串门和路径集合门必须同时存在。只扫 token 会漏掉无字符串的 VVD/VTX，只比哈希会漏掉被轻微重编但仍携带旧材质的候选。

## 8. 阶段 G：QC、StudioMDL 与 compiled 合同

QC 生成器可从 ABI 参考复制经过审计的接口行，但必须重写：

- `$modelname` 为目标正式路径；
- `$bodygroup "arms" { studio "arms.smd" }` 为 source-derived SMD；
- `$cdmaterials` 为本项目 namespace；
- preview 版仅改变 `$modelname`，其他输入与正式 QC 同源。

每次 StudioMDL 编译后审计：

- return code、warning/error 分类；
- MDL/VVD/VTX 版本和共享 checksum；
- compiled bone/material/sequence 数；
- 每顶点最大影响；
- 正式 companion SHA-256；
- QC 输入哈希和工具哈希。

Karin 正式 compiled arms：

| 文件 | bytes | SHA-256 |
| --- | ---: | --- |
| `v_arms_producer_new.mdl` | 26,492 | `8CA326BB03910BB919E489BFEE3B49161058DA3F6DDDEAEDD918F2DD34F3D65F` |
| `v_arms_producer_new.vvd` | 743,744 | `9BBA6B0E747B6FD277B9981747EA62F2B6461EA9C2CDCB9368843B060D1CF2BD` |
| `v_arms_producer_new.dx90.vtx` | 213,631 | `5F10FD88D66BB20BB05F73EB612FE6A1E509D602D78748B72D3B9C0B806E7D2C` |

三件共享 checksum 字节为 `BF4A8254`。SourceIO 回读为 55 bones、11,620 compiled vertices、18,042 tris、三个项目材质、最多三影响。独立只读二进制核对还确认 49 个 compiled bones 带 `0x40000 BONE_USED_BY_BONE_MERGE`，两个 sequence flags 为 `0` 与 `1289`，两个 animation 都是一帧。

当前项目尚缺一份把 compiled 节点顺序/父级/rest、49 个 merge flags、sequence/animation 数和 flags 汇总到一起的机器可读 `compiled-view-arms-abi-contract.json`。QC JSON 的 55/49 计数与 SourceIO 的 55 bones 不能替代这个门；后续项目应增加专用 MDL 解析器并让 release manifest 链接其 path+hash。

## 9. 阶段 H：HLMV 必须证明加载对象和关键视角

正式路径可能被游戏 VFS 解析成原版或另一个 addon。为预览编译唯一 alias，并从隔离 game root 加载；alias QC 除 `$modelname` 外必须与正式 QC 同源。

至少保存：

- 正面整体；
- 斜侧面；
- 左右腕口；
- 掌心和手指；
- 肩口 cut/stub；
- 宽袖和脱离腕饰；
- 可用时的 idle/proportion sequence。

单张正面图不能证明没有漏袖、腕环重叠、掌心破面或参考几何混入。截图应保留窗口标题/模型路径；必要时附 alias QC 与正式 QC 的输入哈希差异证明。

Karin 最终预览证据：

```text
reports/ui/hlmv-source-arms-final-smooth-front.png
reports/ui/hlmv-source-arms-final-smooth-angle.png
```

这两张只覆盖 front/angle，可证明唯一 alias 静态加载且没有明显长刺；它们没有完整覆盖左右腕口、掌心/手指、肩口 cut、背面和 proportion sequence，因此 Karin 的完整 HLMV 视角矩阵仍是证据缺口。HLMV 静态通过也不等于所有武器动作通过。

## 10. 阶段 I：原子组装、VPK 与运行时挂载

arms 的 MDL/VVD/VTX 必须作为同一轮 companion 原子替换。以已接受的上一版 loose tree 为基线时，只允许 manifest 声明的路径变化；旧参考材质目录必须整体删除，其他 world/HUD/material 文件保持哈希不变。

Karin final release closure：

- 33 files；
- 44,029,711 payload bytes；
- VPK 44,031,174 bytes；
- VPK SHA-256 `D59B4B001AC2B63BF1E61A0E136BC8E6E9326DAE5AC99B8A30CE05FD270AA0CA`；
- 正式运行名 `KarinPT_Rochelle_SourceArms.vpk`。

文件数和字节数只是该候选的项目实测门，不是 L4D2 arms 的固定标准。

`vpk.exe l` 和 33/33 payload 校验只能证明归档结构，不证明本次游戏会话已经挂载。发布名使用唯一、短 ASCII stem，保守建议不超过 32 字符；完整退出游戏后安装，移走旧长名/同路径覆盖包，再完整启动。

运行时用以下命令取证：

```text
show_addon_load_order
show_addon_metadata
```

Add-ons 菜单复选框、磁盘文件存在和 `addonlist.txt` 静态内容都不是最终挂载证明。

Karin 曾出现“离线 VPK 完全正确，但游戏显示原版 Rochelle”。修复没有重编 payload，而是改用唯一短名、移走旧副本、在游戏关闭时预先启用并完整重启。用户在 2026-08-14 确认该候选已经生效。因为多项挂载变量同时修复，没有该故障会话的引擎 load-order 日志，所以不能把长文件名单独写成已证实唯一根因。

## 11. 实机测试顺序

先把“是否挂载”和“动画是否正确”分开：

1. 角色替换是否出现，第一人称是否不再回到原版；
2. 常用长枪、手枪/双枪、近战；
3. idle、瞄准、射击、换弹、推击；
4. 医疗包、药瓶、针、投掷物和携带物；
5. 倒地、受伤及其他特殊 viewmodel 状态；
6. 左右腕口、掌心、手指、肩口、袖子、腕饰与武器的穿插；
7. 不同 FOV/分辨率下的构图。

每个结果记录候选 SHA-256、地图、武器、动作、FOV、截图/录像和其他启用 addon。用户说“已经生效”只能升级挂载与替换状态；除非证据明确覆盖，不自动升级为“所有武器动作和极限裁口已通过”。

## 12. 反面案例与根因索引

| 反面方案/现象 | 为什么失败 | 正确门槛 |
| --- | --- | --- |
| 参考 MDL 内 `mechanic -> producer` 定长替换，VVD/VTX 原样搬运 | 只改变目标 token，可见网格和材质仍来自参考 Mod | 源 polygon manifest、world-SMD 血缘、旧哈希/namespace 负面门 |
| 按坐标框裁手臂 | 漏宽袖/腕饰，或带入胸腹/裙摆 | shape key、源骨权重、完整 edge component |
| 在派生 Valve 权重上重算源阈值 | 重绑定改变分数，选面数量漂移 | 源哈希上生成 indices，拓扑相同时映射 |
| clear shape keys 前未写回 Basis | 导出旧坐标，骨架/权重与网格不在同一空间 | snapshot Basis -> clear -> write back，或黄金 world-SMD 抽取 |
| 逐 influence 公式数值正确便直接发布 | helper/VRD 映射在相邻顶点间不连续 | triangle-edge ratio 和 HLMV 腕口门 |
| 最近参考点权重逐点硬赋值 | 三角内部权重跳变，动作时撕裂 | topology smoothing、same-position、wrong-side、corner L1 |
| 每轮平滑都 top-3 | 弱影响反复丢失，形成硬边 | 保留完整权重迭代，最后一次 top-3 |
| 用原生 Rochelle rest 代替同角色 view ABI | 动漫手掌/手指/前臂比例被压回原生体型 | 分离 slot source 与 rest/ABI source |
| 保留参考 `ko_komado_pt` 材质 | 可见外观和血缘仍属于参考包 | 只允许项目 atlas namespace，actual paths == manifest |
| HLMV 打开正式同名路径 | 可能加载原版或其他 addon | 唯一 alias + 隔离 game root + 标题证据 |
| VPK payload 通过便认定游戏已加载 | 归档正确与运行时挂载是不同层 | load order/metadata、唯一短名、完整重启 |

## 13. 最小报告集合

一个可交接的 source-derived arms 构建至少保存：

```text
source-lock.json
source-arm-selection-manifest.json
world-smd-extraction-report.json
view-space-placement-report.json
weight-transfer-and-continuity-report.json
arms-qc-contract.json
studiomdl-run.json
compiled-arms-contract.json
hlmv-screenshot-manifest.json
loose-tree-manifest.json
vpk-payload-validation.json
runtime-test-report.md
```

报告应允许后续 agent 回答四个问题：看见的三角面从哪里来、为什么这套 55/其他骨接口能驱动它、编译输出是否仍是本项目材质、游戏本次会话是否真的挂载了它。

## 14. Karin 证据地图

核心脚本和报告：

```text
src/scripts/build_source_arm_selection_manifest.py
src/scripts/audit_first_person_arm_components.py
src/scripts/extract_source_first_person_arms_from_world_smd.py
src/scripts/build_view_arms_rigid_alignment_smd.py
src/scripts/transfer_reference_arm_weights.py
src/scripts/transfer_reference_arm_surface_weights.py
src/scripts/smooth_transferred_arm_weights.py
src/scripts/audit_first_person_arms_surface_candidate.py
src/scripts/generate_source_first_person_arms_qc.py
src/scripts/assemble_source_arms_release.py
src/scripts/validate_vpk_tree.py
src/scripts/repair_runtime_mount_name.ps1

work/arms_from_source/source_selection_contract.json  # SHA-256 D09E6A965DE9F39919E04539A787D559F22EDEF863DDB4BBCB491D972D848069
work/arms_from_source/arm_selection_subagent_audit.json
reports/arms_hud/source-first-person-arms-world-smd-extract.json
reports/arms_hud/source-first-person-arms-similarity-bonefit.json
reports/arms_hud/source-first-person-arms-similarity-bonefit-reference-weight-transfer.json
reports/arms_hud/source-first-person-arms-similarity-reference-weight-smoothing-unpruned24.json
reports/arms_hud/source-first-person-arms-qc-similarity-reference-weights-smooth-final.json
reports/arms_hud/source-first-person-arms-similarity-reference-weights-smooth-final-sourceio-audit.json
reports/compile/source-first-person-arms-similarity-reference-weights-smooth-final-studiomdl.json
reports/ui/hlmv-source-arms-final-smooth-front.png
reports/ui/hlmv-source-arms-final-smooth-angle.png
reports/release/loose-tree-zoey-bile-selfillum-source-arms-smooth-final.json
reports/release/vpk-validation-source-arms-short-name.json
reports/runtime/source-arms-short-name-mount-repair.json
```

当前 selection/topology 证据仍有两份文件位于 `work/`，这是归档技术债。后续正式构建应把合并后的 source-arm selection contract 提升到 `reports/`，由 release manifest 记录 path+hash，避免清理工作目录时丢失证据。

用户实机证据见 [Karin source-derived 第一人称手臂运行确认](evidence/karin-source-arms-runtime-confirmation-2026-08-14.md)。

相关专项文档：

- [骨架、绑定与角色比例](03-rigging-retargeting-and-proportions.md)
- [QC、编译与模型预览](07-qc-compile-and-hlmv.md)
- [第一人称手臂、HUD、打包与发布](08-arms-hud-packaging-release.md)
- [排障手册](09-debugging-playbook.md)
- [自动化脚本目录](12-automation-script-catalog.md)
