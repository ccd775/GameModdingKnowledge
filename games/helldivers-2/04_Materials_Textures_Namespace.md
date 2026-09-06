# 材质、贴图、UV、Draw 与私有资源合同

> 适用范围：HD2 角色替换 Mod。通用方法为 `project-proven`；工具/序列化行为为 `format-confirmed`；SR24 的 ID、尺寸、数量和阈值均为 `case-specific`。

## 1. 五个独立责任域

材质问题必须拆成：

```text
UV 语义
纹理编码与像素
shader/child 参数
draw/section 路由
Material/TextureMap 资源 ID
```

- 看到黑色、过曝或透明异常时，不要立即重做 atlas。
- 一次候选只改变一个责任域，先做单变量探针，再合入最终闭包。
- 模型引用数值 Material ID，不依赖 Blender 显示名；child Material 同样按数值 TextureMap ID 引用纹理。
- 源贴图 provenance 来自实际材质 node/binding、UV ROI 与文件哈希，不来自同目录文件名。磁盘上“看起来配套”但材质未绑定的 normal/control 可能是废弃或错误资产，必须先做像素/ROI 审计。
- AQ load/save 只证明资源可解析/重序列化，不证明颜色、透明、光照和运行时 draw 正确。
- 用户截图可推翻全部静态材质门禁。

## 2. 先冻结材质与 draw 合同

每个 Unit、LOD、RawMesh 记录：

```text
raw_mesh_count
material_section_count
ordered list of (material_id, start_index, index_count)
total index coverage
child material parent / variables / texture references
```

### 材质槽与崩溃

- 替换 LOD 的材质槽或 section 数超过原生目标合同，可能启动即崩溃。
- 新外观分组应在 donor/目标允许的 section 内拆分或复用，不可任意增加 Blender 材质槽。
- 所有 LOD 都要检查；只看 LOD0 会漏掉距离切换错误。
- AQ 导入旧 patch 时可能无法恢复原生 material-slot ID，生成的槽位名不是 ID 证据；必须解析 Unit 数值 ID 和 draw range。
- hidden/fallback mesh 可有事先声明的 stock material 哨兵。门禁应锁精确 Unit/LOD/位置/次数，不要禁止所有 stock material。

### 锁完整三元组

正确门禁逐 LOD 比较：

```text
(material_id, start_index, index_count)
```

并验证 section 数、顺序、连续覆盖、无重叠、无越界。若修复只应改材质路由，还要证明：

- 只改预期数量的 64-bit Material ID 字段。
- GPU、stream、indices、UV、position、weights、BoneInfo 不变。
- AQ 回读的 material table 与 raw-material table 匹配。
- 输入 triplet 哈希不变。

SR24 V21 Head 每级最终为 `(0,54882)` 与 `(54882,3324)` 两段，虽然都走同一 opaque face material 仍保留两 draw。旧脚本硬编码 `54879` 已被门禁拒绝。这些数值不得复制到新项目。

## 3. UV 层存在不等于语义正确

当前已验证的不透明角色路线使用：

| UV | 语义 |
| --- | --- |
| UV0 | BaseColor/角色 atlas |
| UV1 | gore/size 等附加效果数据 |
| UV2 | decal atlas |

必须验证三层 loop 数、有限性、范围、面实际落点、各 section 与 LOD 的一致性。HD2SDK 的“复制三份 UV”只保证数量/布局，不会自动产生 UV1/UV2 语义。

把 UV0 复制到三层或将后两层清零可能让基础颜色正常，却无法宣称支持 gore、血液、污渍或 decal。O44 Advanced 的 `WoundPaintingEnabled=0` 且 UV1/UV2 全零，因此 New_SR24 基础材质不能宣称支持玩家血液、Terminid gunk、acid 或环境覆盖层。

材质迁移后必须重新读取目标 parent shader 的 component mapping。Advanced 常从 UV0 取作者 atlas，不代表 Armor LUT 仍从 UV0 取同一颜色；已观察到 Armor LUT 将 UV0 用于 BaseData/ID mask、UV1 用于动态 tiler、UV2 用于 DecalSheet。具体索引属于 parent/game-build ABI，不得仅凭上述案例硬编码。

## 4. BaseColor 与数据纹理色彩空间

- BaseColor、肤色、衣物颜色通常使用 `BC7_UNORM_SRGB`。
- NAR、normal、control、mask 按 shader 合同使用线性格式，例如 `BC7_UNORM`。
- 指定输出格式不一定足够；对无明确 sRGB 元数据的源图，`texconv` 需显式 `-srgb`。
- 编码后重新解码 DDS，在固定 alpha/ROI 下与源图比较；只查 DDS header 不够。

