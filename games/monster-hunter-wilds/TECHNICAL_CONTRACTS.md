# 技术合同（Monster Hunter Wilds）

> 类别标注：`invariant` = 与 build 无关的工程规则；其余为 `build-sensitive` 快照。
> 快照绑定：Steam App `2246340` / build `24705561` / exe `1.42.0.2`（2026-08-15）。
> 1.042.00.00（2026-08-05，`patch_015`）的材质迁移见
> [案例](cases/KARIN_1042_MDF_MIGRATION.md)。新 build 必须重新提取与复验。

## 1. 资源版本（build-sensitive）

| 资源 | 扩展名 | 最新所在层 | 备注 |
| --- | --- | --- | --- |
| Mesh | `.mesh.241111606` | `patch_014` | 文件头 `MESH` + uint32 `0x0E58DD3C` |
| MDF | `.mdf2.45` | `patch_015` | 1.042 起装备材质为 `Base_Equip_NoMultiBlend.mmtr` |
| Chain2 | `.chain2.14` | `patch_012` | 第三方文件名列表仍写 `.13`，**已过期** |
| 碰撞预设 | `.clsp.3` | — | |
| 关节约束 | `.jcns.29` | — | |
| TEX | `.tex.241106027` | — | |
| 骨架 | `.fbxskel.7` | — | |

`invariant` 方法：

- 版本号以**官方 PAK 索引**为准：路径哈希 = murmur3(UTF-16LE 全小写路径) 与
  murmur3(全大写路径) 组成 `(lower, upper)` 对；按 `re_chunk_000.pak` → `patch_NNN` →
  `sub_000` 链合并，后层覆盖前层。144 字节的占位 patch 不含条目，跳过。
- 常用文件名列表（Ekey REE.PAK.Tool 的 `MHWs_STM_Release.list`）**不含 streaming 路径**，
  需自行派生 `natives/stm/streaming/<同路径>`。
- 很多 Mesh 需要同名的 streaming Mesh 才能解析（RE Mesh Editor 报
  `Streaming mesh file is missing`），抽取时两份一起抽。
- RE Mesh Editor 的 `meshVersion` 来自**扩展名**，对解析结果做版本断言是同义反复；
  版本闸门要比对文件头 uint32@4 与原版。
- 临时抽取一律显式指定报告路径，不要让抽取器写回项目的输入锁报告。

## 2. 装备部位与引擎挂点骨（build-sensitive 值，invariant 规则）

女性装备 `ch03_XXX_YYY` 的部位编号（由部位 Mesh 的骨名反推）：

| 部位 | 内容 | 每套原版都带的非 fbxskel 骨（抽样） | 作用 |
| --- | --- | --- | --- |
| 1 | 腕甲 / 袖 | 无 | — |
| 2 | 胴甲 | `Spine_1_WpConst`、`Spine_2_WpConst`（15/15） | 背负武器挂点 |
| 3 | 头盔 | `HelmJoint_*`（约 9/14，非全部） | `hypothesis`：头盔与脸部配合 |
| 4 | 腿甲 | 无（但大腿/小腿碰撞体条目在这里） | — |
| 5 | 腰甲 | `Hip_WpConst`、`Cage`（15/15），`Cage_L`（14/15） | 腰部武器挂点、腰部挂件 |
| 6 | 投射器 | `Slg_Base`、`Slg_00…05` 等 10–15 根（12/12） | 投射器骨 |

抽样方法（`invariant`）：同时抽取 8 套原版装备的 1–6 号部位 Mesh（含 streaming），
对每个部位统计「不在 fbxskel 里、且不是 `_CH_` 链骨」的骨名在多少套里出现。出现在
**所有**套里的，视为引擎合同骨。

**合同**（`runtime-confirmed`，本例 r6）：

- 隐藏部位的占位件必须保留这些骨。r5 的占位件只有 `root/COG/Hip` 三骨，并且把投射器
  也换成了空壳，结果是**武器完全看不见**，而且**除大集会所外进入任何地图都会崩溃**
  （大集会所不使用投射器/武器逻辑）。
- 投射器部位最稳妥的做法是**不替换**：保留原版文件，由 BoneSystem 的 `HideSlinger`
  隐藏。参考 mod 的 6 号部位就是原版 17 骨。
- 挂点骨只需进 Mesh 骨架，不进 fbxskel；不需要权重。

挂点位置（`case-derived`）：取默认内衣装备 `ch03_000` 的局部偏移作高度/朝向。

| 挂点 | 父骨 | `ch03_000` 局部平移 | 局部旋转 |
| --- | --- | --- | --- |
| `Spine_1_WpConst` | `Spine_1` | `(0, 0.013, -0.061)` | 绕 X 约 9° |
| `Spine_2_WpConst` | `Spine_2` | `(0, 0.001, -0.086)` | 绕 X 约 5° |
| `Hip_WpConst` | `Hip` | `(0, 0.035, -0.166)` | 0 |
| `Cage` | `Hip` | `(0.157, -0.065, 0.123)` | 0 |

