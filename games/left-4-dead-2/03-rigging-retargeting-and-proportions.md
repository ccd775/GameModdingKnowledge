# 骨架映射、重定向与角色比例

本文记录把非 Source 角色制作成《Left 4 Dead 2》幸存者替换模型时，骨架、权重、比例动画与编译后审计的通用方法。重点是同时满足两件事：保留角色原始体态，并遵守游戏动画、武器、附件、IK、碰撞和 bonemerge 所依赖的接口。

文中严格区分两类结论：

- **通用规则**：可迁移到其他角色和幸存者槽位，但仍须以该槽位当前游戏文件和成熟参考模型复核。
- **Karin 实测值**：只对本项目锁定输入及当前构建成立，不应直接复制到其他角色。

## 1. 四层证据模型

### 通用规则

不要把“目标幸存者的原生骨架”当成唯一标准。可靠的角色替换至少有四层证据，各自回答不同问题：

| 层 | 权威内容 | 不应承担的内容 |
| --- | --- | --- |
| 原始角色源文件 | 网格、原始权重、形态键、角色部件关系 | L4D2 骨名、序列与附件契约 |
| 同角色成熟 Mod | 角色在 Source 中已经验证过的 rest skeleton、层级、比例、辅助骨和物理骨取舍 | 当前目标槽位所有原生接口细节 |
| 当前游戏原生模型 | 槽位路径、ValveBiped/附件/IK/hitbox/物理等接口；也可作为候选动画合同的证据之一 | 角色应该被改造成何种身材；不能仅由输出槽位决定主动画/include/sequence |
| 编译后二进制 | StudioMDL 最终保留了什么 | 作者期望保留什么 |

同角色成熟 Mod 应优先作为角色比例与 rest skeleton 的证据；当前原生模型作为游戏接口的证据。两者冲突时，通常应保留前者的骨骼位置和角色体态，通过 ValveBiped 名称、层级及 proportion delta 接入后者的动画，而不是把角色强行拉成原生幸存者的身材。

最终真值始终是编译后的 `.mdl/.vvd/.vtx`，不是 Blender 场景、SMD 或 QC。StudioMDL 可能裁骨、改变索引、生成 procedural bone 或重排 sequence；“编译成功”只说明语法可接受。

### Karin 实测

本项目采用三个不同来源，不把它们混为一谈：

- Karin 原始模型提供网格、原始权重和形态键。
- 已编译的同角色 Picodra Ellis 模型提供 **126 骨 rest skeleton、父子层级、61 个 jigglebone 配置和 6 个 QuatInterp helper**。
- 当前 Rochelle 资料提供幸存者槽位接口；Zoey 的动画模型和 rest translation 被用于最终的动画体态与 proportion trick。

输出路径仍是 Rochelle/Producer 槽位契约。使用 Zoey 动画基准不等于把输出槽位改成 Zoey；“槽位路径”“动画来源”“角色 rest skeleton”是三个独立决策。

Riptide Louis 再次证明这条规则跨槽位成立：输出为 Louis `survivor_manager`，但动漫比例与主动画仍使用 Zoey/TeenAngst。按 Louis 槽位回退到 Manager/Biker corrective 会压短腿链并造成额外屈膝/偏矮。完整解释见 [槽位、动画基准与 Zoey/TeenAngst](15-animation-basis-slot-and-zoey.md)。

## 2. 先冻结骨架映射，再移动网格

### 通用规则

骨架映射必须是可审计的数据表，不能只存在于 Blender 里的重命名结果。开始重定向前，至少记录：

- 源骨名、源父骨、是否被顶点使用、顶点数与权重和。
- 目标骨名、目标父骨、是否存在于同角色参考和当前原生模型。
- 动作类别：直接映射、生成中间骨、折叠到祖先、保留自定义骨、procedural helper、忽略非变形骨。
- 权重处理：直接转移、按网格拆分、合并到目标骨、截断后归一化。
- 映射置信度、证据来源和潜在变形风险。

映射顺序建议如下：

1. 盘点所有源骨，特别是所有有实际权重的骨。
2. 锁定同角色参考的目标骨名、顺序、父子层级和 rest transform。
3. 锁定目标槽位所需的 ValveBiped、weapon、attachment、IK、hitbox 和 bonemerge 接口。
4. 先映射 Pelvis、腿、脊柱、颈头、锁骨、手臂、手和手指等核心链。
5. 再映射头发、服装、尾巴等角色骨，并决定哪些链必须折叠。
6. 单独处理 QuatInterp、VRD、jigglebone 等 procedural helper，不把它们当普通装饰骨。
7. 检查每个有权重源骨都已有去向，再开始权重和网格变换。

不要仅靠字符串相似度自动映射。`Chest` 可能对应 `Spine4`，而 `Spine1/Spine2` 可能是目标骨架中保留的动画中间层；直接按名字或编号配对会破坏躯干链。

### 旋转、pivot 与骨轴是一份 bind 合同

骨名、index、parent 都正确，仍不表示骨架能正确驱动网格。每根 core bone 的 rotation basis 和 pivot translation 共同决定 child 的 parent-local transform；把参考/原生的 world rotation 与另一个 avatar 的 T-pose pivot 拼接，可能产生明显离轴的 Forearm、Hand 或腿链，即使静态 bind 看起来合理。

rotation 与 pivot 可以来自不同的、各自有证据的来源，但组合后必须把它当作新的 bind candidate 单独审计：

- 锁定每个来源、坐标换算和哈希，覆盖全部 core bone；
- 比较 target world rotation/pivot 与计划值，不能只比较骨名和 parent；
- 对主要链检查 child local translation 相对骨轴的横向分量、parent-to-child segment 以及带权几何到 pivot 的半径；
- 在完整代表动画中检查相对 bind 的肘/膝弯曲变化、末端 reach 和骨段长度漂移；
- 若运动学异常，再查权重/服装；不要先交换 L/R、全局平滑或放宽 edge 阈值。

