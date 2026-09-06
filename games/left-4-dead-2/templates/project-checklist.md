# L4D2 角色替换项目检查表

将本模板复制到新项目并填写。方括号中的数字必须由项目审计生成，不得沿用案例。

## 输入与工具

- [ ] Blend/VRM/FBX/贴图/参考 VPK 已记录路径、大小和 SHA-256
- [ ] 游戏 build ID 与挂载顺序已记录
- [ ] Blender、插件、SourceIO、Crowbar、StudioMDL、VTEX、VPK 工具已锁版本与哈希
- [ ] source-lock required roles 完整；跨项目借用的库/插件/正式 gate 脚本没有漏锁
- [ ] 原始输入保持只读，派生 Blend 有独立名称
- [ ] 隔离 compile game root 已创建

## 目标接口

- [ ] output/replacement slot 与世界模型目标路径已验证
- [ ] 第一人称手臂目标路径已验证
- [ ] HUD lobby/panel/incap 路径已验证
- [ ] 原生骨、attachments、hitboxes、bbox/cbox、surfaceprop 已审计
- [ ] slot interface source 与 SHA-256 已记录
- [ ] flex/eye/physics/LOD 契约已保存
- [ ] 若覆盖多个 runtime variant：每个 target 的 QC/collision/PHY 来源独立锁定；共享可见 bind 的 canonical、projected Pelvis/core/full reference 与 root delta equality 已定义

## 源模型

- [ ] scene/unit/object/data matrices 已审计
- [ ] mesh、material slot、UV 和 texture connection 已审计
- [ ] 所有 shape key 的实际 delta 已计算
- [ ] VRM spring/collider/humanoid 已审计
- [ ] 缺失资源和 packed data 已处理

## 骨架与几何

- [ ] 显式 source-to-target bone map 已冻结
- [ ] bind 策略明确为 target-fit mesh 或 source-fit skeleton；未重复应用两种 rest 变换
- [ ] source-fit 目标已量化 similarity baseline 后的逐 corner bind displacement 并为零/容差内；target-fit 目标另行记录转换与 edge 门
- [ ] core bind basis 的 name/index/parent、pivot、world rotation、坐标来源与输入 hash 已分别锁定；组合后的 world transform 已审计
- [ ] raw DCC bone frame 未直接冒充 ValveBiped rotation；中间 helper 的 offset/累计段长比例有锁定来源
- [ ] 关键 child local-axis/off-axis、带权点到 pivot 半径和 parent-to-child segment 已通过项目门
- [ ] 核心 weighted-centroid/pivot、seam 半径、全 edge/triangle stretch 与左右 side sign 已比较
- [ ] 服装/helper 权重按有证据的 source deform ancestor 映射；未按对象名批量强压不相干骨
- [ ] 肩/肘/腕等高形变区域的减面前后拓扑、局部权重连续性、同侧/对侧泄漏和样本覆盖已审计
- [ ] 普通骨与 procedural/helper 骨保留理由已记录
- [ ] 每顶点最多三影响，权重损失已报告
- [ ] 无零权重顶点、无缺失骨引用
- [ ] Source 单位已作用于 armature data 和唯一 mesh data
- [ ] 对象矩阵保持 identity
- [ ] 必须常驻的 shape key 已烘焙到 Basis 和剩余相对 key
- [ ] 脚在鞋内，鞋底基准已测量

## 动画与表情

- [ ] output slot、character rest skeleton、primary animation family、corrective baseline、sequence contract 已分别记录
- [ ] 动漫风格 survivor 默认使用 Zoey/TeenAngst；non-survivor 使用当前槽位/同槽位已验证动画合同；任何例外有成熟参考、编译二进制和实机证据
- [ ] corrective source 路径与 SHA-256 匹配 primary animation family，不是从 output slot 推断
- [ ] corrective/target proportion 的 frame count 来自锁定 sequence contract；subtract 所引帧存在，静态重复帧逐帧一致，父链与语义正确
- [ ] common-bone corrective translations 来自动画基准；target translations 来自自定义 rest
- [ ] corrective 优先来自锁定 compiled native animation rest；未使用 normalize-axis/length-only target translation
- [ ] corrective/target rotations 相同，编译 delta rotations 符合预期 identity
- [ ] pelvis ground offset 有测量证据且唯一 owner 为 proportion-target Pelvis local Z
- [ ] 完整代表动画已执行关节运动学审计：elbow/knee bend delta、末端 reach/链长、关键骨段长度漂移、finite 与样本覆盖
- [ ] surface edge 门按全对象、主体与局部高风险区域分别统计；不以全局 edge 统计替代关节运动学
- [ ] 已知坏候选存在时，其输入 hash/schema/预期失败 check ID 已锁；若没有机读负控，缺口已如实记录
- [ ] sequence 声明行数、unique 数、有意重复项和有序列表均匹配锁定合同
- [ ] include model 路径、大小写和顺序匹配锁定合同
- [ ] reference/proportions tail indices、flags 与 hidden/delta/predelta/post 语义匹配锁定合同
- [ ] `reference`/`CustomModel`/`ragdoll` 等关键本地 pose sequence 的 frame count、position owner、rotation owner 已逐骨审计
- [ ] Calf/Foot/Toe parent-local 链长未被 corrective 压短；reference 腿链与 authored idle 屈膝分开审计
- [ ] 真实 include ANI + proportion/FK 的 wrist/head 或等价定向探针与 compatible 正负对照一致
- [ ] VTA frame 0 与 SMD 匹配
- [ ] flex controller/rule 闭合
- [ ] light strict reference diagnostic 与 relative-to-bind motion hard gate 分开记录；覆盖序列/帧/骨完整