`invariant`：在原版上，背部挂点**贴着外层背表面**（距背表面 −0.4 / +0.1 cm）。给新体型
使用时，保持「挂点到最外层衣物背表面」的原版间距，而不是照搬局部偏移 —— 本例照搬时
`Spine_1_WpConst` 会陷进毛衣 2.4 cm。

## 3. 骨架与 BoneSystem

BoneSystem（社区插件，作者 南风焓 / nfh994，本例 `26.1.13.1`）是一个 REFramework 插件
DLL，内嵌一段 Lua 5.4 字节码（按 key `BoneSystem` 异或），解码后可读到：

- `fix_bone`：把配置部位 `via.motion.CustomSkeleton` 的 `ch03_000_9000.fbxskel` 换成
  `natives/STM/BoneSystem/<FbxPath>.fbxskel.7`，并处理 RetargetCtrl；
- `bind_face`：用 `get/set_Local*` 与 `get_BaseLocal*`，按骨名把脸部骨「相对基准姿态的
  增量」传到装备骨（`reference-inferred`，由 API 名推断）；
- `HideFace` / `HideHair`：关闭对应部件材质；`HideSlinger`：对名为 Slinger 的子对象
  `HideSelfAndChild`。

每部位一个配置 `reframework/data/BoneSystem/<ch03_060_0002>.json`，本例只用参考 mod
同样的 6 个键：`HideFace`、`HideHair`、`HideSlinger`、`BindFace`、`BindPart`（几何所在
部位号）、`FbxPath`（fbxskel 名，不带扩展名）。

骨架合同（`runtime-confirmed`）：

- fbxskel 保持原版 `ch03_000_9000.fbxskel.7` 的 **224 骨名字、顺序、父子**，只写入新
  角色的 rest。Mesh 中与 fbxskel 共享的骨，绑定矩阵必须等于 fbxskel rest（本例误差
  1e-7 级）。
- Mesh 可以额外携带 fbxskel 没有的骨：脸部 169 骨、链骨（本例 134 根 `KO_*`）、挂点骨；
  按名字绑定，骨数与顺序不是合同。
- 参考 mod 的 fbxskel 使用自身比例与 T 姿势手臂 rest，实机正常 —— 游戏会 retarget 动画。
- jcns 不必随包替换：参考 mod 的 jcns 与原版逐字节相同，而其骨架缺少其中相当一部分
  关节，仍正常运行。

比例（`case-derived`）：一次统一缩放使头高对齐参考体型；COG 保持原版高度；只对肢体骨
做最小摆动对齐与掌心滚转修正，其余骨保持原版局部旋转；辅助 `*_HJ_*` 骨按段长比例缩放
原版偏移；踝关节放到原版踝高 0.088（实机未报告脚部问题）。

## 4. 脸部与表情（case-derived）

- 原版女脸 `ch00_001_0000` **没有 blendshape**，表情全由骨骼驱动；眼睑枢轴在眼球中心，
  下颌是铰链。
- 做法：把原版脸部 `HeadAll_SCL` 子树（169 骨，姿态不变）按区域放到新角色的眼/眉/嘴/
  下颌，用新角色自己的形态键拟合权重：眨眼 → `*_UpEyeLid_LOD01` / `*_LoEyeLid_LOD01`
  （枢轴按弦几何求），眼球 → `*_EyeJ_LOD02`，张嘴 → `C_Jaw_LOD02`（最小二乘铰链），
  眉 → `*_EyeBrow_LOD02`。共 9 根表情骨必须有权重（打包闸门检查）。
- 表情幅度角度是估计值；需要精调时写一个只读 REFramework 采集脚本记录实机脸部骨的
  局部变换，再回填参数。本例未做采集，表情未被单独签收。
- 源模型中默认关闭的形态键（如腮红）在骨骼驱动下无法打开，按源默认状态处理。

## 5. 材质、TEX 与 NRRO

### 5.1 MDF 模板（build-sensitive）

- 模板从**当前 build** 的原版装备材质拷贝（本例 `ch03_060_0002_body`，
  `MaterialShader/Variation/Base_Equip_NoMultiBlend.mmtr`，176 个属性、23 个贴图槽、
  3 个 GPBF），只改自己拥有的贴图槽与少数参数；RE Mesh Editor 的 `writeMDF` 能把原版
  与参考 MDF 逐字节往返。
- 参考配方（`case-derived`，动漫自发光风格）：`EmissiveMap` = 反照率，`Emissive_Power`
  2（脸 3），`UseCounterExposureEmit` 1，`CounterExposureEmit_Blend` 0.5，双面。代价是
  不跟随捏脸肤色。
- 每个材质整体沿用一套已实机的标志位/属性；不要给没有原版先例的 shader 组合临时加
  alpha test / dither 之类的开关。