这是一条通用策略门，不是要求所有项目复用某个成功参考的 rotation。案例与可量化反例见 [Karin Y -> Witch 双目标替换案例](19-karin-y-witch-case-study.md)。

不要把 Blender/VRM 的 `bone.matrix_local` 直接当成 ValveBiped world rotation。
Blender 常以骨 Y 轴描述长度方向，Source interface frame 的主轴和 roll 约定可能完全
不同；即使 pivot 正确，也会出现 Head roll、UpperArm 翻轴或 Hand twist。必须显式
完成 DCC-to-Source basis conversion，或锁定同 runtime slot、同动画族且已有运行证据的
Source custom frame。后者通常比临时用 parent-child 方向推导 swing/roll 更可复现，但
仍要重新验收新的 pivot+rotation 组合，不能把“参考成功”当自动豁免。

### ValveBiped 核心接口

常见语义映射如下，实际项目仍须以同角色参考和目标槽位为准：

| 源角色语义 | ValveBiped 目标 |
| --- | --- |
| Hips | `ValveBiped.Bip01_Pelvis` |
| UpperLeg / LowerLeg | `ValveBiped.Bip01_[L/R]_Thigh` / `_Calf` |
| Foot / Toes | `ValveBiped.Bip01_[L/R]_Foot` / `_Toe0` |
| Spine | `ValveBiped.Bip01_Spine` |
| 上胸 | 通常落到 `Spine1`、`Spine2`、`Spine4` 链中的证据指定节点 |
| Neck / Head | `ValveBiped.Bip01_Neck1` / `_Head1` |
| Shoulder / UpperArm / LowerArm / Hand | `_Clavicle` / `_UpperArm` / `_Forearm` / `_Hand` |
| 五指三节 | `_Finger0..4`、对应的 `01/02`、`11/12` 等后续节 |

ValveBiped 不只是“供动画旋转的骨”。骨名和层级还会被以下系统引用：

- `$bonemerge` 与第一人称/第三人称部件合并。
- 武器握持骨、弹匣骨和枪栓骨。
- `$attachment`、muzzle、眼睛、嘴、相机和物品挂点。
- `$ikchain`、`$ikautoplaylock` 和动画 IK rule。
- hitbox、ragdoll、collision joint。
- QuatInterp/VRD 等 procedural bone 的控制骨。

因此不能为了省骨位随意删除一个“看起来没有顶点权重”的 ValveBiped 骨。先确认它是否被 QC 或编译后二进制标记使用；确实省略时，必须同步改写所有引用，并用武器、附件和 IK 动作验证替代方案。

### Karin 实测

Karin 的映射表位于 `L4d2/Karin_PT_L4D2/reports/rig/karin-to-rochelle-bone-map.json`，关键盘点为：

| 项目 | 实测值 |
| --- | ---: |
| Karin 源骨 | 237 |
| 有权重源骨 | 233 |
| Picodra 目标骨 | 126 |
| 与原生共通的 ValveBiped 骨 | 58 |
| 角色附件骨 | 68 |
| 直接由源控制的目标骨 | 113 |
| 折叠处理的源控制 | 124 |
| 其中有权重的折叠源控制 | 121 |
| Source 128 骨上限下的余量 | 2 |

核心映射包括 `Hips -> Pelvis`、`Spine -> Spine`、`Chest -> Spine4`、`Neck -> Neck1`、`Head -> Head1`，以及左右腿、手臂和五指链的对应映射。`Spine1`、`Spine2` 等目标中间骨按 Picodra rest skeleton 保留，不能因 Karin 没有同名源骨而删除。

Karin 的左右 `Foot/Toes` 还存在按网格分配到原生脚骨和 Picodra helper 的特例，不能简化成一次全局重命名。

## 3. Character rest、target-fit 与 source-fit bind

### 通用规则

rest skeleton 决定角色的静态比例。对动漫或非写实角色，正确目标通常是“同角色成熟 Mod 已验证的 Source rest skeleton”，而不是原生幸存者的肩宽、头身比和腿长。

建立目标骨架时应完整复制：

- 骨名和骨索引约束。
- 父子层级。
- 每根骨的 parent-local translation 与 rotation。
- 自定义骨和 procedural helper 的 rest transform。
- 需要保留的 bonemerge、attachment、hitbox 和物理引用。

这里必须先选择 bind 策略，不能把一种项目路径写成通用强制规则。

**Target-fit mesh**：若目标 rest skeleton 已被同角色成熟参考证明适合当前几何，则网格从源 bind space 变换到目标 bind space。对源骨 `s`、其映射目标 `m(s)`、源全局 bind 矩阵 `B_s`、目标全局 bind 矩阵 `B_t`，线性蒙皮候选为：

```text
v_target = sum_s weight_s * B_t[m(s)] * inverse(B_s[s]) * v_source
```

多个源骨折叠到同一目标骨时，先用各自的源 bind 矩阵计算几何贡献，再把目标相同的权重合并并归一化。该公式仍只是候选：离散映射、helper 分支和宽服装可能让跨骨三角发生严重非刚性拉伸，必须用全拓扑 edge/triangle 门决定是否采用。

**Source-fit skeleton**：若目标 ABI 的名字、顺序、父级和接口方向可复用，但参考 pivot translation 不适合当前网格，则把目标 pivot 放到源 bone head；网格、Basis、shape key 和法线只做同一 global similarity，权重重映射后不再做逐骨 LBS rebake。此时“只换目标骨架不变换网格”是有意设计，因为骨架已经进入源 bind 空间；再套一次上述公式会重复改变体型。

