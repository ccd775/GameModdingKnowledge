# 角色替换：PT 模板、V 改造、Karin_Original 构建

数值都是 `case-derived`（build `24901913`，用户的 KarinPT 包与 Karin 源模型）。

## 1. PT 身体网格模板（参考 mod 反推）

- 骨架 = 原版 Dante 339 骨 + 142 根 Karin 专用布料 / 头发骨（世界旋转为单位阵）。PT 包的所有身体槽位
  用同一份 Karin 几何。各槽位网格的 Hip 随角色不同（见 [技术合同](TECHNICAL_CONTRACTS.md) §4），
  Nero 魔人 `pl0010` 的骨架也不同（360 骨），所以每个槽位都要以对应的 PT 网格为模板单独构建。
- 子网格：4 个真实子网格，加上若干零面积占位子网格。占位子网格的作用是保留目标角色的全部材质名。
- 头、头发、过场头部换成 2244 字节的空网格，把原角色的头和头发藏掉。Karin 的头和头发都长在身体网格里。
- 几何放置：把 Karin 源模型的手部和脸部分别 ICP 到 PT 网格上，得到
  `身体 = 源 × 1.5688 + (0, 0.00575, 0.02397)`、`头 = 源 × 1.7063 + (0, −0.1402, 0.0289)`（RE 空间，单位米）。
  两者按顶点的 Head 子树权重混合，所以 PT 的头比身体大约 9%。PT 的脸、耳朵和头发与这条变换吻合。

## 2. KarinPT → V（从 PT Nero 网格改造）

1. 导入 PT Nero 身体网格，把 Hip 的世界平移挪到 V 原版的 `(0, 1.08, 0)`，Hip 的子骨重算 local，
   世界位置保持不变。
2. 补上 V 独有的 45 根骨（无权重）：`world = V_local @ parentWorld`，四种矩阵一起写。
   V 的骨骼约束和物理数据会引用这些骨，缺了可能出问题。
3. 占位子网格改名为 V 的材质名（`m_handaccessories / m_pendant / m_bone / m_handR / m_chain`），
   不够就复制。裸身 `pl0210` 把 `m_handR` 的占位留在 group 5。
4. 导出后把源网格的法线 / 切线流原样搬回（Blender 重导会改约 18% 的法线），再断言几何、法线、
   按骨名的权重都和 Nero 网格一致。结果为 526 骨、9 个材质名。
5. 身体 MDF：取 Nero 的 `pl0000.mdf2.10`，把 `m_glove` 克隆两份，第 4–8 个材质改名为 V 的占位名，
   贴图指向独立文件夹 `V_KazamiRika_tex`（与另外两个 mod 的贴图不冲突）。所有身体 MDF 变体都用它：
   默认、`_blood / _burn / _freeze / _slow / _vmode / _wet`、`c00`、`pl0210`（含 `_astral`）、
   裂纹 `pl0230/0231/0232`。
6. 头部：空网格，加上 V 原版的 7 个头部 MDF，只把 `m_teeth` 的 NormalRoughnessMap 指向签名贴图。
   头发：空网格，加 Nero 的头发 MDF（改指向）。过场头部：空网格。
7. UI 只替换 `ui0040_02`、`ui2100_30`、`ui2100_32`，用 Nero 的对应图（与 PT 包换图的规律一致）。

Karin 的腿比 V 短约 3 cm，曾担心 V 的动作里脚会悬空。用户在标题画面确认「脚基本贴在地面上」。

## 3. Karin_Original 从源模型构建

源：Karin_Original 的 authoring blend（来自 RE4 项目）。对象有 `Body`（脸）、`body_2`（皮肤）、
`hair`、`kemomimi`、`tail`、`pullover`、`skirt`、`shoes`、`knee_socks`、`underwear`；
材质有 `Karin_Face / Karin_Alpha / Karin_Body / Karin_Hair / Karin_Hair_Transparent / Karin_Costume`；
另有 VRM SpringBone（耳朵、头发、缎带、尾巴、17 条裙链、鞋标签等）。

