# 工具链、版本与脚本使用

> 原则：工具“能运行”不等于格式兼容。每个项目锁定版本、commit、EXE/脚本哈希，并用冻结参考 triplet 做兼容性探针。

## 工具职责

| 工具 | 主要职责 | 不能替代什么 |
| --- | --- | --- |
| Blender 4.2 LTS | 场景、网格、权重、UV、姿态、离线渲染和 Python 自动化 | 不能证明游戏外部驱动或最终 archive 正确 |
| AQ Modified / ArchiveQT | HD2 Unit/Material/TextureMap 导入、导出、archive 读写 | 不能证明运行时 shader/动画正确；Unit save 会规范化部分字段 |
| HD2SDK CE | Stingray/HD2 资源结构与序列化库 | 版本不匹配时不能盲写当前游戏资源 |
| FileDiver CLI | 当前游戏 archive/FileID 映射与资源提取 | 不能替代 donor authoring/compiled 对应证明 |
| DirectXTex `texconv` | DDS/BC7/sRGB/alpha 编码与解码 | header 正确不能替代解码后像素验证 |
| `hd2-armor-lut-splat-recovery` skill | Armor LUT 机制、Piece ownership、IdMask/LUT、UV ABI、same-ID 注入和运行时矩阵 | 不能把静态闭包提升为 mission splat 通过 |
| PowerShell | 哈希、路径、进程、文件清单和串行流水线 | 不应用宽泛 glob 做部署/回滚删除 |
| Python | 二进制报告、确定性 ZIP、差分/统计 | 避免 ad-hoc 字符串解析结构化资源 |

## New_SR24 的可复现实例

| 工具 | 版本/commit | 工作区位置 |
| --- | --- | --- |
| Blender | `4.2.23 LTS`, build `d0cbe84903e8` | `Shared/blender-4.2.23/blender-4.2.23-windows-x64/blender.exe` |
| AQ Modified | `2.4.3`, commit `28b775689270ee079a3df007a691e9d7db4b277d` | Blender 插件环境；项目 SOP 有锁定证据 |
| HD2SDK CE | `3.9.6`, commit `c90e2f4088e444953899b8338711548e9d9c222c` | `HD2/New_SR24/Work/tools/HD2SDK-CommunityEdition-v3.9.6` |
| FileDiver | `0.7.35` | `HD2/New_SR24/Work/tools/FileDiver-CLI-v0.7.35` |
| texconv | DirectXTex，实际版本/hash 见项目报告 | 项目/共享工具目录 |

这些不是“推荐最新版本”，而是 V21 R2 的复现基线。升级时建立新 environment matrix，先只读解析，再在隔离目录 roundtrip。

## Karin Nyako RE2310 的 RefBindAxis 入口

以下脚本是本知识库当前肩部、肢体、shape key、suppression 和槽位方法的权威案例实现；它们仍含角色名、对象清单、FileID 和阈值，不能直接复制运行：

