# 第一人称手臂、HUD、打包与发布

从用户源模型生成第一人称手模的完整权威流程见 [从角色源模型制作第一人称手臂](17-first-person-arms-from-source.md)。本章侧重固定路径、HUD、loose tree、VPK、发布和回滚；不要把这里的项目实测数字当作通用 arms 参数。

## 1. 固定接口路径

不同 survivor 使用固定的世界模型、手臂和 HUD 路径。以 Rochelle 接口为例：

```text
models/survivors/survivor_producer.*
models/weapons/arms/v_arms_producer_new.*
materials/vgui/s_panel_lobby_producer.vtf
materials/vgui/s_panel_producer.vtf
materials/vgui/s_panel_producer_incap.vtf
```

这些是目标接口示例。新项目必须从当前游戏资源重新提取，不能根据 survivor 显示名猜文件名。

## 2. 第一人称手臂

检查：

- MDL/VVD/VTX checksum 与版本；
- 目标 viewmodel 所需骨骼和父子关系；
- 武器 attachment、袖口和手腕接缝；
- 每顶点最大三权重；
- 所有武器、换弹、推击、倒地和特殊动画。

参考手臂只应提供 viewmodel ABI，不应默认提供可见几何。推荐分工是：

- 用户 Blend 提供皮肤、前臂、袖套、腕饰、UV、法线和 atlas 材质；
- 已验收 world 构建提供相同源模型的最终 Basis、world bind、单位、权重和三角顺序；
- 同角色成熟手臂参考只提供 55 骨接口、bonemerge、idle/proportion 和前臂 helper 的 rest/权重证据；
- 当前 survivor 原生资料提供目标路径和游戏兼容性检查。

### source-derived 选面与 manifest

选面必须在不可变源 Blend 上完成，并输出带源 SHA-256、对象拓扑合同和排序 polygon index 的 manifest。不要在已经重绑定的派生 Blend 上重新跑权重阈值；重绑定会改变分数，但 polygon index 可以在拓扑不变时原样映射。

Karin 对锁定源 SHA-256 `43B1A8DBE7990B9AB6547369B93C6EFE30777B4E714B266370AE1CF64F545C41` 的实测合同为：

| 对象 | 精确规则 | 结果 |
| --- | --- | ---: |
| `Body.003` / `Body` | 取 `Shoulder_OFF`、`UpperArm_OFF`、`Elbow_OFF`、`LowerArm_OFF`、`Wrist_OFF`、`Hand_OFF`、`Finger_OFF` 相对 Basis 位移 `>1e-7` 的顶点并集；三角面的三个顶点都必须在并集中 | 9,636 tris |
| `Body.006` / `ClothA_Blue` | 完整 mesh-edge 连通块；锁定源中四块为 `1134/750/90/90` tris，空间/权重复核为 `z_min>0.87` 且对应侧臂骨平均权重 `>0.90` | 2,064 tris |
| `Body.001` 主袖 | 在 8,896-face 最大主体块中，对 Shoulder、UpperArm、LowerArm、Hand 和五指三节共 19 个对应侧源骨求每顶点权重和；取每面三顶点分数中位数，严格 `>0.6525174379348755`，再按共享完整边取最大 face region | 左右各 2,213 tris |
| `Body.001` 脱离腕饰 | 排除最大主体块；按共享完整边求 face component；要求 `z_min>0.75`、对应侧 19 骨平均权重 `>0.01`，且左侧 `x_min>0`、右侧 `x_max<0` | 左右各 958 tris |

最终闭包是 `Body=9636`、`ClothA=2064`、`ClothB=6342`，合计 18,042 tris / 54,126 SMD corners，只允许 `Body`、`ClothA_Blue`、`ClothB_Blue` 三个材质。组件编号和阈值均是源哈希锁定值；移植到其他角色时保留算法与断言，不复制计数。

