# 构建流水线

命令都在便携包里（[使用说明](../../portable-kits/nioh-3/README.md)）。构建脚本以环境变量 `N3_BUILD` 指向的工作目录为根：
`orig/` 放原版文件副本，`source/` 放源模型导出，`g1m/`、`g1t/` 放产物。游戏在另一台测试机上，命令和文件走 SSH，界面操作走用户会话。

## 1. 定位要改的资源

1. **按阶段追踪游戏读了哪些资源**（测试机，管理员权限）：
   ```text
   logman start n3fio -p Microsoft-Windows-Kernel-File 0x190 0x4 -o <trace dir>\n3fio_01.etl -bs 1024 -nb 64 512 -max 4096 -ets
   （启动游戏；每到一个阶段在 <trace dir> 里新建 MARK_<nn>_<名字>.txt：主菜单、载入、进关卡、换流派……）
   logman stop n3fio -ets
   tracerpt <trace dir>\n3fio_01.etl -o reads.csv -of CSV
   etw_reads.py reads.csv <游戏目录>\package reads.json [--patched]
   ```
   `etw_reads.py` 把游戏进程对每个容器的读操作映射回 `root.rdb` 记录，按阶段输出资源。已经装了 mod 时，`--patched` 按当前的表映射。
   `phase_diff.py` / `phase_only.py` 求几个阶段的交集或差集。
2. **从模型找到它的伙伴资源**：`model_refs.py <package> <模型>` 列出 CharacterEditor 里的条目、属性和引用的资源（贴图表、物理注册表、每材质计数）。
3. **找当前染色**：[材质与贴图](MATERIALS_AND_TEXTURES.md) §2 的五步。
4. **提取原版文件**：`extract_many.py <package> <输出目录> <哈希列表>`（有 `root.rdb.original` 时从它读，所以装了 mod 也能取到原版）。
   全部放进 `$N3_BUILD/orig/` 并记下 sha256，之后的构建只读这些副本。
5. 统计格式时用 `census.py`（`root.rdb` 按类型计数）、`missing.py`（缺了哪些容器）、`dump_names.py`、`g1m_summary.py`、`g1m_subs.py`、`rec_params.py`。

本案例的结论（[技术合同](TECHNICAL_CONTRACTS.md) §3.3、§6）：主菜单阶段只读到上衣和袴；进关卡阶段才读到手甲、额饰和当前染色贴图。
Karin 写进忍者上衣 `0x5548953f` 和武士上衣 `0xed9b4309`，其余 13 个模型隐藏。

## 2. 源模型

```text
blender -b --factory-startup --python scripts/blender/ko_extract_source.py -- <Karin.fbx> $N3_BUILD/source
blender -b --factory-startup --python scripts/n3build/blender_shapekeys.py -- <Karin.fbx> $N3_BUILD/source
```

- `ko_extract_source.py`（浪人崛起项目的脚本）把 FBX 的网格、骨骼、权重和 UV 导出成 `source.json` / `source.npz`，形态键按预制体的值应用。Blender 4.0.2。
- `blender_shapekeys.py` 导出每个形态键相对 Basis 的世界空间位移（`shapekeys.json` / `shapekeys.npz`，和源模型放在同一个 `source/` 里），与预制体当前的组合无关；表情拟合和换装形态键都从这里读。
- `n3_common.EXTRA_SHAPE_KEYS` 在预制体的组合之上再加形态键，可按源模型高度遮罩：`(名字, z_keep, z_full)`，z ≥ z_keep 权重 0、z ≤ z_full 权重 1、中间线性。
  `[C]` `body_2` 的 `kisekae_UppeLeg 2`：`(0.515, 0.49)`，把袜子里的大腿皮肤收进去，袜口那一圈（z 0.523–0.525）不动（build23）。

## 3. 贴合到游戏骨架

`n3_conform.py`（方法来自浪人崛起的 `ko_conform.py`，换成本作的骨号）：

- 源模型整体缩放（`N3_HEAD_SCALE`，默认 150）后平移，让 Karin 的 Neck 落在游戏骨 11 上。头和颈保持刚性；其余人形骨各拟合一个仿射（骨段方向和长度，保持截面），
  按 Karin 自己的权重做线性混合。
