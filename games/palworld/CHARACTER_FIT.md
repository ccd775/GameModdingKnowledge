# 角色拟合

全部在 `build_pal.py` 里完成（Blender 4.2 无界面）。数值是 Karin_Original 的案例值。

## 1. 比例与重摆（Karin 自己的比例）

骨架对 4075 根骨用 Skeleton 平移重定向（[技术合同](TECHNICAL_CONTRACTS.md) §3），所以 bind 姿势里的位置就是游戏里的比例。
规则：**朝向逐骨等于原版，位置用 Karin 的。**

- 缩放 ×1.30（VRM 米 → 厘米再乘 1.3）。r3 的 pelvis 高 97.4 cm、head 关节 136.3 cm。
- 关节对应：pelvis ← Hips、spine_01 ← Spine、neck_01 ← Neck、head ← Head、eyes ← LeftEye / RightEye，四肢、手指按 VRM 人形骨一一对应。
- **延续段**（上一节骨指向下一节骨的方向，动画依赖它）：用原版方向、Karin 的长度。包括脊柱、锁骨 → 上臂 → 前臂 → 手、
  大腿 → 小腿 → 脚 → 脚掌、手指各节。
- **分叉段**（pelvis → thigh、spine_03 → clavicle、hand → 手指根、head → eyes）：用 Karin 自己的关节，由重摆后的 Karin 父骨带过去。
- Karin 没有 spine_02 / spine_03：Spine → Neck 这一段按原版的分段比例分给 spine_01..neck_01，整体缩放到弦长等于 Karin 的
  Spine → Neck；躯干作为一个刚体重摆上去。
- 不对应的辅助骨（扭转骨、武器骨）：原版偏移乘父骨的长度比。
- 网格重摆：每根 Karin 骨一个刚体变换（把 Karin 的骨段摆到原版方向上），按原权重线性混合。
  报告里的 `joint_mismatch_cm`（Karin 关节重摆后离新关节的距离）r3 为 0。

源模型的「穿衣」形态键（`body_2` 上的 `kisekae_*`：肩、上臂、肘、前臂、胸、膝、小腿、脚踝、脚、脚趾）在重摆前烘进基础网格，
否则皮肤会从衣服里透出来。

## 2. 权重

- Karin 人形骨直接对应 PalHuman 骨；Karin 的 Spine / Chest 权重按顶点高度分给 `spine_01/02/03`（在关节上下 3 cm 内平滑过渡）。
- 没有对应的骨（饰物、末端）并到最近的已映射祖先；物理链骨改名后保留自己的权重。
- 每个顶点最多 8 个影响骨，归一化。报告里 `groups_not_bones` 必须为空。

## 3. 物理链：改名落到游戏骨架的配件链上

Kawaii 按 USkeleton 建链（[Kawaii 物理](KAWAII_PHYSICS.md) §1）。每条 Karin 链从链头沿唯一子骨走到底（有分叉就报错），
按顺序改名成一条游戏骨架里的线性配件链，链长不能超过那条配件链。链骨的 X 轴沿骨方向（UE 惯例，节点 `BoneForwardAxis = X_Positive`）。

| Karin 链 | 游戏骨架链 | 父骨 |
| --- | --- | --- |
| 裙 前中 `Skirt_0` / 后中 `Skirt_8` | `NPC_SakurajimaBoss_skirtA_01..` / `skirtB_01..` | pelvis |
| 裙 左右 `Skirt_1..7_L/R` | `NPC_SnowBoss001_skirtA..D_0N_l/r`、`NPC_GrassBoss001_Skin001_skirtB..D_0N_l/r` | pelvis |
| 尾巴 | `NPC_Female_Kunoichi01_cloth_A_01..08` | pelvis |
| 双马尾 | `NPC_Female_Kunoichi01_hair_0N_l/r` | head |
| 侧发 | `NPC_SakurajimaBoss_hairE_0N_l/r` | head |
| 兽耳 | `NPC_SakurajimaBoss_hairF_0N_l/r` | head |
| 头部丝带 | `NPC_GrassBoss001_hair_0N_l/r` | head |
| 前发 中 / 左右 | `NPC_SakurajimaBoss_hairA_0N`、`NPC_Female_Farmer01_hairB_0N_l/r` | head |
| 面颊发 | `NPC_WorldTreeBoss001_sidehair_0N_l/r` | head |
| 胸前丝带 / 领口丝带 | `NPC_SorajimaBoss001_chesthimoA_0N`、`NPC_WorldTreeBoss001_collarB_0N_l/r` | spine_03 |

