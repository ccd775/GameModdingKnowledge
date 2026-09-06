# PowerShell 命令配方

这些命令展示 Karin 项目脚本的正确调用形态，帮助后续 agent 快速建立可追溯流水线。先在项目根运行每个脚本的 `--help`；新项目的路径、文件名、survivor、骨数和 pelvis 偏移必须重新填写。

## 1. 统一变量

```powershell
$ProjectRoot = '<workspace>\Mods\L4d2\<ProjectName>'
$BlenderPath = Join-Path $ProjectRoot 'tools\Blender-<version>\blender.exe'
$SourceIoRoot = Join-Path $ProjectRoot 'tools\SourceIO-<version>'
$GameRoot = '<steam-library>\steamapps\common\Left 4 Dead 2'
$StudioMdlPath = Join-Path $GameRoot 'bin\studiomdl.exe'
$VtexPath = Join-Path $GameRoot 'bin\vtex.exe'
$VpkPath = Join-Path $GameRoot 'bin\vpk.exe'
$CompileSandbox = Join-Path $ProjectRoot 'work\compile_sandbox'
Set-Location -LiteralPath $ProjectRoot
```

不要使用 `$HOME` 等系统变量保存任务路径。正式报告应记录展开后的绝对路径和工具 SHA-256。

## 2. 查看脚本契约

普通脚本：

```powershell
python src\scripts\verify_source_lock.py --help
```

依赖 `bpy` 的脚本必须从固定 Blender 运行：

```powershell
& $BlenderPath --background --factory-startup `
  --python src\scripts\build_retargeted_world_blend.py -- --help
```

## 3. 验证 source lock

```powershell
python src\scripts\verify_source_lock.py `
  --lock source-lock.json `
  --report reports\source-lock-validation.json
```

任何 mismatch 都应停止后续修改，并决定是恢复输入还是有意识地更新锁和重新审计。

## 4. 审计 Blend 与 shape key

```powershell
& $BlenderPath --background --factory-startup '<source.blend>' `
  --python src\scripts\audit_blend_source.py -- `
  --output reports\source\blend-audit.json

& $BlenderPath --background --factory-startup '<source.blend>' `
  --python src\scripts\audit_shape_key_deltas.py -- `
  --output reports\source\shape-key-deltas.json `
  --epsilon 0.000001
```

`epsilon` 是项目参数。报告中同时保留未阈值化的最大位移或足够精度，避免小但有效的 key 被误判为零。

## 5. 审计 VRM

```powershell
python src\scripts\audit_source_vrm.py `
  --blend '<source.blend>' `
  --vrm '<source.vrm>' `
  --output reports\source\vrm-audit.json
```

该脚本是 Karin 定制脚本的例子；新角色应检查其默认字段和角色名称假设。

## 6. 生成骨架映射

`build_rig_candidate_map.py` 接收源审计、VRM、权重、参考 body/QC、当前原生 body/QC/arms 和同角色模型探针。参数很多，建议先输出完整 help，再将实际命令保存到报告：

```powershell
python src\scripts\build_rig_candidate_map.py `
  --project-root $ProjectRoot `
  --source-audit reports\source\blend-audit.json `
  --vrm-audit reports\source\vrm-audit.json `
  --reference-body '<reference-body.smd>' `
  --reference-qc '<reference.qc>' `
  --native-current-body '<native-body.smd>' `
  --native-current-qc '<native.qc>' `
  --native-current-arms-qc '<native-arms.qc>' `
  --output-json reports\rig\bone-map.json `
  --output-md reports\rig\bone-map.md
```

不要省略实际使用的额外审计参数；命令只是结构示例。

## 7. 构建派生 Blend

脚本在当前打开的源 Blend 上运行，并将变更写入新的 output Blend：

```powershell
& $BlenderPath --background --factory-startup '<source.blend>' `
  --python src\scripts\build_retargeted_world_blend.py -- `
  --sourceio-root $SourceIoRoot `
  --target-model '<same-avatar-reference.mdl>' `
  --mapping reports\rig\bone-map.json `
  --output-blend work\blender\retargeted-world.blend `
  --output-report reports\build\retargeted-world.json `
  --max-influences 3
```

