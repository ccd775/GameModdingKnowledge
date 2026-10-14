# 角色拟合

源模型：Karin_Original 的 VRM 1.0（34,304 顶点、46,414 三角、6 材质 / 5 贴图、148 根带权骨、39 个 spring、237 个脸部 morph），
不随本库发布。工具：`sm2_karin_geo.py`（重摆、拟合、权重）、`sm2_batch.py`（批量写入）、`sm2_face.py`（表情）。

## 1. 重摆与拟合（`sm2_karin_geo.py`）

1. **LBS 重摆**：把 T-pose 的 Karin 按骨架逐段转到英雄 bind 骨架（A-pose）的方向，覆盖肩、上下臂（手的扭转只分一半）、手、手指、拇指、腿、脚。
2. **TPS 变形**到英雄关节上：拟合器 `sm2_fit.py` 与对马岛构建器同源，单位 cm，x 前 / y 左 / z 上。
   - 头的子树（脸、头发、耳朵）跟头部映射刚性移动，不让 TPS 拉变形；
   - 脚底抬到英雄的地面高度。
3. **权重**只落到英雄的变形关节（`u2 & 0x80`）上：
   - 脊柱链、四肢的扭转辅助骨按沿骨的位置分配；
   - 裙子复制裙下臀部 / 大腿表面的权重（见 §2）；
   - 尾巴给 pelvis，头的子树给 head；
   - `--dyn` 时，链上的部件保留为自己的 `karin_*` 关节（[物理](PHYSICS.md) §1）。
- 参数（`case-derived`）：
  - `--scale 1.45`：Karin 的整体比例；
  - `--head-scale 1.45`：等于 `--scale` 就是 Karin 原比例。T8 及以前用 1.3，用户反馈头偏小；
  - `--neck-drop 3`：颈部比英雄的 neck 关节低 3 cm；
  - `--shoulder-fit 0.3`。
- **一种骨架签名只拟合一次**。签名 = 拟合要用的关节（名字 + bind 世界位置，取 mm）的 SHA-1 前 12 位（`survey_targets.py`），108 个目标模型共 7 种；拟合结果缓存在 `build_sig/<签名>/`，
  改了拟合参数必须加 `--refit`。物理链参数例外，构建时直接读当前值。

## 2. 裙子

- T4b 实机：蹲下时大腿从裙子侧面穿出。原做法按高度在骨盆和大腿之间插值。
- T9 起改成**复制裙下臀部 / 大腿表面的权重**（`skirt_transfer`，高斯核 3 cm），再按（绕身角度, 高度）平滑 2.5 cm，不计半径，
  让褶子内外层的权重相同。
- 离线姿势检查（`sm2_pose_check.py`，按游戏骨架摆蹲 / 栖 / 坐 / 跨步，统计大腿穿出裙子的比例）：

  | 姿势 | 修改前 | 修改后 |
  | --- | --- | --- |
  | 蹲 | 10.4% | 1.8% |
  | 栖（膝盖外展 50°） | 11.6% | 2.1% |
  | 坐 | 6.2% | 0.7% |

  用户实机确认蹲姿正常（T9）。
- SM2 的 AnimDynamics 没有碰撞体，所以裙摆保持静态权重，不做成链。

## 3. 合并网格与写入（`sm2_batch.py`）

- Karin 的各部件合并成一个网格：UV 压进 2×2 图集（脸 | 身体 / 头发 | 服装），`face_alpha` 丢弃。
- 只用一个材质：`characters/hero/karin_original/materials/karin_atlas.material`，模板是 Kraven 手套的 `basic_normal_gloss`。
- 贴图四张：`karin_atlas_c`（4096 BC7）、`karin_atlas_g`（512 BC1，按象限给不同光泽）、`karin_flat_n`（平法线）、`karin_cloth_m`。
- 每个目标模型：
  1. 按关节名重映射权重，缺的关节退到最近的祖先；
  2. body/Default look 第一槽的全部 LOD 共用一块几何；
  3. 其余网格退化（刀具道具保留）；
  4. 删除 strands / Morph / Ziva 段；
  5. 给用到的关节补 0x80 变形位。
