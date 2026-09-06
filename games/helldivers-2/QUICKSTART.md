# HD2 角色替换 Mod 快速开始

> 这是执行摘要，不替代各专题合同。遇到任何异常先停止合并/部署，回到对应门禁定位。

## 0. 建立项目边界

```text
Project/
  Ref/                 # 用户参考与 donor，只读
  SOP.md               # 当前状态、证据、恢复命令
  Work/
    reference_unpacked/
    Reference/
    scripts/
    tools/
    contracts/
    reports/
    audits/
    candidates/
  Output/              # 仅接受的交付物
```

立即记录：

- 源 `.blend`、参考 ZIP、donor triplet 的绝对路径、大小、SHA-256。
- 用户指定参考的精确目录、authoring Blend、编译 triplet 和原始角色身份；禁止用目录昵称或历史记忆代替 reference identity。
- Blender、AQ 插件、HD2SDK、FileDiver、`texconv`、游戏版本和 commit/hash。
- 游戏目录当前所有相关 archive patch index 与哈希，但不修改它们。
- 用户是否授权部署、是否授权启动游戏。两者默认均为否。

## 1. 解包与审计参考 Mod

1. 在隔离目录测试 ZIP 路径安全并解包。
2. 找出每个 `ARCHIVE.patch_N`、`.gpu_resources`、`.stream` 三件套。
3. 解析 manifest，建立“选项 -> archive -> FileID -> 装备槽”图。
4. 用 FileDiver/HD2SDK/AQ 只读解析 Unit、Material、TextureMap。
5. 记录每个 Unit 的 LOD、stride、UV 数、骨调色板、材质 section、draw start/count、TransformInfo、BoneInfo、inverse bind。

任何 parser error、缺少 companion 文件或旧格式不兼容都必须先解决；不能把“工具没报错”当成内容正确。

## 2. 审计源模型

至少输出：

- 对象、网格、顶点、三角形、退化面、shape key、材质槽。
- 骨架、实际加权骨、每顶点 influence 数、权重和误差、未加权点、错侧骨。
- UV 层名称、loop 数、范围、重复/全零情况、贴图来源与色彩空间。
- object/world/armature 变换、父子关系、Armature Modifier。
- neutral/front/side/three-quarter 渲染和全局 bounds。

Morph 未被目标 Unit 明确支持时，先冻结源文件保存中的全部非零 `对象 -> key -> value`，预计算 current mix，再用 shape-key-only `apply_mix` 烘到 Basis。烘焙必须早于法线、分件和 bind retarget；不要应用带活动 Armature Modifier 的完整 evaluated mesh，也不要把 shape key 原样带入希望游戏自动处理。

## 3. 先证明 donor，再做目标模型

优先选择一个“同角色或相近骨架、已在当前游戏运行”的 donor Mod，并同时取得其配套源 `.blend`。需要证明：

- authoring 网格与已编译 donor RawMesh 对应。
- authoring 的局部 `0_N` palette 与 donor BoneInfo 对应。
- donor mesh-local 坐标、TransformInfo 和 inverse bind 可以闭合。
- donor 在外部运行时驱动下的 rest 语义，而不只是 Blender 内部自洽。
- 源骨段纵轴与 donor/HD2 `TransformInfo` 链轴的有符号对应；不要假定 Blender local `+Y` 与目标 local `+X/+Y` 相同。

没有这层证明时，不要按 HD2 原生人形骨长逐段拉伸角色，也不要从 edit-bone roll 猜人体关节方向。

## 4. 建立 authoring 候选

推荐冻结合同：

- 保留角色原始比例；最多使用一个已证明的全局刚性/等比变换和刚性换姿。
- object transform 应为 identity，顶点已在 donor mesh-local 坐标。
- `LegacyWeightNames=True`，每个导出对象使用 donor Unit 的局部 `0_N` bone palette。
- 不依赖 Armature Modifier 参与 AQ 导出。
- 每顶点最多 4 influences，权重归一，无未绑定点。
- LOD/材质槽数量不超过目标合同。
- UV0/UV1/UV2 不只“存在”，还要分别满足颜色、gore/size、decal 的语义。
- Advanced -> Armor LUT 时，从目标 shader 证明作者 DecalSheet 实际读取的 UV component；连续 UV1 不代表 UV2 的颜色 sampler 可达。

每次只改变一个声明的边界：几何、rest、权重、材质或 draw 合同。用候选差分证明非目标内容逐位不变。

## 5. 姿态与局部门禁

标准姿态至少包含：neutral、arm-up、crouch、asymmetric locomotion、左右手摸头。每次权重从骨 A 迁到骨 B，还要添加让 A/B 相对运动最大的专项姿势。

检查：

- p01/p99 和 absolute edge-length ratio。
- seam 对应点距离、bounds、中心漂移、错侧穿越。
- 连通片整体赢家骨与相邻顶点权重连续性。
- 手指 30 根语义骨是否全部运动、关节过渡是否平滑。
- 头盔/身体接口高度与遮盖量。
- 肩部 source/target 语义骨数量、signed chain-axis、左右完整镜像、world fore/aft、段端点闭合、Torso/Arm 权威 seam 集合与腋下装饰走向。Ref 若证明是闭环才强制闭环；开放/多组件衣物必须声明拓扑，并验证两侧点/边覆盖、位置、完整权重行和固定对应的差分姿态。
- 肩、腰、髋腿逐 seam 报告任何 post edit 前的自然 final-lineage 权重误差。自然肩缝已一致时禁止强制 shared-bone override 或固定两圈插值；差分姿态显式列出 moving/excluded bones，并同时测 seam gap 与肢体内部 edge ratio。

