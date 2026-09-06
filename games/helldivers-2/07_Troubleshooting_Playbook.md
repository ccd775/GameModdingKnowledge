# 排障手册

> 使用方式：先根据运行时症状选择假设，再用最小差分审计证伪。不要从截图直接跳到大规模重绑或全身比例重做。

## 全身或局部明显拉伸

### 高概率根因

- 把 armature/world-space 顶点写成 donor mesh-local，运行时二次应用 transform。
- 错把 Stingray edit-bone roll 当人体骨段方向。
- 按 HD2 原生骨长逐段拟合源角色，破坏原比例。
- donor swap 实际继承 donor bind，但 authoring 按 target bind 计算。
- rest origin 逐骨替换不连续，多骨 LBS 边界产生剪切。
- local `0_N` palette 映射错位。

### 检查顺序

1. 对比源、authoring、compiled RawMesh 的逐顶点坐标与矩阵链。
2. 检查 object matrix 是否 identity、AQ 是否未应用它。
3. 证明 `Z_ObjectID` donor 的 TransformInfo/BoneInfo provenance。
4. 对每 Unit 解析 `0_N -> BoneInfo`，不要只看组名。
5. 比较骨 origin delta 在父子链上的连续性。
6. 用差分姿势和 edge ratio 定位第一条异常边。

### 不要做

- 不要继续通过视觉缩放某一肢体“对齐”。
- 不要用 neutral pose 成功证明动态合同正确。
- 不要把全身权重重新自动归一后直接发布。

## 多个分件同时爆开，或头盔巨大悬空

肩、胯、腿、尾巴和头盔若在同一装备中同时出现比例/间距异常，优先把问题升级为 Unit ABI/lineage 故障，不要逐个部位刷权重或缩放：

1. 比较每个最终目标 Unit 的 `MeshInfo transform`、`TransformInfo`、`BoneInfo/RealIndices` 与 inverse bind provenance。
2. 检查编译器是否把同一 RawMesh 分别注入了多个 target-native Unit，却默认这些 target bind 相容。
3. 按逻辑角色统计完整 Toc/GPU/Stream payload 哈希；若预期完全相同而哈希不同，继续做字段差分。
4. 选择一个已证明的完整 carrier 做单角色探针：编译一次、锁定 bind signature、只改 FileID 克隆完整 Unit。
5. Helmet 单独检查 head carrier 与 anchor；刚性 `head` 权重不能证明 container 尺度正确。

