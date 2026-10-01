# 技术合同（生化危机 安魂曲）

适用 build `23634047`。版本号与路径是 `build-sensitive`；「怎么发现它」的方法是 `invariant`。

## 1. 资源版本（build-sensitive）

| 资源 | 后缀 | 备注 |
| --- | --- | --- |
| Mesh | `.mesh.250925211` | 内部版本 `250904410`；**八权重**：raw 权重记录 16 字节 = 8 个 u8 骨索引 + 8 个 u8 权重（和为 255），未用槽位用最后一个有效索引填充 |
| MDF | `.mdf2.51` | RE Mesh Editor 可逐字节往返用户参考 mod 的 mdf2（含「偏移清零后重写」） |
| TEX | `.tex.250813143` | GDeflate；RE Mesh Editor 写出 |
| chain2 | `.chain2.15` | 与 PRAGMATA 同版本，RE-Chain-Editor（修 `padding2` 写入 bug 后）可往返 |
| Prefab | `.pfb.18` | RSZ v16，类型库 REasy `rszre9.json` |
| refskel | `.refskel.8` | 每关节局部 TRS；整个角色号共用（`ch01.refskel.8` 84 个关节，`ch02.refskel.8` 68 个） |
| clsp | `.clsp.3` | 角色碰撞形状；原生 Chain2 默认只碰它（见 [物理](CHAIN2_PHYSICS.md) §3） |
| montage | `chXXXX_montagedata_N.user.3` | 套件 → prefab 后缀集合 |

发现方法：路径表用 Ekey 的 `RE9_STM_Release.list`（按 `natives/stm/` 过滤后交给 REtool 按表提取）；
解析原生 mesh 时把 `natives/stm/streaming/...` 一并提取。某个文件属于哪个 mdf2 变体、哪个部件变体，全部从路径表里
正则列出，不靠猜。

## 2. 角色、部件号与变体（case-derived）

| 角色 | 角色号 | 路径前缀（`natives/stm/` 下） |
| --- | --- | --- |
| 里昂 Leon | `ch0100` | `character/ch/ch01/0100/<部件>/<变体>/ch0100_<部件>_<变体>.mesh.250925211` |
| 格蕾丝 Grace | `ch0200` | `character/ch/ch02/0200/...` |

部件号（按网格内容与 prefab 引用观察，部分用途未确认）：`01` / `02` 手臂与手、`08`（未确认）、`09` 手表、
`10` 脸（`10_60` 颈部伤口件）、`14` 耳机、`15` 眼镜、`20` 头发、`21` GPU 发丝（strands，设置开启时才用）、
`40` 身体/内衣、`41` 腰带、`43` 背心、`44` 护垫、`45` 外套（带 GpuCloth）、`48` 毯子、`50` 裤子与鞋。

- 同一部件号有多个变体：里昂身体 `40` 有 `00/01/02/03/50/51/60/61/70/71/80/81`，格蕾丝有
  `00–04/50/51/60/61/70/71/80/81`。`40_6x` / `40_8x` 只出现在 `45x/55x/65x/75x` 后缀的 prefab 里，与
  `40_5x` / `40_7x`（`40x/500`、`60x/700` 后缀）对应，推断是可肢解的上/下半身拆分。参考 mod 把 `6x/8x` 做成屏蔽件、
  完整身体放在 `5x/7x`（`case-derived`，切割观感未实测）。
- 每个变体有多份材质：`<mesh 名>_NN.mdf2.51`（里昂脸 `10_00` 有 21 份，身体 `40_00` 有 4 份）。
- 用户参考 mod 的 `43_01` 下有一个 `ch0100_43_01_00.mdf2.250925211`（实为 mesh 内容、后缀错误），游戏不会按这个名字加载，
  无害；复刻配方时不要照抄。

### prefab 与套件

- 部件 prefab：`character/ch/ch01/0100/<部件>/ch0100_<部件>_<NNN>.pfb.18`，`NNN` 是套件后缀。每个 prefab 的
  GameObject 引用一个 mesh、mdf2、可选的 chain2 / clsp。
- 身体 prefab 数（本 build）：里昂 72 个，其中引用 `40_00`（17 个）/`40_01`（13 个）的原生带 Chain2，引用
  `40_02/03/50/51/70/71` 的 22 个**没有**；格蕾丝 37 个，`40_01–04`（8 个）带 Chain2，默认 T 恤 `40_00`（13 个）与
  `40_50/51/70/71`（8 个）共 21 个没有。
- 套件选择在 `chXXXX_montagedata_N.user.3`：每份 montage 把各部件映射到一个后缀。里昂 `montagedata(0)` = `700` 套件、
  格蕾丝 = `602` 套件，两者身体都是 **`40_70`**，原生 prefab **没有 Chain2**。
