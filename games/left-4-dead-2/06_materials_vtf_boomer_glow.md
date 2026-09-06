# L4D2 幸存者世界模型材质：VTF、Boomer 污渍与低亮度发光

本文面向 Left 4 Dead 2 的幸存者世界模型替换 Mod，整理 `VertexLitGeneric` 世界材质、VTF/VTEX、法线贴图、Boomer 污渍和低亮度发光的可复用做法。

本文刻意区分四种结论：

- **通用规则**：可用于后续同类项目的默认工程约束。
- **已验证机制**：已经从游戏原生文件、参考 Mod、编译产物或用户提供的实机结果中得到直接证据。
- **Karin 个案参数**：只描述 Karin PT 当前构建，不能不加判断地复制到其他角色。
- **失败方案**：已经出现明确问题，或存在未解决的着色器组合风险，不应继续作为默认方案。

静态检查、HLMV 预览和游戏实测不是同一层级的证据。本文不会把未执行的游戏运行写成“已测试通过”。

## 1. 通用规则

### 1.1 世界材质优先使用原生 Boomer 共享材质补丁

需要接收 Boomer 胆汁覆盖的普通幸存者世界材质，应以 `patch` 包装原生共享材质：

```vmt
"patch"
{
    "include" "materials/models/survivors/survivors_it_shared.vmt"
    "insert"
    {
        "$basetexture" "models/survivors/example/example_color"
        "$bumpmap" "models/survivors/example/example_normal"
        "$halflambert" "1"
        "$nocull" "1"
        "$nodecal" "1"
    }
}
```

规则如下：

- 对模型 SMD/DMX 实际引用的每个可见 `VertexLitGeneric` 世界材质逐一处理，不能只处理身体或头部。
- `include` 指向游戏自带的 `materials/models/survivors/survivors_it_shared.vmt`。通常不需要在 Mod 内复制该文件。
- 不要在 `insert` 中自行添加另一个 `$detail`、`$detailblendfactor` 或同名 `IT` proxy，否则会覆盖或破坏共享胆汁层。
- `$nodecal 1` 与 Boomer 胆汁机制不是同一个开关。参考 Mod 在保留 `$nodecal 1` 时仍通过共享 `$detail`/`IT` proxy 接收胆汁。
- `EyeRefract`、纯加法特效等非标准材质不能机械套用 `VertexLitGeneric` 补丁，应按其着色器能力单独判断。
- 原生角色也可通过 `_it` 第二皮肤族切换到胆汁材质；自定义单皮肤模型直接 patch 共享材质通常更简单。若选择 `_it` 皮肤族方案，必须同时验证 QC 的 `$texturegroup`、材质顺序和运行时皮肤切换。

### 1.2 Boomer 污渍的实际机制

从 L4D2 原生 VPK 提取的 `survivors_it_shared.vmt` 核心内容是：

```vmt
VertexLitGeneric
{
    $detail "models\survivors\survivor_it.vtf"
    $detailscale 3
    $detailblendfactor ".001"
    $detailblendmode 0
    $ITAmount 0
    Proxies
    {
        IT
        {
            resultVar $ITAmount
        }
        Equals
        {
            srcVar1 $ITAmount
            resultVar $detailblendfactor
        }
    }
}
```

已验证机制：

- `IT` proxy 从游戏状态取得胆汁覆盖量。
- `Equals` 把 `$ITAmount` 写入 `$detailblendfactor`。
- `models/survivors/survivor_it.vtf` 作为 detail 层覆盖在角色材质上。
- 因此，“VMT 中能找到 `$nodecal 0`”不是 Boomer 兼容性的判据；应检查共享材质、detail 和 proxy 链是否仍在最终着色器通道中。
- 原生 Rochelle 的 `producer_body_it.vmt` 和 `producer_head_it.vmt` 都是 patch `survivors_it_shared.vmt`，其 QC 使用普通与 `_it` 两组 skin family。这是该机制的原生证据。

### 1.3 VTF/VTEX 构建

推荐把源图、VTEX 中间输入和游戏输出分开：

```text
source_png/       原始或锁定的 PNG
materialsrc/      VTEX 输入 TGA 与同名 .txt
compile_sandbox/  VTEX 输出的 materials/.../*.vtf
game/             经验证后发布的松散 addon 树
release/          最终 VPK 与 manifest
```

