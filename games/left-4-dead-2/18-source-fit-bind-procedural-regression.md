# Source-Fit Bind、动画接入与 Procedural 回归排障

本文整理角色替换项目中最容易互相误诊的数据层：网格 bind、目标骨架 rest、原生
动画接入、本地 pose sequence、比例校正和附件 procedural 物理。核心目标是先证明
错误发生在哪一层，再选择最小且可回归验证的修复。

文中的流程是通用方法。骨数、角度、质量、刚度、阻尼、地面偏移和顶点阈值都必须由当前项目重新测量；案例数值只作为证据示例。

## 1. 先分清七个独立数据层

一个模型“能编译、能显示”并不能证明这些层彼此匹配：

| 层 | 决定什么 | 主要证据 |
| --- | --- | --- |
| Output slot / ABI | 覆盖路径、ValveBiped 名称、bonemerge、attachment、hitbox | 原生当前版本和目标槽位 |
| Character bind/rest | 角色的骨长、肩宽、头身比、旋转中心 | 用户源模型、同角色成熟参考 |
| Mesh bind | 每个带权点相对其控制骨枢轴的位置 | Blend、SMD、VVD 权重与几何 |
| Animation basis | include 进来的动作族及 parent-local 动作 | 原生 animation MDL/ANI |
| Proportion corrective | 把动画 rest translation 接到角色 bind 的合同帧 delta | corrective/target SMD 与编译动画轨道 |
| Local pose sequences | `reference`、`CustomModel`、`ragdoll` 等本地一帧姿势的各自职责 | 原生/成功参考与 compiled sequence |
| Procedural motion | 头发、耳、尾、袖等二次运动 | VRM spring、`$jigglebone`、VRD 与编译规则 |

常见误诊来自跨层修复：看到双臂交叉就交换 L/R 动画；看到发根拉丝就降低阻尼；看到脚陷地就移动鞋网格。这些修改可能暂时改变截图，却不会修复真正的数据合同。

## 2. 两条 bind 路线必须二选一

### 2.1 Target-fit mesh：网格变换到目标 rest

目标 rest skeleton 已被成熟同角色参考证明，而且必须原样保留时，可把源网格逐 influence 转到目标 bind：

```text
v_target = sum_s w_s * B_target[m(s)] * inverse(B_source[s]) * v_source
```

适用前提：

- `m(s)` 的源/目标语义和父链可靠；
- 目标 rest 确实适合该角色几何；
- 多骨折叠、helper 分支和宽服装不会制造局部非刚性拉伸；
- Basis、所有 shape key 和法线使用同一变换合同。

公式成立不等于离散映射正确。必须比较所有三角边的变换前后长度、局部面积、法线和关键部位包围盒；若只有少量跨骨三角被放大数倍，应拒绝该映射，而不是提高全局阈值。

### 2.2 Source-fit skeleton：目标枢轴贴合源网格

若需要保留目标游戏的骨名、索引、父级和接口方向，但参考 rest translation 不适合用户几何，可以反过来让目标骨架贴合源 bind：

1. 保留目标 ABI 的骨名、顺序、父级和必须锁定的接口方向。
2. 为每个目标 deform bone 选择一个有证据的源代表骨。
3. 把目标 pivot 放到经过统一坐标/单位换算的源 bone head。
4. 对源模型没有的目标 helper，保留已验证的 parent-local offset 或按明确规则插值。
5. 网格、Basis、shape key 和 custom normal 只做同一个 global similarity。
6. 重命名、合并权重，最后一次性裁到引擎允许影响数并归一化；不做逐骨 LBS rest rebake。
7. 用 proportion delta 把原生动画 rest translation 接到新的角色 bind。

这条路线的关键不是“完全不变换”，而是**网格与目标 pivot 已在同一源 bind 空间**。如果再做一次 `B_target * inverse(B_source)`，会重复改变体型。

source-fit 报告应以完成统一 global similarity 后的源网格为 baseline，统计每个导出
corner 的额外逐骨 bind displacement。若大量角点非零，说明网格又被 target-fit；
这个 hard gate 只适用于选择 source-fit 的具体 runtime target。同一 Mod 的 world 和
viewmodel 可以分别选不同路线，但不能对同一份几何重复两条路线。

