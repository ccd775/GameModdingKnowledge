# 技术合同（Stellar Blade build 24463856）

## 1. 引擎与容器

| 项 | 值 | 等级 |
| --- | --- | --- |
| 引擎 | UE 4.26.2 的 SB 分支（版本串 `4.26.2-0+++UE4+Release-4.26-SB`） | build-sensitive |
| 容器 | IoStore，TOC v3（带 PartitionSize），未加密，Oodle 压缩 | build-sensitive |
| 映射 | usmap `SB-v1.4.1`；Dumper-7 的 SDK dump 用来核对结构体字段（例如游戏的 Kawaii 节点有没有某个曲线字段） | build-sensitive |
| Mod 位置 | `SB/Content/Paks/~mods/`，文件名以 `_P` 结尾；每个包 = `.utoc` + `.ucas` + 一个 347 字节的 `.pak` | invariant（本作） |
| 打包 | 编辑器 cook → 只挑出新资源 → `retoc to-zen --version UE4_26`。用户的参考 mod 用的是 TOC v2 容器加带版本标签的属性，也能加载 | case-derived |

导出工具（基于 CUE4Parse 的命令行）只读游戏本体：`~mods` 里的包**不会**覆盖它读到的资源。
想检查自己打的包，要在 UE 编辑器里检查，或者直接解析自己的容器。本项目曾用导出工具读「自己的网格」，
读回来的是原版 201 骨的网格。

## 2. 骨架与重定向

- 共享骨架 `/Game/Art/Character/PC/CH_P_EVE_01/CH_P_EVE_01_Skeleton`：3267 根骨。平移重定向：Animation 3258、
  Skeleton 8、AnimationRelative 1。**关节位置来自动画**，网格必须绑在 EVE 的关节位置上，网格本身改不了比例。
- 58 根骨的参考缩放行列式为负（如 `Ab-L/R-Venter`、`Ab-L/R-BrochiUp`、`Ab-R-Deltoid`）。导回来后这些骨会差 180°；
  它们不带权重，可以忽略。
- 骨架里有大量没用到的配件链：`Bip001-Head` 下 122 个子骨，`Bip001-Pelvis` 下 88 个，`Bip001-Spine` 下也有。
  检查过的 EVE 动画（idle、run）只有 Bip 骨和 Ab/Dm 辅助骨的轨道，`BtoB_CtrlRig` 也不驱动这些配件链。
  所以可以借用它们做物理链（见 [Kawaii 物理](KAWAII_PHYSICS.md) §1）。
- UE 4.26 `IsCompatibleMesh`：网格里凡是骨架也有的骨，父骨必须相同，否则网格和骨架不兼容。
- Biped 层级：两条大腿是 `Bip001-Spine` 的子骨，不是 `Bip001-Pelvis` 的。

## 3. 目标资源

| 资源 | 内容 |
| --- | --- |
| `CH_P_EVE_09`（Planet Diving Suit，初始服装） | 201 骨，7 个材质槽，后处理 AnimBP `CH_P_EVE_09_AnimBP`（ControlRig + 颈部配件的 Kawaii），物理资源 `CH_P_EVE_09_Physics`。变体 `_TypeB`、`_TypeC`、`_NoHair` 是独立网格 |
| `CH_P_EVE_Head/CH_P_EVE_Face_Jali3` | 公用脸：10 根骨（Root … `Bip001-Head`、颈部辅助骨），169 个 JALI 变形（`brow_*`、`upLid_*`、`jaw_*`、`lip*` 等），没有后处理 AnimBP |
| `00_HR/EVE_HR_01` | 默认头发：独立骨架，AnimBP = MeshRefPose → 6 个 Kawaii |
| `CH_P_EVE_Hair_PonyTail_2`、`ACC_EAR_12M` | 马尾、耳饰；本项目用极小三角形网格隐藏 |

## 4. 服装后处理 AnimBP

导出全部 59 个服装 AnimBP 后，拓扑一致：

```text
LinkedInputPose → ControlRig(BtoB_CtrlRig) → LocalToComponent → KawaiiPhysics × N（每个链头一个）→ ComponentToLocal → Output
```

- `BtoB_CtrlRig` 在每个服装 AnimBP 里都有，驱动 244 根辅助骨（含所有扭转骨）。暴露的输入在所有服装里取同样的值：
  `BtoB_UpperArm` = 10、`BtoB_ForeamArm` = 13（原拼写）、`BtoB_Hand` = 15、`BtoB_UpperArm move` = 2（rig 默认值都是 0）。