构建器必须拒绝覆盖原始 Blend。高跟鞋等常驻 shape key 应在该阶段由审计证据驱动烘焙。

## 8. 导出 SMD/VTA

```powershell
& $BlenderPath --background --factory-startup 'work\blender\retargeted-world.blend' `
  --python src\scripts\export_world_smd.py -- `
  --addon-root '<BlenderSourceTools-addon-root>' `
  --output-dir work\modelsrc\world `
  --report reports\build\world-smd-export.json `
  --source-units-per-meter 52.49343832020997 `
  --include-shapes
```

只有在脚本/派生 Blend 尚未应用 Source 单位时才传相应缩放语义；避免重复缩放。以该脚本当前实现和报告为准。

## 9. Source-derived 第一人称手臂

以下展示阶段关系，不提供可跨角色复制的 Karin 阈值。先在不可变源 Blend 生成选面 manifest：

```powershell
& $BlenderPath --background --factory-startup '<immutable-source.blend>' `
  --python src\scripts\build_source_arm_selection_manifest.py -- `
  --output work\arms_from_source\source-selection-manifest.json
```

在把 polygon indices 应用到派生资产前，另行比较每个对象的 vertex/edge/polygon 顺序和 topology hash。当前项目脚本若未把它们写进主 manifest，必须链接独立 topology 审计，不能口头假设一致。

从已验收、已三角化的 world SMD 精确抽取 triangle blocks：

```powershell
python src\scripts\extract_source_first_person_arms_from_world_smd.py `
  --selection-manifest work\arms_from_source\source-selection-manifest.json `
  --world-smd-report reports\build\world-smd-export.json `
  --retarget-report reports\build\retargeted-world-blend.json `
  --legacy-dir build\modelsrc\<character>\first_person_source `
  --output-dir build\modelsrc\<character>\first_person_source\corrected_world_bind `
  --report reports\arms_hud\world-smd-extract.json
```

若构建器仍要求 `--legacy-dir`，它只用于 Basis 坐标回归；新实现应把该诊断输入改为可选或显式命名，不要让历史失败产物成为正式几何来源。

用重新拟合的单一 similarity 保持全部源三角形形状。每个材质 SMD 使用一个 `--source`：

```powershell
python src\scripts\build_view_arms_rigid_alignment_smd.py `
  --source '<body-world-bind.smd>' `
  --source '<cloth-a-world-bind.smd>' `
  --source '<cloth-b-world-bind.smd>' `
  --target-reference '<same-avatar-reference-arms.smd>' `
  --scale '<fitted-uniform-scale>' `
  --x-offset '<fitted-x>' --y-offset '<fitted-y>' --z-offset '<fitted-z>' `
  --output build\modelsrc\<character>\first_person_source\arms-view-geometry.smd `
  --report reports\arms_hud\view-similarity.json
```

只有 edge ratio 的 local nonuniform stretch 为零/在项目锁定容差内，才进入权重阶段。然后只转移同角色参考权重，沿源 topology 保留完整影响平滑，最后一次性 top-3：

```powershell
python src\scripts\transfer_reference_arm_weights.py `
  --source build\modelsrc\<character>\first_person_source\arms-view-geometry.smd `
  --reference '<same-avatar-reference-arms.smd>' `
  --output build\modelsrc\<character>\first_person_source\arms-view-reference-weights.smd `
  --report reports\arms_hud\reference-weight-transfer.json

python src\scripts\smooth_transferred_arm_weights.py `
  --source build\modelsrc\<character>\first_person_source\arms-view-reference-weights.smd `
  --iterations '<audited-count>' --self-weight '<audited-weight>' `
  --max-influences 3 `
  --output build\modelsrc\<character>\first_person_source\arms-view-final.smd `
  --report reports\arms_hud\reference-weight-smoothing.json