Karin 的原 Blend 与 Zoey-proportion 派生 Blend 在上述三个对象上顶点数、边、polygon 顺序和 topology hash 完全一致，因此 manifest 的 polygon index 可直接应用到派生 Blend。这项证明来自 `work/arms_from_source/arm_selection_subagent_audit.json` 与派生 Blend 的锁定 SHA；当前 `source_selection_contract.json` 本身只保存源 SHA、规则、polygon arrays 和 totals。未来 manifest 应直接内嵌逐对象 counts/topology hash。通用实现必须先比较拓扑合同；不一致时停止并重建 manifest，不能用坐标近邻猜 index。

### 黄金 world-SMD 抽取路径

稳定路径如下：

```text
immutable source Blend
  -> source polygon-index manifest
  -> accepted retargeted world Blend
  -> accepted triangulated world SMDs
  -> 按 manifest 精确复制 material + 3 corner 的 triangle block
  -> 全局 uniform similarity 保形放入 view rest space
  -> 只转移同角色参考的最近唯一位置样本权重
  -> 在源 topology 上保留完整权重平滑
  -> 最后一次 top-3 与归一化
  -> 复用参考 ABI/QC 接口编译正式 arms
```

该路径比重新导出临时裁剪 Blend 更容易证明血缘：每个输出三角块逐字节来自已验收 world SMD，header 也来自同一 world SMD。前提是 mesh 已三角化，并且另有顺序回归证明 SMD triangle 顺序等于 Blender polygon 顺序。Karin 当时的 world export report 没有直接保存 polygon-to-triangle hash；可信度来自最终抽取报告对 54,126 个 corners 的 position/material/parent/UV/weight 回归和 copied-block 断言。未来 exporter 应直接输出 mapping/hash。SMD corner 行开头是 parent bone ID，不是 Blender vertex/polygon index；不能据此反推 manifest。

若走 Blender 裁剪分支，必须在删除 shape key 前把当前 `Basis.co` 快照写回基础 mesh：`snapshot Basis -> clear keys -> mesh.vertices.foreach_set(snapshot)`。仅 clear 而未写回会让第一人称网格回到旧 Basis，造成整体错位；这也是 Karin 最终改用 world-SMD 精确抽取作为黄金路径的原因之一。

55 骨参考只作为接口：可以复用其 55 个 definebone、49 个 bonemerge、`idle`、`arml_proportions` 和前臂 helper rest pose，但 QC 的 `$bodygroup "arms" { studio "arms.smd" }` 必须指向 18,042-tri source-derived SMD，`$cdmaterials` 必须指向本项目 atlas namespace。参考三角面、旧材质名和旧材质目录都不得进入候选。

Karin 早期采用过把 Picodra Ellis `mechanic` 固定长度改成 `producer`、并原样搬运 VVD/VTX 的方案。用户已确认这不满足“第一人称来自所提供 Blend”的要求；该方案现已**否决并废弃**，不得作为快捷方式恢复，也不得把旧报告中的“结构兼容”误写成视觉资产验收。

结构审计通过后仍必须列出游戏内武器 smoke test，因为 HLMV 无法覆盖所有 viewmodel 动作与遮挡。

## 3. HUD

- 确认 lobby、panel、incap 三类目标路径。
- 保留需要的 alpha；不要只看 RGB 预览。
- 引擎可能继续使用原生 VMT wrapper，替换包只需提供同路径 VTF。
- 对每张 VTF 解码预览并检查尺寸、格式、mip、alpha 和方向。

## 4. Loose tree 组装

每个候选写入新目录，例如：

```text
work/release_candidate_007/game/
```

组装器应拒绝覆盖现有输出，并只接收显式输入路径。至少验证：

- 必需的 world/arms companion 文件齐全；
- world 的 MDL/VVD/VTX/PHY 和 arms 的 MDL/VVD/VTX 各自来自同轮候选；不得只替换其中一个 companion；
- 所有 VMT/VTF 路径解析；
- `addoninfo.txt` 存在；
- 无临时源文件、报告、`.pwl.vtf`、绝对路径或开发机路径；
- 无 preview alias、compile-only animation sidecar、DX80/SW VTX、QC/SMD 或参考资产；
- 无大小写不一致的重复路径；
- 无同步盘生成的 `*_冲突文件_*`、副本或 expected manifest 外 extra；
- 文件后缀在允许列表中。

