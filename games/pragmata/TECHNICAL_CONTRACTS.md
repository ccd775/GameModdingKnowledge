# 技术合同（PRAGMATA）

适用 build `24543093`。版本号与路径是 `build-sensitive`；「怎么发现它」的方法是 `invariant`。

## 1. 资源版本（build-sensitive）

| 资源 | 后缀 | 备注 |
| --- | --- | --- |
| Mesh | `.mesh.251121828` | 内部版本 `250707828` = RE Mesh Editor 的 Pragmata demo 布局，**六权重**压缩（每顶点 16 字节权重记录） |
| MDF | `.mdf2.51` | 与鬼武者同为 51，但本作条目要按下文 §4 处理写出 bug |
| TEX | `.tex.251111100` | GDeflate 压缩 |
| chain2 | `.chain2.15` | RE-Chain-Editor 可读写，原生**逐字节往返**（需修其 `padding2` 写入 bug） |
| 旧 chain | `.chain.55` | 编辑器**不能**往返，本项目未使用 |
| Prefab | `.pfb.18` | RSZ v16 |
| refskel | `.refskel.8` | 每关节局部 TRS |
| clsp | `.clsp.3` | 角色碰撞形状（见 [物理](CHAIN2_PHYSICS.md) §5） |

发现方法：路径表用 Ekey 的 `P_STM_Release.list`；`REtool -l` 列 TOC；路径哈希 =
murmur3(UTF-16 小写) / (大写) 的一对，可直接按哈希探测某路径在哪个 PAK。
解析原生 mesh 还需要把对应的 `natives/stm/streaming/...` 一并提取，否则编辑器找不到高 LOD 数据。

## 2. 槽位（case-derived，本 build）

**Hugh（`ch0000`，默认宇航服造型）**

| 用途 | 路径（`natives/stm/character/` 下） |
| --- | --- |
| 游玩身体 | `ch/ch00/ch0000/00/ch0000_00_playergame.mesh` + `ch0000_00_playergame_mat.mdf2` |
| refskel | `ch/ch00/ch0000/ch0000.refskel.8` |
| 需屏蔽的部件 | `ch0000_10/13/15/20/60`（头盔、脸、面部毛发、腰包等） |
| 过场模型 | `ch/ch00/ch0091/00/ch0091_00.mesh` + `ch0091.refskel.8`（过场 cs0030） |
| 注入物理的 prefab | `prefab/ch01000/costume/cospl0000/body_spacesuit.pfb.18`（patch_002 里是最新版） |

Hugh 的玩家 prefab **没有任何 Chain 组件**。同一个身体 mesh 还被诱饵道具 wp8500 `Decoy2` 引用（静态分身，无物理，接受）。

**Diana（`ch0100`）**

| 用途 | 路径 |
| --- | --- |
| 身体 | `ch/ch01/ch0100/00/ch0100_00.mesh` + `ch0100_00_mat.mdf2` |
| 需屏蔽的部件 | `ch0100_10`、`ch0100_20`、`ch0100_40_neo`（脸、头发、外套） |
| 未处理 | GPU 发丝 `ch0100_22`（strands，部分画质/服装才用） |
| 引用身体 mesh 的 prefab | 主 prefab `prefab/ch05000/ch05000.pfb.18`、`ch05200.pfb.18`、`cospa0000/ch05000_parts_body1`、`cospa0020/..._pa0020`、`breakbodybase/ch05000_parts_body2`、`cospa9010/..._pa9010`、`cospa9020/..._pa9020`（共 7 个文件、9 个 GameObject，其中两个文件各有第二个 `DefaultBody` GO） |

扫描方法（`invariant`）：把**全部**原生 prefab（本 build 2,836 个）提取出来，逐个读 RSZ，列出
所有引用目标 mesh 路径的 GameObject。只改主 prefab 的版本，在破损形态、第二套服装等场景里物理会消失。
另有环境静态道具（`sm90_108_14`）也引用 Diana 的 mesh，无动画，不改。

