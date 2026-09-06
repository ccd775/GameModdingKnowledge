# 已验证工具与脚本入口

> 本目录只记录可复用入口。脚本仍保留在产生其证据的项目中；复制到新项目前先移除项目专用 schema/name，并重新锁定 SHA-256。

## 知识库自检

公共库自带只读检查器 [`validate_knowledge_base.ps1`](validate_knowledge_base.ps1)。在交接、更新源 SOP、替换案例成品或提交公共文档后运行：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File 'HD2/SharedKnowledge/tools/validate_knowledge_base.ps1' -Deep -AsJson
```

它验证 Markdown 相对链接与代码块、全部 JSON、manifest 文件集合、活动源 SOP/authoring/集成报告/ZIP/三件套哈希、两个 supporting case 的锁定证据，以及主 ZIP 三成员顺序与 stored 模式；`-Deep` 还逐成员计算主 ZIP 内 SHA-256。活动证据失败时返回非零退出码；manifest 明确声明未驻留的历史 evidence root 只生成 warning。它不会修改知识库、项目或游戏目录。

## 通用性较高的脚本

| 用途 | 已验证实现 | 复用注意 |
| --- | --- | --- |
| 参考 Unit 只读解析 | `../../New_SR24/Work/scripts/audit_reference_units.py` | 需 Blender 4.2 + AQ 已注册；输入绝不保存 |
| Blend 几何合同 | `../../New_SR24/Work/scripts/audit_blend_geometry_contract.py` | 检查对象、拓扑、Basis 等；阈值需项目化 |
| 姿态/边长回归 | `../../New_SR24/Work/scripts/validate_karin_hd2_pose_regression.py` | 姿势、对象类别和门槛当前带项目语义，应抽象后复用 |
| 单 triplet 确定性 ZIP | `../../New_SR24/Work/scripts/package_karin_hd2_single_triplet.py` | 参数化较好；schema 名仍带 New_SR24 |
| 安全直拷部署 | `../../New_SR24/Work/scripts/deploy_karin_hd2_single_triplet.py` | 仅适用于新槽并严格拒绝覆盖；replacement 需另用精确旧哈希门流程，执行均需要用户授权 |
| 两次 ZIP 复现验证 | `../../New_SR24/Work/scripts/verify_karin_hd2_single_triplet_reproducibility.py` | schema 常量需为新项目更新 |
| 私有命名空间审计 | `../../New_SR24/Work/audits/namespace_conflict_20260729/audit_private_namespace.py` | 需重建目标资源/安装资源清单 |
| donor/O44 冲突审计 | `../../New_SR24/Work/audits/namespace_conflict_20260729/audit_conflict_namespace.py` | O44-specific，作为算法范例 |

## 专项算法范例

这些脚本不应直接当通用工具运行，但包含可复用的审计模式：

| 主题 | 范例 |
| --- | --- |
| donor source/compiled 对应 | `../../New_SR24/Work/scripts/compare_o44_source_authoring_geometry.py` |
| donor rest/inverse-bind 提取 | `../../New_SR24/Work/scripts/extract_o44_donor_full_bind_contract.py` |
| 坐标/形体不变量 | `../../New_SR24/Work/scripts/analyze_o44_d7_shape_invariants.py` |
| 局部 palette 和骨映射 | `../../New_SR24/Work/scripts/analyze_c4_o44_donor_mapping.py` |
| 源几何 provenance | `../../New_SR24/Work/scripts/audit_karin_v10_source_geometry_preservation.py` |
| 连通片语义 | `../../New_SR24/Work/scripts/audit_c4_nosleeve_component_semantics_v17.py` |
| 姿态 outlier 定位 | `../../New_SR24/Work/scripts/audit_karin_hd2_pose_edge_outliers.py` |
| 肩部/肢体 semantic-axis retarget | `../../Karin_Nyako_RE2310/Work/scripts/nyako_ref_bind_axis_retarget_v5.py` |
| 肩部 game-space 分件与 shape-key bake | `../../Karin_Nyako_RE2310/Work/scripts/build_nyako_re2310_ref_bind_axis_v5.py` |
| signed axis/mirror/closure 几何门禁 | `../../Karin_Nyako_RE2310/Work/scripts/audit_nyako_ref_bind_axis_geometry_v5.py` |
| compiled bind/suppression/helmet contract | `../../Karin_Nyako_RE2310/Work/scripts/audit_compiled_ref_bind_axis_v5.py` |
| Shoulder/UpperArm many-to-one + carrier roll/minimal swing | `../../Umbrella_Replace_RS6RS67RS100/Work/scripts/umbrella_ref_bind_retarget_v2.py` |
| torso -> hip -> leg ownership/seam bridge | `../../Umbrella_Replace_RS6RS67RS100/Work/scripts/build_umbrella_rs_candidate_v2.py` |
| compile-once + complete Unit clone | `../../Umbrella_Replace_RS6RS67RS100/Work/scripts/compile_umbrella_rs_v2.py` |
| exact-lineage replacement package/collision gate | `../../Umbrella_Replace_RS6RS67RS100/Work/scripts/package_umbrella_rs_v2.py` |
| 面部贴图 UV/ROI | `../../New_SR24/Work/scripts/audit_karin_face_atlas_uv.py` |
| 材质像素对比 | `../../New_SR24/Work/scripts/validate_karin_face_shadow_comparison.py` |
| 最终引用闭包 | `../../New_SR24/Work/scripts/audit_karin_hd2_v21_integration.py` |

## 工具版本基线

New_SR24 最终链使用：

- Blender `4.2.23 LTS`, build hash `d0cbe84903e8`。
- AQ Modified `2.4.3`, commit `28b775689270ee079a3df007a691e9d7db4b277d`。
- HD2SDK Community Edition `3.9.6`, commit `c90e2f4088e444953899b8338711548e9d9c222c`。
- FileDiver CLI `0.7.35`，项目内 EXE SHA-256 见案例 SOP。
- DirectXTex `texconv`，用于 BC7/sRGB/`-sepalpha`；新项目需记录实际 EXE 版本和哈希。

这些版本是复现实例，不是“永远最新”。升级任一工具后先对冻结参考 triplet 做只读解析和 roundtrip compatibility probe。

## Blender 调用模式

需要 AQ 的脚本通常使用：

```powershell
& '<BLENDER_EXE>' --background '<AUTHORING_BLEND>' --python '<SCRIPT>' -- <SCRIPT_ARGS>
```

注意：

- `--` 之后才是 Python 脚本参数。
- 不要默认加 `--factory-startup`；它可能导致 AQ 未注册。
- 一个时间只运行一个 AQ archive 写/roundtrip 任务。
- 输出和 report 使用不存在的新路径。
- 保存 `.blend` 的脚本必须明确指定副本，不能让参考/源文件成为当前场景输出。

## 推荐抽象方向

将项目脚本迁移到新项目时，优先参数化：

- archive ID、target/donor FileID manifest。
- 对象类别与 LOD 列表。
- local palette 映射。
- 正式 binding report schema。
- 允许变化/必须冻结的资源集合。
- 姿态集和阈值。
- material/texture 私有 namespace manifest。

不要只做字符串替换版本号；任何硬编码 draw count、资源计数、对象名、骨 local index 都必须重新从新项目输入测量。
