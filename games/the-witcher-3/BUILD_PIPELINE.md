# 构建流水线

命令和环境变量见 [便携包](../../portable-kits/the-witcher-3/README.md)。这里讲每一步做什么、产物是什么、怎么判断它成功了。

```text
prepare.ps1（一次）           pipeline.ps1（每一版）
 bundle 清单 ─────────────┐     karin_build.py（Blender）──► karin_body.w2mesh、karin_face.w2mesh、*.xbm、dyng 规格、表情规格
 原版资源提取 → uncook\     │     make_stub_mesh.py ─────► 颈部过渡存根
 物品模板提取 → extract_items\    make_dyng.py ─► WolvenKit ─► fix_cr2w_skeleton_names.py ─► karin_body.w3dyng
 WolvenKit：模板 / dyng / w3fac ─► JSON      make_dangle_item_template.py ─► WolvenKit ─► karin_coif_item.w2ent
 空物品模板                │     make_w3fac.py ─► WolvenKit ─► fix_cr2w_skeleton_names.py ─► karin_face.w3fac
                         │     make_head_item_template.py ─► WolvenKit ─► karin_head_face_item.w2ent
                         └──►  build_mod.py stage（817 个模板路径 + depot）─► pack ─► w3metadata_write.py ─► [部署]
```

## 1. 准备（`prepare.ps1`，一次）

- 复制 WolvenKit 7 nightly 到工作目录的 `tools\wk7`，把 `.exe.config` 的 .NET sku 从 4.8.1 改成 4.8。
- `w3bundle.py list -v` 列出全部 bundle → `scratch\all_bundles.tsv`（`build_mod.py` 从这里找杰洛特的全部物品模板路径）。
- 提取到 `uncook\`：`man_base.w2rig`、杰洛特身体网格（预览对比用）、`h_01_mg__geralt` 头（含 w3fac）、`c_02_mg__half_tail`（dyng 模板）、
  `man_geralt_movement.w2anims`（待机姿势、离线检查用的走跑动画）。提取到 `extract_items\`：全部 `geralt_items` 模板。
- WolvenKit 把三个模板（裸躯干、`c_01_mg__witcher` 发型、`h_01_mg__geralt` 头）、半马尾 dyng 和杰洛特的 w3fac 转成 JSON；生成空物品模板。

## 2. Blender 构建（`karin_build.py`）

按顺序：读 `man_base` 骨架 → 取待机姿势 → 导入 Karin 的 FBX → 逐骨映射（[角色拟合](CHARACTER_FIT.md)）→ 贴图（PNG 写到 `karin_src\textures`，
xbm 写进 depot）→ 处理每个网格（拟合、权重重定向、保留物理链骨、裙子跟随大腿、采集脸部形状键）→ dyng 规格（[物理](PHYSICS.md)）→ 合并身体网格、
加 dyng 骨 → 表情求解与脸部骨架（[表情](FACE.md)）→ 导出两个 w2mesh → 报告。

- 成功的标志：日志里有 `[karin_build] DONE`（`pipeline.ps1` 检查它），`scratch\karin_build_report.json` 里有 `fit`、`meshes`、`dyng`（节点、链接、
  三角形、模拟节点数、代理半径）、`face`（骨数、残差历史）、`export`。
- `dyng_bone_matrix_err`：加进导出骨架的 dyng 骨重新读出的 W3 世界矩阵和规格的最大差（v0.4.4 约 2.7e-6）。
- v0.4.4 的报告：230 个节点、361 条链接、91 个三角形、80 个模拟节点；网格 176 根骨，其中 91 根 dyng 骨；代理半径：大腿 c0 / c1 / c2
  0.098 / 0.094 / 0.081 m、膝 0.060、上臂 0.071–0.073、髋 0.169、背下 / 中 / 上 0.173 / 0.111 / 0.120、头 0.231。
- 可选：`karin_preview.py` 重新导入导出的 w2mesh，和源 blend 比包围盒和顶点数，渲染正 / 侧视图和测试姿势。

## 3. 资源与模板

- `make_dyng.py`：dyng 规格 → 以半马尾 dyng 为模板的 JSON（替换全部数组，给每根骨补 `name`）→ WolvenKit `json2cr2w` →
  `fix_cr2w_skeleton_names.py`（日志 `fixed 230 bone names`）。
- `make_dangle_item_template.py --fur drop --wind 0 --gravity 0`：发型物品（[技术合同](TECHNICAL_CONTRACTS.md) §4）。`--fur stub` 保留毛发组件但让它们
  渲染存根网格（备用）；`--dampening` 只在实验时传。
- `make_w3fac.py` → WolvenKit → `fix_cr2w_skeleton_names.py`（日志 `fixed 356 bone names`：两个骨架的骨和轨道）；
  `make_head_item_template.py`：头部物品。
- 关掉表情（`{"face":false}`）时不写头部物品，头保持空模板；关掉物理（`{"physics":false}`）时退回里程碑 1 的布局：Karin 网格放进一个由裸躯干模板改成的
  头部物品（`make_mesh_item_template.py`），发型为空。

## 4. 打包与部署

- `build_mod.py stage`：按 bundle 清单写 817 个模板路径（剑鞘除外），再把 depot（Karin 的网格、贴图、dyng、w3fac、存根和颈部过渡存根）叠上去，
  共 829 个文件。`pack`：v5 bundle，zlib。`w3metadata_write.py`：给 `content\` 写 v7 store。
- v0.4.4：`blob0.bundle` 8 041 799 B，`metadata.store` 147 450 B。
- `-Deploy`：杀掉正在运行的游戏、等句柄释放（进程消失后再等 2 秒）、复制、启动 `bin\x64_dx12\witcher3.exe`。**用户在玩时先问。**

## 5. 确定性

- 打包这一段是确定的：同一个 depot，`-SkipBlender` 重跑得到逐字节相同的 bundle 和 store（项目里用 v0.1.0 验证过）。
- Blender 这一段不是逐字节确定的：
  - 身体 w2mesh 的顶点顺序每次运行都可能不同（插件导出器内部的顺序）；顶点位置、按骨名的权重、面、UV 作为多重集合完全相同；
  - xbm 里写着源 PNG 的绝对路径：工作目录换了，xbm 和 bundle 的字节都会变，像素不变。
  所以「重建是否等价」要按内容比（[验证与发布](VALIDATION_AND_RELEASE.md) §1），bundle 的哈希只用来标识某一次发行。dyng、w3fac、脸部网格、模板在
  多次运行间逐字节相同。