按 companion family 原子闭合，而不是按单文件理解“只改了一点”：

| Family | 常见运行件 | 规则 |
| --- | --- | --- |
| world | MDL/VVD/VTX/PHY | MDL checksum 改变时 PHY 即使 hull 几何未改也要同轮生成/替换 |
| light | MDL/VVD/VTX | 明确无 PHY 的合同要拒绝 stray `.phy` |
| first-person arms | MDL/VVD/VTX | 可独立复用，但必须对当前候选做 hash reuse attestation |

多个 runtime variant 覆盖同一 avatar 时，每个目标路径仍是独立 companion family：分别携带并审计自己的 MDL/VVD/VTX/PHY、QC/collision/physics 来源和 checksum。共享可见网格不授权复制另一个 variant 的 PHY，也不要求不同 sequence/physics family 的 MDL 原始字节相同；应以显式 cross-variant bind/root contract 说明哪些数据必须相等。

复用上一候选未变化的 arms、材质或 HUD 时，报告 `reused_from_candidate`、上一报告哈希和当前 loose-entry 哈希相等。不要仅链接带旧绝对路径的历史报告并假定本轮仍是同一字节。

## 5. 构建与验证 VPK

使用 L4D2 自带 `vpk.exe`。随后不能只执行列表命令；验证器应读取 VPK 内每个 payload，并与 loose tree 对应文件逐字节比较。

### 运行时 VPK 文件名合同

`vpk.exe l` 能离线列出归档，不等于 L4D2 的 Addons 管理器一定能用该文件名挂载它。公开的相关 Source 分支 Addons 实现存在固定大小的 addon 基名缓冲，但这不是当前 L4D2 分支的完整源码证据；因此把它视为兼容风险，而非已证实唯一根因。发布名采用短 ASCII 名，保守建议 stem 不超过 32 字符。构建门分别记录完整文件名/stem 的字符数与编码后字节数。

发生“列表里启用但游戏显示原版”时，可在不重编 payload 的前提下把同一 VPK 改成唯一短名作为挂载探针。必须同时：完整退出游戏、移走旧长名副本、备份并保持 `addonlist.txt` 原编码、把短名设为第一个启用项、重新启动。随后优先保存 `show_addon_load_order` 和 `show_addon_metadata`，它们是最强的引擎挂载证据；独特替换在复测中恢复也可记为 runtime mount pass，但不能据此还原唯一根因。不要只看 Add-ons 菜单复选框。

报告至少包含：

- entry 数；
- 每个相对路径的 size、CRC 和 SHA-256；
- loose tree 与 VPK 的 missing、extra、mismatch；
- VPK 整体大小和 SHA-256。

文件数量是项目实测值，不是固定标准。

相同 entry 数、payload 总字节和 VPK 总大小也不能证明候选相同。两个版本完全可能只做等长二进制变化，最终大小一致但整体 SHA 不同；身份必须由逐 entry 哈希和整个 VPK SHA 共同确定。候选 VPK 通过后，复制/提升到正式 release 路径，再对正式 VPK 做第二次逐 entry 验证。

Cloth04 Zoey v1.2 与 v1.3 都是 32 entries、28,400,301 VPK bytes，但 SHA-256 分别为 `269503...157BF` 与 `B5931A...719B4`。这是“相同数量/大小仍不是同一候选”的直接反例；具体完整哈希见 Cloth04 案例。

