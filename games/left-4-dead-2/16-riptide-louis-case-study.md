# Karin Riptide 替换 Louis 案例

本文记录 `L4d2/riptide_replace_louis` 中可复用的成功、失败和排障证据。数字均为 **Riptide 项目实测值**，不是新项目通用常量。

当前证据状态：v1.3 已通过全部离线门禁，仍等待用户游戏内视觉复测。用户已确认的运行事实只有：旧超顶点候选加载 `tumtara` 崩溃；v1.2 可以加载，但半透明未按预期出现，角色额外屈膝且偏矮。

## 1. 目标与输入分工

- Output slot：Louis，世界路径 `models/survivors/survivor_manager.*`。
- 第一人称手臂：`models/weapons/arms/v_arms_louis.*`，不是 `manager_new`。
- HUD：`materials/vgui/select_louis.vmt`、`s_panel_manager.vmt`、`s_panel_manager_incap.vmt`。
- 用户模型：`Karin_Riptide_GeneralWorkflow.blend`；旁边 VRM 只作为动态骨和 collider 意图证据。
- 主动画与 proportion corrective 基准：Zoey/TeenAngst。
- Rest skeleton、54 个 jiggle 规则和 2 个 VRD helper：用户提供的成功同角色参考与派生 rig。
- Louis 原生资源：槽位接口、attachments、hitboxes、PHY 和输出路径证据。

参考 VPK 只有 14 个 payload，没有世界 `.phy`，也没有角色世界/手臂材质闭包。它能证明一种成功 Louis 路径/动画实现，但不能原样当完整发布树或原生 Louis 合同。

## 2. 首个崩溃：编译成功不代表 VTX 可运行

旧世界模型：

| 项目 | 旧失败候选 | 成功参考 |
| --- | ---: | ---: |
| Source triangles | 195,455 | 82,873 |
| VVD LOD0 vertices | 153,854 | 65,474 |
| Bodyparts | 25 | 14 |

用户启用旧包后，`tumtara` 在加载期稳定崩溃；关闭 Mod 则正常。三份 minidump 都是：

```text
0xC0000005 read
studiorender.dll + 0x6894F
```

故障指令在读取 16-byte tangent/vertex 数据。三次运行时地址计算都落到全局顶点 `157,035`，而 VVD 最大合法索引只有 `153,853`。

逐 VTX strip-group 解析后确认 companion 内部自相矛盾，而不是 addon 冲突：

- 至少 11,565 条 VTX vertex record 越过所属 MDL mesh/model 范围。
- 最大 VTX 引用全局顶点为 160,349。
- bodypart 0..12 累计 63,861 顶点仍合法；下一 bodypart 首次跨过 65,536，后续映射逐渐损坏。
- 成功参考总顶点 65,474，最大引用 65,473，映射完整。
- 游戏中实际安装 VPK 与 release 哈希一致；扫描 143 个启用 VPK 后，只有目标包提供 Louis world/arms 路径。

根因是 StudioMDL/optimizer 在聚合世界顶点越过 16-bit 安全域后静默生成坏 VTX。MDL/VVD/VTX/PHY checksum 一致、StudioMDL return 0、最大三权重，都没有发现这一错误。

### 新的强制门禁

- 世界 LOD0 工程上限 `<= 60,000`，硬拒绝 `>= 65,535`。
- 不只检查 VTX header。逐 bodypart/model/mesh 验证：

  ```text
  original_mesh_vertex_index < mdl_mesh.vertex_count
  mesh.vertex_index_start + original_mesh_vertex_index < mdl_model.vertex_count
  ```

- 每个 model 的合法 VTX 映射集合必须完整覆盖 `0..model.vertex_count-1`。
- `maximum_referenced_global_vertex + 1 == summed_model_vertices == VVD LOD0 count`。
- MDL/VVD/VTX/PHY 必须来自同轮构建，checksum 一致。

正式 RuntimeSafe 世界降为 10 个 bodyparts、59,248 个 compiled vertices；59,413 条 VTX 引用完整覆盖 0..59,247，零缺失、零越界。

## 3. Minidump 排障方法

这次有效的顺序是：

