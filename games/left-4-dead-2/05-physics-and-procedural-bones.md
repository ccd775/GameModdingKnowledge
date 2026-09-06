# 附件、Procedural 骨与物理

## 1. 三种运动系统不要混为一谈

| 系统 | 用途 | 主要来源 |
| --- | --- | --- |
| 普通骨骼蒙皮 | 身体和刚性附件随动画 | Blend 权重与 ValveBiped 动画接口 |
| procedural / jiggle | 头发、耳朵、尾巴、衣摆的二次运动 | VRM spring 意图、成熟参考、`$jigglebone`/VRD |
| ragdoll physics | 死亡或物理状态下的碰撞 hull | 原生 survivor physics 契约与定制 PHY |

把 VRM spring 参数直接抄成 Source 数值通常不正确；把 ragdoll hull 当作附件碰撞也不正确。

若问题同时涉及 mesh bind、proportion、light 动画或 collapsed-chain 长刺，先读 [Source-Fit Bind、动画接入与 Procedural 回归排障](18-source-fit-bind-procedural-regression.md)。

## 2. 保留辅助骨的条件

StudioMDL 可能裁掉未被网格、动画、附件或 procedural 规则引用的骨。对每根自定义骨记录：

- 父骨；
- 有权重顶点数；
- 最大/总权重；
- 是否出现在 jiggle/VRD/attachment/hitbox/physics；
- 最终保留理由。

仅在 QC 写 `$jigglebone` 不一定足够。如果 helper 权重或 procedural 定义缺失，编译后骨数会下降，附件链可能整段失效。

## 3. 从 VRM spring 转换

先保存原始意图：spring group、joint 顺序、center、stiffness、drag、gravity、hit radius、collider group 和 offset。

再按链类别分 profile，例如：

- 短耳朵/发饰：高刚度、小角度；
- 长发束：中刚度、中阻尼、分段递减；
- 尾巴：较大角度但限制基部；
- 衣摆：限制横向穿体，必要时减少自由度。

每个转换后的 profile 记录参数来源和 clamp。先在 HLMV 的 idle/运动序列检查爆炸、翻转和无限摆动，再进入游戏。

## 4. 折叠 spring chain 时先锁铰链

设源链为：

```text
A(static anchor) -> D0(first dynamic) -> D1 -> ... -> Dn
```

若受骨预算限制折叠成 `A' -> D'`，`D'` 的代表必须是经 VRM 审计确认的 `D0`，通常是 `path_position=0` 且为 `A` 的 direct child。后续 `D1..Dn` 可以合并权重，但不能因为某个远端控制的带权顶点更多，就让它成为首动态 pivot。

必须区分：

```text
d_hinge = length(head(D0) - head(A))
L_jiggle = length(tail(D0) - head(D0))
```

`d_hinge` 决定网格绕哪里转，`L_jiggle` 是 Source solver 的模拟长度。`$jigglebone length`、mass、stiffness、damping 和 angle 都不会搬动错误的 bind pivot。调参顺序必须是：parent/representative/pivot/weights/axis -> length -> mass/stiffness/damping/angle -> runtime collision。

若没有显式静态锚，应保留或创建 spring root 的非动态父控制。若无法在骨预算内形成安全铰链，明确使用静态 fallback，优于在错误 pivot 上保留物理。

## 5. Procedural CPU skin 因果探针

当运行时出现发根细条、长发主体远离头部或附件长刺时，可对 compiled bind 做角度探针。对骨 `j`：

```text
S_j = G_j_pose * inverse(G_j_bind)
v_pose = sum_j weight_j * S_j * v_bind
```

在动态骨 local 轴上施加声明角限的正负旋转，至少统计：

- anchor/dynamic 共权 seam 边的 `length_pose / length_bind`、P99 和 max；
- 根区动态顶点相对 bind 的最大/分位位移；
- 三角绝对边长、绝对变化和新增退化面；
- parent-to-dynamic segment 与源 path-0 segment 的比率；
- 带权点到 pivot 的 bind/pose 半径。

近零微边会放大比率，必须同时报告绝对长度/变化并将微边作为非门禁诊断。可做 pivot-only counterfactual：只把 pivot 改到 D0，保持权重、旋转和角度不变；若畸变骤降，主因是 pivot，而非参数。若不降，再查权重梯度、旋转轴、父链和双重 bind 变换。