对每个 PT 身体网格模板（`pl0000/0010/0100/0110/0120` 取自 PT 的 Nero / Dante 包，`pl0200/0210`
取自 §2 的 V 网格）各跑一次 `ko_build`：

1. 导入模板，删掉 142 根 PT 专用骨；DMC5 骨架和 bind 原样保留。
2. 加入源模型的 spring 骨，命名为 `KO_<name>`，世界旋转为单位阵，挂在单位旋转的 `KO_Base_<DMC骨>` 下。
   这样链的父骨系等于世界系，chain 方向可以直接用世界坐标算（见 [chain 物理](CHAIN_PHYSICS.md) §2）。
   源里有个命名笔误：`Hair_tail_L.005_end 1` 实际是右侧双马尾的末端，要映射成 `KO_Hair_tail_R_005_end`。
3. 人形骨映射：`Hips → Hip`、`Spine → Waist`、`Chest → Chest`、`UpperLeg → Thigh`、`LowerLeg → Shin`、
   手指按节映射。眼睛和 `Cheek*` 的权重并到 `Head`：**没有表情**。
4. 几何按 §1 的身体 / 头部变换放置。
5. 删掉 `Karin_Alpha` 的面。这是源里默认藏在头内的叠加层。
6. 法线：
   - 先按角记录作者设定的法线。
   - `body_2` 的自定义法线是坏的（1091 个零向量角，约 10% 朝内，多在衣服下面），清掉，改用平滑几何法线。
   - RE 导出器每个顶点只保留一个法线，所以在相邻面法线差超过 2° 的边上拆开顶点（衣褶、鞋底、毛衣缝），
     再用 `normals_split_custom_set` 把法线写回去。
7. UV 映射到 4096 图集的四个象限；补第二套 UV（= UV1）和白色顶点色，与 PT 网格的流一致。
8. 合并后按用途拆成皮肤 / 服装 / 头发 / 脸，名字沿用模板的 `Group_0_Sub_0..3`，所以材质名和占位子网格都保持不变。
9. 导出，并用 `ko_verify` 过闸门（见 [验证与发布](VALIDATION_AND_RELEASE.md) §1）。

结果：约 33.8k 顶点、46k 三角形，144 根有权重的骨，142 根 `KO_*` 骨（含 `KO_Base_*`）。

## 4. 贴图与材质

- 图集 4096²：左上头发，右上服装，左下脸，右下皮肤（源里头发 / 服装是 4096，脸 / 皮肤是 2048，统一缩到 2048 一格）。
- albm：RGB 为颜色，**A = 255**。Env_Emissive 用 alpha 控制自发光，见 [排障手册](TROUBLESHOOTING.md)。
- NRMR：平坦 `(128,128,255,255)`，1024，BC7_UNORM。atos：`(255,0,255,255)`，与 PT 相同。
- 材质沿用 PT MDF 的 `MasterMaterial/Master/Env_Emissive.mmtr`。PT 贴图路径
  `*_KazamiRika_tex/...` 改指 `KarinOriginal_<角色>_tex/KarinOriginal_<角色>_{albm,nrmr,atos,sign_albm}.tex`。
  每个包用自己的贴图文件夹，三个包可以同时安装。
- 使用图集的材质清掉双面位（bit0），三包合计 1404 个材质条目。
- PT 包自己的 `*_KazamiRika_tex` 文件夹不带走。PT Dante 包引用了一个它自己没带的
  `Dante_KazamiRika_tex`，改指向之后不再有悬空引用。

## 5. UI 立绘与签名

- 立绘用 Blender 平光渲染：放松姿势，`ui0040` 脸部特写 1024²，`ui2100` 全身 1024²，透明背景，
  编码为 BC7_SRGB（头 `0x700`）。
  Blender 预览如果全黑，是预乘 alpha 造成的，把图像 `alpha_mode` 设为 `NONE`。
  菜单里实际显示的效果**没有检查**。
- 签名贴图：标题行用黑体重绘「KarinOriginal replaces X」（颜色 127,127,255），作者行和声明行按像素
  从 PT 签名拷贝。
