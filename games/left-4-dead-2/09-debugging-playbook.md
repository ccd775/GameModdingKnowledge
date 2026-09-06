# 排障手册

先从现象定位到最小数据层，再修改 source-of-truth。不要在最终 VPK 中盲改，也不要用一次全量重建掩盖根因。

爆指、假性左右互换、source-fit 和发根拉丝的跨层决策树见 [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md)。

## 1. 快速分层

| 层 | 典型证据 | 先查什么 |
| --- | --- | --- |
| 源模型 | Blend/VRM 审计 | 单位、shape key、骨架、权重、材质连接 |
| 导出 | SMD/VTA | 骨变换、顶点、权重、材质名、frame 0 |
| QC/编译 | StudioMDL log、MDL/VVD/VTX/PHY | warning、骨裁剪、序列、checksum、include |
| 材质 | VMT/VTF 解码 | patch、纹理闭包、flags、mip、shader pass |
| 打包 | loose tree/VPK payload | missing、extra、哈希、陈旧文件 |
| 运行 | HLMV/游戏截图录像 | 实际加载对象、动作、光照、bile、物理 |

如果 loose tree 就错，不必先调查 VPK；如果 HLMV 唯一 alias 正确而游戏错，再查目标路径、挂载优先级和冲突 addon。

### 现象：Add-ons 菜单显示启用，但游戏完全回到原版角色

先把它当作“VPK 未进入本次运行时搜索路径”，不要重做模型：

1. 用 Valve `vpk.exe` 确认根路径没有多一层目录，并逐 payload 对比 accepted loose tree。
2. 检查目标 world MDL/VVD/VTX/PHY 是否齐全；与上一个已生效候选逐字节比较。若完全相同，arms 或材质变化不可能使世界模型单独回到原版。
3. 结构化扫描所有已启用 VPK 的同一目标路径，并核对 `addonlist.txt` 中实际状态与优先级；不要只按文件名猜冲突。
4. 检查运行时 VPK 名称。使用短 ASCII stem，建议不超过 32 字符；`vpk.exe` 能读取长名不能证明游戏 Addons 管理代码不会截断它。
5. 游戏完全退出后，备份 `addonlist.txt`，移走旧/长名副本，把同一 VPK 以唯一短名放入 `addons` 并置为第一个启用项，再完整重启。
6. 在故障会话执行 `show_addon_load_order` 和 `show_addon_metadata`。只有这两项能证明引擎实际挂载；菜单复选框和磁盘文件存在都不够。

Karin SourceArms 曾使用 66 字符文件名，离线 33/33 payload 校验和世界模型闭包均正确，但用户看到原版 Rochelle。修复采用 31 字符短名 `KarinPT_Rochelle_SourceArms.vpk`，不重编任何 payload，SHA-256 保持不变；用户已在 2026-08-14 确认组合修复后 Mod 生效。该案例同时改变了 enabled 状态、旧副本、优先级与重启时序，因此知识库只把“短名 + 唯一副本 + 预启用 + 完整重启”记录为已确认有效，把长名缓冲记录为兼容风险，不在缺少故障会话 load-order 日志时声称唯一根因。详见 [运行确认](evidence/karin-source-arms-runtime-confirmation-2026-08-14.md)。

## 2. 体态、比例和落地

### 现象：缩头缩肩、上半身/腹部拉伸

高概率原因：把自定义网格或完整 skeleton 强行对齐到原版 survivor 身体比例，只保留了动画接口，没有保留角色 rest pose。

处理：

1. 比较源角色、同角色成熟参考、当前 SMD 和编译 MDL 的骨端点。
2. 检查是否把 native local translations 写入了最终 bind skeleton。
3. 恢复角色 rest skeleton。
4. 用该项目锁定 flags 的 autoplay proportion delta 连接所选动画基准，不拉伸网格去配 survivor。
5. 重查 include model 顺序和 proportion sequence flags。

### 现象：脚陷地或悬空

高概率原因：proportion target 的 pelvis 地面基准错误；也可能是单位或 source/reference SMD 不一致。

处理：