| 职责 | 案例实现 | 可复用方法 |
| --- | --- | --- |
| rest-to-bind | [`nyako_ref_bind_axis_retarget_v5.py`](../../SOURCE_REFERENCES.md#local-only) | signed semantic basis、shortest-arc、segment scale、末端 linear inheritance、法线 inverse transpose |
| authoring build | [`build_nyako_re2310_ref_bind_axis_v5.py`](../../SOURCE_REFERENCES.md#local-only) | saved shape-key current mix、game-space shoulder partition、唯一 role ownership |
| 几何审计 | [`audit_nyako_ref_bind_axis_geometry_v5.py`](../../SOURCE_REFERENCES.md#local-only) | signed axis、full-3D mirror、fore/aft、segment closure、shape-key/helmet gates |
| 编译 | [`compile_nyako_re2310_ref_bind_axis_v5.py`](../../SOURCE_REFERENCES.md#local-only) | 全可见 LOD、微米 suppression、slot ownership、AQ save/readback |
| 编译后二进制审计 | [`audit_compiled_ref_bind_axis_v5.py`](../../SOURCE_REFERENCES.md#local-only) | 从最终 Unit 重算 bind-axis、镜像、腿链和 suppression 合同 |
| 独立验证 | [`verify_nyako_re2310_ref_bind_axis_v5.py`](../../SOURCE_REFERENCES.md#local-only) | 不复用 builder 内存状态的 AQ 回读与闭包 |

脚本中的 `0.2585172355 m` envelope、角色/Unit 数、骨映射、占位大小和门限均为 `case-specific`。复用前先把它们移入新项目合同，并用新 Ref/目标重新测量。

## Karin Umbrella 的完整 carrier 与肩骨折叠入口

以下实现补充多目标完整 Unit、many-to-one 肩骨和骨盆桥接方法；v2 仅离线通过，不能当作运行时接受模板直接复制：

| 职责 | 案例实现 | 可复用方法 |
| --- | --- | --- |
| bind retarget | [`umbrella_ref_bind_retarget_v2.py`](../../SOURCE_REFERENCES.md#local-only) | UpperArm 锚、carrier roll、minimal closure swing、左右同 basis、法线 inverse transpose |
| authoring build | [`build_umbrella_rs_candidate_v2.py`](../../SOURCE_REFERENCES.md#local-only) | Shoulder/UpperArm many-to-one、game-space ownership、torso -> hip -> leg、共享权重行 |
| visible compile | [`compile_umbrella_rs_v2.py`](../../SOURCE_REFERENCES.md#local-only) | carrier-per-role、compile once、完整 Unit clone、TransformInfo/核心 bone-bind lock |
| replacement package | [`package_umbrella_rs_v2.py`](../../SOURCE_REFERENCES.md#local-only) | 精确旧 triplet 哈希门、排除单一 replaced lineage 的全局碰撞扫描、确定性 ZIP |

脚本内 carrier/FileID、肩 envelope、pelvis split、Material/TextureMap ID 和旧版 live 哈希全部为 `case-specific`。完整失败链见 [Umbrella 案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

## Karin SSF 的自然 seam 与 DS42 owner-clone 入口

以下脚本提供“先审计自然权重、只保留下半身必要 seam edit、按 DS42 owner 编译并克隆、最终 palette/payload 回读”的运行时已接受案例实现：

| 责任 | 脚本 | 可抽象模式 |
| --- | --- | --- |
| authoring build | [`build_ssf_fs37_sc15_candidate_v4_ds42.py`](../../SOURCE_REFERENCES.md#local-only) | 从冻结 donor contract 读取 owner/palette/projection；肩部无 post edit；其他 seam 逐接口处理 |
| shoulder pose audit | [`audit_ssf_v4_shoulder_seam.py`](../../SOURCE_REFERENCES.md#local-only) | 固定 neutral 对应、明确排除 clavicle 的 shoulder-only 差分姿态、seam gap + 邻接 edge ratio + moving coverage |
| visible compile | [`compile_ssf_fs37_sc15_v4_ds42.py`](../../SOURCE_REFERENCES.md#local-only) | 每身体角色在 owner Unit 各 LOD 实际索引中编译一次，保存/回读后完整克隆到目标；helmet native 例外 |
| compiled audit | [`audit_ssf_v4_compiled_ds42_palettes.py`](../../SOURCE_REFERENCES.md#local-only) | 最终语义 palette、used-group coverage、全 LOD shoulder/thigh 链和同角色完整 Unit payload identity |
| namespace/package | [`build_ssf_private_namespace_v4.py`](../../SOURCE_REFERENCES.md#local-only)、[`package_ssf_fs37_sc15_v4.py`](../../SOURCE_REFERENCES.md#local-only) | 版本化私有资源、live full/high32 扫描、严格 aggregate texture budget、确定性三件套 ZIP |

脚本中的 171 点、DS42 owner FileID、FS37/SC15 target、patch index、贴图尺寸和阈值全部为 `case-specific`。复用时应保留报告字段与失败关闭顺序，替换项目合同，不复制常量。完整失败链见 [SSF 案例](case-studies/Karin_SSF_FS37_SC15.md)。

## Blender 后台执行

典型模式：

```powershell
& '<BLENDER_EXE>' --background '<INPUT_BLEND>' --python '<SCRIPT.py>' -- `
  --report '<NEW_REPORT.json>' <other-args>
```

规则：

- Blender 参数在 `--` 前，脚本参数在 `--` 后。
- 含 AQ 的脚本启动后先验证 addon module/version。
- 不默认使用 `--factory-startup`；它可能让 AQ 未注册。
- 保存场景的脚本只写新候选路径，不能覆盖用户源/参考 Blend。
- 对只读审计，在运行前后检查输入 Blend SHA-256。
- 若脚本需要临时 Armature Modifier/对象/组，保存前清理并验证 authoring 合同。

## AQ 串行队列

以下任务不得互相并行：

- archive merge。
- material/TextureMap rewrite。
- AQ resource load-save audit。
- whole archive roundtrip。
- 任何共享 TEMP 中的纹理解码/编码步骤。

纯只读、完全不经过 AQ 临时文件的几何/JSON 分析可以并行。若不确定，按串行处理。

建议为 AQ 进程创建独立临时目录并显式设置：

```powershell
$env:TEMP = '<fresh-project-temp>'
$env:TMP = '<fresh-project-temp>'
```

这里的路径必须是当前项目内已验证的新目录，不要复用系统变量名作为其他含义，也不要并发共享同一路径。

## 后台脚本、BlenderMCP 与桌面自动化的边界

- 对可重复的网格、权重、姿态、AQ 编译和报告任务，优先使用 `--background --python`。命令、输入哈希、报告和退出码比 GUI 操作更适合长线复现。
- BlenderMCP 或 Blender GUI 适合交互观察、骨骼/材质探索和一次性人工修形；一旦结论稳定，应转写为脚本或精确操作清单，并由保存后的 `.blend` 哈希与独立审计绑定。
- `control-special-windows-apps` 一类桌面控制只在普通截图/输入路径无法操作 DCC、DirectX 游戏或特殊窗口时使用。它是交互通道，不是模型、archive 或运行时正确性的证据。
- 通过 Steam 启动游戏、写游戏 `data` 和控制游戏 UI 是三个独立授权域。桌面控制能力存在不代表获得了其中任何授权。
- GUI 截图必须记录对应文件/部署 triplet 哈希；不能仅以窗口标题、Mod 名或 patch index 判断当前加载的是哪个候选。

## FileDiver 的使用边界

FileDiver 用于从当前游戏版本建立 archive/FileID 映射：

- 解析前记录 archive magic/signature、版本和文件大小；parser 不认识新签名时失败关闭，不能把“0 entries”或异常字段解释成目标不存在。
- 记录 CLI 版本和 EXE SHA-256。
- 输出到 `Work/` 新目录，不写 live game data。
- 资源路径和 FileID 从当前游戏重新提取，不沿用几个月前参考 Mod 的映射。
- 对结果建立 machine-readable manifest，避免只靠终端输出或人工文件名。

参考 Mod 的旧 triplet 能被 FileDiver/AQ 解析，也不代表能直接作为当前游戏 target 编译基线。

反过来也成立：当前游戏 archive 更新为工具尚未证明支持的新容器时，不能临时用它替换已锁定 carrier。应区分“当前 target 身份/消费者图来源”和“已证明的 authoring/bind carrier 来源”，分别记录格式兼容风险。Umbrella 构建期间观察到当前基础 archive 的 DSAR 签名与旧命名变化，但尚无独立格式报告，因此该观察保持 `case-specific`，不能提升为通用格式事实。

## texconv 纪律

- 锁定 EXE 版本/hash和完整命令行。
- 输出目录必须新建，避免拾取旧 DDS。
- BaseColor 明确 sRGB；数据纹理明确 linear。
- 稀疏 alpha 使用/评估 `-sepalpha`。
- 逻辑不透明 BC7 另做 alpha-preservation 探针；必要时使用 `-bc x -aw 1000`，并要求解码 alpha min/max 精确满足合同。
- mip 数、尺寸、format 与目标 TextureMap 合同一致。
- 两次隔离编码做逐字节比较。
- 解码后做 luma、alpha、ROI 和边缘像素统计。

## PowerShell 哈希与进程检查

只读示例：

```powershell
Get-FileHash -Algorithm SHA256 -LiteralPath '<PATH>'
Get-Process -Name helldivers2 -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath '<GAME_DATA>' -File |
  Where-Object Name -Like '<ARCHIVE>.patch_*'
```

部署/回滚应使用参数化、带哈希硬门的脚本。不要根据 `Get-ChildItem` 的结果拼接跨 shell 删除命令。

## 脚本分层

建议每个项目按职责分开：

```text
inspect_*     只读探索，不生成接受结论
analyze_*     统计/建立假设
build_*       从冻结输入生成新候选
compile_*     authoring -> visible triplet
patch_*       单字段/单资源 rewrite
merge_*       显式来源合并
audit_*       独立硬门与报告
validate_*    视觉/像素/姿态验证
package_*     确定性 ZIP
deploy_*      明确授权后的安全写入
verify_*      独立复现与最终确认
```

脚本应拒绝覆盖输出、记录输入/输出 SHA-256、返回非零退出码表示门禁失败，并在报告中保持 `accepted == all(required_checks)`。

### Armor LUT/splat 工具

执行 Armor LUT/splat 任务时，应先阅读当前项目提供的工具说明和对应症状 reference；本公共知识库只总结已经在项目中复核过的结论，不依赖任何个人机器上的 skill 路径。

- `scripts/inspect_patch.py`：只读清单、结构验证和 non-streaming DDS 反提取。
- `scripts/audit_id_mask_array.py`：IdMasksArray row-weight 证据。
- `scripts/inject_runtime_lut.py`：按完整 coverage map 做确定性多目标 same-ID LUT 注入。
- `scripts/collapse_lut_rows.py`：在有证据时构建全 mip 等行 LUT 探针。
- `scripts/copy_unit_uv_channels.py`：材质范围内复制兼容 UV component；只有 shader/UV ABI 已证明时使用。

New_SR24 V22 没有直接复制 UV0 到 UV1，而是项目脚本 `write_karin_v22_body_oblique_uv1.py` 对 body-only 顶点生成连续斜投影，并逐三角形证明不退化。用户运行时截图随后暴露出独立的 DecalSheet UV2 缺口；V23 使用通用 `copy_unit_uv_channels.py` 在两个 body Material 范围内执行 UV0 -> UV2，同时保持 UV1。两类操作解决不同 sampler，不得合并为“复制三套 UV”。

V24 增加三份 case-specific 脚本：`audit_karin_v24_helmet_lut_ownership.py` 从当前 customization 快照证明独立 Helmet Piece/LUT ownership；`build_karin_v24_head_splat_candidate.py` 只迁移 head hybrid 材质、head UV1/UV2 和 Helmet same-ID LUT；`verify_karin_v24_helmet_splat.py` 检查 40 资源、DDS ABI、59,300 个 head 顶点、精确差分和整档 roundtrip。它们的 FileID/计数不可复制到其他 Mod，但“先枚举全部 kit type，再按可见 Unit 闭合 coverage”的顺序可复用。

V25 增加两份 case-specific 脚本：`generate_karin_v25_opaque_head_decalsheet.py` 锁定源 DDS/PNG/texconv 哈希，保留 RGB、固定 alpha=255，并执行 BC7 回读 alpha 与 RGB PSNR 门禁；`verify_karin_v25_opaque_head_decalsheet.py` 从两个独立候选证明只改变指定 TextureMap 的 GPU payload，验证 40 个 SDK 资源、归档 DDS header/payload 差异和整档 roundtrip。可复用的方法是“跨 shader 迁移前重分类 alpha 通道语义 + 解码验证”，其中角色 FileID、GPU offset、资源计数和预期哈希仍是案例数据。

### Blender 注册插件与冻结 SDK 不同版本

本机 Blender 可能注册一个 AQ 版本，同时脚本动态载入另一个冻结 HD2SDK。若两者的 `Hd2ToolPanelSettings` 属性集不同，Material `entry.Save()` 可因 UI PropertyGroup 缺字段而失败。不要把它误判为资源损坏：

- 记录两个 `__init__.py` 的 SHA-256/版本。
- 使用冻结 SDK 的底层 `StingrayMaterial.Serialize` 比较 main payload。
- Texture 仍执行 `Load/Save`，Unit 执行 load-only。
- 最后执行整个 StreamToc triplet roundtrip，要求逐字节一致。
- 报告中明确该分层验证模式；不能声称执行了未执行的 UI-level Material Save。

## 通用脚本入口

详见 [tools/README.md](tools/README.md)。其中打包、部署、复现脚本参数化程度较高；V17-V21 builder 和硬编码 draw/对象脚本只作为算法范例，不能直接套到新项目。

## 从项目脚本抽象时的检查表

- [ ] 移除角色名、版本号和旧 JSON schema 常量。
- [ ] 参数化 archive ID、patch index、target/donor FileID。
- [ ] 参数化对象、LOD、体型和 local palette manifest。
- [ ] 删除硬编码 draw count、material occurrence 和资源计数。
- [ ] 把阈值移入项目合同并记录校准来源。
- [ ] 把允许变化/冻结域写成输入 manifest。
- [ ] 绑定上游报告的 schema、path、SHA-256 和 accepted 状态。
- [ ] 所有输出使用 exclusive create，不覆盖。
- [ ] 失败时不留下会被误认成正式候选的 Output 文件。
- [ ] 在冻结小样上做成功、失败、输入变化、目标占用等测试。

## 互联网研究的证据规则

社区论坛和 Mod 页面适合发现工具、版本变化和已知症状，但不能直接替代当前资源审计：

- 保存页面 URL、发布日期、适用游戏/工具版本和结论摘要。
- 格式/插件行为优先验证官方/项目源码和本地二进制。
- 下载工具后记录来源、版本、哈希并隔离测试。
- 不把社区声称“works”提升为本项目 `runtime_validated`。
- 发布日期早于当前游戏更新的工具/教程必须重做兼容性探针。