几何上，半径 `r` 的点在角度 `theta` 下位移近似为：

```text
displacement = 2 * r * sin(theta / 2)
```

这解释了为什么远端 pivot 的大力臂不能靠阻尼修好。

同一审计器必须让修复候选通过，并让锁定哈希的已知坏候选在预期 check ID 上失败。不要只锁总失败数；验证器 schema 改变后，总数可能变化而故障签名不变。

## 6. World/light procedural parity

如果 world 与 light 设计为共享可见骨架和附件物理，应从同一生成源构建，并比较：

- QCI jiggle 名称、顺序、唯一性和全部字段；
- compiled bone name/index/parent、procedural type 和 flags；
- length、tip mass、pitch/yaw/along stiffness+damping、angle；
- ordinary/JiggleRule/QuatInterp 完整清单；
- QCI 到 MDL 仅存在有证据的浮点量化误差。

只比较 rule count 或只比较刚修改的两根骨不够，可能让其他附件静默漂移。world/light MDL 因 sequence/PHY 不同不要求文件哈希相同；共享 procedural payload 应逐字段一致。

## 7. Procedural 规则验证

编译前后比较：

- 预期骨清单与最终骨清单；
- 父子关系；
- JiggleRule 与 QuatInterp 数；
- VRD rule 是否命中正确骨；
- bind pose 骨端点误差；
- 动画姿势下附件根部是否连续。

Karin 案例中，126 根最终骨包含 61 根 JiggleRule 和 6 根 QuatInterp。一个 120 骨候选曾是回归，因为 6 根 helper 被裁掉。数字本身不通用，教训是必须比较“预期辅助骨集合”，不能只判断编译成功。

## 8. 权重限制

在本项目验证过的 L4D2 v48/v49 路径中，每顶点最多三根骨骼影响。处理时：

1. 保留最高三权重；
2. 归一化；
3. 报告被删权重总量、最大单点损失和受影响顶点数；
4. 重点检查肩、胯、裙摆根部、手腕和面部。

不得留下零权重顶点或引用不存在骨的权重。

### 8.1 Source-fit 后的 attachment 与 hitbox

source-fit 改变 pivot 后，attachment/hitbox 不能只靠“原生行还在 QC”判定正确，也
不能一律反算成保持 stock world 坐标。先确定它们的所有权：

- 若新 parent 的 Source frame rotation 与已验证接口一致，只是 pivot 随 avatar 解剖
  位置变化，原 local attachment/hitbox 可以保留；world 点随 parent pivot 平移是预期。
- 若 parent frame、parent bone 或旋转发生变化，先锁定选择保留的 reference global
  transform，再用 `local = inverse(new_parent_world) * reference_global` 重表达；挂在被裁
  骨上时沿原生树上溯最近保留祖先。
- 不要为了保留 stock world 点把手、脚、面部挂点拉离自定义角色的实际表面。

审计至少比较 attachment 名称/parent/local matrix、相对 parent pivot 的 offset/rotation、
到对应可见几何的最近距离，以及编译后数量。示例 Mod 可能漏掉当前原生版本新增的
`forward` 等接口，当前原生 ABI 优先。

hitbox 先保留 hitgroup 语义，再在最终 bind frame 中验证 local bounds 与几何覆盖。
拟合或统计只使用身体白名单网格，排除头发、耳朵、尾巴、裙摆、宽袖和饰品，否则
配饰会放大碰撞盒。报告 body/face 覆盖率及未覆盖点的 P99/max 距离，不要求视觉附件
进入伤害 hitbox。

## 9. Ragdoll hull 精简

原生 physics SMD 可能声明许多节点，但只有少数骨真正拥有 hull 顶点。合理做法：

1. 解析每个三角形/顶点实际归属的骨。
2. 保留所有拥有 hull 的骨。
3. 加入它们到根的必要祖先，保持合法层级。
4. 删除完全未使用节点。
5. 保持 hull 拓扑、材质和关节关系可解释。

Karin 案例从原生 Rochelle physics 的 79 个声明节点中确认 18 个骨拥有 hull，加入祖先后使用 21 个节点、490 个三角形。它只是一个精简示例。

## 10. 避免 physics 双重变换

StudioMDL 会依据同名骨的 bind pose 对 physics 几何做转换。如果先手工把 physics 顶点从原生 skeleton 变换到自定义 skeleton，然后又让 StudioMDL 做 named-bone bind conversion，就会双重变换，导致 hull 严重错位。