```

不要传 `--prune-every-iteration`，除非项目报告证明它优于完整权重迭代。最后审计几何零变化、edge、左右泄漏、同坐标权重和 triangle-corner L1：

```powershell
python src\scripts\audit_first_person_arms_surface_candidate.py `
  --source '<body-world-bind.smd>' --source '<cloth-a-world-bind.smd>' --source '<cloth-b-world-bind.smd>' `
  --geometry build\modelsrc\<character>\first_person_source\arms-view-geometry.smd `
  --candidate build\modelsrc\<character>\first_person_source\arms-view-final.smd `
  --reference '<same-avatar-reference-arms.smd>' `
  --output reports\arms_hud\surface-candidate-audit.json
```

再用 `generate_source_first_person_arms_qc.py` 绑定已审计 ABI，编译正式路径；preview 候选只改 `--model-name`：

```powershell
python src\scripts\generate_source_first_person_arms_qc.py `
  --reference-qc '<decompiled-reference-arms.qc>' `
  --arms-smd build\modelsrc\<character>\first_person_source\arms-view-final.smd `
  --reference-idle '<reference-idle.smd>' `
  --reference-proportion '<reference-proportion.smd>' `
  --model-name 'weapons\arms\v_arms_<target>_new.mdl' `
  --output-dir build\modelsrc\<character>\first_person_source\compile_final `
  --report reports\arms_hud\source-arms-qc.json

python src\scripts\run_studiomdl.py `
  --studiomdl $StudioMdlPath `
  --game $CompileSandbox `
  --qc build\modelsrc\<character>\first_person_source\compile_final\v_arms_<target>_new.qc `
  --log reports\compile\source-arms-studiomdl.log `
  --report reports\compile\source-arms-studiomdl.json

& $BlenderPath --background --factory-startup `
  --python src\scripts\audit_sourceio_model.py -- `
  --sourceio-root $SourceIoRoot `
  --model (Join-Path $CompileSandbox 'models\weapons\arms\v_arms_<target>_new.mdl') `
  --output reports\arms_hud\source-arms-sourceio-audit.json
```

专用 compiled ABI gate 还应读取最终 MDL 的 ordered bones/parents/rest、bone-merge flags 和 sequence/animation flags；SourceIO 的骨数统计不能替代。完成唯一 alias 多视角 HLMV 后，再从已验收 world/material/HUD loose tree 原子替换三件 arms 并删除旧参考闭包：

```powershell
python src\scripts\assemble_source_arms_release.py `
  --accepted-tree work\release_<accepted-world-material-candidate>\game `
  --compiled-arms (Join-Path $CompileSandbox 'models\weapons\arms') `
  --output work\release_<source-arms-candidate>\game `
  --report reports\release\loose-tree-source-arms.json
```

完整接受/否决分支见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。

## 10. 生成比例 SMD

```powershell
python src\scripts\generate_proportion_smd.py `
  --custom-reference work\modelsrc\world\avatar_reference.smd `
  --zoey-reference '<native-animation-reference.smd>' `
  --proportion-output work\modelsrc\world\anims\avatar_proportion.smd `
  --reference-output work\modelsrc\world\anims\avatar_native_reference.smd `
  --report reports\build\proportion.json `
  --pelvis-z-offset-source-units '<measured-value>'
```

参数名保留了 Karin 项目的 `zoey-reference` 术语。用于其他动画基准前应确认脚本实现，而不是只替换文件路径。

这里的 `--zoey-reference` 是 **proportion corrective 的动画基准输入**，不是 output slot，也不是最终角色 rest skeleton。对本库默认 Zoey profile，它应锁定 native TeenAngst reference SMD 的路径与 SHA-256；即使输出是 Louis 的 `survivor_manager.*`，也不能把参数自动改成 `Manager.smd`。报告还应显式记录 primary animation basis、sequence contract source 和 ground offset owner。

## 11. Flex、Jiggle 与 Physics