source-fit 的几何门应把 global similarity 与逐骨 displacement 分开记录。完成统一尺度/
坐标变换后，每个导出角点相对同一 similarity baseline 的逐骨 bind displacement 应为零
或量化容差内；若大量角点再次被 `B_target * inverse(B_source)` 移动，说明同一几何被
重复处理。这个零位移门只约束采用 source-fit 的具体 runtime target；同一 Mod 的
第一人称 arms 等其他目标仍可独立选择 target-fit 并接受非零转换。

源模型没有的动画 helper 不应随意按 `1/3`、`2/3` 插入主链。应保留锁定接口的
parent-local offset，或按兼容参考的累计段长比例插值，并把零/近零段长作为显式合同
记录。看起来反常的 helper 拓扑若已有运行证据，不应为了“均匀”而擅自重排。

服装、袖子和附件 helper 的权重不能只按对象名或字符串前缀强塞到某一根 UpperArm/Spine。先保留 source-to-target lineage，沿 source parent chain 找到最近的有效 deform ancestor，再合并落到同一目标骨的权重，最后一次性 top-3/归一化。对肩、肘、腕等区域的重权重或平滑必须在 bind-space 的已审计局部范围内进行，并保留未参与修复的原有 influence；同时报告同侧性、对侧泄漏、腕区上下臂权重分布和局部样本覆盖。

激进减面同样要把肩-肘-腕、衣物折线和共权 seam 当作独立拓扑区域。只看总三角预算会把关节带简化成少量长边，随后任何合理动画都可能读成硬折。记录区域 before/after 的三角与唯一顶点覆盖，并与蒙皮门一同复查。

两条路线必须用核心骨的 weighted-centroid/pivot、seam 半径、全 edge/triangle stretch、左右 side sign 和极端姿态 CPU skin 比较。Cloth04 案例中，全 LBS 候选在多个身体/服装区域产生最高约 85 倍局部边拉伸，因此选择 source-fit + no-LBS；这个结果不能反推其他角色也必须 no-LBS。

需要区分四种操作：

- **刚体对齐**：整个角色的统一旋转、平移和尺度，只解决坐标系差异。
- **bind-space 重定向**：逐骨把源比例转换到目标 rest skeleton。
- **source-fit pivot**：保留目标 ABI，把目标旋转中心贴合实际源网格。
- **运行时 proportion delta**：让游戏动画从原生 rest translation 适配目标 rest translation。

这些操作不能互相替代，也不能重复应用。完整决策树和回归门见 [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md)。

### Karin 实测

Karin 最终 126 骨的 rest 层级和变换直接保持 Picodra 参考，不改造成原生 Rochelle 或 Zoey 身材。编译后与 Picodra 参考比较结果为：

| 指标 | 实测 | 本项目门槛 |
| --- | ---: | ---: |
| 共同骨 | 126 / 126 | 126 / 126 |
| 父骨不一致 | 0 | 0 |
| bone head RMSE | 0.0000056452 m | <= 0.0001 m |
| bone tail RMSE | 0.0025582207 m | <= 0.005 m |
| 最大端点误差 | 0.0287158857 m | <= 0.03 m |

最大端点误差来自 `ValveBiped.Bip01_R_Hand` 的 tail 表示差异；head 和父子层级仍通过门槛。这些阈值是 Karin 项目验收值，不是所有模型的通用容差。

### 第一人称手臂的独立 bind 合同

完整的选面、Basis、view-space placement、权重连续性、QC、HLMV、VPK 与实机流程见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。本节只保留骨架/bind 层的合同。

世界模型与第一人称手臂是两个独立编译目标。成熟的同角色手臂参考可以提供 **viewmodel ABI**：节点表、索引、父级、rest transform、`$definebone`、`$bonemerge`、`idle` 与手臂 proportion sequence；它不因此拥有最终可见网格。除非用户明确授权复用，可见皮肤、袖子、腕饰、UV 和材质必须来自用户源模型。

对 source-derived 手臂，先从已验收 world bind 中抽取源网格。逐 influence bind conversion 可作为理论候选；对 world 骨 `s` 及其 view 目标 `m(s)`：

```text
p_view = sum_s weight_s * B_view[m(s)] * inverse(B_world[s]) * p_world
```

法线使用对应线性部分并重新单位化。逐 influence 诊断候选在序列化前把映射到同一目标骨的权重合并，再截到最多三项并归一化；若后续还要做拓扑权重平滑，中间迭代不得反复 top-3，必须到最终写出前才统一裁剪。肩根处真实存在的 `Chest`/`Spine` 小权重不能误当附件权重删除；分别映射到 `ValveBiped.Bip01_Spine4` 和 `ValveBiped.Bip01_Spine`。但公式正确不等于离散骨映射一定连续：Karin 在 Basis 修复后仍有 17 个三角面因 VRD/helper 分支差异发生异常局部放大。因此还必须比较转换前后每条 triangle edge；出现局部非均匀 stretch 时拒绝该路径。

Karin 的最终保形路径是：用一个统一 similarity 将 source geometry 放入 view rest space，再转移同角色参考的最近唯一位置样本权重，沿源 topology 平滑，最后才裁 top 3。接受值为 scale `1.072`、offset `[0,1.43,0.14]` Source units；54,126 条 edge 的比率完全一致（最大误差 `4.2e-13`），局部非均匀 stretch 为 0。权重必须额外满足同坐标一致、左右骨串零泄漏，以及 triangle-corner L1 连续性接近参考；Karin smooth 候选最大 `0.973790`，参考最大 `0.950164`。uniform similarity 只证明静态三角保形，不证明武器动画中的蒙皮质量；仍需权重连续性门、多角度 HLMV 和游戏内武器动作 smoke test。

