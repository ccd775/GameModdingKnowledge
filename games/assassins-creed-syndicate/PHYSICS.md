# 物理

方法与骨架规则来自大革命（完整仓库里的 `games/assassins-creed-unity/PHYSICS.md`）：Karin 的次级骨（`KP_*`，35 个链根、139 根 KP 骨）生成一个新的附加骨架，BallJoint 没有弹簧，
用「锥中心逆着下垂方向偏一个锥角」让重力把静止姿势托在锥边（rest-on-edge）。这里记录枭雄的差异和 v1–v5 的调参轨迹。

## 1. 宿主

- 头部表第 14 列是头发附加骨架；头发网格反正去掉了，这一格改指 `Karin_Phys_<twin>`（`build_mod.PHYS_HOSTS`：雅各布的 Head、伊薇的 Head 和 Head_SpecialLOD、
  莉迪亚的 Head），骨架和它的 `BallJointCommonData` / `LiteRagdoll` 作为新对象嵌进每一份头部表所在的数据文件（64 份）。莉迪亚的头部行缺这一格，用
  `bt_tool.edit(add_missing=True)` 补上。
- 模板是雅各布的头发附加骨架 `ACVI_CHR_P_JacobFrye_Hair`（`SkeletonType` CUSTOM 和非骨字段沿用，骨列表重建），`--id` = `CHARS[twin]["base"] + 0xF00`。
- 每位双胞胎 121 骨、55 个 BallJoint（v4 是 59 个）；Karin 的 LOD 175 骨，≤ 255。

## 2. 与大革命的差异（构建前核对过）

| 项 | 枭雄 | 依据 |
| --- | --- | --- |
| `ChildBoneCount` | 后代数（同大革命） | 18 个服装骨架 486 / 486 根骨 |
| 骨的额外字段 | `MirroringTag`（空）、`EnablePoseDrivenWrinkles`（False） | 每根原版骨都有，生成器照写 |
| 裙片碰撞关节 | `GravityMode` = GlobalGravity（0）+ CommonData | 241 个原版 BallJoint 没有 `GlobalOwnGravity`；带 CommonData 的用 GlobalGravity / LocalOwnGravity / LocalGravity |
| GravityMode 枚举 | GlobalGravity 0、LocalGravity 1、LocalOwnGravity 3 | 原版统计 |
| 偏移约定 | 同大革命（`LocalPitchOft` 绕局部 Z、`LocalYawOft` 绕局部 Y） | 153 个带偏移的 GlobalGravity 原版关节里 144 个的锥中心在绑定方向之上，六种轴向 / 符号组合里最好 |

## 3. `LocalOwnGravity` 的反证（`rejected`）

- v1（= 大革命 v6 / v7 的模型，链节停在锥边，摩擦 1.5–3 / 1–2）：用户「两个角色都被正确替换了，有物理有表情」，但耳朵和双马尾「太硬，稍微一动就到限位」。
  原版伊薇的头发是 30° 锥、摩擦 0.2 / 0.3。
- v2 参照原版 `EvieFrye_Outfit11` 的饰物（`LocalOwnGravity`，OwnGravity (15, 0, 0) / (20, 0, 0)，20°，摩擦 0.5–0.7 / 0.7–1），推断 OwnGravity 沿骨自己的 +X，
  当回弹用：耳朵 20°、g 12；双马尾五节都模拟、10°、g 15。agent 本机跑动转身时双马尾呈软弧并回位（`runtime-load-pass`）。
- 用户实机（2026-10-30）：**两只耳朵静止时都朝头的右侧歪**，双马尾**一直快速高频抖动**。两只耳朵的 OwnGravity 各沿自己的 X，却歪向同一侧 → 引擎在某个共享坐标系
  （角色或世界 X）里施加它，「骨自己的坐标系」的推断错了。v3 起不再用 `LocalOwnGravity`。

## 4. 调参轨迹（`case-derived`）

| 版本 | 双马尾（`KP_Hair_tail`） | 耳朵（`KP_Ear`） | 用户评价 |
| --- | --- | --- | --- |
| v1 | GlobalGravity、链节 0 / 2 / 4、12°、摩擦 1.5 / 1 | 5°、3 / 2，锥中心在静止姿势上 | 硬、一动就到限位 |
| v2 | LocalOwnGravity g 15、五节都模拟、10°、1.2 / 0.9 | LocalOwnGravity g 12、20°、0.8 / 0.6 | 耳朵歪向右侧，双马尾持续抖 |
| v3 | GlobalGravity rest-on-edge、链节 0 / 2 / 4、18°、0.8 / 0.6 | 6°、1.0 / 0.8，`upright` 偏移 | 耳朵好；双马尾太松，走两步就整根甩起，没有链感 |
| v4 | 五节都模拟，逐节 5 / 7 / 9 / 12 / 14°，摩擦 1.5→0.8 / 1.2→0.7 | 同 v3 | 双马尾又开始快速抖 |
| v5 | 链节 0 / 2 / 4，逐节 6 / 10 / 14°，摩擦 1.3 / 1.0 / 0.8 和 1.1 / 0.9 / 0.7 | 9°（最多摆 18°）、0.6 / 0.5 | 「看起来可以」（2026-10-30） |

- **抖动跟着「相邻链节都模拟」走**：v2、v4 五节都挂 BallJoint 都抖；v1、v3、v5 隔节模拟（中间的节刚性跟随）都不抖。
- **链感靠逐节分级**：根节锥小、摩擦大，越往梢锥越大、摩擦越小；`DEFAULT_PARAMS` 里的值可以是列表（按链序号，0 = 根，最后一个值重复）。
- **耳朵的 `upright` 偏移**：耳朵朝上，原 rest-on-edge 规则对朝上的链不偏；`upright` 让锥中心朝竖直方向偏，重力把耳朵往外倒时正好停在源模型的约 14° 倾角上。
  v5 的 9° 锥已越过竖直约 4°，静止姿势仍是锥边上唯一的稳定点，但经过竖直附近时回位会慢。
- 其他链从 v1 起没动：侧发 5°、2 / 1.5；前发 5°、3 / 2；脸颊发 6°；丝带 15°；鞋标 12°；裙片 14°、2 / 1（碰撞）；尾巴 12°、1.5 / 1，隔节模拟。

## 5. 裙片碰撞

沿用大革命 v7 的两段大腿胶囊（每条大腿 (x, Height, radius) = (0.12, 0.1, 0.13) 和 (0.32, 0.1, 0.11)，Y 偏 -0.008），经
`CommonData → BallJointCommonData → LiteRagdoll`；关节的 GravityMode 用 GlobalGravity（§2）。stage 2 起在枭雄里正常加载、跑动可用（用户确认有物理），
没有单独做碰撞专项评价。

## 6. 没覆盖的

- `LocalOwnGravity` 的实际坐标系没有测出来（只知道不是骨自己的）。
- 骑马、驾车、绳索发射器飞行、战斗大动作中的双马尾和裙片没有专门看；过场是预渲染视频，不涉及。