Karin source-derived arms 最终 smooth 候选的锁定 release closure 为 33 文件、`44,029,711` payload bytes：替换三件 arms companion，删除旧 `materials/ko_komado_pt` 的 14 件参考手臂材质，不新增其他路径。VPK 为 `44,031,174` bytes，SHA-256 `D59B4B001AC2B63BF1E61A0E136BC8E6E9326DAE5AC99B8A30CE05FD270AA0CA`。正式运行时名为 `KarinPT_Rochelle_SourceArms.vpk`；此前两次地图测试时尚无该条目已落盘为 enabled 的确认，66 字符长名也存在兼容风险，因此长名已废弃。其 payload 与短名包逐字节相同。用户已在 2026-08-14 确认组合挂载修复后的短名候选能生效并替换 Rochelle；这不自动证明全部武器动作和极限裁口。后续只改材质或 HUD 时不能盲目沿用总字节数，但必须保持 `actual paths == candidate manifest paths`；若仍出现 `ko_komado_pt`，即使 VPK 能构建也应失败。

Basis 修复后也不要默认逐 influence bind 转换已经安全；VRD/helper 折叠仍可在相邻顶点间制造局部不连续。Karin 最终使用一个全局 similarity（scale `1.072`、offset `[0,1.43,0.14]` Source units）保持源三角形形状，再转移同角色参考的最近唯一位置样本权重，沿源拓扑进行 24 轮不提前 top-3 的邻接平滑，最后裁为最多三影响并归一化。54,126 条 edge 的局部非均匀 stretch 为 0；同坐标权重一致、左右骨串零泄漏，triangle-corner L1 最大差 `0.973790`（参考最大 `0.950164`）。中间的 `44,029,647` 与 `44,029,767` loose-tree 计数都不是最终交付。

## 6. 候选清单

候选 manifest 是交付件的唯一索引。它应记录：

```json
{
  "candidate_id": "candidate_007",
  "status": "current",
  "vpk": {
    "path": "<absolute or project-relative path>",
    "size": 0,
    "sha256": "<hash>",
    "entry_count": 0
  },
  "source_lock_sha256": "<hash>",
  "animation_contract": {
    "output_slot": "<path>",
    "primary_animation_basis": "<Zoey/TeenAngst or proven exception>",
    "corrective_source_sha256": "<hash>",
    "sequence_contract_report": "<path>",
    "world_vertex_mapping_report": "<path>"
  },
  "runtime_variant_contract": {
    "targets": [],
    "shared_visible_bind": {"path": "<report>", "sha256": "<hash>"},
    "cross_variant_root_parity": {"path": "<report>", "sha256": "<hash>"}
  },
  "first_person_arms_contract": {
    "slot_interface_source": {"path": "<report>", "sha256": "<hash>"},
    "visible_geometry_source": {"path": "<report>", "sha256": "<hash>"},
    "geometry_selection_source": {"path": "<manifest>", "sha256": "<hash>"},
    "topology_contract": {"path": "<report>", "sha256": "<hash>"},
    "world_smd_extraction": {"path": "<report>", "sha256": "<hash>"},
    "viewmodel_abi_source": {"path": "<report>", "sha256": "<hash>"},
    "weight_guidance_source": {"path": "<report>", "sha256": "<hash>"},
    "compiled_arms_contract": {"path": "<report>", "sha256": "<hash>"},
    "hlmv_screenshot_manifest": {"path": "<report>", "sha256": "<hash>"}
  },
  "reports": [],
  "runtime_mount": "pending-user-test",
  "runtime_world_visual": "pending-user-test",
  "runtime_first_person_weapons": "pending-user-test",
  "supersedes": "candidate_006"
}
```

不要让后续 agent 从目录修改时间、文件名或“最大的 VPK”推断当前候选。

动画合同必须进入 manifest，因为同一个 Louis/Rochelle 输出路径可以合法使用 Zoey 主动画；只记录 `target_survivor` 无法复现 corrective、include 或 sequence flags。compiled world 还必须链接 VVD 顶点预算与 VTX mapping 报告。

manifest 还应记录：

- `component_closure`：world/light/arms 各自预期文件与 checksum；
- `reused_components`：复用来源和本轮字节等价证明；
- `expected_changes_from_previous` 与 unchanged closure；
- `negative_controls`：锁定坏候选哈希、审计器 schema 和预期失败 check ID；
- native compile-only dependency denylist；
- source-lock required roles 完整性，而不只写“已列项全部通过”；
- runtime evidence sidecar 列表，不原地改写历史发布状态。