Karin 的 viewmodel ABI 锁定为参考的 55 节点、55 行 `$definebone`、49 行 `$bonemerge`，并保留左右 `Forearm_driven`、`Driven_ulna` 和 `thumbroot`。世界模型的 `VRD_L/R` 是 QuatInterp helper，不应塞进 55 骨 viewmodel。若输入已经只有 world `VRD` 权重且无法重新做表面转移，Karin 的兼容折叠为：

```text
VRD_L -> 0.410034 L_Forearm_driven + 0.589966 L_Driven_ulna
VRD_R -> 0.362251 R_Forearm_driven + 0.637749 R_Driven_ulna
```

这两个比例是项目实测后备值，不是通用常量。更可靠的方法是把同角色参考的前臂扭转权重在共同 rest space 中转移到源几何；参考只提供权重与 ABI，不能把它的三角面或材质带进输出。

Blender 还有一个容易漏掉的 Basis 合同：删除形态键前，必须先复制 `key_blocks["Basis"].data[].co`，执行 clear，再把保存坐标写回 `mesh.vertices[].co`。直接 `shape_key_clear()` 可能使基础网格回退到未重定向坐标，随后 bind 转换会得到整体偏移或错误比例。Karin 的黄金 world-SMD 抽取路径从已经验收、已烘焙的 world SMD 按 polygon manifest 精确取三角块；它与“先把变换后 Basis 烘回 mesh 再 clear”的最大位置误差为 `7.51e-6` Source units，可作为此故障的回归证据。

## 4. Source 单位与 Blender 尺度

### 通用规则

Source 人物模型使用 Source unit：

```text
1 Source unit = 1/16 foot = 0.75 inch = 1.905 cm = 0.01905 m
1 m = 52.49343832020997 Source units
```

SMD 骨骼 translation 和顶点坐标必须处于同一 Source 尺度。Blender/SourceIO 常以米显示导入结果，导出前必须明确工具是否自动换算，不能凭视窗大小猜测。

如果场景数据当前以米为真实数值，而导出器要求 Source unit，稳妥做法是：

1. 保持 Armature 和 Mesh 对象矩阵为 identity。
2. 对 `armature.data` 中的 rest bone 数据统一乘 `52.49343832020997`。
3. 对每个唯一 mesh data block 的基础网格和所有 shape key 坐标乘相同系数。
4. 重新导出所有 SMD，并重新生成依赖 rest translation 的 reference/proportion 动画。
5. 回读 SMD，检查 Pelvis、头、手、脚及网格包围盒的数量级。

只把 `armature.scale` 改大是典型错误：根骨可能看似合理，子骨 parent-local translation 仍保持米数量级，编译后就会出现躯干压缩、四肢错位或动画拉伸。只缩放基础网格而漏掉 shape key 也会让表情和服装形变跳回旧尺度。

### Karin 实测

Karin 的 bind/rest Pelvis Z 为 `38.591732` Source units；经 SourceIO 导入为 `0.73517251 m`，换算一致：

```text
38.591732 * 0.01905 = 0.7351724946 m
```

最终所有 10 个 SMD 的骨架和网格均使用 Source unit 数据，导出顶点最多 3 权重。

## 5. 每顶点最多三权重

### 通用规则

Source 这一代 Studio 模型格式对每顶点骨影响数的可靠上限是 3。导出前必须保证：

- 每个导出顶点最多 3 个非零影响。
- 权重非负，剔除近零项后重新归一化到 1。
- 不存在指向已删除骨、未映射骨或错误骨索引的权重。
- 镜像接缝、肩腋、髋部、裙摆根部和长发根部经过单独形变检查。

不要简单地对所有顶点“取前三名”后结束。正确顺序是先完成骨映射与折叠，把映射到同一目标骨的权重相加，再按目标骨影响截断并归一化。对于前三名与第四名权重接近的顶点，应记录截断误差并在极端姿势下检查。

建议至少输出以下审计：最大影响数、1/2/3 权重顶点直方图、被截断顶点数、丢弃权重最大值/总和、归一化误差和未解析骨名列表。

### Karin 实测

Karin 构建报告确认 `maximum_influences = 3`。同角色 Picodra 原始 VVD 的 LOD0 也只出现 1、2、3 权重，直方图为：

| 影响数 | Picodra LOD0 顶点数 |
| ---: | ---: |
| 1 | 25,575 |
| 2 | 16,999 |
| 3 | 6,332 |

## 6. autoplay delta proportion trick

### 通用规则

当目标角色需要保留自己的骨长和身体比例，但又要播放原生动画时，可用 corrective
与 target 两段动画生成平移比例差。所有数值均为 **parent-local transform**，不是
骨头世界坐标。frame count 必须来自当前 sequence contract：常见 survivor corrective/
target 各一帧，但已验证的 infected 合同也可能要求 target 把同一静态 pose 重复多帧。

定义：

- `T(b)`：目标角色的 rest transform，即 proportion target。
- `C(b)`：动画基准角色的 corrective transform。
- `g`：经测量得到的 Pelvis 地面修正，只有 Pelvis 的目标 Z 使用它。

对目标与动画基准共有的 ValveBiped 骨：

```text
T.position(b) = custom_rest.position(b)
T.rotation(b) = custom_rest.rotation(b)

C.position(b) = native_animation_rest.position(b)
C.rotation(b) = custom_rest.rotation(b)

T.position(Pelvis).z += g
```

对目标角色独有的附件骨：

```text
C(b) = T(b) = custom_rest(b)
```

然后让 StudioMDL 在 **frame 0** 执行：

```text
D = subtract(T, C[frame 0])
```

操作层面的平移校验式为：

```text
delta_position(b) = T.position(b) - C.position(b)
```

因为 `T.rotation == C.rotation`，编译后的旋转 delta 应为 identity。不要直接对 Euler 角做手算相减；让 StudioMDL 的 `subtract` 按动画格式生成 delta，并在二进制中验证旋转通道。