```powershell
python src\scripts\generate_flex_include.py `
  --vta work\modelsrc\world\avatar_face.vta `
  --smd work\modelsrc\world\avatar_face.smd `
  --output src\qc\avatar-flex.qci `
  --report reports\build\flex.json

python src\scripts\generate_jigglebone_include.py `
  --mapping reports\rig\bone-map.json `
  --output src\qc\avatar-jiggle.qci `
  --report reports\build\jiggle.json

python src\scripts\prepare_physics_smd.py `
  --source '<native-physics.smd>' `
  --target-reference work\modelsrc\world\avatar_reference.smd `
  --output work\modelsrc\world\avatar_physics.smd `
  --report reports\build\physics.json
```

如使用 jiggle smoke compile，显式传同一个 `$StudioMdlPath`、`$CompileSandbox` 和新 smoke directory。

## 12. 构建与验证材质

```powershell
python src\scripts\build_l4d2_atlas_materials.py `
  --audit reports\materials\blender-material-audit.json `
  --source-dir work\material_build\source_png `
  --build-dir work\material_build `
  --output-dir work\compile_sandbox\materials\models\survivors\<material-folder> `
  --vtex $VtexPath `
  --game $CompileSandbox `
  --report reports\materials\material-build.json `
  --markdown reports\materials\material-pipeline.md `
  --max-dimension 2048

python src\scripts\validate_l4d2_material_outputs.py `
  --sourceio-root $SourceIoRoot `
  --material-dir work\compile_sandbox\materials\models\survivors\<material-folder> `
  --materialsrc-dir work\material_build\materialsrc\models\survivors\<material-folder> `
  --smd-report reports\build\world-smd-export.json `
  --output reports\materials\material-validation.json `
  --preview reports\materials\vtf-contact-sheet.png
```

`2048` 是本流程在 L4D2 VTEX 中验证的上限，不代表源贴图必须永久降到该分辨率；保留原始高分辨率源图。

## 13. 生成 QC 并编译

`generate_world_qc.py` 需要完整的 attachment、hitbox、sequence、procedural、jiggle、flex、proportion 和可选 physics 输入。先用 `--help` 填齐，不要删掉看似多余的原生契约。

```powershell
python src\scripts\run_studiomdl.py `
  --studiomdl $StudioMdlPath `
  --game $CompileSandbox `
  --qc '<generated-world.qc>' `
  --log reports\build\studiomdl.log `
  --report reports\build\studiomdl.json

python src\scripts\audit_compiled_world_contract.py `
  --sourceio-root $SourceIoRoot `
  --model work\compile_sandbox\models\survivors\<target>.mdl `
  --reference-model '<native-target.mdl>' `
  --output reports\build\compiled-world-contract.json
```

该命令后还必须运行项目的 compiled geometry/VTX mapping audit。最低门禁是：VVD LOD0 工程预算 `<=60000`，拒绝 `>=65535`；每个 VTX original ID 在 mesh/model/VVD 范围内；每个 model 顶点覆盖完整。不要因为 `studiomdl.exe` return 0、无 warning 或 companion checksum 一致而跳过。

## 14. 组装、打包和 payload 验证

始终使用新的候选目录：

```powershell
python src\scripts\assemble_release_tree.py `
  --world-dir work\compile_sandbox\models\survivors `
  --world-name '<target-model-stem>' `
  --world-materials work\compile_sandbox\materials\models\survivors\<material-folder> `
  --arms-hud-game build\arms_hud\<candidate>\game `
  --addoninfo src\runtime\addoninfo.txt `
  --output work\release_<candidate>\game `
  --report reports\release\loose-tree-<candidate>.json

& $VpkPath (Join-Path $ProjectRoot 'work\release_<candidate>\game')

python src\scripts\validate_vpk_tree.py `
  --vpk-exe $VpkPath `
  --vpk work\release_<candidate>\game.vpk `
  --loose work\release_<candidate>\game `
  --report reports\release\vpk-validation-<candidate>.json
```