推荐命令形态：

```powershell
texconv.exe -y -f BC7_UNORM_SRGB -srgb -w <W> -h <H> -m 1 `
  -o <fresh-output-dir> <source.png>
```

SR24 错误路径把源图平均 luma `102.80506` 抬到约 `139.7`；正确路径解码为 `102.81463`。这些数值只说明应做像素回读，不是通用阈值。

## 5. 稀疏 Alpha 与 `-sepalpha`

RGBA 的 alpha 很稀疏时，BC7 联合压缩会让低 alpha 区参与 RGB 端点选择，导致遮罩外 RGB 变黑或变白；此时 material ID、UV、shader 可能都正确。

处理合同：

1. 使用 `texconv -sepalpha`。
2. 在两个新目录独立编码，要求 DDS 逐字节一致。
3. 检查 format、尺寸、mip、header、payload。
4. 解码后分别比较遮罩内/外 RGB 与 alpha。
5. 补丁只允许改变目标 TextureMap 的 GPU payload 区间。

```powershell
texconv.exe -y -f BC7_UNORM_SRGB -srgb -sepalpha `
  -w <W> -h <H> -m 1 -o <fresh-output-dir> <source-rgba.png>
```

New_SR24 的 face fill 缺少 `-sepalpha` 时 Head 在游戏中大片黑白；重编码只替换对应 TextureMap GPU 区间，Material、ID 和槽位保持。

## 6. “Transparent” 只是名字

透明策略根据实际 alpha 和目标 shader 决定：

- 统计 alpha min/max、分位数、低于 cutoff 的像素数。
- 只统计实际被目标面/UV 使用的区域。
- 区分真镂空、浅半透明、全不透明和 alpha 作为其他 shader 数据。
- 游戏不支持浅半透明时，近乎不透明的卡片通常走 opaque。
- 对象/材质名含 `Alpha` 或 `Transparent` 不是 AlphaClip 证据。

SR24 的刘海最低 alpha `0.996`，没有像素低于 `0.5`；最终四级 LOD 都走 opaque，模型中 AlphaClip 引用为 0。早期私有 AlphaClip 只是诊断阶段，后续实测推翻了该假设。

## 7. Emission、atlas alpha 与 AO 分开诊断

同一 atlas alpha 在 parent shader 中可能是 emission mask，而非透明度。推荐顺序：

1. 读取 parent/child 参数与 TextureMap slot 语义。
2. 统计 atlas alpha 覆盖。
3. 只将 emission strength 改为 0，其余字节冻结。
4. 单独修 sRGB。
5. 最后才修改 alpha 或 parent。

O44 Advanced 的颜色/发光 mask 与强度 `20/30` 叠加 C4 非零 alpha，造成全身青白过曝；这不是单纯“贴图太白”。

### 跨 parent 迁移时必须重新定义 alpha

不能因为同一 TextureMap 的 RGB 可复用，就假定其 alpha 在另一个 parent shader 中也可复用。Advanced 的 Color/Emission atlas alpha 可能是 fill 或 emission mask；Armor LUT 的 DecalSheet alpha 可能直接控制作者颜色 coverage。若把前者原样接到后者，低 alpha 区会露出 LUT 金属底层，即使 RGB、UV、Material ID、namespace 和 LUT 都完全正确。

处理合同：

1. 分别记录 source slot 与 target slot 对 RGBA 的通道语义，不能只记录纹理名。
2. 解码并统计全图及实际 UV ROI 的 alpha min/max、0/255 像素数和分位数。
3. 若目标 draw 逻辑上应全不透明，而 source alpha 只是旧 shader 数据，构造独立 opaque Decal 资产：RGB 保持，输入 alpha 固定 255。
4. 使用 alpha-preserving BC7 编码并回读，要求 alpha min/max 精确为 255，同时记录 RGB PSNR/ROI。
5. 补丁只改目标 TextureMap 的 GPU payload；保留已验证 Material、UV、LUT 和 Texture main metadata。归档反提取 DDS 的 `miscFlags2` 可能继承旧容器，与 texconv 输入头不同；验证应锁定 ABI 与像素 payload，不能为追求整份 DDS 哈希一致而无证据改写 metadata。