- 自己的 AnimBP 引用游戏路径上的 dummy `BtoB_CtrlRig`（4 个可编辑 float 变量，不打包）。运行时解析到游戏自带的 rig；
  cook 出的 AnimBP 的 29 个导入在游戏里都存在。父类用 `AnimInstance`，与游戏一致。
- 游戏的 Kawaii 节点有 SB 专有属性（`EnterVehicleScale`、`MasterMeshDataAsset` 等），要用 KawaiiPhysics-SB 分支
  （1.11.0-SB）编写。游戏的 Kawaii 有 `StiffnessCurveData` / `LimitAngleCurveData` 等 `FRuntimeFloatCurve` 字段，
  没有 BoneConstraints。
- 游戏 exe 里有 `AnimNode_BoneDrivenController`，结构与 4.26 原版一致。`.Euler()` 的单位是度（头文件里「弧度」的注释是旧的）。
- 后处理 AnimBP 能写网格独有的骨：ModifyBone、BoneDrivenController 对它们都生效（诊断标记验证过）。

## 5. 材质

| 用途 | 父材质 | 说明 |
| --- | --- | --- |
| 皮肤、头发 | `CH_P_EVE_09/Materials/MI_P_EVE_09_Skin`（`MA_Skin_EVE`） | 头发也挂这里，配 ORSS 贴图（遮蔽 1、粗糙 0.6、高光 0.35、SSS≈0） |
| 服装 | `CH_P_EVE_50/Materials/CH_P_EVE_50_Skirt`（`MA_CH_Standard_Ver03`） | 与参考 mod 相同 |

- `MA_CH_Standard_Ver03` 的父 MI 打开了这些静态开关：`DetailLayer_01-03`、`UesFuzzLayer`（原拼写）、`UseClipMask`。
  通道：DetailLayer_01/02/03 = DetailLayerMask 的 R/G/B，Fuzz = FuzzMask 的 G。
- 自己的 MI cook 时面对的是 dummy 母材质，**静态开关不能改**，只能沿用父 MI 的着色器排列。所以双面不能靠
  MI 覆盖 TwoSided，要在网格里复制反向面（[角色替换](CHARACTER_REPLACEMENT.md) §6）。
- 布料细节法线是游戏资源 `/Game/Art/Character/Generic/MF/Fabric/{Knitted_N, T_HeavyFabric02_N, NylonTricot_N}`。
  在同一路径放不打包的 dummy 来引用它们。
- 风险（未验证）：`UseClipMask` 的材质会被运行时的盒子和平面裁切（`ClipMaskLocation/Bound/TMBasis1..4`、
  `ExclusivePlane*`）。`MA_Skin_EVE`、`MA_HumanSkin_Ver01`、`MA_DitherAlpha` 没有 ClipMask。本项目没有观察到裁切。

## 6. 工具链

| 工具 | 用途 |
| --- | --- |
| UE 4.26.2 编辑器（Epic 启动器安装） | 导入、编写 AnimBP、cook；项目里放 KawaiiPhysics-SB 1.11.0 |
| 编辑器 C++ 插件（项目原创，`Scripts/ue/project/Plugins/SBModTools`） | 暴露 `unreal.SBGraphLib`：加动画图节点、连线、按导出文本设嵌套属性、读属性、设引脚默认值、加蓝图变量、编译、导出图、读参考姿态。用 UBT + VS2019 BuildTools 无界面编译；编译时会顺带从源码重编 Kawaii |
| retoc v0.1.5（+ oo2core_9） | cook 结果 → IoStore 容器 |
| CUE4Parse 命令行、FModel | 导出原版网格、骨架、AnimBP（JSON），只读游戏本体 |
| Blender 4.2.23 | 构建脚本；FBX 导出器换成 SB 社区的反向骨修正版（ByLemi21 4.2.11_LTS），另装 UEFormat v10 导入器 |

UE 4.26 Python 的坑：

- `-run=pythonscript -script="..."` 会吃掉反斜杠路径里的 `\u…`（`builds\ue_x.py` 变成 `builds_x.py`）：路径一律用正斜杠。
- `replace_existing` 重导入会保留旧的材质槽列表：先删网格再导入。`import_materials=False` 会把所有分段并成一个槽。
- 刚导入的网格上，Python 设的材质有时不持久：导入后总是再跑一遍材质指定，并用打包后的校验把关。
- `MaterialEditingLibrary` 的修改不会把包标脏：先 `modify()`，再用 `only_if_is_dirty=False` 保存。MI 贴图的 setter 永远返回 False。
- 导入时可能弹出无人值守的消息框，日志里带一段堆栈，无害。