标准 QC 结构：

```qc
$animation "a_proportions_corrective_animation" "anims/custom_animation_reference.smd" {
    fps 30
}

$animation "a_proportions" "anims/custom_proportion_target.smd" {
    fps 30
    subtract "a_proportions_corrective_animation" 0
}

$sequence "proportions" {
    "a_proportions"
    autoplay
    delta
    hidden
}
```

两份 SMD 都应：

- 使用与编译模型完全相同的节点表和父子层级。
- 包含 sequence contract 要求的 frame；`subtract` 引用的 corrective frame 必须存在。
- 若 target 是多帧静态重复，每一帧都必须覆盖相同骨并在量化容差内保持同一 transform。
- 对每个必需 frame 的所有目标骨提供 transform，而不是只写 ValveBiped 子集。
- 在每次 rest skeleton、单位或 Pelvis 修正改变后重新生成。

运行时，隐藏的 `autoplay + delta` sequence 会把 `D` 叠加到 include 进来的原生动画上。它改变动画所依据的局部骨位移，不改变模型 bind skeleton，因此可以保留角色头身比、肩宽、腿长和附件骨位置。

这里的 `C` 必须来自**已经选定的主动画基准**，不能自动取 output slot 的原生 reference。对于本库默认的动漫角色 Zoey profile，`C.position` 来自 native TeenAngst parent-local translations。主动画 include 和 corrective baseline 必须成套；TeenAngst include + Manager corrective 或 Biker include + TeenAngst corrective 都属于混合合同。

优先从锁定的 compiled native animation MDL 解码 `C`，并记录其 SHA-256。Crowbar 反编译 SMD 可能带有版本、Euler 或量化差异，只能作为交叉证据。`T.position` 必须直接使用目标角色 parent-local rest；不要把它改写成 `normalize(C.position) * target_length`。动画基准与角色 rest 的骨轴方向不完全相同时，纯长度算法会把姿势差混入 translation delta，并沿 Clavicle、Hand 和 Finger 链累积成明显错位。

示例 QC 中的 `hidden + delta` 只是某类合同的写法，不是通用常量。另一个已验证 Louis-path 合同使用 `autoplay + predelta` 且不 hidden，编译 flags 为 12。必须按成功 sequence contract 保留顺序/flags，并从最终 MDL 复核，不能在项目之间照抄。

某些 infected/survivor 模型还有 `reference`、`CustomModel`、`ragdoll` 等本地序列源。
它们的名称不能推断内容，也不能因为都只有一帧就写成同一 projected pose。应从当前
原生模型、同目标成功参考和 compiled sequence 逐项确认：哪些序列使用 custom bind
rotation、哪些必须使用完整 native pose、哪些只服务 proportion corrective。发布前按
序列比较所有非 root core 的 position/rotation source；root 若因 StudioMDL animation
basis 被排除，必须明确记录原因和剩余覆盖数。

### Karin 实测

Karin 的生成文件和报告位于：

- `L4d2/Karin_PT_L4D2/build/modelsrc/karin_pt/world_zoey_proportion/anims/karin_zoey_reference.smd`
- `L4d2/Karin_PT_L4D2/build/modelsrc/karin_pt/world_zoey_proportion/anims/karin_proportion.smd`
- `L4d2/Karin_PT_L4D2/reports/build/karin-proportion-zoey-ground.json`

两份动画各有 126 个节点和一个 `time 0` 帧。58 个 Karin/Zoey 共通骨使用“Zoey local translation + Karin local rotation”作为 corrective frame；68 个 Karin 独有骨在两帧中相同。实测：

| 项目 | 值 |
| --- | ---: |
| 共通骨 | 58 |
| Karin 独有骨 | 68 |
| Pelvis 地面修正 `g` | +2.750011 Source units |
| `g` 的米值 | 0.05238770955 m |
| proportion target Pelvis Z | 41.341743 Source units |
| corrective Pelvis `(x,y,z)` | `(0, -1.441406, 35.343750)` |
| 编译前 Pelvis translation delta | `(0, 1.441406, 5.997993)` |
| 编译前 Head translation delta | `(-1.109414, 0.837336, 0.000003)` |

这里的 `41.341743 = 38.591732 + 2.750011`。`38.591732` 是不改动的 Karin bind/rest Pelvis Z；额外高度只存在于 proportion target 动画。

## 7. ground 与 Pelvis 校正

### 通用规则

脚陷地首先要区分三种原因：

1. 鞋或高跟形态键没有烘焙，网格鞋底本身就不在预期位置。
2. Source 单位或 bind-space 错误，腿长和脚骨位置已经失真。
3. 骨架和网格正确，但动画基准的地面高度与目标角色鞋底高度不同。

只有第 3 类问题适合用 Pelvis proportion offset 修正。测量时应在最终 bind 网格、最终鞋形和最终 rest skeleton 上求实际最低鞋底位置，并与动画预览中的地平面比较。修正值写入 proportion target 的 Pelvis local Z；通常脚陷地需要正值，悬空需要负值。

不要用以下手段代替：

- 整体抬高最终网格但不抬骨架。
- 单独移动 `Foot`/`Toe0` rest bone。
- 修改鞋子顶点来掩盖动画高度错误。
- 只调 `$bbox/$cbox`。
- 修改 bind Pelvis 后仍沿用旧 proportion SMD。

Pelvis delta 会一致抬升整条骨架、附件和动画；改脚骨会改变腿链与 IK，改网格会造成骨架/网格分离，改 bbox 则根本不改变渲染位置。