1. 测量鞋底最低点和目标地面，不凭截图随意估值。
2. 只在 proportion target 中调整 pelvis 平移。
3. 保持鞋、脚骨、网格、IK、bbox 和 ragdoll 不做独立补偿。
4. 在 bind、idle、walk、run、crouch 都检查。

### 现象：脚从鞋中露出

高概率原因：高跟鞋或鞋型 shape key 没有真正烘焙到 Basis。

处理：审计每个同名 key 的非零 delta，将有效 key 烘焙到 Basis 和所有保留相对 key，删除已烘焙 key，再导出。

### 现象：角色明显偏矮并额外屈膝，但鞋底大致接地

高概率原因：把 output slot 错当成 animation basis，或 primary include 与 corrective translation 来源不一致。错误 subtract 会压短 Calf/Foot/Toe parent-local 链；Foot IK 只能在已经缩短的腿上求解，因此看起来又矮又弯。

处理：

1. 分别核对 output slot、primary animation、corrective source/hash、rest skeleton 和 sequence contract，不从 `survivor_manager` 等路径推断动作族。
2. 对比 target、corrective 与编译 delta 中 Thigh/Calf/Foot/Toe 的 parent-local translations 和链长。
3. 在一帧 reference/rest pose 中检查腿链是否接近目标 rest；再把真实 idle 的 authored pose 单独评估。
4. Zoey/TeenAngst idle 本身可以自然屈膝并带 foot IK；目标是消除额外链缩短，不是强迫所有动画达到 180 度。
5. 不要用 Pelvis ground offset 修身高/腿长，也不要移动 Foot/Toe 或鞋网格。接地与 corrective 链长是两个问题。

Riptide 的 Manager/Biker 混合基准使角色顶部少约 8.04 Source units；改用匹配的 TeenAngst corrective 后恢复。详见 [Zoey 动画基准](15-animation-basis-slot-and-zoey.md)和 [Riptide 案例](16-riptide-louis-case-study.md)。

## 3. 骨架与动画

### 现象：编译成功但骨数减少

原因：StudioMDL 裁掉没有权重或 procedural/VRD/attachment 引用的 helper 骨。

处理：比较预期骨清单与编译骨清单，恢复实际权重和 procedural 规则。不要只把缺失名称再写进 QC。

### 现象：动作严重扭曲但 bind 正常

检查：

- 公共 ValveBiped 骨父级是否匹配动画接口；
- local translation 是否混用了米与 Source unit；
- proportion reference/target 是否放反；
- delta rotation 是否意外非 identity；
- include model 顺序和 sequence 声明是否改变；
- 同一骨是否被重复预变换。

### 现象：待机像 T Pose；一次骨轴修正后头歪、下巴前伸

不要把它当成一个问题继续旋 Head 或整条手臂。按两个数据层并行排查：

1. 对每根公共 core 解码 compiled proportion，验证
   `actual_delta ~= target_bind_local_position - animation_bind_local_position`，并检查
   rotation delta 是否符合合同。Forearm/Hand 的大侧轴误差会把 T Pose 泄漏到 idle。
2. 分别解码 `reference`、`CustomModel`、`ragdoll` 等一帧本地序列，确认各自使用的
   native/custom position 与 rotation source，不能默认三者同 pose。
3. 统计每个 world mesh corner 相对 source-fit similarity baseline 的 bind displacement。
   若 source-fit 候选的大部分网格又被逐骨 LBS 移动，头部/头发/宽袖可能被 prepose，
   即使关节轨迹数值看起来已修好。
4. 比较编译后 custom bind 与锁定 Source reference 的 Head/Neck quaternion；不要直接
   使用 Blender/VRM `bone.matrix_local` 作为 ValveBiped frame。
5. 合成真实 include ANI 的 standing/crouching 帧，比较 wrist-vs-clavicle 下倾、Head
   world quaternion 和 known-good/known-bad，而不是只看静态 SMD。

source-fit world 的典型修复是“有证据的 Source custom rotation + 源 pivot + 零逐骨
网格 rebake”，不是“native rotation + 全身 LBS 补偿”。项目级正反例见
[Karin Nyako -> Hunter 案例](20-karin-nyako-hunter-case-study.md)。