- 权重：
  - 皮肤和贴身衣物：从原版基础身体 `0x4ba258df` 按最近点迁移（原版的扭转 / 辅助骨分布），距离越远越淡出；手保留映射过来的手指权重；
  - 头、头发、耳朵 → 骨 12；尾巴 → 骨 2；
  - 袖子不跟手（不用手和手指骨）；
  - 裙子从胯骨向最近的腿部皮肤过渡，越往下摆越跟腿。
- 带跨侧检查：左边的顶点不能拿右边骨的权重（按骨架父子链判断左右，不按骨号奇偶）。
- 输出 `conformed.npz` + `conform.json`。

## 4. 物理与表情数据

- `n3_physics.py`（默认用 Karin VRM 的弹簧链，需要 `N3_VRM` 指向 VRM 文件；`--geometry` 是早期按几何形状推的 11 条链）→ `physics.json`：
  每条链的挂接骨、模板、点、碰撞组和逐顶点权重。详见 [物理](PHYSICS.md) §3。
- `n3_face.py [--extended]` → `face.json`：脸的逐顶点面部骨权重。详见 [表情](FACE.md)。

## 5. 写 G1M 并读回

```text
n3_build_g1m.py ninja   --physics --collide --face
n3_build_g1m.py samurai --physics --collide --face
n3_validate_g1m.py $N3_BUILD/g1m/0x5548953f.g1m $N3_BUILD/orig/0x5548953f.g1m --layout-changed --physics
```

- 写入规则见 [技术合同](TECHNICAL_CONTRACTS.md) §3.4。调色板超过 85 时那个子网格改用 u16 索引，上限 128；超过 128 时把权重最小的骨合并到最近的保留祖先，
  物理关节和面部骨不允许合并。
- 构建时丢掉源空间面积为 0 的三角形（build22 起，与浪人版做法相同）。
- `n3_validate_g1m.py` 用 `g1m_tool.py` 独立读回：块与节能解析、索引范围、调色板大小、每个条目都有原生绑定、权重和为 1、骨索引是 3 的倍数且在调色板内；
  除了预期的块以外其余字节不变。
- 离线检查（便携包 `scripts/checks/`）：`swing.py`（绑定姿势漂移，以及每条链单独绕根部转动时只有它自己的顶点在动）、`facecheck.py`（按面部姿势蒙皮渲染）、
  `diff24.py`（两个构建之间哪些块变了，新碰撞组的世界坐标）。

## 6. 贴图

- `n3_textures.py` → `$N3_BUILD/g1t/`：图集和常量槽（[材质与贴图](MATERIALS_AND_TEXTURES.md) §3–4）。
- `n3_g1t.py` 按原版容器写回；尺寸变了用 `n3_g1t_resize.py`（2048 模板 → 4096 图集）。

## 7. 注册表、计数、贴图表、塌缩

```text
n3_registry.py ninja
n3_registry.py samurai
collapse_set.py <输出目录> 0x4ba258df 0xb24cac84 … --from $N3_BUILD/orig
ktid_repoint.py <package> <变体 KTID> <输出文件> 0=<G1T> 1=<G1T> …
```

- `n3_registry.py` 读原版注册表和构建好的模型，写出物理注册表和每材质计数（[技术合同](TECHNICAL_CONTRACTS.md) §5）。
- `collapse_set.py` 用 `g1m_tool.py hide --all` 塌缩要隐藏的模型。
- 贴图表：`ktid_repoint.py`（按 G1T 哈希找对象）或 `ktid_setref.py`（直接写对象）；变体表可以直接复制一张改好的。

## 8. 安装到测试机

```text
n3inject.py install <游戏目录>\package <覆盖文件目录>
n3inject.py verify  <游戏目录>\package <覆盖文件目录>
n3inject.py restore <游戏目录>\package
```

- 覆盖文件目录里只放 `0x<哈希>.<扩展名>`。本案例 33 个：两件上衣、两个注册表、两个计数、5 张贴图（两张 COLOR、NORMAL、SHADING、49 号槽）、9 张贴图表（忍者 3 张、武士 6 张），以及 13 个塌缩模型。
- 每个构建在测试机上单独一个目录（`build<n>`），不覆盖已有构建；安装前游戏必须关闭。
- 远端传文件：单次超过 2–3 MB 会让隧道卡住几分钟，大文件分块传；截图先转 JPEG。路径一律写正斜杠。

## 9. 发行包

见 [验证与发布](VALIDATION_AND_RELEASE.md) §3：只带自制文件，安装器从玩家自己的游戏数据生成塌缩模型，按原版 sha256 拒绝不符的版本。