## 7. 防止误交付参考 Mod

用户曾合理怀疑交付 VPK 实际是参考 Mod。应从数据血缘上预防：

- 比较候选 MDL/VVD/VTX/PHY 与参考包和本项目编译输出的 SHA-256；
- 比较材质名、骨数、贴图哈希与 modelname；
- VPK payload 必须逐字节等于本候选 loose tree；
- HLMV 使用唯一 preview alias，截图中保留模型名；
- manifest 指向生成该候选的审计与编译报告。

HLMV 正式路径可能被 VFS 解析成游戏原版或其他 addon。应另编译一个只改 `$modelname` 的唯一 alias，确认 alias QC 与正式 QC 的网格、骨架、材质、sequence 和输入哈希相同，再以**绝对** `-game` sandbox 路径和绝对 preview MDL 路径启动。相对 MDL 参数可能按进程 cwd 解析，不能作为血缘验证。预览至少保存正面、背面、侧面/斜侧面和能看到腕口、掌心、袖套的近景；长序列还要记录固定进度帧、Ground 与至少一个 Origin+Bones 诊断帧。单张正面图不足以证明没有复制参考几何或漏选腕饰。

Karin 旧 Picodra 搬运 arms 的 SHA-256 负面门为：

| 文件 | 必须拒绝的旧哈希 |
| --- | --- |
| MDL | `DFBAD4CE20FE13356375BC3034BAABB4574119D05CE6DBB5E759100FE5C892A1` |
| VVD | `4D7757362316C334A85F57E9E0E9A4A694C46C9A2183710F825C863ED74E9864` |
| DX90.VTX | `D4C0634282C57ACCB847F47AEB1915DFBE1C81E6018BC9FB9E3CDD73D9C5717F` |

同时拒绝 arms MDL 中的 `mechanic`、`ko_komado_pt`、`clotha_pink`、`clothb_pink`，以及 release tree 中任何 `materials/ko_komado_pt/**`。正面门应要求新 atlas token `Body`、`ClothA_Blue`、`ClothB_Blue` 和本项目 `$cdmaterials` namespace；哈希负面门与 token/路径门必须同时存在。

“文件路径正确”不足以证明内容来自本项目。

## 8. 候选差异门槛

新候选与上一候选按 `relative path + SHA-256` 比较。修材质时，world MDL/VVD/VTX 不应无故变化；修骨架时，HUD 不应变化。任何超出预期的改变都应阻止交付并调查 source-of-truth 或构建目录污染。

回归验证器应有正、负双门：当前候选通过，锁定哈希的已知坏候选在预期语义 check ID 上失败。不要只锁“失败数量”，因为验证器 schema 增加检查后总数会变化。负候选意外通过、输入哈希不符或负报告缺失都应阻止 release。

## 9. 安装与回滚

安装器：

1. 定位明确的 addon 目标路径。
2. 如目标存在，创建带时间戳的备份并记录原哈希。
3. 复制候选并记录安装哈希。
4. 写安装 manifest。

卸载器：

1. 仅当现有文件哈希仍等于本次安装哈希时删除。
2. 若用户已修改文件，停止而不覆盖。
3. 若有备份，逐字节恢复并验证原哈希。

先在 fake game root 完成 roundtrip 验证，再提供给用户。

## 10. 交付说明

交付时明确：

- VPK 的绝对路径、大小和 SHA-256；
- 本候选相比上一版改了什么；
- 已完成哪些静态/HLMV 检查；
- 哪些项目仍需用户实机测试；
- 如何安装与回滚；
- 已知限制和待观察场景。

不要把“未运行自动化游戏测试”写成“未验证”；应准确区分静态、HLMV 和游戏内三个验证层。

发布 manifest/final report 是打包时的不可变快照。用户后续确认通过或发现失败时，新增 append-only runtime evidence sidecar，以 VPK SHA-256、日期、验收范围和未声称范围绑定反馈；不要回写旧 manifest 伪造“发布前已经知道实机结果”。