### 现象：手指放射状爆开，或双臂看起来左右互换

不要从截图直接交换 L/R。按以下顺序定位：

1. 比较左右 clavicle/upperarm/forearm/hand/finger 的 name、index、parent 和 side sign。
2. 比较 light/主模型原始 parent-local 动画轨道，而不是先比较最终 global pose。
3. 解码 compiled proportion 逐轴 translation 和 quaternion rotation；检查是否用了错误 corrective、纯长度/归一化轴算法或模型专用静态 correction。
4. 计算每根手/指骨的带权几何质心、最近表面和最远点到 bind pivot 的距离，并与源模型比较。
5. 对代表 light 帧做 compiled CPU skin，检查指骨段长度、左右侧别、带权半径和三角绝对边长。

若名称、父链、side sign 和原始 local 动画都正确，而网格离 pivot 数个 Source units，视觉上的“左右互换”通常是错误旋转中心，不是动画真的互换。此时应选择 source-fit pivot 或重新证明 target-fit bind，不能交换左右骨名掩盖问题。

### 现象：手臂像四段折断，但 bind、L/R 和全局 edge 门都正常

先把它当作“完整 bind basis 或关节运动学失败”，不是默认的权重问题。推荐按以下顺序排查：

1. 锁定核心 Clavicle/UpperArm/Forearm/Hand 的 name、index、parent、world rotation 来源和 pivot 来源；检查 child parent-local translation 是否沿预期骨轴。
2. 对一整条代表动画做 predelta FK + CPU LBS：比较相对 bind 的肘部 bend delta、shoulder-hand reach/链长、upper-arm/forearm length drift、有限性和样本覆盖；只看最终 global pose 或全局 edge 分位数不够。
3. 检查 Body、袖子、手套等对象的 source-to-target weight lineage：服装 helper 应沿最近有效 deform ancestor 回落，不能仅因名字含 `Arm`/`Sleeve` 就强塞 UpperArm。
4. 分别审计关节区的同侧/对侧泄漏、Forearm/UpperArm 主导权重、局部连续性和减面后 topology 覆盖。
5. 只有确认是局部权重过渡时，才在已审计 bind-space 区域做最小 smooth；保留其他 influence，重跑下游 proportion、compile、pose、HLMV 与包审计。

不要先交换 L/R、全局涂权重、放宽 edge threshold，或把整片袖子锁到上臂。Witch v0.2 是“旧 edge/HLMV 通过、游戏内仍多段折臂”的反例，见 [Karin Y -> Witch 双目标替换案例](19-karin-y-witch-case-study.md)。

### 现象：序列数少、动作缺失

原因可能是生成 QC 时去重了原生 `$declaresequence`。重复行也可能是接口的一部分。

处理：保留原始声明行及顺序，分别记录总行数、unique 数和有意重复项；审计编译后的 local/virtual sequence。

### 现象：第一人称手臂外形、材质或拓扑仍像参考 Mod

端到端重建与验收流程见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。

高概率原因：只把参考 arms 的内部 `mechanic` token 改成目标 `producer`，VVD/VTX 和参考材质仍被逐字节搬运；骨架兼容被误当成“可见几何来自用户 Blend”的证明。

处理：

1. 分别审计 ABI 与视觉血缘。55 骨、bonemerge 和 sequence 相同只能证明接口兼容，不能证明网格来源。
2. 将最终 arms MDL/VVD/VTX 与参考三件 companion 做 SHA-256 负面比较。
3. 扫描 MDL token 和 release paths，拒绝 `mechanic`、旧参考材质名、旧 `$cdmaterials` namespace。
4. 要求候选只有源 atlas 的材质名，并链接 source polygon manifest、world-SMD extraction、已接受的 view-space placement 和 weight-continuity 报告。逐 influence bind-retarget 若被 edge stretch 门否决，只能作为失败证据。
5. 旧二进制 token 搬运方案在 Karin 项目已被用户否决并废弃，不得重新启用。

### 现象：第一人称手臂三角数正确，但整体位置、大小或比例错误

