# HD2 Mod 发布检查表

## Provenance

- [ ] 源模型、用户指定参考的精确目录/Blend/triplet/源角色、donor、工具和脚本哈希已锁定。
- [ ] 当前 authoring/visible/final triplet 的路径与哈希已写入 SOP。
- [ ] 所有 binding reports 路径、schema、哈希匹配且 `accepted: true`。
- [ ] 输入 before/after 哈希不变。

## Authoring

- [ ] 角色比例符合源角色和用户要求。
- [ ] object transform/mesh-local 坐标合同正确。
- [ ] 保存中的非零 shape-key map 已记录；current mix 在法线/分件/retarget 前烘焙，topology、UV、weights、材质槽和 face ownership 不变。
- [ ] 无未加权点；权重归一；influences 不超限。
- [ ] local `0_N` palette 映射逐 Unit 验证。
- [ ] 允许变化域与冻结域差分通过。

## Deformation

- [ ] 标准全身姿态全部通过。
- [ ] 本次骨 A/B 迁移的差分姿势通过。
- [ ] 肩部 source/target 语义基数、game-space 分件、声明的闭环/开放权威 seam、完整权重行、carrier roll/minimal closure、signed chain-axis、full-3D mirror、fore/aft 与腋下装饰走向通过；endpoint closure 未被当作单独充分条件。
- [ ] 肩、腰、髋腿每条 seam 在 post edit 前的自然 final-lineage 权重误差已记录；所有 post edit 逐接口证明，未用 blanket override 或固定过渡圈掩盖 owner/palette 错误。
- [ ] 差分姿态声明 moving/excluded bones 与实际 coverage；同时检查固定 seam gap 和肢体内部邻接 edge ratio。
- [ ] 肘部 shortest-arc/roll 与 LowerArm/Hand linear/pivot 连续性通过。
- [ ] 腿脚完整链 signed axis、closure、mirror、Foot/Ball continuity 与鞋面包覆通过。
- [ ] 颈、腰、髋等 seam 通过；若 ownership 图为 torso -> hip -> leg，direct torso/leg bypass 为 0。
- [ ] 手指、袖口、腰带、短裤、小附件按连通片通过。
- [ ] 原版/自定义可组合装备接口通过离线合同。

## Compiled Unit

- [ ] visible target/donor FileID 清单完整。
- [ ] TransformInfo/BoneInfo/MeshInfo/inverse-bind provenance 正确。
- [ ] carrier-clone 路线中每角色只编译一次，carrier 输入哈希锁定，header/TransformInfo/BoneInfo/MeshInfo/inverse-bind/culling 同源且保持，每 LOD 使用 owner 实际索引，同角色完整 Unit payload 逐字节相同。
- [ ] RawMesh、weights、LOD、Slim/Stocky 与 authoring 对应。
- [ ] material section start/count 逐 LOD 正确。
- [ ] suppression/hidden Unit 覆盖完整；正 render LOD 使用已证明的微型/zero-draw 几何而非透明玻璃，culling LOD 独立冻结。
- [ ] 可见/suppression target 互斥；head package 只归实际 Helmet 消费者，所有源面恰好出现一次。
- [ ] 编译后专项审计通过。

## Materials

- [ ] UV0/UV1/UV2 语义已验证。
- [ ] BaseColor sRGB、数据纹理线性格式正确。
- [ ] 每张源贴图由实际材质 binding、UV ROI 与文件哈希证明；未绑定的邻近 normal/control 未被误用。
- [ ] 稀疏 alpha BC7 已使用/评估 `-sepalpha`。
- [ ] AlphaClip/opaque 选择基于实际 alpha 分布。
- [ ] emission 与遮罩联合审计通过。
- [ ] 所有本地 child Material/TextureMap 已私有化。
- [ ] full-ID/high32-ID 冲突为 0。
- [ ] 所有不同私有 TextureMap 的 aggregate base-level 面积与语义小计均报告，严格总预算通过。
- [ ] model/material/texture 引用闭包完整。

## Integration And Package

- [ ] 所有 AQ 写/roundtrip 任务串行执行。
- [ ] 最终资源类型和数量与 manifest 完全一致。
- [ ] GPU/stream 区间有效、无重叠。
- [ ] 最终 archive roundtrip 通过。
- [ ] ZIP 恰好三成员、stored、固定顺序/时间戳。
- [ ] CRC、成员大小和 SHA-256 通过。
- [ ] 第二次隔离构建与正式 ZIP 逐字节一致。
- [ ] `Output/` 无被拒绝/旧候选。

## Deployment

- [ ] 用户明确授权部署。
- [ ] 用户是否授权启动 Steam/游戏已单独记录。
- [ ] 游戏未运行。
- [ ] game data 路径严格匹配。
- [ ] 部署模式已冻结：新槽要求 index 未占用且不覆盖；精确旧版替换要求 live 三件套哈希完全匹配、只排除该 triplet 做碰撞扫描、旧新版不共存。
- [ ] 精确三件套部署后哈希匹配。
- [ ] 部署报告与精确回滚路径已生成。

## Runtime

- [ ] 截图/录像绑定已部署 triplet 哈希。
- [ ] 军械库与任务内通过。
- [ ] Slim/Stocky 通过。
- [ ] 近中远 LOD 通过。
- [ ] 待机、敬礼、跑动、踏步、蹲伏、举臂、双侧 hand-to-head、瞄准、手指动作通过。
- [ ] 原生装备没有透明/玻璃叠层，脚趾没有穿出鞋面，左右脚在交替步态中不交叉。
- [ ] 原版和其他自定义可组合装备通过。
- [ ] 正面、背面、侧面、三分之四通过。
- [ ] 声明支持的 dirt/blood/gunk/acid 状态通过。
- [ ] 未验证功能已列入 known limits。
- [ ] 若由用户手动验收，记录精确候选/package 与接受范围；未观察部署、未提供矩阵和未自动化测试不被虚构为已完成。

## Final Status

- [ ] 状态词精确，没有把离线通过写成运行时通过。
- [ ] 用户拒绝的候选已隔离为 `do_not_use`。
- [ ] SOP、交接摘要和公共知识更新完成。
