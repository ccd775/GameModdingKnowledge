# 构建流水线：源模型 → `pak_mods` 包

一条命令重建全部资产（项目里是 `build_all.sh`，[便携包](../../portable-kits/dragons-dogma-2/README.md) 写了逐步命令）。
两个模型共用同一套脚本，差异放在 profile 里（`picodra` / `original`：源文件、资产路径、材质表、链表、物理变体）；
加 profile 时必须证明旧 profile 的构建逐字节不变。

```text
Blender build_karin_body.py  →  karin_body.mesh.240423143（RE Mesh Editor 0.66 导出）
DD2Tool meshconv … "DD2"     →  .mesh.260421070
DD2Tool meshreorder          →  前 192 根骨恢复原生 body_000_f 顺序
patch_mesh_header.py         →  头部 flags = 4099
DD2Tool meshinfo             →  骨表 / 材质 / 组 JSON（chain 生成要用）
build_karin_textures.py      →  *_ALBD / *_NRMR / *_ATOC .tex.251211553
DD2Tool mdfbuild <spec>      →  .mdf2.51
make_chain_spec.py + DD2Tool chainbuild → .chain.55
DD2Tool pack <out.pak> <staging>       →  pak_mods/<Mod>.pak
```

## 1. 骨架：原生骨名 + 源模型比例（invariant 级做法）

- 输出网格带**完整 192 根 DD2 女性身体骨**（名字、父子关系、DD2 静止朝向都不变），只把关节**位置**移到源模型的位置。
  游戏构建身体时按网格骨架建立 joint 表，所以运行时骨架就是 Karin 比例，网格零变形；动画按骨名驱动照常工作。
- 统一缩放 `s`：源模型 Hips 高 = DD2 Hip 高 0.9667 m，脚底留在地面（PicodraTech `s = 1.4428`）。
- **重摆姿势**：四肢逐段对齐到 DD2 静止方向（手掌用整帧对齐；末端节用 DD2 的 X 轴，并按父段方向定号——右侧 RE 骨的
  X 轴朝回指），姿势烘进几何。不做这一步，动画会把源模型的 T-pose 偏差放大到每一帧。
- 没有映射的辅助骨（twist / offset / 道具挂点 / 体型编辑骨）按「源模型段长 / DD2 段长」的局部比例放置。
- 源模型的次级骨（头发、尾巴、外套、缎带……）保留为 `K_<名字>`，挂在映射后的 DD2 骨下，供 chain 使用。
  **`K_*` 骨的局部 +X 必须指向子骨**（原生链骨都如此），否则 chain 回弹目标错乱。只保留带权重的次级骨及其祖先；
  链末端不带权重的 `_end` 子骨按需保留（链要摆动最后一根加权骨，需要它的下一个节点）。

## 2. 权重

- 人形骨直接改名（Hips→Hip、Head→Head_0、手指 `ThumbProximal.L` → `L_Hand_ThumbF_1` ……）。
- Spine/Chest 按高度平滑分到 `Spine_0/1/2`，Neck 分到 `Neck_0/1`。
- 上下臂、大小腿按轴向投影分到 `*_Twist_0/1/2`（t = 0、1/3、2/3），与原版身体一致。
- 每顶点 ≤ 8 个影响；**每个网格最多 256 根加权骨**（构建时断言）。骨不够时把最大权重很小（< 0.12）的次级骨并回父骨。
- 源模型的「收肢 / 换装」形态键在拆分前烘进几何（`bake_shape_keys`）。

## 3. 骨序

Blender / RE Mesh Editor 导出会按深度优先重排骨骼。`DD2Tool meshreorder <in> <body_000_f 参照> <out>` 把前 192 根
恢复为原生顺序，`K_*` / `KF_*` 接在后面。

## 4. 网格组与可见性

- 一个材质一个子网格；可见组 0..7。游戏只开 group 0，替换脚本对 1..7 调 `setPartsEnable(i, true)`。
- 两套 UV：UV0 = 源 UV，UV1 = 拷贝（DD2 顶点布局带两条 UV 流）。
- 所有 LOD 槽都写（可复用 LOD0 几何），缺 LOD 会崩。

## 5. 兼容桩子网格（必须有）

游戏的逐角色材质系统（皮肤细节、脏污、伤口、VFX、皮肤烘焙）按名字在身体网格上找 `body_mat / hand_mat / nail_mat / vfx_mat`。
输出网格另带 4 个**零面积三角形**子网格（位于 Hip），名字就是这 4 个；MDF 里这 4 条材质从运行时
`body_runtime_human.mdf2` 复制。

- 实验（`rejected`）：把原生身体的真实子网格藏进一个关闭的可见组（`--native-compat`）——皮肤烘焙照样崩，
  且游戏内 Karin 贴图全是占位棋盘格（未驻留，原因未查）。保留零面积桩。

## 6. 贴图与 MDF

- 每张图集出三张：`_ALBD`（BC7 sRGB，RGB 颜色）、`_NRMR`（BC7：RG 法线 XY，OpenGL 约定；B 法线 Z；A 粗糙度）、
  `_ATOC`（BC1：R alpha、G 透光 = 1、B AO = 1）。源法线是 DirectX 约定时翻 G；没有法线图的源（Original）用平法线。
  以一张原生 `.tex.251211553` 作头部模板，经 texconv 压缩后由 DD2Tool 写 TEX。默认 2048（大于 2K 会被降采样）。
- MDF：每个材质克隆 `Character_Default.mmtr` 的原生条目（模板 `body_001_f.mdf2.51` 的 `nail_mat`），按 spec 换贴图路径与 flag
  （透明部件开 `BaseAlphaTestEnable` / `BaseTwoSideEnable` + `AlphaTestRef`）。PicodraTech 用 7 个唯一材质名
  （皮肤 / 脸 / 眼透明 / 头发 / 头发透明 / 衣 A / 衣 B），再加上 4 个兼容材质。

## 7. 表情骨与 chain

- 表情：形态键增量编码成 `Head_0` 下的平移骨 `KF_*`，见 [表情](FACIAL_EXPRESSIONS.md)。它们也占加权骨预算
  （PicodraTech 原有 249，并掉两根弱骨后加 7 根 → 254；Original 164 + 13 → 177）。
- chain：`make_chain_spec.py` 从 `meshinfo` 的骨表生成 `chainbuild` spec，见 [chain 物理](CHAIN_PHYSICS.md)。

## 8. 打包

- 资产放独立路径：`natives/STM/Character/_karin/karin_body.{mesh.260421070, mdf2.51, chain.55}` + `tex/`。
  第二个模型用 `Character/_karin_original/karin_original_body.*`，两个 Mod 的资源不冲突（脚本互斥，见 [运行时注入](RUNTIME_INJECTION.md) §3）。
- `DD2Tool pack` 把 staging 目录打成 KPKA，放进 `<game>/pak_mods/`。staging 每次构建前清空，否则旧产物被一起打包。
- 确定性：PicodraTech 从源模型重建逐字节一致（v1.2 资产与 v1.1 / rc6 相同）。Original 的 Blender 那一步重跑每次相差约 11 字节（原因未查，对游戏的影响未测）；从同一份 Blender 输出往后重建逐字节一致（f5 与测试包相同）。

## 9. Blender 侧

- Blender 4.5.12 LTS + RE Mesh Editor 0.66（导出旧版 `240423143`）。`blender -b --factory-startup --python build_karin_body.py -- <out>`。
- 只读源 Blend；所有派生物写到项目工作目录。
- 第二个源模型（FBX）先经 `prepare_karin_original.py` 整理成同样结构的 Blend（骨名、材质、贴图页）。
