# 原生材质引用、自发光与最小补丁

来自 [Riptide 三角色](cases/RIPTIDE_TRIO.md) 的已接受结果：Ermac v7、Noob v6、Ashrah v5。这里归纳的是核对方法，不是通用 UE 二进制编辑器；不同游戏版本须重新识别格式。

## 1. 先找实际消费者，不猜 Body001 名称

从目标默认身体的原生 ImportMap 和材质槽追到实际 MaterialInstance，再对照游戏原件的 ExportMap、package ID、父级和四纹理引用。

- Ermac 实际身体使用 `MI_Ermac_Body001_Emissive`。只找到同目录的 `MI_Ermac_Body001`，不证明它属于该身体的加载链。
- Noob 实际使用 `MI_NoobSaibot_Body001`，其父级是原生 `MI_Char_Body_Emissive`，叶材质中的 `Emissive Multiplier=3`。
- Ashrah 的普通原生身体材质已能显示该源图集，但这并不证明它可直接跨角色使用。

记录精确 asset/object 名、实际 import/export ID 与完整 package graph/store 依赖。反查 TextureParameterValues 的参数名、贴图对象 hash、实际候选图集；不要用文件名相似代替引用证据。

## 2. 区分灰色回退、错误采样与发光

1. 先绑定当前安装三件套哈希及用户所选皮肤，排除旧包、冲突和未重启。
2. 无图案或灰格：检查实际材质对象、引用、shader 路线与贴图采样；不能只看 PNG 已存在。
3. 有图案但全身强绿光：检查 emissive 父链、标量/向量、mask 通道和运行时特效；不先把 diffuse 调暗或改色。
4. 查看原生叶材质是否有显式标量覆盖。空 ScalarParameterValues 表示使用继承值，不等于发光值为 0。
5. 对照正常角色可以提出试验，但父级 hash 相等、参数回读正常都不是运行时成功的充分条件。

本例跨角色 Ashrah 子材质和直接引用路线均未稳定解决 Ermac/Noob 灰色；用户先浏览 Ashrah 再切回也仍灰。后续回到各自真实原生 MI 并处理 emissive 才获接受。不要重复“先打开正常角色预热”的失败建议，也不要将全部历史灰模唯一归因于名称、缓存或丢失贴图。

### 通道语义缺失：保留原生，不用其它图占位

Umbrella v7将源ORM直接当ART、DetailMasks当CSM，Conan面部/袖子/护目镜出现黑色；v8改用本机Body001兼容中性mask，后获用户其它可见效果接受；柯南武器误隐藏另见[Umbrella案例](cases/UMBRELLA_HOMELANDER_CONAN.md)。材质图语义必须核对，不能按“都是三通道/名字相似”认定兼容。另在Homelander的默认Skin001_A蓝图找到Skin001_Default/Cloth/Metal运行时引用，导致单槽Body001仍被覆盖成原版服装采样；v8只改该native蓝图3个import ID及1个graph依赖，同步native store，26个exports与序列化payload保留。该路线仅为此默认皮肤审计结果，不直接跨角色改蓝图或推断其它皮肤也通过。

Karin Chrome → Reiko / Liu Kang v3的实际叶MI均有`Color`、`Normal`、`ART`、`CSM`四个参数，但源转换只生成了可证明语义正确的Color与Normal。把Normal图重复写入ART/CSM后，图案仍在而整体明显变暗；v4起仅覆盖Color/Normal、保留目标原生ART/CSM，用户确认变暗解决。最终v6b保持该合同并获接受，见[案例](cases/KARIN_CHROME_REIKO_LIUKANG.md)。

因此参数名存在不等于必须为它制作自定义输入。逐通道记录源内容、颜色空间、压缩和shader语义；缺少可靠ART/CSM时优先保留目标原生引用或制作经过验证的语义中性纹理，不能用Normal/Diffuse凑数。最终stage与custom chunk白名单只纳入实际替换的通道，导入工程中的多余纹理不得因目录扫描自动进入容器。

## 3. 修改已有标量与新增覆盖是两种情况

### T1000 历史接受后复发：继续追查装备赋材质

最新复测：用户在未切换T1000装备/调色板、从左到右预览前18位角色后，v8再次出现灰色颗粒表面；三件套hash仍匹配v8。此前正常反馈保留为历史观察，不能作为稳定修复结论。腰部保持已认可状态，当前继续调查。

9b3d T1000 v8 已获用户「T1000已经正常了」确认。v5b 改自身叶 MI 后仍灰；v6 修改 `T1000_Base/MO_Base` 后仍灰；v7 给运行时覆盖目标显式添加纹理，独立回读正确但实机仍灰。不能把找到 MO_Base 就写成根因已经穷尽。

