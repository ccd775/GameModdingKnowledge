# 面部

## 1. 形变按游戏的曲线名命名

- 原版头是 MetaHuman：`Hun_Head_New` 带 DNA，后处理 `Hun_Head_PostProcess_AnimBP` 跑 RigLogic；游戏用 277 条 `CTRL_expressions_*` 曲线。
- 把 Karin 的形状键按曲线名导出成形变（43 个：眨眼、眯眼、脸颊、睁大、视线、眉、`jawOpen`、嘴角、拉伸、嘟嘴、抿嘴、上下唇），
  并写上网格的曲线元数据（插件 `SetMorphCurveMetaData`），游戏的动画就会驱动它们。骨架里有这 43 条曲线（`invariant`：UE 按名字把曲线驱动到同名形变）。
- 另加 34 个 ARKit 别名（`head_` + 小写 ARKit 名，按 CTRL 配方合成），对应 `Animation/SoundLip/` 里的对话口型与情绪混合空间的曲线名。
  没覆盖：dimple、press、roll、shrug、鼻皱、下颌左右（Karin 没有对应形状键）。
- 少年魂的面部曲线不是 CTRL 名：少年头的形变不被驱动（序章的表情只靠眨眼循环，见 §4）。

## 2. 平时游玩没有面部反应（原版也没有）

受击、死亡动画（`Hun_Unarmed_Hit*`、`_Dead*`）不带面部曲线；它们给 `jaw_root` / `FACIAL_C_Jaw` 打了关键帧，但角度是 0。口型和情绪只在 NPC 的头部
后处理动画蓝图里有（InPose → DefaultSlot 叠加对话 → EmoSlot 叠加情绪混合空间）；玩家的头部后处理没有这些槽。用户确认原版魂平时也没有面部反应。

## 3. 成年头上脸发暗：运行时的动态材质实例

- 现象：脸放在成年头组件上时整张脸深棕、眼睛发灰；同一张脸和同一个材质在少年头上正常，旁边的脖子也正常。
- 排除过：光照通道 / 模板、外观表的材质覆盖（没有）、形变法线（插件 `DumpMorphTargets`：UE 重算，平均 |dN| 0.07）。
- 原因（读蓝图字节码 `PBZX_SCRIPT=1` 找到）：原生代码调用蓝图事件 `RefreshMaterialParamByHead(Component)`；`BP_Renewal_Hun` 覆盖了它：
  取 `GetMaterial(0)` → 转成或新建动态材质实例 → 设全局参数 `HealthPercentage` = clamp((剩余天数 − 10) / 56)（「66 天」效果，≤ 10 天时为 0）。
  只有原版的 `Hun_Status/MI_ZeroHun_Head_health` 有这个参数；`BP_Renewal_Hun_Young` 不覆盖这个事件，所以只有成年头的**槽 0** 变暗。
- 规则：成年头的槽 0 放一个隐藏三角形（`MI_Karin_Skin`），脸放在槽 1（`MI_Karin_Face`）。`build_pbz.py` 的 `face_slot0`。

## 4. 眨眼：谁跑哪个动画蓝图

逐步排除得到的事实（每条都有一版实机证伪 / 证实）：

| 假设 | 结果 |
| --- | --- |
| 领导者是 `Hun_Invs`，身体跟随它 | 证伪：身体网格装在 `CharacterMesh0` 上，它就是领导者 |
| 平时游玩时头跑 `Hun_CopyPose` | 证伪：在 `Hun_CopyPose` 里加按组件标签门控的眨眼，头不眨（模板上的标签到不了运行时的头） |
| 头跑 `Hun_CopyPose_Head` | 证伪：重建 `Hun_CopyPose_Head`（第二个复制姿势 → DefaultSlot → 从 neck_01 分层混合），按类名门控，仍不眨 |
| 睫毛片组件（头的子组件）跑 `Hun_CopyPose` | 证实：脸放在睫毛片上、`Hun_CopyPose` 里加不门控的眨眼循环，平时游玩会眨眼 |
| 过场角色（`BP_Seq_*`，父类 `BP_SeqCharacter`）的头跑 `Hun_CopyPose` 并带过场的面部动画 | 证实 |

插件 `BuildCopyPoseOverlayAnimBP(AnimBP, Overlay, GateClass, SlotName, SlotRootBone)` 重建这两个动画蓝图：Copy Pose From Mesh（附着父级、复制曲线和属性、
根 `root`）→ Layered Blend Per Bone（无分支过滤、权重 1、`CurveBlendOption = UseMaxValue`：最大值混合不看逐骨权重，5.7 源码确认）→ 输出；叠加的是只有曲线的循环动画
`A_Karin_Blink`（插件 `SetCurveSequence`：14 秒，在 1.0 / 5.2 / 8.6 / 8.95 / 12.3 秒眨眼，闭 70 ms、停 40 ms、睁 150 ms，`eyeBlinkL/R`）。
门控：成员变量 `KarinBlinkWeight` 绑到混合权重，在 Blueprint Initialize Animation 里设成
`Conv_BoolToDouble(NOT Contains(GetClassDisplayName(GetObjectClass(GetOwningActor())), "BP_Seq"))`。`ue_blink.py` 用插件 `TestCopyPoseAnim`
在编辑器世界里跑 1.09 秒，对 `!Actor`（权重 0、曲线 0）和 `!BP_Seq`（权重 1、曲线 0.998）两种门控自测，都对才写 `BLINK_OK`。

## 5. 最终方案：两张脸

- 睫毛片（`Karin_Face.fbx` → `Hun_BrowLashCard`）：普通的脸，77 个形变；平时游玩靠门控的眨眼循环眨眼；过场角色把它隐藏（见下）。
- 头（`Karin_Head.fbx` → `Hun_Head_New`，槽 0 隐藏三角）：基础形状绕头关节缩到 90%（平时藏在睫毛片的脸里面），加一个形变 `KarinFaceShow`（共 78 个）恢复原大；
  mod 的 `Hun_CopyPose` / `Hun_CopyPose_Head` 总是输出 `KarinFaceShow = 1`（插件的 "Always" 叠加 `A_Karin_FaceShow`），所以头上的脸只在它自己的动画蓝图
  起作用的地方（过场）出现。
- 过场：`BP_Seq_Hun` 的睫毛片（和 `CA_Hun_Hair`）带 `bInfluencedByMainHairMode`，groom 带 `bIsMainHair`：开着 groom 头发（画质设置 GroomQuality）时卡片式的后备会被隐藏，
  于是只剩头上的脸。groom 本身用隐藏占位换掉。
- `probe_face3.py`：缩到 90% 时头上那张脸没有任何部分跑到睫毛片完全闭合的眼睑前面（眨到一半时更深的睁眼可能从眼缝里露几帧）；导入器在缩放后的基础形状 + 未缩放的增量上
  算的表情法线平均偏 1.3°、95 分位 6°。先试过缩到 5%：表情法线错（眨眼平均 |dN| 0.467，睫毛片上是 0.124）；导入后改 `UMorphTarget` 增量（插件 `CopyMorphTangents`）
  到不了 cook（GPU 形变数据从源重建）。cook 后的形变数据用 `PbzExport morphs` 读：头的眨眼 0.150、下颌 0.226，睫毛片 0.124 / 0.209，`KarinFaceShow` 约 0。
- 证据：平时眨眼、脸色、过场有脸和口型经用户实机确认（`runtime-confirmed`）。限制：只在开着 groom 头发时测过过场；groom 质量低时睫毛片也会在过场里显示，
  两张重合的脸用同样的曲线，可能闪。