同一个自定义角色若覆盖多个 runtime variant，地面/根位移还需要跨目标合同：分别保留每个 variant 的原生 QC、collision/PHY 语义，但对设计为共享的可见 bind/proportion，比较 canonical reference、projected Pelvis、core/full projected reference 和 root delta。任一变体单独使用不同坐标系的 canonical position 或 rotation，都可能只让其中一个角色悬空；不要用 Foot、mesh、PHY、bbox 或 `$illumposition` 补偿这种 root-contract 错误。

### Karin 实测

Karin 在做地面校正前先烘焙 `Body.003` 的 `Foot_HighHeel = 1.0`。该形态键改变 1,886 个顶点，最大位移为 `0.0305431835 m`。高跟几何正确后，才使用 `+2.750011` Source units 的 Pelvis autoplay delta；bind skeleton、鞋网格、脚骨和包围盒保持不变。

## 8. sequence 与 include 保真

### 通用规则

幸存者模型的动画能力主要来自 `$includemodel` 和 sequence 契约。重建 QC 时必须从当前实际目标和成熟参考中提取，而不是凭记忆重写。

需要逐项保真：

- `$includemodel` 的路径、大小写和顺序。
- 所有 `$declaresequence` 行的原顺序。
- 有意存在的重复声明；不能擅自去重或排序。
- 本地 animation/sequence 的数量、名称和尾部顺序。
- `reference`、`proportions` 等 sequence 的 flags、animation index 和 frame count。
- IK chain、IK autoplay lock 和 sequence 内的 IK release rule。

sequence 索引可能被游戏代码、活动表或工具隐式依赖。即使名称都存在，改变声明顺序也可能把本地尾部 sequence 推到不同索引。因而验收应同时比较“名称集合”和“有序列表/索引”。

不要把 include 进来的数百个动画重新烘焙到自定义骨架。成熟流程是保留原生 include，通过 ValveBiped 接口和 autoplay proportion delta 适配角色比例。

对具有独立本地序列的 light 模型，source-fit 项目应同时保留两类报告：`strict reference equivalence` 逐骨量化与参考的绝对差异，只作诊断；`relative-to-bind motion contract` 检查原始 parent-local 动画、候选 proportion 对自身 bind 的重建以及相对各自 bind 的动作，是发布硬门。角色 bind 有意不同时，前者可以为 false、后者必须为 true。不能因为绝对 global pose 不同就交换 L/R 骨或动画。

### Karin 实测

Karin 的 include 顺序锁定为：

```qc
$includemodel "survivors/anim_teenangst.mdl"
$includemodel "survivors/gestures_TeenAngst.mdl"
$includemodel "survivors/anim_producer.mdl"
$includemodel "survivors/anim_gestures.mdl"
```

项目保留 928 行 `$declaresequence`，对应 924 个唯一名称和 4 个有意重复的声明：

- `AimMatrix_axe_Standing`
- `AimMatrix_Fry_Pan_Standing`
- `AimMatrix_bat_Standing`
- `NamVet_AimMatrix_Melee_Shove_Rifle_Standing`

编译后二进制契约为：

| 项目 | Karin 实测 |
| --- | ---: |
| 本地 animation | 5 |
| 本地 sequence 总数 | 932 |
| `reference` sequence | index 930，flags 1024，1 帧 |
| `proportions` sequence | index 931，flags 1052，1 帧 |

`1052` 对应 `HIDDEN | POST | AUTOPLAY | DELTA` 的组合；`reference` 保持隐藏。若数量、尾部索引、flags 或 include 顺序改变，即使模型能加载，也视为契约回归。

## 9. procedural helper 与 120/126 回归

### 通用规则

procedural bone 必须按编译后的类型和 payload 验收，不能只检查骨名。尤其要保存：

- helper 骨名和父骨。
- procedural 类型，例如 QuatInterp 或 JiggleRule。
- 控制骨名、trigger 数量和每个 trigger 的参数。
- `.vrd` 的精确内容及 QC 中 `$proceduralbones` 引用。
- helper 是否被顶点、附件或其他程序骨间接依赖。

若一个 helper 没有普通顶点权重，StudioMDL 仍可能因 VRD、attachment、bonemerge 或显式定义而保留；反之，源 SMD 中有节点并不保证编译后仍存在。必须解析 MDL 骨表和 procedural payload。

### Karin 实测

Karin 合格的 126 骨组成是：

```text
59 ordinary + 61 JiggleRule + 6 QuatInterp = 126
```

6 个 QuatInterp helper 必须全部存在：

| Helper | 控制骨 | Trigger 数 |
| --- | --- | ---: |
| `L_Foot` | `ValveBiped.Bip01_L_Foot` | 4 |
| `L_Toe0` | `ValveBiped.Bip01_L_Toe0` | 2 |
| `R_Foot` | `ValveBiped.Bip01_R_Foot` | 4 |
| `R_Toe0` | `ValveBiped.Bip01_R_Toe0` | 2 |
| `VRD_L` | `ValveBiped.Bip01_L_Hand` | 4 |
| `VRD_R` | `ValveBiped.Bip01_R_Hand` | 4 |

QC 必须引用 `karin_picodra.vrd`。若编译结果恰好变成 **120 骨**，通常不是“成功优化”，而是 6 个 QuatInterp helper 全部丢失：

```text
59 ordinary + 61 JiggleRule = 120
```

这会使脚/脚趾和前臂/手部在动画中失去参考模型的程序修正。120 骨构建即使能加载，也应直接判定为回归。

## 10. 编译后骨架与动画审计

### 通用规则

每次正式编译后，用独立解析器重新读取 MDL/VVD/VTX；不要只复用生成 QC 的内存数据。最低审计清单如下。

**骨架：**

- 总骨数、完整骨名列表和索引。
- 每根骨的父索引，所有预期骨是否存在。
- 与锁定同角色 reference 的 global rest head/tail 或矩阵误差。
- 核心 ValveBiped 链的逐骨误差，而不只看整体 RMSE。
- `USED_BY_BONE_MERGE`、vertex、attachment、hitbox 等 flags。
- ordinary/JiggleRule/QuatInterp 数量及 procedural payload。