目标缺少源对应的 Spine/helper 时，不要默认平均插点。保留已验证 parent-local offset，
或用兼容参考的累计段长比例在源端点间插值，再由
`local = inverse(parent_world) * desired_world` 反求 local。近零段长也必须记录，不能
为了视觉上“均匀”擅自修改动画接口。

### 2.2.1 复合 bind basis 必须整体验收

保留游戏 ABI 的 name/index/parent，并不自动允许把任意参考的 rotation 与 avatar 的 pivot position 拼在一起。rotation、pivot 和 parent chain 共同定义 child local transform；每个来源单独“看起来正确”时，组合仍可能让 Forearm、Hand、Calf 或 Foot 离轴。

允许有证据地分开选择 rotation source 和 pivot source，但要把产物定义为新的 candidate，并至少验证：

- 每个 core bone 的 name/index/parent 覆盖、rotation/pivot 来源和输入 hash；
- world transform 对计划值的误差；
- 核心 child local translation 的轴向性，以及 parent-to-child rest segment；
- 关键骨的带权半径、seam 半径和左右 side sign；
- 完整代表动画下的关节弯曲、末端 reach 与骨段长度。

若这类门失败，先修 composite basis；不要把现象误判成 L/R swap，也不要先做全局权重平滑。Karin Y -> Witch 的四段手臂反例见 [双目标案例](19-karin-y-witch-case-study.md)。

rotation source 必须已经位于 Source/ValveBiped frame。raw Blender/VRM
`bone.matrix_local` 常使用不同的主轴和 roll 约定，不能直接写入 SMD/QC core rotation。
应显式转换 basis，或锁定同 slot、同动画族且已由运行证明的 Source custom reference；
后一种选择仍要对新 pivot 组合重跑 world/local/动画/几何门。

### 2.3 决策门

在两条路线之间选择时，至少生成两个隔离候选并比较：

- 源/输出拓扑边长度和 bounds；
- 每根核心 deform bone 的带权质心、最近表面和 seam 顶点到 pivot 的距离；
- 左右几何是否仍由同侧骨控制；
- 极端关节角下的三角绝对伸长和塌陷；
- 动画、attachment、hitbox、physics 需要重建的范围。

不要同时采用“把骨架贴源”和“把网格拉到参考 rest”，也不要因为某条路线理论上更完整就跳过几何门。

## 3. Source-fit 代表骨选择

### 3.1 代表选择不是最大权重竞赛

对于一对一身体骨，可优先直接语义映射。对于多对一折叠链，代表骨还决定目标 pivot，因此排序应考虑：

1. 控制语义是否匹配；
2. 是否为目标链的直接父子关系；
3. 若来自 spring chain，是否是首动态段；
4. 是否拥有真实正权重；
5. 稳定的源索引或显式 override；
6. 最后才考虑带权顶点数。

“带权顶点最多”常会选到长链中段或末端。该骨适合描述局部网格覆盖，不适合作整个折叠链的铰链。

### 3.2 Pivot 质量门

仅比较骨名和 parent 不够。对每个核心骨或折叠链记录：

- target pivot 与被选源 bone head 的误差；
- parent-to-child rest segment 长度；
- 带权质心到 pivot 的距离；
- anchor/dynamic 共权 seam 顶点到 pivot 的距离分布；
- 最远带权点半径；
- 左右 side sign 与对侧骨泄漏；
- 编译 MDL rest 是否在量化容差内保留上述 pivot。

带权质心只是快速信号。最终要定位到 seam 顶点和跨权重三角，因为少量根部三角足以形成明显长刺，而整体平均值可能仍正常。

## 4. Proportion 的正确所有权

设：

- `T(b)` 为角色目标 bind 的 parent-local transform；
- `C(b)` 为所选原生动画基准的 parent-local corrective transform；
- `g` 为单独测量的 Pelvis ground offset。

对于公共接口骨，常见 translation-only 合同为：

```text
T.position(b) = character_bind.position(b)
C.position(b) = native_animation_rest.position(b)
delta.position(b) = T.position(b) - C.position(b)
T.rotation(b) = C.rotation(b)
T.position(Pelvis).z += g
```

