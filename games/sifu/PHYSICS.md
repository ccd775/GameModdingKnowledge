# 物理

两套机制并用：**骨链**（双马尾、尾巴、侧发、外套下摆、袖子、绳带）用网格自己的后处理动画蓝图里的 RigidBody 节点；
**裙摆**用 UE 4.26 的 NvCloth。体积感强的发束试过 NvCloth，被否决（§4 末尾）。

## 1. 宿主骨：骨架里的备用骨

RigidBody 节点按**骨架骨索引**模拟，所以只有骨架里已有的骨能被模拟，父骨也由骨架决定。`Base_skeleton` 里有给其它服装留的空骨：

| 父骨 | 备用骨 |
| --- | --- |
| `head` | `cloth_head_A_l_01..03`、`cloth_head_A_r_01..03`、`cloth_head_A_01..05`、`accessories_head_01_l/r` |
| `spine_03` / `spine_02` | `cloth_spine_03_A_01..03`、`accessories_spine_03_01_l/r` / `accessories_spine_02_01_l/r` |
| `pelvis` | `cloth_pelvis_A_01..05`、`cloth_pelvis_A_l_01..05`、`cloth_pelvis_A_r_01..05`、23 根单节 `accessories_pelvis_*`、`thigh_sleeve_l/r → calf_sleeve_l/r` |
| 四肢 | `upperarm_sleeve_01..04_*`、`lowerarm_sleeve_01..04_*`、`accessories_lowerarm_*_01_*`、`thigh/calf_sleeve_01..04_*` |

一条源模型的链（如 7 节发束）映射到 2–5 根宿主骨：宿主关节按比例 `fracs` 放在源链的折线上，顶点权重按帽函数分给宿主。
链的父子必须和骨架一致（构建时校验）。

## 2. RigidBody 骨链（`dyn_tuning.py`）

**节点设置**（`FAnimNode_RigidBody`）：模拟空间 `BaseBoneSpace`（`root`）、重力覆盖 −300 cm/s²、`ComponentLinearAccScale` 0.35、
`ComponentLinearVelScale` 0.3、`ComponentAppliedLinearAccClamp` 2500、不碰世界几何、约束两端刚体之间不碰撞。
**物理资产** `PA_Karin_Dynamics`：运动学碰撞体（Karin_Original 14 个：头、颈、胸、上臂、骨盆、脊椎…）+ 每节一个模拟胶囊，关节带角度限制和 SLERP 驱动。

**v1 像钟摆一样来回晃（用户反馈）**的原因：
- 重力全开，驱动刚度远小于重力力矩；
- PhysX 的刚体角阻尼只作用在**质心惯量** I_com 上，对绕关节的摆动几乎无效（一根双马尾绕根部的惯量约为 I_com 的 70 倍）；
  线阻尼当时只有 0.5。

**v2 的做法**：目标是源模型 VRChat PhysBones（导出为 VRM spring）的行为：gravity 0、pull 0.17–0.27、drag 0.27–0.63，
即保持建模形状、只随动作摆、阻尼很重。
- UE 4.26 的 PhysX 约束驱动是**加速度驱动**（`PhysicsInterfacePhysX.cpp` 里 `bDrivesUseAcceleration = true`）：
  角向力矩 = I_com ×（S × 角度 + D × 相对角速度）。要让惯量为 I_sub（子链绕该关节）的部分以频率 ω 振动：
  **S = ω² · I_sub / I_com，D = 2ζω · I_sub / I_com**。
- 模态频率：双马尾 1.3 Hz、尾巴 1.5 Hz、侧发 2 Hz；阻尼比 ζ 0.45–0.5；线阻尼 8、角阻尼 4。
- 碰撞只开源模型自己的碰撞组（双马尾：头 / 颈 / 胸 / 上臂；尾巴：骨盆 / `spine_01`；侧发：头 / 胸），链与链之间不碰。
- 参照：游戏自己的 `PA_M_MainChar_Dynamics`（男主披风）用锥形限制 30/20、扭转锁死或 10、无驱动、0.65–1 kg 的盒体配角阻尼 15–20。

