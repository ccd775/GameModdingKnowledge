# 端到端 SOP

本文给出一个可重复的角色替换流水线。每一步都必须有输入、产物、报告和退出门槛。项目实测数字不得直接复制到新角色。

## 阶段 0：建立项目状态

创建：

- `PROJECT_STATE.md`：当前阶段、最新通过项、阻塞项、下一命令；
- `source-lock.json`：输入与工具哈希；
- `reports/`：所有审计、验证、截图和候选清单；
- 隔离 `compile_sandbox`；
- 一个永不从通配符推断的候选命名规则。

退出门槛：新 agent 只读这些文件即可知道当前权威输入、当前候选和下一步。

## 阶段 1：确定目标接口

1. 读取游戏 `gameinfo.txt` 和实际挂载顺序。
2. 提取当前生效的原版 survivor 资源。
3. 审计 output slot 的世界路径、第一人称手臂、HUD、attachments、hitbox、flex 和 physics 接口。
4. 单独选择 primary animation family、proportion corrective baseline 和 sequence contract；不得从 output slot 自动推断。
5. 审计参考 Mod 的真实模型身份、动画来源、sequence flags 和版本。

退出门槛：分别形成 output slot、slot interface、character rest skeleton、primary animation、corrective baseline、sequence contract 和 ground owner 字段，并明确每项来源/hash。对本库管理的动漫风格/动漫比例 survivor，若没有另一套成熟参考、编译二进制和实机共同证明的合同，默认且强制选择 Zoey/TeenAngst；non-survivor 必须锁定当前目标槽位或同槽位成功参考的动画合同，禁止套用 survivor 默认。

## 阶段 2：只读审计用户源模型

1. 审计 Blend 场景、骨架、网格、材质、UV、权重和形态键。
2. 审计 VRM humanoid、spring、collider 与参数。
3. 审计贴图连接，区分 base、normal、emission、alpha。
4. 记录模型单位、对象矩阵、bounds 与关键点。

退出门槛：所有可见特征均有明确数据来源；高跟鞋等必要 shape key 的非零 delta 已定位。

## 阶段 3：确定骨架策略

1. 评估同角色成熟参考的 rest skeleton 与用户几何是否兼容，不把参考 pivot translation 自动视为最终 bind。
2. 建立显式 source-to-target bone map，每行记录目标、方法、置信度和理由。
3. 公共 ValveBiped 骨骼满足已选 primary animation family 的接口；它不必与 output slot 同名。
4. 保留有权重的附件、头发、裙摆、耳朵、尾巴和 procedural helper 骨。
5. 把超出引擎限制的权重裁到最多三影响，归一化并报告损失。
6. 明确二选一：target-fit mesh 使用逐骨 bind-space 候选；source-fit skeleton 保留 ABI/接口方向，把 pivot 贴合源网格并保持网格统一 similarity。
7. 用 weighted-centroid/pivot、seam 半径、全 edge/triangle stretch、左右 side sign 和极端姿态比较候选；禁止同时重复应用两种 bind 路线。
8. 将 core bone 的 name/index/parent、pivot、world rotation 和坐标来源写成一份 composite bind-basis contract；若 rotation 与 pivot 来自不同证据，锁定各自 hash，并验证 child local-axis、完整 world transform 与代表动作的关节运动学。
9. 对服装/袖子/helper 沿 source parent chain 映射到最近有效 deform ancestor；不要按对象名批量强制某根 UpperArm/Spine。减面计划单独保护肩、肘、腕和共权 seam 的局部拓扑，并报告区域 before/after 覆盖。
10. core rotation 必须已经位于 Source interface frame；raw Blender/VRM
    `bone.matrix_local` 需显式 basis conversion，或改用锁定的同 slot Source custom
    reference。源缺少的中间 helper 按已验证 offset/累计段长比例插值，再由 world matrix
    反求 local，不默认等分。
11. source-fit 目标以统一 similarity 后的源几何为 baseline，量化额外逐骨 bind
    displacement 并要求为零或容差内；target-fit 目标单独执行非零转换与 edge 门。

