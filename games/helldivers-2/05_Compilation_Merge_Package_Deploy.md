# 编译、合并、打包、部署与回滚

> 置信度：流程在 New_SR24 多个版本中重复执行；最终 V21 R2 通过 52/52 集成和两次独立构建逐字节一致。具体 patch index、资源计数和哈希仍是案例数据。

## 编译前冻结

进入编译前必须冻结：

- authoring `.blend` 的 SHA-256。
- donor triplet、target FileID 映射、local palette 合同。
- 本次允许改变的对象/权重/rest/material section。
- 编译器脚本 SHA-256 和参数。
- 输出目录必须不存在且位于 `Work/candidates/`。

不要让编译脚本在原 `.blend` 上保存；运行前后重新哈希所有不可变输入。

## 推荐编译阶段

### 1. Preflight

在写 archive 前拒绝：

- 缺失 `Z_ObjectID` / `Z_SwapID_N`。
- donor/target 数量或 ID 不符合项目清单。
- object transform 非 identity。
- 未知 `0_N`、未加权点、超过 influence 上限、权重和异常。
- 材质 section 数/LOD 数超出 donor 合同。
- draw range、vertex stride、UV 数与预期不符。
- 输入报告或脚本哈希不匹配。

### 2. Visible compile

以 whole-unit donor 方式编译可见 Unit。每个 Unit 报告应记录：

```text
target FileID
donor FileID
source object(s)
logical role / compile count
complete carrier FileID and locked triplet hash
clone target FileIDs, if used
LOD
vertex / triangle / index counts
material sections
local palette and BoneInfo
TransformInfo / MeshInfo / inverse-bind provenance
patch/gpu/stream byte ranges
```

多目标使用完整 carrier clone 时还必须报告：

- `compile_count_by_role == 1`。
- 保存/回读前后的 `TransformInfo` 与核心 bone-bind signature 一致。
- AQ 因材质 section 重建的 BoneInfo remap 落在显式允许列表。
- 同角色所有 clone target 的完整 Toc/GPU/Stream payload 唯一哈希数为 1。
- culling body 与不属于本次修改的 Unit/LOD 保持冻结。

不要把同一 RawMesh 分别编入多个未经证明相容的 target-native Unit。Umbrella v1 的运行时反例与 v2 carrier-per-role 方法见 [案例](case-studies/Karin_Umbrella_RS6_RS67_RS100.md)。

### 3. Compiled postflight

使用独立读取路径解析刚生成的 triplet，检查：

- 目标 FileID 存在且无重复。
- donor 字段确实被携带。
- RawMesh 与 authoring 的位置、indices、UV、weights 对应。
- 所有 LOD、Slim/Stocky、左右分件都存在。
- 修改域外字段/Unit 与冻结基线一致。

编译器自己的“成功”日志不是独立证据。

### 4. Complete Main

将 visible compile 与冻结 suppression Unit 合并，覆盖 manifest 中完整目标集合。此阶段只允许新增/替换明确列出的 Unit，不加入材质或无关参考包 payload。

### 5. Material pipeline

保持模型和材质 patch 分开演进，直到最后合并。建议顺序：

```text
base materials/textures
-> special head/alpha material
-> face material
-> private namespace migration
-> model material-ID rewrite
-> opaque/AlphaClip final draw correction
-> emission/color final patch
```

每一步使用新路径并生成 delta 报告；不要原地覆盖前一阶段。

## AQ / ArchiveQT 并发限制

已确认 AQ 会使用共享系统临时贴图路径。两个 Blender/AQ 进程并发执行 archive merge、material rewrite 或 integration audit 时，可能出现：

- 临时 DDS 被另一个进程替换。
- `OSError 22`。
- 单资源 load-save 不一致。
- 报告失败，但最终三件套碰巧与成功候选同哈希。

执行规则：

1. 所有 AQ 写操作串行。
2. 集成审计也串行，避免读写共享临时文件。
3. 必要时为单个进程指定独立 `TEMP`/`TMP` 目录。
4. 任务结束后验证输入哈希未变。
5. 失败报告永远保留为失败；即使输出碰巧正确，也重新串行运行并生成新接受报告。

`--factory-startup` 可能使 AQ 插件未注册。使用前先做插件导入/版本 preflight，不能把 Blender 正常启动当作 AQ 可用。

## 合并合同

最终合并器应验证：

- 资源类型和 FileID 唯一。
- 资源数量与显式 manifest 完全一致。
- 每个资源 payload 来自指定上游，SHA-256/区间一致。
- GPU/stream offset、size 和边界合法，无重叠。
- Unit 使用 load-only 语义验证，Material/TextureMap 按工具能力 load-save。
- model -> child Material -> TextureMap 引用闭合。
- 私有 full-ID 和 high32-ID 不与 donor/已安装资源冲突。
- 最终 Head/特殊 draw 的 material ID、start/count 逐 LOD 正确。
- 完整 archive roundtrip 后三文件达到项目定义的字节身份。

合并报告必须绑定所有上游正式报告的路径和哈希，且拒绝 `accepted != true` 的 binding report。

## 确定性三成员 ZIP

推荐合同：