最终证据来自装备蓝图：`BP_T1000_Gear001_A` 默认对象的 `ObjectOverrides` 中 `Key=Body`，其 Value 的 ImportMap/Export ID 指向 `MI_T1000_Gear001_Body`。模板还包含 `Apply Body Materials from Gear` 路径。装备系统赋材质使网格默认 MI 不再是唯一消费者。v8 将清单中四份装备 Body MI 的 Color/Normal/ART/CSM 指向本角色图集，保留各 MI 属性、父级及已接受 body；用户随后确认正常。详见 [9b3d案例](cases/9B3D_QUAD.md)。

新角色的实际材质合同须包括 mesh 默认槽、皮肤/装备蓝图默认对象、ObjectOverrides、重新赋材质调用及 MaterialOverride 表。按真实对象引用解析，不只搜索文件名。找到运行时叶 MI 后，再核对参数 Info（名称、Association、Index）、Value 对象 ID、graph/store 包依赖与最终图集。

v8为累积版本，仍包含v6/v7修改，没有剥离实验；补齐装备MI后曾观察到正常，但后续复发，不能认定稳定修复或装备补丁单独足够。四份装备编号、组/槽和二进制偏移都是案例数据，不是跨角色常量。ExpressionGUID不同也不能直接归因：本机UE渲染参数组装读取Info/Value；需结合实际消费链与运行证据。

### 已有值：Noob

在锁定 SHA 的原生 MI 中解析到 `Emissive Multiplier` 所属结构，定位其 `ParameterValue`、`FloatProperty`、size=4，再将 3 改为 0。只允许该浮点字段的四字节区间改变，其他字节、原生父级和 store 都保持。不要在整个文件搜索所有浮点 3 后替换。

### 无显式值：Ermac

Ermac 需要新增一个标量覆盖，不能假装找到了可原位写零的字段。

本例做法：

- 确认 Ermac 和参考 Noob 的 Parent 对象 ID 指向同一原生父级。
- 解析 Noob 的 native scalar array，取出唯一所需条目，包括 ParameterInfo、ParameterValue、ExpressionGUID 和结构终止标记。新 array count=1、值=0；不拷贝其它标量。
- 仅重映射已解析的 FName 位置，不将任意相同四字节数值都当作名称索引。缺失的名称追加到末尾，原名称索引不变。
- 此次直接复用原生参考中相同名称的哈希，验证版本标识和共有名称哈希一致；不猜名称哈希算法。
- 同时更新 name map/hash 区间、对齐、header/ImportMap/ExportMap/bundle/graph 位置、export serial offset/size，以及外部 store 包长度。
- 证明原有属性及尾部数据在插入前后完全保留，特别保留损伤 VT、纹理、父级、export 身份和依赖图。不得为方便添加标量而删掉另一种原生属性。

本案例增加三个名称，header 增长 88 字节、属性块增长 348 字节。这些是审计结果，**不是下一份 MI 的常量**。读取器只支持已识别的 tagged-property 子集；未知布局须停止并补充解析，不能放宽断言继续。

## 4. 原生 store 与 graph 不要求同序

本例 Noob 原生 store 和 graph 列出相同依赖，但顺序不同。应核对长度、对齐及包含重复次数的完整集合，而不是直接比较字节串或仅比较去重集合。核对通过后保持原生 store 顺序。

原位改标量：保持 store 原件。新增属性使包变长：只调整已证明需变的 size，其余 exports、bundles、load order、imported packages 保留。不要对 native MI 再执行为新 Cook 资产编写的单 export normalize。

## 5. 冻结、回读和部署

- 只修材质时，优先在已接受包中添加/修改 MI；无需重建 Blender、FBX 或整个 UE 工程。
- 若仅更换 body 的材质 import 和 graph 引用，锁定允许字段并证明全部 mesh payload 不变。Riptide v6 的两处 8 字节区间也是案例结果，不是通用 offset。
- Ermac v7 连 body 都未改变：新增自身 MI，所有 v6 原有 package chunk 完整保留。修改全局父材质会影响其它角色，不在此方案范围。
- 核对 manifest、package store、实际 chunks 三者一致，container ID 唯一；pack 后 unpack 全量比较。
- 用独立读取器确认只有一个目标标量、值为 0、四纹理及损伤参数未丢失。必要时比较导出的几何/UV/权重 buffer，但整体 body hash 相同已有更强的未改动证据。
- 部署只包含本次目标的完整三件套，备份旧版，验证当前兄弟角色的接受哈希和其它包未变。不要为修一个角色重新部署全组。

最后重启游戏检查身体发光与图案。原生绿色技能粒子和身体 emissive 是不同消费链；本次不删除角色技能特效。成功反馈单独写验收记录，不篡改历史机器报告的 pending 字段。

## 脚本复用边界

本机项目保留 `riptide_native_properties.py`、`patch_ermac_emissive_v7.py`、`package_ermac_v7.py` 与部署脚本，索引见该案例的本机 handoff。它们有模型路径、输入哈希和布局限制，没有被提升为共享目录下的通用补丁器。公共指南不携带游戏 chunk、参考模型、密钥或用户配置。