退出门槛：无未映射的有权重顶点、无缺失目标骨、无零权重顶点；辅助骨保留策略已冻结；bind 策略、composite basis、局部拓扑和几何拒绝门有结构化报告。

## 阶段 4：处理单位、形态键和角色外形

1. 在派生 Blend 中按 Source 单位缩放 armature data 和唯一 mesh data；保持对象矩阵 identity。
2. 对必须常驻的形态键先审计 delta，再烘焙到 Basis 和所有剩余相对形态。
3. 删除已烘焙的常驻 key，避免导出或运行时重复应用。
4. 保持原角色身体比例，不把网格强行压到 survivor 身体。

退出门槛：重新审计显示单位正确、常驻形态已进入 basis、其他 flex key 保留、脚在鞋内。

## 阶段 5：导出网格与表情

1. 用固定版本 Blender Source Tools 导出 reference SMD、mesh SMD 和 VTA。
2. 确认 SMD 材质名为稳定 ASCII，并与 VMT 计划一一对应。
3. 检查每顶点最大权重数、骨索引、三角形和 bounds。
4. 检查 VTA frame 0 与 SMD bounds 一致，frame 数和名称符合 flex 计划。
5. 如果 Blender 已写完 VTA 但导出过程卡住，可结构化解析并只缩放 position；禁止字符串替换坐标。

退出门槛：SMD/VTA 可被独立解析，且所有导出契约有报告。

## 阶段 6：比例校正与动画接口

1. 生成 corrective SMD：公共 Valve 骨使用**已选动画基准**的 parent-local translations；优先从锁定 compiled animation MDL 解码，反编译 SMD 只作交叉证据；corrective rotations 与自定义角色 rest rotations相同；自定义骨保持角色 bind。
2. 生成 proportion-target SMD：使用角色 bind；仅在有测量证据时调整 pelvis 地面偏移。
3. 在 QC 中用 frame-0 subtract 生成比例动画；`delta`/`predelta`、`post`、`hidden` 和 `autoplay` flags 从当前已验证 sequence contract 保真，不能跨项目照抄。
4. 原样保留锁定合同的 sequence 声明、include model 顺序和有意重复项；不能从 include sequence union 重建或去重。
5. 不单独移动鞋、脚骨、网格、IK、bbox 或 ragdoll 来补地面问题。
6. target translation 直接使用角色 parent-local rest，禁止用 native axis 归一化后只搬长度。
7. 对 light 本地序列分别生成 strict reference diagnostic 与 relative-to-bind motion hard gate。
8. 若同一可见角色覆盖多个 runtime variant，分别锁定每个 target 的原生 QC/collision/PHY，同时比较共享 canonical reference、projected Pelvis、core/full reference 和 root delta；ground offset 仍只有 proportion-target Pelvis 的一个 owner。
9. 从原生/成功参考枚举 `reference`、`CustomModel`、`ragdoll` 等本地 pose sequence，
   为每条记录 frame count、position owner 与 rotation owner；不得把名字不同的一帧资产
   全写成同一 custom/projected pose。
10. corrective/target 的 frame count 由 sequence contract 决定。`subtract` 引用帧必须
    存在；多帧静态 target 逐帧验证 transform 一致，不能套 survivor 一帧模板。

退出门槛：corrective path/hash 与 primary animation 匹配；corrective/target frame count、
本地 pose sequence 的 transform owner 与锁定合同一致；delta rotation 为预期 identity；
编译后 proportion sequence flags、include 顺序、declaration 数和重复项与锁定合同一致；
reference/rest 腿链未被压短；HLMV 或明确记录的替代门中 bind、idle、locomotion 都
保持角色比例并落地。

## 阶段 7：附件、procedural 与物理

