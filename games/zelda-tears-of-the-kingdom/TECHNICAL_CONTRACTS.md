# 技术合同

游戏 1.2.0、yuzu EA 4176。数字和名字都是 `build-sensitive`，除非另有说明。

## 1. 加载：LayeredFS 与 RESTBL

- **mod 位置**：`user\load\0100F2C0115B6000\<mod 名>\romfs\<游戏内路径>`。exefs 补丁放 `<mod 名>\exefs\`，例如 UltraCam。UltraCam 的设置在 `user\sdmc\UltraCam\`。
- **加载顺序**：同一文件被多个 mod 提供时，**文件夹名排序靠前的那个生效**（`invariant`，对 yuzu 系模拟器）。
  - 本 mod 用 `00_` 开头，所以能盖过 `03_kalin` 的同名模型、pack 和图标。
  - 在模拟器的「附加组件」里取消勾选，可以临时停用一个 mod。
- **RESTBL**：`System/Resource/ResourceSizeTable.Product.120.rsizetable.zs`。
  - 文件比表里记的大小大，游戏就读不了。整张表也是普通文件，所以同样是排在前面的生效。
  - 本 mod 的表 = 原版表 + 其他启用的 mod 改过的条目（每项取较大值） + 本 mod 自己的条目。
  - `03_kalin` 改了 11311 条，已经包含 `01_Kalin_Base` 的文件，所以只需合并它的表。
  - 格式：`RESTBL`、u32 版本、u32 名字长度（0xA0）、u32 crc 条目数、u32 名字条目数。然后是按 crc 排序的 `(u32 crc32(路径), u32 大小)`，最后是撞 crc 的路径 `(char[0xA0], u32)`。
  - 键是去掉 `.zs` / `.mc` 后缀的游戏内路径，例如 `Model/Armor_1061.Armor_1061_Head.bfres`。
  - 大小估算（`package.py`）：

    | 类型 | 估算 | 与原版对比 |
    |---|---|---|
    | txtg | align32(文件) + 256 | 与原版逐条相同 |
    | pack | align32(解压后) + 384 | 与原版逐条相同 |
    | bntx | align32(解压后) + 256 | 与原版逐条相同 |
    | Switch Toolbox 存的 BFRES | align32(解压后) × 2 + 64 KB | 刻意放宽 |

  - 原版条目比估算大时保留原值：Head 原版记 23.6 MB，实际只需 1.26 MB。

## 2. 模型：`.bfres.mc`

- **封装**：`MCPK`、`01 01 00 00`、u32 flags，后面是不带 magic 的 zstd 帧。
  - 解压大小 = `(flags >> 5) << (flags & 0xF)`，写出时按 4 KB 向上取整：`flags = ((size_4k >> 12) << 5) + 0xC`（`mc.py`，与 Switch Toolbox 的 MeshCodec.cs 一致）。
- **零售版顶点数据**：用任天堂的 mesh codec 压缩，Switch Toolbox（2026-10-31 版）读不了（`build-sensitive`）。
  - 能读的是 Switch Toolbox 另存过的 BFRES：解压后 0xEF 处的字节为 1，表示不需要外部字符串表就能重新打开。
  - 项目用用户旧 mod `03_kalin` 的三件 1061 当基础模型，骨架、材质、平滑矩阵表都来自它们。
  - 原版模型只用来核对骨骼名和材质名。
- **平滑矩阵表**（skeleton 的 Node_Array）：只有列在表里的骨骼能当蒙皮骨骼。
  - 原版 / 03 的头部只列了 Head、Hair_Back_C/L/R_1–3、Momi_A_1/2；上衣只列了 Skirt_1/2_BC 两根裙骨。
  - TotkMdl `replace` 的 `smoothBones` 会按需要的骨骼重建这张表。重建后 24 根裙骨、Hair_Side_A/B 和各个布料骨骼都能用。
- **Link 的绑定姿势**：T 姿势。
  - Head 关节高 1.518 m，Waist 0.994 m，手腕 x 0.70 m，Arm_1 在 x ±0.183 m。
  - 右手是单独的模型 `Link_RaulSkin_RightHand`，套装上衣里没有右手指骨，所以 Karin 的右手不画（03 也一样）。
- **本 mod 的形状**：

  | 模型 | 形状 |
  |---|---|
  | 头 | `KarinOri_Face`、`KarinOri_Hair`、`KarinOri_HairAcce`、`KarinOri_Neck` |
  | 上衣 | `KarinOri_Body`、`KarinOri_Clothes`、`KarinOri_Tail` |
  | 下装 | `KarinOri_Legs`、`KarinOri_Socks` |

  - 文件名：`Model/Armor_1061.Armor_1061_{Head,RaulSkin_Upper,Lower}.bfres.mc`。1062–1064 的升级档引用同一组模型。
- **权重格式**：原版是 `Format_8_8_8_8_UNorm`。头部的脸、头发改成 `Format_32_32_32_32_Single` 后，带符号、大于 1 的权重在实机生效（`runtime-confirmed`，[面部](FACE.md) §4）。

## 3. 材质、贴图与染色

- **材质**：Karin 的所有部件都用原套装皮肤材质（Link 皮肤着色器）的副本，每个部件一套贴图。
- **TexToGo `.txtg`**：
  - 布局：0x50 字节头 → 每个 surface（mip 为主序、数组为次序）一个 `u16 数组, u8 mip, u8 1` → 每个 surface 一个 `u32 zstd 大小, u32 6` → 每个 surface 一帧 zstd，内容是块线性重排后的数据。
  - `txtg.py` 写出的文件与原版逐字节相同（132 个 surface 核对过）：
    - 每个 mip 单独做块线性重排，截断到最后一个用到的字节；
    - 重排调用 Switch Toolbox 的 `tegra_swizzle_x64.dll`。
  - 贴图头的模板：

    | 贴图 | 模板 | 格式 / 参数 |
    |---|---|---|
    | 反照率 | `Link_RaulSkin_Alb` | 格式码 0x101（ASTC 4×4），flag 1；本 mod 按 sRGB 编码 |
    | 法线 | `Link_RaulSkin_Nrm` | 平直 BC5（0x707），flag 4，分量 (R, G, 1, 1) |
    | Spm | `Link_RaulSkin_Spm` | 常量 BC4（0x606），flag 6，值 20（原版均值 35、中位 15） |

  - 贴图名用新的 `KarinOri_*`，不与其他 mod 冲突。
- **染色动画**（v1 实机问题的原因）：`Model/Armor_1061.anim.bfres.zs` 里的 `Head/Upper/Lower_ftp` 是贴图切换动画。
  - 套装的 ModelInfo 通过 `ModelVariationAnims` 和 `ColorVariationParam ArmorDye` 引用它，共 16 帧，第 0 帧 = 未染色。
  - 它按材质名绑定：`Mt_Upper_L/R_1061`、`Mt_Upper_Acce_L/R_1061`、`Mt_Lower_1061`、`Mt_Head_1061`、`Mt_Head_Paint_1061`、`Mt_Hair_1061`、`Mt_Face`。
  - 动画把这些材质的 `_a0` 设成 `Armor_1061_{Upper,Lower}_Alb.<n>`。`03_kalin` 正好用这些名字放它自己的图集，所以 v1 的身体和腿显示了 03 的贴图。
  - **修法**：TotkMdl `renameMaterials`（保持顺序），把用到的染色绑定材质全部改名为 `Mt_KarinOri_<形状>`。几何不变，RESTBL 不变；代价是染色对 Karin 无效。

## 4. Pack 与压缩

- **ZsDic 字典**：`Pack/ZsDic.pack.zs` 是 zstd 压缩的 SARC，里面有 `zs.zsdic`、`pack.zsdic`、`bcett.byml.zsdic`。

  | 文件 | 字典 |
  |---|---|
  | `.pack.zs` | `pack.zsdic` |
  | `.bcett.byml.zs` | `bcett.byml.zsdic` |
  | `.rsizetable.zs` | 不用字典 |
  | 其他 `.zs` | `zs.zsdic` |

- **SARC 写出时的对齐**：FRES / BNTX 0x1000，嵌套 SARC 0x2000，BYML 8（`totkfs.py`）。
- **头盔 pack** `Pack/Actor/Armor_106{1..4}_Head.pack.zs`：ArmorParam 的 `HideMaterialGroupNameList` 追加 `G_Face_Only`、`G_Head_All`，戴上头饰时隐藏 Link 的脸和头。
  - 这是 `03_kalin` 对 pack 唯一的修改，四个等级的差异相同。本 mod 原样沿用。
- **cloth**：头和上衣的 pack 里有 `Phive/Cloth/*.bphcl`（Havok cloth）和 ClothParam；`.bphhb` 是辅助骨。本 mod 不改它们（[物理](PHYSICS.md)）。

## 5. 背包图标

`UI/Tex/Icon/Armor_106?_{Head,Upper,Lower}.bntx.zs`：BNTX 里一张 256×256、格式 0x2D06（ASTC 4×4 sRGB）、1 个 mip 的图。

`make_icons.py` 按原大小、原块高度重排后原地覆盖像素数据，文件其余部分不变。

## 6. 动画

- **玩家动画**：`Model/Player_Animation.anim.bfres.zs`，压缩后 14 MB，解压 36 MB。
  - 骨架在 `Player_Animation.Skeleton.bfres.mc`（121 根骨），面部骨骼的静止姿势与头部套装骨架相同。
- **读取**：Syroot.NintenTools.NSW 读不了本作的动画 BFRES（FMAA 块），所以 `fska.py` 自己实现了 FSKA v10：
  - 结构大小：头 0x50，BoneAnim 0x38，曲线 0x30；
  - 关键帧：int16 三次曲线，值 = 关键值 × scale + offset；
  - 基础数据：0x10–0x18 平移，0x20–0x28 欧拉旋转，R = Rz·Ry·Rx。
- 面部动画清单和用法见 [面部](FACE.md) §1。

## 7. 原版文件的获取

- **yuzu 的「转储 RomFS → 完整」**：在 `Banc/` 里报错后卡死（2026-11-02），不可用。
- **NxExtract**（LibHac 0.19）：
  - 基础版取 XCI 里的程序 NCA，更新取 NAND `registered\` 里 1.2.0 的程序 NCA，叠加后按 glob 列出或解出。
  - 需要 `prod.keys` 和更新的 title key（yuzu 的 `title.keys`）。
  - 在 pwsh 7.4（.NET 8）里用 `Add-Type` 加载，`nxx.ps1` 是驱动脚本。
  - glob 不支持 `[]` 字符类。

## 8. 存档

`progress.sav` 的结构见 [存档与发行](SAVE_AND_RELEASE.md) §3。