高概率原因：复制选中 mesh 后直接 `shape_key_clear()`；Blender 删除 shape keys 时没有把当前变换后的 Basis 坐标保留到基础 mesh，导出实际回到了旧 Basis。也可能对 world-bind 顶点只做刚体平移，未执行 view-bind 转换。

处理：

1. 删除 keys 前快照 `Basis.data[].co`，clear 后写回 `mesh.vertices[].co`，再更新 mesh。
2. 更稳妥时，从已验收 world SMD 按 manifest 精确抽取 material + 三个 corner 的 triangle block，避免临时 Blend 的 Basis 状态成为隐式输入。
3. 对比 `selected_world_position` 与“旧未烘焙位置经过已锁定 similarity transform”的最大/RMS 误差，同时要求 UV、权重 ID、权重值和材质零差异。
4. 不要把“公式正确”当作最终门槛。逐权重 `B_view * inverse(B_world)` 后必须比较所有 triangle edge；若 helper/VRD 折叠让相邻点走不同空间分支，改用统一 similarity 保形，再做有证据的同角色参考权重转移和 topology smoothing。单独一个未记录拟合目标与 residual 的经验 Z offset 仍不可接受。

### 现象：静态长刺消失，但腕口仍有小拉片或武器动作下可能撕裂

高概率原因：Basis 已修复，但逐 influence bind conversion 在 `VRD`、`Forearm_driven`、`Driven_ulna` 与 `Hand` 的离散映射边界仍不连续；或者 nearest-reference-point 权重逐点硬赋值后没有沿源拓扑平滑。

处理：

1. 对所有 triangle edge 计算输出/源长度比；全局 similarity 可以整体缩放，但同一候选的局部比率必须一致。
2. 同坐标 corner 必须具有相同权重；左右几何不得出现对侧骨串权重。
3. 计算每个三角形三个角点间权重向量的最大 L1 差，并与成熟参考比较。Karin 参考最大 `0.950164`，最终 smooth 候选 `0.973790`。
4. 权重平滑期间不要每轮 top-3；先在 topology 邻接上扩散完整权重，最后一次性裁 top-3 并归一化。Karin 接受参数为 24 轮、self-weight 2.0。
5. 重新编译唯一 alias，从正面与斜侧面检查腕口、掌心、手指、肩口和脱离腕饰。

### 现象：第一人称漏袖子/腕饰，或把胸腹、裙摆、耳机线带进视野

高概率原因：在重绑定后的 Valve 权重上重新计算源阈值、用坐标长方体裁面、按共享单顶点连通，或把一次审计里的 component 序号硬编码到另一拓扑版本。

处理：

1. 在源哈希锁定的原 Blend 上生成 polygon-index manifest；权重阈值只在原源骨组上计算。
2. 对源与派生对象比较顶点数、edge/polygon 顺序和 topology hash。完全一致才可复用 polygon indices。
3. 面区域必须按共享完整边连接；脱离腕饰也按完整 edge component 与侧向权重/空间条件选择。
4. `Outer*`、`Code*`、`Pocket_String*`、`Back_Ribbon*` 出现在最终手臂正权重闭包中即失败；它们不是腕饰骨。
5. 肩根裁切通常会留下相机外的开口。极限动作可见时只扩一圈或封切环，不要把整个胸腹主块并入 viewmodel。

### 现象：手腕旋转时袖子塌陷或前臂像一根硬管

原因：把全部 `LowerArm` 权重映射到普通 `Forearm`，丢掉 viewmodel 的 `Forearm_driven` / `Driven_ulna` 扭转分布，或者错误地把 world `VRD_L/R` 当作 55 骨 ABI 节点。

处理：保留参考 55 骨中两侧的两个 forearm helper 及 rest transform，优先从同角色参考在共同 rest space 转移扭转权重。world `VRD` 只允许按有证据的比例折叠为 helper 权重，不得增加到 view ABI。

### 现象：启用 Mod 后地图加载期稳定崩溃，关闭后正常

先把“启用 Mod 才崩”当作定位范围，不要当作根因。若 dump 固定落在 `studiorender.dll` 的 vertex/tangent 读取路径，优先审计 world MDL/VVD/VTX，而不是同时拆 HUD、PHY、jiggle、flex 和材质。