基本规则：

- 不直接修改已锁定的 PNG、Blend 或已验收 VTF。每次构建使用独立工作目录。
- 颜色带 Alpha 时使用能保存 Alpha 的格式，例如 DXT5；不需要 Alpha 的法线或遮罩可根据质量和体积预算使用 DXT1。
- 必须生成完整 mip 链。仅有最高分辨率的 VTF 会在远距离、缩放和斜视角下产生明显闪烁或锯齿。
- VMT 中的纹理路径从 `materials/` 之后开始，不写扩展名；路径大小写必须在打包前做不区分大小写的唯一性检查。
- VTEX 可能额外生成 `.pwl.vtf`。PC 世界材质未引用时，应记录后移除，避免把无用平台副本打进 VPK。
- 记录 VTEX 命令、退出码、stdout/stderr、工具哈希、输入哈希、输出哈希、VTF 头信息和所有后处理字节偏移。

常用 VTEX 配置示例：

```text
// color_alpha
"dxt5" "1"
"numchannels" "4"

// tangent-space normal
"normal" "1"
"invertgreen" "1"
"numchannels" "3"

// RGB mask
"numchannels" "3"
```

颜色空间规则：

- 颜色贴图按 sRGB 处理。
- 切线空间法线必须按线性数据处理，设置 normal flag，不能同时带 sRGB flag。
- 发光遮罩是否按颜色或线性遮罩采样，应结合目标 Source 分支和实际着色器验证，不能只看 PNG 的 ICC 信息。
- 本项目所用 L4D2 VTEX 没有通过 `.txt` 的 `srgb` 键可靠设置目标头标志。因此若构建器需要补写 VTF header，只允许修改已知 flags 字段，并验证变化仅发生在 header offset `20..23`；不得进行不受审计的二进制改写。

### 1.4 法线贴图

Blender/VRM 常见切线法线使用 OpenGL 约定，而 Source 1 目标材质通常需要 DirectX 方向。安全流程是：

1. 确认源法线约定，不凭文件名猜测。
2. 将未使用 UV 区域的精确黑色 `(0,0,0)` 改为中性法线 `(128,128,255)`。
3. 缩放时把 RGB 解码为向量，缩放后重新归一化，再编码回 RGB。
4. 只翻转一次绿色通道。若 VTEX 使用 `invertgreen 1`，前处理脚本就不能再次翻绿。
5. VTF 应有 normal flag、无 sRGB flag，并有完整 mip 链。
6. 解码最终 VTF，检查向量长度、绿色通道方向、UV 岛边缘和 mip 污染。

错误的黑色填充会在重采样时向 UV 岛边缘混入彩色法线；错误的双重翻绿会使凹凸方向完全反转。仅凭“VTF 编译成功”无法发现这两类问题。

若源资产没有皮肤/面部法线、粗糙度或金属度贴图，不应静默伪造并声称还原。可以使用保守的常量材质参数，但必须把缺失通道记录为限制。

### 1.5 SelfIllum 低亮度发光

需要与标准 `VertexLitGeneric` 光照和 Boomer detail 共存时，优先使用独立 SelfIllum mask：

```vmt
"$selfillum" "1"
"$selfillummask" "models/survivors/example/example_selfillum_mask"
```

规则如下：

- 使用独立 `$selfillummask`，不要默认占用 `$basetexture` Alpha；底图 Alpha 往往还承担透明或 alpha-test。
- 遮罩是强度数据：黑色不自发光，白色接近满强度。动漫角色的“夜间仍可辨认”通常只需要很低的字节值，不应默认使用纯白。
- 一个很小的常量 VTF 足以提供全材质均匀低亮度填充；常量纹理仍应包含 mip，且应解码最终 VTF 检查压缩后数值。
- 对有作者发光图的部位，可把源灰度重映射到低范围，而不是直接使用 `0..255`。这样普通区域只获得轻微填充，标记区域略强，同时保留正常受光。
- SelfIllum 只是材质在黑暗中保持可见，不会给周围地图投射动态光。
- 不要在同一个大面积角色材质上同时叠加 SelfIllum 和 EmissiveBlend，除非已经针对 L4D2 的目标渲染路径完成实机验证。