新资源可以放在自定义路径（例如 `character/KarinNM/*.tex`、`*_karinnm.chain2.15`），由修改后的
mdf/prefab 引用即可加载（`runtime-load-pass`，Fluffy 散装 `natives/` 路线）。

## 3. PFB / RSZ（invariant 于本作的 RSZ v16）

- RSZ 类型库必须用正式版 CRC（REasy 的 `rszpragmata.json`）。alphazolam 仓库里的版本是 demo 导出，
  Mesh / CharacterBodyParts 等类型 CRC 不同。
- RSZ userdata 表里的实例（作为外部 `.user` 引用的对象）在数据区**不占字节**；userdata 表与
  数据区按**文件绝对偏移** 16 字节对齐，不是按块内偏移。
- 在 GameObject 上插入组件 = 在对象表里插入实例 + 改该 GO 的组件列表。插入点之后的所有
  **对象表索引**都要平移：包括子 GO 的 `parentId`，以及主 prefab 里的 `GameObjectRefInfo`
  条目（它们存的是对象表索引，不是实例 ID）。漏平移的症状是离线看似正常、运行时引用错对象。
- 读写器闸门：150+ 个原生 PFB 读入再写出逐字节一致；注入后的验证器「剔除插入的实例后逐字段
  与原文件对齐」，允许一个文件里多处插入。
- `app.TimelineEventResetSimulationRegister`（过场/传送时重置物理）：原生 ID **按类别共用**，
  不是名字哈希；缺的 GO 从同角色带 Chain2 的部件（Diana `ch05000_parts_body_pa2010`）拷一份。

Chain2 组件相关字段见 [物理](CHAIN2_PHYSICS.md) §1。

## 4. 工具适配层的坑（build-sensitive）

**RE Mesh Editor（mesh）**

- 用 raw 模式：法线、UV、颜色、权重按原字节读写。编辑器自己的法线/UV 编码有损；raw 模式下
  权重是 16 字节记录，需要自己解码（六个索引 + 六个权重）。
- 往返闸门：原生/参考 mesh 读入写出后**载荷一致**；编辑器会改写 4 处版本头字段，由构建器回填。
- 新 mesh 的头部只从同槽原生供体拷 `lodGroupNameHash`（`0x0c`）。整块拷参考 mod 的头部固定偏移
  曾把 `0x12c`（在新布局下是第一个 mesh group 的索引数）写成错误值。

**RE Mesh Editor（MDF 写出 bug）**

- 写字符串表前会 seek 到每个材质的 `GPUBufferOffset`，只重算值为 0 的条目 → 从别的文件拷来的
  条目必须先把该字段清零。
- AlphaTest 条目排在 Emissive 条目之后时写出会截断文件 → **alpha 条目排前面**。
- 参考 mod（Gamer JP）的 mdf 无法被编辑器往返。做法：用**原生**条目当模板（`Env_Emissive` 取
  原生 `sm20_024`，`Env_AlphaTest` 取 `sm16_016`），再填参考 mod 的参数与标志位。
- 闸门：生成的 mdf 读入 → 偏移清零 → 重写，必须逐字节一致。

**RE-Chain-Editor（chain2.15）**：修掉 `padding2` 的写入 bug 后，原生文件逐字节往返。

## 5. 贴图头（case-derived）

| 贴图 | 格式 | header flags |
| --- | --- | --- |
| 漫反射 ALBD | BC7 sRGB（format 99） | `0 / 69`（与参考 mod 相同） |
| 镂空 ATOS（R 通道 = alpha） | BC1（format 71） | `128 / 68`（原生非流式 ATOS 为 `129 / 68`，按参考 mod 对 albedo 的做法清掉 bit0） |

生成：texconv → DDS → RE Mesh Editor TEX 写出（GDeflate）。贴图尺寸取源图尺寸即可。