处理：

1. 立即复制所有 minidump 并保存 SHA-256、时间和候选 VPK SHA-256。
2. 比较异常码、模块、ASLR 归一化 offset 和调用栈；重复落在同一 offset 表明确定性数据问题。
3. 反汇编 fault 附近指令，从寄存器还原 vertex index/base address，再映射回 MDL bodypart/model/mesh、VTX original ID 与 VVD 上界。
4. 检查 compiled VVD LOD0；工程目标 `<=60,000`，拒绝 `>=65,535`。
5. 逐 strip-group 验证 VTX raw index 在 mesh 内、加 mesh start 后在 model 内、最终 global index 在 VVD 内，并要求每个 model 覆盖完整。
6. 验证实际安装 VPK 与 release 哈希一致；扫描启用 addon 的相同目标路径，排除混包。
7. 将 MDL/VVD/VTX/PHY 作为同轮原子 companion 替换。若 `<60k` 且 mapping clean 后仍崩，再在相同几何基线上按 animation/flex、procedural/VRD、PHY、arms/HUD 分组二分。

StudioMDL exit 0、无 warning 和 companion checksum 一致不能证明 VTX mapping 正确。

## 4. 单位与导出

### 现象：根骨正常，子骨翻译小约 52 倍

原因：只设置 `armature.scale`，没有缩放 `armature.data` 的 edit bones/local translations。

处理：保持对象矩阵 identity，统一缩放 armature data 和每个唯一 mesh data block；重新导出所有 SMD/VTA/reference。

### 现象：VTA 与 SMD 尺寸不同

原因：VTA 未经过同一单位转换或导出中途卡住。

处理：结构化解析 VTA，只缩放 position；保持 normals、indices、frame 信息；比较 frame 0 bounds。

## 5. 材质、Boomer bile 与发光

### 现象：bile 在皮肤/头发可见，在大面积衣物不可见

已验证根因：衣物使用 EmissiveBlend 额外加法 pass；该 pass 不采样 `survivors_it_shared.vmt` 的 `$detail`/IT，干净颜色层会盖淡或盖住污渍。错误的 flow/emissive 参数还可能让整件衣物采样固定角落。

处理：删除衣物 `$emissiveblend*`，把作者 emission 强度与低背景合成为 SelfIllum mask，在标准 VertexLitGeneric pass 中同时使用 bile patch 和 SelfIllum。然后重新构建 VMT/VTF 与 VPK，并在游戏中复测。Karin 的该修复已由用户手工实机确认正常；后续角色仍需针对自己的材质和遮罩重复验证。

### 现象：所有 VMT 都 include bile，但游戏无污渍

检查：

- include 是否精确为 `materials/models/survivors/survivors_it_shared.vmt`；
- VMT 根是否为 `patch`，参数是否放在 `insert`；
- 是否本地又定义 `$detail` 覆盖了共享 bile；
- 游戏是否实际加载本 VMT；
- 是否有其他 shader pass 或 skin family 覆盖显示；
- VPK 中的 VMT 是否等于刚生成 loose tree。

`$nodecal 1` 不是主要嫌疑，Boomer bile 使用 `$detail` 和 `IT` proxy，不是普通 decal。

### 现象：VTF 有连续 alpha，VMT 也写了 `$translucent`，游戏仍显示不透明

不要再次只检查 token。按层隔离：

1. 解码最终 VTF，统计 `0 < alpha < 255` 的像素，而不是只看源 PNG。
2. 用 SMD UV 证明帽檐、袖子或衣摆确实采样这些半透明区。
3. 验证 `$alphatest`/`$translucent`/`$additive` 互斥。
4. 只替换这一张 VMT 做矩阵：原组合、`$phong 0` 保留 bump、最小 shared-bile translucent、必要时 standalone 对照；每次只改一个变量。
5. 最小 shared-bile profile 保留 basetexture/halflambert/nocull/nodecal/translucent/phong0，先移除 bump、其余 Phong family、SelfIllum 和本地 detail。
6. loose tree、VPK 内 entry 与游戏实际加载文件逐字节一致后再实机复测。