- 成员恰好为 patch、`.gpu_resources`、`.stream`。
- 成员顺序固定。
- `ZIP_STORED`，不使用可能受库版本影响的压缩参数。
- 时间戳固定为 1980-01-01 00:00:00。
- 文件 mode 固定。
- 写入后 `testzip()`/CRC 通过。
- 每个成员的解包 SHA-256 与源 triplet 一致。
- 输出 ZIP 和报告路径必须不存在；不覆盖旧发布证据。
- 打包器禁止写入 live game data tree。

已验证实现入口见 [tools/README.md](tools/README.md)。项目脚本会检查源三件哈希、固定 ZIP 元数据并写机器报告。

## 独立复现

“重新运行同一命令”至少要做到：

1. 使用新输出目录和新报告路径。
2. 输入 triplet、脚本和参数完全相同。
3. 如涉及 AQ，使用串行、隔离临时目录。
4. 比较两份 package report 的 source/member contract。
5. 比较 ZIP 大小、SHA-256 和逐字节内容。
6. 再次确认输入文件前后未变化。

不能用复制第一份 ZIP 伪造“第二次构建”。

## 部署前检查

部署是外部状态写入，只有用户明确授权后才能执行。

### 先冻结互斥部署模式

- **新槽安装（默认）**：目标三路径必须不存在，patch index 高于当前同 archive 最大值。
- **精确旧版替换（例外）**：只用于用户明确要求替换的同一 Mod lineage。live 三件套必须逐份匹配已诊断旧版哈希；碰撞扫描只排除这一个精确旧 triplet；旧新版禁止以任何 index 共存。任一 live 哈希变化即停止。

replacement 包的生成不等于已获部署授权。优先由 Mod Manager 禁用/卸载精确旧版后安装替换包；若执行直接文件替换，必须另有明确授权、可恢复旧三件套和逐文件前后哈希记录。

### 必须满足

- `helldivers2.exe` 未运行，并在 staging 后再次检查。
- `game-data` resolve 后恰为 `...\Helldivers 2\data`。
- source triplet 三份哈希与发布报告一致。
- 部署模式已明确且满足对应前置条件；新槽要求目标三路径不存在，精确替换要求旧三件套哈希完全匹配。
- 新槽模式的 patch index 高于当前同 archive 最大值；替换模式的 archive/index 精确等于被替换 lineage。
- 部署报告输出路径不存在。

### 安全写入算法

```text
source -> unique hidden temporary file in game data
       -> flush + fsync
       -> SHA-256 verify
       -> recheck game process and mode-specific destination contract
       -> atomic rename each exact member
       -> post-deploy SHA-256 verify
```

中途失败时，仅回滚/删除本次生成且哈希仍匹配的精确文件。不得用递归删除、glob 或“清理所有 patch”命令。replacement 模式必须在写入前记录可恢复的旧 triplet；不得只保留旧文件名而没有内容/哈希。

## 直拷部署

对于此类 HD2 patch Mod，部署的资源单元仍是精确三份文件，不需要 Arsenal。新槽模式直接复制到空目标；replacement 模式先由已授权流程移除/替换哈希匹配旧版。不要额外复制 ZIP、manifest、参考 Mod 子目录或多个候选 triplet。

部署报告至少记录：

- 时间、游戏目录、archive ID、patch index。
- 部署前后 index 列表。
- source 与 installed 三份的路径/大小/SHA-256。
- 新槽模式记录 `preexisting_files_overwritten: false`；replacement 模式记录旧文件是否由 Mod Manager 先移除或被精确替换，并绑定旧内容备份/恢复证据，禁止未记录覆盖。
- `deployment_mode: new_slot | exact_lineage_replacement`；replacement 时另记旧三件套路径/大小/SHA-256、恢复位置和 `old_and_new_coexist: false`。
- `game_launched: false`，除非另有单独启动证据。
- 回滚所需精确路径和哈希。

## 回滚

回滚不是“删掉最新 patch”。必须：

1. 确认游戏未运行。
2. 对部署报告中的三个精确路径逐一读取。
3. 三份都存在且 SHA-256 与部署报告匹配。
4. 只删除这三个精确文件。
5. 如果任何一份不匹配，停止并报告外部状态变化。

历史 index、文件名排序或修改时间都不能替代哈希匹配。

## 发布物卫生

- `Output/` 只保留当前接受的交付物和绑定报告。
- 用户拒绝、门禁失败或 superseded 的包可恢复地移至 `Work/candidates/<reason>_do_not_use/`。
- 不删除失败证据；它们是避免回归的重要输入。
- 不把 `.blend1`、autosave、TEMP、preview、日志或解码纹理塞入 ZIP。
- README 中诚实声明复制 LOD、gibs、splat、透明或其他未验证限制。

## 示例命令形态

路径和哈希仅作占位，必须替换为当前项目值：

```powershell
python .\Work\scripts\package_karin_hd2_single_triplet.py `
  --source-patch .\Work\candidates\final\Main\ARCHIVE.patch_BUILD `
  --archive-id 0123456789abcdef `
  --patch-index 12 `
  --expected-patch-sha256 <PATCH_SHA> `
  --expected-gpu-sha256 <GPU_SHA> `
  --expected-stream-sha256 <STREAM_SHA> `
  --output-zip .\Output\character_v1_patch12.zip `
  --report .\Output\character_v1_patch12-package.json
```

部署命令不得放进无人复核的自动流水线；执行前重新确认授权和 live 目录。