1. 立即复制并哈希保全全部 `.mdmp`，避免后续崩溃覆盖证据。
2. 比较异常码、模块和 ASLR 归一化 offset；三次相同 offset 说明确定性数据问题。
3. 反汇编 fault 指令，判断它在读 vertex/tangent、physics、material 还是 UI 数据。
4. 从寄存器和前序指令还原最终索引与基址计算。
5. 将运行时索引映射回 MDL bodypart/model/mesh、VTX original ID 和 VVD 上界。
6. 同时做 VPK 哈希、companion checksum 和已启用 addon 路径冲突扫描，排除混包。
7. 先修与 fault address 最吻合的数据层，再考虑 HUD、arms、PHY、flex 或 jiggle。

不要看到“启用 Mod 才崩”就从所有功能平均猜测。堆栈与越界索引已经指向 world render data 时，先降低几何并做 mapping audit。

## 4. 第二个反例：Louis 槽位不等于 Louis/Biker 动画基准

v1.2 使用 Louis `Manager.smd` 做 proportion corrective，并继承 Biker 动画。用户截图显示角色额外屈膝且比其他动漫 Mod 矮。

错误基准压短了 parent-local 腿链：

| Segment | v1.2 错误链 | Zoey corrective 后 |
| --- | ---: | ---: |
| Calf L/R | 11.3811 / 11.3968 | 14.0974 / 14.0974 |
| Foot L/R | 13.1329 / 13.1328 | 14.4564 / 14.4563 |
| Toe L/R | 3.8522 / 3.8522 | 5.0465 / 5.0464 |

错误链模拟 bounds 为 `-0.729216..58.522029`；正确 TeenAngst reference 为 `0.147763..66.564440`，顶部恢复约 8.04 Source units。

v1.3 改为：

- output path 仍是 Louis `survivor_manager`；
- corrective 公共骨 translation 来自当前 native `TeenAngst.smd`，SHA-256 `F75F261E...7327`；
- corrective/target rotation 都使用 Riptide rest，编译 proportion rotation delta 为 identity；
- 成功 Louis-path 合同的 1,011 条 declaration 原顺序保留：997 unique、14 个有意重复名；
- include 顺序：TeenAngst animation、TeenAngst gestures、Producer fallback、generic gestures、Biker gestures；
- 编译 1,015 sequences，尾部 `reference flags=0`、`proportions flags=12`。

后面三个 include 是该成功 Louis-path 合同的兼容回退，不推翻 Zoey 主动画/基准。

### 自然屈膝与错误屈膝要分开

正确 TeenAngst reference 中膝角接近 180 度，说明 rest/proportion 腿链完整；但 Zoey 的真实 standing/aim 动画本身约有 153..159 度的自然屈膝，并带 foot touch IK。这属于 authored pose，不应通过继续调 Pelvis 或缩放腿链强行消除。

## 5. Ground correction 与身高是两个问题

Riptide 最终鞋底 bind minimum 为 4.442911，原生 Louis 测量基准为 0.058585，因此：

```text
g = 0.058585 - 4.442911 = -4.384326 Source units
```

这个值只写入 proportion target Pelvis local Z。切换到正确 Zoey corrective 后仍保留它；没有修改 bind mesh/skeleton、Foot/Toe、physics、attachments、bbox 或 `$origin`。

v1.2 的偏矮来自错误 corrective 对腿链的压缩，不来自 ground offset。用 Pelvis offset 修屈膝/身高，或用 Foot/Toe/鞋网格修接地，都会把不同问题混成一个不可审计补丁。

## 6. 半透明反例：VTF 有 alpha 且写了 `$translucent` 仍不够

用户要求帽檐、袖子中段和雨衣下摆保留连续半透明。

第一次实现用 `$alphatest 1` / reference 0.5，把连续 alpha 二值裁掉。v1.2 改成 `$translucent 1`，VTF 也确实保留 981,034 个 partial-alpha pixels，但用户仍报告透明效果没有出现。

排除项：

- 安装 VPK 与 release 完全一致。
- DXT5 VTF alpha 未丢失。
- 原生 `survivors_it_shared.vmt` 没有冲突的 alpha/Phong/bump 参数。
- MDL 已有 translucent two-pass 相关 flag。

剩余差异是 v1.2 在 translucent surface 上仍组合 `$bumpmap` 和完整 Phong family。v1.3 采用 Karin_PT 已知简化 profile：