挑链的条件（换 build 要重查）：链在骨架里是线性的、父骨对、长度够；玩家动画里没有这些骨的轨道（检查了 idle / jog / dance /
damage / jump，都只有 65 根基础骨）。手上丝带、鞋带、裙根、前发根这类很短的链直接并进父骨。r3 的身体网格共 189 根骨
（65 根基础骨 + 124 根链骨）。

## 4. 面部变形

VRM 的 `expressions.preset` 是空的；形态键在脸对象上（237 个）。每个游戏形变是若干形态键的加权和，跟网格一起重摆后写到头部网格上：

| 形变 | 配方 | r3 最大位移 |
| --- | --- | --- |
| `eye_close` | blink 1.0 | 3.9 cm |
| `eye_halfclose` | blink 0.55 | 2.2 cm |
| `eye_smile` | smile 1.0 | 2.5 cm |
| `eye_anger` | jitome 0.45 + mayu_angry_1 1.0 | 1.8 cm |
| `eye_pain` | `><` 1.0 + mayu_sad_1 0.8 | 7.2 cm |
| `eye_trouble` | mayu_sad_2 1.0 + LowerEyelid_up 0.3 | 1.0 cm |
| `eye_guruguru` | guruguru_1 1.0 | 7.9 cm |
| `mouth_open` | kuchi_A 1.0 | 1.4 cm |
| `mouth_smile` | wa 0.75 | 1.1 cm |
| `mouth_pain` | hawa 1.0 | 0.3 cm |
| `mouth_anger` | Λ_1 1.0 | 0.3 cm |

- 用户实机确认了眨眼；其余形变只在离线网格图里看过。r2 时发现嘴型偏弱、`mouth_pain` 原配方（△_2）看着怪，r3 换了源键；
  `mouth_pain` / `mouth_anger` 位移仍小，是 `hypothesis` 级的待改项。
- 脸上的腮红叠层（`Karin_Alpha`，408 个面）需要半透明材质，暂时删掉。
- 眼球骨 `eyes_l/r` 用 Karin 的位置；头部 AnimBP 的 `EyeLocationFix` 会按角色创建的眼睛位置参数移动它们，这一点没测。

## 5. 网格细节

- **双面裙**：VRM 是单面的（glTF `doubleSided=false`）。复制裙子的面、翻转，角法线取反，就有了内侧；不需要双面材质（剑星 r12 的做法）。
- **材质槽**：身体 3 个（`MI_Karin_Skin`、`MI_Karin_Hair`、`MI_Karin_Costume`；透明头发并进头发槽），脸 1 个（`MI_Karin_Face`）。
- **隐藏发型**：一个挂在 head 骨上、位于 head 关节上方 1 cm 的极小三角形（藏在头里），复制到所有发型路径。比删资产安全：蓝图和数据表的引用都还在。
- **插槽**：原版网格上的 `Socket_BackWeapon_R`（背负武器）要补到新网格上，偏移按 Karin 躯干厚度缩到 0.85。背武器的样子没在游戏里查。

## 6. 材质与贴图

- MI 只覆盖贴图参数，父级是游戏的 MI（[技术合同](TECHNICAL_CONTRACTS.md) §6）。
- Karin 只有基础色贴图：法线用 4×4 平法线，`MetallicRoughnessOcclusionSpecular` 用 4×4 常量（粗糙度取原版均值：皮肤 0.40、
  头发 0.60、服装 0.85；AO 为 1），`BaseColor Mask` 和覆盖法线遮罩全黑，SSS 颜色取原版女性身体 SSS 贴图均值。
- 用户的参考 mod 用自己的自发光母材质把颜色提亮，用户认为材质「不理想」；本项目改用游戏光照模型，没有自发光。
- 头发在游戏里偏淡紫，原因未查（[技术合同](TECHNICAL_CONTRACTS.md) §6）。