New_SR24 V24 的 2048² head atlas 有完整 RGB，但 alpha 88.4498596% 为 0、最大仅 191、没有 255。Advanced -> Armor LUT 后，hair/eyes/ears 因 Decal coverage 缺失变成深灰金属。V25 仅把 head Decal alpha 固定为 255，解码 4,194,304 个像素全部保持 255；RGB PSNR 60.3167 dB，其余资源不变。

### 动漫脸“脏”不一定是 AO

- 先确认 NAR 的 AO 是否本来已中性。
- 分离 diffuse 梯度、动态光、AO 和 emission 做 A/B。
- skin-only mask 排除眼睛、眉、嘴线和刘海，并做 ROI 像素门禁。
- 不要长期用 emission 抵消阴影，它会让面部在其他光照下高于身体。

New_SR24 的低强度 face fill 在离线强阴影下有效，但游戏中脸过亮；最终只把 face emission 一个 float32 从 `0.18` 改为 `0`，其他材质/GPU 不变。

## 8. 确定性私有资源命名空间

### 必须私有化

- 自定义 child Material。
- child 引用的所有本地 TextureMap。
- 面部、透明件、mask 等新增资源。
- 从 donor 复制但 payload 会改变的任何本地资源。

通常只共享已确认的 stock parent Material 引用，不修改 stock parent 本身。

### 稳定 ID

为资源建立带版本的语义路径：

```text
mods/<author>/<mod>/<version>/materials/<semantic>
mods/<author>/<mod>/<version>/textures/<semantic>
```

使用游戏一致的 Murmur64A 生成 64-bit ID，并在 manifest 记录 type、semantic、name、old/new ID。不要随机生成，不要只改模型 Material ID 而漏改 child 内 TextureMap 引用。

### 精确旧版替换时的 namespace 例外

同一批私有 ID 只有在以下条件同时成立时才可沿用：

1. 新包明确替换同一 Mod 的旧 lineage，而不是与它共存。
2. live 旧三件套逐份匹配已诊断版本的 SHA-256。
3. 碰撞扫描只排除这一个即将被替换的精确 triplet，其他 archive root 全部扫描。
4. 打包/部署合同明确禁止旧新版以其他 patch index 同时启用。

任一 live 哈希变化、旧版可能残留、普通并存升级或作者无法证明 lineage 时，都必须创建新 namespace 并从 Material/TextureMap 闭包重新编译。Umbrella v2 的 same-slot replacement 是该例外的离线案例，不是“同一作者永远可复用 ID”的许可。见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

SSF v4 即使与 v1-v3 属于同一项目，也为普通升级创建新的版本 namespace，并在封包时重扫当前 live patch TOC；随后获得用户运行时验收。可复用结论是“新版本默认新 namespace，发布时扫描当前外部状态”，其具体 ID 不可复制。见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

### 两级碰撞审计

同时检查：

- 完整 64-bit ID。
- high32/ShortID/thin ID。

扫描最终候选、donor、参考 Mod、当前游戏安装资源、工作区其他 Mod 和历史候选。任何 parser error 都使审计失败；只把本候选/roundtrip 目录列为 allowed roots。

迁移后要求：

- donor 本地 ID 不再出现在模型材质或 child texture refs。
- 每个本地 TextureMap 引用在最终 archive 闭合。
- 每个运行时 Material 被模型正确引用，或明确标记为有意未引用。
- full/high32 冲突均为 0。

旧 New_SR24 候选完整复用 O44 的 2 child Material + 6 TextureMap ID，Unit ID 虽不冲突仍按加载顺序串贴图。最终使用私有 namespace 和 4 Material + 10 TextureMap；具体 ID 不可复用。

## 9. 构建顺序也是合同

通用顺序：

```text
visible Unit compile
-> complete visible/hidden Unit merge
-> special Head draw/material
-> private face/special material
-> all child/texture private namespace migration
-> alpha-data-driven opaque/AlphaClip rewrite
-> frozen final material closure
-> final integration audit
```

每步声明输入资源计数、预期 ID occurrence 和允许 delta，计数变化时失败关闭。

namespace 迁移中间产物可能只用于证明 ID rewrite，不一定含完整最终材质。最终 merge 必须选明确冻结的材质闭包，而不是文件时间最新的产物。

## 10. AQ 往返的正确分层

- Material/TextureMap：当前工具链可执行 AQ load-save，并要求适用的 payload 字节一致。
- Unit：`Unit.Save()` 会规范化 offset/material-slot 元数据，不适合作为任意旧 Unit 的通用字节身份门；用 load-only 语义验证，同时要求 Unit payload 与已独立审计源一致。
- Archive：最终 triplet 验证资源 key、精确集合、引用闭包、整档 roundtrip、输入不变和第二次独立构建。
- 空 `.stream` 是合法文件，不可省略。