### 1.6 透明材质例外

透明不是一个可以统一处理的布尔选项：

- `$alphatest 1` 是硬切边，适合发丝卡片等边界明确的表面。使用独立 SelfIllum mask 时，不必占用底图 Alpha 作为发光遮罩。
- `$translucent 1` 是连续透明，涉及排序和不同 shader combo。SelfIllum 与 translucency 的组合在当前流程中没有可靠实机证据，默认应排除发光。
- 不要为了让透明区域发光而把 `$translucent` 静默改成 `$alphatest`；这会改变玻璃、薄纱、翅膀和渐变透明的原始外观。
- 双面显示应由模型需求决定。若 Blender 中关闭背面剔除，可在 VMT 中保留 `$nocull 1`，但需要检查透明面排序和重叠。

连续透明必须同时审计四层，缺一层都不能判定为通过：

1. 源 opacity 是否真的存在 `0 < alpha < 255` 的像素。
2. 最终 VTF 是否使用保留 alpha 的格式，并在解码后仍有连续 alpha 分布。
3. 实际透明几何的 UV 是否采样到这些像素，而不是落在全不透明区域。
4. 游戏运行时所选 shader combo 是否真正显示连续透明。

`$alphatestreference 0.5` 会把连续 alpha 二值化；源图里有灰度不能阻止低于阈值的区域被整个丢弃。反过来，VTF 有 partial-alpha 且 VMT 写了 `$translucent 1`，也只能证明 payload 和 token 存在，不能证明包含 `$bumpmap`、Phong、SelfIllum 或额外 pass 的组合在 L4D2 中正确运行。

对必须同时接收 Boomer bile 的连续透明表面，可从以下最小 profile 开始隔离：

```vmt
"patch"
{
    "include" "materials/models/survivors/survivors_it_shared.vmt"
    "insert"
    {
        "$basetexture" "models/survivors/example/example_color"
        "$halflambert" "1"
        "$nocull" "1"
        "$nodecal" "1"
        "$translucent" "1"
        "$phong" "0"
    }
}
```

该 profile 刻意不含 `$bumpmap`、其他 `$phong*`、`$selfillum*`、`$detail`、`$additive` 或 `$alphatest`。它是一个保守的排障起点，不是所有透明材质的引擎定律；透明排序和 bile 表现仍须实机确认。材质文件名中的 `Alpha`、`Cutout` 或 `Translucent` 也不决定行为，验证器必须解析 VMT 参数。

## 2. 已验证机制与证据边界

### 2.1 已由文件和静态分析确认

以下项目可以通过解析文件直接确认：

- VMT 是否能解析，是否为 patch，是否 include `survivors_it_shared.vmt`。
- VMT 是否错误重定义 `$detail`，是否残留 `$EmissiveBlend*`。
- SMD 材质名是否逐一解析到 VMT，VMT 的 VTF 引用是否存在。
- VTF magic、版本、宽高、格式、flags、帧数、mip 数和 SHA-256。
- 颜色/法线 flags 是否互斥正确，Alpha 是否保留。
- alpha histogram 是否包含期望的透明/半透明/不透明区间，相关 SMD UV 是否真的覆盖这些区间。
- `$alphatest`、`$translucent` 和 `$additive` 是否互斥；连续透明材质是否残留未经证明的 bump/Phong/SelfIllum 组合。
- SelfIllum mask 的解码最小值、最大值、均值、唯一值和空间覆盖率。
- 法线贴图中性区、向量长度和通道方向的数值检查。
- 松散 addon 与从 VPK 再提取出的 payload 是否逐文件字节一致。
- VPK 是否包含意外旧文件、未引用 VTF、大小写冲突或重复路径。

这些检查可以证明构建确定、引用闭合、元数据合理，但不能证明最终画面正确。

### 2.2 HLMV/离线预览能确认的范围

HLMV 或可靠的 Source 模型预览可以用于检查：

- 基础颜色、法线方向、Phong、cubemap 和透明切边是否大致正确。
- 是否出现紫黑棋盘、全黑材质、法线彩边、亮缝、透明区域变实心。
- 发光区域的空间位置是否与 UV/作者遮罩一致。

