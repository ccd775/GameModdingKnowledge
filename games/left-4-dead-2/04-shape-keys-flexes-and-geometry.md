# 形态键、表情与几何处理

第一人称裁剪网格在删除全部 shape keys 前还存在一个独立的 Basis 保存合同：必须快照当前 `Basis` 坐标、clear keys、再写回基础 mesh，否则派生比例/姿态可能静默丢失。完整故障与黄金 world-SMD 抽取方案见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。

## 1. 先审计实际 delta

不要用 shape key 名称推断它是否有效。对每个 mesh、每个 key 输出：

- 名称；
- relative key；
- 非零 delta 顶点数；
- 最大位移和包围盒变化；
- 当前 value、slider range；
- 是否参与预期 flex 或必须常驻的体型修正。

同名 key 可能存在于多个 mesh，但只有一个包含实际位移。Karin 的 `Foot_HighHeel` 在多个 mesh 上存在，真正改变脚部的只有一个身体网格。仅看到名称而未检查 delta 会导致漏烘焙。

## 2. 常驻形态键的正确烘焙

高跟鞋脚型、固定体型或必须永远启用的修正应烘焙到几何，而不是只设置 `value = 1` 后期待导出器求值。

对相对 shape key，安全流程是：

1. 在派生 Blend 中确认目标 key 的非零 delta。
2. 将该 delta 加入 Basis。
3. 将相同 delta 正确传播到所有需要保留的相对 key，使它们仍相对于新 Basis 表达原效果。
4. 删除已烘焙的常驻 key，避免再次应用。
5. 重审计所有剩余 key 的数量、名称、relative key 和 delta。
6. 在导出 SMD/VTA 后检查脚、鞋、表情和 frame 0。

为什么不能只改 Basis：剩余表情或身体 key 仍可能以旧 Basis 为参照，造成双重位移或抵消。为什么不能只设 value：导出器、modifier 顺序或相对 key 求值可能不按视图结果写入 SMD。

## 3. 高跟鞋专项检查

高跟鞋模型至少检查：

- 脚趾、脚背、脚跟是否完全在鞋内；
- Basis、所有 flex key 和极端表情下是否仍在鞋内；
- 左右脚 key 是否对称或有意不对称；
- 鞋底最低点与角色地面基准；
- foot/toe 骨位置是否来自角色 bind，而非为遮穿模随意移动；
- idle、走、跑、蹲、倒地时是否穿鞋。

脚露出鞋子与脚陷地是两个不同问题。前者通常是形态键/几何；后者通常是比例序列或 pelvis 地面偏移。不要用移动整个脚网格同时掩盖两者。

## 4. 表情与 VTA

目标 survivor 的 flex 接口来自原生模型契约，自定义角色的表情形态来自源模型。需要建立显式映射：

- 源 shape key -> VTA frame；
- VTA frame -> flexdesc / flexcontroller / flexrule；
- 未支持的源 key 和原因；
- 原生必须存在但源模型没有的 controller 如何降级。

验证：

- frame 0 与 reference SMD 几何一致；
- frame 数、名称和顶点索引稳定；
- normals 未被位置缩放破坏；
- 编译后 flex controller 数和名称符合计划；
- HLMV 中逐个控制器检查眼睑、嘴角、张嘴和极端组合。

## 5. VTA 结构化重缩放

如果 Blender Source Tools 在完成 VTA 写入后卡住，而文件结构完整，可以用解析器重缩放：

1. 解析 header、节点、skeleton、vertexanimation frame 和每行顶点记录。
2. 只缩放 position 三元组。
3. 保持 vertex index、normal、frame time、frame 名和顺序不变。
4. 输出到新文件。
5. 重新解析并比较非 position 字段逐项相等。
6. 比较 frame 0 bounds 与 SMD bounds。

禁止使用正则或字符串替换所有浮点数，因为这会连 normals、时间或索引附近的数据一起改变。

## 6. 网格与材质槽稳定性

- 最终材质名使用稳定 ASCII，避免 StudioMDL、VPK 和大小写处理差异。
- SMD 中每个材质槽必须有且只有一个 VMT。
- 合并网格或 atlas 后重新检查 alpha 排序、双面需求、法线接缝和 UV island bleed。
- 去掉完全不可见、未绑定或未被任何 bodygroup 使用的几何，但记录删除依据。
- 任何破坏性 UV/atlas 操作都只在派生文件中进行，并保存映射报告。

## 7. Bounds 与最低点

至少在以下阶段记录 bounds 和最低点：

- 原始 Blend；
- 常驻 shape key 烘焙后；
- Source 单位转换后；
- SMD/VTA 导出后；
- 编译 MDL 重新导入后。

若某阶段出现突变，可以定位是 shape key、单位、导出器还是编译器导致，而不必凭 HLMV 截图猜测。

## 8. 编译后世界顶点预算与 VTX 映射

Blender/SMD 顶点数不是 Source 运行时顶点数。材质、法线、UV、strip 和 bodypart 拆分会增加 compiled VVD vertices。L4D2 的旧 StudioMDL/optimizer 在世界模型聚合顶点越过 16-bit 安全域后可能返回成功，却生成越界 VTX。