```vmt
"patch"
{
    "include" "materials/models/survivors/survivors_it_shared.vmt"
    "insert"
    {
        "$basetexture" "..."
        "$halflambert" "1"
        "$nocull" "1"
        "$nodecal" "1"
        "$translucent" "1"
        "$phong" "0"
    }
}
```

这个候选保留 bile shared patch，不再包含 `$bumpmap` 或 `$phongalbedotint/$phongboost/$phongexponent/$phongfresnelranges`。静态 shader/alpha gate 已通过，但 v1.3 的实际透明显示仍需用户游戏内复测；不能提前写成 runtime pass。

材质名中的 `Cutout` 是嵌入 SMD/MDL 的历史名字，不决定实际 shader alpha mode。

## 7. 参考 Mod 不能直接复刻

参考包虽然能运行，但具有以下边界：

- 65,474 compiled vertices，距离 65,536 只余 62，不能作为安全工程目标。
- 没有 `.phy`。
- 没有角色世界/手臂 VMT/VTF，材质闭包不完整。
- 混合 Zoey/Rochelle/Francis 的 include/fallback，不能被误称为原生 Louis 合同。
- 反编译 QC 存在重复 animation、独立 QCI 与 inline declaration 重叠、auto-hitbox 未完整恢复等 Crowbar 产物。

正确做法是提取“已运行成功的有序接口证据”，再用当前原生槽位和用户模型重建，而不是直接编译反编译 QC。

## 8. 第一人称、HUD 与发布经验

- Louis arms 固定为 `models/weapons/arms/v_arms_louis.*`。
- 本项目自定义 arms：65 bones、20,435 compiled vertices、最多三权重、VTX mapping 完整。
- HUD wrappers 是 `select_louis`、`s_panel_manager`、`s_panel_manager_incap`。
- 世界、arms、materials、HUD 应分别编译/验证，再组装到全新 loose tree。
- 修材质时 world/arms 二进制不应变化；修 proportion 时 HUD/VTF 不应无故变化。
- BaiduSync 曾生成 `*_冲突文件_*.vtf`。严格闭包门禁正确拒绝了旧输出树；正式流程改用全新 v1.3 目录，而不是删除未知冲突文件后继续原地打包。
- 旧 release 在提升新候选前完整归档；正式 VPK 再做一次 33 个 payload 逐字节比较。

## 9. 当前 v1.3 离线合同

- World checksum `4D8B5671`；127 bones；10 bodyparts；59,248 vertices。
- 54 JiggleRule + 2 QuatInterp helper；30 attachments；17 hitboxes；18 PHY solids。
- 5 local animations / 601 frames；1,015 sequences；Zoey 主动画合同通过。
- Arms checksum `B1681CC3`；65 bones；20,435 vertices。
- 8 world VMT + 10 VTF；3 HUD VMT + 3 VTF。
- VPK 33 payload，SHA-256 `EBA3EA...1933D`。
- 最终离线验证 21/21；runtime 状态仍为 `pending_user_visual_retest_v1.3`。

## 10. 证据路径

- `L4d2/riptide_replace_louis/reports/diagnostics/tumtara-load-crash-isolation-20260812.md`
- `L4d2/riptide_replace_louis/reports/diagnostics/world-vertex-mapping.json`
- `L4d2/riptide_replace_louis/reports/diagnostics/reference-world-vertex-mapping.json`
- `L4d2/riptide_replace_louis/reports/diagnostics/zoey-proportion-height-knee-fix-20260813.md`
- `L4d2/riptide_replace_louis/reports/build/world-qc-assets-zoey-v1.3.json`
- `L4d2/riptide_replace_louis/reports/build/compiled-model-audit-zoey-v1.3.json`
- `L4d2/riptide_replace_louis/reports/diagnostics/zoey-v1.3-world-vertex-mapping.json`
- `L4d2/riptide_replace_louis/reports/materials/uv2-runtime-candidate-matrix.md`
- `L4d2/riptide_replace_louis/reports/materials/uv2-translucency-v1.3.json`
- `L4d2/riptide_replace_louis/reports/release/final-validation-v1.3.json`

## 11. 不得复制为通用常量的值

59,248 vertices、127 bones、54 jiggle rules、`-4.384326` ground offset、1,011 declarations、1,015 sequences、五项 include 和 flags 12 都是 Riptide 当前输入/参考的项目合同。新角色必须重新审计；可复用的是分层方法、Source 上限、VTX mapping gate、Zoey 默认策略和证据闭环。