1. 从 VRM 与成熟参考生成有界的 `$jigglebone` 配置；记录 spring root、path order、collider 和转换/clamp。
2. 保留 procedural helper 的权重和 VRD/规则，否则 StudioMDL 会裁掉骨。
3. 从原生 physics SMD 保留真正拥有 hull 顶点的骨及其必要祖先。
4. 不要在更换 physics skeleton 前先预变换顶点；StudioMDL 会做 named-bone bind conversion。
5. 在同一次 StudioMDL 编译中生成 MDL 与 PHY，验证 checksum、solid 和 convex。
6. 多 target 的 physics SMD 保持各自 native source-local hull；只裁未用 node/重映 index，不预变换顶点后再让 StudioMDL 做第二次 named-bone conversion。
7. 多段 spring 折叠时分离静态 anchor 和首动态段；动态代表必须是 VRM `path_position=0` 的 direct child，不能按最大带权顶点数选远端骨。
8. 先验证 parent/pivot/seam，再调 length、mass、stiffness、damping 和 angle；`jigglebone length` 不能重定位 bind pivot。
9. 用 authored angle 的多轴正负 CPU skin 检查 seam 边、根区位移和三角退化；同一审计器必须让修复候选通过、已知坏候选按预期失败。
10. world/light 共享 procedural 合同时，比较 QCI 和 compiled 全部规则的 flags、length、mass、三向 stiffness/damping 和 angle。
11. source-fit 改 pivot 后，分别审计 attachment/hitbox 的 local frame 与最终几何。
    parent rotation/frame 未变时允许 local 合同随 avatar pivot 移动；frame 或 parent 变化时
    从锁定 global reference 反算新 local。hitbox 保留 hitgroup，并只用 body/face 白名单
    验证覆盖，排除头发、袖子、尾巴和饰品。

退出门槛：目标骨数与辅助骨清单一致；collapsed chain 的 anchor/path-0/pivot 门通过；procedural 正负回归和 world/light parity 通过；PHY 无 checksum/bone 错误。若自定义 PHY 未证明可靠，明确回退到经过验证的原生方案。

## 阶段 8：构建材质

1. 将 base、normal、emission、alpha 按每个材质真实 UV 关系生成。
2. 限制 VTF 最大尺寸为当前 L4D2 VTEX 已验证值，生成 mipmap。
3. normal resize 后重新归一化；精确黑色无定义 normal 像素先改为 `(128,128,255)`。
4. 用 `invertgreen` 处理 Source DirectX normal 方向。
5. 每个外露材质以 `patch` include `survivors_it_shared.vmt`，本地不要再占用 `$detail`。
6. 普通表面使用低强度 SelfIllum；作者发光 mask 与低底光合成后仍走主 pass。
7. 避免在必须显示 bile 的衣物上使用 EmissiveBlend 额外 pass。
8. 连续透明与 alphatest 分开建模；统计最终 VTF alpha histogram，并证明实际 SMD UV 覆盖半透明区。
9. 未有实机合同的连续透明先使用最小 shared-bile profile：`$translucent 1`、`$phong 0`，不带 bump、其他 Phong family、SelfIllum 或本地 detail。
10. 删除 PC 包不需要的 `.pwl.vtf`，验证 VTF header flags。

退出门槛：SMD 材质、VMT、VTF 形成严格闭包；无陈旧额外 VMT/VTF；bile、夜光和透明均有明确实现及待实机项。

## 阶段 9：生成 QC 并编译

1. QC 只从结构化审计和模板生成，不手抄参考文件。
2. 明确保留 modelname、cdmaterials、bodygroups、attachments、hitboxes、bbox/cbox、surfaceprop、flex/eyes、procedural、LOD、include 和 sequence。
3. 用 L4D2 自带 StudioMDL，显式 `-game <compile_sandbox>`。
4. 保存完整 stdout/stderr；所有 warning 先失败后分类。
5. 独立审计编译 MDL/VVD/VTX/PHY 的版本、checksum、骨、动画、序列、材质和 include。
6. 以 compiled VVD LOD0 为准执行顶点预算：工程目标 `<=60,000`，拒绝 `>=65,535`。
7. 逐 bodypart/model/mesh/strip-group 审计 VTX original ID 的 mesh-local、model-local、VVD-global 范围和完整覆盖。
8. 多 runtime target 分别审计 companion checksum、VTX mapping、collision/physics 和 sequence/interface；共享可见 geometry 只比较计划共享的规范化数据，不要求不同 model family 的 MDL 原始字节相同。
9. 从最终 target SMD 为所有必须锁定的骨生成 `$definebone`。当前工具链的 raw SMD
   rotation `(rx,ry,rz)` radians 写入 QC 时按 `(ry,rz,rx)` degrees 排列；生成后必须
   从 compiled MDL 做 name/parent/world-transform roundtrip，不能只相信文本换序。