AQ 写/往返任务必须串行。共享 TEMP 竞争曾导致 `all_resources_aq_validation_byte_exact=false`、`OSError 22` 和部分资源失败。必要时隔离 `TEMP/TMP`；失败报告保留，重新生成 r2/r3，不覆盖。即使失败任务输出碰巧同哈希也不能作为 binding evidence。

## 11. 最终材质门禁

```text
[ ] 每级 LOD section 数不超过目标合同
[ ] 每个 draw 的 material_id/start/count 精确且覆盖合法
[ ] 每张源贴图由实际材质 binding、UV ROI 和文件哈希证明；未绑定的邻近文件未被误用
[ ] UV0/UV1/UV2 数量与语义分别通过
[ ] BaseColor sRGB，数据纹理为正确线性格式
[ ] 稀疏 alpha BC7 已评估/使用 -sepalpha
[ ] DDS 解码后像素与 ROI 比较通过
[ ] 每个语义类型的 base-level 总像素面积不超过项目预算
[ ] 逻辑不透明的 BC7 BaseColor 解码后 alpha 仍满足不透明硬门
[ ] emission、strength、atlas alpha 组合已审计
[ ] 跨 parent 的 source/target alpha 通道语义已分别证明；Advanced emission/fill alpha 不得直接当 Armor LUT Decal coverage
[ ] AO、diffuse、动态光、emission 已分离诊断
[ ] child Material/TextureMap 全部私有化
[ ] full 64-bit 与 high32/ShortID 冲突为 0
[ ] model -> Material -> TextureMap 引用闭合
[ ] donor 本地 ID 不再出现在结构引用中
[ ] Material/TextureMap AQ load-save 通过
[ ] Unit 使用 load-only + 独立 payload identity
[ ] 整档 triplet roundtrip 通过
[ ] 两次串行独立构建逐字节一致
[ ] 所有输入哈希前后不变
[ ] offline_verified 未冒充 runtime_validated
```

## 12. 症状速查

| 症状 | 常见误判 | 优先检查 |
| --- | --- | --- |
| 全身青白 | BaseColor 太亮 | emission strength/color × atlas alpha |
| 普遍偏亮 | 仍是 emission | 归零 emission 后比较 sRGB luma |
| 头发局部异常偏暗 | atlas 底色坏 | 检查 normal 是否真的被源材质绑定；审计对应 UV cell 是否为黑/无效法线 |
| 刘海发黑 | UV 坏 | Head 第二 draw 是否路由到 gore/错误 material |
| 刘海消失 | 调 cutoff | 先统计 alpha；接近全 1 时走 opaque |
| Head 纯黑/白 | namespace 冲突 | 解码稀疏 alpha BC7，检查 `-sepalpha` |
| Head hair/eyes/ears 呈深灰金属 | UV/LUT 仍坏 | 检查 Advanced atlas alpha 是否被误作 Armor LUT Decal coverage |
| 动漫脸脏 | AO 必然过重 | NAR AO、diffuse 梯度、动态光分离 |
| 脸比身体亮 | diffuse 清理过头 | face emission 是否仍非 0 |
| 两 Mod 串贴图 | Unit ID 冲突 | child Material/TextureMap full/high32 冲突 |
| 启动即崩溃 | 骨架坏 | LOD 材质槽、section 数、draw range |
| AQ 导入材质名变化 | 原 ID 变化 | 不信显示名，解析数值 ID |
| roundtrip 偶发失败 | 资源坏 | AQ 并发 TEMP、`OSError 22`、插件注册 |

## 13. 证据入口

