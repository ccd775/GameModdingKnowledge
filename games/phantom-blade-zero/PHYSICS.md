# 物理

结论：次级物理全部用 **Chaos 骨骼网格布料**（`UClothingAssetCommon`），挂在身体网格的材质段上，碰撞体是专用的物理资产。
游戏原有的链骨和后处理 RigidBody 不用。

## 1. 被放弃的路线：链骨 + RigidBody（`rejected`）

第一版把 Karin 的头发、裙子挂到游戏的链骨（`Hair_0..3`、`bns_skirt_*`）上，并替换后处理动画蓝图 `ABP_Hun_PostProcess` 的 RigidBody 覆盖物理资产
`SkinParts/Hun_Cloth_Streamer_Physics`（11 个运动学碰撞体 + 链，参数照师父调过的值）。结果侧发、双马尾、裙摆被拉长：游戏的动画给每根链骨打了关键帧，
后处理里还有别的节点在摆它们。构建脚本保留了这条路（`chains=True`），默认关闭。

## 2. 分段

每一块会动的部件是身体网格里的一个材质槽，`cloth.json` 每段一项（槽名、掩码、最大距离、参数），插件 `CreateClothFromSlot` 从槽建布料并绑回同一段。

Karin_Original（成年 / 少年）：

| 段 | 掩码要点 | 关键参数（最终） |
| --- | --- | --- |
| 裙摆 `MI_Karin_Skirt`（用外壳 `MI_Karin_SkirtSim` 模拟，见 §4） | 只固定腰带（高度的 8%），深度 60% 处起全自由；backstop | 驱动 0.3、重力 0.5、碰撞厚度 2.5、CCD |
| 双马尾 `MI_Karin_HairTail` | 链长径向 | 驱动 0.12、阻尼 0.03、速度比例 1.0、最大距离 0.45 × 链长 |
| 尾巴 `MI_Karin_Tail` | 固定到伸出裙子的地方（尾巴在裙摆以上、裙子半径以内的顶点） | 驱动 0.12、重力 0.4 |
| 耳朵 `MI_Karin_Ear` | 固定区 0.3 × 耳长 | 驱动 0.5、阻尼 0.1、重力 0、最大距离 0.22 × 耳长、无碰撞 |
| 刘海与侧发 `MI_Karin_HairFront` | 在与其余头发相接的 89 个顶点处锚定，自由范围到最长发束的 0.85；删除内层面 | 驱动 0.2、重力 0.3、无碰撞、不投影 |

Karin_PicodraTech（按源骨权重选面，面的平均权重占比 > 0.5）：

| 段 | 来源 | 参数 |
| --- | --- | --- |
| `MI_Karin_HairTail` | Hair_Tail | 最大距离 0.45 × 链长、驱动 0.12、重力 0.5 |
| `MI_Karin_Tail` | 尾巴 + 系在上面的 Back_Ribbon / Tail_Ribbon（合成贴图，见 §5） | 0.45 × 尾长、驱动 0.12、重力 0.4 |
| `MI_Karin_HairFront` | Hair_Front* / Hair_Side*（不含 Hair_Front_Root），删内层面 | 0.4、驱动 0.2、无碰撞 |
| `MI_Karin_Ear` | Ear_*，固定到耳罩以上 1 cm（耳罩随头刚性） | 0.22 × 耳长、驱动 0.5、重力 0、无碰撞 |
| `MI_Karin_Jacket` | Outer*、Pocket_String*，在与蒙皮外套的交界处锚定 | 0.4、驱动 0.3、阻尼 0.08、CCD、惯性 0.8 |
| `MI_Karin_Cord` | 耳机线 Code*，锚在 Code.L / R | 0.3、驱动 0.15、重力 0.6 |
| `MI_Karin_Strap` | 腰带垂带 Belt_Ribbon | 0.35、驱动 0.2、重力 0.6 |

腿环、大腿环、腰带绳不做布料：按最近 8 个皮肤顶点的权重跟随（`follow_skin`，按链上的位置渐变）。

## 3. 碰撞体

- `cloth_collision.json` → 插件 `BuildPhysicsAsset` 建物理资产 `PA_Karin_ClothCollide(_Young)`：大腿胶囊（皮肤距离的第 85 百分位）、臀部球（第 85 百分位）；
  成年 10.2 cm、少年 10.9 cm。从 70 / 75 百分位调上来，因为跑动时大腿穿出裙片。