**权重与网格：**

- VVD 最大影响数不超过 3。
- 权重引用的每个骨索引合法。
- 关键 helper 和自定义链是否仍有预期权重或程序引用。
- LOD 顶点数、fixup、材质分片和网格边界是否异常改变。

**动画与序列：**

- include model 的有序列表。
- local animation 和 sequence 数量。
- `$declaresequence` 的有序名称及重复项。
- `reference`/`proportions` 的索引、flags、帧数和 animation index。
- proportion rotation delta 是否为 identity，translation delta 是否与生成报告一致。

**视觉抽查：**

- 正面和侧面的 bind/reference pose。
- 站立、跑动、下蹲、倒地、攀爬、持枪、近战和双手武器。
- 头肩比例、脊柱长度、手腕扭转、膝肘弯曲、鞋底高度。
- 第一/第三人称武器、附件、hitbox、ragdoll 和 bonemerge。

将二进制结构审计与视觉审计分开记录。结构相同不保证皮肤权重正确，画面暂时正常也不保证 sequence 或 helper 没有丢失。

### Karin 实测

Karin 当前已接受的编译后结构检查为：

- 126/126 骨存在，0 个父骨不一致。
- 59 ordinary、61 JiggleRule、6 QuatInterp，15 种 jiggle profile。
- 58 个 bonemerge 骨。
- 10 个网格，58,213 个 SourceIO 导入顶点，88,512 个三角形。
- 5 个本地 animation、932 个本地 sequence。
- proportion 旋转编译为 identity delta。
- include 顺序和尾部 sequence 索引与第 8 节一致。

对应证据：

- `L4d2/Karin_PT_L4D2/reports/build/compiled-world-zoey-proportion-skeleton-comparison.json`
- `L4d2/Karin_PT_L4D2/reports/build/compiled-world-zoey-proportion-contract.json`
- `L4d2/Karin_PT_L4D2/reports/build/compiled-world-zoey-proportion-sourceio-audit.json`

## 11. 典型失败案例

### 缩头缩肩

**现象：** 头明显变小或下沉，肩宽收窄，颈部短，角色像被塞进原生幸存者体型。

**常见根因：**

- 把原生幸存者 rest translation 直接写进目标 bind skeleton。
- 用原生骨架绝对位置重绑网格，而不是保留同角色 rest skeleton。
- proportion corrective 与 target 的 rotation 不同，产生了不需要的旋转 delta。
- Chest/Spine4、Clavicle、Neck/Head 层级映射错误。
- 同时做了 bind-space 重定向和重复的绝对比例烘焙。

**修正：** 恢复同角色 reference 的 rest 层级和变换；仅通过 ValveBiped 接口继承动画；按当前 sequence contract 重生成 translation-only proportion delta，并审计 Head、Neck、Clavicle、Spine4 的 global head/tail。

### 腹部与上半身拉伸

**现象：** 腹部被纵向拉长，胸腔和骨盆间出现不自然空段，跑动或扭腰时更明显。

**常见根因：**

- `Spine`、`Spine1`、`Spine2`、`Spine4` 映射错层或父链不一致。
- 一部分骨使用世界坐标，另一部分使用 parent-local 坐标。
- 只缩放 Armature 对象，子骨 translation 仍是米数量级。
- 网格没有用源/目标 bind 矩阵转换，或 rest transform 被应用两次。
- 折叠脊柱/服装根骨后未先合并权重就截断到三权重。

**修正：** 对每层脊柱比较 parent-local translation、rotation 和 global endpoint；确认对象矩阵 identity、骨架与所有 shape key 同尺度；根据已冻结策略重建：target-fit 才使用 bind-space 公式，source-fit 则修 target pivot 并保持网格统一 similarity。两者都要检查全拓扑边长和躯干极端旋转。

### 脚陷地或悬空

**现象：** 鞋底穿过地面、脚踝压缩、左右鞋高度不同，或站立正常但动作中悬空。

**常见根因：**

- 高跟/鞋底形态键未烘焙。
- Source 单位错位或脚链 rest transform 被原生骨架覆盖。
- 用错误动画基准生成 corrective frame。
- Pelvis offset 写进 bind mesh、Foot/Toe 骨或 bbox，而非 proportion target。
- 比例 SMD 在 rest skeleton 或尺度变化后没有重建。

**修正：** 先确认最终鞋几何与脚链，再测地面差；仅在 target frame 的 Pelvis local Z 写入修正，重新执行 frame 0 subtraction；用站立、下蹲、跑动和 IK 锁脚动作验证。

### 额外屈膝且角色偏矮

**现象：** bind 模型外形正常、游戏也能加载，但角色比同类 Mod 矮，膝盖在所有站姿上比预期更弯。

**常见根因：** output slot 被误当成 animation basis；include 和 corrective 属于不同动作族；Calf/Foot/Toe 的 parent-local translations 被错误 subtract 压短。Foot IK 只能在已经缩短的腿链上求解，会进一步放大视觉异常。

**修正：** 分别核对 primary includes 与 corrective source/hash；比较 target、corrective 和 compiled delta 的 Thigh/Calf/Foot/Toe 局部链长；在 reference frame 检查 rest 腿链，在真实 idle 中另行接受动画作者设计的自然屈膝。不要用 Pelvis ground offset、Foot/Toe 或鞋网格去修腿链长度。

### 手臂像四段折断，静态 bind 或全局 edge 统计却正常

**现象：** 上臂、前臂、袖子或腕口在动作中像出现额外关节；截图可能看起来像 L/R 交换，但 bone name、parent、权重和全局 edge 分位数都没有明显错误。