- Look 组覆盖：一些预设里看不到 body 槽（tuxedo、teacher、spider_suit、dj_suit_group），Karin 会在这些预设里隐身。
  `cover_looks` 给每个这样的非叠加组再挂同一块几何（T5b）。
- 三个独立头模型：`--face` 时换成绑好面部骨骼的 Karin 脸（§4），不加 `--face` 时清空。

## 4. 表情（`sm2_face.py`，T7）

- 不戴面罩时，脸在独立的头模型上：`hero_peterparker_head`（577 骨）、`hero_milesmorales_head`、`hero_peterparker_young_head`。
  这些头模型约有 500 个 `FACIAL_*` 关节（密集的补丁式叶关节），由对话和过场动画驱动。
  - Peter 的嘴唇 / 舌头挂在 `FACIAL_C_Jaw` 下；Miles 的挂在 `FACIAL_C_LowerLipRotation` 下，而且没有 `_analog` 系列。
  - 眼球网格只绑 `FACIAL_*_EyeParallel`。
- 做法：
  1. 用标志点把 Karin 的脸变形到原头的脸上；
  2. 每个脸部顶点复制同一区域（上 / 下眼睑、上 / 下唇、眉、舌）里最近的原头顶点的皮肤权重；虹膜跟 `*_EyeParallel` 走；
  3. 顶点跟多少运动（alpha）由 Karin 自己的 blendshape 决定：她的眨眼、嘴型、眉毛、舌头形状从来不动的地方，刚性留在 `head` 上。
- 头模型有自己的绑定姿势（Peter 头关节比战衣高 4.4 cm、前 10 cm），运行时按关节名跟随身体，所以网格要按「头关节局部坐标」换算进头模型空间。
- 同一家族（Peter / Miles / young）的各个拟合，先按头关节坐标刚性对齐到家族参考战衣的拟合（`head_fix`），
  这样共用的头模型才对得上每个身体的头发。Peter 便装原来差 19 mm，对齐后为 0。
- 戴面罩时，战衣的 `mask` look 第一槽放一张静态的 Karin 脸（便装不放）。
- 限制：Peter 的眼睑关节行程约 1 cm，Karin 的动漫眼睑要约 4 cm，靠迁移权重做不出完整眨眼，所以眼睑保持静止。
  眨眼要用 Morph2（矫正形变，无名字，未解）。
- 离线闸门 `sm2_verify_face.py`：面罩脸与头模型脸逐顶点比较（0.12 / 0.33 mm）、权重和为 1、0x80 位齐全。

## 5. 物理链的拆分（v1 / v2）

- `--dyn` 拟合把 Karin 的 12 条 spring 链保留为 48 个 `karin_*` 关节（双马尾、侧发、前发、耳朵、头上丝带、尾巴）。
- 物理不放在战衣里（[物理](PHYSICS.md) §3），所以要按三角形拆分：
  - 一个三角形只要有一个顶点在 `karin_*` 上的权重 ≥ 0.5，就搬去载体模型（每个签名 5,066 个三角形）；
  - 其余留在战衣身体上（35,876 个），身体里残留的 `karin_*` 权重退回 head / pelvis（`sm2_prop_test.chain_fit` / `strip_body`）。
- 尾根顶点有最多约 0.6 的 spine / spine_helper1 权重。载体里要有这两个关节并把它们映射到身体，否则尾巴中段会错位（T21）。
- 判断家族用文件夹名里是否有 `miles`（`sm2_face.family_of`）。只看 `/hero_spiderman_miles_` 前缀会把
  `hero_spiderman_milesmorales`（Miles 经典战衣）误判成 Peter。