- PicodraTech 的 `_coll` 组：皮肤 + 饰品占比 < 0.1 的 ClothA 顶点。
- 少年版的布料复用 `PA_Karin_ClothCollide_Young`：旧布料还引用它时删掉它，下一次保存身体会在 AsyncLoading2 里断言失败。
- 求解器：插件 `SetClothSolver(Mesh, 3, 2)`（Python 拿不到 `UChaosClothSharedSimConfig`）：3 次迭代、2 个子步。Chaos 的刚度与迭代次数无关，
  所以这样只收紧壳和碰撞，不让驱动变硬。

## 4. 百褶裙：外壳模拟、backstop、法线

问题与解法（Karin_Original 的裙摆，五轮用户反馈）：

1. **双面裙变成同一批粒子（第三轮）。** 母材质是双面的，复制一层反向面后，`ClothingAssetFactory::ImportToLodInternal` 把同位置的顶点焊成同一个粒子：
   每个三角形出现两次，绑定法线互相抵消（退回 +X），边约束加倍，裙摆看起来像湿的。改成单面。
2. **大腿穿出（第四轮）。** `probe_r4.py` 在 Blender 里摆姿势（大腿外展 12°、跑步 60° / 85°、弯腰跑、蹲）量蒙皮后的裙子和皮肤：除了蹲和弯腰时的前腰（≤ 1.9 cm）都没有穿透，
   所以穿模来自模拟（重力、惯性把裙片往里推）。加 backstop（插件掩码 `backstop`：距离 0、半径 50，只给法线背离裙轴 > 0.3 的自由粒子）、`bUseCCD`、
   `bUseLegacyBackstop=false`。焊接后粒子的导入法线只是其中一个源顶点的渲染法线（常是侧向的褶壁），插件把带 backstop 的布料的 `Phys.Normals`
   换成按面积加权的面法线（方向与导入法线一致）。
3. **沿褶线的光泽闪动（第五轮）。** 裙子是一面宽的工字褶（16 道），绑定（`BindToSkeletalMesh` → `GenerateMeshToMeshVertData`）用模拟网格的平均法线重建每个渲染法线，
   约三分之一的面角上平均法线与面相差 60–90°，褶子一开一合法线就摆。解法：`skirt_shell` 在外层褶上生成一层平滑外壳（19 圈 × 32 列，放在
   `MI_Karin_SkirtSim`），插件掩码 `sim_slot` 用外壳建布料、把外壳段禁用（等同编辑器的「从网格移除」），让裙子段绑到外壳上。内层褶在外壳内最多 1.9 cm。
   副作用：褶子跟着外壳走，不再一道一道张开。

## 5. 硬限制（UE 5.7）

- **一个布料资产每个 LOD 只能绑一个 section**（`UClothingAssetCommon::BindToSkeletalMesh` 的 LodMap 检查）。要一起动的部件放进同一个槽；
  PicodraTech 的蝴蝶结在服装图集上、尾巴在头发图集上，于是 `combine_texture` 按 UV 岛做架子装箱，合成一张 `Karin_TailComb`（2048²、17 个岛，
  第一次整块裁剪缩成了半分辨率，改成按岛装箱）。
- **焊接后的退化三角让整段建不出来。** `UClothingAssetFactory` 焊接同位置顶点后遇到零长边 / 零面积三角就报 `CreateFromSkeletalMesh failed`，
  整个布料段没有了。构建器的 `drop_degenerate` 先三角化布料段，删掉边 < 1e-3 或面积 < 1e-6 的面（PicodraTech 双马尾删了 4 个）；`ue_cloth.py`
  任何一段失败就让这一步失败（原来只写日志继续）。
- **闭合发束的内层面要删。** 刘海是闭合的壳（外层 + 内层在边缘相连），焊成粒子后 260 / 788 个粒子的法线抵消过半，渲染出暗斑。删掉朝发心的面
  （与发心方向点积 < -0.3，361 个），双面材质显示外层的背面。

## 6. 证据

裙摆五轮、耳朵、刘海暗斑、裙摆光泽由用户实机确认（`runtime-confirmed`）。PicodraTech 的七段只做了构建、读回（每个身体 7 个布料资产）和装进游戏，
用户未反馈（`offline-accepted`）。大动作（翻滚、处决、骑乘）下的穿模没有专门测。
