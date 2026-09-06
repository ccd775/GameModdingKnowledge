# New_SR24 案例：从错误骨架拟合到 V25 不透明头部 Decal 闭包

> 项目：`HD2/New_SR24`
>
> 目标：以 Karin C4 完整替换 SR-24 Ramune 覆盖的角色资源，保留角色比例，并与已运行 O44 donor 合同兼容。
>
> 权威状态：以 [`../../New_SR24/SOP.md`](../../../SOURCE_REFERENCES.md#local-only) 为准。本案例只提炼决策，不替代完整哈希和恢复命令。

## 最终离线状态

- V22 沿用冻结 authoring 与 22 个 Unit；不修改位置、权重、骨架或 draw，只缩减/合并贴图并迁移身体材质到私有 hybrid Armor LUT 路线。
- V22 保留 face 的 Advanced emission-zero child；身体 10 个 Unit 的目标 Material 顶点获得连续 UV1，9 个当前 SR24 kit 独占的 `Piece.MaterialLut` ID 使用合同保持的同 ID 覆盖。
- V22 虽通过 39/39 SDK 分层验证和整档逐字节 roundtrip，用户运行时截图仍显示全部 body 为深灰反光金属；原因是 Armor LUT DecalSheet 读取 UV2，而 V22 只写入 UV1，body UV2 仍为常量 `(0,1)`。
- V23 仅对 10 个 body Unit / 40 mesh / 552,428 个目标顶点执行 UV0 -> UV2 字节复制，保留斜投影 UV1 与全部模型、材质、纹理和 LUT payload；用户随后确认身体 clean color 与 splat 已恢复。
- 同一截图反馈指出整个头部/头盔仍无 splat。根因是 head 仍使用 Advanced child、head UV1/UV2 恒定，并且 Helmet 属于独立 `kit_type=1`，不在只枚举 armor `kit_type=0` 得到的九个 body runtime LUT 中。
- V24 将 head 迁移到 hybrid 13/40、写入 1 Unit / 4 mesh / 59,300 顶点的连续 UV1 和 UV0 -> UV2，并对 Helmet `Piece.MaterialLut` `0xf81d50ef0ea7d046` 做 same-ID 注入；但它错误沿用了 Advanced atlas alpha，用户截图显示 hair/eyes/ears 大面积变成深灰反光金属，因此 V24 已被运行时否决。
- V25 保留 V24 的 RGB、Material、UV、10 个 runtime LUT、模型与预算，只把 2048² head Decal 输入 alpha 固定为 255；BC7 回读 4,194,304 个像素全部为 255，RGB PSNR 60.3167 dB。
- 当前包为 `Karin_C4_SR24_v25_OpaqueHeadDecalFix_patch427.zip`，约 77.6 MB；V23 身体效果已由用户截图接受，V24 已被截图拒绝，V25 尚未部署或运行时复验，blood/gunk/acid/weather 的完整任务矩阵仍未测试。

上述数字和 patch index 全是 `case-specific`。

## V25 证据快照

| 产物/门禁 | 冻结结果 |
| --- | --- |
| Authoring Blend | `BC4433D83DDE8340B9CEE46A3CE67EEDFF61650318433D95051DFFC53A4476D1` |
| 标准全身姿态 | `176/176` |
| 手指 edge ratio p99 | 左/右 `1.438009 / 1.277000`；30 根 finger bones 均运动 |
| 贴图预算 | BaseColor `13,631,488`；Normal `16,777,216`；Data `4,194,304`；runtime LUT `1,840`，各自均不超过 `16,777,216` |
| 身体 UV1 | 10 Unit / 40 mesh / 552,428 顶点 / 604,864 三角形；exact/near UV 退化均为 0 |
| 身体 UV2 | V22 全部为 `(0,1)`；V23 的 552,428 个目标 UV2 与源 UV0 逐字节一致，UV0/UV1 保持 |
| 头部 UV1/UV2 | 1 Unit / 4 mesh / 59,300 顶点；UV1 exact/near 退化均为 0，UV2 与 UV0 逐字节一致 |
| Armor LUT | 三个可见 child 均为 hybrid `13/40`；9 个 body LUT + 1 个独立 Helmet LUT；当前快照中各目标的爆炸半径已证明 |
| 最终集成 | 40/40 SDK 验证；22 Unit + 4 Material + 14 Texture；整档 roundtrip 逐字节一致 |
| Triplet patch | 212,152 bytes；`66B3C6126D476E6B8F161F086B7F5B9ED73B32AD1029CF612583E05E85476E30` |
| Head Decal | 2048² BC7 sRGB；alpha 全 255；RGB PSNR `60.31672653947439 dB` |
| V24 -> V25 差分 | 只改 GPU offset `73,132,288` / size `4,194,304`；区间外 `73,152,072` bytes 全同 |
| Triplet GPU | 77,346,376 bytes；`FA2295017CFE1D2DAF508951AAF5FD4C7822864DC85742A06C8C3F6FE8C16F89` |
| Triplet stream | 0 bytes；`E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855` |
| ZIP | 77,559,036 bytes；`AACCBF1D87C0CB9FD1340E56FA76AADA52D637AA2BEE1E925DFAF3CD8F44E70D` |
| 运行时状态 | V22/V24 已截图拒绝；V23 body clean color/splat 已由用户接受；V25 未部署，head/helmet 待截图 |

这些指标只证明冻结 V25 候选满足本项目的离线合同。V22 已经证明 LUT、UV1 与 SDK 闭包完整仍可能遗漏作者颜色 sampler；V23 又证明 body 成功不等于 Helmet Piece 成功；V24 进一步证明 RGB、UV、LUT 和 SDK 全绿仍可能因 alpha 通道语义错配而在运行时露出金属底层。V25 不能在用户截图前提升为 head/helmet `runtime_validated`。

## 版本演进与每次学到的东西

| 阶段 | 结果 | 根因/结论 |
| --- | --- | --- |
| V1-V3 | 全身与三视图拉伸 | edit-bone roll 不是人体骨段方向；armature-space 写成 mesh-local 会二次偏移；AQ swap 转移 whole donor entry，不保留 target bind |
| V4c | 静态形体较好，运行时颜色/刘海/鞋错误 | 几何、材质和 draw 是独立合同；离线姿态通过不能覆盖材质错误 |
| V4d | 修平鞋底，修 sRGB/emission，刘海材料分离 | Toe 几何 override 与已合并 Foot 权重重复校正；emission × atlas alpha 导致青白；BC7 需正确 sRGB |
| V4e | 手指不扭但完全不动；贴图串味 | 把 finger 全并到 hand 是功能性失败；复用 donor child/texture ID 会跨 Mod 冲突 |
| V5 | 恢复 O44 手指并做 neck bridge；Head 黑白 | bridge 槽归属和 body interface 仍错；稀疏 alpha 的 BC7 联合压缩污染 RGB，应 `-sepalpha` |
| V6 | 恢复源形体、刘海强制 opaque | rest/inverse-bind 中立自洽可恢复静态几何，但仍不证明游戏驱动；材质名“透明”不等于真实需要裁切 |
| V7-V8 | 权重/头颈局部修复，运行时仍拉伸或长脖 | 不可通过拉长脖子补偿整个身体 anchor；全表面迁移损伤离散组件 |
| V9-V10 | 全局 rest/similarity 离线全绿，运行时全身崩坏 | neutral identity、11/11 Unit、52/52 integration 都无法替代 donor 外部驱动合同 |
| V11-V15 | 一系列 external-control 探针被拒绝 | 先建立 donor 源到 compiled Unit 的外部 residual gate；DQS/LBS 或全模型 donor 权重没有捷径 |
| V16 | 51-origin role-consistent 中间金基线 | 消除全身性错误后，只保留局部组件语义问题；不要再全身平滑 |
| V17 | 仅改 144 行权重，176/176 通过；运行时腹部整圈断裂 | 通用姿势未让 chest/spine2 足够相对运动；一个小权重表可以控制大型环状壳体 |
| V18 | 精确回滚 V17，仍有黑带 | 黑带不是缺面/UV；深色内衬在分层时暴露，且 Torso/Hip 仍有 spine 语义不一致 |
| V19 | spine1 bridge + 排除内衬；运行时断层消失 | 接口要按拓扑和共同骨语义构造；局部桥接优于新填充壳/全局平滑 |
| V22 | 贴图预算 + body hybrid Armor LUT + 9 个 runtime LUT；运行时全身深灰金属 | 静态闭包只验证了 UV1 tiler，遗漏 DecalSheet 使用的 UV2；资源已绑定不代表 shader sampler branch 可达 |
| V23 | body-only UV0 -> UV2；离线全部通过 | 作者 Advanced atlas 必须按目标 Armor LUT shader 的 DecalSheet UV ABI 迁移；UV1 保持专用 tiler 坐标 |
| V24 | 补齐 head hybrid/UV 与第十个 Helmet runtime LUT；运行时 hair/eyes/ears 变深灰金属 | customization coverage 必须枚举所有 kit type；Advanced Color/Emission alpha 不能直接当 Armor LUT Decal coverage |
| V25 | 只替换 head Decal BC7 payload，alpha 回读全 255；离线闭包通过 | 跨 shader 迁移必须分别证明 RGB、UV 和 alpha 通道语义；逻辑不透明时用 opaque Decal 单变量修复 |

## 最关键的失败模式

### 1. 把目标原版人体当形体模板

用户明确要求保留 Karin 原始比例。早期按目标关节逐段拟合，造成腹部、大腿根、脚和头部高度连续回归。正确证据是同角色 donor 的 authoring/compiled 对应，而非“HD2 骨看起来在哪里”。

### 2. 把内部自洽当运行时正确

V10 同时通过完整 Unit、手指、头盔接口、集成和打包，游戏仍出现手臂错位、袖子破面、腹部锯齿、腿脚折叠。这一阶段明确建立原则：preview rig 只能证明候选在自身假设下自洽。

### 3. 对全模型使用统一权重迁移

最近三角形/重心权重适合连续皮肤，却会跨越空间接近但拓扑独立的短裤、袖口、腰带、内衬和饰带。全模型 O44 迁移产生大量异常边；后来所有成功修复都基于连通片和声明域。

### 4. 通用姿势漏掉差分骨运动

V17 的 176/176 是 false positive。其 chest/spine2 迁移只在这两个骨发生显著相对运动时才暴露。此后建立“每次 A -> B 语义迁移必须增加 A/B 差分姿势”的规则。

### 5. 资源闭包正确但 ID 不私有

旧版复用 O44 的两份 child Material 和六份 TextureMap ID。单独启用每个 Mod 都可能看似正确，同时加载时却按顺序串贴图。修复要求全私有 child/texture ID、full/high32 碰撞扫描和最终引用闭包。

### 6. AQ 并发污染证据

多次并发 merge/audit 因共享系统 TEMP 出现 load-save mismatch 或 `OSError 22`。即使输出 triplet 偶然与接受候选同哈希，失败报告仍不能升级。最终链全部串行，并在必要时隔离 `TEMP/TMP`。

### 7. 把 Armor LUT 当成单一材质开关

仅替换 parent 或静态 LUT 不会形成完整 splat 路线。V22 发现 body UV1 原为恒定 `(0,1)`，且 spawn 时九个 `Piece.MaterialLut` 会覆盖静态 child LUT。它完成 body-only 连续 UV1、完整 hybrid 13/40 ABI、IdMask row0 fallback 与九目标 coverage map，却仍遗漏 DecalSheet 的 UV2，最终在游戏中只显示 LUT 的深灰金属响应。V23 因此增加独立的作者颜色坐标门禁。

### 8. 把“贴图已绑定”当成“贴图已采样”

V22 的 3072 BaseColor DDS、Material slot 和 private parent 均通过反提取与 SDK 往返，游戏仍不显示衣服图案。目标 shader 对 UV2 使用严格开区间，常量 `(0,1)` 直接跳过 DecalSheet sampler。以后 Advanced -> Armor LUT 必须同时证明 source sampler、target component mapping、实际 compiled UV 值和 clean-color 运行时结果。

### 9. 只枚举 body kit 就宣布 splat 完成

V23 的身体已经恢复，但 Helmet 是独立 `kit_type=1`、独立 archive 和独立 `Piece.MaterialLut`；head draw 自身也仍是 Advanced 且 UV1/UV2 恒定。以后 coverage map 必须从所有 customization kit type 出发，以可见 Unit/Material 为终点，逐项覆盖 body、head/helmet、undergarment、outer armor、附件、Slim/Stocky 和左右侧 Piece。某一分支运行时成功不能替代其他分支的审计。

### 10. 把旧 shader 的 alpha 当成新 shader 的同义通道

V24 的 head atlas RGB 完整、UV2 可达、Helmet LUT 已注入、40/40 SDK 资源均通过，但 Advanced atlas alpha 88.4498596% 为 0。Armor LUT 将该 alpha 当 Decal coverage，于是 hair/eyes/ears 显示金属底层。以后迁移 parent 时必须为 RGBA 每个通道建立 source -> target 语义映射；若 draw 逻辑不透明，应生成 RGB 保持、alpha=255 的独立 Decal，并以解码像素和 exact-range 差分证明修复。

## 最有效的调试习惯

- 每张用户截图原样冻结并计算 SHA-256。
- 从最近运行时确认的版本分叉，不在被拒绝候选上继续堆补丁。
- 先写 root-cause contract，再写 builder。
- builder 只允许声明域改变，报告精确 changed vertex/weight rows。
- 使用 semantic vertex identity 跨 LOD/Slim/Stocky 同步修复。
- 对最坏边记录对象、edge index、两个 vertex index、中点和权重前后值。
- authoring 门通过后仍要检查 compiled Unit 中相同语义行。
- 最后再重放冻结材质闭包，避免几何迭代重做贴图。
- 失败候选可恢复隔离并明确 `do_not_use`。

## 可复用的冻结策略

项目后期效率提升来自“层层冻结”：

```text
V19 accepted abdomen bridge
  + frozen authoring baseline
    + V22 texture-budget closure
      + body-only hybrid Armor LUT/UV1
        + SR24-exclusive runtime Piece LUT coverage
          + V23 body-only UV0 -> DecalSheet UV2
            + V24 head hybrid/UV1/UV2
              + independent Helmet Piece.MaterialLut coverage
                + V25 opaque head Decal alpha coverage
```

每层都通过哈希和差分证明只增加一个合同。后续项目应尽早采用这种结构，而不是维护一个不断被整体重写的 `.blend`。

## 证据入口

- 完整版本链、哈希、恢复命令：[`../../New_SR24/SOP.md`](../../../SOURCE_REFERENCES.md#local-only)
- V22 贴图、UV、LUT 与 SDK 闭包：[`../../New_SR24/Work/audits/v22_texture_budget_splat_20260805`](../../../SOURCE_REFERENCES.md#local-only)
- V22 最终报告：[`../../New_SR24/Work/audits/v22_texture_budget_splat_20260805/v22-final-static-sdk-closure-r1.json`](../../../SOURCE_REFERENCES.md#local-only)
- V23 UV2 修复与最终报告：[`../../New_SR24/Work/audits/v23_decalsheet_uv2_20260806`](../../../SOURCE_REFERENCES.md#local-only)
- V24 头部/头盔 splat、ownership 与最终报告：[`../../New_SR24/Work/audits/v24_helmet_splat_20260806`](../../../SOURCE_REFERENCES.md#local-only)
- V25 opaque head Decal、运行时拒绝截图与最终报告：[`../../New_SR24/Work/audits/v25_head_decalsheet_opaque_20260806`](../../../SOURCE_REFERENCES.md#local-only)
- 发布包与报告：[`../../New_SR24/Output`](../../../SOURCE_REFERENCES.md#local-only)