角色独有骨通常使用 `T == C`，使 proportion delta 为零。具体 `delta`/`predelta`、`hidden`、`post` 和 flags 必须来自当前 sequence contract。

注意事项：

- 所有值都是 parent-local，不是 global bone head。
- 不要把 `T.position` 改成 `normalize(C.position) * target_length`。源/动画 rest 方向不同会把姿势差混进比例差，并沿手臂、手指或腿链累积。
- corrective baseline 应尽量从锁定的 compiled native animation MDL 读取；反编译 SMD 可能有旋转、量化或旧版本差异。
- 不要直接做 Euler 分量相减。让 StudioMDL 执行 frame-0 subtract，再解码编译轨道。
- identity rotation 是常见 source-fit 设计，不是所有成熟参考的通用真理。若保留非 identity 静态 correction，必须明确列出骨和四元数来源。
- ground offset 只有一个 owner：proportion target 的 Pelvis local translation。不要同步移动 bind mesh、Foot/Toe、attachment、physics 或 bbox。

corrective 与 target 的 frame count 必须来自当前 sequence contract。常见 survivor
两者各一帧，但某些 infected 合同会把同一静态 target 重复多帧；这时必须逐帧覆盖并
确认每帧 transform 一致，不能由通用模板强制压成一帧。

`reference`、`CustomModel`、`ragdoll` 等本地 pose sequence 也属于动画合同。不能把
它们全部写成 proportion corrective 或 custom T Pose。分别锁定每条 sequence 的
position/rotation owner，从 compiled MDL 比较全部非 root core；root 若受 StudioMDL
animation basis 影响而排除，报告必须写明原因与覆盖数。

## 5. Light 模型：严格参考等价与 bind-relative 等价

light 模型经常包含独立本地序列。source-fit 改变 bind translation 后，候选与参考的绝对 local/global pose 不再相同是设计结果，不应自动判错。

同时输出两种结论：

### Strict reference equivalence

逐骨比较参考与候选的 compiled rest、原始 local 动画、proportion 后 effective local/global。它用于量化“与参考有何差异”。当角色 bind 有意不同，这一项可以诚实为 false。

### Relative-to-bind motion contract

检查：

- 目标骨名、索引、父级和 L/R 不变；
- 原始本地动画轨道在编译量化容差内保持；
- 候选 proportion 能重建候选自己的 bind；
- 动画相对各自 bind 的局部运动一致；
- 每条序列、每帧、每根选定骨都有完整覆盖。

发布门可以要求 relative contract 为 true，同时保留 strict=false 作为诊断。不得把前者改写成“与参考完全一致”，也不得因后者失败就交换左右骨。

## 6. 折叠 VRM spring chain 的正确方法

### 6.1 先识别 anchor 与首动态段

VRM spring root 可能从骨链第二根开始：第一根是随头/身体刚性运动的 anchor，下一根才是 `path_position=0` 的首动态段。折叠到较少 Source 控制时：

- 静态目标骨代表 anchor；
- 第一根 `$jigglebone` 必须代表 VRM path 0 的直接子骨；
- 后续源段可按有报告的分组折叠到一个或多个动态目标骨；
- 不能用路径末端、带权最多或“看起来最重要”的骨作首铰链。

### 6.2 `$jigglebone length` 不能修 pivot

Source `length` 描述 solver 从当前骨基点到模拟 tip 的长度/约束。它不会重定位骨的 bind origin。若 pivot 已位于链远端：

- 降低 angle 只能缩小错误半径上的扫掠；
- 提高 stiffness 或 damping 只能改变响应；
- 降低 mass 只能减小惯性；
- 根部 seam 仍绕错误铰链运动。

因此顺序必须是：**先修 bind pivot 和父链，再调 length/mass/stiffness/damping/angle。**

### 6.3 参数转换

VRM stiffness、drag、gravity、hit radius 和 collider 是作者意图证据，不应直接当 Source 单位。推荐：

1. 保存原 VRM group、root、path order、collider 和数值。
2. 按链类别建立有界 profile。
3. 记录单位换算、rank/map/clamp 和项目 override。
4. 对折叠长链降低根部自由度和惯性，但数值由当前网格半径与动作探针决定。
5. 若无法在骨预算内保留安全动态链，明确选择静态 fallback，优于在错误 pivot 上保留物理。