HLMV 不能替代完整 L4D2 运行时：它不一定复现 `IT` proxy、Boomer 状态、地图光照、手电、第三人称透明排序和所有游戏 shader combo。

### 2.3 必须由游戏实测确认的范围

最终至少需要在游戏中观察：

- 明亮地图与暗地图中的整体亮度，是否“轻微可见”而非全身发白。
- Boomer 胆汁是否连续覆盖头、身体、两组衣物、头发和附件，特别关注所有有发光的材质。
- 胆汁逐渐变化或消退时，发光层是否露出一份干净底图。
- 手电、燃烧、受伤、血迹与环境 cubemap 下是否有异常叠加。
- `$translucent` 和 `$alphatest` 表面在第一/第三人称、不同距离与视角下的排序和边缘。
- 不同材质细分之间是否出现亮度跳变或接缝。

当前流程可以产出可部署 VPK 和完整静态验证报告，但用户已明确不需要自动化游戏测试。发布时应先写成“静态验证通过，等待用户实机复测”；收到用户截图或明确反馈后，可以升级对应运行项，但必须注明证据来源和候选 VPK 身份。Karin 的 SelfIllum 修复候选后来已收到用户明确的手工实机确认，因此该候选的衣物 Boomer bile 与预期微光表现可以记录为 `user-confirmed pass`，但不能写成“自动化游戏测试通过”。

## 3. Karin PT 个案参数

以下数值只适用于 `L4d2/Karin_PT_L4D2` 当前世界材质构建。

### 3.1 材质与 VTF

- 世界模型共有 11 个 VMT，全部 patch `survivors_it_shared.vmt`。
- 10 个非 translucency 材质使用 SelfIllum；`Karin_Alpha` 是唯一不启用 SelfIllum 的透明例外。
- 8 个无作者发光图的材质使用 `karin_global_selfillum_mask.vtf`。
- `ClothA_Blue` 与 `ClothB_Blue` 使用各自作者 emission atlas 经重映射后的 VTF 作为 `$selfillummask`。
- 9 张 atlas 派生世界 VTF 均为 `2048x2048`、12 级 mip；另有一张 `64x64`、7 级 mip 的常量 mask。
- ColorAlpha VTF 使用 DXT5；当前法线与 SelfIllum RGB mask 使用 DXT1；常量 RGBA mask 使用 DXT5。
- 11 个材质保留 `$nocull 1` 和 `$nodecal 1`；后者不妨碍原生 IT detail。

### 3.2 Karin 低亮度数值

参考 CCD 材质包的 `selfillum_mask.vtf` 解码后整张 RGB 恒为 `(8,9,8)`，Alpha 为 255。Karin 因此采用：

```text
全局常量 mask：RGB (8, 9, 8)，RGBA Alpha 255，尺寸 64x64
作者发光 mask：8 + round(source * 8 / 255)
作者发光输出范围：8..16
SelfIllum tint：默认白色，不再额外乘强度
```

这意味着无标记区域保持与参考量级相近的低亮度填充，作者白色标记区域达到约两倍遮罩字节值。这里的“约三到六个百分点”只是设计量级描述；最终感知亮度仍受 Source 的颜色空间、压缩、地图曝光和材质颜色影响。Karin 当前候选已由用户实机确认表现正常；其他角色和其他遮罩数值仍必须重新实测。

### 3.3 Karin 法线与缺失通道

- Clothing A、Clothing B 和 Hair 使用源 atlas 法线。
- 缩放前把精确黑色未用区替换为 `(128,128,255)`，缩放后重新归一化。
- VTEX 通过 `invertgreen 1` 完成 OpenGL 到 Source/DirectX 绿色通道转换。
- Skin/Face 没有独立源法线；源资产也没有可无损对应的粗糙度或金属度 mask。当前流程没有伪造这些贴图。

### 3.4 Karin 当前验收状态