若同一模型在一个目标相对正常、在另两个目标整体爆开，这是 target-native bind 差异的强信号。Umbrella v1 的 RS6/RS67/RS100 运行时反例见 [案例记录](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

不要先做局部缩放/平移。它可能只让一个目标或 neutral 画面对齐，同时固化错误 mesh-local/container 关系。

## 头发、腹部或单侧肢体完全消失

先查 role/face coverage，而不是骨权重：

1. 从权威源生成对象、连通片、源面和保存 shape-key inventory。
2. 记录每个源面是被显式删除，还是恰好归一个 visible role；零归属和多归属都硬失败。
3. 对每个 role 核对 target Unit、全部正 LOD、local palette、section index/count 和材质。
4. 检查左右 role/target manifest 是否完整；不要因为一个体型或 LOD 与另一个字节相同就少写目标 FileID。
5. 删除衣物使用精确 delete set；共享材质、空间接近或名字相似不构成删除依据。

若 authoring 中存在但 compiled Unit 不存在，定位编译 role/LOD/section；若 compiled 中存在但游戏不显示，定位 target ownership、culling/LOD 或材质。不要用新增重复几何掩盖缺失。

## 肩膀圆、塌、断开或举臂破面

先按症状定位责任层：

| 运行时/预览症状 | 首查 | 典型根因 |
| --- | --- | --- |
| 肩膀圆、宽、像健壮体型 | reference identity、源 current mix、局部形变清单 | 用错参考；人工抬肩峰/扩肩；腋下误分到 Arm |
| 肩根有直切断面 | Torso/Arm face ownership 与权威 seam 拓扑 | 漏面、重复面、声明边界不对应、顶点不共点或完整权重行不同 |
| 上背绳从肩顶跨到大臂 | game-space partition 与腋下位置 | 在 source space 套 game-space envelope，把腋下切向肘部 |
| 右臂向前折、左臂向后折 | signed source/target chain axis | source local `+Y` 被映到 target local `+Y`，而目标链沿 `+X` |
| 左右宽袖反向扭转 | elbow roll 与 parent-child axis | 直接套用不镜像的 target raw roll |
| 腕口剪切、掌心方向错 | LowerArm/Hand continuity | Hand 使用独立 fixed frame，未继承 LowerArm linear |
| endpoint closure 近 0 仍断肩 | source/target 肩语义基数、seam、完整 Unit lineage | closure 只覆盖被测 correction；Shoulder/UpperArm 仍可能分骨或使用不同 bind |
| 肩线仍错且大臂中段出现折带 | natural seam 权重、几何 correction、post-edit rings | 几何按 shoulder 烘焙后改绑 clavicle；固定两圈过渡把断缝移到上臂中段 |

排查顺序：

1. 锁定用户指定的精确 Ref 目录、Blend、triplet、源角色和哈希。发现参考错误时，隔离所有派生阈值/候选，不在其上继续调肩。
2. 比较 source current mix 与候选的肩帽、肩胛、腋下和近端上臂。若出现未授权 local shape edit，先回滚。
3. 将候选面心变换到阈值所属的游戏空间，再分 Torso/Arm；检查每个源面恰好归属一次。冻结权威 seam 点/边集合；只有 Ref 证明单闭环时才要求单闭环，开放衣物也必须两侧覆盖完整、共点且同完整权重行。
4. 以 neck-to-axilla 绳路作示踪；绳子跨大臂时先修面归属，不先改绳权重。
5. 比较 source Shoulder/UpperArm 与 final-lineage clavicle/shoulder 的语义数量。many-to-one 时把两组权重投影到同一 target shoulder，以 UpperArm -> LowerArm 为实际段锚。
6. 在任何 seam edit 前分别计算 Torso/Arm 的自然 final-lineage 权重。若已逐点一致，禁止 blanket shared-bone override；若误差很大，先修 owner/palette/projection，不用覆写掩盖。
7. 肩部保留已证明 carrier roll，并只附加闭合实际链轴的 minimal swing；再计算有符号 chain axis、segment endpoint closure、full-3D mirror、target-local transverse 和 world fore/aft。
8. 肘部使用 parent-child shortest-arc + 轴向段长配准；Hand 继承 LowerArm linear 后在 wrist 重锚。
9. 在 authoring 与最终编译 Unit 上分别跑 idle、salute、arm-up、左右 hand-to-head、asymmetric locomotion；固定 neutral seam 对应，不在 posed 状态重新配对。专项姿态显式排除待证伪的替代骨，并同时检查 seam gap、上臂邻接 edge ratio、正背与两侧近景。

禁止操作：

- 不用局部抬肩峰、外扩肩帽或缩放近端上臂“做出肩峰”。
- 不用 `R_target * transpose(R_source)` 代替有符号语义轴证明。
- 不用 radial RMS 单独验收方向；错转 90 度仍可能保持相同半径。
- 不给左右两侧使用额外相反的 basis sign；镜像应由源骨架和完整三维门禁证明。
- 不把 endpoint closure、neutral 共点或 bounds 正常中的任何一个单项写成“肩部已通过”。
- 不把肩缝整圈锁成 clavicle/chest/root 后再用固定两圈插值“平滑”；先证明自然权重和最终 Unit lineage。
- 不让差分姿态同时旋转正确 shoulder 与待证伪 clavicle，再以 gap=0 宣布通过。

肩部主方法见 [Karin Nyako RE2310 案例](case-studies/Karin_Nyako_RE2310.md)；开放跨 profile seam 见 [DR03 案例](case-studies/Karin_DR03_CM10_EX00.md)；many-to-one 肩骨与完整 Unit 反例见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)；自然权重与错误人工过渡圈的运行时对照见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

## 腹部黑带、锯齿空隙或巨大断层

### 先区分材质与几何