### 6.4 World/light 一致性

如果 world 和 light 复用同一几何、target 和 procedural 合同，应验证：

- 骨数和父链；
- ordinary/JiggleRule/QuatInterp 数；
- 每条 JiggleRule 的 flags、length、mass、三向 stiffness/damping 和 angle；
- QCI 规则顺序与编译 payload；
- world/light 全规则逐字段一致。

只比较规则数量会漏掉某一版本仍使用旧质量、角度或远端 pivot。

## 7. 用 CPU Skin 建立可重复回归门

HLMV 可能因工具、驱动、game root 或特定模型路径崩溃。此时可从 compiled MDL/VVD 和最终 SMD 建立离线前门，但必须明确它不是游戏实测。

### 7.1 核心探针

- 对手臂/手指：解码 light 代表帧，检查 L/R side、指骨段长度、带权半径、三角绝对边长和新增塌陷。
- 对 collapsed spring：围绕编译 pivot 施加 authored angle 的多轴正负旋转，检查 seam 三角和贴 anchor 顶点。
- 对关键骨：比较 bind 半径与 posed 半径，而不是只看最终截图。
- 对外部 include 动画：把 native MDL/ANI 的真实 frame、candidate compiled
  proportion 与层级 FK 合成；比较 wrist-vs-clavicle/hip-vs-foot 等相对向量和 Head
  quaternion，而不是只看 candidate 本地序列。

对于手臂、腿和其他关节链，还必须把**解剖运动学**与表面 LBS 分开记录：

- 相对各自 bind 的 elbow/knee bend delta，并与锁定动画控制组比较；
- shoulder/hip 到 hand/foot 的 reach 除以相应长骨链长度；
- reach 相对控制组的误差；
- UpperArm/Forearm、Thigh/Calf 等关键 segment 的长度漂移；
- parent mapping、权重和、bind reconstruction、有限性和样本覆盖。

edge stretch 只说明局部表面被拉多长，不能说明关节究竟有没有弯曲。一个臂链可以保持近似原长度却沿错误 basis 几乎伸直，画面仍会像多段折断。

手腕下倾角、Head quaternion 差等阈值必须由 compatible known-good、known-bad 和
当前动画全帧重新校准。它们是定向探针，不是跨角色常量；正负候选的差异应明显大于
编译量化误差。

### 7.2 指标选择

比率对接近零长度的微边非常敏感。报告应同时包含：

- bind 与 pose 的绝对边长；
- 绝对长度变化的 P99/P999/max；
- 排除或单独列出的微边 ratio；
- 带权顶点到 pivot 的 bind/pose 半径；
- 骨段长度比与有限性；
- 新增退化三角数量；
- 每侧、每帧和样本总覆盖数。

同时按对象和 bind-space 局部区域统计表面门。全对象 arm、主体皮肤、袖子/裙摆根部和关节带可能有不同可见风险；每个 scope 应明确两端顶点选择条件、样本数、edge 分位数、绝对变化和最坏 bind 长度。阈值必须由当前原生/成熟参考、已知坏候选和可见尺度校准，不能复制其他角色的数值。

不要通过放宽阈值让已知坏候选通过。阈值应由源几何、成熟参考、视觉可见尺度和已知坏/好候选共同确定。

### 7.3 正面与负面对照

一个新审计器至少证明两件事：

1. 修复候选通过；
2. 已知会在游戏中出错的旧候选失败，而且失败项指向同一数据层。

负面对照可防止“检查了错误字段”“阈值永远为真”或“报告只看文件存在”。release manifest 应锁定正面和负面报告哈希及预期结果。

## 8. 编译后二进制才是运行合同

Source SMD/QC 正确仍可能在 StudioMDL 中被裁骨、量化或重排。发布前至少解析：

