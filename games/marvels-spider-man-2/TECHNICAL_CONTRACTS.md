# 技术合同

除标注外，全部是 toc SHA-1 `318f4345f3a1`（v1.130.1.0）上的实测。读写代码见便携包 `scripts/`。

## 1. toc、资产头与资产名

- `toc` 的结构：`u32 0x34E89035` + `u32 DAT1 长度` + DAT1。文件尾另有 3,636 个 0 字节（Overstrike 存回时会丢掉，不影响游戏）。
- DAT1 段：

  | 段 | 内容 |
  | --- | --- |
  | `EDE8ADA9` | span 表：256 × {u32 首资产序号, u32 数量} |
  | `506D7B8A` | 资产 id：u64，span 内升序 |
  | `65BCF461` | 尺寸表，每项 16 B：size, archive, offset, i32 header_offset（-1 = 无头） |
  | `398ABFF0` | 归档表，每项 66 B：40 B 文件名 + Q Q I H I |
  | `36A6C8CC` | 贴图 id（u64 升序） |
  | `C9FB9DDA` | 贴图 meta，72 B/张 |
  | `62297090` | 贴图数 |
  | `654BDED9` | 资产头数据 |

- **i30 资产头是变长的**：`u32 magic | u8 ? | u8 pairs | u16 extra | pairs×8 | extra`。ALERT 按固定 36 B 切，那是 i29 的格式，在 i30 上会错。
- 规模：1,423,247 个资产，225 个归档（`d\*`，DSAR 压缩块：LZ4 = 3，GDeflate = 2）。
- 资产名：取游戏根目录 `dagstr` 里的字符串，算 CRC64（ALERT 的表；路径转小写、`\` → `/`、合并重复的 `/`）后与 id 匹配。
  解出 420,966 个名字（`sm2_index.py`）。

## 2. `.stage` 与安装（复刻 Overstrike 的 MetaInstaller_I29 + StageInstaller_I29_V2）

- `.stage` v2 是 zip：`info.json`（`game: "MSM2"`、`format_version: 2`、name、author、description）+ `<span>/<16 位十六进制 id>` 条目。
  - 条目可带 `STG\0` 包装：flags 1 = 写资产头，2 = 写贴图 meta（72 B）。
  - 头长度相同就原位覆盖，否则追加。
  - **新贴图必须带 meta**，否则游戏不知道它是贴图。
- 安装：
  1. 第一次安装把原 toc 复制成 `toc.BAK`；以后每次安装都先用 `toc.BAK` 覆盖 `toc`。
  2. 第 i 个 mod 写成未压缩的 `d\mods\mod<i>`，归档表追加一项（A=B=2678794514496, C=3844228203, D=32763, E=0）。
  3. 逐资产在 span 里查找或插入，设置 archive / offset / size，写资产头和贴图 meta。
  4. 每个 span 内按 id 重新排序，存回 toc。
- 多个 `.stage` 按命令行顺序成为 mod0、mod1……，后面的覆盖前面的。测试时可以只传一个小的增量包，例如 `install base.stage delta.stage`，
  不必每次重传完整包。
- 卸载：用 `toc.BAK` 还原 `toc`，并删除 `d\mods\mod*`。
- 同一个 `.stage` 装出来的 toc 是确定的。本项目 v2 装后 toc SHA-1 为 `69ce1233d4fe`，可以用来核对安装是否一致。

## 3. `.model`

- 资产头 24 B：`8a9a061b 00 02 0000` + 两对 (A, B)。
  - A 的低 30 位：pair0 = GeomData 段偏移（即 CPU 部分大小），pair1 = GeomData 大小。A 的高 2 位在两对里相同，含义未知，保留原值。
  - B 两对相同，高 4 位恒为 1；低 28 位随模型变大，非 Ziva 模型约为 8 × 总顶点数，推测是运行时显存预留。替换时保留原值。
- DAT1 段顺序照原文件。`ModelLook / ModelLookGroup / ModelSubset / ModelSubsetGeomData / ModelLocator` 按 64 B 对齐，其余按 16 B，
  这样存回与原文件逐字节一致。
- 段名（InsomniacTools `ModelHashes.cs`）：

  | 段 | id | 说明 |
  | --- | --- | --- |
  | Built | `283D0383` | 96 B |
  | Subset | `78D9CBDE` | |
  | GeomData | `F4EA9E18` | |
  | Joint | `15DF9D3B` | |
  | BindPose | `DCC88A19` | 48 B/骨，局部：scale3+pad、quat xyzw、pos3+pad |
  | InvBindPose | `2C2CA205` | 64 B/骨，4×4 行主序，平移在最后一行 |
  | Material | `3250BB80` | |
  | Look | `06EB7EFC` | |
  | LookGroup | `4CCEA4AD` | |
  | LookBuilt | `811902D7` | |
  | Ziva2 | `6694064E` | |
  | AnimVertInfo2 | `06E24ED4` | |
  | VertSmooth | `55187F02` | |
  | ModelAnimDynamicsDef | `ADD1CBD3` | 见 [物理](PHYSICS.md) §1 |
  | ModelJointBspheres | `0AD3A708` | 见 §3.4 |
  | ModelMirrorIds | `C5354B60` | 见 §3.3 |

- 从 DAT1 开头算的绝对字符串偏移只出现在两处：ModelMaterial（前 n 项每项 16 B：path_off, 0, name_off, 0；后 n 项是哈希）和
  ModelLookBuilt（每个 look 80 B，名字偏移在 +76）。删段或加段会移动字符串块，这两处要一起改。
- `ModelBuilt` 首字是能力标志，都是 `invariant`：
  - `0x10000000` ⇔ 有 AnimVertInfo2（174 个 hero 模型无例外）。删 anim-vert 段必须清这一位，否则整件身体不显示（T1）。
  - `0x20000000` ⇔ 有 ModelAnimDynamicsDef。
  - 按 f32 读：[8..10] 是包围球中心，[11] 是半径，[12..14] 是包围盒半边长。
- 结论：删 Ziva2 / AnimVertInfo2 / VertSmooth 三段并清掉 0x10000000，模型就能正常显示（T2 `runtime-load-pass`）。

### 3.1 网格记录与顶点

- Subset 每网格 128 B：

  | 偏移 | 含义 |
  | --- | --- |
  | 0 / 4 | index_count / vertex_count |
  | 12 | 索引缓冲在块内的偏移 |
  | 20 | fmt 位标志（1 = 普通蒙皮） |
  | 24 | 位置缩放 f32 = 1/4096 |
  | 28 | 材质序号（低 16 位） |
  | 32 / 36 | 表面积（m²）/ UV 面积 |
  | 64 / 68 | 位置流 / 第二路 4 B 流的块内偏移 |
  | 76 / 80 | 蒙皮数据 / 蒙皮批表的块内偏移 |
  | 84 | 全局起始顶点（各网格顶点数累加，偶数对齐） |
  | 88 / 92 | 网格块在 GeomData 中的偏移 / 大小（按 16 对齐） |
  | 100 | 低 16 位：LOD0 网格的蒙皮批数；高 16 位：LOD 位掩码 |
  | 118 | u16 最长边（1/4096 m） |

- 顶点 16 B：`i16 x,y,z,w`（×1/4096，单位米，Y 朝上）+ `u32` 打包法线（10/10 位 + 第 31 位符号）+ `i16 u,v`（÷16384，可以超出 0–1）。
  w 疑似打包切线，未解；写入时用中性值。fmt = 1 时没有第二路流，索引紧跟顶点。
- `fmt & 0x4000`（头模型的网格）：位置为 i16 × 1/65536 m，再加原点 `(0, +52 的 u32/256, +56 的 i32/256)`。
  例如 Peter 头的原点是 (0, 1.66797, 0.0352)。自己写的网格一律用 fmt 1 的格式，在头模型里也能正常显示。

### 3.2 蒙皮

- 批表每项 `u16 偏移, u16 info`，每批 32 个顶点槽（末批补齐）。info 各位：
  - bit0–3：偏移的高 4 位（偏移 = u16 | (info & 0xF) << 16，单位 4 B）；
  - bit4：宽关节；
  - bit5–8：影响数 − 1（最多 16）；
  - bit9：字节关节号从 256 起算；
  - 0x2000 只出现在 anim-vert 模型里。
- 窄格式：每顶点 g 对 `(u8 关节增量, u8 权重/256)`。关节号升序，第一个是绝对值，其后是与前一个的差；g = 1 时只有一个绝对关节号字节。
- **关节号超过 255**（527 骨的模型）：u8 增量放不下时，插入 `(255, 0)` 垫脚石（关节 +255、权重 0），可以连续插多个。权重 256 写成 `(j, 255) + (0, 1)`。
  原版里确实有这种编码。
- **只有 `u2 & 0x80` 的关节能带权重**（`invariant`）。重映射后用到的关节要补上这一位，否则蒙皮不生效。

### 3.3 关节

- 关节表每项 16 B：`i16 parent, u16 index, u16 ?, u16 ?, u32 hash, u32 name_off`。**name_off 相对该项自身的起点**。
  Peter 战衣 164 骨，Miles 170 骨；有的便装有 527 骨。
- 关节哈希 = ALERT crc32(名字)，不归一化，保留大小写。顺序是 DFS 先序、子树连续（378/378 原版模型）。
- `ModelJointLookup` = (哈希, 序号)，按哈希排序，末尾加 (FFFFFFFF, FFFFFFFF) 哨兵。`ModelLeafIds` = 所有无子关节。
  `ModelJointHierarchy` = (0, 关节数, Mirror 数, Leaf 数, …)。
- 绑定姿势的四元数转成列向量 R，行向量的局部矩阵 = Rᵀ。
- `u2` 位（统计全部 1,614 个角色模型）：

  | 位 | 含义 |
  | --- | --- |
  | 0x80 | 带蒙皮权重 |
  | 0x02 / 0x04 | 左 / 右侧 |
  | 0x08 | `*_end` 叶 |
  | 0x10 / 0x30 | 布料关节 |
  | 0x01 | ⇔ 出现在 `ModelMirrorIds` 里（`invariant`） |

- `ModelMirrorIds`：`u16 (类型 << 12 | 关节), u16 镜像关节`，按关节号升序。中线关节映射到自己（类型 3），左右对只列一次。
  项数等于 hierarchy 的 mirror count。**追加的 0x01 关节没有镜像项时，游戏里会停在模型原点**（T9）。
- 追加关节时要同步：Joint、BindPose、InvBindPose、Lookup、Hierarchy 计数、Mirror、Leaf。本项目把关节追加在末尾，不满足「子树连续」，
  但实机正常（`runtime-confirmed`）。

### 3.4 ModelJointBspheres

- `u32 数量, 12 B 0`，然后每项 20 B：`f32 中心 xyz, f32 半径, u32 关节号 × 64`。只覆盖部分带权关节（advanced 是 45/80）。
- **运行时每帧用它重算模型实例的包围球**，进而决定动力学的更新距离（[物理](PHYSICS.md) §3）。`ModelBuilt` 的半径不参与。
- 一个只有 1 mm 占位网格的模型，这里的半径是亚毫米级。拿来当动力学载体前，要把半径放大（本项目放到 1 m）。

### 3.5 Look 与 Look 组

- Look：每个 look × 8 个 LOD 各一对 (u16 起点, u16 数量)，指向 LookBuilt 尾部的网格序号表。
  Peter 战衣的 look：Default、body、mask、dmg_decal、knife_*、civ_carry_coll。
- LookGroup：`u8 组数`，然后每组 24 B `(u64 列表偏移, u64 数量, u32 crc32(组名), u32 组名字符串偏移)`，之后是各组的 u16 look 序号表。
  一组是一个外观预设，显示组内各 look 的网格并集。
  - 战衣的 `Default` 组 = [Default, body, mask]；有的战衣还有 `noMask` 组 = [body]，摘面罩时用。
  - 便装 `hero_peterparker.model` 有 8 个预设（flannel / tuxedo / teacher …）。
  - Miles 的 `LookGroup_Mask` 之类是叠加开关，不是预设。
- **Karin 只放在 body/Default 槽，会在一些预设里隐身**（T5）。需要给每个看不到 Karin 的非叠加组再挂同一块几何（`cover_looks`）。

## 4. `.texture` 与 `.material`

- `.texture` 资产头两对：(DAT1 大小, B) 和 (SD 字节, B)。DAT1 = "Texture Built File" + 32 B 的头段 `4EDE3593`：
  - `u32 sd_len, u32 hd_len, u16 hd_w, hd_h, sd_w, sd_h, u16 array(1)`；
  - 6 B 角色字节（颜色 91 00、法线 12 00、gloss 93 02 / 93 00、mask 10 00）；
  - `u8 DXGI, u8 ?, u8 SD 级数, u8 HD 级数, 01 01 01 01`。
- SD 部分是 256（或更小）到 8×8 的各级，跟在 DAT1 后面；更大的级放在 span 1（HD，无资产头）。
- toc 的贴图 meta 72 B（18 × u32）：[0]=3、[4]/[6] 全尺寸宽高、[7]=1、[8] 总级数、[9] DXGI、[10]=1、[13]=0x4000、[14] SD+HD 字节、
  [15] HD 字节、[16] = HD 级数 | SD 级数 << 8。
- 常见格式：颜色 BC7 sRGB(99) / BC1 sRGB(72)，法线 BC5(83)，gloss BC1 sRGB（R 光泽，G ≈ 56–60），mask BC1(71)。
- `.material` 资产头一对：(DAT1 大小, B)。字符串块 = "Material Built File" + material graph 路径；DAT1 的 unknown 项是 (E1275683 段偏移, 大小)，
  段移动时要跟着改。
  - 段 `F5260180` 是序列化参数，贴图槽哈希：g 360110152、n 2061717114、c 2883245952、m 3867750572。
  - `E1275683` 的 +8 是渲染标志：不透明 0x2810 / 0x2811，睫毛的 alpha-test 是 0x2807，+52 处 f32 0.5 为阈值。
- **材质图要和网格顶点格式匹配**：`materialgraph\characters\shared\*_sand` 只给 fmt 5 网格用，在 fmt 1 网格上标题画面即崩溃（T4）。
  fmt 1 网格上常用的是 `required\materials\basic_normal_gloss`、`..._subsurface`、`cloth_distressed`。

## 5. `.actor`

经 `test_actor_roundtrip.py` 验证：全部 11,477 个 actor 解码再编码后逐字节相同。

- 资产头 16 B：`u32 0x521BEEB8 | u8 0 | u8 pairs=1 | u16 0 | (u32 A, u32 B)`。A 的低 30 位是 DAT1 大小。
  B 的含义未知，原版里约等于 DAT1 大小 / 8；改变长度时按 DAT1 大小同比例放大，实机可以加载。
- DAT1：`'DAT1', u32 0x521BEEB8, u32 size, u16 nsec, u16 nunk`，然后是按 tag 排序的段表、字符串块（C 字符串，绝对偏移），
  各段按 16 对齐。
  - `135832C8` ActorPriusBuilt：每个组件 32 B：`u64 实例 id, u32 name_off, u32 crc32(name), u32 0, u32 data_off（DAT1 绝对偏移，0 = 无数据）, u32 data_size, u32 0xFFFFFFFF`。
  - `6D4301EF` ActorPriusBuiltData：每个组件一个序列化对象，16 对齐。
  - `3AB204B9` 引用表：每项 16 B `(u64 crc64(路径), u32 字符串偏移, u32 扩展名哈希)`。扩展名哈希：.actor 0x37E72F50、.config 0xA9F149C4、
    .model 0xA4070B70、.animset 0xD1AD9F7C。
  - `32FAC8E0` ActorBuilt：首字是模型路径的字符串偏移（反斜杠路径）。
- 序列化对象：
  - 头：`u32 0, u32 0x03150044, u32 n_children, u32 data_len`；
  - n 个 `(u32 crc32(字段名), u16 flags（bit0 = 数组，>>4 = 个数）, u8 0, u8 节点类型)`，然后 n 个 u32 name_off（每次出现各存一个字符串）；
  - 按 4 对齐后是值，值之间**不对齐**（u8 / bool / f32 可以落在奇数地址）。
  - 字符串值内联：`u32 len, u32 crc32, u64 crc64, 字节, NUL`，再补零使 `(len + 1 + pad) % 4 == 0`；空数组写一个 0 字节。
  - 节点类型：u8 0x00、u16 0x01、u32 0x02、i8 0x04、i16 0x05、i32 0x06、f32 0x08、字符串 0x0A、对象 0x0D、bool 0x0F、u64 id 0x11、null 0x13。
- **同类型组件只认第一条**：类型描述的 `[ti+0xE4]` bit7 表示「允许多个」，HeroSuitAddition 的值是 0x01（`0x1428a5665`，`build-sensitive`）。
  多加的 HSA 在实机上被丢掉（T18 `runtime-rejected`）。
- 改组件字段时，引用表要同步：带 Autoload（默认 true）的 AssetReference 和 File 字符串都要在引用表里有一行。

## 6. 战衣链与 loadout

- 链条：`configs/inventory/inv_reward_loadout_*.config`（118 个）→ `configs/masteritemloadoutlist/itemloadout_*.config` →
  各 vanity 物品 → `.model`。每套战衣有自己的身体模型；`equip_*_var*.config` 的款式是在同一模型上按名字覆盖材质。
- 目标模型共 108 个，7 种骨架签名。Peter 战衣 45 个、Miles 战衣 45 个共用两种签名；便装、young 等是其余几种。
- 一个 loadout 由几件物品组成：`VanityBody_SpiderMan.config`（kTypeBodyActor → `hero_spiderman.actor`）、`VanityHEDSpiderMan1.config`
  （kTypeHeadActor → `HMA_HED_base.actor`）、战衣物品（kTypeBareTorsoAndArms → 战衣模型）。
  Miles 的 loadout 不带头物品，用 `hero_milesmorales.actor` 的 `HeadManager.HeadActor` 默认值，也是 `HMA_HED_base.actor`。
- **91 个战衣模型的每个 loadout 都生成同一个头 actor `actors/hma_hed_base/hma_hed_base.actor`**，模型是 `test_i20_Head.model`。
  这个头只有 14 个关节和一个 1 mm 的四边形，其它东西都不用它。v2 就把物理放在这里（[物理](PHYSICS.md) §5）。
  - 例外：`hero_spiderman_antiock.model` 也被剧情 loadout `spiderman_nomask` / `antiock_nomask` 使用，那里的头是 Peter 的脸。
  - 便装（Peter 10、Miles 4）、young 和两个过场模型有各自的头 actor。

## 7. HeadManager（头 actor 的关节映射）

- 英雄 actor 的 `HeadManager` 组件有三个字段：`HeadActor`、`AutoMatchJoints`（Peter 和 Miles 都是 false）、`CustomJointMap`（`{BodyJoint, HeadJoint}` 对象数组）。
- 映射内容：
  - Peter：a_body、chest、neck、head、LF_clavicle、RT_clavicle；
  - Miles：同上，另加 root；
  - `boss_symbiote_pete.actor`（共生体 Peter boss，用 hero_spiderman_base 并穿战衣 loadout）：同 Peter；
  - 菜单的 `ui_spiderman_proxy` / `ui_spidermanmiles_proxy`：没有 CustomJointMap，按名字自动匹配。
- **头 actor 里只有被映射的关节跟随身体**；其余关节作为它们的子节点刚性跟随。
  **a_body 是移动根，不跟随胯部动画**，所以挂在头 actor 上的尾巴必须把 pelvis 也加进映射（T21 → T22）。
- 头模型缺少某个映射关节时，该项被跳过，不报错（`test_i20_Head` 没有 root，Miles 照常显示）。
- 映射的语义：Miles 的 head 关节在 bind 下比 Peter 靠前 21 mm，但一个按 Peter 对齐的载体在 Miles 身上也没有可见偏移（T21–T23）。
  所以按「相对 bind 的变化」来处理：载体几何放在身体的 bind 空间即可，两族共用（`hypothesis`，有实机支持）。
- HeadManager 每帧对映射子树施加一个刚体变换（`0x1429c3435` → `0x142b12ce0`），并不覆盖子关节的动力学结果。
  所以头 actor 上的链可以自由模拟（`build-sensitive` 地址，T21 实机证实行为）。