**实机（agent 连拍，15 fps）**：标题待机和站立时保持建模的外翻、没有残余摆动；走动后停下，双马尾 0.3–0.5 s 稳定；
快速旋转攻击时被甩到接近水平再恢复（惯性）；走路时尾巴保持向后的弧度。

只调参数时不用重跑 Blender：`python dyn_tuning.py cloth.json` 就地重算，UE 端用 `physics_only` 只重建物理资产和动画蓝图。

## 3. 多模型的链规格（`dyn_stage.py` + `profiles.py`）

profile 的 `dyn` 里每条链：

| 键 | 含义 |
| --- | --- |
| `root` / `path` | 源链根骨；显式骨路径（默认取最深的后代路径） |
| `subtree` / `exclude_subtrees` | 顶点取整个子树（默认只取路径上的骨）；排除的子树 |
| `hosts` / `fracs` | 宿主骨；宿主关节在源链上的位置（0..1） |
| `rscale` | 碰撞胶囊半径缩放 |
| `blend` / `centers` | 链在第一个宿主关节之前接管顶点自身权重的过渡长度；或直接给帽函数中心 |
| `tune` | `dyn_tuning` 参数（预设 `T_TWIN`、`T_TAIL`、`T_SIDE`、`T_PANEL`、`T_CABLE`、`T_RIBBON`、`T_STRING`、`T_SLEEVE`、`T_LONGPANEL` + 每节质量） |

- 权重模式 `orig`：w = 帽函数₀ × 顶点自己的（已折叠）权重 + 宿主权重。链根附近平滑接管，不撕开衣服。
- 静止时就和碰撞体重叠的刚体对会被关掉碰撞，**但新式链保留与大腿 / 小腿的碰撞**（下摆、袖子正是要被腿推开；RBAN 会把它们推出去）。
  早期全部关掉时，外套下摆和长袖直接穿过腿。
- 「最深后代路径」可能走错：PicodraTech 外套的 OuterB 下摆沿着口袋绳走了，改成显式 `path` + `subtree`。
- 挂在手臂上的链先要在重摆时回正（[角色拟合](CHARACTER_FIT.md) §1 `hang`），否则静止姿势就在腿里。
- 线状件（Umbrella 的袖绳）用软驱动（0.6 Hz）让它垂下来，只碰骨盆和大腿。

各模型用到的链见 [案例：另外四个 Karin 模型](cases/KARIN_VARIANTS.md)。

## 4. NvCloth 裙摆（Karin_Original）

**代理网格**：`cloth_stage` 生成锥形环网格（v6：11 环 × 32 段，环距约 3.6 cm），贴在裙褶的内包络上（渲染裙面比代理高 +0.02..+1.8 cm）。
渲染裙摆通过 mesh-to-mesh 映射跟随代理；代理段在 UE 里建完布料后删除，槽号保留。

| 设置 | 值 |
| --- | --- |
| 最大距离 | 16 cm，按 f^0.8 从上到下增大（顶点色 R）；顶环固定在裙腰上沿 |
| 配置 | Damping 0.4、LinearDrag 0.3、BendConstraint 0.6、`StiffnessFrequency` 60、**`SolverFrequency` 240**、CollisionThickness 1.0 |
| 碰撞（`PA_Karin_Cloth`） | 只放骨盆、大腿、小腿、手臂；大腿用锥形胶囊（皮肤 + 袜子半径的 95 百分位：髋 9.4 cm、膝 6.8 cm） |
| 锚定 | 构建时的蒙皮里大腿份额：前 0.55、侧 0.6、后 0.15（后片不能被前抬的大腿拖进臀部）；渲染裙用代理的重心坐标蒙皮，作无布料时的退路 |
| backstop | 环 1–9：半径 15 cm、向内行程 0；顶环固定，下摆环自由（只碰大腿胶囊） |