## 物理与附件

- [ ] source-fit 后 attachment 的 parent/local matrix 与最终表面距离通过；未强行保持 stock world 点
- [ ] hitbox 保留 hitgroup，并用 body/face 白名单验证覆盖；头发、袖子、尾巴、饰品未主导拟合
- [ ] VRM 到 `$jigglebone` 的参数假设和 clamp 已记录
- [ ] collapsed spring 的静态 anchor、VRM path-0 首动态 direct child 和 parent-to-child segment 已锁定
- [ ] 先验证 pivot/weights/axis，再调 length/mass/stiffness/damping/angle；未用参数掩盖错误 pivot
- [ ] procedural CPU skin 的 seam 边、根区位移和退化门通过；已知坏候选按预期 check ID 失败
- [ ] world/light 共享 procedural payload 的完整规则逐字段一致
- [ ] 最终辅助骨清单与编译结果一致
- [ ] physics hull 骨与必要祖先已验证
- [ ] 未发生 physics 双重 bind 变换
- [ ] 多 variant 的 physics 维持各自 source-local hull，只 trim/remap，不通过平移/预变换补 root/ground
- [ ] MDL/PHY checksum、solid、convex 和骨引用通过
- [ ] HLMV 静止与动画 physics overlay 通过

## 材质

- [ ] SMD material -> VMT 一一对应
- [ ] VMT/VTF actual 集合严格等于 expected 集合
- [ ] 所有外露材质 include `survivors_it_shared.vmt`
- [ ] 本地没有覆盖 `$detail`
- [ ] normal 黑区中性化、resize 后归一化、green 方向正确
- [ ] VTF 尺寸、格式、mip、sRGB/normal flags 通过
- [ ] 普通微光与作者发光分层明确
- [ ] 必须显示 bile 的表面不使用会覆盖它的额外发光 pass
- [ ] translucent 组合只使用已证明方案
- [ ] 最终 VTF alpha histogram 符合用途，实际 SMD UV 覆盖期望透明区
- [ ] `$alphatest`/`$translucent`/`$additive` 互斥
- [ ] 未实机证明的连续透明 profile 不含 bump、Phong family、SelfIllum 或本地 `$detail`
- [ ] `.pwl.vtf` 与陈旧材质未打包

## QC、编译与 HLMV

- [ ] QC 由项目 source-of-truth 生成
- [ ] 全部必需目标骨都有 `$definebone`，SMD->QC rotation 换序经原生控制组确认，compiled bind roundtrip 通过
- [ ] StudioMDL 来自目标 L4D2 安装，`-game` 指向沙盒
- [ ] 所有 warning 已分类
- [ ] MDL/VVD/VTX/PHY checksum 与版本正确
- [ ] compiled world VVD LOD0 `<= 60,000`，且未触及 `>=65,535` 拒绝线
- [ ] VTX original ID 在 mesh/model/VVD 范围内，每个 model 顶点零缺失、完整覆盖
- [ ] 编译后骨、序列、材质、附件、hitbox、flex、include 契约通过
- [ ] 多 runtime target 的 companion checksum、VTX mapping 与 physics/interface 分别闭合；共享数据的 cross-target parity 已通过
- [ ] 唯一 preview alias 证明加载的是本项目模型
- [ ] preview QC 与正式 QC 的规范化差异仅为 `$modelname`；preview/compile-only animation/DX80/SW/QC/SMD/reference 已从 release denylist 验证排除
- [ ] bind/front/side/idle/walk/run/crouch/injured/flex/physics/LOD 预览通过
- [ ] 每个 runtime variant 都覆盖同一代表 sequence 的开头/中间/末尾和高风险姿势；Ground 已启用，至少一个诊断帧记录 Ground + Origin Axis + Bones
- [ ] HLMV 自动化/手工记录已回读唯一窗口、sequence、frame 和控件状态，不只依赖截图文件名
- [ ] 若 HLMV 与控制组共同失败，已记录 unavailable 原因，并用 compiled decode/CPU skin/非空渲染替代；runtime 未被误写为 pass