静态 alpha 完整只能证明 payload；shader combo 和第三人称排序必须由游戏画面确认。材质名中的 `Cutout` 也不是 alpha mode。

### 现象：开启“微光”后表面变暗或失去正常照明

原因：把 128/255 之类高 SelfIllum mask 再乘很低 tint。SelfIllum mask 是正常光照与自发光之间的插值权重，高 mask 会过度压制正常照明。

处理：普通区域用约 8/255 的 mask；作者亮区可映射到约 16/255。不要用高 mask + 低 tint 模拟低亮。

### 现象：法线 mip 出现彩边

原因：源 normal atlas 的黑色无定义区域被 resize/mipmap 插值。

处理：在 resize 前把精确 `(0,0,0)` 改为中性 `(128,128,255)`，resize 后重新归一化，并验证 green channel 方向。

### 现象：VTF 校验器报告常量 mask 上下翻转

原因：常量图与其垂直翻转逐像素完全相同，方向检测没有可辨识信号。

处理：对被证明为常量的 mask 明确豁免 orientation 比较；非恒定 base/normal/emission 仍保持方向检查。

## 6. 物理

### 现象：ragdoll hull 与模型远离或巨大错位

高概率原因：physics 顶点被手工变换后，StudioMDL 又执行 named-bone bind conversion。

处理：移除预变换，从原始 hull 与目标骨命名关系重编；验证同轮 MDL/PHY checksum 和 HLMV overlay。

### 现象：同一角色的某个 Bride/DLC/特殊 variant 悬空，另一变体正常

优先检查跨变体 animation/proportion root 合同，而不是调整鞋、Foot/Toe、`$illumposition`、bbox 或 PHY：

1. 分别列出 canonical reference 的完整 position + rotation 坐标系和 hash。
2. 比较 projected Pelvis、core/full projected reference、root delta 与 world parts 是否应相等。
3. 验证同一 sequence、相同相机/控制状态下的 Ground 接触，排除 HLMV framing 假象。
4. 若共享可见 bind 的目标不相等，统一正确的 canonical/proportion 投影后重建两目标；仍保留各自原生 QC/collision/PHY。

不要用移动 mesh、PHY 顶点或单独追加第二个 ground offset 掩盖 root delta 错误。地面高度只有 proportion target Pelvis 的一个 owner。

### 现象：头发、耳朵、尾巴抖动爆炸

检查 VRM 到 Source 的单位/重力假设、链父级、首动态代表、pivot、刚度/阻尼上限、根部角度限制和是否存在循环/断链。按附件类别使用稳定 profile，而非逐骨原样复制 VRM 数值。

### 现象：长发根部出现细条，整束头发被拉到很远

高概率原因不是“阻尼太低”，而是多段 spring 折叠后误选了链中/末端骨作首动态代表。根部 seam 因此绕远端 pivot 旋转，形成长力臂。

处理：

1. 从 VRM group 找到静态 anchor 与 `path_position=0` 首动态段。
2. 要求动态目标代表是 anchor 的 direct child；比较 compiled parent-to-child segment 与源 path-0 segment。
3. 统计 anchor/dynamic 共权 seam 顶点到 pivot 的距离。
4. 用声明 angle 做多轴正负 CPU skin，报告边长 max/P99、绝对变化和根区位移。
5. 做 pivot-only counterfactual：只换近端 pivot，不改权重/角度。畸变骤降即可确认主因。
6. 修 source-of-truth mapping，重新生成 target、Blend、全部 world/light SMD/QC/MDL；不能只手改 QCI。
7. pivot 正确后再调 length、mass、stiffness、damping 和 angle，并验证 world/light compiled payload 全字段一致。

`$jigglebone length` 不会搬动 bind pivot。即使把角度降得很小，错误的大半径仍可能产生可见拉丝。

## 7. HLMV 与数据血缘

### 现象：HLMV 显示正常，但交付 VPK 像参考/原版模型

原因：HLMV 可能通过虚拟文件系统加载同路径原版模型，或 VPK 从错误 loose tree 构建。