- 扫描方法（`invariant`）：把角色目录下全部 `.pfb.18` 提取出来逐个读 RSZ，输出「prefab → GameObject → mesh / mdf2 /
  chain2 / clsp」表；覆盖面、注入范围、验证器都以这张表为准。

### 展柜（奖励内容 → 游戏模型）

- 展柜对象是 `gameassets/figure/prefab/detail/bo20_00_*.pfb.18`，上面的 `app.CharacterMontageRequester` 用
  KindID（里昂 `cp_A000`、格蕾丝 `cp_A100`）和 ModelID（= 角色号 `100` / `200`）选套件，并按展柜场景时间选 montage。
- 它的 `PartsMotionData` 给指定部件喂展柜专用 `.mot`，**这些部件的 Chain2 被关闭**：里昂是 `45`（外套），
  格蕾丝是 `40`（身体）。所以格蕾丝的身体物理在展柜里永远不动，这是游戏行为，不是 mod 问题。
- 展柜里按 `E` 在里昂与格蕾丝之间切换。

## 3. PFB / RSZ（invariant 于本作的 RSZ v16）

- 读写器直接沿用 PRAGMATA 的实现，类型库换成 REasy `rszre9.json`：原生 prefab 读入写出逐字节一致。
- 插入组件 = 在对象表里插入实例 + 改 GameObject 的组件列表，并平移插入点之后的对象表索引（`parentId`、
  `GameObjectRefInfo`），细节见 [PRAGMATA 技术合同](../pragmata/TECHNICAL_CONTRACTS.md) §3。
- 本作身体 GameObject 上的物理组合是 `via.motion.ChainWind` + `via.motion.Chain2` + `app.ActorChain2`；
  有的 prefab 已经带 `app.ActorChain2` 但没有 Chain2（例如里昂 `ch0100_40_019`），只补缺的那几个。

## 4. 网格写法（RE Mesh Editor，build-sensitive）

- 用 raw 模式读写：法线/切线 int8、UV 为 u16 半精度位、颜色 u8、权重 16 字节记录。**分析脚本里读 UV 要先按
  `<u2` 取位再 `view(float16)`**；直接把整数当 float 用，所有顶点会采到贴图左上角（本项目因此一度误判贴图 alpha）。
- 法线 `w = 0`、切线 `w = ±127`（RE Mesh Editor 写 RE9 时的约定，与参考 mod 一致）。
- 新网格以参考 mod 的身体 mesh（编辑器产物、实机可用）作写出模板；每种 mod 材质合成一个 submesh。

## 5. 材质与贴图（case-derived 值，invariant 做法）

| 用途 | 模板 | 设置 |
| --- | --- | --- |
| 皮肤 | 参考 mod 的 `Body_Mat`（`Ch_Skin_Detail_Record_Wet_Burnt.mmtr`） | — |
| 脸 | 参考 mod `ch0100_10_00_00` 的脸条目（同一着色器族） | — |
| 衣服 / 头发 | 参考 mod 的 `Karin_Mat`（`ChWp_Default_Wet_Burnt.mmtr`） | 双面（flags bit `0x1`） |
| 镂空贴花 | 同上 | 双面 + AlphaTest（`0x2`），`AlphaTestRef 0.5`，镂空取 ACOT 的 R 通道 |

- 从别的 mdf2 拷来的条目先清零 `GPUBufferOffset` / `mmtrsDataOffset`，alpha 条目排在前面（编辑器写出 bug，见
  [PRAGMATA](../pragmata/TECHNICAL_CONTRACTS.md) §4）；开工前对参考 mdf2 做往返闸门。
- **NRMR 的 alpha = 粗糙度。** 引擎 `systems/rendering/NullNormal.tex` 解码为 `(127,127,254,0)` → 粗糙度 0 → 乳胶感。
  每个材质的 `NormalRoughnessMap` 都要指向真实的 NRMR 或一张平图：64×64、BC7_UNORM（线性）、`(128,128,255,255)`。
- ALBD 的 alpha = 非金属度：生成时把 alpha 强制为 255。检查别人的 ALBD 时**按网格 UV 实际覆盖的区域采样**，
  整图 alpha 统计会被不用的区域误导。
- 贴图：ALBD BC7 sRGB（format 99）、ACOT BC1（format 71）、NRMR BC7 线性（format 98），全 mip，header flags `0 / 0`
  （与参考 mod 相同）；texconv → DDS → RE Mesh Editor TEX 写出，再回读比对载荷。

## 6. 运行时探针（invariant 方法）

REFramework 已装（Lua `autorun`）。写一个只读脚本：枚举场景里角色的 `via.motion.Chain2` 组件（ChainAsset、
CollisionTarget、是否启用），读链节点与碰撞体所在关节的世界坐标，按类型反射读枚举的字段名与值，用
`json.dump_file` 写到 `reframework/data/`。读完就删脚本和输出，不要留在用户的游戏目录里。
本项目的 CollisionTarget 枚举和「节点陷进碰撞体 6 cm」都是这样读出来的。
