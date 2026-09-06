# Watch Dogs Karin 角色替换 Mod 长线 SOP

最后更新：2026-08-05（Asia/Shanghai）

## 1. 交付范围

- 目标游戏：《Watch Dogs》(2014, PC)。
- 只完整替换 Aiden 默认“私法制裁者”服装对应的 `char01.xbg`。
- 商店换装、DLC、囚服、开场和剧情强制模型不在本轮范围。
- 运行包使用 NexusTools/ModManager 独立 FAT/DAT，不覆盖原版游戏档案。
- 当前数据库重定向兼容 Living City 2.9.3，Karin 必须位于 `Living_City` 上方。
- diffuse 只使用原始 diffuse RGB。emission、glow、bloom mask 永不合入 diffuse。

## 2. 版本状态

| 版本 | 状态 | 用途 |
|---|---|---|
| 1.0.0 | 历史冻结 | 首个完整替换基线 |
| 1.2.0 | 已冻结、当前回滚点 | 比例、鞋底、头发材质和基础动态已通过实机 |
| 1.3.0 | 已冻结、当前发布版 | 双马尾孔位、脖套动态和手部权重改进；可部署 |

1.3 的 Blender、FBX、ZModeler、XBG、FAT/DAT、ModManager 哈希门和实机动作验收均已通过。用户于 2026-08-05 接受该版本；少数持枪或插兜动画仍有轻微手指变形，作为已接受限制保留，不再阻断发布。

## 3. 不可变输入

- 用户源：`karin_D7-E4-04_uv_optimized.blend`，SHA-256 `564DF9BFFDFF764E57BA1B6FA6C1928264AFC14C9121E4C49CDA6EE2F9BA2F79`。
- 净化源：`.work/blender/04_hair_subfloat_seam_repaired.blend`，SHA-256 `7A25E1EB4333A708B4F21A96AC42E5922B303D683FB8A92C97FBDF8B3715810E`。
- 骨映射：`.work/retarget/source_to_target_mapping.csv`，SHA-256 `A8199FDCD22319BA871505FE7AFDC5B1C9DB22E1A77CBE4960C6B644C94FFBB6`。
- 原版 donor `char01.xbg`：SHA-256 `C22D937A4A66605CA8666AF2130305FCC64246839B254795E783747B75DCB613`。
- donor sidecar A/B/C：`163BCF0280F916EE377E8CCBD24BA772123EB45CCA29AFD7DF194C3A3A9F8CA3` / `6B326143A07C774DB878C840CB4467F95F4239010B008CF44F74B5104822FF9D` / `AA2CD24CCCF0B3A33804285AA11666C56212C5711B29BF4F09232E57750721E5`。
- 私有中性头发材质：`droylouo-m-20260729190000-v6a.material.bin`，SHA-256 `28576B7F3A0A9724CF068A28A4BBA52ACED6E6DB768DB1B7514233B4E818DAB9`。
- Living City-compatible `graphickit_models.lib`：SHA-256 `CEA69043A894D5659795E41348364AC740507FAD68CBB9D6BB0DF6FA14A6686E`。

输入只读。破坏性处理必须输出到新的版本化路径，并证明输入哈希未改变。

## 4. 1.2 冻结基线

发布目录：`dist/karin_replacer_v1_2_0/`；归档：`dist/karin_replacer_v1_2_0.zip`。

- DAT：25,584,656 bytes，SHA-256 `EC3D7E107CC7C23C8D9686DEA72C96BB1DD8C19AA890B63E98F9F54DEBEE2A9E`。
- FAT：372 bytes，SHA-256 `A2F586D7D3C9DF0FC6799F79E7115D8FB07D996FA0B47E14D0992678A9473A41`。
- `modconfig.json`：604 bytes，SHA-256 `4F8A0CB2C3B5BD448C7AD3FC897A68F08EBAC50D77BB9C21711EC0BA380BEB54`。
- ZIP：5,753,215 bytes，SHA-256 `1D7C4A8923AE124EBDF44A46D73FDE80DA4236C5D7B9541043B3A1FA83273BB2`。
- 冻结报告：`.work/release_freezes/karin_replacer_v1_2_0/RELEASE_FREEZE.json`。

1.2 的历史问题推动了 1.3：双马尾首端和脖套动态已经通过门控；手部已明显改善，但仍保留上述轻微限制。

## 5. 1.3 权威生产链