- [New_SR24 SOP](../../SOURCE_REFERENCES.md#local-only)，特别是 7.7、7.10-7.16、7.18、7.21、7.25、7.28、7.57、7.63-7.65。
- [刘海根因记录](../../SOURCE_REFERENCES.md#local-only)
- [face sepalpha 构建](../../SOURCE_REFERENCES.md#local-only)
- [face emission-zero 验证](../../SOURCE_REFERENCES.md#local-only)
- [private namespace manifest](../../SOURCE_REFERENCES.md#local-only)
- [O44 隔离审计](../../SOURCE_REFERENCES.md#local-only)

## 14. 总贴图面积预算与语义小计

“单张不超过 4096”不能限制一个 Mod 同时携带多张重复大图。若项目要求“全部贴图合计不超过 4096²”，主门禁必须按包内不同私有 TextureMap FileID 汇总，而不是让每个 semantic 分类分别获得一份 4096²：

```text
total_local_pixels
  = sum(width * height for each distinct packaged private TextureMap FileID)
total_local_pixels <= project_total_limit

semantic_pixels[k]
  = sum(width * height for each counted texture whose semantic == k)
sum(semantic_pixels.values()) == total_local_pixels
```

- 每个不同私有 TextureMap ID 计一次，即使两个 ID 的 GPU payload 相同；只有先重写引用并真正去重资源后才能少计。
- BaseColor、Normal/NAR、Data/Control、Emission、runtime Material LUT 分开报告小计，但小计不能代替严格总预算；不要把压缩后的字节数当像素面积。
- primary/secondary 若引用完全相同的像素，应重写 child 引用并合并为一个本地 TextureMap，而不是保留两份重复 DDS。
- 删除已经没有 Material 或 Unit 引用的诊断 AlphaClip/旧材质闭包；先证明引用数为 0，再移除资源。
- 降采样后重新验证 DDS format、sRGB/linear、mip、alpha 和关键 ROI；尺寸合规不代表内容正确。
- mip 链是否计入预算必须由项目合同明确。本知识库默认的“4096 平方”指 base-level 面积；显存/磁盘预算另算。
- 23x8 一类参数 LUT 是独立语义，仍应计数，但不能拿它抵消 BaseColor 或 Normal 的预算。

New_SR24 V22 的案例值为 BaseColor `3072² + 2048² = 13,631,488`、Normal/NAR `4096² = 16,777,216`、Data `2048² = 4,194,304`、九张 runtime Material LUT 合计 `1,656` 像素。这些尺寸是 `case-specific`，算法是 `project-proven`。

Umbrella v2 按 11 个私有 TextureMap 的 base level 合计为 `8,912,945 / 16,777,216` 像素；其中两张 2048² 主图和全部小依赖都计入。这是严格 aggregate-total 合同的 `case-specific` 示例。

SSF v4 的 11 个私有 TextureMap 合计 `4,718,641 / 16,777,216` 像素；两张 `2048x1024` 主图之外，禁用数据和 shader ABI 小贴图也全部计入。这是同一严格总预算的另一个 `case-specific` 示例，见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

### 逻辑不透明的 BC7 alpha

源图 alpha 全为 255 不保证 BC7 回读仍为 255。New_SR24 的普通 BC7 编码曾解码到 alpha 251，可能重新触发不希望的半透明/裁切语义。处理路线与稀疏 alpha 的 `-sepalpha` 不同：

1. 先把输入 alpha 明确写为 255。
2. 使用 exhaustive BC7 搜索并提高 alpha 权重，例如 DirectXTex `-bc x -aw 1000`。
3. 解码 DDS，要求 alpha min/max 都为 255；同时记录 RGB PSNR/ROI，防止只顾 alpha 损伤颜色。
4. 两次隔离编码，绑定命令、工具哈希和输出 DDS 哈希。

## 15. Armor LUT/splat 恢复的三层合同

Armor LUT 迁移不是“把 parent ID 换成 Armor LUT”。至少要分别证明：

```text
Unit UV ABI
  -> child/root Material ABI and static IdMasksArray/MaterialLut
    -> runtime HelldiverCustomizationKit -> Body -> Piece.MaterialLut
```

### Material 与可见接收者

- native parent 是 ABI donor，不是中性外观 donor。克隆到私有 root 时，主/GPU payload、thin ID 镜像、13-slot/40-variable 等合同必须由当前模板重新测量。
- Advanced 到 Armor LUT 的 child 必须重建完整纹理槽和变量 ABI；不能只改 `ParentMaterialID`。
- 动漫脸可在用户明确接受“该 draw 无 splat”时保留 Advanced child，以避免 splat/AO 路线污染面部；这不是默认完成条件。若用户要求头部/头盔也接收 splat，必须为 head 重建 hybrid child、保留干净 face atlas，并单独证明 head UV1/UV2 与运行时 Helmet Piece LUT。
- 全零 IdMasksArray 权重意味着 row 0 fallback；必须把实际 mask 与静态 LUT 一起审计，不能凭 dominant-row 预览推断硬选择。

### UV1 必须有可用坐标

声明了 UV1/UV2 不等于有坐标。常量 `(0,1)` 会让目标采样退化。若 shader 证据要求身体 UV1：

- 只选择使用目标 body Material 的顶点，并拒绝与 face/其他 Material 共享的顶点。
- 使用连续投影或经证明的源 UV 通道；相同 float32 position 必须得到相同 float32 UV，避免 Unit/LOD 接缝。
- 对每个非退化 3D 三角形检查 UV 面积；exact 和 near-degenerate 都应为 0 或有显式例外。
- main patch、stream、GPU 长度保持；仅允许选中顶点的目标 UV component 字节区间改变。

New_SR24 V22 复用了 O44 已搜索并验证的全局斜投影基向量作为方法，但重新对 SR24 的 10 个 body Unit、40 个 mesh、552,428 个顶点和 604,864 个三角形执行了独立退化门禁。具体基向量和计数不可复制到其他模型。

### UV2 必须让 DecalSheet 作者颜色可达

连续 UV1 只证明 blood/gunk/weather tiler 有坐标，不证明作者颜色 atlas 被采样。Advanced -> Armor LUT 后若 clean body 统一变成灰、银或黑色，而 LUT 调整仍能改变金属度/粗糙度：

- 先从目标 shader 证明 DecalSheet 使用哪个 Unit UV component，以及是否存在严格 `(0,1)` 开区间门禁。
- 测量选中 Material 的实际 UV 值。常量 `(0,1)`、`(0,0)` 或只有结构声明的零填充通道都不是有效 atlas coordinate。
- 若源 Advanced 的作者 atlas 由 UV0 驱动、目标 Armor LUT 的 DecalSheet 由 UV2 驱动，可在无跨 Material 共享顶点的前提下做 material-scoped UV0 -> UV2 字节复制；UV1 保留专用连续投影。
- 证明 main/stream、GPU 长度、UV0、UV1、模型和非目标 GPU 字节保持，且每个目标 UV2 与源 UV0 逐字节一致。
- clean color 仍是运行时门禁。Material/Texture/LUT/SDK roundtrip 全绿不能证明 sampler branch 实际执行。

New_SR24 V22 因只修 UV1、遗漏 DecalSheet UV2 而在游戏中全身变成深灰金属；V23 的唯一变化是 10 body Unit / 40 mesh / 552,428 顶点的 UV0 -> UV2 复制，随后由用户确认身体 clean color/splat 恢复。V24 对 head 另做 1 Unit / 4 mesh / 59,300 顶点的 UV1 与 UV0 -> UV2，但运行时又因沿用 Advanced alpha 而让 hair/eyes/ears 露出金属底层；V25 再以单纹理 payload 修复 alpha coverage。body 与 head 必须分别证明坐标可达和通道语义正确。

### Piece.MaterialLut 是运行时层

- 从当前游戏的 customization/armor-set 快照枚举所有相关 kit type 和整套 Piece；按 kit type、body type、slot、layer 统计每个非零 `MaterialLut` 的全局引用。至少检查 armor `kit_type=0` 与 helmet `kit_type=1`，不得从“身体已恢复”推断头盔也已覆盖。
- 只有全局作用域/爆炸半径已证明并接受的目标 ID 才能 same-ID 覆盖。不要覆盖广泛共享的 `PatternLut`。
- 每个目标保留自己的原生 ID 和 DDS 容器合同；可提供经验证源 LUT 的像素/mip 内容，但不得把 donor 的资源 ID带入发布包。
- target/source 必须匹配完整 DDS ABI。当前已见 Armor LUT 常为 `23x8`、5 mip、`R16G16B16A16_FLOAT`，游戏更新后必须重审。
- 完整 coverage map 应绑定 armor kit/package、armor-set 快照 SHA-256、精确 Piece scope、正引用计数、原生目标 DDS 和所有权报告。
- 注入后反提取每个目标 DDS，要求与选定内容逐字节一致；旧资源 payload 必须全部保持。

完整案例证据位于 [V22 贴图预算与 splat 审计](../../SOURCE_REFERENCES.md#local-only)、[V23 DecalSheet UV2 修复审计](../../SOURCE_REFERENCES.md#local-only)、[V24 头部/头盔 splat 审计](../../SOURCE_REFERENCES.md#local-only) 和 [V25 不透明 head Decal 审计](../../SOURCE_REFERENCES.md#local-only)。V22 与 V24 的离线报告都已被运行时灰金属截图否决；V23 身体 clean color/splat 已由用户接受；V25 尚未部署或运行时复验，完整 blood/gunk/acid/weather 矩阵仍未通过。