New_SR24 使用过的 `176/176`、`0.05..12x` 等是已验证起点，不是所有模型的永久阈值。先用源模型和 donor 建立分布，再锁定本项目门槛。

## 6. 编译与序列化验证

whole-unit donor swap 的正确顺序：

1. 用 `Z_ObjectID` 加载完整 donor entry。
2. 在其既有 TransformInfo/BoneInfo/MeshInfo/material-section 合同内替换 RawMesh。
3. 保存完整 donor entry。
4. 最后把输出 FileID 改成目标 `Z_SwapID_N`。

编译后重新解析最终 Unit，不能只相信 authoring `.blend` 或编译日志。验证可见 Unit、隐藏/suppression Unit、LOD、palette、inverse bind、draw ranges、材质 ID 和资源区间。隐藏原生装备优先使用经证明的微型可渲染几何或 zero-draw 合同；不要把透明/玻璃材质当作不可见性的证据。

若多个目标应得到完全相同的角色与绑定，而 target-native Unit 的 `TransformInfo/BoneInfo` 不同，应按角色选一个已证明的完整 carrier：每角色编译一次，保存/回读后仅改 FileID 克隆完整 Unit。要求同角色目标的 Toc/GPU/Stream payload 唯一哈希数为 1，并锁定 carrier 的 header、TransformInfo、BoneInfo/MeshInfo、inverse bind、culling 与核心 bone-bind。每级 LOD 使用 owner 自己的实际 RawMesh 索引。不要把同一 RawMesh 分别注入多个未经证明兼容的 target-native bind。

## 7. 材质与资源 ID

- BaseColor 使用正确 sRGB 编码；NAR/control/normal 依具体合同使用线性格式。
- 贴图输入 provenance 来自源材质的实际 node/binding、UV ROI 与文件哈希，不来自邻近文件名；磁盘上存在但源材质未绑定的 normal/control 不能自动纳入 atlas。
- 稀疏 alpha 的 BC7 用 `texconv -sepalpha` 并做解码后像素/ROI 对比。
- 先按项目严格总预算累加包内每个不同私有 TextureMap FileID 的 base-level `width * height`，再报告 BaseColor、Normal/NAR、Data/Control 等语义小计；重复 primary/secondary 纹理先合并引用，再判断是否满足预算。
- 对逻辑不透明 BC7，解码后重新检查 alpha；源图 alpha=255 不足以证明 DDS 仍全不透明。
- 材质名带 Transparent 不代表必须 AlphaClip；读取实际 alpha 分布。
- 审计 emission 与 atlas alpha 的乘积，避免全身青白过曝。
- 除 stock parent 外，本地 child Material/TextureMap 必须使用确定性私有 ID。
- 同时查 full 64-bit 和 high32/ShortID 碰撞，并验证引用闭包。
- 旧私有 ID 只有在“精确识别旧三件套、同一 lineage 原位替换、旧新版禁止共存”时才可复用；普通升级、并存版本或 live 哈希变化必须使用新 namespace。
- 需要血液/gunk/weather 时，分别证明 Unit UV ABI、完整 Armor LUT child/root ABI、IdMasksArray/static LUT，以及当前 armor-set 中所有 `Piece.MaterialLut` 的所有权与覆盖范围。
- Armor LUT clean view 若统一变灰/银/金属，应停止调 LUT，先检查 DecalSheet 坐标通道和值域；资源绑定和 SDK 往返不能证明 sampler branch 已执行。

## 8. 串行合并与确定性打包

AQ/Blender 的 archive merge、material rewrite 和 integration audit 必须串行。必要时为每个进程设置独立 `TEMP/TMP`；不要同时跑两个 AQ 写/往返任务。

最终包要求：

- 单一 triplet；ZIP 恰好三个成员。
- 固定成员顺序、时间戳、权限和压缩方式。
- ZIP CRC、成员大小、成员 SHA-256 与源 triplet 一致。
- 在隔离新路径做第二次构建，ZIP 逐字节一致。
- 发布报告绑定全部上游接受报告与哈希。

## 9. 部署与运行时

只有明确授权后，先冻结互斥的部署模式：

- **新槽安装**：确认 `helldivers2.exe` 未运行；选择高于当前最大值且完全未占用的 patch index；绝不覆盖。
- **精确旧版替换**：只用于用户明确要求替换的同一 Mod lineage。旧三件套必须逐份匹配被拒绝/被取代版本的 SHA-256；碰撞扫描只排除这一份精确旧 triplet；旧版和新版不得以任何 index 共存。任一 live 哈希变化即停止。

随后将精确三件套作为一个发布单元部署，逐份复核 SHA-256，并记录部署前后身份、模式和精确回滚路径。优先让 Mod Manager 禁用/卸载旧版后安装替换包；不要把 replacement ZIP 当作任意空槽包。

运行时矩阵至少覆盖军械库、任务内、Slim/Stocky、近远 LOD、主要动画、原版及自定义可组合装备、正面/侧面/背面，以及项目声明支持的污渍/血液/gunk/acid 状态。

截图必须绑定已部署 triplet 的 SHA-256。出现新问题后，先记录截图哈希、版本和姿势，再回到最小责任域修复；不要同时重写全身。