- 黑色区域轮廓随姿态扩张、能看见背景：通常是几何/权重断层。
- 区域始终贴着表面且纹理连续性异常：可能是材质/UV。
- 前后都有环状断层：常见于 torso/hip 壳的不同骨语义。

### 常见几何根因

- bridge 几何归属错误或被放在可替换 Helmet 槽。
- 腹部环一部分由 chest/spine2，另一部分由 spine1/hips 驱动。
- 最近表面权重迁移穿过腰带/内衬/皮肤之间的空间邻近，却忽略拓扑组件。
- 脚本只在 authoring 对象上修复，最终编译 Unit 使用另一 LOD/副本。

### 排查

1. 列出断层上下边界的连通片和 winner bones。
2. 构造 chest-spine2、spine1-hips 最大相对姿势。
3. 在 authoring 与 compiled Unit 中分别定位同一 semantic vertices。
4. 检查所有 LOD 和 Slim/Stocky 副本。
5. 比较最终 draw/index，确认不是 section 漏面。
6. 只回滚/重分配目标权重行，冻结已确认的比例和材质。

## 大腿根嵌入骨盆、短裤消失

- donor 最近三角形迁移把短裤/腿带当皮肤处理。
- thigh/hips 权重边界按空间距离而非连通片语义切分。
- 骨 origin/rest 与源骨盆比例不一致。

解决：分别审计皮肤、短裤、腰带和腿带连通片；比较源模型姿态轮廓；使用 donor 语义作为引导而不是全模型直接拷贝权重。对相邻但独立的刚性组件设置明确保护。

若症状是真正的腿/胯断开，再检查 ownership 图是否从 Torso 直接跨到 Leg。设计为 `torso -> hip -> leg` 时，必须分别冻结 torso/hip 与 hip/leg seam，并把 direct torso/leg 共享点数量设为 0；不要用一条 emergency root 权重旁路掩盖缺失的 hip bridge。

## 手指极度扭曲

### 失败方法

- 将所有 finger weights 合并到 hand：外观暂时不扭曲，但手指完全不动。
- 逐骨复制另一个角色 finger rest origin：枢轴距离和父子不连续会拉长/反曲。
- 保留远离手指的微小 finger 权重：袖口/饰带在 curl 时飞出。

### 正确方向

- 保留完整左右 finger palette 和逐指 articulation。
- 在分件/导出前把源 rest 顶点按每个 influence 烘焙到 Ref/game bind；显式证明源骨纵轴到目标链轴。
- Hand 继承 LowerArm linear 并在 wrist 重锚，finger 再使用其已证明的 semantic frame，避免掌腕断开。
- 过渡区权重限制在合理枢轴距离，最多 4 influences。
- 远离手指的附件清除 finger mass，并转给语义父骨（通常 hand/elbow，需按组件证明）。
- 验证 30/30 语义骨运动、单/双手 curl、抬臂 + curl、过渡环 edge ratios。

## 鞋底卷曲或脚折叠

先区分三类：

- 鞋尖静态卷曲：可能是“geometry rest override + 已合并权重”重复校正。
- 走路/踏步时双脚交叉：通常是腿链只做全局 affine，未完成 `thigh -> knee -> foot -> ball` 的 source-rest -> target-bind。
- 脚趾静态穿出鞋面：优先检查源 Blend 保存的高跟/鞋型 shape key 是否在 retarget 前烘焙。

检查：

1. 源/候选侧面轮廓和鞋底平面。
2. Toe/Foot 的 geometry overrides 与权重合并是否同时存在。
3. 审计完整腿链的 signed axis、segment closure、左右 palette、distal mirror 和 Foot/Ball linear/pivot continuity。
4. 冻结保存中的 `对象 -> shape key -> value`；用 shape-key-only current mix 烘焙，证明 topology/UV/weights/face ownership 不变。
5. 验证左右腿所有 LOD，并在 alternating step 的正面和两侧近景检查脚距中线及鞋面包覆。

Karin Nyako v4 因漏烘焙 `Foot_HighHeel=1.0` 而在游戏中露脚趾；该键影响 1,886 顶点、最大源位移 `0.0305432 m`。这是 `case-specific` 反例，不是通用阈值。