| 阶段 | 权威工件 | SHA-256 / 结果 |
|---|---|---|
| Blender 候选 | `.work/v13/35_candidate_v1_3_hole_exact.blend` | `0D60FE536B742A35CEBD870A39A95069C34A6C4A856C2624441DCF5DBE5D085F` |
| 修复报告 | `.work/v13/35_candidate_v1_3_hole_exact.report.json` | `A46F861B05A2DADA54C16605945A66E3AF29BAACCD435FE1961DDBAECEF665A3` |
| 发带孔门 | `.work/v13/38_ponytail_hole_alignment_final.json` | `PASS`；两侧误差 `0.119 / 0.122 mm` |
| 姿态门 | `.work/v13/39_pose_regression_hole_exact.json` | `all_pass=true` |
| 脖套门 | `.work/v13/41_collar_pose_audit_hole_exact/collar_pose_audit.json` | 6 个姿态全部通过 |
| 双 LOD | `.work/module_build/karin_v13_hole_exact_final/karin_modules_lod_karin_v13_hole_exact_final.blend` | LOD0 `45,003 / 84,586`；LOD1 `15,828 / 28,488` |
| 朝向 FBX | `.work/fbx_handoff/karin_v13_hole_exact_final_orientation/karin_char01_scale001_orientation_fixed.fbx` | `98FE401213627B4E630D64D29CDA37F43BDB1E86CE339A20261472C1C6237126` |
| Z3D checkpoint | `.work/zmodeler_production/karin_char01_v13_hole_exact_final/project/char01_karin_v13_final_compound_checkpoint.z3d` | `CD8E70ACFF29A0BF6921707374FB49556DB67700B52FBC27197CAB2E45F13F30`；只读 |
| raw XBG | `.work/zmodeler_production/karin_char01_v13_hole_exact_final/output/graphics/characters/char/char01/char01.xbg` | `D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7` |
| XBG GPU 门 | `.work/zmodeler_production/karin_char01_v13_hole_exact_final/audit/xbg_mesh_buffers.json` | `PASS_CLEAN_TARGET`，`84,586 / 28,488` |
| 正式运行包 | `dist/karin_replacer_v1_3_0.zip` | 5,752,682 bytes；`5B2BE5A472F5AFCA0B0F42BF3BA80B89FE24481701E72C846DA00B86041701FB` |
| 构建报告 | `.work/release_freezes/karin_replacer_v1_3_0/evidence/build_validation_published.json` | `PASS / published`；`F05116E4F5F0B4AEEE0DA054521CF1D1AB9E74F5386DBBEBDCC41A87108E6172` |
| 冻结报告 | `.work/release_freezes/karin_replacer_v1_3_0/RELEASE_FREEZE.json` | `PASS / USER_ACCEPTED` |

### 5.1 修复合同

- 手部保留同一手指相邻两节渐变，禁止 direct Meta 权重和左右手交叉权重；最大手部影响数为 4。
- 掌指连接处采用四圈衰减 Hand 混合：`0.8 / 0.6 / 0.4 / 0.2`。
- 双马尾整体 Z 位移固定为 `-0.03627 m`；两侧必须在各自 62 顶点绿色发带孔内达到 `<= 0.5 mm` 源形象归一化误差。
- 脖套高度缩放 `0.76`，后上缘再下降 `0.010 m`；Head 权重上限 `0.20`，Spine2 权重上限 `0.25`。
- 1.3 不再修改 1.2 已认可的身体比例、鞋底高度、头发/尾巴中性材质或 diffuse-only 贴图。

## 6. 生产与审计顺序

1. 从冻结 1.2 候选运行 `pipeline/fix_karin_v13_final_issues.py`；输出不得覆盖源 BLEND。
2. 运行 `pipeline/audit_karin_ponytail_hole_alignment.py`、姿态门和脖套姿态门。
3. 应用 diffuse-only atlas，构建双 LOD；UVSet1、材质、骨架和拓扑合同不得漂移。
4. 输出 binary FBX 7400，`global_scale=0.01`、`-Z Forward / Y Up`、EDGE smoothing、423 bones、四个 donor 材质、Color1、自定义法线、最多 6 权重。
5. ZModeler 导入固定为 Axes `1.000`、Geometry `1.000`、axis system `Blender`；不得再乘 `0.01`。
6. 新 LOD 分别绑定原 `char01.skel`，删除旧 donor geometry，再建立只有 `L0/L1` 的全新 `char01.mesh` Compound。
7. 最终根节点恰好为 `char01.skel` 与粗体 `char01.mesh`；不得留下 `Pelvis`、独立 LOD、donor branch 或第三个 state。
8. 导出后运行 GPU buffer audit；必须精确为 `84,586 / 28,488` 且无 donor index sequence/faces。
9. 在全新 ZModeler 进程回读 XBG，L0/L1 必须都显示完整 Karin。验证场景关闭时不保存。
10. 运行包严格为 22 项：1 XBG、19 diffuse-only XBT、1 私有材质、1 完整 `graphickit_models.lib`。

