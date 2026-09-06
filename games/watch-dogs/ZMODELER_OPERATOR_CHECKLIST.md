# ZModeler 操作清单：Karin `char01` v1.3 最终 Compound

最后更新：2026-08-05（Asia/Shanghai）

## 1. 用途与状态

本清单用于复现或审计默认“私法制裁者”服装的最终 `char01.xbg`。`1.3.0` 已完成双 LOD Compound、GPU buffer 审计、全新进程回读、ModManager 安装和实机验收；这里没有未完成的 GUI 游标。

- 最终发布包：`dist/karin_replacer_v1_3_0.zip`
- 冻结记录：`.work/release_freezes/karin_replacer_v1_3_0/RELEASE_FREEZE.json`
- 生产根：`.work/zmodeler_production/karin_char01_v13_hole_exact_final/`
- 工具：`.tools/zmodeler3-3.3.1.1244/ZModeler3.exe`

商店服装、囚服、开场和剧情强制模型不在范围内。

## 2. GUI 与许可证合同

1. 所有 ZModeler 键鼠操作使用 `$control-special-windows-apps`。
2. 生产期间只允许一个 ZModeler 实例；不要并行启动第二个实例。
3. 启动、模态窗口关闭或进程重启后重新发现句柄；输入前后都用 mss 截图确认。
4. 坐标只来自最新截图；长路径由外部设置剪贴板，再发送 `Ctrl+A`、`Ctrl+V`。
5. 不记录或复制许可证、Platform ID、Ubisoft 账号或任何凭据。
6. 出现 license denial、空白渲染或错误进程时先关闭错误实例，不在未确认的窗口继续操作。
7. 不从 autosave 覆盖生产 checkpoint。

## 3. 权威输入与恢复点

唯一允许导入的 FBX：

`.work/fbx_handoff/karin_v13_hole_exact_final_orientation/karin_char01_scale001_orientation_fixed.fbx`

- 6,028,956 bytes
- SHA-256 `98FE401213627B4E630D64D29CDA37F43BDB1E86CE339A20261472C1C6237126`
- binary FBX 7400，423 bones，四个原生材质槽
- LOD0：45,003 vertices / 84,586 triangles
- LOD1：15,828 vertices / 28,488 triangles

关键恢复点：

- 双绑定 checkpoint：`project/char01_karin_v13_double_bound_checkpoint.z3d`
  - 12,377,111 bytes
  - SHA-256 `2CCC226BB36591ADCD2D6A797146E21F6F695A416C5C0F9B6EFE5B3599359E30`
- 最终 Compound checkpoint：`project/char01_karin_v13_final_compound_checkpoint.z3d`
  - 9,488,657 bytes
  - SHA-256 `CD8E70ACFF29A0BF6921707374FB49556DB67700B52FBC27197CAB2E45F13F30`
  - 只读，不直接编辑
- 最终 raw XBG：`output/graphics/characters/char/char01/char01.xbg`
  - 3,802,672 bytes
  - SHA-256 `D77BA08F1630CA1E58E103A2BAE8878C7165917C55BD657D16B13DA2CC7E73F7`

donor sidecar A/B/C 只用于 ZModeler 导入/导出，必须来自本生产树 `input`。它们不进入 Mod 包。

## 4. 每次复现前

- [ ] 当前只有一个已授权 Build 1244 进程。
- [ ] FBX、donor、double-bound checkpoint 和 final checkpoint 哈希匹配。
- [ ] final checkpoint 保持只读；任何修改从独立 working 副本开始。
- [ ] 输出仅指向本生产根，不指向游戏目录、`refer/` 或原版资源。
- [ ] 已阅读本次步骤的成功条件和失败恢复点。

身份或哈希不符时停止，不在 GUI 中猜测修复。

## 5. FBX 导入与材质合并

1. 在空场景导入权威 FBX。
2. 固定 `Rescale Axes=1.000`、`Rescale Geometry=1.000`、`Convert axis system=Blender`。
3. 不再乘 `0.01`，不修改对象名、材质顺序或骨架。
4. 导入后应出现 `Pelvis`、`char01.mesh LOD0_REBUILT` 和 `char01.mesh LOD1_REBUILT`。
5. 将 staging 合并到 donor working 时，`Merge Collisions` 固定为：
   - `Materials = Use from Scene`
   - `Objects = Autoresolve (rename)`
6. 新 LOD 只能使用 donor 的四个原生材质槽，不允许 `Material.001`、`[1]` 或 Default 面分配。

## 6. 双 LOD 绑定

对 LOD0 和 LOD1 分别执行一次：

1. 只显示原 `char01.skel` 和当前目标 LOD，隐藏旧 `char01.mesh`、独立 `Pelvis` 与另一 LOD。
2. 清除旧 mark，在两脚间根部选中完整 Skeleton Base；整副骨架统一高亮才算成功。
3. 重新显示目标 LOD，执行 `Rigging > Skeleton > Skin Bind`。
4. 日志必须精确确认当前 LOD 与 `char01.skel` 已绑定；出现单根 `Ph_...`、另一 LOD、`already bind` 或 missing mark 均失败。
5. 两个 LOD 都成功后保存新的 double-bound working；不要覆盖只读 checkpoint。