## 头部/身体接口过低、头盔悬空

- 不要直接拉长脖子。
- 先测最终编译 Torso 顶部与已验证 donor 的 body interface，高度问题可能是整个身体 anchor/rest，而非可见颈部顶点。
- bridge 必须属于 Torso 等常驻槽。
- 使用原版头盔和其他自定义头部验证；只用自家头部会掩盖接口错误。
- 检查 Helmet 与 Torso Unit 是否使用不同 rest 合同。
- 若头盔巨大悬空且其他身体分件也有比例问题，优先检查 Helmet target-native Unit 与写入 RawMesh 的完整 bind/container lineage；不要先缩小或下移头盔。

## 原版盔甲呈透明塑料叠加

这不是“透明度还不够低”，而是 suppression 方法错误：原生三角形仍在 draw，只换成 glass/alpha 材质。glass shader 可继续输出 base opacity、specular、refraction 或排序效果。

正确方向：

1. 枚举全部 suppression target 与其每个正 render LOD，另行识别 culling LOD。
2. 保留 Unit metadata、TransformInfo/BoneInfo、LOD/MeshInfo、indices、sections、原材质和 culling body。
3. 仅把正 render LOD position stream 收缩为确定性微型占位，或使用已被当前工具/游戏证明的 zero-draw 合同。
4. 编译后回读 bounds、finite positions、weights、palette、sections；禁止任何正 draw 依赖 suppression glass。
5. 游戏内在强光、正背和两侧确认没有面罩、绑带、板甲或透明轮廓。

不要把“纹理 alpha=0”或“材质名 Transparent”写成 invisible 证明。

## 穿盔甲有头，但头盔槽为空

这是 target ownership 错误，不是头部模型丢失：完整头部被编进 armor/body role，而 Helmet Unit 被 suppression。

1. 从 customization/manifest 建立实际消费者槽位图。
2. 让 head/face/hair/ears/head accessories 只归可见 Helmet role，并使用该目标可解析的 head palette。
3. 从 Torso 移除同一批源面；每个源面/对象恰好出现一次。
4. Helmet target 必须从 suppression 集合移到 visible 集合，两集合互斥。
5. 分别装备盔甲和头盔验证；整套同时装备会掩盖跨槽重复或缺失。

## 刘海黑色或消失

### 黑色

- 第二 draw 仍引用 donor gore/错误 child material。
- material ID 正确但 draw start/count 仍是旧数值。
- 私有 TextureMap ID 未闭合或与另一 Mod 冲突。
- BaseColor/alpha 编码污染。

### 消失

- 材质名显示 Transparent，因此误套 AlphaClip；实际 alpha 可能接近 1。
- alpha mask 通道/阈值错误。
- Head LOD 只有部分 draw 被重写。

### 处理

1. 统计源 alpha min/max、低于阈值的像素比例。
2. 若最低仍约 0.996 且无像素低于 0.5，按 opaque 处理。
3. 只重写 Head 各 LOD 的目标 draw material ID。
4. 证明 GPU、indices、UV、weights 不变。
5. 锁定当前实际 draw start/count，不沿用旧 magic number。

## 角色青白过曝或面部亮度异常

### 青白过曝

- donor child material emission strength 很高。
- atlas alpha 非零并参与 emission mask。
- BaseColor BC7 编码未声明 sRGB，gamma 被抬高。

检查 child 参数与 atlas 通道联合效果，不能只看贴图 RGB。关闭/降低 emission 后做 exact float/payload delta 和解码 luma 对比。

### 面部过亮/过暗/脏

- 先判断 AO、NAR、diffuse 梯度、动态光照和 emission 哪一项主导。
- 面部修复使用 skin-only UV mask，排除眼睛、嘴线和刘海。
- 以强阴影和中等光照两个场景做 ROI 统计，防止修暗处时把正常光照烧白。
- New_SR24 最终选择 emission 归零；说明离线 fill 有帮助不代表游戏 parent shader 下应保留。

## 头部纯黑或纯白

稀疏 alpha 与 BC7 联合压缩可能污染遮罩外 RGB。症状可以表现为大块黑/白，而材质 ID 本身完全正确。