- VMT/VTF 结构、引用、格式、flags、mips、mask 数值、VPK payload 一致性可以静态验证。
- 先前用户实测已经证明 EmissiveBlend 衣物方案存在 Boomer 覆盖失败。
- 改为 SelfIllum 的候选包随后由用户手工实机确认正常：衣物重新接受 Boomer bile，微光效果也符合预期。
- 该确认对应 `release/Karin_PT_Rochelle_ZoeyProportions_BileGlowSelfIllum.vpk`，SHA-256 为 `A201FA053507E16C441B85EEE57E54625A706A222E3D408F5288DFB3B7C1F39B`。
- 证据类型是用户明确反馈，不是自动化游戏测试；透明材质排序和其他不属于此次修复的运行项仍按各自证据判断。

## 4. 已知失败方案

### 4.1 在大面积衣物上使用 EmissiveBlend

失败候选在 `ClothA_Blue`、`ClothB_Blue` 上使用了：

```vmt
"$EmissiveBlendEnabled" "1"
"$EmissiveBlendBaseTexture" "..._color"
"$EmissiveBlendTexture" "..._emission"
"$EmissiveBlendFlowTexture" "vgui/white"
"$EmissiveBlendStrength" "1"
```

用户实机截图显示：头部和身体能够显示 Boomer 胆汁，但两块 EmissiveBlend 衣物仍显示干净表面。由此已验证，在这个 L4D2 幸存者世界材质组合中，附加发光通道没有正确呈现原生 `$detail`/`IT` 覆盖，并可在标准胆汁层上重新叠出干净衣物。

结论必须限定为：

- 不把 EmissiveBlend 用于既是主要可见表面、又必须接收 Boomer 胆汁的大面积幸存者材质。
- EmissiveBlend 并非在所有 Source 材质上都“不可用”。独立的 glow-only 小几何、无需胆汁覆盖的纯特效材质仍可单独研究，但不能作为角色主衣物的默认实现。
- 将 strength 从 `1` 降至 `0.06` 只能改变亮度，不能修复缺失 IT detail 的通道问题。

### 4.2 其他应避免的方案

- **只写 `$selfillum 1` 而不提供独立 mask**：会回退到基底 Alpha 等隐式来源，可能与透明用途冲突，也无法稳定控制全身亮度。
- **在同一主材质同时启用 SelfIllum 与 EmissiveBlend**：可能双重发光或触发未验证 shader combo，并不能解决 EmissiveBlend 的胆汁覆盖问题。
- **给 `$translucent` 材质强行启用 SelfIllum**：当前无可靠 L4D2 实机证据，可能出现 shader combo、排序或 Alpha 语义问题。
- **为了发光把 translucency 改成 alpha-test**：会破坏原始渐变透明外观。
- **看到 VTF 有连续 Alpha 就宣布透明通过**：这只证明纹理 payload；还必须验证 UV 覆盖、VMT mode 与游戏 shader combo。
- **只把 `$alphatest` 改为 `$translucent`，继续保留全部 bump/Phong 参数**：Riptide v1.2 已证明 token 与 alpha 都正确时，运行时仍可能显示为不透明；应通过一次只改一个变量的 VMT 矩阵隔离。
- **在 patch 中加入自己的 `$detail`**：会覆盖 `survivors_it_shared.vmt` 提供的胆汁 detail。
- **把 `$nodecal 1` 当作胆汁失效原因并盲目删除**：没有触及真正的 `IT` proxy/detail 机制。
- **直接把作者 emission 的白色区域以满值 SelfIllum/strength 1 输出**：在暗图中通常过亮，且与参考角色的低亮度量级不符。
- **法线翻绿两次、把法线标记成 sRGB、或保留黑色空白区再缩图**：会造成凹凸反转、错误光照或 UV 边缘彩缝。
- **没有 mip 或只检查源 PNG**：不能证明最终 VTF 在游戏缩放时正常。
- **覆盖已有 release VPK 后再验证**：一旦同步或构建中断，将失去可追溯的上一候选。

## 5. 静态验证清单

每次材质构建至少检查：

