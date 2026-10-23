# 角色拟合

`karin_build.py`（Blender 5.0 + Witcher3-Blender-Tools）把 Karin 的 FBX 拟合到杰洛特的 `man_base` 骨架上，写出身体网格、脸部网格、贴图、
dyng 规格和表情规格。下面的数值都是 Karin 的案例值（`case-derived`），参数名是脚本 `CFG` 的键，可以用 JSON 参数覆盖。

## 1. 原生骨架路线（`invariant`）

- `man_base` 的静止姿势不动。W3 的动画带每根骨的平移，骨长只能是杰洛特的；把骨架改成 Karin 的比例，动画一播就被拉回去。
- 所以反过来：**按骨把 Karin 的几何仿射到 `man_base` 的关节上**。每根 Karin 骨一个 4×4 映射 M（平移到目标关节、沿骨轴拉伸到杰洛特的段长、
  横截面单独缩放），顶点按 Karin 自己的权重做线性混合；然后把权重重定向到 `man_base` 的骨（[§4](#4-权重)）。
- 结果是一个比例接近少女、但关节位置是杰洛特的角色：身高、四肢长度、肩宽都由杰洛特的骨架决定。

## 2. 比例

| 部位 | 做法（最终值） | 来历 |
| --- | --- | --- |
| 躯干 | Karin 髋关节连线 → `man_base` 两个大腿关节，Karin 的 Neck → `neck`；竖直缩放 kv ≈ 1.675；宽 / 深：髋 1.675 / 1.675、腰 1.574 / 1.608、胸 1.474 / 1.541（`chest_w_ratio` 0.88、`chest_d_ratio` 0.92，腰取两者平均） | v0.2 全身都用 1.675：和 ×1.5 的头、四肢放在一起，上身显胖（用户 v0.2 反馈）→ v0.3 |
| 上臂 / 前臂 | 沿骨轴拉到 `man_base` 段长（×1.34 / ×1.53），横截面 `arm_cross` 1.38 | |
| 大腿 / 小腿 | 段长 ×1.74 / ×1.53，横截面 `leg_cross` 1.5 | |
| 头 | ×1.5（`head_scale`） | |
| 颈 | 只沿轴拉 ×1.5（`neck_along`），头因此比 `man_base` 头关节低 2.66 cm | v0.1 拉到 `man_base` 全长（约 ×2.0）：用户说脖子太长 |
| 手 | ×1.4，手指按骨的朝向对齐 | |
| 脚 | 平放（`foot_h` 1.3），脚踝高度不变 | |
| 狐尾 | 绕根部 ×0.75（`tail_scale`） | |

## 3. 窄肩：在待机姿势里拟合（v0.4.0）

- 杰洛特的肩关节在 ±0.208 m，Karin 自己缩放后的肩在 ±0.11 m。直接放上去是一个挂在宽肩关节上的少女（v0.2 用户：肩很宽）。
- 做法：上臂挂在一个支点 P 上，P 在肩关节内侧 `arm_root_inset` 5 cm（水平、朝锁骨内端方向，跟着 `l_shoulder` 走）；Karin 的锁骨区整个平移到 P
  （`shoulder_shift_frac` 1.0）。
- **肩和上臂（Karin 权重在 Shoulder / UpperArm 上的约 1140 个顶点）在杰洛特的待机姿势里拟合**：待机姿势取
  `animations\man\movement\man_geralt_movement.w2anims` 里 `locomotion_idle` 的第 0 帧（插件在构建时导入）。先用 Karin 自己的蒙皮，把上臂从 P 重新对准
  待机姿势的肘，得到目标形状；再通过最终的 `man_base` 权重解回绑定姿势：`v_bind = (Σ w_i G_i)^-1 · target`。这样无论辅助骨怎么动，
  待机时看到的就是这个形状。
- 被否决的 v0.3.0：把一个固定偏移按假设的 80° 下垂角转回绑定姿势。可是 `l_shoulderRoll`（上臂根部 325 个顶点）在待机里几乎不转，
  `l_bicep` 转约 57°，待机时上臂根部出现一道缺口（用户 v0.3 反馈；离线用原版待机动画复现）。
- 上臂根部的权重保留 `shoulderRoll`（`ua_shoulder_roll`）：去掉它，跑步摆臂时出现凹陷。
- 离线检查：在原版动画（待机、跑、冲刺、持剑待机、举过头顶的攻击）里渲染，没有缺口；举手过头时肩胛附近的褶皱和 v0.3 相当（已知限制）。

## 4. 权重

按原版杰洛特身体的习惯重定向（`make_retarget`）：

- 脊柱权重按高度在 `pelvis` / `torso` / `torso2` / `torso3` 之间分；
- 前臂只放在 roll 骨上（扭转由 roll 骨承担）；上臂 `shoulderRoll` / `bicep2` / `bicep`；大腿根 `legRoll` / `legRoll2`；膝 `kneeRoll`；
- 每顶点最多 4 个影响；
- 物理链（头发、耳、尾、裙、丝带）的骨保留成 dyng 骨（[物理](PHYSICS.md)），不重定向。

## 5. 裙子跟随大腿（v0.2.0）

- 抬腿时大腿从裙子的节点之间穿出来：dyng 节点之间是空的，球形碰撞（大腿代理的最小距离链接，每节点 5 个代理也一样）挡不住两节点之间的面。
- 做法 `skirt_follow_thighs`：髋关节以下的裙子顶点，一部分权重混到 `l_thigh` / `r_thigh`：从髋关节上方 3 cm 处的 0（`skirt_follow_top`），
  线性升到下方 15 cm 处的 0.6（`skirt_follow_full`、`skirt_thigh_follow`）；左右用宽 2.5 cm 的 logistic 分配（`skirt_follow_split`）；剩下的权重留给 dyng。
- 代价：裙摆自己的摆动比头发小；腿抬到接近水平时仍可能轻微穿插。

## 6. 调参入口

`chest_w_ratio` / `chest_d_ratio`、`arm_root_inset` / `arm_root_lift`、`shoulder_shift_frac`、`arm_cross`、`neck_along`、`skirt_thigh_follow` /
`skirt_follow_*`、`albedo_scale`。改完先跑 `karin_preview.py`（导出的 w2mesh 重新导入、与杰洛特原版身体叠在一起的正 / 侧视图和一个测试姿势），
再在游戏里看待机的正面、背面和侧面。