原则：

- 让 StudioMDL 负责它已有明确定义的 bind conversion；
- 不在没有独立数学审计时预变换 physics 顶点；
- 对比编译前 physics SMD 与编译后 HLMV overlay；
- 静止和动画姿势都要检查。

## 11. PHY 完整性

自定义 `.phy` 必须：

- 与 MDL 在同一次 StudioMDL 运行生成；
- checksum 与 MDL 一致；
- 只引用最终 MDL 存在的骨；
- solid/convex 数与报告一致；
- 没有旧 `.phz` 或陈旧 `.phy` 被误打包；
- HLMV overlay 与网格合理对齐。

如果无法证明自定义 PHY 正确，明确选择经过验证的 fallback，并在 manifest 写清楚。无 `.phy` 的参考 Mod 可能是刻意依赖原生行为，不代表遗漏。

### 多 runtime variant 的 PHY 合同

一个 avatar 可能同时覆盖普通/特殊皮肤、DLC bride、world/light 或其他 runtime path。共享可见几何不等于可以复制同一个 QC/collision/PHY：每个 target 都应锁定自己的原生 physics 来源、model path、同轮 companion checksum 和 solid/convex 审计。若多个 target 设计为共享同一 bind/proportion，则把 canonical、root 与 ground parity 放在动画/模型源合同中比较，而不是通过复制或平移另一 target 的 PHY 来补偿。

安全的转换边界不变：physics SMD 保持其 source-local hull 坐标，只裁未用节点、保留必要祖先并重映射节点索引；让 StudioMDL 完成一次 named-bone bind conversion。不要把 target rest 或网格变换预写进 hull，再让 StudioMDL 转换第二次。双目标 Bride 悬空与 PHY 独立保留的例子见 [Karin Y -> Witch 双目标替换案例](19-karin-y-witch-case-study.md)。

## 12. HLMV 与离线替代检查

HLMV 可用时检查：

- bind pose 中 hull 是否覆盖头、躯干和四肢；
- idle、walk、run、crouch 和 injured 下 hull 是否跟随；
- 耳朵、头发、尾巴、光环、衣摆根部无断裂；
- jiggle 不持续增幅、不翻转、不高速抖动；
- 近地附件不会持续穿地；
- physics 骨和视觉骨没有明显坐标系/单位差。

若锁定参考/控制组与候选在同一 HLMV 模块和位置共同崩溃，可把 HLMV 标记为 `unavailable_with_control_failure`，改用 compiled MDL 解码、CPU skin、骨段/pivot/边形变门和非空离线渲染作为发布前门。该替代不等于游戏实测，runtime 状态仍保持 pending。

## 13. 常见失败

| 现象 | 根因 | 修复 |
| --- | --- | --- |
| 编译后附件骨消失 | 无权重或 procedural/VRD 引用缺失 | 恢复真实权重和规则，比较骨清单 |
| 头发/尾巴爆炸 | 参数尺度、重力方向、父链或 pivot 错误 | 先锁 anchor/path-0 pivot，再按链 profile 限幅 |
| 发根出现细条、整束远离身体 | 折叠链误选远端代表，seam 绕大力臂旋转 | 代表改为首动态 direct child，全量重建骨架/world/light；不要只调阻尼 |
| hull 与角色相距很远 | physics 被预变换后又被 StudioMDL 转换 | 移除预变换，保留 named-bone 流程 |
| PHY checksum 不匹配 | 混用了不同编译轮次的文件 | 清理隔离输出并同轮重编 |
| 静止正常、动画错位 | 只检查 bind pose 或骨父级不一致 | 动画序列下检查 overlay 和父链 |

## 14. 退出门槛

- 预期骨、辅助骨、procedural 类型和编译结果逐项闭合；
- 权重影响数和损失报告通过；
- VRM 到 Source 的转换假设已记录；
- collapsed chain 的静态锚、首动态代表、parent-to-child segment 和 seam 半径已验证；
- procedural CPU skin 正候选通过、已知坏候选按预期失败；
- 设计为共享的 world/light procedural payload 已逐字段一致；
- PHY checksum、骨、solid/convex 与报告一致；
- HLMV 静止和动画 overlay 通过，或已按控制组失败规则记录为 unavailable 并通过独立离线替代门；
- 未经实机验证的附件碰撞和 ragdoll 行为仍明确标记为 pending。