要点：
- NvCloth 读物理资产里的 `TaperedCapsuleElems`；插件 `BuildPhysicsAsset` 支持 `"type": "tapered"`。RigidBody 节点不认锥形胶囊，给它普通胶囊。
- **backstop 是插件补的**：UE 4.26 的 NvCloth 有 BackstopDistance / BackstopRadius（在 `ClothingSimulationNv.cpp` 的
  `UpdateMotionConstraints` 里变成沿蒙皮法线的分离球），但没有编辑器以外的设置入口。`CreateClothProxy(..., BackstopScale)` 读代理顶点色
  G = 距离、B = 半径（× 32 cm）。方向取自法线（TangentZ），所以代理的三角形绕序要翻成法线朝外；mesh-to-mesh 映射在绑定和运行时都用同一绕序，不受影响。
- **UE 4.26 的 NvCloth 没有连续碰撞**：环距 7 cm 时，快速踢腿一帧就把大腿扫过稀疏的下排粒子，粒子从另一侧被推出，拉长的三角形让大腿侧面露出来。
  加密到 11 环 + 求解频率 240 后解决；刚度仍按 `StiffnessFrequency` 60 换算，不会变硬。加粗大腿胶囊 1 cm 也有效，但静止时把 2–3 环往外推了 1 cm，没用。

**版本轨迹**（每一轮都是用户实机反馈）：

| 版本 | 症状 | 原因 | 改动 |
| --- | --- | --- | --- |
| v3 | 跑步时大腿侧面切进裙子 | 渲染裙在代理里面（中位 −0.6 cm）；大腿胶囊按 60 百分位半径，偏细 | 代理贴内包络；锥形胶囊按 95 百分位；最大距离 16 cm |
| v4 | 裙子松垮、腰部有缝 | 圆形 `spine_01/02` 胶囊在静止时就在裙腰外 4–6 cm，把顶环推开 | 裙摆碰撞只留骨盆 / 腿 / 手臂；顶环放到裙腰上沿 |
| v5 | 贴合了，但偶尔透出臀部、大腿根、肚子、裆部 | 后面什么都没有，锥面在运动中向内塌 | backstop；裙腰前部跟皮肤分布（[角色拟合](CHARACTER_FIT.md) §3） |
| v6 | 少数姿势下大腿侧面露一点肉 | 没有连续碰撞，粗网格被快速踢腿穿过 | 11 环 + `SolverFrequency` 240 |

v6 用户实机：「基本好了」。

**被否决**：双马尾用 NvCloth 管状代理。体积感强的发束在 mesh-to-mesh 映射下被撕成碎条（实机截图），改用骨链。

## 5. 离线裙摆替身（`skirt_sim.py`）

在 Blender 里用时间步进的 PBD 近似 NvCloth：重力、阻尼、拉伸 / 剪切 / 弯曲边、到固定环的系绳、最大距离、backstop 球、
物理资产形状碰撞 + 厚度。骨骼旋转在解出的动画帧之间球面插值驱动。每个动画帧都从粒子重建渲染裙面，与摆好姿势的皮肤比较：
渲染顶点算「在皮肤里」需要同时满足「最近的皮肤面在它后面」和「沿布料法线第一次穿过皮肤是出射」（只看最近面会被内裤边这类薄边骗）。手臂忽略。

- 变体键：`sub_r` / `sub_s`（环 / 段细分）、`thick`、`thigh_dr`、`leg`（前 / 侧 / 后锚定份额）、`bs_last`、`travel`、`hz`。
- 只是粗略替身：在 2 次和 6 次迭代下各跑一遍，**只信两者都同意的结论**。
- v5 → v6 的依据（跑步 + 9 个踢腿 / 膝击动画，共 263 帧）：大腿穿出 > 1 cm 的帧 14 / 41（v5，2 / 6 次迭代）→ 0 / 1；
  肚子 / 臀部的帧数基本不变；跑步不变。
- 用法：用户指出某个动作露肉时，先 `SifuExport anim` 解出那一招，再在替身里比较候选。