1. 枚举模型实际引用的材质名，并与 VMT 做一一对应。
2. 所有适用世界 VMT 均为 patch，且 include 路径完全正确。
3. 不存在本地 `$detail` 覆盖；修复版本中主角色材质的 `$EmissiveBlend*` 数量为零。
4. 所有 `$basetexture`、`$bumpmap`、`$selfillummask` 路径均能解析。
5. VTF 头 magic、版本、宽高、格式、flags、mip 和 Alpha 符合角色用途。
6. 法线 VTF 有 normal flag、无 sRGB flag；颜色 VTF 的颜色空间标记符合构建约定。
7. 解码最终 VTF，而不是只检查 TGA/PNG；统计 SelfIllum mask 的数值范围并检查压缩漂移。
8. 对 alpha 材质统计最终 VTF histogram，并用实际 SMD UV 证明透明几何采样到了预期区间。
9. 验证 alpha mode 互斥；连续透明 profile 中的 bump/Phong/SelfIllum/detail 必须来自已锁定实机合同，否则拒绝。
10. 检查大小写冲突、重复路径、未引用 VTF、残留 `.pwl.vtf` 和旧候选文件。
11. 打包 VPK 后重新列表并提取到新的隔离目录，逐 payload 比较 SHA-256。
12. 报告中分别记录“静态通过”“HLMV 预览结果”“用户游戏反馈”；不存在的测试项明确写“未执行”。

## 6. BaiduSync 文件锁与可恢复构建

工作区位于 BaiduSync 同步目录时，同步客户端、索引器或杀毒扫描可能在 VTEX 刚写完 VTF 后短暂持有文件句柄。常见表现是覆盖、补写 header 或删除 `.pwl.vtf` 时出现 `PermissionError`。这不等同于材质内容错误，但必须以有边界的方式处理。

通用规则：

- 构建到新的 `work/<run-id>/` 或 compile sandbox，不在成功候选上原地覆盖。
- 修改前锁定并哈希源 Blend、PNG、VRM 和工具；构建后再次验证输入哈希未变。
- 只对明确的单文件读、写、删除操作捕获 `PermissionError`；语法错误、工具失败、路径错误等异常必须立即暴露。
- 重试必须有次数与间隔上限，并把实际重试次数写入报告。Karin 当前实现为最多 121 次、间隔 0.25 秒，即最多约 30 秒等待窗口；这个数值是个案参数，不是永久标准。
- 每次重试前重新执行目标操作，不要假定上一次部分写入已经成功。成功后重新读取 VTF header 和 SHA-256。
- 若持续锁定，停止发布并保留工作目录；不要用广域删除、强制终止同步进程或覆盖上一版 VPK 来“解锁”。
- 高频锁定时，可在非同步临时目录完成 VTEX 编译和验证，再把已验证的封闭输出复制到 BaiduSync 工作树；复制后必须再次比对哈希。
- release 使用新文件名和 manifest 指向当前候选。等新候选通过静态验证后再更新指针，旧候选作为回退证据保留。

## 7. 证据索引

Karin 项目中的主要证据文件：

- `L4d2/Karin_PT_L4D2/reports/materials/material-pipeline-boomer-selfillum-final.md`
- `L4d2/Karin_PT_L4D2/reports/materials/material-build-boomer-selfillum-final.json`
- `L4d2/Karin_PT_L4D2/reports/materials/material-output-validation-boomer-selfillum-final.json`
- `L4d2/Karin_PT_L4D2/reports/runtime/user-boomer-clothing-emissiveblend-failure.png`
- `L4d2/SharedKnowledge/evidence/karin-selfillum-user-confirmation-2026-08-08.md`
- `L4d2/Karin_PT_L4D2/src/scripts/build_l4d2_atlas_materials.py`
- `L4d2/Karin_PT_L4D2/src/scripts/validate_l4d2_material_outputs.py`

参考与原生证据：

- CCD 参考材质包：`L4d2/ref/ccd_unendingFlame/【材质】karin_ccd_uf_pd.vpk`
- Picodra 参考材质包：`L4d2/Karin_PT_L4D2/references/picodra_material_reference.vpk`
- 游戏原生共享材质：安装目录 `left4dead2/pak01_dir.vpk` 内的 `materials/models/survivors/survivors_it_shared.vmt`

这些文件证明实现来源、静态产物、已观察到的 EmissiveBlend 失败，以及 SelfIllum 修复候选随后获得的用户实机确认。当前确认覆盖衣物 Boomer 覆盖与预期微光；透明排序等未被该反馈明确涵盖的项目仍需独立证据。