10. 解码 compiled proportion 的全部合同帧，验证
    `delta.position ~= target_bind.position - animation_bind.position` 与预期 rotation
    profile；逐条审计关键本地 pose sequence 的 transform owner。

退出门槛：编译输出与输入契约闭合，不存在未解释 warning；VTX 映射零越界、零缺失且覆盖完整。StudioMDL exit 0 与 companion checksum 一致不能替代该门禁。

## 阶段 10：HLMV 视觉验证

1. 编译一个唯一 preview alias，仅 `$modelname` 与正式 QC 不同。
2. 从隔离 game root 启动 HLMV，`-game` 与唯一 preview MDL 都使用绝对路径，避免同名原版或 cwd 相对路径被虚拟文件系统选中。
3. 对每个 runtime variant 在同一序列中覆盖开头、中间、结尾和高风险姿势；每个基础帧启用 Ground，至少一个中间诊断帧启用 Ground + Origin Axis + Bones。
4. 检查 bind/front/side、reference/rest 腿链、真实 idle 自然屈膝、行走/跑步、受伤、表情、眼睛、附件、hitbox、physics overlay、角色身高、鞋底和地面。
5. 保存带窗口标题、唯一 alias、sequence、frame 和控件状态的原始截图，再生成 contact sheet。自动化必须锁定目标窗口并回读 sequence/frame，避免多窗口串控。
6. 对 idle/高风险动作增加 compiled 动作探针：合成真实 include ANI + candidate
   proportion/FK，比较 wrist-vs-clavicle、elbow bend、reach、Head quaternion 与兼容
   known-good/known-bad；阈值按项目校准，不复制案例角度。

若锁定控制组与候选在同一 HLMV 模块/位置共同崩溃，记录 `unavailable_with_control_failure`，改用 compiled MDL 解码、CPU skin、骨段/pivot/边形变门和非空离线渲染。不得因 HLMV 不可用跳过实机状态。

退出门槛：没有缩头缩肩、躯干拉伸、脚穿鞋、脚陷地、附件爆炸或 physics 错位；表面 edge 门和全帧关节运动学门同时通过；HLMV 不可用时，独立替代门全部通过且限制已记录。

## 阶段 11：第一人称手臂与 HUD

1. 提取目标 survivor 固定 arms/HUD 路径。
2. 分别声明 `visible_geometry_source`、`geometry_selection_source`、`viewmodel_abi_source`、`slot_interface_source`、`weight_guidance_source` 和 `material_source`。
3. 在不可变源 Blend 上用 shape key、源骨权重和完整 edge component 生成 polygon-index manifest；只有源/派生 topology 合同完全一致时才映射 indices。
4. 删除 shape keys 前把当前 Basis 写回基础 mesh；优先从已验收 world SMD 按 manifest 精确抽取 triangle blocks。
5. 用有证据的 view-space placement 保持源 triangle shape。逐 influence bind conversion 必须通过全 edge stretch 门；失败时使用重新拟合的 global similarity，再只转移同角色参考权重。
6. 权重沿源 topology 平滑，最后一次性裁到最多三影响；验证同坐标一致、左右骨串、triangle-corner L1 与 helper 连续性。
7. 参考 arms 只允许提供 ABI、rest、bonemerge、idle/proportion 与权重指导。固定长度 token 替换、参考 VVD/VTX 搬运和参考材质闭包不得作为最终可见手臂方案。
8. 编译正式路径和唯一 HLMV alias；执行参考 companion 哈希、token、材质 namespace 和 release paths 负面门。
9. HUD VTF 保持所需 alpha 和原生 VMT 接口；很多替换只需要提供 VTF payload。