处理：

- 用 `texconv -sepalpha` 重新编码。
- 保持 TextureMap ID 和 Material payload 不变，仅替换目标 GPU 区间。
- 解码候选 DDS，比较 alpha 外/内 ROI、luma、边界颜色。
- 做 TextureMap load-save 和整档 roundtrip。

## 两个 Mod 互相串贴图

根因通常不是 Unit ID，而是复用了 donor 的本地 child Material 或 TextureMap ID。加载顺序决定同 ID 最终解析到哪份 payload。

修复：

1. 生成稳定 namespace 字符串，例如 `mods/<author>/<character>/<slot>/<version>`。
2. 为所有本地 child Material/TextureMap 生成确定性私有 64-bit ID。
3. 重写材质内部纹理引用和模型 material ID。
4. 允许 stock parent 保留外部引用。
5. 扫描当前游戏和工作区的 full ID 与 high32/ShortID 碰撞。
6. 验证每个私有材质被模型按预期引用，所有纹理闭合。

## AQ 合并随机失败或 OSError 22

- 检查是否并发运行了多个 Blender/AQ 进程。
- 检查共享 `TEMP/TMP` 是否被竞争。
- 串行重跑，并为进程设置隔离临时目录。
- 检查 AQ 插件是否在 `--factory-startup` 下未注册。
- 保留失败报告；不要因最终文件哈希碰巧相同而重新解释为成功。

## 静态报告全绿但游戏仍错

这说明验证模型缺少外部合同。常见缺口：

- preview rig 与游戏驱动矩阵不同。
- 只测 neutral，没有骨 A/B 相对运动。
- 只测 post-override seam 相同，没有记录 natural pre-override 权重失败。
- 差分姿态把正确骨和错误替代骨一起移动，实际没有制造相对运动。
- 只测 authoring，没有检查 compiled Unit。
- 只测自家头部，没有可组合装备。
- 只看 LOD0/Slim。
- 材质 roundtrip 正确，但 parent shader 运行时语义不同。

正确反应是把运行时症状转成新的可证伪门禁，并回到最近运行时接受基线；不是继续提高同一离线报告的检查数量而不改变其观察面。

## Armor LUT 迁移后仍无血液/虫液/污渍

按层排查，不要继续盲调 LUT 颜色：

1. child 是否真的迁移到完整 Armor LUT/hybrid ABI，而非只替换 parent ID。
2. shader 读取的 UV component 是否有非恒定、非退化坐标；“存在 UV1”不是证据。
3. `IdMasksArray` 是否实际提供非零 row weights，static `MaterialLut` 是否与它匹配。
4. 当前装备的 `Piece.MaterialLut` 是否在 spawn 时覆盖 static LUT。
5. coverage map 是否遗漏 undergarment、outer armor、肩、附件、Slim/Stocky 或左右侧 Piece。
6. 游戏目录实际部署哈希与 intended candidate 是否一致；同 archive root 不得堆叠多个候选。

若颜色/粗糙度变化但 splat 边界不变，说明 LUT 可达但不是唯一主导层。若整件变灰、银、黑白或出现棕灰摩尔纹，优先检查 DecalSheet coordinate、ID-mask 行权重和 donor LUT/模型耦合，不要把现象命名成“灰尘”。

当 face/Advanced draw 正常而所有 Armor LUT body draw 同时变成深灰反光金属时，优先按“作者颜色 sampler 未执行”处理：

1. 确认 DecalSheet 纹理槽确实绑定作者 BaseColor，但不要把“已绑定”当作“已采样”。
2. 从目标 parent shader 确认 DecalSheet 使用 UV0/UV1/UV2 中哪一层及坐标范围门禁。
3. 对选中 Material 的 compiled Unit 顶点统计该层的 unique/min/max；常量 `(0,1)` 可能被严格开区间直接拒绝。
4. 若源颜色来自 UV0、目标 DecalSheet 来自 UV2，用 material-scoped UV0 -> UV2 单变量候选；保留专用 UV1，不要再次改 LUT。
5. 要求候选 GPU 精确等于源 GPU 加目标 UV2 写入，并做 clean-color 运行时复验。