## 手臂、HUD 与发布

- [ ] `visible_geometry_source`、`geometry_selection_source`、`viewmodel_abi_source`、`slot_interface_source`、`weight_guidance_source`、`material_source` 已分别记录
- [ ] source arm polygon manifest 锁定源 SHA、选面规则、indices、材质和三角闭包
- [ ] source/派生对象的 vertex/edge/polygon 顺序与 topology hash 已证明一致；不一致时未使用坐标近邻回退
- [ ] 删除 shape keys 前已 snapshot/clear/write-back 当前 Basis，或从已验收 world SMD 精确抽取
- [ ] view-space placement 的 triangle-edge ratio 通过，无局部非均匀 stretch
- [ ] 权重同坐标一致、左右骨串零泄漏、triangle-corner L1 接近已验收参考；top-3 只在最终写出前执行
- [ ] arms nodes/rest/definebone/bonemerge/idle/proportion ABI 通过，world-only helper 未混入
- [ ] 正式 MDL/VVD/VTX 与参考旧哈希不同，且旧 token/材质 namespace/release paths 负面门通过
- [ ] 唯一 HLMV alias 的正面、斜面、掌心、腕口、肩口、袖套和腕饰预览通过
- [ ] HUD alpha/尺寸/方向预览通过
- [ ] 新 loose tree 拒绝覆盖旧候选
- [ ] 无 missing/extra/case duplicate/absolute path leak
- [ ] 无同步盘 `*_冲突文件_*` 或 manifest 外副本
- [ ] VPK 每个 payload 与 loose tree 逐字节一致
- [ ] candidate VPK 与正式 release VPK 均执行 entry 集合、bytes、CRC、SHA 验证
- [ ] world/light/arms companion family 原子闭合；复用组件有本轮 hash reuse attestation
- [ ] 与上一候选只有预期路径变化
- [ ] 正候选通过、锁定坏候选按预期失败；negative-control 输入 hash/schema/check ID 已记录
- [ ] manifest 指向唯一当前 VPK 及其 SHA-256
- [ ] 运行时 VPK 使用唯一短 ASCII stem，并记录字符数与编码后字节数
- [ ] fake game root 安装/回滚 roundtrip 通过

## 实机

- [ ] `show_addon_load_order` / `show_addon_metadata` 或等价强证据证明候选实际挂载
- [ ] 世界角色替换与第一人称手臂分别确认，不把“原版角色”误诊为模型数据错误
- [ ] 长枪、手枪/双枪、近战、医疗/药品、投掷物、携带物第一人称手臂
- [ ] 射击、换弹、推击、倒地/特殊 viewmodel 动作
- [ ] 左右腕口、掌心、手指、肩口、袖子/腕饰与武器穿插；不同 FOV/分辨率
- [ ] 地图载入稳定，无确定性 studiorender/datacache 崩溃
- [ ] idle/walk/run/crouch/jump/injured/incap
- [ ] 表情、眼睛、嘴、附件二次运动
- [ ] 角色总体身高与同类基线合理
- [ ] reference/rest 腿链无额外压缩
- [ ] idle/aim 的自然屈膝符合已选动画族，不与 corrective 错误混淆
- [ ] 鞋底在 bind/idle/walk/run/crouch 中与地面接触
- [ ] Boomer bile 覆盖所有外露材质
- [ ] 微光、作者发光、透明在多种光照下表现
- [ ] ragdoll、受击、血迹、燃烧、LOD
- [ ] 截图/录像、复现步骤和候选 SHA-256 已归档
- [ ] 验收范围与明确未声称覆盖的动作/地图/FOV/材质项已记录

## 交付

- [ ] VPK 路径、大小、SHA-256 已提供
- [ ] 已说明相对上一版的变更
- [ ] 静态/HLMV/实机状态分别说明
- [ ] 发布 manifest 保持不可变；发布后反馈写入按 VPK SHA 绑定的 append-only runtime evidence sidecar
- [ ] 已知限制和待复测项明确
- [ ] `PROJECT_STATE.md`、排障记录和知识库已更新
