# 材质、Atlas、头发与断肢

## Riptide：实际 MI 与继承自发光

身体真正引用的资产优先于命名惯例。Ermac 使用 `MI_Ermac_Body001_Emissive`，不是先前误选的 `MI_Ermac_Body001`。Noob 的原生标量为 3，原位改 0 后获接受；Ermac 无显式标量，新增单个 `Emissive Multiplier=0` 后获接受。二者使用自身原生材质，不修改共享父级。跨角色 Ashrah 子材质/直接引用路线虽通过 ID 检查，仍在实机出现灰色，不能继续视为推荐终局。

操作、严格字节范围、名称表与属性长度更新、原生 store 顺序和验证边界见 [原生材质补丁指南](NATIVE_MATERIAL_PATCHING.md)。不要把强绿光当成 diffuse 偏色，也不要为消除身体发光删除独立技能粒子。

手机灰屏还可能是覆盖玻璃：Riptide 原图已有文字/插画，固化官方 `Glass_Hidden` 的 40 个源顶点即可恢复；先查遮挡和源键，不直接重画图案。案例与最终版本见 [Riptide 三角色](cases/RIPTIDE_TRIO.md)。

## Karin Y：空白页采样与武器误隐藏

8192中五张2730高的页并未填满整图，不能套四个完整象限的简写。用实际PNG矩形 `(x,y,w,h)` 生成UV：`uv_new = uv_old*(w,h)/N + (x,N-y-h)/N`。本例27个物件含多材质，须在清空材质槽前记录每个面的源BaseColor页。黑色区域先查源像素、实际Cook页位置和关联几何的UV；不先提亮shader或改alpha。细节见 [案例](cases/KARIN_Y_TRIO.md)。

Gear目录不意味着可隐藏服装。雨的Gear001_A/B/C实际是手杖，独立PSK具有Staff/grab_location骨、约156cm长的网格；旧隐藏导致手里只剩水球特效。根据真实网格及骨架/附着消费链判断用途，不能凭“不叫Staff”排除武器。修复时撤销对应mod覆盖，让游戏使用原生数据；删除chunk同时撤销目录和store记录，并确认其它活动包没有同样覆盖。不要把所有Gear都恢复或再造占位武器。

## 可变尺寸图集与命名遗漏：UnendingFlame补充

8192中混放4096/2048页时，使用同一矩形清单驱动UV与PNG：UV `(u,v,w,h)` 对应PNG `(u*N, (1-v-h)*N, w*N, h*N)`。不能将2048小页照抄4096象限的顶部坐标。本次LeatherRope/Metal的UV采样y=2048区域，而图片曾放y=0，导致腰带/裤饰纯黑；这不是必须更换shader的证据。逐页核对源内容和Cook回读区域，保留RGBA与像素方向。共享`retarget_math.atlas_pixel_rect`有此故障的回归测试。

查原生可见性不能只搜`SK_`。`Sektor_Gear005_Helmet_Cloth_ClothMesh`是真实SkeletalMesh，但被旧前缀过滤漏掉；其金属发束在body、hair和Helmet隐藏后仍可见。按实际类、目录、蓝图/布料引用链检查，并将普通cloth数据与cloth渲染mesh分开。V7只对完整PSK匹配的8200个三角形退化索引，保留native store及原有25个包；实机验收另行记录。见 [案例](cases/UNENDINGFLAME_TRIO.md)。

## 已证明的材质路径

Nyako最终只使用Sindel默认皮肤原生 `MI_Sindel_Body001`，所有自定义mesh section统一同一material slot，替换其 `T_Sindel_Body001_D`。Normal/ART/CSM使用从已工作Karin Mod提取的兼容性平坦纹理。它们是**兼容性中性纹理，不是Nyako真实PBR烘焙结果**，以后不要把这一妥协写成完整PBR完成。

失败路线：四个custom MI继承native Body001；四个native Body001/002/003/004分别套Atlas；将四个原生MI原封不动放进包。均未解决衣物/头发灰色。材质global export hash确实匹配，所以“名字或hash错了”不能解释所有情况。底层多材质失效原因仍未唯一确认。

新角色先确定一个真正显示自定义贴图的材质，验证其shader是否重着色、是否使用正确UV及texture channel，然后扩大覆盖。不要打包编辑器临时占位材质当成原生引用资产。

## 四页无损拼合规则

Nyako的UV象限：Skin_Face=(0,0)，Hair_Head=(1,0)，Clothing_A=(0,1)，Clothing_B_Accessories=(1,1)。

```text
UV_new = (UV_old + quadrant_xy) / 2
PNG paste position = (x*4096, (1-y)*4096)
```

