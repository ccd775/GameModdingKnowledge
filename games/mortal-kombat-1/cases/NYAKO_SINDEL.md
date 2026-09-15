# 案例：Karin Nyako Normal → Sindel

## 最终身份与范围

游戏build17941244，UE定制4.27-MK1-release，retoc0.1.5，Blender4.5.12，ACL UModel2.1。
源为用户提供的 `Karin_Nyako_Normal_Unified_Atlas.blend`，原23mesh、323骨、四张4096图。目标221骨，最终单材质，合并为8192图集。输出源前缀 `a_nyako_sindel_complete_P`；游戏安装前缀 `a_nyako_sindel_bundle_P`。

最终UCAS：`e0ab3dd65b4faf9925c3ae2aef8a68b62c481a5308484bb99bc994e9373d09ee`。
用户先确认材质颜色正确，再对腿部修正表示“我觉得可以了”。时间以项目本地milestone和manifest记录为准；历史日志UTC与本地日期可能不同。

## 已验证技术路线

1. native221骨，厘米mesh/骨数据、scene0.01、object identity。
2. evaluated geometry冻结，修正FBX parent/transform，回读确认。
3. 全部材质统一原生Sindel Body001，一张8192 D，兼容性中性N/ART/CSM。
4. 修正头组比例，保持鞋子源刚性，脚底静止高度正确。
5. native hair render index退化隐藏，保留native cloth等所有非索引字节。
6. sock与skin相容过渡，扩大平底鞋补偿场，消除小腿过度压缩。
7. cook→Zen normalization→restore native raw rest→回读→部署完整trio。

## 目标资源：仅此case

| 内容 | 身份 |
| --- | --- |
| Body | `/Game/Disk/Char/Sindel/Skin/001/Mesh/SK_Sindel_Skin001_A` |
| Body chunk | `dd8f4660f193f68700000002` |
| Skeleton | `/Game/Disk/Char/Sindel/Template/Mesh/SK_Sindel_Template_Skeleton` |
| Material | `/Game/Disk/Char/Sindel/Skin/001/Mat/SetA/MI_Sindel_Body001` |
| D/N/ART/CSM | `/Game/Disk/Char/Sindel/Skin/001/Texture/SetA/T_Sindel_Body001_*` |
| Hair mesh chunk | `a2574543e093340800000002` |
| Hair cloth mesh chunk | `201b4a48a074689100000002` |

Hair001原始hash `6a563e7348910bdb432c025ea79abca8fab61bb24543684ef827c74ea86b4a13`；三段16位render索引起点/数量为135698/43704、874069/29163、1416126/18294。
Hair001_Cloth原始hash `99057ecd6db06db363f5702c4deb780b8235edf2fead63f6b660a697f2b3a2f9`；32位render索引635960/273702。范围外字节完全不变。**这些不是扫描算法，不准用于不同源hash。**

## 故障序列与结论

| 阶段 | 结果 | 可靠结论 |
| --- | --- | --- |
| 早期容器 | 原版显示/选中崩溃 | 未成功替换，不是截图误判 |
| Zen单bundle、加载名修正 | 自定义消费链生效但身体不可见 | 下一步查raw单位 |
| root100→1及原生rest恢复 | Nyako完整出现 | viewer归一化曾掩盖raw差异 |
| 多个MI、多原生body material | 仅skin正常、衣发灰 | 四材质路径未通过；底层原因未唯一定位 |
| 微小hair替代网格+材质联合实验 | 崩溃 | 多变量，不能唯一归因 |
| native hair索引隐藏 | 用户确认原发消失 | 保留cloth的方式通过 |
| 单槽8192 | 用户确认全部颜色正常 | 可作为后续优先路线 |
| 脚底修正 | 鞋正确但sock上移/小腿折 | 几何补偿场有副作用，不一定是权重 |
| 平滑腿部补偿 | 用户接受 | 冻结当前范围，不扩大为全部动画验证 |

## 不可直接套用的数字

0.835505头组缩放、Head pivot、膝高54.0884cm、shoe floor0.3cm、source过渡0.08–0.32m、raw FTransform17171偏移和221记录均属于本案。新的输入先采样，保持源头身比和脚部形状，并验证target关节兼容。

## 最终离线报告摘录

- FBX屈膝0/30/60/90的最大位置误差小于0.000039cm，weight error0。
- 最终包原生骨local translation/scale error0。
- 最终包skinned geometry双向最近顶点误差约0.0000973cm；Cook额外顶点由UV/normal等拆分产生，不要求顶点总数相等。
- 原始源顶点85182，Cook skinned顶点105183；glTF导入helper sphere另42顶点必须排除。
- 最终身体chunk14258893字节；仅身体asset变化，贴图和两个hair hider payload与已认可版本逐字节相同。

这些数值是本案记录，不是所有新角色都必须达到同一精度的固定阈值。新工程在运行前选定单位、容差和检查，不能失败后为通过而降低门槛。