## 7. 运行包命令

候选构建：

```powershell
python pipeline\build_karin_runtime_v13.py `
  --raw-xbg .work\zmodeler_production\karin_char01_v13_hole_exact_final\output\graphics\characters\char\char01\char01.xbg `
  --expected-raw-xbg-sha256 D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7 `
  --staging-only
```

游戏门通过后的发布命令：

```powershell
python pipeline\build_karin_runtime_v13.py `
  --raw-xbg .work\zmodeler_production\karin_char01_v13_hole_exact_final\output\graphics\characters\char\char01\char01.xbg `
  --expected-raw-xbg-sha256 D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7 `
  --publish --replace-staging
```

1.3 已经发布并冻结；不得为“重建验证”删除或覆盖当前 `dist/karin_replacer_v1_3_0{,.zip}`。后续变化必须使用新的版本号和发布目录。当前脚本仍依赖 `.work/runtime_probe_build/karin_replacer_v1_1_0_v3j/workspace/` 的冻结 diffuse-only 基线，禁止提前删除。

## 8. ModManager 安装与游戏门

1. 启动游戏目录中的 `bin/ModManager.exe`，不要操作其他同名 Mod 管理器。
2. `Install Mod` 选择 `dist/karin_replacer_v1_3_0.zip`，确认显示 `Karin Default Outfit Replacer (v1.3.0)`。
3. 安装后保持 Karin 高于 `Living_City`；不删除、不禁用、不重排其他用户 Mod。
4. 核对实时临时目录的 DAT/FAT/config 与构建包逐字节一致。
5. 从 ModManager 启动游戏，只装备默认“私法制裁者”。
6. 基础门：载入、待机、转身、前后行走，确认完整 Karin、朝向和 LOD 正常。
7. 1.3 重点门：
   - 手枪和步枪握持：不得出现掌面爆裂、手指大范围分层或严重反折。
   - 插兜与手机：指尖不得远距离爆出；少数姿态的轻微手指变形是 1.3 已接受限制。
   - 双马尾首端：正面、背面和侧面均从绿色发带孔内起始。
   - 脖套：待机、跑动低头、抬头和转头时不过度拉伸，不与后脑/后发明显穿插。
8. 回归门：鞋底、体态、头发/尾巴亮度、diffuse 颜色、跑跳/翻越/攀爬/驾驶均不得退化。

剧情强制切换到非默认模型只记录，不作为本轮失败。默认服装出现 Aiden 几何、崩溃、反向行走、手掌爆裂、马尾根明显偏孔或脖套严重穿模时属于回归失败。

## 9. 恢复与回滚

1. 恢复任务先读本 SOP、`ZMODELER_OPERATOR_CHECKLIST.md` 和最新构建/冻结报告。
2. ZModeler 只允许一个 Build 1244 实例；checkpoint 只读，working 必须是独立副本。
3. 磁盘证据与文档冲突时，以哈希通过的最新 checkpoint 和审计报告为准，并立即修正文档。
4. 1.3 运行时失败：在 ModManager 中用同一 `friendlyId` 安装冻结的 `dist/karin_replacer_v1_2_0.zip`，保持其仍高于 Living City。
5. 测试前备份位于 `.work/runtime_test_backups/v13_preinstall_20260805/`；不回滚 Living City、游戏原档或其他用户 Mod。

## 10. 永久禁止事项

- 禁止编辑源 BLEND、donor、只读 checkpoint 或原版游戏 DAT/FAT。
- 禁止把 replacement 拖入仍含 donor geometry 的旧 Compound。
- 禁止从其他 XBG 借用 unknown sidecar；sidecar 不进入运行包。
- 禁止把 emission/glow mask 合入 diffuse。
- 禁止仅凭“可见”“日志无 error”或文件头宣称 XBG 合格；GPU audit 与 fresh-process 回读缺一不可。
- 禁止记录、复制或传播 ZModeler 许可证、Ubisoft 账号或其他凭据。
- ZModeler、ModManager 和游戏的键鼠操作统一使用 `$control-special-windows-apps`。

## 11. 保留与清理

长期保留：不可变输入、1.2/1.3 发布物与 freeze、`.work/v13/35`、`38`、`39`、`40-42`、最终 atlas/LOD/FBX/Z3D/XBG、最小 fresh-process 证据、构建审计和游戏证据。

1.3 已正式冻结，可删除被替代的重型候选、重复预览、临时对位渲染、ZModeler 逐点击截图和 `pipeline/__pycache__`。不得批量改写历史审计，也不得删除当前构建仍引用的 v1.1 v3j workspace。最终用户安装见 `DEPLOYMENT_WATCH_DOGS_KARIN.md`。