- MDL 骨名、索引、父级、rest、flags 和 procedural type；
- compiled animation 的 translation/quaternion delta；
- VVD LOD 顶点数、最大权重数、骨索引与 fixup；
- VTX 每个 bodypart/model/mesh/strip-group 的 original ID 覆盖与越界；
- MDL/VVD/VTX/PHY 同轮 checksum；
- sequence、include、declare 顺序和 flags；
- attachment、hitbox、flex 和材质闭包。
- QC `$definebone` 对所有必须锁定的目标骨完整覆盖，数量与 target inventory 一致；
- compiled bind 与生成 target 的 name/index/parent/world transform roundtrip；
- 每条关键本地 pose sequence 的 position/rotation owner 和 frame count。

StudioMDL exit 0 和无 warning 不能替代这些检查。HLMV 能打开也不能证明游戏加载的是同一 VPK payload。

## 9. 症状到数据层的最短路径

| 症状 | 优先检查 | 不要先做 |
| --- | --- | --- |
| 手指放射状爆开 | 手/指 mesh-to-pivot 半径、proportion 逐轴 translation、权重侧别 | 交换手指名、删手指骨 |
| 双臂像左右互换 | L/R index/parent/local animation 后，检查 bind pivot | 直接交换左右动画 |
| 手臂像四段折断，edge 门正常 | composite bind rotation+pivot、child local-axis、bend delta、reach、segment drift，再查袖子 ancestor/局部拓扑 | 交换 L/R、放宽 stretch、全局 smooth |
| idle 横向张臂；改骨轴后头歪/下巴前伸 | compiled target-native proportion delta、本地 pose sequence 职责、world mesh bind displacement、真实 ANI 的 wrist/Head 探针 | 单独旋 Head、复制 raw DCC rotation、对 source-fit 网格做全身 LBS |
| 发根出现细条、整束远离头部 | anchor/dynamic 代表、path 0、父子段长度、seam 半径 | 只调 mass/damping |
| 脸侧短发摆幅过大 | collapsed chain 的角度、惯性、碰撞缺失 | 全局降低所有 jiggle angle |
| bind 正常但 light 动作异常 | relative-to-bind 动画、proportion 重建、light 本地序列 | 强求 reference global pose 相等 |
| physics hull 远离身体 | 是否预变换后又被 StudioMDL named-bone 转换 | 移动 hull 顶点补偿 |
| 仅一个 Bride/DLC variant 悬空 | canonical/proportion 坐标系、projected Pelvis/core/full/root delta parity | 移动鞋、Foot、mesh、PHY 或 `$illumposition` |
| HLMV 崩溃 | 先比较已知好/坏是否同样崩，再做 compiled CPU/binary gate | 把工具崩溃直接归因于模型 |

## 10. 修复与发布纪律

1. 运行时截图优先于“结构看起来合理”的推断。
2. 每轮只修改已确认的数据层，但从该层向下完整重建。
3. 使用新 candidate、compile sandbox、loose tree 和 release 版本；不覆盖上一版。
4. 对比新旧 payload，表外变化必须解释。例如物理/骨架修复不应改变 HUD 和基础材质。
5. VPK 每个 entry 与 accepted loose tree 做 bytes/SHA/CRC 比较。
6. manifest 记录输入锁、正负回归报告、VPK 身份和 `runtime_status`。
7. 离线通过时写 `pending_user_runtime_test`；收到用户反馈后单独记录候选 SHA、测试范围和未覆盖项。
8. 用户说“验收通过”可以升级该候选在实际测试范围内的证据等级，但不能自动推断每个武器、地图、FOV 和极端动作都已逐项覆盖。

## 11. 通用退出门

进入用户实机测试前，至少满足：

- 骨架策略被明确标记为 target-fit mesh 或 source-fit skeleton；不存在双重 bind 处理。
- 映射覆盖全部正权重源骨；collapsed chain 的 anchor/首动态代表有硬门。
- 核心带权质心、seam 半径、左右侧别和极端 pose 几何门通过。
- composite bind basis 的 rotation/pivot/parent 来源与关键 child local-axis 通过；全帧关节运动学和对象/局部 surface 门同时通过。
- proportion 逐轴 translation 与 rotation profile 从 compiled track 验证。
- proportion frame count 与 sequence contract 一致；关键本地 pose sequence 的 transform
  owner 已逐骨验证。