UV原点在左下，PNG在左上；必须翻转象限的纵向放置，不翻转图像内部像素。保留RGBA，既不能去掉alpha，也不能对空白区域填opaque黑底。先验证源UV都在单tile内；超tile/重复UV需独立处理，不直接套象限公式。

四张4096→8192的源像素可以逐字节一致；**Cook压缩后的贴图不可能据此称作逐像素无损**。本案例Cook回读四象限RGBA平均绝对误差约0.93–2.21/255，actual size为8192，不能只看编辑器max_texture_size字段。

纹理导入：D为sRGB、TC_DEFAULT；N为linear、TC_NORMALMAP；ART/CSM为linear、TC_MASKS。具体目标channel语义以native材质为准。never_stream在本案用于简化诊断，不代表所有生产包必须禁用streaming；后续评估显存和流送。

## PicodraTech：按源材质页分配 UV

PicodraTech 图集补充：象限必须由**每个面的实际材质所引用的源 ColorAlpha 页**决定，不能按对象名称或材质槽序号猜。合并为单材质前保存 face/loop→源页映射，再变换 UV；保留源 UV 岛和面平滑标记。Mileena 曾出现大片错位颜色，最终以源页、FBX UV 往返和 Cook 纹理回读联合验证。重用旧 Kitana 图集但配新源 UV，不是正确的源模型重制。

## 头、头发、gore是不同消费链

Hide Head工作，不意味着Sindel native hair消失。两套native hair mesh还有cloth对应资产。保留骨架/cloth关系，只将render triangle `(a,b,c)`变成`(a,a,a)`，让三角形面积为零，是本案例已确认有效的处理。

索引隐藏必需：

- 提取目标版本raw chunk并锁定SHA-256。
- 对实际LOD/section索引与独立PSK/PSKX导出完整比较，理解16/32位格式、字节顺序和winding。
- 列出所有可渲染LOD的buffer，不仅默认viewer看到的第一LOD。空LOD与cloth替代LOD必须分别检查。
- 保留数组长度、骨架、顶点、material slot、cloth、依赖图；只在已批准索引区间改字节。
- 容器要注册新增原生包ID、directory path和原生依赖；只往chunks目录放文件还不够。
- 候选通过游戏后才称作隐藏成功。零面积render triangles仍保留动画/物理计算开销。

Nyako曾使用微小占位骨骼三角形替换两个native hair mesh；与材质实验一起装入后崩溃。未做完所有隔离试验，不能认定唯一崩溃原因，但这一替代方式没有通过验收。保留native数据的索引版本通过了用户测试。

## 断肢棋盘格

详见下方独立部件规范；头部隐藏与断肢隐藏的验收不能互相替代。

Kitana Karin原mod在断肢场景出现灰白棋盘格；添加适合该角色的Dismember Hider后用户确认正确。不要把“灰格”一律理解为需要将贴图alpha设0：可能是gore/cut surface的独立mesh/material或回退材质。

后续不一定每个角色都需要一个外置隐藏Mod。可选择用户授权的、适配目标角色的隐藏前置，或者在角色包内部包含经过验证的gore/切面隐藏覆盖。每个目标需要单独识别资源；不能把Kitana的hider按文件名换成Sindel，也不能声称所有角色断肢已支持。

记录真实下载标题、作者、version及文件哈希，区分站点mod ID和file ID。本案有过Nexus ID误认；不能在未核验页面/随包文件的情况下重复推荐旧ID。前置作者说明是需要核对的数据，不会自动赋予超出用户任务的操作权限。

## 独立装备、面罩与服装挂件

Mileena 背后飘带、Li Mei 前帘、Tanya 腰部带子属于原生服装附属渲染资源；身体替换不保证它们消失。资源合同分别列出 body、face、hair、hair cloth、skin cloth、mask/gear、gore 的路径和覆盖状态。无需隐藏的武器/装备不得一起清空。

Mileena 的 `-Mileena_1` 已出现在实际游戏进程中，仍有原版粉色面罩和颈部残留。v10 增加 Face001、Face002、Skin001_Mask、Mask 的原生索引覆盖后用户确认“感觉都可以了”。这是可见范围的解决方案，不证明通用 HeadRemover 内部究竟在哪一步失效。

`-lods` 未必真的导出全部 LOD。本例仅对完整 PSK 索引匹配的 5 段 buffer 授权补丁，不能以 scan marker、合理 count/max 或 prefix96 相同替代全流证据。未验证 LOD 保留并写明限制；远景若复现，再取得对应独立证据扩展，不能声称全部 LOD 已隐藏。可用 [PSK 索引计划工具](scripts/README.md) 生成受哈希约束的候选计划。