公共工程门禁：

- 以编译后的 VVD LOD0 为准，目标 `<= 60,000`；拒绝 `>= 65,535`。
- 逐 bodypart/model/mesh/strip-group 解析 `original_mesh_vertex_index`。
- 要求 raw index 在 mesh 内，`mesh.vertex_index_start + raw` 在 model 内，最终 global index 在 VVD 内。
- 每个 model 的合法映射集合完整覆盖它的全部顶点。
- MDL/VVD/VTX（以及 PHY）来自同轮候选，checksum 一致。

StudioMDL exit 0、无 warning、最大三权重和 companion checksum 一致，都不能代替 mapping audit。Riptide 153,854-vertex 候选就是确定性加载崩溃反例，见 [Riptide Louis 案例](16-riptide-louis-case-study.md)。

## 9. Bind pivot 与蒙皮几何门

骨名、父级和权重和为 1 仍不能证明网格围绕正确旋转中心。对手、指、发根、袖口等高风险区域记录：

- 每根 deform bone 的带权质心/最近表面/最远点到 pivot 的距离；
- anchor/dynamic 或相邻关节的共权 seam 顶点与跨权重三角；
- 左右 side sign 和对侧骨串泄漏；
- bind/pose 三角绝对边长、绝对变化 P99/P999/max；
- 带权点到 pivot 的 bind/pose 半径和骨段长度；
- 新增退化/塌陷面。

近零微边会让长度比率失真，不能只按最大 ratio 放行/拒绝。比率、绝对边长、绝对变化和可见尺度应一起报告。对错误 pivot 的角色，平均权重统计可能正常，少量 seam 面仍会在动画中形成长刺。

source-fit/no-LBS 候选应证明统一 similarity 下 topology edge 不发生局部非均匀变化；target-fit/LBS 候选则必须证明逐骨变换后的全拓扑 stretch 可接受。完整策略见 [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md)。

### 关节区拓扑与局部蒙皮门

全局 triangle/edge 统计不足以保护关节和服装。对肩、肘、腕、髋、膝、裙摆/袖口根部等高形变区域，单独记录：

- bind-space 选择规则、对象名和样本覆盖；
- 三角/唯一顶点的减面前后数量与保留率；
- 同侧/对侧骨影响、主导骨分布和跨权重连续性；
- pose edge 的分位数、绝对变化与最坏边的 bind 长度；
- 只在该区域内生效的平滑或权重修复，以及未修改 influence 的保留证明。

减面保护不能把整片衣物永久锁死，也不能只靠总面数通过。局部保护应允许项目在顶点预算内保留关节带的必要拓扑，并在导出后删除临时 vertex group/诊断数据。对象/区域名称和数值阈值必须来自当前角色审计；Witch 的袖子反例见 [Karin Y -> Witch 双目标替换案例](19-karin-y-witch-case-study.md)。

## 10. Karin 案例数据

以下仅用于说明审计粒度：

- `Foot_HighHeel` 实际改变 1,886 个顶点；
- 最大位移约 `0.0305431835 m`；
- 烘焙后保留 59 个其他 shape key；
- 最终表情导出包含 base + 30 个 flex frame。

这些数字不是新项目的验收阈值。新角色必须从自己的 delta 审计得出。

## 11. 失败模式

| 现象 | 常见原因 | 正确处理 |
| --- | --- | --- |
| 脚从鞋里露出 | 高跟鞋 key 未烘焙或只设 value | 审计非零 delta，烘焙 Basis 与剩余相对 key |
| 表情后脚/身体回到旧形状 | 只改 Basis，未传播到其他 key | 重建相对 key 基准并逐帧比较 |
| VTA 比模型小约 52 倍 | 单位只作用在部分数据 | 结构化缩放 positions，重验 frame 0 |
| 表情索引错乱 | 合并/重排顶点后复用旧 VTA | 在最终拓扑上重新导出 VTA |
| 脚陷地 | 把几何问题和比例问题混为一谈 | 用 proportion/pelvis 测量修正地面，不移鞋补偿 |
| 地图加载期在 studiorender 崩溃 | compiled world vertices 超安全域或 VTX 映射损坏 | 降至 <=60k，逐 mesh 审计 VTX -> MDL -> VVD |
| 手指/发根形成长刺但权重合法 | mesh-to-pivot 半径或 collapsed-chain 铰链错误 | 定位 seam 三角，比较源/compiled pivot，执行极端姿态 CPU skin |

## 12. 退出门槛

- 常驻 key 已被证明写入最终 Basis；
- 其余 key 数量、名称、delta 和相对关系符合报告；
- SMD/VTA 顶点拓扑和 frame 0 一致；
- 脚在鞋内，鞋底在正确地面；
- 编译后 flex 接口闭合；
- HLMV 极端 flex 无爆点或大面积穿模；
- 所有几何破坏性处理都有可追溯派生文件和报告。
- compiled VVD LOD0 在预算内，VTX 映射零越界、零缺失且覆盖完整。
- 核心 mesh-to-pivot、seam、side sign 与极端姿态 edge/radius 门通过；已知坏候选不会被同一验证器放行。