### 5.2 贴图通道语义（invariant 于本作）

- ALBD（`BaseDielectricMap`）：RGB = 基色，**A = dielectric**（1 = 非金属）。A 写 255
  是非金属，不会造成金属反光。
- NRRO（`NormalRoughnessOcclusionMap`）：**R = 粗糙度**，G/A = 法线 XY（0.5 为平直），
  B = 遮蔽。
- 引擎 `systems/rendering/NullNormalRoughnessOcclusion.tex` 为 8×8、BC7_UNORM、1 mip，
  解码 `(128, 127, 255, 127)` —— **粗糙度 0.5**，布料会出现集中高光。

原版 NRRO 的 R 通道参考（streaming 全尺寸均值）：布甲 `ch02_060_0002` 0.77、默认内衣
`ch03_000_0002` 0.73、`ch03_004_0002` 0.65；毛发 NRRO ≈ 1.0（毛发 shader）；脸
`ch00_002_0000` ≈ 0.58（眼/唇低）。

本例修复（`runtime-confirmed`）：自带常量 NRRO，与 NullNRRO 同形态（8×8、1 mip、
BC7_UNORM、头字节 28/29 = `0x80 / 0x06`），R = 衣物/头发 0.90、皮肤/脸 0.80。

### 5.3 TEX 头（build-sensitive）

`.tex.241106027`：宽/高 u16 @8/@10，mip 数打包在 @14（`>>12`），格式 @16
（98 BC7_UNORM、99 BC7_SRGB、71/72 BC1）。字节 28/29：

| 文件 | 尺寸 / mip | byte 28 | byte 29 |
| --- | --- | --- | --- |
| 原版 base（`natives/STM/<path>`） | ≤64 px，尾部 mip 到最短边 8 | bit0 = 1（非颜色数据再加 `0x80`） | `(流式 mip 数 << 5) \| 用途类` |
| 原版 streaming（`natives/STM/streaming/<path>`） | 全尺寸，mip 到最短边 8 | 0（非颜色 `0x80`） | 用途类 |

用途类：ALBD 5、NRRO 6、MSK/ATOS 4、ALBA/NRM 1、风场 0。

实测（`runtime-confirmed`，新 REFramework）：自制**单文件**贴图（完整 mip 链、字节
28/29 为 0/0）放在 `natives/STM/streaming/...`、MDF 写 `streaming/<dir>/<name>.tex`，
可以正常显示；不需要拆成原版式 base + streaming 对。MDF 路径解析为
`natives/STM/<MDF 中的路径>`。

打包闸门（`invariant`）：解包后逐个检查 MDF 引用的贴图，要么在包内，要么在官方 PAK
索引里。一张找不到的贴图会让开机永久黑屏（见 [加载](LOADING_AND_REFRAMEWORK.md)）。

## 6. chain2 与 clsp

- chain2 `.14` 用 RE Chain Editor 14 读写。设置/分组参数按类别（双马尾、侧发、刘海、
  耳、蝴蝶结、尾、裙、饰带）从已实机的参考 mod 拷贝，节点静止指向由骨骼几何计算。
- `clspFlags0` 是**碰撞体位掩码**，`-1` = 全部碰撞体（参考 mod 52 组中 27 组如此）。
  本例裙/尾 = `49155` = `Hip_HJ_00(1) | Spine_0(2) | L_Thigh(16384) | R_Thigh(32768)`。
- clsp 条目 = 关节 + 配对关节（胶囊）+ 两端偏移 + 位；原版与参考只用
  `collisionSphereRadius`，胶囊起止半径恒为 0。
- 位是**跨部位共享的池**：原版 5 号裙链引用 4 号的大腿位。所以把几何集中到 2 号时，
  2 号的 clsp 要带上原版 4 号的大腿/小腿条目；占位部位只放一条零半径条目并用一个
  原版没用过的位（本例 `1 << 30`），不要占用 2 号已定义的位。原版从不发空 clsp。
- chain 节点 `collisionShape` 0 = None（饰带类），不参与碰撞，也不参与静止间隙计算。

半径拟合（`invariant` 规则，数值 `case-derived`）：

- 半径 = 胶囊轴到最外层身体表面（衣物/皮肤，不含头发、裙、尾、脸）距离的分位数，
  且不超过原版；再按「所有选中该碰撞体的碰撞节点在静止时位于外侧 ≥ 3 mm」封顶，
  封顶低于 0.02 m 则拒绝写出。
- **要把布料推开的碰撞体按外表面拟合。** r5 大腿用 35 分位得 0.059 m，而大腿上半外
  表面约 0.09 m，奔跑时大腿根穿出裙片；r6 改为「胶囊上半段、90 分位」得 0.095 m
  （静止封顶 0.100 m，静止穿透仍为 −3 mm），实机确认。
- 参考 mod 的裙链掩码是 `30`（只碰躯干），根本不碰大腿 —— 设计不同，不能拿来证明
  大腿半径合理。