当身体 splat 已恢复、但整个头部或头盔完全没有时，不要继续修改九个 body LUT：

1. 从 customization-set 重新枚举全部 kit type；确认 Helmet 是否属于独立 `kit_type=1`、独立 archive/set/kit。
2. 以可见 Head/Helmet Unit 为终点反查 Material；检查它是否仍为 Advanced child，以及目标 Material 顶点的 UV1/UV2 是否仍为常量。
3. 单独统计 Helmet `Piece.MaterialLut` 的全局引用和 `PatternLut`；只有爆炸半径已证明并接受的 MaterialLut 才能 same-ID 覆盖，不要顺手覆盖 PatternLut。
4. 反提取原生 Helmet LUT，要求目标与验证源的完整 DDS ABI 一致，再保留目标 ID/header/mip 合同注入内容。
5. head 材质迁移应保留已接受的脸部 atlas/颜色处理；不要把 body 的 DecalSheet 纹理直接套到 face。
6. 分开记录 body runtime accepted 与 head/helmet pending；一个 Piece 成功不能提升整套装备状态。

当 head 已迁移到 hybrid、UV 和 Helmet LUT 均已闭合，但 hair/eyes/ears 反而呈深灰反光金属时，优先检查 DecalSheet alpha，而不是再次修改 UV 或 LUT：

1. 先证明 RGB atlas 仍完整，并冻结能区分 body 正常、head 金属的前后截图。
2. 解码 head Decal，统计 alpha min/max、0/255 像素数和实际 UV ROI。大量 alpha=0 且 RGB 有内容，说明颜色可能被 coverage 遮掉。
3. 比较 source/target parent 的 alpha 语义。Advanced Color/Emission alpha 可能是 fill/emission mask；Armor LUT DecalSheet alpha 可能是作者颜色 coverage，二者不可直接等同。
4. 若 head draw 逻辑上应不透明，构造 RGB 保持、alpha=255 的独立 Decal；使用 alpha-preserving BC7 并解码确认每个像素仍为 255。
5. 只替换该 TextureMap 的 GPU payload，要求 Material、UV、LUT、Texture main、其他 GPU 区间和贴图预算不变；双构建与整档 roundtrip 仍需通过。
6. DDS 输入头和归档继承头的 `miscFlags2` 可不同。若宽高/format/mip/array 相同且 BC payload 逐字节一致，不要为了整份 DDS 哈希相等而擅自改 Texture main metadata。

New_SR24 V24 就是该故障：head atlas RGB 正常，但 alpha 88.4498596% 为 0，Armor LUT 因此显示金属底层。V25 仅把 2048² head Decal alpha 固定为 255；这是一项 texture-payload 修复，不是新的骨架、UV 或 LUT 修复。

## Armor LUT 同 ID 覆盖污染其他装备

- 从当前 armor-set 快照统计该 LUT ID 的所有 Piece 和 armor kit，不只看目标套装。
- 目标 ID 只要被另一个 kit 引用，就必须拒绝默认 same-ID 覆盖，除非用户明确接受完整爆炸半径。
- 发布包保留目标套装自己的 LUT ID；donor 只可作为像素内容证据，不能复用 donor ID。
- target/source DDS 的 148-byte header、尺寸、mip、format、array、总长和 GPU payload 必须全部一致。
- 注入后反提取每个目标 DDS，并比较精确哈希；仅看 builder 成功日志不够。

## 降贴图后包仍异常大或透明件复发

- 按语义累加所有独立 TextureMap 的 base-level 面积；不要只列每张最大尺寸。
- 检查 primary/secondary 是否携带内容相同但 ID 不同的重复图。
- 检查已经无 draw 引用的旧 AlphaClip、材质探针和纹理闭包是否仍被打包。
- 逻辑不透明 BaseColor 必须解码检查 alpha。普通 BC7 即使输入 alpha=255，也可能回读到 251；需要提高 alpha 权重的编码探针，而不是重新启用 AlphaClip。
- 将 GPU/ZIP 体积变化与资源清单绑定；体积下降本身不能证明材质和引用闭包正确。
