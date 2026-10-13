# 技术合同

除标注外均为 build `18739835`（`v_1.29_6.775`）上的实测。

## 1. 游戏与 pak

- 引擎：Sloclap 改过的 UE 4.26。材质带自定义的 `WuguanCustomLightingMode`，有 `slcp.*` 控制台变量；forward shading；
  `bShareMaterialShaderCode=False`；**没有 IoStore**。安装目录里带 shipping PDB（`Sifu-Win64-Shipping.pdb`），可以按符号名搜类和属性。
- 资源只有一个 `Sifu\Content\Paks\pakchunk0-WindowsNoEditor.pak`（+ `.sig`），pak v11，**索引加密**（AES-256）。
- AES 密钥的找法：在 `Sifu-Win64-Shipping.exe` 里搜「立即数逐段写栈」的指令序列（UE 把编进 exe 的密钥拆成一串立即数写到栈上），
  拼出候选后解密索引，开头能读出挂载点 `../../../` 即为正确。本库**不发布密钥**；便携工具从环境变量 `SIFU_AES` 读。
- CUE4Parse 以 `GAME_UE4_26` 读取，不需要 usmap（属性是带版本的序列化）。

## 2. mod 加载

- mod pak 放 `Sifu\Content\Paks\~mods\`（没有就新建）。命名沿用社区惯例 `pakchunk99-<名字>_P.pak`
  （`_P` 后缀让 UE 把它当补丁包，优先于原包挂载）。
- 每个 pak 旁边放同名 `.sig`，内容直接复制游戏的 `pakchunk0-WindowsNoEditor.sig`（社区做法，本项目一直这样装；
  不带 `.sig` 的情况没有测试）。
- pak 里的路径是 `../../../Sifu/Content/...`；所以 UE 内容工程的名字必须是 `Sifu`。
- 只能在游戏关闭时替换 pak。同一资产路径被两个 mod 替换时只有一个生效，所以替换同一网格的 mod 一次只装一个。

## 3. 目标资产与使用者

- 目标：`/Game/Characters/MainChar/W/Meshes/SK_W_MainChar_01`（女主默认服装）。
- 同一网格还被女主的第 2、3 套服装（「复仇」「武德」）和几个女性「分身」敌人蓝图（如
  `BP_AICharacter_Grunt_W_HD1_Fighter_01_Doppelganger2`）使用；替换后它们也变成这个模型。第 2、3 套服装按**槽号**给这个网格
  覆盖材质（槽 11–16 和 18），见 §5。
- 女主用的是「man」系列动画（例如 `Locomotion/Man/Barehands/Moving/V3/North/MC_man_barehands_V3_north` 是跑，V2 是慢跑），
  没有单独的女性动作集。

## 4. 骨架与重定向

- 骨架是共用的 `/Game/Characters/Skeleton/Base_skeleton`（385 根骨）。W 网格用其中 268 根；其余是给别的服装留的 `cloth_*` / `accessories_*` /
  `*_sleeve_*` 等备用骨，替换网格可以拿来挂次级物理（[物理](PHYSICS.md) §1）。
- 编辑器里的 `Base_skeleton` 必须和游戏的一致：本项目从游戏参考姿势重建（`make_skeleton_fbx.py` → `ue_import_skeleton.py`），
  读回误差 ≤ 0.0003 cm / 1e-7 rad。它只作占位，不进 pak；烘焙后的网格按路径引用游戏自己的骨架。
- 网格参考姿势：**旋转逐骨等于 W 的参考姿势**（误差 7e-8），**位置用替换模型自己的**。游戏骨架的平移重定向设置
  （OrientAndScale / AnimationRelative）会把动画按新比例搬过来。Karin 按 1.4 倍放大（身高约 1.75 m，不含耳朵）。
- 骨盆放在髋关节上方（同 W 的相对位置），锁骨相对 `spine_03` 的位置照 W（Karin 自己的肩关节几乎贴着上臂）。
- FBX 里骨架对象必须叫 `Armature`：UE 只在根节点名字正好是 `Armature` 时把它剥掉。场景单位 cm（unit scale 0.01）。

## 5. 材质与槽位

- W 默认服装的三个材质实例：脸 `W/Materials/MI_MainChar_W_Head_Dyn`、皮肤 `MI_MainChar_W_20_Body`、
  衣服 / 头发 `MI_MainChar_W_BasicOutfit`（母材质是 Cloth_Dyn，带 `bUsedWithClothing`）。
  替换模型的 MIC 以它们为父级，只覆盖贴图和少数标量，就继承了 W 的静态开关组合，不需要编译新的着色器
  （[材质与贴图](MATERIALS_AND_TEXTURES.md) §1）。
- 槽 0–10 放自己的材质，NvCloth 代理放槽 11（代理段在构建时被移除，槽保留）。第 2、3 套服装覆盖槽 11–16 和 18，
  所以可见槽最多 11 个（构建脚本断言）。
- W 网格的顶点色是材质遮罩，按部位类别复制到替换模型上。

## 6. 面部与眼球

- 游戏用 `Animations/01_FacialPoseAsset/MC_woman_facial_PoseAsset`（50 个叠加姿势：眨眼、口型、疼痛、发力、惊讶、对话）
  驱动面部骨（`brows_*`、`upperLids_*`、`jaw` 等）。替换模型的脸只要用对面部骨的权重，就自动有表情（[角色拟合](CHARACTER_FIT.md) §4）。
- 眼球：看向 NPC / 敌人 / 可交互物时，游戏通过注视混合空间（`Grunt_M_EyeLookAt_BS`，注视 ±50°，眼球最多约 46°）转 `eye_l` / `eye_r`。

## 7. 物理资产与后处理蓝图

- 网格的 PhysicsAsset / ShadowPhysicsAsset 保持引用游戏的 `PA_W_MainChar` / `PA_M_MainChar_ShadowCapsules`（受击与布娃娃）。
- 网格的 **PostProcessAnimBlueprint** 设成自己的 `ABP_Karin_PostProcess`：它在游戏的动画蓝图之后对这个网格运行，
  里面只有一个 RigidBody 节点，用自己的 `PA_Karin_Dynamics`。所有用这个网格的角色都会跑它，不用碰游戏的动画蓝图。
- NvCloth 的碰撞体来自另一个物理资产 `PA_Karin_Cloth`（只放骨盆 / 大腿 / 小腿 / 手臂）。
- 主角动画会给部分备用骨打关键帧（例如 V2 慢跑里的 `cloth_spine_03_A`、`cloth_pelvis_A`），值等于骨架参考旋转；
  RigidBody 节点对模拟刚体忽略输入姿势，所以无害。

## 8. build 变化时

依次核对：pak 版本与加密（索引能否解开）、目标网格路径、`Base_skeleton` 骨数与参考姿势（与旧 dump 逐骨比较）、
W 三个材质实例的路径与参数名（`BaseColor`、`ComboMap`、`Normal`、`Color_Old`、`Aging_Mask`、`Aging_Normal_A/B`、
`Camera Dist Falloff`）、面部姿势资产的曲线名、第 2、3 套服装覆盖的槽号。全部一致才能沿用旧的构建结果。