退出门槛：源几何血缘、viewmodel ABI、edge/权重连续性、compiled companion 和多角度 HLMV 均通过；仍将所有武器和特殊动作列为实机 smoke test。完整细节见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。

## 阶段 12：组装、VPK 与回滚

1. 组装到全新 loose tree，拒绝覆盖旧目录。
2. 只包含运行时后缀；扫描绝对路径泄漏、大小写重复和缺失文件。
3. 拒绝同步盘产生的 `*_冲突文件_*`、未引用副本和任何 manifest 外 extra；出现时换新候选目录重建，不在旧树上清理后继续发布。
4. 用游戏 `vpk.exe` 构建。
5. 从 VPK 读取每个 payload，与 loose tree 逐字节比较并记录 CRC/SHA-256。
6. 生成候选专属 manifest，包含 VPK 路径、大小、哈希、entry 数、动画合同和证据路径。
7. 与上一个候选按相对路径+SHA 比较，只允许预期文件变化。
8. 在假游戏根测试安装与卸载：备份被覆盖文件；卸载只删除哈希仍等于安装值的文件，并逐字节恢复备份。
9. 按 companion family 原子处理：world 通常为 MDL/VVD/VTX/PHY，light 为 MDL/VVD/VTX 且拒绝 stray PHY，arms 为独立 MDL/VVD/VTX。复用未改组件时生成本轮 hash reuse attestation。
10. 在候选 VPK 和正式 release VPK 两层分别做 entry 集合、bytes、CRC 和 SHA 比较；相同 entry 数和总大小不能证明是同一候选。
11. final manifest 锁定正面回归与已知坏候选的负面对照，并锁预期变化 allowlist 与未变化闭包。
12. 打包前重新哈希已接受的 compiled/pose/材料审计输入；explicit allowlist 拒绝 preview alias、compile-only animation、QC/SMD、DX80/SW、参考资产和任何 stale extra。

退出门槛：VPK payload 完整一致，候选清单唯一，安装/回滚可重复。

## 阶段 13：实机反馈闭环

记录：

- 游戏版本、地图、角色、第三/第一人称、光照条件；
- 测试动作、武器、感染状态和复现步骤；
- 角色总体身高、reference/rest 腿链、idle authored 屈膝和鞋底接地分别记录，不能合成一个“姿势正常”；
- 连续透明、alpha-test、Boomer bile 与微光分别记录，静态 alpha 不能替代视觉结论；
- 原始截图/录像；
- 观察、推断、被排除原因和下一修复；
- 对应候选 SHA-256。
- acceptance scope 与明确未声称覆盖的场景。

实机失败后只修改最小 source-of-truth，并重新执行受影响的下游阶段。不要无理由重做骨架、材质和打包全链路。

若实机推翻了离线门，保留旧候选、截图和失败说明，明确指出遗漏的数据层，再给审计器补齐覆盖。不要把旧报告改写成“从未通过”，也不要声称有机器负控，除非其输入 hash、schema 和预期失败 check 已实际归档。

发布 manifest 是打包时快照，收到用户反馈后不要原地改写。新增 append-only runtime evidence sidecar，以 VPK SHA-256 绑定日期、用户原话/摘要、测试范围和未覆盖项，再让 `PROJECT_STATE.md` 指向该证据。

## 最终交付条件

- 可部署 VPK 与 SHA-256；
- 候选 manifest；
- 静态验证报告；
- HLMV 预览证据，或控制组共同失败时的 unavailable 记录与 compiled decode/CPU skin/非空渲染替代证据；
- 已知未完成的实机项；
- 安装与回滚说明；
- 更新后的 `PROJECT_STATE.md` 和排障记录。