- 全骨 `$definebone` 与 compiled bind roundtrip 通过；source-fit target 的额外逐骨
  geometry displacement 为零或量化容差内。
- light strict diagnostic 与 relative hard gate 分开记录。
- world/light procedural payload 在预期相同时逐字段一致。
- 正候选通过，已知坏候选在同一审计器中失败。
- compiled MDL/VVD/VTX/PHY、VPK payload 和 manifest 闭合。
- 实机状态与实际证据范围一致。

## 12. Cloth04 Zoey 证据索引

下列数值是本案例证据，不可复制到新角色：

- 项目案例：[Karin Cloth04 -> Zoey](15-karin-cloth04-zoey-case-study.md)
- 用户验收：[Cloth04 Zoey v1.3 用户验收](evidence/karin-cloth04-zoey-v1.3-user-acceptance-2026-08-18.md)
- source-fit target：`L4d2/cloth04_replace_zoey/reports/rig/target-sourcefit-ponytail-v15.json`
- 旧/新根部 CPU skin：`reports/rig/ponytail-root-skinning-sourcefit-v14.json`、`ponytail-root-skinning-sourcefit-v15.json`
- compiled world/light physics：`reports/compile/compiled-ponytail-physics-sourcefit-v15.json`
- v1.2 负面对照：`reports/compile/compiled-ponytail-physics-v1.2-negative.json`
- light bind-relative 动画：`reports/compile/compiled-light-animation-equivalence-sourcefit-ponytail-v15.json`
- 最终发布：`reports/release/final-validation-ponytail-v15.json`

该案例的最终 accepted VPK 是 v1.3；旧 v1.0-v1.2 保留为反面证据。

## 13. Karin Y -> Witch 证据索引

下列内容只证明该双目标替换，不能把骨数、帧数、对象名、阈值或 VPK 身份复制到其他项目：

- 项目案例：[Karin Y -> Witch 双目标替换案例](19-karin-y-witch-case-study.md)
- 用户验收：[Karin Y -> Witch v0.3 用户验收](evidence/karin-y-witch-v0.3-user-acceptance-2026-08-18.md)
- composite bind / 权重 / 局部拓扑：`L4d2/Y_Replace_Witch/reports/build/model-build.json`
- 双变体 canonical/root/PHY：`L4d2/Y_Replace_Witch/reports/build/modelsrc-build.json`
- 全帧 pose：`L4d2/Y_Replace_Witch/reports/audit/pose-deformation.json`
- compiled/VTX：`L4d2/Y_Replace_Witch/reports/compiled/compiled-model-audit.json`
- HLMV 和 v0.2 假阴性说明：`L4d2/Y_Replace_Witch/reports/visual/hlmv-visual-validation.md`

v0.2 的用户游戏截图是可信反例，但当前没有独立锁定的 schema-v2 machine-readable negative report。后续项目应在审计器发布前锁定 bad-candidate 输入 hash、schema 和预期失败 check ID；不要把这一建议误写成当前 Witch 项目已经拥有的资产。

## 14. Karin Nyako -> Hunter 证据索引

下列内容证明本次 Hunter 替换，不代表其他特感应复制 53/85 骨、101 帧、角度或 VPK
条目数：

- 项目案例：[Karin Nyako -> Hunter](20-karin-nyako-hunter-case-study.md)
- 用户验收：[2026-08-18 用户验收](evidence/karin-nyako-hunter-user-acceptance-2026-08-18.md)
- bind/geometry：`L4d2/nyako_replace_hunter/reports/build/model-build.json`
- sequence/definebone：`L4d2/nyako_replace_hunter/reports/build/modelsrc-build.json`
- compiled proportion/local pose/VTX：`L4d2/nyako_replace_hunter/reports/compiled/compiled-model-audit.json`
- idle/head 正反诊断：`L4d2/nyako_replace_hunter/reports/idle-arm-head-sourcefit-fix-20260816.md`
- package：`L4d2/nyako_replace_hunter/reports/package/package-validation.json`

被否决 native-rotation + world-mesh LBS 候选只有归档 VPK、历史报告与用户截图链，
没有独立锁定 schema 的可重跑 machine-negative report。它是有效运行时反例，但不能
写成“当前审计器已拥有完整自动负控”。