**常见根因：**

- 将不相容的 world rotation 与 source pivot 组合，导致 child local translation 严重离骨轴；
- 只用 surface edge stretch 验收，遗漏关节弯曲、reach 与骨段长度；
- 袖子/helper 被按名称强制映射到上臂，真实前臂已经弯曲而衣物仍跟随上臂；
- 肩/肘/腕区域减面过度，或局部权重过渡出现硬断层。

**修正：** 先审计核心链的完整 bind basis、child local-axis、全帧 elbow bend delta、shoulder-hand reach 和 segment drift；再按 source ancestor 检查服装 lineage、同侧/对侧权重与局部拓扑。修复只能落在确认的 source-of-truth 层，随后重建 SMD、proportion、QC、companion、姿态审计和视觉证据。不要先交换 L/R、全局涂权重、把整片袖子锁到 UpperArm，或仅放宽 edge 阈值。

### 待机仍横向张臂，改 bind 后又出现歪头或下巴前伸

**现象：** 初始模型在 idle 中像保留 T Pose；一次“对齐原生骨轴”的修正后，静态或
compiled 关节轨迹可能更接近参考，但可见头部、头发、袖子被整体扭歪，手臂仍未达到
预期。

**常见根因是两个独立问题：**

- compiled proportion translation 不等于 target bind local position 减 animation
  baseline local position，Forearm/Hand 的源 T Pose 侧轴位移被永久叠加；
- 为迁就另一套 native rest rotation，对已经 source-fit 的 world mesh 又执行全身
  bind-space LBS prepose，inverse bind 在运行时把多权重几何扭坏；
- `reference`、`CustomModel`、`ragdoll` 等本地序列源被错误写成同一姿势；
- raw DCC bone frame 被误当 Source interface frame。

**修正：** 先分别审计 compiled proportion/sequence 职责和 world geometry bind
displacement。source-fit 候选应恢复锁定的 Source custom rotations、源 pivot 与零逐骨
网格 displacement；随后合成真实 include ANI 的 standing/crouching 帧，比较手腕相对
锁骨向量、Head quaternion 和 known-good/known-bad。不要继续单独旋 Head，也不要用
“child local Y/Z 必须为零”代替 target-native delta 合同。完整反例见
[Karin Nyako -> Hunter 案例](20-karin-nyako-hunter-case-study.md)。

### 120/126 helper 骨回归

**现象：** 模型能够编译和显示，但脚趾、脚腕、手腕或前臂的动态修正退化；骨数从 126 变成 120。

**根因：** `.vrd` 未引用、helper 名称/控制骨不匹配、生成 QC 漏掉 `$proceduralbones`，或只根据普通顶点权重裁骨，导致 6 个 QuatInterp helper 被 StudioMDL 删除。

**修正：** 恢复参考 `.vrd`、核对 6 个 helper 的控制骨和 trigger payload，重新编译并从 MDL 骨表验证 `59 + 61 + 6 = 126`。不要以 SMD 节点表存在作为通过条件。

## 12. 推荐验收门

### 通用规则

一个角色替换模型至少同时满足以下条件，才能进入实机测试：

1. 映射表覆盖全部有权重源骨，没有未解释的丢骨。
2. bind 策略已明确为 target-fit mesh 或 source-fit skeleton；目标 ABI、父链、pivot/端点与当前策略的锁定证据通过门槛。
3. 核心 ValveBiped、武器、附件、IK、hitbox 和 bonemerge 引用均能解析。
4. VVD 每顶点不超过 3 权重，权重已归一化且无非法骨索引。
5. Source 单位在骨、网格、shape key、physics 和动画之间一致。
6. proportion target/corrective frame count 与锁定 sequence contract 一致，subtract 引用帧存在；预期静态帧逐帧一致，旋转 delta 为 identity，Pelvis 修正只有一个所有者。
7. include 顺序、declaresequence 顺序与重复、sequence 索引和 flags 通过二进制审计。
8. procedural helper 的类型、控制骨和 payload 与参考一致。
9. 正面/侧面比例和关键动作视觉检查均无缩头缩肩、躯干拉伸、脚陷地或武器错位。
10. output slot、primary animation、corrective baseline、rest skeleton、sequence contract 与 ground owner 已分别记录；Zoey profile 不含 Manager/Biker corrective。
11. 核心 weighted-centroid/pivot、seam 半径、左右 side sign 和极端姿态几何门通过；已知坏候选在同一回归器中按预期失败。
12. light 的严格参考差异与 bind-relative 动画合同分开记录，不能用 global pose 差异推断 L/R swap。
13. core bind basis 的 rotation/pivot 来源、逐骨覆盖和 child local-axis 门已锁定；全帧关节弯曲、reach 与核心段长度门不能被全局 edge 统计替代。
14. 若同一角色有多个 runtime variant，共享可见 bind 的 canonical/Pelvis/core/full/root-delta equality 与每个 variant 独立的 QC/physics companion 合同均通过。
15. source-fit 目标的逐骨网格 displacement 相对统一 similarity baseline 为零；target-fit
    目标另行报告转换与 edge 门，不能在同一几何上重复两条路线。
16. 关键本地 pose sequence 的 pose source 职责与 compiled target-native proportion delta
    已逐骨验证；代表 idle 的手腕/头部运行时探针与正负对照方向一致。

### Karin 实测验收摘要

Karin 的当前结构基线是：126 骨、58 bonemerge、最多 3 权重、`+2.750011` Source unit Pelvis proportion offset、928 条 declaresequence、932 个本地 sequence，以及完整的 `59 ordinary + 61 JiggleRule + 6 QuatInterp`。任何后续构建若偏离这些数字，都应先解释差异并更新证据，不能仅以 StudioMDL 返回成功作为放行依据。