## 7. 建立全新 Compound

1. 从双绑定 checkpoint 创建可写 working。
2. 删除旧 donor `char01.mesh` 和独立导入的 `Pelvis`；保留原 `char01.skel` 与两条已绑定 LOD。
3. 选择 LOD0，激活全局 `L0`，在 Structure 页执行 `Convert to Compound`。
4. 将新 Compound 精确重命名为 `char01.mesh`。
5. 点击 Compound 标题旁的小锁图标，固定 Structure 目标。
6. 激活全局 `L1`，把 LOD1 拖入空的 L1 state；源 LOD 根应被消费。
7. state 列表必须只有 `L0`、`L1`，不得出现第三个 state。
8. 分别激活 L0/L1，确认两者都显示完整 Karin，无放射碎片、空 state 或 donor 叠加。
9. 最终 Hierarchy 根层必须恰好为：
   - `char01.skel`
   - 粗体 `char01.mesh`
10. 不得留下独立 `Pelvis`、`LOD*_REBUILT`、donor branch 或无名根。
11. 保存 working，复制为新的只读 checkpoint，并记录大小和 SHA-256。

不要把 replacement 拖进已经含 donor geometry 的旧 Compound；这会把 donor 三角形追加到两个 GPU buffer。

## 8. XBG 隔离导出

1. 输出固定为 `output/graphics/characters/char/char01/char01.xbg`。
2. 使用 Watch Dogs XBG filter；不启用 `Create .skeleton`，不修改缩放、轴向、LOD 或材质选项。
3. 输出目录只提供同 donor A/B/C 供转换器读取；sidecar 不进入运行包。
4. 导出前截图应同时证明双根、L0/L1 和输出路径。
5. 导出后记录完整日志、文件大小和 SHA-256；任何 error/failed 或第三根都阻断。

## 9. 两个独立硬门

### GPU buffer 审计

- [ ] 运行 `pipeline/audit_karin_xbg_mesh_buffers.py`。
- [ ] 状态为 `PASS_CLEAN_TARGET`。
- [ ] L0 精确为 84,586 triangles。
- [ ] L1 精确为 28,488 triangles。
- [ ] descriptor index coverage 连续，所有索引在声明流内。
- [ ] 不含 donor index sequence、donor faces 或 excess faces。

最终报告：`audit/xbg_mesh_buffers.json`，SHA-256 `03C75A11FBA7FFCEE5AEA36AD9E5E5D8A0B7FA5AFA32FEDDA6457BA0088832D7`。

### 全新进程回读

1. 完全退出 ZModeler，再启动唯一一个全新 Build 1244 进程。
2. 导入最终 XBG，`Root folder` 指向包含 `graphics` 的 validation 根，启用 `Retain mat-names`。
3. 根层仍必须恰好为 `char01.skel` 和 `char01.mesh`。
4. Structure 列表仍只能是 L0/L1；两者都必须显示完整 Karin。
5. validation 场景关闭时选择不保存。

冻结证据：

- `.work/release_freezes/karin_replacer_v1_3_0/evidence/zmodeler_fresh_reimport_l0.png`
- `.work/release_freezes/karin_replacer_v1_3_0/evidence/zmodeler_fresh_reimport_l1.png`

GPU 审计和全新进程回读缺一不可。

## 10. 运行时移交

1. 将 raw XBG 交给 `pipeline/build_karin_runtime_v13.py`；脚本只允许指定的 raw XBG 哈希。
2. 构建器只修改 XBG 材质表中的头发私有材质路径，网格和骨架 payload 必须逐字节不变。
3. workspace 必须恰好 22 项：1 XBG、19 XBT、1 私有材质、1 完整 Living City-compatible `graphickit_models.lib`。
4. 正式包外层必须恰好为 `karin_replacer.dat`、`karin_replacer.fat`、`modconfig.json`。
5. ModManager 中 Karin 必须位于 `Living_City` 上方；不重排其他用户 Mod。

## 11. 失败恢复

- UI 误点且未保存：不保存关闭，从最近只读 checkpoint 建立新 working。
- 已误保存 working：保留作失败证据，不覆盖 checkpoint。
- Compound 结构错误：回到 double-bound checkpoint，重新建立全新 Compound。
- XBG 审计失败：保留隔离输出，不复制到 runtime workspace 或游戏目录。
- fresh-process 回读失败：验证场景不保存；生产 checkpoint 保持不变。
- 哈希不符：先检查同步、路径和并行实例，不在 GUI 中继续试错。

每个正式门只保留输入哈希、关键成功截图、输出哈希和审计结果；不要追加逐坐标点击流水账。