处理：

1. 编译唯一 preview alias。
2. QC 除 `$modelname` 外与正式构建一致，并比较输入哈希。
3. 从隔离 game root 打开 alias。
4. 比较 VPK 内 MDL 与项目编译输出、参考包的 SHA-256。
5. 用候选 manifest，而非目录扫描，指定交付 VPK。
6. 保存正面、背面、侧面/斜侧面以及腕口近景；标题或模型标签必须能看到唯一 alias。单一正面图不能证明手背、掌心和腕饰闭包正确。

### 现象：HLMV 绝对路径打不开或浏览器显示错误模型

将资源放在隔离 gameinfo root 下，并同时给 `-game` 与唯一 preview MDL 使用绝对路径。HLMV 的相对模型参数可能按启动 cwd 而不是 `-game` root 解析，导致空白或错误模型。保留窗口标题、唯一 alias、选择的 sequence/frame 和 Ground/Bones/Origin 控件状态；多窗口自动化还要锁定目标窗口并回读 frame，不能只看截图文件名。

若绝对路径、候选和控制组仍不能获得可信视图，把 HLMV 门记为 `unknown` 或
`unavailable_with_control_failure`，既不能写 pass，也不能仅凭工具错误写模型 fail。
继续使用 compiled bind/sequence/proportion 解码、真实 ANI 合成、CPU skin 与非空离线
渲染作为前门，最终状态仍由游戏实测闭环。

## 8. 构建与同步盘

### 现象：VTEX 成功退出后写回/删除 VTF 报 PermissionError

原因：同步客户端短暂持有文件句柄。

处理：对读取、删除、原子替换使用有限重试和明确总时限；超时后保留中间文件并报错，不无限等待。Karin 构建使用过约 30 秒上限。

### 现象：静态验证通过，VPK 仍包含旧文件

原因：输出目录未清理、验证器只检查 SMD 引用集合而未拒绝 extra VMT/VTF，或从旧 loose tree 打包。

处理：输出到新目录；验证 `actual files == expected closure`；VPK payload 与 loose tree 逐字节比较。

Karin source-derived arms 候选的项目实测闭包是 33 文件。若仍是带 14 件 `materials/ko_komado_pt/**` 的旧闭包，说明参考 arms 材质尚未移除；不要把“文件更多”误解为更完整。

### 现象：输出树出现 `*_冲突文件_*` 或同步客户端副本

原因：同步盘在并发写入或重命名时保留冲突副本。该文件即使未被 VMT 引用，也会破坏严格 payload 闭包，并可能被错误打包。

处理：停止在该树上继续发布，保全并哈希冲突文件，使用新的 run/candidate 目录重建。不要自动删除未知冲突后宣称原树干净；验证器必须拒绝任何不在 expected manifest 中的文件。

## 9. 修复后的最小重建原则

| 修复内容 | 必须重建 | 一般不应变化 |
| --- | --- | --- |
| VMT/VTF | 材质输出、loose tree、VPK | MDL/VVD/VTX/PHY、HUD |
| shape key/网格 | SMD/VTA、MDL/VVD/VTX、可能 PHY、VPK | HUD |
| skeleton/proportion | SMD/reference/QC、MDL 全套、HLMV、VPK | HUD/材质源图 |
| accessory/procedural pivot | rig map、target/derived Blend、world/light SMD/QC/MDL、相关 interface/physics、VPK | HUD、基础材质；arms 仅在共享骨受影响时重建 |
| physics | physics SMD/QC、同轮 MDL/PHY、VPK | HUD、base VTF |
| HUD | HUD VTF、loose tree、VPK | world/arms 二进制 |

候选差异出现表外变化时停止交付。

## 10. 排障记录格式

每次异常至少记录：

```text
现象：
候选 SHA-256：
环境与复现步骤：
直接证据：
初始假设：
排除项：
确认根因：
修改的 source-of-truth：
重建范围：
静态结果：
HLMV 结果：
实机复测状态：
正面回归报告：
已知坏候选/预期失败 check ID：
```

保留失败候选和报告，但明确标记 rejected，避免后续 agent 再次采用。
