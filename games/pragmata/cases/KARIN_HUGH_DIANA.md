# 案例：Karin → Hugh / Diana（2026-09-28 → 09-30）

游戏 build `24543093`。源模型：Karin_PicodraTech（与鬼武者项目同源，用于 JP 版加物理）、
Karin_Original（VRM1）、Karin_kipfel（优化版 FBX + 原版 VRM 取 spring）、Minahoshi（VRM0）。
源模型与参考 mod 都不随本库发布。

## 1. 在参考 mod 上加物理（JP Karin Hugh v1.1 / JP Diana Minahoshi v1.0）

| 版本 | 改动 | 反馈 |
| --- | --- | --- |
| Karin phys1 | 41 组 / 186 骨，鬼武者档位；Hugh prefab 首次插入 Chain2；碰撞关（Hugh clsp 不匹配） | 有物理；长链与布料移动中高频乱颤 |
| Karin phys2 | 只改 reduceSelf（长链 0.50、布料 0.70，去第二档），chain2 26 字节变化 | 不再乱颤；没有运动跟随 |
| Mina phys1 → phys2 | 23 组 / 62 骨；全量扫描后 9 个 GO 全部注入；补重置注册器；节点碰撞形状从档案复制 | （同批反馈）Minahoshi 物理偏弱 |
| phys3（两者） | UpdateTiming 3 → 4；长链 0.25、布料 0.45；Mina 麻花辫改用双马尾档 | 「挺好的」 |

转折点：乱颤的真因更可能是从布料部件复制来的 `UpdateTiming 3`，而 phys2 的「治抖」方向（调高
reduceSelf）恰好杀掉了跟随。

## 2. 从源模型完整构建（Karin_Original → Hugh，Karin_kipfel → Diana）

| 版本 | 改动 | 反馈 |
| --- | --- | --- |
| v0.1.0 | 按 JP 配方：Hugh refskel 路线（肩高 ×1.459）、Diana 原生 rest 路线（臀高 ×1.214 + 鞋底贴地）；Env_Emissive 材质；屏蔽件；phys3 物理；Hugh 碰撞关、Diana 只开空开关 | 加载正常、材质正确；Hugh：大腿根从裙片两侧漏出；膝盖附近素体从袜子里漏出 |
| v0.2.0 | 烘焙 `kisekae_*`（袜口遮罩）/ `Foot_OFF`、`Toe_OFF`；chain2 内置大腿 ×2 + 骨盆 ×2 胶囊；静止间隙闸门；裙片摆角/半径配方；Hugh 碰撞开 | Diana：走动时迈出去的大腿从裙片侧面穿出 |
| v0.3.0 | 裙链中间节点 `collisionShape` 1 → 2（节点到子节点的胶囊）；静止闸门改为检查整段；只改两个 chain2 | **验收通过** |

v0.3 的诊断：离线步幅估计（假定碰撞生效）里，无碰撞 13/28、v0.2 节点球 6/28、v0.3 胶囊节点 2/28。
即使碰撞体完全生效，节点球也挡不住两节点之间的布，所以缺口定位在节点形状而不是碰撞体尺寸；
把碰撞体放大 15% 会让静止间隙变负，被否决。v0.3 实机验收通过后才确认这一判断。

两轮双轨独立审查修掉的问题：mesh 头部固定偏移写坏、法线未用逆转置、refskel 四元数提取不稳、
验证器覆盖缺口（refskel 旋转/缩放、链组逐条对应、Chain2 组件字段）、贴图槽带着原生环境图、构建前未清空输出。

## 3. 未解决 / 未检查

- Diana 的 GPU 发丝（`ch0100_22`）未处理；若实机出现 Diana 原发，需要 strands 屏蔽件。
- 其它服装（Hugh 非默认造型、Diana 其它 cospa 的布料/头发部件）未覆盖；破损形态的侵蚀部件未屏蔽。
- 没有表情和眼动（脸绑 `Head`），与参考 mod 相同。
- 过场模型 ch0091 没有物理；诱饵道具共用 mesh（静态）。
- 裙片之间没有 link；极端姿势（60° 屈 + 大外展）离线估计仍会少量漏。
- 发布前核对源模型授权：本项目的一个源 VRM 的作者/许可字段为 `Unknown`。
