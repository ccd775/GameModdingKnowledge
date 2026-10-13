# 角色替换（VRM → EVE）

构建脚本在项目目录 `Scripts/`：`build_body.py`（身体）、`build_face.py`（脸）、`build_hidden.py`（隐藏件）、
`render_preview.py`（与 EVE 并排的预览），UE 侧在 `Scripts/ue/`。下面是它们的方法和关键决定。

## 1. 坐标与拟合

- VRM 1.0 → EVE 坐标：绕 Z 转 +90°，×130（米到厘米 ×100，再按身高 ×1.30）。`case-derived`
- 逐骨仿射拟合到 `CH_P_EVE_09` 的关节：
  - 躯干从两腿中点到颈部统一缩放；锁骨保持长度；手掌绕前臂轴转正；头刚性直立；
  - 脚只平移。EVE 的脚部骨架是脚跟着地的姿势。
- 所有 Karin 网格做线性蒙皮变形；源里换装用的形态键按作者保存的状态烘焙进网格（body 上 11 个）。
- 丢弃 `Karin_Alpha`（腮红叠加层），`HairTransparent` 并进头发。

## 2. 权重重映射

- 权重改挂到 EVE 骨：手臂、腿的扭转按位置分配到 `Ab-*-Tw0/Tw1`；脊柱按区间分配（「帐篷」形过渡）。
- 方案 B 保留 Karin 的 140 根次级骨（裙 16 条 × 4、尾巴、11 条头部链、丝带），先加 `KO_` 前缀；
  后来改名落到游戏骨架的配件链上（见 [Kawaii 物理](KAWAII_PHYSICS.md) §1）。组根骨和手腕丝带被丢弃，
  权重并进最近的保留祖先；手腕丝带因此是刚性的。
- 最终网格 315 骨：313 根在游戏骨架里存在且父骨相同，另外 2 根是网格独有的裙摆辅助骨 `KO_SkirtExt_L/R`
  （由 BoneDrivenController 驱动，见 [Kawaii 物理](KAWAII_PHYSICS.md) §4）。

## 3. 运行时改比例（reprop）

骨架是 Animation 平移重定向：网格只能按 EVE 的关节位置绑定，Karin 的腿会被拉成 EVE 的腿长。拟合时 EVE 对 Karin@1.30 的
测量值：大腿 44.9 / 36.6（+22%）、小腿 39.8 / 37.2、髋高 100.0 / 83.3（+20%），躯干基本相同。

不做 reprop 时的折中方案被拒绝：EVE 脚踝高 15.3、Karin 9.5，只能把鞋底拉长 5.8 cm 去填，鞋底看起来很厚。

做法（用户选择了运行时方案，已在游戏里验证）：

1. `build_body.py --reprop`：拟合前编辑 EVE 的导出骨架，把大腿、小腿缩到 Karin 的长度（子骨偏移沿骨轴缩放，
   大腿 k = 0.811、小腿 0.935），再把 Root 以下整体下移，让脚踝落在 Karin 的脚踝高度（下移 16.875 cm，髋高 83.1）。
   结果：腿部拟合 σ 1.0，脚底无缝，鞋保留原来的 19 cm。
2. `ue_build_abp.py`：拿网格 bind 姿态和 EVE 原始姿态（游戏路径上的 dummy `CH_P_EVE_01` 网格）逐骨比较，
   每根平移不同的骨加一个 ModifyBone（Translation 加性、ParentBoneSpace，值 = 两者的局部平移差），放在 ControlRig
   之后、物理之前。本例 14 根：`Bip001`、两侧小腿/脚/扭转骨/膝辅助骨。
3. 腿上的碰撞胶囊按 k 沿骨轴缩短长度和偏移。

验证：比例在游戏里看起来是 Karin；鞋正常，idle 和跑步时脚贴地；脸网格跟着降低的头走，与头发对齐。

未检查：深蹲、跪地、攀爬、梯子等交互；膝盖弯得很深时脚可能陷地，手可能对不准边缘。

## 4. 脸

- `build_face.py`：Karin 的脸放进 `CH_P_EVE_Face_Jali3` 的 10 骨脸部骨架（全挂 `Bip001-Head`）。
- 169 个 JALI 变形里合成了 61 个（眨眼、眼睑、视线、眉毛、口型、舌头），由 VRM 的形态键组合而成；
  左右和视线方向用几何方法核对过。
- FBX 导入时会警告 bind pose 无效并重建，游戏里脸的对齐没有问题。
- 表情在游戏里没有检查过（`hypothesis`）。

## 5. 隐藏原版部件

`build_hidden.py` 生成只有一个 0.01 cm 三角形的网格，替换 `EVE_HR_01`、`CH_P_EVE_Hair_PonyTail_2`、
`ACC_EAR_12M`。它们和脸一起打成一个独立的包，所以对所有服装生效。

## 6. 材质与贴图

- 源 VRM 只有 5 张颜色贴图，没有法线和 ORM。UV 覆盖率：服装 40%、头发 48%、身体 67%。用户拒绝 AI 放大，
  保留原始 2048 颜色贴图。
- `build_body.py` 按 UV 岛光栅化（1024²，8 px 外扩）为每个部件生成遮罩：
  - `CostumeORM`；
  - `CostumeDetail`：R = 毛衣针织，G = 裙子/内衣斜纹，B = 袜子尼龙，按底色亮度门控；
  - `CostumeFuzz`（G）；头发/耳朵/尾巴的 `HairORSSMap`。
- 细节层平铺 = 1 / (uv_per_cm × tile_cm)，tile 取针织 6 cm、斜纹 4 cm、尼龙 3 cm。在 EVE 50 上标定过：
  麂皮层约 13.6 cm 一块，细布 2.9 cm，带子 3.3 cm。
- MI 标量：Pattern TextureIntensity 0、RoughnessIntencity 0、Brightness 1，让 Karin 的颜色和 ORM 粗糙度保持原样。
- EVE UV 用的遮罩用 4×4 中性贴图覆盖。
- **双面**：VRM 每个材质都是单面（glTF `doubleSided` false），裙子从里面看是空的。静态开关不能改，所以在
  `build_body.py` 里给裙子复制一份反向面（1488 面），并把这份的自定义角法线取反。实机确认从下往上看能看到裙子里面。

## 7. UE 导入

- `ue_import_body.py` 在游戏路径上建 dummy 骨架、dummy 物理资源、dummy 父材质和布料贴图（都不打包），
  导入网格和 Karin 的 MI、贴图到 `/Game/Mods/KarinOriginal`；先删旧网格再导入，材质槽顺序 = FBX 顺序。
- `ue_assign_materials.py` 在导入后再指定一次材质。
- `cook_and_pack.ps1`：cook → 只挑新资源 → retoc → 可选安装。`verify_pack.ps1` 检查骨数、空材质、变形数。