确认 `vpk.exe` 实际输出路径后再写 manifest；不要假定目录中任意 `.vpk` 是本轮结果。候选提升到 `release/` 后，再以正式 VPK 路径运行一次逐 entry 验证。相同 entry 数和文件大小不是身份门，必须锁整个 VPK SHA-256。

## 15. 安装回滚与最终 gate

```powershell
python src\scripts\validate_installer_roundtrip.py `
  --release work\release_<candidate>\game.vpk `
  --work work\installer-roundtrip_<candidate> `
  --report reports\release\installer-roundtrip-<candidate>.json

python src\scripts\build_final_validation.py `
  --root $ProjectRoot `
  --output reports\release\final-validation-<candidate>.json
```

最后生成候选 manifest，写入 VPK 的绝对/项目相对路径、大小、SHA-256、entry 数和报告路径。运行状态至少拆成 `runtime_mount`、`runtime_world_visual` 与 `runtime_first_person_weapons`，不要用一个 `runtime` 字段把“包未挂载”和“武器动作异常”混在一起。

用户复测后新增 `reports/runtime/<candidate>-<date>.md/json` sidecar，以 VPK SHA 绑定反馈。不要修改已经发布的 manifest/final report；它们是打包时快照。

## 16. 短名挂载探针与运行取证

只在游戏完全退出、候选哈希已锁定且用户授权的游戏目录中执行。脚本会备份原 VPK 和 GBK `addonlist.txt`，不会重编 payload：

```powershell
& src\scripts\repair_runtime_mount_name.ps1 `
  -SourceVpk (Join-Path $ProjectRoot 'release\<short-name>.vpk') `
  -GameRoot (Join-Path $GameRoot 'left4dead2') `
  -BackupRoot (Join-Path $ProjectRoot 'work\runtime_backups') `
  -ReportPath (Join-Path $ProjectRoot 'reports\runtime\mount-repair.json') `
  -OldName '<old-or-long-name>.vpk' `
  -NewName '<unique-short-ascii-name>.vpk' `
  -ExpectedSha256 '<candidate-sha256>'
```

安装前后分别用 `Get-FileHash` 证明同一 payload。完整重启游戏，在故障/复测会话保存控制台输出：

```text
show_addon_load_order
show_addon_metadata
```

记录 VPK 文件名、stem 字符数、编码后字节数、`addonlist.txt` 编码/状态、其他同路径 addon、完整重启与地图进入时间。短名修复有效只证明组合挂载措施恢复运行，不自动证明长名是唯一根因。

## 17. Source-fit 与 Procedural 正负回归

项目脚本参数不同，先运行 `--help`。通用调用形态为：

```powershell
python src\scripts\audit_<runtime-failure>.py `
  --candidate '<compiled-good-candidate>' `
  --contract '<rig/sourcefit/procedural-report>' `
  --output reports\regression\<candidate>-positive.json

python src\scripts\audit_<runtime-failure>.py `
  --candidate '<locked-known-bad-candidate>' `
  --contract '<matching-old-contract>' `
  --output reports\regression\<known-bad>-negative.json
```

final gate 同时要求：positive 的必需 check ID 全通过；negative 输入 SHA 与锁定坏版一致，并在预期 check ID 上失败。不要只要求“失败数量大于零”。

Cloth04 的可执行实例位于：

```powershell
python L4d2\cloth04_replace_zoey\src\scripts\audit_ponytail_root_skinning.py --help
python L4d2\cloth04_replace_zoey\src\scripts\audit_compiled_ponytail_physics.py --help
```

它们分别覆盖 collapsed-chain seam CPU skin，以及 world/light compiled procedural 全字段 parity；骨名、阈值和参数是 Cloth04 个案，不能原样复制。

## 18. 命令执行记录

每次正式构建保存：

- 展开后的命令与 cwd；
- 输入文件 SHA-256；
- 工具路径、版本与 SHA-256；
- stdout、stderr、exit code；
- 产物清单和 SHA-256；
- 重试次数；
- 运行时长；
- 候选 ID。

命令成功但报告门槛失败时，候选仍为失败。
